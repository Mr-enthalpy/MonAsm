#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P29-evex-mem-sib-absolute.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0054/fixture.asm`, which is the oracle input.
Each width contributes a load and a store, all eleven bytes: `ModRM` is `04` and
the `SIB` byte is the constant `25` (`index = 100`, `base = 101`), so the only
operand besides the vector is the 32-bit absolute address. The fixture uses the
five-bit EVEX window at `xmm20`/`xmm21` and `zmm30`/`zmm31`, a positive address,
a negative address, the signed `disp32` end point `-2147483648`, and the value
`0x7fff` that would fit a `disp8` but is still written in four bytes.
`expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0054/fixture_p29.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P29-evex-mem-sib-absolute"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0054/fixture.asm"

VERSION = "0.25.0"
DIGEST = "sha256:b72c0b08d30e9bbfd0c5129e01e1cecf77abcde36e2928aab2f94bb80c06a51c"

# (form_id, width, role, vector register, absolute address)
PLAN = [
    ("x86:vmovaps/xmm-abs32/evex", "xmm", "dest", 20, 4660),
    ("x86:vmovaps/abs32-xmm/evex", "xmm", "src", 21, -4096),
    ("x86:vmovaps/ymm-abs32/evex", "ymm", "dest", 8, 4096),
    ("x86:vmovaps/abs32-ymm/evex", "ymm", "src", 9, 32767),
    ("x86:vmovaps/zmm-abs32/evex", "zmm", "dest", 31, -1),
    ("x86:vmovaps/abs32-zmm/evex", "zmm", "src", 30, -2147483648),
]

SIZE = 11


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p29.py <oracle.bin>")
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
    for index, (form_id, width, role, reg, disp) in enumerate(PLAN, 1):
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": SIZE, "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            {"role": role, "kind": "x86.%s" % width, "target_type": width,
             "payload": {"reg": reg}, "modifiers": []},
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
                    "research/evidence/experiments/EXP-0054/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "Six EVEX vmovaps instructions with a 32-bit absolute address, one "
            "per 0.25.0 row, eleven bytes each (66 bytes total). In every "
            "instruction ModRM is 04 (mod 00, r/m 100) and the SIB byte is the "
            "constant 25: scale 00, index 100 (\"no index\") and base 101 "
            "(\"no base, disp32\"). There is no base, index or scale operand, "
            "and the address is always four bytes, even for 0x7fff, which would "
            "fit a disp8. The vector register sits in the five-bit field at "
            "[43,3] plus the inverted R-bar/R-bar-prime bits at [12,1]/[15,1]: "
            "%xmm20 and %xmm21 are 62 e1, %ymm8 and %ymm9 are 62 71, %zmm30 "
            "and %zmm31 are 62 61. The addresses cover a positive value (4660), "
            "a negative one (-4096), 0x7fff, 4096, -1 and the signed end point "
            "-2147483648, whose four bytes are 00 00 00 80. input_sha256 is "
            "fixture.asm (the source above); output_sha256 is the 66-byte "
            ".text."
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
