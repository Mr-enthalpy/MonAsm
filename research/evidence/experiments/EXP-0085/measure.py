"""Re-run the `EXP-0085` measurements and write the recorded files.

The probe list is the twelve-instruction measurement: the four `0.56.0` rows
(`0x67` + `REX.W` on the 32-bit indexed address shape, both directions at both
displacement widths) plus eight corners (`REX.RBX` with `%r8`, `%r12` on all
three operands, `%r13`, `%ebp` as a base, `%r12d` as an index, `%r12d` as a
base, the x8 scale and a `%r15`/`%r15d`/`%ebp` store). The adjacent list
measures the shapes this slice does not take or that sit next to it: `%esp` as
an index (rejected), the 64-bit addressing rows, the 32-bit value row, `%esp`
as a base, `REX.R`/`REX.X`/`REX.B` on the same `0x67` row, and a `movq` with a
32-bit value register (rejected).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0085/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0085")


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
assert compact(rows) == [
    "67488b440808", "674889440808",
    "67488b8408c8000000", "6748898408c8000000",
    "674f8b440808", "674f8b642408", "674f8b6c2d08",
    "67488b440d08", "674a8b442008", "67498b440c08",
    "67488b44c808", "674d897c2f08",
], compact(rows)
lengths = [6, 6, 9, 9, 6, 6, 6, 6, 6, 6, 6, 6]
assert sum(lengths) == 78
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# The first and last lines are rejected (`%esp` as an index, `movq %eax`); the
# remaining seven encode.
assert len(adjacent) == 7, len(adjacent)
assert compact(adjacent) == [
    "488b440808", "4f8b440808", "678b440808",
    "67488b440c08", "674c8b440808", "674a8b440808", "67498b440808",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
