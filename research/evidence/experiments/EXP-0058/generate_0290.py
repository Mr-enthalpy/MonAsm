#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.29.0.json` from `0.28.0.json`.

One change (ADR-0056): eight `mov` rows for the 8-bit GPR family that carry a
32-bit absolute address -- load and store in each of the four byte-register
windows.

The low (`%al`-`%bl`) and high (`%ah`-`%bh`) windows have no `REX` byte, so the
opcode sits at `[0,8]`, `ModRM` at `[8,8]`, `SIB = 25` at `[16,8]` and the
address at `[24,32]`, seven bytes; the register is the three-bit `ModRM.reg`
at `[11,3]` and the two windows differ only in the template's register bits
(`04`-`1c` against `24`-`3c`). The `REX = 40` window is the same shape one
byte later -- `REX` at `[0,8]`, opcode at `[8,8]`, `ModRM` at `[16,8]`, the
register at `[19,3]`, `SIB` at `[24,8]`, address at `[32,32]`, eight bytes --
and holds only registers `4`-`7`, the numbers the `REX` byte relabels to
`%spl`-`%dil`. The `REX = 44` window is the same eight bytes with `REX.R = 1`,
so the register is `[19,3]` plus `REX.R` at `[2,1]` and the row reaches
`%r8b`-`%r15b` only.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0058/generate_0290.py [target]

With no argument the target is `definitions/x86_64/0.29.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.28.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.29.0.json"


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def plain_register_slot(role: str, kind: str, target_type: str) -> dict:
    """The three-bit `ModRM.reg` field of a row with no `REX` byte."""
    excluded = [4, 5, 6, 7] if kind == "x86.gpr8" else [0, 1, 2, 3]
    return {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
        "excluded": excluded,
        "modifiers": [],
        "placements": [
            placement(11, 3),
        ],
    }


def rex_register_slot(role: str) -> dict:
    """`REX = 40`: the three-bit field names `%spl`-`%dil` only."""
    return {
        "role": role,
        "kind": "x86.gpr8",
        "target_type": "r8",
        "from": "reg_number",
        "excluded": [0, 1, 2, 3],
        "modifiers": [],
        "placements": [
            placement(19, 3),
        ],
    }


def ext_register_slot(role: str) -> dict:
    """`REX = 44`: four bits, `%r8b`-`%r15b` only."""
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
    role = "dest" if load else "src"
    opcode = "8a" if load else "88"
    # The store form's id names the register after the address, matching the
    # wider rows (`abs32-r8`); the load form's names it first.
    if load:
        stem = {"low": "r8", "high": "r8h",
                "rex": "r8-rex", "ext": "r8-ext"}[window]
        form_id = "x86:mov/%s-abs32/legacy" % stem
    else:
        stem = {"low": "r8", "high": "r8h",
                "rex": "r8-rex", "ext": "r8-ext"}[window]
        form_id = "x86:mov/abs32-%s/legacy" % stem

    if window == "low":
        template = opcode + "04" + "25" + "00000000"
        slots = [plain_register_slot(role, "x86.gpr8", "r8"), abs_slot(24)]
    elif window == "high":
        template = opcode + "24" + "25" + "00000000"
        slots = [plain_register_slot(role, "x86.gpr8h", "r8h"), abs_slot(24)]
    elif window == "rex":
        template = "40" + opcode + "24" + "25" + "00000000"
        slots = [rex_register_slot(role), abs_slot(32)]
    else:
        template = "44" + opcode + "04" + "25" + "00000000"
        slots = [ext_register_slot(role), abs_slot(32)]
    return {"form_id": form_id, "template": template, "slots": slots}


NEW_FORMS = [
    row(direction, window)
    for direction in ("load", "store")
    for window in ("low", "high", "rex", "ext")
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
    if document["version"] != "0.28.0":
        raise SystemExit("source is not 0.28.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.28.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.28.0"', '"version": "0.29.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
