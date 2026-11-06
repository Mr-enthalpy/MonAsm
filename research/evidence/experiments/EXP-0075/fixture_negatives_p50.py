#!/usr/bin/env python3
"""Emit the eight `X86-P50` negative fixtures.

Each case names a `0.46.0` low-register 16-bit indexed `mov` row and violates
exactly one rule: the row is absent from `0.45.0` (both directions), the index
operand is missing, the scale is `4` (past the two-bit field), the register is
past the target type or past the three-bit field (it would need a `REX.R` the
row does not have), the base is past the three-bit field, or the index is `4`
(`%rsp`, the "no index" encoding).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0075/fixture_negatives_p50.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.46.0"
DIGEST = "sha256:44a396f348cc940bdf247c21e4752358d929df952ea0c7f2e5b5be14a63e2e9e"
PREVIOUS = "sha256:9adaf50a6798c7b4bd5f0090f9860de30e360994c45138f017a3c1298e5fc2d8"

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


LOAD8 = "x86:mov/r16-base-index-disp8/legacy"    # `66 8b 44 08 08`
STORE8 = "x86:mov/base-index-disp8-r16/legacy"   # `66 89 44 08 08`

CASES = [
    # Both directions are new in 0.46.0, so 0.45.0 must reject the names.
    (
        "N01ct-absent-gpr16-mov-index-disp8-low-load-row-on-0.45.0",
        "0.45.0",
        PREVIOUS,
        5,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01cu-absent-gpr16-mov-index-disp8-low-store-row-on-0.45.0",
        "0.45.0",
        PREVIOUS,
        5,
        STORE8,
        [reg("src", "x86.gpr16", "r16", 7),
         reg("base", "x86.gpr64", "rm64", 7),
         reg("index", "x86.gpr64", "sib_index", 6), scale(2), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02bp-missing-index-operand-on-gpr16-mov-index-disp8-low-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 0), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a ×16 multiplier) does not fit.
    (
        "N03y-scale4-on-gpr16-mov-index-disp8-low-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The register window is four bits, so 16 is past its end.
    (
        "N14ba-register16-on-gpr16-mov-index-disp8-low-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 16),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # Without a `REX.R` the register field is only three bits, so 8 is past it.
    (
        "N14bb-register8-on-gpr16-mov-index-disp8-low-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # Without a `REX.B` the base field is only three bits, so 8 is past it.
    (
        "N14bc-base8-on-gpr16-mov-index-disp8-low-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # `SIB.index = 100` with no `REX.X` means "no index", so `%rsp` is illegal.
    (
        "N16bx-index4-on-gpr16-mov-index-disp8-low-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 4), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
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
