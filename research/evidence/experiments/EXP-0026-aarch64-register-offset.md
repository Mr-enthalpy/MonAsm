# EXP-0026 — AArch64 register offset: `option`, `S`, `Rm`

- Date: 2026-11-05
- Question: which fields name the register-offset kind, what does each `option`
  value select, which shift amounts exist, which spellings does the assembler
  refuse, and what does register 31 mean in each slot?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The field layout comes from the
  MRS node and the accepted words from the assembler; the meaning of register 31
  in each slot is taken from the node's role and confirmed by the measured bits.

## 1. The nodes

`LDR_64_ldst_regoff` and `STR_64_ldst_regoff` have identical encodings except
`opc`. `start+width` counts from bit 0 of the 32-bit word:

### `LDR_64_ldst_regoff` → `aarch64:ldr/x64-base-regoff-*`

| Field | start+width | Value | Our use |
|---|---|---|---|
| `size` | 30+2 | `11` | fixed — 64-bit access |
| — | 28+2 | `11` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed (no SIMD/FP) |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `0` | fixed |
| `opc` | 22+2 | `01` | fixed — `LDR Xt` |
| — | 21+1 | `1` | fixed — the register-offset kind bit |
| `Rm` | 16+5 | `xxxxx` | slot `index` |
| `option` | 13+3 | `xxx` | pinned per row (`011`/`010`/`110`/`111`) |
| `S` | 12+1 | `x` | pinned per row (`0`/`1`) |
| — | 11+2 | `10` | fixed — the register-offset kind bits |
| `Rn` | 5+5 | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | slot `dest` |

`STR_64_ldst_regoff` is the same table with `opc = 00` (`STR Xt`) and `Rt` as the
stored register (`src`). With `option` and `S` zeroed the remaining fixed pattern
is `0xf8600800` for the load and `0xf8200800` for the store; with `option = 011`
and `S = 0` the load template is `0xf8606800`.

Both nodes leave the same five fields variable, so every row is one `option`/`S`
pair. `option` is three bits wide but the assembly language has four keywords,
and each keyword also fixes the index register's width, which is why the rows
cannot be collapsed into one `option` operand.

## 2. The fields, measured

One instruction per run at offset 0, `llvm-mc -triple=aarch64 -filetype=obj`,
then `llvm-objcopy -O binary --only-section=.text`:

| Source | Word | `option` | `S` | Reading |
|---|---|---|---|---|
| `ldr x0, [x1, x2]` | `0xf8626820` | `011` | 0 | `lsl` with `#0` |
| `ldr x0, [x1, x2, lsl #0]` | `0xf8626820` | `011` | 0 | same word as the bare spelling |
| `ldr x0, [x1, x2, lsl #3]` | `0xf8627820` | `011` | 1 | `S` is bit 12, nothing else moved |
| `ldr x0, [x1, w2, uxtw]` | `0xf8624820` | `010` | 0 | `w` index, zero-extended |
| `ldr x0, [x1, w2, uxtw #3]` | `0xf8625820` | `010` | 1 | |
| `ldr x0, [x1, w2, sxtw]` | `0xf862c820` | `110` | 0 | `w` index, sign-extended |
| `ldr x0, [x1, w2, sxtw #3]` | `0xf862d820` | `110` | 1 | |
| `ldr x0, [x1, x2, sxtx]` | `0xf862e820` | `111` | 0 | `x` index, sign-extended |
| `ldr x0, [x1, x2, sxtx #3]` | `0xf862f820` | `111` | 1 | |
| `str x0, [x1, x2]` | `0xf8226820` | `011` | 0 | `opc = 00` |
| `str x0, [x1, x2, lsl #3]` | `0xf8227820` | `011` | 1 | |

The four `option` values are read straight off the words: bits 15–13 are `011`,
`010`, `110` and `111`. The bit that separates a scaled row from an unscaled one
is bit 12 only; `0xf8626820` and `0xf8627820` differ by `0x1000`.

**Spelled-out zeros are the same instruction.** `lsl #0`, `uxtw #0`, `sxtw #0`
and `sxtx #0` produce exactly the bare words above, and `lsl #0x3` produces the
same word as `lsl #3`. This is the `-lsl0`/`-imm6-lsl` situation of `ADR-0015`
repeated on a second field.

**The shift is the access size, so it is 0 or 3 here.** `size = 11` is an 8-byte
access, and `S = 1` multiplies the index by 8. The 32-bit nodes show the same
rule with a different amount: `ldr w0, [x1, x2, lsl #2]` is `0xb8627820` and
`ldr w0, [x1, w2, uxtw #2]` is `0xb8625820`, i.e. the same field values with
`size = 10` and the `#2` scale.

**Register 31 keeps the node's role.** The field is a 5-bit number; whether it
means `sp` or `xzr`/`wzr` comes from the slot, not from the row:

