#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.19.0.json` from `0.18.0.json`.

One change (ADR-0046): twenty-eight fixed-base `SIB` rows for the 8/16-bit
`mov` memory families, so `%rsp` and `%r12` become legal bases.

A `%rsp` or `%r12` base spends a `SIB` byte after the `ModRM` (`r/m = 100`)
and, for `%r12`, `REX.B = 1`. Both change the instruction length relative to
the `-base-disp*` rows, so the pair is a form of its own: the base is fixed in
the template and the row carries only the register and the displacement, the
same shape `0.3.0`/`0.7.0` gave the 64-bit rows. The high-byte family gets only
the `%rsp` rows, because `movb %ah, 8(%r12)` has no encoding at all.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0048/generate_0190.py [target]

With no argument the target is `definitions/x86_64/0.19.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.18.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.19.0.json"

# The byte register partitions 0.4.0 fixed: numbers 0-3 are the REX-less low
# set, 4-7 without `REX` are the high set, and 4-7 with `REX` are `spl`-`dil`.
LOW_BYTE_EXCLUDED = [4, 5, 6, 7]
HIGH_BYTE_EXCLUDED = [0, 1, 2, 3]


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


def word_pair(direction: str, base: str) -> list[dict]:
    """`66 8b`/`66 89`, `r/m = 100`, `SIB = 24`, `REX.B` only for `%r12`.

    The `66` byte and a possible `REX` byte both precede the `ModRM`, so the
    register and displacement move with them: bits 19/32 on the `%rsp` rows and
    27/40 on the `%r12` rows, exactly as `0.18.0`'s `-base-ext` word rows.
    """
    load = direction == "load"
    prefix = "6641" if base == "r12" else "66"
    opcode = "8b" if load else "89"
    role = "dest" if load else "src"
    shift = 8 if base == "r12" else 0
    reg = reg_slot(role, "x86.gpr16", "r16", 19 + shift)
    forms = []
    for bits in (8, 32):
        modrm = "44" if bits == 8 else "84"
        disp = "00" if bits == 8 else "00000000"
        if load:
            form_id = "x86:mov/r16-%s-disp%d/legacy" % (base, bits)
        else:
            form_id = "x86:mov/%s-disp%d-r16/legacy" % (base, bits)
        forms.append(form(form_id, prefix + opcode + modrm + "24" + disp,
                          [dict(reg), disp_slot(bits, 32 + shift)]))
    return forms


def byte_pair(direction: str, base: str, family: str) -> list[dict]:
    """`8a`/`88` at the three register sets, `r/m = 100`, `SIB = 24`.

    `family` is `low` (numbers 0-3, no `REX`), `high` (4-7, no `REX`) or
    `rex` (4-7 behind a `40`/`41` byte). Every row spends the `SIB` byte, and a
    `REX` byte in the template shifts `ModRM` and the displacement by eight
    bits: the `%r12` low-byte rows and both `40` rows sit at 19/32, while the
    REX-less `%rsp` rows sit at 11/24.
    """
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "8a" if load else "88"
    if family == "low":
        prefix = "41" if base == "r12" else ""
        kind, target = "x86.gpr8", "r8"
        excluded = LOW_BYTE_EXCLUDED
        suffix = ""
    elif family == "high":
        prefix = ""
        kind, target = "x86.gpr8h", "r8h"
        excluded = HIGH_BYTE_EXCLUDED
        suffix = ""
    else:
        prefix = "41" if base == "r12" else "40"
        kind, target = "x86.gpr8", "r8"
        excluded = HIGH_BYTE_EXCLUDED
        suffix = "-rex"
    shift = 8 if prefix else 0
    reg = reg_slot(role, kind, target, 11 + shift, excluded=excluded)
    # The template's `ModRM.reg` sits inside the row's own window: 0 for the
    # REX-less low set, 4 for the high set and the `40` rows.
    reg_field = "4" if family == "low" else "6"
    forms = []
    for bits in (8, 32):
        modrm = "%02x" % ((0x40 if bits == 8 else 0x80)
                          | (0 if family == "low" else 0x20) | 4)
        disp = "00" if bits == 8 else "00000000"
        if load:
            form_id = "x86:mov/%s-%s-disp%d%s/legacy" % (target, base, bits, suffix)
        else:
            form_id = "x86:mov/%s-disp%d-%s%s/legacy" % (base, bits, target, suffix)
        forms.append(form(form_id, prefix + opcode + modrm + "24" + disp,
                          [dict(reg), disp_slot(bits, 24 + shift)]))
    return forms


NEW_FORMS = (
    word_pair("load", "rsp") + word_pair("load", "r12")
    + word_pair("store", "rsp") + word_pair("store", "r12")
    + byte_pair("load", "rsp", "low") + byte_pair("load", "r12", "low")
    + byte_pair("store", "rsp", "low") + byte_pair("store", "r12", "low")
    + byte_pair("load", "rsp", "high") + byte_pair("store", "rsp", "high")
    + byte_pair("load", "rsp", "rex") + byte_pair("load", "r12", "rex")
    + byte_pair("store", "rsp", "rex") + byte_pair("store", "r12", "rex")
)

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
    if document["version"] != "0.18.0":
        raise SystemExit("source is not 0.18.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.18.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.18.0"', '"version": "0.19.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
