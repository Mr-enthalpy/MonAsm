#!/usr/bin/env python3
"""Emit the eight `X86-P51` negative fixtures.

Each case names a `0.47.0` low-register 16-bit indexed `mov` row and violates
exactly one rule: the row is absent from `0.46.0` (both windows), the index
operand is missing, the scale is `4` (past the two-bit field), the register is
past the three-bit field, the base on an `-index-ext` row is past the three-bit
field, the index on an `-index-ext` row is still in the low window (it would
clear the fixed `REX.X`), or the base on a `-base-ext` row is still low (it
would clear the fixed `REX.B`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0076/fixture_negatives_p51.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.47.0"
DIGEST = "sha256:0894646319c6f42071b0fd9d24417e27246a49343144540c80d05e49da7045c3"
PREVIOUS = "sha256:44a396f348cc940bdf247c21e4752358d929df952ea0c7f2e5b5be14a63e2e9e"

HEADER = """{
  "format_version": "fmp/0.1",
  "target_identity": {
    "isa_family": "x86",
    "isa_variant": "x86-64",
    "execution_mode": "64",
    "enabled_extensions": ["avx", "avx512f", "avx512vl"],
    "feature_constraints": [],
    "byte_order": "little",
    "address_width": 64
  },
  "definition_identity": {
    "namespace": "monasm.isa.x86",
    "version": "%s",
    "digest": "%s"
  },
  "output_contract": {
    "artifact": "bytes",
    "section_order": [".text"],
    "fixup_record_order": "section_id,offset,fixup_id",
    "include_symbol_table": false,
    "emit_fixups": true
  },
  "sections": [
    {
      "section_id": ".text",
      "section_kind": "code",
      "image_backed": true,
      "declared_size": %d,
      "fragments": [
        { "offset": 0, "size": %d, "kind": "instruction", "instruction_id": "I0001" }
      ]
    }
  ],
  "symbols": [],
  "instructions": [
    {
      "instruction_id": "I0001",
      "section_id": ".text",
      "offset": 0,
      "form_id": "%s",
      "operands": [
%s
      ],
      "expected_size": %d
    }
  ],
  "fixups": []
}
"""


def operand(role, kind, target_type, payload) -> str:
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }'
            % (role, kind, target_type, json.dumps(payload)))


def reg(role, kind, target_type, number) -> str:
    return operand(role, kind, target_type, {"reg": number})


def scale(value) -> str:
    return operand("imm", "x86.scale", "scale2", {"value": value})


def disp(value) -> str:
    return operand("disp", "x86.imm", "disp8", {"value": value})


LOAD_BASE = "x86:mov/r16-base-ext-index-disp8/legacy"    # `66 41 8b 44 08 08`
STORE_INDEX = "x86:mov/base-index-ext-disp8-r16/legacy"  # `66 42 89 44 08 08`

CASES = [
    # Both windows are new in 0.47.0, so 0.46.0 must reject the names.
    (
        "N01cv-absent-gpr16-mov-index-base-ext-load-row-on-0.46.0",
        "0.46.0",
        PREVIOUS,
        6,
        LOAD_BASE,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01cw-absent-gpr16-mov-index-ext-store-row-on-0.46.0",
        "0.46.0",
        PREVIOUS,
        6,
        STORE_INDEX,
        [reg("src", "x86.gpr16", "r16", 7),
         reg("base", "x86.gpr64", "rm64", 7),
         reg("index", "x86.gpr64", "sib_index", 15), scale(3), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02bq-missing-index-operand-on-gpr16-mov-index-base-ext-row",
        VERSION,
        DIGEST,
        6,
        LOAD_BASE,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 8), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03z-scale4-on-gpr16-mov-index-base-ext-row",
        VERSION,
        DIGEST,
        6,
        LOAD_BASE,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The register stays in the low window, so 8 is past its three-bit field.
    (
        "N14bd-register8-on-gpr16-mov-index-base-ext-row",
        VERSION,
        DIGEST,
        6,
        LOAD_BASE,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # An `-index-ext` row has no `REX.B`, so base 8 is past its three-bit field.
    (
        "N14be-base8-on-gpr16-mov-index-ext-row",
        VERSION,
        DIGEST,
        6,
        STORE_INDEX,
        [reg("src", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 9), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The `-index-ext` window starts at 8, so 3 would clear the fixed `REX.X`.
    (
        "N16by-index3-on-gpr16-mov-index-ext-row",
        VERSION,
        DIGEST,
        6,
        STORE_INDEX,
        [reg("src", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 3), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The `-base-ext` window starts at 8, so 3 would clear the fixed `REX.B`.
    (
        "N16bz-base3-on-gpr16-mov-index-base-ext-row",
        VERSION,
        DIGEST,
        6,
        LOAD_BASE,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 3),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
]


def main() -> int:
    for name, version, digest, size, form_id, operands, errors in CASES:
        body = ",\n".join(operands)
        plan = HEADER % (version, digest, size, size, form_id, body, size)
        plan_path = TARGET / ("%s.fmp.json" % name)
        with plan_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(plan)
        error_path = TARGET / ("%s.expected-error.json" % name)
        with error_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"errors": errors}, indent=2) + "\n")
    print("%d negative fixtures" % len(CASES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
