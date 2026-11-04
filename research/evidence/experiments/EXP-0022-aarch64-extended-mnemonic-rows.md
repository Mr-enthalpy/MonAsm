# EXP-0022 — the extended-register `sub`/`adds`/`subs` rows: three nodes, one keyword table

- Date: 2026-11-04
- Question: what changes between `ADD_64_addsub_ext` and its `op = 1`, `S = 1`
  twins; which register 31 meanings appear in which slot; and does the
  disassembler's `lsl` spelling ever make two forms indistinguishable in bytes?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the legal spellings
  come from the MRS nodes and the assembler; what each row computes is not
  claimed here.

## 1. The nodes

`start+width` counts from bit 0 of the 32-bit word. The layout is the one
`EXP-0018` §1 records for `ADD_64_addsub_ext`; these three nodes differ only in
`op` (30+1) and `S` (29+1):

| Field | start+width | `SUB_64_addsub_ext` | `ADDS_64S_addsub_ext` | `SUBS_64S_addsub_ext` | Our use |
|---|---|---|---|---|---|
| `sf` | 31+1 | `1` | `1` | `1` | fixed (64-bit) |
| `op` | 30+1 | `1` | `0` | `1` | **fixed by the node** |
| `S` | 29+1 | `0` | `1` | `1` | **fixed by the node** |
| `op1` | 28+1 | `0` | `0` | `0` | fixed |
| — | 25+3 | `101` | `101` | `101` | fixed |
| — | 24+1 | `1` | `1` | `1` | fixed |
| `opt` | 22+2 | `00` | `00` | `00` | fixed |
| — | 21+1 | `1` | `1` | `1` | fixed — the bit that separates this layout from the shifted one |
| `Rm` | 16+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `src2`; width depends on the keyword |
| `option` | 13+3 | `xxx` | `xxx` | `xxx` | **pinned** per row: `0`…`7` |
| `imm3` | 10+3 | `xxx` | `xxx` | `xxx` | slot `imm`, unsigned, `0…4`, `5…7` excluded |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `dest` |

The MRS spells the operand roles in its assembly grammar, and the three nodes do
**not** spell `Rd` the same way:

| Node | `Rd` rule | `Rn` rule | `Rm` rule |
|---|---|---|---|
| `SUB_64_addsub_ext` | `XdSP_option` | `XnSP_option__6` | `Rm_option` |
| `ADDS_64S_addsub_ext` | `XdOrXZR__6` | `XnSP_option__6` | `Rm_option` |
| `SUBS_64S_addsub_ext` | `XdOrXZR__6` | `XnSP_option__6` | `Rm_option` |

Its `_meta.encoded_in` map agrees: `"<Xd|SP>"` for `sub`'s `Rd`, `"<Xd>"` for
both S nodes' `Rd`, `"<Xn|SP>"` for `Rn` in all three, and a single `"<m>"` for
`Rm` — the placeholder the `Rm_option` rule fills with `<Wm>` or `<Xm>` depending
on the extend keyword (§2 measures both pairings). So the `sp`-in-`Rd` spelling
exists on exactly one of the three families, and the plan cannot choose it: the
bits are the same 31 either way.

### Read, not used (the boundaries)

- `cmp`/`cmn`: the two-operand aliases `ADR-0018` left out. §2 measures that the
  `subs`/`adds` words are their encoding, but the alias drops the destination.
- `ADD_32_addsub_ext` / `SUB_32_addsub_ext` / `ADDS_32S_addsub_ext` /
  `SUBS_32S_addsub_ext`: the same layout with `sf = 0`. Absent from `0.11.0`;
  `add w0, wsp, w1` (`0x0b2143e0`) is `EXP-0021` §2's measurement of that node.

## 2. The spellings, measured

`llvm-mc -triple=aarch64 -show-encoding`, one run per row.

### Accepted, one per keyword

