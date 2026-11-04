# ADR-0023: the literal load carries its offset in `imm19` and has no base register

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P16` (the literal load `ADR-0013` and `ADR-0022` held out), and
  the one-instruction half of `EC-15`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0013` shipped the `ldr`/`ldur`/`str` offset kinds and held three out:
register offset, literal, and the store `imm9` trio. `ADR-0022` closed the store
trio. What is left of the load/store family is the literal kind, and it is the
first one whose *operand list* differs rather than only its bits: `LDR (literal)`
has no `Rn` at all, and its displacement is a 19-bit field scaled by 4.

`EC-15` is frozen with the counterexample "a load from a label is a plan
decision: one literal load or two instructions (`adrp` + `:lo12:`)". Until this
slice the one-instruction half of that decision had no row, so a plan that made
it was `E-FORM-001` while the two-instruction half was expressible — a table that
silently preferred one side of a frozen choice.

Five measurements decide the slice (all `llvm-mc` 23.1.2, `EXP-0025`):

1. **The node has no `Rn` and no kind bits.** `LDR_64_loadlit` fixes
   `opc = 01` at 31–30, bits 28–24, `VR = 0`, and leaves exactly two variable
   fields: `imm19` at 5+19 and `Rt` at 0+5. Bits 11–10 and bit 21, which carry
   the address kind on the other load rows, are not fields here — they are part
   of the fixed `0x58000000` pattern.
2. **`imm19` is field content in words.** `ldr x0, #4` at offset 0 is
   `0x58000020`, i.e. `imm19 = 1`, and `ldr x0, #12` at offset 4 is
   `0x58000060`, i.e. `imm19 = 3`. The byte displacement is the field times four.
3. **The reference is the instruction address.** `ldr x0, <label 20 bytes
   ahead>` is `0x580000a0` (`imm19 = 5`), not `imm19 = 6`. The scaled AArch64
   `b`/`bl`/`b.cond` rows already use `pcrel_begin`, and this row shares it.
4. **The range is the signed 19-bit field, so the byte range is
   `−1048576 … +1048572`.** `#-1048576` and `#1048572` assemble, `#1048576`
   does not; the upward end is not a round MiB for the same reason `b.cond`'s is
   not. `llvm-mc` reports a misaligned displacement (`#2`, `#6`) with the same
   message as an out-of-range one.
5. **There is no store literal.** The drop has no `STR_*_loadlit` node (a scan of
   every node name containing `loadlit` returns seven: the 32-bit, 64-bit,
   `LDRSW`, `S`/`D`/`Q` and `PRFM` loads), and `llvm-mc` rejects both
   `str x0, #4` and `str x0, lit` with `invalid operand for instruction`.

## Decision

1. **One form is added in `definitions/aarch64/0.14.0.json`**:
   `aarch64:ldr/x64-imm19` from `LDR_64_loadlit`. `0.14.0` repeats the 135
   `0.13.0` rows unchanged and adds this one; `0.1.0` … `0.13.0` stay frozen, so
   a plan bound to `0.13.0` cannot reach it (`E-FORM-001`, `N01o`).
2. **The operand list is `dest`, `target` — there is no `base`.** `dest` is
   `aarch64.gpr64`/`x64` at `[0,5]`; `target` is `aarch64.rel`/`imm19` at
   `[5,19]`. A plan that passes a `base` has three operands where the row
   declares two, which is `E-OPERAND-002` by the count rule `N02e` pins.
3. **The slot is the field, so `align_bits` is 0 on the slot.** `{ "value": n }`
   is the `imm19` content: `n = 1` loads from PC+4 and is legal, exactly as
   `bl`'s `imm26` is (`07_definition_format.md` §8.3). A byte offset goes
   through a fixup, which carries the division: `pcrel_begin`,
   `value_transform = scale` with `transform_shift = 2`, `range.bits = 19`,
   `align_bits = 2` — the same four fields as the `bl`/`b.cond` fixtures, and
   the new row of the `03_fixup_model.md` §6 table.
4. **The form covers the 64-bit `x` load only.** The same node name carries four
   `opc` values with different meanings: `01` is `LDR Xt`, `00` is `LDR Wt`,
   `10` is `LDRSW Xt` and `11` is `PRFM`; `VR = 1` is the `S`/`D`/`Q` family.
   `opc` selects the destination register class and the operation, so each is
   its own row (`INV-02`), and the three other `opc` values plus the SIMD
   family stay out.
5. **No store literal is added, because none exists.** A plan naming
   `aarch64:str/x64-imm19` is `E-FORM-001` in every document; the store side of
   the literal kind is not a slice this table is postponing.
