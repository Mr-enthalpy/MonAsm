#!/usr/bin/env python3
"""Measure the `EXP-0118` `mul`/`csel` vector and derive its fields.

Eight instructions, four forms (`ADR-0119`):

- `mul` at 32 and 64 bits: the `MADD` alias with `Ra` (bits 14-10) fixed to
  31. One row puts 31 in `Rm` (`wzr`), because these rows read a plain
  register number and exclude nothing;
- `csel` at 32 and 64 bits, with the condition at bits 12-15. The four rows
  use `eq` (0), `ne` (1), `al` (14) and `nv` (15), the last two because the
  ISA defines all sixteen values.

The expected words are derived here from the MRS nodes, not from the
assembler: `MADD_32A_dp_3src`/`MADD_64A_dp_3src` fix `op54`/`op1`/`op31`/`o0`
and leave `Rd`/`Rn`/`Rm`/`Ra`; `CSEL_32_condsel`/`CSEL_64_condsel` fix the
same class of bits and leave `Rd`/`Rn`/`Rm`/`cond`. Only after the derivation
agrees word for word does the script compare with `llvm-mc` 23.1.2, and
`llvm-objdump -d` is the second read of the mnemonic and the operands.

A four-instruction second vector measures the two contrasts that the new
tables rely on:

- `mul x0, x1, x2` vs `madd x0, x1, x2, x3`: the same word except bits
  14-10, which is why the alias is a one-field pin and not a second opcode
  (`EC-44`);
- `csel x0, x1, x2, eq` vs `csinc x0, x1, x2, eq`: the same word except bit
  10 (`o2`), which the CSEL node fixes and the CSINC node does not.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0118/measure.py
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
SOURCE = HERE / "A64-P24-mul-csel.s"
CONTRAST = HERE / "A64-P24-mul-vs-madd.s"
MRS = ROOT / "research/external/arm-mrs/Instructions.json"

CONDITIONS = {0: "eq", 1: "ne", 12: "gt", 14: "al", 15: "nv"}

# (mnemonic, width, rd, rn, rm, cond). `cond` is None on the `mul` rows.
ROWS = [
    ("mul", "w32", 2, 3, 4, None),
    ("mul", "x64", 5, 6, 7, None),
    ("mul", "w32", 0, 1, 31, None),
    ("csel", "w32", 8, 9, 10, 0),
    ("csel", "x64", 11, 12, 13, 1),
    ("csel", "x64", 0, 1, 2, 14),
    ("csel", "w32", 3, 4, 5, 15),
    ("csel", "x64", 31, 0, 0, 12),
]

LINE = re.compile(r"^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)$")


def mrs_fields(name: str) -> dict:
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


def check_ranges(fields: dict, wanted: dict) -> None:
    for name, span in wanted.items():
        if fields["ranges"].get(name) != span:
            raise SystemExit("%s is not at %d+%d (found %r)"
                             % (name, span[0], span[1],
                                fields["ranges"].get(name)))


def encode_mul(fields: dict, rd: int, rn: int, rm: int) -> int:
    check_ranges(fields, {"Rd": (0, 5), "Rn": (5, 5), "Rm": (16, 5),
                          "Ra": (10, 5)})
    word = fields["fixed"]
    word |= rm << 16
    word |= 31 << 10          # the alias's Ra = 31
    word |= rn << 5
    word |= rd
    return word


def encode_csel(fields: dict, rd: int, rn: int, rm: int, cond: int) -> int:
    check_ranges(fields, {"Rd": (0, 5), "Rn": (5, 5), "Rm": (16, 5),
                          "cond": (12, 4)})
    if not 0 <= cond < 16:
        raise SystemExit("cond %d leaves the four-bit field" % cond)
    word = fields["fixed"]
    word |= rm << 16
    word |= cond << 12
    word |= rn << 5
    word |= rd
    return word


def register(width: str, number: int) -> str:
    if number == 31:
        return "wzr" if width == "w32" else "xzr"
    return ("w%d" if width == "w32" else "x%d") % number


def render(mnemonic: str, width: str, rd: int, rn: int, rm: int,
           cond) -> tuple:
    operands = [register(width, rd), register(width, rn),
                register(width, rm)]
    if cond is not None:
        operands.append(CONDITIONS[cond])
    return mnemonic, ", ".join(operands)


def run(arguments: list) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit("%s failed: %s" % (arguments[0], result.stderr))
    return result.stdout


def assemble(source: Path, name: str) -> tuple:
    with tempfile.TemporaryDirectory() as temporary:
        workdir = Path(temporary)
        obj = workdir / (name + ".o")
        image = workdir / (name + ".bin")
        run(["llvm-mc", "-triple=aarch64", "-filetype=obj", str(source),
             "-o", str(obj)])
        run(["llvm-objcopy", "-O", "binary", "--only-section=.text",
             str(obj), str(image)])
        measured = image.read_bytes()
        listing = [LINE.match(line) for line in
                   run(["llvm-objdump", "-d", str(obj)]).splitlines()]
    return measured, [match for match in listing if match]


def main() -> int:
    expected = bytearray()
    for mnemonic, width, rd, rn, rm, cond in ROWS:
        if mnemonic == "mul":
            node = ("MADD_32A_dp_3src" if width == "w32"
                    else "MADD_64A_dp_3src")
        else:
            node = ("CSEL_32_condsel" if width == "w32"
                    else "CSEL_64_condsel")
        fields = mrs_fields(node)
        if mnemonic == "mul":
            word = encode_mul(fields, rd, rn, rm)
        else:
            word = encode_csel(fields, rd, rn, rm, cond)
        expected += word.to_bytes(4, "little")

    measured, listing = assemble(SOURCE, "A64-P24-mul-csel")
    if measured != bytes(expected):
        raise SystemExit("assembly is %s, field derivation says %s"
                         % (measured.hex(), bytes(expected).hex()))
    if len(listing) != len(ROWS):
        raise SystemExit("expected %d disassembled lines, found %d"
                         % (len(ROWS), len(listing)))

    lines = ["fixture bytes %d: %s" % (len(measured), measured.hex())]
    for index, (mnemonic, width, rd, rn, rm, cond) in enumerate(ROWS):
        offset = index * 4
        word = int.from_bytes(measured[offset: offset + 4], "little")
        address, encoding, seen, operands = (
            listing[index].group(1), listing[index].group(2),
            listing[index].group(3), listing[index].group(4).strip())
        wanted_mnemonic, wanted_operands = render(
            mnemonic, width, rd, rn, rm, cond)
        if seen != mnemonic or int(encoding, 16) != word:
            raise SystemExit("disassembly says %s %s" % (seen, encoding))
        if operands != wanted_operands:
            raise SystemExit("disassembly operands %r, expected %r"
                             % (operands, wanted_operands))
        if int(address, 16) != offset:
            raise SystemExit("row %d at 0x%s" % (index, address))
        lines.append("%-28s %s" % ("%s %s" % (wanted_mnemonic,
                                             wanted_operands),
                                   measured[offset: offset + 4].hex()))

    lines.append("")
    lines.append("`mul` fixes bits 14-10 (`Ra`) to 31 and reads Rd/Rn/Rm as")
    lines.append("plain register numbers, so `wzr` is 31 and not an excluded")
    lines.append("value. `csel` fixes `op`/`S` at 30-29 and `o2` at 10 and")
    lines.append("reads bits 12-15 as the condition; all sixteen values are")
    lines.append("defined, including `al` (14) and `nv` (15).")

    contrast, contrast_listing = assemble(CONTRAST, "A64-P24-mul-vs-madd")
    if len(contrast) != 16:
        raise SystemExit("contrast image is %d bytes" % len(contrast))
    mul = int.from_bytes(contrast[0:4], "little")
    madd = int.from_bytes(contrast[4:8], "little")
    csel = int.from_bytes(contrast[8:12], "little")
    csinc = int.from_bytes(contrast[12:16], "little")
    if mul ^ madd != 0x7000:
        raise SystemExit("mul/madd differ in %08x" % (mul ^ madd))
    if (madd >> 10) & 0x1F != 3:
        raise SystemExit("madd's Ra is not 3: %08x" % madd)
    if csel ^ csinc != 0x400:
        raise SystemExit("csel/csinc differ in %08x" % (csel ^ csinc))
    for index, mnemonic in enumerate(("mul", "madd", "csel", "csinc")):
        if contrast_listing[index].group(3) != mnemonic:
            raise SystemExit("contrast row %d says %s"
                             % (index, contrast_listing[index].group(3)))
    lines.append("")
    lines.append("contrast (`EC-44` and the `csel` row):")
    lines.append("  mul   x0, x1, x2      %s" % contrast[0:4].hex())
    lines.append("  madd  x0, x1, x2, x3  %s   xor %04x (bits 14-10 only)"
                 % (contrast[4:8].hex(), mul ^ madd))
    lines.append("  csel  x0, x1, x2, eq  %s" % contrast[8:12].hex())
    lines.append("  csinc x0, x1, x2, eq  %s   xor %04x (bit 10 only)"
                 % (contrast[12:16].hex(), csel ^ csinc))
    lines.append("The alias is one pinned field over the base node, and the")
    lines.append("`csel` row is the CSEL node with `o2 = 0`, not the CSINC")
    lines.append("shape with a condition.")

    with (HERE / "direction.txt").open("w", encoding="utf-8",
                                       newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    with (HERE / "A64-P24-mul-csel-bytes.txt").open(
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
