#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.20.0.json` from `0.19.0.json`.

One change (ADR-0047): sixteen fixed-base `SIB` rows for the legacy `movaps`
and the two-byte/three-byte VEX `vmovaps` memory families at `xmm` width, so
`%rsp` and `%r12` become legal bases there.

A `%rsp` base spends a `SIB` byte after the `ModRM` (`r/m = 100`) and `%r12`
spends `REX.B` as well in the legacy family; in the VEX family `%r12` forces the
three-byte prefix. Both change the instruction length relative to the
`-base-disp*` rows, so the pair is a form of its own: the base is fixed in the
template and the row carries only the register and the displacement, the same
shape `0.3.0`/`0.7.0` gave the 64-bit rows.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0049/generate_0200.py [target]

With no argument the target is `definitions/x86_64/0.20.0.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.19.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.20.0.json"


def placement(bit_offset: int, width: int, invert: bool = False) -> dict:
    entry = {"bit_offset": bit_offset, "width": width}
    if invert:
        entry["invert"] = True
    return entry


def xmm_slot(role: str, bit_offset: int, vex: bool) -> dict:
    """The register field, with the VEX `R` bit inversion `0.10.0` added."""
    placements = []
    if vex:
        placements.append(placement(15, 1, invert=True))
    placements.append(placement(bit_offset, 3))
    return {
        "role": role,
        "kind": "x86.xmm",
        "target_type": "xmm",
        "from": "reg_number",
        "modifiers": [],
        "placements": placements,
    }


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


def legacy_pair(direction: str, base: str) -> list[dict]:
    """`0f 28`/`0f 29`, `r/m = 100`, `SIB = 24`, `41` only for `%r12`.

    The optional `REX` byte precedes the `ModRM`, so the register and the
    displacement move with it: bits 19/32 on the `%rsp` rows and 27/40 on the
    `%r12` rows.
    """
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "28" if load else "29"
    prefix = "41" if base == "r12" else ""
    shift = 8 if base == "r12" else 0
    reg = xmm_slot(role, 19 + shift, vex=False)
    forms = []
    for bits in (8, 32):
        modrm = "44" if bits == 8 else "84"
        disp = "00" if bits == 8 else "00000000"
        if load:
            form_id = "x86:movaps/xmm-%s-disp%d/legacy" % (base, bits)
        else:
            form_id = "x86:movaps/%s-disp%d-xmm/legacy" % (base, bits)
        forms.append(form(form_id, prefix + "0f" + opcode + modrm + "24" + disp,
                          [dict(reg, placements=[dict(p) for p in reg["placements"]]),
                           disp_slot(bits, 32 + shift)]))
    return forms


def vex_pair(direction: str, base: str) -> list[dict]:
    """`c5 f8`/`c5 fc`-shaped family at `L = 0`, `r/m = 100`, `SIB = 24`.

    `%rsp` keeps the two-byte prefix (`c5 f8`/`c5 f8`) and `%r12` forces the
    three-byte one (`c4 c1 78`), so the register and the displacement move
    eight bits: 27/40 and 35/48.
    """
    load = direction == "load"
    role = "dest" if load else "src"
    opcode = "28" if load else "29"
    prefix = "c4c178" if base == "r12" else "c5f8"
    shift = 8 if base == "r12" else 0
    reg = xmm_slot(role, 27 + shift, vex=True)
    forms = []
    for bits in (8, 32):
        modrm = "44" if bits == 8 else "84"
        disp = "00" if bits == 8 else "00000000"
        if load:
            form_id = "x86:vmovaps/xmm-%s-disp%d/vex" % (base, bits)
        else:
            form_id = "x86:vmovaps/%s-disp%d-xmm/vex" % (base, bits)
        forms.append(form(form_id, prefix + opcode + modrm + "24" + disp,
                          [dict(reg, placements=[dict(p) for p in reg["placements"]]),
                           disp_slot(bits, 40 + shift)]))
    return forms


NEW_FORMS = (
    legacy_pair("load", "rsp") + legacy_pair("load", "r12")
    + legacy_pair("store", "rsp") + legacy_pair("store", "r12")
    + vex_pair("load", "rsp") + vex_pair("load", "r12")
    + vex_pair("store", "rsp") + vex_pair("store", "r12")
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
    if document["version"] != "0.19.0":
        raise SystemExit("source is not 0.19.0")
    # The renderer must reproduce the source byte for byte before it is trusted
    # with the extension.
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.19.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.19.0"', '"version": "0.20.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
