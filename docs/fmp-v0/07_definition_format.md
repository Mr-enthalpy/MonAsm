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
| `excluded` | no | Closed, strictly increasing list of exact values the slot may not carry; absent means no exclusion | `c.addi a0, 0` is inside `[-32, 31]` and encodes as `01 05`, which `llvm-objdump` calls a HINT, not the addition the plan names. |
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

`excluded` is the one place a slot may be **non-convex**, and it is data, not a
predicate (`ADR-0009`, `OD-14`). It is a closed list of exact integers, strictly
increasing, each inside the slot's representable domain: `range` for
`operand_value`, and the placements' summed width for `reg_number`. A value in
the list is rejected with `E-RANGE-004` even though `range` accepts it; an
absent key means no value is excluded, and an empty list is a definition error
because it is not a statement. The check is a lookup, never an expression
(`INV-06`), so "legal" remains decidable by inspection. No v0 x86 or AArch64
slot declares one; `riscv:c.addi/rd-imm6` is the first, excluding `0` on both
slots (§8.5).

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
6. Each operand's value MUST be inside the slot's domain (`E-RANGE-001`/`002`/
   `003`/`004`); an `excluded` entry is rejected even when `range` contains it.

Only after these pass is a byte written.

## 8. v0 definition tables

Each table below is a reading aid; `definitions/<isa>/<version>.json` is
canonical, and `tools/check_definition.py` fails if a row and the JSON disagree.

| Table | Namespace | Digest |
|---|---|---|
| `definitions/x86_64/0.1.0.json` | `monasm.isa.x86` | `sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad` |
| `definitions/aarch64/0.1.0.json` | `monasm.isa.aarch64` | `sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e` |
| `definitions/aarch64/0.2.0.json` | `monasm.isa.aarch64` | `sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed` |
| `definitions/aarch64/0.3.0.json` | `monasm.isa.aarch64` | `sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb` |
| `definitions/aarch64/0.4.0.json` | `monasm.isa.aarch64` | `sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78` |
| `definitions/aarch64/0.5.0.json` | `monasm.isa.aarch64` | `sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e` |
| `definitions/aarch64/0.6.0.json` | `monasm.isa.aarch64` | `sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964` |
| `definitions/rv64/0.1.0.json` | `monasm.isa.riscv` | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` |
| `definitions/rv64/0.2.0.json` | `monasm.isa.riscv` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |

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

### 8.2 `aarch64` `0.1.0`, `0.2.0`, `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` and `0.7.0`

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `aarch64:add/x64-x64-x64-lsl0` | `0000008b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P1` |
| `aarch64:add/x64-imm12-lsl0` | `00000091` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P2` |
| `aarch64:add/x64-imm12-lsl12` | `00004091` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P2` — `0.2.0`+ |
| `aarch64:bl/imm26` | `00000094` | target: `aarch64.rel`/`imm26` → `[0,26]` | 4 | `A64-P5` |
| `aarch64:adrp/x64-imm21` | `00000090` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; target: `aarch64.rel`/`imm21` → `[5,19]`, `[29,2]` | 4 | `EC-15`, `EC-17`, `A64-P6` |
| `aarch64:b.cond/imm19` | `00000054` | imm: `aarch64.cond`/`cond4` → `[0,4]`; target: `aarch64.rel`/`imm19` → `[5,19]` | 4 | `EC-29`, `A64-P4` — `0.3.0` only |
| `aarch64:ldr/x64-base-imm12` | `000040f9` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:ldr/x64-base-imm9-pre` | `000c40f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:ldr/x64-base-imm9-post` | `000440f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:ldur/x64-base-imm9` | `000040f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:str/x64-base-imm12` | `000000f9` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:movz/x64-imm16-lsl0` | `000080d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl16` | `0000a0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl32` | `0000c0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl48` | `0000e0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:add/x64-x64-x64-imm6-lsl` | `0000008b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P8` — `0.6.0` only |
| `aarch64:add/x64-x64-x64-imm6-lsr` | `0000408b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P8` — `0.6.0` only |
| `aarch64:add/x64-x64-x64-imm6-asr` | `0000808b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P8` — `0.6.0` only |
| `aarch64:add/x64-x64-w32-imm3-uxtb` | `0000208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-uxth` | `0020208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-uxtw` | `0040208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-x64-imm3-uxtx` | `0060208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-sxtb` | `0080208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-sxth` | `00a0208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-sxtw` | `00c0208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-x64-imm3-sxtx` | `00e0208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |

