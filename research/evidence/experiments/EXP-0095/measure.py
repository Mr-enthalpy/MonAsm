"""Re-run the `EXP-0095` measurements and write the recorded files.

The probe list is nine instructions that name one external symbol in an
absolute 32-bit content field: eight 32-bit displacements (the four value
widths, both directions, the extended prefixes, the high-byte row and one
EVEX vector row) and one 32-bit immediate. The adjacent list measures the
neighbouring spellings this slice does not take: the same symbol in a
RIP-relative displacement (`R_X86_64_PC32`), in `moffs` (`R_X86_64_64`), in a
`mov` immediate that has no form yet (`R_X86_64_32`) and in an `add`
immediate that does (`R_X86_64_32S`). Three value widths are rejected.

The second half places `.text` at `0x1000` with `ld.lld` and reads the bytes
of the same field after resolution, so `resolve_in_place` is measured too, not
derived.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0095/measure.py
"""

import subprocess
import tempfile
from pathlib import Path

LLVM_MC = r"C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe"
LLVM_OBJCOPY = r"C:\Users\hanni\Tools\llvm\bin\llvm-objcopy.exe"
LLVM_READOBJ = r"C:\Users\hanni\Tools\llvm\bin\llvm-readobj.exe"
LLVM_NM = r"C:\Users\hanni\Tools\llvm\bin\llvm-nm.exe"
LLVM_OBJDUMP = r"C:\Users\hanni\Tools\llvm\bin\llvm-objdump.exe"
LD_LLD = r"C:\Users\hanni\Tools\llvm\bin\ld.lld.exe"
DIR = Path(__file__).resolve().parent

PROBES = [
    ("movl ext, %eax", "8b042500000000", 7),
    ("movl %eax, ext", "89042500000000", 7),
    ("movl ext, %r8d", "448b042500000000", 8),
    ("movq ext, %rax", "488b042500000000", 8),
    ("movw %r9w, ext", "6644890c2500000000", 9),
    ("movb %ah, ext", "88242500000000", 7),
    ("movb ext, %al", "8a042500000000", 7),
    ("vmovaps ext, %zmm1", "62f17c48280c2500000000", 11),
    ("addq $ext, %rax", "4881c000000000", 7),
]

ADJACENT = [
    ("movl ext, %eax", "8b042500000000", 7),
    ("movl ext(%rip), %eax", "8b0500000000", 6),
    ("movabs ext, %rax", "48a10000000000000000", 10),
    ("movl $ext, %eax", "b800000000", 5),
    ("addq $ext, %rax", "4881c000000000", 7),
]

RESOLVED = [
    ("movq L1, %rax", "488b04251e100000", 8),
    ("movl L1+4, %eax", "8b042522100000", 7),
    ("movl %ecx, L1", "890c251e100000", 7),
    ("movw %dx, L1+2", "6689142520100000", 8),
    ("movb L1, %al", "8a04251e100000", 7),
]


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def run(tool, source, target, extra=()):
    command = [tool, "-triple=x86_64"] + list(extra) + [str(DIR / source)]
    result = subprocess.run(command, capture_output=True, text=True)
    text = (result.stdout + result.stderr).replace("\r\n", "\n")
    write(DIR / target, text)
    return result.returncode, text


def assemble(source, folder):
    obj = Path(folder) / "out.o"
    result = subprocess.run(
        [LLVM_MC, "-triple=x86_64", "-filetype=obj", str(DIR / source),
         "-o", str(obj)], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stdout + result.stderr)
    return obj


def object_bytes(source, folder):
    obj = assemble(source, folder)
    binary = Path(folder) / "out.bin"
    subprocess.run(
        [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(obj),
         str(binary)], check=True)
    return binary.read_bytes()


def check(source, table, folder):
    data = object_bytes(source, folder)
    expected = "".join(row[1] for row in table)
    actual = data.hex()
    assert actual == expected, (actual, expected)
    assert len(data) == sum(row[2] for row in table), len(data)
    return data


def relocations_of(obj):
    """`llvm-readobj --relocations` with the temporary path normalized."""
    text = subprocess.run(
        [LLVM_READOBJ, "--relocations", str(obj)],
        capture_output=True, text=True, check=True).stdout
    text = text.replace("\r\n", "\n").replace(str(obj), "out.o")
    return text.replace(str(Path(obj).parent), "<tmp>")


