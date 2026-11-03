# Definition Format

Status: **frozen for `x86-64` `0.1.0`**; the same format is intended for the
other targets, whose tables wait on source data, not on an open decision
(`OD-07` is settled by ADR-0005). This document defines the artifact a pinned
`definition_identity` names. It is the operational form of `OD-10`: the table
*is* the feature surface, and a `form_id` the table does not contain is
`E-FORM-001`.

A definition is **data**. It is not a library, a plugin, or a table of callbacks
(`INV-06`). The materializer reads it, checks it, and encodes from it.

## 1. What a definition answers

Two questions, and only two:

1. Does this `form_id` exist, and what is its operand signature?
2. For each operand, which bits of the output does that operand own?

Everything else stays out: fixup descriptors (the plan owns them), layout (the
plan owns it), defaults, aliases, feature flags, and any instruction the plan did
not name. A definition that tries to answer a third question has crossed back
into selection (`INV-01`, `INV-02`).

## 2. Document shape

```json
{
  "definition_format": "fmp-def/0.1",
  "namespace": "monasm.isa.x86",
  "version": "0.1.0",
  "target_identity": { "isa_family": "x86", "isa_variant": "x86-64",
                       "execution_mode": "64", "enabled_extensions": [],
                       "byte_order": "little", "address_width": 64 },
  "forms": [ { "form_id": "...", "template": "...", "slots": [ ... ] } ]
}
```

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `definition_format` | yes | Format version of this document | A newer document is read by an older loader with different rules and accepted. |
| `namespace`, `version` | yes | Identity the plan must name | Two rule sets are loadable under one name; the plan cannot say which it was built for. |
| `target_identity` | yes | The target the table is valid for | An x86 table is applied to an `x86-32` plan, and `REX.W` is emitted for a 32-bit mode. |
| `forms` | yes | The closed form set | An empty table would accept nothing but claim to be a definition. |

`target_identity` is compared field by field with the plan's, excluding
`feature_constraints` (which the contract already requires to be empty). A
difference in `isa_family`, `isa_variant,` or `enabled_extensions` is
`E-TARGET-001`, in `execution_mode` `E-TARGET-002`, and in `byte_order` or
`address_width` `E-TARGET-004`. `E-TARGET-003` has no trigger here because a row
carries no extension requirement of its own: the table declares one
`enabled_extensions` set for the whole document. The table is never filtered per
plan: a definition covers exactly one target.

There is **no digest field inside the definition**. The digest is computed over
the document and compared with `definition_identity.digest` (`E-DEF-001`); a
field that contained its own hash would have to exclude itself from its own
input, which is the kind of special case that drifts.

## 3. Forms

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `form_id` | yes | The identity a plan must name, exactly | Resolution becomes a search, and a search is a decision. |
| `template` | yes | One hex byte string; its length is the form's size, with every operand-owned bit at its base value | Without a base the loader would have to invent zeros for bits no operand writes. |
| `slots` | yes | Ordered operand signature, one entry per operand | The plan could supply operands in any order and a length check would be the only guard. |

Rules:

- `form_id` MUST follow `01_contract.md` §7. For `x86` it MUST end in
  `/legacy`, `/vex` or `/evex`; v0 contains only `/legacy`.
- `size` is **not** a field: it is `len(template) / 2`. A redundant size field
  can disagree with the template, and the disagreement has no correct resolution.
- Two rows MUST NOT share a `form_id` (`E-DEF-001` at load; the plan's failure
  is `E-FORM-001`).
- A row MUST NOT be reachable from another row's signature. `rm-r64` and
  `r64-rm` are two rows; neither is a fallback for the other.
- The template's operand-owned bits are the base value the operand overwrites in
  full. For a fixup-covered field the base value MUST be zero
  (`03_fixup_model.md` §3), so the emitted byte is the fixup's alone.

## 4. Slots

```json
{ "role": "dest", "kind": "x86.gpr64", "target_type": "rm64",
  "from": "reg_number", "modifiers": [],
  "placements": [ { "bit_offset": 16, "width": 3 } ] }
```

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `role` | yes | Same closed set as the plan operand `role` | Two operands of one form become interchangeable and `src`/`dest` can swap silently. |
| `kind` | yes | Target-namespaced payload type, e.g. `x86.gpr64`, `x86.imm`, `x86.rel` | A `{"reg": 1}` payload is read as a value `1`. |
| `target_type` | yes | The slot constraint the plan operand must name | A `r64` operand fills a `rm64` slot; the check has nothing to compare. |
| `from` | yes | `reg_number` \| `operand_value` | The loader would have to guess whether `payload.reg` or `payload.value` is the number. |
| `range` | only for `operand_value` | `{signed, bits, align_bits}` | `imm8 = 300` is truncated to `0x2c` and becomes `44`. |
| `placements` | yes | Ordered bit ranges, most significant operand bits first | The bit order of a split field would be a convention, not data. |
| `modifiers` | yes | The closed set of `{name, value}` pairs this slot permits; `[]` means none | An ignored `lock` emits `0xf0`-less bytes with different semantics and no error. |

