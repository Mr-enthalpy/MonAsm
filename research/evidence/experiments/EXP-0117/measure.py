#!/usr/bin/env python3
"""Measure the `EXP-0117` `adr` vector and derive its fields.

Eight instructions, one form (`aarch64:adr/x64-imm21`):

- five literal displacements (`#0`, `#8`, `#-8`, `#1048575`, `#-1048576`), the
  last two being the signed 21-bit ends;
- three symbol targets: `.L1` at the `adr x5` site (displacement 0), `.Lback`
  at offset 0 (`-24`) and `.L1` again from offset 28 (`-8`).

The expected words are derived here from the MRS node, not from the assembler:
`ADR_only_pcreladdr` fixes bit 31 = 0 and splits a signed 21-bit value over
`immlo` (bits 30-29, the low two bits) and `immhi` (bits 23-5, bits 2-20), with
`Rd` at 0-5. Only after the derivation agrees word for word does the script
compare with `llvm-mc` 23.1.2, and `llvm-objdump -d` is the second read: it
prints `P + v`, so a wrong reference point or a wrong split shows up as a
different target address.

A second, four-instruction vector (`A64-P23-adr-vs-adrp.s`) measures the `adr`
vs `adrp` contrast for `EC-43`: the same two fields under `adr` and `adrp`,
with `adrp`'s operand divided into pages, so `#4096` lands as field content 1.
`encode()` is reused with the `ADRP_only_pcreladdr` fixed bits, and the script
checks that bit 31 names the mnemonic.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0117/measure.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = HERE / "A64-P23-adr-imm21.s"
CONTRAST = HERE / "A64-P23-adr-vs-adrp.s"
MRS = ROOT / "research/external/arm-mrs/Instructions.json"

# rd, displacement in bytes. The three symbol rows are listed with the
# displacement the symbol offsets in the source produce.
ROWS = [
    (0, 0),
    (1, 8),
    (2, -8),
    (3, 1048575),
    (4, -1048576),
    (5, 0),      # adr x5, .L1   (.L1 = 20, site = 20)
    (6, -24),    # adr x6, .Lback (.Lback = 0, site = 24)
    (7, -8),     # adr x7, .L1   (.L1 = 20, site = 28)
]

LINE = re.compile(r"^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)$")
SPLIT = re.compile(r"^x(\d+), (0x[0-9a-f]+)")

# The `adr`/`adrp` contrast (`EC-43`): same fields, bit 31 apart, but the
# value means bytes on one row and 4 KiB pages on the other. Every operand here
# is a PC offset, so instruction 3's `#4096` becomes page delta 1.
CONTRAST_ROWS = [
    ("adr", 0, 0),
    ("adrp", 0, 0),
    ("adr", 1, 8),
    ("adrp", 1, 4096),
]


def mrs_fields(name: str = "ADR_only_pcreladdr") -> dict:
    """Read the named node's fixed bits and variable ranges."""
    document = json.loads(MRS.read_text(encoding="utf-8"))

    def walk(node):
        if isinstance(node, list):
            for item in node:
                for found in walk(item):
                    yield found
            return
        if not isinstance(node, dict):
            return
        yield node
        for child in node.get("children") or []:
            for item in walk(child):
                yield item

    for node in walk(document["instructions"]):
        if (node.get("name") == name
                and str(node.get("_type", "")).endswith(
                    "Instruction.Instruction")):
            values = node["encoding"]["values"]
            fixed = 0
            ranges = {}
            for field in values:
                span = field["range"]
                raw = (field.get("value") or {}).get("value")
                text = raw.strip("'")
                if "x" in text:
                    ranges[field["name"]] = (span["start"], span["width"])
                else:
                    fixed |= int(text, 2) << span["start"]
            return {"fixed": fixed, "ranges": ranges}
    raise SystemExit("%s not found" % name)


def encode(fields: dict, rd: int, displacement: int) -> int:
    if not -1048576 <= displacement <= 1048575:
        raise SystemExit("displacement %d leaves the signed 21-bit field"
                         % displacement)
    value = displacement & 0x1FFFFF
    immlo_lsb, immlo_width = fields["ranges"]["immlo"]
    immhi_lsb, immhi_width = fields["ranges"]["immhi"]
    rd_lsb, rd_width = fields["ranges"]["Rd"]
    if (immlo_lsb, immlo_width) != (29, 2):
        raise SystemExit("immlo is not at 29+2")
    if (immhi_lsb, immhi_width) != (5, 19):
        raise SystemExit("immhi is not at 5+19")
    if (rd_lsb, rd_width) != (0, 5):
        raise SystemExit("Rd is not at 0+5")
    word = fields["fixed"]
    word |= (value & 0x3) << immlo_lsb
    word |= (value >> 2) << immhi_lsb
    word |= rd << rd_lsb
    return word


def run(arguments: list) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit("%s failed: %s" % (arguments[0], result.stderr))
    return result.stdout


