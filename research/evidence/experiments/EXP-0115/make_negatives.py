#!/usr/bin/env python3
"""Build the S4 negative plans and their registered diagnostics.

Three cases (`ADR-0116`):

- `N01fb`: the indexed sibling (`base + index * scale + disp`) has no row;
- `N01fc`: a new `0.78.0` row against the previous `0.77.0` table;
- `N03zz`: `disp8 = 128` is outside the signed-8 displacement.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0115/make_negatives.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/x86_64/negative"

DIGEST_0770 = "sha256:093d8f3c0abefc04b9c9b4ed421412a1f9a1fe54bf430951653fac0955d4c68b"
DIGEST_0780 = "sha256:30cb9f13047ff742d8f53a20f93218a601302bd52814ad26364347cb85576a21"

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
        "N01fb-absent-sub-index-form",
        plan("0.78.0", DIGEST_0780, 5, "x86:sub/base-index-disp8-r64/legacy", [
            operand("src", "x86.gpr64", "r64", {"reg": 1}),
            operand("base", "x86.gpr64", "rm64", {"reg": 0}),
            operand("index", "x86.gpr64", "sib_index", {"reg": 1}),
            operand("disp", "x86.imm", "disp8", {"value": 8}),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N01fc-sub-memory-row-on-0.77.0",
        plan("0.77.0", DIGEST_0770, 4, "x86:sub/base-disp8-r64/legacy", [
            operand("src", "x86.gpr64", "r64", {"reg": 1}),
            operand("base", "x86.gpr64", "rm64", {"reg": 0}),
            operand("disp", "x86.imm", "disp8", {"value": 8}),
        ]),
        [{"code": "E-FORM-001", "path": "/instructions/0/form_id",
          "detail_keys": FORM_KEYS}],
    ),
    (
        "N03zz-sub-disp8-past-signed-8",
        plan("0.78.0", DIGEST_0780, 4, "x86:sub/base-disp8-r64/legacy", [
            operand("src", "x86.gpr64", "r64", {"reg": 1}),
            operand("base", "x86.gpr64", "rm64", {"reg": 0}),
            operand("disp", "x86.imm", "disp8", {"value": 128}),
        ]),
        [{"code": "E-RANGE-001",
          "path": "/instructions/0/operands/2/payload/value",
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
