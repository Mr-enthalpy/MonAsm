#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P31-gpr32-mov-abs32.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0056/fixture.asm`, which is the oracle input.
Both directions appear at a low and an extended register: `%eax`/`%edi` keep
`REX.R = 0` and no `REX` byte at all (seven bytes), while `%r8d`/`%r10d`/`%r15d`
carry `REX = 44` (eight bytes). `ModRM` is `04` and the `SIB` byte is the
constant `25`, so the 32-bit absolute address is the only address operand. The
addresses cover a positive value, `0`, `-1` and the signed end point
`-2147483648`, whose bytes are `00 00 00 80`. `expected.bin` is copied from
`llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0056/fixture_p31.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P31-gpr32-mov-abs32"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0056/fixture.asm"

VERSION = "0.27.0"
DIGEST = "sha256:c51a0a6b1fefd708a8f05303079fc4fd245462a3f4d4d59d4fe3a5d7063430b9"

# (form_id, role, register, absolute address, size)
PLAN = [
    ("x86:mov/r32-abs32/legacy", "dest", 0, 4660, 7),
    ("x86:mov/abs32-r32/legacy", "src", 0, 4660, 7),
    ("x86:mov/r32-ext-abs32/legacy", "dest", 8, -1, 8),
    ("x86:mov/abs32-r32-ext/legacy", "src", 15, 4660, 8),
    ("x86:mov/r32-abs32/legacy", "dest", 7, -2147483648, 7),
    ("x86:mov/abs32-r32-ext/legacy", "src", 10, 0, 8),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p31.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[4] for entry in PLAN)
    if len(PLAN) != 6:
        raise SystemExit("plan is not 6 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, (form_id, role, reg, disp, size) in enumerate(PLAN, 1):
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            {"role": role, "kind": "x86.gpr32", "target_type": "r32",
             "payload": {"reg": reg}, "modifiers": []},
            {"role": "disp", "kind": "x86.imm", "target_type": "disp32",
             "payload": {"value": disp}, "modifiers": []},
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
                    "research/evidence/experiments/EXP-0056/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "Six 32-bit mov instructions with a 32-bit absolute address, one "
            "per 0.27.0 row (three per direction, low and extended windows), "
            "45 bytes total: four seven-byte instructions without a REX byte "
            "and two eight-byte instructions with REX = 44. In every "
            "instruction ModRM is 04 (mod 00, r/m 100) and the SIB byte is the "
            "constant 25: scale 00, index 100 (\"no index\") and base 101 "
            "(\"no base, disp32\"). The low rows carry the register in "
            "ModRM.reg only (%eax is 04, %edi is 3c), so they are seven bytes; "
            "the extended rows set REX.R (%r8d is 04, %r15d is 3c, %r10d is "
            "14) and spend one byte on the prefix, so they are eight. The "
            "address is always four bytes, even for 0, and the field is "
            "signed: -1 is ff ff ff ff and -2147483648 is 00 00 00 80. "
            "movabsl (A1/A3) is a second legal encoding at ten bytes and is "
            "not a row. input_sha256 is fixture.asm (the source above); "
            "output_sha256 is the 45-byte .text."
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