| Source | Word | Field | Meaning |
|---|---|---|---|
| `ldr x0, [sp, x2]` | `0xf8626be0` | `Rn = 31` | `sp` |
| `ldr x0, [x1, xzr]` | `0xf87f6820` | `Rm = 31` | `xzr` |
| `ldr x0, [x1, xzr, lsl #3]` | `0xf87f7820` | `Rm = 31`, `S = 1` | `xzr`, scaled |
| `ldr x0, [x1, wzr, uxtw]` | `0xf87f4820` | `Rm = 31`, `option = 010` | `wzr` |
| `str x0, [sp, x2, lsl #3]` | `0xf8227be0` | `Rn = 31`, `S = 1` | `sp` |

No `sp`-or-`zr` operand kind is needed: `reg_number` writes the five bits and the
row's role supplies the meaning (`aarch64.gpr64`/`x64` and
`aarch64.gpr32`/`w32` already behave this way on the `0.4.0` rows).

## 3. What the assembler rejects

One instruction per run, same command:

| Source | Diagnostic |
|---|---|
| `ldr x0, [x1, x2, lsl]` | `expected #imm after shift specifier` |
| `ldr x0, [x1, x2, lsl #1]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #3` |
| `ldr x0, [x1, x2, lsl #4]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #3` |
| `ldr x0, [x1, x2, lsl #-1]` | `expected integer shift amount` |
| `ldr x0, [x1, x2, uxtw]` | `expected 'lsl' or 'sxtx' …` |
| `ldr x0, [x1, x2, sxtw]` | `expected 'lsl' or 'sxtx' …` |
| `ldr x0, [x1, x2, uxtb]` | `expected 'lsl' or 'sxtx' …` |
| `ldr x0, [x1, x2, sxtb]` | `expected 'lsl' or 'sxtx' …` |
| `ldr x0, [x1, x2, uxtx]` | `expected 'lsl' or 'sxtx' …` |
| `ldr x0, [x1, w2, lsl #3]` | `expected 'uxtw' or 'sxtw' with optional shift of #0 or #3` |
| `ldr x0, [x1, w2, sxtw #4]` | `expected 'uxtw' or 'sxtw' …` |
| `ldur x0, [x1, x2]` | `index must be an integer in range [-256, 255]` |
| `ldr x0, [x1, x2, lsl #3]!` | `invalid operand for instruction` |
| `ldr x0, [x1, x2, uxtw #3]!` | `expected 'lsl' or 'sxtx' …` (the `!` is not reached) |

Two things follow. First, the **only** amounts a 64-bit register offset can carry
are 0 and 3, and the assembler enumerates them in its own message; `#1` and `#4`
are not range errors with a legal field value, they are spellings of nothing.
Second, the `x`-index vs `w`-index split is enforced in both directions, so the
index's width is part of the row, not a plan choice.

`ldur x0, [x1, x2]` shows the other side of the same coin: the unscaled
mnemonic does not accept a register index at all, so "unscaled register offset"
is not a kind this table is postponing.

## 4. The vector

Input (LF, trailing newline; 510 bytes,
`sha256:17ddf5e13cafcd23f9c14b7eb673be91e5ebf677593e555839b0efcd700ea4f9`):

```text
  ldr x0, [x1, x2]
  ldr x1, [x2, x3, lsl #3]
  ldr x2, [x3, w4, uxtw]
  ldr x3, [x4, w5, uxtw #3]
  ldr x4, [x5, w6, sxtw]
  ldr x5, [x6, w7, sxtw #3]
  ldr x6, [x7, x8, sxtx]
  ldr x7, [x8, x9, sxtx #3]
  str x0, [x1, x2]
  str x1, [x2, x3, lsl #3]
  str x2, [x3, w4, uxtw]
  str x3, [x4, w5, uxtw #3]
  str x4, [x5, w6, sxtw]
  str x5, [x6, w7, sxtw #3]
  str x6, [x7, x8, sxtx]
  str x7, [x8, x9, sxtx #3]
  ldr x0, [sp, x2]
  ldr x0, [x1, xzr, lsl #3]
  str x0, [sp, x2, lsl #3]
  ldr x0, [x1, wzr, uxtw]
```

The first sixteen lines visit each new row once. Registers 0–9 keep every field
value distinct on those lines, so a placement slip shows up in the word. The last
four lines put 31 in `Rn` or `Rm`, which is the only way the vector pins that the
index slot is a plain `reg_number` and not a `sp`/`zr` kind.

`llvm-readobj -r` prints an empty relocation list and the source names no
symbols, so no linker is involved.

