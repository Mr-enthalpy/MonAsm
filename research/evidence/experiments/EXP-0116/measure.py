#!/usr/bin/env python3
"""Measure the `EXP-0116` load/store width vectors.

Eleven instructions, one per new row plus the signed `imm12` endpoints:

- the six loads (`lb`, `lh`, `lw`, `lbu`, `lhu`, `lwu`) and the three stores
  (`sb`, `sh`, `sw`) at `8(a1)`;
- `lb a0, -2048(a1)` and `sw a2, 2047(a1)`, the two ends of the signed
  12-bit field.

The expected bytes are derived here from the UDB field geometry
(`funct3 << 12 | opcode`, `imm` at 31-20 or 31-25|11-7, `xs1` at 19-15,
`xd` at 11-7, `xs2` at 24-20) and only then compared with the assembler. The
disassembly is the second read of the same bytes: `llvm-objdump -d` must name
the mnemonic the row claims.

`fence`, `ecall`/`ebreak`, the atomics and the compressed load/store family
stay out of the table; their encodings are not measured again here (`EC-24`
and `EXP-0096` already carry the `fence` bytes).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0116/measure.py
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "RV-P12-load-store-widths.s"

# mnemonic, kind, rd (loads) or rs2 (stores), rs1, imm
ROWS = [
    ("lb", "load", 10, 11, 8),
    ("lh", "load", 10, 11, 8),
    ("lw", "load", 10, 11, 8),
    ("lbu", "load", 10, 11, 8),
    ("lhu", "load", 10, 11, 8),
    ("lwu", "load", 10, 11, 8),
    ("sb", "store", 12, 11, 8),
    ("sh", "store", 12, 11, 8),
    ("sw", "store", 12, 11, 8),
    ("lb", "load", 10, 11, -2048),
    ("sw", "store", 12, 11, 2047),
]

FUNCT3 = {"lb": 0b000, "lh": 0b001, "lw": 0b010, "lbu": 0b100,
          "lhu": 0b101, "lwu": 0b110,
          "sb": 0b000, "sh": 0b001, "sw": 0b010}

LOAD_OPCODE = 0b0000011
STORE_OPCODE = 0b0100011

ABI = {10: "a0", 11: "a1", 12: "a2"}

LINE = re.compile(r"^\s*[0-9a-f]+:\s+(\S.*)$")


def encode(kind: str, funct3: int, value: int, rs1: int, imm: int) -> bytes:
    field = imm & 0xFFF
    if kind == "load":
        word = ((field << 20) | (rs1 << 15) | (funct3 << 12)
                | (value << 7) | LOAD_OPCODE)
    else:
        word = ((((field >> 5) & 0x7F) << 25) | (value << 20) | (rs1 << 15)
                | (funct3 << 12) | ((field & 0x1F) << 7) | STORE_OPCODE)
    return word.to_bytes(4, "little")


EXPECTED = b"".join(
    encode(kind, FUNCT3[mnemonic], value, rs1, imm)
    for mnemonic, kind, value, rs1, imm in ROWS
)


def run(arguments: list) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True,
                            check=True)
    return result.stdout


def decode(kind: str, word: int) -> dict:
    funct3 = (word >> 12) & 0x7
    if kind == "load":
        imm = (word >> 20) & 0xFFF
        rs1 = (word >> 15) & 0x1F
        value = (word >> 7) & 0x1F
    else:
        imm = (((word >> 25) & 0x7F) << 5) | ((word >> 7) & 0x1F)
        rs1 = (word >> 15) & 0x1F
        value = (word >> 20) & 0x1F
    if imm & 0x800:
        imm -= 0x1000
    return {"funct3": funct3, "imm": imm, "rs1": rs1, "value": value,
            "opcode": word & 0x7F}


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        workdir = Path(temporary)
        obj = workdir / "RV-P12-load-store-widths.o"
        image = workdir / "RV-P12-load-store-widths.bin"
        run(["llvm-mc", "-triple=riscv64", "-filetype=obj",
             str(SOURCE), "-o", str(obj)])
        run(["llvm-objcopy", "-O", "binary", "--only-section=.text",
             str(obj), str(image)])
        measured = image.read_bytes()
        if measured != EXPECTED:
            raise SystemExit("assembly is %s, field derivation says %s"
                             % (measured.hex(), EXPECTED.hex()))
        listing = [LINE.match(line).group(1).strip()
                   for line in run(["llvm-objdump", "-d",
                                    "--no-show-raw-insn", str(obj)]).splitlines()
                   if LINE.match(line)]

    if len(listing) != len(ROWS):
        raise SystemExit("expected %d disassembled lines, found %d"
                         % (len(ROWS), len(listing)))

    with (HERE / "RV-P12-load-store-widths-bytes.txt").open(
            "w", encoding="utf-8", newline="\n") as handle:
        handle.write(" ".join("%02x" % byte for byte in measured) + "\n")

    lines = ["fixture bytes %d: %s" % (len(measured), measured.hex())]
    for index, (mnemonic, kind, value, rs1, imm) in enumerate(ROWS):
        word = int.from_bytes(measured[index * 4: index * 4 + 4], "little")
        decoded = decode(kind, word)
        if (decoded["funct3"] != FUNCT3[mnemonic]
                or decoded["imm"] != imm
                or decoded["rs1"] != rs1
                or decoded["value"] != value):
            raise SystemExit("%s: decoded %r" % (mnemonic, decoded))
        text = listing[index]
        if not text.startswith(mnemonic):
            raise SystemExit("%s: disassembly says %r" % (mnemonic, text))
        name = "rd" if kind == "load" else "rs2"
        lines.append(
            "%-4s %-12s %s  funct3=%s imm=%d rs1=%d %s=%d  %s"
            % (mnemonic, "%s, %d(%s)" % (ABI[value], imm, ABI[rs1]),
               measured[index * 4: index * 4 + 4].hex(),
               format(decoded["funct3"], "03b"), decoded["imm"],
               decoded["rs1"], name, decoded["value"], text))
    lines.append("")
    lines.append("Every row is one `funct3` away from the `ld`/`sd` geometry:")
    lines.append("the load field is contiguous at 31-20, the store field is the")
    lines.append("S-type scatter 31-25|11-7. The last two rows are the signed")
    lines.append("12-bit ends (-2048 and 2047).")
    with (HERE / "direction.txt").open("w", encoding="utf-8",
                                      newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")

    print("bytes: %d" % len(measured))
    print("output sha256: %s" % hashlib.sha256(measured).hexdigest())
    print("input sha256: %s" % hashlib.sha256(
        SOURCE.read_bytes()).hexdigest())
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
