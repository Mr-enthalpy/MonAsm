#!/usr/bin/env python3
"""Emit the seven `X86-P44` negative fixtures.

Each case names a `0.40.0` 32-bit `SIB` `disp32` `mov` row and violates exactly
one rule: the row is absent from `0.39.0` (both directions), the `disp` operand
is missing, the displacement is outside `-2147483648…2147483647`, an operand is
past its encoded field (the 3-bit and 4-bit ends), or a value enters the
`REX.R` window's floor.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0069/fixture_negatives_p44.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.40.0"
DIGEST = "sha256:ddeb4734cab0483c6f440106954233072d352910998c5680e28b6d33352eb468"
PREVIOUS = "sha256:08e2fb7afee30bc6bf63f3bd795f88f6dfb4ae100a41e72f2f6491b113a3b1a0"

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


def disp(value) -> str:
    return operand("disp", "x86.imm", "disp32", {"value": value})


LOAD_LOW = "x86:mov/r32-rsp-disp32/legacy"       # `8b 84 24 00 00 00 00`
STORE_LOW = "x86:mov/rsp-disp32-r32/legacy"      # `89 84 24 00 00 00 00`
LOAD_EXT = "x86:mov/r32-ext-rsp-disp32/legacy"   # `44 8b 84 24 00 00 00 00`

CASES = [
    # Both directions are new in 0.40.0, so 0.39.0 must reject the names.
    (
        "N01ch-absent-gpr32-mov-mem-sib-disp32-load-row-on-0.39.0",
        "0.39.0",
        PREVIOUS,
        7,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), disp(200)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01ci-absent-gpr32-mov-mem-sib-disp32-store-row-on-0.39.0",
        "0.39.0",
        PREVIOUS,
        7,
        STORE_LOW,
        [reg("src", "x86.gpr32", "r32", 7), disp(100000)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `disp32` is a slot: the row cannot supply an implied displacement.
    (
        "N02bj-missing-disp-operand-on-gpr32-mov-mem-sib-disp32-row",
        VERSION,
        DIGEST,
        7,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # One past `2147483647`: the slot is a signed 32-bit field.
    (
        "N03u-disp32-out-of-range-on-gpr32-mov-mem-sib-row",
        VERSION,
        DIGEST,
        7,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), disp(2147483648)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # Four bits reach `r15`; `r16` is one past the `REX.R` window.
    (
        "N14at-register16-on-gpr32-mov-mem-sib-ext-disp32-row",
        VERSION,
        DIGEST,
        8,
        LOAD_EXT,
        [reg("dest", "x86.gpr32", "r32", 16), disp(200)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The low row owns only the 3-bit field; `8` is one past it.
    (
        "N14au-register8-on-gpr32-mov-mem-sib-disp32-low-row",
        VERSION,
        DIGEST,
        7,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 8), disp(200)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The `REX.R` row owns only the extended register window.
    (
        "N16bg-register0-on-gpr32-mov-mem-sib-ext-disp32-row",
        VERSION,
        DIGEST,
        8,
        LOAD_EXT,
        [reg("dest", "x86.gpr32", "r32", 0), disp(200)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
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
