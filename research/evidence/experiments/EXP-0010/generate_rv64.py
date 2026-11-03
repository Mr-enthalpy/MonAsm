#!/usr/bin/env python3
"""Generate `definitions/rv64/0.1.0.json` from the pinned UDB resolved spec.

This is disposable research tooling (ADR-0007 §Decision 7). The shipped artifact
is the JSON document plus its digest; this script is how that document was
derived and how it stays traceable to the instruction nodes it reads.

What it does, per form:

1. Reads the UDB node named in the spec. Only the `encoding` block is read:
   `match` (fixed bits) and `variables[]` (`location`, `sign_extend`,
   `left_shift`, `not`). `operation()` is never read (INV-06).
2. Turns each variable's `location` into `{bit_offset, width}` placements. The
   source lists instruction bit groups in value order, most significant first,
   so no scatter is hand-written here; `beq`, `jal` and `auipc` are derived.
3. Refuses to emit unless every bit of the word is covered exactly once by a
   fixed bit or a slot placement, and unless the bits `match` calls variable are
   exactly the bits the placements own.
4. Refuses to emit a form whose source states `not:` — `fmp-def/0.1` has no
   non-zero constraint, so `c.addi` stays out of v0 (ADR-0007 §Decision 5).
5. Re-encodes a small set of probe vectors from the table it just built and
   compares them with the `llvm-mc 23.1.2` bytes recorded in EXP-0009 §6.

Reads:  research/external/rv64-udb/gen/resolved_spec/_/inst/...  (pinned by
        tools/check_rv64_source.py)
Writes: definitions/rv64/0.1.0.json

Usage:
    python research/evidence/experiments/EXP-0010/generate_rv64.py
"""

import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

SPEC_ROOT = os.path.join(
    ROOT, "research", "external", "rv64-udb", "gen", "resolved_spec", "_", "inst"
)
OUT = os.path.join(ROOT, "definitions", "rv64", "0.1.0.json")

DOCUMENT = {
    "definition_format": "fmp-def/0.1",
    "namespace": "monasm.isa.riscv",
    "version": "0.1.0",
    "target_identity": {
        "isa_family": "riscv",
        "isa_variant": "rv64",
        "execution_mode": "n/a",
        # Every v0 form is a base-ISA `I` node (asserted per node below), so the
        # document declares the base extension set. The contract's own example
        # is ["rv64i","rv64m","rv64c"]; one set covers the whole document and is
        # compared exactly with the plan's (07_definition_format.md §2).
        "enabled_extensions": ["rv64i"],
        "byte_order": "little",
        "address_width": 64,
    },
}

# One entry per row of 07_definition_format.md §8.4.
#
# `udb_extension` is the node's `definedBy.extension.name`; the generator
# asserts it instead of inferring it. `operands` is in plan operand order. Each
# entry names the UDB variable that carries it; the placement list is derived
# from that variable's `location`.
FORMS = [
    {
        "form_id": "riscv:add/rd-rs1-rs2",
        "node": "I/add.yaml",
        "udb_name": "add",
        "udb_extension": "I",
        "operands": [
            ("dest", "riscv.xreg", "xreg", "reg_number", "xd", None, 0),
            ("src", "riscv.xreg", "xreg", "reg_number", "xs1", None, 0),
            ("src2", "riscv.xreg", "xreg", "reg_number", "xs2", None, 0),
        ],
        "covers": "`RV-P1`",
    },
    {
        "form_id": "riscv:addi/rd-rs1-imm12",
        "node": "I/addi.yaml",
        "udb_name": "addi",
        "udb_extension": "I",
        "operands": [
            ("dest", "riscv.xreg", "xreg", "reg_number", "xd", None, 0),
            ("src", "riscv.xreg", "xreg", "reg_number", "xs1", None, 0),
            ("imm", "riscv.imm", "imm12", "operand_value", "imm", True, 0),
        ],
        "covers": "`RV-P2`",
    },
    {
        "form_id": "riscv:beq/rs1-rs2-imm12",
        "node": "I/beq.yaml",
        "udb_name": "beq",
        "udb_extension": "I",
        "operands": [
            ("src", "riscv.xreg", "xreg", "reg_number", "xs1", None, 0),
            ("src2", "riscv.xreg", "xreg", "reg_number", "xs2", None, 0),
            # B-type immediate: 12 field bits over four placements, `left_shift`
            # 1 in the source. The slot holds field content; a byte offset is a
            # `scale` fixup with `transform_shift: 1`.
            ("target", "riscv.rel", "imm12", "operand_value", "imm", True, 1),
        ],
        "covers": "`RV-P4`, `RV-P6`",
    },
    {
        "form_id": "riscv:jal/rd-imm20",
        "node": "I/jal.yaml",
        "udb_name": "jal",
        "udb_extension": "I",
        "operands": [
            ("dest", "riscv.xreg", "xreg", "reg_number", "xd", None, 0),
            # J-type immediate: 20 field bits over four placements, shift 1.
            ("target", "riscv.rel", "imm20", "operand_value", "imm", True, 1),
        ],
        "covers": "`RV-P5`, `RV-P6`",
    },
    {
        "form_id": "riscv:auipc/rd-imm20",
        "node": "I/auipc.yaml",
        "udb_name": "auipc",
        "udb_extension": "I",
        "operands": [
            ("dest", "riscv.xreg", "xreg", "reg_number", "xd", None, 0),
            # U-type immediate: 20 field bits, `left_shift` 12. The `%pcrel_hi`
            # pair half of RV-P8 is not in this form: it needs the psABI
            # `R_RISCV_PCREL_HI20`/`LO12_I` relation, which the encoding block
            # does not state (ADR-0007 §Decision 9, EXP-0009 §9).
            ("target", "riscv.rel", "imm20", "operand_value", "imm", True, 12),
        ],
        "covers": "`RV-P8` (field half)",
    },
]

