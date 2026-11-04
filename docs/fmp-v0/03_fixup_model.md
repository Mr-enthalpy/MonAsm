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
| Relocation representation | How is an unresolved patch recorded? | `resolution_mode` + the one record shape `fmp/0.1` defines (§8) |
| Resolution policy | What happens if the value is unknown? | `resolution_mode` |

Collapsing any two of these is the classic source of "the assembler resolved it
for me" bugs.

## 2. `FixupPlan`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `fixup_id` | yes | Unique id | Deterministic ordering and diagnostics | Record order becomes unstable. | frozen |
| `section_id` | yes | Section of the site | Locates the bytes | Cross-section patches need an address model. | frozen |
| `offset` | yes | Byte offset of the site within the section | Exact patch location | One byte of drift corrupts the instruction. | frozen |
| `field_descriptor` | yes | Ordered list of `{lsb, width}` bit ranges relative to `offset`, most significant value bits first | Some fields are split across the instruction | RISC-V B-type immediate is split into `imm[12\|10:5]` and `imm[4:1\|11]`; a contiguous write cannot express it. | frozen |
| `target` | yes | `{kind: symbol \| absolute \| section_relative, ...}` | The value source | An absolute patch with no target is a silent zero. | frozen |
| `addend` | yes | Signed integer, explicit, even when zero | The addend is part of the computed value; `fmp/0.1` records are RELA-shaped so it is never read from the field | Inferring the addend from the field's current contents makes output depend on prior bytes, and a zero field becomes indistinguishable from a deliberate addend. | frozen |
| `pc_reference_rule` | yes | `none` \| `pcrel_begin` \| `pcrel_end` \| `pcrel_page` \| `pcrel_hi` \| `definition:<id>` | `P` is not universal | x86 uses the end of the instruction; RISC-V branches use the instruction address; an RV64 `lo` half uses its paired `hi`'s address, which is neither. | frozen |
| `value_transform` | yes | `identity`, `scale(shift)`, `page`, `hi20`, `lo12_i`, `lo12_s`, `pcrel_hi20`, `pcrel_lo12`, … | Encodes range and scaling semantics | AArch64 page/scaled immediates are not plain displacements; an absolute low 12 bits and a paired low 12 bits differ whenever the `hi` is not page-aligned. | frozen |
| `range_constraint` | yes | `{signed, bits, align_bits}` | Determines legality, not just formatting | A rel8 with a 200-byte target must be rejected, not truncated. | frozen |
| `resolution_mode` | yes | `resolve_in_place` \| `emit_relocation` | Chooses "write the value now" from "write a record for later" | A mode inferred from whether the target happens to be defined makes bytes depend on symbol liveness; an unresolved patch written with no record loses the reference silently. | frozen |
| `pair_group` | no | Id shared by associated fixups | Some patches only make sense as a pair | `adrp`+`add` and `auipc`+`addi` are pairs; applying one alone yields a wrong address. | frozen |
| `pair_role` | no | `hi` \| `lo` | Selects the member's transform | Swapping roles produces a plausible but wrong address. | frozen |

`overwrite_bytes` was removed from `fmp/0.1`. It was required and pinned to
`false`, so it could not be true without already being rejected and carried no
information when false. The condition it was meant to prevent — a plan writes
raw bytes and then patches them — is scheme C, which `OD-01`/ADR-0004 already
excludes at the level of `form_id` and operands. Recorded here so the removal is
traceable rather than a silent schema drift.

### 2.1 Target kinds

`target.kind` is a closed set of three. Each names a different source of `S`, and
the difference matters because only two of them need a bound section:

| `target.kind` | `S` | `base_address` needed |
|---|---|---|
| `symbol` | the symbol's address: `base_address(section) + offset` when the rule needs an absolute address, or `offset` alone for a same-section PC-relative rule | in effect only |
| `absolute` | `target.address`, used exactly as written | no |
| `section_relative` | `base_address` of `target.section_id` | yes |

