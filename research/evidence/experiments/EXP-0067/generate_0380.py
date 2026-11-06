#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.38.0.json` from `0.37.0.json`.

One change (ADR-0065): the 32-bit GPR `mov` family takes the plain-base
`disp32` shape (`mod = 10`). The legacy row has no `REX` byte, so a high
register or a high base changes the length; the reach is three rows per
direction (low/low, `REX.R`, `REX.B`). `%rsp`/`%r12` still need the `SIB`
byte, but `%rbp`/`%r13` are ordinary bases at `mod = 10`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0067/generate_0380.py [target]

With no argument the target is `definitions/x86_64/0.38.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.37.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.38.0.json"

LOW_DEST = [{"bit_offset": 11, "width": 3}]
LOW_BASE = [{"bit_offset": 8, "width": 3}]
LOW_DISP = [{"bit_offset": 16, "width": 32}]
HIGH_DEST = [{"bit_offset": 2, "width": 1}, {"bit_offset": 19, "width": 3}]
HIGH_BASE = [{"bit_offset": 0, "width": 1}, {"bit_offset": 16, "width": 3}]
HIGH_DISP = [{"bit_offset": 24, "width": 32}]

LOW = list(range(8))

ROWS = [
    # (role, form_id, template, arg placements, arg excluded,
    #  base placements, base excluded, disp placements)
    ("dest", "x86:mov/r32-base-disp32/legacy", "8b8000000000",
     LOW_DEST, None, LOW_BASE, [4], LOW_DISP),
    ("src", "x86:mov/base-disp32-r32/legacy", "898000000000",
     LOW_DEST, None, LOW_BASE, [4], LOW_DISP),
    ("dest", "x86:mov/r32-ext-base-disp32/legacy", "448b8000000000",
     HIGH_DEST, LOW, HIGH_BASE, [4, 12], HIGH_DISP),
    ("src", "x86:mov/base-disp32-r32-ext/legacy", "44898000000000",
     HIGH_DEST, LOW, HIGH_BASE, [4, 12], HIGH_DISP),
    ("dest", "x86:mov/r32-base-ext-disp32/legacy", "418b8000000000",
     HIGH_DEST[1:], None, HIGH_BASE, LOW + [12], HIGH_DISP),
    ("src", "x86:mov/base-ext-disp32-r32/legacy", "41898000000000",
     HIGH_DEST[1:], None, HIGH_BASE, LOW + [12], HIGH_DISP),
]


def slot(role, kind, target_type, placements, excluded, span=None):
    entry = {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
        "modifiers": [],
        "placements": placements,
    }
    if span is not None:
        entry["from"] = "operand_value"
        entry["range"] = span
    if excluded is not None:
        entry["excluded"] = excluded
    return entry


DISP32 = {"signed": True, "bits": 32, "align_bits": 0}

NEW_FORMS = [
    {
        "form_id": form_id,
        "template": template,
        "slots": [
            slot(role, "x86.gpr32", "r32", arg, arg_excluded),
            slot("base", "x86.gpr64", "rm64", base, base_excluded),
            slot("disp", "x86.imm", "disp32", disp, None, DISP32),
        ],
    }
    for (role, form_id, template, arg, arg_excluded, base, base_excluded,
         disp) in ROWS
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
    if document["version"] != "0.37.0":
        raise SystemExit("source is not 0.37.0")
    # The renderer must reproduce the source byte for byte before it is
    # trusted with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.37.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.37.0"', '"version": "0.38.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
