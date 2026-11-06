"""Re-run the `EXP-0075` measurements and write the recorded files.

The probe list is the twelve-instruction measurement: all four `0.46.0` rows,
with both displacement widths, both directions, and bases that exercise the
`SIB` rules (`%rax`, `%rdi`, `%rsp` and `%rbp`) and the two-bit scale. The
adjacent list measures the shapes this slice does not take or that sit next to
it: `%rsp` as an index (rejected by the assembler), the `REX.R` row from
`0.45.0`, the three `REX`-carrying base/index windows, the no-index shape, the
signed `disp8` ends and the APX `%r16w` window.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0075/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0075")


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
    "668b440808", "668b7cb708",
    "668b440c08", "668b440d08",
    "6689440808", "66897cb708",
    "668b8408c8000000", "668bbcb7c8000000",
    "668b840cc8000000", "668b840dc8000000",
    "66898408c8000000", "6689bcb7c8000000",
]
assert compact(rows) == expected, compact(rows)
lengths = [5, 5, 5, 5, 5, 5, 8, 8, 8, 8, 8, 8]
assert sum(lengths) == 78
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Nine lines produce an encoding: `%rsp` as an index is rejected by the
# assembler and is covered as a negative fixture instead.
assert len(adjacent) == 9, len(adjacent)
assert compact(adjacent) == [
    "66448b440808",
    "66418b440808",
    "66428b440808",
    "66438b440808",
    "668b4008",
    "668b44087f",
    "668b440880",
    "66d5408b440808",
    "66418b8408c8000000",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
