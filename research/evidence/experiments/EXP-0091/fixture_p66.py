#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P66-gpr64-mov-index-addr32-no-base.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0091/probe.asm`, which is the oracle input
and the 117-byte vector. The two `0.62.0` rows cover the no-base indexed shape
(`SIB.base = 101`, `disp32` only) at the 64-bit value width in both
directions; because `REX.W` is mandatory, `R` and `X` are free bits of the same
row rather than separate windows. Five corners follow: a zero displacement, a
negative displacement, the x4 scale, `%r12d` as the index under `REX.X`, and
`4660(,%r15d,8), %r15`. `expected.bin` is copied from `llvm-objcopy`, never
produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0091/fixture_p66.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P66-gpr64-mov-index-addr32-no-base"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0091/probe.asm"

VERSION = "0.62.0"
DIGEST = "sha256:bbcd8062c84580e208c1cbf275254593a7d937fd7de28fde19e7dc5c5049e3b3"

LOAD = "x86:mov/r64-addr32-index-disp32/legacy"
STORE = "x86:mov/addr32-index-disp32-r64/legacy"

# (form_id, role, register, index, scale, disp, size)
PLAN = [
    (LOAD, "dest", 0, 1, 0, 8, 9),
    (STORE, "src", 0, 1, 0, 8, 9),
    (LOAD, "dest", 8, 1, 0, 8, 9),
    (STORE, "src", 8, 1, 0, 8, 9),
    (LOAD, "dest", 0, 9, 0, 8, 9),
    (STORE, "src", 0, 9, 0, 8, 9),
    (LOAD, "dest", 8, 9, 0, 8, 9),
    (STORE, "src", 8, 9, 0, 8, 9),
    (LOAD, "dest", 0, 1, 0, 0, 9),
    (LOAD, "dest", 0, 1, 0, -8, 9),
    (LOAD, "dest", 0, 1, 2, 8, 9),
    (LOAD, "dest", 0, 12, 0, 8, 9),
    (LOAD, "dest", 15, 15, 3, 4660, 9),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p66.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[6] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, reg, sib_index, scale, disp, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size,
                          "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            operand(role, "x86.gpr64", "r64", {"reg": reg}),
            operand("index", "x86.gpr32", "sib_index32",
                    {"reg": sib_index}),
            operand("imm", "x86.scale", "scale2", {"value": scale}),
            operand("disp", "x86.imm", "disp32", {"value": disp}),
        ]
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": operands,
            "expected_size": size,
        })
        offset += size

    document = {
        "format_version": "fmp/0.1",
        "target_identity": {
            "isa_family": "x86",
            "isa_variant": "x86-64",
            "execution_mode": "64",
            "enabled_extensions": ["avx", "avx512f", "avx512vl"],
            "feature_constraints": [],
            "byte_order": "little",
            "address_width": 64,
        },
        "definition_identity": {
            "namespace": "monasm.isa.x86",
            "version": VERSION,
            "digest": DIGEST,
        },
        "output_contract": {
            "artifact": "bytes",
            "section_order": [".text"],
            "fixup_record_order": "section_id,offset,fixup_id",
            "include_symbol_table": False,
            "emit_fixups": True,
        },
        "sections": [
            {
                "section_id": ".text",
                "section_kind": "code",
                "image_backed": True,
                "declared_size": total,
                "fragments": fragments,
            }
        ],
        "symbols": [],
        "instructions": instructions,
        "fixups": [],
    }

    target = FIXTURES / (STEM + ".fmp.json")
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2) + "\n")
    shutil.copyfile(oracle, FIXTURES / (STEM + ".expected.bin"))

    source = ORACLE_ASM.read_bytes()
    output = (FIXTURES / (STEM + ".expected.bin")).read_bytes()
    input_sha = hashlib.sha256(source).hexdigest()
    output_sha = hashlib.sha256(output).hexdigest()

    oracle_document = {
        "tool": "llvm-mc 23.1.2 + llvm-objcopy",
        "version": "23.1.2",
        "command": ("llvm-mc -triple=x86_64 -filetype=obj "
                    "research/evidence/experiments/EXP-0091/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The two 0.62.0 rows: the 0x67 movq no-base indexed shape "
            "(ModRM 04, SIB.base 101, disp32 mandatory) in both directions, "
            "with REX.W mandatory at byte 1. R ([10,1]) and X ([9,1]) are "
            "free bits of that byte, so the load/store rows cover all "
            "sixteen value registers and indexes: 48 is the low pair, 4c an "
            "extended value, 4a an extended index and 4e both, and every row "
            "is nine bytes. Corners: zero displacement, -8, the x4 scale "
            "(SIB 8d), %r12d as the index under REX.X "
            "(67 4a 8b 04 25 08 00 00 00) and 4660(,%r15d,8), %r15 "
            "(67 4e 8b 3c fd 34 12 00 00). 0x67 is byte 0, REX byte 1, the "
            "opcode byte 2, ModRM 04 byte 3 and SIB byte 4; the value is "
            "[10,1]+[27,3], the index [9,1]+[35,3], the scale [38,2] and "
            "the displacement [40,32]. There is no base slot, so no REX.B "
            "bit exists. input_sha256 is probe.asm; output_sha256 is the "
            "117-byte .text."
        ),
    }
    oracle_path = FIXTURES / (STEM + ".oracle.json")
    with oracle_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(oracle_document, indent=2) + "\n")

    print("%s: %d instructions, %d bytes" % (STEM, len(PLAN), total))
    print("input_sha256  %s" % input_sha)
    print("output_sha256 %s" % output_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
