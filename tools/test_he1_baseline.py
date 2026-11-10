#!/usr/bin/env python3
"""Self-tests for `tools/he1_baseline.py`.

The baseline gate compares 128 payloads with a real binary, which makes it a
slow place to learn that the comparator has a hole. These tests exercise the
same code paths on two synthetic snapshots: no Rust build, no `definitions/`
scan, no subprocess except the timeout test.

The property that matters most is the one the first draft of the split got
wrong: when the implementation receipt differs, the envelope is skipped **and the
payload is still compared**. A comparator that silently stops comparing is worse
than a comparator that fails, because the gate would stay green.

Run: `python tools/test_he1_baseline.py`
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import he1_baseline as baseline  # noqa: E402


def synthetic_snapshot():
    """The smallest snapshot the comparator accepts."""
    return {
        "schema": baseline.SCHEMA,
        "projections": {
            "payload": baseline.PAYLOAD_PROJECTION,
            "envelope": baseline.ENVELOPE_PROJECTION,
        },
        "provenance": {
            "original_baseline_commit": "0" * 40,
            "projection_recording_commit": "1" * 40,
            "projection_recording_worktree": "dirty",
        },
        "implementation": {
            "name": "fmp-materialize",
            "version": "0.0.0",
            "binary_sha256": "sha256:" + "1" * 64,
        },
        "toolchain": {"rust": "cargo test", "python": "Python test"},
        "definitions": {"count": 1, "newest": {}, "documents": []},
        "corpus": {"positives": 1, "negatives": 1, "by_isa": {}, "negative_phase_split": {}},
        "oracle": {"kinds": {"assembler": 1}, "manual_derivation": []},
        "artifacts": {
            "count": 1,
            "payload_root": "sha256:" + "a" * 64,
            "envelope_root": "sha256:" + "b" * 64,
            "entries": [
                {
                    "fixture": "fixtures/x86_64/positive/X86-P1.fmp.json",
                    "payload_sha256": "sha256:" + "c" * 64,
                    "payload": {"bytes_hex": "90", "level": 0, "size": 1},
                    "envelope": {
                        "sha256": "sha256:" + "d" * 64,
                        "materializer_version": "0.0.0",
                    },
                }
            ],
        },
        "probes": [],
    }


def run_compare(recorded, fresh):
    """`compare()`'s exit code plus everything it printed."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = baseline.compare(recorded, fresh)
    return code, buffer.getvalue()


class ComparatorTests(unittest.TestCase):
    def test_identical_snapshots_pass(self):
        recorded = synthetic_snapshot()
        code, output = run_compare(recorded, copy.deepcopy(recorded))
        self.assertEqual(code, 0)
        self.assertIn("OK: payload projection identical", output)
        self.assertIn("envelope: identical", output)

    def test_payload_digest_change_fails(self):
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["artifacts"]["entries"][0]["payload_sha256"] = "sha256:" + "0" * 64
        code, output = run_compare(recorded, fresh)
        self.assertEqual(code, 1)
        self.assertIn("payload_sha256", output)

    def test_payload_bytes_change_fails(self):
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["artifacts"]["entries"][0]["payload"]["bytes_hex"] = "cc"
        code, output = run_compare(recorded, fresh)
        self.assertEqual(code, 1)
        self.assertIn("payload/bytes_hex", output)

    def test_implementation_change_is_not_a_payload_change(self):
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["implementation"] = {
            "name": "fmp-materialize",
            "version": "9.9.9",
            "binary_sha256": "sha256:" + "2" * 64,
        }
        code, output = run_compare(recorded, fresh)
        self.assertEqual(code, 0)
        self.assertIn("envelope: not compared", output)
        self.assertIn("binary 222222222222", output)

    def test_payload_is_compared_even_when_the_receipt_differs(self):
        """The bug the first draft of the split had: a filter that skipped too much."""
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["implementation"] = {
            "name": "fmp-materialize",
            "version": "9.9.9",
            "binary_sha256": "sha256:" + "2" * 64,
        }
        fresh["artifacts"]["entries"][0]["payload"]["bytes_hex"] = "cc"
        code, output = run_compare(recorded, fresh)
        self.assertEqual(code, 1)
        self.assertIn("payload/bytes_hex", output)

    def test_envelope_change_fails_when_the_receipt_matches(self):
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["artifacts"]["entries"][0]["envelope"]["sha256"] = "sha256:" + "e" * 64
        code, output = run_compare(recorded, fresh)
        self.assertEqual(code, 1)
        self.assertIn("envelope/sha256", output)

    def test_a_removed_entry_fails(self):
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["artifacts"]["entries"] = []
        code, output = run_compare(recorded, fresh)
        self.assertEqual(code, 1)
        self.assertIn("length 1 -> 0", output)

    def test_a_count_change_fails(self):
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["corpus"]["negatives"] = 2
        code, output = run_compare(recorded, fresh)
        self.assertEqual(code, 1)
        self.assertIn("corpus/negatives", output)

    def test_receipts_and_observations_are_not_compared(self):
        recorded = synthetic_snapshot()
        fresh = copy.deepcopy(recorded)
        fresh["provenance"]["projection_recording_commit"] = "2" * 40
        fresh["toolchain"]["rust"] = "cargo other"
        fresh["probes"] = [{"probe": "deep-json", "outcome": "timeout"}]
        code, _ = run_compare(recorded, fresh)
        self.assertEqual(code, 0)


