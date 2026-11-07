#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P65-gpr32-mov-index-addr32-no-base.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0090/probe.asm`, which is the oracle input
and the 112-byte vector. The eight `0.61.0` rows cover the no-base indexed
shape (`SIB.base = 101`, `disp32` only) at the 32-bit value width in both
directions across the four `REX` windows (`none`, `R` value, `X` index, `RX`
both), plus five corners: a zero displacement, a negative displacement, the
x4 scale, `%r12d` as the index under `REX.X`, and `4660(,%r15d,8), %r15d`.
`expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0090/fixture_p65.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P65-gpr32-mov-index-addr32-no-base"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0090/probe.asm"

VERSION = "0.61.0"
DIGEST = "sha256:e5a57fc7f72d810283980e1c059ff4195b77b1bc3c5ff30ff830798d7dd91983"

LOW_LOAD = "x86:mov/r32-addr32-index-disp32/legacy"
LOW_STORE = "x86:mov/addr32-index-disp32-r32/legacy"
R_LOAD = "x86:mov/r32-ext-addr32-index-disp32/legacy"
R_STORE = "x86:mov/addr32-index-disp32-r32-ext/legacy"
X_LOAD = "x86:mov/r32-addr32-index-ext-disp32/legacy"
X_STORE = "x86:mov/addr32-index-ext-disp32-r32/legacy"
RX_LOAD = "x86:mov/r32-ext-addr32-index-ext-disp32/legacy"
RX_STORE = "x86:mov/addr32-index-ext-disp32-r32-ext/legacy"

# (form_id, role, register, index, scale, disp, size)
PLAN = [
    (LOW_LOAD, "dest", 0, 1, 0, 8, 8),
    (LOW_STORE, "src", 0, 1, 0, 8, 8),
    (R_LOAD, "dest", 8, 1, 0, 8, 9),
    (R_STORE, "src", 8, 1, 0, 8, 9),
    (X_LOAD, "dest", 0, 9, 0, 8, 9),
    (X_STORE, "src", 0, 9, 0, 8, 9),
    (RX_LOAD, "dest", 8, 9, 0, 8, 9),
    (RX_STORE, "src", 8, 9, 0, 8, 9),
    (LOW_LOAD, "dest", 0, 1, 0, 0, 8),
    (LOW_LOAD, "dest", 0, 1, 0, -8, 8),
    (LOW_LOAD, "dest", 0, 1, 2, 8, 8),
    (X_LOAD, "dest", 0, 12, 0, 8, 9),
    (RX_LOAD, "dest", 15, 15, 3, 4660, 9),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p65.py <oracle.bin>")
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
            operand(role, "x86.gpr32", "r32", {"reg": reg}),
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
                    "research/evidence/experiments/EXP-0090/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The eight 0.61.0 rows: the 0x67 movl no-base indexed shape "
            "(ModRM 04, SIB.base 101, disp32 mandatory) across the four REX "
            "windows (none, 44 value, 42 index, 46 both), both directions, "
            "plus five corners: zero displacement, -8, the x4 scale (SIB 8d), "
            "%r12d as the index under REX.X (67 42 8b 04 25 08 00 00 00) "
            "and 4660(,%r15d,8), %r15d (67 46 8b 3c fd 34 12 00 00). "
            "0x67 is byte 0, REX byte 1 when present, the opcode byte 1 or 2, "
            "ModRM 04 and SIB at byte 3 or 4; without REX the value is "
            "[19,3], the index [27,3], the scale [30,2] and the displacement "
            "[32,32], and the REX byte moves each eight bits "
            "([27,3]/[35,3]/[38,2]/[40,32]). There is no base slot, so no "
            "REX.B bit exists. input_sha256 is probe.asm; output_sha256 is "
            "the 112-byte .text."
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
