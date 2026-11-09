#!/usr/bin/env python3
"""Build the `X86-P84-sub-mem` plan and expected bytes.

Twelve instructions, one per new row: the `29 /r` store direction and the
`2B /r` load direction at 64, 32 and 16 bits, each with `base + disp8` and
`base + disp32`. The register is `%rcx`/`%ecx`/`%cx` (1) or `%rdx`/`%edx`/`%dx`
(2); the base is `%rax` (0) for the `disp8` rows and `%rbx` (3) for the
`disp32` rows. That keeps every field operand-owned: the two directions of the
same operands differ only in the opcode byte.

The expected image is the measured `EXP-0115` `X86-P84-sub-mem.s`, which
`measure.py` assembles and checks byte for byte.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0115/make_fixture.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/x86_64/positive/X86-P84-sub-mem"

EXPECTED = bytes.fromhex(
    "48294808" "4829932c010000"
    "482b4808" "482b932c010000"
    "294808" "29932c010000"
    "2b4808" "2b932c010000"
    "66294808" "6629932c010000"
    "662b4808" "662b932c010000"
)

DIGEST = "sha256:30cb9f13047ff742d8f53a20f93218a601302bd52814ad26364347cb85576a21"

# form_id, direction, width, register, base, displacement, size
ROWS = [
    ("x86:sub/base-disp8-r64/legacy", "store", 64, 1, 0, 8, 4),
    ("x86:sub/base-disp32-r64/legacy", "store", 64, 2, 3, 300, 7),
    ("x86:sub/r64-base-disp8/legacy", "load", 64, 1, 0, 8, 4),
    ("x86:sub/r64-base-disp32/legacy", "load", 64, 2, 3, 300, 7),
    ("x86:sub/base-disp8-r32/legacy", "store", 32, 1, 0, 8, 3),
    ("x86:sub/base-disp32-r32/legacy", "store", 32, 2, 3, 300, 6),
    ("x86:sub/r32-base-disp8/legacy", "load", 32, 1, 0, 8, 3),
    ("x86:sub/r32-base-disp32/legacy", "load", 32, 2, 3, 300, 6),
    ("x86:sub/base-disp8-r16/legacy", "store", 16, 1, 0, 8, 4),
    ("x86:sub/base-disp32-r16/legacy", "store", 16, 2, 3, 300, 7),
    ("x86:sub/r16-base-disp8/legacy", "load", 16, 1, 0, 8, 4),
    ("x86:sub/r16-base-disp32/legacy", "load", 16, 2, 3, 300, 7),
]


def register(role: str, width: int, number: int) -> dict:
    return {
        "role": role,
        "kind": "x86.gpr%d" % width,
        "target_type": "r%d" % width,
        "payload": {"reg": number},
        "modifiers": [],
    }


def main() -> int:
    if len(EXPECTED) != 62:
        raise SystemExit("expected bytes are not 62 long")
    instructions = []
    fragments = []
    offset = 0
    for index, (form_id, direction, width, register_number, base_number,
                disp, size) in enumerate(ROWS, 1):
        instruction_id = "I%04d" % index
        bits = 8 if "disp8" in form_id else 32
        operands = []
        if direction == "store":
            operands.append(register("src", width, register_number))
        else:
            operands.append(register("dest", width, register_number))
        operands.append({
            "role": "base" if direction == "store" else "src",
            "kind": "x86.gpr64",
            "target_type": "rm64",
            "payload": {"reg": base_number},
            "modifiers": [],
        })
        operands.append({
            "role": "disp",
            "kind": "x86.imm",
            "target_type": "disp%d" % bits,
            "payload": {"value": disp},
            "modifiers": [],
        })

        rendered = []
        for operand in operands:
            rendered.append(
                "        { \"role\": \"%s\", \"kind\": \"%s\", "
                "\"target_type\": \"%s\", \"payload\": %s, \"modifiers\": [] }"
                % (operand["role"], operand["kind"], operand["target_type"],
                   json.dumps(operand["payload"])))
        instructions.append(
            "    {\n"
            "      \"instruction_id\": \"%s\",\n"
            "      \"section_id\": \".text\",\n"
            "      \"offset\": %d,\n"
            "      \"form_id\": \"%s\",\n"
            "      \"operands\": [\n%s\n      ],\n"
            "      \"expected_size\": %d\n"
            "    }"
            % (instruction_id, offset, form_id, ",\n".join(rendered), size))
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
        "    \"version\": \"0.78.0\",\n"
        "    \"digest\": \"%s\"\n"
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
        % (DIGEST, len(EXPECTED), ",\n".join(fragments),
           ",\n".join(instructions))
    )

    parsed = json.loads(text)
    if len(parsed["instructions"]) != 12:
        raise SystemExit("expected 12 instructions")

    with (FIXTURE.parent / "X86-P84-sub-mem.fmp.json").open(
            "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with (FIXTURE.parent / "X86-P84-sub-mem.expected.bin").open("wb") as handle:
        handle.write(EXPECTED)
    print("instructions: 12")
    print("bytes: %d" % len(EXPECTED))
    print("output sha256: %s" % hashlib.sha256(EXPECTED).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
