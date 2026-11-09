#!/usr/bin/env python3
"""Build the `RV-P12` plan and expected bytes.

Eleven instructions: the six new load rows (`lb`, `lh`, `lw`, `lbu`, `lhu`,
`lwu`) and the three new store rows (`sb`, `sh`, `sw`), each at `8(a1)`, plus
`lb a0, -2048(a1)` and `sw a2, 2047(a1)` for the signed 12-bit endpoints. The
load destination is `a0`, the stored register `a2`, the base `a1` in every
row, so a wrong placement would change a byte rather than hide behind a
matching register.

The expected image is the measured `EXP-0116` `RV-P12-load-store-widths.s`,
which `measure.py` assembles and derives field by field.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0116/make_fixture.py
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/rv64/positive/RV-P12-load-store-widths"

EXPECTED = bytes.fromhex(
    "03858500" "03958500" "03a58500"
    "03c58500" "03d58500" "03e58500"
    "2384c500" "2394c500" "23a4c500"
    "03850580" "a3afc57e"
)

DIGEST = "sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585"

# mnemonic, kind, value register, immediate
ROWS = [
    ("lb", "load", 10, 8),
    ("lh", "load", 10, 8),
    ("lw", "load", 10, 8),
    ("lbu", "load", 10, 8),
    ("lhu", "load", 10, 8),
    ("lwu", "load", 10, 8),
    ("sb", "store", 12, 8),
    ("sh", "store", 12, 8),
    ("sw", "store", 12, 8),
    ("lb", "load", 10, -2048),
    ("sw", "store", 12, 2047),
]

BASE = 11


def operand(role: str, kind: str, target_type: str, payload: str) -> str:
    return ('        { "role": "%s", "kind": "%s", "target_type": "%s", '
            '"payload": %s, "modifiers": [] }'
            % (role, kind, target_type, payload))


def main() -> int:
    if len(EXPECTED) != 44:
        raise SystemExit("expected bytes are not 44 long")
    fragments = []
    instructions = []
    for index, (mnemonic, kind, value, imm) in enumerate(ROWS, 1):
        offset = (index - 1) * 4
        instruction_id = "I%04d" % index
        form_id = ("riscv:%s/rd-base-imm12" % mnemonic if kind == "load"
                   else "riscv:%s/rs-base-imm12" % mnemonic)
        value_role = "dest" if kind == "load" else "src"
        fragments.append(
            '        { "offset": %d, "size": 4, "kind": "instruction", '
            '"instruction_id": "%s" }' % (offset, instruction_id))
        instructions.append(
            "    {\n"
            '      "instruction_id": "%s",\n'
            '      "section_id": ".text",\n'
            '      "offset": %d,\n'
            '      "form_id": "%s",\n'
            '      "operands": [\n'
            "%s,\n%s,\n%s\n"
            "      ],\n"
            '      "expected_size": 4\n'
            "    }"
            % (instruction_id, offset, form_id,
               operand(value_role, "riscv.xreg", "xreg",
                       '{ "reg": %d }' % value),
               operand("base", "riscv.xreg", "xreg",
                       '{ "reg": %d }' % BASE),
               operand("disp", "riscv.imm", "imm12",
                       '{ "value": %d }' % imm)))

    text = (
        "{\n"
        '  "format_version": "fmp/0.1",\n'
        '  "target_identity": {\n'
        '    "isa_family": "riscv",\n'
        '    "isa_variant": "rv64",\n'
        '    "execution_mode": "n/a",\n'
        '    "enabled_extensions": ["rv64i", "rv64c"],\n'
        '    "feature_constraints": [],\n'
        '    "byte_order": "little",\n'
        '    "address_width": 64\n'
        "  },\n"
        '  "definition_identity": {\n'
        '    "namespace": "monasm.isa.riscv",\n'
        '    "version": "0.6.0",\n'
        '    "digest": "%s"\n'
        "  },\n"
        '  "output_contract": {\n'
        '    "artifact": "bytes",\n'
        '    "section_order": [".text"],\n'
        '    "fixup_record_order": "section_id,offset,fixup_id",\n'
        '    "include_symbol_table": false,\n'
        '    "emit_fixups": true\n'
        "  },\n"
        '  "sections": [\n'
        "    {\n"
        '      "section_id": ".text",\n'
        '      "section_kind": "code",\n'
        '      "image_backed": true,\n'
        '      "declared_size": %d,\n'
        '      "fragments": [\n%s\n      ]\n'
        "    }\n"
        "  ],\n"
        '  "symbols": [],\n'
        '  "instructions": [\n%s\n  ],\n'
        '  "fixups": []\n'
        "}\n"
        % (DIGEST, len(EXPECTED), ",\n".join(fragments),
           ",\n".join(instructions)))

    with FIXTURE.parent.joinpath(
            "RV-P12-load-store-widths.fmp.json").open(
                "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with FIXTURE.parent.joinpath(
            "RV-P12-load-store-widths.expected.bin").open("wb") as handle:
        handle.write(EXPECTED)
    print("instructions: %d" % len(ROWS))
    print("bytes: %d" % len(EXPECTED))
    print("output sha256: %s" % hashlib.sha256(EXPECTED).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
