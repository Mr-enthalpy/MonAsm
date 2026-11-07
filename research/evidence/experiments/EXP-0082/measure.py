"""Re-run the `EXP-0082` measurements and write the recorded files.

The probe list is the ten-instruction measurement: the four `0.53.0` rows (the
`0x67` prefix on the 32-bit indexed `mov`, both directions at both displacement
widths) plus six corners (`%esp` as a base, `%ebp` as a base, `%edi`/`%esi` at
x4, the x8 scale, a negative displacement and a second low pair at x2). The
adjacent list measures the shapes this slice does not take or that sit next to
it: `%esp` as an index (rejected by the assembler), the 64-bit addressing rows
without the prefix, the `0x67`+`REX` windows, a `%esp` base without an index,
a bare `%eax` base, `%ebp` as an index, the 64-bit `REX.W` sibling and `%r13`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0082/measure.py
"""

import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0082")


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
    "678b440808", "6789440808",
    "678b8408c8000000", "67898408c8000000",
    "678b440c08", "678b440d08",
    "678b7cb708", "678b44c808", "678b4408f8", "678b445a08",
], compact(rows)
lengths = [5, 5, 8, 8, 5, 5, 5, 5, 5, 5]
assert sum(lengths) == 56
write(DIR / "probes.txt", "\n".join(rows) + "\n")
write(DIR / "probe-lengths.txt", " ".join(str(value) for value in lengths) + "\n")

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# Eleven lines produce an encoding: `%esp` as an index is rejected by the
# assembler and is covered as a negative fixture instead.
assert len(adjacent) == 10, len(adjacent)
assert compact(adjacent) == [
    "8b440808", "67478b440808", "67448b440808", "418b440808",
    "678b442408", "678b4008", "67478b442408", "678b442808",
    "67488b440808", "67478b6c2d08",
], compact(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
