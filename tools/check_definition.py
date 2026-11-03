#!/usr/bin/env python3
"""Consistency checks for FMP definition documents.

Checks, for every `definitions/<isa>/<version>.json`:
  1. The document shape required by `docs/fmp-v0/07_definition_format.md` §2-§4.
  2. Load-time rules that make a definition usable: unique `form_id`s, even
     hex templates, placements inside the template, no overlapping placements,
     slot widths that sum to `range.bits`.
  3. The reading-aid table in §8 of `07_definition_format.md` matches the JSON.
  4. Prints the canonical digest so a plan can name it.

Exit code 0 means no errors.

The canonical form is the one `01_contract.md` §12 defines: sorted keys, compact
separators, `ensure_ascii=False`, no trailing newline. The Rust materializer
computes the same bytes with `serde_json`, whose default map is a `BTreeMap`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS = ROOT / "definitions"
DOC = ROOT / "docs/fmp-v0/07_definition_format.md"

FORM_ID = re.compile(r"^(x86|aarch64|riscv):[^/]+/.+$")
X86_FORM_ID = re.compile(r"^(x86|aarch64|riscv):[^/]+/[^/]+(/[^/]+)?$")
HEX = re.compile(r"^([0-9a-f]{2})+$")
ROLES = {
    "dest",
    "src",
    "src2",
    "base",
    "index",
    "disp",
    "imm",
    "target",
    "pred",
    "list",
    "modifier",
}
FROM = {"reg_number", "operand_value"}
TARGET_KEYS = {
    "isa_family",
    "isa_variant",
    "execution_mode",
    "enabled_extensions",
    "byte_order",
    "address_width",
}
FORM_KEYS = {"form_id", "template", "slots"}
SLOT_KEYS = {
    "role",
    "kind",
    "target_type",
    "from",
    "range",
    "modifiers",
    "placements",
}


def canonical_bytes(document) -> bytes:
    text = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return text.encode("utf-8")


def digest(document) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(document)).hexdigest()


def fail(errors, where, message):
    errors.append("%s: %s" % (where, message))


def check_definition(path: Path, errors):
    where = path.relative_to(ROOT).as_posix()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        fail(errors, where, "not parseable: %s" % exc)
        return None

    if document.get("definition_format") != "fmp-def/0.1":
        fail(errors, where, "definition_format must be 'fmp-def/0.1'")
    for key in ("namespace", "version"):
        if not isinstance(document.get(key), str) or not document[key]:
            fail(errors, where, "%s must be a non-empty string" % key)

    target = document.get("target_identity")
    if not isinstance(target, dict):
        fail(errors, where, "target_identity must be an object")
    else:
        if set(target) != TARGET_KEYS:
            fail(
                errors,
                where,
                "target_identity keys must be exactly %s" % sorted(TARGET_KEYS),
            )
        family = target.get("isa_family")
        prefix = {
            "x86": "x86",
            "aarch64": "aarch64",
            "riscv": "riscv",
        }.get(family)
        if prefix is None:
            fail(errors, where, "unsupported isa_family %r" % (family,))
        if target.get("byte_order") != "little":
            fail(errors, where, "v0 definitions must declare byte_order 'little'")

    forms = document.get("forms")
    if not isinstance(forms, list) or not forms:
        fail(errors, where, "forms must be a non-empty array")
        return None

    seen = set()
    for index, form in enumerate(forms):
        spot = "%s/forms/%d" % (where, index)
        if not isinstance(form, dict):
            fail(errors, spot, "form must be an object")
            continue
        if set(form) != FORM_KEYS:
            fail(errors, spot, "keys must be exactly %s" % sorted(FORM_KEYS))
            continue
        form_id = form["form_id"]
        if not isinstance(form_id, str) or not FORM_ID.match(form_id):
            fail(errors, spot, "form_id %r violates contract §7" % (form_id,))
            continue
        if not X86_FORM_ID.match(form_id):
            fail(errors, spot, "form_id %r has an empty component" % form_id)
        if form_id in seen:
            fail(errors, spot, "duplicate form_id %s" % form_id)
        seen.add(form_id)

        template = form["template"]
        if not isinstance(template, str) or not HEX.match(template):
            fail(errors, spot, "template must be a non-empty even-length hex string")
            continue
        template_bits = len(bytes.fromhex(template)) * 8

        slots = form["slots"]
        if not isinstance(slots, list) or not slots:
            fail(errors, spot, "slots must be a non-empty array")
            continue
        occupied = {}
        for slot_index, slot in enumerate(slots):
            slot_spot = "%s/slots/%d" % (spot, slot_index)
            if not isinstance(slot, dict):
                fail(errors, slot_spot, "slot must be an object")
                continue
            required = SLOT_KEYS - {"range"}
            missing = required - set(slot)
            if missing:
                fail(errors, slot_spot, "missing keys %s" % sorted(missing))
                continue
            extra = set(slot) - SLOT_KEYS
            if extra:
                fail(errors, slot_spot, "unknown keys %s" % sorted(extra))
            if slot["role"] not in ROLES:
                fail(errors, slot_spot, "role %r not in the contract set" % slot["role"])
            if slot["from"] not in FROM:
                fail(errors, slot_spot, "from %r not supported" % (slot["from"],))
            if not isinstance(slot["modifiers"], list):
                fail(errors, slot_spot, "modifiers must be an array (possibly empty)")
            has_range = "range" in slot
            if slot["from"] == "operand_value" and not has_range:
                fail(errors, slot_spot, "operand_value slot needs a range")
            if slot["from"] == "reg_number" and has_range:
                fail(errors, slot_spot, "reg_number slot must not declare a range")

            placements = slot["placements"]
            if not isinstance(placements, list) or not placements:
                fail(errors, slot_spot, "placements must be a non-empty array")
                continue
            total = 0
            for placement in placements:
                if set(placement) != {"bit_offset", "width"}:
                    fail(errors, slot_spot, "placement keys must be bit_offset,width")
                    continue
                offset = placement["bit_offset"]
                width = placement["width"]
                if (
                    not isinstance(offset, int)
                    or not isinstance(width, int)
                    or isinstance(offset, bool)
                    or isinstance(width, bool)
                    or width <= 0
                    or offset < 0
                ):
                    fail(errors, slot_spot, "placement values must be positive integers")
                    continue
                if offset + width > template_bits:
                    fail(
                        errors,
                        slot_spot,
                        "placement [%d,%d] exceeds the %d-bit template"
                        % (offset, width, template_bits),
                    )
                for bit in range(offset, offset + width):
                    if bit in occupied:
                        fail(
                            errors,
                            slot_spot,
                            "placement bit %d already owned by %s" % (bit, occupied[bit]),
                        )
                    occupied[bit] = "%d/%s" % (slot_index, slot["target_type"])
                total += width
            if has_range:
                bits = slot["range"].get("bits")
                if isinstance(bits, int) and not isinstance(bits, bool) and total != bits:
                    fail(
                        errors,
                        slot_spot,
                        "placements sum to %d bits, range.bits is %d" % (total, bits),
                    )
    return document


def render_slot_cell(slot) -> str:
    placements = ", ".join(
        "`[%d,%d]`" % (p["bit_offset"], p["width"]) for p in slot["placements"]
    )
    return "%s: `%s`/`%s` \u2192 %s" % (
        slot["role"],
        slot["kind"],
        slot["target_type"],
        placements,
    )


def check_doc_table(documents, errors):
    if not DOC.is_file():
        fail(errors, DOC.name, "missing definition format document")
        return
    text = DOC.read_text(encoding="utf-8")
    rows = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        match = re.match(r"^`(x86:[^`]+)`$", cells[0])
        if not match:
            continue
        rows[match.group(1)] = cells

    expected = {}
    for document in documents:
        for form in document["forms"]:
            if not form["form_id"].startswith("x86:"):
                continue
            expected[form["form_id"]] = [
                "`%s`" % form["form_id"],
                "`%s`" % form["template"],
                "; ".join(render_slot_cell(slot) for slot in form["slots"]),
                str(len(bytes.fromhex(form["template"]))),
            ]

    if set(rows) != set(expected):
        fail(
            errors,
            "07_definition_format.md §8",
            "table rows %s != definition forms %s"
            % (sorted(set(rows) - set(expected)) or "same", sorted(set(expected) - set(rows)) or "same"),
        )
        return
    for form_id, cells in expected.items():
        for index in (1, 2, 3):
            if rows[form_id][index] != cells[index]:
                fail(
                    errors,
                    "07_definition_format.md §8 %s" % form_id,
                    "column %d is %r, definition says %r"
                    % (index, rows[form_id][index], cells[index]),
                )


def main() -> int:
    errors = []
    documents = []
    if not DEFINITIONS.is_dir():
        print("no definitions directory; nothing to check")
        return 0
    paths = sorted(DEFINITIONS.rglob("*.json"))
    for path in paths:
        document = check_definition(path, errors)
        if document is not None:
            documents.append(document)

    check_doc_table(documents, errors)

    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        print(
            "%s  %s/%s  %d forms  %s"
            % (
                path.relative_to(ROOT).as_posix(),
                document["namespace"],
                document["version"],
                len(document["forms"]),
                digest(document),
            )
        )

    for error in errors:
        print("error: %s" % error)
    if errors:
        print("FAIL (%d error(s))" % len(errors))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
