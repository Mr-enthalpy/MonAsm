#!/usr/bin/env python3
"""Emit the seven `X86-P56` negative fixtures.

Each case names a `0.52.0` 32-bit indexed `mov` `REX.RBX` row and violates
exactly one rule: the row is absent from `0.51.0` (both directions), the index
operand is missing, the scale is `4` (past the two-bit field), or one of the
three extended register slots is below its floor of `8`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0081/fixture_negatives_p56.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.52.0"
DIGEST = "sha256:4587b149e1119681ffefe011862343d8bccd0f52dbe7d278a0afb05517f7f7ae"
PREVIOUS = "sha256:e73395dffc494d13d0b142cbba0e4c55a40d19bcd68a6b793025156bbcb41bc5"

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


LOAD8 = "x86:mov/r32-ext-base-ext-index-ext-disp8/legacy"     # `47 8b 44 08 08`
STORE8 = "x86:mov/base-ext-index-ext-disp8-r32-ext/legacy"    # `47 89 44 08 08`

CASES = [
    # The rows are new in 0.52.0, so 0.51.0 must reject both names.
    (
        "N01df-absent-gpr32-mov-index-rex-rbx-load-row-on-0.51.0",
        "0.51.0",
        PREVIOUS,
        5,
        LOAD8,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 9), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01dg-absent-gpr32-mov-index-rex-rbx-store-row-on-0.51.0",
        "0.51.0",
        PREVIOUS,
        5,
        STORE8,
        [reg("src", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 9), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02bv-missing-index-operand-on-gpr32-mov-index-rex-rbx-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 8), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03ze-scale4-on-gpr32-mov-index-rex-rbx-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 9), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # All three register slots start at 8, so a lower value clears a fixed bit.
    (
        "N16ci-register3-on-gpr32-mov-index-rex-rbx-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr32", "r32", 3),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 9), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    (
        "N16cj-base3-on-gpr32-mov-index-rex-rbx-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 3),
         reg("index", "x86.gpr64", "sib_index", 9), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    (
        "N16ck-index3-on-gpr32-mov-index-rex-rbx-row",
        VERSION,
        DIGEST,
        5,
        LOAD8,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr64", "rm64", 8),
         reg("index", "x86.gpr64", "sib_index", 3), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
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
