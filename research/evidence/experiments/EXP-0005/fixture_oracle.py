"""Regenerate the x86-64 positive fixtures' oracle records.

The expected bytes are produced by LLVM, never by the materializer under test.
`llvm-mc` assembles the committed `.asm` input to an object file, `llvm-objcopy`
extracts `.text`, and that byte string becomes `*.expected.bin`. The script then
records the tool version, the exact command, and the SHA-256 of both the input
and the output, so the measurement can be repeated from a clean checkout.

Two cases cannot be produced from a mnemonic and are handled explicitly:

- `X86-P1`'s `8B /r` half: `llvm-mc` always picks `89 /r` for
  `movq %rbx, %rax`. The second instruction's bytes are therefore verified by
  disassembly, and the record says `manual+disassembly` rather than pretending a
  tool emitted them.
- `X86-P8`'s external branch: the assembled bytes are `e9 00 00 00 00` plus one
  `R_X86_64_PLT32 ext -4` relocation. The record's `records` count is 1; the
  materializer's `pcrel_end` with `addend = 0` is the same value
  (`03_fixup_model.md` §6.1).
- `X86-P6`'s external load: `movq ext(%rip), %rbx` assembles to
  `48 8b 1d 00 00 00 00` plus one `R_X86_64_PC32 ext -4` relocation at the
  `disp32` field. Its `records` count is 1, for the same `pcrel_end` reason.

Run with `--check` to verify the committed files still match without rewriting.
"""

import hashlib
import io
import json
import os
import subprocess
import sys

TOOLS = r"C:\Users\hanni\Tools\llvm\bin"
LLVM_MC = os.path.join(TOOLS, "llvm-mc.exe")
LLVM_OBJCOPY = os.path.join(TOOLS, "llvm-objcopy.exe")
LLVM_READOBJ = os.path.join(TOOLS, "llvm-readobj.exe")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
POSITIVE = os.path.join(ROOT, "fixtures", "x86_64", "positive")

