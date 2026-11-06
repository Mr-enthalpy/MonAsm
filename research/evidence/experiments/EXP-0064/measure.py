"""Re-run the `EXP-0064` measurements and write the recorded files.

The probe list is the twelve-instruction fixture: each of the six `0.35.0`
rows twice, so every reach window appears at both ends. The adjacent list
measures the shapes this slice does not take: the RIP-relative and `SIB`
bases, the explicit zero displacement, the `disp8` neighbour, the 64/16/8-bit
analogues, the APX register window and a `disp8` store.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0064/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0064")


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
assert len(rows) == 12, len(rows)
compact = [row.replace("0x", "").replace(",", "") for row in rows]

# One probe per fixture instruction, in the order `probe.asm` lists them: the
# six rows twice, at each end of the reach windows.
expected = [
    "8b00", "8b3e", "8900", "893e",
    "448b00", "458b39", "448900", "458939",
    "418b00", "418b3f", "418900", "41893f",
]
assert compact == expected, compact
lengths = [2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3]
assert sum(lengths) == 32
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Twelve lines produce an encoding: no line here is rejected.
assert len(adjacent) == 12, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "8b4500", "418b4500", "8b0424", "418b0424", "8b0500000000",
    "8b00", "8b4008", "488b00", "668b00", "8a00", "d5408b00", "41894008",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
