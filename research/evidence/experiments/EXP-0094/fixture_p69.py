#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P69-gpr16-mov-addr32-abs32.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0094/probe.asm`, which is the oracle input
and the 94-byte vector. The four `0.65.0` rows cover the absolute `SIB = 25`
shape behind `0x67 66` in both directions and both value windows; six corners
follow: a zero displacement, `-1`, both signed ends of `disp32`, `%r15w` as the
load value and `%r15w` as the store value. `expected.bin` is copied from
`llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0094/fixture_p69.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P69-gpr16-mov-addr32-abs32"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0094/probe.asm"

VERSION = "0.65.0"
DIGEST = "sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a"

LOAD = "x86:mov/r16-addr32-abs32/legacy"
STORE = "x86:mov/addr32-abs32-r16/legacy"
LOAD_EXT = "x86:mov/r16-ext-addr32-abs32/legacy"
STORE_EXT = "x86:mov/addr32-abs32-r16-ext/legacy"

# (form_id, role, register, disp, size)
PLAN = [
    (LOAD, "dest", 0, 4660, 9),
    (STORE, "src", 0, 4660, 9),
    (LOAD_EXT, "dest", 8, 4660, 10),
    (STORE_EXT, "src", 8, 4660, 10),
    (LOAD, "dest", 0, 0, 9),
    (LOAD, "dest", 0, -1, 9),
    (LOAD, "dest", 0, 2147483647, 9),
    (LOAD, "dest", 0, -2147483648, 9),
    (LOAD_EXT, "dest", 15, 4660, 10),
    (STORE_EXT, "src", 15, 4660, 10),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p69.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[4] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, reg, disp, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size,
                          "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            operand(role, "x86.gpr16", "r16", {"reg": reg}),
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
                    "research/evidence/experiments/EXP-0094/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The four 0.65.0 rows: the absolute SIB = 25 shape behind 0x67 66 "
            "at the 16-bit value width, in both directions and both value "
            "windows. The bare rows are nine bytes (67 66 at bytes 0-1, opcode "
            "byte 2, ModRM 04 byte 3, SIB 25 byte 4, value [27,3], disp32 at "
            "[40,32]); the REX.R rows are ten, with the REX byte at position 2 "
            "moving every later field eight bits (value [18,1]+[35,3], "
            "disp32 at [48,32]). SIB = 25 is template content, so there is no "
            "base, index or scale role and no REX.B/REX.X bit. The "
            "displacement is four bytes at every value, including zero "
            "(67 66 8b 04 25 00 00 00 00); the signed ends are "
            "67 66 8b 04 25 00 00 00 80 and 67 66 8b 04 25 ff ff ff 7f. "
            "%r15w moves ModRM.reg to 3c (67 66 44 8b 3c 25 34 12 00 00). "
            "input_sha256 is probe.asm; output_sha256 is the 94-byte .text."
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