`0.1.0` holds the first, second, fourth and fifth rows; `0.2.0` adds
`aarch64:add/x64-imm12-lsl12` (ADR-0011); `0.3.0` repeats all five and adds
`aarch64:b.cond/imm19` (ADR-0012); `0.4.0` repeats all six and adds the five
load/store rows (ADR-0013); `0.5.0` repeats all eleven and adds the four `movz`
rows (ADR-0014); `0.6.0` repeats all fifteen and adds the three shift rows
(ADR-0015); `0.7.0` repeats all eighteen and adds the eight extend rows
(ADR-0016). Each document therefore shares its earlier rows
unchanged and differs only in the rows its version introduced, so a plan bound to
an older version cannot reach a newer form (`E-FORM-001`, `N01`) even though the
newest document has it.

The templates are little-endian file order, so `0000008b` is the word
`0x8b000000` in a disassembler. The generator
(`research/evidence/experiments/EXP-0008/generate_aarch64.py`) derives every
bit from the MRS node, requires the MRS node name to exist, and refuses to emit
unless all 32 bits are covered exactly once by a fixed bit or a slot placement;
`EXP-0008` §2–§3 records the nodes and the coverage check. The twenty-six forms come
from twelve nodes: `ADD_64_addsub_shift` is read four times, once with `imm6`
pinned to 0 and once per shift keyword, `ADD_64_addsub_ext` eight times, once per
`option` value, `ADD_64_addsub_imm` twice, once with
`sh = 0` and once with `sh = 1`, `MOVZ_64_movewide` four times, once per `hw`
value, `B_only_condbranch` contributes one row with both of its variable
fields as operands, and each of the five load/store rows reads one node whose
addressing-kind bits are fixed and whose `imm12`/`imm9` is the single variable
field; the generator states each pinned value explicitly and asserts that
`0.1.0` … `0.6.0` still hash to their frozen digests.

The `-lsl0`/`-lsl12` suffix on the `add` rows carries a decision the operand list
does not state, and the name states it instead (`01_contract.md` §7, `ADR-0004`):
the MRS leaves AArch64 `shift` (2 bits) and `imm6` (6 bits) variable in the
shifted-register node, and `sh` (1 bit) variable in the immediate node. This
table pins `shift` to `LSL` and `imm6` to 0 in the plain register row, and pins
`sh` to `0` or `1` in the two immediate rows. The shift *keyword* is a decision;
the shift *amount* is not: `-imm6-lsl`/`-imm6-lsr`/`-imm6-asr` pin `shift` and
leave `imm6` open as a `0…63` operand, so `add x0, x1, x2, lsl #4` is
`aarch64:add/x64-x64-x64-imm6-lsl` with `imm = 4`, and nothing shifts implicitly
(`INV-02`, `INV-03`, `EC-31`, ADR-0015). `lsl #0` is expressible both ways —
`-lsl0` and `-imm6-lsl` with `imm6 = 0` are the same word `0x8b020020` — because
the assembly language itself treats the two spellings as one instruction, and
excluding `0` would make an operand's value choose the form.

The two immediate rows hold the *same* operand value type, and only the form
differs: `{ "value": n }` must be in `[0, 4095]` for both, and the instruction
does the `<< 12` on the `-lsl12` one. Writing `add x0, x1, #0x1000` as
`-lsl0` is therefore `E-RANGE-001` (`N18a`), not a silent switch to `-lsl12` —
which is exactly what `llvm-mc` does with the plain literal (`EV-26`,
`EXP-0013` §2). Writing `0x123000` as `-lsl12` is `E-RANGE-001` too (`N18b`),
because the operand is field content, not the shifted literal.

`aarch64:b.cond/imm19` is the one row whose *condition* is an operand. `cond` is a
4-bit field, all sixteen values are architecture-defined, and the sixteen rows it
would otherwise need differ only in that nibble, so `role: imm`,
`kind: aarch64.cond`, `target_type: cond4` carries it with a `range` of
`0..15` and no `excluded` list (`EC-29`, ADR-0012). A `cond` of 16 is
`E-RANGE-001`, not a masked `0`: the low four bits of 16 are `eq`, a different
branch. The target is `imm19` field content, exactly as `bl`'s `imm26` is, so a
byte displacement is a `pcrel_begin` + `scale` fixup (`EXP-0014`).

