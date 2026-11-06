#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P40-gpr32-mov-mem-sib-nodisp.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0065/fixture.asm`, which is the oracle
input. All eight `0.36.0` rows appear twice: each base, direction and register
window at both ends, so `%eax`/`%edi` cover the low rows and `%r8d`/`%r15d`
the `-ext` rows. `expected.bin` is copied from `llvm-objcopy`, never produced
by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0065/fixture_p40.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P40-gpr32-mov-mem-sib-nodisp"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0065/fixture.asm"

VERSION = "0.36.0"
DIGEST = "sha256:c4a61297e71ed19a79c0f01fb7495832ee447a1448a3b9071e1477eaeb70892f"

# (form_id, role, register, size)
PLAN = [
    ("x86:mov/r32-rsp/legacy", "dest", 0, 3),
    ("x86:mov/r32-rsp/legacy", "dest", 7, 3),
    ("x86:mov/rsp-r32/legacy", "src", 0, 3),
    ("x86:mov/rsp-r32/legacy", "src", 7, 3),
    ("x86:mov/r32-r12/legacy", "dest", 0, 4),
    ("x86:mov/r32-r12/legacy", "dest", 7, 4),
    ("x86:mov/r12-r32/legacy", "src", 0, 4),
    ("x86:mov/r12-r32/legacy", "src", 7, 4),
    ("x86:mov/r32-ext-rsp/legacy", "dest", 8, 4),
    ("x86:mov/r32-ext-rsp/legacy", "dest", 15, 4),
    ("x86:mov/rsp-r32-ext/legacy", "src", 8, 4),
    ("x86:mov/rsp-r32-ext/legacy", "src", 15, 4),
    ("x86:mov/r32-ext-r12/legacy", "dest", 8, 4),
    ("x86:mov/r32-ext-r12/legacy", "dest", 15, 4),
    ("x86:mov/r12-r32-ext/legacy", "src", 8, 4),
    ("x86:mov/r12-r32-ext/legacy", "src", 15, 4),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p40.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[3] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, reg, size = entry
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
                    "research/evidence/experiments/EXP-0065/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "All eight 0.36.0 rows, twice each, sixteen instructions and 60 "
            "bytes: the %rsp low rows are three bytes (8b 04 24 / 89 04 24), "
            "every %r12 row and every -ext row is four (41/44/45 ...). The "
            "base is template content -- ModRM = 04 and SIB = 24 -- because "
            "%rsp and %r12 share the low three bits 100 and the REX.B byte is "
            "the only bit that tells them apart; each row fixes its base and "
            "the register windows are disjoint (the -ext rows exclude 0-7). "
            "%rbp/%r13 stay on the zero-displacement shape (r/m = 101 at "
            "mod = 00 is RIP-relative). input_sha256 is fixture.asm (the "
            "source above); output_sha256 is the 60-byte .text."
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
