#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P73-call-rel32.{fmp.json,
expected.bin}` and its `oracle.json`.

The four instructions match `EXP-0103/probe.asm`, the oracle input:

| # | source | shape | bytes |
|---|---|---|---|
| 1 | `call L1` | local symbol, `pcrel_end`, `resolve_in_place` | `e8 05 00 00 00` |
| 2 | `call ext` | external symbol, `pcrel_end`, `emit_relocation` | `e8 00 00 00 00` |
| 3 | `addq $1, %rax` | the `0.1.0` `add` row that hosts `L1` | `48 83 c0 01` |
| 4 | `call .+130` | literal displacement `125` | `e8 7d 00 00 00` |

`expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0103/fixture_p73.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P73-call-rel32"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0103/probe.asm"

VERSION = "0.67.0"
DIGEST = "sha256:367d76ebf89ee9c1cf51f561b4798eeb0a2000ae3688ee9a52a4c4a9eaea5c9e"

CALL = "x86:call/rel32/legacy"
ADD = "x86:add/rm64-imm8/legacy"


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def rel_target(payload):
    return operand("target", "x86.rel", "rel32", payload)


def fixup(fixup_id, offset, target, mode):
    return {
        "fixup_id": fixup_id,
        "section_id": ".text",
        "offset": offset,
        "field_descriptor": [{"lsb": 8, "width": 32}],
        "target": target,
        "addend": 0,
        "pc_reference_rule": "pcrel_end",
        "value_transform": "identity",
        "range_constraint": {"signed": True, "bits": 32, "align_bits": 0},
        "resolution_mode": mode,
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p73.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    if oracle.stat().st_size != 19:
        raise SystemExit("oracle is %d bytes, expected 19"
                         % oracle.stat().st_size)

    instructions = [
        {
            "instruction_id": "I0001",
            "section_id": ".text",
            "offset": 0,
            "form_id": CALL,
            "operands": [rel_target({"symbol_id": "L1"})],
            "expected_size": 5,
        },
        {
            "instruction_id": "I0002",
            "section_id": ".text",
            "offset": 5,
            "form_id": CALL,
            "operands": [rel_target({})],
            "expected_size": 5,
        },
        {
            "instruction_id": "I0003",
            "section_id": ".text",
            "offset": 10,
            "form_id": ADD,
            "operands": [
                operand("dest", "x86.gpr64", "rm64", {"reg": 0}),
                operand("imm", "x86.imm", "imm8", {"value": 1}),
            ],
            "expected_size": 4,
        },
        {
            "instruction_id": "I0004",
            "section_id": ".text",
            "offset": 14,
            "form_id": CALL,
            "operands": [rel_target({"value": 125})],
            "expected_size": 5,
        },
    ]

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
                "declared_size": 19,
                "fragments": [
                    {"offset": 0, "size": 5, "kind": "instruction",
                     "instruction_id": "I0001"},
                    {"offset": 5, "size": 5, "kind": "instruction",
                     "instruction_id": "I0002"},
                    {"offset": 10, "size": 4, "kind": "instruction",
                     "instruction_id": "I0003"},
                    {"offset": 14, "size": 5, "kind": "instruction",
                     "instruction_id": "I0004"},
                ],
            }
        ],
        "symbols": [
            {"symbol_id": "L1", "name": "L1", "kind": "defined",
             "binding": "local", "section_id": ".text", "offset": 10},
            {"symbol_id": "ext", "name": "ext", "kind": "external",
             "binding": "global"},
        ],
        "instructions": instructions,
        "fixups": [
            fixup("F0001", 0, {"kind": "symbol", "symbol_id": "L1"},
                  "resolve_in_place"),
            fixup("F0002", 5, {"kind": "symbol", "symbol_id": "ext"},
                  "emit_relocation"),
        ],
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
                    "research/evidence/experiments/EXP-0103/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": 19,
        "records": 1,
        "notes": (
            "The 0.67.0 call/rel32 row in three shapes: call L1 resolves in "
            "place (e8 05 00 00 00; L1 is at offset 10 and the instruction "
            "ends at 5), call ext assembles to e8 00 00 00 00 with one "
            "R_X86_64_PLT32 ext -4 record, and call .+130 is the literal "
            "field 125 (e8 7d 00 00 00). The addq is the 0.1.0 row that hosts "
            "L1. input_sha256 is probe.asm; output_sha256 is the 19-byte "
            ".text."
        ),
        "relocation_check": (
            "llvm-readobj --relocations reports one record: "
            "0x6 R_X86_64_PLT32 ext 0xFFFFFFFFFFFFFFFC; the .Ltmp0+130 "
            "literal resolves in place and emits none"
        ),
    }
    oracle_path = FIXTURES / (STEM + ".oracle.json")
    with oracle_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(oracle_document, indent=2) + "\n")

    print("%s: %d instructions, 19 bytes" % (STEM, len(instructions)))
    print("input_sha256  %s" % input_sha)
    print("output_sha256 %s" % output_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
