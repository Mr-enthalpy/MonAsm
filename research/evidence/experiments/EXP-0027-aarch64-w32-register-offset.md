# EXP-0027 — the 32-bit AArch64 register offset: `size = 10`, `S` is `#2`

- Date: 2026-11-05
- Question: what changes when the register-offset rows address 4 bytes instead of
  8 — the `option` mapping, the accepted shift amounts, the register widths, and
  the encoded words — and what does the assembler refuse?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The field layout comes from the
  MRS node and the accepted words from the assembler; the meaning of register 31
  in each slot is taken from the node's role and confirmed by the measured bits.

## 1. The nodes

`LDR_32_ldst_regoff` and `STR_32_ldst_regoff` are the 64-bit pair with
`size = 10`. Every field position and every other fixed bit is unchanged, and
the `opc` split is the same (`01` is `LDR Wt`, `00` is `STR Wt`). `start+width`
counts from bit 0 of the 32-bit word:

### `LDR_32_ldst_regoff` → `aarch64:ldr/w32-base-regoff-*`

| Field | start+width | Value | Our use |
|---|---|---|---|
| `size` | 30+2 | `10` | fixed — 32-bit access |
| — | 28+2 | `11` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed (no SIMD/FP) |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `0` | fixed |
| `opc` | 22+2 | `01` | fixed — `LDR Wt` |
| — | 21+1 | `1` | fixed — the register-offset kind bit |
| `Rm` | 16+5 | `xxxxx` | slot `index` |
| `option` | 13+3 | `xxx` | pinned per row (`011`/`010`/`110`/`111`) |
| `S` | 12+1 | `x` | pinned per row (`0`/`1`) |
| — | 11+2 | `10` | fixed — the register-offset kind bits |
| `Rn` | 5+5 | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | slot `dest` |

`STR_32_ldst_regoff` is the same table with `opc = 00` (`STR Wt`) and `Rt` as the
stored register (`src`). With `option` and `S` zeroed the remaining fixed pattern
is `0xb8600800` for the load and `0xb8200800` for the store; with `option = 011`
and `S = 0` the load template is `0xb8606800`.

Only `size` and `opc` differ from `EXP-0026`'s nodes, so the slice is again
`Rm`/`option`/`S`/`Rn`/`Rt`, and the only new decision is which amount `S = 1`
names on this `size`.

## 2. The fields, measured

One instruction per run at offset 0, `llvm-mc -triple=aarch64 -filetype=obj`,
then `llvm-objcopy -O binary --only-section=.text`:

| Source | Word | `option` | `S` | Reading |
|---|---|---|---|---|
| `ldr w0, [x1, x2]` | `0xb8626820` | `011` | 0 | `lsl` with `#0` |
| `ldr w0, [x1, x2, lsl #0]` | `0xb8626820` | `011` | 0 | same word as the bare spelling |
| `ldr w0, [x1, x2, lsl #2]` | `0xb8627820` | `011` | 1 | `S` is bit 12, nothing else moved |
| `ldr w0, [x1, w2, uxtw]` | `0xb8624820` | `010` | 0 | `w` index, zero-extended |
| `ldr w0, [x1, w2, uxtw #2]` | `0xb8625820` | `010` | 1 | |
| `ldr w0, [x1, w2, sxtw]` | `0xb862c820` | `110` | 0 | `w` index, sign-extended |
| `ldr w0, [x1, w2, sxtw #2]` | `0xb862d820` | `110` | 1 | |
| `ldr w0, [x1, x2, sxtx]` | `0xb862e820` | `111` | 0 | `x` index, sign-extended |
| `ldr w0, [x1, x2, sxtx #2]` | `0xb862f820` | `111` | 1 | |
| `str w0, [x1, x2]` | `0xb8226820` | `011` | 0 | `opc = 00` |
| `str w0, [x1, x2, lsl #2]` | `0xb8227820` | `011` | 1 | |

The four `option` values read straight off bits 15–13, exactly as at 64 bits;
`0xb8626820` and `0xb8627820` differ by `0x1000`, so bit 12 is still the only
scale carrier. The words are the 64-bit set with the top byte `0xf8` replaced by
`0xb8`, which is what `size = 10` does to bits 31–30.

**Spelled-out zeros are the same instruction.** `lsl #0`, `uxtw #0`, `sxtw #0`
and `sxtx #0` produce exactly the bare words above, and `lsl #0x2` produces the
same word as `lsl #2`, so the suffix states the amount the row encodes and never
a second form.

**The scale is the access size, so it is `#2` here.** `size = 10` is a 4-byte
access and `S = 1` multiplies the index by 4. That is the whole difference from
`EXP-0026`: same fields, same keywords, same widths, one lower shift.

