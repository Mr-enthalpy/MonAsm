#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.43.0.json` from `0.42.0.json`.

One change (ADR-0070): the 16-bit `disp8` `mov` rows gain the `%r8w`-`%r15w`
register window. `REX.R` is fixed in the template, so the slot excludes the
low register window. At `mod = 01` the base window is wider than at `mod = 00`:
`%rbp`/`%r13` are legal bases, so the plain low-base row excludes `%rsp` only
and the plain `-ext`-base row excludes `0`-`7` and `%r12`. The `SIB` bases
stay fixed and only gain `REX.R`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0072/generate_0430.py [target]

With no argument the target is `definitions/x86_64/0.43.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.42.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.43.0.json"

# `REX.R` is bit 2 of the `REX` byte, so it sits at `[10,1]`; `ModRM` is byte
# 3 and its `reg` field is `[27,3]`.
REG_REX = [{"bit_offset": 10, "width": 1}, {"bit_offset": 27, "width": 3}]
LOW_BASE = [{"bit_offset": 24, "width": 3}]
HIGH_BASE = [{"bit_offset": 8, "width": 1}, {"bit_offset": 24, "width": 3}]
DISP_PLAIN = [{"bit_offset": 32, "width": 8}]
DISP_SIB = [{"bit_offset": 40, "width": 8}]

LOW_REG = list(range(8))
PLAIN_LOW = (LOW_BASE, [4])
PLAIN_HIGH = (HIGH_BASE, [0, 1, 2, 3, 4, 5, 6, 7, 12])

ROWS = [
    # (role, form_id, template, base placements, base excluded, disp placements)
    ("dest", "x86:mov/r16-ext-base-disp8/legacy", "66448b4000",
     *PLAIN_LOW, DISP_PLAIN),
    ("src", "x86:mov/base-disp8-r16-ext/legacy", "6644894000",
     *PLAIN_LOW, DISP_PLAIN),
    ("dest", "x86:mov/r16-ext-base-ext-disp8/legacy", "66458b4000",
     *PLAIN_HIGH, DISP_PLAIN),
    ("src", "x86:mov/base-ext-disp8-r16-ext/legacy", "6645894000",
     *PLAIN_HIGH, DISP_PLAIN),
    ("dest", "x86:mov/r16-ext-rsp-disp8/legacy", "66448b442400",
     None, None, DISP_SIB),
    ("src", "x86:mov/rsp-disp8-r16-ext/legacy", "664489442400",
     None, None, DISP_SIB),
    ("dest", "x86:mov/r16-ext-r12-disp8/legacy", "66458b442400",
     None, None, DISP_SIB),
    ("src", "x86:mov/r12-disp8-r16-ext/legacy", "664589442400",
     None, None, DISP_SIB),
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
for role, form_id, template, base_placements, base_excluded, disp in ROWS:
    slots = [slot(role, "x86.gpr16", "r16", REG_REX, LOW_REG)]
    if base_placements is not None:
        slots.append(slot("base", "x86.gpr64", "rm64", base_placements,
                          base_excluded))
    disp_slot = slot("disp", "x86.imm", "disp8", disp, None, from_="operand_value")
    disp_slot["range"] = {"signed": True, "bits": 8, "align_bits": 0}
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
    if document["version"] != "0.42.0":
        raise SystemExit("source is not 0.42.0")
    # The renderer must reproduce the source byte for byte before it is
    # trusted with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.42.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.42.0"', '"version": "0.43.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
