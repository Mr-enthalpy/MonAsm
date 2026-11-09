#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.69.0.json` from `0.68.0.json`.

One change (`ADR-0105`): six SSE `%rip`-relative rows join the table. They are
the `movaps`/`vmovaps` xmm load and store at the legacy, VEX and EVEX encodings,
with the base+`disp32` slots replaced by the one `riprel32` slot that
`x86:mov/r64-riprel32/legacy` already pins. Form ids, templates and slots of the
513 existing rows are unchanged.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0106/generate_0690.py [target]

With no argument the target is `definitions/x86_64/0.69.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.68.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.69.0.json"

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"


def rel_slot(role: str) -> dict:
    return {
        "role": role,
        "kind": "x86.rel",
        "target_type": "riprel32",
        "from": "operand_value",
        "range": {"signed": True, "bits": 32, "align_bits": 0},
        "modifiers": [],
        "placements": [{"bit_offset": 0, "width": 32}],
    }


def vec_slot(role: str, placements: list) -> dict:
    return {
        "role": role,
        "kind": "x86.xmm",
        "target_type": "xmm",
        "from": "reg_number",
        "modifiers": [],
        "placements": placements,
    }


# The template is the measured `16(%rip)` encoding with the displacement zeroed
# (`EXP-0106` §2); the target placement is `-16` from the template end because
# the 32-bit field is the last thing in every one of these instructions.
NEW_FORMS = [
    {
        "form_id": "x86:movaps/xmm-riprel32/legacy",
        "requires_extensions": [],
        "template": "0f280500000000",
        "slots": [
            vec_slot("dest", [{"bit_offset": 19, "width": 3}]),
            rel_slot("target"),
        ],
    },
    {
        "form_id": "x86:movaps/riprel32-xmm/legacy",
        "requires_extensions": [],
        "template": "0f290500000000",
        "slots": [
            vec_slot("src", [{"bit_offset": 19, "width": 3}]),
            rel_slot("target"),
        ],
    },
    {
        "form_id": "x86:vmovaps/xmm-riprel32/vex",
        "requires_extensions": ["avx"],
        "template": "c5f8280500000000",
        "slots": [
            vec_slot(
                "dest",
                [
                    {"bit_offset": 15, "width": 1, "invert": True},
                    {"bit_offset": 27, "width": 3},
                ],
            ),
            rel_slot("target"),
        ],
    },
    {
        "form_id": "x86:vmovaps/riprel32-xmm/vex",
        "requires_extensions": ["avx"],
        "template": "c5f8290500000000",
        "slots": [
            vec_slot(
                "src",
                [
                    {"bit_offset": 15, "width": 1, "invert": True},
                    {"bit_offset": 27, "width": 3},
                ],
            ),
            rel_slot("target"),
        ],
    },
    {
        "form_id": "x86:vmovaps/xmm-riprel32/evex",
        "requires_extensions": ["avx", "avx512f", "avx512vl"],
        "template": "62f17c08280500000000",
        "slots": [
            vec_slot(
                "dest",
                [
                    {"bit_offset": 12, "width": 1, "invert": True},
                    {"bit_offset": 15, "width": 1, "invert": True},
                    {"bit_offset": 43, "width": 3},
                ],
            ),
            rel_slot("target"),
        ],
    },
    {
        "form_id": "x86:vmovaps/riprel32-xmm/evex",
        "requires_extensions": ["avx", "avx512f", "avx512vl"],
        "template": "62f17c08290500000000",
        "slots": [
            vec_slot(
                "src",
                [
                    {"bit_offset": 12, "width": 1, "invert": True},
                    {"bit_offset": 15, "width": 1, "invert": True},
                    {"bit_offset": 43, "width": 3},
                ],
            ),
            rel_slot("target"),
        ],
    },
]


def place_target(form: dict) -> None:
    """The `riprel32` field is the last 32 bits of the instruction."""
    bits = len(bytes.fromhex(form["template"])) * 8
    form["slots"][-1]["placements"] = [{"bit_offset": bits - 32, "width": 32}]


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
    if document["version"] != "0.68.0":
        raise SystemExit("source is not 0.68.0")
    if document["definition_format"] != "fmp-def/0.2":
        raise SystemExit("source is not fmp-def/0.2")
    if body != render_body(document["forms"]):
        raise SystemExit("renderer does not reproduce the 0.68.0 forms block")

    forms = document["forms"]
    known = {form["form_id"] for form in forms}
    table_extensions = set(document["target_identity"]["enabled_extensions"])
    for form in NEW_FORMS:
        place_target(form)
        if form["form_id"] in known:
            raise SystemExit("%s already exists" % form["form_id"])
        if form["requires_extensions"] != sorted(set(form["requires_extensions"])):
            raise SystemExit("%s: requirement is not sorted/unique"
                             % form["form_id"])
        missing = set(form["requires_extensions"]) - table_extensions
        if missing:
            raise SystemExit("%s: %s not declared by the table"
                             % (form["form_id"], sorted(missing)))

    updated = head.replace('"version": "0.68.0"', '"version": "0.69.0"', 1)
    updated = updated + HEAD_MARKER + render_body(forms + NEW_FORMS) + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    if checked["forms"][: len(forms)] != forms:
        raise SystemExit("old forms changed")
    if checked["forms"][len(forms) :] != NEW_FORMS:
        raise SystemExit("new forms differ from the rendered plan")
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
