#!/usr/bin/env python3
"""Measure the `EXP-0111` register/register `sub` vectors.

`probe.s` and `X86-P80-sub-rr.s` are the same six instructions: the `29 /r`
row at 64/32/16 bits, both operand directions.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0111/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P80-sub-rr.s"

EXPECTED = bytes.fromhex(
    "4829c8"                  # subq %rcx, %rax
    "4829c1"                  # subq %rax, %rcx
    "29c8"                    # subl %ecx, %eax
    "29c1"                    # subl %eax, %ecx
    "6629c8"                  # subw %cx, %ax
    "6629c1"                  # subw %ax, %cx
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
    probe = assemble(PROBE, "probe")
    if probe != EXPECTED:
        raise SystemExit("probe.s is %s, expected %s"
                         % (probe.hex(), EXPECTED.hex()))
    write(HERE / "probe-bytes.txt",
          " ".join("%02x" % byte for byte in probe) + "\n")
    write(HERE / "probe-show-encoding.txt",
          run(["llvm-mc", "-triple=x86_64", "-show-encoding",
               str(PROBE)]).stdout)

    fixture = assemble(FIXTURE, "X86-P80-sub-rr")
    if fixture != EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), EXPECTED.hex()))
    write(HERE / "X86-P80-sub-rr-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