with tempfile.TemporaryDirectory() as folder:
    probe = check("probe.asm", PROBES, folder)
    write(DIR / "probe-bytes.txt", probe.hex() + "\n")
    write(DIR / "probe-lengths.txt",
          " ".join(str(row[2]) for row in PROBES) + "\n")
    run(LLVM_MC, "probe.asm", "show-encoding.txt", ("-show-encoding",))
    relocations = relocations_of(assemble("probe.asm", folder))
    write(DIR / "relocations.txt", relocations)
    assert relocations.count("R_X86_64_32S ext 0x0") == 9, relocations

    adjacent = check("adjacent.asm", ADJACENT, folder)
    write(DIR / "adjacent-bytes.txt", adjacent.hex() + "\n")
    run(LLVM_MC, "adjacent.asm", "adjacent-show-encoding.txt",
        ("-show-encoding",))
    adjacent_relocations = relocations_of(assemble("adjacent.asm", folder))
    write(DIR / "adjacent-relocations.txt", adjacent_relocations)
    for kind in ("R_X86_64_32S", "R_X86_64_PC32", "R_X86_64_64",
                 "R_X86_64_32 "):
        assert kind in adjacent_relocations, (kind, adjacent_relocations)

    # `resolve_in_place`: assembled, then linked at a fixed address so the
    # bytes in the field are the linker's, not ours.
    resolved_obj = assemble("resolved.asm", folder)
    resolved_relocations = relocations_of(resolved_obj)
    write(DIR / "resolved-relocations.txt", resolved_relocations)
    assert resolved_relocations.count("R_X86_64_32S .text") == 5, \
        resolved_relocations
    symbols = subprocess.run(
        [LLVM_NM, str(resolved_obj)], capture_output=True, text=True,
        check=True).stdout.replace("\r\n", "\n")
    assert "t L1" in symbols, symbols

    elf = Path(folder) / "resolved.elf"
    subprocess.run(
        [LD_LLD, "-m", "elf_x86_64", "--image-base=0", "-Ttext", "0x1000",
         "-o", str(elf), str(resolved_obj)], capture_output=True, text=True,
        check=True)
    linked_symbols = subprocess.run(
        [LLVM_NM, str(elf)], capture_output=True, text=True,
        check=True).stdout.replace("\r\n", "\n")
    write(DIR / "resolved-symbols.txt", linked_symbols)
    assert "000000000000101e t L1" in linked_symbols, linked_symbols
    binary = Path(folder) / "resolved.bin"
    subprocess.run(
        [LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", str(elf),
         str(binary)], check=True)
    resolved = binary.read_bytes()
    expected = "".join(row[1] for row in RESOLVED)
    assert resolved.hex() == expected, (resolved.hex(), expected)
    write(DIR / "resolved-bytes.txt", resolved.hex() + "\n")
    dis = subprocess.run(
        [LLVM_OBJDUMP, "-d", "--no-show-raw-insn", str(elf)],
        capture_output=True, text=True, check=True)
    write(DIR / "resolved-disassembled.txt",
          dis.stdout.replace("\r\n", "\n").replace(str(elf), "resolved.elf"))

rejected_code, rejected_text = run(
    LLVM_MC, "rejected.asm", "rejected.txt", ("-show-encoding",))
assert rejected_code != 0, rejected_code
assert rejected_text.count("error: invalid operand for instruction") == 3

# `llvm-mc -disassemble` on the object bytes names the field's value.
lines = [",".join("0x" + probe.hex()[i:i + 2]
                  for i in range(0, len(probe.hex()), 2))]
write(DIR / "probes.txt", "\n".join(lines) + "\n")
dis = subprocess.run(
    [LLVM_MC, "-triple=x86_64", "-disassemble", str(DIR / "probes.txt")],
    capture_output=True, text=True)
dis_text = (dis.stdout + dis.stderr).replace("\r\n", "\n")
write(DIR / "probes-disassembled.txt", dis_text)
assert dis_text.count("movl") == 3, dis_text
assert dis_text.count("zmm1") == 1, dis_text

print(probe.hex())
print(resolved.hex())
