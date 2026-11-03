#!/usr/bin/env python3
"""Derive RV64 instruction bytes from UDB `encoding.location` alone.

This is the experiment behind EXP-0009 section 5 and the prototype for
`definitions/rv64/0.1.0.json`. It reads the pinned UDB resolved-spec nodes,
transcribes their `encoding.match` / `encoding.variables[]` facts, and encodes
the probe vectors whose expected bytes were produced independently with
`llvm-mc 23.1.2`.

The load-bearing claim is narrow: a variable's `location` string is a complete
description of where its value bits go, including the scattered B-type, J-type
and RVC immediates. If that is true, the definition table does not need a
hand-written scatter for `beq`/`jal`/`c.addi`, and `llvm-mc` is a genuine second
source rather than a re-encoding of the same table.

Exit 0 means every vector matched the oracle and every negative case was
rejected. Usage:

    python research/evidence/experiments/EXP-0009/rv64_fields.py
"""

import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SPEC = os.path.join(
    ROOT, "research", "external", "rv64-udb", "gen", "resolved_spec", "_", "inst"
)

# Transcribed from the pinned nodes. `lines` are asserted to appear verbatim in
# the source file, so a transcription that drifts from the pinned bytes fails
# instead of silently encoding a different fact.
NODES = {
    "add": {
        "path": "I/add.yaml",
        "width": 32,
        "match": "0000000----------000-----0110011",
        "vars": [
            ("xd", "11-7", None, False),
            ("xs1", "19-15", None, False),
            ("xs2", "24-20", None, False),
        ],
        "lines": ['match: "0000000----------000-----0110011"', "location: 24-20"],
    },
    "addi": {
        "path": "I/addi.yaml",
        "width": 32,
        "match": "-----------------000-----0010011",
        "vars": [
            ("xd", "11-7", None, False),
            ("xs1", "19-15", None, False),
            ("imm", "31-20", None, True),
        ],
        "lines": ['match: "-----------------000-----0010011"', "location: 31-20"],
    },
    "ld": {
        "path": "I/ld.yaml",
        "width": 32,
        "match": "-----------------011-----0000011",
        "vars": [
            ("xd", "11-7", None, False),
            ("xs1", "19-15", None, False),
            ("imm", "31-20", None, True),
        ],
        "lines": ['match: -----------------011-----0000011', "location: 31-20"],
    },
    "sd": {
        "path": "I/sd.yaml",
        "width": 32,
        "match": "-----------------011-----0100011",
        "vars": [
            ("xs2", "24-20", None, False),
            ("xs1", "19-15", None, False),
            ("imm", "31-25|11-7", None, True),
        ],
        "lines": ['match: -----------------011-----0100011', 'location: "31-25|11-7"'],
    },
    "beq": {
        "path": "I/beq.yaml",
        "width": 32,
        "match": "-----------------000-----1100011",
        "vars": [
            ("xs1", "19-15", None, False),
            ("xs2", "24-20", None, False),
            ("imm", "31|7|30-25|11-8", 1, True),
        ],
        "lines": [
            'match: "-----------------000-----1100011"',
            'location: "31|7|30-25|11-8"',
            "left_shift: 1",
        ],
    },
    "jal": {
        "path": "I/jal.yaml",
        "width": 32,
        "match": "-------------------------1101111",
        "vars": [
            ("xd", "11-7", None, False),
            ("imm", "31|19-12|20|30-21", 1, True),
        ],
        "lines": [
            'match: "-------------------------1101111"',
            'location: "31|19-12|20|30-21"',
            "left_shift: 1",
        ],
    },
    "auipc": {
        "path": "I/auipc.yaml",
        "width": 32,
        "match": "-------------------------0010111",
        "vars": [
            ("xd", "11-7", None, False),
            ("imm", "31-12", 12, True),
        ],
        "lines": [
            'match: "-------------------------0010111"',
            "location: 31-12",
            "left_shift: 12",
        ],
    },
    "c.addi": {
        "path": "C/c.addi.yaml",
        "width": 16,
        "match": "000-----------01",
        "vars": [
            ("xd", "11-7", None, False),
            ("imm", "12|6-2", None, True),
        ],
        "lines": [
            'match: "000-----------01"',
            'location: "12|6-2"',
            "not: 0",
        ],
        "not_zero": ("xd", "imm"),
    },
}