For `symbol` the location comes from `symbols[]`, never from a name lookup in
`sections[]`. `absolute` is the only kind that does not consult the layout at
all. `section_relative` is `inference`: `01_contract.md` names the kind, no v0
fixture exercises it, and §5.1's five cases do not need it. It is implemented as
"the named section's base address, plus the addend", refused `E-FIXUP-002` when
that section has no `base_address`, and stays `unverified` until a slice uses it.
A plan that wants an address *inside* a section names a `symbol`, because that is
the only form that carries an offset.

## 3. Field descriptors

```json
{ "offset": 12,
  "field_descriptor": [
    { "lsb": 31, "width": 1 },
    { "lsb": 25, "width": 6 },
    { "lsb": 8,  "width": 4 },
    { "lsb": 7,  "width": 1 }
  ] }
```

Rules:

- `field_descriptor` entries are in **value order**: the first entry receives the
  most significant bits of the value. There is no separate `bit_order` field:
  the list order is the order, and a one-value enum with a schema `default`
  would be a defaulted field. It was removed with `overwrite_bytes` for the same
  reason.
- `lsb` is relative to the instruction's first byte in the section, not to the
  plan's byte buffer.
- `offset` MUST be that first byte, so the site and the descriptor base are the
  same point. A site inside an instruction would make `lsb` ambiguous — "relative
  to the instruction's first byte" and "relative to the site" would disagree —
  and is rejected `E-FIXUP-005`. For x86 `rel32` the site is the instruction
  start and the descriptor is `[{ "lsb": 8, "width": 32 }]`; the displacement
  starts one byte in, and the descriptor says so.
- `width` is in bits; bits MUST lie inside the instruction's `expected_size`.
- Overlapping descriptors within one fixup are rejected (`E-FIXUP-005`).
- Overlapping fixups in the same byte are rejected (`E-FIXUP-006`).
- The sum of the `width`s MUST equal `range_constraint.bits` (`E-FIXUP-001`).
  Otherwise a plan could declare a narrower range than the field it writes, and
  the range check would never fire.
- Bits not covered by any descriptor are left untouched; the encoder, not the
  fixup, produced them.

One writer per bit (OD-02). A field covered by a fixup is written by that fixup
and by nothing else:

- The form's template leaves the covered bits zero.
- An operand MUST NOT supply a numeric value for a covered field. If it does,
  the plan states two different values for one field and the fixup silently wins
  (`E-FIXUP-006`). The site is `section_id` + `offset` + `field_descriptor`, so
  the materializer cannot tell a deliberate placeholder from a mistake.
- An operand may still name the same target as the fixup, as a signature guard.
  The target operand and `fixup.target` MUST then agree, or the fixup is
  incompatible with the form (`E-FIXUP-001`).

The rule matters because "operand value overwritten by a fixup" is the same
silent repair the rest of the contract forbids, one layer down: the plan would
be accepted while one of its fields is ignored.

## 4. `pc_reference_rule`

`P` is the reference point used to compute the displacement. It is never
defaulted.

| Rule | `P` | Used by |
|---|---|---|
| `none` | not applicable | absolute patches |
| `pcrel_begin` | address of the fixup site | RISC-V B-type and J-type, AArch64 `b`/`bl`/`b.cond` |
| `pcrel_end` | address immediately after the instruction that contains the site | x86-64 `rel32` |
| `pcrel_page` | page base of `P` | AArch64 `adrp` |
| `pcrel_hi` | address of the paired `hi` member's site | RV64 `addi`/load/store low half (`pcrel_lo12`) |

For `pcrel_end` the containing instruction is found through the section's
fragments, not by arithmetic on the site offset: the site may sit several bytes
into the instruction (x86 `rel32` starts at byte 1), so "site + size" would be
wrong by exactly that much. An earlier draft of this table said that; it was
fixed after `EXP-0002` §6.1 exposed the off-by-one.

