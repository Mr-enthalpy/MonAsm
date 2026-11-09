#!/usr/bin/env python3
"""Emit the two `fmp-def/0.2` target-gate negative fixtures.

Both pin `definitions/x86_64/0.68.0.json`:

- `N06b` declares `enabled_extensions: []` and names a VEX row. The empty set is
  a legal subset of the table's set, so step 2 passes; step 6 finds the row's
  `["avx"]` unmet and reports `E-TARGET-003` on `extension = avx`.
- `N06c` declares `["sse4.2"]`, which the table does not carry. Step 2 rejects
  the set with `E-TARGET-001` and `found = sse4.2`; the legacy row it names has
  an empty requirement, so no second diagnostic follows.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0104/fixture_negatives_n06.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/negative"

VERSION = "0.68.0"
DIGEST = "sha256:4c9ff304b305ceb831fd99e22bf0a7c422cce4104d08de604a6509f58e1501d2"

HEADER = """{
  "format_version": "fmp/0.1",
  "target_identity": {
    "isa_family": "x86",
    "isa_variant": "x86-64",
    "execution_mode": "64",
    "enabled_extensions": %s,
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


def extension_error() -> list:
    return [{
        "code": "E-TARGET-003",
        "path": "/instructions/0/form_id",
        "detail_keys": ["extension", "form_id"],
    }]


def target_error() -> list:
    return [{
        "code": "E-TARGET-001",
        "path": "/target_identity/enabled_extensions",
        "detail_keys": ["found"],
    }]


VEX = "x86:vmovaps/ymm-base/vex"
LEGACY = "x86:movaps/xmm-xmm/legacy"

CASES = [
    (
        "N06b-per-form-extension-not-enabled",
        "[]",
        VEX,
        4,
        [
            operand("dest", "x86.ymm", "ymm", {"reg": 0}),
            operand("base", "x86.gpr64", "rm64", {"reg": 0}),
        ],
        extension_error(),
    ),
    (
        "N06c-extension-not-declared-by-definition",
        '["sse4.2"]',
        LEGACY,
        3,
        [
            operand("dest", "x86.xmm", "xmm", {"reg": 0}),
            operand("src", "x86.xmm", "xmm", {"reg": 1}),
        ],
        target_error(),
    ),
]


def main() -> int:
    for name, extensions, form_id, size, operands, errors in CASES:
        plan = HEADER % (extensions, VERSION, DIGEST, size, size, form_id,
                         ",\n".join(operands), size)
        plan_path = TARGET / (name + ".fmp.json")
        with plan_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(plan)
        error_path = TARGET / (name + ".expected-error.json")
        with error_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"errors": errors}, indent=2) + "\n")
        print("%s (%s)" % (name, form_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
