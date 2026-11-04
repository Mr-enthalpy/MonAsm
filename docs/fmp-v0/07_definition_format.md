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
| `definitions/x86_64/0.2.0.json` | `monasm.isa.x86` | `sha256:d9c088cacb9d20dcf8b801cbdb978996ed31d2e70b631897a905d179207991ac` |
| `definitions/aarch64/0.1.0.json` | `monasm.isa.aarch64` | `sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e` |
| `definitions/aarch64/0.2.0.json` | `monasm.isa.aarch64` | `sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed` |
| `definitions/aarch64/0.3.0.json` | `monasm.isa.aarch64` | `sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb` |
| `definitions/aarch64/0.4.0.json` | `monasm.isa.aarch64` | `sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78` |
| `definitions/aarch64/0.5.0.json` | `monasm.isa.aarch64` | `sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e` |
| `definitions/aarch64/0.6.0.json` | `monasm.isa.aarch64` | `sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964` |
| `definitions/aarch64/0.7.0.json` | `monasm.isa.aarch64` | `sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053` |
| `definitions/aarch64/0.8.0.json` | `monasm.isa.aarch64` | `sha256:9f82b566af004aaa9f0471151497d65acb45c3a7b46e4240345d21f4e330bc35` |
| `definitions/aarch64/0.9.0.json` | `monasm.isa.aarch64` | `sha256:99728cd9bd85b8b0768e700e15dd6263171d6261c385ac15ceeb5df6d2cafcff` |
| `definitions/aarch64/0.10.0.json` | `monasm.isa.aarch64` | `sha256:e958d69b4ba93222e7621a1f5c3ebd056ce929e2974a961a03abb7b66f0b247b` |
| `definitions/aarch64/0.11.0.json` | `monasm.isa.aarch64` | `sha256:c5a9aec943f9b195c400380b8416bf63cba944da3fdf0203f90de5baff295002` |
| `definitions/aarch64/0.12.0.json` | `monasm.isa.aarch64` | `sha256:8a428926568b99f0674785cc674bc066adc452216131706d458b9e3390da03b6` |
| `definitions/aarch64/0.13.0.json` | `monasm.isa.aarch64` | `sha256:d3876dd37a8441057b586312b3bee410e39594c64806b2c5c59960c06f9c7a5f` |
| `definitions/aarch64/0.14.0.json` | `monasm.isa.aarch64` | `sha256:a90ceac19824fbb00731e040346daa191973652e58522fab72336e24f769a5ba` |
| `definitions/aarch64/0.15.0.json` | `monasm.isa.aarch64` | `sha256:422ebb83b897b18e010da37539796b0b97cfc9018a47209fc4a6ddc5b14af5d3` |
| `definitions/aarch64/0.16.0.json` | `monasm.isa.aarch64` | `sha256:1e83c6cad91594e8315500f39d0bcffa235edc90c5f47c012555c077a8dbc457` |
| `definitions/aarch64/0.17.0.json` | `monasm.isa.aarch64` | `sha256:de2c53e1871f5c24f6af73082dcc402729786d2e6e2495f84e3ed553adb4e4ed` |
| `definitions/rv64/0.1.0.json` | `monasm.isa.riscv` | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` |
| `definitions/rv64/0.2.0.json` | `monasm.isa.riscv` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |

A plan names its `namespace`, `version` and digest in `definition_identity`.

### 8.1 `x86-64` `0.1.0` … `0.2.0`

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `x86:mov/rm-r64/legacy` | `4889c0` | dest: `x86.gpr64`/`rm64` → `[16,3]`; src: `x86.gpr64`/`r64` → `[19,3]` | 3 | `EC-27` |
| `x86:mov/r64-rm/legacy` | `488bc0` | dest: `x86.gpr64`/`r64` → `[19,3]`; src: `x86.gpr64`/`rm64` → `[16,3]` | 3 | `EC-27` |
| `x86:add/rm64-imm8/legacy` | `4883c000` | dest: `x86.gpr64`/`rm64` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | `EC-01` |
| `x86:add/rm64-imm32/legacy` | `4881c000000000` | dest: `x86.gpr64`/`rm64` → `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | `EC-01`, `EC-04` |
| `x86:add/rax-imm32/legacy` | `480500000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | `EC-04` |
| `x86:jmp/rel8/legacy` | `eb00` | target: `x86.rel`/`rel8` → `[8,8]` | 2 | `EC-03` |
| `x86:jmp/rel32/legacy` | `e900000000` | target: `x86.rel`/`rel32` → `[8,32]` | 5 | `EC-03` |
| `x86:mov/r64-riprel32/legacy` | `488b0500000000` | dest: `x86.gpr64`/`r64` → `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `EC-34`, `X86-P6` — `0.2.0`+ |
| `x86:mov/riprel32-r64/legacy` | `48890500000000` | src: `x86.gpr64`/`r64` → `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `EC-34`, `X86-P6` — `0.2.0`+ |

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

`0.2.0` adds the two RIP-relative rows. `mod = 00` and `r/m = 101` are template,
the destination/source is `ModRM.reg`, and `disp32` is the instruction's last
field. The displacement is a `target` operand with `kind: x86.rel`, not a `disp`,
because the form has no base register: RIP is not in `x86.gpr64` and no slot
carries it (`ADR-0027`). A symbol reference uses `pcrel_end` with `addend = 0`;
the measured `L1` at `0x20` with the instruction at offset `7` gives
`12 00 00 00` (`EXP-0029` §4). Base+disp8/disp32, SIB shapes, the `0x67`
address-size prefix and `moffs` remain absent.

### 8.2 `aarch64` `0.1.0` … `0.17.0`

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
| `aarch64:str/x64-base-imm9-pre` | `000c00f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P15` |
| `aarch64:str/x64-base-imm9-post` | `000400f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P15` |
| `aarch64:stur/x64-base-imm9` | `000000f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P15` |
| `aarch64:ldr/x64-imm19` | `00000058` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; target: `aarch64.rel`/`imm19` → `[5,19]` | 4 | `EC-15`, `A64-P16` |
| `aarch64:movz/x64-imm16-lsl0` | `000080d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl16` | `0000a0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl32` | `0000c0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl48` | `0000e0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movk/x64-imm16-lsl0` | `000080f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movk/x64-imm16-lsl16` | `0000a0f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movk/x64-imm16-lsl32` | `0000c0f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movk/x64-imm16-lsl48` | `0000e0f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl0` | `00008092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl16` | `0000a092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl32` | `0000c092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl48` | `0000e092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
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
| `aarch64:sub/x64-x64-x64-lsl0` | `000000cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-imm12-lsl0` | `000000d1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-imm12-lsl12` | `000040d1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-x64-x64-imm6-lsl` | `000000cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-x64-x64-imm6-lsr` | `000040cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-x64-x64-imm6-asr` | `000080cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P10` — `0.8.0` only |
| `aarch64:adds/x64-x64-x64-lsl0` | `000000ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-imm12-lsl0` | `000000b1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-imm12-lsl12` | `000040b1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-x64-x64-imm6-lsl` | `000000ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-x64-x64-imm6-lsr` | `000040ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-x64-x64-imm6-asr` | `000080ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-lsl0` | `000000eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-imm12-lsl0` | `000000f1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-imm12-lsl12` | `000040f1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-imm6-lsl` | `000000eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-imm6-lsr` | `000040eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-imm6-asr` | `000080eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:add/w32-w32-w32-lsl0` | `0000000b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:add/w32-w32-w32-imm6-lsl` | `0000000b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:add/w32-w32-w32-imm6-lsr` | `0000400b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:add/w32-w32-w32-imm6-asr` | `0000800b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:add/w32-imm12-lsl0` | `00000011` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:add/w32-imm12-lsl12` | `00004011` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-lsl0` | `0000004b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-imm6-lsl` | `0000004b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-imm6-lsr` | `0000404b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-imm6-asr` | `0000804b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:sub/w32-imm12-lsl0` | `00000051` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:sub/w32-imm12-lsl12` | `00004051` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-lsl0` | `0000002b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-imm6-lsl` | `0000002b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-imm6-lsr` | `0000402b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-imm6-asr` | `0000802b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:adds/w32-imm12-lsl0` | `00000031` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:adds/w32-imm12-lsl12` | `00004031` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-lsl0` | `0000006b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-imm6-lsl` | `0000006b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-imm6-lsr` | `0000406b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-imm6-asr` | `0000806b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:subs/w32-imm12-lsl0` | `00000071` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:subs/w32-imm12-lsl12` | `00004071` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:sub/x64-x64-w32-imm3-uxtb` | `000020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-uxth` | `002020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-uxtw` | `004020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-x64-imm3-uxtx` | `006020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-sxtb` | `008020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-sxth` | `00a020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-sxtw` | `00c020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-x64-imm3-sxtx` | `00e020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-uxtb` | `000020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-uxth` | `002020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-uxtw` | `004020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-x64-imm3-uxtx` | `006020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-sxtb` | `008020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-sxth` | `00a020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-sxtw` | `00c020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-x64-imm3-sxtx` | `00e020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-uxtb` | `000020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-uxth` | `002020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-uxtw` | `004020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-x64-imm3-uxtx` | `006020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-sxtb` | `008020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-sxth` | `00a020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-sxtw` | `00c020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-x64-imm3-sxtx` | `00e020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:cmp/x64-x64-lsl0` | `1f0000eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-imm6-lsl` | `1f0000eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-imm6-lsr` | `1f0040eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-imm6-asr` | `1f0080eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-imm12-lsl0` | `1f0000f1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-imm12-lsl12` | `1f0040f1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-lsl0` | `1f00006b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-imm6-lsl` | `1f00006b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-imm6-lsr` | `1f00406b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-imm6-asr` | `1f00806b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-imm12-lsl0` | `1f000071` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-imm12-lsl12` | `1f004071` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtb` | `1f0020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-uxth` | `1f2020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtw` | `1f4020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-x64-imm3-uxtx` | `1f6020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtb` | `1f8020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-sxth` | `1fa020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtw` | `1fc020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-x64-imm3-sxtx` | `1fe020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-lsl0` | `1f0000ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-imm6-lsl` | `1f0000ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-imm6-lsr` | `1f0040ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-imm6-asr` | `1f0080ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-imm12-lsl0` | `1f0000b1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-imm12-lsl12` | `1f0040b1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-lsl0` | `1f00002b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-imm6-lsl` | `1f00002b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-imm6-lsr` | `1f00402b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-imm6-asr` | `1f00802b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-imm12-lsl0` | `1f000031` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-imm12-lsl12` | `1f004031` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtb` | `1f0020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-uxth` | `1f2020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtw` | `1f4020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-x64-imm3-uxtx` | `1f6020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtb` | `1f8020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-sxth` | `1fa020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtw` | `1fc020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-x64-imm3-sxtx` | `1fe020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:ldr/x64-base-regoff-lsl0` | `006860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-lsl3` | `007860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-uxtw0` | `004860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-uxtw3` | `005860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtw0` | `00c860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtw3` | `00d860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtx0` | `00e860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtx3` | `00f860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-lsl0` | `006820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-lsl3` | `007820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-uxtw0` | `004820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-uxtw3` | `005820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtw0` | `00c820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtw3` | `00d820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtx0` | `00e820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtx3` | `00f820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/w32-base-regoff-lsl0` | `006860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-lsl2` | `007860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-uxtw0` | `004860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-uxtw2` | `005860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtw0` | `00c860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtw2` | `00d860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtx0` | `00e860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtx2` | `00f860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-lsl0` | `006820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-lsl2` | `007820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-uxtw0` | `004820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-uxtw2` | `005820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtw0` | `00c820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtw2` | `00d820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtx0` | `00e820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtx2` | `00f820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |

`0.1.0` holds the first, second, fourth and fifth rows; `0.2.0` adds
`aarch64:add/x64-imm12-lsl12` (ADR-0011); `0.3.0` repeats all five and adds
`aarch64:b.cond/imm19` (ADR-0012); `0.4.0` repeats all six and adds the five
load/store rows (ADR-0013); `0.5.0` repeats all eleven and adds the four `movz`
rows (ADR-0014); `0.6.0` repeats all fifteen and adds the three shift rows
(ADR-0015); `0.7.0` repeats all eighteen and adds the eight extend rows
(ADR-0016); `0.8.0` repeats all twenty-six and adds the six `sub` rows (ADR-0017);
`0.9.0` repeats all thirty-two and adds the twelve `adds`/`subs` rows (ADR-0018);
`0.10.0` repeats all forty-four and adds the twenty-four `w` rows (ADR-0019);
`0.11.0` repeats all sixty-eight and adds the twenty-four extended
`sub`/`adds`/`subs` rows (ADR-0020); `0.12.0` repeats all ninety-two and adds the
forty `cmp`/`cmn` alias rows (ADR-0021); `0.13.0` repeats all one hundred and
thirty-two and adds the three store `imm9` rows (ADR-0022); `0.14.0` repeats all
one hundred and thirty-five and adds the literal load row (ADR-0023); `0.15.0`
repeats all one hundred and thirty-six and adds the sixteen register-offset rows
(ADR-0024); `0.16.0` repeats all one hundred and fifty-two and adds the sixteen
32-bit register-offset rows (ADR-0025); `0.17.0` repeats all one hundred and
sixty-eight and adds the eight `movk`/`movn` rows (ADR-0026).
Each document therefore shares its earlier rows
unchanged and differs only in the rows its version introduced, so a plan bound to
an older version cannot reach a newer form (`E-FORM-001`, `N01`) even though the
newest document has it.

The templates are little-endian file order, so `0000008b` is the word
`0x8b000000` in a disassembler. The generator
(`research/evidence/experiments/EXP-0008/generate_aarch64.py`) derives every
bit from the MRS node, requires the MRS node name to exist, and refuses to emit
unless all 32 bits are covered exactly once by a fixed bit or a slot placement;
`EXP-0008` §2–§3 records the nodes and the coverage check. The one hundred and
seventy-six forms come
from thirty-nine encode nodes: `ADD_64_addsub_shift` is read four times, once with `imm6`
pinned to 0 and once per shift keyword, `ADD_64_addsub_ext` eight times, once per
`option` value, `ADD_64_addsub_imm` twice, once with
`sh = 0` and once with `sh = 1`, `MOVZ_64_movewide` four times, once per `hw`
value, `MOVK_64_movewide` and `MOVN_64_movewide` four times each, once per `hw`
value (`ADR-0026`), `SUB_64_addsub_shift` four times and `SUB_64_addsub_imm` twice, each once
per row it shares with the `add` half (`ADR-0017`), `ADDS_64_addsub_shift` and
`SUBS_64_addsub_shift` four times each, `ADDS_64S_addsub_imm` and
`SUBS_64S_addsub_imm` twice each (`ADR-0018`), the eight `*_32*` nodes four times
(shifted) or twice (immediate) each on the same pattern (`ADR-0019`),
`SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext` eight times
each, once per `option` value (`ADR-0020`),
`B_only_condbranch` contributes one row with both of its variable
fields as operands, and each of the eight load/store rows reads one node whose
addressing-kind bits are fixed and whose `imm12`/`imm9` is the single variable
field (`ADR-0022` adds the three store `imm9` nodes); `LDR_64_loadlit` is the one
node with no base register, and its `imm19` is the single variable field
(`ADR-0023`); `LDR_64_ldst_regoff` and `STR_64_ldst_regoff` are each read eight
times, once per `option`/`S` pair (`ADR-0024`), and the 32-bit pair
`LDR_32_ldst_regoff`/`STR_32_ldst_regoff` eight times each on the same pattern
(`ADR-0025`); the ten `CMP`/`CMN` alias
nodes are read for verification only, because
they carry no `encoding` and the bytes stay the base node's (`ADR-0021`). The
generator states each pinned value explicitly and asserts that `0.1.0` … `0.15.0`
still hash to their frozen digests.

The literal row's `imm19` follows §8.3's rule, not a slot transform: the slot is
the field, so `{ "value": 1 }` loads from `PC + 4`, and a byte displacement is
the `pcrel_begin` + `scale(2)` fixup with `align_bits: 2`. That is the same
shape as `bl`'s `imm26` and `b.cond`'s `imm19`, and it is why the row's only
difference from a branch row is that the destination is a register and the
target is not a branch: `aarch64:ldr/x64-imm19` has no `base` slot because the
MRS node has no `Rn`.

The `-lsl0`/`-lsl12` suffix on the `add`, `sub`, `adds` and `subs` rows carries a
decision the operand list does not state, and the name states it instead
(`01_contract.md` §7, `ADR-0004`, ADR-0017, ADR-0018):
the MRS leaves AArch64 `shift` (2 bits) and `imm6` (6 bits) variable in the
shifted-register node, and `sh` (1 bit) variable in the immediate node. This
table pins `shift` to `LSL` and `imm6` to 0 in the plain register row, and pins
`sh` to `0` or `1` in the two immediate rows. The shift *keyword* is a decision;
the shift *amount* is not: `-imm6-lsl`/`-imm6-lsr`/`-imm6-asr` pin `shift` and
leave `imm6` open as a `0…63` operand on the `x64-…` rows (`0…31` on the
`w32-…` ones, below), so `add x0, x1, x2, lsl #4` is
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
because the operand is field content, not the shifted literal. The six `sub` rows
repeat both rules with `op = 1` (`ADR-0017`): `-lsl0`/`-lsl12` behave exactly as
`add`'s two rows do, and a literal outside the named half is `E-RANGE-001`
(`N18d`), even though `llvm-mc` re-encodes `sub x0, x1, #0x1000` without a
diagnostic (`EXP-0019` §2). The twelve `adds`/`subs` rows repeat it once more
with `S = 1` (`ADR-0018`): the same two `sh` halves and the same three keywords,
and `0x1000` on `adds/x64-imm12-lsl0` is `E-RANGE-001` (`N18e`) even though
`llvm-mc` re-encodes it (`EXP-0020` §2).

