#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.62.0.json` from `0.61.0.json`.

One change (ADR-0089): the no-base indexed shape reaches the 64-bit value
width. `REX.W` is mandatory, so the `REX` byte always exists and `R`/`X` are
free bits inside it rather than separate windows:

- `0x67` at byte 0 and `REX = 48` at byte 1, so the opcode is byte 2,
  `ModRM = 04` byte 3 and `SIB = 05` byte 4;
- the value is `[10,1]` (its fourth bit) plus `[27,3]`, the index is `[9,1]`
  plus `[35,3]` (excluding `4`), the scale is `[38,2]` and the displacement
  is `[40,32]`.

There is no `base` role and therefore no `REX.B` bit.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0091/generate_0620.py [target]

With no argument the target is `definitions/x86_64/0.62.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.61.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.62.0.json"

NO_INDEX = [4]

# direction -> (opcode, value role)
DIRECTIONS = [
    ("load", "8b", "dest"),
    ("store", "89", "src"),
]

TEMPLATE_HEAD = "6748"


def name(value_role, direction):
    if direction == "load":
        return "x86:mov/r64-addr32-index-disp32/legacy"
    return "x86:mov/addr32-index-disp32-r64/legacy"


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


NEW_FORMS = []
for direction, opcode, value_role in DIRECTIONS:
    scale_slot = slot("imm", "x86.scale", "scale2",
                      [{"bit_offset": 38, "width": 2}], from_="operand_value")
    scale_slot["range"] = {"signed": False, "bits": 2, "align_bits": 0}
    disp_slot = slot("disp", "x86.imm", "disp32",
                     [{"bit_offset": 40, "width": 32}], from_="operand_value")
    disp_slot["range"] = {"signed": True, "bits": 32, "align_bits": 0}
    NEW_FORMS.append({
        "form_id": name(value_role, direction),
        "template": TEMPLATE_HEAD + opcode + "04" + "05" + "00" * 4,
        "slots": [
            slot(value_role, "x86.gpr64", "r64",
                 [{"bit_offset": 10, "width": 1},
                  {"bit_offset": 27, "width": 3}]),
            slot("index", "x86.gpr32", "sib_index32",
                 [{"bit_offset": 9, "width": 1},
                  {"bit_offset": 35, "width": 3}], NO_INDEX),
            scale_slot,
            disp_slot,
        ],
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
    if document["version"] != "0.61.0":
        raise SystemExit("source is not 0.61.0")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.61.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.61.0"', '"version": "0.62.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
