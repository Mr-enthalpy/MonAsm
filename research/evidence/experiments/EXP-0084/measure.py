"""Re-run the `EXP-0084` measurements and write the recorded files.

The probe list is the twenty-instruction measurement: the sixteen `0.55.0` rows
(`0x67` plus two fixed `REX` bits on the 32-bit indexed `mov`, both directions
at both displacement widths) plus four corners (`%r12d` on all three operands,
`%r13d` on all three, the x8 scale with `%r15d` and a store with `%r15d`/
`%ebp`). The adjacent list measures the shapes this slice does not take or that
sit next to it: `%esp` as an index (rejected) and as a base on an `X` row, the
single-bit rows (`42`, `41`, `43`), the 64-bit addressing `REX.RBX` row, the
`0x67` `REX.WBX` sibling, `%r12d` as a base with `%ebp` as an index, `%ebp` as
a base with `%r12d` as an index, and the bare `0x67` row.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0084/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0084")


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
assert len(rows) == 20, len(rows)
assert compact(rows) == [
    "67438b440808", "674389440808",
    "67438b8408c8000000", "6743898408c8000000",
    "67458b440808", "674589440808",
    "67458b8408c8000000", "6745898408c8000000",
    "67468b440808", "674689440808",
    "67468b8408c8000000", "6746898408c8000000",
    "67478b440808", "674789440808",
    "67478b8408c8000000", "6747898408c8000000",
    "67478b642408", "67478b6c2d08",
    "67478b7cc808", "6745897c2f08",
], compact(rows)
lengths = [6, 6, 9, 9, 6, 6, 9, 9, 6, 6, 9, 9, 6, 6, 9, 9, 6, 6, 6, 6]
assert sum(lengths) == 144
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# The first line is rejected (`%esp` as an index); the remaining nine encode.
assert len(adjacent) == 9, len(adjacent)
assert compact(adjacent) == [
    "67428b440c08", "67428b440808", "67418b440808", "67438b440808",
    "478b440808", "674b8b440808",
    "67418b442c08", "67428b442508", "678b441a08",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
