#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.70.0.json` from `0.69.0.json`.

One change (`ADR-0106`): the legacy SSE `movaps` xmm load and store gain the
extended-register window on the two fixed `%rsp`/`%r12` bases. The low rows
(`xmm0`-`xmm7`, 5/8 bytes for `%rsp` and 6/9 for `%r12`) cannot carry the
`REX.R` byte without changing the instruction length, so the `xmm8`-`xmm15`
window is a new row (`E-OPERAND-004` on the low rows, `INV-04`).

The eight rows are load/store x `disp8`/`disp32` x `%rsp`/`%r12`. Templates are
the measured `EXP-0107` bytes with the register and displacement zeroed:

| row | template | bytes |
|---|---|---|
| `xmm-ext-rsp-disp8` | `440f28442400` | 6 |
| `xmm-ext-rsp-disp32` | `440f28842400000000` | 9 |
| `xmm-ext-r12-disp8` | `450f28442400` | 6 |
| `xmm-ext-r12-disp32` | `450f28842400000000` | 9 |
| `rsp-disp8-xmm-ext` | `440f29442400` | 6 |
| `rsp-disp32-xmm-ext` | `440f29842400000000` | 9 |
| `r12-disp8-xmm-ext` | `450f29442400` | 6 |
| `r12-disp32-xmm-ext` | `450f29842400000000` | 9 |

Usage (from the repository root):

    python research/evidence/experiments/EXP-0107/generate_0700.py [target]

With no argument the target is `definitions/x86_64/0.70.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.69.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.70.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"

LOW_XMM = [0, 1, 2, 3, 4, 5, 6, 7]


def vec_slot(role: str) -> dict:
    """`xmm8`-`xmm15` = `ModRM.reg` plus `REX.R`; the low window is excluded."""
    return {
        "role": role,
        "kind": "x86.xmm",
        "target_type": "xmm",
        "from": "reg_number",
        "excluded": LOW_XMM,
        "modifiers": [],
        "placements": [
            {"bit_offset": 2, "width": 1},
            {"bit_offset": 27, "width": 3},
        ],
    }


def disp_slot(width: int) -> dict:
    return {
        "role": "disp",
        "kind": "x86.imm",
        "target_type": "disp%d" % width,
        "from": "operand_value",
        "range": {"signed": True, "bits": width, "align_bits": 0},
        "modifiers": [],
        "placements": [{"bit_offset": 40, "width": width}],
    }


def make_form(form_id: str, template: str, role: str, width: int) -> dict:
    return {
        "form_id": form_id,
        "requires_extensions": [],
        "template": template,
        "slots": [vec_slot(role), disp_slot(width)],
    }


NEW_FORMS = [
    make_form("x86:movaps/xmm-ext-rsp-disp8/legacy",
              "440f28442400", "dest", 8),
    make_form("x86:movaps/xmm-ext-rsp-disp32/legacy",
              "440f28842400000000", "dest", 32),
    make_form("x86:movaps/xmm-ext-r12-disp8/legacy",
              "450f28442400", "dest", 8),
    make_form("x86:movaps/xmm-ext-r12-disp32/legacy",
              "450f28842400000000", "dest", 32),
    make_form("x86:movaps/rsp-disp8-xmm-ext/legacy",
              "440f29442400", "src", 8),
    make_form("x86:movaps/rsp-disp32-xmm-ext/legacy",
              "440f29842400000000", "src", 32),
    make_form("x86:movaps/r12-disp8-xmm-ext/legacy",
              "450f29442400", "src", 8),
    make_form("x86:movaps/r12-disp32-xmm-ext/legacy",
              "450f29842400000000", "src", 32),
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
    if document["version"] != "0.69.0":
        raise SystemExit("source is not 0.69.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.69.0 forms block")

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

    updated = head.replace('"version": "0.69.0"', '"version": "0.70.0"', 1)
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
