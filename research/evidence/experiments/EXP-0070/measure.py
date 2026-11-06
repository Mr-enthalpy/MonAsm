"""Re-run the `EXP-0070` measurements and write the recorded files.

The probe list is the ten-instruction measurement: both directions over a plain
base at both ends of the base window (`%rax`/`%r15` and the `REX.B` window),
plus the two fixed `SIB` bases. The fixture then duplicates the four plain-base
rows at `%rdi` to show the base field. The adjacent list measures the shapes
this slice does not take: `%rbp`/`%r13` at `mod = 00`, the `REX.R` register
window, the other widths and the index/scale shapes.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0070/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0070")


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

expected = [
    "668b00", "66418b00", "66418b07", "668b0424", "66418b0424",
    "668900", "66418900", "66418907", "66890424", "6641890424",
]
assert compact == expected, compact
lengths = [3, 4, 4, 4, 5, 3, 4, 4, 4, 5]
assert sum(lengths) == 40
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Ten lines produce an encoding: no line here is rejected.
assert len(adjacent) == 10, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "668b4500", "66418b4500", "66448b0424", "66458b0424", "668b00",
    "8b00", "488b00", "8a00", "668b0404", "668b0484",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
