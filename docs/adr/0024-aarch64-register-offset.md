# ADR-0024: register offset is a form family; `option` and `S` are form bits

- Status: accepted
- Date: 2026-11-05
- Settles: `A64-P17` (the register-offset kind `ADR-0013`, `ADR-0022` and
  `ADR-0023` held out), and the register-offset counterexample of `EC-14`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0013` shipped the `ldr`/`ldur`/`str` offset kinds and held three out:
register offset, literal, and the store `imm9` trio. `ADR-0022` closed the store
trio and `ADR-0023` the literal. Register offset is what is left, and it is the
first kind whose operand list has *two* registers in the address and whose
remaining variable fields are not a displacement at all: `Rm`, `option` and `S`
replace the `imm12`/`imm9` slot.

The coarse id `aarch64:ldr/x64-base-regoff` has been the `E-FORM-001` example
since `0.4.0` (`N01b`). This slice does not turn that id into a form. It adds the
concrete rows the kind needs, one per `option`/`S` pair, and keeps the coarse
name absent in every document.

Six measurements decide the slice (all `llvm-mc` 23.1.2, `EXP-0026`):

1. **The two nodes have the same shape.** `LDR_64_ldst_regoff` and
   `STR_64_ldst_regoff` fix `size = 11` (30+2 and 28+2), bit 27 = 1, `VR = 0`,
   bits 25 and 24 = 0, bit 21 = 1 and bits 11–10 = `10`. They leave `Rm` (16+5),
   `option` (13+3), `S` (12+1), `Rn` (5+5) and `Rt` (0+5) variable, and they
   differ only in `opc` (22+2): `01` is `LDR Xt` and `00` is `STR Xt`.
2. **`option` is the keyword, and it also fixes the index width.** Measured
   words carry `011` for `lsl`, `010` for `uxtw`, `110` for `sxtw` and `111` for
   `sxtx`. `lsl`/`sxtx` take an `x` register and `uxtw`/`sxtw` take a `w`; the
   assembler rejects every cross pairing, and the two rejections name the two
   directions (`expected 'lsl' or 'sxtx' …` for an `x` index, `expected 'uxtw'
   or 'sxtw' …` for a `w` one).
3. **`S` is the scale, and only two shifts exist on a 64-bit access.** `S = 0`
   is the bare spelling or `#0`, `S = 1` is `#3`, and the two words differ only
   in bit 12 (`0xf8626820` versus `0xf8627820`). `lsl #1`, `lsl #4`, a bare
   `lsl` and `lsl #-1` are all rejected, so the amount is not a range with two
   holes — it is the single bit, named.
4. **The assembler states the accepted shift set.** `lsl #1` and `lsl #4` are
   rejected with `expected 'lsl' or 'sxtx' with optional shift of #0 or #3`, and
   `lsl #-1` with `expected integer shift amount`. `lsl #0x3` is the same word
   as `lsl #3`.
5. **Register 31 keeps the node's role.** `ldr x0, [sp, x2]` is `0xf8626be0`
   (`Rn = 31`), `ldr x0, [x1, xzr, lsl #3]` is `0xf87f7820` (`Rm = 31`), and
   `ldr x0, [x1, wzr, uxtw]` is `0xf87f4820`. No `sp`-or-`zr` register kind is
   needed: the field is the number and the role is the row's.
6. **The kind has no other spellings.** `ldur x0, [x1, x2]` is read as an
   unscaled offset and rejected (`index must be an integer in range [-256,
   255]`); a register offset with `!` is rejected (`invalid operand for
   instruction`). There is no register-offset pre/post-index form to add later.

## Decision

1. **Sixteen forms are added in `definitions/aarch64/0.15.0.json`**, eight per
   mnemonic: `aarch64:ldr/x64-base-regoff-{lsl,uxtw,sxtw,sxtx}{0,3}` and the
   same eight for `str`. `0.15.0` repeats the 136 `0.14.0` rows unchanged and
   adds these sixteen, so `0.1.0` … `0.14.0` stay frozen and a plan bound to
   `0.14.0` cannot reach a register-offset row (`E-FORM-001`, `N01p`).
2. **`option` and `S` are pinned in the row, not passed as operands.** They are
   byte-affecting decisions (`INV-02`, `ADR-0004`), the `form_id` states them,
   and the generator lists each pinned value explicitly. An operand would let a
   plan write the `option` bits directly, which is the encoding decision the
   table exists to remove.
3. **`lsl #0` is the same form as the bare spelling.** The assembler accepts both
   spellings for `S = 0` (`ldr x0, [x1, x2]` and `ldr x0, [x1, x2, lsl #0]` are
   both `0xf8626820`), exactly as `add`'s `-lsl0` and `-imm6-lsl` with `imm6 = 0`
   are one word (`ADR-0015`). Excluding the spelled-out zero would make an
   operand's spelling choose the form.
4. **The shift amount is not a slot, so `#1` and `#4` are absent forms.** Only
   `S` is a bit; nothing in the row holds an amount of 1 or 4. A plan naming
   `aarch64:ldr/x64-base-regoff-lsl1` is `E-FORM-001` (`N01q`), and no
   `E-RANGE` diagnostic is owed, because there is no field to compare against a
   range.
