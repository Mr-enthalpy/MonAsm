#!/usr/bin/env python3
"""Emit the seven `X86-P45` negative fixtures.

Each case names a `0.41.0` 16-bit `mod = 00` `mov` row and violates exactly one
rule: the row is absent from `0.40.0` (both directions), a `disp` operand is
supplied to a row that has no displacement, `%rsp`/`%r12` reach a plain-base
row, a low base reaches the `-ext` row, or `%rbp`/`%r13` — which `mod = 00`
cannot hold — reach either plain window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0070/fixture_negatives_p45.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.41.0"
DIGEST = "sha256:a2c5fa28122f43ce824ee637017dd6fdaef4e7455122b5cfa0e065c3400ffaef"
PREVIOUS = "sha256:ddeb4734cab0483c6f440106954233072d352910998c5680e28b6d33352eb468"

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


LOAD_LOW = "x86:mov/r16-base/legacy"        # `66 8b 00`
STORE_LOW = "x86:mov/base-r16/legacy"       # `66 89 00`
LOAD_EXT = "x86:mov/r16-base-ext/legacy"    # `66 41 8b 00`
STORE_EXT = "x86:mov/base-ext-r16/legacy"   # `66 41 89 00`
LOAD_RSP = "x86:mov/r16-rsp/legacy"         # `66 8b 04 24`

CASES = [
    # Both directions are new in 0.41.0, so 0.40.0 must reject the names.
    (
        "N01cj-absent-gpr16-mov-mem-nodisp-load-row-on-0.40.0",
        "0.40.0",
        PREVIOUS,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 0)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    (
        "N01ck-absent-gpr16-mov-mem-nodisp-store-row-on-0.40.0",
        "0.40.0",
        PREVIOUS,
        3,
        STORE_LOW,
        [reg("src", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 7)],
        [{
            "code": "E-FORM-001",
            "path": "/instructions/0/form_id",
            "detail_keys": ["form_id", "namespace", "version"],
        }],
    ),
    # `mod = 00` is no displacement, so the row has one slot and a supplied
    # `disp` is one operand too many.
    (
        "N02bk-supplied-disp-operand-on-gpr16-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        4,
        LOAD_RSP,
        [reg("dest", "x86.gpr16", "r16", 0), disp(8)],
        [{
            "code": "E-OPERAND-002",
            "path": "/instructions/0/operands",
            "detail_keys": ["expected", "found"],
        }],
    ),
    # `%rsp` is `r/m = 100` and needs the fixed `SIB` row, not a plain base.
    (
        "N16bh-rsp-on-gpr16-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 4)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%r12` is the same `r/m = 100`, so it needs the fixed `SIB` row.
    (
        "N16bi-r12-on-gpr16-mov-mem-nodisp-ext-row",
        VERSION,
        DIGEST,
        4,
        LOAD_EXT,
        [reg("dest", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 12)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # The `-ext` row owns only the extended base window.
    (
        "N16bj-low-base-on-gpr16-mov-mem-nodisp-ext-row",
        VERSION,
        DIGEST,
        4,
        LOAD_EXT,
        [reg("dest", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 0)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `r/m = 101` at `mod = 00` is `rip`-relative, so `%rbp` is not a base.
    (
        "N16bk-rbp-on-gpr16-mov-mem-nodisp-row",
        VERSION,
        DIGEST,
        3,
        LOAD_LOW,
        [reg("dest", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 5)],
        [{
            "code": "E-RANGE-004",
            "path": "/instructions/0/operands/1/payload/reg",
            "detail_keys": ["excluded", "target_type", "value"],
        }],
    ),
    # `%r13` is the same `r/m = 101` behind `REX.B`.
    (
        "N16bl-r13-on-gpr16-mov-mem-nodisp-ext-row",
        VERSION,
        DIGEST,
        4,
        LOAD_EXT,
        [reg("dest", "x86.gpr16", "r16", 0), reg("base", "x86.gpr64", "rm64", 13)],
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
