#!/usr/bin/env python3
"""Emit the seven `X86-P53` negative fixtures.

Each case names a `0.49.0` 32-bit `mov` indexed row whose register, base and
index are all in the low window, and violates exactly one rule: the row is
absent from `0.48.0` (both directions), the index operand is missing, the scale
is `4` (past the two-bit field), the register is past the three-bit field, the
base is past the three-bit field, or the index is `4` (the "no index"
encoding).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0078/fixture_negatives_p53.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.49.0"
DIGEST = "sha256:5a7ec114d02101465839a60645c4cfb8b4527dab766a6c90f801e0b38161ccd0"
PREVIOUS = "sha256:552b82733ac35ec9d6270dbab21bef8b19f3de800f25fc7f9c0654c4eb6189ff"

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


LOAD = "x86:mov/r32-base-index-disp8/legacy"    # `8b 44 08 08`
STORE = "x86:mov/base-index-disp8-r32/legacy"   # `89 44 08 08`

CASES = [
    # The rows are new in 0.49.0, so 0.48.0 must reject both names.
    (
        "N01cz-absent-gpr32-mov-index-load-row-on-0.48.0",
        "0.48.0",
        PREVIOUS,
        4,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01da-absent-gpr32-mov-index-store-row-on-0.48.0",
        "0.48.0",
        PREVIOUS,
        4,
        STORE,
        [reg("src", "x86.gpr32", "r32", 7),
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
        "N02bs-missing-index-operand-on-gpr32-mov-index-row",
        VERSION,
        DIGEST,
        4,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 0), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03zb-scale4-on-gpr32-mov-index-row",
        VERSION,
        DIGEST,
        4,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The register field is three bits, so 8 (which needs REX.R) does not fit.
    (
        "N14bg-register8-on-gpr32-mov-index-row",
        VERSION,
        DIGEST,
        4,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The base field is three bits, so 8 (which needs REX.B) does not fit.
    (
        "N14bh-base8-on-gpr32-mov-index-row",
        VERSION,
        DIGEST,
        4,
        STORE,
        [reg("src", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # SIB.index = 100 with no REX.X means "no index", so 4 is excluded.
    (
        "N16cc-index4-on-gpr32-mov-index-row",
        VERSION,
        DIGEST,
        4,
        STORE,
        [reg("src", "x86.gpr32", "r32", 0),
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
