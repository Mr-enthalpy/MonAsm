#!/usr/bin/env python3
"""Measure the `EXP-0103` `call rel32` vector and the absent indirect forms.

`probe.asm` is the fixture input:

- `call L1` resolves in place: `L1` is at offset 10, the instruction ends at
  offset 5, so the displacement is `+5` (`e8 05 00 00 00`);
- `call ext` has no definition, so `llvm-mc` emits `e8 00 00 00 00` and one
  `R_X86_64_PLT32` record with addend `-4`;
- `addq $1, %rax` is the existing `0.1.0` row that gives the label a home;
- `call .+130` is a literal displacement: `llvm-mc` measures `130` from the
  start of the instruction, so the field is `125` (`e8 7d 00 00 00`) and no
  relocation is emitted.

`indirect.asm` measures the deliberately absent `FF /2` family, so its absence
from the table is a decision and not an oversight.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0103/measure.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.asm"
INDIRECT = HERE / "indirect.asm"

EXPECTED = bytes.fromhex(
    "e805000000"    # call L1      -> e8 + (10 - 5)
    "e800000000"    # call ext     -> PLT32 relocation
    "4883c001"      # addq $1, %rax
    "e87d000000"    # call .+130   -> literal field 125
)

INDIRECT_EXPECTED = bytes.fromhex(
    "ffd0"          # callq *%rax
    "ff10"          # callq *(%rax)
    "ff5008"        # callq *8(%rax)
)

RELOCATION = re.compile(
    r"R_X86_64_PLT32\s+ext\s+0xFFFFFFFFFFFFFFFC\b")


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
    measured = assemble(PROBE, "probe")
    if measured != EXPECTED:
        raise SystemExit("probe.asm is %s, expected %s"
                         % (measured.hex(), EXPECTED.hex()))
    write(HERE / "bytes.txt",
          " ".join("%02x" % byte for byte in measured) + "\n")

    shown = run(["llvm-mc", "-triple=x86_64", "-show-encoding", str(PROBE)])
    write(HERE / "show-encoding.txt", shown.stdout)

    relocations = subprocess.run(
        ["llvm-readobj", "--relocations", "probe.o"],
        capture_output=True, text=True, check=True, cwd=HERE)
    write(HERE / "relocations.txt", relocations.stdout)
    if not RELOCATION.search(relocations.stdout):
        raise SystemExit("probe.o has no R_X86_64_PLT32 ext -4 record:\n%s"
                         % relocations.stdout)
    records = sum(1 for line in relocations.stdout.splitlines()
                  if "R_X86_64_PLT32" in line)
    if records != 1:
        raise SystemExit("probe.o has %d PLT32 records, expected 1"
                         % records)

    indirect = assemble(INDIRECT, "indirect")
    if indirect != INDIRECT_EXPECTED:
        raise SystemExit("indirect.asm is %s, expected %s"
                         % (indirect.hex(), INDIRECT_EXPECTED.hex()))
    write(HERE / "indirect-bytes.txt",
          " ".join("%02x" % byte for byte in indirect) + "\n")

    print("probe.asm     %d bytes: %s" % (len(measured), measured.hex()))
    print("indirect.asm  %d bytes: %s" % (len(indirect), indirect.hex()))
    print("relocation    R_X86_64_PLT32 ext -4 (one record)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