# (form_id, {variable: field value}, oracle bytes, assembler text). The bytes
# were produced by `llvm-mc 23.1.2 -triple=riscv64`; for `auipc a0, -1` the
# assembler wants the unsigned spelling of the same 20-bit field, so the oracle
# line says 1048575.
VECTORS = [
    ("riscv:add/rd-rs1-rs2", {"dest": 10, "src": 11, "src2": 12},
     "33 85 c5 00", "add a0, a1, a2"),
    ("riscv:addi/rd-rs1-imm12", {"dest": 10, "src": 11, "imm": -2048},
     "13 85 05 80", "addi a0, a1, -2048"),
    ("riscv:beq/rs1-rs2-imm12", {"src": 10, "src2": 11, "target": 4},
     "63 04 b5 00", "beq a0, a1, 8"),
    ("riscv:beq/rs1-rs2-imm12", {"src": 10, "src2": 11, "target": -4},
     "e3 0c b5 fe", "beq a0, a1, -8"),
    ("riscv:jal/rd-imm20", {"dest": 1, "target": 4},
     "ef 00 80 00", "jal ra, 8"),
    ("riscv:jal/rd-imm20", {"dest": 1, "target": -4},
     "ef f0 9f ff", "jal ra, -8"),
    ("riscv:auipc/rd-imm20", {"dest": 10, "target": 1},
     "17 15 00 00", "auipc a0, 1"),
    ("riscv:auipc/rd-imm20", {"dest": 10, "target": -1},
     "17 f5 ff ff", "auipc a0, 1048575"),
]

NAME_LINE = re.compile(r"^(\s*)-\s+name:\s*(\S+)\s*$")
PROP_LINE = re.compile(r"^\s+([a-z_]+):\s*(.*?)\s*$")
MATCH_LINE = re.compile(r"^\s+match:\s*(.*?)\s*$")
BLOCK_LINE = re.compile(r"^  ([A-Za-z0-9_]+):\s*$")


