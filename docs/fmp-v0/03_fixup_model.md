# Fixup Model

Status: **draft**. This document defines how a planned patch is expressed and
executed. It is deliberately more general than "write a 32-bit value at an
offset".

## 1. Separated concepts

| Concept | Question it answers | Where it lives |
|---|---|---|
| Symbol identity | Which symbol is this, independent of name? | `symbol_id` |
| Symbol definition | Where is it, if it exists here? | `section_id` + `offset` |
| Symbol reference | Which symbol does this patch mention? | `fixup.target.symbol_id` |
| Fixup site | Where are the bits to change? | `section_id` + `offset` |
| Field descriptor | Which bits, and in what order? | `field_descriptor` |
| Fixup kind | What computation is performed? | `pc_reference_rule` + `value_transform` |
| Relocation representation | How is an unresolved patch recorded? | `resolution_mode` + output contract |
| Resolution policy | What happens if the value is unknown? | `resolution_mode` |

Collapsing any two of these is the classic source of "the assembler resolved it
for me" bugs.

## 2. `FixupPlan`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `fixup_id` | yes | Unique id | Deterministic ordering and diagnostics | Record order becomes unstable. | frozen |
| `section_id` | yes | Section of the site | Locates the bytes | Cross-section patches need an address model. | frozen |
| `offset` | yes | Byte offset of the site within the section | Exact patch location | One byte of drift corrupts the instruction. | frozen |
| `field_descriptor` | yes | Ordered list of `{lsb, width}` bit ranges relative to `offset`, plus `bit_order` | Some fields are split across the instruction | RISC-V B-type immediate is split into `imm[12\|10:5]` and `imm[4:1\|11]`; a contiguous write cannot express it. | frozen |
| `target` | yes | `{kind: symbol \| absolute \| section_relative, ...}` | The value source | An absolute patch with no target is a silent zero. | frozen |
| `addend` | yes | Signed integer, explicit, even when zero | REL and RELA differ in where the addend lives | Inferring the addend from the field's current contents makes output depend on prior bytes. | frozen |
| `pc_reference_rule` | yes | `none` \| `pcrel_begin` \| `pcrel_end` \| `pcrel_page` \| `definition:<id>` | `P` is not universal | x86 uses the end of the instruction; RISC-V branches use the instruction address. | frozen |
| `value_transform` | yes | `identity`, `scale(shift)`, `page`, `hi20`, `lo12_i`, `lo12_s`, `pcrel_hi20`, … | Encodes range and scaling semantics | AArch64 page/scaled immediates are not plain displacements. | frozen |
| `range_constraint` | yes | `{signed, bits, align_bits}` | Determines legality, not just formatting | A rel8 with a 200-byte target must be rejected, not truncated. | frozen |
| `resolution_mode` | yes | `resolve_in_place` \| `emit_relocation` \| `reject_if_unresolved` | Distinguishes "patch now" from "record for a linker" | Emitting bytes without a relocation record loses the reference silently. | frozen |
| `pair_group` | no | Id shared by associated fixups | Some patches only make sense as a pair | `adrp`+`add` and `auipc`+`addi` are pairs; applying one alone yields a wrong address. | frozen |
| `pair_role` | no | `hi` \| `lo` | Selects the member's transform | Swapping roles produces a plausible but wrong address. | frozen |
| `overwrite_bytes` | yes | Boolean, MUST be false in v0 | Prevents template-style patching from hiding encoding decisions | A plan that writes raw bytes then patches them is scheme C (OD-01). | draft |

## 3. Field descriptors

```json
{ "offset": 12,
  "field_descriptor": [
    { "lsb": 31, "width": 1 },
    { "lsb": 25, "width": 6 },
    { "lsb": 8,  "width": 4 },
    { "lsb": 7,  "width": 1 }
  ],
  "bit_order": "value_msb_first" }
```

Rules:

- `field_descriptor` entries are in **value order**: the first entry receives the
  most significant bits of the value when `bit_order` is `value_msb_first`.
- `lsb` is relative to the instruction's first byte in the section, not to the
  plan's byte buffer.
- `width` is in bits; bits MUST lie inside the instruction's `expected_size`.
- Overlapping descriptors within one fixup are rejected (`E-FIXUP-005`).
- Overlapping fixups in the same byte are rejected (`E-FIXUP-006`).
- Bits not covered by any descriptor are left untouched; the encoder, not the
  fixup, produced them.

## 4. `pc_reference_rule`

`P` is the reference point used to compute the displacement. It is never
defaulted.

| Rule | `P` | Used by |
|---|---|---|
| `none` | not applicable | absolute patches |
| `pcrel_begin` | address of the fixup site | RISC-V B-type and J-type, AArch64 `b`/`bl` |
| `pcrel_end` | address immediately after the instruction that contains the site | x86-64 `rel32` |
| `pcrel_page` | page base of `P` | AArch64 `adrp` |

For `pcrel_end` the containing instruction is found through the section's
fragments, not by arithmetic on the site offset: the site may sit several bytes
into the instruction (x86 `rel32` starts at byte 1), so "site + size" would be
wrong by exactly that much. An earlier draft of this table said that; it was
fixed after `EXP-0002` §6.1 exposed the off-by-one.

A definition MAY declare additional named rules (`definition:<id>`), but the
string must be resolved by the pinned definition, never by convention.

## 5. Resolution modes

| Mode | Behavior when the target is known | Behavior when unknown |
|---|---|---|
| `resolve_in_place` | compute, range-check, write bits | reject `E-FIXUP-002` |
| `emit_relocation` | optionally write a resolved value, and emit a record | emit a record with the declared addend; if the output contract cannot carry it, reject `E-FIXUP-004` |
| `reject_if_unresolved` | compute and write | reject `E-FIXUP-002` |

