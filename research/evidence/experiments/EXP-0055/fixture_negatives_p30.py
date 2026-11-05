#!/usr/bin/env python3
"""Emit the seven `X86-P30` negative fixtures.

Each case names a `0.26.0` absolute-address row and violates exactly one rule:
the row is absent from `0.25.0` (load and store), the `moffs` row does not
exist at all (`EC-05`), a `base` operand is supplied to a row with no register
in its address, the address carries the `disp8` target type instead of
`disp32`, the address content is one past the signed end point, or the register
is one past the four-bit field.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0055/fixture_negatives_p30.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.26.0"
DIGEST = "sha256:e253e0506d89f16b4d23fe9e9341720c5e6ada53534c199cabe31cc1b2c94212"
PREVIOUS = "sha256:b72c0b08d30e9bbfd0c5129e01e1cecf77abcde36e2928aab2f94bb80c06a51c"

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
    reg("dest", "x86.gpr64", "r64", 0),
    disp("disp32", 4660),
]

CASES = [
    # The load row is new in 0.26.0, so 0.25.0 must reject the name rather than
    # reuse a base row.
    (
        "N01bd-absent-gpr-mov-abs32-load-row-on-0.25.0",
        "0.25.0",
        PREVIOUS,
        8,
        "x86:mov/r64-abs32/legacy",
        FULL,
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store half is a separate row, so it has its own version boundary.
    (
        "N01be-absent-gpr-mov-abs32-store-row-on-0.25.0",
        "0.25.0",
        PREVIOUS,
        8,
        "x86:mov/abs32-r64/legacy",
        [
            reg("src", "x86.gpr64", "r64", 10),
            disp("disp32", 0),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `moffs` is the second legal encoding of the same source instruction; the
    # table carries no such row, so the plan cannot ask for the longer form.
    (
        "N01bf-absent-gpr-mov-moffs-row",
        VERSION,
        DIGEST,
        10,
        "x86:mov/r64-moffs64/legacy",
        [
            reg("dest", "x86.gpr64", "r64", 0),
            disp("disp64", 4660),
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
        "N02ah-extra-base-operand-on-gpr-mov-abs32-row",
        VERSION,
        DIGEST,
        8,
        "x86:mov/r64-abs32/legacy",
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
        "N02ai-address-carried-as-disp8-on-gpr-mov-abs32-row",
        VERSION,
        DIGEST,
        8,
        "x86:mov/r64-abs32/legacy",
        [FULL[0], disp("disp8", 0)],
        [{
            "code": "E-OPERAND-001",
            "path": "/instructions/0/operands/1/target_type",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `disp32` is signed 32-bit content; 2147483648 is one past the field, and
    # `llvm-mc` silently switches to `moffs` there, which a plan may not do.
    (
        "N03m-disp32-past-end-on-gpr-mov-abs32-row",
        VERSION,
        DIGEST,
        8,
        "x86:mov/r64-abs32/legacy",
        [FULL[0], disp("disp32", 2147483648)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The register slot is four bits; 16 is outside the field (`llvm-mc` would
    # reach for the APX `d5` prefix, which the row does not carry).
    (
        "N14z-register-16-on-gpr-mov-abs32-row",
        VERSION,
        DIGEST,
        8,
        "x86:mov/r64-abs32/legacy",
        [
            reg("dest", "x86.gpr64", "r64", 16),
            disp("disp32", 4660),
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
