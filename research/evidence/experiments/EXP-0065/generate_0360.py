#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.36.0.json` from `0.35.0.json`.

One change (ADR-0063): the 32-bit GPR `mov` family takes the `%rsp`/`%r12`
`SIB` bases at `mod = 00`. The base is not a slot -- `SIB = 24` and the base's
`REX.B` are template content -- so each base, direction and register window is
its own row. `%rsp` needs a `REX` byte only for a high register, `%r12` carries
`REX.B = 1` in every row, and the low rows keep the 3-bit register field while
the `-ext` rows carry `REX.R` plus a 3-bit field and exclude `0`-`7`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0065/generate_0360.py [target]

With no argument the target is `definitions/x86_64/0.36.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.35.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.36.0.json"

ARG_3BIT = [{"bit_offset": 11, "width": 3}]
ARG_3BIT_HIGH = [{"bit_offset": 19, "width": 3}]
ARG_4BIT = [{"bit_offset": 2, "width": 1}, {"bit_offset": 19, "width": 3}]

LOW = list(range(8))

ROWS = [
    # (role, form_id, template, placements, excluded)
    ("dest", "x86:mov/r32-rsp/legacy", "8b0424", ARG_3BIT, None),
    ("src", "x86:mov/rsp-r32/legacy", "890424", ARG_3BIT, None),
    ("dest", "x86:mov/r32-r12/legacy", "418b0424", ARG_3BIT_HIGH, None),
    ("src", "x86:mov/r12-r32/legacy", "41890424", ARG_3BIT_HIGH, None),
    ("dest", "x86:mov/r32-ext-rsp/legacy", "448b0424", ARG_4BIT, LOW),
    ("src", "x86:mov/rsp-r32-ext/legacy", "44890424", ARG_4BIT, LOW),
    ("dest", "x86:mov/r32-ext-r12/legacy", "458b0424", ARG_4BIT, LOW),
    ("src", "x86:mov/r12-r32-ext/legacy", "45890424", ARG_4BIT, LOW),
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
        "slots": [slot(role, "x86.gpr32", "r32", placements, excluded)],
    }
    for (role, form_id, template, placements, excluded) in ROWS
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
    if document["version"] != "0.35.0":
        raise SystemExit("source is not 0.35.0")
    # The renderer must reproduce the source byte for byte before it is
    # trusted with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.35.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.35.0"', '"version": "0.36.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
