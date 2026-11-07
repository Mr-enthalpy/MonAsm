#!/usr/bin/env python3
"""Emit the eight `X86-P60` negative fixtures.

Each case names a `0.56.0` `0x67` `REX.W` `movq` row and violates exactly one
rule: the row is absent from `0.55.0` (both directions), the index operand is
missing, the base is a 64-bit register instead of a 32-bit address register,
the scale is `4`, the index is `4` (the `%esp`/`%rsp` slot), or a four-bit
register slot carries `16`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0085/fixture_negatives_p60.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.56.0"
DIGEST = "sha256:d039c97253fbdefba9c68c4fdab0d3310d17b809b8ba29fc268e6d8458f2ef87"
PREVIOUS = "sha256:e4fe01184a25274242c3eb9cf29b411d48d2d629cd2befbcbd274ef6384618fc"

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


def scale(value) -> str:
    return operand("imm", "x86.scale", "scale2", {"value": value})


def disp(value) -> str:
    return operand("disp", "x86.imm", "disp8", {"value": value})


LOAD8 = "x86:mov/r64-addr32-base-index-disp8/legacy"     # `67 48 8b 44 08 08`
STORE8 = "x86:mov/addr32-base-index-disp8-r64/legacy"    # `67 48 89 44 08 08`

CASES = [
    # The rows are new in 0.56.0, so 0.55.0 must reject both names.
    (
        "N01dn-absent-addr32-rexw-load-row-on-0.55.0",
        "0.55.0",
        PREVIOUS,
        6,
        LOAD8,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01do-absent-addr32-rexw-store-row-on-0.55.0",
        "0.55.0",
        PREVIOUS,
        6,
        STORE8,
        [reg("src", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02ca-missing-index-operand-on-addr32-rexw-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr32", "rm32", 0), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # With 0x67 the address registers are 32-bit: a 64-bit base is wrong.
    (
        "N02cb-gpr64-base-on-addr32-rexw-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [
            {
                "code": "E-OPERAND-001",
                "path": "/instructions/0/operands/1/kind",
                "detail_keys": ["expected", "found"],
            },
            {
                "code": "E-OPERAND-001",
                "path": "/instructions/0/operands/1/target_type",
                "detail_keys": ["expected", "found"],
            },
        ],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03zi-scale4-on-addr32-rexw-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # Index 4 is the %esp/%rsp slot, which has no register.
    (
        "N16cs-index4-on-addr32-rexw-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 4), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # A four-bit register slot cannot hold 16.
    (
        "N14br-register16-on-addr32-rexw-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr64", "r64", 16),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
        }],
    ),
    (
        "N14bs-index16-on-addr32-rexw-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr64", "r64", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 16), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
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
