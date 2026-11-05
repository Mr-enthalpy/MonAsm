#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.14.0.json` from `0.13.0.json`.

The only differences are the `version` string and the five register-direct
`ymm`/`zmm` rows appended at the end of `forms` (ADR-0041). Formatting follows
the existing document so the diff stays reviewable; the canonical digest is
computed over sorted compact JSON, so formatting never moves it.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0043/generate_0140.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.13.0.json"
TARGET = ROOT / "definitions/x86_64/0.14.0.json"

LOW = [0, 1, 2, 3, 4, 5, 6, 7]


def slot(role: str, kind: str, target_type: str, placements: list[dict],
         excluded: list[int] | None = None) -> dict:
    entry = {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
    }
    if excluded is not None:
        entry["excluded"] = excluded
    entry["modifiers"] = []
    entry["placements"] = placements
    return entry


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def form(form_id: str, template: str, dest: dict, src: dict) -> dict:
    return {"form_id": form_id, "template": template, "slots": [dest, src]}


# VEX.256 mirror of the `0.11.0` `xmm` windows: the low/low row already carries
# `ModRM.reg`'s fourth bit in the inverted `R̄`; the high source moves to opcode
# 29 so it stays in a two-byte prefix; both-high needs the three-byte `C4`.
NEW_FORMS = [
    form(
        "x86:vmovaps/ymm-ymm/vex",
        "c5fc28c0",
        slot("dest", "x86.ymm", "ymm",
             [placement(15, 1, invert=True), placement(27, 3)]),
        slot("src", "x86.ymm", "ymm", [placement(24, 3)]),
    ),
    form(
        "x86:vmovaps/ymm-ymm-src-ext/vex",
        "c57c29c0",
        slot("dest", "x86.ymm", "ymm", [placement(24, 3)]),
        slot("src", "x86.ymm", "ymm",
             [placement(15, 1, invert=True), placement(27, 3)], excluded=LOW),
    ),
    form(
        "x86:vmovaps/ymm-ymm-both-ext/vex",
        "c4417c28c0",
        slot("dest", "x86.ymm", "ymm",
             [placement(15, 1, invert=True), placement(35, 3)], excluded=LOW),
        slot("src", "x86.ymm", "ymm",
             [placement(13, 1, invert=True), placement(32, 3)], excluded=LOW),
    ),
    # EVEX.256: the fifth register bit is `R̄'`/`X̄`, the same placement as
    # `0.13.0`; `L'L = 10` in the template is the width.
    form(
        "x86:vmovaps/ymm-ymm/evex",
        "62f17c2828c0",
        slot("dest", "x86.ymm", "ymm",
             [placement(12, 1, invert=True), placement(15, 1, invert=True),
              placement(43, 3)]),
        slot("src", "x86.ymm", "ymm",
             [placement(14, 1, invert=True), placement(13, 1, invert=True),
              placement(40, 3)]),
    ),
    # EVEX.512: `L'L = 11`. There is no VEX or legacy `zmm`.
    form(
        "x86:vmovaps/zmm-zmm/evex",
        "62f17c4828c0",
        slot("dest", "x86.zmm", "zmm",
             [placement(12, 1, invert=True), placement(15, 1, invert=True),
              placement(43, 3)]),
        slot("src", "x86.zmm", "zmm",
             [placement(14, 1, invert=True), placement(13, 1, invert=True),
              placement(40, 3)]),
    ),
]


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


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    document = json.loads(text)
    if document["version"] != "0.13.0":
        raise SystemExit("source is not 0.13.0")

    marker = "\n  ]\n}\n"
    if not text.endswith(marker):
        raise SystemExit("unexpected file tail")
    body = text[: -len(marker)]
    block = ",\n".join(render_form(entry) for entry in NEW_FORMS)
    updated = body + ",\n" + block + marker
    updated = updated.replace('"version": "0.13.0"', '"version": "0.14.0"', 1)
    with TARGET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(TARGET.read_text(encoding="utf-8"))
    print("%s: %d forms" % (TARGET.relative_to(ROOT).as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