The twenty-four `w` rows repeat all of those rules on the `sf = 0` nodes
(`ADR-0019`), with one slot-level difference. Every register slot is
`aarch64.gpr32`/`w32`, so an `x64` operand is `E-OPERAND-001` on `kind` and
`target_type` (`N02c`); register 31 stays a plain `reg_number` whose meaning is
the node's role, and no `sp` operand kind exists. `sh`, the shift keyword and
`imm12` behave exactly as on the `x64` rows, so `4096` on
`adds/w32-imm12-lsl0` is `E-RANGE-001` (`N18f`). The `imm6` slot is the
difference: the field is six bits wide but the 32-bit instruction allocates only
`0…31` (`lsl #32` is rejected, the `imm6 = 32` word does not decode), so the
slot declares `bits: 6` and `excluded: [32 … 63]`; `imm6 = 32` is
`E-RANGE-004` (`N16d`), never a truncated shift (`EXP-0021` §2).

The twenty-four `sub`/`adds`/`subs` extended rows repeat the `0.7.0` extend rows
on the three nodes that fix `op` at bit 30 and/or `S` at bit 29 (`ADR-0020`).
The slots are identical to `add`'s: the keyword pins `option` at 13+3 and fixes
`src2`'s width, and `imm3` is `[10,3]` with `excluded: [5, 6, 7]`. Register 31 is
again a plain `reg_number` — `sp` in `sub`'s `Rd`, `xzr` in `adds`/`subs` `Rd` —
because the node's role supplies the meaning, not the slot (`EXP-0022` §2). The
four `sf = 0` extended nodes have no row, so `sub w0, w1, w2, uxtb` is
`E-FORM-001` (`N01l`).

