#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P41-gpr32-mov-mem-disp8.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0066/fixture.asm`, which is the oracle
input. All six `0.37.0` rows appear twice: the low rows at `%eax`/`%edi` over
`%rax`/`%rsi`, the `REX.R` rows at `%r8d`/`%r15d` over `%rax`/`%r9`, and the
`REX.B` rows at `%eax`/`%edi` over `%r8`/`%r15`. `expected.bin` is copied from
`llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0066/fixture_p41.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P41-gpr32-mov-mem-disp8"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0066/fixture.asm"

VERSION = "0.37.0"
DIGEST = "sha256:1a29805f2f9e58f4d7ab749999c90fa415c29985dae9c5e45a9294ddf25102d6"

# (form_id, role, register, base, disp, size)
PLAN = [
    ("x86:mov/r32-base-disp8/legacy", "dest", 0, 0, 8, 3),
    ("x86:mov/r32-base-disp8/legacy", "dest", 7, 6, 8, 3),
    ("x86:mov/base-disp8-r32/legacy", "src", 0, 0, 8, 3),
    ("x86:mov/base-disp8-r32/legacy", "src", 7, 6, 8, 3),
    ("x86:mov/r32-ext-base-disp8/legacy", "dest", 8, 0, 8, 4),
    ("x86:mov/r32-ext-base-disp8/legacy", "dest", 15, 9, 8, 4),
    ("x86:mov/base-disp8-r32-ext/legacy", "src", 8, 0, 8, 4),
    ("x86:mov/base-disp8-r32-ext/legacy", "src", 15, 9, 8, 4),
    ("x86:mov/r32-base-ext-disp8/legacy", "dest", 0, 8, 8, 4),
    ("x86:mov/r32-base-ext-disp8/legacy", "dest", 7, 15, 8, 4),
    ("x86:mov/base-ext-disp8-r32/legacy", "src", 0, 8, 8, 4),
    ("x86:mov/base-ext-disp8-r32/legacy", "src", 7, 15, 8, 4),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p41.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[5] for entry in PLAN)
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
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": [
                {"role": role, "kind": "x86.gpr32", "target_type": "r32",
                 "payload": {"reg": reg}, "modifiers": []},
                {"role": "base", "kind": "x86.gpr64", "target_type": "rm64",
                 "payload": {"reg": base}, "modifiers": []},
                {"role": "disp", "kind": "x86.imm", "target_type": "disp8",
                 "payload": {"value": disp}, "modifiers": []},
            ],
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
                    "research/evidence/experiments/EXP-0066/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "All six 0.37.0 rows, twice each, twelve instructions and 44 "
            "bytes: the low rows are three bytes (8b 40 08 / 89 40 08), the "
            "REX.R and REX.B rows four (44/45 or 41 ...). This is the "
            "mod = 01 shape, so the ModRM byte is 40 + base and the signed "
            "disp8 follows at [16,8] or [24,8] behind a REX byte. Only "
            "%rsp/%r12 are excluded (SIB); %rbp/%r13 are ordinary bases here "
            "(8b 45 08), unlike at mod = 00. input_sha256 is fixture.asm "
            "(the source above); output_sha256 is the 44-byte .text."
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
