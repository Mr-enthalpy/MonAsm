#!/usr/bin/env python3
"""Emit the nine `X86-P54` negative fixtures.

Each case names a `0.50.0` 32-bit indexed `mov` `REX` window row and violates
exactly one rule: the row is absent from `0.49.0` (both directions), the index
operand is missing, the scale is `4` (past the two-bit field), an operand that
should stay in the low window is `8` (register on the `REX.B` row, base on the
`REX.X` row), or a window slot is below its floor (register on `REX.R`, base on
`REX.B`, index on `REX.X`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0079/fixture_negatives_p54.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.50.0"
DIGEST = "sha256:6f38e272ef1464b5067053c7a10d744adee19699fbe4ecbc0928fb3c8f7da75a"
PREVIOUS = "sha256:5a7ec114d02101465839a60645c4cfb8b4527dab766a6c90f801e0b38161ccd0"

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


LOAD_R = "x86:mov/r32-ext-base-index-disp8/legacy"     # `44 8b 44 08 08`
STORE_B = "x86:mov/base-ext-index-disp8-r32/legacy"    # `41 89 44 08 08`
STORE_X = "x86:mov/base-index-ext-disp8-r32/legacy"    # `42 89 44 08 08`

CASES = [
    # The rows are new in 0.50.0, so 0.49.0 must reject both names.
    (
        "N01db-absent-gpr32-mov-index-rex-r-load-row-on-0.49.0",
        "0.49.0",
        PREVIOUS,
        5,
        LOAD_R,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01dc-absent-gpr32-mov-index-rex-b-store-row-on-0.49.0",
        "0.49.0",
        PREVIOUS,
        5,
        STORE_B,
        [reg("src", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02bt-missing-index-operand-on-gpr32-mov-index-rex-row",
        VERSION,
        DIGEST,
        5,
        LOAD_R,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 0), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03zc-scale4-on-gpr32-mov-index-rex-row",
        VERSION,
        DIGEST,
        5,
        LOAD_R,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The register stays low on the REX.B row, so 8 is past its three-bit field.
    (
        "N14bi-register8-on-gpr32-mov-index-rex-b-row",
        VERSION,
        DIGEST,
        5,
        STORE_B,
        [reg("src", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The base stays low on the REX.X row, so 8 is past its three-bit field.
    (
        "N14bj-base8-on-gpr32-mov-index-rex-x-row",
        VERSION,
        DIGEST,
        5,
        STORE_X,
        [reg("src", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 9), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The REX.R window starts at 8, so register 3 would clear the fixed bit.
    (
        "N16cd-register3-on-gpr32-mov-index-rex-r-row",
        VERSION,
        DIGEST,
        5,
        LOAD_R,
        [reg("dest", "x86.gpr32", "r32", 3),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The REX.B window starts at 8, so base 3 would clear the fixed bit.
    (
        "N16ce-base3-on-gpr32-mov-index-rex-b-row",
        VERSION,
        DIGEST,
        5,
        STORE_B,
        [reg("src", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 3),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The REX.X window starts at 8, so index 3 would clear the fixed bit.
    (
        "N16cf-index3-on-gpr32-mov-index-rex-x-row",
        VERSION,
        DIGEST,
        5,
        STORE_X,
        [reg("src", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 3), scale(0), disp(8)],
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
