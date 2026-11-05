#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P28-evex-mem-sib-nobase-index.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0053/fixture.asm`, which is the oracle input.
Each width contributes a load and a store, all eleven bytes: `mod = 00` with
`SIB.base = 101` means "no base", so the `disp32` slot is mandatory and there is
no `base` operand. Index, scale and displacement are operands. The fixture uses
all four scale contents (`0`-`3`), index numbers `0`, `1`, `6`, `12`, `13` and
`15` (so both the `SIB` field and `X̄` are exercised), the five-bit EVEX window
at `xmm20`/`xmm21`/`zmm30`/`zmm31`, a negative displacement and the signed
`disp32` end point. `expected.bin` is copied from `llvm-objcopy`, never produced
by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0053/fixture_p28.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P28-evex-mem-sib-nobase-index"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0053/fixture.asm"

VERSION = "0.24.0"
DIGEST = "sha256:2521f2dcc9636c1e3a671bbfbf224dcaecb741014bf65b0660ae5cc1c8c4aca3"

# (form_id, width, role, vector register, index, scale content, displacement)
PLAN = [
    ("x86:vmovaps/xmm-index-disp32/evex", "xmm", "dest", 20, 0, 0, 0),
    ("x86:vmovaps/index-disp32-xmm/evex", "xmm", "src", 21, 12, 2, 4660),
    ("x86:vmovaps/ymm-index-disp32/evex", "ymm", "dest", 8, 13, 3, -4096),
    ("x86:vmovaps/index-disp32-ymm/evex", "ymm", "src", 9, 15, 1, 8192),
    ("x86:vmovaps/zmm-index-disp32/evex", "zmm", "dest", 31, 1, 0, 128),
    ("x86:vmovaps/index-disp32-zmm/evex", "zmm", "src", 30, 6, 1, 2147483647),
]

SIZE = 11


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p28.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = SIZE * len(PLAN)
    if len(PLAN) != 6:
        raise SystemExit("plan is not 6 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, (form_id, width, role, reg, sib_index, scale, disp) in enumerate(
            PLAN, 1):
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": SIZE, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            {"role": role, "kind": "x86.%s" % width, "target_type": width,
             "payload": {"reg": reg}, "modifiers": []},
            {"role": "index", "kind": "x86.gpr64", "target_type": "sib_index",
             "payload": {"reg": sib_index}, "modifiers": []},
            {"role": "imm", "kind": "x86.scale", "target_type": "scale2",
             "payload": {"value": scale}, "modifiers": []},
            {"role": "disp", "kind": "x86.imm", "target_type": "disp32",
             "payload": {"value": disp}, "modifiers": []},
        ]
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": operands,
            "expected_size": SIZE,
        })
        offset += SIZE

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
                    "research/evidence/experiments/EXP-0053/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "Six EVEX vmovaps instructions with an index, a scale and no base, "
            "one per 0.24.0 row, eleven bytes each (66 bytes total). In every "
            "instruction ModRM is 04 (mod 00, r/m 100) and the SIB byte's base "
            "field is the constant 101, which at mod 00 means \"no base, "
            "disp32\"; the displacement slot is therefore present even when its "
            "content is zero (instruction 1). The SIB byte holds the scale at "
            "bits 7-6 and the index at bits 5-3, and the index's fourth bit is "
            "the inverted X-bar in P0 at [14,1] (62 b1 for %r12 as the index, "
            "62 31 for %r13 and %r15). The vector register sits in the five-bit "
            "field at [43,3] plus the inverted R-bar/R-bar-prime bits at "
            "[12,1]/[15,1]. disp32 operands carry bytes: instruction 3 is "
            "-4096 and instruction 6 is the signed end point 2147483647. The "
            "fixture uses all four scale contents (0, 1, 2 and 3) and index "
            "%rax/%rcx/%rsi/%r12/%r13/%r15, so both the three-bit field and "
            "X-bar are exercised. input_sha256 is fixture.asm (the source "
            "above); output_sha256 is the 66-byte .text."
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
