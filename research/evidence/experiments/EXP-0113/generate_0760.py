#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.76.0.json` from `0.75.0.json`.

One change (`ADR-0114`): the integer ALU immediate family. Thirty-six rows,
low register window only:

- `add`/`sub` at 32 bits (`83 /r ib`, `81 /r id`) and 16 bits
  (`66 83 /r ib`, `66 81 /r iw`), eight rows. The 64-bit rows already exist
  (`0.1.0`, `0.66.0`);
- `and`/`or`/`xor`/`cmp` at 64, 32 and 16 bits, `imm8` plus the full-width
  immediate, twenty-four rows;
- the 64-bit `%rax` short form of those four mnemonics (`25`, `0D`, `35`,
  `3D`), four rows. The `add`/`sub` short forms already exist (`05`, `2D`).

The 32/16-bit `%rax` short forms, the `test`/`neg`/`not` group, the 8-bit
width and the memory shapes stay out.

Templates are the measured `EXP-0113` bytes with the register and immediate
fields zeroed.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0113/generate_0760.py [target]

With no argument the target is `definitions/x86_64/0.76.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.75.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.76.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"

# mnemonic, ModRM /digit
MNEMONICS = [
    ("add", 0),
    ("sub", 5),
    ("and", 4),
    ("or", 1),
    ("xor", 6),
    ("cmp", 7),
]

# mnemonic, the `%rax` short-form opcode
ACCUMULATOR = [
    ("and", "25"),
    ("or", "0d"),
    ("xor", "35"),
    ("cmp", "3d"),
]

ROWS = []
for mnemonic, digit in MNEMONICS:
    modrm = 0xC0 | (digit << 3)
    if mnemonic in ("add", "sub"):
        widths = [
            (32, "", "x86.gpr32", "rm32", [{"bit_offset": 8, "width": 3}], 16),
            (16, "66", "x86.gpr16", "rm16", [{"bit_offset": 16, "width": 3}], 24),
        ]
    else:
        widths = [
            (64, "48", "x86.gpr64", "rm64",
             [{"bit_offset": 0, "width": 1},
              {"bit_offset": 16, "width": 3}], 24),
            (32, "", "x86.gpr32", "rm32", [{"bit_offset": 8, "width": 3}], 16),
            (16, "66", "x86.gpr16", "rm16", [{"bit_offset": 16, "width": 3}], 24),
        ]
    for bits, prefix, kind, rm, dest, imm_offset in widths:
        short = prefix + "83" + ("%02x" % modrm)
        full = prefix + "81" + ("%02x" % modrm)
        ROWS.append((
            "x86:%s/rm%d-imm8/legacy" % (mnemonic, bits),
            short + "00", kind, rm, dest, "imm8", 8, imm_offset,
        ))
        if bits == 16:
            imm = "0000"
            target = "imm16"
            target_bits = 16
        else:
            imm = "00000000"
            target = "imm32"
            target_bits = 32
        ROWS.append((
            "x86:%s/rm%d-%s/legacy" % (mnemonic, bits, target),
            full + imm, kind, rm, dest, target, target_bits, imm_offset,
        ))
for mnemonic, opcode in ACCUMULATOR:
    ROWS.append((
        "x86:%s/rax-imm32/legacy" % mnemonic,
        "48" + opcode + "00000000", None, None, None, "imm32", 32, 16,
    ))


def reg_slot(role: str, kind: str, target_type: str, placements: list) -> dict:
    return {
        "role": role,
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


def make_form(form_id: str, template: str, kind: str | None, rm: str | None,
              dest: list | None, target_type: str, bits: int,
              imm_offset: int) -> dict:
    if kind is None:
        slots = [imm_slot(target_type, bits, imm_offset)]
    else:
        slots = [reg_slot("dest", kind, rm, dest),
                 imm_slot(target_type, bits, imm_offset)]
    return {
        "form_id": form_id,
        "requires_extensions": [],
        "template": template,
        "slots": slots,
    }


NEW_FORMS = [make_form(*row) for row in ROWS]


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
    if document["version"] != "0.75.0":
        raise SystemExit("source is not 0.75.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.75.0 forms block")

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

    updated = head.replace('"version": "0.75.0"', '"version": "0.76.0"', 1)
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
