#!/usr/bin/env python3
"""Build the `A64-P24` plan and expected bytes.

Eight instructions over the four `0.20.0` forms (`ADR-0119`):

- `mul` at 32 and 64 bits (`aarch64:mul/w32-w32-w32`,
  `aarch64:mul/x64-x64-x64`), three operands, `Ra = 31` supplied by the alias
  node and never by the plan; one row puts 31 in `Rm` (`wzr`);
- `csel` at 32 and 64 bits (`aarch64:csel/w32-w32-w32-cond4`,
  `aarch64:csel/x64-x64-x64-cond4`), with the condition as an
  `aarch64.cond`/`cond4` operand at bits 12-15; `eq`, `ne`, `al` and `nv`
  bracket the four-bit field.

The expected image is the measured `EXP-0118` `A64-P24-mul-csel.s`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0118/make_fixture.py
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/aarch64/positive/A64-P24-mul-csel"

EXPECTED = bytes.fromhex(
    "627c041b" "c57c079b" "207c1f1b"
    "28018a1a" "8b118d9a" "20e0829a" "83f0851a" "1fc0809a"
)

DIGEST = "sha256:05033c9e1c5ca430d2922312cf7139c9bc4e8cc7c34364e24a455efa9a1df6cd"

# (mnemonic, width, rd, rn, rm, cond). `cond` is None on the `mul` rows.
ROWS = [
    ("mul", "w32", 2, 3, 4, None),
    ("mul", "x64", 5, 6, 7, None),
    ("mul", "w32", 0, 1, 31, None),
    ("csel", "w32", 8, 9, 10, 0),
    ("csel", "x64", 11, 12, 13, 1),
    ("csel", "x64", 0, 1, 2, 14),
    ("csel", "w32", 3, 4, 5, 15),
    ("csel", "x64", 31, 0, 0, 12),
]


def operands(mnemonic: str, width: str, rd: int, rn: int, rm: int,
             cond) -> str:
    kind = "aarch64.gpr32" if width == "w32" else "aarch64.gpr64"
    rows = [
        '        { "role": "dest", "kind": "%s", "target_type": "%s", '
        '"payload": { "reg": %d }, "modifiers": [] }' % (kind, width, rd),
        '        { "role": "src", "kind": "%s", "target_type": "%s", '
        '"payload": { "reg": %d }, "modifiers": [] }' % (kind, width, rn),
        '        { "role": "src2", "kind": "%s", "target_type": "%s", '
        '"payload": { "reg": %d }, "modifiers": [] }' % (kind, width, rm),
    ]
    if cond is not None:
        rows.append(
            '        { "role": "imm", "kind": "aarch64.cond", '
            '"target_type": "cond4", "payload": { "value": %d }, '
            '"modifiers": [] }' % cond)
    return ",\n".join(rows)


def form_id(mnemonic: str, width: str) -> str:
    if mnemonic == "mul":
        return "aarch64:mul/%s-%s-%s" % (width, width, width)
    return "aarch64:csel/%s-%s-%s-cond4" % (width, width, width)


def main() -> int:
    if len(EXPECTED) != len(ROWS) * 4:
        raise SystemExit("expected bytes are not %d long" % (len(ROWS) * 4))
    fragments = []
    instructions = []
    for index, (mnemonic, width, rd, rn, rm, cond) in enumerate(ROWS):
        offset = index * 4
        instruction_id = "I%04d" % (index + 1)
        fragments.append(
            '        { "offset": %d, "size": 4, "kind": "instruction", '
            '"instruction_id": "%s" }' % (offset, instruction_id))
        instructions.append(
            "    {\n"
            '      "instruction_id": "%s",\n'
            '      "section_id": ".text",\n'
            '      "offset": %d,\n'
            '      "form_id": "%s",\n'
            '      "operands": [\n%s\n      ],\n'
            '      "expected_size": 4\n'
            "    }"
            % (instruction_id, offset, form_id(mnemonic, width),
               operands(mnemonic, width, rd, rn, rm, cond)))

    text = (
        "{\n"
        '  "format_version": "fmp/0.1",\n'
        '  "target_identity": {\n'
        '    "isa_family": "aarch64",\n'
        '    "isa_variant": "aarch64",\n'
        '    "execution_mode": "n/a",\n'
        '    "enabled_extensions": [],\n'
        '    "feature_constraints": [],\n'
        '    "byte_order": "little",\n'
        '    "address_width": 64\n'
        "  },\n"
        '  "definition_identity": {\n'
        '    "namespace": "monasm.isa.aarch64",\n'
        '    "version": "0.20.0",\n'
        '    "digest": "%s"\n'
        "  },\n"
        '  "output_contract": {\n'
        '    "artifact": "bytes",\n'
        '    "section_order": [".text"],\n'
        '    "fixup_record_order": "section_id,offset,fixup_id",\n'
        '    "include_symbol_table": false,\n'
        '    "emit_fixups": true\n'
        "  },\n"
        '  "sections": [\n'
        "    {\n"
        '      "section_id": ".text",\n'
        '      "section_kind": "code",\n'
        '      "image_backed": true,\n'
        '      "declared_size": %d,\n'
        '      "fragments": [\n%s\n      ]\n'
        "    }\n"
        "  ],\n"
        '  "symbols": [],\n'
        '  "instructions": [\n%s\n  ],\n'
        '  "fixups": []\n'
        "}\n"
        % (DIGEST, len(EXPECTED), ",\n".join(fragments),
           ",\n".join(instructions)))

    with FIXTURE.parent.joinpath("A64-P24-mul-csel.fmp.json").open(
            "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with FIXTURE.parent.joinpath("A64-P24-mul-csel.expected.bin").open(
            "wb") as handle:
        handle.write(EXPECTED)
    print("instructions: %d" % len(ROWS))
    print("bytes: %d" % len(EXPECTED))
    print("output sha256: %s" % hashlib.sha256(EXPECTED).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
