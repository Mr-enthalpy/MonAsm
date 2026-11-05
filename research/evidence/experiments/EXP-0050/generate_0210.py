#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.21.0.json` from `0.20.0.json`.

One change (ADR-0048): twenty-four fixed-base `SIB` rows for the EVEX
`vmovaps` memory family at `xmm`/`ymm`/`zmm` width, so `%rsp` and `%r12`
become legal bases there.

An EVEX memory row spends exactly one byte on the `SIB` (`r/m = 100`,
`SIB = 24`) and nothing on the base's fourth bit, which `P0` already carries as
the inverted `B̄` (`62 f1 ...` for `%rsp`, `62 d1 ...` for `%r12`). The prefix
does not grow, so the vector slot keeps its place at `[43,3]` and only the
displacement moves, from `[48,...]` to `[56,...]`. The two bases still need
separate rows because the `P0` byte is part of the template.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0050/generate_0210.py [target]

With no argument the target is `definitions/x86_64/0.21.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.20.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.21.0.json"

# width -> (P2 `L'L` byte, displacement unit, template target type)
WIDTHS = {
    "xmm": ("08", 16),
    "ymm": ("28", 32),
    "zmm": ("48", 64),
}


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


def disp_slot(target_type: str, bits: int, offset: int) -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": target_type,
        "from": "operand_value",
        "range": {"signed": True, "bits": bits, "align_bits": 0},
        "modifiers": [],
        "placements": [placement(offset, bits)],
    }


def form(form_id: str, template: str, slots: list[dict]) -> dict:
    return {"form_id": form_id, "template": template, "slots": slots}


def row(direction: str, width: str, base: str, bits: int) -> dict:
    """One fixed-base EVEX row.

    `bits = 8` uses the `disp8*N` target type for the width, `bits = 32` the
    plain `disp32`. The `SIB` byte is fixed in the template, so the row carries
    only the vector register and the displacement.
    """
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "28" if load else "29"
    prefix = "62d17c" if base == "r12" else "62f17c"
    ll = WIDTHS[width][0]
    unit = WIDTHS[width][1]
    if bits == 8:
        target_type = "disp8x%d" % unit
        modrm = "44"
        disp = "00"
        suffix = "disp8x%d" % unit
    else:
        target_type = "disp32"
        modrm = "84"
        disp = "00000000"
        suffix = "disp32"
    if load:
        form_id = "x86:vmovaps/%s-%s-%s/evex" % (width, base, suffix)
    else:
        form_id = "x86:vmovaps/%s-%s-%s/evex" % (base, suffix, width)
    return form(
        form_id,
        prefix + ll + opcode + modrm + "24" + disp,
        [vector_slot(role, width), disp_slot(target_type, bits, 56)],
    )


NEW_FORMS = []
for _width in ("xmm", "ymm", "zmm"):
    for _direction in ("load", "store"):
        for _base in ("rsp", "r12"):
            for _bits in (8, 32):
                NEW_FORMS.append(row(_direction, _width, _base, _bits))

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
    if document["version"] != "0.20.0":
        raise SystemExit("source is not 0.20.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.20.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.20.0"', '"version": "0.21.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