The forty `cmp`/`cmn` alias rows are the same words as the `subs`/`adds` rows with
`Rd` at 31 and the destination dropped (`ADR-0021`). Each is the base row with
`dest` removed and `Rd` pinned, so its slots are `src`, `src2` or `imm`, and the
inherited `imm6`/`imm3`/`imm12` shapes; the shift and immediate rules transfer per
width, and the `w32` `imm6` rows carry the `32…63` tail. The alias node is the
check, not the source: it has no `encoding`, its `operation_id` names the base
node, and its `condition` is `Rd == '11111'`. A plan that names a `cmp`/`cmn` row
and also passes `dest` is `E-OPERAND-002` (`N02e`); the 32-bit extended alias rows
stay out while their base rows do (`N01l`).

`aarch64:b.cond/imm19` is the one row whose *condition* is an operand. `cond` is a
4-bit field, all sixteen values are architecture-defined, and the sixteen rows it
would otherwise need differ only in that nibble, so `role: imm`,
`kind: aarch64.cond`, `target_type: cond4` carries it with a `range` of
`0..15` and no `excluded` list (`EC-29`, ADR-0012). A `cond` of 16 is
`E-RANGE-001`, not a masked `0`: the low four bits of 16 are `eq`, a different
branch. The target is `imm19` field content, exactly as `bl`'s `imm26` is, so a
byte displacement is a `pcrel_begin` + `scale` fixup (`EXP-0014`).

