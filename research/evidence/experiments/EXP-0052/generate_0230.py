#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.23.0.json` from `0.22.0.json`.

One change (ADR-0050): eighteen `SIB` rows for the EVEX `vmovaps` memory
family with an index and a scale -- three widths x load/store x three
displacement shapes (none, `disp8*N`, `disp32`).

`r/m = 100` announces the `SIB` byte, so the base is an operand again instead
of a template byte. The base is `[48,3]` plus the inverted `B-bar` at
`[13,1]`, the index is `[51,3]` plus the inverted `X-bar` at `[14,1]`, and the
scale is the two bits at `[54,2]`. `mod = 00` drops the displacement slot; its
`SIB` base `101` means "no base", so the two bases whose low three bits are
`101` (`%rbp`, `%r13`) are excluded from that row only.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0052/generate_0230.py [target]

With no argument the target is `definitions/x86_64/0.23.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.22.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.23.0.json"

# width -> (the `P2` `L'L` byte, the `disp8*N` unit)
WIDTHS = {"xmm": ("08", 16), "ymm": ("28", 32), "zmm": ("48", 64)}

# (suffix, `ModRM`, displacement template hex, displacement shape)
SHAPES = [
    ("", "04", "", "none"),
    ("-disp8x", "44", "00", "compressed"),
    ("-disp32", "84", "00000000", "disp32"),
]


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


def base_slot(no_disp: bool) -> dict:
    """The `SIB` base: `[48,3]` plus the inverted `B-bar` at `[13,1]`."""
    slot = {
        "role": "base",
        "kind": "x86.gpr64",
        "target_type": "rm64",
        "from": "reg_number",
        "modifiers": [],
        "placements": [
            placement(13, 1, invert=True),
            placement(48, 3),
        ],
    }
    if no_disp:
        # `mod = 00` with `SIB.base = 101` is "no base, disp32".
        slot["excluded"] = [5, 13]
    return slot


def index_slot() -> dict:
    """The `SIB` index: `[51,3]` plus the inverted `X-bar` at `[14,1]`."""
    return {
        "role": "index",
        "kind": "x86.gpr64",
        "target_type": "sib_index",
        "from": "reg_number",
        "excluded": [4],
        "modifiers": [],
        "placements": [
            placement(14, 1, invert=True),
            placement(51, 3),
        ],
    }


def scale_slot() -> dict:
    """The two-bit `SIB` scale, carried as field content."""
    return {
        "role": "imm",
        "kind": "x86.scale",
        "target_type": "scale2",
        "from": "operand_value",
        "range": {"signed": False, "bits": 2, "align_bits": 0},
        "modifiers": [],
        "placements": [
            placement(54, 2),
        ],
    }


def disp_slot(kind: str) -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": kind,
        "from": "operand_value",
        "range": {"signed": True, "bits": 8 if kind != "disp32" else 32,
                  "align_bits": 0},
        "modifiers": [],
        "placements": [
            placement(56, 8 if kind != "disp32" else 32),
        ],
    }


def form(form_id: str, template: str, slots: list[dict]) -> dict:
    return {"form_id": form_id, "template": template, "slots": slots}


def row(direction: str, width: str, shape) -> dict:
    suffix, modrm, disp_hex, disp_shape = shape
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "28" if load else "29"
    unit = WIDTHS[width][1]
    shape_name = suffix if disp_shape != "compressed" else "-disp8x%d" % unit
    disp_kind = None
    if disp_shape == "compressed":
        disp_kind = "disp8x%d" % unit
    elif disp_shape == "disp32":
        disp_kind = "disp32"
    if load:
        form_id = "x86:vmovaps/%s-base-index%s/evex" % (width, shape_name)
    else:
        form_id = "x86:vmovaps/base-index%s-%s/evex" % (shape_name, width)
    template = "62f17c" + WIDTHS[width][0] + opcode + modrm + "00" + disp_hex

    slots = [vector_slot(role, width), base_slot(disp_kind is None),
             index_slot(), scale_slot()]
    if disp_kind is not None:
        slots.append(disp_slot(disp_kind))
    return form(form_id, template, slots)


NEW_FORMS = []
for _width in ("xmm", "ymm", "zmm"):
    for _direction in ("load", "store"):
        for _shape in SHAPES:
            NEW_FORMS.append(row(_direction, _width, _shape))

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"


def render_placements(placements: list[dict]) -> str:
    pieces = []
    for item in placements:
        text = '{ "bit_offset": %d, "width": %d' % (
            item["bit_offset"], item["width"])
        if item.get("invert"):
            text += ', "invert": true'
        pieces.append(text + " }")
    return "[" + ", ".join(pieces) + "]"


def render_slot(entry: dict) -> list[str]:
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


def render_body(forms: list[dict]) -> str:
    return ",\n".join(render_form(entry) for entry in forms)


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    text = SOURCE.read_text(encoding="utf-8")
    if not text.endswith(TAIL_MARKER):
        raise SystemExit("unexpected file tail")
    head, block = text.split(HEAD_MARKER, 1)
    body = block[: -len(TAIL_MARKER)]

    document = json.loads(text)
    if document["version"] != "0.22.0":
        raise SystemExit("source is not 0.22.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.22.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.22.0"', '"version": "0.23.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
