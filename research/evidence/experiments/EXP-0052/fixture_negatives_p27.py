#!/usr/bin/env python3
"""Emit the six `X86-P27` negative fixtures.

Each case names a `0.23.0` `SIB` index/scale row and violates exactly one rule:
the row is absent from `0.22.0` (load and store), the scale is carried as
`x86.imm` instead of `x86.scale`, a `disp` operand is supplied to a row with no
`disp` slot, the index is `4` (the "no index" encoding), or the base is `5` on
the no-displacement row (where `SIB.base = 101` means "no base").

Usage (from the repository root):

    python research/evidence/experiments/EXP-0052/fixture_negatives_p27.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.23.0"
DIGEST = "sha256:507e55c84cc80cf8bd9be10a6c6e4f7cff4999084fb41b3138df60b68a283962"

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


# `dest`, base `%rsp`, index `%rax`, scale ×1: the first row of the fixture.
FULL = [
    reg("dest", "x86.xmm", "xmm", 20),
    reg("base", "x86.gpr64", "rm64", 4),
    reg("index", "x86.gpr64", "sib_index", 0),
    scale(0),
]

CASES = [
    # The load row is new in 0.23.0, so 0.22.0 must reject the name rather than
    # repurpose the fixed-base or general-base row.
    (
        "N01ax-absent-evex-mem-sib-index-row-on-0.22.0",
        "0.22.0",
        "sha256:61c7cd1c940a7b22838a2c3418ba54031a20c6b227203fb9b4a57875f1c36b58",
        7,
        "x86:vmovaps/xmm-base-index/evex",
        FULL,
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store half is a separate row, so it has its own version boundary.
    (
        "N01ay-absent-evex-mem-sib-index-store-row-on-0.22.0",
        "0.22.0",
        "sha256:61c7cd1c940a7b22838a2c3418ba54031a20c6b227203fb9b4a57875f1c36b58",
        7,
        "x86:vmovaps/base-index-zmm/evex",
        [
            reg("src", "x86.zmm", "zmm", 28),
            reg("base", "x86.gpr64", "rm64", 4),
            reg("index", "x86.gpr64", "sib_index", 12),
            scale(0),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The scale is field content under `x86.scale`; `x86.imm` is a different
    # encoder and must never write the two `SIB` bits.
    (
        "N02ab-scale-spelled-x86-imm",
        VERSION,
        DIGEST,
        7,
        "x86:vmovaps/xmm-base-index/evex",
        FULL[:3] + [operand("imm", "x86.imm", "scale2", {"value": 0})],
        [{
            "code": "E-OPERAND-001",
            "path": "/instructions/0/operands/3/kind",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The no-displacement row has no `disp` slot, so a displacement operand is
    # one operand too many.
    (
        "N02ac-extra-disp-operand-on-evex-mem-sib-index-row",
        VERSION,
        DIGEST,
        7,
        "x86:vmovaps/xmm-base-index/evex",
        FULL + [disp("disp8x16", 1)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `SIB.index = 100` with no extension bit is the "no index" encoding, so
    # `%rsp` is not an index; `%r12` (number 12) is.
    (
        "N16aa-index4-on-evex-mem-sib-index-row",
        VERSION,
        DIGEST,
        8,
        "x86:vmovaps/xmm-base-index-disp8x16/evex",
        [
            reg("dest", "x86.xmm", "xmm", 21),
            reg("base", "x86.gpr64", "rm64", 4),
            reg("index", "x86.gpr64", "sib_index", 4),
            scale(1),
            disp("disp8x16", 2),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # On the no-displacement row `SIB.base = 101` means "no base, disp32", so
    # `%rbp` and `%r13` keep the `disp8*N = 0` row instead.
    (
        "N16ab-base5-on-evex-no-displacement-index-row",
        VERSION,
        DIGEST,
        7,
        "x86:vmovaps/xmm-base-index/evex",
        [
            reg("dest", "x86.xmm", "xmm", 20),
            reg("base", "x86.gpr64", "rm64", 5),
            reg("index", "x86.gpr64", "sib_index", 0),
            scale(0),
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
