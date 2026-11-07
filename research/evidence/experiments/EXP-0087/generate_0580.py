#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.58.0.json` from `0.57.0.json`.

One change (ADR-0085): the `0x67 66` `movw` rows take the three single-`REX`
windows. The `REX` byte sits at position 2, so `0x67` is template byte 0,
`0x66` byte 1, `REX` byte 2, the opcode byte 3, `ModRM` byte 4 and `SIB`
byte 5. The value register is `x86.gpr16`/`r16` at `[35,3]`, the base is
`x86.gpr32`/`rm32` at `[40,3]`, the index is `x86.gpr32`/`sib_index32` at
`[43,3]` (index `4` excluded), the scale is `[46,2]` and the displacement
`[48,8]` or `[48,32]`. The fixed bit is `R` at `[18,1]`, `B` at `[16,1]` or
`X` at `[17,1]`, and its slot excludes `0`-`7`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0087/generate_0580.py [target]

With no argument the target is `definitions/x86_64/0.58.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.57.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.58.0.json"

REG = [{"bit_offset": 35, "width": 3}]
BASE = [{"bit_offset": 40, "width": 3}]
INDEX = [{"bit_offset": 43, "width": 3}]
SCALE = [{"bit_offset": 46, "width": 2}]
DISP8 = [{"bit_offset": 48, "width": 8}]
DISP32 = [{"bit_offset": 48, "width": 32}]

LOW = [0, 1, 2, 3, 4, 5, 6, 7]
NO_INDEX = [4]

# window -> (template head bytes, extended role, fixed bit offset)
WINDOWS = [
    ("r16-ext", "676644", "dest", 18),
    ("base-ext", "676641", "base", 16),
    ("index-ext", "676642", "index", 17),
]

# direction -> (opcode, role)
DIRECTIONS = [
    ("load", "8b", "dest"),
    ("store", "89", "src"),
]

DISPS = [("disp8", DISP8, 8), ("disp32", DISP32, 32)]


def name(role, window, direction, disp_bits):
    """Build the `form_id` the same way the earlier `addr32` slices do."""
    if direction == "load":
        head = "r16-ext" if window == "r16-ext" else "r16"
    else:
        head = "r16-ext" if window == "r16-ext" else "r16"

    middle = "addr32-"
    if window == "base-ext":
        middle += "base-ext-index"
    elif window == "index-ext":
        middle += "base-index-ext"
    else:
        middle += "base-index"

    if direction == "load":
        return "x86:mov/%s-%s-disp%d/legacy" % (head, middle, disp_bits)
    return "x86:mov/%s-disp%d-%s/legacy" % (middle, disp_bits, head)


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


NEW_FORMS = []
for window, head, extended_role, fixed_bit in WINDOWS:
    for direction, opcode, value_role in DIRECTIONS:
        for disp_name, disp_placements, disp_bits in DISPS:
            modrm = "44" if disp_bits == 8 else "84"
            template = head + opcode + modrm + "00"
            if disp_bits == 8:
                template += "00"
            else:
                template += "00" * 4
            value_placements = REG
            base_placements = BASE
            index_placements = INDEX
            if extended_role == "dest":
                value_placements = [{"bit_offset": fixed_bit, "width": 1}] + REG
            elif extended_role == "base":
                base_placements = [{"bit_offset": fixed_bit, "width": 1}] + BASE
            else:
                index_placements = [{"bit_offset": fixed_bit, "width": 1}] + INDEX
            slots = [
                slot(value_role, "x86.gpr16", "r16", value_placements,
                     LOW if extended_role == "dest" else None),
                slot("base", "x86.gpr32", "rm32", base_placements,
                     LOW if extended_role == "base" else None),
                slot("index", "x86.gpr32", "sib_index32", index_placements,
                     LOW if extended_role == "index" else NO_INDEX),
                slot("imm", "x86.scale", "scale2", SCALE, None,
                     from_="operand_value"),
            ]
            slots[-1]["range"] = {"signed": False, "bits": 2, "align_bits": 0}
            disp_slot = slot("disp", "x86.imm", "disp%d" % disp_bits,
                             disp_placements, None, from_="operand_value")
            disp_slot["range"] = {
                "signed": True, "bits": disp_bits, "align_bits": 0}
            slots.append(disp_slot)
            NEW_FORMS.append({
                "form_id": name(value_role, window, direction, disp_bits),
                "template": template,
                "slots": slots,
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
    if document["version"] != "0.57.0":
        raise SystemExit("source is not 0.57.0")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.57.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.57.0"', '"version": "0.58.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
