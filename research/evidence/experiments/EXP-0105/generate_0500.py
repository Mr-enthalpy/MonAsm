#!/usr/bin/env python3
"""Generate `definitions/rv64/0.5.0.json` from `0.4.0.json`.

One change (`ADR-0104`): the five remaining B-type mnemonics join `beq`.
Each is the same template as `beq` with a different `funct3` (bits 12-14),
so the field geometry, the scatter and the `scale` fixup rule are unchanged.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0105/generate_0500.py [target]
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/rv64/0.4.0.json"
DEFAULT_TARGET = ROOT / "definitions/rv64/0.5.0.json"

MARKER = "\n  ]\n}\n"

# `funct3` sits in template bits 12-14, which is the high nibble of byte 1.
NEW_FORMS = [
    ("bne", "001", "63100000"),
    ("blt", "100", "63400000"),
    ("bge", "101", "63500000"),
    ("bltu", "110", "63600000"),
    ("bgeu", "111", "63700000"),
]

UDB = ROOT / "research/external/rv64-udb/gen/resolved_spec/_/inst/I"


def check_source_node(mnemonic: str, funct3: str) -> None:
    """The row is only a re-use of the B-type encoding if the pinned node says
    so: same opcode, same `funct3`, same scatter, same `left_shift`."""
    text = (UDB / ("%s.yaml" % mnemonic)).read_text(encoding="utf-8")
    expected_match = 'match: "-----------------%s-----1100011"' % funct3
    expected_extension = "definedBy:\n  extension:\n    name: I"
    if expected_match not in text:
        raise SystemExit("%s: encoding.match is not %r" % (mnemonic, expected_match))
    if 'location: "31|7|30-25|11-8"' not in text:
        raise SystemExit("%s: target location differs from beq" % mnemonic)
    if "left_shift: 1" not in text:
        raise SystemExit("%s: target left_shift is not 1" % mnemonic)
    if expected_extension not in text:
        raise SystemExit("%s: not defined by the base I extension" % mnemonic)


def render_placements(placements: list) -> str:
    pieces = []
    for item in placements:
        pieces.append(
            '{ "bit_offset": %d, "width": %d }'
            % (item["bit_offset"], item["width"])
        )
    return "[" + ", ".join(pieces) + "]"


def render_slot(entry: dict) -> list:
    lines = [
        "        {",
        '          "role": "%s",' % entry["role"],
        '          "kind": "%s",' % entry["kind"],
        '          "target_type": "%s",' % entry["target_type"],
        '          "from": "%s",' % entry["from"],
    ]
    if "range" in entry:
        span = entry["range"]
        lines.append(
            '          "range": { "signed": %s, "bits": %d, "align_bits": %d },'
            % (
                "true" if span["signed"] else "false",
                span["bits"],
                span["align_bits"],
            )
        )
    if "excluded" in entry:
        lines.append(
            '          "excluded": [%s],'
            % ", ".join(str(value) for value in entry["excluded"])
        )
    lines.append('          "modifiers": [],')
    lines.append(
        '          "placements": %s' % render_placements(entry["placements"])
    )
    lines.append("        }")
    return lines


def render_form(entry: dict) -> str:
    lines = [
        "    {",
        '      "form_id": "%s",' % entry["form_id"],
        '      "template": "%s",' % entry["template"],
        '      "slots": [',
    ]
    for index, item in enumerate(entry["slots"]):
        rendered = render_slot(item)
        if index + 1 < len(entry["slots"]):
            rendered[-1] += ","
        lines.extend(rendered)
    lines.append("      ]")
    lines.append("    }")
    return "\n".join(lines)


def render_body(forms: list) -> str:
    return ",\n".join(render_form(form) for form in forms)


def canonical_digest(document) -> str:
    text = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    text = SOURCE.read_text(encoding="utf-8")
    if not text.endswith(MARKER):
        raise SystemExit("unexpected file tail")

    document = json.loads(text)
    if document["version"] != "0.4.0":
        raise SystemExit("source is not 0.4.0")
    if document["definition_format"] != "fmp-def/0.1":
        raise SystemExit("source is not fmp-def/0.1")
    if set(document["target_identity"]["enabled_extensions"]) != {"rv64i", "rv64c"}:
        raise SystemExit("unexpected extension set")

    head = text[: -len(MARKER)]
    if head[head.rindex("\n") + 1 :] != "    }":
        raise SystemExit("source does not end at a form object")
    if head[head.rindex("  \"forms\": [\n") :] != (
        "  \"forms\": [\n" + render_body(document["forms"])
    ):
        raise SystemExit("renderer does not reproduce the 0.4.0 forms block")

    beq = next(
        form for form in document["forms"] if form["form_id"] == "riscv:beq/rs1-rs2-imm12"
    )
    new = []
    for mnemonic, funct3, template in NEW_FORMS:
        check_source_node(mnemonic, funct3)
        form = json.loads(json.dumps(beq))
        form["form_id"] = "riscv:%s/rs1-rs2-imm12" % mnemonic
        form["template"] = template
        new.append(form)

    updated = head + ",\n" + render_body(new) + MARKER
    updated = updated.replace('"version": "0.4.0"', '"version": "0.5.0"', 1)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    if checked["forms"][: len(document["forms"])] != document["forms"]:
        raise SystemExit("old forms changed")
    if checked["forms"][len(document["forms"]) :] != new:
        raise SystemExit("new forms differ from the rendered plan")
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