**Register 31 keeps the node's role.** `Rn` and `Rm` are still 64-bit address and
index registers; only `Rt` is `w`:

| Source | Word | Field | Meaning |
|---|---|---|---|
| `ldr w0, [sp, x2]` | `0xb8626be0` | `Rn = 31` | `sp` |
| `ldr w0, [x1, xzr, lsl #2]` | `0xb87f7820` | `Rm = 31`, `S = 1` | `xzr`, scaled by 4 |
| `ldr w0, [x1, wzr, uxtw]` | `0xb87f4820` | `Rm = 31`, `option = 010` | `wzr` |
| `str w0, [sp, x2, lsl #2]` | `0xb8227be0` | `Rn = 31`, `S = 1` | `sp` |

No `sp`-or-`zr` operand kind is needed: `reg_number` writes the five bits and the
row's role supplies the meaning, as on the `0.4.0` and `0.15.0` rows.

## 3. What the assembler rejects

One instruction per run, same command:

| Source | Diagnostic |
|---|---|
| `ldr w0, [x1, x2, lsl #1]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #2` |
| `ldr w0, [x1, x2, lsl #3]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #2` |
| `ldr w0, [x1, x2, lsl #4]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #2` |
| `ldr w0, [x1, w2, lsl #2]` | `expected 'uxtw' or 'sxtw' with optional shift of #0 or #2` |
| `ldr w0, [x1, x2, uxtw]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #2` |
| `ldr w0, [x1, x2, sxtw]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #2` |
| `ldr w0, [x1, w2, uxtw #3]` | `expected 'uxtw' or 'sxtw' with optional shift of #0 or #2` |
| `ldr w0, [x1, x2, sxtx #3]` | `expected 'lsl' or 'sxtx' with optional shift of #0 or #2` |
| `ldr w0, [x1, x2, lsl #2]!` | `invalid operand for instruction` |
| `str w0, [x1, x2, lsl #2]!` | `invalid operand for instruction` |
| `ldur w0, [x1, x2]` | `index must be an integer in range [-256, 255]` |

The accepted set is `#0` and `#2` only, and the assembler states it in its own
message; `#1` is not a smaller legal scale, it is a spelling of nothing. The
`x`-index vs `w`-index split is enforced in both directions exactly as at 64
bits, and the 32-bit kind has no writeback or unscaled register form either.

## 4. The vector

Input (LF, trailing newline; 470 bytes,
`sha256:14762aed10d0fde0f50061c368591bfd2b26d485d669f265c4a02fb37545a24a`):

```text
  ldr w0, [x1, x2]
  ldr w1, [x2, x3, lsl #2]
  ldr w2, [x3, w4, uxtw]
  ldr w3, [x4, w5, uxtw #2]
  ldr w4, [x5, w6, sxtw]
  ldr w5, [x6, w7, sxtw #2]
  ldr w6, [x7, x8, sxtx]
  ldr w7, [x8, x9, sxtx #2]
  str w0, [x1, x2]
  str w1, [x2, x3, lsl #2]
  str w2, [x3, w4, uxtw]
  str w3, [x4, w5, uxtw #2]
  str w4, [x5, w6, sxtw]
  str w5, [x6, w7, sxtw #2]
  str w6, [x7, x8, sxtx]
  str w7, [x8, x9, sxtx #2]
  ldr w0, [sp, x2]
  ldr w0, [x1, xzr, lsl #2]
  str w0, [sp, x2, lsl #2]
  ldr w0, [x1, wzr, uxtw]
```

The first sixteen lines visit each new row once. Registers 0–9 keep every field
value distinct, so a placement slip shows up in the word. The last four lines put
31 in `Rn` or `Rm`, which is the only way the vector pins that the index slot is a
plain `reg_number` and not a `sp`/`zr` kind.

`llvm-readobj -r` prints an empty relocation list and the source names no
symbols, so no linker is involved.

