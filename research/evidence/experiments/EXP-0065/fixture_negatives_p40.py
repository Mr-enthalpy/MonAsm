#!/usr/bin/env python3
"""Emit the seven `X86-P40` negative fixtures.

Each case names a `0.36.0` 32-bit `SIB` `mov` row and violates exactly one
rule: the row is absent from `0.35.0` (both directions), a `base` or `disp`
operand is supplied to a fixed-base row, an operand is past its encoded field
(the 3-bit and 4-bit ends), or the low register window of an `-ext` row is
entered.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0065/fixture_negatives_p40.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.36.0"
DIGEST = "sha256:c4a61297e71ed19a79c0f01fb7495832ee447a1448a3b9071e1477eaeb70892f"
PREVIOUS = "sha256:d4fd01ad8f795ea595f77dc928ded8188a0e98e7b1c5e098c458bea46616780d"

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


LOAD_LOW = "x86:mov/r32-rsp/legacy"            # `8b 04 24`
STORE_LOW = "x86:mov/rsp-r32/legacy"           # `89 04 24`
LOAD_EXT = "x86:mov/r32-ext-rsp/legacy"        # `44 8b 04 24`

CASES = [
    # Both directions are new in 0.36.0, so 0.35.0 must reject the names.
    (
        "N01bz-absent-gpr32-mov-mem-sib-load-row-on-0.35.0",
        "0.35.0",
        PREVIOUS,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 0)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01ca-absent-gpr32-mov-mem-sib-store-row-on-0.35.0",
        "0.35.0",
        PREVIOUS,
        3,
        STORE_LOW,
        [reg("src", "x86.gpr32", "r32", 7)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The base is template content, not a slot.
    (
        "N02be-extra-base-operand-on-gpr32-mov-mem-sib-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [
            reg("dest", "x86.gpr32", "r32", 0),
            reg("base", "x86.gpr64", "rm64", 4),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `mod = 00` carries no displacement byte.
    (
        "N02bf-extra-disp-operand-on-gpr32-mov-mem-sib-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [
            reg("dest", "x86.gpr32", "r32", 0),
            disp("disp8", 0),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # Four bits reach `r15`; `r16` is one past the `REX.R` window.
    (
        "N14al-register16-on-gpr32-mov-mem-sib-ext-row",
        VERSION,
        DIGEST,
        4,
        LOAD_EXT,
        [reg("dest", "x86.gpr32", "r32", 16)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The low rows own only the 3-bit field; `8` is one past it.
    (
        "N14am-register8-on-gpr32-mov-mem-sib-low-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr32", "r32", 8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The `-ext` row owns only the extended register window.
    (
        "N16aw-register0-on-gpr32-mov-mem-sib-ext-row",
        VERSION,
        DIGEST,
        4,
        LOAD_EXT,
        [reg("dest", "x86.gpr32", "r32", 0)],
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
