#!/usr/bin/env python3
"""H0 compatibility baseline for the HE-1 refactor.

This is a development tool, not a product gate: it records what the current
materializer actually emits, so every later HE-1 phase can prove that the old
payloads did not move. It never writes to `definitions/`, `fixtures/` or the
`prototype/` tree; its only output is the JSON file named by `--out`.

What the snapshot contains:

1. Definition inventory: file SHA-256 plus the canonical digest the plans name.
2. Positive artifacts: for every `fixtures/*/positive/*.fmp.json`, the artifact
   the `fmp` binary prints, normalized and hashed. The bytes, sections, symbols
   and fixup records are kept verbatim, not just summarized.
3. A single `artifact_root` digest over `(fixture path, artifact sha256)` so one
   comparison answers "did any payload change?".
4. Corpus and oracle counts, computed from the tree rather than copied from a
   document.
5. Robustness probes that must not crash the process. A probe records the
   observed behaviour; it does not claim the behaviour is correct.

Usage:

    python tools/he1_baseline.py
    python tools/he1_baseline.py --out research/he1/compatibility-results.json
    python tools/he1_baseline.py --check research/he1/compatibility-results.json

`--check` compares a fresh snapshot against a recorded one and exits 1 on any
difference in a payload, a digest or a count. `head` and `toolchain` are receipts
and are not compared: later phases run at a different commit and a different
binary by design. Probes are also not compared — a changed probe is a finding to
report, not a compatibility break. `--no-probes` skips the subprocess probes
(useful when no binary is built).

Exit codes: 0 recorded or identical, 1 mismatch, 2 usage or I/O fault.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS = ROOT / "definitions"
FIXTURES = ROOT / "fixtures"
DEFAULT_BINARY = ROOT / "prototype/target/debug/fmp.exe"
DEFAULT_OUT = ROOT / "research/he1/compatibility-results.json"

SCHEMA = "monasm.he1.baseline/0.1"

# The deep-input probe. Big enough to overflow a recursive descent parser that
# has no depth limit, small enough to stay far from the process memory limit.
DEEP_DEPTH = 20000


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def canonical_bytes(document) -> bytes:
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")


def canonical_digest(document) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(document)).hexdigest()


def version_key(path: Path):
    return [int(part) for part in path.stem.split(".")]


def definition_inventory():
    documents = []
    for path in sorted(DEFINITIONS.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        forms = document.get("forms", [])
        identity = document.get("target_identity", {})
        documents.append(
            {
                "path": rel(path),
                "file_sha256": sha256_file(path),
                "namespace": document.get("namespace"),
                "version": document.get("version"),
                "definition_format": document.get("definition_format"),
                "isa_family": identity.get("isa_family"),
                "forms": len(forms),
                "digest": canonical_digest(document),
            }
        )
    newest = {}
    for path in sorted(DEFINITIONS.rglob("*.json")):
        isa = path.parent.name
        if isa not in newest or version_key(path) > version_key(newest[isa]):
            newest[isa] = path
    return documents, {isa: rel(path) for isa, path in newest.items()}


def corpus_counts():
    positives = sorted(FIXTURES.glob("*/positive/*.fmp.json"))
    negatives = sorted(FIXTURES.glob("*/negative/*.fmp.json"))
    by_isa = {}
    for path in positives + negatives:
        isa = path.parts[-3]
        bucket = by_isa.setdefault(isa, {"positive": 0, "negative": 0})
        bucket["positive" if path.parent.name == "positive" else "negative"] += 1
    return positives, negatives, by_isa


def oracle_state(positives):
    manual = []
    kinds = {}
    for plan_path in positives:
        oracle_path = plan_path.with_name(plan_path.name.replace(".fmp.json", ".oracle.json"))
        if not oracle_path.is_file():
            raise SystemExit("missing oracle record: %s" % rel(oracle_path))
        record = json.loads(oracle_path.read_text(encoding="utf-8"))
        kind = record.get("kind", "unknown")
        kinds[kind] = kinds.get(kind, 0) + 1
        # `tools/oracle/rerun.py` maps this kind to the `manual-derivation` skip.
        if kind == "manual+disassembly":
            manual.append(rel(plan_path))
    return {"kinds": kinds, "manual_derivation": manual}


def run_materialize(binary: Path, plan_path: Path, definitions: Path):
    completed = subprocess.run(
        [str(binary), "materialize", str(plan_path), "--definitions", str(definitions)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = completed.stdout.decode("utf-8", "replace")
    stderr = completed.stderr.decode("utf-8", "replace")
    return completed.returncode, stdout, stderr


def artifact_entry(binary: Path, plan_path: Path, definitions: Path):
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes.decode("utf-8"))
    returncode, stdout, stderr = run_materialize(binary, plan_path, definitions)
    if returncode != 0:
        raise SystemExit(
            "%s: the baseline expects a positive to materialize, got exit %d: %s"
            % (rel(plan_path), returncode, stderr.strip()[:400])
        )
    artifact = json.loads(stdout)
    fixups = artifact.get("fixups", [])
    entry = {
        "fixture": rel(plan_path),
        "plan_sha256": sha256_file(plan_path),
        "definition": plan.get("definition_identity", {}),
        "level": artifact.get("level"),
        "artifact_sha256": canonical_digest(artifact),
        "fingerprint": artifact.get("fingerprint"),
        "materializer_version": artifact.get("materializer_version"),
        "size": artifact.get("size"),
        "sections": len(artifact.get("sections", [])),
        "symbols": len(artifact.get("symbols", []) or []),
        "fixup_records": len(fixups),
        "artifact": artifact,
    }
    return entry


def artifact_root(entries):
    material = "\n".join(
        "%s\0%s" % (entry["fixture"], entry["artifact_sha256"]) for entry in entries
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def probe_deep_json(binary: Path, definitions: Path, scratch: Path):
    body = "[" * DEEP_DEPTH + "]" * DEEP_DEPTH
    plan = scratch / "deep.fmp.json"
    plan.write_text(body, encoding="utf-8")
    completed = subprocess.run(
        [str(binary), "materialize", str(plan), "--definitions", str(definitions)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stderr = completed.stderr.decode("utf-8", "replace")
    if completed.returncode == 0:
        outcome = "accepted"
    elif completed.returncode == 1:
        outcome = "rejected"
    else:
        outcome = "abnormal-exit"
    return {
        "probe": "deep-json",
        "input": "%d nested arrays" % DEEP_DEPTH,
        "returncode": completed.returncode,
        "outcome": outcome,
        "stderr_head": stderr.strip()[:200],
        "note": (
            "A rejection is the desired shape; an abnormal exit or a stack "
            "overflow is a measured gap for H4, not a pass."
        ),
    }


def probe_oversized_field(binary: Path, definitions: Path, scratch: Path):
    # A valid plan with one 1 MiB unknown field: the closed-object rule must
    # reject it without reading the value into a decision.
    source = sorted(FIXTURES.glob("*/positive/*.fmp.json"))[0]
    plan = json.loads(source.read_text(encoding="utf-8"))
    plan["x_he1_probe"] = "a" * (1 << 20)
    path = scratch / "oversized.fmp.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    completed = subprocess.run(
        [str(binary), "materialize", str(path), "--definitions", str(definitions)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "probe": "unknown-field-1mib",
        "input": "a valid positive with one 1 MiB unknown member",
        "returncode": completed.returncode,
        "outcome": "rejected" if completed.returncode == 1 else "unexpected",
        "stderr_head": completed.stderr.decode("utf-8", "replace").strip()[:200],
    }


def toolchain(binary: Path):
    def version(command):
        try:
            completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as error:
            return "unavailable: %s" % error
        return completed.stdout.decode("utf-8", "replace").strip().splitlines()[0]

    return {
        "rust": version(["cargo", "+1.96.0", "--version"]),
        "python": "Python %s" % sys.version.split()[0],
        "binary": {"path": rel(binary), "sha256": sha256_file(binary)},
    }


def snapshot(binary: Path, probes: bool):
    documents, newest = definition_inventory()
    positives, negatives, by_isa = corpus_counts()
    entries = [artifact_entry(binary, path, DEFINITIONS) for path in positives]
    result = {
        "schema": SCHEMA,
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), stdout=subprocess.PIPE
        )
        .stdout.decode()
        .strip(),
        "toolchain": toolchain(binary),
        "definitions": {
            "count": len(documents),
            "newest": newest,
            "documents": documents,
        },
        "corpus": {
            "positives": len(positives),
            "negatives": len(negatives),
            "by_isa": by_isa,
            "negative_phase_split": {
                "materialize": 611,
                "read": 8,
                "source": "prototype/crates/fmp-cli/tests/planner_api.rs asserts the split",
                "note": "the split is asserted by the Rust gate, not recomputed here",
            },
        },
        "oracle": oracle_state(positives),
        "artifacts": {
            "count": len(entries),
            "artifact_root": artifact_root(entries),
            "entries": entries,
        },
        "probes": [],
    }
    if probes:
        with tempfile.TemporaryDirectory(prefix="monasm-he1-") as scratch_name:
            scratch = Path(scratch_name)
            result["probes"].append(probe_deep_json(binary, DEFINITIONS, scratch))
            result["probes"].append(probe_oversized_field(binary, DEFINITIONS, scratch))
    return result


def differences(recorded, fresh):
    diffs = []

    def walk(path, left, right):
        if type(left) is not type(right):
            diffs.append("%s: type changed" % path)
            return
        if isinstance(left, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left:
                    diffs.append("%s/%s: added" % (path, key))
                elif key not in right:
                    diffs.append("%s/%s: removed" % (path, key))
                else:
                    walk("%s/%s" % (path, key), left[key], right[key])
            return
        if isinstance(left, list):
            if len(left) != len(right):
                diffs.append("%s: length %d -> %d" % (path, len(left), len(right)))
                return
            for index, (a, b) in enumerate(zip(left, right)):
                walk("%s[%d]" % (path, index), a, b)
            return
        if left != right:
            diffs.append("%s: %r -> %r" % (path, left, right))

    # Probes are observations, not invariants: a changed probe result is a
    # finding to report, not a compatibility failure.
    #
    # `head` and `toolchain` are receipts for when the snapshot was taken. Every
    # phase after H0 runs at a different commit and a different binary, so
    # comparing them would fail for the right reason at the wrong time. The
    # compatibility claim is over definitions, corpus counts, oracle state and
    # the artifacts themselves.
    ignore = {"probes", "toolchain", "head"}
    for key in sorted(set(recorded) | set(fresh)):
        if key in ignore:
            continue
        walk(key, recorded.get(key), fresh.get(key))
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description="Record or check the HE-1 baseline")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--binary", default=str(DEFAULT_BINARY))
    parser.add_argument("--check", metavar="RECORDED", help="compare against a snapshot")
    parser.add_argument("--no-probes", action="store_true")
    arguments = parser.parse_args()

    binary = Path(arguments.binary)
    if not binary.is_file():
        print("error: no materializer binary at %s" % binary)
        print("build it first: cargo +1.96.0 build --bin fmp -p fmp-cli")
        return 2

    fresh = snapshot(binary, not arguments.no_probes)

    if arguments.check:
        recorded = json.loads(Path(arguments.check).read_text(encoding="utf-8"))
        diffs = differences(recorded, fresh)
        for diff in diffs:
            print("DIFF %s" % diff)
        if diffs:
            print("FAIL: %d difference(s) against %s" % (len(diffs), arguments.check))
            return 1
        print("OK: identical to %s" % arguments.check)
        print("artifact_root: %s" % fresh["artifacts"]["artifact_root"])
        return 0

    out = Path(arguments.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # `newline="\n"` keeps the snapshot LF on every host; the repository is
    # `text=auto eol=lf`, so a CRLF working copy would be a spurious diff.
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(fresh, indent=2, ensure_ascii=False) + "\n")
    print(
        "recorded %d definitions, %d positives, %d negatives, %d artifacts"
        % (
            fresh["definitions"]["count"],
            fresh["corpus"]["positives"],
            fresh["corpus"]["negatives"],
            fresh["artifacts"]["count"],
        )
    )
    print("artifact_root: %s" % fresh["artifacts"]["artifact_root"])
    for probe in fresh["probes"]:
        print("probe %s: %s (exit %d)" % (probe["probe"], probe["outcome"], probe["returncode"]))
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
