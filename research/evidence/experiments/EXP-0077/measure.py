"""Re-run the `EXP-0077` measurements and write the recorded files.

The probe list is the twelve-instruction measurement: the four `0.48.0` rows
(both displacement widths, both directions), each with the two extremes of the
window (`%r8`/`%r9` and `%r15`/`%r15` with the ×8 scale) plus a `%r12`/`%r12`
pair, which is legal on both operands once `REX.B` and `REX.X` are set. The
adjacent list measures the shapes this slice does not take or that sit next to
it: `%rsp` as an index (rejected by the assembler), the three earlier rows
(`0.46.0` low/low, `0.47.0` base window, `0.47.0` index window), the `0.45.0`
`REX.R` row, the signed `disp8` ends, `%rbp` and `%r13` trading places as base
and index, and the APX `%r16w` window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0077/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0077")


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
assert len(rows) == 12, len(rows)

expected = [
    "66438b440808", "66438b7cff08",
    "664389440808", "6643897cff08",
    "66438b442408", "664389442408",
    "66438b8408c8000000", "66438bbcffc8000000",
    "6643898408c8000000", "664389bcffc8000000",
    "66438b8424c8000000", "6643898424c8000000",
]
assert compact(rows) == expected, compact(rows)
lengths = [6, 6, 6, 6, 6, 6, 9, 9, 9, 9, 9, 9]
assert sum(lengths) == 90
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: `%rsp` as an index is rejected by the
# assembler and is covered as a negative fixture instead.
assert len(adjacent) == 11, len(adjacent)
assert compact(adjacent) == [
    "668b440808",
    "66418b440808",
    "66428b440808",
    "66478b440808",
    "66438b44087f",
    "66438b440880",
    "66428b442d08",
    "66418b442d08",
    "66428b440c08",
    "66438b442c08",
    "66d5438b440808",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
