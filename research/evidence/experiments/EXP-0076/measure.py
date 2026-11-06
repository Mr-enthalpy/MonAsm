"""Re-run the `EXP-0076` measurements and write the recorded files.

The probe list is the twelve-instruction measurement: the eight `0.47.0` rows,
with both displacement widths and both directions. The `-base-ext` rows put the
base in `%r8`-`%r15`; the `-index-ext` rows put the index in `%r8`-`%r15`. The
adjacent list measures the shapes this slice does not take or that sit next to
it: `%rsp` as an index (rejected by the assembler), the `REX.R` row from
`0.45.0`, the `REX.BX` window left for the next slice, the `SIB.base = 100`
`%r12`/`%rsp` bases, `%rbp` at `mod = 01`, `%r12` as an index, the signed
`disp8` ends and a `%r12` base at `disp32`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0076/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0076")


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
    "66418b440808", "66418b7cff08",
    "66428b440808", "66428b7cff08",
    "664189440808", "6642897cff08",
    "66418b8408c8000000", "66418bbcffc8000000",
    "66428b8408c8000000", "66428bbcffc8000000",
    "6641898408c8000000", "664289bcffc8000000",
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
    "66448b440808",
    "66438b440808",
    "66418b440c08",
    "66418b440d08",
    "66428b440c08",
    "66428b440d08",
    "66428b442008",
    "66418b44087f",
    "66418b440880",
    "66418b840cc8000000",
    "664289440c08",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
