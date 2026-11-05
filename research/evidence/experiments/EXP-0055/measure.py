import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0055")


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
    return rows


rows = show_encoding("probe.asm", "show-encoding.txt")
assert len(rows) == 13, len(rows)

# The first eight rows are the 64-bit `SIB`-absolute shape this experiment
# decides; rows 9 and 10 are `moffs`, rows 11-13 are the register neighbours.
address = rows[:8]
assert all(len(row.split(",")) == 8 for row in address)
write(DIR / "probes.txt", "\n".join(address) + "\n")

fixture = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 6, len(fixture)
assert all(len(row.split(",")) == 8 for row in fixture)

adjacent = show_encoding("adjacent.asm", "adjacent-encoding.txt")
assert len(adjacent) == 13, len(adjacent)

ext = show_encoding("ext.asm", "ext-encoding.txt")
assert len(ext) == 5, len(ext)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(address))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
