#!/usr/bin/env python3
"""Emit the six `X86-P23` negative fixtures.

Each case names one of the twenty-eight fixed-base `SIB` rows and violates
exactly one rule: the row is absent from `0.18.0`, the high-byte set is asked
for a `%r12` base that has no encoding, the register kind or the register value
is wrong for the row, or the displacement content leaves its byte.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0048/fixture_negatives_p23.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.19.0"
DIGEST = "sha256:dddc678fe0abc6fa03c2e61c8fcafef2570b496775a11a25e1ab29e01bfe5130"

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


CASES = [
    # The fixed-base rows are new in 0.19.0, so 0.18.0 must reject the name
    # rather than fall back to the `-base-disp*` row.
    (
        "N01ap-absent-mov-memory-sib-row-on-0.18.0",
        "0.18.0",
        "sha256:e1281b0c11d7e2bed9bd1ec7fa5404dadca2c82959376cbe3edfd9ff56b9e33d",
        5,
        "x86:mov/r16-rsp-disp8/legacy",
        [reg("dest", "x86.gpr16", "r16", 0), disp("disp8", 8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `movb %ah, 8(%r12)` has no encoding at all: the `REX` byte that carries
    # `REX.B` renames `ah` to `spl`, so the row cannot exist.
    (
        "N01aq-absent-high-byte-r12-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8h-r12-disp8/legacy",
        [reg("dest", "x86.gpr8h", "r8h", 4), disp("disp8", 8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # A word operand on a byte row: width is part of the kind.
    (
        "N02u-gpr16-operand-on-mov-memory-sib-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8-rsp-disp8/legacy",
        [reg("dest", "x86.gpr16", "r16", 0), disp("disp8", 8)],
        [
            {"code": "E-OPERAND-001", "path": "/instructions/0/operands/0/kind",
             "detail_keys": ["expected", "found"]},
            {"code": "E-OPERAND-001",
             "path": "/instructions/0/operands/0/target_type",
             "detail_keys": ["expected", "found"]},
        ],
    ),
    # The `SIB` row still reads a signed byte, so 128 is a `disp32` operand.
    (
        "N03h-disp8-content-out-of-range-mov-memory-sib",
        VERSION,
        DIGEST,
        5,
        "x86:mov/r16-rsp-disp8/legacy",
        [reg("dest", "x86.gpr16", "r16", 0), disp("disp8", 128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The byte register field is three bits, so 8 does not fit.
    (
        "N14v-register8-on-mov-memory-sib-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8-rsp-disp8/legacy",
        [reg("dest", "x86.gpr8", "r8", 8), disp("disp8", 8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The `40` row carries numbers 4-7 (`spl`-`dil`); number 0 is `al`, which
    # is the REX-less row's job.
    (
        "N16y-low-byte-number-on-mov-memory-sib-rex-row",
        VERSION,
        DIGEST,
        5,
        "x86:mov/r8-rsp-disp8-rex/legacy",
        [reg("dest", "x86.gpr8", "r8", 0), disp("disp8", 8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
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
