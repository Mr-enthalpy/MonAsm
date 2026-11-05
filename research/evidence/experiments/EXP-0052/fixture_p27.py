#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P27-evex-mem-sib-index.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0052/fixture.asm`, which is the oracle
input. Each width contributes six instructions: load and store at each of the
three displacement shapes (none, `disp8*N`, `disp32`), so the sizes per width
are 7, 8, 11, 7, 8, 11. Base, index and scale are operands; the `SIB` byte and
the `ModRM` escape are template. The `xmm` six run `xmm20`-`xmm25`, the `ymm`
six `ymm9`-`ymm15`, the `zmm` six `zmm26`-`zmm31`, so the fixture pins the
five-bit EVEX window as well as all three scales and both the low and the
high `SIB` base windows. `expected.bin` is copied from `llvm-objcopy`, never
produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0052/fixture_p27.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P27-evex-mem-sib-index"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0052/fixture.asm"

VERSION = "0.23.0"
DIGEST = "sha256:507e55c84cc80cf8bd9be10a6c6e4f7cff4999084fb41b3138df60b68a283962"

# (form_id, width, role, vector register, base, index, scale content,
#  displacement field content, size). The `disp8*N` value is the field content
#  (byte offset / N), never the byte offset; `disp32` is the byte value.
PLAN = [
    # xmm
    ("x86:vmovaps/xmm-base-index/evex", "xmm", "dest", 20, 4, 0, 0, None, 7),
    ("x86:vmovaps/xmm-base-index-disp8x16/evex", "xmm", "dest", 21, 4, 12, 1, 2, 8),
    ("x86:vmovaps/xmm-base-index-disp32/evex", "xmm", "dest", 22, 12, 9, 2, -4096, 11),
    ("x86:vmovaps/base-index-xmm/evex", "xmm", "src", 23, 12, 15, 3, None, 7),
    ("x86:vmovaps/base-index-disp8x16-xmm/evex", "xmm", "src", 24, 4, 13, 0, -1, 8),
    ("x86:vmovaps/base-index-disp32-xmm/evex", "xmm", "src", 25, 4, 0, 0, 2048, 11),
    # ymm
    ("x86:vmovaps/ymm-base-index/evex", "ymm", "dest", 9, 8, 12, 0, None, 7),
    ("x86:vmovaps/ymm-base-index-disp8x32/evex", "ymm", "dest", 10, 12, 12, 1, 2, 8),
    ("x86:vmovaps/ymm-base-index-disp32/evex", "ymm", "dest", 12, 0, 1, 0, 8, 11),
    ("x86:vmovaps/base-index-ymm/evex", "ymm", "src", 13, 4, 2, 2, None, 7),
    ("x86:vmovaps/base-index-disp8x32-ymm/evex", "ymm", "src", 14, 12, 12, 3, -1, 8),
    ("x86:vmovaps/base-index-disp32-ymm/evex", "ymm", "src", 15, 5, 0, 0, 4096, 11),
    # zmm
    ("x86:vmovaps/zmm-base-index/evex", "zmm", "dest", 31, 12, 12, 3, None, 7),
    ("x86:vmovaps/zmm-base-index-disp8x64/evex", "zmm", "dest", 30, 4, 13, 0, 2, 8),
    ("x86:vmovaps/zmm-base-index-disp32/evex", "zmm", "dest", 29, 0, 1, 0, 8192, 11),
    ("x86:vmovaps/base-index-zmm/evex", "zmm", "src", 28, 4, 12, 0, None, 7),
    ("x86:vmovaps/base-index-disp8x64-zmm/evex", "zmm", "src", 27, 0, 1, 0, -128, 8),
    ("x86:vmovaps/base-index-disp32-zmm/evex", "zmm", "src", 26, 4, 0, 3, 8192, 11),
]

COMPRESSED = {"xmm": "disp8x16", "ymm": "disp8x32", "zmm": "disp8x64"}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p27.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(item[8] for item in PLAN)
    if len(PLAN) != 18:
        raise SystemExit("plan is not 18 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, (form_id, width, role, reg, base, sib_index, scale, disp,
                size) in enumerate(PLAN, 1):
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            {"role": role, "kind": "x86.%s" % width, "target_type": width,
             "payload": {"reg": reg}, "modifiers": []},
            {"role": "base", "kind": "x86.gpr64", "target_type": "rm64",
             "payload": {"reg": base}, "modifiers": []},
            {"role": "index", "kind": "x86.gpr64", "target_type": "sib_index",
             "payload": {"reg": sib_index}, "modifiers": []},
            {"role": "imm", "kind": "x86.scale", "target_type": "scale2",
             "payload": {"value": scale}, "modifiers": []},
        ]
        if size == 7:
            disp_kind = None
        elif size == 8:
            disp_kind = COMPRESSED[width]
        else:
            disp_kind = "disp32"
        if disp_kind is not None:
            operands.append({"role": "disp", "kind": "x86.imm",
                             "target_type": disp_kind,
                             "payload": {"value": disp}, "modifiers": []})
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
                    "research/evidence/experiments/EXP-0052/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "Eighteen EVEX vmovaps instructions with an index and a scale, one "
            "per 0.23.0 row. Each width contributes six: load and store at "
            "mod=00 (no displacement, 7 bytes), disp8*N (8 bytes) and disp32 "
            "(11 bytes), so the sizes per width are 7, 8, 11, 7, 8, 11 and "
            "the fixture is 156 bytes. The xmm six run xmm20-xmm25, the ymm "
            "six ymm9-ymm15, the zmm six zmm26-zmm31. In every row ModRM is "
            "04/44/84 (mod 00/01/10, reg 0, r/m 100), the next byte is the "
            "SIB byte (scale at bits 7-6, index at 5-3, base at 2-0), and the "
            "displacement follows only on the 44/84 rows. A disp8*N operand "
            "carries the field content, not the byte offset: instruction 2 is "
            "32(%rsp,%r12,2) but its plan value is 2, and instruction 17 is "
            "-8192(%rax,%rcx,1) with plan value -128; disp32 operands carry "
            "bytes. The base's fourth "
            "bit is the inverted B-bar in P0 at [13,1] (62 f1 with %rsp, 62 "
            "d1 with %r12), the index's fourth bit is the inverted X-bar at "
            "[14,1] (62 b1 with a high index such as %r12/%r13), and the "
            "vector register sits in the five-bit field at [43,3] plus the "
            "inverted R-bar/R-bar-prime bits at [12,1]/[15,1]. A displacement "
            "that is not a multiple of N promotes to disp32 (instruction 9 is "
            "8(%rax,%rcx,1) at ymm, so N=32 and the row is 11 bytes). The "
            "fixture uses all four scale contents (0, 1, 2 and 3), base %rsp, "
            "%rbp, %r8 and %r12, and index %rax/%rcx/%rdx/%r9/%r12/%r13/%r15. "
            "input_sha256 is fixture.asm (the source above); output_sha256 is "
            "the 156-byte .text."
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
