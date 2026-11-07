"""Re-run the `EXP-0099` measurements and write the recorded files.

Four inputs measure the RV64 `jalr` slice:

* `field.asm` -- the `imm12` field at `0`, `2047` and `-2048`, with `.option
  norvc` so the 4-byte form is what the assembler emits;
* `call.asm` -- `auipc ra, %pcrel_hi(blob)` + `jalr ra, %pcrel_lo(.L0)(ra)`
  against an external symbol, so the object carries the two relocation records;
* `call-resolved.asm` -- the same pair with `.text` at `0x1000` and `L1` at
  `0x1900`, linked, so both fields are measured and the low half's sign bit is
  set;
* `cjalr.asm` -- the same source line with `.option rvc`, which is the two-byte
  `c.jalr`; the absent sibling.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0099/measure.py
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
LLVM_OBJDUMP = shutil.which("llvm-objdump")

FIELD = "678505006780f57f67800580"
CALL = "97000000e7800000"
RESOLVED = "97100000e7800090" + "00" * 2300
CJALR = "8290"


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
    if not (LLVM_MC and LLVM_OBJCOPY and LLVM_READOBJ and LD_LLD and LLVM_OBJDUMP):
        raise SystemExit(
            "llvm-mc, llvm-objcopy, llvm-readobj, llvm-objdump and ld.lld "
            "must be on PATH"
        )
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)

        _, field = assemble(DIR / "field.asm", folder)
        assert field.hex() == FIELD, (field.hex(), FIELD)

        call_obj, call = assemble(DIR / "call.asm", folder)
        assert call.hex() == CALL, (call.hex(), CALL)
        relocations = subprocess.run(
            [LLVM_READOBJ, "--relocations", str(call_obj)],
            capture_output=True, text=True, check=True,
        ).stdout
        lines = [
            line.strip()
            for line in relocations.replace("\r\n", "\n").splitlines()
            if "R_RISCV" in line
        ]
        assert [(line.split()[0], line.split()[1]) for line in lines] == [
            ("0x0", "R_RISCV_PCREL_HI20"),
            ("0x4", "R_RISCV_PCREL_LO12_I"),
        ], lines

        resolved_obj = folder / "resolved.o"
        subprocess.run(
            [LLVM_MC, "-triple=riscv64", "-filetype=obj",
             str(DIR / "call-resolved.asm"), "-o", str(resolved_obj)],
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
        assert data.hex() == RESOLVED, (data.hex()[:32], RESOLVED[:32])

        disassembly = subprocess.run(
            [LLVM_OBJDUMP, "-d", "--no-show-raw-insn", str(elf)],
            capture_output=True, text=True, check=True,
        ).stdout
        disassembly = disassembly.replace("\r\n", "\n").replace(str(elf), "resolved.elf")
        assert "jalr\t-0x700(ra) <L1>" in disassembly, disassembly

        _, cjalr = assemble(DIR / "cjalr.asm", folder)
        assert cjalr.hex() == CJALR, (cjalr.hex(), CJALR)

        write(DIR / "bytes.txt",
              "field.asm %s\ncall.asm %s\ncall-resolved.asm %s\ncjalr.asm %s\n"
              % (field.hex(), call.hex(), data.hex(), cjalr.hex()))
        write(DIR / "relocations.txt", "\n".join(lines) + "\n")

        shown = []
        for source in ("field.asm", "call.asm"):
            shown.append(subprocess.run(
                [LLVM_MC, "-triple=riscv64", "-show-encoding", str(DIR / source)],
                capture_output=True, text=True, check=True,
            ).stdout.replace("\r\n", "\n"))
        write(DIR / "show-encoding.txt", "".join(shown))
        write(DIR / "disassembly.txt", disassembly)

        print(field.hex())
        print(call.hex())
        print(data.hex()[:16])
        print(cjalr.hex())


if __name__ == "__main__":
    main()
