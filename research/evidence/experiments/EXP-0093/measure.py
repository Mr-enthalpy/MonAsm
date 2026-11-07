"""Re-run the `EXP-0093` measurements and write the recorded files.

The probe list is the two `0.64.0` rows (the absolute `SIB = 25` shape behind
`0x67` at the 64-bit value width: two directions, where the mandatory `REX.W`
makes `R` a free bit of the same byte) plus eight corners: zero, `-1`,
`2147483647`, `-2147483648`, `%r8` as the load and store value, and `%r15` in
both directions. The adjacent list measures the shapes this slice does not
take: the same absolute row without `0x67`, the 32-bit and 16-bit siblings,
the no-base indexed and base+index neighbours, both `moffs` forms and the
`0x67` RIP-relative row. Two spellings are rejected.

`llvm-mc -show-encoding` prints an explicit `addr32` prefix on its own line,
so the instruction bytes are read from the object file instead; the recorded
`show-encoding.txt` keeps the printer's view for reference.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0093/measure.py
"""

import subprocess
import tempfile
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
LLVM_OBJCOPY = r"C:\Users\hanni\Tools\llvm\bin\llvm-objcopy.exe"
DIR = Path(__file__).resolve().parent

PROBES = [
    ("addr32 movq 4660, %rax", "67488b042534120000", 9),
    ("addr32 movq %rax, 4660", "674889042534120000", 9),
    ("addr32 movq 4660, %r8", "674c8b042534120000", 9),
    ("addr32 movq %r8, 4660", "674c89042534120000", 9),
    ("addr32 movq 0, %rax", "67488b042500000000", 9),
    ("addr32 movq -1, %rax", "67488b0425ffffffff", 9),
    ("addr32 movq 2147483647, %rax", "67488b0425ffffff7f", 9),
    ("addr32 movq -2147483648, %rax", "67488b042500000080", 9),
    ("addr32 movq 4660, %r15", "674c8b3c2534120000", 9),
    ("addr32 movq %r15, 4660", "674c893c2534120000", 9),
]

ADJACENT = [
    ("movq 4660, %rax", "488b042534120000", 8),
    ("addr32 movl 4660, %eax", "678b042534120000", 8),
    ("addr32 movw 4660, %ax", "67668b042534120000", 9),
    ("movq 8(,%rcx,1), %rax", "488b040d08000000", 8),
    ("movq 8(%eax,%ecx,1), %rax", "67488b440808", 6),
    ("movabs 4660, %rax", "48a13412000000000000", 10),
    ("addr32 movabs 4660, %rax", "6748a13412000000000000", 11),
    ("addr32 movq 4660(%rip), %rax", "67488b0534120000", 8),
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
