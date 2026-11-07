# ADR-0093: a symbol in an absolute 32-bit content field (`R_X86_64_32S`)

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P70` (one symbol in nine absolute 32-bit content fields: eight
  `disp32` slots at four value widths, both directions and one EVEX vector row,
  plus one `imm32` slot)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `disp32` of the absolute rows is also a relocation
  site), `EC-05` (a symbol in that field never promotes the row to `moffs`),
  `EC-34` (an absolute field carries `pc_reference_rule = none`, never a
  measurement from the end of the instruction) and `EC-39` (an EVEX `disp32`
  fixup target is never compressed to `disp8`)

## Context

The table already carries absolute `disp32` rows at four value widths, one EVEX
vector width and an `imm32` slot on `add`. Every one of those fields was frozen
as *literal content*: an `x86.imm` / `disp32` (or `imm32`) slot whose
`from` is `operand_value`, filled by `payload.value`. The PC-relative family
(`X86-P6`, `X86-P7`) already shows the other half of the mechanism — an operand
with `payload: {}` and one fixup over the field bits — but only for `rel32`.

Nothing in the table stopped a symbol from reaching an absolute field; the
question was what the plan must say, and what the materializer may then write.
`EXP-0095` measures both answers with `llvm-mc` and `ld.lld`:

1. **The field is zero in the object file and the reference travels in a
   record.** `llvm-readobj --relocations` on `probe.asm` reports nine
   `R_X86_64_32S ext 0x0` records, and `llvm-mc -disassemble` on the object
   bytes reads every field as `0`. The record offset is the field's first byte
   in all nine cases, so the record is `field_descriptor`-shaped, not
   instruction-shaped.
2. **The field position depends on the row, not on the operand.** Measured:

   | `form_id` | Bytes | Length | `lsb` | Record offset |
   |---|---|---|---|---|
   | `x86:mov/r32-abs32/legacy` | `8b042500000000` | 7 | 24 | `0x3` |
   | `x86:mov/abs32-r32/legacy` | `89042500000000` | 7 | 24 | `0xA` |
   | `x86:mov/r32-ext-abs32/legacy` | `448b042500000000` | 8 | 32 | `0x12` |
   | `x86:mov/r64-abs32/legacy` | `488b042500000000` | 8 | 32 | `0x1A` |
   | `x86:mov/abs32-r16-ext/legacy` | `6644890c2500000000` | 9 | 40 | `0x23` |
   | `x86:mov/abs32-r8h/legacy` | `88242500000000` | 7 | 24 | `0x2A` |
   | `x86:mov/r8-abs32/legacy` | `8a042500000000` | 7 | 24 | `0x31` |
   | `x86:vmovaps/zmm-abs32/evex` | `62f17c48280c2500000000` | 11 | 56 | `0x3C` |
   | `x86:add/rm64-imm32/legacy` | `4881c000000000` | 7 | 24 | `0x43` |

   The eight `disp32` rows put the field at `[24,32]`, `[32,32]`, `[40,32]`
   or `[56,32]` depending only on the template's prefixes; the `imm32` slot of
   `add` is at `[24,32]`. The field kind is therefore irrelevant to the
   mechanism: what matters is where the bits are.
3. **The record is the signed 32-bit absolute class.** The same symbol in the
   neighbours takes other classes, so the row and the descriptor do not imply
   this one: `movl ext(%rip), %eax` is `R_X86_64_PC32` with addend
   `-4`, `movabs ext, %rax` is `R_X86_64_64`, `movl $ext, %eax` is
   `R_X86_64_32` (and has no `mov` immediate row yet), while
   `addq $ext, %rax` is `R_X86_64_32S` — the same class as the eight
   displacements.
4. **`resolve_in_place` is measurable, and it needs a bound section.**
   `resolved.asm` binds `.text` at `0x1000` and places `L1` at offset 30, so
   `S = 0x101e`. `ld.lld -m elf_x86_64 --image-base=0 -Ttext 0x1000` writes
   the five displacements `0x101e`, `0x1022`, `0x101e`, `0x1020` and `0x101e`
   (the two non-zero addends are 4 and 2), and the linked image re-disassembles
   as `movq 0x101e, %rax` and so on. Without linking, the same object carries
   five `R_X86_64_32S .text` records with addends `0x1E`, `0x22`, `0x1E`, `0x20`
   and `0x1E` — exactly `S + A` with `S` replaced by the symbol's offset.

## Decision

1. **An absolute content field carrying a symbol is an empty operand payload
   plus one fixup over exactly the slot's bits.** The operand keeps its role,
   kind and target type (`disp`/`x86.imm`/`disp32`, or `imm`/`x86.imm`/`imm32`)
   and carries `payload: {}`. The fixup is
   `pc_reference_rule: none`, `value_transform: identity`, an explicit
   `addend`, `range_constraint {signed: true, bits: 32, align_bits: 0}` and a
   `resolution_mode`. Its `field_descriptor` is the single window the row's
   `operand_value` slot declares: a descriptor whose widths do not sum to
   `range_constraint.bits`, or that covers only part of the slot, is
   `E-FIXUP-001`; one that runs past the instruction's bits is `E-FIXUP-005`;
   and one that overlaps template bytes is `E-FIXUP-006`.
2. **The payload does not name the symbol.** `payload: {symbol_id}` on a
   non-`target` role is `E-OPERAND-003` (`N15b`): the operand would then carry
   a decision the fixup already carries, and two carriers can disagree. The
   reference lives only in `fixup.target`.
3. **An empty payload with no covering fixup is `E-OPERAND-003`** (`N15c`),
   never a zero. Zero is a value the plan did not state, and writing it would
   be the implicit default `INV-05` forbids.
4. **`emit_relocation` writes zero and emits one record.** The materializer
   computes no value and therefore cannot range-check it (`03_fixup_model.md`
   §5); the record carries the signed 32-bit constraint for the consumer. The
   nine-record order in the fixture is the plan's
   `fixup_record_order` (`section_id,offset,fixup_id`).
5. **`resolve_in_place` writes `S + A` and needs the target's section bound.**
   Because `pc_reference_rule` is `none`, the site and the symbol cannot cancel
   (`03_fixup_model.md` §4); a same-section symbol without
   `.text.base_address` is `E-FIXUP-002` (`N08d`), not an offset used as an
   address. `S` is `base_address + symbol.offset`, so the fixture's
   `0x101e` is `0x1000 + 30`.
6. **A value already written in the operand is a second writer.**
   `payload: {value}` plus a covering fixup is `E-FIXUP-006` (`N07c`); the two
   would disagree silently otherwise.
7. **No definition, schema, loader or materializer change.** Every slot and
   every fixup field this uses already exists; the slice states how they
   compose and pins it with fixtures. `0.65.0` stays canonical, still 509
   forms with digest
   `sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a`.

## Consequences

- `X86-P70-abs32-symbol` is nine instructions and 71 bytes: eight displacements
  at four value widths, both directions, the high-byte row and one EVEX vector
  row, plus `addq $ext, %rax`. All nine fixups are `emit_relocation`; the
  record count is 9 and every field is zero in the bytes. Its `expected.bin`
  comes from `llvm-mc` + `llvm-objcopy`, never from the materializer.
- `X86-P70-abs32-symbol-resolved` resolves the same window in place against a
  defined symbol in a `.text` placed at `0x1000`: five instructions, 37 bytes,
  values `0x101e`/`0x1022`/`0x101e`/`0x1020`/`0x101e`. The bytes come from
  `ld.lld` + `llvm-objcopy`, and `llvm-nm` on the linked image reports
  `000000000000101e t L1`.
- Seven negatives pin the shape: a symbol payload on the `disp` role (`N15b`,
  `E-OPERAND-003`), an empty payload with no fixup (`N15c`, `E-OPERAND-003`), a
  value plus a covering fixup (`N07c`, `E-FIXUP-006`), a 16-bit partial
  descriptor (`N07d`, `E-FIXUP-001` twice — the width sum and the uncovered
  operand), the 64-bit row's `[32,32]` window on a 7-byte row (`N07e`,
  `E-FIXUP-005` and `E-FIXUP-001`), `resolve_in_place` without a bound section
  (`N08d`, `E-FIXUP-002`) and an absolute `0x1000` in the 8-bit `add`
  immediate (`N04f`, `E-FIXUP-003`).
- `E-FIXUP-005` and `E-FIXUP-006` now have negative fixtures, so their
  `04_errors.md` negative columns stop being `—`; `E-OPERAND-003` gains
  `N15b`/`N15c` and `E-FIXUP-002`'s description gains the
  non-PC-relative-symbol case. The `N07`, `N08`, `N15` and `N04` matrix rows and
  the negative lists gain the new ids in place.
- `EC-02`, `EC-05`, `EC-34` and `EC-39` are revised in place; no `EC` row is
  added or renumbered.

## Alternatives rejected

- **A `target`-role operand naming the symbol, one row per direction and
  width.** Rejected: the bytes are identical to the absolute row, so every
  absolute form would be duplicated once per direction, width and vector
  width, and the duplicate would differ only in a role name. The field is
  content; the reference is a fixup.
- **A new operand kind (`x86.abs`) that means "address content".** Rejected
  for the same reason: it duplicates the slot and gives the operand a second
  way to say "this field is a relocation site". `field_descriptor` already
  says which bits change.
- **`payload: {symbol_id}` on the `disp` role.** Rejected: `E-OPERAND-003`
  (`N15b`). It also makes the operand, not the fixup, the carrier of the
  target, so the descriptor and the addend would have nowhere to live.
- **Resolve a same-section absolute symbol from its offset when no
  `base_address` is set.** Rejected: an absolute field needs an address, and
  offset `30` is not `0x101e`. Using the offset would invent a base of zero
  (`INV-05`); `E-FIXUP-002` is the same answer `N08c` already gives for an
  `absolute` target under a PC rule.
- **Promote a symbol in a `disp32` to `moffs` or to an eight-byte offset.**
  Rejected: the row and its length are frozen by `form_id`; a symbol changes
  the field's value, never its width (`INV-02`, `INV-04`). `llvm-mc` keeps
  `R_X86_64_32S` here and chooses `R_X86_64_64` only for `movabs`.
- **Compress an EVEX `disp32` fixup target to `disp8`.** Rejected: `disp8`
  compression is a function of the value and the element size, and the value
  is not known at materialization time; the field's width is a form fact
  (`EC-39`).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| the nine fields are zero and carry nine `R_X86_64_32S ext 0x0` records | `llvm-readobj --relocations`, `EXP-0095` §1 | high |
| the record offsets and field `lsb`s are 7/7/8/8/9/7/7/11/7 bytes at 24/24/32/32/40/24/24/56/24 | object bytes plus `0.65.0` slot placements, `EXP-0095` §1 | high |
| the neighbours take `R_X86_64_PC32`, `R_X86_64_64`, `R_X86_64_32` and `R_X86_64_32S` | `llvm-readobj --relocations` on `adjacent.asm`, `EXP-0095` §3 | high |
| `resolve_in_place` writes `0x101e`/`0x1022`/`0x101e`/`0x1020`/`0x101e` for `S = 0x101e` | `ld.lld` at `0x1000` + `llvm-objcopy`, `EXP-0095` §2 | high |
| `llvm-nm` reports `000000000000101e t L1` in the linked image | `llvm-nm`, `EXP-0095` §2 | high |
| `movl $ext, %eax` has no `mov` immediate row and is not this slice | `0.65.0` forms list, `EXP-0095` §3 | high |
| `llvm-mc` rejects a width mismatch (`movl ext, %ax`, `movq ext, %eax`, `movw ext, %r9d`) | `llvm-mc -show-encoding`, `EXP-0095` §3 | high |

## Review triggers

- A symbol is proposed in a `mov` immediate field (`R_X86_64_32`, not `32S`);
  that needs its own row and its own evidence.
- A `moffs` field is proposed with a symbol; the offset width is still
  unresolved (`ADR-0092`).
- A 64-bit absolute field (or a `disp64`) is proposed; v0 has no such row.
- A plan asks for a symbol in an EVEX `disp8` or with a compressed
  displacement.
- A relocation class other than the signed 32-bit absolute one is proposed for
  these rows.
