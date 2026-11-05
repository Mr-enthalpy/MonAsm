#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.17.0.json` from `0.16.0.json`.

The only differences are the `version` string and the sixteen 8/16-bit `mov`
memory rows appended at the end of `forms` (ADR-0044). Four rows are word
(`66` prefix, `89`/`8b`, `x86.gpr16`), twelve are byte: the REX-less low set
(`0`-`3`), the high-byte set (`4`-`7`), and the `spl`-`dil` set (`4`-`7` behind
a template `40` byte). Every base is the three-bit window `0`-`7` minus
`%rsp`; the displacement carriers are the 0.3.0 ones.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0046/generate_0170.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.16.0.json"
TARGET = ROOT / "definitions/x86_64/0.17.0.json"

# `mod = 01`/`10` with `r/m = 100` spends the byte on a SIB, so `%rsp` stays
# out; the window is three bits wide, so `%r12` is outside it anyway.
BASE_EXCLUDED = [4]


def placement(bit_offset: int, width: int) -> dict:
    return {"bit_offset": bit_offset, "width": width}


def reg_slot(role: str, kind: str, target_type: str, bit_offset: int,
             excluded: list[int] | None = None) -> dict:
    entry = {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
    }
    if excluded is not None:
        entry["excluded"] = excluded
    entry["modifiers"] = []
    entry["placements"] = [placement(bit_offset, 3)]
    return entry


def base_slot(bit_offset: int) -> dict:
    return reg_slot("base", "x86.gpr64", "rm64", bit_offset,
                    excluded=BASE_EXCLUDED)


def disp_slot(bits: int, offset: int) -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp%d" % bits,
        "from": "operand_value",
        "range": {"signed": True, "bits": bits, "align_bits": 0},
        "modifiers": [],
        "placements": [placement(offset, bits)],
    }


def form(form_id: str, template: str, slots: list[dict]) -> dict:
    return {"form_id": form_id, "template": template, "slots": slots}


# The three byte register sets keep the register-direct exclusions: numbers 4-7
# without REX are `ah`-`bh`, 4-7 with REX are `spl`-`dil`, and 0-3 are the
# REX-less low set that a redundant REX would rename (EC-28).
LOW_BYTE_EXCLUDED = [4, 5, 6, 7]
HIGH_BYTE_EXCLUDED = [0, 1, 2, 3]
REX_BYTE_EXCLUDED = [0, 1, 2, 3]

