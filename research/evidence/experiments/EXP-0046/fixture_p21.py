#!/usr/bin/env python3
"""Emit `fixtures/x86_64/positive/X86-P21-mov-mem-8-16.fmp.json`.

The plan is a line-for-line transcription of `P21.asm`, so the oracle's bytes
(llvm-mc on that source) and this plan describe the same instructions. Offsets
and `declared_size` are computed from `expected_size`, so the fixture cannot
drift from its own lengths.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0046/fixture_p21.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/positive/X86-P21-mov-mem-8-16.fmp.json"

VERSION = "0.17.0"
DIGEST = "sha256:eb8370255811a2364550bf98ae106f8f972c9a3e54e94d1aeb98ddde921fbcd0"

# `(role, kind, target_type, value)`: a register number, a base number or the
# displacement content, exactly as the definition rows declare them.
INSTRUCTIONS = [
    # --- word, `66` prefix ------------------------------------------------
    ("x86:mov/base-disp8-r16/legacy",
     [("src", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/r16-base-disp8/legacy",
     [("dest", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/base-disp32-r16/legacy",
     [("src", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", 128)], 7),
    ("x86:mov/r16-base-disp32/legacy",
     [("dest", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", 128)], 7),
    ("x86:mov/base-disp8-r16/legacy",
     [("src", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 127)], 4),
    ("x86:mov/base-disp8-r16/legacy",
     [("src", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", -128)], 4),
    ("x86:mov/base-disp32-r16/legacy",
     [("src", "x86.gpr16", "r16", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", -129)], 7),
    # --- low byte, numbers 0-3, no prefix ---------------------------------
    ("x86:mov/base-disp8-r8/legacy",
     [("src", "x86.gpr8", "r8", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 3),
    ("x86:mov/r8-base-disp8/legacy",
     [("dest", "x86.gpr8", "r8", 0), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 3),
    ("x86:mov/base-disp8-r8/legacy",
     [("src", "x86.gpr8", "r8", 1), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 3),
    ("x86:mov/base-disp32-r8/legacy",
     [("src", "x86.gpr8", "r8", 1), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", 128)], 6),
    ("x86:mov/r8-base-disp32/legacy",
     [("dest", "x86.gpr8", "r8", 1), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", -129)], 6),
    # --- high byte, numbers 4-7, no prefix --------------------------------
    ("x86:mov/base-disp8-r8h/legacy",
     [("src", "x86.gpr8h", "r8h", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 3),
    ("x86:mov/base-disp8-r8h/legacy",
     [("src", "x86.gpr8h", "r8h", 5), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 3),
    ("x86:mov/r8h-base-disp8/legacy",
     [("dest", "x86.gpr8h", "r8h", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 3),
    ("x86:mov/base-disp8-r8h/legacy",
     [("src", "x86.gpr8h", "r8h", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 127)], 3),
    ("x86:mov/base-disp8-r8h/legacy",
     [("src", "x86.gpr8h", "r8h", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", -128)], 3),
    ("x86:mov/base-disp32-r8h/legacy",
     [("src", "x86.gpr8h", "r8h", 5), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", 128)], 6),
    ("x86:mov/r8h-base-disp32/legacy",
     [("dest", "x86.gpr8h", "r8h", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", -129)], 6),
    # --- low byte behind a REX byte, numbers 4-7 are `spl`-`dil` ----------
    ("x86:mov/base-disp8-r8-rex/legacy",
     [("src", "x86.gpr8", "r8", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/base-disp8-r8-rex/legacy",
     [("src", "x86.gpr8", "r8", 5), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/r8-base-disp8-rex/legacy",
     [("dest", "x86.gpr8", "r8", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/r8-base-disp8-rex/legacy",
     [("dest", "x86.gpr8", "r8", 7), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp8", 8)], 4),
    ("x86:mov/base-disp32-r8-rex/legacy",
     [("src", "x86.gpr8", "r8", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", 128)], 7),
    ("x86:mov/base-disp32-r8-rex/legacy",
     [("src", "x86.gpr8", "r8", 4), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", -129)], 7),
    ("x86:mov/r8-base-disp32-rex/legacy",
     [("dest", "x86.gpr8", "r8", 5), ("base", "x86.gpr64", "rm64", 0),
      ("disp", "x86.imm", "disp32", 128)], 7),
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