CASES = [
    {
        "stem": "X86-P1-mov-r64-both-directions",
        "asm": "P1.asm",
        "suffix": bytes.fromhex("488bc3"),
        "records": 0,
        "kind": "manual+disassembly",
        "notes": (
            "First instruction is emitted by llvm-mc (`movq %rbx, %rax` -> 48 89 d8). "
            "The second is the 8B /r encoding of the same move, which llvm-mc will not "
            "select from a mnemonic; its bytes are verified by `llvm-mc -disassemble`, "
            "which prints `movq %rbx, %rax`."
        ),
    },
    {
        "stem": "X86-P2-add-imm8-and-imm32",
        "asm": "P2.asm",
        "suffix": b"",
        "records": 0,
        "kind": "assembler",
        "notes": "83 /0 ib for the imm8 form, 81 /0 id for the imm32 form; both measured.",
    },
    {
        "stem": "X86-P3-two-legal-encodings",
        "asm": "P3.asm",
        "suffix": b"",
        "records": 0,
        "kind": "assembler",
        "notes": (
            "The same operation in two legal encodings: 05 id (the rax form) and "
            "81 /0 id. The encoder never chooses between them; the plan names the form. "
            "llvm-mc always picks the rax short form when the destination is rax, so the "
            "81 /0 half is measured on rbx; the 81 /0 encoding with rax is decode-verified "
            "in EXP-0004."
        ),
    },
    {
        "stem": "X86-P7-short-and-near-branch",
        "asm": "P7.asm",
        "suffix": b"",
        "records": 0,
        "kind": "assembler",
        "notes": (
            "`jmp .+0x81` -> eb 7f, `jmp .+0x82` -> e9 7d 00 00 00. llvm-mc promotes to "
            "rel32 when rel8 does not fit; the plan states each form explicitly, so the "
            "fixture pairs the two forms rather than proving promotion."
        ),
    },
    {
        "stem": "X86-P4-base-disp",
        "asm": "P4.asm",
        "suffix": bytes.fromhex("488b8508000000"),
        "records": 0,
        "kind": "manual+disassembly",
        "notes": (
            "The assembled part exercises `mod=01`/`mod=10` on `%rbp` and the SIB shape "
            "for `%rsp`: `movq 0(%rbp),%rax` is 48 8b 45 00 (not RIP), `movq "
            "4096(%rbp),%rbx` is 48 8b 9d 00 10 00 00, `movq 8(%rsp),%rsi` is 48 8b 74 "
            "24 08, and the two stores use opcode 89. The appended 48 8b 85 08 00 00 00 "
            "is `mod=10` with a displacement that would fit `disp8`; llvm-mc never "
            "selects it from a mnemonic, so it is derived from the ModRM rule and "
            "verified by `llvm-mc -disassemble`, which prints `movq 8(%rbp), %rax`. It "
            "pins that the disp32 form is not shortened (INV-02)."
        ),
    },
    {
        "stem": "X86-P6-rip-relative",
        "asm": "P6.asm",
        "suffix": b"",
        "records": 1,
        "kind": "assembler",
        "notes": (
            "`movq 16(%rip), %rax` is a literal disp32; `movq L1(%rip), %rcx` and "
            "`movq %rdx, L1(%rip)` resolve against L1 at 0x20 (disp 0x12 and 0x09); "
            "`movq ext(%rip), %rbx` assembles to 48 8b 1d 00 00 00 00 with "
            "R_X86_64_PC32 ext -4, and our pcrel_end with addend 0 is the same value."
        ),
        "relocation_check": (
            "llvm-readobj --relocations reports "
            "'0x27 R_X86_64_PC32 ext 0xFFFFFFFFFFFFFFFC'"
        ),
    },
    {
        "stem": "X86-P8-local-and-external-branch",
        "asm": "P8.asm",
        "suffix": b"",
        "records": 1,
        "kind": "assembler",
        "notes": (
            "`jmp L1` resolves in place (e9 cb 00 00 00; L1 is 203 bytes after the end "
            "of the instruction). `jmp ext` assembles to e9 00 00 00 00 with "
            "R_X86_64_PLT32 ext -4; our pcrel_end with addend 0 is the same value."
        ),
        "relocation_check": (
            "llvm-readobj --relocations reports "
            "'0xD5 R_X86_64_PLT32 ext 0xFFFFFFFFFFFFFFFC'"
        ),
    },
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run(argv, stdin=None):
    result = subprocess.run(
        argv,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        raise SystemExit("command failed: " + " ".join(argv))
    return result.stdout


def tool_version():
    text = run([LLVM_MC, "--version"]).decode("utf-8", "replace")
    # First non-empty line after the leading blank: "LLVM (http://llvm.org/):"
    # then "  LLVM version 23.1.2". Take the version token.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("LLVM version "):
            return stripped[len("LLVM version "):]
    raise SystemExit("could not read llvm-mc version")


def assemble_bytes(asm_path):
    work = os.path.join(HERE, "_work")
    os.makedirs(work, exist_ok=True)
    obj = os.path.join(work, os.path.basename(asm_path) + ".o")
    raw = os.path.join(work, os.path.basename(asm_path) + ".bin")
    run([LLVM_MC, "-triple=x86_64", "-filetype=obj", asm_path, "-o", obj])
    run([LLVM_OBJCOPY, "-O", "binary", "--only-section=.text", obj, raw])
    with open(raw, "rb") as handle:
        data = handle.read()
    os.remove(obj)
    os.remove(raw)
    try:
        os.rmdir(work)
    except OSError:
        pass
    return data


def disassemble(data):
    # `llvm-mc -disassemble` reads hex tokens from stdin, not raw bytes.
    text = " ".join("0x%02x" % byte for byte in data) + "\n"
    out = run([LLVM_MC, "-triple=x86_64", "-disassemble"], stdin=text.encode("ascii"))
    return out.decode("utf-8", "replace").strip()


def main():
    check = "--check" in sys.argv[1:]
    version = tool_version()
    failures = []

    for case in CASES:
        asm_path = os.path.join(HERE, case["asm"])
        with open(asm_path, "rb") as handle:
            asm_bytes = handle.read()
        assembled = assemble_bytes(asm_path) + case["suffix"]
        stem = case["stem"]
        bin_path = os.path.join(POSITIVE, stem + ".expected.bin")
        json_path = os.path.join(POSITIVE, stem + ".oracle.json")

        command = (
            "llvm-mc -triple=x86_64 -filetype=obj {asm} -o out.o && "
            "llvm-objcopy -O binary --only-section=.text out.o out.bin"
        ).format(asm=case["asm"])

        record = {
            "tool": "llvm-mc " + version + " + llvm-objcopy",
            "version": version,
            "command": command,
            "kind": case["kind"],
            "input_sha256": sha256(asm_bytes),
            "output_sha256": sha256(assembled),
            "size": len(assembled),
            "records": case["records"],
            "notes": case["notes"],
        }
        if case["suffix"]:
            record["disassembly"] = disassemble(case["suffix"])
        if case.get("relocation_check"):
            record["relocation_check"] = case["relocation_check"]

        encoded = json.dumps(record, indent=2, sort_keys=False) + "\n"
        if check:
            with open(bin_path, "rb") as handle:
                if handle.read() != assembled:
                    failures.append(stem + ": expected.bin differs")
            with open(json_path, "r", encoding="utf-8") as handle:
                if json.load(handle) != json.loads(encoded):
                    failures.append(stem + ": oracle.json differs")
        else:
            with io.open(bin_path, "wb") as handle:
                handle.write(assembled)
            with io.open(json_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
        print("{:<40} {:>4} bytes  {}  records={}".format(
            stem, len(assembled), sha256(assembled)[:16], case["records"]))

    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
