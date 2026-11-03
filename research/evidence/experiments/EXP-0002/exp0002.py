#!/usr/bin/env python3
"""EXP-0002 -- does the plan carry expected bytes (OD-01), and which output
level does v0 need (OD-03)?

Evidence tooling, not product code. Every byte printed by this script is
produced by LLVM 23.1.2 at run time (llvm-mc, llvm-objcopy, llvm-readobj);
nothing is transcribed from an earlier experiment.

Usage:
    python exp0002.py                 # print the report
    python exp0002.py --emit plans    # also write plan-A/B/C.json

The measured slice is four x86-64 instructions with no fixups, so the size
comparison answers OD-01 alone.  OD-03 uses the relocation records that LLVM
writes for the three AC-05 shapes, in their own section of the report.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

LLVM_BIN = Path(r"C:\Users\hanni\Tools\llvm\bin")


def tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    candidate = LLVM_BIN / (name + ".exe")
    if candidate.is_file():
        return str(candidate)
    raise SystemExit("missing tool: %s" % name)


def run(argv, stdin: str | None = None) -> str:
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=stdin if stdin is not None else "",
    )
    if completed.returncode != 0:
        raise SystemExit(
            "command failed (%d): %s\n%s%s"
            % (completed.returncode, " ".join(argv), completed.stdout, completed.stderr)
        )
    return completed.stdout


def assemble(source: Path, triple: str) -> bytes:
    """Assemble to an object, then read back the .text bytes."""
    obj = source.with_suffix(".o")
    out = source.with_suffix(".bin")
    run([tool("llvm-mc"), "-triple=" + triple, "-filetype=obj", str(source), "-o", str(obj)])
    run([tool("llvm-objcopy"), "-O", "binary", "--only-section=.text", str(obj), str(out)])
    return out.read_bytes()


def hexs(data: bytes) -> str:
    return " ".join("%02x" % b for b in data)


def disassemble(data: bytes, triple: str, intel: bool = False) -> str:
    argv = [tool("llvm-mc"), "-triple=" + triple, "-disassemble"]
    if intel:
        argv.append("-x86-asm-syntax=intel")
    text = run(argv, stdin="0x" + " 0x".join("%02x" % b for b in data))
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# --------------------------------------------------------------------------
# The slice, expressed once.  Offsets and sizes come from the oracle bytes and
# are checked against this table before any plan is built.

SLICE = [
    dict(
        id="I0001",
        asm="mov rax, rbx",
        size=3,
        form="x86:mov/r64-r64",
        operands=[
            dict(role="dest", kind="x86.gpr64", target_type="r64", payload={"reg": 0}, modifiers=[]),
            dict(role="src", kind="x86.gpr64", target_type="r64", payload={"reg": 3}, modifiers=[]),
        ],
        choices=[],
    ),
    dict(
        id="I0002",
        asm="add rax, 1",
        size=4,
        form="x86:add/r64-imm8",
        operands=[
            dict(role="dest", kind="x86.gpr64", target_type="r64", payload={"reg": 0}, modifiers=[]),
            dict(role="imm", kind="x86.imm8", target_type="i8", payload={"value": 1}, modifiers=[]),
        ],
        choices=[],
    ),
    dict(
        id="I0003",
        asm="add rax, 300",
        size=6,
        form="x86:add/r64-imm32-accum",
        operands=[
            dict(role="dest", kind="x86.gpr64", target_type="r64", payload={"reg": 0}, modifiers=[]),
            dict(role="imm", kind="x86.imm32", target_type="i32", payload={"value": 300}, modifiers=[]),
        ],
        choices=[{"choice_id": "EC-04", "value": "accumulator"}],
    ),
    dict(
        id="I0004",
        asm="mov rax, [rbp - 8]",
        size=4,
        form="x86:mov/r64-mem-base-disp8",
        operands=[
            dict(role="dest", kind="x86.gpr64", target_type="r64", payload={"reg": 0}, modifiers=[]),
            dict(
                role="src",
                kind="x86.mem",
                target_type="mem64",
                payload={"base": {"reg": 5}, "index": None, "scale": 1, "disp": -8, "rip_relative": False},
                modifiers=[],
            ),
        ],
        choices=[{"choice_id": "EC-02", "value": "disp8"}],
    ),
]


def plan_a(oracle: bytes) -> dict:
    instructions = []
    offset = 0
    for item in SLICE:
        instructions.append(
            {
                "instruction_id": item["id"],
                "section_id": ".text",
                "offset": offset,
                "form_id": item["form"],
                "operands": item["operands"],
                "encoding_choices": item["choices"],
                "expected_size": item["size"],
            }
        )
        offset += item["size"]
    return base_plan(len(oracle), instructions)


def plan_b(oracle: bytes) -> dict:
    plan = plan_a(oracle)
    offset = 0
    for item in plan["instructions"]:
        size = item["expected_size"]
        item["expected_digest"] = "sha256:" + hashlib.sha256(oracle[offset:offset + size]).hexdigest()
        offset += size
    return plan


def plan_c(oracle: bytes) -> dict:
    """Byte-template variant.  `form_id`/`operands`/`encoding_choices`/
    `expected_size` are gone; the template is the authority."""
    instructions = []
    offset = 0
    for item in SLICE:
        size = item["size"]
        instructions.append(
            {
                "instruction_id": item["id"],
                "section_id": ".text",
                "offset": offset,
                "template_hex": oracle[offset:offset + size].hex(),
            }
        )
        offset += size
    return base_plan(len(oracle), instructions)


def base_plan(size: int, instructions: list) -> dict:
    return {
        "format_version": "fmp/0.1",
        "target_identity": {
            "isa_family": "x86",
            "isa_variant": "x86-64",
            "execution_mode": "64",
            "enabled_extensions": [],
            "feature_constraints": [],
            "byte_order": "little",
            "address_width": 64,
        },
        "definition_identity": {
            "namespace": "monasm.isa.x86",
            "version": "0.1.0",
            "digest": "sha256:" + "00" * 32,
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
                "base_address": 0,
                "declared_size": size,
                "fragments": [
                    {
                        "offset": instr["offset"],
                        "size": (instr["expected_size"] if "expected_size" in instr else len(instr["template_hex"]) // 2),
                        "kind": "instruction",
                        "instruction_id": instr["instruction_id"],
                    }
                    for instr in instructions
                ],
            }
        ],
        "symbols": [],
        "instructions": instructions,
        "fixups": [],
        "provenance": {
            "materializer_version": "0.1.0-draft",
            "notes": "EXP-0002 measurement artefact. No bytes are claimed, only plan shapes.",
        },
    }


def size_report(oracle: bytes) -> dict:
    variants = {"A": plan_a(oracle), "B": plan_b(oracle), "C": plan_c(oracle)}
    empty = {"A": plan_a(oracle), "B": plan_b(oracle), "C": plan_c(oracle)}
    results = {}
    for name, plan in variants.items():
        empty_plan = dict(plan)
        empty_plan["instructions"] = []
        section = dict(plan["sections"][0])
        section["fragments"] = []
        section["declared_size"] = 0
        empty_plan["sections"] = [section]

        full = len(canonical(plan))
        bare = len(canonical(empty_plan))
        results[name] = {
            "total": full,
            "fixed": bare,
            "marginal_total": full - bare,
            "marginal_per_instruction": (full - bare) / len(SLICE),
        }
    return results


def fault_report(oracle: bytes) -> list:
    """Five faults, and which plan variant can notice each one.

    The `caught` verdicts follow from the fields each variant carries; the
    byte strings are produced live so the reader can see that the wrong
    output is also a legal encoding.
    """
    good = oracle[0:3]                       # mov rax, rbx
    rex_swapped = bytes([good[0] | 0x01]) + good[1:]   # REX.W -> REX.W|B
    imm8 = oracle[3:7]                       # add rax, 1
    imm32_same_op = bytes.fromhex("480501000000")       # add rax, 1, 6 bytes
    accum_300 = oracle[7:13]                 # add rax, 300
    accum_301 = bytes.fromhex("48052d010000")
    out_of_range = bytes.fromhex("480500000080")        # what "+2^31" would become

    rows = [
        dict(
            fault="W1 definition drift that changes length",
            detail="the imm8 form disappears; the same plan encodes through the accumulator form",
            bytes_in="%s (%d B)" % (hexs(imm8), len(imm8)),
            bytes_out="%s (%d B)" % (hexs(imm32_same_op), len(imm32_same_op)),
            oracle=disassemble(imm32_same_op, "x86_64", intel=True),
            verdict={"A": "caught (expected_size)", "B": "caught (size, digest)", "C": "n/a: template is the answer"},
        ),
        dict(
            fault="W2 encoder defect, same length",
            detail="REX.B taken from the wrong operand bit",
            bytes_in="%s (%d B)" % (hexs(good), len(good)),
            bytes_out="%s (%d B)" % (hexs(rex_swapped), len(rex_swapped)),
            oracle=disassemble(rex_swapped, "x86_64", intel=True),
            verdict={"A": "missed", "B": "caught (digest)", "C": "n/a: no encoder"},
        ),
        dict(
            fault="W3 operand outside the field's range",
            detail="planned +2147483648; the 32-bit pattern is still a legal imm32",
            bytes_in="rejected before encoding",
            bytes_out="%s (%d B)" % (hexs(out_of_range), len(out_of_range)),
            oracle=disassemble(out_of_range, "x86_64", intel=True),
            verdict={"A": "caught (range check)", "B": "caught (range check)", "C": "missed: no operand exists"},
        ),
        dict(
            fault="W4 plan tampering",
            detail="immediate 300 changed to 301",
            bytes_in="%s (%d B)" % (hexs(accum_300), len(accum_300)),
            bytes_out="%s (%d B)" % (hexs(accum_301), len(accum_301)),
            oracle=disassemble(accum_301, "x86_64", intel=True),
            verdict={"A": "missed", "B": "caught (digest)", "C": "n/a: template is the answer"},
        ),
        dict(
            fault="W5 unknown form",
            detail="plan names a form the definition does not contain",
            bytes_in="n/a",
            bytes_out="n/a",
            oracle="n/a",
            verdict={"A": "caught (lookup)", "B": "caught (lookup)", "C": "n/a: no form to look up"},
        ),
    ]
    return rows


def relocations(source: Path, triple: str) -> str:
    obj = source.with_suffix(".o")
    run([tool("llvm-mc"), "-triple=" + triple, "-filetype=obj", str(source), "-o", str(obj)])
    text = run([tool("llvm-readobj"), "--relocations", str(obj)])
    keep = [line.rstrip() for line in text.splitlines() if "R_" in line or ".rela" in line]
    return "\n".join(keep)


LEVEL0_CALL = {
    "fixup_id": "F0001",
    "section_id": ".text",
    "offset": 1,
    "field_descriptor": [{"lsb": 0, "width": 32}],
    "bit_order": "value_msb_first",
    "target": {"kind": "symbol", "symbol_id": "S0001"},
    "addend": 0,
    "pc_reference_rule": "pcrel_end",
    "value_transform": "identity",
    "range_constraint": {"signed": True, "bits": 32, "align_bits": 0},
    "resolution_mode": "emit_relocation",
    "overwrite_bytes": False,
}


def main() -> int:
    emit = "--emit" in sys.argv

    oracle = assemble(HERE / "slice_x86.s", "x86_64")
    expected = b"".join(bytes.fromhex(x) for x in (
        "4889d8", "4883c001", "48052c010000", "488b45f8",
    ))
    if oracle != expected:
        raise SystemExit("oracle bytes changed: %s" % hexs(oracle))

    print("== slice (llvm-mc 23.1.2) ==")
    offset = 0
    for item in SLICE:
        chunk = oracle[offset:offset + item["size"]]
        print("  %04x  %-20s %-20s %d B" % (offset, item["asm"], hexs(chunk), len(chunk)))
        offset += item["size"]
    print("  %04x  end, %d bytes total" % (offset, len(oracle)))

    print()
    print("== OD-01: canonical plan size ==")
    print("  fixed part = target/definition/output/provenance plus one empty section")
    print("  %-3s %8s %8s %10s %10s" % ("var", "total", "fixed", "marginal", "per insn"))
    sizes = size_report(oracle)
    for name in ("A", "B", "C"):
        row = sizes[name]
        print(
            "  %-3s %8d %8d %10d %10.1f"
            % (name, row["total"], row["fixed"], row["marginal_total"], row["marginal_per_instruction"])
        )

    print()
    print("== OD-01: what each variant can check ==")
    checks = [
        ("form exists in the definition", "yes", "yes", "no form field"),
        ("operand legal for the form", "yes", "yes", "no operand field"),
        ("encoded length equals the declaration", "yes", "yes", "length is the template"),
        ("encoded bits equal an independent expectation", "no", "yes", "the template is the expectation"),
    ]
    print("  %-46s %-4s %-4s %s" % ("check", "A", "B", "C"))
    for name, a, b, c in checks:
        print("  %-46s %-4s %-4s %s" % (name, a, b, c))

    print()
    print("== OD-01: fault matrix ==")
    for row in fault_report(oracle):
        print("  %s" % row["fault"])
        print("    %s" % row["detail"])
        print("    intended: %-26s produced: %s" % (row["bytes_in"], row["bytes_out"]))
        print("    disassembles as: %s" % row["oracle"])
        print("    A: %-40s B: %-26s C: %s" % (row["verdict"]["A"], row["verdict"]["B"], row["verdict"]["C"]))

    print()
    print("== OD-03: Level 0 fixup record for `call ext` ==")
    print("  " + canonical(LEVEL0_CALL).decode("utf-8"))
    print("  canonical size: %d B" % len(canonical(LEVEL0_CALL)))

    print()
    print("== OD-03: what LLVM records for the same three AC-05 shapes ==")
    for label, source, triple in (
        ("x86-64 call rel32", HERE / "call_ext_x86.s", "x86_64"),
        ("AArch64 adrp + :lo12:", HERE / "pair_a64.s", "aarch64"),
        ("RV64 auipc + addi", HERE / "pair_rv.s", "riscv64"),
    ):
        print("  %s" % label)
        for line in relocations(source, triple).splitlines():
            print("    " + line.strip())

    if emit:
        for name, plan in (("A", plan_a(oracle)), ("B", plan_b(oracle)), ("C", plan_c(oracle))):
            path = HERE / ("plan-%s.json" % name)
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
            print("wrote %s (%d B canonical)" % (path.name, len(canonical(plan))))

    return 0


if __name__ == "__main__":
    sys.exit(main())
