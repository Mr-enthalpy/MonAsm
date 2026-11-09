#!/usr/bin/env python3
"""Generate `definitions/x86_64/0.68.0.json` from `0.67.0.json`.

One change (`ADR-0103`): the document format becomes `fmp-def/0.2` and every
form gains a required `requires_extensions`. Form ids, templates and slots are
unchanged, so the table encodes exactly the same bytes.

The requirement is the operand width, not the mnemonic (`EXP-0104`):

| rows | count | `requires_extensions` |
|---|---|---|
| `/legacy` | 388 | `[]` |
| `/vex` | 38 | `["avx"]` |
| `/evex` with a `zmm` slot | 29 | `["avx","avx512f"]` |
| `/evex` with only `xmm`/`ymm` slots | 58 | `["avx","avx512f","avx512vl"]` |

Usage (from the repository root):

    python research/evidence/experiments/EXP-0104/generate_0680.py [target]

With no argument the target is `definitions/x86_64/0.68.0.json`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "definitions/x86_64/0.67.0.json"
DEFAULT_TARGET = ROOT / "definitions/x86_64/0.68.0.json"

AVX = ["avx"]
AVX512F = ["avx", "avx512f"]
AVX512VL = ["avx", "avx512f", "avx512vl"]

HEAD_MARKER = '  "forms": [\n'
TAIL_MARKER = "\n  ]\n}\n"


def requirement(form: dict) -> list:
    form_id = form["form_id"]
    if form_id.endswith("/legacy"):
        return []
    if form_id.endswith("/vex"):
        return list(AVX)
    types = {slot["target_type"] for slot in form["slots"]}
    if "zmm" in types:
        return list(AVX512F)
    return list(AVX512VL)


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


def render_form(entry: dict, requires: list) -> str:
    lines = [
        "  {",
        '    "form_id": "%s",' % entry["form_id"],
    ]
    if requires is not None:
        lines.append(
            '    "requires_extensions": [%s],'
            % ", ".join('"%s"' % name for name in requires))
    lines.append('    "template": "%s",' % entry["template"])
    lines.append('    "slots": [')
    for index, item in enumerate(entry["slots"]):
        rendered = render_slot(item)
        if index + 1 < len(entry["slots"]):
            rendered[-1] += ","
        lines.extend(rendered)
    lines.append("    ]")
    lines.append("  }")
    return "\n".join(lines)


def render_body(forms: list, version: str) -> str:
    rendered = []
    for entry in forms:
        requires = None if version == "0.67.0" else requirement(entry)
        rendered.append(render_form(entry, requires))
    return ",\n".join(rendered)


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
    if document["version"] != "0.67.0":
        raise SystemExit("source is not 0.67.0")
    if document["definition_format"] != "fmp-def/0.1":
        raise SystemExit("source is not fmp-def/0.1")
    if body != render_body(document["forms"], "0.67.0"):
        raise SystemExit("renderer does not reproduce the 0.67.0 forms block")

    forms = document["forms"]
    table_extensions = set(document["target_identity"]["enabled_extensions"])
    used = set()
    for entry in forms:
        names = requirement(entry)
        if names != sorted(set(names)):
            raise SystemExit("%s: requirement is not sorted/unique"
                             % entry["form_id"])
        missing = set(names) - table_extensions
        if missing:
            raise SystemExit("%s: %s not declared by the table"
                             % (entry["form_id"], sorted(missing)))
        used.update(names)
    if used != table_extensions:
        raise SystemExit("table declares %s but forms use %s"
                         % (sorted(table_extensions), sorted(used)))

    updated = head.replace(
        '"definition_format": "fmp-def/0.1"',
        '"definition_format": "fmp-def/0.2"', 1)
    updated = updated.replace('"version": "0.67.0"', '"version": "0.68.0"', 1)
    updated = updated + HEAD_MARKER + render_body(forms, "0.68.0") + TAIL_MARKER
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)

    checked = json.loads(target.read_text(encoding="utf-8"))
    counts = {}
    for entry in checked["forms"]:
        key = ",".join(entry["requires_extensions"]) or "<baseline>"
        counts[key] = counts.get(key, 0) + 1
    print("%s: %d forms" % (target.as_posix(), len(checked["forms"])))
    for key in sorted(counts):
        print("  %-26s %d" % (key, counts[key]))
    print("definition digest %s" % canonical_digest(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
