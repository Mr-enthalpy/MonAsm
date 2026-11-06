#!/usr/bin/env python3
"""Emit the five `X86-P38` negative fixtures.

Each case names a `0.34.0` `%rsp`/`%r12` no-displacement `SIB` row and violates
exactly one rule: the row is absent from `0.33.0` (a load and a store), a
`base` operand is supplied to a row whose address is fixed in the template, a
`disp` operand is supplied there, or the register is one past the four-bit
field.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0063/fixture_negatives_p38.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.34.0"
DIGEST = "sha256:03368b63e89e40d4cc0c58f7b394110e6dcc2e69bd801d469fa8adc505ad117f"
PREVIOUS = "sha256:b6659c62116dab7bf79f6c9704844d0fd9a1ad27ac8780e2071a93cf28dd6d8e"

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


def disp(target_type, value) -> str:
    return operand("disp", "x86.imm", target_type, {"value": value})


LOAD_RSP = "x86:mov/r64-rsp/legacy"      # `48 8b 04 24`
STORE_R12 = "x86:mov/r12-r64/legacy"     # `49 89 04 24`

CASES = [
    # The load row is new in 0.34.0, so 0.33.0 must reject the name rather
    # than fall back to the disp8 row (which needs a displacement operand).
    (
        "N01bv-absent-gpr64-mov-mem-sib-load-row-on-0.33.0",
        "0.33.0",
        PREVIOUS,
        4,
        LOAD_RSP,
        [
            reg("dest", "x86.gpr64", "r64", 0),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store row carries its own boundary, at the top of the field.
    (
        "N01bw-absent-gpr64-mov-mem-sib-store-row-on-0.33.0",
        "0.33.0",
        PREVIOUS,
        4,
        STORE_R12,
        [
            reg("src", "x86.gpr64", "r64", 15),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The base is in the template, so a `base` operand is a count mismatch.
    (
        "N02bb-extra-base-operand-on-gpr64-mov-mem-sib-row",
        VERSION,
        DIGEST,
        4,
        LOAD_RSP,
        [
            reg("dest", "x86.gpr64", "r64", 0),
            reg("base", "x86.gpr64", "rm64", 4),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `mod = 00` carries no displacement byte on this shape either.
    (
        "N02bc-extra-disp-operand-on-gpr64-mov-mem-sib-row",
        VERSION,
        DIGEST,
        4,
        STORE_R12,
        [
            reg("src", "x86.gpr64", "r64", 0),
            disp("disp8", 0),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # Four bits reach `r15`; `r16` is one past the field.
    (
        "N14ai-register16-on-gpr64-mov-mem-sib-row",
        VERSION,
        DIGEST,
        4,
        LOAD_RSP,
        [
            reg("dest", "x86.gpr64", "r64", 16),
        ],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
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