The five load/store rows fix their addressing-kind bits in the template (bit 24
for the unsigned-offset rows, bits 11–10 for pre/post/unscaled) and leave one
`imm12` or `imm9` slot open, so the kind is the `form_id` and never an operand
value (`EC-14`, ADR-0013). `disp` is again the field, not the byte offset: the
two `imm12` rows count 8-byte units for these `size = 11` rows (`#16` is
`disp = 2`, `#32760` is `4095`) and the three `imm9` rows count signed bytes
(`-256 … 255`). A plan that states a byte offset on an `imm12` row therefore
addresses eight times too far without any error; `expected_digest` (`OD-01`) is
what catches that class of same-length defect, which is why the unit is stated
here rather than inferred. `align_bits` is `0` on both because the range check
applies to the field value (§4), not to a byte offset that was divided first.

The four `movz` rows are the fourth form-variant case and the first whose pinned
field is multi-bit. `hw` (bits 22–21) selects the 16-bit lane, the four values are
exactly the four `lsl #0/#16/#32/#48` spellings the assembler accepts, and the slot
holds `imm16` field content in `0…65535`: the value the instruction builds,
`imm16 << 16·hw`, belongs to the row (`EC-30`, ADR-0014). A pre-scaled literal such
as `0x12340000` on `-lsl16` is `E-RANGE-001` (`N18c`), and a lane the ISA does not
have (`-lsl8`) is `E-FORM-001` (`N01d`). `movk`, `movn`, the `w` variant and the
`mov` alias have no row: the first three differ in `opc`/`sf`, and the alias picks
its lane from the literal's value, which is `EC-16`.

The three shift rows are the fifth form-variant case, and the first where one
modifier spelling splits into a form and an operand. `shift` (bits 23–22) is the
keyword: three spellings, no numeric one, and `shift = 11` is unallocated in this
node. `imm6` (bits 15–10) is the amount: `0…63`, field content, one slot with
`align_bits = 0` because nothing is scaled. An amount of `64` is `E-RANGE-001`
(`N03-imm6`), and the same shift stated as a `modifiers` entry on `-lsl0` is
`E-OPERAND-003` (`N19`): a modifier is a guard and never writes a bit, so
accepting it would emit the unshifted word and report success.

The eight extend rows are the sixth form-variant case and the first where the
form fixes an operand's *width* as well as a field. `option` (bits 15–13) is the
keyword: six `[su]xt[bhw]` spellings consume a `w` register and two `[su]xtx`
spellings consume an `x` register, and the assembler rejects the cross pairings,
so the width has to be the row's (`src2` is `aarch64.gpr32`/`w32` on six rows and
`aarch64.gpr64`/`x64` on two). The encoded register is the same 5-bit number
either way, so a single row with a free `option` and a free register class would
emit a legal word for a plan the assembler refuses (`INV-07`, `EC-32`,
ADR-0016). `imm3` (bits 12–10) is the amount: the field is three bits, but
`add/sub` extended allocates only `0…4`, so the slot is `bits: 3` with
`excluded: [5, 6, 7]` (`ADR-0009`) — `8` is `E-RANGE-001` (`N03-imm3`) and `5` is
`E-RANGE-004` (`N16c`). `imm3 = 0` stays legal: the assembler prints `uxtb #0`
back as `uxtb`, the same word, so excluding it would make the value choose the
form. `sub`, `adds`/`subs` and the `sf = 0` node have no row (`N01f`).

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

`aarch64:add/x64-imm12-lsl12` is the same rule on an immediate: the slot holds
`imm12`, and the `sh = 1` the form fixes is what multiplies it by 4096. A
slot-level scale was rejected for the reason above — the same number would mean
different things on the `-lsl0` and `-lsl12` rows — and because it would be a
second carrier for a decision the `form_id` already names (`INV-02`, ADR-0011).

