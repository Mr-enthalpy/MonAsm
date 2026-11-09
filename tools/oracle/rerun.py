#!/usr/bin/env python3
"""Re-derive every positive fixture's oracle bytes and diff them.

`fixtures/README.md` requires an independent oracle for every positive vector.
This tool re-runs that oracle instead of trusting the recorded file:

1. hash every `*.s`/`*.asm` under `research/evidence/experiments/`;
2. match each `*.oracle.json` by `input_sha256` (content, never file name);
3. stage the input under the basename the recorded command names, split the
   recorded command into `&&` stages, run each stage as an argv list (never
   through a shell, and only for executables on `ALLOWED_EXECUTABLES`), and
   compare the produced image with `*.expected.bin`, `output_sha256` and `size`.

A record whose input is no longer in the tree is reported as `SKIP:
input-not-stored`; it is never counted as verified. `kind = manual+disassembly`
is skipped too, because part of its bytes is a hand-checked encoding that the
assembler does not select. A skip reason must be named with
`--allow-skip-reason` to stay a skip: any other skip is a failure, so a gate
cannot pass by quietly skipping the records it was meant to reproduce.

Usage:
    python tools/oracle/rerun.py [--root DIR] [--only SUBSTRING] [--strict]
                                 [--allow-skip-reason REASON]... [--verbose]

Exit codes: 0 every resolved record passes, 1 a resolved record differs or was
skipped for a reason that was not allowed, 2 the environment is unusable
(missing tool, unreadable record, no record matched).
"""

import argparse
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

INPUT = re.compile(r"[^\s\"']+\.(?:asm|s)")
VERSION = re.compile(r"LLVM version (\d+\.\d+\.\d+)")
PRODUCED = "out.bin"

# The only programs an oracle record may name. The records are data files in the
# tree, so this is an allowlist rather than a convention: a record cannot ask the
# rerun to execute an arbitrary binary.
ALLOWED_EXECUTABLES = frozenset({"llvm-mc", "llvm-objcopy", "llvm-readobj", "ld.lld"})

# Characters that only mean something to a shell. A record that uses one was
# written for `shell=True`; running the same text as an argv list would change
# its meaning, so it is refused rather than reinterpreted.
SHELL_METACHARACTERS = set(";|&<>$`")


class RecordError(Exception):
    """A record that cannot be run as written."""

    def __init__(self, reason, detail=""):
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def rel(root, path):
    return os.path.relpath(path, root).replace("\\", "/")


def index_inputs(evidence):
    """Map sha256 -> sorted list of input paths, walking in sorted order."""
    index = {}
    for dirpath, dirnames, filenames in os.walk(evidence):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.endswith((".s", ".asm")):
                continue
            path = os.path.join(dirpath, name)
            with open(path, "rb") as handle:
                digest = sha256(handle.read())
            index.setdefault(digest, []).append(path)
    return index


