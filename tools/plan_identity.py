#!/usr/bin/env python3
"""Independent encoder for `plan-identity/0.1` (`ADR-0127`).

The Rust implementation lives in
`prototype/crates/fmp-model/src/identity.rs`. This file is a second
implementation of the *byte encoding* — same tag table, same field order, same
enum variant numbers — written from the protocol text, not from the Rust source.
Agreement between the two is the `ADR-0127` §3.2 evidence that the protocol is
not an artefact of one language's data layout.

The three vectors are hand-built here. The Rust tests build the same three plans
field by field and assert the same digests, so a changed tag, field order or
variant number in either implementation stops the build.

Usage:

    python tools/plan_identity.py           # print the three vectors
    python tools/plan_identity.py --check   # print and verify the pinned table

No third-party dependency; `hashlib` and `struct` are standard library.
"""

from __future__ import annotations

import hashlib
import struct
import sys

ALGORITHM = "plan-identity/0.1"
DOMAIN = b"plan-identity/0.1\0"


# --- primitive encoders (ADR-0127 §3.2 tag table) ---------------------------

def u8(value: int) -> bytes:
    return b"\x01" + struct.pack("<B", value)


def boolean(value: bool) -> bytes:
    return u8(1 if value else 0)


def u64(value: int) -> bytes:
    return b"\x02" + struct.pack("<Q", value)


def i128(value: int) -> bytes:
    return b"\x03" + value.to_bytes(16, "little", signed=True)


def string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return b"\x04" + struct.pack("<Q", len(encoded)) + encoded


def none() -> bytes:
    return b"\x05"


def some(value: bytes) -> bytes:
    return b"\x06" + value


def vector(items: list[bytes]) -> bytes:
    return b"\x07" + struct.pack("<Q", len(items)) + b"".join(items)


def structure(*fields: bytes) -> bytes:
    return b"\x08" + b"".join(fields)


def enum(variant: int, payload: bytes = b"") -> bytes:
    return b"\x09" + struct.pack("<I", variant) + payload


def digest(facts: bytes) -> str:
    return "sha256:" + hashlib.sha256(DOMAIN + facts).hexdigest()


# --- covered types, in the field order ADR-0127 makes normative -------------

def target(family, variant, mode, extensions, constraints, order, width, path):
    return structure(
        string(family),
        string(variant),
        string(mode),
        vector([string(item) for item in extensions]),
        vector([string(item) for item in constraints]),
        string(order),
        u64(width),
        string(path),
    )


def definition(namespace, version, sha, source_ref, path):
    return structure(
        string(namespace),
        string(version),
        string(sha),
        none() if source_ref is None else some(string(source_ref)),
        string(path),
    )


def output(artifact, section_order, symbol_order, record_order, symbols, fixups, path):
    return structure(
        artifact,
        vector([string(item) for item in section_order]),
        none() if symbol_order is None else some(vector([string(item) for item in symbol_order])),
        string(record_order),
        boolean(symbols),
        boolean(fixups),
        string(path),
    )


def section(section_id, kind, image_backed, base, size, fragments, path):
    return structure(
        string(section_id),
        kind,
        boolean(image_backed),
        none() if base is None else some(u64(base)),
        u64(size),
        vector(fragments),
        string(path),
    )


def fragment(offset, size, body, path):
    return structure(u64(offset), u64(size), body, string(path))


def symbol(symbol_id, name, kind, binding, section_id, offset, path):
    return structure(
        string(symbol_id),
        string(name),
        kind,
        binding,
        none() if section_id is None else some(string(section_id)),
        none() if offset is None else some(u64(offset)),
        string(path),
    )


def instruction(instruction_id, section_id, offset, form_id, operands, size, expected, path):
    return structure(
        string(instruction_id),
        string(section_id),
        u64(offset),
        string(form_id),
        vector(operands),
        u64(size),
        none() if expected is None else some(string(expected)),
        string(path),
    )


def operand(role, kind, target_type, payload, modifiers, path):
    return structure(
        string(role),
        string(kind),
        string(target_type),
        payload,
        vector(modifiers),
        string(path),
    )


def modifier(name, value):
    return structure(string(name), value)


def fixup(fixup_id, section_id, offset, descriptor, target_value, addend,
          pc_rule, transform, transform_shift, constraint, mode,
          pair_group, pair_role, path):
    return structure(
        string(fixup_id),
        string(section_id),
        u64(offset),
        vector(descriptor),
        target_value,
        i128(addend),
        pc_rule,
        transform,
        none() if transform_shift is None else some(u64(transform_shift)),
        constraint,
        mode,
        none() if pair_group is None else some(string(pair_group)),
        none() if pair_role is None else some(pair_role),
        string(path),
    )


