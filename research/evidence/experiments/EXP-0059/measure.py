import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0059")


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
assert len(rows) == 20, len(rows)

# One probe per shape, in the order `probe.asm` lists them: load and store for
# the plain base, `%rsp` and `%r12` windows, each at disp8 and disp32, then the
# `%rbp`/`%r13` bases and the two displacement end points.
lengths = [len(row.split(",")) for row in rows]
assert lengths == [4, 7, 5, 8, 4, 7, 5, 8, 4, 7, 5, 8, 4, 7, 5, 8,
                   4, 4, 4, 4], lengths
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture, fixture_text = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 12, len(fixture)
assert [len(row.split(",")) for row in fixture] == [
    4, 7, 5, 8, 5, 8, 4, 7, 5, 8, 5, 8], fixture
write(DIR / "fixture-encoding.txt", fixture_text)
assert sum(len(row.split(",")) for row in fixture) == 74

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# `movb 8(%r8), %ah` is rejected outright, so eleven of the twelve lines
# produce an encoding and the file keeps the rejection message.
assert len(adjacent) == 11, len(adjacent)

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
