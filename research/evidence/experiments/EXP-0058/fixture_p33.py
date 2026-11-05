#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P33-gpr8-mov-abs32.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0058/fixture.asm`, which is the oracle input.
Every one of the eight rows appears exactly once, so both directions are covered
in each of the four byte-register windows: the low `%al`-`%bl` window and the
high `%ah`-`%bh` window are seven bytes with no `REX` byte, while the
`REX = 40` window (`%spl`-`%dil`) and the `REX = 44` window (`%r8b`-`%r15b`)
are eight. `ModRM.reg` carries the register in all four; `ModRM` is `04`
(`reg = 000`) or `24`/`34`/`3c` and the `SIB` byte is the constant `25`, so the
32-bit absolute address is the only address operand. The addresses cover
`0x1234`, `0`, `-1`, `127`, `-32768`, `2147483647` (the signed end point) and a
repeated `0x1234`. `expected.bin` is copied from `llvm-objcopy`, never produced
by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0058/fixture_p33.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P33-gpr8-mov-abs32"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0058/fixture.asm"

VERSION = "0.29.0"
DIGEST = "sha256:cf78fac0b9c9b9828e74559bec9f612b609468ea2894c94c6e3e5b131c3951e6"

# (form_id, role, kind, target_type, register, absolute address, size)
PLAN = [
    ("x86:mov/r8-abs32/legacy", "dest", "x86.gpr8", "r8", 0, 4660, 7),
    ("x86:mov/abs32-r8/legacy", "src", "x86.gpr8", "r8", 3, 0, 7),
    ("x86:mov/r8h-abs32/legacy", "dest", "x86.gpr8h", "r8h", 4, 4660, 7),
    ("x86:mov/abs32-r8h/legacy", "src", "x86.gpr8h", "r8h", 6, -1, 7),
    ("x86:mov/r8-rex-abs32/legacy", "dest", "x86.gpr8", "r8", 4, 127, 8),
    ("x86:mov/abs32-r8-rex/legacy", "src", "x86.gpr8", "r8", 7, -32768, 8),
    ("x86:mov/r8-ext-abs32/legacy", "dest", "x86.gpr8", "r8", 8,
     2147483647, 8),
    ("x86:mov/abs32-r8-ext/legacy", "src", "x86.gpr8", "r8", 15, 4660, 8),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p33.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[6] for entry in PLAN)
    if len(PLAN) != 8:
        raise SystemExit("plan is not 8 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, kind, target_type, reg, disp, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            {"role": role, "kind": kind, "target_type": target_type,
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
                    "research/evidence/experiments/EXP-0058/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "One 8-bit mov per 0.29.0 row, eight instructions, 60 bytes: four "
            "seven-byte instructions with no REX byte (the low %al-%bl window "
            "and the high %ah-%bh window) and four eight-byte instructions "
            "with a REX byte (REX = 40 for %spl-%dil and REX = 44 for "
            "%r8b-%r15b). Every row is opcode 8a (load) or 88 (store), ModRM "
            "mod 00 r/m 100 and the constant SIB byte 25: scale 00, index 100 "
            "(\"no index\") and base 101 (\"no base, disp32\"). ModRM.reg "
            "carries the register: %al is 04, %bl is 1c, %ah is 24, %dh is 34, "
            "%spl is 24 under REX = 40, %dil is 3c, %r8b is 04 under REX = 44 "
            "and %r15b is 3c. The address is always four bytes, even for 0, "
            "and the field is signed: -1 is ff ff ff ff, -32768 is 00 80 ff ff "
            "and 2147483647 is ff ff ff 7f. movabsb (A0/A2) is a second legal "
            "encoding at nine bytes and is not a row. input_sha256 is "
            "fixture.asm (the source above); output_sha256 is the 60-byte "
            ".text."
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
