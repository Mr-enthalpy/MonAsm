#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P72-sub-immediates.{fmp.json,
expected.bin}` and its `oracle.json`.

The ten instructions match `EXP-0102/probe.asm`, the oracle input:

| # | source | row | bytes |
|---|---|---|---|
| 1 | `subq $1, %rax` | `rm64-imm8` | `48 83 e8 01` |
| 2 | `subq $127, %rcx` | `rm64-imm8` | `48 83 e9 7f` |
| 3 | `subq $-128, %rax` | `rm64-imm8` | `48 83 e8 80` |
| 4 | `subq $1, %r8` | `rm64-imm8` (REX.B) | `49 83 e8 01` |
| 5 | `subq $300, %rbx` | `rm64-imm32` | `48 81 eb 2c 01 00 00` |
| 6 | `subq $2147483647, %r15` | `rm64-imm32` (REX.B) | `49 81 ef ff ff ff 7f` |
| 7 | `subq $-2147483648, %rdx` | `rm64-imm32` | `48 81 ea 00 00 00 80` |
| 8 | `subq $300, %rax` | `rax-imm32` | `48 2d 2c 01 00 00` |
| 9 | `subq $2147483647, %rax` | `rax-imm32` | `48 2d ff ff ff 7f` |
| 10 | `subq $-2147483648, %rax` | `rax-imm32` | `48 2d 00 00 00 80` |

`expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0102/fixture_p72.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P72-sub-immediates"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0102/probe.asm"

VERSION = "0.66.0"
DIGEST = "sha256:63b3b3a153aa0b5508f2055496efa1c56ac74e56b03d56f56f5c522b6d2e1904"

IMM8 = "x86:sub/rm64-imm8/legacy"
IMM32 = "x86:sub/rm64-imm32/legacy"
RAX = "x86:sub/rax-imm32/legacy"

# (form_id, dest or None, immediate, size)
PLAN = [
    (IMM8, 0, 1, 4),
    (IMM8, 1, 127, 4),
    (IMM8, 0, -128, 4),
    (IMM8, 8, 1, 4),
    (IMM32, 3, 300, 7),
    (IMM32, 15, 2147483647, 7),
    (IMM32, 2, -2147483648, 7),
    (RAX, None, 300, 6),
    (RAX, None, 2147483647, 6),
    (RAX, None, -2147483648, 6),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p72.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[3] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, dest, immediate, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size,
                          "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = []
        if dest is not None:
            operands.append(operand("dest", "x86.gpr64", "rm64",
                                    {"reg": dest}))
        operands.append(operand("imm", "x86.imm", "imm32",
                                {"value": immediate}))
        if form_id == IMM8:
            operands[-1]["target_type"] = "imm8"
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
                    "research/evidence/experiments/EXP-0102/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The three 0.66.0 sub rows: REX.W 83 /5 ib (48 83 e8 01 / "
            "48 83 e8 80 / 49 83 e8 01), REX.W 81 /5 id "
            "(48 81 eb 2c 01 00 00 / 49 81 ef ff ff ff 7f / "
            "48 81 ea 00 00 00 80) and REX.W 2d id "
            "(48 2d 2c 01 00 00 / 48 2d ff ff ff 7f / 48 2d 00 00 00 80). "
            "llvm-mc picks the accumulator for subq $300, %rax, which is "
            "EC-04's counterexample; subq $1, %r8 shows the dest slot's "
            "REX.B bit (49, not 48). input_sha256 is probe.asm; "
            "output_sha256 is the 55-byte .text."
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
