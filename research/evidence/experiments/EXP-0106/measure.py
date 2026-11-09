#!/usr/bin/env python3
"""Measure the `EXP-0106` SSE `%rip`-relative vectors.

`probe.s` is the six instructions with a literal `16(%rip)` displacement, one
per new row. It fixes the template bits and the prefix selection:

- legacy `movaps` is `0f 28/29 05` plus `disp32`;
- VEX `vmovaps` is `c5 f8 28/29 05` plus `disp32`;
- `{evex} vmovaps` is `62 f1 7c 08 28/29 05` plus `disp32`.

`X86-P75-sse-riprel32.s` is the fixture input: the same six instructions target
one local label after 16 bytes of padding, so each `pcrel_end` displacement is
`label - (instruction offset + instruction length)` and the six lengths matter.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0106/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P75-sse-riprel32.s"

PROBE_EXPECTED = bytes.fromhex(
    "0f280510000000"          # movaps 16(%rip), %xmm0
    "0f290510000000"          # movaps %xmm0, 16(%rip)
    "c5f8280510000000"        # vmovaps 16(%rip), %xmm0
    "c5f8290510000000"        # vmovaps %xmm0, 16(%rip)
    "62f17c08280510000000"    # {evex} vmovaps 16(%rip), %xmm0
    "62f17c08290510000000"    # {evex} vmovaps %xmm0, 16(%rip)
)

FIXTURE_EXPECTED = bytes.fromhex(
    "0f28053b000000"          # L1 at 66, end at 7  -> 59
    "0f290534000000"          # L1 at 66, end at 14 -> 52
    "c5f828052c000000"        # L1 at 66, end at 22 -> 44
    "c5f8290524000000"        # L1 at 66, end at 30 -> 36
    "62f17c0828051a000000"    # L1 at 66, end at 40 -> 26
    "62f17c08290510000000"    # L1 at 66, end at 50 -> 16
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

    fixture = assemble(FIXTURE, "X86-P75-sse-riprel32")
    if fixture != FIXTURE_EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), FIXTURE_EXPECTED.hex()))
    write(HERE / "X86-P75-sse-riprel32-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
