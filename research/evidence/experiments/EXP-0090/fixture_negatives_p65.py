#!/usr/bin/env python3
"""Emit the eight `X86-P65` negative fixtures.

Each case names a `0.61.0` no-base indexed `movl` row and violates exactly one
rule: the row is absent from `0.60.0` (load and store), the index operand is
missing, an extra base operand is supplied, the scale is `4`, a four-bit value
slot carries `16`, or an index slot carries a value below its window floor
(`4` on a row without `REX.X`, `0` on an extended row).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0090/fixture_negatives_p65.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.61.0"
DIGEST = "sha256:e5a57fc7f72d810283980e1c059ff4195b77b1bc3c5ff30ff830798d7dd91983"
PREVIOUS = "sha256:f951de4cc1532c3df5a8f715343d8a9e7a4b3ba302df49c9fa3fa2f85a45d7b1"

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


LOW_LOAD = "x86:mov/r32-addr32-index-disp32/legacy"                # `67 8b 04 0d 08 00 00 00`
LOW_STORE = "x86:mov/addr32-index-disp32-r32/legacy"               # `67 89 04 0d 08 00 00 00`
X_LOAD = "x86:mov/r32-addr32-index-ext-disp32/legacy"              # `67 42 8b 04 0d 08 00 00 00`
RX_LOAD = "x86:mov/r32-ext-addr32-index-ext-disp32/legacy"         # `67 46 8b 04 0d 08 00 00 00`

CASES = [
    # The rows are new in 0.61.0, so 0.60.0 must reject both directions.
    (
        "N01dx-absent-addr32-32bit-no-base-load-row-on-0.60.0",
        "0.60.0",
        PREVIOUS,
        8,
        LOW_LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01dy-absent-addr32-32bit-no-base-store-row-on-0.60.0",
        "0.60.0",
        PREVIOUS,
        8,
        LOW_STORE,
        [reg("src", "x86.gpr32", "r32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has four slots, so dropping the index is a role-sequence miss.
    (
        "N02ci-missing-index-operand-on-addr32-32bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        RX_LOAD,
        [reg("dest", "x86.gpr32", "r32", 8), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The shape has no base role, so a supplied base is the same miss.
    (
        "N02cj-extra-base-operand-on-addr32-32bit-no-base-row",
        VERSION,
        DIGEST,
        8,
        LOW_LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
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
        "N03zn-scale4-on-addr32-32bit-no-base-row",
        VERSION,
        DIGEST,
        8,
        LOW_LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/2/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The four-bit value slot holds 0-15; 16 is past its end.
    (
        "N14by-register16-on-addr32-32bit-no-base-row",
        VERSION,
        DIGEST,
        9,
        RX_LOAD,
        [reg("dest", "x86.gpr32", "r32", 16),
         reg("index", "x86.gpr32", "sib_index32", 9), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
        }],
    ),
    # The bare row leaves REX.X at 0, so index 4 is the "no index" constant.
    (
        "N16dc-index4-on-addr32-32bit-no-base-row",
        VERSION,
        DIGEST,
        8,
        LOW_LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("index", "x86.gpr32", "sib_index32", 4), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The RX row fixes X = 1, so the index slot's floor is 8.
    (
        "N16dd-index0-on-addr32-32bit-no-base-ext-row",
        VERSION,
        DIGEST,
        9,
        RX_LOAD,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("index", "x86.gpr32", "sib_index32", 0), scale(0), disp(8)],
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
