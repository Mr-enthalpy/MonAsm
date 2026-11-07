"""Re-run the `EXP-0094` measurements and write the recorded files.

The probe list is the four `0.65.0` rows (the absolute `SIB = 25` shape behind
`0x67 66` at the 16-bit value width: two value windows x two directions) plus
six corners: zero, `-1`, `2147483647`, `-2147483648`, `%r15w` as the load and
store value. The adjacent list measures the shapes this slice does not take:
the same absolute row without `0x67`, the 32-bit and 64-bit siblings, the
no-base indexed and base+index 16-bit rows, both `moffs` forms and the
`0x67 66` RIP-relative row. Two spellings are rejected.

`llvm-mc -show-encoding` prints an explicit `addr32` prefix on its own line,
so the instruction bytes are read from the object file instead; the recorded
`show-encoding.txt` keeps the printer's view for reference.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0094/measure.py
"""

import subprocess
import tempfile
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
LLVM_OBJCOPY = r"C:\Users\hanni\Tools\llvm\bin\llvm-objcopy.exe"
DIR = Path(__file__).resolve().parent

PROBES = [
    ("addr32 movw 4660, %ax", "67668b042534120000", 9),
    ("addr32 movw %ax, 4660", "676689042534120000", 9),
    ("addr32 movw 4660, %r8w", "6766448b042534120000", 10),
    ("addr32 movw %r8w, 4660", "67664489042534120000", 10),
    ("addr32 movw 0, %ax", "67668b042500000000", 9),
    ("addr32 movw -1, %ax", "67668b0425ffffffff", 9),
    ("addr32 movw 2147483647, %ax", "67668b0425ffffff7f", 9),
    ("addr32 movw -2147483648, %ax", "67668b042500000080", 9),
    ("addr32 movw 4660, %r15w", "6766448b3c2534120000", 10),
    ("addr32 movw %r15w, 4660", "676644893c2534120000", 10),
]

ADJACENT = [
    ("movw 4660, %ax", "668b042534120000", 8),
    ("addr32 movl 4660, %eax", "678b042534120000", 8),
    ("addr32 movq 4660, %rax", "67488b042534120000", 9),
    ("movw 8(,%ecx,1), %ax", "67668b040d08000000", 9),
    ("movw 8(%eax,%ecx,1), %ax", "67668b440808", 6),
    ("movabs 4660, %ax", "66a13412000000000000", 10),
    ("addr32 movabs 4660, %ax", "6766a13412000000000000", 11),
    ("addr32 movw 4660(%rip), %ax", "67668b0534120000", 8),
]


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def run(source, target, extra=()):
    result = subprocess.run(
        [LLVM_MC, "-triple=x86_64"] + list(extra) + [str(DIR / source)],
        capture_output=True, text=True)
    text = (result.stdout + result.stderr).replace("\r\n", "\n")
    write(DIR / target, text)
    return result.returncode, text


def object_bytes(source):
    with tempfile.TemporaryDirectory() as folder:
        obj = Path(folder) / "out.o"
        binary = Path(folder) / "out.bin"
        result = subprocess.run(
            [LLVM_MC, "-triple=x86_64", "-filetype=obj", str(DIR / source),
             "-o", str(obj)], capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(result.stdout + result.stderr)
        subprocess.run(
            [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(obj),
             str(binary)], check=True)
        return binary.read_bytes()


def check(source, table):
    data = object_bytes(source)
    expected = "".join(row[1] for row in table)
    actual = data.hex()
    assert actual == expected, (actual, expected)
    assert len(data) == sum(row[2] for row in table), len(data)
    return data


probe = check("probe.asm", PROBES)
write(DIR / "probe-bytes.txt", probe.hex() + "\n")
write(DIR / "probe-lengths.txt",
      " ".join(str(row[2]) for row in PROBES) + "\n")
run("probe.asm", "show-encoding.txt", ("-show-encoding",))

adjacent = check("adjacent.asm", ADJACENT)
write(DIR / "adjacent-bytes.txt", adjacent.hex() + "\n")
run("adjacent.asm", "adjacent-show-encoding.txt", ("-show-encoding",))

rejected_code, rejected_text = run(
    "rejected.asm", "rejected.txt", ("-show-encoding",))
assert rejected_code != 0, rejected_code
assert rejected_text.count("error: invalid operand for instruction") == 2

# `llvm-mc -disassemble` on the object bytes names the `addr32` prefix.
lines = [",".join("0x" + probe.hex()[i:i + 2]
                  for i in range(0, len(probe.hex()), 2))]
write(DIR / "probes.txt", "\n".join(lines) + "\n")
dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
dis_text = (dis.stdout + dis.stderr).replace("\r\n", "\n")
write(DIR / "probes-disassembled.txt", dis_text)
assert dis_text.count("addr32") == 10, dis_text

print(probe.hex())
print("---")
print(dis_text)