| Source | Bytes | Word | `option` / keyword | `imm3` |
|---|---|---|---|---|
| `sub x0, x1, w2, uxtb #0` | `20 00 22 cb` | `0xcb220020` | 0 / `uxtb` | 0 |
| `sub x0, x1, w2, uxth #4` | `20 30 22 cb` | `0xcb223020` | 1 / `uxth` | 4 |
| `sub x0, x1, w2, uxtw #3` | `20 4c 22 cb` | `0xcb224c20` | 2 / `uxtw` | 3 |
| `sub x0, x1, x2, uxtx #0` | `20 60 22 cb` | `0xcb226020` | 3 / `uxtx` | 0 |
| `sub x0, x1, w2, sxtb #4` | `20 90 22 cb` | `0xcb229020` | 4 / `sxtb` | 4 |
| `sub x0, x1, w2, sxth #0` | `20 a0 22 cb` | `0xcb22a020` | 5 / `sxth` | 0 |
| `sub x0, x1, w2, sxtw #4` | `20 d0 22 cb` | `0xcb22d020` | 6 / `sxtw` | 4 |
| `sub x0, x1, x2, sxtx #3` | `20 ec 22 cb` | `0xcb22ec20` | 7 / `sxtx` | 3 |
| `adds x0, x1, w2, uxtb #0` | `20 00 22 ab` | `0xab220020` | 0 / `uxtb` | 0 |
| `adds x0, x1, x2, sxtx #3` | `20 ec 22 ab` | `0xab22ec20` | 7 / `sxtx` | 3 |
| `subs x0, x1, w2, uxtb #0` | `20 00 22 eb` | `0xeb220020` | 0 / `uxtb` | 0 |
| `subs x0, x1, x2, sxtx #3` | `20 ec 22 eb` | `0xeb22ec20` | 7 / `sxtx` | 3 |

The first eight rows pin the field split on this layout: the words differ only in
bits 15–13 (`option`) and 12–10 (`imm3`), and the `uxtb #0` row differs from
`add`'s `0x8b220020` in bits 31–29 alone. Comparing the `uxtb #0` and `sxtx #3`
rows across the four mnemonics, bits 28–0 are identical every time:
`0x8b220020`/`0xcb220020`/`0xab220020`/`0xeb220020` and
`0x8b22ec20`/`0xcb22ec20`/`0xab22ec20`/`0xeb22ec20`.

### Register 31 in each role

| Source | Bytes | Word | What 31 denotes there |
|---|---|---|---|
| `sub sp, x1, w2, uxtb #3` | `3f 0c 22 cb` | `0xcb220c3f` | `Rd` 31 = `sp` (`sub` only) |
| `sub x0, sp, w1, uxtb #3` | `e0 0f 21 cb` | `0xcb210fe0` | `Rn` 31 = `sp` |
| `adds x0, sp, w1, uxtb #0` | `e0 03 21 ab` | `0xab2103e0` | `Rn` 31 = `sp` |
| `subs x0, sp, x1, sxtx #4` | `e0 f3 21 eb` | `0xeb21f3e0` | `Rn` 31 = `sp` |
| `subs xzr, x1, w2, uxtb #0` | `3f 00 22 eb` | `0xeb22003f` | `Rd` 31 = `xzr`; printed as `cmp x1, w2, uxtb` |
| `adds xzr, x1, w2, uxtb #0` | `3f 00 22 ab` | `0xab22003f` | `Rd` 31 = `xzr`; printed as `cmn x1, w2, uxtb` |

Two spellings that name the other meaning are rejected: `adds sp, x1, w2, uxtb
#0` and `subs sp, x1, w2, uxtb #0` are `invalid operand for instruction`, while
`sub sp, x1, w2, uxtb #3` is accepted. `sp` in the `src2` slot is never legal:
`sub x0, x1, sp, uxtx` and `add x0, x1, sp, uxtb` are rejected. Our rows take the
number and the node's role, not the spelling (`ADR-0020` decision 5).

### `imm3` is `0…4`

| Source | Result |
|---|---|
| `sub x0, x1, w2, uxtb #4` | accepted |
| `sub x0, x1, w2, uxtb #5` | rejected: `expected '[su]xt[bhw]' with optional integer in range [0, 4]` |
| `sub x0, x1, w2, uxtb #8` | rejected with the same message |
| `subs x0, x1, w2, uxtb #5` | rejected with the same message |
| `sub x0, x1, x2, sxtx #5` | rejected: `expected 'sxtx' 'uxtx' or 'lsl' with optional integer in range [0, 4]` |
| `add x0, x1, x2, sxtx #8` | rejected with the same message |

The amount is optional: `sub x0, x1, w2, uxtb` and `sub x0, x1, w2, uxtb #0`
are the same word, so `imm3 = 0` stays legal.

### Cross pairings are rejected

| Source | Result |
|---|---|
| `sub x0, x1, x2, uxtw #3` | rejected: `expected 'sxtx' 'uxtx' or 'lsl' with optional integer in range [0, 4]` |
| `sub x0, x1, w2, uxtx #3` | rejected: `expected '[su]xt[bhw]' with optional integer in range [0, 4]` |
| `sub x0, x1, w2, lsl #3` | rejected with the same message |

The six `[su]xt[bhw]` keywords take a `w` source and the two `[su]xtx` keywords
an `x` source, exactly as `EXP-0018` §2 measured on `add`.

### `lsl`, `uxtx` and the disassembler

