"""Re-run the `EXP-0065` measurements and write the recorded files.

The probe list is the sixteen-instruction fixture: each of the eight `0.36.0`
rows twice, so every base, direction and register window appears at both ends.
The adjacent list measures the shapes this slice does not take: the
RIP-relative and zero-displacement bases, the `disp8` `SIB` neighbours, the
64/16/8-bit analogues, the APX register window and a plain base.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0065/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0065")


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
assert len(rows) == 16, len(rows)
compact = [row.replace("0x", "").replace(",", "") for row in rows]

# One probe per fixture instruction, in the order `probe.asm` lists them: the
# eight rows twice, at each end of the reach windows.
expected = [
    "8b0424", "8b3c24", "890424", "893c24",
    "418b0424", "418b3c24", "41890424", "41893c24",
    "448b0424", "448b3c24", "44890424", "44893c24",
    "458b0424", "458b3c24", "45890424", "45893c24",
]
assert compact == expected, compact
lengths = [3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
assert sum(lengths) == 60
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Twelve lines produce an encoding: no line here is rejected.
assert len(adjacent) == 12, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "8b4500", "418b4500", "8b0500000000", "8b0424",
    "8b442408", "458b442408", "488b0424", "668b0424",
    "8a0424", "d5408b0424", "8b00", "4189442408",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
