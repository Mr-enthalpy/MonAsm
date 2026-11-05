#!/usr/bin/env python3
"""Emit the ten `X86-P34` negative fixtures.

Each case names a `0.30.0` extended-byte-register memory row and violates
exactly one rule: the row is absent from `0.29.0` (a load and a store), the
high-byte kind is supplied to an extended row, the displacement carries the
`disp8` target type instead of `disp32`, a `base` operand is supplied to a
`SIB` row that has no base slot, the displacement content is one past the
signed end, the register is one past the four-bit field, the register is below
the extended window, or the base is `%rsp` / `%r12` on a row that has no `SIB`
byte.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0059/fixture_negatives_p34.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.30.0"
DIGEST = "sha256:5dae4541162884f14dfbebd7aaf38a49d4212f0e24155137391e6e0bf93c3cf2"
PREVIOUS = "sha256:cf78fac0b9c9b9828e74559bec9f612b609468ea2894c94c6e3e5b131c3951e6"

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


# `dest`, `8(%rax), %r8b`: the first row of the fixture.
FULL = [
    reg("dest", "x86.gpr8", "r8", 8),
    reg("base", "x86.gpr64", "rm64", 0),
    disp("disp8", 8),
]

CASES = [
    # The load row is new in 0.30.0, so 0.29.0 must reject the name rather
    # than reuse a `%spl`-`%dil` row.
    (
        "N01bm-absent-gpr8-ext-mov-mem-load-row-on-0.29.0",
        "0.29.0",
        PREVIOUS,
        4,
        "x86:mov/r8-ext-base-disp8/legacy",
        FULL,
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The `%r12` store row carries its own boundary.
    (
        "N01bn-absent-gpr8-ext-mov-mem-store-row-on-0.29.0",
        "0.29.0",
        PREVIOUS,
        8,
        "x86:mov/r12-disp32-r8-ext/legacy",
        [
            reg("src", "x86.gpr8", "r8", 11),
            disp("disp32", 200),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `%ah`-`%bh` cannot sit behind a REX byte, so the high-byte kind is a
    # different name on both axes (`ADR-0029`, `EC-36`).
    (
        "N02at-gpr8h-operand-on-gpr8-ext-mov-mem-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8-ext-base-disp8/legacy",
        [
            reg("dest", "x86.gpr8h", "r8h", 8),
            reg("base", "x86.gpr64", "rm64", 0),
            disp("disp8", 8),
        ],
        [
            {
                "code": "E-OPERAND-001",
                "path": "/instructions/0/operands/0/kind",
                "detail_keys": ["expected", "found"],
            },
            {
                "code": "E-OPERAND-001",
                "path": "/instructions/0/operands/0/target_type",
                "detail_keys": ["expected", "found"],
            },
        ],
    ),
    # The displacement width is the row's target type; the unit may not be
    # re-derived from the value.
    (
        "N02au-displacement-carried-as-disp8-on-gpr8-ext-mov-mem-disp32-row",
        VERSION,
        DIGEST,
        7,
        "x86:mov/r8-ext-base-disp32/legacy",
        [
            reg("dest", "x86.gpr8", "r8", 15),
            reg("base", "x86.gpr64", "rm64", 8),
            disp("disp8", 8),
        ],
        [{
            "code": "E-OPERAND-001",
            "path": "/instructions/0/operands/2/target_type",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # A `SIB` row fixes `SIB.base = 100`, so there is no base operand to name.
    (
        "N02av-extra-base-operand-on-gpr8-ext-mov-mem-sib-row",
        VERSION,
        DIGEST,
        5,
        "x86:mov/r8-ext-rsp-disp8/legacy",
        [
            reg("dest", "x86.gpr8", "r8", 9),
            reg("base", "x86.gpr64", "rm64", 0),
            disp("disp8", 8),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `disp32` is signed 32-bit content; 2147483648 is one past the field.
    (
        "N03q-disp32-past-end-on-gpr8-ext-mov-mem-row",
        VERSION,
        DIGEST,
        7,
        "x86:mov/r8-ext-base-disp32/legacy",
        [
            reg("dest", "x86.gpr8", "r8", 15),
            reg("base", "x86.gpr64", "rm64", 8),
            disp("disp32", 2147483648),
        ],
        [{
            "code": "E-RANGE-001",
            "path": "/instructions/0/operands/2/payload/value",
            "detail_keys": ["min", "max", "value", "target_type"],
        }],
    ),
    # The extended register slot is four bits; 16 is outside the field
    # (`llvm-mc` would reach for the APX `d5` prefix).
    (
        "N14ad-register-16-on-gpr8-ext-mov-mem-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8-ext-base-disp8/legacy",
        [
            reg("dest", "x86.gpr8", "r8", 16),
            reg("base", "x86.gpr64", "rm64", 0),
            disp("disp8", 8),
        ],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # The template's `REX.R = 1` is the slot's top bit, so `%al`-`%r7b` would
    # clear it and emit the `%spl`-`%dil` row's prefix.
    (
        "N16ag-register-0-on-gpr8-ext-mov-mem-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8-ext-base-disp8/legacy",
        [
            reg("dest", "x86.gpr8", "r8", 0),
            reg("base", "x86.gpr64", "rm64", 0),
            disp("disp8", 8),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/0/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%rsp` needs the `SIB` byte, so the plain-base row excludes it.
    (
        "N16ah-base-rsp-on-gpr8-ext-mov-mem-plain-base-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8-ext-base-disp8/legacy",
        [
            reg("dest", "x86.gpr8", "r8", 8),
            reg("base", "x86.gpr64", "rm64", 4),
            disp("disp8", 8),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%r12` shares `%rsp`'s low three bits and needs its own `SIB` row.
    (
        "N16ai-base-r12-on-gpr8-ext-mov-mem-plain-base-row",
        VERSION,
        DIGEST,
        4,
        "x86:mov/r8-ext-base-disp8/legacy",
        [
            reg("dest", "x86.gpr8", "r8", 8),
            reg("base", "x86.gpr64", "rm64", 12),
            disp("disp8", 8),
        ],
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
