"""Re-run the `EXP-0086` measurements and write the recorded files.

The probe list is the eight-instruction measurement: the four `0.57.0` rows
(`0x67` + `0x66` on the 32-bit indexed address shape, both directions at both
displacement widths) plus four corners (`%ebp` as a base, `%ebp` as an index,
the x8 scale and a `%dx` value). The adjacent list measures the shapes this
slice does not take or that sit next to it: a `%r8d` base and a `%r8w` value
(which need a `REX` byte), the 64-bit addressing row, the 32-bit value row,
`%esp` as a base, `%esp` as an index (rejected), and a `movw` with a 32-bit
value register (rejected).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0086/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0086")


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
assert len(rows) == 8, len(rows)
assert compact(rows) == [
    "67668b440808", "676689440808",
    "67668b8408c8000000", "6766898408c8000000",
    "67668b440d08", "67668b442808", "67668b44c808", "67668b540808",
], compact(rows)
lengths = [6, 6, 9, 9, 6, 6, 6, 6]
assert sum(lengths) == 54
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Lines 5 and 7 are rejected (a 32-bit value register and `%esp` as an index).
assert len(adjacent) == 7, len(adjacent)
assert compact(adjacent) == [
    "6766418b440808", "6766448b440808", "668b440808", "678b440808",
    "67668b440c08", "67668b440808", "67668b8408c8000000",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
