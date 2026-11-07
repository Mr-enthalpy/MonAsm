#!/usr/bin/env python3
"""Write the two `X86-P70` positive fixtures and their `oracle.json` files.

`X86-P70-abs32-symbol` puts one external symbol in the absolute 32-bit field
of nine instructions (eight `disp32` slots at four value widths, both
directions and one EVEX vector row, plus one `imm32` slot). Every fixup is
`emit_relocation`, so the bytes stay zero and the reference travels in nine
records.

`X86-P70-abs32-symbol-resolved` resolves the same field in place against a
defined symbol in a `.text` placed at `0x1000` by `ld.lld`, with two non-zero
addends.

The instruction bytes come from `measure.py`'s recorded `probe-bytes.txt` and
`resolved-bytes.txt` (written from `llvm-objcopy` output, never from the
materializer); this script only carries them into `expected.bin`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0095/fixture_p70.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
EXPERIMENT = ROOT / "research/evidence/experiments/EXP-0095"
DEFINITION = ROOT / "definitions/x86_64/0.65.0.json"

VERSION = "0.65.0"
DIGEST = "sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a"

DISP = ("disp", "x86.imm", "disp32", {})
IMM = ("imm", "x86.imm", "imm32", {})


def gpr(role, kind, target_type, reg):
    return (role, kind, target_type, {"reg": reg})


# (form_id, operands, size, field lsb, addend, measured hex)
EMIT = [
    ("x86:mov/r32-abs32/legacy",
     [gpr("dest", "x86.gpr32", "r32", 0), DISP], 7, 24, 0,
     "8b042500000000"),
    ("x86:mov/abs32-r32/legacy",
     [gpr("src", "x86.gpr32", "r32", 0), DISP], 7, 24, 0,
     "89042500000000"),
    ("x86:mov/r32-ext-abs32/legacy",
     [gpr("dest", "x86.gpr32", "r32", 8), DISP], 8, 32, 0,
     "448b042500000000"),
    ("x86:mov/r64-abs32/legacy",
     [gpr("dest", "x86.gpr64", "r64", 0), DISP], 8, 32, 0,
     "488b042500000000"),
    ("x86:mov/abs32-r16-ext/legacy",
     [gpr("src", "x86.gpr16", "r16", 9), DISP], 9, 40, 0,
     "6644890c2500000000"),
    ("x86:mov/abs32-r8h/legacy",
     [gpr("src", "x86.gpr8h", "r8h", 4), DISP], 7, 24, 0,
     "88242500000000"),
    ("x86:mov/r8-abs32/legacy",
     [gpr("dest", "x86.gpr8", "r8", 0), DISP], 7, 24, 0,
     "8a042500000000"),
    ("x86:vmovaps/zmm-abs32/evex",
     [gpr("dest", "x86.zmm", "zmm", 1), DISP], 11, 56, 0,
     "62f17c48280c2500000000"),
    ("x86:add/rm64-imm32/legacy",
     [gpr("dest", "x86.gpr64", "rm64", 0), IMM], 7, 24, 0,
     "4881c000000000"),
]

RESOLVED = [
    ("x86:mov/r64-abs32/legacy",
     [gpr("dest", "x86.gpr64", "r64", 0), DISP], 8, 32, 0,
     "488b04251e100000"),
    ("x86:mov/r32-abs32/legacy",
     [gpr("dest", "x86.gpr32", "r32", 0), DISP], 7, 24, 4,
     "8b042522100000"),
    ("x86:mov/abs32-r32/legacy",
     [gpr("src", "x86.gpr32", "r32", 1), DISP], 7, 24, 0,
     "890c251e100000"),
    ("x86:mov/abs32-r16/legacy",
     [gpr("src", "x86.gpr16", "r16", 2), DISP], 8, 32, 2,
     "6689142520100000"),
    ("x86:mov/r8-abs32/legacy",
     [gpr("dest", "x86.gpr8", "r8", 0), DISP], 7, 24, 0,
     "8a04251e100000"),
]


def operand(entry):
    role, kind, target_type, payload = entry
    return {"role": role, "kind": kind, "target_type": target_type,
            "payload": payload, "modifiers": []}


def field_lsb(form, role):
    """The table's single `operand_value` placement for `role`."""
    for slot in form["slots"]:
        if slot["role"] == role and slot["from"] == "operand_value":
            placements = slot["placements"]
            if len(placements) != 1 or placements[0]["width"] != 32:
                raise SystemExit("%s: unexpected field shape" % form["form_id"])
            return placements[0]["bit_offset"]
    raise SystemExit("%s: no operand_value slot for %s"
                     % (form["form_id"], role))


