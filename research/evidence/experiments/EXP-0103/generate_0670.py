#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.67.0.json` from `0.66.0.json`.

One change (`ADR-0102`): the direct `call rel32` row. It is `E8 cd`, the
`jmp rel32` row of `0.1.0` with opcode `E8` instead of `E9`, so the `target`
slot keeps the same shape: `x86.rel`/`rel32` at `[8,32]`, signed 32 bits,
filled by `payload.value` when the plan carries a literal displacement.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0103/generate_0670.py [target]

With no argument the target is `definitions/x86_64/0.67.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.66.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.67.0.json"


def rel32_slot():
    return {
        "role": "target",
        "kind": "x86.rel",
        "target_type": "rel32",
        "from": "operand_value",
        "range": {"signed": True, "bits": 32, "align_bits": 0},
        "modifiers": [],
        "placements": [{"bit_offset": 8, "width": 32}],
    }


NEW_FORMS = [
    {
        "form_id": "x86:call/rel32/legacy",
        "template": "e800000000",
        "slots": [rel32_slot()],
    },
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
    if document["version"] != "0.66.0":
        raise SystemExit("source is not 0.66.0")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.66.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.66.0"', '"version": "0.67.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
