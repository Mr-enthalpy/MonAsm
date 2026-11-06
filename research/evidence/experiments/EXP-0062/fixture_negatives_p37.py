#!/usr/bin/env python3
"""Emit the eight `X86-P37` negative fixtures.

Each case names a `0.33.0` 64-bit no-displacement `mov` row and violates
exactly one rule: the row is absent from `0.32.0` (a load and a store), a
`disp` operand is supplied to a row with no displacement slot, the register is
one past the four-bit field, or the base is one of the four excluded values
(`%rsp`, `%rbp`, `%r12`, `%r13`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0062/fixture_negatives_p37.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.33.0"
DIGEST = "sha256:b6659c62116dab7bf79f6c9704844d0fd9a1ad27ac8780e2071a93cf28dd6d8e"
PREVIOUS = "sha256:bad81d6655d9e612fa353814fa40ba9910ba3830ac954df2169365abd02563ac"

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


LOAD = "x86:mov/r64-base/legacy"    # `48 8b 00`
STORE = "x86:mov/base-r64/legacy"   # `48 89 00`

CASES = [
    # The load row is new in 0.33.0, so 0.32.0 must reject the name rather
    # than fall back to the disp8 row (which needs a displacement operand).
    (
        "N01bt-absent-gpr64-mov-mem-load-row-on-0.32.0",
        "0.32.0",
        PREVIOUS,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr64", "r64", 0),
            reg("base", "x86.gpr64", "rm64", 0),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store row carries its own boundary, at the top of the fields.
    (
        "N01bu-absent-gpr64-mov-mem-store-row-on-0.32.0",
        "0.32.0",
        PREVIOUS,
        3,
        STORE,
        [
            reg("src", "x86.gpr64", "r64", 15),
            reg("base", "x86.gpr64", "rm64", 9),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `mod = 00` carries no displacement byte, so a `disp` operand is a count
    # mismatch rather than an implied zero.
    (
        "N02ba-extra-disp-operand-on-gpr64-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr64", "r64", 0),
            reg("base", "x86.gpr64", "rm64", 0),
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
        "N14ah-register16-on-gpr64-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr64", "r64", 16),
            reg("base", "x86.gpr64", "rm64", 0),
        ],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # %rsp needs the SIB byte this shape does not carry.
    (
        "N16ao-base-rsp-on-gpr64-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr64", "r64", 0),
            reg("base", "x86.gpr64", "rm64", 4),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # %rbp is `r/m = 101`, the RIP-relative shape.
    (
        "N16ap-base-rbp-on-gpr64-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr64", "r64", 0),
            reg("base", "x86.gpr64", "rm64", 5),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # %r12 is the extended half of the same SIB pair.
    (
        "N16aq-base-r12-on-gpr64-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr64", "r64", 0),
            reg("base", "x86.gpr64", "rm64", 12),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # %r13 is the extended half of the RIP-relative pair.
    (
        "N16ar-base-r13-on-gpr64-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        STORE,
        [
            reg("src", "x86.gpr64", "r64", 0),
            reg("base", "x86.gpr64", "rm64", 13),
        ],
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
