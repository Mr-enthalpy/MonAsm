#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P60-gpr64-mov-index-addr32-rex-w.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0085/probe.asm`, which is the oracle input
and the 78-byte vector. The four `0.56.0` rows cover both directions at both
displacement widths, plus eight corners: `REX.RBX` with `%r8`, `%r12` on all
three operands, `%r13` on all three, `%ebp` as a base, `%r12d` as an index,
`%r12d` as a base, the x8 scale and a `%r15`/`%r15d`/`%ebp` store. `expected.bin`
is copied from `llvm-objcopy`, never produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0085/fixture_p60.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P60-gpr64-mov-index-addr32-rex-w"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0085/probe.asm"

VERSION = "0.56.0"
DIGEST = "sha256:d039c97253fbdefba9c68c4fdab0d3310d17b809b8ba29fc268e6d8458f2ef87"

LOAD8 = "x86:mov/r64-addr32-base-index-disp8/legacy"
STORE8 = "x86:mov/addr32-base-index-disp8-r64/legacy"
LOAD32 = "x86:mov/r64-addr32-base-index-disp32/legacy"
STORE32 = "x86:mov/addr32-base-index-disp32-r64/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (LOAD8, "dest", 0, 0, 1, 0, 8, 6),
    (STORE8, "src", 0, 0, 1, 0, 8, 6),
    (LOAD32, "dest", 0, 0, 1, 0, 200, 9),
    (STORE32, "src", 0, 0, 1, 0, 200, 9),
    (LOAD8, "dest", 8, 8, 9, 0, 8, 6),
    (LOAD8, "dest", 12, 12, 12, 0, 8, 6),
    (LOAD8, "dest", 13, 13, 13, 0, 8, 6),
    (LOAD8, "dest", 0, 5, 1, 0, 8, 6),
    (LOAD8, "dest", 0, 0, 12, 0, 8, 6),
    (LOAD8, "dest", 0, 12, 1, 0, 8, 6),
    (LOAD8, "dest", 0, 0, 1, 3, 8, 6),
    (STORE8, "src", 15, 15, 5, 0, 8, 6),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p60.py <oracle.bin>")
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
        fragments.append({"offset": offset, "size": size,
                          "kind": "instruction",
                          "instruction_id": instruction_id})
        operands = [
            operand(role, "x86.gpr64", "r64", {"reg": reg}),
            operand("base", "x86.gpr32", "rm32", {"reg": base}),
            operand("index", "x86.gpr32", "sib_index32", {"reg": sib_index}),
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
                    "research/evidence/experiments/EXP-0085/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The four 0.56.0 rows: the 0x67 REX.W movq on the 32-bit indexed "
            "address shape, both directions at disp8 and disp32. 0x67 is byte "
            "0, REX = 48 byte 1, the opcode byte 2, ModRM byte 3 (value "
            "register [10,1]+[27,3]) and SIB byte 4 (base [8,1]+[32,3], index "
            "[9,1]+[35,3], scale [38,2]), with the displacement at [40,8] or "
            "[40,32]. REX.W is template content; R/X/B come from the operands, "
            "so REX = 4f is the same row as 48. The base and index are 32-bit "
            "address registers (%eax-%r15d) while the value is %rax-%r15. The "
            "eight extra instructions cover REX.RBX with %r8 "
            "(67 4f 8b 44 08 08), %r12 on all three operands "
            "(67 4f 8b 64 24 08), %r13 (67 4f 8b 6c 2d 08), %ebp as a base "
            "(67 48 8b 44 0d 08), %r12d as an index (67 4a 8b 44 20 08), "
            "%r12d as a base (67 49 8b 44 0c 08), the x8 scale "
            "(67 48 8b 44 c8 08) and a %r15/%r15d/%ebp store "
            "(67 4d 89 7c 2f 08). input_sha256 is probe.asm; output_sha256 is "
            "the 78-byte .text."
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
