"""Re-run the `EXP-0063` measurements and write the recorded files.

The probe list is one instruction per `0.34.0` row over the two `SIB` bases
(eight lines, all four bytes): both directions over `%rsp` and `%r12`, with a
register from each `REX.R` value the template allows. The fixture is the
eight-instruction oracle input, and the adjacent list measures the shapes this
slice does not take: the two `mod = 01` bases, the `disp8` neighbours, the APX
register window, the 32/16/8-bit analogues, and the plain-base row from
`0.33.0`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0063/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0063")


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
assert len(rows) == 8, len(rows)
compact = [row.replace("0x", "").replace(",", "") for row in rows]

# One probe per row, in the order `probe.asm` lists them: both directions over
# `%rsp` and `%r12`, each with `%rax` (REX.R = 0) and `%r8` (REX.R = 1).
expected = [
    "488b0424", "4c8b0424", "48890424", "4c890424",
    "498b0424", "4d8b0424", "49890424", "4d890424",
]
assert compact == expected, compact
lengths = [4] * 8
assert sum(lengths) == 32
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture, fixture_text = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 8, len(fixture)
assert [row.replace("0x", "").replace(",", "") for row in fixture] == expected, fixture
assert sum(len(row.split(",")) for row in fixture) == 32

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: no line here is rejected.
assert len(adjacent) == 11, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "488b4500", "498b4500", "488b442408", "498b442408",
    "d5488b0424", "8b0424", "668b0424", "8a0424",
    "488b00", "4c8b3c24", "4d8b3c24",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
