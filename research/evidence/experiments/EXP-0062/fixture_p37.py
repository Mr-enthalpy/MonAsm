#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P37-gpr64-mov-mem-nodisp.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0062/fixture.asm`, which is the oracle
input. Both `0.33.0` rows appear three times each: load and store over `%rax`
(`REX.R = 0`, `REX.B = 0`), over `%r8` (both set), and over `%r9` with `%r15`
(the top of both four-bit fields). Every instruction carries the register and
the base operand; `REX.W` is in the template. `expected.bin` is copied from
`llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0062/fixture_p37.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P37-gpr64-mov-mem-nodisp"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0062/fixture.asm"

VERSION = "0.33.0"
DIGEST = "sha256:b6659c62116dab7bf79f6c9704844d0fd9a1ad27ac8780e2071a93cf28dd6d8e"

# (form_id, role, kind, target_type, register, base, size)
PLAN = [
    ("x86:mov/r64-base/legacy", "dest", "x86.gpr64", "r64", 0, 0, 3),
    ("x86:mov/r64-base/legacy", "dest", "x86.gpr64", "r64", 8, 8, 3),
    ("x86:mov/r64-base/legacy", "dest", "x86.gpr64", "r64", 15, 9, 3),
    ("x86:mov/base-r64/legacy", "src", "x86.gpr64", "r64", 0, 0, 3),
    ("x86:mov/base-r64/legacy", "src", "x86.gpr64", "r64", 8, 8, 3),
    ("x86:mov/base-r64/legacy", "src", "x86.gpr64", "r64", 15, 9, 3),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p37.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[6] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, kind, target_type, reg, base, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": [
                {"role": role, "kind": kind, "target_type": target_type,
                 "payload": {"reg": reg}, "modifiers": []},
                {"role": "base", "kind": "x86.gpr64",
                 "target_type": "rm64", "payload": {"reg": base},
                 "modifiers": []},
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
                    "research/evidence/experiments/EXP-0062/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "One 64-bit mov per 0.33.0 row, six instructions, 18 bytes: both "
            "directions over %rax (48 8b 00 / 48 89 00), over %r8 with both "
            "extension bits set (4d 8b 00 / 4d 89 00), and over %r9 with %r15 "
            "at the top of both four-bit fields (4d 8b 39 / 4d 89 39). REX.W "
            "is a template constant (48); REX.R carries the register's fourth "
            "bit at [2,1] and REX.B the base's at [0,1]. The base slot "
            "excludes %rsp/%r12 (SIB byte) and %rbp/%r13 (RIP-relative at "
            "r/m = 101), so a plan that names one of them is E-RANGE-004 and "
            "the rows for those four bases are separate forms. There is no "
            "disp slot, so a displacement operand is E-OPERAND-002. "
            "input_sha256 is fixture.asm (the source above); output_sha256 is "
            "the 18-byte .text."
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
