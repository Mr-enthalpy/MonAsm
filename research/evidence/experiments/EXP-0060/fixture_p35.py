#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P35-gpr8-mov-mem-nodisp.{fmp.json,expected.bin}`
and its `oracle.json`.

The instruction order matches `EXP-0060/fixture.asm`, which is the oracle
input. Every one of the eight rows appears exactly once: load and store in the
four byte-register windows at `mod = 00`, so each instruction is opcode plus
`ModRM` (two bytes) or one `REX` byte plus those two (three bytes). The bases
stay inside the legal set -- `%rax`, `%rcx`, `%rdx`, `%rbx`, `%rsi`, `%rdi`,
`%r8`, `%r9` -- because `%rsp`/`%r12` would need a `SIB` byte and `%rbp`/`%r13`
collide with `r/m = 101`. `expected.bin` is copied from `llvm-objcopy`, never
produced by the materializer.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0060/fixture_p35.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
STEM = "X86-P35-gpr8-mov-mem-nodisp"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0060/fixture.asm"

VERSION = "0.31.0"
DIGEST = "sha256:cc01b72ceed0c77e5079b53ea8f3035ebf44b02fd156f1aae207044cb44327d5"

# (form_id, role, kind, target_type, register, base, size)
PLAN = [
    ("x86:mov/r8-base/legacy", "dest", "x86.gpr8", "r8", 0, 0, 2),
    ("x86:mov/base-r8/legacy", "src", "x86.gpr8", "r8", 1, 1, 2),
    ("x86:mov/r8h-base/legacy", "dest", "x86.gpr8h", "r8h", 4, 2, 2),
    ("x86:mov/base-r8h/legacy", "src", "x86.gpr8h", "r8h", 7, 3, 2),
    ("x86:mov/r8-base-rex/legacy", "dest", "x86.gpr8", "r8", 7, 6, 3),
    ("x86:mov/base-r8-rex/legacy", "src", "x86.gpr8", "r8", 6, 7, 3),
    ("x86:mov/r8-ext-base/legacy", "dest", "x86.gpr8", "r8", 8, 8, 3),
    ("x86:mov/base-r8-ext/legacy", "src", "x86.gpr8", "r8", 15, 9, 3),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p35.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    total = sum(entry[6] for entry in PLAN)
    if oracle.stat().st_size != total:
        raise SystemExit("oracle is %d bytes, plan says %d"
                         % (oracle.stat().st_size, total))

    offset = 0
    fragments = []
    instructions = []
    for index, entry in enumerate(PLAN, 1):
        form_id, role, kind, target_type, reg, base, size = entry
        instruction_id = "I%04d" % index
        fragments.append({"offset": offset, "size": size, "kind": "instruction",
                          "instruction_id": instruction_id})
        instructions.append({
            "instruction_id": instruction_id,
            "section_id": ".text",
            "offset": offset,
            "form_id": form_id,
            "operands": [
                {"role": role, "kind": kind, "target_type": target_type,
                 "payload": {"reg": reg}, "modifiers": []},
                {"role": "base", "kind": "x86.gpr64", "target_type": "rm64",
                 "payload": {"reg": base}, "modifiers": []},
            ],
            "expected_size": size,
        })
        offset += size

    document = {
        "format_version": "fmp/0.1",
        "target_identity": {
            "isa_family": "x86",
            "isa_variant": "x86-64",
            "execution_mode": "64",
            "enabled_extensions": ["avx", "avx512f", "avx512vl"],
            "feature_constraints": [],
            "byte_order": "little",
            "address_width": 64,
        },
        "definition_identity": {
            "namespace": "monasm.isa.x86",
            "version": VERSION,
            "digest": DIGEST,
        },
        "output_contract": {
            "artifact": "bytes",
            "section_order": [".text"],
            "fixup_record_order": "section_id,offset,fixup_id",
            "include_symbol_table": False,
            "emit_fixups": True,
        },
        "sections": [
            {
                "section_id": ".text",
                "section_kind": "code",
                "image_backed": True,
                "declared_size": total,
                "fragments": fragments,
            }
        ],
        "symbols": [],
        "instructions": instructions,
        "fixups": [],
    }

    target = FIXTURES / (STEM + ".fmp.json")
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2) + "\n")
    shutil.copyfile(oracle, FIXTURES / (STEM + ".expected.bin"))

    source = ORACLE_ASM.read_bytes()
    output = (FIXTURES / (STEM + ".expected.bin")).read_bytes()
    input_sha = hashlib.sha256(source).hexdigest()
    output_sha = hashlib.sha256(output).hexdigest()

    oracle_document = {
        "tool": "llvm-mc 23.1.2 + llvm-objcopy",
        "version": "23.1.2",
        "command": ("llvm-mc -triple=x86_64 -filetype=obj "
                    "research/evidence/experiments/EXP-0060/fixture.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": total,
        "records": 0,
        "notes": (
            "One byte-width mov per 0.31.0 row, eight instructions, 20 bytes: "
            "load and store in the four register windows at mod = 00, where the "
            "row is opcode plus ModRM and nothing else. The low and high "
            "windows have no REX byte (8a 00, 88 09, 8a 22, 88 3b, two bytes "
            "each); the REX = 40 window relabels 4-7 (40 8a 3e, 40 88 37) and "
            "the REX.R window reaches r8b-r15b (45 8a 00, 45 88 39), both "
            "three bytes. The base is ModRM.r/m at [8,3] for the three-bit "
            "rows and REX.B at [0,1] plus [16,3] for the four-bit rows. The "
            "base set here is %rax, %rcx, %rdx, %rbx, %rsi, %rdi, %r8, %r9; "
            "%rsp/%r12 would need a SIB byte and %rbp/%r13 collide with "
            "r/m = 101 (llvm-mc writes %rbp as 8a 45 00, mod = 01). The "
            "disp8/disp32 twins (8a 40 00, 8a 80 00 00 00 00) stay separate "
            "rows, and movabsb (A0/A2) is a fourth shape. input_sha256 is "
            "fixture.asm (the source above); output_sha256 is the 20-byte "
            ".text."
        ),
    }
    oracle_path = FIXTURES / (STEM + ".oracle.json")
    with oracle_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(oracle_document, indent=2) + "\n")

    print("%s: %d instructions, %d bytes" % (STEM, len(PLAN), total))
    print("input_sha256  %s" % input_sha)
    print("output_sha256 %s" % output_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
