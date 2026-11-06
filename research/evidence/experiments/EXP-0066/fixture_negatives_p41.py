#!/usr/bin/env python3
"""Emit the ten `X86-P41` negative fixtures.

Each case names a `0.37.0` 32-bit `disp8` `mov` row and violates exactly one
rule: the row is absent from `0.36.0` (both directions), the `disp` operand is
missing, the displacement is outside `-128…127`, an operand is past its
encoded field (the 3-bit and 4-bit ends), or a value enters a disjoint window
(the two `SIB`-forcing bases, the `REX.R` register floor and the `REX.B` base
floor).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0066/fixture_negatives_p41.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.37.0"
DIGEST = "sha256:1a29805f2f9e58f4d7ab749999c90fa415c29985dae9c5e45a9294ddf25102d6"
PREVIOUS = "sha256:c4a61297e71ed19a79c0f01fb7495832ee447a1448a3b9071e1477eaeb70892f"

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


def base(number) -> str:
    return reg("base", "x86.gpr64", "rm64", number)


def disp(value) -> str:
    return operand("disp", "x86.imm", "disp8", {"value": value})


LOAD_LOW = "x86:mov/r32-base-disp8/legacy"          # `8b 40 00`
STORE_LOW = "x86:mov/base-disp8-r32/legacy"         # `89 40 00`
LOAD_REXR = "x86:mov/r32-ext-base-disp8/legacy"     # `44 8b 40 00`
LOAD_REXB = "x86:mov/r32-base-ext-disp8/legacy"     # `41 8b 40 00`

CASES = [
    # Both directions are new in 0.37.0, so 0.36.0 must reject the names.
    (
        "N01cb-absent-gpr32-mov-mem-disp8-load-row-on-0.36.0",
        "0.36.0",
        PREVIOUS,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), base(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01cc-absent-gpr32-mov-mem-disp8-store-row-on-0.36.0",
        "0.36.0",
        PREVIOUS,
        3,
        STORE_LOW,
        [reg("src", "x86.gpr32", "r32", 7), base(6), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `disp8` is a slot: the row cannot supply an implied zero.
    (
        "N02bg-missing-disp-operand-on-gpr32-mov-mem-disp8-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), base(0)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `128` needs `mod = 10`, which is a different form.
    (
        "N03r-disp8-out-of-range-on-gpr32-mov-mem-base-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), base(0), disp(128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/2/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # Four bits reach `r15`; `r16` is one past the `REX.R` window.
    (
        "N14an-register16-on-gpr32-mov-mem-ext-disp8-row",
        VERSION,
        DIGEST,
        4,
        LOAD_REXR,
        [reg("dest", "x86.gpr32", "r32", 16), base(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The low row owns only the 3-bit field; `8` is one past it.
    (
        "N14ao-register8-on-gpr32-mov-mem-disp8-low-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 8), base(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # `%rsp` needs the `SIB` byte, which this shape has no room for.
    (
        "N16ax-base-rsp-on-gpr32-mov-mem-disp8-low-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0), base(4), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%r12` is the same `SIB` case one register number higher.
    (
        "N16ay-base-r12-on-gpr32-mov-mem-ext-disp8-row",
        VERSION,
        DIGEST,
        4,
        LOAD_REXR,
        [reg("dest", "x86.gpr32", "r32", 8), base(12), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The `REX.R` row owns only the extended register window.
    (
        "N16az-register0-on-gpr32-mov-mem-ext-disp8-row",
        VERSION,
        DIGEST,
        4,
        LOAD_REXR,
        [reg("dest", "x86.gpr32", "r32", 0), base(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The `REX.B` row owns only the extended base window.
    (
        "N16ba-base0-on-gpr32-mov-mem-base-ext-disp8-row",
        VERSION,
        DIGEST,
        4,
        LOAD_REXB,
        [reg("dest", "x86.gpr32", "r32", 0), base(0), disp(8)],
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
