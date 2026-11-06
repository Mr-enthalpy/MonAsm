"""Re-run the `EXP-0068` measurements and write the recorded files.

The probe list is the sixteen-instruction fixture: each of the eight `0.39.0`
rows twice, at displacement `8` and `100`, so both ends of each register
window appear. The adjacent list measures the shapes this slice does not take:
the signed byte range ends, the `mod = 10` `SIB` neighbours, the `mod = 00`
`SIB` row, ordinary bases that stay out of `SIB`, the APX register window, the
64/16-bit analogues and the index/scale shapes.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0068/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0068")


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
assert len(rows) == 16, len(rows)
compact = [row.replace("0x", "").replace(",", "") for row in rows]

# One probe per fixture instruction, in the order `probe.asm` lists them: the
# eight rows twice, at displacement 8 and 100.
expected = [
    "8b442408", "8b7c2464", "448b442408", "448b7c2464",
    "89442408", "897c2464", "4489442408", "44897c2464",
    "418b442408", "418b7c2464", "458b442408", "458b7c2464",
    "4189442408", "41897c2464", "4589442408", "45897c2464",
]
assert compact == expected, compact
lengths = [4, 4, 5, 5, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
assert sum(lengths) == 76
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Twelve lines produce an encoding: no line here is rejected.
assert len(adjacent) == 12, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "8b442480", "8b44247f", "8b842480000000", "8b8424c8000000",
    "8b0424", "8b4508", "418b4508", "d5408b442408", "488b442408",
    "668b442408", "8b440408", "8b448408",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
