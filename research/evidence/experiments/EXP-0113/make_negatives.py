#!/usr/bin/env python3
"""Build the S2 negative plans and their registered diagnostics.

Four cases (`ADR-0114`):

- `N01ex`: `test` has no row at all;
- `N01ey`: a new `0.76.0` row against the previous `0.75.0` table;
- `N03zw`: `imm8 = 128` is past the signed-8 end;
- `N03zx`: `imm16 = 32768` is past the signed-16 end.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0113/make_negatives.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/x86_64/negative"

DIGEST_0750 = "sha256:5b13b6b96a4061f354e7d0a371175936cb66c71dbfa80a7eabbf74bfe7eef40d"
DIGEST_0760 = "sha256:7535ae0641806b1785096bd286ac62f90f7f02023fd5d47a92b4d4df6371e39a"

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
        "N01ex-absent-test-imm-row",
        plan("0.76.0", DIGEST_0760, 7, "x86:test/rm64-imm32/legacy", [
            operand("dest", "x86.gpr64", "rm64", {"reg": 0}),
            operand("imm", "x86.imm", "imm32", {"value": 1}),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01ey-alu-imm-row-on-0.75.0",
        plan("0.75.0", DIGEST_0750, 7, "x86:and/rm64-imm32/legacy", [
            operand("dest", "x86.gpr64", "rm64", {"reg": 0}),
            operand("imm", "x86.imm", "imm32", {"value": 1}),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N03zw-alu-imm8-past-signed-8",
        plan("0.76.0", DIGEST_0760, 4, "x86:add/rm64-imm8/legacy", [
            operand("dest", "x86.gpr64", "rm64", {"reg": 0}),
            operand("imm", "x86.imm", "imm8", {"value": 128}),
        ]),
        [{"code": "E-RANGE-001", "path": "/instructions/0/operands/1/payload/value",
          "detail_keys": RANGE_KEYS}],
    ),
    (
        "N03zx-alu-imm16-past-signed-16",
        plan("0.76.0", DIGEST_0760, 5, "x86:and/rm16-imm16/legacy", [
            operand("dest", "x86.gpr16", "rm16", {"reg": 0}),
            operand("imm", "x86.imm", "imm16", {"value": 32768}),
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
