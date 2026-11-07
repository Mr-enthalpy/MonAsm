#!/usr/bin/env python3
"""Emit the eight `X86-P62` negative fixtures.

Each case names a `0.58.0` `0x67 66` single-`REX` `movw` row and violates
exactly one rule: the row is absent from `0.57.0` (load and store), the index
operand is missing, the fixed bit's slot carries a low register (`0`), the
scale is `4`, or a three-bit register slot carries `16`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0087/fixture_negatives_p62.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.58.0"
DIGEST = "sha256:8e7fc7e799ede398cb5d560b2ca43991c11cba518cadae45f84222bbf93994bf"
PREVIOUS = "sha256:4b41ac755862f46d9e9e8bd574c399d8aa6a771cf93358772e590fae11314ca7"

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


R_LOAD8 = "x86:mov/r16-ext-addr32-base-index-disp8/legacy"      # `67 66 44 8b 44 08 08`
R_STORE8 = "x86:mov/addr32-base-index-disp8-r16-ext/legacy"     # `67 66 44 89 44 08 08`
B_LOAD8 = "x86:mov/r16-addr32-base-ext-index-disp8/legacy"      # `67 66 41 8b 44 08 08`
X_LOAD8 = "x86:mov/r16-addr32-base-index-ext-disp8/legacy"      # `67 66 42 8b 44 08 08`

CASES = [
    # The rows are new in 0.58.0, so 0.57.0 must reject both directions.
    (
        "N01dr-absent-addr32-16bit-rex-r-load-row-on-0.57.0",
        "0.57.0",
        PREVIOUS,
        7,
        R_LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01ds-absent-addr32-16bit-rex-r-store-row-on-0.57.0",
        "0.57.0",
        PREVIOUS,
        7,
        R_STORE8,
        [reg("src", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02ce-missing-index-operand-on-addr32-16bit-rex-row",
        VERSION,
        DIGEST,
        7,
        R_LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr32", "rm32", 0), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The REX.R row fixes R = 1, so the value slot excludes 0-7.
    (
        "N16cu-register0-on-addr32-16bit-rex-r-row",
        VERSION,
        DIGEST,
        7,
        R_LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The REX.B row fixes B = 1, so the base slot excludes 0-7.
    (
        "N16cv-base0-on-addr32-16bit-rex-b-row",
        VERSION,
        DIGEST,
        7,
        B_LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The REX.X row fixes X = 1, so the index slot excludes 0-7.
    (
        "N16cw-index0-on-addr32-16bit-rex-x-row",
        VERSION,
        DIGEST,
        7,
        X_LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 0), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03zk-scale4-on-addr32-16bit-rex-row",
        VERSION,
        DIGEST,
        7,
        R_LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # A three-bit slot holds 0-7; 16 is past its end.
    (
        "N14bv-register16-on-addr32-16bit-rex-row",
        VERSION,
        DIGEST,
        7,
        R_LOAD8,
        [reg("dest", "x86.gpr16", "r16", 16),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
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
