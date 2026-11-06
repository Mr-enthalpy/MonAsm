#!/usr/bin/env python3
"""Emit the seven `X86-P43` negative fixtures.

Each case names a `0.39.0` 32-bit `SIB` `disp8` `mov` row and violates exactly
one rule: the row is absent from `0.38.0` (both directions), the `disp` operand
is missing, the displacement is outside `-128…127`, an operand is past its
encoded field (the 3-bit and 4-bit ends), or a value enters the `REX.R`
window's floor.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0068/fixture_negatives_p43.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.39.0"
DIGEST = "sha256:08e2fb7afee30bc6bf63f3bd795f88f6dfb4ae100a41e72f2f6491b113a3b1a0"
PREVIOUS = "sha256:47355a151d981fdbf36942305b3cad5d1a29bf6d4b20eb60d8efb13e39e2c5b2"

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
    return operand("disp", "x86.imm", "disp8", {"value": value})


LOAD_LOW = "x86:mov/r32-rsp-disp8/legacy"       # `8b 44 24 00`
STORE_LOW = "x86:mov/rsp-disp8-r32/legacy"      # `89 44 24 00`
LOAD_EXT = "x86:mov/r32-ext-rsp-disp8/legacy"   # `44 8b 44 24 00`

CASES = [
    # Both directions are new in 0.39.0, so 0.38.0 must reject the names.
    (
        "N01cf-absent-gpr32-mov-mem-sib-disp8-load-row-on-0.38.0",
        "0.38.0",
        PREVIOUS,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01cg-absent-gpr32-mov-mem-sib-disp8-store-row-on-0.38.0",
        "0.38.0",
        PREVIOUS,
        4,
        STORE_LOW,
        [reg("src", "x86.gpr32", "r32", 7), disp(100)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `disp8` is a slot: the row cannot supply an implied displacement.
    (
        "N02bi-missing-disp-operand-on-gpr32-mov-mem-sib-disp8-row",
        VERSION,
        DIGEST,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `128` needs `mod = 10`, which is a different form.
    (
        "N03t-disp8-out-of-range-on-gpr32-mov-mem-sib-row",
        VERSION,
        DIGEST,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), disp(128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # Four bits reach `r15`; `r16` is one past the `REX.R` window.
    (
        "N14ar-register16-on-gpr32-mov-mem-sib-ext-disp8-row",
        VERSION,
        DIGEST,
        5,
        LOAD_EXT,
        [reg("dest", "x86.gpr32", "r32", 16), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The low row owns only the 3-bit field; `8` is one past it.
    (
        "N14as-register8-on-gpr32-mov-mem-sib-disp8-low-row",
        VERSION,
        DIGEST,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 8), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The `REX.R` row owns only the extended register window.
    (
        "N16bf-register0-on-gpr32-mov-mem-sib-ext-disp8-row",
        VERSION,
        DIGEST,
        5,
        LOAD_EXT,
        [reg("dest", "x86.gpr32", "r32", 0), disp(8)],
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
