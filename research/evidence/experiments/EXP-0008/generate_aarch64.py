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
version), so a later document cannot silently lose an earlier form. `0.1.0` …
`0.15.0` stay frozen: their digests are asserted below, so a later edit that
perturbs any of them fails loudly instead of shipping.

Reads:  research/external/arm-mrs/Instructions.json (pinned by check_mrs.py)
Writes: definitions/aarch64/0.1.0.json
        definitions/aarch64/0.2.0.json
        definitions/aarch64/0.3.0.json
        definitions/aarch64/0.4.0.json
        definitions/aarch64/0.5.0.json
        definitions/aarch64/0.6.0.json
        definitions/aarch64/0.7.0.json
        definitions/aarch64/0.8.0.json
        definitions/aarch64/0.9.0.json
        definitions/aarch64/0.10.0.json
        definitions/aarch64/0.11.0.json
        definitions/aarch64/0.12.0.json
        definitions/aarch64/0.13.0.json
        definitions/aarch64/0.14.0.json
        definitions/aarch64/0.15.0.json
        definitions/aarch64/0.16.0.json

Usage:
    python research/evidence/experiments/EXP-0008/generate_aarch64.py
"""

import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

MRS = os.path.join(ROOT, "research", "external", "arm-mrs", "Instructions.json")
OUT_DIR = os.path.join(ROOT, "definitions", "aarch64")

VERSIONS = ["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0",
            "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0",
            "0.14.0", "0.15.0", "0.16.0"]

# Frozen digests. Fixtures name them, so they may not move.
FROZEN_DIGESTS = {
    "0.1.0": "sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e",
    "0.2.0": "sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed",
    "0.3.0": "sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb",
    "0.4.0": "sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78",
    "0.5.0": "sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e",
    "0.6.0": "sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964",
    "0.7.0": "sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053",
    "0.8.0": "sha256:9f82b566af004aaa9f0471151497d65acb45c3a7b46e4240345d21f4e330bc35",
    "0.9.0": "sha256:99728cd9bd85b8b0768e700e15dd6263171d6261c385ac15ceeb5df6d2cafcff",
    "0.10.0": "sha256:e958d69b4ba93222e7621a1f5c3ebd056ce929e2974a961a03abb7b66f0b247b",
    "0.11.0": "sha256:c5a9aec943f9b195c400380b8416bf63cba944da3fdf0203f90de5baff295002",
    "0.12.0": "sha256:8a428926568b99f0674785cc674bc066adc452216131706d458b9e3390da03b6",
    "0.13.0": "sha256:d3876dd37a8441057b586312b3bee410e39594c64806b2c5c59960c06f9c7a5f",
    "0.14.0": "sha256:a90ceac19824fbb00731e040346daa191973652e58522fab72336e24f769a5ba",
    "0.15.0": "sha256:422ebb83b897b18e010da37539796b0b97cfc9018a47209fc4a6ddc5b14af5d3",
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
    # `A64-P3` (ADR-0013). The four immediate addressing kinds are four MRS
    # nodes, so the kind is a `form_id`, not an operand value. `disp` is field
    # content: `imm12` counts 8-byte units for these `size = 11` rows and is
    # unsigned; `imm9` counts signed bytes. No slot-level scale exists
    # (07_definition_format.md §5), and `align_bits` checks the field value, not
    # the byte offset (§4).
    {
        "form_id": "aarch64:ldr/x64-base-imm12",
        "mrs": "LDR_64_ldst_pos",
        "decision": "bit 24 = 1 (unsigned offset); imm12 is field content in 8-byte units",
        "pinned": {},
        "since": "0.4.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm12"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm12",
             "range": {"signed": False, "bits": 12, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-imm9-pre",
        "mrs": "LDR_64_ldst_immpre",
        "decision": "bits 11-10 = 11 (pre-index); imm9 is signed field content in bytes",
        "pinned": {},
        "since": "0.4.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm9"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm9",
             "range": {"signed": True, "bits": 9, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-imm9-post",
        "mrs": "LDR_64_ldst_immpost",
        "decision": "bits 11-10 = 01 (post-index); imm9 is signed field content in bytes",
        "pinned": {},
        "since": "0.4.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm9"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm9",
             "range": {"signed": True, "bits": 9, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:ldur/x64-base-imm9",
        "mrs": "LDUR_64_ldst_unscaled",
        "decision": "bits 11-10 = 00 (unscaled); imm9 is signed field content in bytes",
        "pinned": {},
        "since": "0.4.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm9"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm9",
             "range": {"signed": True, "bits": 9, "align_bits": 0}},
        ],
    },
    {
        # Same layout as the `ldr` unsigned-offset row with `opc = 00`; the
        # stored register is `Rt`. This row is what proves `opc` comes from the
        # form and not from the mnemonic (ADR-0013 decision 5).
        "form_id": "aarch64:str/x64-base-imm12",
        "mrs": "STR_64_ldst_pos",
        "decision": "bit 24 = 1 (unsigned offset); opc = 00 (store); imm12 is field content in 8-byte units",
        "pinned": {},
        "since": "0.4.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm12"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm12",
             "range": {"signed": False, "bits": 12, "align_bits": 0}},
        ],
    },
    # `A64-P15` (ADR-0022). The store half of the same four addressing kinds:
    # the three nodes are `STR_64_ldst_immpre`/`immpost` and
    # `STUR_64_ldst_unscaled`, which are the load rows' shapes with `opc = 00`
    # and `Rt` as the stored register, so the kind stays a `form_id` and the
    # `imm9` slot keeps its signed-byte range.
    {
        "form_id": "aarch64:str/x64-base-imm9-pre",
        "mrs": "STR_64_ldst_immpre",
        "decision": "bits 11-10 = 11 (pre-index); opc = 00 (store); imm9 is signed field content in bytes",
        "pinned": {},
        "since": "0.13.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm9"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm9",
             "range": {"signed": True, "bits": 9, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-imm9-post",
        "mrs": "STR_64_ldst_immpost",
        "decision": "bits 11-10 = 01 (post-index); opc = 00 (store); imm9 is signed field content in bytes",
        "pinned": {},
        "since": "0.13.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm9"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm9",
             "range": {"signed": True, "bits": 9, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:stur/x64-base-imm9",
        "mrs": "STUR_64_ldst_unscaled",
        "decision": "bits 11-10 = 00 (unscaled); opc = 00 (store); imm9 is signed field content in bytes",
        "pinned": {},
        "since": "0.13.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm9"], "role": "disp", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm9",
             "range": {"signed": True, "bits": 9, "align_bits": 0}},
        ],
    },
    # `A64-P16` (ADR-0023). The literal load is the one load with no `Rn`: the
    # node fixes `opc = 01`, bit 24 = 0 and the kind bits that the other rows
    # vary, and leaves only `Rt` and `imm19`. `imm19` is field content in
    # 4-byte units, so a byte displacement is the fixup's `scale` with shift 2
    # (07_definition_format.md §8.3) and the slot's `align_bits` stays 0. The
    # other `opc` values (00 `LDR Wt`, 10 `LDRSW`, 11 `PRFM`) and the `VR = 1`
    # SIMD/FP loads are different rows; no store literal node exists.
    {
        "form_id": "aarch64:ldr/x64-imm19",
        "mrs": "LDR_64_loadlit",
        "decision": "opc = 01 (LDR Xt); imm19 is field content in 4-byte units",
        "pinned": {},
        "since": "0.14.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm19"], "role": "target", "kind": "aarch64.rel",
             "from": "operand_value", "target_type": "imm19",
             "range": {"signed": True, "bits": 19, "align_bits": 0}},
        ],
    },
    # `A64-P17` (ADR-0024). The register-offset kind: `Rm`, `option` and `S` are
    # the three fields the immediate kinds do not have. `option` picks the index
    # register's width and extension (`011` LSL takes an `x`, `010` UXTW and
    # `110` SXTW take a `w`, `111` SXTX takes an `x`) and `S` selects whether the
    # index is scaled by the access size (8 bytes here). Both are byte-affecting
    # decisions the assembler spells as the keyword plus `#0`/`#3`, so each
    # combination is its own row (`INV-02`, ADR-0004). `Rm` is the `index`
    # slot; `Rn` stays `base` and `Rt` is `dest`/`src`.
    {
        "form_id": "aarch64:ldr/x64-base-regoff-lsl0",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 0 (no scale)",
        "pinned": {"option": 3, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-regoff-lsl3",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 1 (index scaled by 8)",
        "pinned": {"option": 3, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-regoff-uxtw0",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 2, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-regoff-uxtw3",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 1 (index scaled by 8)",
        "pinned": {"option": 2, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-regoff-sxtw0",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 6, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-regoff-sxtw3",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 1 (index scaled by 8)",
        "pinned": {"option": 6, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-regoff-sxtx0",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 0 (no scale)",
        "pinned": {"option": 7, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:ldr/x64-base-regoff-sxtx3",
        "mrs": "LDR_64_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 1 (index scaled by 8)",
        "pinned": {"option": 7, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-lsl0",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 0 (no scale)",
        "pinned": {"option": 3, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-lsl3",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 1 (index scaled by 8)",
        "pinned": {"option": 3, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-uxtw0",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 2, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-uxtw3",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 1 (index scaled by 8)",
        "pinned": {"option": 2, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-sxtw0",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 6, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-sxtw3",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 1 (index scaled by 8)",
        "pinned": {"option": 6, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-sxtx0",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 0 (no scale)",
        "pinned": {"option": 7, "S": 0},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/x64-base-regoff-sxtx3",
        "mrs": "STR_64_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 1 (index scaled by 8)",
        "pinned": {"option": 7, "S": 1},
        "since": "0.15.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    # `A64-P18` (ADR-0025). The 32-bit register-offset pair: the same nodes, the
    # same `option` mapping and the same width pairing as `A64-P17`, but
    # `size = 10`, so `S = 1` scales the index by the 4-byte access size (`#2`).
    # `Rt` is a `w` register on both mnemonics; `Rn` and `Rm` stay `x`, so only
    # the destination/source slot changes width.
    {
        "form_id": "aarch64:ldr/w32-base-regoff-lsl0",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 0 (no scale)",
        "pinned": {"option": 3, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:ldr/w32-base-regoff-lsl2",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 1 (index scaled by 4)",
        "pinned": {"option": 3, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:ldr/w32-base-regoff-uxtw0",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 2, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/w32-base-regoff-uxtw2",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 1 (index scaled by 4)",
        "pinned": {"option": 2, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/w32-base-regoff-sxtw0",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 6, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/w32-base-regoff-sxtw2",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 1 (index scaled by 4)",
        "pinned": {"option": 6, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:ldr/w32-base-regoff-sxtx0",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 0 (no scale)",
        "pinned": {"option": 7, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:ldr/w32-base-regoff-sxtx2",
        "mrs": "LDR_32_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 1 (index scaled by 4)",
        "pinned": {"option": 7, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "dest", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-lsl0",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 0 (no scale)",
        "pinned": {"option": 3, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-lsl2",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 011 (LSL, x index), S = 1 (index scaled by 4)",
        "pinned": {"option": 3, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-uxtw0",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 2, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-uxtw2",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 010 (UXTW, w index), S = 1 (index scaled by 4)",
        "pinned": {"option": 2, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-sxtw0",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 0 (no scale)",
        "pinned": {"option": 6, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-sxtw2",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 110 (SXTW, w index), S = 1 (index scaled by 4)",
        "pinned": {"option": 6, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-sxtx0",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 0 (no scale)",
        "pinned": {"option": 7, "S": 0},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    {
        "form_id": "aarch64:str/w32-base-regoff-sxtx2",
        "mrs": "STR_32_ldst_regoff",
        "decision": "option = 111 (SXTX, x index), S = 1 (index scaled by 4)",
        "pinned": {"option": 7, "S": 1},
        "since": "0.16.0",
        "slots": [
            {"mrs": ["Rt"], "role": "src", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["Rn"], "role": "base", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "index", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
        ],
    },
    # `A64-P7` (ADR-0014). `MOVZ`'s 2-bit `hw` field selects which 16-bit lane
    # the `imm16` content lands in, so the same field value means four different
    # 64-bit results. The assembly language spells the lane as `lsl #0/#16/#32/
    # #48` and fixes `imm16` at the field content in [0, 65535], so the lane is a
    # form-level decision like `add`'s `sh` (ADR-0011) and not a slot transform:
    # `imm16 << 16*hw` is a property of the row, and `0.5.0` holds all four lanes.
    {
        "form_id": "aarch64:movz/x64-imm16-lsl0",
        "mrs": "MOVZ_64_movewide",
        "decision": "hw = 0 (LSL #0); imm16 is field content in the low lane",
        "pinned": {"hw": 0},
        "since": "0.5.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm16"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm16",
             "range": {"signed": False, "bits": 16, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:movz/x64-imm16-lsl16",
        "mrs": "MOVZ_64_movewide",
        "decision": "hw = 1 (LSL #16); imm16 is field content in bits 31:16",
        "pinned": {"hw": 1},
        "since": "0.5.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm16"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm16",
             "range": {"signed": False, "bits": 16, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:movz/x64-imm16-lsl32",
        "mrs": "MOVZ_64_movewide",
        "decision": "hw = 2 (LSL #32); imm16 is field content in bits 47:32",
        "pinned": {"hw": 2},
        "since": "0.5.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm16"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm16",
             "range": {"signed": False, "bits": 16, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:movz/x64-imm16-lsl48",
        "mrs": "MOVZ_64_movewide",
        "decision": "hw = 3 (LSL #48); imm16 is field content in bits 63:48",
        "pinned": {"hw": 3},
        "since": "0.5.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm16"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm16",
             "range": {"signed": False, "bits": 16, "align_bits": 0}},
        ],
    },
    # `A64-P8` (ADR-0015). The shift on a register operand is one keyword plus
    # one number: `add x0, x1, x2, lsl #3`. The keyword is the 2-bit `shift`
    # field, the number is the 6-bit `imm6` field. The keyword is a form (three
    # spellings exist and none of them is numeric), the number is field content
    # (`0…63`), for the same reason `movz`'s lane is a form and `imm16` is not
    # (ADR-0014). `shift = 11` is unallocated for add/sub, so `-ror` is not a row.
    {
        "form_id": "aarch64:add/x64-x64-x64-imm6-lsl",
        "mrs": "ADD_64_addsub_shift",
        "decision": "shift = LSL (00); imm6 is field content (the shift amount)",
        "pinned": {"shift": 0},
        "since": "0.6.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-x64-imm6-lsr",
        "mrs": "ADD_64_addsub_shift",
        "decision": "shift = LSR (01); imm6 is field content (the shift amount)",
        "pinned": {"shift": 1},
        "since": "0.6.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-x64-imm6-asr",
        "mrs": "ADD_64_addsub_shift",
        "decision": "shift = ASR (10); imm6 is field content (the shift amount)",
        "pinned": {"shift": 2},
        "since": "0.6.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    # `A64-P9` (ADR-0016). The extended-register node is one bit apart from the
    # shifted one: bit 21 = 1 and `opt` = 00 instead of a variable `shift`. Its
    # three variable fields are `option` (13+3), `imm3` (10+3) and the registers.
    # The keyword is the form because it also fixes the width of the register it
    # consumes: the six `[su]xt[bhw]` keywords take a `w` source, `uxtx`/`sxtx`
    # take an `x` source, and the assembler rejects the other pairing. The amount
    # is field content, but the field is 3 bits and only `0…4` are allocated, so
    # the slot carries `excluded: [5, 6, 7]` (ADR-0009) and `8` is outside the
    # field. `sub`, `adds`/`subs` and the `sf = 0` node are other nodes.
    {
        "form_id": "aarch64:add/x64-x64-w32-imm3-uxtb",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = UXTB (000); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 0},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-w32-imm3-uxth",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = UXTH (001); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 1},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-w32-imm3-uxtw",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = UXTW (010); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 2},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-x64-imm3-uxtx",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = UXTX (011); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 3},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-w32-imm3-sxtb",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = SXTB (100); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 4},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-w32-imm3-sxth",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = SXTH (101); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 5},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-w32-imm3-sxtw",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = SXTW (110); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 6},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr32",
             "from": "reg_number", "target_type": "w32"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    {
        "form_id": "aarch64:add/x64-x64-x64-imm3-sxtx",
        "mrs": "ADD_64_addsub_ext",
        "decision": "option = SXTX (111); imm3 is field content in 0..4, 5..7 excluded",
        "pinned": {"option": 7},
        "since": "0.7.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm3",
             "range": {"signed": False, "bits": 3, "align_bits": 0},
             "excluded": [5, 6, 7]},
        ],
    },
    # `A64-P10` (ADR-0017). `SUB_64_addsub_imm` and `SUB_64_addsub_shift` are the
    # `ADD_64` nodes with `op = 1` (bit 30); everything else, including the
    # `sh`/`shift`/`imm6`/`imm12` fields, is identical. So the mnemonic is a form
    # family and each row repeats the `add` shape with the `op` bit pinned by the
    # node itself (nothing is `pinned` for `op`; the MRS already fixes it).
    # `S = 1` (`SUBS_64*`), the `sf = 0` nodes and `SUB_64_addsub_ext` stay out.
    {
        "form_id": "aarch64:sub/x64-x64-x64-lsl0",
        "mrs": "SUB_64_addsub_shift",
        "decision": "shift = LSL (00) and imm6 = 000000; the node fixes op = 1",
        "pinned": {"shift": 0, "imm6": 0},
        "since": "0.8.0",
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
        "form_id": "aarch64:sub/x64-imm12-lsl0",
        "mrs": "SUB_64_addsub_imm",
        "decision": "sh = 0 (no LSL #12); the node fixes op = 1",
        "pinned": {"sh": 0},
        "since": "0.8.0",
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
        "form_id": "aarch64:sub/x64-imm12-lsl12",
        "mrs": "SUB_64_addsub_imm",
        "decision": "sh = 1 (LSL #12), imm12 still field content; the node fixes op = 1",
        "pinned": {"sh": 1},
        "since": "0.8.0",
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
        "form_id": "aarch64:sub/x64-x64-x64-imm6-lsl",
        "mrs": "SUB_64_addsub_shift",
        "decision": "shift = LSL (00); imm6 is field content (the shift amount)",
        "pinned": {"shift": 0},
        "since": "0.8.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:sub/x64-x64-x64-imm6-lsr",
        "mrs": "SUB_64_addsub_shift",
        "decision": "shift = LSR (01); imm6 is field content (the shift amount)",
        "pinned": {"shift": 1},
        "since": "0.8.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:sub/x64-x64-x64-imm6-asr",
        "mrs": "SUB_64_addsub_shift",
        "decision": "shift = ASR (10); imm6 is field content (the shift amount)",
        "pinned": {"shift": 2},
        "since": "0.8.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    # `A64-P11` (ADR-0018). `ADDS_*`/`SUBS_*` are the four nodes above with
    # `S` at 29+1 fixed to `1` — one bit, and nothing else. The mnemonic is the
    # form family and the flag-setting bit is the node's, so each row repeats the
    # `add`/`sub` shape of the same name. `cmp`/`cmn` are aliases that fix `Rd`
    # to 31 and drop the destination, so they are their own family and stay out.
    {
        "form_id": "aarch64:adds/x64-x64-x64-lsl0",
        "mrs": "ADDS_64_addsub_shift",
        "decision": "shift = LSL (00) and imm6 = 000000; the node fixes S = 1",
        "pinned": {"shift": 0, "imm6": 0},
        "since": "0.9.0",
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
        "form_id": "aarch64:adds/x64-imm12-lsl0",
        "mrs": "ADDS_64S_addsub_imm",
        "decision": "sh = 0 (no LSL #12); the node fixes S = 1",
        "pinned": {"sh": 0},
        "since": "0.9.0",
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
        "form_id": "aarch64:adds/x64-imm12-lsl12",
        "mrs": "ADDS_64S_addsub_imm",
        "decision": "sh = 1 (LSL #12), imm12 still field content; the node fixes S = 1",
        "pinned": {"sh": 1},
        "since": "0.9.0",
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
        "form_id": "aarch64:adds/x64-x64-x64-imm6-lsl",
        "mrs": "ADDS_64_addsub_shift",
        "decision": "shift = LSL (00); imm6 is field content (the shift amount)",
        "pinned": {"shift": 0},
        "since": "0.9.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:adds/x64-x64-x64-imm6-lsr",
        "mrs": "ADDS_64_addsub_shift",
        "decision": "shift = LSR (01); imm6 is field content (the shift amount)",
        "pinned": {"shift": 1},
        "since": "0.9.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:adds/x64-x64-x64-imm6-asr",
        "mrs": "ADDS_64_addsub_shift",
        "decision": "shift = ASR (10); imm6 is field content (the shift amount)",
        "pinned": {"shift": 2},
        "since": "0.9.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:subs/x64-x64-x64-lsl0",
        "mrs": "SUBS_64_addsub_shift",
        "decision": "shift = LSL (00) and imm6 = 000000; the node fixes S = 1 and op = 1",
        "pinned": {"shift": 0, "imm6": 0},
        "since": "0.9.0",
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
        "form_id": "aarch64:subs/x64-imm12-lsl0",
        "mrs": "SUBS_64S_addsub_imm",
        "decision": "sh = 0 (no LSL #12); the node fixes S = 1 and op = 1",
        "pinned": {"sh": 0},
        "since": "0.9.0",
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
        "form_id": "aarch64:subs/x64-imm12-lsl12",
        "mrs": "SUBS_64S_addsub_imm",
        "decision": "sh = 1 (LSL #12), imm12 still field content; the node fixes S = 1 and op = 1",
        "pinned": {"sh": 1},
        "since": "0.9.0",
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
        "form_id": "aarch64:subs/x64-x64-x64-imm6-lsl",
        "mrs": "SUBS_64_addsub_shift",
        "decision": "shift = LSL (00); imm6 is field content (the shift amount)",
        "pinned": {"shift": 0},
        "since": "0.9.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:subs/x64-x64-x64-imm6-lsr",
        "mrs": "SUBS_64_addsub_shift",
        "decision": "shift = LSR (01); imm6 is field content (the shift amount)",
        "pinned": {"shift": 1},
        "since": "0.9.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
    {
        "form_id": "aarch64:subs/x64-x64-x64-imm6-asr",
        "mrs": "SUBS_64_addsub_shift",
        "decision": "shift = ASR (10); imm6 is field content (the shift amount)",
        "pinned": {"shift": 2},
        "since": "0.9.0",
        "slots": [
            {"mrs": ["Rd"], "role": "dest", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["Rm"], "role": "src2", "kind": "aarch64.gpr64",
             "from": "reg_number", "target_type": "x64"},
            {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
             "from": "operand_value", "target_type": "imm6",
             "range": {"signed": False, "bits": 6, "align_bits": 0}},
        ],
    },
]

# `A64-P12` (ADR-0019). The eight `*_32*` nodes are the `*_64*` nodes above with
# `sf` at 31+1 fixed to `0`; every other field, including `op` (30+1) and `S`
# (29+1), is in the same place. So each `w` row repeats the `x64` row of the same
# name with every register slot narrowed to `aarch64.gpr32`/`w32`, and the MRS
# node supplies `sf` — no plan field names the width and nothing is pinned by
# hand. The `imm6` field stays six bits wide, but the 32-bit form allocates only
# 0..31 (measured: `imm6 = 32` does not decode), so the slot carries the excluded
# tail 32..63 — the same shape as the `imm3` tail of ADR-0009/ADR-0016.
_W_FAMILIES = [
    ("add", "ADD_32_addsub_shift", "ADD_32_addsub_imm", ""),
    ("sub", "SUB_32_addsub_shift", "SUB_32_addsub_imm", " and op = 1"),
    ("adds", "ADDS_32_addsub_shift", "ADDS_32S_addsub_imm", " and S = 1"),
    ("subs", "SUBS_32_addsub_shift", "SUBS_32S_addsub_imm",
     " and S = 1 and op = 1"),
]

_W_SHIFT_ROWS = [
    ("lsl0", 0, "shift = LSL (00) and imm6 = 000000"),
    ("imm6-lsl", 0, "shift = LSL (00); imm6 is field content (the shift amount)"),
    ("imm6-lsr", 1, "shift = LSR (01); imm6 is field content (the shift amount)"),
    ("imm6-asr", 2, "shift = ASR (10); imm6 is field content (the shift amount)"),
]


def _w_register(mrs, role):
    return {"mrs": [mrs], "role": role, "kind": "aarch64.gpr32",
            "from": "reg_number", "target_type": "w32"}


def _w_forms():
    rows = []
    for mnemonic, shift_node, imm_node, note in _W_FAMILIES:
        for shape, shift_value, decision in _W_SHIFT_ROWS:
            pinned = {"shift": shift_value}
            slots = [_w_register("Rd", "dest"), _w_register("Rn", "src"),
                     _w_register("Rm", "src2")]
            if shape == "lsl0":
                pinned["imm6"] = 0
            else:
                slots.append(
                    {"mrs": ["imm6"], "role": "imm", "kind": "aarch64.imm",
                     "from": "operand_value", "target_type": "imm6",
                     "range": {"signed": False, "bits": 6, "align_bits": 0},
                     "excluded": list(range(32, 64))}
                )
            rows.append({
                "form_id": "aarch64:{0}/w32-w32-w32-{1}".format(mnemonic, shape),
                "mrs": shift_node,
                "decision": "sf = 0 is the node's; {0}{1}".format(decision, note),
                "pinned": pinned,
                "since": "0.10.0",
                "slots": slots,
            })
        for shape, sh_value, decision in [
            ("lsl0", 0, "sh = 0 (no LSL #12)"),
            ("lsl12", 1, "sh = 1 (LSL #12), imm12 still field content"),
        ]:
            rows.append({
                "form_id": "aarch64:{0}/w32-imm12-{1}".format(mnemonic, shape),
                "mrs": imm_node,
                "decision": "sf = 0 is the node's; {0}{1}".format(decision, note),
                "pinned": {"sh": sh_value},
                "since": "0.10.0",
                "slots": [
                    _w_register("Rd", "dest"),
                    _w_register("Rn", "src"),
                    {"mrs": ["imm12"], "role": "imm", "kind": "aarch64.imm",
                     "from": "operand_value", "target_type": "imm12",
                     "range": {"signed": False, "bits": 12, "align_bits": 0}},
                ],
            })
    return rows


FORMS.extend(_w_forms())

# `A64-P13` (ADR-0020). `SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and
# `SUBS_64S_addsub_ext` are `ADD_64_addsub_ext` with `op` (30+1) and/or `S`
# (29+1) fixed, so each row repeats the `add` extended row of the same keyword
# with the mnemonic component changed. The keyword still fixes the width of
# `src2` — the six `[su]xt[bhw]` take a `w` register, `uxtx`/`sxtx` an `x` one —
# and `imm3` still carries the excluded tail 5..7. Register 31 is not pinned
# anywhere: it stays a plain `reg_number` and the node's role says whether it is
# `sp` or `wzr`/`xzr` (ADR-0020 decision 5).
_EXT_FAMILIES = [
    ("sub", "SUB_64_addsub_ext", " and op = 1"),
    ("adds", "ADDS_64S_addsub_ext", " and S = 1"),
    ("subs", "SUBS_64S_addsub_ext", " and S = 1 and op = 1"),
]

_EXT_KEYWORDS = [
    ("uxtb", 0, "w32"),
    ("uxth", 1, "w32"),
    ("uxtw", 2, "w32"),
    ("uxtx", 3, "x64"),
    ("sxtb", 4, "w32"),
    ("sxth", 5, "w32"),
    ("sxtw", 6, "w32"),
    ("sxtx", 7, "x64"),
]


def _ext_forms():
    rows = []
    for mnemonic, node, note in _EXT_FAMILIES:
        for keyword, option, source in _EXT_KEYWORDS:
            kind = "aarch64.gpr32" if source == "w32" else "aarch64.gpr64"
            rows.append(
                {
                    "form_id": "aarch64:{0}/x64-x64-{1}-imm3-{2}".format(
                        mnemonic, source, keyword
                    ),
                    "mrs": node,
                    "decision": "option = {0} ({1}); imm3 is field content in "
                    "0..4, 5..7 excluded{2}".format(option, keyword.upper(), note),
                    "pinned": {"option": option},
                    "since": "0.11.0",
                    "slots": [
                        {
                            "mrs": ["Rd"],
                            "role": "dest",
                            "kind": "aarch64.gpr64",
                            "from": "reg_number",
                            "target_type": "x64",
                        },
                        {
                            "mrs": ["Rn"],
                            "role": "src",
                            "kind": "aarch64.gpr64",
                            "from": "reg_number",
                            "target_type": "x64",
                        },
                        {
                            "mrs": ["Rm"],
                            "role": "src2",
                            "kind": kind,
                            "from": "reg_number",
                            "target_type": source,
                        },
                        {
                            "mrs": ["imm3"],
                            "role": "imm",
                            "kind": "aarch64.imm",
                            "from": "operand_value",
                            "target_type": "imm3",
                            "range": {"signed": False, "bits": 3, "align_bits": 0},
                            "excluded": [5, 6, 7],
                        },
                    ],
                }
            )
    return rows


FORMS.extend(_ext_forms())

# `A64-P14` (ADR-0021). `cmp` and `cmn` are `subs`/`adds` with `Rd` fixed to
# 31 and the destination dropped: each row is the `subs`/`adds` row of the same
# layout and width with `Rd` pinned to 31 and the `dest` slot removed. The
# alias nodes (`Instruction.InstructionAlias`) carry no `encoding`; they are
# read only to verify the pairing — `operation_id` names the base node,
# `condition` is `Rd == '11111'`, `preferred` is true — so the bytes stay the
# base node's. The 32-bit extended alias rows stay out: the 32-bit extended
# base rows are not in the table either (ADR-0021 decision 4).
_ALIAS_FAMILIES = [
    ("cmp", "CMP", "SUBS"),
    ("cmn", "CMN", "ADDS"),
]

_ALIAS_WIDTHS = [("x64", "64"), ("w32", "32")]


def _alias_register(width, mrs, role):
    if width == "x64":
        return {"mrs": [mrs], "role": role, "kind": "aarch64.gpr64",
                "from": "reg_number", "target_type": "x64"}
    return _w_register(mrs, role)


def _alias_forms():
    rows = []
    for mnemonic, alias, base in _ALIAS_FAMILIES:
        for width, base_width in _ALIAS_WIDTHS:
            shift_node = "{0}_{1}_addsub_shift".format(base, base_width)
            imm_node = "{0}_{1}S_addsub_imm".format(base, base_width)
            for shape, shift_value, decision in _W_SHIFT_ROWS:
                pinned = {"Rd": 31, "shift": shift_value}
                slots = [_alias_register(width, "Rn", "src"),
                         _alias_register(width, "Rm", "src2")]
                if shape == "lsl0":
                    pinned["imm6"] = 0
                else:
                    imm6 = {"mrs": ["imm6"], "role": "imm",
                            "kind": "aarch64.imm", "from": "operand_value",
                            "target_type": "imm6",
                            "range": {"signed": False, "bits": 6,
                                      "align_bits": 0}}
                    if width == "w32":
                        imm6["excluded"] = list(range(32, 64))
                    slots.append(imm6)
                rows.append({
                    "form_id": "aarch64:{0}/{1}-{1}-{2}".format(
                        mnemonic, width, shape),
                    "mrs": shift_node,
                    "decision": "Rd = 31 (the alias drops the destination); "
                    "sf is the node's; {0}".format(decision),
                    "pinned": pinned,
                    "since": "0.12.0",
                    "alias": alias,
                    "alias_width": width,
                    "slots": slots,
                })
            for shape, sh_value, decision in [
                ("lsl0", 0, "sh = 0 (no LSL #12)"),
                ("lsl12", 1, "sh = 1 (LSL #12), imm12 still field content"),
            ]:
                rows.append({
                    "form_id": "aarch64:{0}/{1}-imm12-{2}".format(
                        mnemonic, width, shape),
                    "mrs": imm_node,
                    "decision": "Rd = 31 (the alias drops the destination); "
                    "sf is the node's; {0}".format(decision),
                    "pinned": {"Rd": 31, "sh": sh_value},
                    "since": "0.12.0",
                    "alias": alias,
                    "alias_width": width,
                    "slots": [
                        _alias_register(width, "Rn", "src"),
                        {"mrs": ["imm12"], "role": "imm",
                         "kind": "aarch64.imm", "from": "operand_value",
                         "target_type": "imm12",
                         "range": {"signed": False, "bits": 12,
                                   "align_bits": 0}},
                    ],
                })
        for keyword, option, source in _EXT_KEYWORDS:
            kind = "aarch64.gpr32" if source == "w32" else "aarch64.gpr64"
            rows.append({
                "form_id": "aarch64:{0}/x64-x64-{1}-imm3-{2}".format(
                    mnemonic, source, keyword),
                "mrs": "{0}_64S_addsub_ext".format(base),
                "decision": "Rd = 31 (the alias drops the destination); "
                "option = {0} ({1}); imm3 is field content in 0..4, 5..7 "
                "excluded".format(option, keyword.upper()),
                "pinned": {"Rd": 31, "option": option},
                "since": "0.12.0",
                "alias": alias,
                "alias_width": "x64",
                "slots": [
                    {"mrs": ["Rn"], "role": "src", "kind": "aarch64.gpr64",
                     "from": "reg_number", "target_type": "x64"},
                    {"mrs": ["Rm"], "role": "src2", "kind": kind,
                     "from": "reg_number", "target_type": source},
                    {"mrs": ["imm3"], "role": "imm", "kind": "aarch64.imm",
                     "from": "operand_value", "target_type": "imm3",
                     "range": {"signed": False, "bits": 3, "align_bits": 0},
                     "excluded": [5, 6, 7]},
                ],
            })
    return rows


FORMS.extend(_alias_forms())


def _alias_stem(base):
    stem = re.sub(r"_(32S?|64S?)_", "_", base)
    if stem == base:
        raise SystemExit("{0}: no width component to strip".format(base))
    return stem


def _alias_width(node):
    encoded = (node.get("_meta") or {}).get("encoded_in") or {}
    widths = set()
    for key in encoded:
        if key.startswith("<X"):
            widths.add("x64")
        elif key.startswith("<W"):
            widths.add("w32")
    if len(widths) != 1:
        raise SystemExit(
            "{0}/{1}: cannot tell the width from {2}".format(
                node.get("name"), node.get("operation_id"), sorted(encoded)))
    return widths.pop()


def load_alias_nodes(document):
    index = {}
    for node in walk(document["instructions"]):
        if not str(node.get("_type", "")).endswith(
                "Instruction.InstructionAlias"):
            continue
        key = (node.get("name"), node.get("operation_id"))
        index.setdefault(key, []).append(node)
    return index


def verify_alias(spec, node, index):
    name = spec["alias"]
    operation_id = "{0}_{1}".format(name, _alias_stem(spec["mrs"]))
    candidates = index.get((name, operation_id), [])
    if len(candidates) != 2:
        raise SystemExit(
            "{0}: expected two {1} alias nodes for {2}, found {3}".format(
                spec["form_id"], name, operation_id, len(candidates)))
    matching = [item for item in candidates
                if _alias_width(item) == spec["alias_width"]]
    if len(matching) != 1:
        raise SystemExit(
            "{0}: expected one {1} alias node for {2}, found {3}".format(
                spec["form_id"], spec["alias_width"], operation_id,
                len(matching)))
    alias = matching[0]
    if alias.get("encoding") is not None:
        raise SystemExit(
            "{0}: the alias node has an encoding; the row must come from the "
            "base node".format(spec["form_id"]))
    if (alias.get("preferred") or {}).get("value") is not True:
        raise SystemExit(
            "{0}: the alias node is not preferred".format(spec["form_id"]))
    condition = alias.get("condition") or {}
    if (str(condition.get("_type")) != "AST.BinaryOp"
            or (condition.get("left") or {}).get("value") != "Rd"
            or condition.get("op") != "=="
            or (condition.get("right") or {}).get("value") != "'11111'"):
        raise SystemExit(
            "{0}: the alias condition is not Rd == '11111': {1}".format(
                spec["form_id"], json.dumps(condition)))
    sf = None
    for field in encode_fields(node):
        if field["name"] == "sf":
            sf = field["value"]
    if sf is not None:
        expected = "1" if spec["alias_width"] == "x64" else "0"
        if sf != expected:
            raise SystemExit(
                "{0}: base node {1} has sf = {2}, not {3}".format(
                    spec["form_id"], spec["mrs"], sf, expected))



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


def load_nodes(document):
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
        if "excluded" in slot_spec:
            span = slot_spec.get("range") or {}
            if slot_spec["from"] != "operand_value" or "bits" not in span:
                raise SystemExit(
                    "{0}/{1}: `excluded` needs an operand_value slot with a "
                    "declared range.bits".format(spec["form_id"], slot_spec["role"])
                )
            if span.get("signed"):
                raise SystemExit(
                    "{0}/{1}: `excluded` is only emitted for unsigned slots".format(
                        spec["form_id"], slot_spec["role"]
                    )
                )
            values = list(slot_spec["excluded"])
            if sorted(set(values)) != values:
                raise SystemExit(
                    "{0}/{1}: `excluded` must be strictly increasing".format(
                        spec["form_id"], slot_spec["role"]
                    )
                )
            low, high = 0, (1 << span["bits"]) - 1
            for value in values:
                if value < low or value > high:
                    raise SystemExit(
                        "{0}/{1}: excluded value {2} is outside [{3}, {4}]".format(
                            spec["form_id"], slot_spec["role"], value, low, high
                        )
                    )
            slot["excluded"] = values
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
            if "excluded" in slot:
                lines.append(
                    '          "excluded": [{0}],'.format(
                        ", ".join(str(value) for value in slot["excluded"])
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
    with io.open(MRS, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    nodes = load_nodes(document)
    aliases = load_alias_nodes(document)
    for spec in FORMS:
        if "alias" in spec:
            verify_alias(spec, nodes[spec["mrs"]], aliases)
    for version in VERSIONS:
        emit(version, nodes)

    with io.open(MRS, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    print("source Instructions.json sha256:{0}".format(digest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
