#!/usr/bin/env python3
"""EXP-0004: verify the x86-64 v0 definition table against llvm-mc's decoder.

The table (`definitions/x86_64/0.1.0.json`) is the thing under test. A second,
independent implementation of `07_definition_format.md` §4.1 lives here: it reads
the table, applies the placement rule, and produces bytes. `llvm-mc
-disassemble` then reads those bytes back and must print the operands that were
planned. Neither side is the materializer, so a shared bug in the Rust code
cannot hide a wrong table.

This is deliberately not a self-check: the expected operand text comes from the
*inputs* of each case, not from the encoder.

Usage:
    python exp0004.py                # print the measured tables
    python exp0004.py --emit         # rewrite the tables in README.md

The LLVM directory can be overridden with FMP_LLVM_BIN.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LLVM_BIN = Path(os.environ.get("FMP_LLVM_BIN", r"C:\Users\hanni\Tools\llvm\bin"))
LLVM_MC = LLVM_BIN / "llvm-mc.exe"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DEFINITION = ROOT / "definitions/x86_64/0.1.0.json"
README = HERE / "README.md"

REGS = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi"]


# --- the second implementation of the placement rule -----------------------


def encode(form, operands):
    """Apply `07_definition_format.md` §4.1 to one form and a list of operands."""
    size = len(bytes.fromhex(form["template"]))
    bits = int.from_bytes(bytes.fromhex(form["template"]), "little")
    slots = form["slots"]
    if len(operands) != len(slots):
        raise ValueError("%s: operand count" % form["form_id"])
    for slot, value in zip(slots, operands):
        if slot["from"] == "reg_number":
            width = sum(p["width"] for p in slot["placements"])
            if not 0 <= value < (1 << width):
                raise ValueError("%s: register %d needs %d bits"
                                 % (form["form_id"], value, width))
            masked = value
        else:
            bounds = slot["range"]
            low = -(1 << (bounds["bits"] - 1)) if bounds["signed"] else 0
            high = (1 << (bounds["bits"] - (1 if bounds["signed"] else 0))) - 1
            if not low <= value <= high:
                raise ValueError("%s: value %d outside [%d, %d]"
                                 % (form["form_id"], value, low, high))
            masked = value & ((1 << bounds["bits"]) - 1)
        position = 0
        # First placement holds the most significant bits, so walk from the last.
        for placement in reversed(slot["placements"]):
            chunk = (masked >> position) & ((1 << placement["width"]) - 1)
            position += placement["width"]
            bits |= chunk << placement["bit_offset"]
    return bits.to_bytes(size, "little")


# --- the case list ---------------------------------------------------------


def cases():
    """(form_id, operand values, expected decoded text) for every v0 form."""
    out = []
    for dest in range(8):
        for src in range(8):
            text = "movq %%%s, %%%s" % (REGS[src], REGS[dest])
            out.append(("x86:mov/rm-r64/legacy", [dest, src], text))
            out.append(("x86:mov/r64-rm/legacy", [dest, src], text))
    for dest in range(8):
        for imm in (-128, -1, 0, 1, 127):
            out.append(
                ("x86:add/rm64-imm8/legacy", [dest, imm], "addq $%d, %%%s" % (imm, REGS[dest]))
            )
        for imm in (-2147483648, -1, 0, 1, 2147483647):
            out.append(
                ("x86:add/rm64-imm32/legacy", [dest, imm], "addq $%d, %%%s" % (imm, REGS[dest]))
            )
    for imm in (-2147483648, -1, 0, 1, 2147483647):
        out.append(("x86:add/rax-imm32/legacy", [imm], "addq $%d, %%rax" % imm))
    for disp in (-128, -1, 0, 1, 127):
        out.append(("x86:jmp/rel8/legacy", [disp], "jmp %d" % disp))
    for disp in (-2147483648, -1, 0, 1, 2147483647):
        out.append(("x86:jmp/rel32/legacy", [disp], "jmp %d" % disp))
    return out


# --- the oracle ------------------------------------------------------------


def disassemble_all(byte_lines):
    payload = "\n".join(byte_lines) + "\n"
    completed = subprocess.run(
        [str(LLVM_MC), "-triple=x86_64", "-disassemble"],
        input=payload,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "llvm-mc -disassemble failed: %s" % completed.stderr.strip()
        )
    return [normalise(line) for line in completed.stdout.splitlines()]


def normalise(text):
    text = text.split("#", 1)[0].strip()
    return re.sub(r"\s+", " ", text)


def measure():
    document = json.loads(DEFINITION.read_text(encoding="utf-8"))
    forms = {form["form_id"]: form for form in document["forms"]}
    selected = cases()

    unknown = sorted({form_id for form_id, _, _ in selected} - set(forms))
    if unknown:
        raise RuntimeError("cases name forms the definition lacks: %s" % unknown)
    uncovered = sorted(set(forms) - {form_id for form_id, _, _ in selected})
    if uncovered:
        raise RuntimeError("definition forms with no check case: %s" % uncovered)

    lines = []
    expected = []
    for form_id, operands, text in selected:
        data = encode(forms[form_id], operands)
        lines.append(" ".join("0x%02x" % byte for byte in data))
        expected.append((form_id, data.hex(), operands, text))

    got = disassemble_all(lines)
    if len(got) != len(expected):
        raise RuntimeError(
            "expected %d decode lines, got %d" % (len(expected), len(got))
        )

    results = []
    for (form_id, hex_bytes, operands, want), have in zip(expected, got):
        results.append(
            {
                "form_id": form_id,
                "bytes": hex_bytes,
                "operands": operands,
                "expected": want,
                "decoded": have,
                "ok": have == want,
            }
        )
    return document, results


def render_forms(document, results):
    by_form = {}
    for row in results:
        by_form.setdefault(row["form_id"], []).append(row)
    lines = [
        "| `form_id` | cases | pass | sample plan | sample bytes | decodes as |",
        "|---|---|---|---|---|---|",
    ]
    for form in document["forms"]:
        rows = by_form[form["form_id"]]
        ok = sum(1 for row in rows if row["ok"])
        sample = rows[0]
        lines.append(
            "| `%s` | %d | %d | `%s` | `%s` | `%s` |"
            % (
                form["form_id"],
                len(rows),
                ok,
                sample["operands"],
                sample["bytes"],
                sample["decoded"],
            )
        )
    return "\n".join(lines)


def canonical_bytes(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def measure_digest(document):
    """Both halves of the OD-06 test: a rule change breaks, formatting does not."""
    base = hashlib.sha256(canonical_bytes(document)).hexdigest()

    reordered = json.loads(json.dumps(document))
    reordered = {key: reordered[key] for key in reversed(list(reordered))}
    reserialised = hashlib.sha256(canonical_bytes(reordered)).hexdigest()

    mutated = json.loads(json.dumps(document))
    ranged = [
        slot
        for form in mutated["forms"]
        for slot in form["slots"]
        if slot["from"] == "operand_value"
    ]
    ranged[0]["range"]["bits"] = 9
    changed = hashlib.sha256(canonical_bytes(mutated)).hexdigest()

    return base, reserialised, changed


def render_digest(document):
    base, reserialised, changed = measure_digest(document)
    rows = [
        ("definition as stored", base),
        ("same document, keys in reverse order", reserialised),
        ("one rule changed (`imm8` range, 8 -> 9 bits)", changed),
    ]
    lines = ["| Input | sha256 |", "|---|---|"]
    for label, value in rows:
        lines.append("| %s | `%s` |" % (label, value))
    lines.append("")
    lines.append(
        "verdict: formatting-preserving change keeps the digest: **%s**; "
        "one-bit rule change breaks it: **%s**."
        % (reserialised == base, changed != base)
    )
    return "\n".join(lines)


def main() -> int:
    document, results = measure()
    failed = [row for row in results if not row["ok"]]
    forms_table = render_forms(document, results)
    digest_table = render_digest(document)

    if "--emit" in sys.argv:
        text = README.read_text(encoding="utf-8")
        for start, end, table in (
            ("<!-- forms-table:start -->", "<!-- forms-table:end -->", forms_table),
            ("<!-- digest-table:start -->", "<!-- digest-table:end -->", digest_table),
        ):
            if start not in text or end not in text:
                print("README is missing %s" % start, file=sys.stderr)
                return 1
            head, rest = text.split(start, 1)
            _, tail = rest.split(end, 1)
            text = head + start + "\n" + table + "\n" + end + tail
        with README.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("rewrote the measured tables in %s" % README)
    else:
        print(forms_table)
        print()
        print(digest_table)

    if failed:
        for row in failed[:20]:
            print(
                "MISMATCH %s ops=%s bytes=%s expected=%r decoded=%r"
                % (row["form_id"], row["operands"], row["bytes"], row["expected"], row["decoded"])
            )
        print("FAIL (%d of %d cases)" % (len(failed), len(results)))
        return 1
    print("OK (%d cases, %d forms)" % (len(results), len(document["forms"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
