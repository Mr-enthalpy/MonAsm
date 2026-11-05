#!/usr/bin/env python3
"""Emit the six `X86-P20` negative fixtures.

Each case names one of the twelve VEX.256 memory rows and violates exactly one
rule: the row is absent from `0.15.0`, the vector kind/target_type is `zmm`,
the vector number needs a fifth bit, the base is SIB-forcing, the base is
outside the extended window, or the `disp8` content is out of range.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0045/fixture_negatives_p20.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.16.0"
DIGEST = "sha256:64ea1acf467afb2f858a5cb2967839445a5ffecac164a5f1b61931cb8fb3b99e"

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


def vector(role, kind, number) -> str:
    return operand(role, "x86.%s" % kind, kind, {"reg": number})


def base(number) -> str:
    return operand("base", "x86.gpr64", "rm64", {"reg": number})


def disp(target_type, value) -> str:
    return operand("disp", "x86.imm", target_type, {"value": value})


CASES = [
    # The row is new in 0.16.0, so 0.15.0 must reject it rather than fall back
    # to the register-direct `ymm` row.
    (
        "N01am-absent-vex256-base-ext-row-on-0.15.0",
        "0.15.0",
        "sha256:305e96047cf870f963c7115ec1ecb205cdb48d83e629b67d5eb8db7720a014a4",
        6,
        "x86:vmovaps/ymm-base-ext-disp8/vex",
        [vector("dest", "ymm", 0), base(8), disp("disp8", 32)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `x86.ymm` is a distinct kind from `x86.zmm`; the width is the row's.
    (
        "N02q-zmm-operand-on-vex256-memory-row",
        VERSION,
        DIGEST,
        5,
        "x86:vmovaps/ymm-base-disp8/vex",
        [vector("dest", "zmm", 0), base(0), disp("disp8", 32)],
        [
            {"code": "E-OPERAND-001", "path": "/instructions/0/operands/0/kind",
             "detail_keys": ["expected", "found"]},
            {"code": "E-OPERAND-001",
             "path": "/instructions/0/operands/0/target_type",
             "detail_keys": ["expected", "found"]},
        ],
    ),
    # The VEX memory row has four vector bits (`R̄` + `ModRM.reg`).
    (
        "N14s-ymm16-on-4bit-vex256-memory-row",
        VERSION,
        DIGEST,
        6,
        "x86:vmovaps/ymm-base-ext-disp8/vex",
        [vector("dest", "ymm", 16), base(8), disp("disp8", 32)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # `mod = 00` spends `r/m = 101` on RIP-relative, so `%rbp` is excluded.
    (
        "N16r-rbp-on-vex256-no-disp-row",
        VERSION,
        DIGEST,
        4,
        "x86:vmovaps/ymm-base/vex",
        [vector("dest", "ymm", 0), base(5)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # The extended window is `r8`-`r15` minus `%r12` (SIB-forcing low bits).
    (
        "N16s-r12-on-vex256-base-ext-row",
        VERSION,
        DIGEST,
        6,
        "x86:vmovaps/ymm-base-ext-disp8/vex",
        [vector("dest", "ymm", 0), base(12), disp("disp8", 32)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "excluded"],
        }],
    ),
    # VEX `disp8` is the plain signed byte; there is no unit to divide.
    (
        "N03f-disp8-content-out-of-range-vex256",
        VERSION,
        DIGEST,
        5,
        "x86:vmovaps/ymm-base-disp8/vex",
        [vector("dest", "ymm", 0), base(0), disp("disp8", 128)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/2/payload/value",
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
