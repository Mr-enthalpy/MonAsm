#!/usr/bin/env python3
"""Emit `fixtures/x86_64/positive/X86-P20-vex-ymm-memory.fmp.json`.

The plan is a line-for-line transcription of `P20.asm`, so the oracle's bytes
(llvm-mc on that source) and this plan describe the same twenty-four
instructions. Offsets and `declared_size` are computed from `expected_size`, so
the fixture cannot drift from its own lengths.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0045/fixture_p20.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "fixtures/x86_64/positive/X86-P20-vex-ymm-memory.fmp.json"

VERSION = "0.16.0"
DIGEST = "sha256:64ea1acf467afb2f858a5cb2967839445a5ffecac164a5f1b61931cb8fb3b99e"

# `payload` is the field content for a `disp8` slot and the byte offset for
# `disp32`, exactly as the definition rows declare them.
INSTRUCTIONS = [
    # --- two-byte C5 FC, low base -----------------------------------------
    ("x86:vmovaps/ymm-base/vex", [("dest", "ymm", 0), ("base", 0)], 4),
    ("x86:vmovaps/base-ymm/vex", [("src", "ymm", 0), ("base", 0)], 4),
    ("x86:vmovaps/ymm-base-disp8/vex",
     [("dest", "ymm", 0), ("base", 0), ("disp8", 32)], 5),
    ("x86:vmovaps/base-disp8-ymm/vex",
     [("src", "ymm", 0), ("base", 0), ("disp8", -32)], 5),
    ("x86:vmovaps/ymm-base-disp8/vex",
     [("dest", "ymm", 0), ("base", 0), ("disp8", 127)], 5),
    ("x86:vmovaps/ymm-base-disp8/vex",
     [("dest", "ymm", 0), ("base", 0), ("disp8", -128)], 5),
    ("x86:vmovaps/ymm-base-disp32/vex",
     [("dest", "ymm", 0), ("base", 0), ("disp32", 128)], 8),
    ("x86:vmovaps/base-disp32-ymm/vex",
     [("src", "ymm", 0), ("base", 0), ("disp32", -129)], 8),
    # The fourth destination bit is `R̄`, so a low base still reaches ymm8.
    ("x86:vmovaps/ymm-base/vex", [("dest", "ymm", 8), ("base", 0)], 4),
    ("x86:vmovaps/base-ymm/vex", [("src", "ymm", 8), ("base", 0)], 4),
    # --- three-byte C4 C1 7C, extended base -------------------------------
    ("x86:vmovaps/ymm-base-ext/vex", [("dest", "ymm", 0), ("base", 8)], 5),
    ("x86:vmovaps/base-ext-ymm/vex", [("src", "ymm", 0), ("base", 8)], 5),
    ("x86:vmovaps/ymm-base-ext-disp8/vex",
     [("dest", "ymm", 0), ("base", 8), ("disp8", 32)], 6),
    ("x86:vmovaps/base-ext-disp8-ymm/vex",
     [("src", "ymm", 0), ("base", 8), ("disp8", -32)], 6),
    ("x86:vmovaps/ymm-base-ext-disp8/vex",
     [("dest", "ymm", 0), ("base", 8), ("disp8", 127)], 6),
    ("x86:vmovaps/ymm-base-ext-disp8/vex",
     [("dest", "ymm", 0), ("base", 8), ("disp8", -128)], 6),
    ("x86:vmovaps/ymm-base-ext-disp32/vex",
     [("dest", "ymm", 0), ("base", 8), ("disp32", 128)], 9),
    ("x86:vmovaps/base-ext-disp32-ymm/vex",
     [("src", "ymm", 0), ("base", 8), ("disp32", -129)], 9),
    # High base and high vector register in one instruction: B̄ and R̄ both carry.
    ("x86:vmovaps/ymm-base-ext/vex", [("dest", "ymm", 8), ("base", 8)], 5),
    ("x86:vmovaps/base-ext-ymm/vex", [("src", "ymm", 8), ("base", 8)], 5),
    ("x86:vmovaps/ymm-base-ext-disp8/vex",
     [("dest", "ymm", 8), ("base", 8), ("disp8", 32)], 6),
    ("x86:vmovaps/base-ext-disp8-ymm/vex",
     [("src", "ymm", 8), ("base", 8), ("disp8", -32)], 6),
    ("x86:vmovaps/base-ext-disp32-ymm/vex",
     [("src", "ymm", 8), ("base", 8), ("disp32", 128)], 9),
    ("x86:vmovaps/ymm-base-ext-disp32/vex",
     [("dest", "ymm", 8), ("base", 8), ("disp32", 128)], 9),
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


def operand(item) -> str:
    """One operand: `(role, target_type, value)`, `(base, value)` or
    `(disp8|disp32, value)`."""
    if len(item) == 3:
        role, target_type, value = item
        kind = "x86.%s" % target_type
        payload = '{ "reg": %d }' % value
    elif item[0] == "base":
        role, value = item
        target_type = "rm64"
        kind = "x86.gpr64"
        payload = '{ "reg": %d }' % value
    else:
        target_type, value = item
        role = "disp"
        kind = "x86.imm"
        payload = '{ "value": %d }' % value
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }' % (role, kind, target_type, payload))


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
        body = ",\n".join(operand(item) for item in operands)
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
