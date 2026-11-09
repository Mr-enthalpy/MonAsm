#!/usr/bin/env python3
"""Build the S7 negative plans and their registered diagnostics.

Four cases (`ADR-0119`):

- `N01fh`: the `madd` shape (`aarch64:mul/x64-x64-x64-x64`, four operands,
  a plan-supplied accumulator) is not a row; the alias fixes `Ra = 31`
  (`EC-44`);
- `N01fi`: the new `0.20.0` rows named against the previous `0.19.0` table;
- `N02dd`: a `mul` with two operands, proving the accumulator is not one of
  them and the destination is required;
- `N03a1`: `cond = 16` is one past the four-bit condition field. The code is
  `E-RANGE-001`, not `E-OPERAND-004`: `cond` is an immediate range, and the
  plan's S7 line is corrected here (the same shape as `N03-cond-out-of-range`
  on `b.cond`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0118/make_negatives.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/aarch64/negative"

DIGEST_0190 = "sha256:f299d978b734a295fe111f6e03999d891d08a84e6d02c36ce83ee9a25c961546"
DIGEST_0200 = "sha256:05033c9e1c5ca430d2922312cf7139c9bc4e8cc7c34364e24a455efa9a1df6cd"

FORM_KEYS = ["form_id", "namespace", "version"]
OPERAND_KEYS = ["expected", "found"]
RANGE_KEYS = ["min", "max", "value", "target_type"]


def operand(role: str, kind: str, target_type: str, payload: str) -> str:
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }'
            % (role, kind, target_type, payload))


def register(role: str, width: str, number: int) -> str:
    kind = "aarch64.gpr32" if width == "w32" else "aarch64.gpr64"
    return operand(role, kind, width, '{ "reg": %d }' % number)


def condition(value: int) -> str:
    return operand("imm", "aarch64.cond", "cond4",
                   '{ "value": %d }' % value)


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


CASES = [
    (
        "N01fh-madd-shape-named-mul",
        plan("0.20.0", DIGEST_0200, "aarch64:mul/x64-x64-x64-x64", [
            register("dest", "x64", 0),
            register("src", "x64", 1),
            register("src2", "x64", 2),
            register("src3", "x64", 3),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01fi-mul-csel-row-on-0.19.0",
        plan("0.19.0", DIGEST_0190, "aarch64:csel/x64-x64-x64-cond4", [
            register("dest", "x64", 0),
            register("src", "x64", 1),
            register("src2", "x64", 2),
            condition(0),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N02dd-mul-missing-src2",
        plan("0.20.0", DIGEST_0200, "aarch64:mul/x64-x64-x64", [
            register("dest", "x64", 0),
            register("src", "x64", 1),
        ]),
        [{"code": "E-OPERAND-002", "path": "/instructions/0/operands",
          "detail_keys": OPERAND_KEYS}],
    ),
    (
        "N03a1-csel-cond-out-of-range",
        plan("0.20.0", DIGEST_0200, "aarch64:csel/w32-w32-w32-cond4", [
            register("dest", "w32", 0),
            register("src", "w32", 1),
            register("src2", "w32", 2),
            condition(16),
        ]),
        [{"code": "E-RANGE-001",
          "path": "/instructions/0/operands/3/payload/value",
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