"Record a relocation" and "resolve a symbol" are different operations. A plan
that says `emit_relocation` MUST NOT be silently resolved into bytes with no
record.

## 6. Target-specific semantics (v0 candidates)

| Case | Encoding facts | What the plan must pin |
|---|---|---|
| x86-64 `rel32` | `R_X86_64_PC32`-style: value = `S + A - P`, `P` = end of instruction | `pc_reference_rule = pcrel_end`, range `i32` |
| x86-64 PLT/GOT | semantics depend on link-time policy | v0: `E-FIXUP-004` unsupported; see OD-02 |
| AArch64 `b`/`bl` | imm26, signed, scaled by 4, `P` = instruction address, ±128 MB | `pcrel_begin`, `scale(2)`, `range.bits = 26`, `align_bits = 2` |
| AArch64 `adrp` | immhi:immlo = `(page(S+A) - page(P)) >> 12`, signed 21 bits | `pcrel_page`, `value_transform = page`, pair `hi` |
| AArch64 `add :lo12:` | imm12 = `(S+A) & 0xFFF`, optional `lsl #12` | `value_transform = lo12_i`, pair `lo`, same `pair_group` |
| RV64 B-type | imm12…imm1 scattered; `P` = instruction address; ±4 KiB, 2-byte aligned | `pcrel_begin`, `range.bits = 12`, `align_bits = 1` |
| RV64 J-type (`jal`) | imm20…imm1 scattered; ±1 MiB | `pcrel_begin`, `range.bits = 20`, `align_bits = 1` |
| RV64 `auipc` hi20 | `hi20 = (S + A + 0x800) >> 12`, relative to the `auipc` PC | pair `hi`, `pcrel_hi20` |
| RV64 `addi` lo12 | `lo12 = (S + A)` sign-extended 12 bits | pair `lo`, same `pair_group`, references the **auipc** site |

The RISC-V `%pcrel_lo` semantics are the sharpest case: the low fixup references
the *high instruction*, not the symbol directly, because the linker needs the
paired PC. A model that only stores "symbol + addend" cannot express it. This is
AC-05's associated-relocation requirement.

### 6.1 Observed in an object file (EXP-0002 §6.2)

`llvm-readobj --relocations` on hand-written sources produces:

```text
x86-64   call ext                 0x1 R_X86_64_PLT32            ext  -4
AArch64  adrp x0, ext             0x0 R_AARCH64_ADR_PREL_PG_HI21 ext  0
         add  x0, x0, :lo12:ext   0x4 R_AARCH64_ADD_ABS_LO12_NC  ext  0
RV64     auipc a0, %pcrel_hi(ext) 0x0 R_RISCV_PCREL_HI20        ext  0
         addi  a0, a0, %pcrel_lo(.L0)
                                  0x4 R_RISCV_PCREL_LO12_I      .L0  0
```

Three facts this pins down:

1. **RISC-V's low half names the `auipc` site, not the target.** `.L0` is a local
   symbol in `.text` at the `auipc` offset (`llvm-readobj --symbols`), and the
   relocation's symbol field is that label. The pair relation is therefore
   load-bearing, not cosmetic.
2. **AArch64 and RISC-V differ in spelling, not in model.** AArch64's low half
   names `ext`; RISC-V's names `.L0`. Storing `pair_group` + `pair_role` covers
   both, because the relation is stored instead of inferred from the symbol.
3. **x86's `-4` is the ELF spelling of `pcrel_end` with `addend = 0`.** ELF
   writes `S + A - P` with `P` at the displacement field; the plan writes `P`
   after the instruction and leaves `A` at zero. The two are the same value.

Consequence for output level (`OD-03`): a Level 0 record expresses all three
shapes directly. A Level 1 emitter for RISC-V would have to synthesize a local
symbol per `hi` site to fill the relocation, which is extra state, not extra
information.

## 7. Pairing rules

- Every fixup with `pair_group` MUST have exactly one `hi` and one `lo` member
  (`E-FIXUP-007`, N12).
- Both members MUST reference the same logical target.
- The `lo` member's `section_id`/`offset` MUST be a valid site inside the same
  output; its `offset` MAY be in a different section only if the definition
  allows it.
- Membership and roles are data. The materializer never infers a pair from
  adjacency, ordering, or symbol names.

## 8. REL vs RELA

- v0 always carries an explicit `addend` in the plan.
- For REL-style output, the materializer writes the addend into the field.
- For RELA-style output, the materializer emits the addend in the record and
  writes zero (or the resolved value) according to the output contract.
- The choice of REL/RELA belongs to `output_contract`, never to the plan's
  convenience.

## 9. Execution order and determinism

1. Validate all fixups statically (site, overlap, descriptor bounds, pairing).
2. Compute `S`, `P`, `A`, apply `value_transform`, apply `pc_reference_rule`.
3. Range-check after transform, before writing (`E-FIXUP-003`).
4. Write masked bits.
5. Emit records in `(section_id, offset, fixup_id)` order.

Steps 2–4 MUST be independent of iteration order. Because overlap is rejected,
the masked writes commute; the check exists so that this stays true.

## 10. Out of scope for v0 (with rejection tests)

- GOT/PLT/TLS and other link-time-policy relocations → `E-FIXUP-004`.
- Relaxation of any kind, including "convert `jal` to `c.j` to fit".
- Implicit addend extraction from existing bytes.
- Symbol preemption or visibility policy.

Each exclusion needs a negative fixture that must be rejected, per AC-05.
