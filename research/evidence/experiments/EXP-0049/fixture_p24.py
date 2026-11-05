#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P24-sse-mem-sib.{fmp.json,expected.bin}`.

The instruction order matches `EXP-0049/fixture.asm`, which is the oracle
input; the sizes are the measured `llvm-mc` encodings (a `%r12` base adds the
`REX` byte / the three-byte VEX prefix on top of the `%rsp` size). The legacy
eight run `xmm0`-`xmm7`, the three-bit window; the VEX eight run `xmm8`-`xmm15`,
because their slot carries the `R` bit already, so the fixture pins both
windows as well as the base. `expected.bin` is copied from `llvm-objcopy`,
never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0049/fixture_p24.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P24-sse-mem-sib"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0049/fixture.asm"

XMM = {"kind": "x86.xmm", "target_type": "xmm"}

# (form_id, role, register number, disp bits, size)
PLAN = [
    ("x86:movaps/xmm-rsp-disp8/legacy", "dest", 0, 8, 5),
    ("x86:movaps/xmm-r12-disp8/legacy", "dest", 1, 8, 6),
    ("x86:movaps/xmm-rsp-disp32/legacy", "dest", 2, 32, 8),
    ("x86:movaps/xmm-r12-disp32/legacy", "dest", 3, 32, 9),
    ("x86:movaps/rsp-disp8-xmm/legacy", "src", 4, 8, 5),
    ("x86:movaps/r12-disp8-xmm/legacy", "src", 5, 8, 6),
    ("x86:movaps/rsp-disp32-xmm/legacy", "src", 6, 32, 8),
    ("x86:movaps/r12-disp32-xmm/legacy", "src", 7, 32, 9),
    ("x86:vmovaps/xmm-rsp-disp8/vex", "dest", 8, 8, 6),
    ("x86:vmovaps/xmm-r12-disp8/vex", "dest", 9, 8, 7),
    ("x86:vmovaps/xmm-rsp-disp32/vex", "dest", 14, 32, 9),
    ("x86:vmovaps/xmm-r12-disp32/vex", "dest", 15, 32, 10),
    ("x86:vmovaps/rsp-disp8-xmm/vex", "src", 8, 8, 6),
    ("x86:vmovaps/r12-disp8-xmm/vex", "src", 9, 8, 7),
    ("x86:vmovaps/rsp-disp32-xmm/vex", "src", 14, 32, 9),
    ("x86:vmovaps/r12-disp32-xmm/vex", "src", 15, 32, 10),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p24.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(item[4] for item in PLAN)
    if len(PLAN) != 16:
        raise SystemExit("plan is not 16 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, (form_id, role, reg, disp_bits, size) in enumerate(PLAN, 1):
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": [
                {"role": role, "kind": XMM["kind"],
                 "target_type": XMM["target_type"],
                 "payload": {"reg": reg}, "modifiers": []},
                {"role": "disp", "kind": "x86.imm",
                 "target_type": "disp%d" % disp_bits,
                 "payload": {"value": 128 if disp_bits == 32 else 8},
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
            "version": "0.20.0",
            "digest": "sha256:b8bd1ed3ed38d71f6b19cc1854c9252df13850127c4e9433981a3a45f49d0f99",
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
    print("%s: %d instructions, %d bytes" % (STEM, len(PLAN), total))
    print("input_sha256  %s" % hashlib.sha256(source).hexdigest())
    print("output_sha256 %s" % hashlib.sha256(output).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
