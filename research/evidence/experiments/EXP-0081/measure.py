"""Re-run the `EXP-0081` measurements and write the recorded files.

The probe list is the ten-instruction measurement: the four `0.52.0` rows (the
`REX.RBX` window on the 32-bit indexed `mov`, both directions at both
displacement widths) plus six corners (`%r12`/`%r12`, `%r15`/`%r15` and
`%r15d` at x8, `%r12` as an index, `%r12` as a base, the x8 scale, and a second
extended triple with the x2 scale in the store direction). The adjacent list
measures the shapes this slice does not take or that sit next to it: `%rsp` as
an index (rejected by the assembler), the `REX.BX`/`REX.R`/`REX`-less rows,
the 64-bit `REX.W`+`REX.BX` and `REX.W`-only siblings, the APX `%r16d` window,
`%r13` on both memory operands and on the register, and `%rsp` as a base behind
`REX.RX`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0081/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0081")


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
assert len(rows) == 10, len(rows)
assert compact(rows) == [
    "478b440808", "4789440808",
    "478b8408c8000000", "47898408c8000000",
    "478b442408", "478b7cff08",
    "478b442008", "478b440c08", "478b44c808", "47897c5a08",
], compact(rows)
lengths = [5, 5, 8, 8, 5, 5, 5, 5, 5, 5]
assert sum(lengths) == 56
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: `%rsp` as an index is rejected by the
# assembler and is covered as a negative fixture instead.
assert len(adjacent) == 11, len(adjacent)
assert compact(adjacent) == [
    "438b440808", "448b440808", "8b440808", "4f8b440808",
    "d5408b440808", "478b6c2d08", "4b8b440808", "478b440d08",
    "478b442808", "468b440c08", "4789642408",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
