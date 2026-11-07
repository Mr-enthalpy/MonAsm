#!/usr/bin/env python3
"""Emit the eight `X86-P66` negative fixtures.

Each case names a `0.62.0` no-base indexed `movq` row and violates exactly one
rule: the row is absent from `0.61.0` (load and store), the index operand is
missing, an extra base operand is supplied, the scale is `4`, the four-bit
value slot carries `16`, the four-bit index slot carries `16`, or the index is
`4` (the `REX.X = 0` "no index" constant).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0091/fixture_negatives_p66.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.62.0"
DIGEST = "sha256:bbcd8062c84580e208c1cbf275254593a7d937fd7de28fde19e7dc5c5049e3b3"
PREVIOUS = "sha256:e5a57fc7f72d810283980e1c059ff4195b77b1bc3c5ff30ff830798d7dd91983"

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
    return operand("disp", "x86.imm", "disp32", {"value": value})


LOAD = "x86:mov/r64-addr32-index-disp32/legacy"     # `67 48 8b 04 0d 08 00 00 00`
STORE = "x86:mov/addr32-index-disp32-r64/legacy"    # `67 48 89 04 0d 08 00 00 00`

CASES = [
    # The rows are new in 0.62.0, so 0.61.0 must reject both directions.
    (
        "N01dz-absent-addr32-64bit-no-base-load-row-on-0.61.0",
        "0.61.0",
        PREVIOUS,
        9,
        LOAD,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01ea-absent-addr32-64bit-no-base-store-row-on-0.61.0",
        "0.61.0",
        PREVIOUS,
        9,
        STORE,
        [reg("src", "x86.gpr64", "r64", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has four slots, so dropping the index is a role-sequence miss.
    (
        "N02ck-missing-index-operand-on-addr32-64bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        LOAD,
        [reg("dest", "x86.gpr64", "r64", 0), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The shape has no base role, so a supplied base is the same miss.
    (
        "N02cl-extra-base-operand-on-addr32-64bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        LOAD,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03zo-scale4-on-addr32-64bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        LOAD,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/2/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The value slot is four bits (REX.R plus ModRM.reg); 16 is past its end.
    (
        "N14bz-value-register16-on-addr32-64bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        LOAD,
        [reg("dest", "x86.gpr64", "r64", 16),
         reg("index", "x86.gpr32", "sib_index32", 9), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
        }],
    ),
    # The index slot is four bits (REX.X plus SIB.index); 16 is past its end.
    (
        "N14ca-index-register16-on-addr32-64bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        LOAD,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("index", "x86.gpr32", "sib_index32", 16), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
        }],
    ),
    # Index 4 with REX.X = 0 is the "no index" constant, not %rsp.
    (
        "N16de-index4-on-addr32-64bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        LOAD,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("index", "x86.gpr32", "sib_index32", 4), scale(0), disp(8)],
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
