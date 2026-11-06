"""Re-run the `EXP-0069` measurements and write the recorded files.

The probe list is the sixteen-instruction fixture: each of the eight `0.40.0`
rows twice, at displacement `200` and `100000`, so both ends of each register
window appear. The adjacent list measures the shapes this slice does not take:
the signed 32-bit range ends, the `disp8` and `mod = 00` neighbours, ordinary
bases that stay out of `SIB`, the APX register window, the 64/16-bit analogues
and the index/scale shapes.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0069/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0069")


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
# eight rows twice, at displacement 200 and 100000.
expected = [
    "8b8424c8000000", "8bbc24a0860100",
    "448b8424c8000000", "448bbc24a0860100",
    "898424c8000000", "89bc24a0860100",
    "44898424c8000000", "4489bc24a0860100",
    "418b8424c8000000", "418bbc24a0860100",
    "458b8424c8000000", "458bbc24a0860100",
    "41898424c8000000", "4189bc24a0860100",
    "45898424c8000000", "4589bc24a0860100",
]
assert compact == expected, compact
lengths = [7, 7, 8, 8, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8]
assert sum(lengths) == 124
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Thirteen lines produce an encoding: no line here is rejected.
assert len(adjacent) == 13, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "8b842400000080", "8b8424ffffff7f", "8b842480000000", "8b442408",
    "8b0424", "418b0424", "8b85c8000000", "418b85c8000000",
    "d5408b8424c8000000", "488b8424c8000000", "668b8424c8000000",
    "8b8404c8000000", "8b8484c8000000",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
