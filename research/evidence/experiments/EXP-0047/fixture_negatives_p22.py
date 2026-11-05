#!/usr/bin/env python3
"""Emit the six `X86-P22` negative fixtures.

Each case names one of the twelve `0.18.0` extension rows and violates exactly
one rule: the row is absent from `0.17.0`, a low base is passed to an extension
row, `%r12` is passed to either window, base `16` is outside the four-bit field,
or the high-byte set is passed to a REX row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0047/fixture_negatives_p22.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.18.0"
DIGEST = "sha256:e1281b0c11d7e2bed9bd1ec7fa5404dadca2c82959376cbe3edfd9ff56b9e33d"

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
    return operand("base", "x86.gpr64", "rm64", {"reg": number})


def disp(target_type, value) -> str:
    return operand("disp", "x86.imm", target_type, {"value": value})


CASES = [
    # The `-base-ext` rows are new in 0.18.0, so 0.17.0 must reject the name
    # rather than fall back to the short row.
    (
        "N01ao-absent-mov-memory-base-ext-row-on-0.17.0",
        "0.17.0",
        "sha256:eb8370255811a2364550bf98ae106f8f972c9a3e54e94d1aeb98ddde921fbcd0",
        5,
        "x86:mov/r16-base-ext-disp8/legacy",
        [reg("dest", "x86.gpr16", "r16", 0), base(8), disp("disp8", 8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # Bases 0-7 encode with REX.B = 0, which is the short row's job: the two
    # windows must stay disjoint.
    (
        "N16v-low-base-on-mov-memory-base-ext-row",
        VERSION,
        DIGEST,
        5,
        "x86:mov/r16-base-ext-disp8/legacy",
        [reg("dest", "x86.gpr16", "r16", 0), base(0), disp("disp8", 8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # `%r12` has low three bits 100, so `r/m = 100` spends a SIB byte.
    (
        "N16w-r12-on-mov-memory-base-ext-row",
        VERSION,
        DIGEST,
        5,
        "x86:mov/r16-base-ext-disp8/legacy",
        [reg("dest", "x86.gpr16", "r16", 0), base(12), disp("disp8", 8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # The widened `40` row reaches `r8`-`r15`, but `%r12` still forces a SIB.
    (
        "N16x-r12-on-widened-mov-memory-rex-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/base-disp8-r8-rex/legacy",
        [reg("src", "x86.gpr8", "r8", 4), base(12), disp("disp8", 8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # The base is four bits now, so 16 is outside the field.
    (
        "N14u-base16-on-mov-memory-base-ext-row",
        VERSION,
        DIGEST,
        5,
        "x86:mov/r16-base-ext-disp8/legacy",
        [reg("dest", "x86.gpr16", "r16", 0), base(16), disp("disp8", 8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # A REX prefix re-labels numbers 4-7; the high-byte set has no extension
    # row at all.
    (
        "N02t-r8h-operand-on-mov-memory-base-ext-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/base-ext-disp8-r8/legacy",
        [reg("src", "x86.gpr8h", "r8h", 4), base(8), disp("disp8", 8)],
        [
            {"code": "E-OPERAND-001", "path": "/instructions/0/operands/0/kind",
             "detail_keys": ["expected", "found"]},
            {"code": "E-OPERAND-001",
             "path": "/instructions/0/operands/0/target_type",
             "detail_keys": ["expected", "found"]},
            # Number 4 is `spl` on the new row and `ah` only without REX.
            {"code": "E-RANGE-004",
             "path": "/instructions/0/operands/0/payload/reg",
             "detail_keys": ["target_type", "value", "excluded"]},
        ],
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
