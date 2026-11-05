#!/usr/bin/env python3
"""Emit `fixtures/x86_64/positive/X86-P22-mov-mem-base-ext.fmp.json`.

The plan is a line-for-line transcription of `fixture.asm`, so the oracle's
bytes (llvm-mc on that source) and this plan describe the same instructions.
Offsets and `declared_size` are computed from `expected_size`, so the fixture
cannot drift from its own lengths.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0047/fixture_p22.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = (
    ROOT / "fixtures/x86_64/positive/X86-P22-mov-mem-base-ext.fmp.json"
)

VERSION = "0.18.0"
DIGEST = "sha256:e1281b0c11d7e2bed9bd1ec7fa5404dadca2c82959376cbe3edfd9ff56b9e33d"

# `(role, kind, target_type, value)`: a register number, a base number or the
# displacement content, exactly as the definition rows declare them.
INSTRUCTIONS = [
    # --- word `-base-ext`, `66 41` ---------------------------------------
    ("x86:mov/r16-base-ext-disp8/legacy",
     [("dest", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 8),
      ("disp", "x86.imm", "disp8", 8)], 5),
    ("x86:mov/r16-base-ext-disp8/legacy",
     [("dest", "x86.gpr16", "r16", 3), ("base", "x86.gpr64", "rm64", 15),
      ("disp", "x86.imm", "disp8", 127)], 5),
    ("x86:mov/r16-base-ext-disp8/legacy",
     [("dest", "x86.gpr16", "r16", 1), ("base", "x86.gpr64", "rm64", 9),
      ("disp", "x86.imm", "disp8", -128)], 5),
    ("x86:mov/r16-base-ext-disp32/legacy",
     [("dest", "x86.gpr16", "r16", 2), ("base", "x86.gpr64", "rm64", 10),
      ("disp", "x86.imm", "disp32", 128)], 8),
    ("x86:mov/base-ext-disp8-r16/legacy",
     [("src", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 11),
      ("disp", "x86.imm", "disp8", 8)], 5),
    ("x86:mov/base-ext-disp32-r16/legacy",
     [("src", "x86.gpr16", "r16", 6), ("base", "x86.gpr64", "rm64", 13),
      ("disp", "x86.imm", "disp32", -129)], 8),
    ("x86:mov/base-ext-disp32-r16/legacy",
     [("src", "x86.gpr16", "r16", 7), ("base", "x86.gpr64", "rm64", 14),
      ("disp", "x86.imm", "disp32", 128)], 8),
    # --- REX-less low byte, `41` ------------------------------------------
    ("x86:mov/r8-base-ext-disp8/legacy",
     [("dest", "x86.gpr8", "r8", 0), ("base", "x86.gpr64", "rm64", 8),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/r8-base-ext-disp8/legacy",
     [("dest", "x86.gpr8", "r8", 1), ("base", "x86.gpr64", "rm64", 9),
      ("disp", "x86.imm", "disp8", 127)], 4),
    ("x86:mov/r8-base-ext-disp32/legacy",
     [("dest", "x86.gpr8", "r8", 2), ("base", "x86.gpr64", "rm64", 10),
      ("disp", "x86.imm", "disp32", 128)], 7),
    ("x86:mov/base-ext-disp8-r8/legacy",
     [("src", "x86.gpr8", "r8", 0), ("base", "x86.gpr64", "rm64", 11),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/base-ext-disp8-r8/legacy",
     [("src", "x86.gpr8", "r8", 1), ("base", "x86.gpr64", "rm64", 13),
      ("disp", "x86.imm", "disp8", -128)], 4),
    ("x86:mov/base-ext-disp32-r8/legacy",
     [("src", "x86.gpr8", "r8", 2), ("base", "x86.gpr64", "rm64", 14),
      ("disp", "x86.imm", "disp32", -129)], 7),
    # --- widened `40` rows: low base, high base, both `disp` widths -------
    ("x86:mov/base-disp8-r8-rex/legacy",
     [("src", "x86.gpr8", "r8", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/r8-base-disp8-rex/legacy",
     [("dest", "x86.gpr8", "r8", 4), ("base", "x86.gpr64", "rm64", 8),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/base-disp32-r8-rex/legacy",
     [("src", "x86.gpr8", "r8", 5), ("base", "x86.gpr64", "rm64", 15),
      ("disp", "x86.imm", "disp32", 128)], 7),
    ("x86:mov/r8-base-disp8-rex/legacy",
     [("dest", "x86.gpr8", "r8", 7), ("base", "x86.gpr64", "rm64", 15),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/base-disp32-r8-rex/legacy",
     [("src", "x86.gpr8", "r8", 4), ("base", "x86.gpr64", "rm64", 9),
      ("disp", "x86.imm", "disp32", -129)], 7),
]

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
"""


def operand(role: str, kind: str, target_type: str, value: int) -> str:
    if kind == "x86.imm":
        payload = '{ "value": %d }' % value
    else:
        payload = '{ "reg": %d }' % value
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }'
            % (role, kind, target_type, payload))


def main() -> int:
    offsets = []
    cursor = 0
    for _, _, size in INSTRUCTIONS:
        offsets.append(cursor)
        cursor += size
    total = cursor

    fragments = ",\n".join(
        '        { "offset": %d, "size": %d, "kind": "instruction", '
        '"instruction_id": "I%04d" }' % (offset, size, index + 1)
        for index, ((_, _, size), offset) in enumerate(zip(INSTRUCTIONS, offsets))
    )

    instructions = []
    for index, ((form_id, operands, size), offset) in enumerate(
            zip(INSTRUCTIONS, offsets)):
        body = ",\n".join(operand(*item) for item in operands)
        instructions.append(
            '    {\n'
            '      "instruction_id": "I%04d",\n'
            '      "section_id": ".text",\n'
            '      "offset": %d,\n'
            '      "form_id": "%s",\n'
            '      "operands": [\n%s\n      ],\n'
            '      "expected_size": %d\n'
            '    }' % (index + 1, offset, form_id, body, size)
        )
    instruction_block = ",\n".join(instructions)

    text = HEADER % (VERSION, DIGEST)
    text += """  "sections": [
    {
      "section_id": ".text",
      "section_kind": "code",
      "image_backed": true,
      "declared_size": %d,
      "fragments": [
%s
      ]
    }
  ],
  "symbols": [],
  "instructions": [
%s
  ],
  "fixups": []
}
""" % (total, fragments, instruction_block)

    with TARGET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("%s: %d instructions, %d bytes"
          % (TARGET.relative_to(ROOT).as_posix(), len(INSTRUCTIONS), total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
