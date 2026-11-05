import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0058")


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
assert len(rows) == 24, len(rows)

# Rows 1-10 are the no-REX windows: `%al`-`%bl` (reg 0-3) and `%ah`-`%bh`
# (reg 4-7), seven bytes each. Rows 11-15 carry `REX = 40` (`%spl`-`%dil`) and
# rows 16-21 carry `REX = 44` (`%r8b`-`%r15b`), eight bytes each.
lengths = [len(row.split(",")) for row in rows]
assert lengths[:10] == [7] * 10, lengths
assert lengths[10:21] == [8] * 11, lengths
assert lengths[21:] == [7, 7, 7], lengths
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 8, len(fixture)
assert [len(row.split(",")) for row in fixture] == [7, 7, 7, 7, 8, 8, 8, 8], fixture
assert sum(len(row.split(",")) for row in fixture) == 60

adjacent = show_encoding("adjacent.asm", "adjacent-encoding.txt")
assert len(adjacent) == 11, len(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
