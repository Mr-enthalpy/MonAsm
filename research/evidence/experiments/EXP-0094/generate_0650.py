#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.65.0.json` from `0.64.0.json`.

One change (ADR-0092): the absolute `SIB = 25` shape gains the `0x67 66`
prefix pair at the 16-bit value width, in both directions and both value
windows.

- the bare rows are `67 66` at bytes 0-1, the opcode at byte 2, `ModRM = 04` at
  byte 3, `SIB = 25` at byte 4 and `disp32` at `[40,32]`; the value is
  `[27,3]`;
- the `R` rows fix `REX.R` at `[18,1]`, which inserts the `REX` byte at
  position 2 and moves every later field eight bits: the value is `[35,3]` and
  the displacement `[48,32]`.

There is no `base`, `index` or `scale` role: `SIB = 25` is template content, so
the shape has no register in its address and no `REX.B`/`REX.X` bit.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0094/generate_0650.py [target]

With no argument the target is `definitions/x86_64/0.65.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.64.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.65.0.json"

EXTENDED = [0, 1, 2, 3, 4, 5, 6, 7]

# direction -> (value role, opcode)
DIRECTIONS = [
    ("load", "dest", "8b"),
    ("store", "src", "89"),
]


def name(direction, extended):
    if direction == "load":
        if extended:
            return "x86:mov/r16-ext-addr32-abs32/legacy"
        return "x86:mov/r16-addr32-abs32/legacy"
    if extended:
        return "x86:mov/addr32-abs32-r16-ext/legacy"
    return "x86:mov/addr32-abs32-r16/legacy"


def slot(role, kind, target_type, placements, excluded=None, from_="reg_number"):
    entry = {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": from_,
        "modifiers": [],
        "placements": placements,
    }
    if excluded is not None:
        entry["excluded"] = excluded
    return entry


def disp_slot(offset):
    entry = slot("disp", "x86.imm", "disp32",
                 [{"bit_offset": offset, "width": 32}], from_="operand_value")
    entry["range"] = {"signed": True, "bits": 32, "align_bits": 0}
    return entry


NEW_FORMS = []
for extended in (False, True):
    for direction, value_role, opcode in DIRECTIONS:
        if extended:
            head = "676644" + opcode
            value = slot(value_role, "x86.gpr16", "r16",
                         [{"bit_offset": 18, "width": 1},
                          {"bit_offset": 35, "width": 3}], EXTENDED)
            disp = disp_slot(48)
        else:
            head = "6766" + opcode
            value = slot(value_role, "x86.gpr16", "r16",
                         [{"bit_offset": 27, "width": 3}])
            disp = disp_slot(40)
        NEW_FORMS.append({
            "form_id": name(direction, extended),
            "template": head + "04" + "25" + "00" * 4,
            "slots": [value, disp],
        })

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"


def render_placements(placements: list) -> str:
    pieces = []
    for item in placements:
        text = '{ "bit_offset": %d, "width": %d' % (
            item["bit_offset"], item["width"])
        if item.get("invert"):
            text += ', "invert": true'
        pieces.append(text + " }")
    return "[" + ", ".join(pieces) + "]"


def render_slot(entry: dict) -> list:
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
               span["align_bits"]))
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


def render_body(forms: list) -> str:
    return ",\n".join(render_form(entry) for entry in forms)


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    text = SOURCE.read_text(encoding="utf-8")
    if not text.endswith(TAIL_MARKER):
        raise SystemExit("unexpected file tail")
    head, block = text.split(HEAD_MARKER, 1)
    body = block[: -len(TAIL_MARKER)]

    document = json.loads(text)
    if document["version"] != "0.64.0":
        raise SystemExit("source is not 0.64.0")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.64.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.64.0"', '"version": "0.65.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
