#!/usr/bin/env python3
"""Measure the `EXP-0109` legacy/VEX SSE indexed vectors.

`probe.s` is twenty instructions: four zero-displacement shapes plus
`disp8`/`disp32` at both `xmm` windows for the legacy and VEX families, load
and store. `X86-P78-sse-index.s` is the sixteen fixture rows (no
zero-displacement shapes), one per new form.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0109/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P78-sse-index.s"

PROBE_EXPECTED = bytes.fromhex(
    "0f280488"                # movaps (%rax,%rcx,4), %xmm0
    "0f290488"                # movaps %xmm0, (%rax,%rcx,4)
    "0f284c8808"              # movaps 8(%rax,%rcx,4), %xmm1
    "0f294c8808"              # movaps %xmm1, 8(%rax,%rcx,4)
    "0f28948880000000"        # movaps 128(...), %xmm2
    "0f29948880000000"        # movaps %xmm2, 128(...)
    "440f28448808"            # movaps 8(...), %xmm8
    "440f29448808"            # movaps %xmm8, 8(...)
    "440f288c8880000000"      # movaps 128(...), %xmm9
    "440f298c8880000000"      # movaps %xmm9, 128(...)
    "c5f8280488"              # vmovaps (%rax,%rcx,4), %xmm0
    "c5f8290488"              # vmovaps %xmm0, (%rax,%rcx,4)
    "c5f8284c8808"            # vmovaps 8(...), %xmm1
    "c5f8294c8808"            # vmovaps %xmm1, 8(...)
    "c5f828948880000000"      # vmovaps 128(...), %xmm2
    "c5f829948880000000"      # vmovaps %xmm2, 128(...)
    "c57828448808"            # vmovaps 8(...), %xmm8
    "c57829448808"            # vmovaps %xmm8, 8(...)
    "c578288c8880000000"      # vmovaps 128(...), %xmm9
    "c578298c8880000000"      # vmovaps %xmm9, 128(...)
)

FIXTURE_EXPECTED = bytes.fromhex(
    "0f284c8808"              # movaps 8(...), %xmm1
    "0f29548808"              # movaps %xmm2, 8(...)
    "0f289c8880000000"        # movaps 128(...), %xmm3
    "0f29a48880000000"        # movaps %xmm4, 128(...)
    "440f28448808"            # movaps 8(...), %xmm8
    "440f294c8808"            # movaps %xmm9, 8(...)
    "440f28948880000000"      # movaps 128(...), %xmm10
    "440f299c8880000000"      # movaps %xmm11, 128(...)
    "c5f828448808"            # vmovaps 8(...), %xmm0
    "c5f8296c8808"            # vmovaps %xmm5, 8(...)
    "c5f828b48880000000"      # vmovaps 128(...), %xmm6
    "c5f829bc8880000000"      # vmovaps %xmm7, 128(...)
    "c57828648808"            # vmovaps 8(...), %xmm12
    "c578296c8808"            # vmovaps %xmm13, 8(...)
    "c57828b48880000000"      # vmovaps 128(...), %xmm14
    "c57829bc8880000000"      # vmovaps %xmm15, 128(...)
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

    fixture = assemble(FIXTURE, "X86-P78-sse-index")
    if fixture != FIXTURE_EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), FIXTURE_EXPECTED.hex()))
    write(HERE / "X86-P78-sse-index-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
