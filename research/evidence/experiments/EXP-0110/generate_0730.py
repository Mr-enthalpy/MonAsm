#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.73.0.json` from `0.72.0.json`.

One change (`ADR-0109`): the 8-bit `mov` gains the general base-index (`SIB`)
shape over the low base/index window, in the three byte-register windows that
add no new prefix:

- `r8` (no `REX`): `%al`-`%dl`, register field 0-3;
- `r8h` (no `REX`): `%ah`-`%dh`, register field 4-7, `gpr8h`;
- `r8-rex` (`REX = 40`): `%spl`-`%dil`, register field 4-7.

Twelve rows = three windows x load/store x `disp8`/`disp32`. The high-register
window (`%r8b`-`%r15b`) needs a `REX.R` bit and is not part of this slice.

Templates are the measured `EXP-0110` bytes with the register, base, index,
scale and displacement zeroed.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0110/generate_0730.py [target]

With no argument the target is `definitions/x86_64/0.73.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.72.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.73.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"

LOW_BYTES = [4, 5, 6, 7]
HIGH_BYTES = [0, 1, 2, 3]
REX_BYTES = [0, 1, 2, 3]


def value_slot(role: str, target_type: str, excluded: list, bit: int) -> dict:
    return {
        "role": role,
        "kind": "x86.gpr8" if target_type == "r8" else "x86.gpr8h",
        "target_type": target_type,
        "from": "reg_number",
        "excluded": excluded,
        "modifiers": [],
        "placements": [{"bit_offset": bit, "width": 3}],
    }


def base_slot(bit: int) -> dict:
    return {
        "role": "base",
        "kind": "x86.gpr64",
        "target_type": "rm64",
        "from": "reg_number",
        "modifiers": [],
        "placements": [{"bit_offset": bit, "width": 3}],
    }


def index_slot(bit: int) -> dict:
    return {
        "role": "index",
        "kind": "x86.gpr64",
        "target_type": "sib_index",
        "from": "reg_number",
        "excluded": [4],
        "modifiers": [],
        "placements": [{"bit_offset": bit, "width": 3}],
    }


def scale_slot(bit: int) -> dict:
    return {
        "role": "imm",
        "kind": "x86.scale",
        "target_type": "scale2",
        "from": "operand_value",
        "range": {"signed": False, "bits": 2, "align_bits": 0},
        "modifiers": [],
        "placements": [{"bit_offset": bit, "width": 2}],
    }


def disp_slot(width: int, bit: int) -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp%d" % width,
        "from": "operand_value",
        "range": {"signed": True, "bits": width, "align_bits": 0},
        "modifiers": [],
        "placements": [{"bit_offset": bit, "width": width}],
    }


def make_form(form_id: str, template: str, role: str, target_type: str,
              excluded: list, rex: bool, width: int) -> dict:
    shift = 8 if rex else 0
    return {
        "form_id": form_id,
        "requires_extensions": [],
        "template": template,
        "slots": [
            value_slot(role, target_type, excluded, 11 + shift),
            base_slot(16 + shift),
            index_slot(19 + shift),
            scale_slot(22 + shift),
            disp_slot(width, 24 + shift),
        ],
    }


NEW_FORMS = []
for window, target_type, excluded, rex, head in (
    ("r8", "r8", LOW_BYTES, False, "8a"),
    ("r8h", "r8h", HIGH_BYTES, False, "8a"),
    ("r8", "r8", REX_BYTES, True, "408a"),
):
    for width, tag in ((8, "disp8"), (32, "disp32")):
        load_opcode = head
        store_opcode = head.replace("8a", "88")
        suffix = "-rex" if rex else ""
        load_temp = (load_opcode + "440000" if width == 8
                     else load_opcode + "840000000000")
        store_temp = (store_opcode + "440000" if width == 8
                      else store_opcode + "840000000000")
        NEW_FORMS.append(make_form(
            "x86:mov/%s-base-index-%s%s/legacy" % (window, tag, suffix),
            load_temp, "dest", target_type, excluded, rex, width))
        NEW_FORMS.append(make_form(
            "x86:mov/base-index-%s-%s%s/legacy" % (tag, window, suffix),
            store_temp, "src", target_type, excluded, rex, width))


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
    if document["version"] != "0.72.0":
        raise SystemExit("source is not 0.72.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.72.0 forms block")

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

    updated = head.replace('"version": "0.72.0"', '"version": "0.73.0"', 1)
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