def build(stem, plan, measured_file, symbol, base_address, mode):
    table = {form["form_id"]: form
             for form in json.loads(DEFINITION.read_text(encoding="utf-8"))["forms"]}
    data = bytes.fromhex((EXPERIMENT / measured_file).read_text(
        encoding="utf-8").strip())
    total = sum(entry[2] for entry in plan)
    if len(data) != total:
        raise SystemExit("%s: measured %d bytes, plan says %d"
                         % (stem, len(data), total))

    offset = 0
    cursor = 0
    fragments = []
    instructions = []
    fixups = []
    for index, (form_id, operands, size, lsb, addend, expected) in enumerate(
            plan, 1):
        instruction_id = "I%04d" % index
        form = table[form_id]
        actual = field_lsb(form, operands[-1][0])
        if actual != lsb:
            raise SystemExit("%s: %s says lsb %d, table says %d"
                             % (stem, form_id, lsb, actual))
        chunk = data[cursor:cursor + size].hex()
        if chunk != expected:
            raise SystemExit("%s: %s measured %s, expected %s"
                             % (stem, instruction_id, chunk, expected))
        fragments.append({"offset": offset, "size": size,
                          "kind": "instruction",
                          "instruction_id": instruction_id})
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": [operand(item) for item in operands],
            "expected_size": size,
        })
        fixups.append({
            "fixup_id": "F%04d" % index,
            "section_id": ".text",
            "offset": offset,
            "field_descriptor": [{"lsb": lsb, "width": 32}],
            "target": {"kind": "symbol", "symbol_id": symbol},
            "addend": addend,
            "pc_reference_rule": "none",
            "value_transform": "identity",
            "range_constraint": {"signed": True, "bits": 32, "align_bits": 0},
            "resolution_mode": mode,
        })
        offset += size
        cursor += size

    section = {
        "section_id": ".text",
        "section_kind": "code",
        "image_backed": True,
        "declared_size": total,
        "fragments": fragments,
    }
    if base_address is not None:
        section["base_address"] = base_address

    document = {
        "format_version": "fmp/0.1",
        "target_identity": {
            "isa_family": "x86",
            "isa_variant": "x86-64",
            "execution_mode": "64",
            "enabled_extensions": ["avx", "avx512f", "avx512vl"],
            "feature_constraints": [],
            "byte_order": "little",
            "address_width": 64,
        },
        "definition_identity": {
            "namespace": "monasm.isa.x86",
            "version": VERSION,
            "digest": DIGEST,
        },
        "output_contract": {
            "artifact": "bytes",
            "section_order": [".text"],
            "fixup_record_order": "section_id,offset,fixup_id",
            "include_symbol_table": False,
            "emit_fixups": True,
        },
        "sections": [section],
        "symbols": (
            [{"symbol_id": "ext", "name": "ext", "kind": "external",
              "binding": "global"}]
            if symbol == "ext" else
            [{"symbol_id": "L1", "name": "L1", "kind": "defined",
              "binding": "local", "section_id": ".text", "offset": 30}]),
        "instructions": instructions,
        "fixups": fixups,
    }

    target = FIXTURES / (stem + ".fmp.json")
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2) + "\n")
    binary = FIXTURES / (stem + ".expected.bin")
    binary.write_bytes(data)
    # `records` is what the emitter writes: only `emit_relocation` produces a
    # record, so a `resolve_in_place` fixture emits none even though it has
    # fixups.
    records = len(fixups) if mode == "emit_relocation" else 0
    return total, records


