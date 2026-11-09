#!/usr/bin/env python3
"""Build the `X86-P82-alu-imm` plan and expected bytes.

The thirty-six instructions are the measured `EXP-0113` order: for each
mnemonic and width the `imm8` row and the full-width row, with the four 64-bit
`%rax` short forms last. The plan pins `definitions/x86_64/0.76.0.json`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0113/make_fixture.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/x86_64/positive/X86-P82-alu-imm"

EXPECTED = bytes.fromhex(
    "83c301" "81c12c010000" "6683c301" "6681c12c01"
    "83eb01" "81e92c010000" "6683eb01" "6681e92c01"
    "4883e301" "4881e12c010000" "83e301" "81e12c010000"
    "6683e301" "6681e12c01"
    "4883cb01" "4881c92c010000" "83cb01" "81c92c010000"
    "6683cb01" "6681c92c01"
    "4883f301" "4881f12c010000" "83f301" "81f12c010000"
    "6683f301" "6681f12c01"
    "4883fb01" "4881f92c010000" "83fb01" "81f92c010000"
    "6683fb01" "6681f92c01"
    "48252c010000" "480d2c010000" "48352c010000" "483d2c010000"
)

# form_id, destination register (None for the `%rax` short forms), immediate,
# expected size
ROWS = [
    ("x86:add/rm32-imm8/legacy", 3, 1, 3),
    ("x86:add/rm32-imm32/legacy", 1, 300, 6),
    ("x86:add/rm16-imm8/legacy", 3, 1, 4),
    ("x86:add/rm16-imm16/legacy", 1, 300, 5),
    ("x86:sub/rm32-imm8/legacy", 3, 1, 3),
    ("x86:sub/rm32-imm32/legacy", 1, 300, 6),
    ("x86:sub/rm16-imm8/legacy", 3, 1, 4),
    ("x86:sub/rm16-imm16/legacy", 1, 300, 5),
    ("x86:and/rm64-imm8/legacy", 3, 1, 4),
    ("x86:and/rm64-imm32/legacy", 1, 300, 7),
    ("x86:and/rm32-imm8/legacy", 3, 1, 3),
    ("x86:and/rm32-imm32/legacy", 1, 300, 6),
    ("x86:and/rm16-imm8/legacy", 3, 1, 4),
    ("x86:and/rm16-imm16/legacy", 1, 300, 5),
    ("x86:or/rm64-imm8/legacy", 3, 1, 4),
    ("x86:or/rm64-imm32/legacy", 1, 300, 7),
    ("x86:or/rm32-imm8/legacy", 3, 1, 3),
    ("x86:or/rm32-imm32/legacy", 1, 300, 6),
    ("x86:or/rm16-imm8/legacy", 3, 1, 4),
    ("x86:or/rm16-imm16/legacy", 1, 300, 5),
    ("x86:xor/rm64-imm8/legacy", 3, 1, 4),
    ("x86:xor/rm64-imm32/legacy", 1, 300, 7),
    ("x86:xor/rm32-imm8/legacy", 3, 1, 3),
    ("x86:xor/rm32-imm32/legacy", 1, 300, 6),
    ("x86:xor/rm16-imm8/legacy", 3, 1, 4),
    ("x86:xor/rm16-imm16/legacy", 1, 300, 5),
    ("x86:cmp/rm64-imm8/legacy", 3, 1, 4),
    ("x86:cmp/rm64-imm32/legacy", 1, 300, 7),
    ("x86:cmp/rm32-imm8/legacy", 3, 1, 3),
    ("x86:cmp/rm32-imm32/legacy", 1, 300, 6),
    ("x86:cmp/rm16-imm8/legacy", 3, 1, 4),
    ("x86:cmp/rm16-imm16/legacy", 1, 300, 5),
    ("x86:and/rax-imm32/legacy", None, 300, 6),
    ("x86:or/rax-imm32/legacy", None, 300, 6),
    ("x86:xor/rax-imm32/legacy", None, 300, 6),
    ("x86:cmp/rax-imm32/legacy", None, 300, 6),
]


def operands(form_id: str, dest: int | None, imm: int) -> list:
    width = form_id.split("/")[1].split("-")[0][2:]
    target_type = form_id.split("-")[-1].split("/")[0]
    if target_type == "rax":
        target_type = "imm32"
    items = []
    if dest is not None:
        items.append({
            "role": "dest",
            "kind": "x86.gpr" + width,
            "target_type": "rm" + width,
            "payload": {"reg": dest},
            "modifiers": [],
        })
    items.append({
        "role": "imm",
        "kind": "x86.imm",
        "target_type": target_type,
        "payload": {"value": imm},
        "modifiers": [],
    })
    return items


def main() -> int:
    if len(EXPECTED) != 176:
        raise SystemExit("expected bytes are not 176 long")
    instructions = []
    fragments = []
    offset = 0
    for index, (form_id, dest, imm, size) in enumerate(ROWS, 1):
        instruction_id = "I%04d" % index
        instructions.append(
            "    {\n"
            "      \"instruction_id\": \"%s\",\n"
            "      \"section_id\": \".text\",\n"
            "      \"offset\": %d,\n"
            "      \"form_id\": \"%s\",\n"
            "      \"operands\": [\n%s\n      ],\n"
            "      \"expected_size\": %d\n"
            "    }"
            % (instruction_id, offset, form_id,
               ",\n".join(
                   "        { \"role\": \"%s\", \"kind\": \"%s\", "
                   "\"target_type\": \"%s\", \"payload\": %s, "
                   "\"modifiers\": [] }"
                   % (operand["role"], operand["kind"],
                      operand["target_type"],
                      json.dumps(operand["payload"]))
                   for operand in operands(form_id, dest, imm)),
               size))
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
        "    \"version\": \"0.76.0\",\n"
        "    \"digest\": \"sha256:7535ae0641806b1785096bd286ac62f90f7f02023fd5d47a92b4d4df6371e39a\"\n"
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
    if len(parsed["instructions"]) != 36:
        raise SystemExit("expected 36 instructions")

    with (FIXTURE.parent / "X86-P82-alu-imm.fmp.json").open(
            "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with (FIXTURE.parent / "X86-P82-alu-imm.expected.bin").open("wb") as handle:
        handle.write(EXPECTED)
    print("instructions: 36")
    print("bytes: %d" % len(EXPECTED))
    print("output sha256: %s" % hashlib.sha256(EXPECTED).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