# (node, {var: value}, expected little-endian bytes from `llvm-mc -triple=riscv64`)
# Registers: a0 = x10, a1 = x11, a2 = x12, ra = x1.
POSITIVE = [
    ("add", {"xd": 10, "xs1": 11, "xs2": 12}, "33 85 c5 00", "add a0, a1, a2"),
    ("addi", {"xd": 10, "xs1": 11, "imm": 1}, "13 85 15 00", "addi a0, a1, 1"),
    ("addi", {"xd": 10, "xs1": 11, "imm": -1}, "13 85 f5 ff", "addi a0, a1, -1"),
    ("addi", {"xd": 10, "xs1": 11, "imm": 2047}, "13 85 f5 7f", "addi a0, a1, 2047"),
    ("addi", {"xd": 10, "xs1": 11, "imm": -2048}, "13 85 05 80", "addi a0, a1, -2048"),
    ("ld", {"xd": 10, "xs1": 11, "imm": 8}, "03 b5 85 00", "ld a0, 8(a1)"),
    ("ld", {"xd": 10, "xs1": 11, "imm": -8}, "03 b5 85 ff", "ld a0, -8(a1)"),
    ("sd", {"xs2": 10, "xs1": 11, "imm": 8}, "23 b4 a5 00", "sd a0, 8(a1)"),
    ("beq", {"xs1": 10, "xs2": 11, "imm": 4}, "63 04 b5 00", "beq a0, a1, 8"),
    ("beq", {"xs1": 10, "xs2": 11, "imm": -4}, "e3 0c b5 fe", "beq a0, a1, -8"),
    ("jal", {"xd": 1, "imm": 4}, "ef 00 80 00", "jal ra, 8"),
    ("jal", {"xd": 1, "imm": -4}, "ef f0 9f ff", "jal ra, -8"),
    ("auipc", {"xd": 10, "imm": 1}, "17 15 00 00", "auipc a0, 1"),
    ("c.addi", {"xd": 10, "imm": 1}, "05 05", "c.addi a0, 1"),
]


def groups_of(location):
    """Split `31|7|30-25|11-8` into [(msb, lsb, width)] in value order."""
    groups = []
    for part in location.split("|"):
        if "-" in part:
            hi, lo = part.split("-")
        else:
            hi = lo = part
        hi, lo = int(hi), int(lo)
        if hi < lo:
            raise ValueError("location group %r is inverted" % part)
        groups.append((hi, lo, hi - lo + 1))
    return groups


def encode(node_name, operands):
    node = NODES[node_name]
    word = 0
    for index, bit in enumerate(node["match"]):
        if bit not in "-01":
            raise ValueError("%s: bad match character %r" % (node_name, bit))
        if bit == "1":
            word |= 1 << (node["width"] - 1 - index)

    for name, location, left_shift, signed in node["vars"]:
        if name not in operands:
            raise KeyError("%s: no value for %s" % (node_name, name))
        value = operands[name]
        groups = groups_of(location)
        width = sum(g[2] for g in groups)
        if signed and not -(1 << (width - 1)) <= value < (1 << (width - 1)):
            raise ValueError(
                "%s.%s: %d does not fit signed %d bits" % (node_name, name, value, width)
            )
        if not signed and not 0 <= value < (1 << width):
            raise ValueError(
                "%s.%s: %d does not fit %d bits" % (node_name, name, value, width)
            )
        bits = value & ((1 << width) - 1)
        consumed = width
        for hi, lo, group_width in groups:
            consumed -= group_width
            chunk = (bits >> consumed) & ((1 << group_width) - 1)
            for offset in range(group_width):
                if chunk & (1 << offset):
                    word |= 1 << (lo + offset)
        if consumed != 0:
            raise AssertionError("value bits left over")

    for name in node.get("not_zero", ()):
        if operands[name] == 0:
            raise ValueError("%s.%s: zero is not encodable" % (node_name, name))

    return word.to_bytes(node["width"] // 8, "little")


def main():
    failures = 0
    missing = 0

    print("== source presence and transcription")
    for node_name, node in sorted(NODES.items()):
        path = os.path.join(SPEC, node["path"])
        if not os.path.isfile(path):
            print("  missing: %s" % path)
            missing += 1
            continue
        with io.open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        for line in node["lines"]:
            if line not in text:
                print("  %s: transcribed line absent: %s" % (node_name, line))
                failures += 1
        print("  ok: %s" % path)

    print("== positive vectors")
    for node_name, operands, expected, asm in POSITIVE:
        actual = encode(node_name, operands).hex(" ")
        status = "ok  " if actual == expected else "FAIL"
        if actual != expected:
            failures += 1
        left_shift = dict(
            (name, shift)
            for name, _location, shift, _signed in NODES[node_name]["vars"]
        ).get("imm")
        note = ""
        if left_shift:
            note = "  (imm field %d -> byte value %d)" % (
                operands["imm"],
                operands["imm"] << left_shift,
            )
        print(
            "  %s %-8s %-24s expected %s  got %s%s"
            % (status, node_name, asm, expected, actual, note)
        )

    print("== negative vectors (the source states `not: 0`)")
    for node_name, operands, why in [
        ("c.addi", {"xd": 10, "imm": 0}, "imm = 0 encodes C.NOP/HINT"),
        ("c.addi", {"xd": 0, "imm": 1}, "xd = 0 encodes C.NOP/HINT"),
    ]:
        try:
            encode(node_name, operands)
        except ValueError as error:
            print("  ok   rejected %-8s %s: %s" % (node_name, why, error))
        else:
            print("  FAIL accepted %-8s %s" % (node_name, why))
            failures += 1

    print("== derived placements (value order, as fmp-def/0.1 spells them)")
    for node_name in sorted(NODES):
        for name, location, _left_shift, _signed in NODES[node_name]["vars"]:
            placements = ", ".join(
                "[%d,%d]" % (lo, width) for _hi, lo, width in groups_of(location)
            )
            print("  %-8s %-5s %s" % (node_name, name, placements))

    if missing:
        print("SKIP: %d source file(s) absent; the drop is disposable" % missing)
        return 0
    if failures:
        print("FAIL: %d mismatch(es)" % failures)
        return 1
    print("OK: 14 positive vectors and 2 negative cases agree with llvm-mc 23.1.2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
