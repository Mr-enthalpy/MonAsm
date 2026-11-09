#!/usr/bin/env python3
"""Measure the `EXP-0112` ALU register/register vectors.

`probe.s` and `X86-P81-alu-rr.s` are the same thirty instructions: the
`01`/`09`/`21`/`29`/`31`/`39` direction at three widths, both operand orders,
for `add`, `and`, `or`, `xor` and `cmp`.

The script also decodes the sibling opcode of every pair (`03`, `0B`, `23`,
`2B`, `33`, `3B`) to show that the same instruction has two legal encodings
and the assembler picks the first one. v0 ships only the first direction.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0112/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P81-alu-rr.s"

EXPECTED = bytes.fromhex(
    "4801c84801c101c801c16601c86601c1"
    "4821c84821c121c821c16621c86621c1"
    "4809c84809c109c809c16609c86609c1"
    "4831c84831c131c831c16631c86631c1"
    "4839c84839c139c839c16639c86639c1"
)

# mnemonic, the shipped `opcode` bytes, the absent `opcode+1` bytes
PAIRS = [
    ("add", "0x48 0x01 0xc1", "0x48 0x03 0xc8"),
    ("and", "0x48 0x21 0xc1", "0x48 0x23 0xc8"),
    ("or", "0x48 0x09 0xc1", "0x48 0x0b 0xc8"),
    ("sub", "0x48 0x29 0xc1", "0x48 0x2b 0xc8"),
    ("xor", "0x48 0x31 0xc1", "0x48 0x33 0xc8"),
    ("cmp", "0x48 0x39 0xc1", "0x48 0x3b 0xc8"),
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

    fixture = assemble(FIXTURE, "X86-P81-alu-rr")
    if fixture != EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), EXPECTED.hex()))
    write(HERE / "X86-P81-alu-rr-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    lines = []
    for mnemonic, shipped, absent in PAIRS:
        shipped_text = disassemble(shipped)
        absent_text = disassemble(absent)
        if shipped_text != absent_text:
            raise SystemExit("%s: %r and %r decode differently"
                             % (mnemonic, shipped_text, absent_text))
        lines.append("%s  %s  %s  %s"
                     % (mnemonic, shipped, shipped_text, absent))
    write(HERE / "direction.txt",
          "shipped opcode and absent opcode+1 decode to the same instruction\n"
          + "\n".join(lines) + "\n")

    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
