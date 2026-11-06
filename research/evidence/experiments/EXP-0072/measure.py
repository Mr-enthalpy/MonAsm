"""Re-run the `EXP-0072` measurements and write the recorded files.

The probe list is the fourteen-instruction measurement: all eight `0.43.0`
rows, with both ends of the `REX.R` register window (`%r8w`/`%r15w`) on every
base shape. The adjacent list measures the shapes this slice does not take
or that sit next to it: `%rbp`/`%r13` (legal at `mod = 01`), the signed byte
ends (`127`/`-128`), `128` re-formed as `disp32`, the `mod = 00` row, the
index/scale shapes, the low-register row and the APX `%r16w` window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0072/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0072")


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
    "66448b4008", "66448b7f08", "66458b4008", "66458b7f08",
    "6644894008", "6644897f08", "6645894008", "6645897f08",
    "66448b442408", "664489442408", "66458b442408", "664589442408",
    "66458b7c2408", "6645897c2408",
]
assert compact(rows) == expected, compact(rows)
lengths = [5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6]
assert sum(lengths) == 76
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: no line here is rejected.
assert len(adjacent) == 11, len(adjacent)
assert compact(adjacent) == [
    "66448b4508", "66458b4508", "66448b407f", "66448b4080",
    "66448b8080000000", "66448b80c8000000", "66448b00",
    "66448b440408", "66448b448408", "668b4008", "66d5408b4008",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
