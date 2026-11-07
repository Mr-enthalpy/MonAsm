#!/usr/bin/env python3
"""Re-derive every positive fixture's oracle bytes and diff them.

`fixtures/README.md` requires an independent oracle for every positive vector.
This tool re-runs that oracle instead of trusting the recorded file:

1. hash every `*.s`/`*.asm` under `research/evidence/experiments/`;
2. match each `*.oracle.json` by `input_sha256` (content, never file name);
3. stage the input under the basename the recorded command names, run the
   recorded command verbatim in a temporary directory, and compare the produced
   image with `*.expected.bin`, `output_sha256` and `size`.

A record whose input is no longer in the tree is reported as `SKIP:
input-not-stored`; it is never counted as verified. `kind = manual+disassembly`
is skipped too, because part of its bytes is a hand-checked encoding that the
assembler does not select.

Usage:
    python tools/oracle/rerun.py [--root DIR] [--only SUBSTRING] [--strict]
                                 [--verbose]

Exit codes: 0 every resolved record passes, 1 a resolved record differs,
2 the environment is unusable (missing tool, unreadable record).
"""

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

INPUT = re.compile(r"[^\s\"']+\.(?:asm|s)(?=\s|$)")
VERSION = re.compile(r"LLVM version (\d+\.\d+\.\d+)")
PRODUCED = "out.bin"


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


def run_record(record, source, workdir):
    """Run the recorded command over `source`; return (status, reason, note)."""
    command = record.get("command", "")
    matches = INPUT.findall(command)
    if len(matches) != 1:
        return "FAIL", "command-shape", "expected exactly one assembler input"
    token = matches[0]
    staged = os.path.basename(token.replace("\\", "/"))
    shutil.copyfile(source, os.path.join(workdir, staged))
    start = command.index(token)
    executable = command[:start] + staged + command[start + len(token):]

    if "ld.lld" in executable and shutil.which("ld.lld") is None:
        return "SKIP", "tool-missing", "ld.lld not on PATH"

    try:
        result = subprocess.run(
            executable,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.SubprocessError as error:
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

    passes = 0
    skips = []
    failures = []
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
                print("SKIP  %s  manual-derivation" % name)
                skips.append((name, "manual-derivation"))
                continue
            if installed != version:
                print("SKIP  %s  toolchain-version: record %s, installed %s" % (name, version, installed))
                skips.append((name, "toolchain-version"))
                continue
            candidates = index.get(digest, [])
            if not candidates:
                print("SKIP  %s  input-not-stored: %s" % (name, digest[:16]))
                skips.append((name, "input-not-stored"))
                continue

            source = candidates[0]
            note = "%d copies, using %s" % (len(candidates), rel(root, source)) if len(candidates) > 1 else rel(root, source)
            workdir = os.path.join(scratch, os.path.basename(path).replace(".oracle.json", ""))
            os.makedirs(workdir)

            status, reason, detail = run_record(record, source, workdir)
            if status != "OK":
                print("%-4s  %s  %s: %s" % (status, name, reason, detail))
                if status == "SKIP":
                    skips.append((name, reason))
                else:
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

    if failures:
        return 1
    if arguments.strict and skips:
        print("strict: %d record(s) could not be reproduced" % len(skips))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