NEW_FORMS = [
    # `66` at byte 0, opcode at 1, ModRM at 2, displacement at 3.
    form("x86:mov/r16-base-disp8/legacy", "668b4000",
         [reg_slot("dest", "x86.gpr16", "r16", 19), base_slot(16),
          disp_slot(8, 24)]),
    form("x86:mov/r16-base-disp32/legacy", "668b8000000000",
         [reg_slot("dest", "x86.gpr16", "r16", 19), base_slot(16),
          disp_slot(32, 24)]),
    form("x86:mov/base-disp8-r16/legacy", "66894000",
         [reg_slot("src", "x86.gpr16", "r16", 19), base_slot(16),
          disp_slot(8, 24)]),
    form("x86:mov/base-disp32-r16/legacy", "66898000000000",
         [reg_slot("src", "x86.gpr16", "r16", 19), base_slot(16),
          disp_slot(32, 24)]),
    # No prefix: opcode at 0, ModRM at 1, displacement at 2.
    form("x86:mov/r8-base-disp8/legacy", "8a4000",
         [reg_slot("dest", "x86.gpr8", "r8", 11,
                   excluded=LOW_BYTE_EXCLUDED), base_slot(8),
          disp_slot(8, 16)]),
    form("x86:mov/r8-base-disp32/legacy", "8a8000000000",
         [reg_slot("dest", "x86.gpr8", "r8", 11,
                   excluded=LOW_BYTE_EXCLUDED), base_slot(8),
          disp_slot(32, 16)]),
    form("x86:mov/base-disp8-r8/legacy", "884000",
         [reg_slot("src", "x86.gpr8", "r8", 11,
                   excluded=LOW_BYTE_EXCLUDED), base_slot(8),
          disp_slot(8, 16)]),
    form("x86:mov/base-disp32-r8/legacy", "888000000000",
         [reg_slot("src", "x86.gpr8", "r8", 11,
                   excluded=LOW_BYTE_EXCLUDED), base_slot(8),
          disp_slot(32, 16)]),
    form("x86:mov/r8h-base-disp8/legacy", "8a6000",
         [reg_slot("dest", "x86.gpr8h", "r8h", 11,
                   excluded=HIGH_BYTE_EXCLUDED), base_slot(8),
          disp_slot(8, 16)]),
    form("x86:mov/r8h-base-disp32/legacy", "8aa000000000",
         [reg_slot("dest", "x86.gpr8h", "r8h", 11,
                   excluded=HIGH_BYTE_EXCLUDED), base_slot(8),
          disp_slot(32, 16)]),
    form("x86:mov/base-disp8-r8h/legacy", "886000",
         [reg_slot("src", "x86.gpr8h", "r8h", 11,
                   excluded=HIGH_BYTE_EXCLUDED), base_slot(8),
          disp_slot(8, 16)]),
    form("x86:mov/base-disp32-r8h/legacy", "88a000000000",
         [reg_slot("src", "x86.gpr8h", "r8h", 11,
                   excluded=HIGH_BYTE_EXCLUDED), base_slot(8),
          disp_slot(32, 16)]),
    # Template `40`: the prefix is required by the register set, so the base
    # stays three bits and no placement writes REX.B.
    form("x86:mov/r8-base-disp8-rex/legacy", "408a6000",
         [reg_slot("dest", "x86.gpr8", "r8", 19,
                   excluded=REX_BYTE_EXCLUDED), base_slot(16),
          disp_slot(8, 24)]),
    form("x86:mov/r8-base-disp32-rex/legacy", "408aa000000000",
         [reg_slot("dest", "x86.gpr8", "r8", 19,
                   excluded=REX_BYTE_EXCLUDED), base_slot(16),
          disp_slot(32, 24)]),
    form("x86:mov/base-disp8-r8-rex/legacy", "40886000",
         [reg_slot("src", "x86.gpr8", "r8", 19,
                   excluded=REX_BYTE_EXCLUDED), base_slot(16),
          disp_slot(8, 24)]),
    form("x86:mov/base-disp32-r8-rex/legacy", "4088a000000000",
         [reg_slot("src", "x86.gpr8", "r8", 19,
                   excluded=REX_BYTE_EXCLUDED), base_slot(16),
          disp_slot(32, 24)]),
]


def render_placements(placements: list[dict]) -> str:
    pieces = []
    for item in placements:
        text = '{ "bit_offset": %d, "width": %d' % (
            item["bit_offset"], item["width"])
        if item.get("invert"):
            text += ', "invert": true'
        pieces.append(text + " }")
    return "[" + ", ".join(pieces) + "]"


def render_slot(entry: dict) -> list[str]:
    lines = [
        "      {",
        '        "role": "%s",' % entry["role"],
        '        "kind": "%s",' % entry["kind"],
        '        "target_type": "%s",' % entry["target_type"],
        '        "from": "%s",' % entry["from"],
    ]
    if "range" in entry:
        span = entry["range"]
        lines.append(
            '        "range": { "signed": %s, "bits": %d, "align_bits": %d },'
            % ("true" if span["signed"] else "false", span["bits"],
               span["align_bits"])
        )
    if "excluded" in entry:
        lines.append('        "excluded": [%s],'
                     % ", ".join(str(value) for value in entry["excluded"]))
    lines.append('        "modifiers": [],')
    lines.append('        "placements": %s' % render_placements(entry["placements"]))
    lines.append("      }")
    return lines


def render_form(entry: dict) -> str:
    lines = [
        "  {",
        '    "form_id": "%s",' % entry["form_id"],
        '    "template": "%s",' % entry["template"],
        '    "slots": [',
    ]
    for index, item in enumerate(entry["slots"]):
        rendered = render_slot(item)
        if index + 1 < len(entry["slots"]):
            rendered[-1] += ","
        lines.extend(rendered)
    lines.append("    ]")
    lines.append("  }")
    return "\n".join(lines)


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    document = json.loads(text)
    if document["version"] != "0.16.0":
        raise SystemExit("source is not 0.16.0")

    marker = "\n  ]\n}\n"
    if not text.endswith(marker):
        raise SystemExit("unexpected file tail")
    body = text[: -len(marker)]
    block = ",\n".join(render_form(entry) for entry in NEW_FORMS)
    updated = body + ",\n" + block + marker
    updated = updated.replace('"version": "0.16.0"', '"version": "0.17.0"', 1)
    with TARGET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(TARGET.read_text(encoding="utf-8"))
    print("%s: %d forms" % (TARGET.relative_to(ROOT).as_posix(),
                            len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
