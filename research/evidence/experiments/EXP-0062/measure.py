"""Re-run the `EXP-0062` measurements and write the recorded files.

The probe list is one instruction per `0.33.0` row (ten lines, all three bytes),
the fixture is the six-instruction oracle input, and the adjacent list measures
the shapes this slice does not take: the `SIB` bases, the two `mod = 01` bases,
the `disp8`/`disp32` neighbours, the APX register window, the 32/16/8-bit
analogues, and the assembler's normalisation of an explicit zero displacement.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0062/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0062")


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def run(source, target, extra=()):
    result = subprocess.run(
        [LLVM_MC, "-triple=x86_64"] + list(extra) + [str(DIR / source)],
        capture_output=True, text=True)
    text = (result.stdout + result.stderr).replace("\r\n", "\n")
    write(DIR / target, text)
    return text


def show_encoding(source, target):
    text = run(source, target, ("-show-encoding",))
    rows = []
    for line in text.splitlines():
        match = re.search(r"encoding: \[([^\]]+)\]", line)
        if match:
            rows.append(match.group(1).replace(" ", ""))
    return rows, text


rows, text = show_encoding("probe.asm", "show-encoding.txt")
assert len(rows) == 10, len(rows)
compact = [row.replace("0x", "").replace(",", "") for row in rows]

# One probe per row, in the order `probe.asm` lists them: load and store over
# `%rax` and `%r8` (both REX bits clear or both set, so the 48/4d split is
# unambiguous), then two low-register pairs and the top of both four-bit
# fields.
expected = [
    "488b00", "4d8b00", "4d8b39", "488b37", "488b3e",
    "488900", "4d8900", "4d8939", "488937", "48893e",
]
assert compact == expected, compact
lengths = [3] * 10
assert lengths == [3] * 10
assert sum(lengths) == 30
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture, fixture_text = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 6, len(fixture)
assert [row.replace("0x", "").replace(",", "") for row in fixture] == [
    "488b00", "4d8b00", "4d8b39", "488900", "4d8900", "4d8939",
], fixture
assert sum(len(row.split(",")) for row in fixture) == 18

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Thirteen lines produce an encoding: no line here is rejected.
assert len(adjacent) == 13, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "488b0424", "498b0424", "488b4500", "498b4500",
    "488b4008", "488b042534120000", "d5488b00",
    "8b00", "668b00", "8a00",
    "48890424", "49890424", "488b00",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
