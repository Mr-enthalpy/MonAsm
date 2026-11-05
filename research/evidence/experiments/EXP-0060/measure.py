import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0060")


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


rows, text = show_encoding("probe.asm", "show-encoding.txt")
assert len(rows) == 14, len(rows)

# One probe per shape, in the order `probe.asm` lists them: load and store in
# the four byte-register windows over the plain base, then the two extension
# bits taken separately (`%r8` as base, `%r15b` as register, `%dil` as the
# `REX = 40` register), then the two `SIB` bases that need their own rows, and
# finally an explicit zero displacement that `llvm-mc` elides.
lengths = [len(row.split(",")) for row in rows]
assert lengths == [2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 2], lengths
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture, fixture_text = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 8, len(fixture)
assert [len(row.split(",")) for row in fixture] == [
    2, 2, 2, 2, 3, 3, 3, 3], fixture
write(DIR / "fixture-encoding.txt", fixture_text)
assert sum(len(row.split(",")) for row in fixture) == 20

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# `movb (%r13), %ah` is rejected outright, so thirteen of the fourteen lines
# produce an encoding and the file keeps the rejection message.
assert len(adjacent) == 13, len(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
