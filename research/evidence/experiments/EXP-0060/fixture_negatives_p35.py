#!/usr/bin/env python3
"""Emit the nine `X86-P35` negative fixtures.

Each case names a `0.31.0` no-displacement byte `mov` row and violates exactly
one rule: the row is absent from `0.30.0` (a load and a store), the high-byte
kind is supplied to a low-window row, a `disp` operand is supplied to a row
with no displacement slot, the base is one past the three-bit field, or the
base is one of the four values the row excludes (`%rbp` and `%r13` collide
with `r/m = 101`; `%rsp` and `%r12` need a `SIB` byte).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0060/fixture_negatives_p35.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.31.0"
DIGEST = "sha256:cc01b72ceed0c77e5079b53ea8f3035ebf44b02fd156f1aae207044cb44327d5"
PREVIOUS = "sha256:5dae4541162884f14dfbebd7aaf38a49d4212f0e24155137391e6e0bf93c3cf2"

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


LOW = "x86:mov/r8-base/legacy"          # `8a 00`
EXT = "x86:mov/r8-ext-base/legacy"      # `44 8a 00`
EXT_STORE = "x86:mov/base-r8-ext/legacy"  # `44 88 00`

CASES = [
    # The load row is new in 0.31.0, so 0.30.0 must reject the name rather
    # than reuse the three-byte `disp8` row.
    (
        "N01bo-absent-gpr8-mov-mem-load-row-on-0.30.0",
        "0.30.0",
        PREVIOUS,
        2,
        LOW,
        [
            reg("dest", "x86.gpr8", "r8", 0),
            reg("base", "x86.gpr64", "rm64", 0),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # The store row carries its own boundary, on the extended window.
    (
        "N01bp-absent-gpr8-mov-mem-store-row-on-0.30.0",
        "0.30.0",
        PREVIOUS,
        3,
        EXT_STORE,
        [
            reg("src", "x86.gpr8", "r8", 15),
            reg("base", "x86.gpr64", "rm64", 9),
        ],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `%ah`-`%bh` is a different kind, not a different number: the low row
    # carries `x86.gpr8`/`r8` only (`ADR-0029`, `EC-36`).
    (
        "N02aw-gpr8h-operand-on-gpr8-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        2,
        LOW,
        [
            reg("dest", "x86.gpr8h", "r8h", 0),
            reg("base", "x86.gpr64", "rm64", 0),
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
    # The row has no displacement slot at all, so a zero must not be implied.
    (
        "N02ax-extra-disp-operand-on-gpr8-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        2,
        LOW,
        [
            reg("dest", "x86.gpr8", "r8", 0),
            reg("base", "x86.gpr64", "rm64", 0),
            disp("disp8", 0),
        ],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # The `REX`-less rows keep the three-bit base, so `%r8` is outside the
    # field rather than an extended register with a `REX.B` placement.
    (
        "N14ae-base-8-on-gpr8-mov-mem-nodisp-three-bit-row",
        VERSION,
        DIGEST,
        2,
        LOW,
        [
            reg("dest", "x86.gpr8", "r8", 0),
            reg("base", "x86.gpr64", "rm64", 8),
        ],
        [{
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["target_type", "value", "field_bits"],
        }],
    ),
    # `r/m = 101` at `mod = 00` means RIP-relative `disp32`, so `%rbp` cannot
    # inhabit the row (`llvm-mc` writes `8a 45 00`).
    (
        "N16aj-base-rbp-on-gpr8-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        2,
        LOW,
        [
            reg("dest", "x86.gpr8", "r8", 0),
            reg("base", "x86.gpr64", "rm64", 5),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%r13` is the same `r/m` value with `REX.B = 1`, so the four-bit row
    # excludes it too.
    (
        "N16ak-base-r13-on-gpr8-mov-mem-nodisp-ext-row",
        VERSION,
        DIGEST,
        3,
        EXT,
        [
            reg("dest", "x86.gpr8", "r8", 8),
            reg("base", "x86.gpr64", "rm64", 13),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%rsp` needs the `SIB` byte the two-byte row does not carry.
    (
        "N16al-base-rsp-on-gpr8-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        2,
        LOW,
        [
            reg("dest", "x86.gpr8", "r8", 0),
            reg("base", "x86.gpr64", "rm64", 4),
        ],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%r12` shares `%rsp`'s low three bits and needs the same `SIB` byte on
    # the extended row.
    (
        "N16am-base-r12-on-gpr8-mov-mem-nodisp-ext-row",
        VERSION,
        DIGEST,
        3,
        EXT,
        [
            reg("dest", "x86.gpr8", "r8", 8),
            reg("base", "x86.gpr64", "rm64", 12),
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
