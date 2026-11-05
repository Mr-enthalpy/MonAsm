#!/usr/bin/env python3
"""Emit the seven `X86-P21` negative fixtures.

Each case names one of the sixteen 8/16-bit `mov` memory rows and violates
exactly one rule: the row is absent from `0.16.0`, the register kind is 32-bit,
the high-byte set is passed to the REX row, or the base/register/displacement
value is outside the slot's domain.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0046/fixture_negatives_p21.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.17.0"
DIGEST = "sha256:eb8370255811a2364550bf98ae106f8f972c9a3e54e94d1aeb98ddde921fbcd0"

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
    # The row is new in 0.17.0, so 0.16.0 must reject it rather than fall back
    # to the 64-bit row.
    (
        "N01an-absent-mov-memory-r16-row-on-0.16.0",
        "0.16.0",
        "sha256:64ea1acf467afb2f858a5cb2967839445a5ffecac164a5f1b61931cb8fb3b99e",
        4,
        "x86:mov/base-disp8-r16/legacy",
        [reg("src", "x86.gpr16", "r16", 0), base(0), disp("disp8", 8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The width is the row's kind, not the operand's number.
    (
        "N02r-gpr32-operand-on-mov-memory-r16-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/base-disp8-r16/legacy",
        [reg("src", "x86.gpr32", "r32", 0), base(0), disp("disp8", 8)],
        [
            {"code": "E-OPERAND-001", "path": "/instructions/0/operands/0/kind",
             "detail_keys": ["expected", "found"]},
            {"code": "E-OPERAND-001",
             "path": "/instructions/0/operands/0/target_type",
             "detail_keys": ["expected", "found"]},
        ],
    ),
    # `x86.gpr8h` is the REX-less set; the `-rex` row carries `x86.gpr8`.
    (
        "N02s-r8h-operand-on-mov-memory-rex-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/base-disp8-r8-rex/legacy",
        [reg("src", "x86.gpr8h", "r8h", 4), base(0), disp("disp8", 8)],
        [
            {"code": "E-OPERAND-001", "path": "/instructions/0/operands/0/kind",
             "detail_keys": ["expected", "found"]},
            {"code": "E-OPERAND-001",
             "path": "/instructions/0/operands/0/target_type",
             "detail_keys": ["expected", "found"]},
        ],
    ),
    # Numbers 4-7 without REX are `ah`-`bh`, a different register set.
    (
        "N16t-high-byte-number-on-rexless-mov-memory-row",
        VERSION,
        DIGEST,
        3,
        "x86:mov/base-disp8-r8/legacy",
        [reg("src", "x86.gpr8", "r8", 4), base(0), disp("disp8", 8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # `mod = 01` with `r/m = 100` spends a SIB byte on the register number.
    (
        "N16u-rsp-on-mov-memory-r16-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/base-disp8-r16/legacy",
        [reg("src", "x86.gpr16", "r16", 0), base(4), disp("disp8", 8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # The displacement payload is the signed byte, not a byte offset elsewhere.
    (
        "N03g-disp8-content-out-of-range-mov-memory",
        VERSION,
        DIGEST,
        3,
        "x86:mov/base-disp8-r8/legacy",
        [reg("src", "x86.gpr8", "r8", 0), base(0), disp("disp8", 128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/2/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The base window is three bits, so `%r8` cannot be named here.
    (
        "N14t-base8-on-3bit-mov-memory-row",
        VERSION,
        DIGEST,
        3,
        "x86:mov/base-disp8-r8/legacy",
        [reg("src", "x86.gpr8", "r8", 0), base(8), disp("disp8", 8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
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
