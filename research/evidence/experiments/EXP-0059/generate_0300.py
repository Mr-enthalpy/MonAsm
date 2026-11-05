#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.30.0.json` from `0.29.0.json`.

One change (ADR-0057): twelve `mov` rows bring the `%r8b`-`%r15b` window into
the byte-width memory family. The family already has three base windows -- a
plain base (`mod = 01`, displacement byte), `%rsp` behind `ModRM.r/m = 100`
with `SIB = 24`, and `%r12` as the same `SIB` byte with `REX.B = 1` -- and
each at disp8 and disp32, in both directions. Every row here has `REX.R = 1`
(setting the register's fourth bit at `[2,1]`), so the template prefix is `44`
when `REX.B = 0` and `45` when the plain-base slot's top bit sets it.

The register slot is four bits (`[2,1]` plus `ModRM.reg` at `[19,3]`) and
excludes `0`-`7`: those would clear the template's `REX.R` and emit the
`%spl`-`%dil` row's prefix. The plain-base slot is four bits (`[0,1]` plus
`ModRM.rm` at `[16,3]`) and excludes `4` and `12`, the two bases that need the
`SIB` byte. The two `SIB` rows carry no base slot at all, because `44` and `45`
are disjoint templates.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0059/generate_0300.py [target]

With no argument the target is `definitions/x86_64/0.30.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.29.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.30.0.json"


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def register_slot(role: str) -> dict:
    """`REX.R = 1`: four bits, `%r8b`-`%r15b` only."""
    return {
        "role": role,
        "kind": "x86.gpr8",
        "target_type": "r8",
        "from": "reg_number",
        "excluded": [0, 1, 2, 3, 4, 5, 6, 7],
        "modifiers": [],
        "placements": [
            placement(2, 1),
            placement(19, 3),
        ],
    }


def base_slot() -> dict:
    """A plain base: `REX.B` at `[0,1]` plus `ModRM.rm` at `[16,3]`.

    `%rsp` and `%r12` need the `SIB` byte, so they are their own rows.
    """
    return {
        "role": "base",
        "kind": "x86.gpr64",
        "target_type": "rm64",
        "from": "reg_number",
        "excluded": [4, 12],
        "modifiers": [],
        "placements": [
            placement(0, 1),
            placement(16, 3),
        ],
    }


def disp_slot(bit_offset: int, bits: int) -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp%d" % bits,
        "from": "operand_value",
        "range": {"signed": True, "bits": bits, "align_bits": 0},
        "modifiers": [],
        "placements": [
            placement(bit_offset, bits),
        ],
    }


# (base window, displacement bits) -> (template stem, disp bit offset)
SHAPES = {
    ("base", 8): ("40", 24),
    ("base", 32): ("80", 24),
    ("rsp", 8): ("4424", 32),
    ("rsp", 32): ("8424", 32),
    ("r12", 8): ("4424", 32),
    ("r12", 32): ("8424", 32),
}

WINDOW_REX = {"base": "44", "rsp": "44", "r12": "45"}


def row(direction: str, window: str, bits: int) -> dict:
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "8a" if load else "88"
    stem, disp_offset = SHAPES[(window, bits)]

    # The store form names the register after the address, matching the family
    # (`abs32-r8`, `base-disp8-r8`, `rsp-disp8-r8`).
    if load:
        form_id = "x86:mov/r8-ext-%s-disp%d/legacy" % (window, bits)
    else:
        form_id = "x86:mov/%s-disp%d-r8-ext/legacy" % (window, bits)

    if bits == 8:
        template = WINDOW_REX[window] + opcode + stem + "00"
    else:
        template = WINDOW_REX[window] + opcode + stem + "00000000"

    slots = [register_slot(role)]
    if window == "base":
        slots.append(base_slot())
    slots.append(disp_slot(disp_offset, bits))
    return {"form_id": form_id, "template": template, "slots": slots}


NEW_FORMS = [
    row(direction, window, bits)
    for direction in ("load", "store")
    for window in ("base", "rsp", "r12")
    for bits in (8, 32)
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
               span["align_bits"])
        )
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
    if document["version"] != "0.29.0":
        raise SystemExit("source is not 0.29.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.29.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.29.0"', '"version": "0.30.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
