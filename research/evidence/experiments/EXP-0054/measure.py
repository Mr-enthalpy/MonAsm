import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0054")


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def show_encoding(source, target):
    result = subprocess.run(
        [LLVM_MC, "-triple=x86_64", "-show-encoding", str(DIR / source)],
        capture_output=True, text=True)
    text = (result.stdout + result.stderr).replace("\r\n", "\n")
    write(DIR / target, text)
    rows = []
    for line in text.splitlines():
        match = re.search(r"encoding: \[([^\]]+)\]", line)
        if match:
            rows.append(match.group(1).replace(" ", ""))
    return rows


rows = show_encoding("probe.asm", "show-encoding.txt")
assert len(rows) == 12, len(rows)
assert all(len(row.split(",")) == 11 for row in rows)
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 6, len(fixture)
assert all(len(row.split(",")) == 11 for row in fixture)

show_encoding("adjacent.asm", "adjacent-encoding.txt")

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
