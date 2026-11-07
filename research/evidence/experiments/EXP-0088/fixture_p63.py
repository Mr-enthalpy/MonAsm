#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P63-gpr16-mov-index-addr32-rex-two-bit-windows.{fmp.json,
expected.bin}` and its `oracle.json`.

The instruction order matches `EXP-0088/probe.asm`, which is the oracle input
and the 164-byte vector. The sixteen `0.59.0` rows cover the four two-`REX`-bit
windows (`RB`, `RX`, `BX`, `RBX`) in both directions at both displacement
widths, plus four corners: `%r12d` as a base with `%r15w`, `%r12d` as a base
with `%r15d` as an index, `%r12d`/`%r13d` under `REX.RBX`, and the x8 scale.
`expected.bin` is copied from `llvm-objcopy`, never produced by the
materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0088/fixture_p63.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P63-gpr16-mov-index-addr32-rex-two-bit-windows"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0088/probe.asm"

VERSION = "0.59.0"
DIGEST = "sha256:bf7e54f512d27e83a3834b95ec4dc75767ee86d619ec833dee2a7cf13637826f"

BX_LOAD8 = "x86:mov/r16-addr32-base-ext-index-ext-disp8/legacy"
BX_STORE8 = "x86:mov/addr32-base-ext-index-ext-disp8-r16/legacy"
RB_LOAD8 = "x86:mov/r16-ext-addr32-base-ext-index-disp8/legacy"
RB_STORE8 = "x86:mov/addr32-base-ext-index-disp8-r16-ext/legacy"
RX_LOAD8 = "x86:mov/r16-ext-addr32-base-index-ext-disp8/legacy"
RX_STORE8 = "x86:mov/addr32-base-index-ext-disp8-r16-ext/legacy"
RBX_LOAD8 = "x86:mov/r16-ext-addr32-base-ext-index-ext-disp8/legacy"
RBX_STORE8 = "x86:mov/addr32-base-ext-index-ext-disp8-r16-ext/legacy"
BX_LOAD32 = "x86:mov/r16-addr32-base-ext-index-ext-disp32/legacy"
BX_STORE32 = "x86:mov/addr32-base-ext-index-ext-disp32-r16/legacy"
RB_LOAD32 = "x86:mov/r16-ext-addr32-base-ext-index-disp32/legacy"
RB_STORE32 = "x86:mov/addr32-base-ext-index-disp32-r16-ext/legacy"
RX_LOAD32 = "x86:mov/r16-ext-addr32-base-index-ext-disp32/legacy"
RX_STORE32 = "x86:mov/addr32-base-index-ext-disp32-r16-ext/legacy"
RBX_LOAD32 = "x86:mov/r16-ext-addr32-base-ext-index-ext-disp32/legacy"
RBX_STORE32 = "x86:mov/addr32-base-ext-index-ext-disp32-r16-ext/legacy"

# (form_id, role, register, base, index, scale, disp, size)
PLAN = [
    (RB_LOAD8, "dest", 8, 8, 1, 0, 8, 7),
    (RB_STORE8, "src", 8, 8, 1, 0, 8, 7),
    (RX_LOAD8, "dest", 8, 0, 9, 0, 8, 7),
    (RX_STORE8, "src", 8, 0, 9, 0, 8, 7),
    (BX_LOAD8, "dest", 0, 8, 9, 0, 8, 7),
    (BX_STORE8, "src", 0, 8, 9, 0, 8, 7),
    (RBX_LOAD8, "dest", 8, 8, 9, 0, 8, 7),
    (RBX_STORE8, "src", 8, 8, 9, 0, 8, 7),
    (RB_LOAD32, "dest", 8, 8, 1, 0, 200, 10),
    (RB_STORE32, "src", 8, 8, 1, 0, 200, 10),
    (RX_LOAD32, "dest", 8, 0, 9, 0, 200, 10),
    (RX_STORE32, "src", 8, 0, 9, 0, 200, 10),
    (BX_LOAD32, "dest", 0, 8, 9, 0, 200, 10),
    (BX_STORE32, "src", 0, 8, 9, 0, 200, 10),
    (RBX_LOAD32, "dest", 8, 8, 9, 0, 200, 10),
    (RBX_STORE32, "src", 8, 8, 9, 0, 200, 10),
    (RB_LOAD8, "dest", 15, 12, 1, 0, 8, 7),
    (BX_LOAD8, "dest", 2, 12, 15, 0, 8, 7),
    (RBX_LOAD8, "dest", 15, 12, 13, 0, 8, 7),
    (RBX_LOAD8, "dest", 8, 8, 9, 3, 8, 7),
]


def operand(role, kind, target_type, payload):
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p63.py <oracle.bin>")
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
            operand(role, "x86.gpr16", "r16", {"reg": reg}),
            operand("base", "x86.gpr32", "rm32", {"reg": base}),
            operand("index", "x86.gpr32", "sib_index32", {"reg": sib_index}),
            operand("imm", "x86.scale", "scale2", {"value": scale}),
        ]
        operands.append(
            operand("disp", "x86.imm", "disp%d" % (8 if size == 7 else 32),
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
                    "research/evidence/experiments/EXP-0088/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "The sixteen 0.59.0 rows: the 0x67 0x66 movw behind the address-size "
            "prefix takes the four two-REX-bit windows (RB value+base, RX "
            "value+index, BX base+index, RBX all three), both directions at "
            "disp8 and disp32. 0x67 is byte 0, 0x66 byte 1, REX byte 2, the "
            "opcode byte 3, ModRM byte 4 (value register [35,3]) and SIB byte 5 "
            "(base [40,3], index [43,3], scale [46,2]), with the displacement "
            "at [48,8] or [48,32]. The fixed bits are R at [18,1], B at [16,1] "
            "and X at [17,1]; each extended slot excludes 0-7. The base and "
            "index are 32-bit address registers (%r8d-%r15d) while the value is "
            "%r8w-%r15w; index 4 with X=1 names %r12d. The four extra "
            "instructions cover %r12d as a base with %r15w (67 66 45 8b 7c 0c "
            "08), %r12d as a base with %r15d as an index (67 66 43 8b 54 3c "
            "08), %r12d/%r13d under REX.RBX (67 66 47 8b 7c 2c 08) and the x8 "
            "scale (67 66 47 8b 44 c8 08). input_sha256 is probe.asm; "
            "output_sha256 is the 164-byte .text."
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