`movz`'s lane is the field-selected version of the same rule: `imm16` is the
field, `hw` is the exponent of the multiplier, and the four rows are the four
values of `hw`, so no slot has to carry `16 × hw` and no plan can state a lane the
instruction does not have (`EC-30`, ADR-0014, `EXP-0016` §2).

The shift amount is the plainest case of the same rule, with no multiplier at all:
`imm6` is the amount the plan states, `shift` is the keyword the row pins, and the
instruction applies the field directly (`EC-31`, ADR-0015, `EXP-0017` §2). The
extend amount is the same rule with a non-convex domain: `imm3` is the field, and
the three values beyond `4` are unallocated rather than out of range, so they are
`excluded` (`EC-32`, ADR-0016, `EXP-0018` §2).

RV64 follows the same rule with different shift amounts (ADR-0007, `EXP-0009`):
the source states `left_shift: 1` for `beq`/`jal` and `left_shift: 12` for
`auipc`, so a byte offset is a `scale` fixup with `transform_shift` 1 or 12,
while the slot keeps `align_bits: 0` and holds field content. The B- and J-type
slots have several placements each (`beq`: `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]`;
`jal`: `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]`), which is the scattered-field
case directive §6.3 item 6 asks for. `c.addi` needs `imm != 0` and `xd != 0`;
that is the `excluded` rule of §4, not a scaling rule, and §8.5 records it. The
extend rows' `imm3` is the same rule in §8.2: values `5`–`7` fit the field but are
unallocated, so they are excluded rather than scaled or clamped.

