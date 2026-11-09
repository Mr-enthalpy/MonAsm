#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.72.0.json` from `0.71.0.json`.

One change (`ADR-0108`): the legacy and VEX `movaps`/`vmovaps` gain a general
base-index (`SIB`) shape over the low base/index window, at both the low and
the high `xmm` window, for `disp8` and `disp32` and both directions. Sixteen
rows = {legacy, VEX} x {load, store} x {disp8, disp32} x {xmm0-7, xmm8-15}.

The base and index are the three-bit window (0-7, index 4 excluded because it
means "no index"), so the `REX`/VEX extension bits stay at their template
values. The high `xmm` window is a second row in each family because the legacy
`REX.R` byte and the VEX `R̄` bit change the instruction's template:

- legacy low `disp8` is `0f 28 44 ss dd` (5 B), high is `44 0f 28 …` (6 B);
- legacy low `disp32` is 8 B, high is 9 B;
- VEX is five bytes plus the displacement in both windows, because `R̄` lives
  in the two-byte prefix (`c5 f8` -> `c5 78`).

Templates are the measured `EXP-0109` bytes with the register, base, index,
scale and displacement zeroed.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0109/generate_0720.py [target]

With no argument the target is `definitions/x86_64/0.72.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.71.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.72.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"

LOW_XMM = [0, 1, 2, 3, 4, 5, 6, 7]


def legacy_reg_slot(role: str, high: bool) -> dict:
    slot = {
        "role": role,
        "kind": "x86.xmm",
        "target_type": "xmm",
        "from": "reg_number",
        "modifiers": [],
        "placements": (
            [{"bit_offset": 2, "width": 1},
             {"bit_offset": 27, "width": 3}]
            if high
            else [{"bit_offset": 19, "width": 3}]
        ),
    }
    if high:
        slot["excluded"] = LOW_XMM
    return slot


def vex_reg_slot(role: str, high: bool) -> dict:
    """The fourth bit is `R̄` in the two-byte VEX byte at bit 15."""
    slot = {
        "role": role,
        "kind": "x86.xmm",
        "target_type": "xmm",
        "from": "reg_number",
        "modifiers": [],
        "placements": [
            {"bit_offset": 15, "width": 1, "invert": True},
            {"bit_offset": 27, "width": 3},
        ],
    }
    if high:
        slot["excluded"] = LOW_XMM
    return slot


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


def make_form(form_id: str, template: str, extensions: list, role: str,
              width: int, family: str, high: bool) -> dict:
    if family == "legacy":
        reg = legacy_reg_slot(role, high)
        shift = 8 if high else 0
    else:
        reg = vex_reg_slot(role, high)
        shift = 8
    return {
        "form_id": form_id,
        "requires_extensions": extensions,
        "template": template,
        "slots": [
            reg,
            base_slot(24 + shift),
            index_slot(27 + shift),
            scale_slot(30 + shift),
            disp_slot(width, 32 + shift),
        ],
    }


def rows(family: str) -> list:
    is_vex = family == "vex"
    prefix = "vmovaps" if is_vex else "movaps"
    ext = ["avx"] if is_vex else []
    head = "c5f8" if is_vex else "0f"
    high_head = "c578" if is_vex else "440f"
    out = []
    for width, tag in ((8, "disp8"), (32, "disp32")):
        for high in (False, True):
            h = "ext-" if high else ""
            s = "-ext" if high else ""
            load_temp = (high_head + "28440000" if width == 8
                         else high_head + "28840000000000")
            store_temp = (high_head + "29440000" if width == 8
                          else high_head + "29840000000000")
            if not high:
                load_temp = head + "28440000" if width == 8 \
                    else head + "28840000000000"
                store_temp = head + "29440000" if width == 8 \
                    else head + "29840000000000"
            out.append(make_form(
                "x86:%s/xmm-%sbase-index-%s/%s" % (prefix, h, tag, family),
                load_temp, ext, "dest", width, family, high))
            out.append(make_form(
                "x86:%s/base-index-%s-xmm%s/%s" % (prefix, tag, s, family),
                store_temp, ext, "src", width, family, high))
    return out


NEW_FORMS = rows("legacy") + rows("vex")


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
    if document["version"] != "0.71.0":
        raise SystemExit("source is not 0.71.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.71.0 forms block")

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

    updated = head.replace('"version": "0.71.0"', '"version": "0.72.0"', 1)
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
