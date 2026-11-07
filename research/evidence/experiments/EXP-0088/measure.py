"""Re-run the `EXP-0088` measurements and write the recorded files.

The probe list is the sixteen `0.59.0` rows (four two-bit `REX` windows × two
directions × two displacement widths) plus four corners (`%r12d` as a base
with `%r15w` as the value, `%r12d` as a base with `%r15d` as the index,
`%r12d`/`%r13d` under `REX.RBX`, and the x8 scale). The adjacent list measures
the shapes this slice does not take: the bare pair, the three single-`REX`
windows, the 32-bit `REX.RBX` row, the 64-bit addressing row, the two-bit
`%r12w`/`%r12d` row, `%esp` as a base, and `%esp` as an index and a 32-bit
value register (both rejected).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0088/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0088")


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
assert len(rows) == 20, len(rows)
assert compact(rows) == [
    # disp8: REX.RB, REX.RX, REX.BX and REX.RBX, load then store.
    "6766458b440808", "67664589440808",
    "6766468b440808", "67664689440808",
    "6766438b440808", "67664389440808",
    "6766478b440808", "67664789440808",
    # disp32: the same four windows, load then store.
    "6766458b8408c8000000", "676645898408c8000000",
    "6766468b8408c8000000", "676646898408c8000000",
    "6766438b8408c8000000", "676643898408c8000000",
    "6766478b8408c8000000", "676647898408c8000000",
    # Corners.
    "6766458b7c0c08", "6766438b543c08",
    "6766478b7c2c08", "6766478b44c808",
], compact(rows)
lengths = [7] * 8 + [10] * 8 + [7] * 4
assert sum(lengths) == 164
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Lines 9 and 10 are rejected (`%esp` as an index, a 32-bit value register).
assert len(adjacent) == 8, len(adjacent)
assert compact(adjacent) == [
    "67668b440808", "6766448b440808", "6766418b440808", "6766428b440808",
    "67478b440808", "668b440808", "6766478b642408", "67668b440c08",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
