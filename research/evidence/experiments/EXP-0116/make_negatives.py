#!/usr/bin/env python3
"""Build the S5 negative plans and their registered diagnostics.

Three cases (`ADR-0117`):

- `N01fd`: `fence` has no row in any version (`EC-24`);
- `N01fe`: a new `0.6.0` row named against the previous `0.5.0` table;
- `N03a0`: `disp = 2048` is one past the signed 12-bit load/store field.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0116/make_negatives.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/rv64/negative"

DIGEST_0500 = "sha256:571ab1ed93f4464d5ec8981df02dd0444005ababdaaf1e175d0ec489bb33a776"
DIGEST_0600 = "sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585"

FORM_KEYS = ["form_id", "namespace", "version"]
RANGE_KEYS = ["min", "max", "value", "target_type"]


def operand(role: str, kind: str, target_type: str, payload: str) -> str:
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }'
            % (role, kind, target_type, payload))


def plan(version: str, digest: str, form_id: str, operands: list) -> str:
    return (
        "{\n"
        '  "format_version": "fmp/0.1",\n'
        '  "target_identity": {\n'
        '    "isa_family": "riscv",\n'
        '    "isa_variant": "rv64",\n'
        '    "execution_mode": "n/a",\n'
        '    "enabled_extensions": ["rv64i", "rv64c"],\n'
        '    "feature_constraints": [],\n'
        '    "byte_order": "little",\n'
        '    "address_width": 64\n'
        "  },\n"
        '  "definition_identity": {\n'
        '    "namespace": "monasm.isa.riscv",\n'
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


CASES = [
    (
        "N01fd-absent-fence-form",
        plan("0.6.0", DIGEST_0600, "riscv:fence/fm-pred-succ-imm12", [
            operand("imm", "riscv.imm", "imm12", '{ "value": 0 }'),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01fe-load-store-row-on-0.5.0",
        plan("0.5.0", DIGEST_0500, "riscv:lw/rd-base-imm12", [
            operand("dest", "riscv.xreg", "xreg", '{ "reg": 10 }'),
            operand("base", "riscv.xreg", "xreg", '{ "reg": 11 }'),
            operand("disp", "riscv.imm", "imm12", '{ "value": 8 }'),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N03a0-sw-imm12-past-signed-12",
        plan("0.6.0", DIGEST_0600, "riscv:sw/rs-base-imm12", [
            operand("src", "riscv.xreg", "xreg", '{ "reg": 12 }'),
            operand("base", "riscv.xreg", "xreg", '{ "reg": 11 }'),
            operand("disp", "riscv.imm", "imm12", '{ "value": 2048 }'),
        ]),
        [{"code": "E-RANGE-001",
          "path": "/instructions/0/operands/2/payload/value",
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
