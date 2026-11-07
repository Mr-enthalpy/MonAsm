#!/usr/bin/env python3
"""Emit the nine `X86-P58` negative fixtures.

Each case names a `0.54.0` `0x67`+`REX` `mov` row and violates exactly one
rule: the row is absent from `0.53.0` (both directions), the index operand is
missing, the scale is `4` (past the two-bit field), the extended slot carries
`3` (inside the low window the row excludes), or an operand the row keeps low
is `8` (past its three-bit field).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0083/fixture_negatives_p58.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.54.0"
DIGEST = "sha256:4513f6a9b15293f96bb79e46dbd477ea7cc051e3fb33a9a9ce3792e8ac6fa8cd"
PREVIOUS = "sha256:9c4c913f51e0e74710f416cd03d1547e6d4af4f2b678c1f1c4ae46f5722ff52b"

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


LOAD8_R = "x86:mov/r32-ext-addr32-base-index-disp8/legacy"      # `67 44 8b 44 08 08`
STORE8_R = "x86:mov/addr32-base-index-disp8-r32-ext/legacy"     # `67 44 89 44 08 08`
LOAD8_B = "x86:mov/r32-addr32-base-ext-index-disp8/legacy"      # `67 41 8b 44 08 08`
LOAD8_X = "x86:mov/r32-addr32-base-index-ext-disp8/legacy"      # `67 42 8b 44 08 08`

CASES = [
    # The rows are new in 0.54.0, so 0.53.0 must reject both names.
    (
        "N01dj-absent-addr32-single-rex-load-row-on-0.53.0",
        "0.53.0",
        PREVIOUS,
        6,
        LOAD8_R,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01dk-absent-addr32-single-rex-store-row-on-0.53.0",
        "0.53.0",
        PREVIOUS,
        6,
        STORE8_R,
        [reg("src", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The row has five slots, so dropping the index is a role-sequence miss.
    (
        "N02by-missing-index-operand-on-addr32-single-rex-row",
        VERSION,
        DIGEST,
        6,
        LOAD8_B,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr32", "rm32", 8), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The scale slot is two bits, so 4 (a x16 multiplier) does not fit.
    (
        "N03zg-scale4-on-addr32-single-rex-row",
        VERSION,
        DIGEST,
        6,
        LOAD8_X,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 9), scale(4), disp(8)],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/3/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The extended slots exclude 0-7: the low window is another row.
    (
        "N16cm-register3-on-addr32-single-rex-r-row",
        VERSION,
        DIGEST,
        6,
        LOAD8_R,
        [reg("dest", "x86.gpr32", "r32", 3),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    (
        "N16cn-base3-on-addr32-single-rex-b-row",
        VERSION,
        DIGEST,
        6,
        LOAD8_B,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr32", "rm32", 3),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    (
        "N16co-index3-on-addr32-single-rex-x-row",
        VERSION,
        DIGEST,
        6,
        LOAD8_X,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr32", "rm32", 0),
         reg("index", "x86.gpr32", "sib_index32", 3), scale(0), disp(8)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The operands a row keeps low are three-bit fields, so 8 needs the
    # deferred two-bit window rather than an operand value.
    (
        "N14bn-base8-on-addr32-single-rex-r-row",
        VERSION,
        DIGEST,
        6,
        LOAD8_R,
        [reg("dest", "x86.gpr32", "r32", 8),
         reg("base", "x86.gpr32", "rm32", 8),
         reg("index", "x86.gpr32", "sib_index32", 1), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
        }],
    ),
    (
        "N14bo-index8-on-addr32-single-rex-b-row",
        VERSION,
        DIGEST,
        6,
        LOAD8_B,
        [reg("dest", "x86.gpr32", "r32", 0),
         reg("base", "x86.gpr32", "rm32", 8),
         reg("index", "x86.gpr32", "sib_index32", 8), scale(0), disp(8)],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/2/payload/reg",
            "detail_keys": ["field_bits", "target_type", "value"],
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