| Offset | Bytes | Word | `llvm-objdump` |
|---|---|---|---|
| 0 | `20 68 62 f8` | `0xf8626820` | `ldr x0, [x1, x2]` |
| 4 | `41 78 63 f8` | `0xf8637841` | `ldr x1, [x2, x3, lsl #3]` |
| 8 | `62 48 64 f8` | `0xf8644862` | `ldr x2, [x3, w4, uxtw]` |
| 12 | `83 58 65 f8` | `0xf8655883` | `ldr x3, [x4, w5, uxtw #3]` |
| 16 | `a4 c8 66 f8` | `0xf866c8a4` | `ldr x4, [x5, w6, sxtw]` |
| 20 | `c5 d8 67 f8` | `0xf867d8c5` | `ldr x5, [x6, w7, sxtw #3]` |
| 24 | `e6 e8 68 f8` | `0xf868e8e6` | `ldr x6, [x7, x8, sxtx]` |
| 28 | `07 f9 69 f8` | `0xf869f907` | `ldr x7, [x8, x9, sxtx #3]` |
| 32 | `20 68 22 f8` | `0xf8226820` | `str x0, [x1, x2]` |
| 36 | `41 78 23 f8` | `0xf8237841` | `str x1, [x2, x3, lsl #3]` |
| 40 | `62 48 24 f8` | `0xf8244862` | `str x2, [x3, w4, uxtw]` |
| 44 | `83 58 25 f8` | `0xf8255883` | `str x3, [x4, w5, uxtw #3]` |
| 48 | `a4 c8 26 f8` | `0xf826c8a4` | `str x4, [x5, w6, sxtw]` |
| 52 | `c5 d8 27 f8` | `0xf827d8c5` | `str x5, [x6, w7, sxtw #3]` |
| 56 | `e6 e8 28 f8` | `0xf828e8e6` | `str x6, [x7, x8, sxtx]` |
| 60 | `07 f9 29 f8` | `0xf829f907` | `str x7, [x8, x9, sxtx #3]` |
| 64 | `e0 6b 62 f8` | `0xf8626be0` | `ldr x0, [sp, x2]` |
| 68 | `20 78 7f f8` | `0xf87f7820` | `ldr x0, [x1, xzr, lsl #3]` |
| 72 | `e0 7b 22 f8` | `0xf8227be0` | `str x0, [sp, x2, lsl #3]` |
| 76 | `20 48 7f f8` | `0xf87f4820` | `ldr x0, [x1, wzr, uxtw]` |

Output: 80 bytes,
`sha256:d7f2ba579c94ca0ca62ddc2193da1080bdf13e5aeef794a6b3488423e2763091`,
`bytes_hex`
`206862f8417863f8624864f8835865f8a4c866f8c5d867f8e6e868f807f969f8206822f8417823f8624824f8835825f8a4c826f8c5d827f8e6e828f807f929f8e06b62f820787ff8e07b22f820487ff8`.

## 5. What this fixes, and what it does not

Fixes:

- the two templates and the five field placements, derived from the MRS fields
  by the generator;
- the `option` → keyword/width mapping, measured in both directions;
- `S` as the only scale carrier, with `#0`/`#3` as the complete accepted set on
  a 64-bit access;
- the operand list: `dest`/`src`, `base`, `index`, with `index`'s kind following
  the row;
- the register-31 role: `sp` in `Rn`, `xzr`/`wzr` in `Rm`;
- the negative evidence: `0.14.0` has no such row (`E-FORM-001`), `lsl #1` has
  no row (`E-FORM-001`), a `w32` index on `-lsl0` is `E-OPERAND-001`, and a
  modifier carrying `lsl #3` is `E-OPERAND-003`.

Does not fix:

- **32-bit / byte / halfword register offset.** `size` changes the `S = 1` shift
  (`#2`, `#1`, `#0`) and, for the signed loads, the `opc` meaning. Measured for
  the 32-bit `lsl`/`uxtw` pair only; no row is added.
- **`prfm` register offset.** The preload has no destination register, so its
  operand list differs.
- **writeback or unscaled register offset.** No node and no accepted spelling.
- **the `option` values `000`/`001`/`100`/`101`.** No keyword reaches them, so no
  row can name them; whether they decode to something is not tested here.

## 6. Result

The rows ship in `definitions/aarch64/0.15.0.json`, which repeats the 136
`0.14.0` forms and adds sixteen:

```text
definition  definitions/aarch64/0.15.0.json
namespace   monasm.isa.aarch64
version     0.15.0
forms       152
digest      sha256:422ebb83b897b18e010da37539796b0b97cfc9018a47209fc4a6ddc5b14af5d3
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 80 bytes above and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P17-regoff` | twenty instructions, sixteen new rows | 80 bytes, `sha256:d7f2ba57…` |
| `N01p-regoff-absent-in-previous-version` | `-lsl0` against `0.14.0` | `E-FORM-001` |
| `N01q-absent-regoff-shift-one` | `-lsl1` against `0.15.0` | `E-FORM-001` |
| `N02f-w-index-on-lsl-row` | `w32` index on `-lsl0` | `E-OPERAND-001` on `kind` and `target_type` |
| `N19b-regoff-modifier-is-not-a-carrier` | `lsl #3` as a modifier on `-lsl0` | `E-OPERAND-003` |

`N01b-absent-register-offset-form` keeps its meaning: the coarse
`aarch64:ldr/x64-base-regoff` is not a form in any document, before or after this
slice.
