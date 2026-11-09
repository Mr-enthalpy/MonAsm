#!/usr/bin/env python3
"""Generate `definitions/rv64/0.6.0.json` from `0.5.0.json`.

One change (`ADR-0117`): the load/store widths other than `ld`/`sd`.

- loads (`0000011`): `lb`, `lh`, `lw`, `lbu`, `lhu`, `lwu` -- six rows;
- stores (`0100011`): `sb`, `sh`, `sw` -- three rows.

`ld`/`sd` are unchanged. Each row reuses its sibling's slot geometry:
`ld`'s `dest`/`base`/`disp` for a load, `sd`'s `src`/`base`/`disp` for a
store. Only `funct3` (template bits 12-14) changes, so the I-type and S-type
placements are the ones `0.5.0` already carries.

The generator reads the nine resolved UDB nodes and asserts, before writing
anything, that each declares the expected `encoding.match` (opcode plus
`funct3`), the same `imm` scatter as `ld`/`sd`, `sign_extend: true` on the
immediate, and the base `I` extension. A node that disagrees fails the run
rather than silently producing a row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0116/generate_0600.py [target]

With no argument the target is `definitions/rv64/0.6.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/rv64/0.5.0.json"
DEFAULT_TARGET = ROOT / "definitions/rv64/0.6.0.json"
UDB = ROOT / "research/external/rv64-udb/gen/resolved_spec/_/inst/I"

MARKER = "\n  ]\n}\n"

LOAD_OPCODE = "0000011"
STORE_OPCODE = "0100011"

# mnemonic, kind, funct3, hand-derived template. The template is the fixed word
# `funct3 << 12 | opcode` in little-endian; the table below records the same
# bytes derived twice, from the UDB `funct3` and by hand.
ROWS = [
    ("lb", "load", "000", "03000000"),
    ("lh", "load", "001", "03100000"),
    ("lw", "load", "010", "03200000"),
    ("lbu", "load", "100", "03400000"),
    ("lhu", "load", "101", "03500000"),
    ("lwu", "load", "110", "03600000"),
    ("sb", "store", "000", "23000000"),
    ("sh", "store", "001", "23100000"),
    ("sw", "store", "010", "23200000"),
]

# Expected slot geometry, per kind: role, placements.
LOAD_SLOTS = [
    ("dest", [[7, 5]]),
    ("base", [[15, 5]]),
    ("disp", [[20, 12]]),
]
STORE_SLOTS = [
    ("src", [[20, 5]]),
    ("base", [[15, 5]]),
    ("disp", [[25, 7], [7, 5]]),
]


def derive_template(kind: str, funct3: str) -> str:
    word = (int(funct3, 2) << 12) | int(
        LOAD_OPCODE if kind == "load" else STORE_OPCODE, 2)
    return word.to_bytes(4, "little").hex()


def check_node(mnemonic: str, kind: str, funct3: str) -> None:
    """Assert the pinned node states the encoding this row claims."""
    path = UDB / ("%s.yaml" % mnemonic)
    text = path.read_text(encoding="utf-8")
    start = text.index("encoding:")
    block = text[start:]

    match = re.search(r'match: "([^"]+)"', block)
    if match is None:
        raise SystemExit("%s: no encoding.match" % mnemonic)
    expected = "-" * 17 + funct3 + "-" * 5 + (
        LOAD_OPCODE if kind == "load" else STORE_OPCODE)
    if match.group(1) != expected:
        raise SystemExit("%s: encoding.match is %r, expected %r"
                         % (mnemonic, match.group(1), expected))

    imm = re.search(r'- name: imm\n\s+location: "?([^"\n]+)"?\n'
                    r'\s+sign_extend: true', block)
    if imm is None:
        raise SystemExit("%s: imm is not sign-extended" % mnemonic)
    wanted = "31-20" if kind == "load" else "31-25|11-7"
    if imm.group(1) != wanted:
        raise SystemExit("%s: imm location is %r, expected %r"
                         % (mnemonic, imm.group(1), wanted))

    for variable, location in (
            ("xs1", "19-15"),
            ("xd" if kind == "load" else "xs2",
             "11-7" if kind == "load" else "24-20")):
        found = re.search(r"- name: %s\n\s+location: %s\n" % (variable,
                                                             location),
                          block)
        if found is None:
            raise SystemExit("%s: %s is not at %s"
                             % (mnemonic, variable, location))

    declared = text[text.index("definedBy:"):text.index("assembly:")]
    if "name: I" not in declared:
        raise SystemExit("%s: not defined by the base I extension" % mnemonic)
    if mnemonic == "lwu" and "xlen: 64" not in declared:
        raise SystemExit("lwu: not restricted to xlen 64")


def check_slots(form_id: str, form: dict, expected: list) -> None:
    actual = [(slot["role"],
               [[item["bit_offset"], item["width"]]
                for item in slot["placements"]])
              for slot in form["slots"]]
    if actual != expected:
        raise SystemExit("%s: slot geometry differs: %r" % (form_id, actual))


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
    if document["version"] != "0.5.0":
        raise SystemExit("source is not 0.5.0")
    if document["definition_format"] != "fmp-def/0.1":
        raise SystemExit("source is not fmp-def/0.1")
    if set(document["target_identity"]["enabled_extensions"]) != {
            "rv64i", "rv64c"}:
        raise SystemExit("unexpected extension set")

    head = text[: -len(MARKER)]
    if head[head.rindex("\n") + 1:] != "    }":
        raise SystemExit("source does not end at a form object")
    if head[head.rindex('  "forms": [\n'):] != (
            '  "forms": [\n' + render_body(document["forms"])):
        raise SystemExit("renderer does not reproduce the 0.5.0 forms block")

    by_id = {form["form_id"]: form for form in document["forms"]}
    load = by_id["riscv:ld/rd-base-imm12"]
    store = by_id["riscv:sd/rs-base-imm12"]
    check_slots(load["form_id"], load, LOAD_SLOTS)
    check_slots(store["form_id"], store, STORE_SLOTS)

    new = []
    for mnemonic, kind, funct3, template in ROWS:
        check_node(mnemonic, kind, funct3)
        derived = derive_template(kind, funct3)
        if derived != template:
            raise SystemExit("%s: derived %s, table says %s"
                             % (mnemonic, derived, template))
        if kind == "load":
            form = json.loads(json.dumps(load))
            form["form_id"] = "riscv:%s/rd-base-imm12" % mnemonic
        else:
            form = json.loads(json.dumps(store))
            form["form_id"] = "riscv:%s/rs-base-imm12" % mnemonic
        form["template"] = template
        new.append(form)

    updated = head + ",\n" + render_body(new) + MARKER
    updated = updated.replace('"version": "0.5.0"', '"version": "0.6.0"', 1)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    if checked["forms"][: len(document["forms"])] != document["forms"]:
        raise SystemExit("old forms changed")
    if checked["forms"][len(document["forms"]):] != new:
        raise SystemExit("new forms differ from the rendered plan")
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
