#!/usr/bin/env python3
"""Build the `A64-P23` plan and expected bytes.

Eight `adr` instructions in one `0.19.0` form (`aarch64:adr/x64-imm21`):

- five literal byte displacements, including both ends of the signed 21-bit
  range (`1048575` and `-1048576`);
- three symbol targets: `S1` at 20 from the site (displacement 0), `S2` at 0
  (`-24`), and `S1` again from offset 28 (`-8`).

The expected image is the measured `EXP-0117` `A64-P23-adr-imm21.s`. The three
symbol sites carry the same `field_descriptor` as `adrp` (`immhi` at 5+19,
`immlo` at 29+2), but the transform is `identity` with `pcrel_begin`: a byte
displacement, not a page delta, so the field content is the displacement
itself. `pcrel_page` + `page` would name a different reference and shift.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0117/make_fixture.py
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/aarch64/positive/A64-P23-adr-imm21"

EXPECTED = bytes.fromhex(
    "00000010" "41000010" "c2ffff10" "e3ff7f70"
    "04008010" "05000010" "46ffff10" "c7ffff10"
)

DIGEST = "sha256:f299d978b734a295fe111f6e03999d891d08a84e6d02c36ce83ee9a25c961546"

# (rd, immediate payload) — the five literal rows.
LITERALS = [(0, 0), (1, 8), (2, -8), (3, 1048575), (4, -1048576)]

# (offset, rd, symbol) — the three symbol rows.
SYMBOLS = [(20, 5, "S1"), (24, 6, "S2"), (28, 7, "S1")]

TOTAL = len(LITERALS) + len(SYMBOLS)


def operand(role: str, kind: str, target_type: str, payload: str) -> str:
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }'
            % (role, kind, target_type, payload))


def main() -> int:
    if len(EXPECTED) != TOTAL * 4:
        raise SystemExit("expected bytes are not %d long" % (TOTAL * 4))
    fragments = []
    instructions = []
    fixups = []
    n = 0
    for rd, value in LITERALS:
        offset = n * 4
        n += 1
        instruction_id = "I%04d" % n
        fragments.append(
            '        { "offset": %d, "size": 4, "kind": "instruction", '
            '"instruction_id": "%s" }' % (offset, instruction_id))
        instructions.append(
            "    {\n"
            '      "instruction_id": "%s",\n'
            '      "section_id": ".text",\n'
            '      "offset": %d,\n'
            '      "form_id": "aarch64:adr/x64-imm21",\n'
            '      "operands": [\n'
            "%s,\n%s\n"
            "      ],\n"
            '      "expected_size": 4\n'
            "    }"
            % (instruction_id, offset,
               operand("dest", "aarch64.gpr64", "x64",
                       '{ "reg": %d }' % rd),
               operand("target", "aarch64.rel", "imm21",
                       '{ "value": %d }' % value)))
    for offset, rd, symbol in SYMBOLS:
        n += 1
        instruction_id = "I%04d" % n
        fragments.append(
            '        { "offset": %d, "size": 4, "kind": "instruction", '
            '"instruction_id": "%s" }' % (offset, instruction_id))
        instructions.append(
            "    {\n"
            '      "instruction_id": "%s",\n'
            '      "section_id": ".text",\n'
            '      "offset": %d,\n'
            '      "form_id": "aarch64:adr/x64-imm21",\n'
            '      "operands": [\n'
            "%s,\n%s\n"
            "      ],\n"
            '      "expected_size": 4\n'
            "    }"
            % (instruction_id, offset,
               operand("dest", "aarch64.gpr64", "x64",
                       '{ "reg": %d }' % rd),
               operand("target", "aarch64.rel", "imm21",
                       '{ "symbol_id": "%s" }' % symbol)))
        fixups.append(
            "    {\n"
            '      "fixup_id": "F%04d",\n'
            '      "section_id": ".text",\n'
            '      "offset": %d,\n'
            '      "field_descriptor": [ { "lsb": 5, "width": 19 }, '
            '{ "lsb": 29, "width": 2 } ],\n'
            '      "target": { "kind": "symbol", "symbol_id": "%s" },\n'
            '      "addend": 0,\n'
            '      "pc_reference_rule": "pcrel_begin",\n'
            '      "value_transform": "identity",\n'
            '      "range_constraint": { "signed": true, "bits": 21, '
            '"align_bits": 0 },\n'
            '      "resolution_mode": "resolve_in_place"\n'
            "    }"
            % (len(fixups) + 1, offset, symbol))

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
        '    "version": "0.19.0",\n'
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
        '  "symbols": [\n'
        '    { "symbol_id": "S1", "name": "ahead", "kind": "defined", '
        '"binding": "local", "section_id": ".text", "offset": 20 },\n'
        '    { "symbol_id": "S2", "name": "back", "kind": "defined", '
        '"binding": "local", "section_id": ".text", "offset": 0 }\n'
        "  ],\n"
        '  "instructions": [\n%s\n  ],\n'
        '  "fixups": [\n%s\n  ]\n'
        "}\n"
        % (DIGEST, len(EXPECTED), ",\n".join(fragments),
           ",\n".join(instructions), ",\n".join(fixups)))

    with FIXTURE.parent.joinpath(
            "A64-P23-adr-imm21.fmp.json").open(
                "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with FIXTURE.parent.joinpath(
            "A64-P23-adr-imm21.expected.bin").open("wb") as handle:
        handle.write(EXPECTED)
    print("instructions: %d" % TOTAL)
    print("bytes: %d" % len(EXPECTED))
    print("output sha256: %s" % hashlib.sha256(EXPECTED).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
