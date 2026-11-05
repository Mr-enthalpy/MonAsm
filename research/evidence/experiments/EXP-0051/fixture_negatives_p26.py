#!/usr/bin/env python3
"""Emit the six `X86-P26` negative fixtures.

Each case names a `0.22.0` no-displacement `SIB` row and violates exactly one
rule: the row is absent from `0.21.0`, the `%rbp`/`%r13` shape has no encoding
(`mod = 00`, `r/m = 101` is RIP-relative), the register kind is wrong, an extra
`disp` operand is supplied to a row with no `disp` slot, the five-bit EVEX
register field is asked for 32, or `%rsp` is named on the general
no-displacement row that still excludes the `SIB`-forcing values.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0051/fixture_negatives_p26.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.22.0"
DIGEST = "sha256:61c7cd1c940a7b22838a2c3418ba54031a20c6b227203fb9b4a57875f1c36b58"

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


FORM = "x86:vmovaps/xmm-rsp/evex"

CASES = [
    # The fixed-base no-displacement EVEX rows are new in 0.22.0, so 0.21.0
    # must reject the name rather than repurpose the `-base` row.
    (
        "N01av-absent-evex-mem-sib-nodisp-row-on-0.21.0",
        "0.21.0",
        "sha256:30af3fec5c2f50e3ab30fb30d32e6b2e71f4520dbdb2660c6c9de1767b7b1160",
        7,
        FORM,
        [reg("dest", "x86.xmm", "xmm", 0)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `{evex} vmovaps (%rbp), %xmm0` has no `mod = 00` encoding: `r/m = 101`
    # means RIP-relative, so the assembler keeps `disp8 = 0` and no SIB byte.
    (
        "N01aw-absent-rbp-no-displacement-evex-row",
        VERSION,
        DIGEST,
        7,
        "x86:vmovaps/xmm-rbp/evex",
        [reg("dest", "x86.xmm", "xmm", 0)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # A 64-bit GPR on an `xmm` row: the register class is part of the row.
    (
        "N02z-gpr64-operand-on-evex-mem-sib-nodisp-row",
        VERSION,
        DIGEST,
        7,
        FORM,
        [reg("dest", "x86.gpr64", "r64", 0)],
        [
            {"code": "E-OPERAND-001", "path": "/instructions/0/operands/0/kind",
             "detail_keys": ["expected", "found"]},
            {"code": "E-OPERAND-001",
             "path": "/instructions/0/operands/0/target_type",
             "detail_keys": ["expected", "found"]},
        ],
    ),
    # There is no `disp` slot in this shape, so a displacement operand is one
    # operand too many.
    (
        "N02aa-extra-disp-operand-on-fixed-base-row",
        VERSION,
        DIGEST,
        7,
        FORM,
        [reg("dest", "x86.xmm", "xmm", 0), disp("disp8x16", 1)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The EVEX vector slot is five bits, so 32 does not fit.
    (
        "N14y-register32-on-evex-mem-sib-nodisp-row",
        VERSION,
        DIGEST,
        7,
        FORM,
        [reg("dest", "x86.xmm", "xmm", 32)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The general `mod = 00` row still excludes the two SIB-forcing values;
    # `%rsp` must name the new fixed-base row, never the general one.
    (
        "N16z-rsp-on-general-evex-no-displacement-row",
        VERSION,
        DIGEST,
        6,
        "x86:vmovaps/xmm-base/evex",
        [reg("dest", "x86.xmm", "xmm", 0), reg("base", "x86.gpr64", "rm64", 4)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
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
