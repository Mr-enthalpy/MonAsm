#!/usr/bin/env python3
"""Emit the four `X86-P72` negative fixtures.

Each case violates exactly one rule of the `sub` immediate family:

- `N01ej` names the register form (`29`/`2b`), which no version has because the
  register halves are deliberately absent (the same decision `add` made);
- `N01ek` names a `0.66.0` row against `0.65.0`, the version boundary;
- `N03zs` states `128` on the signed 8-bit immediate;
- `N02ct` passes a `r32` destination to the `rm64-imm32` row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0102/fixture_negatives_p72.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.66.0"
DIGEST = "sha256:63b3b3a153aa0b5508f2055496efa1c56ac74e56b03d56f56f5c522b6d2e1904"
PREVIOUS = "sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a"

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


def imm(bits, value) -> str:
    return operand("imm", "x86.imm", "imm%d" % bits, {"value": value})


IMM8 = "x86:sub/rm64-imm8/legacy"
IMM32 = "x86:sub/rm64-imm32/legacy"
REGISTER = "x86:sub/rm64-r64/legacy"

CASES = [
    (
        "N01ej-absent-sub-register-form",
        VERSION,
        DIGEST,
        3,
        REGISTER,
        [reg("dest", "x86.gpr64", "rm64", 0),
         reg("src", "x86.gpr64", "r64", 1)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01ek-sub-absent-in-previous-version",
        "0.65.0",
        PREVIOUS,
        4,
        IMM8,
        [reg("dest", "x86.gpr64", "rm64", 0), imm(8, 1)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N03zs-sub-imm8-out-of-range",
        VERSION,
        DIGEST,
        4,
        IMM8,
        [reg("dest", "x86.gpr64", "rm64", 0), imm(8, 128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    (
        "N02ct-sub-dest-32bit",
        VERSION,
        DIGEST,
        7,
        IMM32,
        [reg("dest", "x86.gpr32", "r32", 0), imm(32, 300)],
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
