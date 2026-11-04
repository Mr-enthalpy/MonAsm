# EXP-0018 — AArch64 extended-register second source: eight keywords, one 3-bit amount

- Date: 2026-11-04
- Question: on `add x0, x1, w2, uxtw #3`, which bits carry the extend keyword and
  the amount, which keywords pair with which source width, and which `imm3`
  values exist?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the legal spellings
  come from the MRS node and the assembler; what each extend *computes* is not
  claimed here, because it changes no bit.

## 1. The node

`start+width` counts from bit 0 of the 32-bit word.

### `ADD_64_addsub_ext` → the eight `aarch64:add/…-imm3-*` rows

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed (64-bit) |
| `op` | 30+1 | `0` | fixed (`add`) |
| `S` | 29+1 | `0` | fixed (no flags) |
| `op1` | 28+1 | `0` | fixed |
| — | 25+3 | `101` | fixed |
| — | 24+1 | `1` | fixed |
| `opt` | 22+2 | `00` | fixed — this is what `ADD_64_addsub_shift` leaves as `shift` |
| — | 21+1 | `1` | fixed — the bit that separates this node from the shifted one |
| `Rm` | 16+5 | `xxxxx` | slot `src2`, width depends on the keyword |
| `option` | 13+3 | `xxx` | **pinned** per row: `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7` |
| `imm3` | 10+3 | `xxx` | slot `imm`, unsigned, `0…4`, with `5…7` excluded |
| `Rn` | 5+5 | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

### Not in the table

- `SUB_64_addsub_ext`: the same layout with `op = 1` (read, not used).
- `ADD_32_addsub_ext` (read, not used): `sf = 0`, and its `option` field is
  three bits with an extra `opt` at 22+2 — a 32-bit destination has its own
  operand-width rule.
- `ADDS_64_addsub_ext` / `SUBS_64_addsub_ext` (`S = 1`, the `cmn`/`cmp`
  spellings).

## 2. The spellings, measured

`llvm-mc -triple=aarch64 -show-encoding`, one run per table row.

### Accepted

| Source | Bytes | Word | `option` | `imm3` |
|---|---|---|---|---|
| `add x0, x1, w2, uxtb #0` | `20 00 22 8b` | `0x8b220020` | 0 | 0 |
| `add x0, x1, w2, uxtb #4` | `20 10 22 8b` | `0x8b221020` | 0 | 4 |
| `add x0, x1, w2, uxth #4` | `20 30 22 8b` | `0x8b223020` | 1 | 4 |
| `add x0, x1, w2, uxtw #3` | `20 4c 22 8b` | `0x8b224c20` | 2 | 3 |
| `add x0, x1, w2, sxtb #4` | `20 90 22 8b` | `0x8b229020` | 4 | 4 |
| `add x0, x1, w2, sxth #4` | `20 b0 22 8b` | `0x8b22b020` | 5 | 4 |
| `add x0, x1, w2, sxtw #3` | `20 cc 22 8b` | `0x8b22cc20` | 6 | 3 |
| `add x0, x1, x2, uxtx #0` | `20 60 22 8b` | `0x8b226020` | 3 | 0 |
| `add x0, x1, x2, uxtx #4` | `20 70 22 8b` | `0x8b227020` | 3 | 4 |
| `add x0, x1, x2, sxtx #3` | `20 ec 22 8b` | `0x8b22ec20` | 7 | 3 |

The first ten rows pin the field split: every word has the same `Rd`, `Rn` and
`Rm`, and differs only in bits 15–13 (`option`) and bits 12–10 (`imm3`). The
`uxtb #0` row and the plain `add` (`0x8b020020`) differ in bit 21 as well, which
is the node boundary rather than a field.

### Rejected

| Source | Assembler message (first line) |
|---|---|
| `add x0, x1, w2, uxtb #5` | `expected '[su]xt[bhw]' with optional integer in range [0, 4]` |
| `add x0, x1, x2, uxtx #5` | `expected 'sxtx' 'uxtx' or 'lsl' with optional integer in range [0, 4]` |
| `add x0, x1, w2, uxtx #3` | `expected '[su]xt[bhw]' with optional integer in range [0, 4]` |
| `add x0, x1, x2, uxtw #3` | `expected 'sxtx' 'uxtx' or 'lsl' with optional integer in range [0, 4]` |
| `add x0, x1, x2, uxtb #3` | `expected 'sxtx' 'uxtx' or 'lsl' with optional integer in range [0, 4]` |
| `add x0, x1, w2, lsl #3` | `expected '[su]xt[bhw]' with optional integer in range [0, 4]` |
| `add x0, x1, w2, uxtb #-1` | `expected integer shift amount` |

Two facts fall out. The six `[su]xt[bhw]` keywords take a `w` source and the two
`[su]xtx` keywords take an `x` source; the message for a wrong pairing is the
other keyword set, which is the assembler offering the legal set for that
register width. `lsl` is not part of this node at all: on an `x` source it is the
shifted-register row (`0x8b020c20` for `#3`), and on a `w` source it does not
exist.

`imm3` is `0…4`: the field is three bits, so values `5`, `6`, `7` are inside it but
not allocated to add/sub extended.

