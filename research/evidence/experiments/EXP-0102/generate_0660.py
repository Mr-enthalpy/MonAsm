#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.66.0.json` from `0.65.0.json`.

One change (ADR-0101): the three `sub` immediate rows that parallel the three
`add` rows already in the table.

- `x86:sub/rm64-imm8/legacy` is `REX.W 83 /5 ib` (`48 83 e8 00`), so the
  `dest` slot is `ModRM.r/m` at `[16,3]` with `REX.B` at `[0,1]` and the
  immediate is `[24,8]`;
- `x86:sub/rm64-imm32/legacy` is `REX.W 81 /5 id` (`48 81 e8 00 00 00 00`),
  the same two slots with the immediate at `[24,32]`;
- `x86:sub/rax-imm32/legacy` is `REX.W 2D id` (`48 2d 00 00 00 00`), the
  accumulator form with no `ModRM` byte and the immediate at `[16,32]`.

The only change between `add` and `sub` is the `ModRM.reg` field: `/0` becomes
`/5` (`c0` -> `e8`), and the accumulator opcode `05` becomes `2d`. Neither is a
plan field, so each is the row's template.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0102/generate_0660.py [target]

With no argument the target is `definitions/x86_64/0.66.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.65.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.66.0.json"


def slot(role, kind, target_type, placements, span=None, from_="reg_number"):
    entry = {
        "role": role,
        "kind": kind,
        "target_type": target_type,
        "from": from_,
        "modifiers": [],
        "placements": placements,
    }
    if span is not None:
        entry["range"] = span
    return entry


def rm64_dest():
    # `0.6.0` widened this slot to four bits: `REX.B` at [0,1] extends
    # `ModRM.r/m` at [16,3] (ADR-0033).
    return slot("dest", "x86.gpr64", "rm64",
                [{"bit_offset": 0, "width": 1},
                 {"bit_offset": 16, "width": 3}])


def imm_slot(offset, bits):
    return slot("imm", "x86.imm", "imm%d" % bits,
                [{"bit_offset": offset, "width": bits}],
                span={"signed": True, "bits": bits, "align_bits": 0},
                from_="operand_value")


NEW_FORMS = [
    {
        "form_id": "x86:sub/rm64-imm8/legacy",
        "template": "4883e800",
        "slots": [rm64_dest(), imm_slot(24, 8)],
    },
    {
        "form_id": "x86:sub/rm64-imm32/legacy",
        "template": "4881e800000000",
        "slots": [rm64_dest(), imm_slot(24, 32)],
    },
    {
        "form_id": "x86:sub/rax-imm32/legacy",
        "template": "482d00000000",
        "slots": [imm_slot(16, 32)],
    },
]

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
    if document["version"] != "0.65.0":
        raise SystemExit("source is not 0.65.0")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.65.0 forms block")

    forms = document["forms"]
    seen = {entry["form_id"] for entry in forms}
    for entry in NEW_FORMS:
        if entry["form_id"] in seen:
            raise SystemExit("duplicate %s" % entry["form_id"])
        forms.append(entry)

    head = head.replace('"version": "0.65.0"', '"version": "0.66.0"', 1)
    updated = head + HEAD_MARKER + render_body(forms) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
