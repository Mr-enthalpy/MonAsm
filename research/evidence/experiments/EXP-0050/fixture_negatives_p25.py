#!/usr/bin/env python3
"""Emit the six `X86-P25` negative fixtures.

Each case names one of the twenty-four fixed-base EVEX `SIB` rows and violates
exactly one rule: the row is absent from `0.20.0`, the no-displacement shape is
still absent from `0.21.0`, the register kind is wrong for the row, an extra
`base` operand is supplied to a row whose base is fixed, the `disp8*N` content
leaves its byte, or the five-bit EVEX register field is asked for 32.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0050/fixture_negatives_p25.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.21.0"
DIGEST = "sha256:30af3fec5c2f50e3ab30fb30d32e6b2e71f4520dbdb2660c6c9de1767b7b1160"

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


FORM = "x86:vmovaps/xmm-rsp-disp8x16/evex"

CASES = [
    # The fixed-base EVEX rows are new in 0.21.0, so 0.20.0 must reject the
    # name rather than fall back to the `-base-disp*` row.
    (
        "N01at-absent-evex-mem-sib-row-on-0.20.0",
        "0.20.0",
        "sha256:b8bd1ed3ed38d71f6b19cc1854c9252df13850127c4e9433981a3a45f49d0f99",
        8,
        FORM,
        [reg("dest", "x86.xmm", "xmm", 0), disp("disp8x16", 1)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `{evex} vmovaps (%rsp), %xmm0` is a different shape
    # (`62 f1 7c 08 28 04 24`, no displacement); the no-displacement decision
    # has not landed for this base, so the name is absent rather than silently
    # reusing a row.
    (
        "N01au-absent-no-displacement-evex-mem-sib-row",
        VERSION,
        DIGEST,
        7,
        "x86:vmovaps/xmm-rsp/evex",
        [reg("dest", "x86.xmm", "xmm", 0)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # A 64-bit GPR on an `xmm` row: the register class is part of the row.
    (
        "N02x-gpr64-operand-on-evex-mem-sib-row",
        VERSION,
        DIGEST,
        8,
        FORM,
        [reg("dest", "x86.gpr64", "r64", 0), disp("disp8x16", 1)],
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
        "N02y-extra-base-operand-on-fixed-base-row",
        VERSION,
        DIGEST,
        8,
        FORM,
        [reg("dest", "x86.xmm", "xmm", 0), disp("disp8x16", 1),
         reg("base", "x86.gpr64", "rm64", 4)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The `disp8x16` content is signed and already divided by 16, so 128 is a
    # `disp32` operand.
    (
        "N03j-disp8x16-content-out-of-range-evex-mem-sib",
        VERSION,
        DIGEST,
        8,
        FORM,
        [reg("dest", "x86.xmm", "xmm", 1), disp("disp8x16", 128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The EVEX vector slot is five bits, so 32 does not fit.
    (
        "N14x-register32-on-evex-mem-sib-row",
        VERSION,
        DIGEST,
        8,
        FORM,
        [reg("dest", "x86.xmm", "xmm", 32), disp("disp8x16", 1)],
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
