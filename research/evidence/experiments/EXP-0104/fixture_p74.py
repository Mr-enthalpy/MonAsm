#!/usr/bin/env python3
"""Write `fixtures/x86_64/positive/X86-P74-per-form-requirements.{fmp.json,
expected.bin}` and its `oracle.json`.

The instructions are exactly `X86-P20`'s 24 VEX.256 memory rows, re-pinned to
the first `fmp-def/0.2` table. Only the target identity changes:

- `definition_identity` names `0.68.0` and its digest;
- `enabled_extensions` becomes `["avx"]`, a strict subset of the table's
  `["avx", "avx512f", "avx512vl"]` that still covers every named form.

`expected.bin` is copied from `llvm-objcopy` running on `EXP-0045/P20.asm`, the
same oracle input the `X86-P20` record names; the materializer never produces
it.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0104/fixture_p74.py <oracle.bin>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/x86_64/positive"
SOURCE = FIXTURES / "X86-P20-vex-ymm-memory.fmp.json"
STEM = "X86-P74-per-form-requirements"
ORACLE_ASM = ROOT / "research/evidence/experiments/EXP-0045/P20.asm"

VERSION = "0.68.0"
DIGEST = "sha256:4c9ff304b305ceb831fd99e22bf0a7c422cce4104d08de604a6509f58e1501d2"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fixture_p74.py <oracle.bin>")
    oracle = Path(sys.argv[1])
    if oracle.stat().st_size != 144:
        raise SystemExit("oracle is %d bytes, expected 144"
                         % oracle.stat().st_size)

    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    if document["definition_identity"]["version"] != "0.16.0":
        raise SystemExit("source plan is not pinned to 0.16.0")
    if len(document["instructions"]) != 24:
        raise SystemExit("source plan has %d instructions, expected 24"
                         % len(document["instructions"]))
    if any(not instruction["form_id"].endswith("/vex")
           for instruction in document["instructions"]):
        raise SystemExit("source plan is not all VEX rows")

    document["target_identity"]["enabled_extensions"] = ["avx"]
    document["definition_identity"] = {
        "namespace": "monasm.isa.x86",
        "version": VERSION,
        "digest": DIGEST,
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
                    "research/evidence/experiments/EXP-0045/P20.asm -o out.o "
                    "&& llvm-objcopy -O binary --only-section=.text out.o out.bin"),
        "kind": "assembler",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "size": 144,
        "records": 0,
        "notes": (
            "Same measurement as X86-P20 (same input_sha256): 24 VEX.256 "
            "memory instructions, 144 bytes. This record supersedes the "
            "X86-P20 pin only in the definition: the plan now names 0.68.0 "
            "and declares the AVX subset [\"avx\"], which the table's "
            "per-form requirements accept. The bytes are unchanged, so the "
            "re-pin exercises the fmp-def/0.2 gate rather than a new "
            "encoding."
        ),
    }
    oracle_path = FIXTURES / (STEM + ".oracle.json")
    with oracle_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(oracle_document, indent=2) + "\n")

    print("%s: 24 instructions, 144 bytes" % STEM)
    print("input_sha256  %s" % input_sha)
    print("output_sha256 %s" % output_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