`from` is a closed two-member set:

- `reg_number` — the operand's `payload.reg`, unsigned. The slot's placements
  must hold `sum(width)` bits; a register number that needs more is
  `E-OPERAND-004`. **It is never truncated**, because `r9` truncated to 3 bits is
  register 1 (`rcx`), and `48 89 c8` is a perfectly legal `movq %rcx, %rax`
  (`04_errors.md`, `E-OPERAND-004` counterexample).
- `operand_value` — the operand's `payload.value`, signed, checked against
  `range` before any bit is written.

`range_kind` is not a field: the error code follows from `role`, which is already
in the table.

| Slot role | Range violation |
|---|---|
| `target` | `E-RANGE-002` (displacement/branch offset) |
| `imm`, `disp` | `E-RANGE-001` (immediate) |

`align_bits` is checked on the value as planned: `align_bits = 0` means no check,
and a non-zero value that is not a multiple is `E-RANGE-003`. No v0 x86 slot
declares a non-zero `align_bits`, because x86 branch displacements are
byte-granular; the field exists for the AArch64 and RV64 branch fields, which are
scaled by 4.

### 4.1 Placements

A placement is a bit range inside the template:

```json
{ "bit_offset": 16, "width": 3 }
```

- `bit_offset` counts from the **least significant bit of template byte 0**. Bit
  `k` therefore lives in byte `k / 8` at bit `k % 8`, and a multi-byte field is
  written little-endian, which is the only byte order v0 definitions declare
  (`byte_order: "big"` is `E-TARGET-004` against a little-endian definition).
- Placements of one slot are in **value order**: the first placement receives the
  most significant bits of the operand value. This mirrors
  `03_fixup_model.md` §3 and, like it, has no separate order field.
- The widths of one slot MUST sum to the number of bits the slot encodes: `bits`
  from `range` for `operand_value`, and the form's own register field width for
  `reg_number`.
- Placements of different slots MUST NOT overlap, and a placement MUST stay
  inside the template. Both are `E-DEF-001` at load time: a definition that
  overlaps itself has no correct output, so it is never a plan error.
- A slot MUST have at least one placement.

## 5. What is deliberately absent

- **No fixup descriptors.** The plan names the field descriptor, its PC rule and
  its transform; a definition that also described them would be a second source
  of truth for the same bits (`OD-02`).
- **No `encoding_choices`, no defaults, no optional bytes.** `ADR-0004` and
  `OD-11` removed the plan-side selector; a definition-side selector would
  reintroduce it one layer down.
- **No alias rows.** A `form_id` that is not in the table is rejected even if a
  near neighbour exists (`N01`).
- **No wildcard or "any register" rows.** Every row names its template.
- **No comments.** The file is JSON; the digest is computed over the canonical
  form (§6), so a comment would not survive canonicalization anyway.

## 6. Digest

`definition_identity.digest` is

```text
sha256(canonical_json(definition_document))
```

with canonical JSON exactly as `01_contract.md` §12 defines it: keys sorted by
code point, no insignificant whitespace, UTF-8 without BOM, no duplicate keys,
integers only, no trailing newline. Nothing is excluded: the document contains
nothing but the fields in §2 and §3, so every byte of it participates.

Consequences, which are the test `OD-06` asks for:

- A change to any rule — a template byte, a width, a range, a slot order —
  changes the digest and the old plan fails `E-DEF-001`.
- Reindenting the file, reordering keys, or writing it with CRLF does not change
  the digest, because canonicalization happens before hashing.
- A comment cannot exist. The "comment-only change" half of `OD-06` is therefore
  unrepresentable rather than merely ignored.

The materializer MUST refuse a definition whose declared `namespace`/`version` it
does not ship (`E-DEF-002`) before hashing, so a plan cannot pull in an arbitrary
table by digest alone.

## 7. Lookup

1. `form_id` MUST be present in `forms` (`E-FORM-001`). No normalisation, no
   case folding, no suffix repair.
2. The plan's operand list MUST match `slots` in length and role sequence
   (`E-OPERAND-002`).
3. Each operand's `kind` and `target_type` MUST equal the slot's
   (`E-OPERAND-001`).
4. Each operand's `modifiers` MUST be a subset of the slot's permitted set
   (`E-OPERAND-003`, reason `modifier not permitted`).