`pcrel_hi` is the one rule that reads another fixup: its `P` is the paired `hi`
member's site, so it is legal only on a fixup with `pair_role: lo`, and the `hi`
must be in the same section. The psABI states the same constraint for the label
("an instruction in the same section with a high-part relocation entry",
`riscv-elf.adoc:1584-1590`). A `lo` whose group has no `hi` is `E-FIXUP-007`;
there is no fallback to `pcrel_begin`, because that would silently measure from
the wrong instruction (ADR-0010).

A definition MAY declare additional named rules (`definition:<id>`), but the
string must be resolved by the pinned definition, never by convention.

An `absolute` target is an address on the same number line as `P`, so a rule
other than `none` needs the site's section `base_address`; without one the fixup
is `E-FIXUP-002` under `resolve_in_place`. A `section_relative` target is itself
a section address, so it needs that section's `base_address` under
`resolve_in_place` whatever the rule. A same-section `symbol` target under
`pcrel_begin`/`pcrel_end` is the one exempt case: the displacement is a
difference of two offsets and is translation-invariant, so offsets alone are
exact. `pcrel_page` is not exempt — it takes the page base of each address, and
moving the section changes which page an offset lands in.

A missing `base_address` is never read as zero. Zero is an address, and choosing
it would turn "the plan did not say where this section lives" into "the section
lives at 0", which is the implicit default `INV-05` forbids.

## 5. Resolution modes (OD-02)

`resolution_mode` has exactly two values. The plan chooses the mode per fixup;
the materializer never infers it from whether the target happens to be defined.

| Mode | Value written | Record emitted | Target unknown |
|---|---|---|---|
| `resolve_in_place` | computed value, range-checked, masked into the descriptor bits | none | `E-FIXUP-002` |
| `emit_relocation` | zero in every descriptor bit | one normalized record | record emitted; nothing to resolve |

Consequences:

- **One fixup has exactly one effect.** "Resolved bytes plus a record" is not a
  third mode: it would need two fixups on the same bits (`E-FIXUP-006`), and it
  leaves open which of the two a consumer should trust.
- **The mode is a function of the plan alone.** Making it depend on whether the
  target is local would make the same plan emit different bytes after a symbol
  moves from `undefined` to `defined`. That is an implicit decision over
  resolution state (`INV-02`, `INV-05`).
- **`emit_relocation` never computes `S + A - P`, so it cannot range-check the
  value.** The record carries `range_constraint` and the consumer performs the
  check. A plan that needs the value checked here must say `resolve_in_place`.
- **`reject_if_unresolved` was removed, not repurposed.** For a known target it
  was byte-identical to `resolve_in_place`; for an unknown target it was
  byte-identical too, because both reject `E-FIXUP-002`. A third name for one
  behaviour is a schema invitation to disagree about it.

`E-FIXUP-002` and `E-SYMBOL-001` are different failures:

- `E-SYMBOL-001` — `fixup.target.symbol_id` names no entry in `symbols[]`. The
  plan is internally inconsistent. A `defined` symbol with no location is
  `E-SYMBOL-003`, not this.
- `E-FIXUP-002` — the symbol exists but carries no address (it is `undefined` or
  `external`), the fixup is `resolve_in_place`, and there is nothing to write.

### 5.1 The directive's five cases

`00_directive.md` §5.2 requires a position on five cases. They are not five
modes; they are five target states mapped onto the two modes:

| Case | Known here? | Legal plan | If the plan asks to resolve |
|---|---|---|---|
| same-section reference | yes | `resolve_in_place` or `emit_relocation` | — |
| known absolute address | yes (`target.kind: absolute`) | `resolve_in_place` or `emit_relocation` | — |
| unresolved external symbol | no | `emit_relocation` | `E-FIXUP-002` |
| cross-section, expressible | yes if both sections are bound | either mode; the record names the symbol | `E-FIXUP-002` if a section has no `base_address` |
| out of the encoding range | yes | `resolve_in_place` | `E-FIXUP-003` |

