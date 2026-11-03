# Definition Format

Status: **frozen for `x86-64` `0.1.0` and `aarch64` `0.1.0`**; the same format
is intended for the other targets, whose tables wait on source data, not on an
open decision (`OD-07` is settled by ADR-0005 and pinned by ADR-0006). This
document defines the artifact a pinned `definition_identity` names. It is the
operational form of `OD-10`: the table *is* the feature surface, and a `form_id`
the table does not contain is `E-FORM-001`.

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
byte-granular; the field exists for scaled branch fixups — AArch64 `bl`
(`align_bits = 2`) and RV64 `beq`/`jal` (`align_bits = 1`) — where the
pre-transform displacement must be instruction-aligned. The slot itself keeps
`align_bits = 0`, because it holds field content (§8.3).

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

## 8. v0 definition tables

Each table below is a reading aid; `definitions/<isa>/<version>.json` is
canonical, and `tools/check_definition.py` fails if a row and the JSON disagree.

| Table | Namespace | Digest |
|---|---|---|
| `definitions/x86_64/0.1.0.json` | `monasm.isa.x86` | `sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad` |
| `definitions/aarch64/0.1.0.json` | `monasm.isa.aarch64` | `sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e` |

A plan names its `namespace`, `version` and digest in `definition_identity`.

### 8.1 `x86-64` `0.1.0`

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
string is decoded, and each `ModRM` and immediate/branch field is exercised
across its whole encoded range.

### 8.2 `aarch64` `0.1.0`

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `aarch64:add/x64-x64-x64-lsl0` | `0000008b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P1` |
| `aarch64:add/x64-imm12-lsl0` | `00000091` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P2` |
| `aarch64:bl/imm26` | `00000094` | target: `aarch64.rel`/`imm26` → `[0,26]` | 4 | `A64-P5` |
| `aarch64:adrp/x64-imm21` | `00000090` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; target: `aarch64.rel`/`imm21` → `[5,19]`, `[29,2]` | 4 | `EC-15`, `EC-17`, `A64-P6` |

The templates are little-endian file order, so `0000008b` is the word
`0x8b000000` in a disassembler. The generator
(`research/evidence/experiments/EXP-0008/generate_aarch64.py`) derives every
bit from the MRS node, requires the MRS node name to exist, and refuses to emit
unless all 32 bits are covered exactly once by a fixed bit or a slot placement;
`EXP-0008` §2–§3 records the four nodes and the coverage check.

The `-lsl0` suffix on both `add` rows carries a decision the operand list does
not state, and the name states it instead (`01_contract.md` §7, `ADR-0004`): the
MRS leaves AArch64 `shift` (2 bits) and `imm6` (6 bits) variable in the
shifted-register node, and `sh` (1 bit) variable in the immediate node. This
table pins them to `LSL #0` and to `sh = 0`. A plan that wants
`add x0, x1, x2, lsl #4` or `add x0, x1, #0x1000` names a form that does not
exist and is rejected `E-FORM-001`; nothing shifts implicitly (`INV-02`,
`INV-03`, `N01`).

`adrp`'s immediate is one value over two fields: `immhi` holds bits `[20:2]` and
`immlo` holds `[1:0]`, which is why the slot has two placements in that order
(§4.1: first placement, most significant bits).

`bl` and `adrp` are the two rows whose field is not a plain integer, and the
next subsection is the rule that follows from it.

### 8.3 Scaled branch fields: the slot is the field

`bl`'s `imm26` counts instructions, not bytes, and `adrp`'s `imm21` counts
4 KiB pages. A definition slot has no scaling transform, so the table cannot say
"divide by 4 first" and must not pretend to:

- `{ "value": n }` on those slots writes `n` into the field, exactly as the
  definition says. It is the field content, not a byte offset. This is the same
  rule as an x86 `rel32` slot; the difference is only that x86's scale is 1.
- A byte offset is expressed with a fixup, which does carry a transform:
  `scale` with `transform_shift: 2` for `bl`, `page` with `pcrel_page` for
  `adrp`. That is the only path where the division happens, and it is why both
  AArch64 branch fixtures use a symbol instead of a plain value.
- `align_bits` follows the value it is attached to: `0` on the slot (a field
  value need not be a multiple of 4), and `2` on the `bl` fixup, where the
  pre-transform displacement must be instruction-aligned (`E-RANGE-003`).
  `adrp`'s fixup uses `align_bits: 0` because the page delta is already divided;
  an `align_bits: 12` there would reject every symbol that is not page-aligned.
- An operand whose bits a fixup owns carries `{}`, not a `symbol_id`
  (`01_contract.md` §8.1): only a `target` slot may name a symbol. In
  `A64-P6` the `add`'s `imm12` is such a slot.

This keeps `INV-04` intact: nothing is relaxed, and a plan that omits the
transform emits the field value it stated, which is a wrong program rather than a
repaired one. The alternative — a slot that silently scales — was rejected
because the same number would then mean different things on `add` and `bl`.

RV64 follows the same rule with different shift amounts (ADR-0007, `EXP-0009`):
the source states `left_shift: 1` for `beq`/`jal` and `left_shift: 12` for
`auipc`, so a byte offset is a `scale` fixup with `transform_shift` 1 or 12,
while the slot keeps `align_bits: 0` and holds field content. The B- and J-type
slots have several placements each (`beq`: `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]`;
`jal`: `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]`), which is the scattered-field
case directive §6.3 item 6 asks for. `c.addi` also needs `imm != 0` and
`xd != 0`; since `fmp-def/0.1` has no non-zero constraint, it stays outside v0
until a format decision adds one.

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
- `OD-07` (AArch64 knowledge source) is settled by ADR-0005 and pinned by
  ADR-0006: the facts come from the Arm MRS 2026-06 OPENSOURCE packaging, and
  the Arm notice ships with the generated table. The format did not need to
  change for it: `adrp`'s split `immhi:immlo` is two placements of one slot, as
  §4.1 anticipated. `definitions/aarch64/0.1.0.json` now exists (§8.2). What is
  missing is coverage, not design: `A64-P3`/`P4`/`P7`/`P8` and the `-lsl12`
  half of `A64-P2` have no row, so naming them is `E-FORM-001`.
- The archive is still not vendored and the drop is not a build input: a
  regeneration reads `research/external/arm-mrs/` after `tools/check_mrs.py`
  passes, and the shipped artifact is the JSON plus its digest.
- A slot has no scaling transform (§8.3). If a future slice needs an operand
  value that is *not* the field content, that is a format change with its own
  ADR, not a convention added here.
- `X86-P9` (explicit encoding family) stays deferred; no `/vex` or `/evex` row
  exists, so naming one is `E-FORM-001`.
