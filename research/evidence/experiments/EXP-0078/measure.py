"""Re-run the `EXP-0078` measurements and write the recorded files.

The probe list is the twelve-instruction measurement: the four `0.49.0` rows
(32-bit `mov` with a `SIB` index, both directions at both displacement widths),
over the plain bases `%rax`/`%rdi` and the `SIB`-announced `%rsp`/`%rbp` bases,
with the two-bit scale at `0` and `2` (`x4`). The adjacent list measures the
shapes this slice does not take or that sit next to it: `%rsp` as an index
(rejected by the assembler), the four `REX` windows (`R`, `B`, `X`, `BX`), a
`%r12` base, the no-index shape, the `%r12` `SIB` base, the signed `disp8` ends,
the 64-bit sibling and the APX `%r16d` window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0078/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0078")


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
    "8b440808", "8b7cb708",
    "89440808", "897cb708",
    "8b440c08", "8b443508",
    "89440c08", "8b8408c8000000",
    "8bbcb7c8000000", "898408c8000000",
    "8b840cc8000000", "898435c8000000",
]
assert compact(rows) == expected, compact(rows)
lengths = [4, 4, 4, 4, 4, 4, 4, 7, 7, 7, 7, 7]
assert sum(lengths) == 63
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: `%rsp` as an index is rejected by the
# assembler and is covered as a negative fixture instead.
assert len(adjacent) == 11, len(adjacent)
assert compact(adjacent) == [
    "448b440808",
    "418b440808",
    "428b440808",
    "438b440808",
    "418b440c08",
    "8b4008",
    "418b442408",
    "8b44087f",
    "8b440880",
    "488b440808",
    "d5408b440808",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
