# ADR-0025: the 32-bit register offset is the same `option` family with a `#2` scale

- Status: accepted
- Date: 2026-11-05
- Settles: `A64-P18` (the 32-bit half of the register-offset kind `ADR-0024`
  decision 8 held out)
- Supersedes: none
- Superseded by: none

## Context

`ADR-0024` added the sixteen 64-bit register-offset rows and deferred the 32-bit
ones with a reason: `size` changes both the access width and the `S = 1` scale,
so the rows are a separate measurement even though the `option` mapping is the
same. This slice is that measurement.

The two nodes are `LDR_32_ldst_regoff` and `STR_32_ldst_regoff`. They are the
64-bit pair with `size = 10` and the same `opc` split (`01` is `LDR Wt`, `00` is
`STR Wt`); every other fixed bit and every field position is unchanged, so the
slice is again `Rm`/`option`/`S`/`Rn`/`Rt` and again sixteen rows per mnemonic
pair. The only decision that is new is the amount `S = 1` names.

Measurements (`llvm-mc` 23.1.2, `EXP-0027`):

1. **`S = 1` is `#2`, not `#3`.** `ldr w0, [x1, x2, lsl #2]` is `0xb8627820`
   and the unscaled `ldr w0, [x1, x2]` is `0xb8626820`; the two words differ in
   bit 12 only, exactly as the 64-bit pair did. `#1`, `#3` and `#4` are rejected
   with `expected 'lsl' or 'sxtx' with optional shift of #0 or #2`, so the
   accepted set is `#0`/`#2` and the amount is the bit again.
2. **`option` keeps its meaning and its width pairing.** `011` (`lsl`) and `111`
   (`sxtx`) take an `x` index, `010` (`uxtw`) and `110` (`sxtw`) take a `w`, and
   the assembler still refuses the cross pairings in both directions
   (`ldr w0, [x1, w2, lsl #2]` → `expected 'uxtw' or 'sxtw' …`;
   `ldr w0, [x1, x2, uxtw]` → `expected 'lsl' or 'sxtx' …`).
3. **Only `Rt` changes width.** `Rn` and `Rm` are the same 64-bit address and
   index registers; the destination of the load and the source of the store are
   `w`. Register 31 therefore still means `sp` in `Rn` and `xzr`/`wzr` in `Rm`
   (`ldr w0, [sp, x2]` is `0xb8626be0`, `ldr w0, [x1, xzr, lsl #2]` is
   `0xb87f7820`).
4. **There is no other spelling.** `ldur w0, [x1, x2]` is read as an unscaled
   offset and rejected, and a register offset with `!` is
   `invalid operand for instruction`, so the 32-bit kind also has no
   pre/post-index or unscaled register form.

## Decision

1. **Sixteen forms are added in `definitions/aarch64/0.16.0.json`**, eight per
   mnemonic: `aarch64:ldr/w32-base-regoff-{lsl,uxtw,sxtw,sxtx}{0,2}` and the same
   eight for `str`. `0.16.0` repeats the 152 `0.15.0` rows unchanged, so a plan
   bound to `0.15.0` cannot reach a 32-bit register-offset row (`E-FORM-001`,
   `N01r`).
2. **`option` and `S` stay pinned in the row.** The reasoning is `ADR-0024`'s:
   both are byte-affecting decisions, and an operand would let a plan write the
   encoding bits. The new fact is only that the pinned `S = 1` row is `#2` here.
3. **The suffix states the amount the row encodes.** `-lsl0`/`-lsl2` and the
   three other keyword pairs name the scale explicitly, so a 32-bit plan cannot
   borrow a 64-bit name: `aarch64:ldr/w32-base-regoff-lsl3` is a name for nothing
   (`E-FORM-001`, `N01s`), not a range error, because no field holds `3`.
