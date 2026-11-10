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
    """The smallest snapshot the comparator accepts.

    Every derived field is computed from its input, so the fixture is a valid
    snapshot rather than a shape that only happens to pass one check. A test that
    wants a broken digest edits one field and leaves the dependency alone.
    """
    payload = {
        "bytes_hex": "90",
        "fingerprint": "sha256:" + "f" * 64,
        "fixups": [],
        "format_version": "fmp/0.1",
        "level": 0,
        "size": 1,
    }
    materializer_version = "0.0.0"
    document_path = "definitions/x86_64/0.1.0.json"
    entries = [
        {
            "fixture": "fixtures/x86_64/positive/X86-P1.fmp.json",
            "plan_sha256": "sha256:" + "c" * 64,
            "definition": {
                "namespace": "x86",
                "version": "0.1.0",
                "digest": "sha256:" + "e" * 64,
            },
            "level": 0,
            "size": 1,
            "sections": 0,
            "symbols": 0,
            "fixup_records": 0,
            "fingerprint": "sha256:" + "f" * 64,
            "payload_sha256": baseline.canonical_digest(payload),
            "payload": payload,
            "envelope": {
                "sha256": baseline.canonical_digest(
                    dict(payload, materializer_version=materializer_version)
                ),
                "materializer_version": materializer_version,
            },
        }
    ]
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
        "definitions": {
            "count": 1,
            "newest": {"x86_64": document_path},
            "documents": [
                {
                    "path": document_path,
                    "file_sha256": "sha256:" + "b" * 64,
                    "namespace": "x86",
                    "version": "0.1.0",
                    "definition_format": "fmp-def/0.1",
                    "isa_family": "x86_64",
                    "forms": 1,
                    "digest": "sha256:" + "e" * 64,
                }
            ],
        },
        "corpus": {
            "positives": 1,
            "negatives": 1,
            "by_isa": {"x86_64": {"positive": 1, "negative": 1}},
            "negative_phase_split": {},
        },
        "oracle": {
            "kinds": {"assembler": 1},
            "manual_derivation": [],
        },
        "artifacts": {
            "count": 1,
            "payload_root": baseline.root_of(
                entries, lambda entry: entry["payload_sha256"]
            ),
            "envelope_root": baseline.root_of(
                entries, lambda entry: entry["envelope"]["sha256"]
            ),
            "entries": entries,
        },
        "probes": [],
    }


def synthetic_anchor(root=None, definitions=None):
    snapshot = synthetic_snapshot()
    if root is None:
        root = snapshot["artifacts"]["payload_root"]
    if definitions is None:
        definitions = baseline.definitions_root(snapshot["definitions"]["documents"])
    return {
        "schema": baseline.ANCHOR_SCHEMA,
        "payload_root": root,
        "definitions_root": definitions,
        "set_by": "test",
        "note": "test anchor",
    }


