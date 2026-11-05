#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.15.0.json` from `0.14.0.json`.

The only differences are the `version` string and the twelve EVEX memory rows
appended at the end of `forms` (ADR-0042). Every new row repeats one of the six
`0.13.0` `xmm` memory shapes with `P2 = 28` (`ymm`) or `P2 = 48` (`zmm`); the
compressed displacement unit is named by the slot's `target_type`
(`disp8x32` / `disp8x64`) and its value is the field content, as `disp8x16`
already is. Formatting follows the existing document so the diff stays
reviewable; the canonical digest is computed over sorted compact JSON, so
formatting never moves it.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0044/generate_0150.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.14.0.json"
TARGET = ROOT / "definitions/x86_64/0.15.0.json"

# The `disp` rows cannot use `%rsp`/`%r12` (they need a SIB byte); the no-disp
# rows add `%rbp`/`%r13`, which `mod=00` would spend on the RIP-relative escape.
DISP_EXCLUDED = [4, 12]
NO_DISP_EXCLUDED = [4, 5, 12, 13]


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def reg_slot(role: str, kind: str, target_type: str,
             placements: list[dict],
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


def disp8_slot(unit: int) -> dict:
    """`disp8*N`: the payload is the 8-bit field content, `N` names the unit."""
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp8x%d" % unit,
        "from": "operand_value",
        "range": {"signed": True, "bits": 8, "align_bits": 0},
        "modifiers": [],
        "placements": [placement(48, 8)],
    }


def disp32_slot() -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp32",
        "from": "operand_value",
        "range": {"signed": True, "bits": 32, "align_bits": 0},
        "modifiers": [],
        "placements": [placement(48, 32)],
    }


def vector_slot(role: str, width: str) -> dict:
    """The five-bit EVEX operand of `0.13.0`: `R?'` at 12, `R?` at 15, reg at 43."""
    return reg_slot(
        role,
        "x86.%s" % width,
        width,
        [placement(12, 1, invert=True), placement(15, 1, invert=True),
         placement(43, 3)],
    )


def base_slot(excluded: list[int]) -> dict:
    return reg_slot("base", "x86.gpr64", "rm64",
                    [placement(13, 1, invert=True), placement(40, 3)],
                    excluded=excluded)


def form(form_id: str, template: str, slots: list[dict]) -> dict:
    return {"form_id": form_id, "template": template, "slots": slots}


def memory_rows(width: str, p2: str, unit: int) -> list[dict]:
    """The six `xmm` memory shapes at one EVEX width (`ADR-0042`)."""
    prefix = "62f17c%s" % p2
    load = "28"
    store = "29"
    return [
        # disp8*N, load then store: `mod=01`, `r/m=base`, content at [48,8].
        form(
            "x86:vmovaps/%s-base-disp8x%d/evex" % (width, unit),
            prefix + load + "4000",
            [vector_slot("dest", width), base_slot(DISP_EXCLUDED),
             disp8_slot(unit)],
        ),
        # disp32, load then store: `mod=10`, displacement at [48,32].
        form(
            "x86:vmovaps/%s-base-disp32/evex" % width,
            prefix + load + "8000000000",
            [vector_slot("dest", width), base_slot(DISP_EXCLUDED),
             disp32_slot()],
        ),
        form(
            "x86:vmovaps/base-disp8x%d-%s/evex" % (unit, width),
            prefix + store + "4000",
            [vector_slot("src", width), base_slot(DISP_EXCLUDED),
             disp8_slot(unit)],
        ),
        form(
            "x86:vmovaps/base-disp32-%s/evex" % width,
            prefix + store + "8000000000",
            [vector_slot("src", width), base_slot(DISP_EXCLUDED),
             disp32_slot()],
        ),
        # No displacement: `mod=00`, `r/m=base`.
        form(
            "x86:vmovaps/%s-base/evex" % width,
            prefix + load + "00",
            [vector_slot("dest", width), base_slot(NO_DISP_EXCLUDED)],
        ),
        form(
            "x86:vmovaps/base-%s/evex" % width,
            prefix + store + "00",
            [vector_slot("src", width), base_slot(NO_DISP_EXCLUDED)],
        ),
    ]


NEW_FORMS = memory_rows("ymm", "28", 32) + memory_rows("zmm", "48", 64)


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


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    document = json.loads(text)
    if document["version"] != "0.14.0":
        raise SystemExit("source is not 0.14.0")

    marker = "\n  ]\n}\n"
    if not text.endswith(marker):
        raise SystemExit("unexpected file tail")
    body = text[: -len(marker)]
    block = ",\n".join(render_form(entry) for entry in NEW_FORMS)
    updated = body + ",\n" + block + marker
    updated = updated.replace('"version": "0.14.0"', '"version": "0.15.0"', 1)
    with TARGET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(TARGET.read_text(encoding="utf-8"))
    print("%s: %d forms" % (TARGET.relative_to(ROOT).as_posix(),
                            len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
