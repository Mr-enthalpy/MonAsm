import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0056")


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
assert len(rows) == 14, len(rows)

# Rows 1-7 are the low register window (`%eax`-`%edi`), seven bytes each; rows
# 8-14 are the `-ext` window (`%r8d`-`%r15d`) and carry the REX byte, eight.
low = rows[:7]
ext = rows[7:]
assert all(len(row.split(",")) == 7 for row in low), low
assert all(len(row.split(",")) == 8 for row in ext), ext
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 6, len(fixture)
assert [len(row.split(",")) for row in fixture] == [7, 7, 8, 8, 7, 8], fixture
assert sum(len(row.split(",")) for row in fixture) == 45

adjacent = show_encoding("adjacent.asm", "adjacent-encoding.txt")
assert len(adjacent) == 13, len(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
