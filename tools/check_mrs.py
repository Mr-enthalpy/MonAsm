#!/usr/bin/env python3
"""Verify that a local Arm MRS drop is the pinned AArch64 source.

ADR-0006 pins a *packaging*, not a release. This is load-bearing: two archives of
the 2026-06 A-profile release were measured, and they differ in bytes and in
terms while declaring the same `_meta.version` (`EXP-0006`, `EXP-0007`):

| archive | `Instructions.json` | `Features.json` | terms |
|---|---|---|---|
| OPENSOURCE (pinned) | present, `a1ad2c65...` | `63325900...` | BSD-3-Clause |
| the other FAT package | absent | `6d5c19e7...` | no reproduction without Arm's written permission |

So three things are checked per file, and all three must hold:

1. `_meta.version` equals the pinned 2026-06 release block;
2. the file's size and SHA-256 equal the pinned values;
3. `_meta.license.info` equals the pinned BSD-3-Clause sentence.

The licence check is not decoration: a byte-identical file could still carry a
different notice object, and the notice is what lets `definitions/aarch64/` ship.

When `research/external/XirAsm/.../manifest.json` is present, its
`source_lock.files` hashes are compared as a cross-check. That is a report, not a
gate: XirAsm lives in the disposable zone, and a hash match says nothing about
licence terms.

Usage:
    python tools/check_mrs.py [--root research/external/arm-mrs] [--archive PATH]

Exit 0 when every required file passes all three checks (and the archive, when
named, matches its pinned hash); 1 otherwise.
"""

import argparse
import hashlib
import io
import json
import os
import sys

# `_meta.version` of the 2026-06 A-profile MRS, as declared by both measured
# packagings and by XirAsm's generated manifest. This block identifies the
# release, not the packaging, so it is necessary but not sufficient.
PINNED_VERSION = {
    "architecture": "vFATAp1-A",
    "build": "818",
    "ref": "2026-06_rel",
    "schema": "2.9.5",
    "timestamp": "2026-06-24 17:12:14",
}

# The two files the AArch64 slice reads, with the measurements from EXP-0007 §2.
PINNED_FILES = {
    "Instructions.json": (
        115441429,
        "a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe",
    ),
    "Features.json": (
        1243621,
        "633259000ffd3da32900bd0c0c1beae4a9eea7095c278f74d62a00c846b41187",
    ),
}

REQUIRED = ("Instructions.json", "Features.json")

# The exact `_meta.license.info` sentence both pinned files declare.
PINNED_LICENSE = (
    "This document is Non-confidential and licensed under the BSD 3-clause license."
)

# `AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz`, measured with Get-FileHash.
PINNED_ARCHIVE = (
    5696585,
    "fe458c521745cc2d07244c416106add69ae8faa12fa3da8aad34fa76ab29399a",
)

# The archive keeps the JSON at its root; accepting a `json/` subdirectory too
# avoids a copy step whose only effect would be to break the provenance record.
CANDIDATE_DIRS = ("", "json")

XIRASM_MANIFEST = os.path.join(
    "research", "external", "XirAsm", "include", "arm", "a64", "generated",
    "latest", "manifest.json",
)


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


def read_meta(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    meta = document.get("_meta")
    if not isinstance(meta, dict):
        return None, "no _meta object"
    version = meta.get("version")
    if not isinstance(version, dict):
        return None, "no _meta.version object"
    license_info = meta.get("license")
    if not isinstance(license_info, dict):
        return None, "no _meta.license object"
    return {"version": version, "license": license_info}, None


def check_release(version):
    problems = []
    for key, expected in PINNED_VERSION.items():
        actual = version.get(key)
        if actual != expected:
            problems.append(
                "version.{0}: expected {1!r}, found {2!r}".format(key, expected, actual)
            )
    return problems


def check_license(license_object):
    actual = license_object.get("info")
    if actual == PINNED_LICENSE:
        return []
    return ["license.info: expected {0!r}, found {1!r}".format(PINNED_LICENSE, actual)]


def check_archive(path):
    if not os.path.isfile(path):
        print("missing archive: {0}".format(path))
        return False
    size, digest = PINNED_ARCHIVE
    actual_size = os.path.getsize(path)
    actual_digest = sha256_file(path)
    print("archive: {0}".format(path))
    print("  size {0}  sha256:{1}".format(actual_size, actual_digest))
    if (actual_size, actual_digest) != (size, digest):
        print("  NOT the pinned archive: expected size {0}, sha256:{1}".format(size, digest))
        print("  ADR-0006 permits only the pinned packaging, whatever the release block says.")
        return False
    print("  matches the ADR-0006 pin")
    return True


def xirasm_cross_check():
    if not os.path.isfile(XIRASM_MANIFEST):
        return
    try:
        with io.open(XIRASM_MANIFEST, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        files = manifest["source_lock"]["files"]
    except (ValueError, KeyError, TypeError) as error:
        print("cross-check: cannot read {0}: {1}".format(XIRASM_MANIFEST, error))
        return
    print("cross-check (not a gate): XirAsm manifest source_lock.files")
    for name, (_, expected) in sorted(PINNED_FILES.items()):
        recorded = files.get(name)
        if recorded is None:
            print("  {0}: not listed".format(name))
        elif recorded == expected:
            print("  {0}: agrees".format(name))
        else:
            print("  {0}: disagrees (manifest {1})".format(name, recorded))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=os.path.join("research", "external", "arm-mrs"),
        help="directory holding the MRS drop (default: research/external/arm-mrs)",
    )
    parser.add_argument(
        "--archive",
        default=None,
        help="also verify this .tar.gz against the pinned archive hash",
    )
    args = parser.parse_args()

    failures = 0
    wrong_identity = 0

    if args.archive is not None and not check_archive(args.archive):
        failures += 1
        wrong_identity += 1

    for name in REQUIRED:
        path = find(args.root, name)
        if path is None:
            print("missing: {0} under {1}".format(name, args.root))
            failures += 1
            continue

        meta, problem = read_meta(path)
        if problem is not None:
            print("unreadable: {0}: {1}".format(path, problem))
            failures += 1
            wrong_identity += 1
            continue

        problems = check_release(meta["version"]) + check_license(meta["license"])
        expected_size, expected_digest = PINNED_FILES[name]
        actual_size = os.path.getsize(path)
        actual_digest = sha256_file(path)
        if (actual_size, actual_digest) != (expected_size, expected_digest):
            problems.append(
                "size/sha256: expected {0}/{1}, found {2}/{3}".format(
                    expected_size, expected_digest, actual_size, actual_digest
                )
            )

        if problems:
            print("wrong drop: {0}".format(path))
            for line in problems:
                print("  " + line)
            failures += 1
            wrong_identity += 1
        else:
            print(
                "ok: {0} ({1}, build {2}, BSD-3-Clause)".format(
                    path, PINNED_VERSION["ref"], PINNED_VERSION["build"]
                )
            )
            print("  size {0}  sha256:{1}".format(actual_size, actual_digest))

    xirasm_cross_check()

    if wrong_identity:
        print("FAIL: a file is not the pinned OPENSOURCE 2026-06 MRS drop (ADR-0006)")
        return 1
    if failures:
        print("FAIL: the drop is incomplete; the AArch64 slice needs both files")
        return 1
    print("OK: pinned Arm MRS OPENSOURCE 2026-06 drop confirmed (ADR-0006)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
