#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P38-gpr64-mov-mem-sib-nodisp.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0063/fixture.asm`, which is the oracle
input. All four `0.34.0` rows appear twice: load and store over `%rsp` and
`%r12`, each with `%rax` (REX.R = 0) and `%r8` (REX.R = 1), so every REX byte
the templates allow appears (`48`/`4c` under `%rsp`, `49`/`4d` under `%r12`).
The base is fixed in the form, so each instruction carries one operand;
`expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0063/fixture_p38.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P38-gpr64-mov-mem-sib-nodisp"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0063/fixture.asm"

VERSION = "0.34.0"
DIGEST = "sha256:03368b63e89e40d4cc0c58f7b394110e6dcc2e69bd801d469fa8adc505ad117f"

# (form_id, role, register, size)
PLAN = [
    ("x86:mov/r64-rsp/legacy", "dest", 0, 4),
    ("x86:mov/r64-rsp/legacy", "dest", 8, 4),
    ("x86:mov/rsp-r64/legacy", "src", 0, 4),
    ("x86:mov/rsp-r64/legacy", "src", 8, 4),
    ("x86:mov/r64-r12/legacy", "dest", 0, 4),
    ("x86:mov/r64-r12/legacy", "dest", 8, 4),
    ("x86:mov/r12-r64/legacy", "src", 0, 4),
    ("x86:mov/r12-r64/legacy", "src", 8, 4),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p38.py <oracle.bin>")
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
                {"role": role, "kind": "x86.gpr64", "target_type": "r64",
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
                    "research/evidence/experiments/EXP-0063/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "All four 0.34.0 rows, twice each, eight instructions and 32 "
            "bytes: both directions over %rsp and %r12, each with %rax "
            "(REX.R = 0) and %r8 (REX.R = 1). REX.W is a template constant "
            "and REX.B is too -- 48 under %rsp, 49 under %r12 -- so the four "
            "REX bytes are 48/4c/49/4d and REX.R at [2,1] is the only bit the "
            "operand owns. ModRM = 04 (mod = 00, r/m = 100 announces the SIB) "
            "and SIB = 24 (scale = 00, index = 100 meaning none, base = 100) "
            "are template bytes. The base is not an operand, so a base or disp "
            "operand is E-OPERAND-002 and the rows for %rbp/%r13 stay the "
            "RIP-relative or disp8 shapes. input_sha256 is fixture.asm (the "
            "source above); output_sha256 is the 32-byte .text."
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
