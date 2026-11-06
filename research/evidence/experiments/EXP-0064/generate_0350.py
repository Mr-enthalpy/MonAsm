#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.35.0.json` from `0.34.0.json`.

One change (ADR-0062): the 32-bit GPR `mov` family takes its first base rows,
the `mod = 00` plain-base shape. The legacy row has no `REX` byte, so a high
register or a high base changes the length; the reach is therefore three
disjoint rows per direction (low/low, `REX.R`, `REX.B`). The exclusions keep
the windows disjoint: `%rsp`/`%r12` need the `SIB` byte and `%rbp` has
`r/m = 101` at `mod = 00`, the RIP-relative shape.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0064/generate_0350.py [target]

With no argument the target is `definitions/x86_64/0.35.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.34.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.35.0.json"

DEST_3BIT = [{"bit_offset": 11, "width": 3}]
DEST_4BIT = [{"bit_offset": 2, "width": 1}, {"bit_offset": 19, "width": 3}]
DEST_3BIT_HIGH = [{"bit_offset": 19, "width": 3}]
BASE_3BIT = [{"bit_offset": 8, "width": 3}]
BASE_4BIT = [{"bit_offset": 0, "width": 1}, {"bit_offset": 16, "width": 3}]

LOW = list(range(8))

ROWS = [
    # (role, form_id, template, dest placements, dest excluded,
    #  base placements, base excluded)
    ("dest", "x86:mov/r32-base/legacy", "8b00",
     DEST_3BIT, None, BASE_3BIT, [4, 5]),
    ("dest", "x86:mov/r32-ext-base/legacy", "448b00",
     DEST_4BIT, LOW, BASE_4BIT, [4, 5, 12, 13]),
    ("dest", "x86:mov/r32-base-ext/legacy", "418b00",
     DEST_3BIT_HIGH, None, BASE_4BIT, LOW + [12, 13]),
    ("src", "x86:mov/base-r32/legacy", "8900",
     DEST_3BIT, None, BASE_3BIT, [4, 5]),
    ("src", "x86:mov/base-r32-ext/legacy", "448900",
     DEST_4BIT, LOW, BASE_4BIT, [4, 5, 12, 13]),
    ("src", "x86:mov/base-ext-r32/legacy", "418900",
     DEST_3BIT_HIGH, None, BASE_4BIT, LOW + [12, 13]),
]


def slot(role, kind, target_type, placements, excluded):
    entry = {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
        "modifiers": [],
        "placements": placements,
    }
    if excluded is not None:
        entry["excluded"] = excluded
    return entry


NEW_FORMS = [
    {
        "form_id": form_id,
        "template": template,
        "slots": [
            slot(role, "x86.gpr32", "r32", dest, dest_excluded),
            slot("base", "x86.gpr64", "rm64", base, base_excluded),
        ],
    }
    for (role, form_id, template,
         dest, dest_excluded, base, base_excluded) in ROWS
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
    if document["version"] != "0.34.0":
        raise SystemExit("source is not 0.34.0")
    # The renderer must reproduce the source byte for byte before it is
    # trusted with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.34.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.34.0"', '"version": "0.35.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
