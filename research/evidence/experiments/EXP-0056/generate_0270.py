#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.27.0.json` from `0.26.0.json`.

One change (ADR-0054): four `mov` rows for the 32-bit GPR family that carry a
32-bit absolute address -- load and store, each in the low register window and
in the extended window.

The low rows have no `REX` byte: `ModRM = 04` at bits 8-15, `SIB = 25` at
16-23 and the address at `[24,32]`, seven bytes. The extended rows spend one
byte on `REX = 44` (`REX.R = 1`, `REX.W = 0`), so `ModRM` moves to 16-23, `SIB`
to 24-31 and the address to `[32,32]`, eight bytes. `SIB = 25` is again the
absolute request: scale `00`, index `100` ("no index") and base `101`
("no base, `disp32`").

Usage (from the repository root):

    python research/evidence/experiments/EXP-0056/generate_0270.py [target]

With no argument the target is `definitions/x86_64/0.27.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.26.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.27.0.json"


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def low_register_slot(role: str) -> dict:
    """The three-bit `ModRM.reg` field: `%eax`-`%edi`, no `REX` byte."""
    return {
        "role": role,
        "kind": "x86.gpr32",
        "target_type": "r32",
        "from": "reg_number",
        "modifiers": [],
        "placements": [
            placement(11, 3),
        ],
    }


def ext_register_slot(role: str) -> dict:
    """The four-bit `ModRM.reg` plus `REX.R` window: `%r8d`-`%r15d` only."""
    return {
        "role": role,
        "kind": "x86.gpr32",
        "target_type": "r32",
        "from": "reg_number",
        "excluded": [0, 1, 2, 3, 4, 5, 6, 7],
        "modifiers": [],
        "placements": [
            placement(2, 1),
            placement(19, 3),
        ],
    }


def abs_slot(bit_offset: int) -> dict:
    """The mandatory signed 32-bit absolute address."""
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp32",
        "from": "operand_value",
        "range": {"signed": True, "bits": 32, "align_bits": 0},
        "modifiers": [],
        "placements": [
            placement(bit_offset, 32),
        ],
    }


def row(direction: str, window: str) -> dict:
    load = direction == "load"
    ext = window == "ext"
    role = "dest" if load else "src"
    opcode = "8b" if load else "89"
    if load:
        form_id = "x86:mov/r32-ext-abs32/legacy" if ext else \
            "x86:mov/r32-abs32/legacy"
    else:
        form_id = "x86:mov/abs32-r32-ext/legacy" if ext else \
            "x86:mov/abs32-r32/legacy"
    # `<44> <opcode> 04 25 00 00 00 00`: the optional REX byte, the `SIB`
    # escape, the constant `SIB`, and the four-byte address.
    template = ("44" if ext else "") + opcode + "04" + "25" + "00000000"
    return {"form_id": form_id, "template": template,
            "slots": [ext_register_slot(role) if ext
                      else low_register_slot(role),
                      abs_slot(32 if ext else 24)]}


NEW_FORMS = [
    row(direction, window)
    for direction in ("load", "store")
    for window in ("low", "ext")
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
    if document["version"] != "0.26.0":
        raise SystemExit("source is not 0.26.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.26.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.26.0"', '"version": "0.27.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
