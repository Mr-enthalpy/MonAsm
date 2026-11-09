#!/usr/bin/env python3
"""Build the `X86-P83-mov-imm` plan and expected bytes.

Ten instructions: the `B8+rd` row at 16/32 bits with two values each, the
`C7 /0` row at 16/32 bits with the same two values, and the 64-bit `C7` row at
`%rbx` and `%r8` (the `REX.B` window). The plan pins
`definitions/x86_64/0.77.0.json`.

The 16/32-bit `C7 /0` bytes are hand-derived and confirmed by
`llvm-mc -disassemble` (`EXP-0114` `direction.txt`): `llvm-mc` always picks
`B8+rd` for a register destination, so the expected image cannot be produced by
assembling the listing.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0114/make_fixture.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/x86_64/positive/X86-P83-mov-imm"

EXPECTED = bytes.fromhex(
    "66bb0100" "66b92c01"
    "bb01000000" "b92c010000"
    "48c7c301000000" "49c7c02c010000"
    "66c7c30100" "66c7c12c01"
    "c7c301000000" "c7c12c010000"
)

# form_id, kind, target_type, register, immediate, size
ROWS = [
    ("x86:mov/r16-imm16/legacy", "x86.gpr16", "r16", 3, 1, 4),
    ("x86:mov/r16-imm16/legacy", "x86.gpr16", "r16", 1, 300, 4),
    ("x86:mov/r32-imm32/legacy", "x86.gpr32", "r32", 3, 1, 5),
    ("x86:mov/r32-imm32/legacy", "x86.gpr32", "r32", 1, 300, 5),
    ("x86:mov/rm64-imm32/legacy", "x86.gpr64", "rm64", 3, 1, 7),
    ("x86:mov/rm64-imm32/legacy", "x86.gpr64", "rm64", 8, 300, 7),
    ("x86:mov/rm16-imm16/legacy", "x86.gpr16", "rm16", 3, 1, 5),
    ("x86:mov/rm16-imm16/legacy", "x86.gpr16", "rm16", 1, 300, 5),
    ("x86:mov/rm32-imm32/legacy", "x86.gpr32", "rm32", 3, 1, 6),
    ("x86:mov/rm32-imm32/legacy", "x86.gpr32", "rm32", 1, 300, 6),
]


def main() -> int:
    if len(EXPECTED) != 54:
        raise SystemExit("expected bytes are not 54 long")
    instructions = []
    fragments = []
    offset = 0
    for index, (form_id, kind, target_type, register, imm, size) in enumerate(
            ROWS, 1):
        instruction_id = "I%04d" % index
        imm_type = "imm16" if target_type.endswith("16") else "imm32"
        instructions.append(
            "    {\n"
            "      \"instruction_id\": \"%s\",\n"
            "      \"section_id\": \".text\",\n"
            "      \"offset\": %d,\n"
            "      \"form_id\": \"%s\",\n"
            "      \"operands\": [\n"
            "        { \"role\": \"dest\", \"kind\": \"%s\", \"target_type\": \"%s\", "
            "\"payload\": { \"reg\": %d }, \"modifiers\": [] },\n"
            "        { \"role\": \"imm\", \"kind\": \"x86.imm\", \"target_type\": \"%s\", "
            "\"payload\": { \"value\": %d }, \"modifiers\": [] }\n"
            "      ],\n"
            "      \"expected_size\": %d\n"
            "    }"
            % (instruction_id, offset, form_id, kind, target_type, register,
               imm_type, imm, size))
        fragments.append(
            "        { \"offset\": %d, \"size\": %d, \"kind\": "
            "\"instruction\", \"instruction_id\": \"%s\" }"
            % (offset, size, instruction_id))
        offset += size
    if offset != len(EXPECTED):
        raise SystemExit("assembled length %d != %d" % (offset, len(EXPECTED)))

    text = (
        "{\n"
        "  \"format_version\": \"fmp/0.1\",\n"
        "  \"target_identity\": {\n"
        "    \"isa_family\": \"x86\",\n"
        "    \"isa_variant\": \"x86-64\",\n"
        "    \"execution_mode\": \"64\",\n"
        "    \"enabled_extensions\": [],\n"
        "    \"feature_constraints\": [],\n"
        "    \"byte_order\": \"little\",\n"
        "    \"address_width\": 64\n"
        "  },\n"
        "  \"definition_identity\": {\n"
        "    \"namespace\": \"monasm.isa.x86\",\n"
        "    \"version\": \"0.77.0\",\n"
        "    \"digest\": \"sha256:093d8f3c0abefc04b9c9b4ed421412a1f9a1fe54bf430951653fac0955d4c68b\"\n"
        "  },\n"
        "  \"output_contract\": {\n"
        "    \"artifact\": \"bytes\",\n"
        "    \"section_order\": [\".text\"],\n"
        "    \"fixup_record_order\": \"section_id,offset,fixup_id\",\n"
        "    \"include_symbol_table\": false,\n"
        "    \"emit_fixups\": true\n"
        "  },\n"
        "  \"sections\": [\n"
        "    {\n"
        "      \"section_id\": \".text\",\n"
        "      \"section_kind\": \"code\",\n"
        "      \"image_backed\": true,\n"
        "      \"declared_size\": %d,\n"
        "      \"fragments\": [\n%s\n      ]\n"
        "    }\n"
        "  ],\n"
        "  \"symbols\": [],\n"
        "  \"instructions\": [\n%s\n  ],\n"
        "  \"fixups\": []\n"
        "}\n"
        % (len(EXPECTED), ",\n".join(fragments),
           ",\n".join(instructions))
    )

    parsed = json.loads(text)
    if len(parsed["instructions"]) != 10:
        raise SystemExit("expected 10 instructions")

    with (FIXTURE.parent / "X86-P83-mov-imm.fmp.json").open(
            "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with (FIXTURE.parent / "X86-P83-mov-imm.expected.bin").open("wb") as handle:
        handle.write(EXPECTED)
    print("instructions: 10")
    print("bytes: %d" % len(EXPECTED))
    print("output sha256: %s" % hashlib.sha256(EXPECTED).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