Cross-section is not a separate mode. `S - P` is well defined as soon as both
sections have a `base_address`; without one, a same-section reference still
resolves from offsets alone, and a cross-section reference is unresolvable.

"Record a relocation" and "resolve a symbol" are different operations. A plan
that says `emit_relocation` MUST NOT be silently resolved into bytes with no
record.

## 6. Target-specific semantics (v0 candidates)

`value_transform` is applied to `D`, the value `pc_reference_rule` produced. The
six transforms `fmp/0.1` defines, and nothing else:

| Transform | Applied as | Where it comes from |
|---|---|---|
| `identity` | `v = D` | — |
| `scale` | `v = D >> transform_shift`, arithmetic | `scale(2)` for AArch64 `b`, `b.cond` and `ldr (literal)` below |
| `page` | `v = (page(S + A) - page(P)) >> 12`, with `page(x) = x & !0xFFF` | `adrp` below |
| `lo12_i` | `v = (S + A) & 0xFFF` — a mask, never range-checked | `add :lo12:` below |
| `pcrel_hi20` | `v = (D + 0x800) >> 12` | RV64 `auipc` below |
| `pcrel_lo12` | `v = D & 0xFFF` — a mask, never range-checked | RV64 `addi`/load/store low half below |

`hi20` and `lo12_s` are named in the schema's `value_transform` enum, but this
document defines no semantics for them and no v0 fixture uses them. A plan that
names one is `E-VERSION-001` (`feature: value_transform:hi20`): `fmp/0.1` cannot
express what the plan means, and inventing a definition at materialization time
would be a decision, not a validation. They are reserved for the AArch64 and RV64
tables, which add their definitions together with the slice that needs them.
`lo12_s` stays reserved on purpose (ADR-0010): the `_i`/`_s` suffix names the
instruction form, which `form_id` already carries, so an S-type low half is
`pcrel_lo12` with an S-type `field_descriptor`. `pcrel_lo12` is *not* a synonym
for `lo12_i`: it masks the displaced value `S + A - P_hi`, while `lo12_i` masks
the absolute `S + A`, and the two differ whenever the `hi` is not page-aligned.

The ISA table:

| Case | Encoding facts | What the plan must pin |
|---|---|---|
| x86-64 `rel32` | `R_X86_64_PC32`-style: value = `S + A - P`, `P` = end of instruction | `pc_reference_rule = pcrel_end`, range `i32` |
| x86-64 PLT/GOT | semantics depend on link-time policy | v0: not expressible; a plan that names it is `E-VERSION-001` (§10) |
| AArch64 `b`/`bl` | imm26, signed, scaled by 4, `P` = instruction address, ±128 MiB | `pcrel_begin`, `scale(2)`, `range.bits = 26`, `align_bits = 2` |
| AArch64 `b.cond` | imm19, signed, scaled by 4, `P` = instruction address, −1 MiB…+1048572 B (`imm19` ends at 262143, so the upward end is not a round MiB) | `pcrel_begin`, `scale(2)`, `range.bits = 19`, `align_bits = 2`; the condition is an operand of the form, never a fixup field (`EC-29`) |
| AArch64 `ldr` (literal) | imm19, signed, scaled by 4, `P` = instruction address, −1048576…+1048572 B | `pcrel_begin`, `scale(2)`, `range.bits = 19`, `align_bits = 2`; destination is a register operand, and there is no base register (`EC-15`) |
| AArch64 `adrp` | immhi:immlo = `(page(S+A) - page(P)) >> 12`, signed 21 bits | `pcrel_page`, `value_transform = page`, pair `hi` |
| AArch64 `add :lo12:` | imm12 = `(S+A) & 0xFFF`; `sh` picks `LSL #0`/`#12` and is fixed by the form, not by the fixup | `value_transform = lo12_i`, pair `lo`, same `pair_group` |
| RV64 B-type | imm12…imm1 scattered; `P` = instruction address; ±4 KiB, 2-byte aligned | `pcrel_begin`, `range.bits = 12`, `align_bits = 1` |
| RV64 J-type (`jal`) | imm20…imm1 scattered; ±1 MiB | `pcrel_begin`, `range.bits = 20`, `align_bits = 1` |
| RV64 `auipc` hi20 | `hi20 = (S + A - P + 0x800) >> 12` in exact arithmetic, `P` = the `auipc`'s address | pair `hi`, `pcrel_begin`, `pcrel_hi20` |
| RV64 `addi`/load/store lo12 | `lo12 = (S + A - P_hi) & 0xFFF`, `P_hi` = the paired `auipc`'s address | pair `lo`, `pcrel_hi`, `pcrel_lo12`, `addend` MUST be 0 |

