#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P25-evex-mem-sib.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0050/fixture.asm`, which is the oracle
input; the sizes are the measured `llvm-mc` encodings (8 bytes for `disp8*N`,
11 for `disp32`). `%rsp` and `%r12` are the same length here: the EVEX prefix
already carries the base's fourth bit as the inverted `B̄` in `P0`, so a `%r12`
base only flips that byte. The `xmm` eight run `xmm0`-`xmm7`, the `ymm` eight
`ymm8`-`ymm15` and the `zmm` eight `zmm16`-`zmm23`, so the fixture pins all
three widths, both bases, both displacement forms and the five-bit EVEX
window. `expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0050/fixture_p25.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P25-evex-mem-sib"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0050/fixture.asm"

VERSION = "0.21.0"
DIGEST = "sha256:30af3fec5c2f50e3ab30fb30d32e6b2e71f4520dbdb2660c6c9de1767b7b1160"

# (form_id, role, register number, target_type, content, size)
PLAN = [
    # xmm: N = 16
    ("x86:vmovaps/xmm-rsp-disp8x16/evex", "dest", 0, "disp8x16", 1, 8),
    ("x86:vmovaps/xmm-r12-disp8x16/evex", "dest", 1, "disp8x16", 1, 8),
    ("x86:vmovaps/xmm-rsp-disp32/evex", "dest", 2, "disp32", 2048, 11),
    ("x86:vmovaps/xmm-r12-disp32/evex", "dest", 3, "disp32", 2048, 11),
    ("x86:vmovaps/rsp-disp8x16-xmm/evex", "src", 4, "disp8x16", 1, 8),
    ("x86:vmovaps/r12-disp8x16-xmm/evex", "src", 5, "disp8x16", 1, 8),
    ("x86:vmovaps/rsp-disp32-xmm/evex", "src", 6, "disp32", 2048, 11),
    ("x86:vmovaps/r12-disp32-xmm/evex", "src", 7, "disp32", 2048, 11),
    # ymm: N = 32
    ("x86:vmovaps/ymm-rsp-disp8x32/evex", "dest", 8, "disp8x32", 1, 8),
    ("x86:vmovaps/ymm-r12-disp8x32/evex", "dest", 9, "disp8x32", 1, 8),
    ("x86:vmovaps/ymm-rsp-disp32/evex", "dest", 10, "disp32", 4096, 11),
    ("x86:vmovaps/ymm-r12-disp32/evex", "dest", 11, "disp32", 4096, 11),
    ("x86:vmovaps/rsp-disp8x32-ymm/evex", "src", 12, "disp8x32", 2, 8),
    ("x86:vmovaps/r12-disp8x32-ymm/evex", "src", 13, "disp8x32", 2, 8),
    ("x86:vmovaps/rsp-disp32-ymm/evex", "src", 14, "disp32", 4096, 11),
    ("x86:vmovaps/r12-disp32-ymm/evex", "src", 15, "disp32", 4096, 11),
    # zmm: N = 64
    ("x86:vmovaps/zmm-rsp-disp8x64/evex", "dest", 16, "disp8x64", 1, 8),
    ("x86:vmovaps/zmm-r12-disp8x64/evex", "dest", 17, "disp8x64", 1, 8),
    ("x86:vmovaps/zmm-rsp-disp32/evex", "dest", 18, "disp32", 8192, 11),
    ("x86:vmovaps/zmm-r12-disp32/evex", "dest", 19, "disp32", 8192, 11),
    ("x86:vmovaps/rsp-disp8x64-zmm/evex", "src", 20, "disp8x64", 2, 8),
    ("x86:vmovaps/r12-disp8x64-zmm/evex", "src", 21, "disp8x64", 2, 8),
    ("x86:vmovaps/rsp-disp32-zmm/evex", "src", 22, "disp32", 8192, 11),
    ("x86:vmovaps/r12-disp32-zmm/evex", "src", 23, "disp32", 8192, 11),
]

WIDTHS = {"xmm": "xmm", "ymm": "ymm", "zmm": "zmm"}


def kind_of(form_id: str) -> str:
    if "/xmm-" in form_id:
        return "xmm"
    if "/ymm-" in form_id:
        return "ymm"
    if "/zmm-" in form_id:
        return "zmm"
    if "-xmm/" in form_id:
        return "xmm"
    if "-ymm/" in form_id:
        return "ymm"
    if "-zmm/" in form_id:
        return "zmm"
    raise SystemExit("cannot read the width from %s" % form_id)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p25.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(item[5] for item in PLAN)
    if len(PLAN) != 24:
        raise SystemExit("plan is not 24 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, (form_id, role, reg, target_type, content, size) in enumerate(
            PLAN, 1):
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
                {"role": role, "kind": "x86.%s" % WIDTHS[width],
                 "target_type": WIDTHS[width],
                 "payload": {"reg": reg}, "modifiers": []},
                {"role": "disp", "kind": "x86.imm",
                 "target_type": target_type,
                 "payload": {"value": content},
                 "modifiers": []},
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
                    "research/evidence/experiments/EXP-0050/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "Twenty-four fixed-base SIB instructions, one per 0.21.0 row. "
            "Instructions 1-8 are the xmm rows (N = 16) and run xmm0-xmm7; "
            "9-16 are the ymm rows (N = 32) and run ymm8-ymm15; 17-24 are the "
            "zmm rows (N = 64) and run zmm16-zmm23. Within each eight the "
            "order is load rsp, load r12, load rsp disp32, load r12 disp32, "
            "store rsp, store r12, store rsp disp32, store r12 disp32. Every "
            "row spends exactly one byte on the SIB byte 24 (scale 00, index "
            "100, base 100); %r12 costs no extra prefix because the base's "
            "fourth bit is already the inverted B-bar in P0 (62 f1 -> 62 d1). "
            "The displacement therefore sits one byte later than on the "
            "corresponding -base-disp rows: bit 56 instead of 48. disp8*N "
            "content is the displacement divided by the width unit: 1 for "
            "16/32/64 and 2 for 64/128 at ymm/zmm width. Length is 8 bytes for "
            "disp8*N and 11 for disp32 on every row. High registers only clear "
            "the inverted R-bar/R-bar-prime bits (62 f1 -> 62 e1 for xmm20, "
            "62 d1 -> 62 41 for zmm30). input_sha256 is fixture.asm (the "
            "source above); output_sha256 is the 228-byte .text."
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
