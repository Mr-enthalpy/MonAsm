#!/usr/bin/env python3
"""Emit the eight `X86-P48` negative fixtures.

Each case names a `0.44.0` 16-bit `disp32` `mov` row with the `REX.R`
register window and violates exactly one rule: the row is absent from
`0.43.0` (both directions), the displacement operand is missing or past the
signed 32-bit span, the register is past the four-bit window, a low register
reaches an `-ext` row (it would clear the fixed `REX.R`), `%rsp` reaches a
plain base (it needs the fixed `SIB` row), or `%rbp` reaches the `-ext`-base
row (it would clear the fixed `REX.B`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0073/fixture_negatives_p48.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.44.0"
DIGEST = "sha256:4361f534bd04064d9ce0b89e8d5f6ad077ceb4a8c890b103efc16899e887c922"
PREVIOUS = "sha256:da40c8548f75b6dd0f509ff1b10e9b3e633c69a7a3a26d660d6bd87c58a1a54c"

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


def disp(value) -> str:
    return operand("disp", "x86.imm", "disp32", {"value": value})


LOAD_LOW = "x86:mov/r16-ext-base-disp32/legacy"          # `66 44 8b 80 00 00 00 00`
STORE_LOW = "x86:mov/base-disp32-r16-ext/legacy"         # `66 44 89 80 00 00 00 00`
LOAD_EXT = "x86:mov/r16-ext-base-ext-disp32/legacy"      # `66 45 8b 80 00 00 00 00`

CASES = [
    # Both directions are new in 0.44.0, so 0.43.0 must reject the names.
    (
        "N01cp-absent-gpr16-mov-mem-disp32-rex-r-load-row-on-0.43.0",
        "0.43.0",
        PREVIOUS,
        8,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0), disp(200)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01cq-absent-gpr16-mov-mem-disp32-rex-r-store-row-on-0.43.0",
        "0.43.0",
        PREVIOUS,
        8,
        STORE_LOW,
        [reg("src", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 7), disp(200)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has three slots, so dropping the `disp` is one operand short.
    (
        "N02bn-missing-disp-operand-on-gpr16-mov-mem-disp32-rex-r-row",
        VERSION,
        DIGEST,
        8,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The displacement slot is a signed 32-bit field, so 2^31 does not fit.
    (
        "N03w-disp32-2147483648-on-gpr16-mov-mem-disp32-rex-r-row",
        VERSION,
        DIGEST,
        8,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 0), disp(2147483648)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/2/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The register window is four bits, so 16 is past its end.
    (
        "N14ax-register16-on-gpr16-mov-mem-disp32-rex-r-row",
        VERSION,
        DIGEST,
        8,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 16),
         reg("base", "x86.gpr64", "rm64", 0), disp(200)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # A low register would clear the fixed `REX.R` bit.
    (
        "N16bs-register0-on-gpr16-mov-mem-disp32-rex-r-row",
        VERSION,
        DIGEST,
        8,
        LOAD_EXT,
        [reg("dest", "x86.gpr16", "r16", 0),
         reg("base", "x86.gpr64", "rm64", 8), disp(200)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%rsp` is `r/m = 100` and needs the fixed `SIB` row.
    (
        "N16bt-rsp-on-gpr16-mov-mem-disp32-rex-r-row",
        VERSION,
        DIGEST,
        8,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 4), disp(200)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%rbp` is a legal base at `mod = 10`, but not on the `-ext` row, where
    # the base would clear the fixed `REX.B` bit.
    (
        "N16bu-rbp-on-gpr16-mov-mem-disp32-rex-r-ext-row",
        VERSION,
        DIGEST,
        8,
        LOAD_EXT,
        [reg("dest", "x86.gpr16", "r16", 8),
         reg("base", "x86.gpr64", "rm64", 5), disp(200)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
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
