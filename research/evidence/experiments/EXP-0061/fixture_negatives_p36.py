#!/usr/bin/env python3
"""Emit the eight `X86-P36` negative fixtures.

Each case names a `0.32.0` `%rsp`/`%r12` no-displacement `SIB` row and
violates exactly one rule: the row is absent from `0.31.0` (a load and a
store), the high-byte `%r12` half does not exist, a `base` or `disp` operand is
supplied to a row whose address is fixed in the template, the register is one
past the three-bit field, the register is below a relabelled window, or the
register is `0` on the `REX = 40` row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0061/fixture_negatives_p36.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.32.0"
DIGEST = "sha256:bad81d6655d9e612fa353814fa40ba9910ba3830ac954df2169365abd02563ac"
PREVIOUS = "sha256:cc01b72ceed0c77e5079b53ea8f3035ebf44b02fd156f1aae207044cb44327d5"

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


LOAD = "x86:mov/r8-rsp/legacy"            # `8a 04 24`
LOAD_EXT = "x86:mov/r12-r8-ext/legacy"    # `45 88 04 24`, store; see below
REX_LOAD = "x86:mov/r8-rsp-rex/legacy"    # `40 8a 24 24`

CASES = [
    # The load row is new in 0.32.0, so 0.31.0 must reject the name rather
    # than fall back to the three-byte plain-base row (which excludes %rsp).
    (
        "N01bq-absent-gpr8-mov-mem-sib-load-row-on-0.31.0",
        "0.31.0",
        PREVIOUS,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr8", "r8", 0),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store row carries its own boundary, on the extended window.
    (
        "N01br-absent-gpr8-mov-mem-sib-store-row-on-0.31.0",
        "0.31.0",
        PREVIOUS,
        4,
        LOAD_EXT,
        [
            reg("src", "x86.gpr8", "r8", 15),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `REX.B` renames `%ah`, so there is no `%r12` row in the high-byte
    # window; naming one is an absent form, not a repairable plan.
    (
        "N01bs-absent-gpr8h-r12-sib-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8h-r12/legacy",
        [
            reg("dest", "x86.gpr8h", "r8h", 4),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The base is a template constant, so a second operand is a count
    # mismatch rather than a base the row could honour.
    (
        "N02ay-extra-base-operand-on-gpr8-mov-mem-sib-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr8", "r8", 0),
            reg("base", "x86.gpr64", "rm64", 4),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `SIB = 24` has no displacement, so a `disp` operand is not an implied
    # zero here either.
    (
        "N02az-extra-disp-operand-on-gpr8-mov-mem-sib-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr8", "r8", 0),
            disp("disp8", 0),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The `REX`-less `%rsp` row keeps the three-bit register field.
    (
        "N14af-register16-on-gpr8-mov-mem-sib-three-bit-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr8", "r8", 16),
        ],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # Register 8 is outside the same three-bit field.
    (
        "N14ag-register8-on-gpr8-mov-mem-sib-three-bit-row",
        VERSION,
        DIGEST,
        3,
        LOAD,
        [
            reg("dest", "x86.gpr8", "r8", 8),
        ],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The `REX = 40` row relabels 4-7, so register 0 is excluded.
    (
        "N16an-register0-on-gpr8-mov-mem-sib-rex-row",
        VERSION,
        DIGEST,
        4,
        REX_LOAD,
        [
            reg("dest", "x86.gpr8", "r8", 0),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
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