4. **`dest`/`src` are `aarch64.gpr32`/`w32`; `base` and the two `x` index rows
   stay `aarch64.gpr64`/`x64`.** An `x64` destination on a `-lsl0` row is
   `E-OPERAND-001` (`N02h`), and a `w32` index on a `-lsl0` row is the same
   diagnostic on `index` (`N02g`), exactly as on the 64-bit rows.
5. **A modifier still cannot carry the shift.** `{ "name": "lsl", "value": 2 }`
   on the `index` of `-lsl0` is `E-OPERAND-003` (`N19c`): a modifier never
   writes the `S` bit, and accepting it would emit the unscaled word.
6. **No schema change and no Rust change.** The row set uses the same three
   roles, the same two register kinds and the same `reg_number` source as
   `0.15.0`; only the `w32` destination/source and the pinned `S` value differ.

## Consequences

- `A64-P18` passes: `A64-P18-w32regoff` is twenty instructions over the sixteen
  new rows plus four register-31 rows, 80 bytes, and matches `llvm-mc` 23.1.2
  with no relocations (`EXP-0027` §4).
- The AArch64 table is 168 forms across sixteen documents, now from
  thirty-six encode nodes plus the ten alias verification nodes.
- The AArch64 fixtures become nineteen positive and fifty negative.
- The `w` load/store width now has its first rows; the `w` immediate kinds
  (`ldr w0, [x1, #4]` and the `b`/`h` widths) remain absent and each is its own
  row set, because their `imm12` unit and `opc` meanings differ.

## Alternatives considered

- **One `-lsl` row with `S` as an operand, shared with the 64-bit rows.**
  Rejected for the same reason as `ADR-0024`: `S` decides a bit, and the two
  widths would then be one form with a `dest` whose class is chosen by a field.
- **Name the 32-bit rows `-lsl0`/`-lsl3` and reuse the 64-bit names.** Rejected:
  the same suffix would then encode different words, and a plan could not tell
  the two apart without reading `size`. The suffix states the amount.
- **Add the `b`/`h` register offsets in the same slice.** Deferred, not refused:
  `size = 00`/`01` makes `S = 1` a `#0`/`#1` scale and `LDUR`-style `opc`
  meanings appear for the signed loads; that is a separate measured row set.
- **Add `LDRSW`/`LDRSB`/`LDRSH` register offsets.** Deferred: they keep
  `size = 10` but change `opc`, and their destination width is not the access
  width, so the row's `dest` class and the load's sign extension are a new
  decision.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The 32-bit nodes differ from the 64-bit pair only in `size` and `opc` | MRS node dump, `EXP-0027` §1 | high |
| `option` is `011`/`010`/`110`/`111` for `lsl`/`uxtw`/`sxtw`/`sxtx` at 32 bits | measured words, `EXP-0027` §2 | high |
| `S = 1` is `#2` and only `#0`/`#2` are accepted | eight accept/reject probes, `EXP-0027` §2–§3 | high |
| `Rt` is `w`, `Rn`/`Rm` stay `x`, and 31 keeps the node's role | measured words, `EXP-0027` §2 | high |
| There is no writeback or unscaled 32-bit register offset | assembler rejections, `EXP-0027` §3 | high (assembler surface) |
| The twenty-instruction vector is 80 bytes | `EXP-0027` §4, `llvm-mc` + `llvm-objcopy`, no relocations | high |
| `-lsl3` on the 32-bit row is `E-FORM-001`, not a range error | the form set has no such row; our contract decision | high (mechanism), **our decision** |

## Review triggers

- `b`/`h` register offset lands. `size` changes the `S = 1` amount and the
  signed-load `opc` meaning.
- A load/store with `opc` other than the plain `LDR`/`STR` pair lands (`LDRSW`,
  `LDRSB`, `LDRSH`, `PRFM`). Each changes the destination class or the operation.
- A plan needs a 32-bit index register that is not `uxtw`/`sxtw`, or an `x`
  index that is not `lsl`/`sxtx`. That would mean a spelling we have not
  measured.
