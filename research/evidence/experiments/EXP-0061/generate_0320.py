#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.32.0.json` from `0.31.0.json`.

One change (ADR-0059): fourteen `mov` rows carry the `%rsp`/`%r12` `SIB`
bases into the byte-width no-displacement memory shape. `ADR-0058` left those
bases out because `r/m = 100` announces a `SIB` byte the plain-base row has no
room for; this slice spends that byte (`SIB = 24`) and fixes the base, and its
`REX.B` bit, in the template -- one row per base, exactly as `EC-35` already
does for the `disp8`/`disp32` rows.

The high-byte window has no `%r12` half: `REX.B` renames `%ah` to `%spl`, so
`movb (%r12), %ah` has no encoding. That is why the slice is seven
base/register combinations and fourteen rows, not eight and sixteen.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0061/generate_0320.py [target]

With no argument the target is `definitions/x86_64/0.32.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.31.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.32.0.json"


def placement(bit_offset: int, width: int) -> dict:
    return {"bit_offset": bit_offset, "width": width}


def reg_slot(role: str, kind: str, target_type: str, placements: list,
             excluded: list) -> dict:
    return {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
        "excluded": excluded,
        "modifiers": [],
        "placements": placements,
    }


LOW = [4, 5, 6, 7]
HIGH = [0, 1, 2, 3]
EXT = [0, 1, 2, 3, 4, 5, 6, 7]

# (direction, form_id, template, kind, target_type, placements, excluded)
ROWS = [
    ("load", "x86:mov/r8-rsp/legacy", "8a0424",
     "x86.gpr8", "r8", [placement(11, 3)], LOW),
    ("store", "x86:mov/rsp-r8/legacy", "880424",
     "x86.gpr8", "r8", [placement(11, 3)], LOW),
    ("load", "x86:mov/r8-r12/legacy", "418a0424",
     "x86.gpr8", "r8", [placement(19, 3)], LOW),
    ("store", "x86:mov/r12-r8/legacy", "41880424",
     "x86.gpr8", "r8", [placement(19, 3)], LOW),
    ("load", "x86:mov/r8h-rsp/legacy", "8a2424",
     "x86.gpr8h", "r8h", [placement(11, 3)], HIGH),
    ("store", "x86:mov/rsp-r8h/legacy", "882424",
     "x86.gpr8h", "r8h", [placement(11, 3)], HIGH),
    ("load", "x86:mov/r8-rsp-rex/legacy", "408a2424",
     "x86.gpr8", "r8", [placement(19, 3)], HIGH),
    ("store", "x86:mov/rsp-r8-rex/legacy", "40882424",
     "x86.gpr8", "r8", [placement(19, 3)], HIGH),
    ("load", "x86:mov/r8-r12-rex/legacy", "418a2424",
     "x86.gpr8", "r8", [placement(19, 3)], HIGH),
    ("store", "x86:mov/r12-r8-rex/legacy", "41882424",
     "x86.gpr8", "r8", [placement(19, 3)], HIGH),
    ("load", "x86:mov/r8-ext-rsp/legacy", "448a0424",
     "x86.gpr8", "r8", [placement(2, 1), placement(19, 3)], EXT),
    ("store", "x86:mov/rsp-r8-ext/legacy", "44880424",
     "x86.gpr8", "r8", [placement(2, 1), placement(19, 3)], EXT),
    ("load", "x86:mov/r8-ext-r12/legacy", "458a0424",
     "x86.gpr8", "r8", [placement(2, 1), placement(19, 3)], EXT),
    ("store", "x86:mov/r12-r8-ext/legacy", "45880424",
     "x86.gpr8", "r8", [placement(2, 1), placement(19, 3)], EXT),
]


def form_of(direction: str, form_id: str, template: str, kind: str,
            target_type: str, placements: list, excluded: list) -> dict:
    role = "dest" if direction == "load" else "src"
    return {"form_id": form_id, "template": template,
            "slots": [reg_slot(role, kind, target_type, placements, excluded)]}


NEW_FORMS = [
    form_of(direction, form_id, template, kind, target_type, placements,
            excluded)
    for direction, form_id, template, kind, target_type, placements, excluded
    in ROWS
]

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
    if document["version"] != "0.31.0":
        raise SystemExit("source is not 0.31.0")
    # The renderer must reproduce the source byte for byte before it is
    # trusted with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.31.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.31.0"', '"version": "0.32.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
