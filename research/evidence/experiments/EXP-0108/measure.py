#!/usr/bin/env python3
"""Measure the `EXP-0108` `addr32` `%rip`-relative vectors.

`probe.s` is the six instructions with a literal `16(%rip)` displacement, one
per new row. It fixes the prefix order (`0x67` first, then `0x66`/`REX`) and the
target placement:

- `r32` is `67 8b/89 05` plus `disp32` (7 bytes);
- `r64` is `67 48 8b/89 05` plus `disp32` (8 bytes);
- `r16` is `67 66 8b/89 05` plus `disp32` (8 bytes).

`X86-P77-addr32-riprel32.s` is the fixture input: the same six instructions
target one local label after 16 bytes of padding, so each `pcrel_end`
displacement is `label - (instruction offset + instruction length)`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0108/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P77-addr32-riprel32.s"

PROBE_EXPECTED = bytes.fromhex(
    "678b0510000000"          # addr32 movl 16(%rip), %eax
    "67890510000000"          # addr32 movl %eax, 16(%rip)
    "67488b0510000000"        # addr32 movq 16(%rip), %rax
    "6748890510000000"        # addr32 movq %rax, 16(%rip)
    "67668b0510000000"        # addr32 movw 16(%rip), %ax
    "6766890510000000"        # addr32 movw %ax, 16(%rip)
)

FIXTURE_EXPECTED = bytes.fromhex(
    "678b0537000000"          # L1 at 62, end at 7  -> 55
    "67890530000000"          # L1 at 62, end at 14 -> 48
    "67488b0528000000"        # L1 at 62, end at 22 -> 40
    "6748890520000000"        # L1 at 62, end at 30 -> 32
    "67668b0518000000"        # L1 at 62, end at 38 -> 24
    "6766890510000000"        # L1 at 62, end at 46 -> 16
    "00000000000000000000000000000000"
    "aabbccdd"
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
    if probe != PROBE_EXPECTED:
        raise SystemExit("probe.s is %s, expected %s"
                         % (probe.hex(), PROBE_EXPECTED.hex()))
    write(HERE / "probe-bytes.txt",
          " ".join("%02x" % byte for byte in probe) + "\n")
    write(HERE / "probe-show-encoding.txt",
          run(["llvm-mc", "-triple=x86_64", "-show-encoding", str(PROBE)]).stdout)

    fixture = assemble(FIXTURE, "X86-P77-addr32-riprel32")
    if fixture != FIXTURE_EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), FIXTURE_EXPECTED.hex()))
    write(HERE / "X86-P77-addr32-riprel32-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
