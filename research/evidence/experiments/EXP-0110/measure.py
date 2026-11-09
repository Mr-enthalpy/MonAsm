#!/usr/bin/env python3
"""Measure the `EXP-0110` indexed byte `mov` vectors.

`X86-P79-movb-index.s` is the twelve fixture rows: three byte-register windows
(`%al`, `%ah`, `%spl`) x load/store x `disp8`/`disp32`, all at
`8/128(%rax,%rcx,4)`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0110/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "X86-P79-movb-index.s"

FIXTURE_EXPECTED = bytes.fromhex(
    "8a448808"                # movb 8(...), %al
    "885c8808"                # movb %bl, 8(...)
    "8a8c8880000000"          # movb 128(...), %cl
    "88948880000000"          # movb %dl, 128(...)
    "8a648808"                # movb 8(...), %ah
    "887c8808"                # movb %bh, 8(...)
    "8aac8880000000"          # movb 128(...), %ch
    "88b48880000000"          # movb %dh, 128(...)
    "408a648808"              # movb 8(...), %spl
    "40886c8808"              # movb %bpl, 8(...)
    "408ab48880000000"        # movb 128(...), %sil
    "4088bc8880000000"        # movb %dil, 128(...)
)


def run(command: list) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, check=True)


def assemble(source: Path, stem: str) -> bytes:
    obj = HERE / (stem + ".o")
    binary = HERE / (stem + ".bin")
    run(["llvm-mc", "-triple=x86_64", "-filetype=obj",
         str(source), "-o", str(obj)])
    run(["llvm-objcopy", "-O", "binary", "--only-section=.text",
         str(obj), str(binary)])
    return binary.read_bytes()


def write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    fixture = assemble(FIXTURE, "X86-P79-movb-index")
    if fixture != FIXTURE_EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), FIXTURE_EXPECTED.hex()))
    write(HERE / "X86-P79-movb-index-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")
    write(HERE / "show-encoding.txt",
          run(["llvm-mc", "-triple=x86_64", "-show-encoding",
               str(FIXTURE)]).stdout)

    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
