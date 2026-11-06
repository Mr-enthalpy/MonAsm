#!/usr/bin/env python3
"""Emit the eight `X86-P49` negative fixtures.

Each case names a `0.45.0` 16-bit indexed `mov` row and violates exactly one
rule: the row is absent from `0.44.0` (both directions), the index operand is
missing, the scale is `4` (past the two-bit field), the register is past the
four-bit window, the index is `4` (`%rsp`, the "no index" encoding), a low
register reaches an `-ext` row (it would clear the fixed `REX.R`), or the base
is past the four-bit window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0074/fixture_negatives_p49.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.45.0"
DIGEST = "sha256:9adaf50a6798c7b4bd5f0090f9860de30e360994c45138f017a3c1298e5fc2d8"
PREVIOUS = "sha256:4361f534bd04064d9ce0b89e8d5f6ad077ceb4a8c890b103efc16899e887c922"

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


def disp(value) -> str:
    return operand("disp", "x86.imm", "disp8", {"value": value})


LOAD8 = "x86:mov/r16-ext-base-index-disp8/legacy"    # `66 44 8b 44 00 00`
STORE8 = "x86:mov/base-index-disp8-r16-ext/legacy"   # `66 44 89 44 00 00`

CASES = [
    # Both directions are new in 0.45.0, so 0.44.0 must reject the names.
    (
        "N01cr-absent-gpr16-mov-index-disp8-rex-rx-load-row-on-0.44.0",
        "0.44.0",
        PREVIOUS,
        6,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01cs-absent-gpr16-mov-index-disp8-rex-rx-store-row-on-0.44.0",
        "0.44.0",
        PREVIOUS,
        6,
        STORE8,
        [reg("src", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 7),
         reg("index", "x86.gpr64", "sib_index", 12), scale(2), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02bo-missing-index-operand-on-gpr16-mov-index-disp8-rex-rx-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a ×16 multiplier) does not fit.
    (
        "N03x-scale4-on-gpr16-mov-index-disp8-rex-rx-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The register window is four bits, so 16 is past its end.
    (
        "N14ay-register16-on-gpr16-mov-index-disp8-rex-rx-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 16),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # `SIB.index = 100` with `REX.X = 0` means "no index", so `%rsp` is illegal.
    (
        "N16bv-index4-on-gpr16-mov-index-disp8-rex-rx-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 4), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # A low register would clear the fixed `REX.R` bit.
    (
        "N16bw-register0-on-gpr16-mov-index-disp8-rex-rx-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 0),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The base window is four bits, so 16 is past its end.
    (
        "N14az-base16-on-gpr16-mov-index-disp8-rex-rx-row",
        VERSION,
        DIGEST,
        6,
        LOAD8,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 16),
         reg("index", "x86.gpr64", "sib_index", 1), scale(0), disp(8)],
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
