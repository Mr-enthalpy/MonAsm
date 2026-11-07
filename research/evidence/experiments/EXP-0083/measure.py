"""Re-run the `EXP-0083` measurements and write the recorded files.

The probe list is the sixteen-instruction measurement: the twelve `0.54.0` rows
(`0x67` plus one `REX` bit on the 32-bit indexed `mov`, both directions at both
displacement widths) plus four corners (`%r12d` as a base, `%r12d` as an index,
`%ebp` as a base on the `REX.R` row and the x8 scale on the `REX.B` row). The
adjacent list measures the shapes this slice does not take or that sit next to
it: `%esp` as an index (rejected by the assembler), the 64-bit addressing rows,
the `0x67`+`REX.RBX` and `0x67`+`REX.RB` windows, the `0x67` `REX.W` sibling,
`%r13d` on all three operands and a second `REX.R` row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0083/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0083")


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
assert len(rows) == 16, len(rows)
assert compact(rows) == [
    "67448b440808", "674489440808",
    "67448b8408c8000000", "6744898408c8000000",
    "67418b440808", "674189440808",
    "67418b8408c8000000", "6741898408c8000000",
    "67428b440808", "674289440808",
    "67428b8408c8000000", "6742898408c8000000",
    "67418b440c08", "67428b442008",
    "67448b440d08", "67418b44c808",
], compact(rows)
lengths = [6, 6, 9, 9, 6, 6, 9, 9, 6, 6, 9, 9, 6, 6, 6, 6]
assert sum(lengths) == 114
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# The first and second lines are rejected (`%esp` as an index); the remaining
# ten encode.
assert len(adjacent) == 10, len(adjacent)
assert compact(adjacent) == [
    "418b440808", "428b440808",
    "67478b440808", "67448b440808", "67468b440808",
    "674b8b440808", "67488b440808",
    "67478b6c2d08", "67448b445a08", "67458b440808",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
