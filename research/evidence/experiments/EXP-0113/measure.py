#!/usr/bin/env python3
"""Measure the `EXP-0113` ALU immediate vectors.

`probe.s` and `X86-P82-alu-imm.s` are the same thirty-six instructions: the
`83 /r ib` short form and the `81 /r iw`/`81 /r id` full-width form at three
value widths, plus the 64-bit `%rax` short forms of `and`/`or`/`xor`/`cmp`.

The script also decodes two pairs that cannot both be selected by a mnemonic:

- `REX.W 83 /0 ib` and `REX.W 81 /0 id` with the same value 1 decode to the
  same instruction, so the immediate width is a byte choice (`EC-01`);
- the `%rax` form (`48 25`, `48 0D`, `48 35`, `48 3D`) and the ModRM form
  (`48 81 /4`, `/1`, `/6`, `/7` with `r/m = %rax`) decode to the same
  instruction, so the accumulator choice is a byte choice (`EC-04`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0113/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P82-alu-imm.s"

EXPECTED = bytes.fromhex(
    "83c301" "81c12c010000" "6683c301" "6681c12c01"
    "83eb01" "81e92c010000" "6683eb01" "6681e92c01"
    "4883e301" "4881e12c010000" "83e301" "81e12c010000"
    "6683e301" "6681e12c01"
    "4883cb01" "4881c92c010000" "83cb01" "81c92c010000"
    "6683cb01" "6681c92c01"
    "4883f301" "4881f12c010000" "83f301" "81f12c010000"
    "6683f301" "6681f12c01"
    "4883fb01" "4881f92c010000" "83fb01" "81f92c010000"
    "6683fb01" "6681f92c01"
    "48252c010000" "480d2c010000" "48352c010000" "483d2c010000"
)

# The imm8 row and the full-width row of one family, with a value that fits
# both encodings.
WIDTH_PAIRS = [
    ("q", "0x48 0x83 0xc0 0x01", "0x48 0x81 0xc0 0x01 0x00 0x00 0x00"),
    ("l", "0x83 0xc0 0x01", "0x81 0xc0 0x01 0x00 0x00 0x00"),
    ("w", "0x66 0x83 0xc0 0x01", "0x66 0x81 0xc0 0x01 0x00"),
]

# The `%rax` short form and the ModRM form that names `%rax` explicitly.
ACCUMULATOR_PAIRS = [
    ("and", "0x48 0x25 0x2c 0x01 0x00 0x00", "0x48 0x81 0xe0 0x2c 0x01 0x00 0x00"),
    ("or", "0x48 0x0d 0x2c 0x01 0x00 0x00", "0x48 0x81 0xc8 0x2c 0x01 0x00 0x00"),
    ("xor", "0x48 0x35 0x2c 0x01 0x00 0x00", "0x48 0x81 0xf0 0x2c 0x01 0x00 0x00"),
    ("cmp", "0x48 0x3d 0x2c 0x01 0x00 0x00", "0x48 0x81 0xf8 0x2c 0x01 0x00 0x00"),
]


def run(command: list, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, input=stdin, capture_output=True,
                          text=True, check=True)


def assemble(source: Path, stem: str) -> bytes:
    obj = HERE / (stem + ".o")
    binary = HERE / (stem + ".bin")
    run(["llvm-mc", "-triple=x86_64", "-filetype=obj",
         str(source), "-o", str(obj)])
    run(["llvm-objcopy", "-O", "binary", "--only-section=.text",
         str(obj), str(binary)])
    return binary.read_bytes()


def disassemble(hex_bytes: str) -> str:
    return run(["llvm-mc", "-disassemble", "-triple=x86_64"],
               hex_bytes + "\n").stdout.strip()


def write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    probe = assemble(PROBE, "probe")
    if probe != EXPECTED:
        raise SystemExit("probe.s is %s, expected %s"
                         % (probe.hex(), EXPECTED.hex()))
    write(HERE / "probe-bytes.txt",
          " ".join("%02x" % byte for byte in probe) + "\n")
    write(HERE / "probe-show-encoding.txt",
          run(["llvm-mc", "-triple=x86_64", "-show-encoding",
               str(PROBE)]).stdout)

    fixture = assemble(FIXTURE, "X86-P82-alu-imm")
    if fixture != EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), EXPECTED.hex()))
    write(HERE / "X86-P82-alu-imm-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    lines = ["imm8 and full-width rows with the same value 1 decode alike"]
    for width, short, full in WIDTH_PAIRS:
        short_text = disassemble(short)
        full_text = disassemble(full)
        if short_text != full_text:
            raise SystemExit("%s: %r and %r decode differently"
                             % (width, short_text, full_text))
        lines.append("%s  %s  %s  %s" % (width, short, short_text, full))
    lines.append("")
    lines.append("%rax short form and the ModRM form decode alike")
    for mnemonic, short, full in ACCUMULATOR_PAIRS:
        short_text = disassemble(short)
        full_text = disassemble(full)
        if short_text != full_text:
            raise SystemExit("%s: %r and %r decode differently"
                             % (mnemonic, short_text, full_text))
        lines.append("%s  %s  %s  %s"
                     % (mnemonic, short, short_text, full))
    write(HERE / "direction.txt", "\n".join(lines) + "\n")

    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
