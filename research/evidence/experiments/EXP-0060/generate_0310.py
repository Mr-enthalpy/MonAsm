#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.31.0.json` from `0.30.0.json`.

One change (ADR-0058): eight `mov` rows bring the `mod = 00`
no-displacement shape to the byte-width memory family. Every other reachable
family already carries it -- the SSE rows since `0.12.0`, the EVEX rows since
`0.22.0` -- and `EC-02` freezes it as a third legal encoding rather than a zero
value.

The plain-base rows are the shortest byte encodings at two or three bytes:
`8a 00` (opcode plus `ModRM` with `mod = 00`), and the row is chosen by the
plan's `form_id`, never by a missing operand. The base slot excludes four
values: `4` (`%rsp`) and `12` (`%r12`) would force a `SIB` byte the template
does not carry, and `5` (`%rbp`) and `13` (`%r13`) collide with the
`r/m = 101` RIP-relative meaning of `mod = 00`, so `llvm-mc` writes those two
bases as `mod = 01` with a zero displacement byte.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0060/generate_0310.py [target]

With no argument the target is `definitions/x86_64/0.31.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.30.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.31.0.json"


def placement(bit_offset: int, width: int) -> dict:
    return {"bit_offset": bit_offset, "width": width}


def reg_slot(role: str, kind: str, target_type: str, placements: list,
             excluded: list) -> dict:
    return {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
        "excluded": excluded,
        "modifiers": [],
        "placements": placements,
    }


def base3_slot(modrm_bit: int):
    """A three-bit base: `r/m` only, with the two `mod = 00` collisions.

    `modrm_bit` is the bit offset of the `ModRM` byte, so `r/m` is its low
    three bits: 8 for a two-byte row (opcode then `ModRM`) and 16 for a
    three-byte row (`REX`, opcode, then `ModRM`).
    """
    def build() -> dict:
        return reg_slot("base", "x86.gpr64", "rm64",
                        [placement(modrm_bit, 3)], [4, 5])
    return build


def base4_slot(modrm_bit: int):
    """A four-bit base: `REX.B` at `[0,1]` plus `r/m` at the `ModRM` byte.

    `4`/`12` need the `SIB` byte and `5`/`13` are the RIP-relative value at
    `mod = 00`.
    """
    def build() -> dict:
        return reg_slot("base", "x86.gpr64", "rm64",
                        [placement(0, 1), placement(modrm_bit, 3)],
                        [4, 5, 12, 13])
    return build


LOW = [4, 5, 6, 7]
HIGH = [0, 1, 2, 3]
EXT = [0, 1, 2, 3, 4, 5, 6, 7]

# (direction, load id, store id, template, register slot, base slot)
ROWS = [
    ("load", "x86:mov/r8-base/legacy", None, "8a00",
     lambda role: reg_slot(role, "x86.gpr8", "r8", [placement(11, 3)], LOW),
     base3_slot(8)),
    ("store", None, "x86:mov/base-r8/legacy", "8800",
     lambda role: reg_slot(role, "x86.gpr8", "r8", [placement(11, 3)], LOW),
     base3_slot(8)),
    ("load", "x86:mov/r8h-base/legacy", None, "8a20",
     lambda role: reg_slot(role, "x86.gpr8h", "r8h", [placement(11, 3)], HIGH),
     base3_slot(8)),
    ("store", None, "x86:mov/base-r8h/legacy", "8820",
     lambda role: reg_slot(role, "x86.gpr8h", "r8h", [placement(11, 3)], HIGH),
     base3_slot(8)),
    ("load", "x86:mov/r8-base-rex/legacy", None, "408a20",
     lambda role: reg_slot(role, "x86.gpr8", "r8", [placement(19, 3)], HIGH),
     base4_slot(16)),
    ("store", None, "x86:mov/base-r8-rex/legacy", "408820",
     lambda role: reg_slot(role, "x86.gpr8", "r8", [placement(19, 3)], HIGH),
     base4_slot(16)),
    ("load", "x86:mov/r8-ext-base/legacy", None, "448a00",
     lambda role: reg_slot(role, "x86.gpr8", "r8",
                           [placement(2, 1), placement(19, 3)], EXT),
     base4_slot(16)),
    ("store", None, "x86:mov/base-r8-ext/legacy", "448800",
     lambda role: reg_slot(role, "x86.gpr8", "r8",
                           [placement(2, 1), placement(19, 3)], EXT),
     base4_slot(16)),
]


def form_of(direction: str, load_id: str, store_id: str, template: str,
            reg, base) -> dict:
    load = direction == "load"
    form_id = load_id if load else store_id
    reg_role = "dest" if load else "src"
    return {"form_id": form_id, "template": template,
            "slots": [reg(reg_role), base()]}


NEW_FORMS = [
    form_of(direction, load_id, store_id, template, reg, base)
    for direction, load_id, store_id, template, reg, base in ROWS
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
    if document["version"] != "0.30.0":
        raise SystemExit("source is not 0.30.0")
    # The renderer must reproduce the source byte for byte before it is
    # trusted with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.30.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.30.0"', '"version": "0.31.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
