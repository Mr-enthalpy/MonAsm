#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P43-gpr32-mov-mem-sib-disp8.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0068/fixture.asm`, which is the oracle
input. All eight `0.39.0` rows appear twice, at displacement `8` and `100`, so
both ends of each register window appear: the low rows at `%eax`/`%edi`, the
`REX.R` rows at `%r8d`/`%r15d`. The base is fixed by the `form_id`, so there is
no `base` operand. `expected.bin` is copied from `llvm-objcopy`, never
produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0068/fixture_p43.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P43-gpr32-mov-mem-sib-disp8"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0068/fixture.asm"

VERSION = "0.39.0"
DIGEST = "sha256:08e2fb7afee30bc6bf63f3bd795f88f6dfb4ae100a41e72f2f6491b113a3b1a0"

# (form_id, role, register, disp, size)
PLAN = [
    ("x86:mov/r32-rsp-disp8/legacy", "dest", 0, 8, 4),
    ("x86:mov/r32-rsp-disp8/legacy", "dest", 7, 100, 4),
    ("x86:mov/r32-ext-rsp-disp8/legacy", "dest", 8, 8, 5),
    ("x86:mov/r32-ext-rsp-disp8/legacy", "dest", 15, 100, 5),
    ("x86:mov/rsp-disp8-r32/legacy", "src", 0, 8, 4),
    ("x86:mov/rsp-disp8-r32/legacy", "src", 7, 100, 4),
    ("x86:mov/rsp-disp8-r32-ext/legacy", "src", 8, 8, 5),
    ("x86:mov/rsp-disp8-r32-ext/legacy", "src", 15, 100, 5),
    ("x86:mov/r32-r12-disp8/legacy", "dest", 0, 8, 5),
    ("x86:mov/r32-r12-disp8/legacy", "dest", 7, 100, 5),
    ("x86:mov/r32-ext-r12-disp8/legacy", "dest", 8, 8, 5),
    ("x86:mov/r32-ext-r12-disp8/legacy", "dest", 15, 100, 5),
    ("x86:mov/r12-disp8-r32/legacy", "src", 0, 8, 5),
    ("x86:mov/r12-disp8-r32/legacy", "src", 7, 100, 5),
    ("x86:mov/r12-disp8-r32-ext/legacy", "src", 8, 8, 5),
    ("x86:mov/r12-disp8-r32-ext/legacy", "src", 15, 100, 5),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p43.py <oracle.bin>")
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
                    "research/evidence/experiments/EXP-0068/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "All eight 0.39.0 rows, twice each at displacements 8 and 100, "
            "sixteen instructions and 76 bytes: the unprefixed %rsp rows are "
            "four bytes (8b 44 24 08 / 89 44 24 08), and the REX.B (%r12) "
            "and REX.R rows are five (41/44/45 ...). This is the mod = 01 "
            "SIB shape: ModRM = 44, SIB = 24, and the signed disp8 at "
            "[24,8] or [32,8] behind a REX byte. The base is fixed in the "
            "template, so %rsp and %r12 differ only in REX.B. input_sha256 "
            "is fixture.asm (the source above); output_sha256 is the "
            "76-byte .text."
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
