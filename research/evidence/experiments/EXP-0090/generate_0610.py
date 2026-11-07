#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.61.0.json` from `0.60.0.json`.

One change (ADR-0088): the no-base indexed shape reaches the 32-bit value
width. `mod = 00` with `SIB.base = 101` frees the base slot and forces a
`disp32`, and the absent `0x66` removes one of the two `0.60.0` geometries:

- a row without a `REX` byte has `0x67` at byte 0, the opcode at byte 1,
  `ModRM = 04` at byte 2 and `SIB = 05` at byte 3, with the value at
  `[19,3]`, the index at `[27,3]`, the scale at `[30,2]` and the
  displacement at `[32,32]`;
- a row that fixes `REX.R` at `[10,1]` or `REX.X` at `[9,1]` inserts the
  `REX` byte at position 1, which moves every later field eight bits:
  value `[27,3]`, index `[35,3]`, scale `[38,2]`, displacement `[40,32]`.

Only `R` and `X` exist: there is no base register, so there is no `B` bit.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0090/generate_0610.py [target]

With no argument the target is `definitions/x86_64/0.61.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.60.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.61.0.json"

LOW = [0, 1, 2, 3, 4, 5, 6, 7]
NO_INDEX = [4]

FIXED_BITS = {"R": 10, "X": 9}

# window -> (template head bytes, extended bits, field shift)
WINDOWS = [
    ("none", "67", "", 0),
    ("R", "6744", "R", 8),
    ("X", "6742", "X", 8),
    ("RX", "6746", "RX", 8),
]

# direction -> (opcode, role)
DIRECTIONS = [
    ("load", "8b", "dest"),
    ("store", "89", "src"),
]


def name(role, bits, direction):
    head = "r32-ext" if "R" in bits else "r32"
    middle = "addr32-index" + ("-ext" if "X" in bits else "")
    if direction == "load":
        return "x86:mov/%s-%s-disp32/legacy" % (head, middle)
    return "x86:mov/%s-disp32-%s/legacy" % (middle, head)


def slot(role, kind, target_type, placements, excluded, from_="reg_number"):
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


def extend(bits, letter, placements):
    if letter in bits:
        return [{"bit_offset": FIXED_BITS[letter], "width": 1}] + placements, LOW
    return placements, None


NEW_FORMS = []
for window, head, bits, shift in WINDOWS:
    reg = [{"bit_offset": 19 + shift, "width": 3}]
    index = [{"bit_offset": 27 + shift, "width": 3}]
    scale_placement = [{"bit_offset": 30 + shift, "width": 2}]
    disp_placement = [{"bit_offset": 32 + shift, "width": 32}]
    for direction, opcode, value_role in DIRECTIONS:
        template = head + opcode + "04" + "05" + "00" * 4
        value_placements, value_excluded = extend(bits, "R", reg)
        index_placements, index_excluded = extend(bits, "X", index)
        if index_excluded is None:
            index_excluded = NO_INDEX
        scale_slot = slot("imm", "x86.scale", "scale2", scale_placement, None,
                          from_="operand_value")
        scale_slot["range"] = {"signed": False, "bits": 2, "align_bits": 0}
        disp_slot = slot("disp", "x86.imm", "disp32", disp_placement, None,
                         from_="operand_value")
        disp_slot["range"] = {"signed": True, "bits": 32, "align_bits": 0}
        NEW_FORMS.append({
            "form_id": name(value_role, bits, direction),
            "template": template,
            "slots": [
                slot(value_role, "x86.gpr32", "r32", value_placements,
                     value_excluded),
                slot("index", "x86.gpr32", "sib_index32", index_placements,
                     index_excluded),
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
    if document["version"] != "0.60.0":
        raise SystemExit("source is not 0.60.0")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.60.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.60.0"', '"version": "0.61.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
