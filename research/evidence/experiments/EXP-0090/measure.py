"""Re-run the `EXP-0090` measurements and write the recorded files.

The probe list is the eight `0.61.0` rows (four `REX` windows of the no-base
indexed `movl` shape x two directions) plus five corners: a zero
displacement, a negative displacement, the x4 scale, `%r12d` as the index
under `REX.X`, and `4660(,%r15d,8), %r15d` (all four bits of the index plus
the x8 scale). The adjacent list measures the shapes this slice does not
take: the base+index sibling, the `0x67 66` `movw` sibling, the 64-bit
addressing shape without `0x67`, the absolute `SIB = 25` shape without
`0x67`, the `REX.W` `movq` sibling, and two rejected spellings (`%esp` as an
index, a 16-bit value register with `movl`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0090/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0090")


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
            rows.append(match.group(1))
    return rows, text


def compact(rows):
    return [row.replace("0x", "").replace(",", "") for row in rows]


rows, _ = show_encoding("probe.asm", "show-encoding.txt")
assert len(rows) == 13, len(rows)
assert compact(rows) == [
    # No REX byte: value low, index low.
    "678b040d08000000", "6789040d08000000",
    # REX.R: extended value register.
    "67448b040d08000000", "674489040d08000000",
    # REX.X: extended index register.
    "67428b040d08000000", "674289040d08000000",
    # REX.RX: both extended.
    "67468b040d08000000", "674689040d08000000",
    # Corners: zero displacement, negative displacement, x4 scale.
    "678b040d00000000", "678b040df8ffffff",
    "678b048d08000000",
    # `%r12d` needs REX.X; `%r15d`/x8/0x1234 stays in the REX.RX row.
    "67428b042508000000", "67468b3cfd34120000",
], compact(rows)
lengths = [8, 8] + [9] * 6 + [8, 8, 8] + [9, 9]
assert sum(lengths) == 112, sum(lengths)
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Lines 6 and 7 are rejected (`%esp` as an index, a 16-bit value register).
assert len(adjacent) == 5, len(adjacent)
assert compact(adjacent) == [
    "678b440808", "67668b040d08000000", "8b040d08000000",
    "8b042534120000", "67488b040d08000000",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