The literal load is the first non-branch PC-relative slot. Every earlier row with
`pcrel_begin` and `scale(2)` was a branch, so the fact that the target is a data
address rather than a control-transfer destination changes no field: the record
still carries `pcrel_begin`, `scale(2)` and the same 19-bit range check, and
`field_descriptor` still names `imm19` at `lsb 5` (`EXP-0025` §3).

The scaled AArch64 low half adds no fixup field: `#:lo12:ext, lsl #12` emits the
same `R_AARCH64_ADD_ABS_LO12_NC` record as the unscaled spelling and, for the
same symbol, the linker writes the same 12-bit field value, so the shift is the `form_id`'s
(`-lsl0`/`-lsl12`, ADR-0011) and a fixup cannot choose it (`EXP-0013` §5,
measured). The `#` is required by the assembler when a shift follows. What the
scaled form does *not* do is address the symbol: the instruction adds the field
at bit 12, so with `S = 0x123450` and `P = 0` the `adrp` + scaled `:lo12:` pair
yields `0x573000`, not `0x123450`. A scaled low half is therefore not a drop-in
address sequence, and no fixture links one; `A64-P6` covers the `-lsl0` pair only.

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

Fact 1 is no longer only an observation. The pinned psABI states it normatively
(`riscv-elf.adoc:1584-1590`, read at tag `v2.0-rc0`): the low-part relocation's
symbol is "a label pointing to an instruction in the same section with a
high-part relocation entry that points to the target symbol". The same section
adds that the value is `symbol_address - hi20_reloc_offset`, that "the addend must
be 0", and that one high part may serve "one or more" low parts that are "not
necessarily sequential" (`:1600-1605`, `:1184`, `:1186`). ADR-0010 turns those four
statements into `pcrel_hi`, `pcrel_lo12`, `E-FIXUP-009` and a 1:N group.

Consequence for output level (`OD-03`): a Level 0 record expresses all three
shapes directly. A Level 1 emitter for RISC-V would have to synthesize a local
symbol per `hi` site to fill the relocation, which is extra state, not extra
information.

## 7. Pairing rules

- Every fixup with `pair_group` MUST have exactly one `hi` and at least one `lo`
  member (`E-FIXUP-007`, `N12`). One high part may serve several low parts, and
  the members are not assumed to be adjacent (`ADR-0010`).
