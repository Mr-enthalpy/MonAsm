#!/usr/bin/env python3
"""Emit the five `X86-P29` negative fixtures.

Each case names a `0.25.0` absolute-address row and violates exactly one rule:
the row is absent from `0.24.0` (load and store), an `index` operand is supplied
to a row that has no register in its address, the address operand carries the
`disp8` target type instead of `disp32`, or the address content is one past the
signed end point.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0054/fixture_negatives_p29.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.25.0"
DIGEST = "sha256:b72c0b08d30e9bbfd0c5129e01e1cecf77abcde36e2928aab2f94bb80c06a51c"
PREVIOUS = "sha256:2521f2dcc9636c1e3a671bbfbf224dcaecb741014bf65b0660ae5cc1c8c4aca3"

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


# `dest`, `0x1234`: the first row of the fixture.
FULL = [
    reg("dest", "x86.xmm", "xmm", 20),
    disp("disp32", 4660),
]

CASES = [
    # The load row is new in 0.25.0, so 0.24.0 must reject the name rather than
    # repurpose the no-base indexed row.
    (
        "N01bb-absent-evex-mem-sib-absolute-load-row-on-0.24.0",
        "0.24.0",
        PREVIOUS,
        11,
        "x86:vmovaps/xmm-abs32/evex",
        FULL,
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store half is a separate row, so it has its own version boundary.
    (
        "N01bc-absent-evex-mem-sib-absolute-store-row-on-0.24.0",
        "0.24.0",
        PREVIOUS,
        11,
        "x86:vmovaps/abs32-zmm/evex",
        [
            reg("src", "x86.zmm", "zmm", 30),
            disp("disp32", -2147483648),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The absolute row has no register in its address: an index operand is one
    # operand too many, and `SIB.index = 100` is a template bit.
    (
        "N02af-extra-index-operand-on-evex-mem-sib-absolute-row",
        VERSION,
        DIGEST,
        11,
        "x86:vmovaps/xmm-abs32/evex",
        [FULL[0], reg("index", "x86.gpr64", "sib_index", 0), FULL[1]],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The address is four bytes; `disp8` is the target type of a different
    # field, and the row's unit may not be re-derived from the value.
    (
        "N02ag-address-carried-as-disp8-on-evex-mem-sib-absolute-row",
        VERSION,
        DIGEST,
        11,
        "x86:vmovaps/xmm-abs32/evex",
        [FULL[0], disp("disp8", 0)],
        [{
            "code": "E-OPERAND-001",
            "path": "/instructions/0/operands/1/target_type",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `disp32` is signed 32-bit content; 2147483648 is one past the field, and
    # wrapping it would be a silent repair.
    (
        "N03l-disp32-past-end-on-evex-mem-sib-absolute-row",
        VERSION,
        DIGEST,
        11,
        "x86:vmovaps/xmm-abs32/evex",
        [FULL[0], disp("disp32", 2147483648)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/1/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
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
