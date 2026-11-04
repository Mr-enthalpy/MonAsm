#!/usr/bin/env python3
"""Generate `definitions/aarch64/**` from the pinned Arm MRS drop.

This is disposable research tooling (ADR-0005 §4). The shipped artifacts are
the JSON documents plus their digests; this script is how those documents were
derived and how they stay traceable to the MRS nodes they read.

What it does, per form:

1. Reads the MRS node named in the spec from `Instructions.json`.
2. Splits the node's encode fields into *fixed* (no `x` in the value string) and
   *variable*. A variable field is either mapped to a slot, or named in
   `pinned` — a value our form fixes although the MRS leaves it open. The
   pinned list is the byte-affecting decision the `form_id` carries (AArch64
   `shift`/`imm6`/`sh`), so it is stated here, not inferred.
3. Builds the template from the fixed bits plus the pinned values.
4. Derives each slot's placements from the MRS field ranges, so a wrong bit
   position is a mismatch, never a typo that silently emits bytes.
5. Refuses to emit unless every one of the 32 bits is covered exactly once by
   either a fixed bit or a slot placement.

Documents are emitted per version. A form appears in a document when the
document's version is at or after the form's `since` (absent `since` means every
version), so a later document cannot silently lose an earlier form. `0.1.0` and
`0.2.0` stay frozen: their digests are asserted below, so a later edit that
perturbs either one fails loudly instead of shipping.

Reads:  research/external/arm-mrs/Instructions.json (pinned by check_mrs.py)
Writes: definitions/aarch64/0.1.0.json
        definitions/aarch64/0.2.0.json
        definitions/aarch64/0.3.0.json

Usage:
    python research/evidence/experiments/EXP-0008/generate_aarch64.py
"""

import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

MRS = os.path.join(ROOT, "research", "external", "arm-mrs", "Instructions.json")
OUT_DIR = os.path.join(ROOT, "definitions", "aarch64")

VERSIONS = ["0.1.0", "0.2.0", "0.3.0"]

# Frozen digests. Fixtures name them, so they may not move.
FROZEN_DIGESTS = {
    "0.1.0": "sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e",
    "0.2.0": "sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed",
}

WIDTH = 32

TARGET_IDENTITY = {
    "isa_family": "aarch64",
    "isa_variant": "aarch64",
    "execution_mode": "n/a",
    "enabled_extensions": [],
    "byte_order": "little",
    "address_width": 64,
}

