#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.25.0.json` from `0.24.0.json`.

One change (ADR-0052): six `SIB` rows for the EVEX `vmovaps` memory family that
carry a 32-bit absolute address -- three widths x load/store.

`ModRM` is `04` (`mod = 00`, `r/m = 100`) and the `SIB` byte is the constant
`25`: scale `00`, index `100` ("no index") and base `101` ("no base, `disp32`").
Both register fields are template bits, so the row has no `base`, `index` or
`scale` slot, and the operand sequence is `dest`/`src` plus the mandatory
signed 32-bit address at `[56,32]`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0054/generate_0250.py [target]

With no argument the target is `definitions/x86_64/0.25.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.24.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.25.0.json"

# width -> the `P2` `L'L` byte
WIDTHS = {"xmm": "08", "ymm": "28", "zmm": "48"}


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def vector_slot(role: str, kind: str) -> dict:
    """The five-bit EVEX vector field at `[43,3]` plus the inverted extensions."""
    return {
        "role": role,
        "kind": "x86.%s" % kind,
        "target_type": kind,
        "from": "reg_number",
        "modifiers": [],
        "placements": [
            placement(12, 1, invert=True),
            placement(15, 1, invert=True),
            placement(43, 3),
        ],
    }


def abs_slot() -> dict:
    """The mandatory signed 32-bit absolute address at `[56,32]`."""
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp32",
        "from": "operand_value",
        "range": {"signed": True, "bits": 32, "align_bits": 0},
        "modifiers": [],
        "placements": [
            placement(56, 32),
        ],
    }


def form(form_id: str, template: str, slots: list) -> dict:
    return {"form_id": form_id, "template": template, "slots": slots}


def row(direction: str, width: str) -> dict:
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "28" if load else "29"
    if load:
        form_id = "x86:vmovaps/%s-abs32/evex" % width
    else:
        form_id = "x86:vmovaps/abs32-%s/evex" % width
    # `62 f1 7c <L'L> <opcode> 04 25 00 00 00 00`: `ModRM` is the `SIB` escape,
    # the `SIB` byte spends both register fields on constants, and the address
    # is always four bytes.
    template = "62f17c" + WIDTHS[width] + opcode + "04" + "25" + "00000000"
    return form(form_id, template, [vector_slot(role, width), abs_slot()])


NEW_FORMS = [row(_direction, _width)
             for _width in ("xmm", "ymm", "zmm")
             for _direction in ("load", "store")]

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
    if document["version"] != "0.24.0":
        raise SystemExit("source is not 0.24.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.24.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.24.0"', '"version": "0.25.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
