#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P36-gpr8-mov-mem-sib-nodisp.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0061/fixture.asm`, which is the oracle
input. Every one of the fourteen rows appears exactly once: load and store over
the two `SIB` bases (`%rsp` and `%r12`) in the four byte-register windows,
minus the high-byte `%r12` half that `EC-36` forbids. The base is fixed in the
form, so each instruction carries one operand; `SIB = 24` is in the template.
`expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0061/fixture_p36.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P36-gpr8-mov-mem-sib-nodisp"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0061/fixture.asm"

VERSION = "0.32.0"
DIGEST = "sha256:bad81d6655d9e612fa353814fa40ba9910ba3830ac954df2169365abd02563ac"

# (form_id, role, kind, target_type, register, size)
PLAN = [
    ("x86:mov/r8-rsp/legacy", "dest", "x86.gpr8", "r8", 0, 3),
    ("x86:mov/r8-r12/legacy", "dest", "x86.gpr8", "r8", 1, 4),
    ("x86:mov/r8h-rsp/legacy", "dest", "x86.gpr8h", "r8h", 4, 3),
    ("x86:mov/r8-rsp-rex/legacy", "dest", "x86.gpr8", "r8", 7, 4),
    ("x86:mov/r8-r12-rex/legacy", "dest", "x86.gpr8", "r8", 6, 4),
    ("x86:mov/r8-ext-rsp/legacy", "dest", "x86.gpr8", "r8", 8, 4),
    ("x86:mov/r8-ext-r12/legacy", "dest", "x86.gpr8", "r8", 15, 4),
    ("x86:mov/rsp-r8/legacy", "src", "x86.gpr8", "r8", 0, 3),
    ("x86:mov/r12-r8/legacy", "src", "x86.gpr8", "r8", 1, 4),
    ("x86:mov/rsp-r8h/legacy", "src", "x86.gpr8h", "r8h", 7, 3),
    ("x86:mov/rsp-r8-rex/legacy", "src", "x86.gpr8", "r8", 7, 4),
    ("x86:mov/r12-r8-rex/legacy", "src", "x86.gpr8", "r8", 6, 4),
    ("x86:mov/rsp-r8-ext/legacy", "src", "x86.gpr8", "r8", 8, 4),
    ("x86:mov/r12-r8-ext/legacy", "src", "x86.gpr8", "r8", 15, 4),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p36.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[5] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, kind, target_type, reg, size = entry
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
                    "research/evidence/experiments/EXP-0061/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "One byte-width mov per 0.32.0 SIB row, fourteen instructions, 52 "
            "bytes: load and store over %rsp and %r12 in the four register "
            "windows, except %r12 with the high-byte window, which has no "
            "encoding because REX.B renames %ah. The two REX-less %rsp rows "
            "are three bytes (8a 04 24, 8a 24 24, 88 04 24, 88 24 24); every "
            "other row is four, with REX = 40/41/44/45. SIB = 24 is scale = "
            "00, index = 100 (no index) and base = 100; REX.B distinguishes "
            "%rsp from %r12, and both are fixed in the template, so the base "
            "is not an operand (a plan that supplies one is E-OPERAND-002). "
            "The disp8/disp32 twins (8a 44 24 00, 8a 84 24 00 00 00 00) stay "
            "separate rows. input_sha256 is fixture.asm (the source above); "
            "output_sha256 is the 52-byte .text."
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
