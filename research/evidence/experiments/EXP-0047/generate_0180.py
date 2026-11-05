#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.18.0.json` from `0.17.0.json`.

Two changes (ADR-0045):

* Eight `-base-ext` rows appended, so the word and REX-less low-byte `mov`
  memory families reach `r8`-`r15`: the word rows put `REX.B` at bit 8 (after
  the `66` byte) and the byte rows at bit 0.
* The four `40`-prefixed byte rows widen their base from three bits to four in
  place. Their `REX` byte already exists, so the fourth bit is `[0,1]` and the
  template is unchanged; only the `excluded` list grows from `[4]` to `[4, 12]`.

Every extension row excludes the low bases (`0`-`7`) and `%r12`, so the two
windows are disjoint. `%rsp` (and `%r12` on the widened rows) stays out because
`mod = 01`/`10` with `r/m = 100` spends a `SIB` byte no `mov` row carries.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0047/generate_0180.py [target]

With no argument the target is `definitions/x86_64/0.18.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.17.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.18.0.json"

LOW_BASES = [0, 1, 2, 3, 4, 5, 6, 7]
# A high base is `8`-`15`; `%r12` is `12` and forces a SIB byte.
EXT_BASE_EXCLUDED = LOW_BASES + [12]
# The widened `40` rows keep bases 0-7 (same bytes as before) and lose `%rsp`
# and `%r12` to the SIB shape.
REX_BASE_EXCLUDED = [4, 12]
# The byte `-base-ext` rows carry the REX-less low set: numbers 4-7 with a REX
# byte are `spl`-`dil`, whose window is the widened `40` row.
LOW_BYTE_EXCLUDED = [4, 5, 6, 7]

REVISED_BASE_EXCLUDED = {
    "x86:mov/r8-base-disp8-rex/legacy": REX_BASE_EXCLUDED,
    "x86:mov/r8-base-disp32-rex/legacy": REX_BASE_EXCLUDED,
    "x86:mov/base-disp8-r8-rex/legacy": REX_BASE_EXCLUDED,
    "x86:mov/base-disp32-r8-rex/legacy": REX_BASE_EXCLUDED,
}


def placement(bit_offset: int, width: int) -> dict:
    return {"bit_offset": bit_offset, "width": width}


def reg_slot(role: str, kind: str, target_type: str, bit_offset: int,
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
    entry["placements"] = [placement(bit_offset, 3)]
    return entry


def base_ext_word_slot() -> dict:
    """`66 41 ...`: the `REX` byte is template byte 1, so `REX.B` is bit 8."""
    entry = reg_slot("base", "x86.gpr64", "rm64", 24,
                     excluded=EXT_BASE_EXCLUDED)
    entry["placements"] = [placement(8, 1), placement(24, 3)]
    return entry


def base_ext_byte_slot() -> dict:
    """`41 88 ...`: the `REX` byte is template byte 0, so `REX.B` is bit 0."""
    entry = reg_slot("base", "x86.gpr64", "rm64", 16,
                     excluded=EXT_BASE_EXCLUDED)
    entry["placements"] = [placement(0, 1), placement(16, 3)]
    return entry


def base_slot(bit_offset: int) -> dict:
    return reg_slot("base", "x86.gpr64", "rm64", bit_offset,
                    excluded=[4])


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


def form(form_id: str, template: str, slots: list[dict]) -> dict:
    return {"form_id": form_id, "template": template, "slots": slots}


# Order: word load `disp8`/`disp32`, word store `disp8`/`disp32`, then the
# REX-less low-byte load pair and store pair.
NEW_FORMS = [
    form("x86:mov/r16-base-ext-disp8/legacy", "66418b4000",
         [reg_slot("dest", "x86.gpr16", "r16", 27), base_ext_word_slot(),
          disp_slot(8, 32)]),
    form("x86:mov/r16-base-ext-disp32/legacy", "66418b8000000000",
         [reg_slot("dest", "x86.gpr16", "r16", 27), base_ext_word_slot(),
          disp_slot(32, 32)]),
    form("x86:mov/base-ext-disp8-r16/legacy", "6641894000",
         [reg_slot("src", "x86.gpr16", "r16", 27), base_ext_word_slot(),
          disp_slot(8, 32)]),
    form("x86:mov/base-ext-disp32-r16/legacy", "6641898000000000",
         [reg_slot("src", "x86.gpr16", "r16", 27), base_ext_word_slot(),
          disp_slot(32, 32)]),
    form("x86:mov/r8-base-ext-disp8/legacy", "418a4000",
         [reg_slot("dest", "x86.gpr8", "r8", 19,
                   excluded=LOW_BYTE_EXCLUDED), base_ext_byte_slot(),
          disp_slot(8, 24)]),
    form("x86:mov/r8-base-ext-disp32/legacy", "418a8000000000",
         [reg_slot("dest", "x86.gpr8", "r8", 19,
                   excluded=LOW_BYTE_EXCLUDED), base_ext_byte_slot(),
          disp_slot(32, 24)]),
    form("x86:mov/base-ext-disp8-r8/legacy", "41884000",
         [reg_slot("src", "x86.gpr8", "r8", 19,
                   excluded=LOW_BYTE_EXCLUDED), base_ext_byte_slot(),
          disp_slot(8, 24)]),
    form("x86:mov/base-ext-disp32-r8/legacy", "41888000000000",
         [reg_slot("src", "x86.gpr8", "r8", 19,
                   excluded=LOW_BYTE_EXCLUDED), base_ext_byte_slot(),
          disp_slot(32, 24)]),
]

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
    if document["version"] != "0.17.0":
        raise SystemExit("source is not 0.17.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the revision.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.17.0 forms block")

    forms = document["forms"]
    for entry in forms:
        excluded = REVISED_BASE_EXCLUDED.get(entry["form_id"])
        if excluded is None:
            continue
        base = [slot for slot in entry["slots"] if slot["role"] == "base"]
        if len(base) != 1 or base[0]["placements"] != [placement(16, 3)]:
            raise SystemExit("%s: unexpected base slot" % entry["form_id"])
        base[0]["placements"] = [placement(0, 1), placement(16, 3)]
        base[0]["excluded"] = excluded
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.17.0"', '"version": "0.18.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
