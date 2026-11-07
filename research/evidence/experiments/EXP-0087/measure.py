"""Re-run the `EXP-0087` measurements and write the recorded files.

The probe list is the twelve `0.58.0` rows (three single-`REX` windows × two
directions × two displacement widths) plus four corners (`%r15w` with `%ebp`
as a base, `%r15d` as a base, `%r15d` as an index and the x8 scale). The
adjacent list measures the shapes this slice does not take: the bare pair, the
two-bit `REX.RB` window (`%r12w`/`%r12d`), the 32-bit value row, the 64-bit
addressing row, `%esp` as a base and `%esp` as an index (rejected).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0087/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0087")


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


rows, text = show_encoding("probe.asm", "show-encoding.txt")
assert len(rows) == 16, len(rows)
assert compact(rows) == [
    "6766448b440808", "67664489440808",
    "6766418b440808", "67664189440808",
    "6766428b440808", "67664289440808",
    "6766448b8408c8000000", "676644898408c8000000",
    "6766418b8408c8000000", "676641898408c8000000",
    "6766428b8408c8000000", "676642898408c8000000",
    "6766448b7c0d08", "6766418b542f08",
    "6766428b543808", "6766448b7cc808",
], compact(rows)
lengths = [7, 7, 7, 7, 7, 7, 10, 10, 10, 10, 10, 10, 7, 7, 7, 7]
assert sum(lengths) == 130
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Lines 3 and 6 are rejected (a 32-bit value register and `%esp` as an index).
assert len(adjacent) == 5, len(adjacent)
assert compact(adjacent) == [
    "67668b440808", "67478b440808", "668b440808",
    "6766458b640c08", "67668b440c08",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
