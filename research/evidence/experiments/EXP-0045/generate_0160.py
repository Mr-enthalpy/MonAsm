#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.16.0.json` from `0.15.0.json`.

The only differences are the `version` string and the twelve VEX.256 memory
rows appended at the end of `forms` (ADR-0043). Each new row repeats one of the
twelve `0.11.0`/`0.12.0` VEX memory shapes with `L = 1`: the low-base rows use
`C5 FC` instead of `C5 F8`, the high-base rows use `C4 C1 7C` instead of
`C4 C1 78`, and the vector slot's kind/target_type become `ymm`. Placements,
base windows and exclusions are unchanged, so VEX.256 memory adds coverage and
no `EC` fact.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0045/generate_0160.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.15.0.json"
TARGET = ROOT / "definitions/x86_64/0.16.0.json"

# The `disp` rows cannot use `%rsp`/`%r12` (they need a SIB byte); the no-disp
# rows add `%rbp`/`%r13`, which `mod=00` would spend on the RIP-relative escape.
LOW_DISP_EXCLUDED = [4]
LOW_NO_DISP_EXCLUDED = [4, 5]
HIGH_DISP_EXCLUDED = [0, 1, 2, 3, 4, 5, 6, 7, 12]
HIGH_NO_DISP_EXCLUDED = [12, 13]


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


def disp_slot(bits: int, offset: int) -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp%d" % bits,
        "from": "operand_value",
        "range": {"signed": True, "bits": bits, "align_bits": 0},
        "modifiers": [],
        "placements": [placement(offset, bits)],
    }


def low_vector_slot(role: str) -> dict:
    """Two-byte VEX: `R̄` at 15, `ModRM.reg` at 27, base at `ModRM.rm`."""
    return reg_slot(role, "x86.ymm", "ymm",
                    [placement(15, 1, invert=True), placement(27, 3)])


def high_vector_slot(role: str) -> dict:
    """Three-byte VEX: `R̄` at 15, `ModRM.reg` at 35 (one byte later)."""
    return reg_slot(role, "x86.ymm", "ymm",
                    [placement(15, 1, invert=True), placement(35, 3)])


def low_base_slot(excluded: list[int]) -> dict:
    """Two-byte VEX has no `B̄`: the base is the three low `ModRM.rm` bits."""
    return reg_slot("base", "x86.gpr64", "rm64",
                    [placement(24, 3)], excluded=excluded)


def high_base_slot(excluded: list[int]) -> dict:
    """Three-byte VEX: `B̄` at 13, the low three `ModRM.rm` bits at 32."""
    return reg_slot("base", "x86.gpr64", "rm64",
                    [placement(13, 1, invert=True), placement(32, 3)],
                    excluded=excluded)


def form(form_id: str, template: str, slots: list[dict]) -> dict:
    return {"form_id": form_id, "template": template, "slots": slots}


NEW_FORMS = [
    # Two-byte `C5 FC ...`: base in `ModRM.rm`, no extension bit.
    form("x86:vmovaps/ymm-base-disp8/vex", "c5fc284000",
         [low_vector_slot("dest"), low_base_slot(LOW_DISP_EXCLUDED),
          disp_slot(8, 32)]),
    form("x86:vmovaps/ymm-base-disp32/vex", "c5fc288000000000",
         [low_vector_slot("dest"), low_base_slot(LOW_DISP_EXCLUDED),
          disp_slot(32, 32)]),
    form("x86:vmovaps/base-disp8-ymm/vex", "c5fc294000",
         [low_vector_slot("src"), low_base_slot(LOW_DISP_EXCLUDED),
          disp_slot(8, 32)]),
    form("x86:vmovaps/base-disp32-ymm/vex", "c5fc298000000000",
         [low_vector_slot("src"), low_base_slot(LOW_DISP_EXCLUDED),
          disp_slot(32, 32)]),
    # Three-byte `C4 C1 7C ...`: `B̄` extends the base and `ModRM` moves one byte.
    form("x86:vmovaps/ymm-base-ext-disp8/vex", "c4c17c284000",
         [high_vector_slot("dest"), high_base_slot(HIGH_DISP_EXCLUDED),
          disp_slot(8, 40)]),
    form("x86:vmovaps/ymm-base-ext-disp32/vex", "c4c17c288000000000",
         [high_vector_slot("dest"), high_base_slot(HIGH_DISP_EXCLUDED),
          disp_slot(32, 40)]),
    form("x86:vmovaps/base-ext-disp8-ymm/vex", "c4c17c294000",
         [high_vector_slot("src"), high_base_slot(HIGH_DISP_EXCLUDED),
          disp_slot(8, 40)]),
    form("x86:vmovaps/base-ext-disp32-ymm/vex", "c4c17c298000000000",
         [high_vector_slot("src"), high_base_slot(HIGH_DISP_EXCLUDED),
          disp_slot(32, 40)]),
    # No displacement: `mod = 00`.
    form("x86:vmovaps/ymm-base/vex", "c5fc2800",
         [low_vector_slot("dest"), low_base_slot(LOW_NO_DISP_EXCLUDED)]),
    form("x86:vmovaps/base-ymm/vex", "c5fc2900",
         [low_vector_slot("src"), low_base_slot(LOW_NO_DISP_EXCLUDED)]),
    form("x86:vmovaps/ymm-base-ext/vex", "c4c17c2800",
         [high_vector_slot("dest"), high_base_slot(HIGH_NO_DISP_EXCLUDED)]),
    form("x86:vmovaps/base-ext-ymm/vex", "c4c17c2900",
         [high_vector_slot("src"), high_base_slot(HIGH_NO_DISP_EXCLUDED)]),
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
    if document["version"] != "0.15.0":
        raise SystemExit("source is not 0.15.0")

    marker = "\n  ]\n}\n"
    if not text.endswith(marker):
        raise SystemExit("unexpected file tail")
    body = text[: -len(marker)]
    block = ",\n".join(render_form(entry) for entry in NEW_FORMS)
    updated = body + ",\n" + block + marker
    updated = updated.replace('"version": "0.15.0"', '"version": "0.16.0"', 1)
    with TARGET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(TARGET.read_text(encoding="utf-8"))
    print("%s: %d forms" % (TARGET.relative_to(ROOT).as_posix(),
                            len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
