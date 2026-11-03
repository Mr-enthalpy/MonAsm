#!/usr/bin/env python3
"""EXP-0003: x86-64 same-semantics encoding pairs, measured with llvm-mc.

Answers one question for ADR-0004 / OD-11: for each alias pair in the v0 x86
slice, is the difference a residual choice, or a distinct row of the ISA opcode
table?  Every pair below is produced or decoded by llvm-mc 23.1.2 without any
project code, so the materializer is not validating itself.

Usage:
    python exp0003.py                # print the table
    python exp0003.py --emit         # rewrite the measured table in README.md

The LLVM directory can be overridden with FMP_LLVM_BIN.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

LLVM_BIN = Path(os.environ.get("FMP_LLVM_BIN", r"C:\Users\hanni\Tools\llvm\bin"))
LLVM_MC = LLVM_BIN / "llvm-mc.exe"
LLVM_OBJDUMP = LLVM_BIN / "llvm-objdump.exe"

HERE = Path(__file__).resolve().parent
README = HERE / "README.md"

# Non-branch snippets: `-show-encoding` resolves them fully.
ASSEMBLE_CASES = [
    ("mov rax, rbx", "mov rax, rbx"),
    ("mov eax, ebx", "mov eax, ebx"),
    ("add rax, 1", "add rax, 1"),
    ("add rax, 300", "add rax, 300"),
    ("mov eax, 300", "mov eax, 300"),
]

# Branch snippets: need a real assembly because -show-encoding leaves a fixup.
OBJECT_CASES = [
    ("jmp .+0x81", "jmp .+0x81"),
    ("jmp .+0x82", "jmp .+0x82"),
    ("jmp .+0x1000", "jmp .+0x1000"),
    ("jmp 0x12", "jmp 0x12"),
    ("jmp 0x7f", "jmp 0x7f"),
    ("jmp 0x80", "jmp 0x80"),
    ("jmp 0x1000", "jmp 0x1000"),
    ("jmp 5", "jmp 5"),
]

# Bytes to decode, as a claim about what else is legal.
DISASSEMBLE_CASES = [
    ("48 89 d8", [0x48, 0x89, 0xD8]),
    ("48 8b c3", [0x48, 0x8B, 0xC3]),
    ("40 89 d8", [0x40, 0x89, 0xD8]),
    ("89 d8", [0x89, 0xD8]),
    ("48 81 c0 2c 01 00 00", [0x48, 0x81, 0xC0, 0x2C, 0x01, 0x00, 0x00]),
    ("c7 c0 2c 01 00 00", [0xC7, 0xC0, 0x2C, 0x01, 0x00, 0x00]),
    ("eb 0e", [0xEB, 0x0E]),
    ("e9 fb 0f 00 00", [0xE9, 0xFB, 0x0F, 0x00, 0x00]),
]


def run(args, stdin: str = "") -> str:
    completed = subprocess.run(
        [str(a) for a in args],
        input=stdin,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed: %s\n%s" % (args, completed.stderr.strip())
        )
    return completed.stdout


def assemble_encoding(source: str) -> str:
    """Return the `# encoding: [...]` field for a fully resolved snippet."""
    out = run(
        [
            LLVM_MC,
            "-triple=x86_64",
            "-x86-asm-syntax=intel",
            "-show-encoding",
        ],
        stdin=source + "\n",
    )
    match = re.search(r"encoding: \[([0-9a-fx,]+)\]", out)
    if not match:
        raise RuntimeError("no encoding in output for %r:\n%s" % (source, out))
    return match.group(1).replace("0x", "").replace(",", " ").lower()


def assemble_object(source: str) -> str:
    """Assemble to an object and return the first instruction's bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "case.s"
        obj = Path(tmp) / "case.o"
        with src.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(source + "\n")
        run([LLVM_MC, "-triple=x86_64", "-filetype=obj", src, "-o", obj])
        out = run([LLVM_OBJDUMP, "-d", obj])
    match = re.search(r"^\s+0:\s+((?:[0-9a-f]{2} )+)", out, re.MULTILINE)
    if not match:
        raise RuntimeError("no encoding in object dump for %r:\n%s" % (source, out))
    return match.group(1).strip()


def disassemble(data) -> str:
    payload = " ".join("0x%02x" % byte for byte in data)
    out = run([LLVM_MC, "-triple=x86_64", "-disassemble"], stdin=payload + "\n")
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if not lines:
        return ""
    return re.sub(r"\s+", " ", lines[0])


def measure():
    rows = []
    for label, source in ASSEMBLE_CASES:
        rows.append(("assemble", label, assemble_encoding(source), ""))
    for label, source in OBJECT_CASES:
        rows.append(("assemble", label, assemble_object(source), ""))
    for label, data in DISASSEMBLE_CASES:
        rows.append(("disassemble", label, "", disassemble(data)))
    return rows


def render(rows) -> str:
    lines = [
        "| Direction | Input | Bytes | Decodes as |",
        "|---|---|---|---|",
    ]
    for direction, label, code, text in rows:
        if direction == "assemble":
            lines.append("| assemble | `%s` | `%s` | |" % (label, code))
        else:
            lines.append("| disassemble | `%s` | | `%s` |" % (label, text))
    return "\n".join(lines)


def main() -> int:
    rows = measure()
    table = render(rows)
    if "--emit" in sys.argv:
        text = README.read_text(encoding="utf-8")
        start = "<!-- measured-table:start -->"
        end = "<!-- measured-table:end -->"
        if start not in text or end not in text:
            print("README is missing the measured-table markers", file=sys.stderr)
            return 1
        head, rest = text.split(start, 1)
        _, tail = rest.split(end, 1)
        with README.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(head + start + "\n" + table + "\n" + end + tail)
        print("rewrote the measured table in %s" % README)
        return 0
    print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
