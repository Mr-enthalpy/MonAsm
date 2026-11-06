#!/usr/bin/env python3
"""Emit the seven `X86-P46` negative fixtures.

Each case names a `0.42.0` 16-bit `mod = 00` `mov` row with the `REX.R`
register window and violates exactly one rule: the row is absent from
`0.41.0` (both directions), a `disp` operand is supplied to a row that has no
displacement, the register is past the four-bit window, a low register reaches
an `-ext` row (it would clear the fixed `REX.R`), or `%rsp`/`%rbp` reach a
plain base (both need their own shape).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0071/fixture_negatives_p46.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.42.0"
DIGEST = "sha256:b45380cd781c4e2fd26da3218a2655b332ba7ab17680782d99aca5ed0bdc6c9b"
PREVIOUS = "sha256:a2c5fa28122f43ce824ee637017dd6fdaef4e7455122b5cfa0e065c3400ffaef"

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
    return operand("disp", "x86.imm", "disp8", {"value": value})


LOAD_LOW = "x86:mov/r16-ext-base/legacy"        # `66 44 8b 00`
STORE_LOW = "x86:mov/base-r16-ext/legacy"       # `66 44 89 00`
LOAD_EXT = "x86:mov/r16-ext-base-ext/legacy"    # `66 45 8b 00`
LOAD_RSP = "x86:mov/r16-ext-rsp/legacy"         # `66 44 8b 04 24`

CASES = [
    # Both directions are new in 0.42.0, so 0.41.0 must reject the names.
    (
        "N01cl-absent-gpr16-mov-mem-nodisp-rex-r-load-row-on-0.41.0",
        "0.41.0",
        PREVIOUS,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 8), reg("base", "x86.gpr64", "rm64", 0)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01cm-absent-gpr16-mov-mem-nodisp-rex-r-store-row-on-0.41.0",
        "0.41.0",
        PREVIOUS,
        4,
        STORE_LOW,
        [reg("src", "x86.gpr16", "r16", 8), reg("base", "x86.gpr64", "rm64", 7)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `mod = 00` is no displacement, so the row has one slot and a supplied
    # `disp` is one operand too many.
    (
        "N02bl-supplied-disp-operand-on-gpr16-mov-mem-nodisp-rex-r-row",
        VERSION,
        DIGEST,
        5,
        LOAD_RSP,
        [reg("dest", "x86.gpr16", "r16", 8), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The register window is four bits, so 16 is past its end.
    (
        "N14av-register16-on-gpr16-mov-mem-nodisp-rex-r-row",
        VERSION,
        DIGEST,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 16), reg("base", "x86.gpr64", "rm64", 0)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # A low register would clear the fixed `REX.R` bit.
    (
        "N16bm-register0-on-gpr16-mov-mem-nodisp-rex-r-row",
        VERSION,
        DIGEST,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 0)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%rsp` is `r/m = 100` and needs the fixed `SIB` row, not a plain base.
    (
        "N16bn-rsp-on-gpr16-mov-mem-nodisp-rex-r-row",
        VERSION,
        DIGEST,
        4,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 8), reg("base", "x86.gpr64", "rm64", 4)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `r/m = 101` at `mod = 00` is `rip`-relative, so `%rbp` is not a base.
    (
        "N16bo-rbp-on-gpr16-mov-mem-nodisp-rex-r-ext-row",
        VERSION,
        DIGEST,
        4,
        LOAD_EXT,
        [reg("dest", "x86.gpr16", "r16", 8), reg("base", "x86.gpr64", "rm64", 5)],
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
