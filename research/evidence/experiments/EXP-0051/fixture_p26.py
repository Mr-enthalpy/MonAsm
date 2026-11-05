#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P26-evex-mem-sib-nodisp.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0051/fixture.asm`, which is the oracle
input; every row is seven bytes because `mod = 00` with `r/m = 100` spends
`ModRM` `04` and `SIB` `24` and no displacement at all. `%rsp` and `%r12` are
the same length: the EVEX prefix already carries the base's fourth bit as the
inverted `B-bar` in `P0`, so a `%r12` base only flips that byte. The `xmm`
four run `xmm0`-`xmm3`, the `ymm` four `ymm8`-`ymm11` and the `zmm` four
`zmm16`-`zmm19`, so the fixture pins all three widths, both bases and the
five-bit EVEX window. `expected.bin` is copied from `llvm-objcopy`, never
produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0051/fixture_p26.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P26-evex-mem-sib-nodisp"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0051/fixture.asm"

VERSION = "0.22.0"
DIGEST = "sha256:61c7cd1c940a7b22838a2c3418ba54031a20c6b227203fb9b4a57875f1c36b58"

# (form_id, role, register number, size)
PLAN = [
    # xmm
    ("x86:vmovaps/xmm-rsp/evex", "dest", 0, 7),
    ("x86:vmovaps/xmm-r12/evex", "dest", 1, 7),
    ("x86:vmovaps/rsp-xmm/evex", "src", 2, 7),
    ("x86:vmovaps/r12-xmm/evex", "src", 3, 7),
    # ymm
    ("x86:vmovaps/ymm-rsp/evex", "dest", 8, 7),
    ("x86:vmovaps/ymm-r12/evex", "dest", 9, 7),
    ("x86:vmovaps/rsp-ymm/evex", "src", 10, 7),
    ("x86:vmovaps/r12-ymm/evex", "src", 11, 7),
    # zmm
    ("x86:vmovaps/zmm-rsp/evex", "dest", 16, 7),
    ("x86:vmovaps/zmm-r12/evex", "dest", 17, 7),
    ("x86:vmovaps/rsp-zmm/evex", "src", 18, 7),
    ("x86:vmovaps/r12-zmm/evex", "src", 19, 7),
]


def kind_of(form_id: str) -> str:
    for width in ("xmm", "ymm", "zmm"):
        if form_id.startswith("x86:vmovaps/%s-" % width):
            return width
        if form_id.endswith("-%s/evex" % width):
            return width
    raise SystemExit("cannot read the width from %s" % form_id)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p26.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(item[3] for item in PLAN)
    if len(PLAN) != 12:
        raise SystemExit("plan is not 12 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, (form_id, role, reg, size) in enumerate(PLAN, 1):
        instruction_id = "I%04d" % index
        width = kind_of(form_id)
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": [
                {"role": role, "kind": "x86.%s" % width,
                 "target_type": width,
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
                    "research/evidence/experiments/EXP-0051/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "Twelve fixed-base mod=00 SIB instructions, one per 0.22.0 row. "
            "Instructions 1-4 are the xmm rows and run xmm0-xmm3; 5-8 are the "
            "ymm rows and run ymm8-ymm11; 9-12 are the zmm rows and run "
            "zmm16-zmm19. Within each four the order is load rsp, load r12, "
            "store rsp, store r12. Every row is seven bytes: `62 P0 7c P2 "
            "28/29 04 24`, where ModRM 04 is mod=00/reg=0/rm=100 and SIB 24 is "
            "scale 00, index 100, base 100, with no displacement at all. %r12 "
            "costs no extra prefix byte because the base's fourth bit is "
            "already the inverted B-bar in P0 (62 f1 -> 62 d1). The vector "
            "register sits in the five-bit EVEX field at [43,3] plus the "
            "inverted R-bar/R-bar-prime bits at [12,1]/[15,1]; high registers "
            "only clear those bits (62 f1 -> 62 71 for ymm8 over %rsp, and "
            "62 d1 -> 62 c1 for zmm17 over %r12). llvm-mc canonicalizes "
            "0(%rsp) to (%rsp), so the "
            "no-displacement shape is the only encoding of a zero offset. "
            "input_sha256 is fixture.asm (the source above); output_sha256 is "
            "the 84-byte .text."
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
