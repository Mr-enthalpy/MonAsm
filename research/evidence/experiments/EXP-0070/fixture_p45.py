#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P45-gpr16-mov-mem-nodisp.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0070/fixture.asm`, which is the oracle
input. The four plain-base rows appear twice, at `%rax`/`%rdi` and
`%r8`/`%r15`, so both ends of each base window appear; the four fixed-base
rows appear once each, because the base is part of the form. `expected.bin` is
copied from `llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0070/fixture_p45.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P45-gpr16-mov-mem-nodisp"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0070/fixture.asm"

VERSION = "0.41.0"
DIGEST = "sha256:a2c5fa28122f43ce824ee637017dd6fdaef4e7455122b5cfa0e065c3400ffaef"

# (form_id, role, register, base, size)
PLAN = [
    ("x86:mov/r16-base/legacy", "dest", 0, 0, 3),
    ("x86:mov/r16-base/legacy", "dest", 0, 7, 3),
    ("x86:mov/r16-base-ext/legacy", "dest", 0, 8, 4),
    ("x86:mov/r16-base-ext/legacy", "dest", 0, 15, 4),
    ("x86:mov/base-r16/legacy", "src", 0, 0, 3),
    ("x86:mov/base-r16/legacy", "src", 0, 7, 3),
    ("x86:mov/base-ext-r16/legacy", "src", 0, 8, 4),
    ("x86:mov/base-ext-r16/legacy", "src", 0, 15, 4),
    ("x86:mov/r16-rsp/legacy", "dest", 0, None, 4),
    ("x86:mov/rsp-r16/legacy", "src", 0, None, 4),
    ("x86:mov/r16-r12/legacy", "dest", 0, None, 5),
    ("x86:mov/r12-r16/legacy", "src", 0, None, 5),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p45.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[4] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, reg, base, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            {"role": role, "kind": "x86.gpr16", "target_type": "r16",
             "payload": {"reg": reg}, "modifiers": []},
        ]
        if base is not None:
            operands.append(
                {"role": "base", "kind": "x86.gpr64", "target_type": "rm64",
                 "payload": {"reg": base}, "modifiers": []})
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
                    "research/evidence/experiments/EXP-0070/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "All eight 0.41.0 rows: the four plain-base rows twice (at "
            "%rax/%rdi and %r8/%r15) and the four fixed %rsp/%r12 rows once "
            "each, twelve instructions and 46 bytes. This is the mod = 00 "
            "shape with the 0x66 operand-size prefix before REX: the two-byte "
            "prefix rows are 66 8b 00 (three bytes) and the REX.B rows are "
            "66 41 8b 00 (four), while the %rsp row is 66 8b 04 24 (four) and "
            "the %r12 row is 66 41 8b 04 24 (five). There is no displacement "
            "and no displacement slot. input_sha256 is fixture.asm (the "
            "source above); output_sha256 is the 46-byte .text."
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
