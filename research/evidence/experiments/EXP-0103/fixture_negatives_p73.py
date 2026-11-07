#!/usr/bin/env python3
"""Emit the five `X86-P73` negative fixtures.

Each case violates exactly one rule of the `call rel32` row:

- `N01el` names the indirect form (`FF /2`), which no version has because the
  direct and indirect calls are separate decisions;
- `N01em` names a `0.67.0` row against `0.66.0`, the version boundary;
- `N02cu` passes an `x86.gpr64`/`r64` operand where the row needs `x86.rel`;
- `N02cv` omits the target operand;
- `N04g` states `2147483648` on the signed 32-bit displacement.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0103/fixture_negatives_p73.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.67.0"
DIGEST = "sha256:367d76ebf89ee9c1cf51f561b4798eeb0a2000ae3688ee9a52a4c4a9eaea5c9e"
PREVIOUS = "sha256:63b3b3a153aa0b5508f2055496efa1c56ac74e56b03d56f56f5c522b6d2e1904"

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


def rel(value) -> str:
    return operand("target", "x86.rel", "rel32", {"value": value})


CALL = "x86:call/rel32/legacy"
INDIRECT = "x86:call/rm64/legacy"


def form_error() -> list:
    return [{
        "code": "E-FORM-001",
        "path": "/instructions/0/form_id",
        "detail_keys": ["form_id", "namespace", "version"],
    }]


def range_error() -> list:
    return [{
        "code": "E-RANGE-002",
        "path": "/instructions/0/operands/0/payload/value",
        "detail_keys": ["min", "max", "value", "bits", "align_bits"],
    }]


def kind_error() -> list:
    return [
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
    ]


def count_error() -> list:
    return [{
        "code": "E-OPERAND-002",
        "path": "/instructions/0/operands",
        "detail_keys": ["expected", "found"],
    }]


CASES = [
    (
        "N01el-absent-indirect-call",
        VERSION,
        DIGEST,
        2,
        INDIRECT,
        [operand("target", "x86.gpr64", "rm64", {"reg": 0})],
        form_error(),
    ),
    (
        "N01em-call-absent-in-previous-version",
        "0.66.0",
        PREVIOUS,
        5,
        CALL,
        [rel(0)],
        form_error(),
    ),
    (
        "N02cu-call-register-target",
        VERSION,
        DIGEST,
        5,
        CALL,
        [operand("target", "x86.gpr64", "r64", {"value": 0})],
        kind_error(),
    ),
    (
        "N02cv-call-missing-target",
        VERSION,
        DIGEST,
        5,
        CALL,
        [],
        count_error(),
    ),
    (
        "N04g-call-rel32-out-of-range",
        VERSION,
        DIGEST,
        5,
        CALL,
        [rel(2147483648)],
        range_error(),
    ),
]


def main() -> int:
    for name, version, digest, size, form_id, operands, errors in CASES:
        plan = HEADER % (version, digest, size, size, form_id,
                         ",\n".join(operands), size)
        plan_path = TARGET / (name + ".fmp.json")
        with plan_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(plan)
        error_path = TARGET / (name + ".expected-error.json")
        with error_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"errors": errors}, indent=2) + "\n")
        print("%s (%s)" % (name, version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