6. **Range and alignment are two rejections, and that split is our own.** The
   assembler reports `#2` and `#1048576` with one message; our contract says a
   field value outside `imm19` is `E-RANGE-002` (`N04d`, value `262144`) while a
   fixup whose pre-transform displacement is not a multiple of 4 is
   `E-RANGE-003` (`N20`, displacement `2`). The value is inside the field in the
   second case, so the defect is the alignment, not the range — the rule
   `OD-09` already states ("alignment on the pre-transform value, range on the
   post-transform value").
7. **No schema change and no Rust change.** `role: target`, `aarch64.rel`, a
   signed per-slot range and a `pcrel_begin` + `scale(2)` fixup all already
   load; the row is the first AArch64 `target` slot that is not a branch, which
   changes no code path.

## Consequences

- `A64-P16` passes: `A64-P16-loadlit` is six instructions over one form, with
  `imm19` at 2 and −4 through the two symbol fixups, at −1 and 1 through plain
  values, and at both ends of the field (262143 and −262144). The 24 bytes match
  `llvm-mc` 23.1.2 with no relocations (`EXP-0025` §3).
- The AArch64 table is 136 forms across fourteen documents, now from
  thirty-three encode nodes plus the ten alias verification nodes.
- The AArch64 fixtures become seventeen positive and forty-one negative.
- `EC-15`'s counterexample is now carried: both halves of the decision have a
  row, and neither is chosen by an operand value.
- `06_validation_matrix.md`'s `N04` row is widened from "branch displacement" to
  "control-transfer or literal displacement", because `E-RANGE-002` now gates a
  non-branch PC-relative field.

## Alternatives considered

- **Give the row a `base` operand naming `pc`, or a `pc` register kind.**
  Rejected: `pc` is not a field in the node, `pcrel_begin` already states the
  reference, and a register operand that writes no bits is a second carrier for
  a decision the fixup owns (`INV-05`, `OD-11`).
- **Make `imm19` a byte displacement and scale the slot by 4.** Rejected for the
  reason in `ADR-0013`: `fmp-def/0.1` has no slot transform, and a slot divisor
  would be a second scaling mechanism beside the fixup's `transform_shift`
  (`07_definition_format.md` §8.3).
- **One row with `opc` as an operand, covering `LDR Xt`/`LDR Wt`/`LDRSW`/`PRFM`.**
  Rejected: `opc` decides the destination class and the operation, so the
  "operand" would select which other slots exist — the same shape `ADR-0022`
  rejected for the store kinds (`INV-02`).
- **Add a store-literal row for symmetry.** Impossible: the MRS drop has no
  `STR_*_loadlit` node and the assembler rejects the spelling. A row would have
  to invent the encoding.
- **Report a misaligned fixup displacement as `E-RANGE-002`, matching the
  assembler's single message.** Rejected: `2` is inside `imm19`; reporting it as
  a range failure would tell a planner to change the value when the plan's
  symbol offset is what has to change, and it would collapse the two checks
  `OD-09` keeps apart.
- **Include register offset in the same slice.** Still deferred, not refused:
  `Rm`/`option`/`S` need a second register, a shift kind and the `S` bit, which
  is its own decision with its own counterexamples (`N01b`).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `LDR_64_loadlit` leaves only `imm19` (5+19) and `Rt` (0+5) variable | MRS `Instructions.json`, node dump in `EXP-0025` §1 | high |
| The template is `0x58000000` plus `Rt` and `imm19 << 5` | MRS fixed bits; `ldr x0, #0` = `0x58000000`, measured | high |
| `imm19` counts words and the reference is the instruction address | `ldr x0, #4` → `0x58000024`; label 20 bytes ahead → `0x580000a0` | high |
| The byte range is `−1048576 … +1048572` | both ends accepted, `+1048576` rejected, `EXP-0025` §2 | high |
| No store literal exists | no `STR_*_loadlit` node; `str x0, #4` / `str x0, lit` rejected | high |
| The six-instruction vector is `40000058 e1ffff58 e2ff7f58 03008058 84ffff58 25000058` | `EXP-0025` §3, `llvm-mc` + `llvm-objcopy`, no relocations | high |
| A non-multiple-of-4 displacement is `E-RANGE-003`, not `E-RANGE-002` | `OD-09`'s rule plus the materializer's fixup alignment check; our contract decision, not the assembler's | high (mechanism), **our decision** |
| A `base` operand on this row is `E-OPERAND-002` | the slot list has no `base`; the count rule is `N02e`'s | high (mechanism), no fixture in this slice |

## Review triggers

- Register-offset loads/stores land. `Rm`/`option`/`S` add a third operand and a
  scale bit, and bit 21 becomes meaningful again.
- A 32-bit, `LDRSW`, `PRFM` or SIMD/FP literal load appears. `opc` and the
  register class change, so each is a new row.
- A plan needs the literal to reference a symbol in another section. The
  `pcrel_begin` delta would cross sections, and no fixture has measured that.
- A plan needs a literal pool or data bytes inside a code section. Output
  fragments are typed, so that is an output-contract decision, not a row.
