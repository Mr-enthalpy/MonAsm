#!/usr/bin/env python3
"""Emit the six `X86-P28` negative fixtures.

Each case names a `0.24.0` no-base index/`disp32` row and violates exactly one
rule: the row is absent from `0.23.0` (load and store), a `base` operand is
supplied to a row that has no `base` slot, the scale is carried as `x86.imm`
instead of `x86.scale`, the `disp32` content is one past the signed end point,
or the index is `4` (the "no index" encoding).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0053/fixture_negatives_p28.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.24.0"
DIGEST = "sha256:2521f2dcc9636c1e3a671bbfbf224dcaecb741014bf65b0660ae5cc1c8c4aca3"
PREVIOUS = "sha256:507e55c84cc80cf8bd9be10a6c6e4f7cff4999084fb41b3138df60b68a283962"

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


def disp(target_type, value) -> str:
    return operand("disp", "x86.imm", target_type, {"value": value})


# `dest`, index `%rax`, scale x1, `disp32 = 0`: the first row of the fixture.
FULL = [
    reg("dest", "x86.xmm", "xmm", 20),
    reg("index", "x86.gpr64", "sib_index", 0),
    scale(0),
    disp("disp32", 0),
]

CASES = [
    # The load row is new in 0.24.0, so 0.23.0 must reject the name rather than
    # repurpose the with-base disp32 row.
    (
        "N01az-absent-evex-mem-sib-nobase-load-row-on-0.23.0",
        "0.23.0",
        PREVIOUS,
        11,
        "x86:vmovaps/xmm-index-disp32/evex",
        FULL,
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store half is a separate row, so it has its own version boundary.
    (
        "N01ba-absent-evex-mem-sib-nobase-store-row-on-0.23.0",
        "0.23.0",
        PREVIOUS,
        11,
        "x86:vmovaps/index-disp32-zmm/evex",
        [
            reg("src", "x86.zmm", "zmm", 30),
            reg("index", "x86.gpr64", "sib_index", 6),
            scale(1),
            disp("disp32", 0),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has no `base` slot at all: `SIB.base = 101` is a template fact,
    # so a base operand is one operand too many.
    (
        "N02ad-extra-base-operand-on-evex-mem-sib-nobase-row",
        VERSION,
        DIGEST,
        11,
        "x86:vmovaps/xmm-index-disp32/evex",
        [FULL[0], reg("base", "x86.gpr64", "rm64", 4)] + FULL[1:],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale is field content under `x86.scale`; `x86.imm` is a different
    # encoder and must never write the two `SIB` bits.
    (
        "N02ae-scale-spelled-x86-imm-on-evex-mem-sib-nobase-row",
        VERSION,
        DIGEST,
        11,
        "x86:vmovaps/xmm-index-disp32/evex",
        FULL[:2] + [operand("imm", "x86.imm", "scale2", {"value": 0}), FULL[3]],
        [{
            "code": "E-OPERAND-001",
            "path": "/instructions/0/operands/2/kind",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `disp32` is signed 32-bit content; 2147483648 is one past the field, and
    # wrapping it would be a silent repair.
    (
        "N03k-disp32-past-end-on-evex-mem-sib-nobase-row",
        VERSION,
        DIGEST,
        11,
        "x86:vmovaps/xmm-index-disp32/evex",
        [FULL[0], FULL[1], FULL[2], disp("disp32", 2147483648)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # `SIB.index = 100` with no extension bit is the "no index" encoding, so
    # `%rsp` is not an index; `%r12` (number 12) is.
    (
        "N16ac-index4-on-evex-mem-sib-nobase-row",
        VERSION,
        DIGEST,
        11,
        "x86:vmovaps/xmm-index-disp32/evex",
        [
            reg("dest", "x86.xmm", "xmm", 20),
            reg("index", "x86.gpr64", "sib_index", 4),
            scale(0),
            disp("disp32", 0),
        ],
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
