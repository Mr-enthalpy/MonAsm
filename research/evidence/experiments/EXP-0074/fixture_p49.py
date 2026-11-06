#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P49-gpr16-mov-index-rex-rx.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0074/probe.asm`, which is the oracle input
and the 90-byte vector. The four rows cover both directions and both
displacement widths; the six `disp8` instructions cover the four scale
factors and the low/high ends of the base and index windows, and the six
`disp32` instructions repeat three of those shapes with the wider
displacement. `expected.bin` is copied from `llvm-objcopy`, never produced by
the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0074/fixture_p49.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P49-gpr16-mov-index-rex-rx"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0074/probe.asm"

VERSION = "0.45.0"
DIGEST = "sha256:9adaf50a6798c7b4bd5f0090f9860de30e360994c45138f017a3c1298e5fc2d8"

LOAD8 = "x86:mov/r16-ext-base-index-disp8/legacy"
STORE8 = "x86:mov/base-index-disp8-r16-ext/legacy"
LOAD32 = "x86:mov/r16-ext-base-index-disp32/legacy"
STORE32 = "x86:mov/base-index-disp32-r16-ext/legacy"

# (form_id, role, register, base, index, scale_bits, disp, size)
PLAN = [
    (LOAD8, "dest", 8, 0, 1, 0, 8, 6),
    (LOAD8, "dest", 15, 15, 13, 3, 8, 6),
    (STORE8, "src", 8, 0, 1, 0, 8, 6),
    (STORE8, "src", 15, 15, 13, 3, 8, 6),
    (LOAD8, "dest", 8, 8, 7, 1, 8, 6),
    (STORE8, "src", 15, 7, 12, 2, 8, 6),
    (LOAD32, "dest", 8, 0, 1, 0, 200, 9),
    (LOAD32, "dest", 15, 15, 13, 3, 200, 9),
    (STORE32, "src", 8, 0, 1, 0, 200, 9),
    (STORE32, "src", 15, 15, 13, 3, 200, 9),
    (LOAD32, "dest", 8, 8, 7, 1, 200, 9),
    (STORE32, "src", 15, 7, 12, 2, 200, 9),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p49.py <oracle.bin>")
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
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
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
                    "research/evidence/experiments/EXP-0074/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "All four 0.45.0 rows: load and store at disp8 and disp32, with "
            "scale 1/2/4/8, both ends of the %r8w-%r15w register window, low "
            "and high bases (%rax/%r8/%r15) and low and high indexes "
            "(%rcx/%rdi/%r12/%r13), twelve instructions and 90 bytes. The "
            "disp8 rows are six bytes (66 44 8b 44 08 08 with REX.R only, "
            "66 47 8b 7c ef 08 with REX.RXB, 66 45 8b 44 78 08 with REX.RB "
            "and 66 46 89 7c a7 08 with REX.RX), and the disp32 rows are "
            "nine (the same prefixes with ModRM 84 and the signed disp32 at "
            "[40,32]). input_sha256 is probe.asm (the source above); "
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
