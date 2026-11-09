#!/usr/bin/env python3
"""Build the `X86-P81-alu-rr` plan and expected bytes.

The thirty instructions are the measured `EXP-0112` order: for each mnemonic
(`add`, `and`, `or`, `xor`, `cmp`) and width (64, 32, 16 bits), the two
operand orders. The plan pins `definitions/x86_64/0.75.0.json`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0112/make_fixture.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures/x86_64/positive/X86-P81-alu-rr"

EXPECTED = bytes.fromhex(
    "4801c84801c101c801c16601c86601c1"
    "4821c84821c121c821c16621c86621c1"
    "4809c84809c109c809c16609c86609c1"
    "4831c84831c131c831c16631c86631c1"
    "4839c84839c139c839c16639c86639c1"
)

MNEMONICS = ["add", "and", "or", "xor", "cmp"]
WIDTHS = [
    ("q", "64", "x86.gpr64", "rm64", "r64", 3),
    ("l", "32", "x86.gpr32", "rm32", "r32", 2),
    ("w", "16", "x86.gpr16", "rm16", "r16", 3),
]


def instruction(index: int, offset: int, mnemonic: str,
                kind: str, dest_type: str, src_type: str,
                dest: int, src: int, bits: str) -> tuple[dict, int]:
    size = 3 if bits != "32" else 2
    instruction_id = "I%04d" % index
    entry = {
        "instruction_id": instruction_id,
        "section_id": ".text",
        "offset": offset,
        "form_id": "x86:%s/rm%s-r%s/legacy" % (mnemonic, bits, bits),
        "operands": [
            {"role": "dest", "kind": kind, "target_type": dest_type,
             "payload": {"reg": dest}, "modifiers": []},
            {"role": "src", "kind": kind, "target_type": src_type,
             "payload": {"reg": src}, "modifiers": []},
        ],
        "expected_size": size,
    }
    return entry, offset + size


def main() -> int:
    if len(EXPECTED) != 80:
        raise SystemExit("expected bytes are not 80 long")
    instructions = []
    fragments = []
    offset = 0
    index = 1
    for mnemonic in MNEMONICS:
        for short, bits, kind, dest_type, src_type, size in WIDTHS:
            for dest, src in ((0, 1), (1, 0)):
                entry, offset = instruction(index, offset, mnemonic,
                                            kind, dest_type, src_type,
                                            dest, src, bits)
                instructions.append(entry)
                fragments.append(
                    "        { \"offset\": %d, \"size\": %d, \"kind\": "
                    "\"instruction\", \"instruction_id\": \"%s\" }"
                    % (entry["offset"], size, entry["instruction_id"]))
                index += 1
    if offset != len(EXPECTED):
        raise SystemExit("assembled length %d != %d" % (offset, len(EXPECTED)))

    rendered_instructions = []
    for entry in instructions:
        operands = ",\n".join(
            "        { \"role\": \"%s\", \"kind\": \"%s\", \"target_type\": "
            "\"%s\", \"payload\": { \"reg\": %d }, \"modifiers\": [] }"
            % (operand["role"], operand["kind"], operand["target_type"],
               operand["payload"]["reg"])
            for operand in entry["operands"])
        rendered_instructions.append(
            "    {\n"
            "      \"instruction_id\": \"%s\",\n"
            "      \"section_id\": \".text\",\n"
            "      \"offset\": %d,\n"
            "      \"form_id\": \"%s\",\n"
            "      \"operands\": [\n%s\n      ],\n"
            "      \"expected_size\": %d\n"
            "    }"
            % (entry["instruction_id"], entry["offset"], entry["form_id"],
               operands, entry["expected_size"]))

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
        "    \"version\": \"0.75.0\",\n"
        "    \"digest\": \"sha256:5b13b6b96a4061f354e7d0a371175936cb66c71dbfa80a7eabbf74bfe7eef40d\"\n"
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
           ",\n".join(rendered_instructions))
    )

    parsed = json.loads(text)
    if len(parsed["instructions"]) != 30:
        raise SystemExit("expected 30 instructions")

    with (FIXTURE.parent / "X86-P81-alu-rr.fmp.json").open(
            "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with (FIXTURE.parent / "X86-P81-alu-rr.expected.bin").open("wb") as handle:
        handle.write(EXPECTED)
    print("instructions: 30")
    print("bytes: %d" % len(EXPECTED))
    print("output sha256: %s"
          % hashlib.sha256(EXPECTED).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
