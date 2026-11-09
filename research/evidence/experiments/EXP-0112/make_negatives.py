#!/usr/bin/env python3
"""Build the S1 negative plans and their registered diagnostics.

Five cases (`ADR-0113`):

- `N01eu`: `adc` has no row at all;
- `N01ev`: the `opcode+1` direction (`add/r64-rm64`) is deliberately absent;
- `N01ew`: the new `add/rm64-r64` row against the previous `0.74.0` table;
- `N02dd`: a `cmp` row with only the destination operand;
- `N14ch`: register 8 on the three-bit destination field.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0112/make_negatives.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/x86_64/negative"

DIGEST_0740 = "sha256:27f337115cffe89c8d7028863e7748783247344ba4d8e622fa9c4345efdead58"
DIGEST_0750 = "sha256:5b13b6b96a4061f354e7d0a371175936cb66c71dbfa80a7eabbf74bfe7eef40d"

FORM_KEYS = ["form_id", "namespace", "version"]


def operand(role: str, kind: str, target_type: str, reg: int) -> dict:
    return {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "payload": {"reg": reg},
        "modifiers": [],
    }


def plan(version: str, digest: str, size: int, form_id: str,
         operands: list) -> dict:
    return {
        "format_version": "fmp/0.1",
        "target_identity": {
            "isa_family": "x86",
            "isa_variant": "x86-64",
            "execution_mode": "64",
            "enabled_extensions": [],
            "feature_constraints": [],
            "byte_order": "little",
            "address_width": 64,
        },
        "definition_identity": {
            "namespace": "monasm.isa.x86",
            "version": version,
            "digest": digest,
        },
        "output_contract": {
            "artifact": "bytes",
            "section_order": [".text"],
            "fixup_record_order": "section_id,offset,fixup_id",
            "include_symbol_table": False,
            "emit_fixups": True,
        },
        "sections": [
            {
                "section_id": ".text",
                "section_kind": "code",
                "image_backed": True,
                "declared_size": size,
                "fragments": [
                    {"offset": 0, "size": size, "kind": "instruction",
                     "instruction_id": "I0001"}
                ],
            }
        ],
        "symbols": [],
        "instructions": [
            {
                "instruction_id": "I0001",
                "section_id": ".text",
                "offset": 0,
                "form_id": form_id,
                "operands": operands,
                "expected_size": size,
            }
        ],
        "fixups": [],
    }


CASES = [
    (
        "N01eu-absent-adc-rr-row",
        plan("0.75.0", DIGEST_0750, 3, "x86:adc/rm64-r64/legacy", [
            operand("dest", "x86.gpr64", "rm64", 0),
            operand("src", "x86.gpr64", "r64", 1),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01ev-absent-opcode-plus-one-direction",
        plan("0.75.0", DIGEST_0750, 3, "x86:add/r64-rm64/legacy", [
            operand("dest", "x86.gpr64", "r64", 0),
            operand("src", "x86.gpr64", "rm64", 1),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01ew-alu-rr-row-on-0.74.0",
        plan("0.74.0", DIGEST_0740, 3, "x86:add/rm64-r64/legacy", [
            operand("dest", "x86.gpr64", "rm64", 0),
            operand("src", "x86.gpr64", "r64", 1),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N02dd-missing-source-on-alu-rr-row",
        plan("0.75.0", DIGEST_0750, 3, "x86:cmp/rm64-r64/legacy", [
            operand("dest", "x86.gpr64", "rm64", 0),
        ]),
        [{"code": "E-OPERAND-002", "path": "/instructions/0/operands",
          "detail_keys": ["expected", "found"]}],
    ),
    (
        "N14ch-register8-on-alu-rr-row",
        plan("0.75.0", DIGEST_0750, 2, "x86:and/rm32-r32/legacy", [
            operand("dest", "x86.gpr32", "rm32", 8),
            operand("src", "x86.gpr32", "r32", 1),
        ]),
        [{"code": "E-OPERAND-004", "path": "/instructions/0/operands/0/payload/reg",
          "detail_keys": ["target_type", "value", "field_bits"]}],
    ),
]


def write(path: Path, document: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2) + "\n")


def main() -> int:
    for stem, document, errors in CASES:
        write(NEGATIVE / (stem + ".fmp.json"), document)
        write(NEGATIVE / (stem + ".expected-error.json"), {"errors": errors})
        print(stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