The eight offset rows fix their addressing-kind bits in the template (bit 24
for the unsigned-offset rows, bits 11–10 for pre/post/unscaled) and leave one
`imm12` or `imm9` slot open, so the kind is the `form_id` and never an operand
value (`EC-14`, ADR-0013, ADR-0022). `disp` is again the field, not the byte
offset: the two `imm12` rows count 8-byte units for these `size = 11` rows
(`#16` is `disp = 2`, `#32760` is `4095`) and the six `imm9` rows count signed
bytes (`-256 … 255`). The three store `imm9` rows are the load rows' layouts
with `opc = 00` and `Rt` as the stored register, so the family is symmetric:
every addressing kind the MRS drop carries now has a row, with register offset
the last one added (`ADR-0024`, below). `LDR_64_loadlit` is the ninth member and
the only one with no `Rn`: bits 11–10 and bit 21 are not fields there, so no
kind question arises, and its single variable field is `imm19` in 4-byte units
(`ADR-0023`). A plan that states a byte offset on
an `imm12` row therefore
addresses eight times too far without any error; `expected_digest` (`OD-01`) is
what catches that class of same-length defect, which is why the unit is stated
here rather than inferred. `align_bits` is `0` on both because the range check
applies to the field value (§4), not to a byte offset that was divided first.

