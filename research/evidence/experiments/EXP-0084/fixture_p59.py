#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P59-gpr32-mov-index-addr32-rex-two-bit-windows.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0084/probe.asm`, which is the oracle input
and the 144-byte vector. The sixteen `0.55.0` rows cover the four two-fixed-bit
windows (`43`, `45`, `46`, `47`) in both directions at both displacement
widths, plus four corners: `%r12d` on all three operands, `%r13d` on all three,
the x8 scale with `%r15d`, and a store with `%r15d`/`%ebp`. `expected.bin` is
copied from `llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0084/fixture_p59.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P59-gpr32-mov-index-addr32-rex-two-bit-windows"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0084/probe.asm"

VERSION = "0.55.0"
DIGEST = "sha256:e4fe01184a25274242c3eb9cf29b411d48d2d629cd2befbcbd274ef6384618fc"

LOAD8_BX = "x86:mov/r32-addr32-base-ext-index-ext-disp8/legacy"
STORE8_BX = "x86:mov/addr32-base-ext-index-ext-disp8-r32/legacy"
LOAD32_BX = "x86:mov/r32-addr32-base-ext-index-ext-disp32/legacy"
STORE32_BX = "x86:mov/addr32-base-ext-index-ext-disp32-r32/legacy"
LOAD8_RB = "x86:mov/r32-ext-addr32-base-ext-index-disp8/legacy"
STORE8_RB = "x86:mov/addr32-base-ext-index-disp8-r32-ext/legacy"
LOAD32_RB = "x86:mov/r32-ext-addr32-base-ext-index-disp32/legacy"
STORE32_RB = "x86:mov/addr32-base-ext-index-disp32-r32-ext/legacy"
LOAD8_RX = "x86:mov/r32-ext-addr32-base-index-ext-disp8/legacy"
STORE8_RX = "x86:mov/addr32-base-index-ext-disp8-r32-ext/legacy"
LOAD32_RX = "x86:mov/r32-ext-addr32-base-index-ext-disp32/legacy"
STORE32_RX = "x86:mov/addr32-base-index-ext-disp32-r32-ext/legacy"
LOAD8_RBX = "x86:mov/r32-ext-addr32-base-ext-index-ext-disp8/legacy"
STORE8_RBX = "x86:mov/addr32-base-ext-index-ext-disp8-r32-ext/legacy"
LOAD32_RBX = "x86:mov/r32-ext-addr32-base-ext-index-ext-disp32/legacy"
STORE32_RBX = "x86:mov/addr32-base-ext-index-ext-disp32-r32-ext/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (LOAD8_BX, "dest", 0, 8, 9, 0, 8, 6),
    (STORE8_BX, "src", 0, 8, 9, 0, 8, 6),
    (LOAD32_BX, "dest", 0, 8, 9, 0, 200, 9),
    (STORE32_BX, "src", 0, 8, 9, 0, 200, 9),
    (LOAD8_RB, "dest", 8, 8, 1, 0, 8, 6),
    (STORE8_RB, "src", 8, 8, 1, 0, 8, 6),
    (LOAD32_RB, "dest", 8, 8, 1, 0, 200, 9),
    (STORE32_RB, "src", 8, 8, 1, 0, 200, 9),
    (LOAD8_RX, "dest", 8, 0, 9, 0, 8, 6),
    (STORE8_RX, "src", 8, 0, 9, 0, 8, 6),
    (LOAD32_RX, "dest", 8, 0, 9, 0, 200, 9),
    (STORE32_RX, "src", 8, 0, 9, 0, 200, 9),
    (LOAD8_RBX, "dest", 8, 8, 9, 0, 8, 6),
    (STORE8_RBX, "src", 8, 8, 9, 0, 8, 6),
    (LOAD32_RBX, "dest", 8, 8, 9, 0, 200, 9),
    (STORE32_RBX, "src", 8, 8, 9, 0, 200, 9),
    (LOAD8_RBX, "dest", 12, 12, 12, 0, 8, 6),
    (LOAD8_RBX, "dest", 13, 13, 13, 0, 8, 6),
    (LOAD8_RBX, "dest", 15, 8, 9, 3, 8, 6),
    (STORE8_RB, "src", 15, 15, 5, 0, 8, 6),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p59.py <oracle.bin>")
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
            operand("base", "x86.gpr32", "rm32", {"reg": base}),
            operand("index", "x86.gpr32", "sib_index32", {"reg": sib_index}),
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
                    "research/evidence/experiments/EXP-0084/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The sixteen 0.55.0 rows: two fixed REX bits on the 0x67 "
            "address-size mov, both directions at disp8 and disp32. 0x67 is "
            "byte 0 and REX byte 1, so the opcode is byte 2, ModRM byte 3 "
            "(register [27,3]) and SIB byte 4 (base [32,3], index [35,3], "
            "scale [38,2]), with the displacement at [40,8] or [40,32]. "
            "REX.BX is 43, REX.RB 45, REX.RX 46 and REX.RBX 47; each extended "
            "operand excludes 0-7 and each low operand stays three bits. The "
            "four extra instructions cover %r12d on all three operands "
            "(67 47 8b 64 24 08), %r13d on all three (67 47 8b 6c 2d 08), the "
            "x8 scale with %r15d (67 47 8b 7c c8 08) and a store with "
            "%r15d/%ebp (67 45 89 7c 2f 08). input_sha256 is probe.asm; "
            "output_sha256 is the 144-byte .text."
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
