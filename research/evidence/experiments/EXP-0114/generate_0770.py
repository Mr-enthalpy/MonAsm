#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.77.0.json` from `0.76.0.json`.

One change (`ADR-0115`): the `mov` immediate family, low register window only:

- `B8+rd` at 16 bits (`66 B8+rw iw`) and 32 bits (`B8+rd id`), two rows;
- `C7 /0` at 16 bits (`66 C7 /0 iw`), 32 bits (`C7 /0 id`) and 64 bits
  (`REX.W C7 /0 id`), three rows.

The plan lists six rows, but `REX.W B8+rd` takes a 64-bit immediate (`io`) and
is `movabs`, which the plan excludes; `EXP-0114` measures `movabsq $300, %rax`
as `48 b8` plus eight immediate bytes, while `movq $300, %rax` is
`48 c7 c0 ...`. Five rows.

The 16/32-bit rows stay three-bit: `%r8`-`%r15` would add a `REX` byte and
change the length. The 64-bit `C7` row reaches `%r8`-`%r15` through `REX.B`,
which shares the `REX.W` byte.

Templates are the measured `EXP-0114` bytes with the register and immediate
fields zeroed; the two 16/32-bit `C7` rows are hand-derived and confirmed by
`llvm-mc -disassemble` because `llvm-mc` always picks `B8+rd` for a register
destination.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0114/generate_0770.py [target]

With no argument the target is `definitions/x86_64/0.77.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.76.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.77.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"

# form_id, template, destination kind/target/placements, immediate target/bits/offset
ROWS = [
    ("x86:mov/r16-imm16/legacy", "66b80000", "x86.gpr16", "r16",
     [{"bit_offset": 8, "width": 3}], "imm16", 16, 16),
    ("x86:mov/r32-imm32/legacy", "b800000000", "x86.gpr32", "r32",
     [{"bit_offset": 0, "width": 3}], "imm32", 32, 8),
    ("x86:mov/rm16-imm16/legacy", "66c7c00000", "x86.gpr16", "rm16",
     [{"bit_offset": 16, "width": 3}], "imm16", 16, 24),
    ("x86:mov/rm32-imm32/legacy", "c7c000000000", "x86.gpr32", "rm32",
     [{"bit_offset": 8, "width": 3}], "imm32", 32, 16),
    ("x86:mov/rm64-imm32/legacy", "48c7c000000000", "x86.gpr64", "rm64",
     [{"bit_offset": 0, "width": 1}, {"bit_offset": 16, "width": 3}],
     "imm32", 32, 24),
]


def reg_slot(kind: str, target_type: str, placements: list) -> dict:
    return {
        "role": "dest",
        "kind": kind,
        "target_type": target_type,
        "from": "reg_number",
        "modifiers": [],
        "placements": placements,
    }


def imm_slot(target_type: str, bits: int, offset: int) -> dict:
    return {
        "role": "imm",
        "kind": "x86.imm",
        "target_type": target_type,
        "from": "operand_value",
        "range": {"signed": True, "bits": bits, "align_bits": 0},
        "modifiers": [],
        "placements": [{"bit_offset": offset, "width": bits}],
    }


NEW_FORMS = [
    {
        "form_id": form_id,
        "requires_extensions": [],
        "template": template,
        "slots": [reg_slot(kind, target, placements),
                  imm_slot(imm_target, bits, offset)],
    }
    for form_id, template, kind, target, placements, imm_target, bits, offset
    in ROWS
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
    if document["version"] != "0.76.0":
        raise SystemExit("source is not 0.76.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.76.0 forms block")

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

    updated = head.replace('"version": "0.76.0"', '"version": "0.77.0"', 1)
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
