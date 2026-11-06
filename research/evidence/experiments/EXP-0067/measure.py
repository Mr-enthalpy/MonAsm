"""Re-run the `EXP-0067` measurements and write the recorded files.

The probe list is the twelve-instruction fixture: each of the six `0.38.0`
rows twice at `200`, so every reach window appears at both ends. The adjacent
list measures the shapes this slice does not take: the signed 32-bit range
ends, the `disp8` and `mod = 00` neighbours, the `%rbp`/`%r13` bases that
`mod = 10` makes legal, the `%rsp`/`%r12` `SIB` bases, the 64/16-bit analogues
and the APX register window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0067/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0067")


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
assert len(rows) == 12, len(rows)
compact = [row.replace("0x", "").replace(",", "") for row in rows]

# One probe per fixture instruction, in the order `probe.asm` lists them: the
# six rows twice at `200`, at each end of the reach windows.
expected = [
    "8b80c8000000", "8bbec8000000", "8980c8000000", "89bec8000000",
    "448b80c8000000", "458bb9c8000000", "448980c8000000", "4589b9c8000000",
    "418b80c8000000", "418bbfc8000000", "418980c8000000", "4189bfc8000000",
]
assert compact == expected, compact
lengths = [6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7]
assert sum(lengths) == 80
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Twelve lines produce an encoding: no line here is rejected.
assert len(adjacent) == 12, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "8b80ffffff7f", "8b8000000080", "8b8080000000", "8b4008",
    "8b00", "8b85c8000000", "418b85c8000000", "8b8424c8000000",
    "418b8424c8000000", "488b80c8000000", "668b80c8000000",
    "d5408b80c8000000",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
