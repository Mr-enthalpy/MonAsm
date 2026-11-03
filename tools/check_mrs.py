#!/usr/bin/env python3
"""Verify that the local Arm MRS drop is the release ADR-0005 pins.

The AArch64 definition table is generated from the Arm Architecture Machine
Readable Specification, 2026-06. The archive is not vendored: it lives in the
disposable `research/external/` zone. This check makes "the same release" a
mechanical statement rather than a memory of one, using the hashes that
XirAsm's generated manifest recorded for the two files the slice needs.

Usage:
    python tools/check_mrs.py [--root research/external/arm-mrs]

Exit 0 when both files match, 1 otherwise. A missing file is a failure, not a
skip: a table generated from a different release would invalidate the notice
and the digest without any visible symptom.
"""

import argparse
import hashlib
import io
import os
import sys

# From research/external/XirAsm/include/arm/a64/generated/latest/manifest.json,
# source_lock.files. These identify the 2026-06 release (ref 2026-06_rel,
# schema 2.9.5) the generated A64 tree was built from.
EXPECTED = {
    "Instructions.json": "a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe",
    "Features.json": "633259000ffd3da32900bd0c0c1beae4a9eea7095c278f74d62a00c846b41187",
}

# The archive keeps the JSON under `json/`; accepting both layouts avoids a
# copy step whose only effect would be to break the hash provenance.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=os.path.join("research", "external", "arm-mrs"),
        help="directory holding the MRS drop (default: research/external/arm-mrs)",
    )
    args = parser.parse_args()

    failures = 0
    for name, expected in EXPECTED.items():
        path = find(args.root, name)
        if path is None:
            print("missing: {0} under {1}".format(name, args.root))
            failures += 1
            continue
        actual = sha256_file(path)
        if actual != expected:
            print("mismatch: {0}".format(path))
            print("  expected sha256:{0}".format(expected))
            print("  actual   sha256:{0}".format(actual))
            failures += 1
            continue
        print("ok: {0} sha256:{1}".format(path, actual))

    if failures:
        print("FAIL: {0} file(s) do not match the pinned 2026-06 release".format(failures))
        return 1
    print("OK: Arm MRS 2026-06 drop matches the pinned hashes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