The sixteen register-offset rows are the only form-variant case whose variant is
two bit fields rather than a keyword, and they close the load/store family.
`option` (bits 15–13) fixes which register the row consumes as the index and how
it extends it: `011`
`lsl` and `111` `sxtx` take an `x` register, `010` `uxtw` and `110` `sxtw` take a
`w`, and the assembler rejects the cross pairings (`ldr x0, [x1, x2, uxtw]`,
`ldr x0, [x1, w2, lsl #3]`), so `index` is `aarch64.gpr64`/`x64` on four rows and
`aarch64.gpr32`/`w32` on four. `S` (bit 12) is whether the index is scaled by the
access size: `0` is the bare spelling or `#0`, `1` is `#3` on these `size = 11`
rows, so the scale is a form bit and never an operand (`INV-02`, `EC-14`,
ADR-0024). `Rm` is the `index` slot at `[16,5]`; `Rn` and `Rt` keep the
`base`/`dest`/`src` roles of the offset rows, and register 31 is again a plain
`reg_number` — `sp` in `Rn`, `xzr`/`wzr` in `Rm`. `lsl #1` and `lsl #4` have no
row: only `#0` and `#3` are encodable on a 64-bit access, and `N01q` names the
`#1` spelling. The other four `option` values (`000`, `001`, `100`, `101`) are
unallocated, so no spelling reaches them and no row needs to exclude them. Bit
21 is `1` in both templates, which is why `ldur x0, [x1, x2]` is not this kind:
the assembler reads it as an unscaled offset and demands an integer. Register
offset has no writeback variant either: `ldr x0, [x1, x2, lsl #3]!` is rejected
(`EXP-0026` §2), so there is no pre/post row to add here.

