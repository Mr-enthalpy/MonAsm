#!/usr/bin/env python3
"""Measure the `EXP-0115` `sub` memory vectors.

Twelve instructions, one per new row: the `29 /r` store direction and the
`2B /r` load direction at 64, 32 and 16 bits, each with `base + disp8` and
`base + disp32`, low base window. `probe.s` also carries three shapes that the
vector does not exercise, so their bytes are recorded rather than inferred:

- `%rsp` as the base needs a SIB byte (`48 29 4c 24 08`);
- `%r8` as the base sets `REX.B` (`49 29 48 08`): reachable at 64 bits because
  `REX.B` shares the existing `REX.W` byte, but not exercised by the vector;
- a zero displacement needs `mod = 00` (`48 29 08`), a different template.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0115/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.s"
FIXTURE = HERE / "X86-P84-sub-mem.s"

EXPECTED = bytes.fromhex(
    "48294808" "4829932c010000"
    "482b4808" "482b932c010000"
    "294808" "29932c010000"
    "2b4808" "2b932c010000"
    "66294808" "6629932c010000"
    "662b4808" "662b932c010000"
)

EXCLUDED = bytes.fromhex(
    "48294c2408" "49294808" "482908"
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


def disassemble(hex_bytes: str) -> str:
    output = subprocess.run(
        ["llvm-mc", "-disassemble", "-triple=x86_64"],
        input=hex_bytes + "\n", capture_output=True, text=True, check=True)
    return output.stdout.strip()


def write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    fixture = assemble(FIXTURE, "X86-P84-sub-mem")
    if fixture != EXPECTED:
        raise SystemExit("fixture source is %s, expected %s"
                         % (fixture.hex(), EXPECTED.hex()))
    write(HERE / "X86-P84-sub-mem-bytes.txt",
          " ".join("%02x" % byte for byte in fixture) + "\n")

    probe = assemble(PROBE, "probe")
    if probe[: len(EXPECTED)] != EXPECTED:
        raise SystemExit("probe.s prefix is %s, expected %s"
                         % (probe[: len(EXPECTED)].hex(), EXPECTED.hex()))
    if probe[len(EXPECTED):] != EXCLUDED:
        raise SystemExit("probe.s tail is %s, expected %s"
                         % (probe[len(EXPECTED):].hex(), EXCLUDED.hex()))
    write(HERE / "probe-bytes.txt",
          " ".join("%02x" % byte for byte in probe) + "\n")
    write(HERE / "probe-show-encoding.txt",
          run(["llvm-mc", "-triple=x86_64", "-show-encoding",
               str(PROBE)]).stdout)

    lines = ["shapes outside the vector, measured with -show-encoding"]
    sources = ["subq %rcx, 8(%rsp)", "subq %rcx, 8(%r8)",
               "subq %rcx, (%rax)"]
    offset = len(EXPECTED)
    for source, size in zip(sources, (5, 4, 3)):
        chunk = probe[offset: offset + size]
        offset += size
        lines.append("%s  %s  %s"
                     % (source, chunk.hex(), disassemble(
                         " ".join("0x%02x" % byte for byte in chunk))))
    lines.append("")
    lines.append("29 /r writes the memory destination, 2B /r the register")
    lines.append("subq %%rcx, 8(%%rax)  %s  %s"
                 % (EXPECTED[:4].hex(), disassemble("0x48 0x29 0x48 0x08")))
    lines.append("subq 8(%%rax), %%rcx  %s  %s"
                 % (EXPECTED[11:15].hex(), disassemble("0x48 0x2b 0x48 0x08")))
    write(HERE / "direction.txt", "\n".join(lines) + "\n")

    print("fixture.s  %d bytes: %s" % (len(fixture), fixture.hex()))
    print("probe.s    %d bytes: %s" % (len(probe), probe.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