# One entry per row of 07_definition_format.md §8.
#
# `mrs` is the exact node name in Instructions.json. `slots` is in plan operand
# order; each entry names the MRS field(s) that carry it (an ADRP immediate is
# one value split over `immhi` and `immlo`, most significant part first).
# `pinned` maps an MRS field name to the integer value our form fixes it to.
# `since` is the first document version that contains the form; omit it for all
# of them.
FORMS = [
    {
        "form_id": "aarch64:add/x64-x64-x64-lsl0",
        "mrs": "ADD_64_addsub_shift",
        "decision": "shift = LSL (00) and imm6 = 000000",
        "pinned": {"shift": 0, "imm6": 0},
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:add/x64-imm12-lsl0",
        "mrs": "ADD_64_addsub_imm",
        "decision": "sh = 0 (no LSL #12)",
        "pinned": {"sh": 0},
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm12"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm12",
             "range": {"signed": False, "bits": 12, "align_bits": 0}},
        ],
    },
    {
        # A64-P2's `-lsl12` half (ADR-0011). The `imm12` slot still holds field
        # content in [0, 4095]; the `sh = 1` the form fixes makes the instruction
        # shift it. No slot-level scale is involved (07_definition_format.md
        # §8.3: the slot is the field).
        "form_id": "aarch64:add/x64-imm12-lsl12",
        "mrs": "ADD_64_addsub_imm",
        "decision": "sh = 1 (LSL #12), imm12 still field content",
        "pinned": {"sh": 1},
        "since": "0.2.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm12"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm12",
             "range": {"signed": False, "bits": 12, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:bl/imm26",
        "mrs": "BL_only_branch_imm",
        "decision": "nothing is left open by the MRS",
        "pinned": {},
        "slots": [
            # The slot is the field, so a plain operand value is the imm26
            # content. A byte displacement is the fixup path (`scale`, shift 2);
            # see 07_definition_format.md §8.3.
            {"mrs": ["imm26"], "role": "target", "kind": "aarch64.rel",
             "from": "operand_value", "target_type": "imm26",
             "range": {"signed": True, "bits": 26, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:adrp/x64-imm21",
        "mrs": "ADRP_only_pcreladdr",
        "decision": "nothing is left open by the MRS",
        "pinned": {},
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["immhi", "immlo"], "role": "target", "kind": "aarch64.rel",
             "from": "operand_value", "target_type": "imm21",
             "range": {"signed": True, "bits": 21, "align_bits": 0}},
        ],
    },
    {
        # `A64-P4` (ADR-0012). The MRS leaves `cond` (4 bits) and `imm19` open;
        # the condition is an operand, not a second form, and the displacement is
        # field content like `bl`'s `imm26` (07_definition_format.md §8.3).
        # All sixteen conditions are encodable, `al`/`nv` included, so there is
        # no `excluded` list: the ISA defines every value.
        "form_id": "aarch64:b.cond/imm19",
        "mrs": "B_only_condbranch",
        "decision": "nothing is left open by the MRS",
        "pinned": {},
        "since": "0.3.0",
        "slots": [
            {"mrs": ["cond"], "role": "imm", "kind": "aarch64.cond",
             "from": "operand_value", "target_type": "cond4",
             "range": {"signed": False, "bits": 4, "align_bits": 0}},
            {"mrs": ["imm19"], "role": "target", "kind": "aarch64.rel",
             "from": "operand_value", "target_type": "imm19",
             "range": {"signed": True, "bits": 19, "align_bits": 0}},
        ],
    },
]


def document_for(version):
    return {
        "definition_format": "fmp-def/0.1",
        "namespace": "monasm.isa.aarch64",
        "version": version,
        "target_identity": dict(TARGET_IDENTITY),
    }


def version_key(version):
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise SystemExit("version {0!r} is not <major>.<minor>.<patch>".format(version))
    return tuple(int(part) for part in parts)


def forms_for(version):
    current = version_key(version)
    selected = []
    for spec in FORMS:
        since = spec.get("since")
        if since is not None and since not in VERSIONS:
            raise SystemExit(
                "{0}: since {1!r} is not a document version".format(
                    spec["form_id"], since
                )
            )
        if since is None or version_key(since) <= current:
            selected.append(spec)
    return selected


def quote_value(field):
    raw = (field.get("value") or {}).get("value")
    if not isinstance(raw, str):
        raise SystemExit(
            "field {0!r} has no value string; this generator does not model "
            "value sets".format(field.get("name"))
        )
    return raw.strip("'")


def walk(node):
    if isinstance(node, list):
        for item in node:
            for found in walk(item):
                yield found
        return
    if not isinstance(node, dict):
        return
    yield node
    for child in node.get("children") or []:
        for item in walk(child):
            yield item


def load_nodes():
    with io.open(MRS, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    wanted = {spec["mrs"] for spec in FORMS}
    nodes = {}
    for node in walk(document["instructions"]):
        if node.get("name") in wanted and str(node.get("_type", "")).endswith(
            "Instruction.Instruction"
        ):
            if node["name"] in nodes:
                raise SystemExit("duplicate MRS node {0}".format(node["name"]))
            nodes[node["name"]] = node
    missing = wanted - set(nodes)
    if missing:
        raise SystemExit("MRS nodes missing: {0}".format(sorted(missing)))
    return nodes


def encode_fields(node):
    encoding = node.get("encoding") or {}
    if encoding.get("width") != WIDTH:
        raise SystemExit(
            "{0}: encoding width {1}, expected {2}".format(
                node["name"], encoding.get("width"), WIDTH
            )
        )
    out = []
    for field in encoding.get("values") or []:
        span = field.get("range") or {}
        start = span.get("start")
        width = span.get("width")
        if not isinstance(start, int) or not isinstance(width, int):
            raise SystemExit("{0}: field without a bit range".format(node["name"]))
        if start < 0 or start + width > WIDTH:
            raise SystemExit(
                "{0}: field [{1},{2}] leaves the {3}-bit word".format(
                    node["name"], start, width, WIDTH
                )
            )
        out.append(
            {
                "name": field.get("name"),
                "start": start,
                "width": width,
                "value": quote_value(field),
            }
        )
    return out


def build(spec, node):
    fields = encode_fields(node)
    by_name = {}
    for field in fields:
        if field["name"] is not None:
            if field["name"] in by_name:
                raise SystemExit(
                    "{0}: duplicate field name {1}".format(node["name"], field["name"])
                )
            by_name[field["name"]] = field

    word = 0
    fixed = []
    variable = []
    for field in fields:
        if set(field["value"]) <= {"0", "1"}:
            if len(field["value"]) != field["width"]:
                raise SystemExit(
                    "{0}: fixed field {1!r} value {2!r} is not {3} bits".format(
                        node["name"], field["name"], field["value"], field["width"]
                    )
                )
            word |= int(field["value"], 2) << field["start"]
            fixed.append(field)
        else:
            if set(field["value"]) != {"x"}:
                raise SystemExit(
                    "{0}: field {1!r} mixes fixed and variable bits ({2!r})".format(
                        node["name"], field["name"], field["value"]
                    )
                )
            variable.append(field)

    pinned = []
    for name, value in spec["pinned"].items():
        field = by_name.get(name)
        if field is None:
            raise SystemExit(
                "{0}: pinned field {1!r} is not in the node".format(spec["mrs"], name)
            )
        if field not in variable:
            raise SystemExit(
                "{0}: pinned field {1!r} is already fixed by the MRS; pinning it "
                "again would hide that".format(spec["mrs"], name)
            )
        if not isinstance(value, int) or not 0 <= value < (1 << field["width"]):
            raise SystemExit(
                "{0}: pinned value {1!r} does not fit field {2!r} ({3} bits)".format(
                    spec["mrs"], value, name, field["width"]
                )
            )
        word |= value << field["start"]
        pinned.append((field, value))

    slots = []
    covered = []
    for slot_spec in spec["slots"]:
        placements = []
        total = 0
        for name in slot_spec["mrs"]:
            field = by_name.get(name)
            if field is None:
                raise SystemExit(
                    "{0}: slot field {1!r} is not in the node".format(spec["mrs"], name)
                )
            if field not in variable:
                raise SystemExit(
                    "{0}: slot field {1!r} is fixed by the MRS to {2!r}, so it is "
                    "not an operand".format(spec["mrs"], name, field["value"])
                )
            placements.append({"bit_offset": field["start"], "width": field["width"]})
            total += field["width"]
            covered.append((field["start"], field["width"], slot_spec["role"]))
        expected = (slot_spec.get("range") or {}).get("bits", total)
        if expected != total:
            raise SystemExit(
                "{0}/{1}: placements hold {2} bits, range.bits is {3}".format(
                    spec["form_id"], slot_spec["role"], total, expected
                )
            )
        slot = {
            "role": slot_spec["role"],
            "kind": slot_spec["kind"],
            "target_type": slot_spec["target_type"],
            "from": slot_spec["from"],
        }
        if "range" in slot_spec:
            slot["range"] = slot_spec["range"]
        slot["modifiers"] = []
        slot["placements"] = placements
        slots.append(slot)

    # Every bit exactly once: fixed, pinned, or one slot placement.
    owner = {}
    for field in fixed:
        for bit in range(field["start"], field["start"] + field["width"]):
            owner[bit] = "fixed"
    for field, _ in pinned:
        for bit in range(field["start"], field["start"] + field["width"]):
            owner[bit] = "pinned"
    for start, width, role in covered:
        for bit in range(start, start + width):
            if bit in owner:
                raise SystemExit(
                    "{0}: bit {1} is claimed by {2} and by {3}".format(
                        spec["form_id"], bit, owner[bit], role
                    )
                )
            owner[bit] = role
    missing = sorted(set(range(WIDTH)) - set(owner))
    if missing:
        raise SystemExit(
            "{0}: bits {1} are neither fixed nor operand-owned".format(
                spec["form_id"], missing
            )
        )

    template = "".join(
        "{:02x}".format((word >> (8 * index)) & 0xFF) for index in range(WIDTH // 8)
    )
    return {
        "form_id": spec["form_id"],
        "template": template,
        "slots": slots,
        "fixed": ["{0}@{1}+{2}".format(f["name"] or "<bits>", f["start"], f["width"])
                  for f in fixed],
        "pinned": ["{0}@{1}+{2}={3}".format(f["name"], f["start"], f["width"], v)
                   for f, v in pinned],
    }


def render(document, forms):
    lines = ["{", '  "definition_format": "{0}",'.format(document["definition_format"]),
             '  "namespace": "{0}",'.format(document["namespace"]),
             '  "version": "{0}",'.format(document["version"]),
             '  "target_identity": {']
    target = document["target_identity"]
    keys = ["isa_family", "isa_variant", "execution_mode", "enabled_extensions",
            "byte_order", "address_width"]
    for index, key in enumerate(keys):
        value = target[key]
        if isinstance(value, list):
            rendered = "[]"
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
                "{{ \"bit_offset\": {0}, \"width\": {1} }}".format(
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


def emit(version, nodes):
    specs = forms_for(version)
    if not specs:
        raise SystemExit("{0}: no forms".format(version))
    forms = []
    for spec in specs:
        built = build(spec, nodes[spec["mrs"]])
        forms.append(built)
        print("{0}".format(built["form_id"]))
        print("  MRS node {0}; {1}".format(spec["mrs"], spec["decision"]))
        print("  template {0}  ({1} bits fixed, {2} pinned)"
              .format(built["template"], len(built["fixed"]), len(built["pinned"])))
        for name in built["pinned"]:
            print("    pinned {0}".format(name))

    document = document_for(version)
    document["forms"] = [
        {"form_id": f["form_id"], "template": f["template"], "slots": f["slots"]}
        for f in forms
    ]

    text = render(document_for(version), forms)
    parsed = json.loads(text)
    if parsed != document:
        raise SystemExit("renderer and builder disagree; refusing to write")
    if canonical_digest(parsed) != canonical_digest(document):
        raise SystemExit("digest mismatch after rendering")

    out = os.path.join(OUT_DIR, version + ".json")
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    with io.open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    digest = canonical_digest(document)
    frozen = FROZEN_DIGESTS.get(version)
    if frozen is not None and digest != frozen:
        raise SystemExit(
            "{0} moved: {1} != frozen {2}".format(version, digest, frozen)
        )

    print("")
    print("wrote {0} ({1} forms)".format(
        os.path.relpath(out, ROOT).replace("\\", "/"), len(forms)))
    print("definition digest {0}{1}".format(
        digest, "" if frozen is None else "  (frozen)"))
    print("")
    return digest


def main():
    nodes = load_nodes()
    for version in VERSIONS:
        emit(version, nodes)

    with io.open(MRS, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    print("source Instructions.json sha256:{0}".format(digest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
