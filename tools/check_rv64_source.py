#!/usr/bin/env python3
"""Verify that a local UDB resolved-spec drop is the pinned RV64 source.

ADR-0007 pins an *archive*, not a revision: the export records no commit (its
`.stamp` is empty and the `$source` map names only a CI workspace), so the only
identity available is the bytes. This gate therefore checks:

1. the archive, when named, has the pinned size and SHA-256;
2. each instruction node the RV64 slice reads has the pinned size and SHA-256;
3. each node still declares `SPDX-License-Identifier: BSD-3-Clause-Clear` and the
   copyright line, which is the licence basis for `definitions/rv64/`;
4. `definitions/rv64/NOTICE` reproduces the pinned licence text between its
   markers, so the shipped notice cannot drift from the text it cites.

A drop that fails any clause is rejected, not repaired (`INV-07`). The drop is
disposable: it lives under `research/external/`, is gitignored, and no product
build step reads it.

Usage:
    python tools/check_rv64_source.py [--root DIR] [--archive PATH] [--notice PATH]

Exit 0 when every check passes, 1 otherwise.
"""

import argparse
import hashlib
import io
import os
import sys

# `resolved_spec.tar.gz` as supplied on 2026-11-04, measured in EXP-0009 §2.
PINNED_ARCHIVE = (
    2694443,
    "be184986ce3c0cacdf06d975de92aa8948b1a9a267a1c9d75d60afa285bd828f",
)

# The eight nodes ADR-0007 §Decision 2 reads, with the measurements from
# EXP-0009 §4. Paths are relative to the resolved-spec root (`.../resolved_spec/_`).
PINNED_NODES = {
    "inst/I/add.yaml": (
        5484,
        "f0c718f33b5394eaa7f3828bc02fbeb8fed0a5dca0d21e9b30fa16662f8b4812",
    ),
    "inst/I/addi.yaml": (
        5475,
        "f8f3099bbbde3120a7d7c796debe3ab30a42f195849208713139f9f3a525e8a6",
    ),
    "inst/I/auipc.yaml": (
        4585,
        "e1cfdacb153cdcbc2d89c1f65005279bb2aa8cde2e30856223886105f6979fa8",
    ),
    "inst/I/beq.yaml": (
        7846,
        "bb8084dbfb7b4a88f9f42e49f316702f39b435576000d3b4d4299212abb3ee40",
    ),
    "inst/I/jal.yaml": (
        6524,
        "3028bcf4bfefca77a50a4bf1bd27353c2d817abac58235af0745b1bfb739ac3e",
    ),
    "inst/I/ld.yaml": (
        27033,
        "a2afcd44fd54f5de7a9a9226f66f273b92c4e868a3519782a06c0f0fe3cc4c35",
    ),
    "inst/I/sd.yaml": (
        26947,
        "f0b69996f811f7ae206f9219cf6057318eb908d6f04af70e83e403606c71390e",
    ),
    "inst/C/c.addi.yaml": (
        8225,
        "584daae38d4e830b88be6474f5420d39d858a6c1ca94acd70ce4f5c300348e75",
    ),
}

# UDB `LICENSE-BSD-3-Clause-Clear.txt`, fetched because the archive omits it
# (EXP-0009 §3).
PINNED_LICENSE = (
    1700,
    "e3f4d72ac78db3ee135dc76442e165e75f644ed93dfc4103acce65e9d7af8f4d",
)

SPDX_LINE = "# SPDX-License-Identifier: BSD-3-Clause-Clear"
COPYRIGHT_LINE = (
    "# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries."
)

BEGIN_MARKER = "--- BEGIN BSD-3-Clause-Clear ---"
END_MARKER = "--- END BSD-3-Clause-Clear ---"

DEFAULT_NOTICE = os.path.join("definitions", "rv64", "NOTICE")
DEFAULT_ROOT = os.path.join(
    "research", "external", "rv64-udb", "gen", "resolved_spec", "_"
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
        print("  ADR-0007 permits only the pinned export, whatever a directory says.")
        return False
    print("  matches the ADR-0007 pin")
    return True


def check_node(root, relative):
    path = os.path.join(root, relative)
    if not os.path.isfile(path):
        print("missing: {0}".format(path))
        return False

    size, digest = PINNED_NODES[relative]
    actual_size = os.path.getsize(path)
    actual_digest = sha256_file(path)
    problems = []
    if (actual_size, actual_digest) != (size, digest):
        problems.append(
            "size/sha256: expected {0}/{1}, found {2}/{3}".format(
                size, digest, actual_size, actual_digest
            )
        )

    with io.open(path, "r", encoding="utf-8") as handle:
        head = handle.read(2048)
    if SPDX_LINE not in head:
        problems.append("missing header line: {0}".format(SPDX_LINE))
    if COPYRIGHT_LINE not in head:
        problems.append("missing header line: {0}".format(COPYRIGHT_LINE))

    if problems:
        print("wrong node: {0}".format(path))
        for line in problems:
            print("  " + line)
        return False
    print("ok: {0} ({1} B)".format(path, actual_size))
    return True


def licence_block(text):
    if BEGIN_MARKER not in text or END_MARKER not in text:
        return None
    body = text.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0]
    body = body.strip("\n").replace("\r\n", "\n")
    return (body + "\n").encode("utf-8")


def check_notice(path):
    if not os.path.isfile(path):
        print("missing notice: {0}".format(path))
        return False

    with io.open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    block = licence_block(text)
    if block is None:
        print("notice: {0}: missing licence markers".format(path))
        return False

    size, digest = PINNED_LICENSE
    actual_size = len(block)
    actual_digest = hashlib.sha256(block).hexdigest()
    problems = []
    if (actual_size, actual_digest) != (size, digest):
        problems.append(
            "licence text: expected {0} B/sha256:{1}, found {2} B/sha256:{3}".format(
                size, digest, actual_size, actual_digest
            )
        )
    if PINNED_ARCHIVE[1] not in text:
        problems.append("does not name the pinned archive hash")
    if "BSD-3-Clause-Clear" not in text:
        problems.append("does not name the SPDX identifier")

    if problems:
        print("wrong notice: {0}".format(path))
        for line in problems:
            print("  " + line)
        return False
    print("ok: {0} (licence text {1} B, sha256:{2})".format(path, actual_size, actual_digest))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=DEFAULT_ROOT,
        help="resolved-spec root holding inst/<EXT>/<name>.yaml (default: {0})".format(
            DEFAULT_ROOT
        ),
    )
    parser.add_argument(
        "--archive",
        default=None,
        help="also verify this .tar.gz against the pinned archive hash",
    )
    parser.add_argument(
        "--notice",
        default=DEFAULT_NOTICE,
        help="NOTICE file to verify (default: {0})".format(DEFAULT_NOTICE),
    )
    args = parser.parse_args()

    failures = 0
    if args.archive is not None and not check_archive(args.archive):
        failures += 1

    for relative in sorted(PINNED_NODES):
        if not check_node(args.root, relative):
            failures += 1

    if not check_notice(args.notice):
        failures += 1

    if failures:
        print("FAIL: {0} check(s) failed; the RV64 source pin is ADR-0007".format(failures))
        return 1
    print("OK: pinned UDB resolved-spec drop and RV64 NOTICE confirmed (ADR-0007)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