| Source or word | Result |
|---|---|
| `sub x0, x1, x2, lsl #2` | `0xcb020820` — the shifted-register node (bit 21 = 0) |
| `sub x0, x1, x2, uxtx #2` | `0xcb226820` — the extended node (bit 21 = 1) |
| `sub x0, sp, x1, uxtx #2` | `0xcb216be0`; printed back as `sub x0, sp, x1, lsl #2` |
| `sub x0, sp, x1, lsl #2` | the same `0xcb216be0` — with `sp` as `Rn` there is no shifted row |
| `adds x0, sp, x1, lsl #2` | `0xab216be0` |
| `subs x0, sp, x1, lsl #2` | `0xeb216be0` |
| `llvm-mc -disassemble` of `0xcb216be0` | `sub x0, sp, x1, lsl #2` |
| `llvm-mc -disassemble` of `0xcb226820` | `sub x0, x1, x2, uxtx #2` |
| `llvm-mc -disassemble` of `0xcb020820` | `sub x0, x1, x2, lsl #2` |

So the printer's `lsl` can name the extended word, and the shifted and extended
words differ in bit 21 — the form is distinguishable in bytes even when the
spelling is not. Our rows are the extended ones; the shifted `sub` rows are
`A64-P10`'s.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 763 bytes,
`sha256:ccc709c80bc75639c8d3197f95373f2d3b3c180d4c28e858ab45752d33ac2fc0`):

