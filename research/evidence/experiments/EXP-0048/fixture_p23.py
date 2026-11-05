#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P23-mov-mem-sib.{fmp.json,expected.bin}`.

The instruction order matches `EXP-0048/fixture.asm`, which is the oracle
input; the sizes are the measured `llvm-mc` encodings (a `%r12` base adds the
`REX` byte on top of the `%rsp` size). `expected.bin` is copied from
`llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0048/fixture_p23.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P23-mov-mem-sib"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0048/fixture.asm"

WORD = {"kind": "x86.gpr16", "target_type": "r16"}
LOW = {"kind": "x86.gpr8", "target_type": "r8"}
HIGH = {"kind": "x86.gpr8h", "target_type": "r8h"}

# (form_id, role, register number, register class, disp bits, size)
PLAN = [
    ("x86:mov/r16-rsp-disp8/legacy", "dest", 0, WORD, 8, 5),
    ("x86:mov/r16-r12-disp8/legacy", "dest", 0, WORD, 8, 6),
    ("x86:mov/r16-rsp-disp32/legacy", "dest", 0, WORD, 32, 8),
    ("x86:mov/r16-r12-disp32/legacy", "dest", 0, WORD, 32, 9),
    ("x86:mov/rsp-disp8-r16/legacy", "src", 0, WORD, 8, 5),
    ("x86:mov/r12-disp8-r16/legacy", "src", 0, WORD, 8, 6),
    ("x86:mov/rsp-disp32-r16/legacy", "src", 0, WORD, 32, 8),
    ("x86:mov/r12-disp32-r16/legacy", "src", 0, WORD, 32, 9),
    ("x86:mov/r8-rsp-disp8/legacy", "dest", 0, LOW, 8, 4),
    ("x86:mov/r8-r12-disp8/legacy", "dest", 3, LOW, 8, 5),
    ("x86:mov/r8-rsp-disp32/legacy", "dest", 1, LOW, 32, 7),
    ("x86:mov/r8-r12-disp32/legacy", "dest", 2, LOW, 32, 8),
    ("x86:mov/rsp-disp8-r8/legacy", "src", 0, LOW, 8, 4),
    ("x86:mov/r12-disp8-r8/legacy", "src", 3, LOW, 8, 5),
    ("x86:mov/rsp-disp32-r8/legacy", "src", 1, LOW, 32, 7),
    ("x86:mov/r12-disp32-r8/legacy", "src", 2, LOW, 32, 8),
    ("x86:mov/r8h-rsp-disp8/legacy", "dest", 4, HIGH, 8, 4),
    ("x86:mov/r8h-rsp-disp32/legacy", "dest", 7, HIGH, 32, 7),
    ("x86:mov/rsp-disp8-r8h/legacy", "src", 4, HIGH, 8, 4),
    ("x86:mov/rsp-disp32-r8h/legacy", "src", 5, HIGH, 32, 7),
    ("x86:mov/r8-rsp-disp8-rex/legacy", "dest", 4, LOW, 8, 5),
    ("x86:mov/r8-r12-disp8-rex/legacy", "dest", 5, LOW, 8, 5),
    ("x86:mov/r8-rsp-disp32-rex/legacy", "dest", 6, LOW, 32, 8),
    ("x86:mov/r8-r12-disp32-rex/legacy", "dest", 7, LOW, 32, 8),
    ("x86:mov/rsp-disp8-r8-rex/legacy", "src", 4, LOW, 8, 5),
    ("x86:mov/r12-disp8-r8-rex/legacy", "src", 5, LOW, 8, 5),
    ("x86:mov/rsp-disp32-r8-rex/legacy", "src", 6, LOW, 32, 8),
    ("x86:mov/r12-disp32-r8-rex/legacy", "src", 7, LOW, 32, 8),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p23.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(item[5] for item in PLAN)
    if len(PLAN) != 28:
        raise SystemExit("plan is not 28 instructions")
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, (form_id, role, reg, kind, disp_bits, size) in enumerate(PLAN, 1):
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": [
                {"role": role, "kind": kind["kind"],
                 "target_type": kind["target_type"],
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
            "version": "0.19.0",
            "digest": "sha256:dddc678fe0abc6fa03c2e61c8fcafef2570b496775a11a25e1ab29e01bfe5130",
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