ORACLE = {
    "X86-P70-abs32-symbol": {
        "tool": "llvm-mc 23.1.2 + llvm-objcopy",
        "asm": "probe.asm",
        "command": ("llvm-mc -triple=x86_64 -filetype=obj "
                    "research/evidence/experiments/EXP-0095/probe.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "notes": (
            "One external symbol `ext` in nine absolute 32-bit content "
            "fields, all `emit_relocation`: the eight `disp32` rows are "
            "7/7/8/8/9/7/7/11 bytes with the field at [24,32], [24,32], "
            "[32,32], [32,32], [40,32], [24,32], [24,32] and [56,32], and "
            "`addq $ext, %rax` puts the same symbol in an `imm32` slot at "
            "[24,32]. Every field is zero in the bytes: `llvm-mc "
            "-disassemble` reads `0`, and each record carries the symbol, "
            "not a value. input_sha256 is probe.asm; output_sha256 is the "
            "71-byte .text."),
        "relocation_check": (
            "llvm-readobj --relocations reports nine `R_X86_64_32S ext 0x0` "
            "records at 0x3, 0xA, 0x12, 0x1A, 0x23, 0x2A, 0x31, 0x3C and "
            "0x43"),
    },
    "X86-P70-abs32-symbol-resolved": {
        "tool": "llvm-mc 23.1.2 + ld.lld 23.1.2 + llvm-objcopy",
        "asm": "resolved.asm",
        "command": ("llvm-mc -triple=x86_64 -filetype=obj "
                    "research/evidence/experiments/EXP-0095/resolved.asm -o "
                    "out.o && ld.lld -m elf_x86_64 --image-base=0 -Ttext 0x1000 "
                    "-o out.elf out.o && llvm-objcopy -O binary "
                    "--only-section=.text out.elf out.bin"),
        "notes": (
            "The same field resolved in place. `.text` is bound to 0x1000 and "
            "`L1` sits at offset 30, so S = 0x101e; the five displacements are "
            "0x101e, 0x1022 (addend 4), 0x101e, 0x1020 (addend 2) and 0x101e, "
            "and the bytes are the linker's, not the materializer's. Before "
            "linking, `llvm-readobj --relocations` reports five "
            "`R_X86_64_32S .text` records with addends 0x1E, 0x22, 0x1E, 0x20 "
            "and 0x1E, which is the same arithmetic the plan states. "
            "`resolve_in_place` writes the bytes and emits no record, so "
            "`records: 0` is five fixups applied, not zero fixups. "
            "input_sha256 is resolved.asm."),
        "relocation_check": (
            "llvm-nm on the linked image reports '000000000000101e t L1'"),
    },
}


def main() -> int:
    forms = {form["form_id"] for form in json.loads(
        DEFINITION.read_text(encoding="utf-8"))["forms"]}
    for form_id in [entry[0] for entry in EMIT + RESOLVED]:
        if form_id not in forms:
            raise SystemExit("%s is not in %s" % (form_id, VERSION))

    built = [
        ("X86-P70-abs32-symbol", build(
            "X86-P70-abs32-symbol", EMIT, "probe-bytes.txt", "ext", None,
            "emit_relocation")),
        ("X86-P70-abs32-symbol-resolved", build(
            "X86-P70-abs32-symbol-resolved", RESOLVED, "resolved-bytes.txt",
            "L1", 0x1000, "resolve_in_place")),
    ]

    for stem, (size, records) in built:
        oracle = ORACLE[stem]
        output = (FIXTURES / (stem + ".expected.bin")).read_bytes()
        document = {
            "tool": oracle["tool"],
            "version": "23.1.2",
            "command": oracle["command"],
            "kind": "assembler",
            "input_sha256": hashlib.sha256(
                (EXPERIMENT / oracle["asm"]).read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(output).hexdigest(),
            "size": size,
            "records": records,
            "notes": oracle["notes"],
            "relocation_check": oracle["relocation_check"],
        }
        path = FIXTURES / (stem + ".oracle.json")
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, indent=2) + "\n")
        print("%s: %d bytes, %d records" % (stem, size, records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