| Offset | Bytes | Word | `llvm-objdump` |
|---|---|---|---|
| 0 | `20 68 62 b8` | `0xb8626820` | `ldr w0, [x1, x2]` |
| 4 | `41 78 63 b8` | `0xb8637841` | `ldr w1, [x2, x3, lsl #2]` |
| 8 | `62 48 64 b8` | `0xb8644862` | `ldr w2, [x3, w4, uxtw]` |
| 12 | `83 58 65 b8` | `0xb8655883` | `ldr w3, [x4, w5, uxtw #2]` |
| 16 | `a4 c8 66 b8` | `0xb866c8a4` | `ldr w4, [x5, w6, sxtw]` |
| 20 | `c5 d8 67 b8` | `0xb867d8c5` | `ldr w5, [x6, w7, sxtw #2]` |
| 24 | `e6 e8 68 b8` | `0xb868e8e6` | `ldr w6, [x7, x8, sxtx]` |
| 28 | `07 f9 69 b8` | `0xb869f907` | `ldr w7, [x8, x9, sxtx #2]` |
| 32 | `20 68 22 b8` | `0xb8226820` | `str w0, [x1, x2]` |
| 36 | `41 78 23 b8` | `0xb8237841` | `str w1, [x2, x3, lsl #2]` |
| 40 | `62 48 24 b8` | `0xb8244862` | `str w2, [x3, w4, uxtw]` |
| 44 | `83 58 25 b8` | `0xb8255883` | `str w3, [x4, w5, uxtw #2]` |
| 48 | `a4 c8 26 b8` | `0xb826c8a4` | `str w4, [x5, w6, sxtw]` |
| 52 | `c5 d8 27 b8` | `0xb827d8c5` | `str w5, [x6, w7, sxtw #2]` |
| 56 | `e6 e8 28 b8` | `0xb828e8e6` | `str w6, [x7, x8, sxtx]` |
| 60 | `07 f9 29 b8` | `0xb829f907` | `str w7, [x8, x9, sxtx #2]` |
| 64 | `e0 6b 62 b8` | `0xb8626be0` | `ldr w0, [sp, x2]` |
| 68 | `20 78 7f b8` | `0xb87f7820` | `ldr w0, [x1, xzr, lsl #2]` |
| 72 | `e0 7b 22 b8` | `0xb8227be0` | `str w0, [sp, x2, lsl #2]` |
| 76 | `20 48 7f b8` | `0xb87f4820` | `ldr w0, [x1, wzr, uxtw]` |

Output: 80 bytes,
`sha256:8ae39fb0113117ff60296f52398b95630d2349e2a3efd0667c43d7bbc24012ca`,
`bytes_hex`
`206862b8417863b8624864b8835865b8a4c866b8c5d867b8e6e868b807f969b8206822b8417823b8624824b8835825b8a4c826b8c5d827b8e6e828b807f929b8e06b62b820787fb8e07b22b820487fb8`.

## 5. What this fixes, and what it does not

Fixes:

- the two 32-bit templates and the five field placements, derived from the MRS
  fields by the generator;
- the `option` → keyword/width mapping at `size = 10`, measured in both
  directions;
- `S` as the only scale carrier, with `#0`/`#2` as the complete accepted set on a
  4-byte access;
- the operand list: `dest`/`src` `w32`, `base` `x64`, `index` per `option`;
- the register-31 role: `sp` in `Rn`, `xzr`/`wzr` in `Rm`;
- the negative evidence: `0.15.0` has no such row (`E-FORM-001`), `-lsl3` has no
  row (`E-FORM-001`), an `x64` destination or a `w32` index on `-lsl0` is
  `E-OPERAND-001`, and a modifier carrying `lsl #2` is `E-OPERAND-003`.

Does not fix:

- **byte and halfword register offset.** `size = 00`/`01` makes `S = 1` a
  `#0`/`#1` scale, and the signed loads add `opc` meanings; no row is added.
- **`LDRSW`/`LDRSB`/`LDRSH` register offset.** Same `size = 10` for the `w`
  forms, but `opc` changes and the destination width is not the access width.
- **`prfm` register offset.** The preload has no destination register.
- **writeback or unscaled register offset.** No node and no accepted spelling.
- **the `option` values `000`/`001`/`100`/`101`.** No keyword reaches them;
  whether they decode to something is not tested here.

## 6. Result

The rows ship in `definitions/aarch64/0.16.0.json`, which repeats the 152
`0.15.0` forms and adds sixteen:

```text
definition  definitions/aarch64/0.16.0.json
namespace   monasm.isa.aarch64
version     0.16.0
forms       168
digest      sha256:1e83c6cad91594e8315500f39d0bcffa235edc90c5f47c012555c077a8dbc457
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 80 bytes above and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P18-w32regoff` | twenty instructions, sixteen new rows | 80 bytes, `sha256:8ae39fb0…` |
| `N01r-w32-regoff-absent-in-previous-version` | `-lsl0` against `0.15.0` | `E-FORM-001` |
| `N01s-absent-w32-regoff-shift-three` | `-lsl3` against `0.16.0` | `E-FORM-001` |
| `N02g-w-index-on-w32-lsl-row` | `w32` index on `-lsl0` | `E-OPERAND-001` on `kind` and `target_type` |
| `N02h-x-dest-on-w32-row` | `x64` destination on `-lsl0` | `E-OPERAND-001` on `kind` and `target_type` |
| `N19c-w32-regoff-modifier-is-not-a-carrier` | `lsl #2` as a modifier on `-lsl0` | `E-OPERAND-003` |

`N01b-absent-register-offset-form` keeps its meaning: the coarse
`aarch64:ldr/x64-base-regoff` is not a form in any document, before or after this
slice.
