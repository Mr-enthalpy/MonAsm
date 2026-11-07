"""Re-run the `EXP-0096` measurements and write the recorded files.

Seven families the contract still marks `draft` (`EC-10`, `EC-16`, `EC-18`,
`EC-23`, `EC-24`, `EC-25`, `EC-26`). Each probe file isolates one family, the
object bytes are asserted against the recorded expectation, and
`llvm-mc -show-encoding` keeps the printer's view for reference. Every
expectation here was measured with LLVM 23.1.2 on 2026-11-08; none of them is
computed by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0096/measure.py
"""

import subprocess
import tempfile
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
LLVM_OBJCOPY = r"C:\Users\hanni\Tools\llvm\bin\llvm-objcopy.exe"
DIR = Path(__file__).resolve().parent

# (file stem, triple, extra llvm-mc arguments, expected .text hex, lengths)
FILES = [
    ("ec10-x86-prefix", "x86_64", (),
     "0318f00318a4f3a4648b042500000000", (2, 3, 1, 2, 8)),
    ("ec16-a64-mov-alias", "aarch64", (),
     "200080d200008092e00301aa2000a0d220008052", (4, 4, 4, 4, 4)),
    ("ec18-a64-cond-branch", "aarch64", (),
     "00000054000000b400000035000000360000f8b7", (4, 4, 4, 4, 4)),
    ("ec23-rv64-call", "riscv64", (),
     "ef00000001a001a082906f000000e7800000", (4, 2, 2, 2, 4, 4)),
    ("ec24-rv64-fence", "riscv64", (),
     "0f0030030f00f00f0f001002", (4, 4, 4)),
    ("ec25-rv64-csr", "riscv64", (),
     "f3100130f3500130", (4, 4)),
    ("ec26-rv64-amo", "riscv64", ("-mattr=+zaamo",),
     "afa02100afa02104afa02102afa02106", (4, 4, 4, 4)),
]

# Substrings that must appear in the recorded `-show-encoding` text.
MARKERS = {
    "ec10-x86-prefix": ("0x03,0x18]", "0xf0,0x03,0x18]", "0xa4]",
                        "0xf3,0xa4]", "0x64,0x8b,0x04,0x25"),
    "ec16-a64-mov-alias": ("0xd2]", "0x92]", "0xaa]", "0x52]"),
    "ec18-a64-cond-branch": ("0x54]", "0xb4]", "0x35]", "0x36]", "0xb7]"),
    "ec23-rv64-call": ("0xef,", "0x82,0x90]", "0x6f,", "0xe7,0x80"),
    "ec24-rv64-fence": ("0x0f,0x00,0x30,0x03]", "0x0f,0x00,0xf0,0x0f]",
                        "0x0f,0x00,0x10,0x02]"),
    "ec25-rv64-csr": ("0xf3,0x10,0x01,0x30]", "0xf3,0x50,0x01,0x30]"),
    "ec26-rv64-amo": ("0x00]", "0x04]", "0x02]", "0x06]"),
}


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def object_bytes(stem, triple, extra):
    with tempfile.TemporaryDirectory() as folder:
        obj = Path(folder) / "out.o"
        binary = Path(folder) / "out.bin"
        result = subprocess.run(
            [LLVM_MC, "-triple=" + triple] + list(extra)
            + ["-filetype=obj", str(DIR / (stem + ".asm")), "-o", str(obj)],
            capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(result.stdout + result.stderr)
        subprocess.run(
            [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(obj),
             str(binary)], check=True)
        return binary.read_bytes()


def show(stem, triple, extra, target):
    result = subprocess.run(
        [LLVM_MC, "-triple=" + triple] + list(extra)
        + ["-show-encoding", str(DIR / (stem + ".asm"))],
        capture_output=True, text=True)
    text = (result.stdout + result.stderr).replace("\r\n", "\n")
    if result.returncode != 0:
        raise SystemExit(text)
    write(DIR / target, text)
    return text


recorded = {}

for stem, triple, extra, expected, lengths in FILES:
    data = object_bytes(stem, triple, extra)
    assert data.hex() == expected, (stem, data.hex(), expected)
    assert len(data) == sum(lengths), (stem, len(data))
    write(DIR / (stem + "-bytes.txt"), data.hex() + "\n")
    write(DIR / (stem + "-lengths.txt"),
          " ".join(str(length) for length in lengths) + "\n")
    text = show(stem, triple, extra, stem + "-show-encoding.txt")
    for marker in MARKERS[stem]:
        assert marker in text, (stem, marker)
    recorded[stem] = data.hex()

# The recorded printer text already shows the shape each family takes: the
# compressed jump prints as `j` with a two-byte `[0bAAAAAA01,0b101AAAAA]`
# encoding while `jal ra` keeps a four-byte `[0xef,...]`, and the three
# `mov` spellings print as MOVZ, MOVN and ORR.

for stem in recorded:
    print(stem, len(recorded[stem]) // 2, recorded[stem])
