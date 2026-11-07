"""Re-run the `EXP-0101` measurements and write the recorded files.

Five inputs measure the AArch64 unconditional-transfer slice:

* `field.asm` -- `b #0`, `b #4`, `b #-4`, so the three `imm26` values 0, 1 and
  -1 are measured against the assembler's byte displacement;
* `indirect.asm` -- `br`/`blr`/`ret` with six register values, so the three
  `op` settings and `Rn` are both measured;
* `local.asm` -- three `b` instructions resolved against labels at 0, 4 and 8,
  so the field values 2, 0 and -2 come from arithmetic the assembler performs;
* `extern.asm` -- `b ext` and `bl ext`, whose two relocation kinds differ;
* `default.asm` -- the assembler's bare `ret`, which is `ret x30`.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0101/measure.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
LLVM_MC = shutil.which("llvm-mc")
LLVM_OBJCOPY = shutil.which("llvm-objcopy")
LLVM_READOBJ = shutil.which("llvm-readobj")

FIELD = "00000014" "01000014" "ffffff17"
INDIRECT = "20001fd6" "00001fd6" "40003fd6" "c0035fd6" "00005fd6" "60025fd6"
LOCAL = "02000014" "00000014" "feffff17"
EXTERN = "00000014" "00000094"
DEFAULT = "c0035fd6"


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def assemble(source, folder):
    obj = folder / "out.o"
    binary = folder / "out.bin"
    subprocess.run(
        [LLVM_MC, "-triple=aarch64", "-filetype=obj", str(source), "-o", str(obj)],
        check=True,
    )
    subprocess.run(
        [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(obj), str(binary)],
        check=True,
    )
    return obj, binary.read_bytes()


def main():
    if not (LLVM_MC and LLVM_OBJCOPY and LLVM_READOBJ):
        raise SystemExit("llvm-mc, llvm-objcopy and llvm-readobj must be on PATH")
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)

        _, field = assemble(DIR / "field.asm", folder)
        assert field.hex() == FIELD, (field.hex(), FIELD)

        _, indirect = assemble(DIR / "indirect.asm", folder)
        assert indirect.hex() == INDIRECT, (indirect.hex(), INDIRECT)

        _, local = assemble(DIR / "local.asm", folder)
        assert local.hex() == LOCAL, (local.hex(), LOCAL)

        extern_obj, extern = assemble(DIR / "extern.asm", folder)
        assert extern.hex() == EXTERN, (extern.hex(), EXTERN)
        relocations = subprocess.run(
            [LLVM_READOBJ, "--relocations", str(extern_obj)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        lines = [
            line.strip()
            for line in relocations.replace("\r\n", "\n").splitlines()
            if "R_AARCH64" in line
        ]
        kinds = [(line.split()[0], line.split()[1]) for line in lines]
        assert kinds == [
            ("0x0", "R_AARCH64_JUMP26"),
            ("0x4", "R_AARCH64_CALL26"),
        ], kinds

        _, default = assemble(DIR / "default.asm", folder)
        assert default.hex() == DEFAULT, (default.hex(), DEFAULT)

        write(
            DIR / "bytes.txt",
            "field.asm %s\nindirect.asm %s\nlocal.asm %s\nextern.asm %s\n"
            "default.asm %s\n"
            % (field.hex(), indirect.hex(), local.hex(), extern.hex(), default.hex()),
        )
        write(DIR / "relocations.txt", "\n".join(lines) + "\n")

        shown = []
        for source in ("field.asm", "indirect.asm", "local.asm", "extern.asm",
                       "default.asm"):
            shown.append(
                subprocess.run(
                    [LLVM_MC, "-triple=aarch64", "-show-encoding", str(DIR / source)],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.replace("\r\n", "\n")
            )
        write(DIR / "show-encoding.txt", "".join(shown))

        print(field.hex())
        print(indirect.hex())
        print(local.hex())
        print(extern.hex())
        print(default.hex())


if __name__ == "__main__":
    main()
