#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.26.0.json` from `0.25.0.json`.

One change (ADR-0053): two `mov` rows for the 64-bit GPR family that carry a
32-bit absolute address -- load and store.

`ModRM` is `04` (`mod = 00`, `r/m = 100`) and the `SIB` byte is the constant
`25`: scale `00`, index `100` ("no index") and base `101` ("no base, `disp32`").
The address sits at `[32,32]` because the `REX.W` byte and the two opcode bytes
put `ModRM` at 16-23 and the `SIB` at 24-31. `moffs` (`A0`-`A3`) is not a row:
`EC-05` is frozen with the `form variant` carrier.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0055/generate_0260.py [target]

With no argument the target is `definitions/x86_64/0.26.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.25.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.26.0.json"


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def register_slot(role: str) -> dict:
    """The four-bit `x86.gpr64` register: `REX.R` plus `ModRM.reg`, raw."""
    return {
        "role": role,
        "kind": "x86.gpr64",
        "target_type": "r64",
        "from": "reg_number",
        "modifiers": [],
        "placements": [
            placement(2, 1),
            placement(19, 3),
        ],
    }


def abs_slot() -> dict:
    """The mandatory signed 32-bit absolute address at `[32,32]`."""
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp32",
        "from": "operand_value",
        "range": {"signed": True, "bits": 32, "align_bits": 0},
        "modifiers": [],
        "placements": [
            placement(32, 32),
        ],
    }


def row(direction: str) -> dict:
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "8b" if load else "89"
    if load:
        form_id = "x86:mov/r64-abs32/legacy"
    else:
        form_id = "x86:mov/abs32-r64/legacy"
    # `48 <opcode> 04 25 00 00 00 00`: `REX.W`, the `SIB` escape, the constant
    # `SIB`, and the four-byte address.
    template = "48" + opcode + "04" + "25" + "00000000"
    return {"form_id": form_id, "template": template,
            "slots": [register_slot(role), abs_slot()]}


NEW_FORMS = [row(_direction) for _direction in ("load", "store")]

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
    if document["version"] != "0.25.0":
        raise SystemExit("source is not 0.25.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.25.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.25.0"', '"version": "0.26.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
