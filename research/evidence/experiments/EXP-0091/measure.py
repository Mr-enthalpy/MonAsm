"""Re-run the `EXP-0091` measurements and write the recorded files.

The probe list is the two `0.62.0` rows (load and store of the no-base indexed
`movq` shape) plus eleven corners: `REX.R` (`%r8` value), `REX.X` (`%r9d`
index), `REX.RX` (both), a zero displacement, a negative displacement, the x4
scale, `%r12d` as the index under `REX.X`, and `4660(,%r15d,8), %r15` (all
four bits of each register plus the x8 scale). The adjacent list measures the
shapes this slice does not take: the base+index sibling, the `0x67 66` `movw`
sibling, the `0x67` `movl` sibling, the 64-bit-addressing shape without
`0x67`, the absolute `SIB = 25` shape without `0x67`, a 64-bit index register
without `0x67`, and two rejected spellings (`%esp` as an index, a 32-bit value
register with `movq`).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0091/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0091")


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
    # Load/store, no extended register: REX = 48.
    "67488b040d08000000", "674889040d08000000",
    # REX.R: extended value register.
    "674c8b040d08000000", "674c89040d08000000",
    # REX.X: extended index register.
    "674a8b040d08000000", "674a89040d08000000",
    # REX.RX: both extended.
    "674e8b040d08000000", "674e89040d08000000",
    # Corners: zero displacement, negative displacement, x4 scale.
    "67488b040d00000000", "67488b040df8ffffff",
    "67488b048d08000000",
    # `%r12d` needs REX.X; `%r15d`/x8/0x1234 stays in the REX.RX row.
    "674a8b042508000000", "674e8b3cfd34120000",
], compact(rows)
lengths = [9] * 13
assert sum(lengths) == 117, sum(lengths)
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Lines 7 and 8 are rejected (`%esp` as an index, a 32-bit value register).
assert len(adjacent) == 6, len(adjacent)
assert compact(adjacent) == [
    "67488b440808", "67668b040d08000000", "678b040d08000000",
    "488b040d08000000", "488b042534120000", "4a8b042508000000",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