**The amount is optional and means 0.** `llvm-mc -show-encoding` prints
`add x0, x1, w2, uxtb #0` back as `add x0, x1, w2, uxtb` — the same word as
leaving the amount out. So `imm3 = 0` is a legal statement and must not be
excluded from the slot.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 226 bytes,
`sha256:1ab62158f5b77e765e95434eb8949903431394666504bd277ca409bbd0b40c95`):

```text
  add x3, x4, w5, uxtb #0
  add x6, x7, w8, uxth #4
  add x9, x10, w11, uxtw #3
  add x12, x13, w14, sxtb #4
  add x15, x16, w17, sxth #0
  add x18, x19, w20, sxtw #4
  add x21, x22, x23, uxtx #0
  add x24, x25, x26, sxtx #4
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is a register or an
immediate, so no linker is involved. `.text` is 32 bytes.

| Offset | Bytes | Word | `option` / keyword | `imm3` | Registers `Rm`/`Rn`/`Rd` |
|---|---|---|---|---|---|
| 0 | `83 00 25 8b` | `0x8b250083` | 0 / `uxtb` | 0 | 5 / 4 / 3 |
| 4 | `e6 30 28 8b` | `0x8b2830e6` | 1 / `uxth` | 4 | 8 / 7 / 6 |
| 8 | `49 4d 2b 8b` | `0x8b2b4d49` | 2 / `uxtw` | 3 | 11 / 10 / 9 |
| 12 | `ac 91 2e 8b` | `0x8b2e91ac` | 4 / `sxtb` | 4 | 14 / 13 / 12 |
| 16 | `0f a2 31 8b` | `0x8b31a20f` | 5 / `sxth` | 0 | 17 / 16 / 15 |
| 20 | `72 d2 34 8b` | `0x8b34d272` | 6 / `sxtw` | 4 | 20 / 19 / 18 |
| 24 | `d5 62 37 8b` | `0x8b3762d5` | 3 / `uxtx` | 0 | 23 / 22 / 21 |
| 28 | `38 f3 3a 8b` | `0x8b3af338` | 7 / `sxtx` | 4 | 26 / 25 / 24 |

Output: 32 bytes,
`sha256:545e77fc75fb8899b28c9ecfaefb31f9426ad1c58be56c1ca73a90eaa1b3e38e`,
`bytes_hex` `8300258be630288b494d2b8bac912e8b0fa2318b72d2348bd562378b38f33a8b`.

The vector pins each decision independently:

- all eight `option` values, in one step of `1, 2, 4, 5, 6` (the `w` keywords) and
  `3, 7` (the `x` keywords), so the register-class split is visible in the bytes;
- every row uses a distinct `Rd`/`Rn`/`Rm`, so a register-field slip cannot hide
  behind another row's registers;
- `imm3` at both ends (`0` and `4`) on both classes: `uxtb #0` and `sxth #0` on
  `w`, `uxtx #0` on `x`; `uxth #4`, `sxtb #4`, `sxtw #4`, `sxtx #4` on the other
  end.

## 4. What this fixes, and what it does not

Fixes:

- the eight templates (`0x8b200000` plus `option << 13`) and one slot placement
  (`imm3` at `[10,3]`), derived from the MRS fields by the generator;
- the rule: the keyword is the `form_id` and picks the source width; the amount is
  field content in `0…4`, with `5…7` excluded and `8` outside the field;
- the negative evidence: `imm3 = 8` is `E-RANGE-001` (`N03-imm3`), `imm3 = 5` is
  `E-RANGE-004` (`N16c`), a `w` operand on `-imm3-uxtx` is `E-OPERAND-001`
  (`N02b`), and `aarch64:sub/x64-x64-w32-imm3-uxtb` is `E-FORM-001` (`N01f`).

Does not fix:

- **`sub`, `adds`/`subs` and the 32-bit node.** Other nodes.
- **the `S = 1` flag-setting rows**, including the `cmp`/`cmn` aliases.
- **what an extend computes.** Semantics, not bytes.
- **a symbol in `imm3`.** None of the eight rows has a fixup.

## 5. Result

The rows ship in `definitions/aarch64/0.7.0.json`, which repeats the eighteen
earlier forms and adds eight:

```text
definition  definitions/aarch64/0.7.0.json
namespace   monasm.isa.aarch64
version     0.7.0
forms       26
digest      sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 32 bytes above with no fixup records, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P9-extend-modifier` | eight instructions, eight forms | 32 bytes, `sha256:545e77fc…` |
| `N03-imm3-out-of-range` | `imm3 = 8` on `-imm3-uxtb` | `E-RANGE-001`, `min 0`, `max 7` |
| `N16c-imm3-excluded` | `imm3 = 5` on `-imm3-uxtb` | `E-RANGE-004`, `excluded 5,6,7` |
| `N02b-w-source-in-shift-form` | `w32` operand on `-imm6-lsl` | `E-OPERAND-001` ×2 (kind, target_type) |
| `N01f-absent-sub-ext` | `aarch64:sub/x64-x64-w32-imm3-uxtb` | `E-FORM-001` |
