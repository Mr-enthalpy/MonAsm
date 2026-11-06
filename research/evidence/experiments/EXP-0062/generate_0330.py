#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.33.0.json` from `0.32.0.json`.

One change (ADR-0060): the 64-bit GPR `mov` memory family takes the
`mod = 00` shape. Two rows -- load and store -- carry a base operand with
four exclusions: `%rbp`/`%r13` because `r/m = 101` at `mod = 00` is
RIP-relative (`EC-34`), and `%rsp`/`%r12` because they need the `SIB` byte
(`EC-35`). `REX.W` is in every template, so both register fields are the
existing four-bit `[2,1]`+`[19,3]` and `[0,1]`+`[16,3]` pairs; no `disp` slot
exists, so a displacement operand is `E-OPERAND-002`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0062/generate_0330.py [target]

With no argument the target is `definitions/x86_64/0.33.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.32.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.33.0.json"

BASES = [4, 5, 12, 13]
REGISTER = [{"bit_offset": 2, "width": 1}, {"bit_offset": 19, "width": 3}]
BASE = [{"bit_offset": 0, "width": 1}, {"bit_offset": 16, "width": 3}]

ROWS = [
    ("dest", "x86:mov/r64-base/legacy", "488b00"),
    ("src", "x86:mov/base-r64/legacy", "488900"),
]

NEW_FORMS = [
    {
        "form_id": form_id,
        "template": template,
        "slots": [
            {
                "role": role,
                "kind": "x86.gpr64",
                "target_type": "r64",
                "from": "reg_number",
                "modifiers": [],
                "placements": REGISTER,
            },
            {
                "role": "base",
                "kind": "x86.gpr64",
                "target_type": "rm64",
                "from": "reg_number",
                "excluded": BASES,
                "modifiers": [],
                "placements": BASE,
            },
        ],
    }
    for role, form_id, template in ROWS
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
    if document["version"] != "0.32.0":
        raise SystemExit("source is not 0.32.0")
    # The renderer must reproduce the source byte for byte before it is
    # trusted with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.32.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.32.0"', '"version": "0.33.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