def field_range(lsb, width):
    return structure(u64(lsb), u64(width))


def range_constraint(signed, bits, align_bits):
    return structure(boolean(signed), u64(bits), u64(align_bits))


# --- the three fixed plans --------------------------------------------------

def plan(format_version, target_value, definition_value, output_value,
         sections, symbols, instructions, fixups):
    return structure(
        string(format_version),
        target_value,
        definition_value,
        output_value,
        vector(sections),
        vector(symbols),
        vector(instructions),
        vector(fixups),
    )


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def vector_1_minimal():
    """An empty plan: every vector is empty and no option is set."""
    return plan(
        "fmp/0.1",
        target("x86", "x86-64", "64", [], [], "little", 64, "/target_identity"),
        definition("monasm.isa.x86", "0.75.0", SHA_A, None, "/definition_identity"),
        output(enum(0), [], None, "section_offset", False, False, "/output_contract"),
        [], [], [], [],
    )


def vector_2_data_fragment():
    """One image-backed `.text` section with a one-byte data fragment."""
    body = enum(1, string("90"))
    text = section(
        ".text", enum(0), True, None, 1,
        [fragment(0, 1, body, "/sections/0/fragments/0")],
        "/sections/0",
    )
    return plan(
        "fmp/0.1",
        target("x86", "x86-64", "64", [], [], "little", 64, "/target_identity"),
        definition("monasm.isa.x86", "0.75.0", SHA_A, None, "/definition_identity"),
        output(enum(0), [".text"], None, "section_offset", False, False, "/output_contract"),
        [text], [], [], [],
    )


def vector_3_unknown_variants():
    """Every `unknown` variant, every `Some`, and all three payload shapes."""
    custom = section(
        "s", enum(4, string("custom")), False, 4096, 0,
        [fragment(3, 0, enum(2, u8(0xCC)), "/sections/0/fragments/0")],
        "/sections/0",
    )
    one_symbol = symbol(
        "s0", "n", enum(3, string("k")), enum(3, string("b")), "s", 7, "/symbols/0",
    )
    one_operand = operand(
        "src", "k", "t", enum(1, i128(-5)),
        [modifier("m", enum(0, i128(-1))),
         modifier("n", enum(1, string("x"))),
         modifier("o", enum(2, boolean(True)))],
        "/instructions/0/operands/0",
    )
    one_instruction = instruction(
        "i0", "s", 0, "f", [one_operand], 0, SHA_B, "/instructions/0",
    )
    one_fixup = fixup(
        "f0", "s", 9, [field_range(1, 2)], enum(3, string("t")), -3,
        enum(5, string("r")), enum(8, string("v")), 4,
        range_constraint(True, 2, 1), enum(2, string("m")),
        "g", enum(2, string("u")), "/fixups/0",
    )
    return plan(
        "fmp/0.1",
        target("x86", "x86-64", "64", ["avx"], [], "little", 64, "/target_identity"),
        definition("monasm.isa.x86", "0.75.0", SHA_A, None, "/definition_identity"),
        output(enum(2, string("future")), ["a", "b"], ["s"], "declared",
               True, True, "/output_contract"),
        [custom], [one_symbol], [one_instruction], [one_fixup],
    )


VECTORS = {
    "minimal": vector_1_minimal(),
    "data-fragment": vector_2_data_fragment(),
    "unknown-variants": vector_3_unknown_variants(),
}

# Filled from a run of this file and pinned in `ADR-0127` §3.2. The Rust tests
# assert the same strings, so neither side can drift silently.
PINNED = {
    "minimal": "sha256:a48faecec39dd1de38f13b4868559f307b575a95a0aa241a01caa325400422c4",
    "data-fragment": "sha256:9da5a3318e943bcbd5c9c32366708922b68a5e7e7c67a0b3d48a9c7b1a68eec2",
    "unknown-variants": "sha256:1a07ae98cba50f7ee65b36bbe2bb1684eaa0885f728270b9baa39824a2a4632a",
}


def main(argv: list[str]) -> int:
    status = 0
    for name, facts in VECTORS.items():
        value = digest(facts)
        print(f"{name}\t{value}\tfacts={facts.hex()}")
        if "--check" in argv and PINNED[name] and PINNED[name] != value:
            print(f"  pinned {PINNED[name]} does not match", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
