#!/usr/bin/env python3
"""H0 compatibility baseline for the HE-1 refactor.

This records what the current materializer actually emits, so every later HE-1
phase can prove that the old payloads did not move. It is a development tool
*and*, since `ADR-0126`, a hosted gate (`baseline` in `gates.yml`); the product
build never reads it. It never writes to `definitions/`, `fixtures/` or the
`prototype/` tree; its only output is the JSON file named by `--out`.

Identity is split into three layers, because they answer different questions:

1. `payload/0.1` — the artifact with `materializer_version` removed. This is the
   machine payload: bytes or sections, symbols, fixup records, `fingerprint`,
   `level`, `size`, `format_version`. A changed payload means the materializer
   computes something different. `--check` compares this.
2. `envelope/0.1` — the whole artifact object, `materializer_version` included.
   Recorded, and compared only when the implementation receipt is identical, so
   a genuine version bump does not masquerade as a payload change.
3. `implementation` — the build receipt (`name`, `version`, binary SHA-256).
   Recorded, never compared.

The snapshot holds, per positive fixture, the payload object verbatim plus both
digests, and a `payload_root` / `envelope_root` over `(fixture path, digest)` so
one comparison answers "did any payload change?".

Also recorded: the definition inventory (file SHA-256 plus canonical digest),
corpus and oracle counts computed from the tree rather than copied from a
document, and — when `--probes` is passed — robustness observations.

Usage:

    python tools/he1_baseline.py --record [--probes] [--out PATH]
    python tools/he1_baseline.py --check research/he1/compatibility-results.json

`--record` is the only way to write a snapshot; `--out` and `--probes` apply
only to it. `--check` exits 1 on any difference in a payload, a digest or a
count, and refuses a snapshot whose `schema` it does not know rather than
silently comparing fewer fields. `provenance`, `toolchain`, `implementation` and
`probes` are receipts/observations and are not compared; `envelope_root` is
compared only when both sides name the same implementation.

`provenance` holds two commits on purpose: `original_baseline_commit` is the
commit whose artifacts H0 first recorded (read from the frozen snapshot), and
`projection_recording_commit` is HEAD when this projection was written. They
differ because a projection can be recorded before it is committed.

Probes are off by default: one of them feeds a 20 000-deep JSON document to a
reader that currently overflows its stack. Every subprocess has a timeout, and a
timeout in a probe is recorded as an outcome instead of raising.

Exit codes: 0 recorded or identical, 1 mismatch, 2 usage, I/O or structural
fault. A fault never exits 1: a regression and a broken invocation must not look
alike. Recording is explicit (`--record`); a bare invocation refuses to overwrite
the frozen snapshot. `--check` also requires the recorded `payload_root` and
`definitions_root` to equal the separate anchor in
`research/he1/baseline-anchor.json`, so re-recording a snapshot cannot silently
redefine either the artifacts or the definition files.
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
DEBUG_BUILD = ROOT / "prototype" / "target" / "debug"
DEFAULT_OUT = ROOT / "research/he1/compatibility-results.json"

# The frozen anchor is separate from the snapshot on purpose. A snapshot can be
# re-recorded by a later commit; the anchor changes only with a compatibility
# ADR. `--check` compares the recorded root to this file, so a re-recorded
# baseline cannot quietly become the reference.
DEFAULT_ANCHOR = ROOT / "research/he1/baseline-anchor.json"
ANCHOR_SCHEMA = "monasm.he1.baseline-anchor/0.2"

# `payload/0.1` and `envelope/0.1` are the two projections; the schema name is
# what `--check` uses to refuse an older snapshot instead of comparing less.
SCHEMA = "monasm.he1.baseline/0.2"
PAYLOAD_PROJECTION = "payload/0.1"
ENVELOPE_PROJECTION = "envelope/0.1"

# The build receipt. `binary_sha256` is the exact build identifier available
# today; `version` is the crate version and is expected to change.
IMPLEMENTATION = ROOT / "prototype/crates/fmp-materialize/Cargo.toml"

MATERIALIZE_TIMEOUT = 120
PROBE_TIMEOUT = 60

# The deep-input probe. Big enough to overflow a recursive descent parser that
# has no depth limit, small enough to stay far from the process memory limit.
DEEP_DEPTH = 20000

# The frozen H0 snapshot, kept byte-identical when the gate moved to the payload
# projection. It is the only place the original recording commit is written down.
FROZEN_H0_SNAPSHOT = ROOT / "research/he1/compatibility-h0-envelope.json"

BUILD_COMMAND = (
    "cargo +1.96.0 build --bin fmp -p fmp-cli --manifest-path prototype/Cargo.toml"
)


class Fault(Exception):
    """A usage or I/O fault. It exits 2, never 1: a broken run is not a diff."""


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


def load_json_object(path, what):
    """Read a JSON object, or raise `Fault`.

    A JSON array is valid JSON but not a document this tool may call `.get()` on.
    Reading it here keeps a malformed definition/oracle record on the `2` path
    instead of letting `AttributeError` escape as exit 1.
    """
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise Fault("cannot read the %s %s: %s" % (what, path, error))
    except ValueError as error:
        raise Fault("%s is not valid JSON: %s" % (path, error))
    if not isinstance(document, dict):
        raise Fault("%s is %s, not a JSON object" % (path, describe(document)))
    return document


def version_key(path: Path):
    return [int(part) for part in path.stem.split(".")]


def payload_of(artifact):
    """The artifact without the build receipt member.

    A second projection rather than a second artifact: the payload is the
    envelope minus exactly one key, and the tests below pin that.
    """
    if not isinstance(artifact, dict):
        raise Fault("artifact is not a JSON object")
    return {key: value for key, value in artifact.items() if key != "materializer_version"}


def definition_inventory():
    documents = []
    for path in sorted(DEFINITIONS.rglob("*.json")):
        document = load_json_object(path, "definition")
        forms = document.get("forms")
        if not isinstance(forms, list):
            raise Fault("definition %s has no forms array" % path)
        identity = document.get("target_identity")
        if not isinstance(identity, dict):
            raise Fault("definition %s has no target_identity object" % path)
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


def definitions_root(documents):
    """One digest over the definition files, sorted by path.

    The snapshot already lists every definition's raw-file digest and canonical
    digest, but it lives in the file `--record` rewrites. This root is copied
    into the separate anchor, so re-recording a whitespace-only edit to a
    historical definition changes the root and the gate fails. The record is
    `path\\0file_sha256\\0digest`, so both the bytes and the parsed content are
    covered.
    """
    material = "\n".join(
        "%s\0%s\0%s" % (document["path"], document["file_sha256"], document["digest"])
        for document in sorted(documents, key=lambda document: document["path"])
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


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
            raise Fault("missing oracle record: %s" % rel(oracle_path))
        record = load_json_object(oracle_path, "oracle record")
        kind = record.get("kind", "unknown")
        if not isinstance(kind, str):
            raise Fault("oracle record %s has a non-string kind" % rel(oracle_path))
        kinds[kind] = kinds.get(kind, 0) + 1
        # `tools/oracle/rerun.py` maps this kind to the `manual-derivation` skip.
        if kind == "manual+disassembly":
            manual.append(rel(plan_path))
    return {"kinds": kinds, "manual_derivation": manual}


def run_limited(command, timeout):
    """Run a command with a bound; `None` means it did not finish in time.

    Separated from its callers so the timeout branch is testable without a
    materializer binary and without waiting on a real hang.
    """
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None


def run_materialize(binary: Path, plan_path: Path, definitions: Path):
    """Run one materialization with a timeout; a hang is a finding, not a lock."""
    completed = run_limited(
        [str(binary), "materialize", str(plan_path), "--definitions", str(definitions)],
        MATERIALIZE_TIMEOUT,
    )
    if completed is None:
        raise Fault(
            "%s: the materializer did not finish within %d s"
            % (rel(plan_path), MATERIALIZE_TIMEOUT)
        )
    stdout = completed.stdout.decode("utf-8", "replace")
    stderr = completed.stderr.decode("utf-8", "replace")
    return completed.returncode, stdout, stderr


def validate_fresh_artifact(artifact, fixture):
    """The fresh CLI artifact must keep the old envelope's required members.

    `--check` compares payloads, and when the binary digest differs it drops the
    envelope from the comparison. Without this check a new materializer could
    omit `materializer_version` (or change another required member's type) on a
    fixture whose payload did not move, and the gate would still pass. The value
    of `materializer_version` may change; the member may not disappear.
    """
    if not isinstance(artifact, dict):
        raise Fault("%s: the materializer emitted %s, not a JSON object" % (fixture, describe(artifact)))
    for key in ("format_version", "fingerprint", "materializer_version"):
        if not isinstance(artifact.get(key), str):
            raise Fault(
                "%s: the fresh artifact has no string %r (the old CLI contract "
                "requires it even when the payload is unchanged)" % (fixture, key)
            )
    if not is_digest(artifact.get("fingerprint")):
        raise Fault("%s: the fresh artifact fingerprint is not a sha256 digest" % fixture)
    level = artifact.get("level")
    if not isinstance(level, int):
        raise Fault("%s: the fresh artifact has no integer 'level'" % fixture)
    if not isinstance(artifact.get("fixups"), list):
        raise Fault("%s: the fresh artifact has no fixups array" % fixture)
    if level == 0:
        if not isinstance(artifact.get("bytes_hex"), str):
            raise Fault("%s: the fresh level-0 artifact has no string 'bytes_hex'" % fixture)
        if not isinstance(artifact.get("size"), int):
            raise Fault("%s: the fresh level-0 artifact has no integer 'size'" % fixture)
    elif level == 1:
        for key in ("sections", "symbols"):
            if not isinstance(artifact.get(key), list):
                raise Fault("%s: the fresh level-1 artifact has no %r array" % (fixture, key))
    else:
        raise Fault("%s: the fresh artifact level is %r, expected 0 or 1" % (fixture, level))


def artifact_entry(binary: Path, plan_path: Path, definitions: Path):
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes.decode("utf-8"))
    returncode, stdout, stderr = run_materialize(binary, plan_path, definitions)
    if returncode != 0:
        raise Fault(
            "%s: the baseline expects a positive to materialize, got exit %d: %s"
            % (rel(plan_path), returncode, stderr.strip()[:400])
        )
    artifact = json.loads(stdout)
    validate_fresh_artifact(artifact, rel(plan_path))
    payload = payload_of(artifact)
    fixups = payload.get("fixups", [])
    return {
        "fixture": rel(plan_path),
        "plan_sha256": sha256_file(plan_path),
        "definition": plan.get("definition_identity", {}),
        "level": payload.get("level"),
        "size": payload.get("size"),
        "sections": len(payload.get("sections", [])),
        "symbols": len(payload.get("symbols", []) or []),
        "fixup_records": len(fixups),
        "fingerprint": payload.get("fingerprint"),
        "payload_sha256": canonical_digest(payload),
        # One object, so the comparison can drop the whole envelope in one
        # place when the implementation receipt differs. `materializer_version`
        # is the envelope's copy of the build identity; it is not payload.
        "envelope": {
            "sha256": canonical_digest(artifact),
            "materializer_version": artifact.get("materializer_version"),
        },
        "payload": payload,
    }


def root_of(entries, digest_of):
    material = "\n".join(
        "%s\0%s" % (entry["fixture"], digest_of(entry)) for entry in entries
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def probe_deep_json(binary: Path, definitions: Path, scratch: Path):
    body = "[" * DEEP_DEPTH + "]" * DEEP_DEPTH
    plan = scratch / "deep.fmp.json"
    plan.write_text(body, encoding="utf-8")
    completed = run_limited(
        [str(binary), "materialize", str(plan), "--definitions", str(definitions)],
        PROBE_TIMEOUT,
    )
    if completed is None:
        return {
            "probe": "deep-json",
            "input": "%d nested arrays" % DEEP_DEPTH,
            "returncode": None,
            "outcome": "timeout",
            "stderr_head": "",
            "note": "A hang inside %d s is also an unbounded-reader finding." % PROBE_TIMEOUT,
        }
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
    completed = run_limited(
        [str(binary), "materialize", str(path), "--definitions", str(definitions)],
        PROBE_TIMEOUT,
    )
    if completed is None:
        return {
            "probe": "unknown-field-1mib",
            "input": "a valid positive with one 1 MiB unknown member",
            "returncode": None,
            "outcome": "timeout",
            "stderr_head": "",
        }
    return {
        "probe": "unknown-field-1mib",
        "input": "a valid positive with one 1 MiB unknown member",
        "returncode": completed.returncode,
        "outcome": "rejected" if completed.returncode == 1 else "unexpected",
        "stderr_head": completed.stderr.decode("utf-8", "replace").strip()[:200],
    }


def implementation_of(binary: Path):
    """The build receipt: crate identity plus the exact binary digest."""
    name, version = None, None
    if IMPLEMENTATION.is_file():
        for line in IMPLEMENTATION.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("name = ") and name is None:
                name = stripped.split("=", 1)[1].strip().strip('"')
            elif stripped.startswith("version.workspace"):
                version = workspace_version()
    if name is None:
        name, version = "fmp-materialize", workspace_version()
    return {"name": name, "version": version, "binary_sha256": sha256_file(binary)}


def workspace_version():
    manifest = ROOT / "prototype/Cargo.toml"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version = "):
            return stripped.split("=", 1)[1].strip().strip('"')
    return "unknown"


def toolchain_version(command, timeout=30):
    """One toolchain fact, or an `unavailable:` string.

    A non-zero exit or empty stdout is a missing fact, not a crash. Returning
    `unavailable` keeps the receipt honest; because `toolchain` is recorded and
    never compared, a host problem cannot turn into a baseline diff (exit 1).
    """
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return "unavailable: %s" % error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        return "unavailable: exit %d%s" % (
            completed.returncode,
            ": " + detail[:200] if detail else "",
        )
    lines = completed.stdout.decode("utf-8", "replace").strip().splitlines()
    if not lines:
        return "unavailable: empty stdout"
    return lines[0]


def toolchain():
    return {
        "rust": toolchain_version(["cargo", "+1.96.0", "--version"]),
        "python": "Python %s" % sys.version.split()[0],
    }


def git_revision(*arguments):
    """A git fact, or `None`. Provenance must not turn missing git into a fault."""
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8", "replace").strip()


def provenance():
    """Two commits and a worktree flag: three facts, three fields.

    `original_baseline_commit` is read from the frozen H0 snapshot instead of
    being remembered here, so it cannot drift from the evidence. The other two
    describe *this* recording; they differ from the first because a projection is
    usually written before the commit that records it.
    """
    original = None
    if FROZEN_H0_SNAPSHOT.is_file():
        frozen = load_json_object(FROZEN_H0_SNAPSHOT, "frozen H0 snapshot")
        original = frozen.get("head")
    status = git_revision("status", "--porcelain")
    return {
        "original_baseline_commit": original,
        "projection_recording_commit": git_revision("rev-parse", "HEAD"),
        "projection_recording_worktree": (
            "unknown" if status is None else ("clean" if status == "" else "dirty")
        ),
    }


def snapshot(binary: Path, probes: bool):
    documents, newest = definition_inventory()
    positives, negatives, by_isa = corpus_counts()
    entries = [artifact_entry(binary, path, DEFINITIONS) for path in positives]
    result = {
        "schema": SCHEMA,
        "projections": {"payload": PAYLOAD_PROJECTION, "envelope": ENVELOPE_PROJECTION},
        "provenance": provenance(),
        "implementation": implementation_of(binary),
        "toolchain": toolchain(),
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
            "payload_root": root_of(entries, lambda entry: entry["payload_sha256"]),
            "envelope_root": root_of(entries, lambda entry: entry["envelope"]["sha256"]),
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


def comparison_projection(snapshot, include_envelope):
    """The part of a snapshot that `--check` actually compares.

    Receipts (`provenance`, `toolchain`, `implementation`) and observations
    (`probes`) are recorded, never compared: `provenance` moves with every
    commit, `toolchain` with the host, `implementation` is what explains an
    envelope difference, and a probe is a finding rather than an invariant.

    The envelope is compared only when both sides name the same implementation.
    It carries `materializer_version`, so making it a gate would report a
    release bump as a payload drift — the defect this split exists to remove.
    The payload and its digest are always compared.
    """
    projected = {
        key: value
        for key, value in snapshot.items()
        if key not in ("probes", "toolchain", "provenance", "implementation")
    }
    artifacts = dict(projected.get("artifacts", {}))
    if not include_envelope:
        artifacts.pop("envelope_root", None)
        if "entries" in artifacts:
            artifacts["entries"] = [
                {key: value for key, value in entry.items() if key != "envelope"}
                for entry in artifacts["entries"]
            ]
    projected["artifacts"] = artifacts
    return projected


def differences(recorded, fresh, include_envelope):
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

    left = comparison_projection(recorded, include_envelope)
    right = comparison_projection(fresh, include_envelope)
    walk("", left, right)
    return diffs


def receipt_label(receipt):
    """`name/version binary <short sha>` — enough to tell two builds apart."""
    if not receipt:
        return "no receipt"
    binary = receipt.get("binary_sha256") or ""
    short = binary[7:19] if binary.startswith("sha256:") else binary[:12]
    return "%s/%s binary %s" % (receipt.get("name"), receipt.get("version"), short or "?")


def compare(recorded, fresh):
    same_implementation = recorded.get("implementation") == fresh.get("implementation")
    diffs = differences(recorded, fresh, same_implementation)
    for diff in diffs:
        print("DIFF %s" % diff)
    if diffs:
        print("FAIL: %d difference(s) against the recorded snapshot" % len(diffs))
        return 1

    print("OK: payload projection identical")
    print("payload_root: %s" % fresh["artifacts"]["payload_root"])
    # Print the anchored definition root too: `--check` fails on a mismatch
    # silently otherwise, and the gate log should show what was pinned.
    print(
        "definitions_root: %s"
        % definitions_root(fresh["definitions"]["documents"])
    )
    if same_implementation:
        print("envelope: identical (same implementation receipt)")
    else:
        # Name the binary digest, not only name/version: two local builds of the
        # same version differ, and a message that prints "0.0.0 -> 0.0.0" reads
        # as "nothing changed, yet the check was skipped".
        print(
            "envelope: not compared, implementation receipt differs (%s -> %s)"
            % (
                receipt_label(recorded.get("implementation")),
                receipt_label(fresh["implementation"]),
            )
        )
        print("recorded envelope_root: %s" % recorded["artifacts"].get("envelope_root"))
        print("fresh    envelope_root: %s" % fresh["artifacts"]["envelope_root"])
    return 0


def resolve_binary(argument: str):
    if argument:
        path = Path(argument)
        if not path.is_file():
            raise Fault("no materializer binary at %s\nbuild it first: %s" % (path, BUILD_COMMAND))
        return path
    candidates = [DEBUG_BUILD / "fmp.exe", DEBUG_BUILD / "fmp"]
    for path in candidates:
        if path.is_file():
            return path
    raise Fault(
        "no materializer binary at %s\nbuild it first: %s"
        % (" or ".join(rel(path) for path in candidates), BUILD_COMMAND)
    )


def load_snapshot(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise Fault("cannot read the recorded snapshot %s: %s" % (path, error))
    except ValueError as error:
        raise Fault("%s is not valid JSON: %s" % (path, error))


def require_schema(recorded):
    if recorded.get("schema") != SCHEMA:
        raise Fault(
            "recorded snapshot records schema %r, this tool speaks %r; an older "
            "snapshot was taken with a different projection, so keep it as evidence "
            "and re-record rather than comparing fewer fields"
            % (recorded.get("schema"), SCHEMA)
        )


def describe(value):
    """The JSON type of a value, for a fault message."""
    if value is None:
        return "null"
    return type(value).__name__


def is_digest(value):
    """`sha256:` plus 64 lowercase hex digits, the only digest the tool writes."""
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    body = value[len("sha256:") :]
    return len(body) == 64 and all(
        character in "0123456789abcdef" for character in body
    )


def load_anchor(path):
    try:
        anchor = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise Fault("cannot read the baseline anchor %s: %s" % (path, error))
    except ValueError as error:
        raise Fault("%s is not valid JSON: %s" % (path, error))
    return anchor


def validate_anchor(anchor, path):
    """The anchor is two frozen roots; it is not a second, partial snapshot."""
    if not isinstance(anchor, dict):
        raise Fault("the baseline anchor %s is %s, not an object" % (path, describe(anchor)))
    if anchor.get("schema") != ANCHOR_SCHEMA:
        raise Fault(
            "the baseline anchor %s records schema %r, this tool speaks %r"
            % (path, anchor.get("schema"), ANCHOR_SCHEMA)
        )
    if not is_digest(anchor.get("payload_root")):
        raise Fault(
            "the baseline anchor %s has no sha256 payload_root" % path
        )
    if not is_digest(anchor.get("definitions_root")):
        raise Fault(
            "the baseline anchor %s has no sha256 definitions_root; schema 0.2 "
            "pins the definition files as well as the artifacts" % path
        )


def validate_snapshot(recorded):
    """Refuse a structurally invalid snapshot before any materialization.

    `--check` compares field by field, so a snapshot that is a JSON array, a bare
    `null`, or missing `artifacts` used to fail inside the walker with an
    uncaught `AttributeError`/`KeyError` -- which Python exits as 1, the code
    that means "the baseline moved". A corrupt snapshot is a fault (2), and it
    must cost one second rather than 128 subprocesses. Every check below is a
    shape the recorder always writes; none of them is a comparison.

    The envelope is checked even when `--check` will skip it because the
    implementation receipts differ. Otherwise deleting `envelope` from the
    recorded file would look like a clean payload match and silently remove the
    evidence it is supposed to hold.
    """
    if not isinstance(recorded, dict):
        raise Fault(
            "the recorded snapshot is %s, not a JSON object" % describe(recorded)
        )
    require_schema(recorded)

    projections = recorded.get("projections")
    if not isinstance(projections, dict):
        raise Fault(
            "the recorded snapshot's projections is %s, not an object"
            % describe(projections)
        )
    for key, expected in (
        ("payload", PAYLOAD_PROJECTION),
        ("envelope", ENVELOPE_PROJECTION),
    ):
        if projections.get(key) != expected:
            raise Fault(
                "the recorded snapshot's projections.%s is %r, this tool speaks %r"
                % (key, projections.get(key), expected)
            )

    for key in ("definitions", "corpus", "artifacts"):
        if not isinstance(recorded.get(key), dict):
            raise Fault(
                "the recorded snapshot's %r is %s, not an object"
                % (key, describe(recorded.get(key)))
            )

    definitions = recorded["definitions"]
    if not isinstance(definitions.get("count"), int):
        raise Fault("the recorded snapshot has no integer definitions.count")
    documents = definitions.get("documents")
    if not isinstance(documents, list):
        raise Fault("the recorded snapshot's definitions.documents is not an array")
    if definitions["count"] != len(documents):
        raise Fault(
            "the recorded snapshot says definitions.count %d but holds %d documents"
            % (definitions["count"], len(documents))
        )
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise Fault(
                "definitions.documents[%d] is %s, not an object"
                % (index, describe(document))
            )
        for key in (
            "path",
            "namespace",
            "version",
            "definition_format",
            "isa_family",
        ):
            if not isinstance(document.get(key), str):
                raise Fault(
                    "definitions.documents[%d] has no string %r" % (index, key)
                )
        if not isinstance(document.get("forms"), int):
            raise Fault(
                "definitions.documents[%d] has no integer 'forms'" % index
            )
        for key in ("file_sha256", "digest"):
            if not is_digest(document.get(key)):
                raise Fault(
                    "definitions.documents[%d] %s is not a sha256 digest"
                    % (index, key)
                )

    newest = definitions.get("newest")
    if not isinstance(newest, dict):
        raise Fault("the recorded snapshot's definitions.newest is not an object")
    known_paths = {document["path"] for document in documents}
    for isa, path in newest.items():
        if not isinstance(isa, str) or not isinstance(path, str):
            raise Fault(
                "the recorded snapshot's definitions.newest[%r] is not a "
                "string path" % (isa,)
            )
        if path not in known_paths:
            raise Fault(
                "the recorded snapshot's definitions.newest[%r] names %r, "
                "which is not in definitions.documents" % (isa, path)
            )

    corpus = recorded["corpus"]
    for key in ("positives", "negatives"):
        if not isinstance(corpus.get(key), int):
            raise Fault("the recorded snapshot has no integer corpus.%s" % key)
    by_isa = corpus.get("by_isa")
    if not isinstance(by_isa, dict):
        raise Fault("the recorded snapshot's corpus.by_isa is not an object")
    for isa, counts in by_isa.items():
        if not isinstance(counts, dict) or not all(
            isinstance(counts.get(key), int) for key in ("positive", "negative")
        ):
            raise Fault(
                "the recorded snapshot's corpus.by_isa[%r] has no integer "
                "positive/negative" % isa
            )
    positive_sum = sum(counts["positive"] for counts in by_isa.values())
    negative_sum = sum(counts["negative"] for counts in by_isa.values())
    if corpus["positives"] != positive_sum:
        raise Fault(
            "the recorded snapshot says corpus.positives %d but by_isa sums to %d"
            % (corpus["positives"], positive_sum)
        )
    if corpus["negatives"] != negative_sum:
        raise Fault(
            "the recorded snapshot says corpus.negatives %d but by_isa sums to %d"
            % (corpus["negatives"], negative_sum)
        )

    oracle = recorded.get("oracle")
    if not isinstance(oracle, dict) or not isinstance(oracle.get("kinds"), dict):
        raise Fault("the recorded snapshot's oracle.kinds is not an object")
    if not isinstance(oracle.get("manual_derivation"), list):
        raise Fault(
            "the recorded snapshot's oracle.manual_derivation is not an array"
        )
    for kind, count in oracle["kinds"].items():
        if not isinstance(kind, str) or not isinstance(count, int):
            raise Fault(
                "the recorded snapshot's oracle.kinds[%r] is not a string/int "
                "pair" % (kind,)
            )
    if sum(oracle["kinds"].values()) != corpus["positives"]:
        raise Fault(
            "the recorded snapshot's oracle.kinds sum to %d but corpus.positives "
            "is %d" % (sum(oracle["kinds"].values()), corpus["positives"])
        )
    for index, fixture in enumerate(oracle["manual_derivation"]):
        if not isinstance(fixture, str):
            raise Fault(
                "the recorded snapshot's oracle.manual_derivation[%d] is not a "
                "string" % index
            )
    manual_count = oracle["kinds"].get("manual+disassembly", 0)
    if len(oracle["manual_derivation"]) != manual_count:
        raise Fault(
            "the recorded snapshot lists %d manual derivations but counts %d"
            % (len(oracle["manual_derivation"]), manual_count)
        )

    artifacts = recorded["artifacts"]
    if not isinstance(artifacts.get("count"), int):
        raise Fault("the recorded snapshot has no integer artifacts.count")
    entries = artifacts.get("entries")
    if not isinstance(entries, list):
        raise Fault(
            "the recorded snapshot's artifacts.entries is %s, not an array"
            % describe(entries)
        )
    if artifacts["count"] != len(entries):
        raise Fault(
            "the recorded snapshot says artifacts.count %d but holds %d entries"
            % (artifacts["count"], len(entries))
        )
    if artifacts["count"] != corpus["positives"]:
        raise Fault(
            "the recorded snapshot records %d artifacts for %d positive fixtures"
            % (artifacts["count"], corpus["positives"])
        )
    for key in ("payload_root", "envelope_root"):
        if not is_digest(artifacts.get(key)):
            raise Fault(
                "the recorded snapshot's artifacts.%s is not a sha256 digest" % key
            )

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise Fault(
                "artifacts.entries[%d] is %s, not an object" % (index, describe(entry))
            )
        for key in ("fixture", "plan_sha256", "fingerprint"):
            if not isinstance(entry.get(key), str):
                raise Fault(
                    "artifacts.entries[%d] has no string %r" % (index, key)
                )
        for key in ("plan_sha256", "fingerprint"):
            if not is_digest(entry.get(key)):
                raise Fault(
                    "artifacts.entries[%d] %s is not a sha256 digest"
                    % (index, key)
                )
        if not isinstance(entry.get("level"), int):
            raise Fault(
                "artifacts.entries[%d] has no integer 'level'" % index
            )
        size = entry.get("size")
        if not (size is None or isinstance(size, int)):
            raise Fault(
                "artifacts.entries[%d] size is %s, not an integer or null"
                % (index, describe(size))
            )
        if entry["level"] == 0 and not isinstance(size, int):
            raise Fault(
                "artifacts.entries[%d] is level 0 but has no integer size" % index
            )
        for key in ("sections", "symbols", "fixup_records"):
            if not isinstance(entry.get(key), int):
                raise Fault(
                    "artifacts.entries[%d] has no integer %r" % (index, key)
                )
        definition = entry.get("definition")
        if not isinstance(definition, dict):
            raise Fault(
                "artifacts.entries[%d] has no definition object" % index
            )
        for key in ("namespace", "version"):
            if not isinstance(definition.get(key), str):
                raise Fault(
                    "artifacts.entries[%d] definition has no string %r"
                    % (index, key)
                )
        if not is_digest(definition.get("digest")):
            raise Fault(
                "artifacts.entries[%d] definition digest is not a sha256 digest"
                % index
            )
        if not isinstance(entry.get("payload_sha256"), str):
            raise Fault(
                "artifacts.entries[%d] has no string 'payload_sha256'" % index
            )
        if not is_digest(entry.get("payload_sha256")):
            raise Fault(
                "artifacts.entries[%d] payload_sha256 is not a sha256 digest" % index
            )
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            raise Fault(
                "artifacts.entries[%d] has no payload object" % index
            )
        for key in ("format_version", "fingerprint"):
            if not isinstance(payload.get(key), str):
                raise Fault(
                    "artifacts.entries[%d] payload has no string %r"
                    % (index, key)
                )
        if not is_digest(payload.get("fingerprint")):
            raise Fault(
                "artifacts.entries[%d] payload fingerprint is not a sha256 digest"
                % index
            )
        if not isinstance(payload.get("level"), int):
            raise Fault(
                "artifacts.entries[%d] payload has no integer 'level'" % index
            )
        if not isinstance(payload.get("fixups"), list):
            raise Fault(
                "artifacts.entries[%d] payload has no fixups array" % index
            )
        if payload["level"] == 0:
            if not isinstance(payload.get("bytes_hex"), str):
                raise Fault(
                    "artifacts.entries[%d] level-0 payload has no string "
                    "'bytes_hex'" % index
                )
            if not isinstance(payload.get("size"), int):
                raise Fault(
                    "artifacts.entries[%d] level-0 payload has no integer 'size'"
                    % index
                )
        elif payload["level"] == 1:
            for key in ("sections", "symbols"):
                if not isinstance(payload.get(key), list):
                    raise Fault(
                        "artifacts.entries[%d] level-1 payload has no %r array"
                        % (index, key)
                    )
        else:
            raise Fault(
                "artifacts.entries[%d] payload level is %r, expected 0 or 1"
                % (index, payload["level"])
            )
        envelope = entry.get("envelope")
        if not isinstance(envelope, dict):
            raise Fault(
                "artifacts.entries[%d] has no envelope object" % index
            )
        if not is_digest(envelope.get("sha256")):
            raise Fault(
                "artifacts.entries[%d] has no sha256 envelope.sha256" % index
            )
        if not isinstance(envelope.get("materializer_version"), str):
            raise Fault(
                "artifacts.entries[%d] has no string envelope.materializer_version"
                % index
            )

    # Digests are derived data too. Recompute them before the roots: an edited
    # payload whose recorded digest was left alone would otherwise surface as a
    # fresh-payload diff (exit 1) instead of a corrupt snapshot (exit 2).
    for index, entry in enumerate(entries):
        if entry["payload_sha256"] != canonical_digest(entry["payload"]):
            raise Fault(
                "artifacts.entries[%d].payload_sha256 does not match its payload"
                % index
            )
        envelope_object = dict(entry["payload"])
        envelope_object["materializer_version"] = entry["envelope"][
            "materializer_version"
        ]
        if entry["envelope"]["sha256"] != canonical_digest(envelope_object):
            raise Fault(
                "artifacts.entries[%d].envelope.sha256 does not match payload + "
                "materializer_version" % index
            )

    # The roots are derived data. If they do not match the entries, the file is
    # internally inconsistent, not merely different from a fresh recording.
    if artifacts["payload_root"] != root_of(
        entries, lambda entry: entry["payload_sha256"]
    ):
        raise Fault(
            "the recorded snapshot's payload_root does not match its entries"
        )
    if artifacts["envelope_root"] != root_of(
        entries, lambda entry: entry["envelope"]["sha256"]
    ):
        raise Fault(
            "the recorded snapshot's envelope_root does not match its entries"
        )

    implementation = recorded.get("implementation")
    if not isinstance(implementation, dict):
        raise Fault(
            "the recorded snapshot's implementation is %s, not an object"
            % describe(implementation)
        )
    for key in ("name", "version", "binary_sha256"):
        if not isinstance(implementation.get(key), str):
            raise Fault(
                "the recorded snapshot's implementation has no string %r" % key
            )


def anchor_differences(recorded, anchor):
    """The recorded roots must equal the frozen anchor, independently of the run.

    `compare()` compares a fresh recording to the recorded snapshot. If a later
    commit re-records the snapshot, both sides move together and the gate would
    still pass. The anchor is the second, slower-moving reference that makes that
    operation visible. Definitions are anchored too: otherwise a whitespace-only
    edit to a historical definition could be re-recorded (the payload does not
    move) and the gate would stay green.
    """
    diffs = []
    expected = anchor["payload_root"]
    actual = recorded["artifacts"]["payload_root"]
    if actual != expected:
        diffs.append(
            "anchor/payload_root: recorded %r != frozen %r; re-recording the "
            "baseline does not move the anchor, and moving the anchor needs a "
            "compatibility ADR" % (actual, expected)
        )
    expected_definitions = anchor["definitions_root"]
    actual_definitions = definitions_root(recorded["definitions"]["documents"])
    if actual_definitions != expected_definitions:
        diffs.append(
            "anchor/definitions_root: recorded %r != frozen %r; the definition "
            "files are frozen evidence, and re-recording a snapshot does not "
            "move the anchor" % (actual_definitions, expected_definitions)
        )
    return diffs


def run(arguments):
    if arguments.check and arguments.record:
        raise Fault("--check and --record are different operations; choose one")
    if not arguments.check and not arguments.record:
        raise Fault(
            "choose --check SNAPSHOT to compare, or --record to overwrite one; "
            "a bare invocation no longer rewrites the frozen baseline"
        )
    if arguments.out and not arguments.record:
        raise Fault("--out only applies to --record")

    recorded = None
    if arguments.check:
        # Read and validate before materializing: a broken snapshot is a fault,
        # and it should cost a second, not 128 subprocesses.
        recorded = load_snapshot(arguments.check)
        validate_snapshot(recorded)
        anchor = load_anchor(arguments.anchor)
        validate_anchor(anchor, arguments.anchor)
        anchor_diff = anchor_differences(recorded, anchor)
        if anchor_diff:
            for diff in anchor_diff:
                print("DIFF %s" % diff)
            print("FAIL: the recorded snapshot no longer matches the frozen anchor")
            return 1

    binary = resolve_binary(arguments.binary)
    fresh = snapshot(binary, arguments.probes)

    if recorded is not None:
        return compare(recorded, fresh)

    out = Path(arguments.out or DEFAULT_OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    # `newline="\n"` keeps the snapshot LF on every host; the repository is
    # `text=auto eol=lf`, so a CRLF working copy would be a spurious diff.
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(fresh, indent=2, ensure_ascii=False) + "\n")
    print(
        "recorded %d definitions, %d positives, %d negatives, %d payloads"
        % (
            fresh["definitions"]["count"],
            fresh["corpus"]["positives"],
            fresh["corpus"]["negatives"],
            fresh["artifacts"]["count"],
        )
    )
    print("payload_root:  %s" % fresh["artifacts"]["payload_root"])
    print("envelope_root: %s" % fresh["artifacts"]["envelope_root"])
    print(
        "definitions_root: %s"
        % definitions_root(fresh["definitions"]["documents"])
    )
    for probe in fresh["probes"]:
        print("probe %s: %s (exit %r)" % (probe["probe"], probe["outcome"], probe["returncode"]))
    print("written: %s" % out)
    print(
        "the anchor %s was not changed; update it only with a compatibility ADR"
        % arguments.anchor
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Record or check the HE-1 baseline")
    parser.add_argument("--out", default="", help="with --record: output path")
    parser.add_argument("--binary", default="", help="default: prototype/target/debug/fmp[.exe]")
    parser.add_argument("--check", metavar="RECORDED", help="compare against a snapshot")
    parser.add_argument(
        "--anchor",
        default=str(DEFAULT_ANCHOR),
        help="frozen payload_root/definitions_root anchor used by --check",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="overwrite a snapshot (explicit; never the default)",
    )
    parser.add_argument(
        "--probes",
        action="store_true",
        help="also run the robustness probes (one feeds a known stack overflow)",
    )
    arguments = parser.parse_args(argv)
    try:
        return run(arguments)
    except Fault as fault:
        print("error: %s" % fault, file=sys.stderr)
        return 2
    except OSError as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    except ValueError as error:
        print("error: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
