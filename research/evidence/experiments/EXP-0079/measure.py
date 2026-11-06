"""Re-run the `EXP-0079` measurements and write the recorded files.

The probe list is the fifteen-instruction measurement: the twelve `0.50.0` rows
(the `REX.R`, `REX.B` and `REX.X` windows on the 32-bit indexed `mov`, both
directions at both displacement widths) plus three window corners (`%r12` as a
base behind `REX.B`, `%r12` as an index behind `REX.X`, and `%rsp` as a base
behind `REX.R`). The adjacent list measures the shapes this slice does not take
or that sit next to it: `%rsp` as an index (rejected by the assembler), the two
window extremes with the x4 scale, `%r13`/`%rbp` as bases, the `REX.BX` window,
the APX `%r16d` window, the 64-bit `REX.W`/`REX.R` sibling, the `REX`-less row,
and the no-index `REX.R`/`REX.B` rows.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0079/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0079")


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
assert len(rows) == 15, len(rows)

expected = [
    "448b440808", "4489440808",
    "448b8408c8000000", "44898408c8000000",
    "418b440808", "4189440808",
    "418b8408c8000000", "41898408c8000000",
    "428b440808", "4289440808",
    "428b8408c8000000", "42898408c8000000",
    "418b440c08", "4289442008", "448b440c08",
]
assert compact(rows) == expected, compact(rows)
lengths = [5, 5, 8, 8, 5, 5, 8, 8, 5, 5, 8, 8, 5, 5, 5]
assert sum(lengths) == 93
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: `%rsp` as an index is rejected by the
# assembler and is covered as a negative fixture instead.
assert len(adjacent) == 11, len(adjacent)
assert compact(adjacent) == [
    "448b7cb708",
    "44897cb708",
    "418b443508",
    "8b443508",
    "438b442c08",
    "438b440808",
    "d5408b440808",
    "4c8b440808",
    "8b440808",
    "448b4008",
    "418b4008",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
