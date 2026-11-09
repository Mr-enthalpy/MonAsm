#!/usr/bin/env python3
"""Build the S3 negative plans and their registered diagnostics.

Three cases (`ADR-0115`):

- `N01ez`: `movabs` has no row at all;
- `N01fa`: a new `0.77.0` row against the previous `0.76.0` table;
- `N03zy`: `imm32 = 2147483648` does not sign-extend into the 64-bit
  destination.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0114/make_negatives.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/x86_64/negative"

DIGEST_0760 = "sha256:7535ae0641806b1785096bd286ac62f90f7f02023fd5d47a92b4d4df6371e39a"
DIGEST_0770 = "sha256:093d8f3c0abefc04b9c9b4ed421412a1f9a1fe54bf430951653fac0955d4c68b"

FORM_KEYS = ["form_id", "namespace", "version"]
RANGE_KEYS = ["min", "max", "value", "target_type"]


def operand(role: str, kind: str, target_type: str, payload: dict) -> dict:
    return {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "payload": payload,
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
        "N01ez-absent-movabs-row",
        plan("0.77.0", DIGEST_0770, 10, "x86:mov/r64-imm64/legacy", [
            operand("dest", "x86.gpr64", "r64", {"reg": 0}),
            operand("imm", "x86.imm", "imm64", {"value": 300}),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01fa-mov-imm-row-on-0.76.0",
        plan("0.76.0", DIGEST_0760, 7, "x86:mov/rm64-imm32/legacy", [
            operand("dest", "x86.gpr64", "rm64", {"reg": 0}),
            operand("imm", "x86.imm", "imm32", {"value": 1}),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N03zy-mov-imm32-past-signed-32",
        plan("0.77.0", DIGEST_0770, 7, "x86:mov/rm64-imm32/legacy", [
            operand("dest", "x86.gpr64", "rm64", {"reg": 0}),
            operand("imm", "x86.imm", "imm32", {"value": 2147483648}),
        ]),
        [{"code": "E-RANGE-001", "path": "/instructions/0/operands/1/payload/value",
          "detail_keys": RANGE_KEYS}],
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
