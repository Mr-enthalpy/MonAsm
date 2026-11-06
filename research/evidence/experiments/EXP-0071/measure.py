"""Re-run the `EXP-0071` measurements and write the recorded files.

The probe list is the fourteen-instruction measurement: all eight `0.42.0`
rows, with both ends of the `REX.R` register window (`%r8w`/`%r15w`) on every
base shape. The adjacent list measures the shapes this slice does not take:
`%rbp`/`%r13` at `mod = 00`, the APX `%r16w` window, the `disp8`/`disp32`
shapes, the other widths and the index/scale shapes.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0071/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0071")


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
assert len(rows) == 14, len(rows)
compact = [row.replace("0x", "").replace(",", "") for row in rows]

expected = [
    "66448b00", "66448b3f", "66458b00", "66458b3f",
    "66448900", "6644893f", "66458900", "6645893f",
    "66448b0424", "6644890424", "66458b0424", "6645890424",
    "66458b3c24", "6645893c24",
]
assert compact == expected, compact
lengths = [4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5]
assert sum(lengths) == 62
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: no line here is rejected.
assert len(adjacent) == 11, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "66448b4500", "66458b4500", "66d5408b00", "66448b4008",
    "66448b80c8000000", "66448b442408", "448b00", "4c8b00", "448a00",
    "66448b0404", "66448b0484",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
