"""Re-run the `EXP-0097` measurement and write the recorded files.

Five instructions: the three `0.17.0` rows that no fixture named, then the two
boundary values (`imm6 = 63` on the 64-bit row, `imm6 = 31` on the 32-bit row,
the highest value that row's `excluded` list admits).

Usage (from the repository root):

    python research/evidence/experiments/EXP-0097/measure.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
LLVM_MC = shutil.which("llvm-mc")
LLVM_OBJCOPY = shutil.which("llvm-objcopy")

ROWS = [
    ("sub w0, w1, w2, asr #3", "200c824b"),
    ("subs x0, x1, x2, asr #3", "200c82eb"),
    ("subs w0, w1, w2, asr #3", "200c826b"),
    ("subs x3, x4, x5, asr #63", "83fc85eb"),
    ("sub w6, w7, w8, asr #31", "e67c884b"),
]


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main():
    if not LLVM_MC or not LLVM_OBJCOPY:
        raise SystemExit("llvm-mc and llvm-objcopy must be on PATH")
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        obj = folder / "out.o"
        binary = folder / "out.bin"
        subprocess.run(
            [LLVM_MC, "-triple=aarch64", "-filetype=obj",
             str(DIR / "asr-rows.asm"), "-o", str(obj)], check=True)
        subprocess.run(
            [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(obj),
             str(binary)], check=True)
        data = binary.read_bytes()

        expected = "".join(row[1] for row in ROWS)
        assert data.hex() == expected, (data.hex(), expected)
        write(DIR / "bytes.txt", data.hex() + "\n")

        shown = subprocess.run(
            [LLVM_MC, "-triple=aarch64", "-show-encoding",
             str(DIR / "asr-rows.asm")], capture_output=True, text=True,
            check=True).stdout
        write(DIR / "show-encoding.txt", shown.replace("\r\n", "\n"))
        print(data.hex())


if __name__ == "__main__":
    main()