def unquote(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def defined_by_extension(lines):
    for index, line in enumerate(lines):
        if line.rstrip() == "definedBy:":
            for following in lines[index + 1:index + 12]:
                found = re.match(r"^\s+name:\s*(\S+)\s*$", following)
                if found:
                    return found.group(1)
            return None
    return None


def encoding_body(lines, block):
    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == "encoding:":
            start = index
            break
    if start is None:
        raise SystemExit("no `encoding:` block")

    body = []
    for line in lines[start + 1:]:
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        body.append(line)

    first = next((line for line in body if line.strip()), "")
    found = BLOCK_LINE.match(first)
    if found:
        wanted = found.group(1)
        if block is None:
            raise SystemExit("node has block {0!r}; say which one".format(wanted))
        if wanted != block:
            raise SystemExit("node has block {0!r}, wanted {1!r}".format(wanted, block))
        nested = []
        after = body[body.index(first) + 1:]
        for line in after:
            if line and not line.startswith("    "):
                break
            nested.append(line)
        body = nested
    elif block is not None:
        raise SystemExit("node has no {0!r} block".format(block))

    return body


def parse_node(path, block):
    with io.open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    body = encoding_body(lines, block)

    match = None
    for line in body:
        found = MATCH_LINE.match(line)
        if found:
            match = unquote(found.group(1))
            break
    if match is None:
        raise SystemExit("{0}: no `match`".format(path))

    variables = {}
    current = None
    for line in body:
        found = NAME_LINE.match(line)
        if found:
            current = found.group(2)
            if current in variables:
                raise SystemExit("{0}: duplicate variable {1}".format(path, current))
            variables[current] = {
                "name": current,
                "location": None,
                "left_shift": 0,
                "sign_extend": False,
                "not": False,
            }
            continue
        if current is None:
            continue
        found = PROP_LINE.match(line)
        if not found:
            continue
        key, value = found.group(1), found.group(2)
        if key == "location":
            variables[current]["location"] = unquote(value)
        elif key == "left_shift":
            variables[current]["left_shift"] = int(unquote(value))
        elif key == "sign_extend":
            variables[current]["sign_extend"] = unquote(value) == "true"
        elif key == "not":
            variables[current]["not"] = True

    for variable in variables.values():
        if variable["location"] is None:
            raise SystemExit(
                "{0}: variable {1} has no location".format(path, variable["name"])
            )

    return {
        "path": path,
        "width": len(match),
        "match": match,
        "extension": defined_by_extension(lines),
        "variables": variables,
    }


def groups_of(location):
    """Split `31|7|30-25|11-8` into [(hi, lo, width)] in value order."""
    groups = []
    for part in location.split("|"):
        if "-" in part:
            hi, lo = part.split("-")
        else:
            hi = lo = part
        hi, lo = int(hi), int(lo)
        if hi < lo:
            raise SystemExit("location group {0!r} is inverted".format(part))
        groups.append((hi, lo, hi - lo + 1))
    return groups


def build(spec, node):
    width = node["width"]
    if width % 8 != 0 or width not in (16, 32):
        raise SystemExit(
            "{0}: {1}-bit word; this generator models 16/32-bit forms".format(
                spec["form_id"], width
            )
        )
    if node["extension"] != spec["udb_extension"]:
        raise SystemExit(
            "{0}: definedBy extension {1!r}, expected {2!r}".format(
                spec["form_id"], node["extension"], spec["udb_extension"]
            )
        )

    match = node["match"]
    if len(match) != width:
        raise SystemExit(
            "{0}: match is {1} chars for a {2}-bit word".format(
                spec["form_id"], len(match), width
            )
        )
    word = 0
    fixed_bits = set()
    variable_bits = set()
    for index, character in enumerate(match):
        bit = width - 1 - index
        if character == "1":
            word |= 1 << bit
            fixed_bits.add(bit)
        elif character == "0":
            fixed_bits.add(bit)
        elif character == "-":
            variable_bits.add(bit)
        else:
            raise SystemExit(
                "{0}: match character {1!r} is not 0/1/-".format(
                    spec["form_id"], character
                )
            )

    slots = []
    owned = {}
    for role, kind, target_type, source, name, signed, shift in spec["operands"]:
        variable = node["variables"].get(name)
        if variable is None:
            raise SystemExit(
                "{0}: variable {1!r} is not in the node".format(spec["form_id"], name)
            )
        if variable["not"]:
            raise SystemExit(
                "{0}: variable {1!r} states `not:`, which fmp-def/0.1 cannot "
                "express; the form stays out of v0 (ADR-0007)".format(
                    spec["form_id"], name
                )
            )

        groups = groups_of(variable["location"])
        placements = [{"bit_offset": lo, "width": w} for _hi, lo, w in groups]
        total = sum(w for _hi, _lo, w in groups)

        if source == "reg_number":
            if signed is not None or shift:
                raise SystemExit(
                    "{0}/{1}: a register slot has no range".format(
                        spec["form_id"], role
                    )
                )
            if variable["sign_extend"] or variable["left_shift"]:
                raise SystemExit(
                    "{0}/{1}: register variable states sign/scale".format(
                        spec["form_id"], role
                    )
                )
        else:
            if signed is None:
                raise SystemExit(
                    "{0}/{1}: operand_value slot needs a signedness".format(
                        spec["form_id"], role
                    )
                )
            if variable["sign_extend"] != signed:
                raise SystemExit(
                    "{0}/{1}: source sign_extend {2}, table says {3}".format(
                        spec["form_id"], role, variable["sign_extend"], signed
                    )
                )
            if variable["left_shift"] != shift:
                raise SystemExit(
                    "{0}/{1}: source left_shift {2}, expected {3}".format(
                        spec["form_id"], role, variable["left_shift"], shift
                    )
                )

        for hi, lo, group_width in groups:
            for bit in range(lo, lo + group_width):
                if bit in owned:
                    raise SystemExit(
                        "{0}: bit {1} is claimed by both {2} and {3}".format(
                            spec["form_id"], bit, owned[bit], role
                        )
                    )
                if bit in fixed_bits:
                    raise SystemExit(
                        "{0}: bit {1} is fixed by the match and claimed by {2}".format(
                            spec["form_id"], bit, role
                        )
                    )
                owned[bit] = role

        slot = {
            "role": role,
            "kind": kind,
            "target_type": target_type,
            "from": source,
        }
        if source == "operand_value":
            slot["range"] = {"signed": signed, "bits": total, "align_bits": 0}
        slot["modifiers"] = []
        slot["placements"] = placements
        slots.append(slot)

    if set(owned) != variable_bits:
        raise SystemExit(
            "{0}: placements own {1}, match marks {2} variable".format(
                spec["form_id"], sorted(owned), sorted(variable_bits)
            )
        )
    if fixed_bits & variable_bits:
        raise SystemExit("{0}: a bit is both fixed and variable".format(spec["form_id"]))
    if fixed_bits | variable_bits != set(range(width)):
        raise SystemExit(
            "{0}: match leaves bits undecided".format(spec["form_id"])
        )

    template = word.to_bytes(width // 8, "little").hex()
    return {
        "form_id": spec["form_id"],
        "template": template,
        "slots": slots,
        "width": width,
        "udb_node": spec["node"],
        "variables": node["variables"],
    }


def encode(form, values):
    """Encode from the built table alone: template plus placements."""
    word = int.from_bytes(bytes.fromhex(form["template"]), "little")
    for slot in form["slots"]:
        value = values[slot["role"]]
        total = sum(p["width"] for p in slot["placements"])
        masked = value & ((1 << total) - 1)
        remaining = total
        for placement in slot["placements"]:
            remaining -= placement["width"]
            chunk = (masked >> remaining) & ((1 << placement["width"]) - 1)
            for offset in range(placement["width"]):
                if chunk & (1 << offset):
                    word |= 1 << (placement["bit_offset"] + offset)
    return word.to_bytes(form["width"] // 8, "little").hex(" ")


def render(document, forms):
    lines = ["{"]
    lines.append('  "definition_format": "{0}",'.format(document["definition_format"]))
    lines.append('  "namespace": "{0}",'.format(document["namespace"]))
    lines.append('  "version": "{0}",'.format(document["version"]))
    lines.append('  "target_identity": {')
    target = document["target_identity"]
    keys = ["isa_family", "isa_variant", "execution_mode", "enabled_extensions",
            "byte_order", "address_width"]
    for index, key in enumerate(keys):
        value = target[key]
        if isinstance(value, list):
            rendered = "[{0}]".format(
                ", ".join('"{0}"'.format(item) for item in value)
            )
        elif isinstance(value, int):
            rendered = str(value)
        else:
            rendered = '"{0}"'.format(value)
        comma = "," if index + 1 < len(keys) else ""
        lines.append('    "{0}": {1}{2}'.format(key, rendered, comma))
    lines.append("  },")
    lines.append('  "forms": [')
    for form_index, form in enumerate(forms):
        lines.append("    {")
        lines.append('      "form_id": "{0}",'.format(form["form_id"]))
        lines.append('      "template": "{0}",'.format(form["template"]))
        lines.append('      "slots": [')
        for slot_index, slot in enumerate(form["slots"]):
            lines.append("        {")
            lines.append('          "role": "{0}",'.format(slot["role"]))
            lines.append('          "kind": "{0}",'.format(slot["kind"]))
            lines.append('          "target_type": "{0}",'.format(slot["target_type"]))
            lines.append('          "from": "{0}",'.format(slot["from"]))
            if "range" in slot:
                span = slot["range"]
                lines.append(
                    '          "range": {{ "signed": {0}, "bits": {1}, '
                    '"align_bits": {2} }},'.format(
                        "true" if span["signed"] else "false",
                        span["bits"],
                        span["align_bits"],
                    )
                )
            lines.append('          "modifiers": [],')
            placements = ", ".join(
                '{{ "bit_offset": {0}, "width": {1} }}'.format(
                    p["bit_offset"], p["width"]
                )
                for p in slot["placements"]
            )
            lines.append('          "placements": [{0}]'.format(placements))
            lines.append(
                "        }," if slot_index + 1 < len(form["slots"]) else "        }"
            )
        lines.append("      ]")
        lines.append("    }," if form_index + 1 < len(forms) else "    }")
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def canonical_digest(document):
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def doc_rows(forms):
    for form in forms:
        cells = []
        for slot in form["slots"]:
            placements = ", ".join(
                "`[{0},{1}]`".format(p["bit_offset"], p["width"])
                for p in slot["placements"]
            )
            cells.append(
                "{0}: `{1}`/`{2}` \u2192 {3}".format(
                    slot["role"], slot["kind"], slot["target_type"], placements
                )
            )
        print(
            "| `{0}` | `{1}` | {2} | {3} | {4} |".format(
                form["form_id"],
                form["template"],
                "; ".join(cells),
                form["width"] // 8,
                form["covers"],
            )
        )


def main():
    nodes = {}
    forms = []
    for spec in FORMS:
        path = os.path.join(SPEC_ROOT, spec["node"])
        if not os.path.isfile(path):
            raise SystemExit(
                "missing pinned node {0}; restore the ADR-0007 drop".format(path)
            )
        node = nodes.get(spec["node"])
        if node is None:
            node = parse_node(path, None)
            nodes[spec["node"]] = node
        built = build(spec, node)
        built["covers"] = spec["covers"]
        forms.append(built)

        print("{0}".format(built["form_id"]))
        print("  node {0} ({1}-bit), template {2}".format(
            spec["node"], built["width"], built["template"]))
        for slot in built["slots"]:
            placements = ", ".join(
                "[{0},{1}]".format(p["bit_offset"], p["width"])
                for p in slot["placements"]
            )
            print("    {0:<6} {1:<11} {2:<12} {3}".format(
                slot["role"], slot["kind"], slot["target_type"], placements))

    document = dict(DOCUMENT)
    document["forms"] = [
        {"form_id": f["form_id"], "template": f["template"], "slots": f["slots"]}
        for f in forms
    ]

    text = render(DOCUMENT, forms)
    parsed = json.loads(text)
    if parsed != document:
        raise SystemExit("renderer and builder disagree; refusing to write")
    if canonical_digest(parsed) != canonical_digest(document):
        raise SystemExit("digest mismatch after rendering")

    print("== probe vectors, encoded from the table above")
    failures = 0
    by_id = {form["form_id"]: form for form in forms}
    for form_id, values, expected, asm in VECTORS:
        if form_id not in by_id:
            continue
        actual = encode(by_id[form_id], values)
        status = "ok  " if actual == expected else "FAIL"
        if actual != expected:
            failures += 1
        print("  {0} {1:<28} {2:<22} expected {3}  got {4}".format(
            status, form_id, asm, expected, actual))
    if failures:
        raise SystemExit("FAIL: probe vectors disagree with llvm-mc")

    directory = os.path.dirname(OUT)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    print("")
    print("wrote {0}".format(os.path.relpath(OUT, ROOT).replace("\\", "/")))
    print("definition digest {0}".format(canonical_digest(document)))
    print("")
    print("07_definition_format.md §8.4 rows:")
    doc_rows(forms)
    return 0


if __name__ == "__main__":
    sys.exit(main())
