#!/usr/bin/env python3
"""Emit the six `X86-P24` negative fixtures.

Each case names one of the sixteen fixed-base SSE `SIB` rows and violates
exactly one rule: the row is absent from `0.19.0`, the no-displacement shape is
still absent from `0.20.0`, the register kind is wrong for the row, an extra
`base` operand is supplied to a row whose base is fixed, the `disp8` content
leaves its byte, or a legacy three-bit register field is asked for `xmm8`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0049/fixture_negatives_p24.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.20.0"
DIGEST = "sha256:b8bd1ed3ed38d71f6b19cc1854c9252df13850127c4e9433981a3a45f49d0f99"

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
    # The fixed-base rows are new in 0.20.0, so 0.19.0 must reject the name
    # rather than fall back to the `-base-disp*` row.
    (
        "N01ar-absent-sse-mem-sib-row-on-0.19.0",
        "0.19.0",
        "sha256:dddc678fe0abc6fa03c2e61c8fcafef2570b496775a11a25e1ab29e01bfe5130",
        5,
        "x86:movaps/xmm-rsp-disp8/legacy",
        [reg("dest", "x86.xmm", "xmm", 0), disp("disp8", 8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `movaps (%rsp), %xmm0` is a different shape (`0f 28 04 24`, no
    # displacement); the no-displacement decision has not landed for these
    # opcodes, so the name is absent rather than silently reusing a row.
    (
        "N01as-absent-no-displacement-sse-mem-sib-row",
        VERSION,
        DIGEST,
        4,
        "x86:movaps/xmm-rsp/legacy",
        [reg("dest", "x86.xmm", "xmm", 0)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # A 64-bit GPR on an `xmm` row: the register class is part of the row.
    (
        "N02v-gpr64-operand-on-sse-mem-sib-row",
        VERSION,
        DIGEST,
        5,
        "x86:movaps/xmm-rsp-disp8/legacy",
        [reg("dest", "x86.gpr64", "r64", 0), disp("disp8", 8)],
        [
            {"code": "E-OPERAND-001", "path": "/instructions/0/operands/0/kind",
             "detail_keys": ["expected", "found"]},
            {"code": "E-OPERAND-001",
             "path": "/instructions/0/operands/0/target_type",
             "detail_keys": ["expected", "found"]},
        ],
    ),
    # The base is fixed in the template and lives in no slot, so a `base`
    # operand is one operand too many.
    (
        "N02w-extra-base-operand-on-fixed-base-row",
        VERSION,
        DIGEST,
        5,
        "x86:movaps/xmm-rsp-disp8/legacy",
        [reg("dest", "x86.xmm", "xmm", 0), disp("disp8", 8),
         reg("base", "x86.gpr64", "rm64", 0)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The `disp8` content is signed, so 128 is a `disp32` operand.
    (
        "N03i-disp8-content-out-of-range-sse-mem-sib",
        VERSION,
        DIGEST,
        7,
        "x86:vmovaps/xmm-r12-disp8/vex",
        [reg("dest", "x86.xmm", "xmm", 1), disp("disp8", 128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The legacy register field is three bits, so 8 does not fit; the VEX rows
    # carry `R` in the prefix and would accept it, which is why this case names
    # a legacy row.
    (
        "N14w-register8-on-legacy-sse-mem-sib-row",
        VERSION,
        DIGEST,
        9,
        "x86:movaps/r12-disp32-xmm/legacy",
        [reg("src", "x86.xmm", "xmm", 8), disp("disp32", 128)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
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
