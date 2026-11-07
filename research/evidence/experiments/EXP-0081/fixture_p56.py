#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P56-gpr32-mov-index-rex-rbx-window.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0081/probe.asm`, which is the oracle input
and the 56-byte vector. The four `0.52.0` rows are covered in both directions at
both displacement widths, plus six corners: `%r12`/`%r12`, `%r15`/`%r15` with
`%r15d` at x8, `%r12` as an index, `%r12` as a base, the x8 scale, and a second
extended triple with the x2 scale in the store direction. `expected.bin` is
copied from `llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0081/fixture_p56.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P56-gpr32-mov-index-rex-rbx-window"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0081/probe.asm"

VERSION = "0.52.0"
DIGEST = "sha256:4587b149e1119681ffefe011862343d8bccd0f52dbe7d278a0afb05517f7f7ae"

LOAD8 = "x86:mov/r32-ext-base-ext-index-ext-disp8/legacy"
STORE8 = "x86:mov/base-ext-index-ext-disp8-r32-ext/legacy"
LOAD32 = "x86:mov/r32-ext-base-ext-index-ext-disp32/legacy"
STORE32 = "x86:mov/base-ext-index-ext-disp32-r32-ext/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (LOAD8, "dest", 8, 8, 9, 0, 8, 5),
    (STORE8, "src", 8, 8, 9, 0, 8, 5),
    (LOAD32, "dest", 8, 8, 9, 0, 200, 8),
    (STORE32, "src", 8, 8, 9, 0, 200, 8),
    (LOAD8, "dest", 8, 12, 12, 0, 8, 5),
    (LOAD8, "dest", 15, 15, 15, 3, 8, 5),
    (LOAD8, "dest", 8, 8, 12, 0, 8, 5),
    (LOAD8, "dest", 8, 12, 9, 0, 8, 5),
    (LOAD8, "dest", 8, 8, 9, 3, 8, 5),
    (STORE8, "src", 15, 10, 11, 1, 8, 5),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p56.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[7] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, reg, base, sib_index, scale, disp, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size,
                          "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            operand(role, "x86.gpr32", "r32", {"reg": reg}),
            operand("base", "x86.gpr64", "rm64", {"reg": base}),
            operand("index", "x86.gpr64", "sib_index", {"reg": sib_index}),
            operand("imm", "x86.scale", "scale2", {"value": scale}),
        ]
        operands.append(
            operand("disp", "x86.imm", "disp%d" % (8 if size == 5 else 32),
                    {"value": disp}))
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
                    "research/evidence/experiments/EXP-0081/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The four 0.52.0 rows: the REX.RBX window on the 32-bit indexed mov, "
            "both directions at disp8 and disp32. One prefix byte carries R, B "
            "and X, so ModRM is byte 2 (register [2,1]+[19,3]) and SIB is byte 3 "
            "(base [0,1]+[24,3], index [1,1]+[27,3], scale [30,2]), with the "
            "displacement at [32,8] or [32,32]. The disp8 rows are five bytes "
            "(47 8b/89 44 08 08) and the disp32 rows are eight. Six extra "
            "instructions cover %r12/%r12 (47 8b 44 24 08), %r15/%r15 with "
            "%r15d at x8 (47 8b 7c ff 08), %r12 as an index, %r12 as a base, the "
            "x8 scale and a second extended triple at x2 in the store direction. "
            "input_sha256 is probe.asm; output_sha256 is the 56-byte .text."
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
