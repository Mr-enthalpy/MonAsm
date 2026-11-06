import re
import subprocess
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
DIR = Path(r"C:\Users\hanni\Projects\MonAsm\research\evidence\experiments\EXP-0061")


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
compact = [row.replace("0x", "").replace(",", "") for row in rows]

# One probe per row, in the order `probe.asm` lists them: load and store over
# `%rsp` in the four byte-register windows (minus the high-byte `%r12` half),
# then the same over `%r12` in the three windows that have it.
expected = [
    "8a0424", "418a0424", "8a2424", "408a2424", "418a2424",
    "448a0424", "458a0424",
    "880424", "41880424", "882424", "40882424", "41882424",
    "44880424", "45880424",
]
assert compact == expected, compact
lengths = [len(row.split(",")) for row in rows]
assert lengths == [3, 4, 3, 4, 4, 4, 4, 3, 4, 3, 4, 4, 4, 4], lengths
assert sum(lengths) == 52
write(DIR / "probes.txt", "\n".join(rows) + "\n")

fixture, fixture_text = show_encoding("fixture.asm", "fixture-encoding.txt")
assert len(fixture) == 14, len(fixture)
assert [len(row.split(",")) for row in fixture] == lengths, fixture
write(DIR / "fixture-encoding.txt", fixture_text)
assert sum(len(row.split(",")) for row in fixture) == 52

adjacent, _ = show_encoding("adjacent.asm", "adjacent-encoding.txt")
# `(%r13), %ah` and `(%r12), %ah` are rejected outright, so eight of the ten
# lines produce an encoding and the file keeps the two rejection messages.
assert len(adjacent) == 8, len(adjacent)
assert [row.replace("0x", "").replace(",", "") for row in adjacent] == [
    "d5408a0424", "8a4500", "8a00", "8a442408",
    "8b0424", "488b0424", "448a3c24", "44883c24",
], adjacent

dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
write(DIR / "probes-disassembled.txt",
      (dis.stdout + dis.stderr).replace("\r\n", "\n"))
print("\n".join(rows))
print("---")
print((dis.stdout + dis.stderr).replace("\r\n", "\n"))
