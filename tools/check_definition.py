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
    "excluded",
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
            required = SLOT_KEYS - {"range", "excluded"}
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
                if not {"bit_offset", "width"} <= set(placement) or set(placement) - {
                    "bit_offset",
                    "width",
                    "invert",
                }:
                    fail(
                        errors,
                        slot_spot,
                        "placement keys must be bit_offset,width[,invert]",
                    )
                    continue
                if "invert" in placement and not isinstance(placement["invert"], bool):
                    fail(errors, slot_spot, "placement.invert must be a boolean")
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
            if "excluded" in slot:
                check_excluded(slot, slot_spot, total, errors)
        check_prefix_kinds(slots, bytes.fromhex(template), spot, errors)
    return document


def check_prefix_kinds(slots, template, spot, errors):
    """`ADR-0029`: a REX prefix re-labels 8-bit register numbers 4-7 as
    `spl`/`bpl`/`sil`/`dil`, so a high-byte slot cannot sit in a REX template
    and a REX-less low-byte slot must exclude 4-7.

    The `0x66` operand-size prefix can precede the REX byte (`ADR-0045`), so
    the search starts after it; `0x40`-`0x4F` is a REX prefix and never an
    opcode in 64-bit mode."""
    prefix = template[1:] if template[:1] == b"\x66" else template
    rex = bool(prefix) and 0x40 <= prefix[0] <= 0x4F
    for index, slot in enumerate(slots):
        kind = slot.get("kind")
        if kind == "x86.gpr8h" and rex:
            fail(
                errors,
                "%s/slots/%d" % (spot, index),
                "a REX-prefixed form cannot carry x86.gpr8h",
            )
        if kind == "x86.gpr8" and not rex:
            excluded = slot.get("excluded") or []
            if not all(value in excluded for value in (4, 5, 6, 7)):
                fail(
                    errors,
                    "%s/slots/%d" % (spot, index),
                    "a REX-less x86.gpr8 slot must exclude 4..7",
                )


def check_excluded(slot, spot, width_bits, errors):
    """`excluded` is a closed, strictly increasing list inside the slot's domain
    (ADR-0009). An empty list is not a statement; the key is omitted instead."""
    values = slot["excluded"]
    if not isinstance(values, list) or not values:
        fail(errors, spot, "excluded must be a non-empty array")
        return
    previous = None
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool):
            fail(errors, spot, "excluded values must be integers")
            return
        if previous is not None and value <= previous:
            fail(errors, spot, "excluded must be strictly increasing")
            return
        previous = value

    if "range" in slot:
        span = slot["range"]
        bits = span.get("bits")
        signed = span.get("signed")
        if not isinstance(bits, int) or isinstance(bits, bool):
            return
        if signed is True:
            low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        elif signed is False:
            low, high = 0, (1 << bits) - 1
        else:
            fail(errors, spot, "range.signed must be a boolean")
            return
    else:
        low, high = 0, (1 << width_bits) - 1

    for value in values:
        if value < low or value > high:
            fail(
                errors,
                spot,
                "excluded value %d is outside the slot domain [%d, %d]"
                % (value, low, high),
            )


def render_slot_cell(slot) -> str:
    pieces = []
    for placement in slot["placements"]:
        piece = "`[%d,%d]`" % (placement["bit_offset"], placement["width"])
        if placement.get("invert"):
            piece += " inverted"
        pieces.append(piece)
    placements = ", ".join(pieces)
    cell = "%s: `%s`/`%s` \u2192 %s" % (
        slot["role"],
        slot["kind"],
        slot["target_type"],
        placements,
    )
    if "excluded" in slot:
        cell += " (excl %s)" % ", ".join(str(value) for value in slot["excluded"])
    return cell


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
        match = re.match(r"^`((?:x86|aarch64|riscv):[^`]+)`$", cells[0])
        if not match:
            continue
        rows[match.group(1)] = cells

    expected = {}
    for document in documents:
        for form in document["forms"]:
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


def version_key(path: Path):
    """Order tables by numeric version, oldest first.

    §8 keeps one row per `form_id` and reads the newest table that still has it,
    so `0.10.0` must be processed after `0.9.0`. A plain `sorted()` compares
    file names as text and puts `0.10.0` between `0.1.0` and `0.2.0`, which
    would let the older row win.
    """
    try:
        parts = tuple(int(part) for part in path.stem.split("."))
    except ValueError:
        parts = (0,)
    return (path.parent.as_posix(), parts, path.stem)


def main() -> int:
    errors = []
    documents = []
    if not DEFINITIONS.is_dir():
        print("no definitions directory; nothing to check")
        return 0
    paths = sorted(DEFINITIONS.rglob("*.json"), key=version_key)
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
