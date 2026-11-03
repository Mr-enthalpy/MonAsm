#!/usr/bin/env python3
"""Verify the identity of a local Arm MRS drop.

The AArch64 definition path names the Arm Architecture Machine Readable
Specification, 2026-06. The archive is not vendored: it lives in the disposable
`research/external/` zone.

This check reads the `_meta.version` block that the MRS files declare about
themselves and compares it with the release ADR-0005 names. That is the honest
identity check available:

- The public package carries an explicit version block
  (`architecture`, `build`, `ref`, `schema`, `timestamp`).
- XirAsm's manifest also records file hashes for its own inputs
  (`source_lock.files`), but those hashes were measured **not** to match the
  public 2026-06 FAT package, so they identify a processed copy rather than the
  upstream file. Using them as a release pin would be a false claim, so this
  tool does not.

File hashes are still printed, for the evidence record, but they are not the
gate.

Usage:
    python tools/check_mrs.py [--root research/external/arm-mrs]

Exit 0 when every present file declares the pinned release and both files the
slice needs are present; 1 otherwise.
"""

import argparse
import hashlib
import io
import json
import os
import sys

# `_meta.version` of the 2026-06 A-profile MRS, as recorded both by the package
# itself and by research/external/XirAsm/include/arm/a64/generated/latest/
# manifest.json. The timestamp is the package's own release stamp.
PINNED = {
    "architecture": "vFATAp1-A",
    "build": "818",
    "ref": "2026-06_rel",
    "schema": "2.9.5",
    "timestamp": "2026-06-24 17:12:14",
}

REQUIRED = ("Instructions.json", "Features.json")

# The archive keeps the JSON under `json/`; accepting both layouts avoids a
# copy step whose only effect would be to break the provenance record.
CANDIDATE_DIRS = ("", "json")


def sha256_file(path):
    digest = hashlib.sha256()
    with io.open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find(root, name):
    for sub in CANDIDATE_DIRS:
        candidate = os.path.join(root, sub, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def read_version(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    meta = document.get("_meta")
    if not isinstance(meta, dict):
        return None, "no _meta object"
    version = meta.get("version")
    if not isinstance(version, dict):
        return None, "no _meta.version object"
    return version, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=os.path.join("research", "external", "arm-mrs"),
        help="directory holding the MRS drop (default: research/external/arm-mrs)",
    )
    args = parser.parse_args()

    failures = 0
    mismatches = 0
    for name in REQUIRED:
        path = find(args.root, name)
        if path is None:
            print("missing: {0} under {1}".format(name, args.root))
            failures += 1
            continue

        version, problem = read_version(path)
        if problem is not None:
            print("unreadable: {0}: {1}".format(path, problem))
            failures += 1
            mismatches += 1
            continue

        wrong = []
        for key, expected in PINNED.items():
            actual = version.get(key)
            if actual != expected:
                wrong.append("{0}: expected {1!r}, found {2!r}".format(key, expected, actual))
        if wrong:
            print("wrong release: {0}".format(path))
            for line in wrong:
                print("  " + line)
            failures += 1
            mismatches += 1
        else:
            print("ok: {0} ({1}, {2})".format(path, PINNED["ref"], PINNED["build"]))

        print(
            "  size {0}  sha256:{1}".format(
                os.path.getsize(path), sha256_file(path)
            )
        )

    if mismatches:
        print("FAIL: a file does not declare the pinned 2026-06 release")
        return 1
    if failures:
        print("FAIL: the drop is incomplete; the AArch64 slice needs both files")
        return 1
    print("OK: Arm MRS 2026-06 release identity confirmed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
