#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P34-gpr8-ext-mem.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0059/fixture.asm`, which is the oracle input.
Every one of the twelve rows appears exactly once: load and store in the three
base windows the byte family already has (a plain base, `%rsp` behind the `SIB`
byte, and `%r12` as the same `SIB` byte with `REX.B = 1`), each at disp8 and
disp32. The registers span the four-bit field (`%r8b`, `%r9b`, `%r10b`, `%r11b`,
`%r14b`, `%r15b`), and the second line's base is `%r8`, so the plain-base row
shows `REX = 45` as well as `44`. `expected.bin` is copied from `llvm-objcopy`,
never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0059/fixture_p34.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P34-gpr8-ext-mem"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0059/fixture.asm"

VERSION = "0.30.0"
DIGEST = "sha256:5dae4541162884f14dfbebd7aaf38a49d4212f0e24155137391e6e0bf93c3cf2"

# (form_id, role, register, base or None, displacement, size)
PLAN = [
    ("x86:mov/r8-ext-base-disp8/legacy", "dest", 8, 0, 8, 4),
    ("x86:mov/r8-ext-base-disp32/legacy", "dest", 15, 8, 200, 7),
    ("x86:mov/r8-ext-rsp-disp8/legacy", "dest", 9, None, 8, 5),
    ("x86:mov/r8-ext-rsp-disp32/legacy", "dest", 14, None, 200, 8),
    ("x86:mov/r8-ext-r12-disp8/legacy", "dest", 10, None, 8, 5),
    ("x86:mov/r8-ext-r12-disp32/legacy", "dest", 11, None, 200, 8),
    ("x86:mov/base-disp8-r8-ext/legacy", "src", 8, 0, 8, 4),
    ("x86:mov/base-disp32-r8-ext/legacy", "src", 15, 8, 200, 7),
    ("x86:mov/rsp-disp8-r8-ext/legacy", "src", 9, None, 8, 5),
    ("x86:mov/rsp-disp32-r8-ext/legacy", "src", 14, None, 200, 8),
    ("x86:mov/r12-disp8-r8-ext/legacy", "src", 10, None, 8, 5),
    ("x86:mov/r12-disp32-r8-ext/legacy", "src", 11, None, 200, 8),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p34.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[5] for entry in PLAN)
    if len(PLAN) != 12:
        raise SystemExit("plan is not 12 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, reg, base, disp, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            {"role": role, "kind": "x86.gpr8", "target_type": "r8",
             "payload": {"reg": reg}, "modifiers": []},
        ]
        if base is not None:
            operands.append({"role": "base", "kind": "x86.gpr64",
                             "target_type": "rm64", "payload": {"reg": base},
                             "modifiers": []})
        bits = 8 if size in (4, 5) else 32
        operands.append({"role": "disp", "kind": "x86.imm",
                         "target_type": "disp%d" % bits,
                         "payload": {"value": disp}, "modifiers": []})
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
                    "research/evidence/experiments/EXP-0059/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "One byte-width mov per 0.30.0 row, twelve instructions, 74 bytes: "
            "load and store for the plain base, %rsp and %r12 windows, each at "
            "disp8 and disp32. Every row carries REX.R = 1 (the register's "
            "fourth bit); REX = 44 when REX.B = 0 and REX = 45 when the base is "
            "%r8-%r15. The plain-base rows put the base in ModRM.rm with "
            "mod = 01 and a displacement byte, %rsp is ModRM.r/m = 100 with "
            "SIB = 24, and %r12 is the same SIB byte with REX.B = 1. The "
            "register is ModRM.reg: %r8b is 000, %r15b is 111, %r14b is 110, "
            "%r11b is 011. Displacements are 8 and 200, and the disp8/disp32 "
            "choice is the row's target type, never the value. The mod = 00 "
            "no-displacement shape (44 8a 00) is a third legal encoding that no "
            "byte row carries, and movabsb (A0/A2) is a fourth. input_sha256 is "
            "fixture.asm (the source above); output_sha256 is the 74-byte "
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