def main() -> int:
    fields = mrs_fields()
    expected = b"".join(encode(fields, rd, disp).to_bytes(4, "little")
                        for rd, disp in ROWS)

    with tempfile.TemporaryDirectory() as temporary:
        workdir = Path(temporary)
        obj = workdir / "A64-P23-adr-imm21.o"
        image = workdir / "A64-P23-adr-imm21.bin"
        run(["llvm-mc", "-triple=aarch64", "-filetype=obj", str(SOURCE),
             "-o", str(obj)])
        run(["llvm-objcopy", "-O", "binary", "--only-section=.text",
             str(obj), str(image)])
        measured = image.read_bytes()
        listing = [LINE.match(line) for line in
                   run(["llvm-objdump", "-d", str(obj)]).splitlines()]
        listing = [match for match in listing if match]

    if measured != expected:
        raise SystemExit("assembly is %s, field derivation says %s"
                         % (measured.hex(), expected.hex()))
    if len(listing) != len(ROWS):
        raise SystemExit("expected %d disassembled lines, found %d"
                         % (len(ROWS), len(listing)))

    lines = ["fixture bytes %d: %s" % (len(measured), measured.hex())]
    for index, (rd, displacement) in enumerate(ROWS):
        offset = index * 4
        word = int.from_bytes(measured[offset: offset + 4], "little")
        if word != encode(fields, rd, displacement):
            raise SystemExit("word %d: %08x" % (index, word))
        address, encoding, mnemonic, operands = (
            listing[index].group(1), listing[index].group(2),
            listing[index].group(3), listing[index].group(4).strip())
        if mnemonic != "adr" or int(encoding, 16) != word:
            raise SystemExit("disassembly says %s %s" % (mnemonic, encoding))
        split = SPLIT.match(operands)
        if split is None or int(split.group(1)) != rd:
            raise SystemExit("disassembly operands %r" % operands)
        target = int(split.group(2), 16)
        wanted = (offset + displacement) & 0xFFFFFFFFFFFFFFFF
        if int(address, 16) != offset or target != wanted:
            raise SystemExit("row %d: target 0x%x, expected 0x%x"
                             % (index, target, wanted))
        lines.append(
            "%-10s %s  imm=%d  %s" % (
                "adr x%d" % rd, measured[offset: offset + 4].hex(),
                displacement, operands))

    lines.append("")
    lines.append("Bit 31 is 0 (`adr`), `immlo` holds the low two bits of the")
    lines.append("signed 21-bit byte displacement and `immhi` bits 2-20. The")
    lines.append("last three rows are symbols: 0, -24 and -8 bytes away, so the")
    lines.append("reference point is the instruction address, not its end.")

    contrast_fields = mrs_fields("ADRP_only_pcreladdr")
    contrast_expected = []
    for index, (mnemonic, rd, operand) in enumerate(CONTRAST_ROWS):
        if mnemonic == "adr":
            contrast_expected.append(encode(fields, rd, operand))
        else:
            offset = index * 4
            delta = (((offset + operand) & ~0xFFF) - (offset & ~0xFFF)) >> 12
            contrast_expected.append(encode(contrast_fields, rd, delta))
    with tempfile.TemporaryDirectory() as temporary:
        workdir = Path(temporary)
        obj = workdir / "A64-P23-adr-vs-adrp.o"
        image = workdir / "A64-P23-adr-vs-adrp.bin"
        run(["llvm-mc", "-triple=aarch64", "-filetype=obj", str(CONTRAST),
             "-o", str(obj)])
        run(["llvm-objcopy", "-O", "binary", "--only-section=.text",
             str(obj), str(image)])
        contrast = image.read_bytes()
        contrast_listing = [LINE.match(line) for line in
                            run(["llvm-objdump", "-d", str(obj)]).splitlines()]
        contrast_listing = [match for match in contrast_listing if match]
    if len(contrast) != len(CONTRAST_ROWS) * 4:
        raise SystemExit("contrast image is %d bytes" % len(contrast))
    lines.append("")
    lines.append("adr/adrp contrast (`EC-43`), same split, bit 31 apart:")
    for index, (mnemonic, rd, operand) in enumerate(CONTRAST_ROWS):
        offset = index * 4
        word = int.from_bytes(contrast[offset: offset + 4], "little")
        if word != contrast_expected[index]:
            raise SystemExit("contrast word %d: %08x, derived %08x"
                             % (index, word, contrast_expected[index]))
        if (mnemonic == "adr") != ((word >> 31) == 0):
            raise SystemExit("bit 31 does not name the mnemonic")
        if contrast_listing[index].group(3) != mnemonic:
            raise SystemExit("disassembly says %s for %s"
                             % (contrast_listing[index].group(3), mnemonic))
        lines.append("  %-4s x%d #%d  %s" % (
            mnemonic, rd, operand, contrast[offset: offset + 4].hex()))
    lines.append("Row 1 is the clean pair: the same zeros under `adr` and")
    lines.append("`adrp` differ only in bit 31. Row 3 states 4096 bytes and")
    lines.append("lands as page delta 1, so one shared row would have to read")
    lines.append("the number to know whether it means bytes or pages.")
    with (HERE / "direction.txt").open("w", encoding="utf-8",
                                      newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    with (HERE / "A64-P23-adr-imm21-bytes.txt").open(
            "w", encoding="utf-8", newline="\n") as handle:
        handle.write(" ".join("%02x" % byte for byte in measured) + "\n")

    print("bytes: %d" % len(measured))
    print("output sha256: %s" % hashlib.sha256(measured).hexdigest())
    print("input sha256: %s" % hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    print("contrast sha256: %s" % hashlib.sha256(CONTRAST.read_bytes()).hexdigest())
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
