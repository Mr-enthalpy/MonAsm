"""Re-run the `EXP-0073` measurements and write the recorded files.

The probe list is the fourteen-instruction measurement: all eight `0.44.0`
rows, with both ends of the `REX.R` register window (`%r8w`/`%r15w`) on every
base shape. The adjacent list measures the shapes this slice does not take
or that sit next to it: `%rbp`/`%r13` (legal at `mod = 10`), the signed
32-bit ends, the neighbouring `disp8` rows, the index/scale shapes, the
low-register row and the APX `%r16w` window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0073/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0073")


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


def compact(rows):
    return [row.replace("0x", "").replace(",", "") for row in rows]


rows, text = show_encoding("probe.asm", "show-encoding.txt")
assert len(rows) == 14, len(rows)

expected = [
    "66448b80c8000000", "66448bbfc8000000",
    "66458b80c8000000", "66458bbfc8000000",
    "66448980c8000000", "664489bfc8000000",
    "66458980c8000000", "664589bfc8000000",
    "66448b8424c8000000", "6644898424c8000000",
    "66458b8424c8000000", "6645898424c8000000",
    "66458bbc24c8000000", "664589bc24c8000000",
]
assert compact(rows) == expected, compact(rows)
lengths = [8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9]
assert sum(lengths) == 118
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Ten lines produce an encoding: `2147483648` is rejected by the assembler and
# is covered as a negative fixture instead.
assert len(adjacent) == 10, len(adjacent)
assert compact(adjacent) == [
    "66448b85c8000000", "66458b85c8000000",
    "66448b80ffffff7f", "66448b8000000080",
    "66448b407f", "66448b4008",
    "66448b8404c8000000", "66448b8484c8000000",
    "668b80c8000000", "66d5408b80c8000000",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
