"""Re-run the `EXP-0098` measurements and write the recorded files.

Three inputs measure the absolute `lui` + `addi` split:

* `literal.asm` -- the `lui` field on its own at `0`, `1` and `0xfffff`;
* `pair.asm` -- `lui a0, %hi(blob)` + `addi a0, a0, %lo(blob)` against an
  external symbol, so the object carries the two relocation records;
* `pair-resolved.asm` -- the same pair with `.text` at `0x1000` and `L1` at
  `0x234`, linked, so the resolved bytes are measured rather than derived.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0098/measure.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
LLVM_MC = shutil.which("llvm-mc")
LLVM_OBJCOPY = shutil.which("llvm-objcopy")
LLVM_READOBJ = shutil.which("llvm-readobj")
LD_LLD = shutil.which("ld.lld")

LITERAL = "370500003715000037f5ffff"
PAIR = "3705000013050500"
RESOLVED = "3715000013054523" + "00" * 560


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def assemble(source, folder):
    obj = folder / "out.o"
    binary = folder / "out.bin"
    subprocess.run(
        [LLVM_MC, "-triple=riscv64", "-filetype=obj", str(source), "-o", str(obj)],
        check=True,
    )
    subprocess.run(
        [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(obj), str(binary)],
        check=True,
    )
    return obj, binary.read_bytes()


def main():
    if not LLVM_MC or not LLVM_OBJCOPY or not LLVM_READOBJ:
        raise SystemExit("llvm-mc, llvm-objcopy and llvm-readobj must be on PATH")
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)

        _, literal = assemble(DIR / "literal.asm", folder)
        assert literal.hex() == LITERAL, (literal.hex(), LITERAL)

        pair_obj, pair = assemble(DIR / "pair.asm", folder)
        assert pair.hex() == PAIR, (pair.hex(), PAIR)
        relocations = subprocess.run(
            [LLVM_READOBJ, "--relocations", str(pair_obj)],
            capture_output=True, text=True, check=True,
        ).stdout
        lines = [
            line.strip()
            for line in relocations.replace("\r\n", "\n").splitlines()
            if "R_RISCV" in line
        ]
        assert [line.split()[1] for line in lines] == [
            "R_RISCV_HI20",
            "R_RISCV_LO12_I",
        ], lines

        if not LD_LLD:
            raise SystemExit("ld.lld must be on PATH")
        resolved_obj = folder / "resolved.o"
        subprocess.run(
            [LLVM_MC, "-triple=riscv64", "-filetype=obj",
             str(DIR / "pair-resolved.asm"), "-o", str(resolved_obj)],
            check=True,
        )
        elf = folder / "resolved.elf"
        subprocess.run(
            [LD_LLD, "-m", "elf64lriscv", "--image-base=0", "-Ttext", "0x1000",
             "-o", str(elf), str(resolved_obj)],
            check=True,
        )
        resolved = folder / "resolved.bin"
        subprocess.run(
            [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(elf),
             str(resolved)],
            check=True,
        )
        data = resolved.read_bytes()
        assert data.hex() == RESOLVED, (data.hex(), RESOLVED)

        write(DIR / "bytes.txt",
              "literal.asm %s\npair.asm %s\npair-resolved.asm %s\n"
              % (literal.hex(), pair.hex(), data.hex()))
        write(DIR / "relocations.txt", "\n".join(lines) + "\n")

        shown = subprocess.run(
            [LLVM_MC, "-triple=riscv64", "-show-encoding", str(DIR / "literal.asm")],
            capture_output=True, text=True, check=True,
        ).stdout
        write(DIR / "show-encoding.txt", shown.replace("\r\n", "\n"))
        print(literal.hex())
        print(pair.hex())
        print(data.hex())


if __name__ == "__main__":
    main()
