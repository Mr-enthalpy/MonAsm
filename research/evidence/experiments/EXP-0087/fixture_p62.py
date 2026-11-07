#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P62-gpr16-mov-index-addr32-rex-windows.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0087/probe.asm`, which is the oracle input
and the 130-byte vector. The twelve `0.58.0` rows cover the three single-`REX`
windows (`R` value, `B` base, `X` index) in both directions at both
displacement widths, plus four corners: `%r15w` with `%ebp` as a base, `%r15d`
as a base, `%r15d` as an index and the x8 scale. `expected.bin` is copied from
`llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0087/fixture_p62.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P62-gpr16-mov-index-addr32-rex-windows"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0087/probe.asm"

VERSION = "0.58.0"
DIGEST = "sha256:8e7fc7e799ede398cb5d560b2ca43991c11cba518cadae45f84222bbf93994bf"

R_LOAD8 = "x86:mov/r16-ext-addr32-base-index-disp8/legacy"
R_STORE8 = "x86:mov/addr32-base-index-disp8-r16-ext/legacy"
B_LOAD8 = "x86:mov/r16-addr32-base-ext-index-disp8/legacy"
B_STORE8 = "x86:mov/addr32-base-ext-index-disp8-r16/legacy"
X_LOAD8 = "x86:mov/r16-addr32-base-index-ext-disp8/legacy"
X_STORE8 = "x86:mov/addr32-base-index-ext-disp8-r16/legacy"
R_LOAD32 = "x86:mov/r16-ext-addr32-base-index-disp32/legacy"
R_STORE32 = "x86:mov/addr32-base-index-disp32-r16-ext/legacy"
B_LOAD32 = "x86:mov/r16-addr32-base-ext-index-disp32/legacy"
B_STORE32 = "x86:mov/addr32-base-ext-index-disp32-r16/legacy"
X_LOAD32 = "x86:mov/r16-addr32-base-index-ext-disp32/legacy"
X_STORE32 = "x86:mov/addr32-base-index-ext-disp32-r16/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (R_LOAD8, "dest", 8, 0, 1, 0, 8, 7),
    (R_STORE8, "src", 8, 0, 1, 0, 8, 7),
    (B_LOAD8, "dest", 0, 8, 1, 0, 8, 7),
    (B_STORE8, "src", 0, 8, 1, 0, 8, 7),
    (X_LOAD8, "dest", 0, 0, 9, 0, 8, 7),
    (X_STORE8, "src", 0, 0, 9, 0, 8, 7),
    (R_LOAD32, "dest", 8, 0, 1, 0, 200, 10),
    (R_STORE32, "src", 8, 0, 1, 0, 200, 10),
    (B_LOAD32, "dest", 0, 8, 1, 0, 200, 10),
    (B_STORE32, "src", 0, 8, 1, 0, 200, 10),
    (X_LOAD32, "dest", 0, 0, 9, 0, 200, 10),
    (X_STORE32, "src", 0, 0, 9, 0, 200, 10),
    (R_LOAD8, "dest", 15, 5, 1, 0, 8, 7),
    (B_LOAD8, "dest", 2, 15, 5, 0, 8, 7),
    (X_LOAD8, "dest", 2, 0, 15, 0, 8, 7),
    (R_LOAD8, "dest", 15, 0, 1, 3, 8, 7),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p62.py <oracle.bin>")
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
            operand("base", "x86.gpr32", "rm32", {"reg": base}),
            operand("index", "x86.gpr32", "sib_index32", {"reg": sib_index}),
            operand("imm", "x86.scale", "scale2", {"value": scale}),
        ]
        operands.append(
            operand("disp", "x86.imm", "disp%d" % (8 if size == 7 else 32),
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
                    "research/evidence/experiments/EXP-0087/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The twelve 0.58.0 rows: the 0x67 0x66 movw behind the address-size "
            "prefix takes the three single-REX windows (R value, B base, X "
            "index), both directions at disp8 and disp32. 0x67 is byte 0, 0x66 "
            "byte 1, REX byte 2, the opcode byte 3, ModRM byte 4 (value "
            "register [35,3]) and SIB byte 5 (base [40,3], index [43,3], scale "
            "[46,2]), with the displacement at [48,8] or [48,32]. The fixed bit "
            "is R at [18,1], B at [16,1] or X at [17,1]; its slot excludes "
            "0-7. The base and index are 32-bit address registers (%r8d-%r15d) "
            "while the value is %r8w-%r15w. The four extra instructions cover "
            "%r15w with %ebp as a base (67 66 44 8b 7c 0d 08), %r15d as a base "
            "(67 66 41 8b 54 2f 08), %r15d as an index (67 66 42 8b 54 38 08) "
            "and the x8 scale (67 66 44 8b 7c c8 08). input_sha256 is "
            "probe.asm; output_sha256 is the 130-byte .text."
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