- All members MUST reference the same logical target. The group is coherent
  through `pair_group`; each member's `target` names the same symbol, and the
  different ELF spellings (§6.1: RISC-V's low record names the `hi` site,
  AArch64's names the symbol) are serialization details rather than plan data.
- The `lo` member's `section_id`/`offset` MUST be a valid site inside the same
  output. A `pcrel_hi` member MUST be in its `hi`'s section, because the psABI
  requires the label to point at an instruction in the same section; any other
  `lo` MAY be in a different section only if the definition allows it.
- Membership and roles are data. The materializer never infers a pair from
  adjacency, ordering, or symbol names.
- A `lo` member's transform is never derived from its `hi` member's. Both
  members declare `value_transform` explicitly, even when the pair makes one
  look redundant (OD-02, "one writer per bit").

## 8. REL vs RELA (OD-02)

`fmp/0.1` has exactly one record shape, and it is RELA-shaped:

- `addend` is always present in the record, even when zero;
- for `emit_relocation` the descriptor bits are zero and the addend is not
  written into them.

There is no `output_contract` switch and no plan field for it. REL semantics —
"the addend lives in the field" — are not expressible, and v0 does not need
them:

- A REL emitter would write the addend into the same bits a later consumer
  reads, so the field would be both an input and a record payload. A field that
  is zero would then be indistinguishable from a deliberate addend of zero.
- A plan that wants the addend folded into the bytes says `resolve_in_place`;
  there the computation includes `addend` explicitly and no record exists.

An earlier draft said the REL/RELA choice "belongs to `output_contract`". No
such field exists in `01_contract.md` §11, and adding one would create a second
byte-affecting switch on a record that already carries the addend. The record
shape is a property of `format_version`, and changing it is a format change, not
a per-plan option.

The record itself is the fixup, minus the mode that produced it:

| Record field | Source | Why it is in the record |
|---|---|---|
| `fixup_id` | `fixups[].fixup_id` | Record identity and `fixup_record_order` |
| `section_id`, `offset` | the fixup site | Where the consumer patches |
| `field_descriptor` | verbatim, in value order | Which bits, and how they are reassembled |
| `target` | verbatim | `symbol` / `absolute` / `section_relative`; a consumer must not have to guess |
| `addend` | verbatim | RELA-shaped: the addend is data, never read back from the bits |
| `pc_reference_rule`, `value_transform`, `transform_shift` | verbatim; `transform_shift` omitted when absent | The computation a consumer redoes |
| `range_constraint` | verbatim | `emit_relocation` cannot check the value, so the check travels with the record |
| `pair_group`, `pair_role` | verbatim; omitted when absent | AArch64/RV64 pairing is data, not adjacency |

`resolution_mode` is absent because every record means `emit_relocation`; a
record that could also mean "already resolved" would be the forbidden third
mode. Nothing else is added: a record with a timestamp, a host name or a
materializer version would make two identical plans produce different output
(`INV-05`). The materializer version lives in the artifact envelope
(`01_contract.md` §11.1), which is not part of the byte comparison.

## 9. Execution order and determinism

1. Validate all fixups statically (site, overlap, descriptor bounds, pairing,
   one writer per bit).
2. For each fixup in `(section_id, offset, fixup_id)` order, apply exactly one
   mode:
   - `resolve_in_place` — compute `S`, `P`, `A` exactly, apply
     `pc_reference_rule` then `value_transform`, check `align_bits` on the
     pre-transform value (`E-RANGE-003`) and `signed`/`bits` on the
     post-transform value (`E-FIXUP-003`), then write the masked bits.
   - `emit_relocation` — zero the descriptor bits and append one record. Do not
     compute a value.
3. Emit records in `(section_id, offset, fixup_id)` order.

Step 2 MUST be independent of iteration order. Because overlap is rejected, the
masked writes commute; the check exists so that this stays true. The two modes
also commute, because `resolve_in_place` writes only bits inside its descriptor
and `emit_relocation` writes only zeroes to its own.

## 10. Out of scope for v0 (with rejection tests)

- GOT/PLT/TLS and other link-time-policy relocations → `E-VERSION-001`, because
  no `fmp/0.1` field names them: `target.kind` is a closed set and
  `value_transform` has no `got`-like member. A plan that invents one declares a
  feature this format version cannot honour; it is not silently turned into a
  PC-relative record.
- Relaxation of any kind, including "convert `jal` to `c.j` to fit".
- Implicit addend extraction from existing bytes.
- Symbol preemption or visibility policy.
- REL output shape (§8).

Each exclusion needs a negative fixture that must be rejected, per AC-05.
