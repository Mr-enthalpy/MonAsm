#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.78.0.json` from `0.77.0.json`.

One change (`ADR-0116`): the `sub` memory directions, low base window only:

- `29 /r` (store direction: the memory operand is the destination, the
  register is `ModRM.reg`) at 64/32/16 bits with `base + disp8` and
  `base + disp32`, six rows;
- `2B /r` (load direction: the register is the destination, the memory
  operand is `ModRM.r/m`) at the same widths and displacements, six rows.

`EC-42` already names both directions for the register/register pair, where
`29` is present and `2B` is absent (`N01ej`). The memory slice has to name the
direction too, because `29` and `2B` are different opcode bytes for the same
operands: `subq %rcx, 8(%rax)` is `48 29 48 08` and `subq 8(%rax), %rcx` is
`48 2b 48 08` (`EXP-0115`).

The base stays a 64-bit register at every width (`x86.gpr64`/`rm64`), matching
the existing `mov` memory rows: in 64-bit mode the address register is 64-bit
while only the data width changes. The base is three-bit at 32/16 bits (no
`REX` byte) and `%rsp`/`%r12` are excluded because they need a `SIB` byte; at
64 bits `REX.B` shares the `REX.W` byte, so `%r8`-`%r15` and `%r13` are
reachable, but `%r12` still needs `SIB`. `%rsp`/`%r12` keep their existing
`rsp-*`/`r12-*` rows, which are out of this slice.

The mod field is `01` for `disp8` and `10` for `disp32`; a zero displacement
(`mod = 00`) is a separate template and stays out.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0115/generate_0780.py [target]

With no argument the target is `definitions/x86_64/0.78.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.77.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.78.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"

# Per-width field geometry, read from the measured `EXP-0115` templates.
# base: REX.B (64-bit only) plus `ModRM.r/m`; `%rsp`/`%r12` need `SIB`.
BASE = {
    64: ([{"bit_offset": 0, "width": 1}, {"bit_offset": 16, "width": 3}],
         [4, 12]),
    32: ([{"bit_offset": 8, "width": 3}], [4]),
    16: ([{"bit_offset": 16, "width": 3}], [4]),
}
REG = {
    64: [{"bit_offset": 2, "width": 1}, {"bit_offset": 19, "width": 3}],
    32: [{"bit_offset": 11, "width": 3}],
    16: [{"bit_offset": 19, "width": 3}],
}
DISP_OFFSET = {64: 24, 32: 16, 16: 24}

# form_id, template, direction, width, displacement bits
ROWS = [
    ("x86:sub/base-disp8-r64/legacy", "48294000", "store", 64, 8),
    ("x86:sub/base-disp32-r64/legacy", "48298000000000", "store", 64, 32),
    ("x86:sub/r64-base-disp8/legacy", "482b4000", "load", 64, 8),
    ("x86:sub/r64-base-disp32/legacy", "482b8000000000", "load", 64, 32),
    ("x86:sub/base-disp8-r32/legacy", "294000", "store", 32, 8),
    ("x86:sub/base-disp32-r32/legacy", "298000000000", "store", 32, 32),
    ("x86:sub/r32-base-disp8/legacy", "2b4000", "load", 32, 8),
    ("x86:sub/r32-base-disp32/legacy", "2b8000000000", "load", 32, 32),
    ("x86:sub/base-disp8-r16/legacy", "66294000", "store", 16, 8),
    ("x86:sub/base-disp32-r16/legacy", "66298000000000", "store", 16, 32),
    ("x86:sub/r16-base-disp8/legacy", "662b4000", "load", 16, 8),
    ("x86:sub/r16-base-disp32/legacy", "662b8000000000", "load", 16, 32),
]


def reg_slot(role: str, width: int) -> dict:
    return {
        "role": role,
        "kind": "x86.gpr%d" % width,
        "target_type": "r%d" % width,
        "from": "reg_number",
        "modifiers": [],
        "placements": REG[width],
    }


def build_slots(direction: str, width: int, disp_bits: int) -> list:
    placements, excluded = BASE[width]
    base = {
        "role": "base",
        "kind": "x86.gpr64",
        "target_type": "rm64",
        "from": "reg_number",
        "excluded": excluded,
        "modifiers": [],
        "placements": placements,
    }
    disp = {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp%d" % disp_bits,
        "from": "operand_value",
        "range": {"signed": True, "bits": disp_bits, "align_bits": 0},
        "modifiers": [],
        "placements": [{"bit_offset": DISP_OFFSET[width], "width": disp_bits}],
    }
    if direction == "store":
        # `29 /r`: the memory operand is the destination. It keeps the
        # `base` role of the existing `mov` memory rows, and the register is
        # `src` in `ModRM.reg`.
        return [reg_slot("src", width), base, disp]
    # `2B /r`: the register is the destination, the memory operand is
    # `ModRM.r/m`.
    base["role"] = "src"
    return [reg_slot("dest", width), base, disp]


NEW_FORMS = [
    {
        "form_id": form_id,
        "requires_extensions": [],
        "template": template,
        "slots": build_slots(direction, width, disp_bits),
    }
    for form_id, template, direction, width, disp_bits in ROWS
]


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
        '    "requires_extensions": [%s],'
        % ", ".join('"%s"' % name for name in entry["requires_extensions"]),
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


def canonical_digest(document) -> str:
    text = json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    text = SOURCE.read_text(encoding="utf-8")
    if not text.endswith(TAIL_MARKER):
        raise SystemExit("unexpected file tail")
    head, block = text.split(HEAD_MARKER, 1)
    body = block[: -len(TAIL_MARKER)]

    document = json.loads(text)
    if document["version"] != "0.77.0":
        raise SystemExit("source is not 0.77.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.77.0 forms block")

    forms = document["forms"]
    known = {form["form_id"] for form in forms}
    for form in NEW_FORMS:
        if form["form_id"] in known:
            raise SystemExit("%s already exists" % form["form_id"])
        for slot in form["slots"]:
            for placement in slot["placements"]:
                if placement["bit_offset"] + placement["width"] > len(
                        form["template"]) * 4:
                    raise SystemExit("%s: placement past the template"
                                     % form["form_id"])

    updated = head.replace('"version": "0.77.0"', '"version": "0.78.0"', 1)
    updated = updated + HEAD_MARKER + render_body(forms + NEW_FORMS) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    if checked["forms"][: len(forms)] != forms:
        raise SystemExit("old forms changed")
    if checked["forms"][len(forms):] != NEW_FORMS:
        raise SystemExit("new forms differ from the rendered plan")
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
