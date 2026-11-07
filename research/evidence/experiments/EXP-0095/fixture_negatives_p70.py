#!/usr/bin/env python3
"""Write the seven `X86-P70` negative fixtures and their `expected-error.json`.

Each plan is one instruction of `0.65.0` and states a different way an
absolute 32-bit field may not carry a symbol:

- `N15b`: the symbol as an operand payload on the `disp` role.
- `N15c`: the field left empty with no fixup covering it.
- `N07c`: a literal `{value}` and a fixup over the same bits.
- `N07d`: a descriptor that covers part of the field.
- `N07e`: the 64-bit row's `[32,32]` descriptor on a 7-byte row.
- `N08d`: `resolve_in_place` for a defined symbol in an unbound `.text`.
- `N04f`: a 32-bit absolute address in the 8-bit `add` immediate field.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0095/fixture_negatives_p70.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEGATIVE = ROOT / "fixtures/x86_64/negative"

VERSION = "0.65.0"
DIGEST = "sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a"

DISP = ("disp", "x86.imm", "disp32")
IMM8 = ("imm", "x86.imm", "imm8")

CASES = [
    {
        "stem": "N15b-symbol-payload-on-disp-role",
        "form": "x86:mov/r32-abs32/legacy",
        "size": 7,
        "operands": [("dest", "x86.gpr32", "r32", {"reg": 0}),
                     ("disp", "x86.imm", "disp32", {"symbol_id": "ext"})],
        "symbols": [{"symbol_id": "ext", "name": "ext", "kind": "external",
                     "binding": "global"}],
        "fixups": [],
        "errors": [{"code": "E-OPERAND-003",
                    "path": "/instructions/0/operands/1/payload",
                    "detail_keys": ["kind", "reason"]}],
    },
    {
        "stem": "N15c-abs32-disp-empty-without-fixup",
        "form": "x86:mov/r32-abs32/legacy",
        "size": 7,
        "operands": [("dest", "x86.gpr32", "r32", {"reg": 0}),
                     ("disp", "x86.imm", "disp32", {})],
        "symbols": [],
        "fixups": [],
        "errors": [{"code": "E-OPERAND-003",
                    "path": "/instructions/0/operands/1/payload",
                    "detail_keys": ["kind", "reason"]}],
    },
    {
        "stem": "N07c-value-and-covering-fixup-on-abs32",
        "form": "x86:mov/r32-abs32/legacy",
        "size": 7,
        "operands": [("dest", "x86.gpr32", "r32", {"reg": 0}),
                     ("disp", "x86.imm", "disp32", {"value": 0})],
        "symbols": [{"symbol_id": "ext", "name": "ext", "kind": "external",
                     "binding": "global"}],
        "fixups": [{"lsb": 24, "width": 32, "bits": 32, "signed": True,
                    "symbol": "ext", "addend": 0, "mode": "emit_relocation"}],
        "errors": [{"code": "E-FIXUP-006",
                    "path": "/instructions/0/operands/1/payload",
                    "detail_keys": ["first", "second"]}],
    },
    {
        "stem": "N07d-partial-disp-descriptor-on-abs32",
        "form": "x86:mov/r32-abs32/legacy",
        "size": 7,
        "operands": [("dest", "x86.gpr32", "r32", {"reg": 0}), DISP + ({},)],
        "symbols": [{"symbol_id": "ext", "name": "ext", "kind": "external",
                     "binding": "global"}],
        "fixups": [{"lsb": 24, "width": 16, "bits": 32, "signed": True,
                    "symbol": "ext", "addend": 0, "mode": "emit_relocation"}],
        "errors": [
            {"code": "E-FIXUP-001", "path": "/fixups/0/range_constraint",
             "detail_keys": ["kind", "form_id", "field"]},
            {"code": "E-FIXUP-001", "path": "/instructions/0/operands/1",
             "detail_keys": ["kind", "form_id", "field"]},
        ],
    },
    {
        "stem": "N07e-gpr64-descriptor-on-gpr32-abs32-row",
        "form": "x86:mov/r32-abs32/legacy",
        "size": 7,
        "operands": [("dest", "x86.gpr32", "r32", {"reg": 0}), DISP + ({},)],
        "symbols": [{"symbol_id": "ext", "name": "ext", "kind": "external",
                     "binding": "global"}],
        "fixups": [{"lsb": 32, "width": 32, "bits": 32, "signed": True,
                    "symbol": "ext", "addend": 0, "mode": "emit_relocation"}],
        "errors": [
            {"code": "E-FIXUP-005", "path": "/fixups/0/field_descriptor",
             "detail_keys": ["fixup_id", "descriptor"]},
            {"code": "E-FIXUP-001", "path": "/instructions/0/operands/1",
             "detail_keys": ["kind", "form_id", "field"]},
        ],
    },
    {
        "stem": "N08d-resolve-abs32-without-section-base",
        "form": "x86:mov/r32-abs32/legacy",
        "size": 7,
        "operands": [("dest", "x86.gpr32", "r32", {"reg": 0}), DISP + ({},)],
        "symbols": [{"symbol_id": "L1", "name": "L1", "kind": "defined",
                     "binding": "local", "section_id": ".text", "offset": 0}],
        "fixups": [{"lsb": 24, "width": 32, "bits": 32, "signed": True,
                    "symbol": "L1", "addend": 0,
                    "mode": "resolve_in_place"}],
        "errors": [{"code": "E-FIXUP-002", "path": "/fixups/0/target",
                    "detail_keys": ["fixup_id", "target"]}],
    },
    {
        "stem": "N04f-absolute-address-in-imm8-field",
        "form": "x86:add/rm64-imm8/legacy",
        "size": 4,
        "operands": [("dest", "x86.gpr64", "rm64", {"reg": 0}),
                     ("imm", "x86.imm", "imm8", {})],
        "symbols": [],
        "fixups": [{"lsb": 24, "width": 8, "bits": 8, "signed": True,
                    "address": 4096, "addend": 0,
                    "mode": "resolve_in_place"}],
        "errors": [{"code": "E-FIXUP-003", "path": "/fixups/0",
                    "detail_keys": ["fixup_id", "min", "max", "value"]}],
    },
]


def payload(entry):
    role, kind, target_type, data = entry
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": data, "modifiers": []}


def fixup(entry, index):
    if "symbol" in entry:
        target = {"kind": "symbol", "symbol_id": entry["symbol"]}
    else:
        target = {"kind": "absolute", "address": entry["address"]}
    return {
        "fixup_id": "F%04d" % index,
        "section_id": ".text",
        "offset": 0,
        "field_descriptor": [{"lsb": entry["lsb"], "width": entry["width"]}],
        "target": target,
        "addend": entry["addend"],
        "pc_reference_rule": "none",
        "value_transform": "identity",
        "range_constraint": {"signed": entry["signed"], "bits": entry["bits"],
                             "align_bits": 0},
        "resolution_mode": entry["mode"],
    }


def main() -> int:
    for case in CASES:
        document = {
            "format_version": "fmp/0.1",
            "target_identity": {
                "isa_family": "x86",
                "isa_variant": "x86-64",
                "execution_mode": "64",
                # The plan's extension set must equal the pinned definition's
                # (`E-TARGET-001` otherwise), so these negatives carry the same
                # list as every other `0.65.0` fixture.
                "enabled_extensions": ["avx", "avx512f", "avx512vl"],
                "feature_constraints": [],
                "byte_order": "little",
                "address_width": 64,
            },
            "definition_identity": {
                "namespace": "monasm.isa.x86",
                "version": VERSION,
                "digest": DIGEST,
            },
            "output_contract": {
                "artifact": "bytes",
                "section_order": [".text"],
                "fixup_record_order": "section_id,offset,fixup_id",
                "include_symbol_table": False,
                "emit_fixups": True,
            },
            "sections": [{
                "section_id": ".text",
                "section_kind": "code",
                "image_backed": True,
                "declared_size": case["size"],
                "fragments": [{
                    "offset": 0,
                    "size": case["size"],
                    "kind": "instruction",
                    "instruction_id": "I0001",
                }],
            }],
            "symbols": case["symbols"],
            "instructions": [{
                "instruction_id": "I0001",
                "section_id": ".text",
                "offset": 0,
                "form_id": case["form"],
                "operands": [payload(item) for item in case["operands"]],
                "expected_size": case["size"],
            }],
            "fixups": [fixup(item, index)
                       for index, item in enumerate(case["fixups"], 1)],
        }
        stem = case["stem"]
        with (NEGATIVE / (stem + ".fmp.json")).open(
                "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, indent=2) + "\n")
        with (NEGATIVE / (stem + ".expected-error.json")).open(
                "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"errors": case["errors"]}, indent=2) + "\n")
        print(stem, len(case["errors"]), "diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