def synthetic_artifact():
    return {
        "format_version": "fmp/0.1",
        "level": 0,
        "bytes_hex": "90",
        "size": 1,
        "fixups": [],
        "fingerprint": "sha256:" + "f" * 64,
        "materializer_version": "0.0.0",
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

    def anchor(self, root=None):
        return self.write("anchor.json", synthetic_anchor(root))

    def main(self, *arguments):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = baseline.main(list(arguments))
        self.last_stdout = stdout.getvalue()
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

    def test_a_deeply_nested_snapshot_is_a_fault(self):
        # `json.loads` raises `RecursionError`, which is not a `ValueError`; it
        # used to escape as a traceback and exit 1 -- the code that means "the
        # baseline moved". A reader limit is a fault, not a difference.
        path = self.write("deep.json", "[" * 20000 + "]" * 20000)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("nested too deeply", stderr)
        self.assertIn("not a difference", stderr)

    def test_a_deeply_nested_anchor_is_a_fault(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        anchor = self.write("deep-anchor.json", "[" * 20000 + "]" * 20000)
        code, stderr = self.main("--check", path, "--anchor", anchor)
        self.assertEqual(code, 2)
        self.assertIn("nested too deeply", stderr)

    def test_an_old_schema_is_a_fault_before_any_binary_runs(self):
        # No --binary is passed, and the check must fail before discovery: a
        # schema refusal is a usage fact, not something to learn after 128 runs.
        path = self.write("old.json", dict(synthetic_snapshot(), schema="monasm.he1.baseline/0.1"))
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("0.1", stderr)

    def test_a_missing_binary_is_a_fault(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        code, stderr = self.main(
            "--check",
            path,
            "--anchor",
            self.anchor(),
            "--binary",
            str(self.root / "absent-binary"),
        )
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

    def test_a_missing_envelope_is_a_fault_even_when_it_would_be_skipped(self):
        # CI's receipt differs from the recorder's, so `--check` would skip the
        # envelope. Deleting it must still be a structural fault: otherwise the
        # evidence the file claims to hold can disappear while the gate is green.
        snapshot = synthetic_snapshot()
        del snapshot["artifacts"]["entries"][0]["envelope"]
        path = self.write("no-envelope.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("has no envelope object", stderr)

    def test_a_missing_projection_is_a_fault(self):
        snapshot = synthetic_snapshot()
        del snapshot["projections"]["payload"]
        path = self.write("no-projection.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("projections.payload", stderr)

    def test_a_wrong_typed_payload_root_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["artifacts"]["payload_root"] = 42
        path = self.write("bad-root.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("payload_root is not a sha256 digest", stderr)

    def test_a_payload_root_not_matching_entries_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["artifacts"]["payload_root"] = "sha256:" + "0" * 64
        path = self.write("stale-root.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("payload_root does not match its entries", stderr)

    def test_a_payload_edited_without_its_digest_is_a_fault(self):
        # The content no longer hashes to the recorded digest. This is corrupt
        # evidence (2), not a fresh-payload diff (1).
        snapshot = synthetic_snapshot()
        snapshot["artifacts"]["entries"][0]["payload"]["bytes_hex"] = "cc"
        path = self.write("stale-payload.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("payload_sha256 does not match its payload", stderr)

    def test_an_envelope_digest_not_matching_its_payload_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["artifacts"]["entries"][0]["envelope"]["sha256"] = (
            "sha256:" + "0" * 64
        )
        path = self.write("stale-envelope.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("envelope.sha256 does not match payload", stderr)

    def test_a_definition_count_not_matching_the_document_array_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["definitions"]["count"] = 2
        path = self.write("bad-definitions-count.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("definitions.count 2 but holds 1 documents", stderr)

    def test_a_newest_path_outside_the_document_array_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["definitions"]["newest"]["x86_64"] = "definitions/x86_64/9.9.9.json"
        path = self.write("bad-newest.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("which is not in definitions.documents", stderr)

    def test_a_corpus_sum_not_matching_by_isa_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["corpus"]["positives"] = 2
        path = self.write("bad-corpus-sum.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("corpus.positives 2 but by_isa sums to 1", stderr)

    def test_an_oracle_sum_not_matching_positives_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["oracle"]["kinds"]["assembler"] = 2
        path = self.write("bad-oracle-sum.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("oracle.kinds sum to 2 but corpus.positives is 1", stderr)

    def test_a_manual_derivation_not_matching_its_oracle_kind_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["oracle"]["manual_derivation"] = ["fixtures/x86_64/positive/X.fmp.json"]
        path = self.write("bad-manual.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("lists 1 manual derivations but counts 0", stderr)

    def test_a_payload_digest_that_is_not_sha256_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["artifacts"]["entries"][0]["plan_sha256"] = "md5:abc"
        path = self.write("bad-plan-digest.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("plan_sha256 is not a sha256 digest", stderr)

    def test_a_level_zero_payload_without_bytes_hex_is_a_fault(self):
        snapshot = synthetic_snapshot()
        del snapshot["artifacts"]["entries"][0]["payload"]["bytes_hex"]
        path = self.write("no-bytes.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("level-0 payload has no string 'bytes_hex'", stderr)

    def test_a_definition_with_a_non_digest_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["artifacts"]["entries"][0]["definition"]["digest"] = "sha256:xyz"
        path = self.write("bad-definition.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("definition digest is not a sha256 digest", stderr)

    def test_a_count_mismatch_is_a_fault(self):
        snapshot = synthetic_snapshot()
        snapshot["artifacts"]["count"] = 2
        path = self.write("bad-count.json", snapshot)
        code, stderr = self.main("--check", path)
        self.assertEqual(code, 2)
        self.assertIn("says artifacts.count 2 but holds 1 entries", stderr)

    def test_recording_requires_an_explicit_flag(self):
        code, stderr = self.main()
        self.assertEqual(code, 2)
        self.assertIn("--check SNAPSHOT", stderr)
        self.assertIn("--record", stderr)

    def test_check_and_record_are_exclusive(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        code, stderr = self.main("--check", path, "--record")
        self.assertEqual(code, 2)
        self.assertIn("different operations", stderr)

    def test_a_missing_anchor_is_a_fault(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        code, stderr = self.main(
            "--check", path, "--anchor", str(self.root / "absent-anchor.json")
        )
        self.assertEqual(code, 2)
        self.assertIn("cannot read the baseline anchor", stderr)

    def test_an_anchor_mismatch_is_a_diff(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        anchor = self.write("other-anchor.json", synthetic_anchor("sha256:" + "0" * 64))
        code, stderr = self.main("--check", path, "--anchor", anchor)
        self.assertEqual(code, 1)
        self.assertIn("no longer matches the frozen anchor", self.last_stdout)

    def test_a_wrong_typed_anchor_is_a_fault(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        anchor = self.write("bad-anchor.json", {"schema": baseline.ANCHOR_SCHEMA})
        code, stderr = self.main("--check", path, "--anchor", anchor)
        self.assertEqual(code, 2)
        self.assertIn("has no sha256 payload_root", stderr)

    def test_the_anchor_accepts_the_synthetic_root(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        anchor = self.anchor()
        code, stderr = self.main(
            "--check",
            path,
            "--anchor",
            anchor,
            "--binary",
            str(self.root / "absent-binary"),
        )
        # The anchor matched; the run stops at binary discovery, not at the anchor.
        self.assertEqual(code, 2)
        self.assertIn("no materializer binary", stderr)

    def test_a_definitions_root_mismatch_is_a_diff(self):
        path = self.write("snapshot.json", synthetic_snapshot())
        anchor = self.write(
            "other-definitions-anchor.json",
            synthetic_anchor(definitions="sha256:" + "0" * 64),
        )
        code, stderr = self.main("--check", path, "--anchor", anchor)
        self.assertEqual(code, 1)
        self.assertIn("anchor/definitions_root", self.last_stdout)

    def test_an_anchor_without_definitions_root_is_a_fault(self):
        # A 0.1-shaped anchor has the right schema string only by accident; the
        # tool must not accept a payload-only anchor as if definitions were pinned.
        path = self.write("snapshot.json", synthetic_snapshot())
        anchor = {
            "schema": baseline.ANCHOR_SCHEMA,
            "payload_root": synthetic_snapshot()["artifacts"]["payload_root"],
        }
        anchor_path = self.write("payload-only-anchor.json", anchor)
        code, stderr = self.main("--check", path, "--anchor", anchor_path)
        self.assertEqual(code, 2)
        self.assertIn("has no sha256 definitions_root", stderr)


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


class ToolchainTests(unittest.TestCase):
    """A missing toolchain fact is recorded, never raised as a traceback."""

    def test_a_successful_subprocess_is_recorded(self):
        value = baseline.toolchain_version(
            [sys.executable, "-c", "print('tool 1.0')"]
        )
        self.assertEqual(value, "tool 1.0")

    def test_a_failing_subprocess_is_unavailable(self):
        value = baseline.toolchain_version(
            [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('no toolchain'); sys.exit(3)",
            ]
        )
        self.assertTrue(value.startswith("unavailable:"))
        self.assertIn("exit 3", value)
        self.assertIn("no toolchain", value)

    def test_empty_stdout_is_unavailable(self):
        value = baseline.toolchain_version([sys.executable, "-c", "pass"])
        self.assertEqual(value, "unavailable: empty stdout")


class InventoryTests(unittest.TestCase):
    """Definition and oracle records must be objects before `.get()` is legal."""

    def test_a_non_object_definition_is_a_fault(self):
        with tempfile.TemporaryDirectory(prefix="monasm-he1-def-") as directory:
            root = Path(directory)
            path = root / "x86_64" / "0.1.0.json"
            path.parent.mkdir(parents=True)
            path.write_text("[]", encoding="utf-8")
            with mock.patch.object(baseline, "DEFINITIONS", root):
                with self.assertRaises(baseline.Fault) as caught:
                    baseline.definition_inventory()
        self.assertIn("not a JSON object", str(caught.exception))

    def test_a_non_object_oracle_record_is_a_fault(self):
        with tempfile.TemporaryDirectory(prefix="monasm-he1-oracle-") as directory:
            root = Path(directory)
            plan = root / "X86-P1.fmp.json"
            plan.write_text("{}", encoding="utf-8")
            oracle = root / "X86-P1.oracle.json"
            oracle.write_text("[]", encoding="utf-8")
            with self.assertRaises(baseline.Fault) as caught:
                baseline.oracle_state([plan])
        self.assertIn("not a JSON object", str(caught.exception))


class DefinitionsRootTests(unittest.TestCase):
    """The anchor's definition root must change with the bytes and the content."""

    def setUp(self):
        self.documents = synthetic_snapshot()["definitions"]["documents"]

    def test_the_root_is_order_independent(self):
        reversed_documents = list(reversed(self.documents))
        self.assertEqual(
            baseline.definitions_root(self.documents),
            baseline.definitions_root(reversed_documents),
        )

    def test_a_changed_file_digest_changes_the_root(self):
        documents = copy.deepcopy(self.documents)
        documents[0]["file_sha256"] = "sha256:" + "0" * 64
        self.assertNotEqual(
            baseline.definitions_root(self.documents),
            baseline.definitions_root(documents),
        )

    def test_a_changed_canonical_digest_changes_the_root(self):
        documents = copy.deepcopy(self.documents)
        documents[0]["digest"] = "sha256:" + "0" * 64
        self.assertNotEqual(
            baseline.definitions_root(self.documents),
            baseline.definitions_root(documents),
        )

    def test_a_changed_path_changes_the_root(self):
        documents = copy.deepcopy(self.documents)
        documents[0]["path"] = "definitions/x86_64/9.9.9.json"
        self.assertNotEqual(
            baseline.definitions_root(self.documents),
            baseline.definitions_root(documents),
        )


class FreshArtifactTests(unittest.TestCase):
    """The fresh CLI artifact is validated too, not only the recorded snapshot."""

    def test_a_valid_level_zero_artifact_is_accepted(self):
        baseline.validate_fresh_artifact(synthetic_artifact(), "fixture")

    def test_a_missing_materializer_version_is_a_fault(self):
        artifact = synthetic_artifact()
        del artifact["materializer_version"]
        with self.assertRaises(baseline.Fault) as caught:
            baseline.validate_fresh_artifact(artifact, "fixture")
        self.assertIn("materializer_version", str(caught.exception))

    def test_a_non_string_materializer_version_is_a_fault(self):
        artifact = synthetic_artifact()
        artifact["materializer_version"] = 1
        with self.assertRaises(baseline.Fault) as caught:
            baseline.validate_fresh_artifact(artifact, "fixture")
        self.assertIn("materializer_version", str(caught.exception))

    def test_a_wrong_typed_level_is_a_fault(self):
        artifact = synthetic_artifact()
        artifact["level"] = "0"
        with self.assertRaises(baseline.Fault) as caught:
            baseline.validate_fresh_artifact(artifact, "fixture")
        self.assertIn("integer 'level'", str(caught.exception))

    def test_a_level_one_artifact_needs_sections_and_symbols(self):
        artifact = {
            "format_version": "fmp/0.1",
            "level": 1,
            "sections": [],
            "fixups": [],
            "fingerprint": "sha256:" + "f" * 64,
            "materializer_version": "0.0.0",
        }
        with self.assertRaises(baseline.Fault) as caught:
            baseline.validate_fresh_artifact(artifact, "fixture")
        self.assertIn("'symbols'", str(caught.exception))


class ArtifactEntryTests(unittest.TestCase):
    """`artifact_entry()` must run the fresh-artifact check before projecting."""

    def run_entry(self, artifact=None, plan_text="{}", stdout=None):
        output = json.dumps(artifact) if stdout is None else stdout
        with tempfile.TemporaryDirectory(prefix="monasm-he1-entry-") as directory:
            plan = Path(directory) / "X86-P1.fmp.json"
            plan.write_text(plan_text, encoding="utf-8")
            with mock.patch.object(
                baseline,
                "run_materialize",
                return_value=(0, output, ""),
            ):
                with mock.patch.object(baseline, "rel", lambda path: "fixture"):
                    return baseline.artifact_entry(
                        Path("unused"), plan, Path("unused")
                    )

    def test_a_fresh_artifact_missing_materializer_version_is_a_fault(self):
        artifact = synthetic_artifact()
        del artifact["materializer_version"]
        with self.assertRaises(baseline.Fault) as caught:
            self.run_entry(artifact)
        self.assertIn("materializer_version", str(caught.exception))

    def test_a_valid_fresh_artifact_produces_an_entry(self):
        entry = self.run_entry(synthetic_artifact())
        self.assertEqual(entry["envelope"]["materializer_version"], "0.0.0")
        self.assertEqual(entry["payload"]["bytes_hex"], "90")
        self.assertNotIn("materializer_version", entry["payload"])

    def test_a_deeply_nested_plan_is_a_fault_not_a_crash(self):
        # The plan is read here, not only inside `load_snapshot`; a reader
        # depth limit on this path is still a fault (exit 2), not a traceback.
        with self.assertRaises(baseline.Fault) as caught:
            self.run_entry(synthetic_artifact(), plan_text="[" * 20000 + "]" * 20000)
        self.assertIn("nested too deeply", str(caught.exception))

    def test_a_deeply_nested_fresh_artifact_is_a_fault_not_a_crash(self):
        # Same for the materializer's own stdout: it is parsed here, after the
        # subprocess, and must not escape as `RecursionError`.
        with self.assertRaises(baseline.Fault) as caught:
            self.run_entry(stdout="[" * 20000 + "]" * 20000)
        self.assertIn("nested too deeply", str(caught.exception))
        self.assertIn("materializer stdout", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