class SchemaTests(unittest.TestCase):
    def test_an_old_schema_is_refused(self):
        recorded = synthetic_snapshot()
        recorded["schema"] = "monasm.he1.baseline/0.1"
        with self.assertRaises(baseline.Fault) as caught:
            baseline.require_schema(recorded)
        self.assertIn("0.1", str(caught.exception))
        self.assertIn("re-record", str(caught.exception))

    def test_the_current_schema_is_accepted(self):
        baseline.require_schema(synthetic_snapshot())


class CommandLineTests(unittest.TestCase):
    """Exit 2 is a fault, exit 1 is a diff, and the two never trade places."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="monasm-he1-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, name, value):
        path = self.root / name
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return str(path)

    def main(self, *arguments):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = baseline.main(list(arguments))
        return code, stderr.getvalue()

    def test_a_missing_snapshot_is_a_fault(self):
        code, stderr = self.main("--check", str(self.root / "absent.json"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read the recorded snapshot", stderr)

    def test_a_corrupt_snapshot_is_a_fault(self):
        path = self.write("corrupt.json", "{not json")
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("not valid JSON", stderr)

    def test_an_old_schema_is_a_fault_before_any_binary_runs(self):
        # No --binary is passed, and the check must fail before discovery: a
        # schema refusal is a usage fact, not something to learn after 128 runs.
        path = self.write("old.json", dict(synthetic_snapshot(), schema="monasm.he1.baseline/0.1"))
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("0.1", stderr)

    def test_a_missing_binary_is_a_fault(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        code, stderr = self.main("--check", path, "--binary", str(self.root / "absent-binary"))
        self.assertEqual(code, 2)
        self.assertIn("no materializer binary", stderr)
        self.assertIn("--manifest-path prototype/Cargo.toml", stderr)

    # A snapshot can be valid JSON and still not be a snapshot. Each of these
    # used to raise inside the comparator and exit 1 -- the code that means
    # "the baseline moved".

    def test_a_json_array_is_a_fault(self):
        path = self.write("array.json", [])
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("is list, not a JSON object", stderr)

    def test_json_null_is_a_fault(self):
        path = self.write("null.json", "null")
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("is null, not a JSON object", stderr)

    def test_a_missing_artifacts_is_a_fault(self):
        snapshot = synthetic_snapshot()
        del snapshot["artifacts"]
        path = self.write("no-artifacts.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("'artifacts' is null, not an object", stderr)

    def test_a_wrong_implementation_type_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["implementation"] = "fmp-materialize/0.0.0"
        path = self.write("bad-receipt.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("implementation is str, not an object", stderr)

    def test_an_entry_without_a_payload_digest_is_a_fault(self):
        snapshot = synthetic_snapshot()
        del snapshot["artifacts"]["entries"][0]["payload_sha256"]
        path = self.write("no-digest.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("has no string 'payload_sha256'", stderr)


class DiscoveryTests(unittest.TestCase):
    def test_the_linux_name_is_found_when_no_exe_exists(self):
        with tempfile.TemporaryDirectory(prefix="monasm-he1-bin-") as directory:
            binary = Path(directory) / "fmp"
            binary.write_bytes(b"")
            with mock.patch.object(baseline, "DEBUG_BUILD", Path(directory)):
                self.assertEqual(baseline.resolve_binary(""), binary)

    def test_the_executable_name_wins_on_windows(self):
        with tempfile.TemporaryDirectory(prefix="monasm-he1-bin-") as directory:
            preferred = Path(directory) / "fmp.exe"
            preferred.write_bytes(b"")
            (Path(directory) / "fmp").write_bytes(b"")
            with mock.patch.object(baseline, "DEBUG_BUILD", Path(directory)):
                self.assertEqual(baseline.resolve_binary(""), preferred)


class TimeoutTests(unittest.TestCase):
    def test_a_finished_command_is_returned(self):
        completed = baseline.run_limited([sys.executable, "-c", "print(1)"], 60)
        self.assertIsNotNone(completed)
        self.assertEqual(completed.stdout.strip(), b"1")

    def test_a_hang_returns_none_instead_of_raising(self):
        started = baseline.run_limited(
            [sys.executable, "-c", "import time; time.sleep(30)"], 0.3
        )
        self.assertIsNone(started)


if __name__ == "__main__":
    unittest.main(verbosity=2)
