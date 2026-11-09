#!/usr/bin/env python3
"""Measure the `EXP-0114` `mov` immediate vectors.

`probe.s` holds the six instructions that `llvm-mc` selects from a mnemonic
plus the excluded `movabs` form:

- `66 B8+rw iw` and `B8+rd id` for the register-in-opcode rows at 16/32 bits;
- `REX.W C7 /0 id` for the 64-bit ModRM row, including `%r8`;
- `REX.W B8+rd io` (`movabsq`, a 64-bit immediate) as the exclusion.

The 16/32-bit `C7 /0` rows cannot be measured from a mnemonic: for a register
destination `llvm-mc` always picks the shorter `B8+rd` form. Their bytes are
hand-derived (`66 C7 C3 iw`, `C7 C3 id` with `ModRM = 11 000 r/m`) and
confirmed by `llvm-mc -disassemble`, which prints the same instruction as the
`B8+rd` bytes. The script records both directions and the register windows.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0114/measure.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"

EXPECTED = bytes.fromhex(
    "66bb0100" "66b92c01"
    "bb01000000" "b92c010000"
    "48c7c301000000" "49c7c02c010000"
    "48b82c01000000000000"
)

# `B8+rd` bytes that `llvm-mc` selects and the `C7 /0` bytes with the same
# operands. Both must decode to the same instruction text.
WIDTH_PAIRS = [
    ("w", "0x66 0xbb 0x2c 0x01", "0x66 0xc7 0xc3 0x2c 0x01"),
    ("l", "0xbb 0x2c 0x01 0x00 0x00", "0xc7 0xc3 0x2c 0x01 0x00 0x00"),
]

# The 64-bit `B8+rd` form is `movabs` with an eight-byte immediate.
ACCUMULATOR_64 = ("0x48 0xc7 0xc3 0x2c 0x01 0x00 0x00",
                  "0x48 0xb8 0x2c 0x01 0x00 0x00 0x00 0x00 0x00 0x00")

# `%r8`-`%r15` need a REX prefix on the 16/32-bit rows, which changes the
# length; the 64-bit row folds `REX.B` into the `REX.W` byte it already has.
WINDOW = [
    ("movl $300, %r8d", "41b82c010000"),
    ("movw $300, %r8w", "6641b82c01"),
    ("movq $300, %r8", "49c7c02c010000"),
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


def encode(source: str) -> bytes:
    output = run(["llvm-mc", "-triple=x86_64", "-show-encoding"],
                 source + "\n").stdout
    match = re.search(r"encoding: \[([^\]]*)\]", output)
    if match is None:
        raise SystemExit("%r: no encoding in %r" % (source, output))
    return bytes(int(token, 16) for token in re.findall(r"0x([0-9a-f]{2})",
                                                        match.group(1)))


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

    window = []
    for source, hex_bytes in WINDOW:
        produced = encode(source).hex()
        if produced != hex_bytes:
            raise SystemExit("%s is %s, expected %s"
                             % (source, produced, hex_bytes))
        window.append((source, produced))

    lines = ["B8+rd bytes and the C7 /0 bytes decode alike"]
    for width, short, full in WIDTH_PAIRS:
        short_text = disassemble(short)
        full_text = disassemble(full)
        if short_text != full_text:
            raise SystemExit("%s: %r and %r decode differently"
                             % (width, short_text, full_text))
        lines.append("%s  %s  %s  %s" % (width, short, short_text, full))
    lines.append("")
    lines.append("64-bit B8+rd is movabs (eight-byte immediate)")
    short, full = ACCUMULATOR_64
    lines.append("%s  %s" % (short, disassemble(short)))
    lines.append("%s  %s" % (full, disassemble(full)))
    lines.append("")
    lines.append("register windows measured with -show-encoding")
    for source, hex_bytes in window:
        lines.append("%s  %s" % (source, hex_bytes))
    write(HERE / "direction.txt", "\n".join(lines) + "\n")

    print("probe.s  %d bytes: %s" % (len(probe), probe.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