```text
  sub x0, x1, w2, uxtb #0
  sub x3, x4, w5, uxth #4
  sub x6, x7, w8, uxtw #3
  sub x9, x10, x11, uxtx #1
  sub x12, x13, w14, sxtb #4
  sub x15, x16, w17, sxth #2
  sub x18, x19, w20, sxtw #3
  sub x21, x22, x23, sxtx #0
  adds x24, x25, w26, uxtb #1
  adds x27, x28, w29, uxth #4
  adds x30, x0, w1, uxtw #0
  adds x2, x3, x4, uxtx #2
  adds x5, x6, w7, sxtb #3
  adds x8, x9, w10, sxth #0
  adds x11, x12, w13, sxtw #4
  adds x14, x15, x16, sxtx #1
  subs x17, x18, w19, uxtb #2
  subs x20, x21, w22, uxth #3
  subs x23, x24, w25, uxtw #4
  subs x26, x27, x28, uxtx #0
  subs x29, x30, w0, sxtb #1
  subs x1, x2, w3, sxth #2
  subs x4, x5, w6, sxtw #3
  subs x7, x8, x9, sxtx #4
  sub sp, x1, w2, uxtb #3
  adds x0, sp, w1, uxtb #0
  subs xzr, x1, w2, uxtb #0
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is a register or an
immediate. `.text` is 108 bytes.

| Offset | Bytes | Word | Row | `Rd`/`Rn`/`Rm` | `imm3` |
|---|---|---|---|---|---|
| 0 | `20 00 22 cb` | `0xcb220020` | `sub -uxtb` | 0/1/2 | 0 |
| 4 | `83 30 25 cb` | `0xcb253083` | `sub -uxth` | 3/4/5 | 4 |
| 8 | `e6 4c 28 cb` | `0xcb284ce6` | `sub -uxtw` | 6/7/8 | 3 |
| 12 | `49 65 2b cb` | `0xcb2b6549` | `sub -uxtx` | 9/10/11 | 1 |
| 16 | `ac 91 2e cb` | `0xcb2e91ac` | `sub -sxtb` | 12/13/14 | 4 |
| 20 | `0f aa 31 cb` | `0xcb31aa0f` | `sub -sxth` | 15/16/17 | 2 |
| 24 | `72 ce 34 cb` | `0xcb34ce72` | `sub -sxtw` | 18/19/20 | 3 |
| 28 | `d5 e2 37 cb` | `0xcb37e2d5` | `sub -sxtx` | 21/22/23 | 0 |
| 32 | `38 07 3a ab` | `0xab3a0738` | `adds -uxtb` | 24/25/26 | 1 |
| 36 | `9b 33 3d ab` | `0xab3d339b` | `adds -uxth` | 27/28/29 | 4 |
| 40 | `1e 40 21 ab` | `0xab21401e` | `adds -uxtw` | 30/0/1 | 0 |
| 44 | `62 68 24 ab` | `0xab246862` | `adds -uxtx` | 2/3/4 | 2 |
| 48 | `c5 8c 27 ab` | `0xab278cc5` | `adds -sxtb` | 5/6/7 | 3 |
| 52 | `28 a1 2a ab` | `0xab2aa128` | `adds -sxth` | 8/9/10 | 0 |
| 56 | `8b d1 2d ab` | `0xab2dd18b` | `adds -sxtw` | 11/12/13 | 4 |
| 60 | `ee e5 30 ab` | `0xab30e5ee` | `adds -sxtx` | 14/15/16 | 1 |
| 64 | `51 0a 33 eb` | `0xeb330a51` | `subs -uxtb` | 17/18/19 | 2 |
| 68 | `b4 2e 36 eb` | `0xeb362eb4` | `subs -uxth` | 20/21/22 | 3 |
| 72 | `17 53 39 eb` | `0xeb395317` | `subs -uxtw` | 23/24/25 | 4 |
| 76 | `7a 63 3c eb` | `0xeb3c637a` | `subs -uxtx` | 26/27/28 | 0 |
| 80 | `dd 87 20 eb` | `0xeb2087dd` | `subs -sxtb` | 29/30/0 | 1 |
| 84 | `41 a8 23 eb` | `0xeb23a841` | `subs -sxth` | 1/2/3 | 2 |
| 88 | `a4 cc 26 eb` | `0xeb26cca4` | `subs -sxtw` | 4/5/6 | 3 |
| 92 | `07 f1 29 eb` | `0xeb29f107` | `subs -sxtx` | 7/8/9 | 4 |
| 96 | `3f 0c 22 cb` | `0xcb220c3f` | `sub` `Rd = 31` = `sp` | 31/1/2 | 3 |
| 100 | `e0 03 21 ab` | `0xab2103e0` | `adds` `Rn = 31` = `sp` | 0/31/1 | 0 |
| 104 | `3f 00 22 eb` | `0xeb22003f` | `subs` `Rd = 31` = `xzr` (`cmp`) | 31/1/2 | 0 |

Output: 108 bytes,
`sha256:9783c84acf84fa0663ff2f51a4c02d4098138af13e2c1c4ff3c10c330b599852`,
`bytes_hex`
`200022cb833025cbe64c28cb49652bcbac912ecb0faa31cb72ce34cbd5e237cb38073aab9b333dab1e4021ab626824abc58c27ab28a12aab8bd12dabeee530ab510a33ebb42e36eb175339eb7a633cebdd8720eb41a823eba4cc26eb07f129eb3f0c22cbe00321ab3f0022eb`.

The vector pins each decision independently:

- one instruction per new row, so a wrong `op`/`S` bit in any row cannot hide
  behind a neighbouring row's bytes;
- every `option` value on every mnemonic, with `imm3` at 0, 1, 2, 3 and 4;
- registers 0–30, each row with three distinct numbers, so a register-field slip
  cannot hide;
- three rows for register 31, one per role the MRS grammar allows
  (`sub` `Rd` = `sp`, `Rn` = `sp`, `subs` `Rd` = `xzr`), so the role rule is in
  the bytes and not only in prose.

## 4. What this fixes, and what it does not

Fixes:

- the twenty-four templates (`0xcb…`, `0xab…`, `0xeb…` at the three
  `[`imm3`]` positions) and their slots, derived from the three MRS nodes by the
  generator;
- the rules: the mnemonic bit is the node's, the keyword is the form and fixes
  the `src2` width, `imm3` is `0…4` with `5…7` excluded, and 31 stays a plain
  register number whose meaning is the node's role;
- the negative evidence: the 32-bit extended node (`N01l`), a cross pairing on
  the new rows (`N02d`), and `imm3 = 5` on a `subs` extended row (`N16e`).

Does not fix:

- **The 32-bit extended nodes**, and therefore `wsp` as a source on the
  extended layout.
- **`cmp`/`cmn`**, which are the `subs`/`adds` words with `Rd = 31` and a
  destination dropped.
- **What the rows compute.** Semantics, not bytes.

## 5. Result

The rows ship in `definitions/aarch64/0.11.0.json`, which repeats the
sixty-eight `0.10.0` forms unchanged and adds twenty-four:

```text
definition  definitions/aarch64/0.11.0.json
namespace   monasm.isa.aarch64
version     0.11.0
forms       92
digest      sha256:c5a9aec943f9b195c400380b8416bf63cba944da3fdf0203f90de5baff295002
```

(The digest is the canonical form `01_contract.md` §12 defines, printed by the
generator and re-checked by `tools/check_definition.py`.)

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 108 bytes above with no fixup records, and rejects:

- a plan naming a 32-bit extended row (`E-FORM-001`, `N01l`);
- an `x` source on a `-uxtb` row (`E-OPERAND-001` on `kind` and `target_type`,
  `N02d`);
- `imm3 = 5` on a `subs` extended row (`E-RANGE-004`, `N16e`).
