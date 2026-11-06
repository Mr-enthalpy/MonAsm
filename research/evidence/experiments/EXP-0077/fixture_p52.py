#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P52-gpr16-mov-index-rex-bx-window.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0077/probe.asm`, which is the oracle input
and the 90-byte vector. The four rows are covered in both directions at both
displacement widths: the two window extremes (`%r8`/`%r9` and `%r15`/`%r15`
with the x8 scale) plus a `%r12`/`%r12` pair, which is legal on both operands
once `REX.B` and `REX.X` are set. `expected.bin` is copied from
`llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0077/fixture_p52.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P52-gpr16-mov-index-rex-bx-window"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0077/probe.asm"

VERSION = "0.48.0"
DIGEST = "sha256:552b82733ac35ec9d6270dbab21bef8b19f3de800f25fc7f9c0654c4eb6189ff"

LOAD8 = "x86:mov/r16-base-ext-index-ext-disp8/legacy"
STORE8 = "x86:mov/base-ext-index-ext-disp8-r16/legacy"
LOAD32 = "x86:mov/r16-base-ext-index-ext-disp32/legacy"
STORE32 = "x86:mov/base-ext-index-ext-disp32-r16/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (LOAD8, "dest", 0, 8, 9, 0, 8, 6),
    (LOAD8, "dest", 7, 15, 15, 3, 8, 6),
    (STORE8, "src", 0, 8, 9, 0, 8, 6),
    (STORE8, "src", 7, 15, 15, 3, 8, 6),
    (LOAD8, "dest", 0, 12, 12, 0, 8, 6),
    (STORE8, "src", 0, 12, 12, 0, 8, 6),
    (LOAD32, "dest", 0, 8, 9, 0, 200, 9),
    (LOAD32, "dest", 7, 15, 15, 3, 200, 9),
    (STORE32, "src", 0, 8, 9, 0, 200, 9),
    (STORE32, "src", 7, 15, 15, 3, 200, 9),
    (LOAD32, "dest", 0, 12, 12, 0, 200, 9),
    (STORE32, "src", 0, 12, 12, 0, 200, 9),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p52.py <oracle.bin>")
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
            operand(role, "x86.gpr16", "r16", {"reg": reg}),
            operand("base", "x86.gpr64", "rm64", {"reg": base}),
            operand("index", "x86.gpr64", "sib_index", {"reg": sib_index}),
            operand("imm", "x86.scale", "scale2", {"value": scale}),
        ]
        operands.append(
            operand("disp", "x86.imm", "disp%d" % (8 if size == 6 else 32),
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
                    "research/evidence/experiments/EXP-0077/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The four 0.48.0 rows: both directions at disp8 and disp32, six "
            "instructions per displacement width. Every instruction sets both "
            "REX extension bits (REX = 43): the base and the index are in "
            "%r8-%r15 while the register stays in %ax-%di, so ModRM.reg is "
            "three bits at [27,3]. The window extremes are %r8/%r9 (low three "
            "bits 0/1) and %r15/%r15 with the x8 scale (SIB = ff), and the "
            "%r12/%r12 pairs exercise SIB.base = 100 and SIB.index = 100 "
            "behind REX.B/REX.X (SIB = 24). The disp8 rows are six bytes "
            "(66 43 8b 44 08 08, 66 43 8b 7c ff 08, 66 43 8b 44 24 08 and "
            "their 89-direction counterparts) and the disp32 rows are nine, "
            "with the signed disp32 at [40,32]. input_sha256 is probe.asm; "
            "output_sha256 is the 90-byte .text."
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
