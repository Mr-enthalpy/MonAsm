#!/usr/bin/env python3
"""Emit the eight `X86-P31` negative fixtures.

Each case names a `0.27.0` 32-bit absolute-address row and violates exactly one
rule: the row is absent from `0.26.0` (load and store), a `base` operand is
supplied to a row with no register in its address, the address carries the
`disp8` target type instead of `disp32`, a 64-bit register kind is supplied to
a 32-bit row, the address content is one past the signed end point, the
register is one past the four-bit field, or the excluded low window is named on
an extended row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0056/fixture_negatives_p31.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.27.0"
DIGEST = "sha256:c51a0a6b1fefd708a8f05303079fc4fd245462a3f4d4d59d4fe3a5d7063430b9"
PREVIOUS = "sha256:e253e0506d89f16b4d23fe9e9341720c5e6ada53534c199cabe31cc1b2c94212"

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


# `dest`, `0x1234`: the first row of the fixture.
FULL = [
    reg("dest", "x86.gpr32", "r32", 0),
    disp("disp32", 4660),
]

CASES = [
    # The low load row is new in 0.27.0, so 0.26.0 must reject the name rather
    # than reuse the 64-bit row.
    (
        "N01bg-absent-gpr32-mov-abs32-load-row-on-0.26.0",
        "0.26.0",
        PREVIOUS,
        7,
        "x86:mov/r32-abs32/legacy",
        FULL,
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The extended store row is a separate row, so it has its own version
    # boundary.
    (
        "N01bh-absent-gpr32-mov-abs32-store-row-on-0.26.0",
        "0.26.0",
        PREVIOUS,
        8,
        "x86:mov/abs32-r32-ext/legacy",
        [
            reg("src", "x86.gpr32", "r32", 8),
            disp("disp32", 4660),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The absolute row has no register in its address: a base operand is one
    # operand too many, and `SIB.base = 101` is a template bit.
    (
        "N02aj-extra-base-operand-on-gpr32-mov-abs32-row",
        VERSION,
        DIGEST,
        7,
        "x86:mov/r32-abs32/legacy",
        [FULL[0], reg("base", "x86.gpr64", "rm64", 0), FULL[1]],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The address is four bytes; `disp8` is the target type of a different
    # field, and the row's unit may not be re-derived from the value.
    (
        "N02ak-address-carried-as-disp8-on-gpr32-mov-abs32-row",
        VERSION,
        DIGEST,
        7,
        "x86:mov/r32-abs32/legacy",
        [FULL[0], disp("disp8", 0)],
        [{
            "code": "E-OPERAND-001",
            "path": "/instructions/0/operands/1/target_type",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # A 64-bit register on a 32-bit row is a different name on both axes; the
    # width is not recoverable from the register number.
    (
        "N02al-gpr64-operand-on-gpr32-mov-abs32-row",
        VERSION,
        DIGEST,
        7,
        "x86:mov/r32-abs32/legacy",
        [
            reg("dest", "x86.gpr64", "r64", 0),
            disp("disp32", 4660),
        ],
        [
            {
                "code": "E-OPERAND-001",
                "path": "/instructions/0/operands/0/kind",
                "detail_keys": ["expected", "found"],
            },
            {
                "code": "E-OPERAND-001",
                "path": "/instructions/0/operands/0/target_type",
                "detail_keys": ["expected", "found"],
            },
        ],
    ),
    # `disp32` is signed 32-bit content; 2147483648 is one past the field, and
    # `llvm-mc` silently switches to `moffs` there, which a plan may not do.
    (
        "N03n-disp32-past-end-on-gpr32-mov-abs32-row",
        VERSION,
        DIGEST,
        7,
        "x86:mov/r32-abs32/legacy",
        [FULL[0], disp("disp32", 2147483648)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The extended register slot is four bits; 16 is outside the field
    # (`llvm-mc` would reach for the APX `d5` prefix, which the row does not
    # carry).
    (
        "N14aa-register-16-on-gpr32-mov-abs32-row",
        VERSION,
        DIGEST,
        8,
        "x86:mov/r32-ext-abs32/legacy",
        [
            reg("dest", "x86.gpr32", "r32", 16),
            disp("disp32", 4660),
        ],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The extended row's template carries `REX.R = 1`, so the low window is
    # excluded: `%eax` would encode `%r8d` at the same byte.
    (
        "N16ad-register-0-on-gpr32-mov-abs32-ext-row",
        VERSION,
        DIGEST,
        8,
        "x86:mov/r32-ext-abs32/legacy",
        [
            reg("dest", "x86.gpr32", "r32", 0),
            disp("disp32", 4660),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
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