5. **The slot list is `dest`/`src`, `base`, `index`.** `index` is
   `aarch64.gpr64`/`x64` on the `lsl`/`sxtx` rows and `aarch64.gpr32`/`w32` on
   the `uxtw`/`sxtw` rows, mirroring the width `option` fixes. A `w32` index on a
   `-lsl0` row is `E-OPERAND-001` on `kind` and `target_type` (`N02f`).
6. **A modifier cannot carry the shift.** A `{ "name": "lsl", "value": 3 }`
   entry on the `index` of `-lsl0` is `E-OPERAND-003`: a modifier is a guard and
   never writes a bit, so accepting it would emit the unscaled word and report
   success (`N19b`, `ADR-0015`).
7. **No schema change and no Rust change.** `role: index`, `aarch64.gpr32`/`w32`
   and three register slots all already load; the row is the first `index` slot
   in the AArch64 table, which changes no code path.
8. **Only 64-bit accesses are in this slice.** Both nodes are the `size = 11`
   pair, so `S = 1` means `#3` and the byte scale is 8. The 32-bit, byte and
   halfword register-offset nodes have different `size` values, different
   `S = 1` shift amounts (`#2`, `#1`, `#0`) and, for the signed loads, different
   `opc` meanings; each is its own row set.

## Consequences

- `A64-P17` passes: `A64-P17-regoff` is twenty instructions over the sixteen new
  rows plus four register-31 rows, 80 bytes, and matches `llvm-mc` 23.1.2 with
  no relocations (`EXP-0026` §4).
- The AArch64 table is 152 forms across fifteen documents, now from
  thirty-five encode nodes plus the ten alias verification nodes.
- The AArch64 fixtures become eighteen positive and forty-five negative.
- `EC-14`'s register-offset branch is now carried: all five addressing kinds the
  MRS drop holds have rows, and none is chosen by an operand value.
- `N01b` keeps its meaning: the coarse `aarch64:ldr/x64-base-regoff` is still
  not a form, in every document.

## Alternatives considered

- **One row per mnemonic with `option` and `S` as operands.** Rejected: `option`
  selects the index register's width, so the "operand" would decide which other
  slot kind exists, and `S` decides a bit. That is the shape `ADR-0022` and
  `ADR-0023` rejected (`INV-02`, `ADR-0004`).
- **One `-lsl` row with a three-bit shift amount.** Rejected: only 0 and 3 are
  encodable on a 64-bit access, so the slot would need `excluded` for the other
  six values, and the accepted values would map onto the `S` bit — an operand
  choosing a bit. It would also make `#1` a legal plan value that the assembler
  refuses.
- **A free `option` with a free register class on `index`.** Rejected: `uxtw` and
  `sxtw` consume `w`, `lsl` and `sxtx` consume `x`, and the assembler refuses
  the cross pairings. A free class would emit a legal word for a plan the
  assembler rejects (`INV-07`).
- **Include the 32-bit `w` register-offset rows in the same slice.** Deferred,
  not refused: `size = 10` makes `S = 1` a `#2` scale, so the names and the
  scale are a separate decision with its own measurements.
- **Include `prfm` register offset.** Deferred: the preload has no destination
  register, so its operand list is `base` + `index` with no `dest`/`src` — a
  different row shape, not a fifth `option` value.
- **Add the register-offset pre/post-index forms.** Impossible: the assembler
  rejects `ldr x0, [x1, x2, lsl #3]!`, and the MRS drop has no such node.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| Both nodes leave exactly `Rm`, `option`, `S`, `Rn`, `Rt` variable | MRS `Instructions.json`, node dump in `EXP-0026` §1 | high |
| `option` is `011`/`010`/`110`/`111` for `lsl`/`uxtw`/`sxtw`/`sxtx` | measured words, `EXP-0026` §2 | high |
| The index width follows `option`, and the cross pairings are rejected | accepted/rejected spellings, `EXP-0026` §2–§3 | high |
| `S` moves bit 12 and is the only scale carrier | `0xf8626820` vs `0xf8627820`; `S = 1` is `#3` | high |
| Only `#0` and `#3` are accepted for this `size` | eight accept/reject probes, `EXP-0026` §3 | high |
| Register 31 is `sp` in `Rn` and `xzr`/`wzr` in `Rm` | measured words; the role comes from the node | high |
| There is no writeback or unscaled register offset | assembler rejections, `EXP-0026` §3 | high (assembler surface) |
| The twenty-instruction vector is 80 bytes | `EXP-0026` §4, `llvm-mc` + `llvm-objcopy`, no relocations | high |
| `lsl #1` is `E-FORM-001`, not a range error | the form set has no such row; our contract decision | high (mechanism), **our decision** |

## Review triggers

- 32-bit `w`, byte or halfword register-offset accesses land. `size` changes the
  `S = 1` shift and the `option`-implied width, so each size is a new row set.
- `prfm` register offset appears. Its operand list has no destination register.
- A plan needs an `option`/`S` pair the four keywords cannot spell. That would
  mean the assembly language has a spelling we have not measured.
- A plan needs the index to be an unextended `x` register other than
  `lsl`/`sxtx`. `option = 011` and `111` are the two `x` values that exist.
