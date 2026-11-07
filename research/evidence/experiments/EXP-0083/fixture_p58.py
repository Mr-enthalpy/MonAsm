#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P58-gpr32-mov-index-addr32-rex-windows.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0083/probe.asm`, which is the oracle input
and the 114-byte vector. The twelve `0.54.0` rows cover the three single-`REX`
windows in both directions at both displacement widths, plus four corners:
`%r12d` as a base, `%r12d` as an index, `%ebp` as a base on the `REX.R` row and
the x8 scale on the `REX.B` row. `expected.bin` is copied from `llvm-objcopy`,
never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0083/fixture_p58.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P58-gpr32-mov-index-addr32-rex-windows"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0083/probe.asm"

VERSION = "0.54.0"
DIGEST = "sha256:4513f6a9b15293f96bb79e46dbd477ea7cc051e3fb33a9a9ce3792e8ac6fa8cd"

LOAD8_R = "x86:mov/r32-ext-addr32-base-index-disp8/legacy"
STORE8_R = "x86:mov/addr32-base-index-disp8-r32-ext/legacy"
LOAD32_R = "x86:mov/r32-ext-addr32-base-index-disp32/legacy"
STORE32_R = "x86:mov/addr32-base-index-disp32-r32-ext/legacy"
LOAD8_B = "x86:mov/r32-addr32-base-ext-index-disp8/legacy"
STORE8_B = "x86:mov/addr32-base-ext-index-disp8-r32/legacy"
LOAD32_B = "x86:mov/r32-addr32-base-ext-index-disp32/legacy"
STORE32_B = "x86:mov/addr32-base-ext-index-disp32-r32/legacy"
LOAD8_X = "x86:mov/r32-addr32-base-index-ext-disp8/legacy"
STORE8_X = "x86:mov/addr32-base-index-ext-disp8-r32/legacy"
LOAD32_X = "x86:mov/r32-addr32-base-index-ext-disp32/legacy"
STORE32_X = "x86:mov/addr32-base-index-ext-disp32-r32/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (LOAD8_R, "dest", 8, 0, 1, 0, 8, 6),
    (STORE8_R, "src", 8, 0, 1, 0, 8, 6),
    (LOAD32_R, "dest", 8, 0, 1, 0, 200, 9),
    (STORE32_R, "src", 8, 0, 1, 0, 200, 9),
    (LOAD8_B, "dest", 0, 8, 1, 0, 8, 6),
    (STORE8_B, "src", 0, 8, 1, 0, 8, 6),
    (LOAD32_B, "dest", 0, 8, 1, 0, 200, 9),
    (STORE32_B, "src", 0, 8, 1, 0, 200, 9),
    (LOAD8_X, "dest", 0, 0, 9, 0, 8, 6),
    (STORE8_X, "src", 0, 0, 9, 0, 8, 6),
    (LOAD32_X, "dest", 0, 0, 9, 0, 200, 9),
    (STORE32_X, "src", 0, 0, 9, 0, 200, 9),
    (LOAD8_B, "dest", 0, 12, 1, 0, 8, 6),
    (LOAD8_X, "dest", 0, 0, 12, 0, 8, 6),
    (LOAD8_R, "dest", 8, 5, 1, 0, 8, 6),
    (LOAD8_B, "dest", 0, 8, 1, 3, 8, 6),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p58.py <oracle.bin>")
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
                    "research/evidence/experiments/EXP-0083/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The twelve 0.54.0 rows: one REX bit on the 0x67 address-size mov, "
            "both directions at disp8 and disp32. 0x67 is byte 0 and REX byte "
            "1, so the opcode is byte 2, ModRM byte 3 (register [27,3]) and "
            "SIB byte 4 (base [32,3], index [35,3], scale [38,2]), with the "
            "displacement at [40,8] or [40,32]. REX.R extends the value "
            "register, REX.B the base and REX.X the index; the disp8 rows are "
            "six bytes (67 44 8b 44 08 08) and the disp32 rows are nine. Four "
            "extra instructions cover %r12d as a base (67 41 8b 44 0c 08), "
            "%r12d as an index (67 42 8b 44 20 08), %ebp as a base on the "
            "REX.R row (67 44 8b 44 0d 08) and the x8 scale on the REX.B row "
            "(67 41 8b 44 c8 08). input_sha256 is probe.asm; output_sha256 is "
            "the 114-byte .text."
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
