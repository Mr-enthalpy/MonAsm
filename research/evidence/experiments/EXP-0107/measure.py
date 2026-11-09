#!/usr/bin/env python3
"""Measure the `EXP-0107` legacy SSE extended-register vectors.

`probe.s` is the eight new rows with the fixture's operands. The four rows per
base only differ in the opcode (`28` load / `29` store) and the displacement
width, so the measurement fixes the template bits:

- `%rsp` pays one `REX = 44` byte (`R`, and the `SIB` base stays in the byte);
- `%r12` pays `REX = 45` (`R` and `B`) and the same, one byte longer than the
  low-register rows.

`X86-P76-sse-ext-fixed-base.s` is the fixture input and is identical to
`probe.s`; its 60 bytes are the expected image.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0107/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P76-sse-ext-fixed-base.s"

PROBE_EXPECTED = bytes.fromhex(
    "440f28442408"            # movaps 8(%rsp), %xmm8
    "450f284c2408"            # movaps 8(%r12), %xmm9
    "440f28b42480000000"      # movaps 128(%rsp), %xmm14
    "450f28bc2480000000"      # movaps 128(%r12), %xmm15
    "440f29542408"            # movaps %xmm10, 8(%rsp)
    "450f295c2408"            # movaps %xmm11, 8(%r12)
    "440f29a42480000000"      # movaps %xmm12, 128(%rsp)
    "450f29ac2480000000"      # movaps %xmm13, 128(%r12)
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

    fixture = assemble(FIXTURE, "X86-P76-sse-ext-fixed-base")
    if fixture != PROBE_EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), PROBE_EXPECTED.hex()))
    write(HERE / "X86-P76-sse-ext-fixed-base-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
