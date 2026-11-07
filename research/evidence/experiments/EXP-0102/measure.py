#!/usr/bin/env python3
"""Measure the `EXP-0102` `sub` immediates and the two `add`/`sub` opcode facts.

Runs `llvm-mc` on `probe.asm` and asserts the ten-instruction, 55-byte vector:

- `REX.W 83 /5 ib` for the `imm8` rows: `48 83 e8 01` is `subq $1, %rax`,
  `49 83 e8 01` is `subq $1, %r8` (the `dest` slot's `REX.B` bit), and the
  signed ends are `7f`/`80`;
- `REX.W 81 /5 id` for the `imm32` rows: `48 81 eb 2c 01 00 00` and
  `49 81 ef ff ff ff 7f`;
- `REX.W 2d id` for the accumulator row: `48 2d 2c 01 00 00`. llvm-mc picks
  the accumulator for `subq $300, %rax` even though `48 81 e8` would encode the
  same operation, which is `EC-04`'s counterexample.

Also assembles the deliberately absent register form and records the mnemonic
it produces, so the absence of `29`/`2b` from the table is a decision and not
an oversight.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0102/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.asm"
REGISTER = HERE / "register.asm"

EXPECTED = bytes.fromhex(
    "4883e801"
    "4883e97f"
    "4883e880"
    "4983e801"
    "4881eb2c010000"
    "4981efffffff7f"
    "4881ea00000080"
    "482d2c010000"
    "482dffffff7f"
    "482d00000080"
)

REGISTER_EXPECTED = bytes.fromhex(
    "4829d8"        # subq %rbx, %rax      -> 29 /r, the absent register form
    "4829c3"        # subq %rax, %rbx      -> 29 /r; llvm-mc never picks 2b
    "4883e801"      # subq $1, %rax        -> the shipped imm8 row
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
    measured = assemble(PROBE, "probe")
    if measured != EXPECTED:
        raise SystemExit("probe.asm is %s, expected %s"
                         % (measured.hex(), EXPECTED.hex()))
    write(HERE / "bytes.txt",
          " ".join("%02x" % byte for byte in measured) + "\n")

    shown = run(["llvm-mc", "-triple=x86_64", "-show-encoding", str(PROBE)])
    write(HERE / "show-encoding.txt", shown.stdout)

    register = assemble(REGISTER, "register")
    if register != REGISTER_EXPECTED:
        raise SystemExit("register.asm is %s, expected %s"
                         % (register.hex(), REGISTER_EXPECTED.hex()))
    write(HERE / "register-bytes.txt",
          " ".join("%02x" % byte for byte in register) + "\n")

    print("probe.asm     %d bytes: %s" % (len(measured), measured.hex()))
    print("register.asm  %d bytes: %s" % (len(register), register.hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
