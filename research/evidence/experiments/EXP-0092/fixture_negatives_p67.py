#!/usr/bin/env python3
"""Emit the seven `X86-P67` negative fixtures.

Each case names a `0.63.0` `0x67` absolute `SIB = 25` row and violates exactly
one rule: the row is absent from `0.62.0` (load and store), the plan supplies a
`base` the shape does not have, the displacement passes the signed 32-bit end,
a value past the four-bit window end, a value past the bare three-bit field, or
`0` on the `-ext` row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0092/fixture_negatives_p67.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.63.0"
DIGEST = "sha256:72c7e8f2fcf4c73ad816d7de274d9b46edec7d9ef99b4834c27140d83d6c91e8"
PREVIOUS = "sha256:bbcd8062c84580e208c1cbf275254593a7d937fd7de28fde19e7dc5c5049e3b3"

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


LOAD = "x86:mov/r32-addr32-abs32/legacy"            # `67 8b 04 25 34 12 00 00`
STORE = "x86:mov/addr32-abs32-r32/legacy"           # `67 89 04 25 34 12 00 00`
LOAD_EXT = "x86:mov/r32-ext-addr32-abs32/legacy"    # `67 44 8b 04 25 34 12 00 00`
STORE_EXT = "x86:mov/addr32-abs32-r32-ext/legacy"   # `67 44 89 04 25 34 12 00 00`

CASES = [
    # The rows are new in 0.63.0, so 0.62.0 must reject both directions.
    (
        "N01eb-absent-addr32-abs32-load-row-on-0.62.0",
        "0.62.0",
        PREVIOUS,
        8,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 0), disp(4660)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01ec-absent-addr32-abs32-store-row-on-0.62.0",
        "0.62.0",
        PREVIOUS,
        8,
        STORE,
        [reg("src", "x86.gpr32", "r32", 0), disp(4660)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The shape has two roles, so a supplied base is a role-sequence miss.
    (
        "N02cm-extra-base-operand-on-addr32-abs32-row",
        VERSION,
        DIGEST,
        8,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr32", "rm32", 0), disp(4660)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The displacement is signed 32-bit; 2^31 is past its upper end.
    (
        "N03zp-disp-past-signed-end-on-addr32-abs32-row",
        VERSION,
        DIGEST,
        8,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 0), disp(2147483648)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The extended value slot is four bits (REX.R plus ModRM.reg); 16 is
    # past its end.
    (
        "N14cb-value-register16-on-addr32-abs32-ext-row",
        VERSION,
        DIGEST,
        9,
        LOAD_EXT,
        [reg("dest", "x86.gpr32", "r32", 16), disp(4660)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
        }],
    ),
    # The bare value slot is three bits (ModRM.reg only); 8 is past its end.
    (
        "N14cc-value-register8-on-addr32-abs32-row",
        VERSION,
        DIGEST,
        8,
        LOAD,
        [reg("dest", "x86.gpr32", "r32", 8), disp(4660)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
        }],
    ),
    # The extended row excludes 0-7, so the low window needs the bare row.
    (
        "N16df-value-register0-on-addr32-abs32-ext-row",
        VERSION,
        DIGEST,
        9,
        STORE_EXT,
        [reg("src", "x86.gpr32", "r32", 0), disp(4660)],
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
