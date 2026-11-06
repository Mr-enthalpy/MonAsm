"""Re-run the `EXP-0074` measurements and write the recorded files.

The probe list is the twelve-instruction measurement: all four `0.45.0` rows,
with the four scale factors, both displacement widths, both directions, both
base windows (`%rax`/`%r15`) and both index windows (`%rcx`/`%r13`, plus
`%r12` through `REX.X`). The adjacent list measures the shapes this slice does
not take or that sit next to it: `%rsp` as an index (rejected by the
assembler), the no-base indexed form, a `%r13` base at `mod = 01`, the signed
`disp8` ends, the low-register row and the APX `%r16w` window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0074/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0074")


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
    "66448b440808", "66478b7cef08",
    "664489440808", "6647897cef08",
    "66458b447808", "6646897ca708",
    "66448b8408c8000000", "66478bbcefc8000000",
    "6644898408c8000000", "664789bcefc8000000",
    "66458b8478c8000000", "664689bca7c8000000",
]
assert compact(rows) == expected, compact(rows)
lengths = [6, 6, 6, 6, 6, 6, 9, 9, 9, 9, 9, 9]
assert sum(lengths) == 90
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Six lines produce an encoding: `%rsp` as an index is rejected by the
# assembler and is covered as a negative fixture instead.
assert len(adjacent) == 6, len(adjacent)
assert compact(adjacent) == [
    "66448b048d00000000",
    "66458b440d08",
    "66448b44087f",
    "66448b440880",
    "668b440808",
    "66d5408b440808",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