5. Each operand's payload shape MUST match `from` (`E-OPERAND-003`).

Only after these pass is a byte written.

## 8. `x86-64` `0.1.0` table

`definitions/x86_64/0.1.0.json` is canonical. The table below is a reading aid;
`tools/check_definition.py` fails if the two disagree.

Canonical digest, computed per §6:

```text
sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad
```

A plan names `namespace: monasm.isa.x86`, `version: 0.1.0` and that digest in
`definition_identity`. The value is reproducible with
`python tools/check_definition.py`, which prints it for every definition.

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `x86:mov/rm-r64/legacy` | `4889c0` | dest: `x86.gpr64`/`rm64` → `[16,3]`; src: `x86.gpr64`/`r64` → `[19,3]` | 3 | `EC-27` |
| `x86:mov/r64-rm/legacy` | `488bc0` | dest: `x86.gpr64`/`r64` → `[19,3]`; src: `x86.gpr64`/`rm64` → `[16,3]` | 3 | `EC-27` |
| `x86:add/rm64-imm8/legacy` | `4883c000` | dest: `x86.gpr64`/`rm64` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | `EC-01` |
| `x86:add/rm64-imm32/legacy` | `4881c000000000` | dest: `x86.gpr64`/`rm64` → `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | `EC-01`, `EC-04` |
| `x86:add/rax-imm32/legacy` | `480500000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | `EC-04` |
| `x86:jmp/rel8/legacy` | `eb00` | target: `x86.rel`/`rel8` → `[8,8]` | 2 | `EC-03` |
| `x86:jmp/rel32/legacy` | `e900000000` | target: `x86.rel`/`rel32` → `[8,32]` | 5 | `EC-03` |

Placements are written `[bit_offset, width]`. `[16,3]` is the low three bits of
byte 2, which is `ModRM.rm`; `[19,3]` is `ModRM.reg`; `[24,8]` is byte 3. The two
`ModRM` bits above them (`bits 6–7` of byte 2) are `mod = 0b11`, part of the
template and not owned by any operand.

`x86:add/rax-imm32/legacy` has no `dest` slot: the register is fixed by the
opcode (`REX.W 05 id`), which is exactly why `rax-imm32` and `rm64-imm32` are two
`form_id`s and not two choices (`01_contract.md` §7).

The register field of the four `ModRM` rows is 3 bits wide, so `r8`–`r15` are not
encodable: the template's `REX` byte is `0x48`, and no extension bit is declared
for those registers. A plan that names `mov rax, r9` is rejected
`E-OPERAND-004`; it is not emitted as `48 89 c8`, which decodes as
`movq %rcx, %rax`. Adding `r8`–`r15` is a table change with its own digest, not an
implicit widening.

Every row is verified against `llvm-mc` 23.1.2 in `EXP-0004`: each template byte
string is decoded, and each `ModRM` and immediate/branch field is exercised across
its whole encoded range.

Every row is verified against `llvm-mc` 23.1.2 in `EXP-0004`: each template byte
string is decoded, and each `ModRM`/immediate/relaxation field is exercised
across its whole encoded range.

## 9. Load-time checks

| Check | Code |
|---|---|
| `definition_format` unsupported (only `fmp-def/0.1` is accepted) | `E-DEF-001` |
| `namespace`/`version` not shipped by this materializer | `E-DEF-002` |
| duplicate `form_id` | `E-DEF-001` |
| `template` empty, odd-length, or non-hex | `E-DEF-001` |
| placement outside the template, or two placements overlapping | `E-DEF-001` |
| slot with no placement | `E-DEF-001` |
| placement widths that do not sum to `range.bits` | `E-DEF-001` |
| plan digest does not match the loaded definition | `E-DEF-001` |

A definition that fails a load-time check is unusable, so the namespace/version
gate is `E-DEF-002` and everything else is `E-DEF-001`, and no plan is read from a
definition that fails either. This is the one place where `E-DEF-001` is raised
without a plan error: the input is the definition.

## 10. Open

- `OD-06` (digest coverage) is settled for this document shape by §6; the
  measurement that confirms both halves is the digest test in `EXP-0004` §4.
- `OD-07` (AArch64 knowledge source) is settled by ADR-0005: the facts come
  from the Arm MRS 2026-06, and the Arm notice ships with the generated table.
  The format does not need to change for it: `adrp`'s split `immhi:immlo` and
  RV64's B-type scatter are both expressible as multiple placements of one
  slot. What is missing is the data, not the design: the archive is not
  vendored, so the table waits on the drop that `tools/check_mrs.py` verifies.
- `X86-P9` (explicit encoding family) stays deferred; no `/vex` or `/evex` row
  exists, so naming one is `E-FORM-001`.
