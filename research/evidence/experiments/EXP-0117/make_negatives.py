#!/usr/bin/env python3
"""Build the S6 negative plans and their registered diagnostics.

Three cases (`ADR-0118`):

- `N01ff`: the page variant of the row does not exist — `adr` never reaches
  `adrp`, whose row is `aarch64:adrp/x64-imm21` (`EC-43`);
- `N01fg`: the new `0.19.0` row named against the previous `0.18.0` table;
- `N04k`: `1048576` is one past the signed 21-bit byte displacement.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0117/make_negatives.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/aarch64/negative"

DIGEST_0180 = "sha256:c32e3674bf50140276d29fd01891bab20a86b849fa1503d2c9d02ae6aa503824"
DIGEST_0190 = "sha256:f299d978b734a295fe111f6e03999d891d08a84e6d02c36ce83ee9a25c961546"

FORM_KEYS = ["form_id", "namespace", "version"]
RANGE_KEYS = ["min", "max", "value", "bits", "align_bits"]


def operand(role: str, kind: str, target_type: str, payload: str) -> str:
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }'
            % (role, kind, target_type, payload))


def plan(version: str, digest: str, form_id: str, operands: list) -> str:
    return (
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
        '    "version": "%s",\n'
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
        '      "declared_size": 4,\n'
        '      "fragments": [\n'
        '        { "offset": 0, "size": 4, "kind": "instruction", '
        '"instruction_id": "I0001" }\n'
        "      ]\n"
        "    }\n"
        "  ],\n"
        '  "symbols": [],\n'
        '  "instructions": [\n'
        "    {\n"
        '      "instruction_id": "I0001",\n'
        '      "section_id": ".text",\n'
        '      "offset": 0,\n'
        '      "form_id": "%s",\n'
        '      "operands": [\n%s\n      ],\n'
        '      "expected_size": 4\n'
        "    }\n"
        "  ],\n"
        '  "fixups": []\n'
        "}\n"
        % (version, digest, form_id, ",\n".join(operands)))

DEST = operand("dest", "aarch64.gpr64", "x64", '{ "reg": 0 }')

CASES = [
    (
        "N01ff-adr-page-variant-absent",
        plan("0.19.0", DIGEST_0190, "aarch64:adr/x64-imm21-page", [
            DEST,
            operand("target", "aarch64.rel", "imm21", '{ "value": 0 }'),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01fg-adr-row-on-0.18.0",
        plan("0.18.0", DIGEST_0180, "aarch64:adr/x64-imm21", [
            DEST,
            operand("target", "aarch64.rel", "imm21", '{ "value": 0 }'),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N04k-adr-imm21-out-of-range",
        plan("0.19.0", DIGEST_0190, "aarch64:adr/x64-imm21", [
            DEST,
            operand("target", "aarch64.rel", "imm21",
                    '{ "value": 1048576 }'),
        ]),
        [{"code": "E-RANGE-002",
          "path": "/instructions/0/operands/1/payload/value",
          "detail_keys": RANGE_KEYS}],
    ),
]


def main() -> int:
    for stem, text, errors in CASES:
        with (NEGATIVE / (stem + ".fmp.json")).open(
                "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        with (NEGATIVE / (stem + ".expected-error.json")).open(
                "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"errors": errors}, indent=2) + "\n")
        print(stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