The sixteen 32-bit register-offset rows (`ADR-0025`) are the same decision one
`size` down: `LDR_32_ldst_regoff`/`STR_32_ldst_regoff` fix `size = 10` and
`opc = 01`/`00`, so the template's top bits change and `S = 1` now means `#2` on
these 4-byte accesses. `option` keeps its keyword/width pairing from the 64-bit
rows, and only `Rt` changes class: `dest`/`src` are `aarch64.gpr32`/`w32` while
`base` and the two `x` index rows stay `aarch64.gpr64`/`x64`. The suffix states
the amount (`-lsl0` … `-sxtx2`), so `-lsl1` and `-lsl3` are names for nothing at
this width (`E-FORM-001`, `N01s`), and the same modifier rule holds: `lsl #2` as
a `modifiers` entry on the `index` is `E-OPERAND-003` (`N19c`).

The move-wide rows are the fourth form-variant case and the first whose pinned
field is multi-bit; `0.17.0` brings them to twelve. `hw` (bits 22–21) selects the 16-bit lane, the four values are
exactly the four `lsl #0/#16/#32/#48` spellings the assembler accepts, and the slot
holds `imm16` field content in `0…65535`: the value the instruction builds,
`imm16 << 16·hw`, belongs to the row (`EC-30`, ADR-0014). A pre-scaled literal such
as `0x12340000` on `-lsl16` is `E-RANGE-001` (`N18c`, `N18g`), and a lane the ISA
does not have (`-lsl8`) is `E-FORM-001` (`N01d`, `N01t`). `0.17.0` adds the same
four lanes for `movk` and `movn`, whose `MOVK_64_movewide`/`MOVN_64_movewide`
nodes fix `opc` to `11`/`00`, so the mnemonic is the node and never an operand
(`EC-16`, ADR-0026). `movn` stores the raw `imm16` field: the complement is the
instruction's operation, not a plan-side computation, so `movn x0, #0x1234` is
`0x92824680` with `imm16 = 0x1234`. The `w` (`sf = 0`) lanes and the `mov` alias
have no row: the first is a different node, and the alias picks its operation and
lane from the literal's value, which is `EC-16` (`N01w`).

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
form. The extended `sub` node and the extended `adds`/`subs` nodes, the `sf = 0`
nodes and the `cmp`/`cmn` aliases have no row (`N01f`, `N01h`, `N01i`, `N01j`);
the shifted and immediate `sub` nodes are rows in `0.8.0` and their `S = 1` twins
are rows in `0.9.0` (§8.2, ADR-0017, ADR-0018). Register 31 in those rows is
`xzr`: `sub sp, …` and `adds x0, sp, x2` are the extended node, so they are not
reachable through these rows. `N01g` names `subs` against `0.8.0`, which predates
the rows.

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
instruction does not have (`EC-30`, ADR-0014, `EXP-0016` §2). `movk` and `movn`
reuse the same four lanes; their `opc` comes from the node, so the mnemonic adds
no field to the operand list (`ADR-0026`, `EXP-0028` §2).

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
  §4.1 anticipated. `definitions/aarch64/0.1.0.json` … `0.17.0.json` now exist
  (§8.2); each is a superset that adds its own rows without a format change
  (ADR-0011 to ADR-0026). What is
  missing is coverage, not design: the `b`/`h` load/store widths, the signed and
  extended load rows (`LDRSW`/`LDRSB`/`LDRSH`), `prfm`, the 32-bit
  extended `add`/`sub` nodes and their aliases, and the `mov` alias and the
  32-bit move-wide lanes have no row. Each is `E-FORM-001` until
  a slice adds it.
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