def tool_version():
    try:
        result = subprocess.run(
            ["llvm-mc", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = VERSION.search(result.stdout)
    return match.group(1) if match else None


def parse_command(record):
    """Split a recorded command into argv stages and locate the input token.

    Returns `(stages, stage_index, token_index)`. Raises `RecordError` when the
    record is malformed: an empty stage, an unbalanced quote, an executable off
    the allowlist, or a number of assembler inputs other than one.
    """
    command = record.get("command", "")
    stages = []
    for raw in command.split("&&"):
        try:
            argv = shlex.split(raw)
        except ValueError as error:
            raise RecordError("command-shape", "unbalanced quotes: %s" % error)
        if not argv:
            raise RecordError("command-shape", "empty && stage")
        executable = os.path.basename(argv[0])
        if executable not in ALLOWED_EXECUTABLES:
            raise RecordError("executable-not-allowed", executable)
        for token in argv:
            if SHELL_METACHARACTERS.intersection(token):
                raise RecordError("command-shape", "shell metacharacter in %r" % token)
        stages.append(argv)

    hits = [
        (stage, index)
        for stage, argv in enumerate(stages)
        for index, token in enumerate(argv)
        if INPUT.fullmatch(token)
    ]
    if len(hits) != 1:
        raise RecordError(
            "command-shape",
            "expected exactly one assembler input, found %d" % len(hits),
        )
    return stages, hits[0][0], hits[0][1]


def run_record(record, source, workdir):
    """Run the recorded command over `source`; return (status, reason, note)."""
    try:
        stages, stage, index = parse_command(record)
    except RecordError as error:
        return "FAIL", error.reason, error.detail

    token = stages[stage][index]
    staged = os.path.basename(token.replace("\\", "/"))
    shutil.copyfile(source, os.path.join(workdir, staged))
    stages[stage][index] = staged

    # Resolve each executable through PATH and run the resolved path. Windows
    # `CreateProcess` only appends `.exe` to a name with no dot, so `ld.lld`
    # (a real file name with a dot) is not found unless it is resolved first.
    missing = []
    for argv in stages:
        resolved = shutil.which(argv[0])
        if resolved is None:
            missing.append(os.path.basename(argv[0]))
        else:
            argv[0] = resolved
    if missing:
        return "SKIP", "tool-missing", "%s not on PATH" % missing[0]

    for argv in stages:
        try:
            result = subprocess.run(
                argv,
                shell=False,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return "FAIL", "command-failed", str(error)
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip().splitlines()
            return "FAIL", "command-failed", message[0] if message else "no output"

    produced_path = os.path.join(workdir, PRODUCED)
    if not os.path.isfile(produced_path):
        return "FAIL", "no-output", "%s was not written" % PRODUCED
    with open(produced_path, "rb") as handle:
        produced = handle.read()
    return "OK", None, produced


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None, help="repository root (default: two levels up)")
    parser.add_argument("--only", default=None, help="run only fixtures whose path contains this text")
    parser.add_argument("--strict", action="store_true", help="fail when any record is skipped")
    parser.add_argument(
        "--allow-skip-reason",
        action="append",
        default=[],
        metavar="REASON",
        help="keep this skip reason a skip (repeatable); every other skip fails",
    )
    parser.add_argument("--verbose", action="store_true", help="print the resolved input for every pass")
    arguments = parser.parse_args()

    root = arguments.root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    evidence = os.path.join(root, "research", "evidence", "experiments")
    fixtures = os.path.join(root, "fixtures")

    installed = tool_version()
    if installed is None:
        print("error: llvm-mc is not on PATH or printed no version", file=sys.stderr)
        return 2
    if shutil.which("llvm-objcopy") is None:
        print("error: llvm-objcopy is not on PATH", file=sys.stderr)
        return 2

    index = index_inputs(evidence)
    paths = []
    for isa in sorted(os.listdir(fixtures)):
        positive = os.path.join(fixtures, isa, "positive")
        if not os.path.isdir(positive):
            continue
        for name in sorted(os.listdir(positive)):
            if name.endswith(".oracle.json"):
                paths.append(os.path.join(positive, name))

    print("toolchain: llvm-mc %s" % installed)
    print("%d positive records, %d distinct inputs in the evidence tree" % (len(paths), len(index)))
    print()

    allowed_skips = set(arguments.allow_skip_reason)
    passes = 0
    skips = []
    failures = []

    def record_skip(name, reason, detail=""):
        """Keep an allowed skip; turn any other skip into a failure."""
        allowed = reason in allowed_skips
        suffix = "  %s" % reason if not detail else "  %s: %s" % (reason, detail)
        print("%s  %s%s" % ("SKIP" if allowed else "FAIL", name, suffix))
        if allowed:
            skips.append((name, reason))
        else:
            failures.append((name, "skip-not-allowed:" + reason, detail))

    with tempfile.TemporaryDirectory(prefix="fmp-oracle-") as scratch:
        for path in paths:
            name = rel(root, path)
            if arguments.only and arguments.only not in name:
                continue
            try:
                with io.open(path, encoding="utf-8") as handle:
                    record = json.load(handle)
                digest = record["input_sha256"]
                version = record.get("version")
                kind = record.get("kind")
            except (OSError, ValueError, KeyError) as error:
                print("FAIL  %s  malformed-record: %s" % (name, error))
                failures.append((name, "malformed-record", str(error)))
                continue

            if kind == "manual+disassembly":
                record_skip(name, "manual-derivation")
                continue
            if installed != version:
                record_skip(
                    name,
                    "toolchain-version",
                    "record %s, installed %s" % (version, installed),
                )
                continue
            candidates = index.get(digest, [])
            if not candidates:
                record_skip(name, "input-not-stored", digest[:16])
                continue

            source = candidates[0]
            note = "%d copies, using %s" % (len(candidates), rel(root, source)) if len(candidates) > 1 else rel(root, source)
            workdir = os.path.join(scratch, os.path.basename(path).replace(".oracle.json", ""))
            os.makedirs(workdir)

            status, reason, detail = run_record(record, source, workdir)
            if status == "SKIP":
                record_skip(name, reason, detail)
                continue
            if status != "OK":
                print("%-4s  %s  %s: %s" % (status, name, reason, detail))
                failures.append((name, reason, detail))
                continue

            produced = detail
            expected_path = os.path.join(
                os.path.dirname(path),
                os.path.basename(path).replace(".oracle.json", ".expected.bin"),
            )
            with open(expected_path, "rb") as handle:
                expected = handle.read()
            if produced != expected:
                offset = next((i for i, (a, b) in enumerate(zip(produced, expected)) if a != b), min(len(produced), len(expected)))
                detail = "first difference at byte %d (%d bytes produced, %d expected)" % (offset, len(produced), len(expected))
                print("FAIL  %s  bytes-differ: %s" % (name, detail))
                failures.append((name, "bytes-differ", detail))
                continue
            if sha256(produced) != record.get("output_sha256"):
                print("FAIL  %s  output-sha256-differ" % name)
                failures.append((name, "output-sha256-differ", ""))
                continue
            if len(produced) != record.get("size"):
                print("FAIL  %s  size-differ: record %s, produced %d" % (name, record.get("size"), len(produced)))
                failures.append((name, "size-differ", ""))
                continue

            passes += 1
            if arguments.verbose:
                print("PASS  %s  %s  (%s)" % (name, note, record.get("command")))
            else:
                print("PASS  %s" % name)

    executed = passes + len(skips) + len(failures)
    print()
    if executed == 0:
        print("error: no record matched --only %r" % arguments.only, file=sys.stderr)
        return 2
    print("%d/%d re-derived, %d skipped, %d failed" % (passes, executed, len(skips), len(failures)))
    if skips:
        reasons = {}
        for _, reason in skips:
            reasons[reason] = reasons.get(reason, 0) + 1
        print("skip reasons: " + ", ".join("%s=%d" % item for item in sorted(reasons.items())))
        print("allowed skip reasons: " + ", ".join(sorted(allowed_skips)))

    if failures:
        return 1
    if arguments.strict and skips:
        print("strict: %d record(s) could not be reproduced" % len(skips))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
