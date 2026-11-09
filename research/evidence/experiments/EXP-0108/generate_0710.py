#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.71.0.json` from `0.70.0.json`.

One change (`ADR-0107`): the GPR `mov` gains the `0x67` address-size prefix on
the `%rip`-relative rows. Six forms: three value widths (`r16`, `r32`, `r64`)
times load and store. The prefix is a form fact, not a target-identity field:
the plan still declares `address_width: 64` and the `67` byte is in the
template (`EXP-0108`).

Templates are the measured bytes with the displacement zeroed:

| row | template | bytes | target placement |
|---|---|---|---|
| `r32-addr32-riprel32` | `678b0500000000` | 7 | `[24,32]` |
| `addr32-riprel32-r32` | `67890500000000` | 7 | `[24,32]` |
| `r64-addr32-riprel32` | `67488b0500000000` | 8 | `[32,32]` |
| `addr32-riprel32-r64` | `6748890500000000` | 8 | `[32,32]` |
| `r16-addr32-riprel32` | `67668b0500000000` | 8 | `[32,32]` |
| `addr32-riprel32-r16` | `6766890500000000` | 8 | `[32,32]` |

Usage (from the repository root):

    python research/evidence/experiments/EXP-0108/generate_0710.py [target]

With no argument the target is `definitions/x86_64/0.71.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.70.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.71.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"


def rel_slot() -> dict:
    return {
        "role": "target",
        "kind": "x86.rel",
        "target_type": "riprel32",
        "from": "operand_value",
        "range": {"signed": True, "bits": 32, "align_bits": 0},
        "modifiers": [],
        "placements": [],
    }


def make_form(form_id: str, template: str, role: str, kind: str,
              target_type: str, placements: list) -> dict:
    form = {
        "form_id": form_id,
        "requires_extensions": [],
        "template": template,
        "slots": [
            {
                "role": role,
                "kind": kind,
                "target_type": target_type,
                "from": "reg_number",
                "modifiers": [],
                "placements": placements,
            },
            rel_slot(),
        ],
    }
    bits = len(bytes.fromhex(template)) * 8
    form["slots"][-1]["placements"] = [{"bit_offset": bits - 32, "width": 32}]
    return form


NEW_FORMS = [
    make_form("x86:mov/r32-addr32-riprel32/legacy", "678b0500000000",
              "dest", "x86.gpr32", "r32",
              [{"bit_offset": 19, "width": 3}]),
    make_form("x86:mov/addr32-riprel32-r32/legacy", "67890500000000",
              "src", "x86.gpr32", "r32",
              [{"bit_offset": 19, "width": 3}]),
    make_form("x86:mov/r64-addr32-riprel32/legacy", "67488b0500000000",
              "dest", "x86.gpr64", "r64",
              [{"bit_offset": 10, "width": 1},
               {"bit_offset": 27, "width": 3}]),
    make_form("x86:mov/addr32-riprel32-r64/legacy", "6748890500000000",
              "src", "x86.gpr64", "r64",
              [{"bit_offset": 10, "width": 1},
               {"bit_offset": 27, "width": 3}]),
    make_form("x86:mov/r16-addr32-riprel32/legacy", "67668b0500000000",
              "dest", "x86.gpr16", "r16",
              [{"bit_offset": 27, "width": 3}]),
    make_form("x86:mov/addr32-riprel32-r16/legacy", "6766890500000000",
              "src", "x86.gpr16", "r16",
              [{"bit_offset": 27, "width": 3}]),
]


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
    if document["version"] != "0.70.0":
        raise SystemExit("source is not 0.70.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.70.0 forms block")

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

    updated = head.replace('"version": "0.70.0"', '"version": "0.71.0"', 1)
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
