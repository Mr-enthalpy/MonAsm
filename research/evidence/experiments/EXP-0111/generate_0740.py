#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.74.0.json` from `0.73.0.json`.

One change (`ADR-0110`): the register/register `sub` row `29 /r` at the three
value widths. Three rows, low register window only:

- `x86:sub/rm64-r64/legacy`, `48 29 c8`, destination at `REX.B` + `ModRM.r/m`
  and source at `REX.R` + `ModRM.reg`;
- `x86:sub/rm32-r32/legacy`, `29 c8`, both operands three bits;
- `x86:sub/rm16-r16/legacy`, `66 29 c8`, with `0x66` as template content.

The memory-destination direction (`2B /r`) stays absent, and the high
register window (`%r8`-`%r15`) needs `REX.R`/`REX.B` and is deferred.

Templates are the measured `EXP-0111` bytes with the register fields zeroed.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0111/generate_0740.py [target]

With no argument the target is `definitions/x86_64/0.74.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.73.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.74.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"

# form_id, template, dest kind, dest target, src kind, src target, rex,
# modrm_bits (bit offset of the ModRM byte; eight bits per template byte)
ROWS = [
    ("x86:sub/rm64-r64/legacy", "4829c8",
     "x86.gpr64", "rm64", "x86.gpr64", "r64", True, 16),
    ("x86:sub/rm32-r32/legacy", "29c8",
     "x86.gpr32", "rm32", "x86.gpr32", "r32", False, 8),
    ("x86:sub/rm16-r16/legacy", "6629c8",
     "x86.gpr16", "rm16", "x86.gpr16", "r16", False, 16),
]


def reg_slot(role: str, kind: str, target_type: str, placements: list) -> dict:
    return {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
        "modifiers": [],
        "placements": placements,
    }


def make_form(form_id: str, template: str, dest_kind: str, dest_type: str,
              src_kind: str, src_type: str, rex: bool, modrm: int) -> dict:
    dest = [{"bit_offset": modrm, "width": 3}]
    src = [{"bit_offset": modrm + 3, "width": 3}]
    if rex:
        dest.insert(0, {"bit_offset": 0, "width": 1})
        src.insert(0, {"bit_offset": 2, "width": 1})
    return {
        "form_id": form_id,
        "requires_extensions": [],
        "template": template,
        "slots": [
            reg_slot("dest", dest_kind, dest_type, dest),
            reg_slot("src", src_kind, src_type, src),
        ],
    }


NEW_FORMS = [make_form(*row) for row in ROWS]


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
        '    "requires_extensions": [%s],'
        % ", ".join('"%s"' % name for name in entry["requires_extensions"]),
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


def canonical_digest(document) -> str:
    text = json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    text = SOURCE.read_text(encoding="utf-8")
    if not text.endswith(TAIL_MARKER):
        raise SystemExit("unexpected file tail")
    head, block = text.split(HEAD_MARKER, 1)
    body = block[: -len(TAIL_MARKER)]

    document = json.loads(text)
    if document["version"] != "0.73.0":
        raise SystemExit("source is not 0.73.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.73.0 forms block")

    forms = document["forms"]
    known = {form["form_id"] for form in forms}
    for form in NEW_FORMS:
        if form["form_id"] in known:
            raise SystemExit("%s already exists" % form["form_id"])
        for slot in form["slots"]:
            for placement in slot["placements"]:
                if placement["bit_offset"] + placement["width"] > len(
                        form["template"]) * 4:
                    raise SystemExit("%s: placement past the template"
                                     % form["form_id"])

    updated = head.replace('"version": "0.73.0"', '"version": "0.74.0"', 1)
    updated = updated + HEAD_MARKER + render_body(forms + NEW_FORMS) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    if checked["forms"][: len(forms)] != forms:
        raise SystemExit("old forms changed")
    if checked["forms"][len(forms):] != NEW_FORMS:
        raise SystemExit("new forms differ from the rendered plan")
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