### 8.4 `rv64` `0.1.0`

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `riscv:add/rd-rs1-rs2` | `33000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]` | 4 | `RV-P1` |
| `riscv:addi/rd-rs1-imm12` | `13000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; src: `riscv.xreg`/`xreg` → `[15,5]`; imm: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P2` |
| `riscv:beq/rs1-rs2-imm12` | `63000000` | src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]`; target: `riscv.rel`/`imm12` → `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` | 4 | `RV-P4`, `RV-P6` |
| `riscv:jal/rd-imm20` | `6f000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; target: `riscv.rel`/`imm20` → `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]` | 4 | `RV-P5`, `RV-P6` |
| `riscv:auipc/rd-imm20` | `17000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; target: `riscv.rel`/`imm20` → `[12,20]` | 4 | `RV-P8` (field half) |
| `riscv:ld/rd-base-imm12` | `03300000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P3` |
| `riscv:sd/rs-base-imm12` | `23300000` | src: `riscv.xreg`/`xreg` → `[20,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[25,7]`, `[7,5]` | 4 | `RV-P3` |

The source is the pinned UDB resolved spec (ADR-0007), not a hand-written table.
`research/evidence/experiments/EXP-0010/generate_rv64.py` reads
`encoding.match` and each `encoding.variables[].location` from
`inst/I/{add,addi,beq,jal,auipc,ld,sd}.yaml`, turns every `location` into the
placements above, and refuses to emit unless every one of the 32 bits is covered
exactly once by a fixed bit or a slot placement and the bits `match` calls
variable are exactly the bits the placements own. `EXP-0009` §5 records the same
derivation; the table is its product.

`ld.yaml` and `sd.yaml` carry one `encoding:` block per xlen. The generator reads
the `RV64` block by name, because the `RV32` block states a `not:` list on `xd`
and `xs2` (the Zilsd pair rule) that the RV64 form does not have. Selecting the
block, rather than taking the first one, is what keeps a 32-bit legality rule out
of a 64-bit table.

The document declares `enabled_extensions: ["rv64i"]` because all seven nodes are
defined by the base `I` extension either unconditionally or under `xlen: 64`,
which the generator asserts per node. One set covers the whole document and is
compared exactly with the plan's (`01_contract.md` §4); the table is never
filtered per plan. A plan that enables a different set is `E-TARGET-001`, not
silently accepted.

That exact comparison is why `c.addi` is not a row here. Its node is
`definedBy: Zca`, and `ext/C.yaml` puts `Zca` in C's `requirements.allOf`, so it
needs `rv64c` enabled — which would change this document's extension set and
therefore its digest. `0.2.0` is that change (§8.5); `0.1.0` keeps its bytes and
its digest, and a plan that names `riscv:c.addi/rd-imm6` against `0.1.0` is
`E-FORM-001` (`N01c`).

The three immediate-bearing arithmetic forms are the scattered-field case:
`beq`'s 12-bit field is `imm[12]|imm[10:5]|imm[4:1]|imm[11]` over four
placements, `jal`'s 20-bit field is `imm[20]|imm[10:1]|imm[11]|imm[19:12]`, and
`auipc`'s field is contiguous. `sd` is scattered over two placements
(`[31,25]`, `[11,7]`), `ld` is contiguous. The placements are derived from the
source `location`, so no scatter is written by hand. The slots keep
`align_bits: 0` and hold field content; a byte offset is the fixup path with
`transform_shift` 1 (`beq`, `jal`) or 12 (`auipc`), as §8.3 requires. `RV-P8`'s
associated-reference half is deliberately absent: the psABI
`R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I` pairing is not in the encoding blocks
and is not yet pinned (ADR-0007 §Decision 9).

`ld`/`sd` are the memory slice, and they are decomposed into `base` + `disp`
rather than a composite payload (ADR-0008, `OD-13`): the base is a 5-bit
register field, the displacement is a 12-bit signed field, and a fixup covering
one does not cover the other. RV64 does not scale the load/store immediate, so
`disp` is the byte displacement and no transform is involved. `ld` has one form
because it has one encoding form; a later x86 or AArch64 memory slice will need
one `form_id` per addressing variant for the same reason.

`RV-P7` (`c.addi`) is not in this table for the extension-set reason above; it
is the first row of `0.2.0`.

### 8.5 `rv64` `0.2.0`

`0.2.0` contains every row of §8.4 unchanged, plus:

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `riscv:c.addi/rd-imm6` | `0100` | dest: `riscv.xreg`/`xreg` → `[7,5]` (excl 0); imm: `riscv.imm`/`imm6` → `[12,1]`, `[2,5]` (excl 0) | 2 | `RV-P7` |

The node is `inst/C/c.addi.yaml`; its `encoding.match` is `000-----------01`, so
the fixed word is `0x0001` and the file template is `0100` (little-endian). `imm`
is `location: "12|6-2"`, which is one bit at 12 plus five bits at 6–2, and `xd` is
`11-7`. Both variables carry `not: 0`, which the generator turns into the
`excluded: [0]` on each slot (ADR-0009). Encoding either zero would still produce
two bytes — `01 05` is `c.addi a0, 0x0` to `llvm-objdump`, and `05 00` is
`c.nop 0x1` — so the plan is rejected with `E-RANGE-004` (`N16a`, `N16b`) rather
than silently materialized as a HINT.

The document's `enabled_extensions` is `["rv64i","rv64c"]`. The generator asserts
the node's `definedBy.extension.name` (`Zca`) maps to a plan token through the
same table that produced §8.4's assertions; `ext/C.yaml` states the relation
(`C` requires `Zca`). A plan that pins `0.2.0` must declare exactly that set
(`E-TARGET-001` otherwise), and a plan that pins `0.1.0` never sees the form.

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
  §4.1 anticipated. `definitions/aarch64/0.1.0.json` … `0.7.0.json` now exist
  (§8.2); each is a superset that adds its own rows without a format change
  (ADR-0011, ADR-0012, ADR-0013, ADR-0014, ADR-0015, ADR-0016). What is missing is
  coverage, not design: neither the register-offset kind nor the literal load nor
  the store's `imm9` kinds has a row, and `sub`, `adds`/`subs` and the `w`-width
  rows of the arithmetic nodes are absent for the same reason.
- The archive is still not vendored and the drop is not a build input: a
  regeneration reads `research/external/arm-mrs/` after `tools/check_mrs.py`
  passes, and the shipped artifact is the JSON plus its digest.
- A slot has no scaling transform (§8.3). If a future slice needs an operand
  value that is *not* the field content, that is a format change with its own
  ADR, not a convention added here. The `-lsl12` immediate did not need one: the
  operand is field content and the shift belongs to the form. The load/store
  `imm12` rows are the same statement: the operand is the field and the
  access-size multiplier belongs to the ISA field, so a byte offset would need
  the format change ADR-0013 declined.
- `X86-P9` (explicit encoding family) stays deferred; no `/vex` or `/evex` row
  exists, so naming one is `E-FORM-001`.
