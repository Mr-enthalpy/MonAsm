"""Re-run the `EXP-0066` measurements and write the recorded files.

The probe list is the twelve-instruction fixture: each of the six `0.37.0`
rows twice, so every reach window appears at both ends. The adjacent list
measures the shapes this slice does not take: the `disp8` range ends, the
`disp32` neighbours, the explicit zero, the `%rbp`/`%r13` bases that `mod = 01`
makes legal, the `%rsp`/`%r12` `SIB` bases, the 64/16-bit analogues and the
APX register window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0066/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0066")


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
    "8b4008", "8b7e08", "894008", "897e08",
    "448b4008", "458b7908", "44894008", "45897908",
    "418b4008", "418b7f08", "41894008", "41897f08",
]
assert compact == expected, compact
lengths = [3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4]
assert sum(lengths) == 44
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Twelve lines produce an encoding: no line here is rejected.
assert len(adjacent) == 12, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "8b4080", "8b407f", "8b8080000000", "8b80c8000000",
    "8b00", "8b4508", "418b4508", "8b442408",
    "418b442408", "488b4008", "668b4008", "d5408b4008",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
