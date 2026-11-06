#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P51-gpr16-mov-index-ext-window.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0076/probe.asm`, which is the oracle input
and the 90-byte vector. The eight rows are covered in both directions at both
displacement widths: the `-base-ext` rows put the base at `%r8`/`%r15`, and the
`-index-ext` rows put the index at `%r9`/`%r15`, with the register always in
`%ax`/`%di`. `expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0076/fixture_p51.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P51-gpr16-mov-index-ext-window"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0076/probe.asm"

VERSION = "0.47.0"
DIGEST = "sha256:0894646319c6f42071b0fd9d24417e27246a49343144540c80d05e49da7045c3"

LOAD_BASE8 = "x86:mov/r16-base-ext-index-disp8/legacy"
STORE_BASE8 = "x86:mov/base-ext-index-disp8-r16/legacy"
LOAD_INDEX8 = "x86:mov/r16-base-index-ext-disp8/legacy"
STORE_INDEX8 = "x86:mov/base-index-ext-disp8-r16/legacy"
LOAD_BASE32 = "x86:mov/r16-base-ext-index-disp32/legacy"
STORE_BASE32 = "x86:mov/base-ext-index-disp32-r16/legacy"
LOAD_INDEX32 = "x86:mov/r16-base-index-ext-disp32/legacy"
STORE_INDEX32 = "x86:mov/base-index-ext-disp32-r16/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (LOAD_BASE8, "dest", 0, 8, 1, 0, 8, 6),
    (LOAD_BASE8, "dest", 7, 15, 7, 3, 8, 6),
    (LOAD_INDEX8, "dest", 0, 0, 9, 0, 8, 6),
    (LOAD_INDEX8, "dest", 7, 7, 15, 3, 8, 6),
    (STORE_BASE8, "src", 0, 8, 1, 0, 8, 6),
    (STORE_INDEX8, "src", 7, 7, 15, 3, 8, 6),
    (LOAD_BASE32, "dest", 0, 8, 1, 0, 200, 9),
    (LOAD_BASE32, "dest", 7, 15, 7, 3, 200, 9),
    (LOAD_INDEX32, "dest", 0, 0, 9, 0, 200, 9),
    (LOAD_INDEX32, "dest", 7, 7, 15, 3, 200, 9),
    (STORE_BASE32, "src", 0, 8, 1, 0, 200, 9),
    (STORE_INDEX32, "src", 7, 7, 15, 3, 200, 9),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p51.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[7] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, reg, base, sib_index, scale, disp, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            operand(role, "x86.gpr16", "r16", {"reg": reg}),
            operand("base", "x86.gpr64", "rm64", {"reg": base}),
            operand("index", "x86.gpr64", "sib_index", {"reg": sib_index}),
            operand("imm", "x86.scale", "scale2", {"value": scale}),
        ]
        operands.append(
            operand("disp", "x86.imm", "disp%d" % (8 if size == 6 else 32),
                    {"value": disp}))
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
                    "research/evidence/experiments/EXP-0076/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The eight 0.47.0 rows: base-ext and index-ext at disp8 and "
            "disp32, both directions, six instructions per displacement "
            "width. The base-ext rows "
            "put the base at %r8/%r15 (REX.B, REX = 41) and the index at "
            "%rcx/%rdi (the SIB low three bits); the index-ext rows put the "
            "index at %r9/%r15 (REX.X, REX = 42) and the base at %rax/%rdi. "
            "The register stays in %ax/%di, so ModRM.reg is three bits at "
            "[19,3]. The disp8 rows are six bytes (66 41 8b 44 08 08 and "
            "66 41 8b 7c ff 08 for the base window, 66 42 8b 44 08 08 and "
            "66 42 8b 7c ff 08 for the index window) and the disp32 rows are "
            "nine, with the signed disp32 at [32,32]. input_sha256 is "
            "probe.asm; output_sha256 is the 90-byte .text."
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
