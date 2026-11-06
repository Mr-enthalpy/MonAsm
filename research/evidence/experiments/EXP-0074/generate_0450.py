#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.45.0.json` from `0.44.0.json`.

One change (ADR-0072): the 16-bit `mov` memory rows gain a `SIB` index and
scale on the `%r8w`-`%r15w` register window, in both directions and at both
displacement widths. The rows already carry a `REX` byte because `REX.R` is
fixed in the template, so `REX.B` and `REX.X` can carry the base's and the
index's fourth bit without changing the instruction length. The base slot
accepts all sixteen values; the index slot excludes `4` (`%rsp`, the "no
index" encoding). The displacement moves behind the `SIB` byte: `[40,8]` for
`disp8` and `[40,32]` for `disp32`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0074/generate_0450.py [target]

With no argument the target is `definitions/x86_64/0.45.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.44.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.45.0.json"

REG_REX = [{"bit_offset": 10, "width": 1}, {"bit_offset": 27, "width": 3}]
BASE_REX = [{"bit_offset": 8, "width": 1}, {"bit_offset": 32, "width": 3}]
INDEX_REX = [{"bit_offset": 9, "width": 1}, {"bit_offset": 35, "width": 3}]
SCALE = [{"bit_offset": 38, "width": 2}]
DISP8 = [{"bit_offset": 40, "width": 8}]
DISP32 = [{"bit_offset": 40, "width": 32}]

LOW_REG = list(range(8))

ROWS = [
    ("dest", "x86:mov/r16-ext-base-index-disp8/legacy", "66448b440000",
     DISP8, 8),
    ("src", "x86:mov/base-index-disp8-r16-ext/legacy", "664489440000",
     DISP8, 8),
    ("dest", "x86:mov/r16-ext-base-index-disp32/legacy", "66448b840000000000",
     DISP32, 32),
    ("src", "x86:mov/base-index-disp32-r16-ext/legacy", "664489840000000000",
     DISP32, 32),
]


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
for role, form_id, template, disp, disp_bits in ROWS:
    slots = [
        slot(role, "x86.gpr16", "r16", REG_REX, LOW_REG),
        slot("base", "x86.gpr64", "rm64", BASE_REX, None),
        slot("index", "x86.gpr64", "sib_index", INDEX_REX, [4]),
        slot("imm", "x86.scale", "scale2", SCALE, None, from_="operand_value"),
    ]
    slots[-1]["range"] = {"signed": False, "bits": 2, "align_bits": 0}
    disp_slot = slot("disp", "x86.imm", "disp%d" % disp_bits, disp, None,
                     from_="operand_value")
    disp_slot["range"] = {"signed": True, "bits": disp_bits, "align_bits": 0}
    slots.append(disp_slot)
    NEW_FORMS.append(
        {"form_id": form_id, "template": template, "slots": slots})

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
    if document["version"] != "0.44.0":
        raise SystemExit("source is not 0.44.0")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.44.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.44.0"', '"version": "0.45.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
