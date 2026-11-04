# EXP-0020 — the flag-setting nodes: one `S` bit, and `cmp`/`cmn` as the boundary

- Date: 2026-11-04
- Question: is `adds`/`subs` a modifier of `add`/`sub`; which spellings map to
  which nodes; and where do `cmp`/`cmn` and the `sp` operands sit?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the legal spellings
  come from the MRS nodes and the assembler; what the flags compute is not
  claimed here.

## 1. The nodes

`start+width` counts from bit 0 of the 32-bit word. Both layouts are the ones
`EXP-0008` §2 and `EXP-0019` §1 already record, with `S` at 29+1 fixed to `1`.
Nothing else differs.

### `ADDS_64_addsub_shift` / `SUBS_64_addsub_shift` → `adds`/`subs` `-lsl0` and `-imm6-*`

| Field | start+width | `ADDS_64` | `SUBS_64` | Our use |
|---|---|---|---|---|
| `sf` | 31+1 | `1` | `1` | fixed (64-bit) |
| `op` | 30+1 | `0` | `1` | fixed by the node |
| `S` | 29+1 | `1` | `1` | **fixed — the only bit that differs from `ADD_64`/`SUB_64`** |
| `op1` | 28+1 | `0` | `0` | fixed |
| — | 25+3 | `101` | `101` | fixed |
| — | 24+1 | `1` | `1` | fixed |
| `shift` | 22+2 | `xx` | `xx` | **pinned** per row: `00`/`00`/`01`/`10` |
| — | 21+1 | `0` | `0` | fixed |
| `Rm` | 16+5 | `xxxxx` | `xxxxx` | slot `src2` |
| `imm6` | 10+6 | `xxxxxx` | `xxxxxx` | **pinned to `000000`** on `-lsl0`; slot `imm` on `-imm6-*` |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | `xxxxx` | slot `dest` (`31` = `xzr`) |

### `ADDS_64S_addsub_imm` / `SUBS_64S_addsub_imm` → `adds`/`subs` `-imm12-lsl0`/`-lsl12`

| Field | start+width | `ADDS_64S` | `SUBS_64S` | Our use |
|---|---|---|---|---|
| `sf` | 31+1 | `1` | `1` | fixed |
| `op` | 30+1 | `0` | `1` | fixed by the node |
| `S` | 29+1 | `1` | `1` | **fixed** |
| — | 26+3 | `100` | `100` | fixed |
| — | 23+3 | `010` | `010` | fixed |
| `sh` | 22+1 | `x` | `x` | **pinned**: `0` on `-lsl0`, `1` on `-lsl12` |
| `imm12` | 10+12 | `xxxxxxxxxxxx` | `xxxxxxxxxxxx` | slot `imm`, unsigned |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | `xxxxx` | slot `dest` (`31` = `xzr`) |

The `64S` in the immediate node names is the MRS's own spelling for the
`S`-setting 64-bit form; the field list carries the fact, so the generator keys
on the name and never infers from the suffix.

### Read, not used (the boundaries)

- `ADDS_64S_addsub_ext` / `SUBS_64S_addsub_ext`: the extended layout of
  `EXP-0018` §1 with `S = 1` (`opt = 00`, bit 21 = `1`, `option` + `imm3`).
  Absent from `0.9.0`.
- `ADDS_32_addsub_shift`, `ADDS_32S_addsub_imm`, `SUBS_32_addsub_shift`,
  `SUBS_32S_addsub_imm`: the same four layouts with `sf` fixed to `0`.
- `cmp`/`cmn`: no node of their own. They are assembler aliases that fix `Rd` to
  31 and drop the destination operand (§2), so they are a two-operand form
  family.

## 2. The spellings, measured

`llvm-mc -triple=aarch64 -show-encoding`, one line per table row.

### Accepted

| Source | Bytes | Word | Row |
|---|---|---|---|
| `adds x0, x1, x2` | `20 00 02 ab` | `0xab020020` | `adds -lsl0` |
| `adds x0, x1, x2, lsl #3` | `20 0c 02 ab` | `0xab020c20` | `adds -imm6-lsl` |
| `adds x0, x1, x2, lsr #7` | `20 1c 42 ab` | `0xab421c20` | `adds -imm6-lsr` |
| `adds x0, x1, x2, asr #63` | `20 fc 82 ab` | `0xab82fc20` | `adds -imm6-asr` |
| `adds x0, x1, #0` | `20 00 00 b1` | `0xb1000020` | `adds -imm12-lsl0` |
| `adds x0, x1, #4095` | `20 fc 3f b1` | `0xb13ffc20` | `adds -imm12-lsl0` |
| `adds x0, x1, #1, lsl #12` | `20 04 40 b1` | `0xb1400420` | `adds -imm12-lsl12` |
| `adds x0, x1, #291, lsl #12` | `20 8c 44 b1` | `0xb1448c20` | `adds -imm12-lsl12` |
| `subs x0, x1, x2` | `20 00 02 eb` | `0xeb020020` | `subs -lsl0` |
| `subs x0, x1, x2, lsl #3` | `20 0c 02 eb` | `0xeb020c20` | `subs -imm6-lsl` |
| `subs x0, x1, x2, lsr #7` | `20 1c 42 eb` | `0xeb421c20` | `subs -imm6-lsr` |
| `subs x0, x1, x2, asr #63` | `20 fc 82 eb` | `0xeb82fc20` | `subs -imm6-asr` |
| `subs x0, x1, #0` | `20 00 00 f1` | `0xf1000020` | `subs -imm12-lsl0` |
| `subs x0, x1, #4095` | `20 fc 3f f1` | `0xf13ffc20` | `subs -imm12-lsl0` |
| `subs x0, x1, #1, lsl #12` | `20 04 40 f1` | `0xf1400420` | `subs -imm12-lsl12` |
| `subs x0, x1, #291, lsl #12` | `20 8c 44 f1` | `0xf1448c20` | `subs -imm12-lsl12` |

Every word is its `add`/`sub` twin with bit 29 set: `0x8b…` → `0xab…`,
`0xcb…` → `0xeb…`, `0x91…` → `0xb1…`, `0xd1…` → `0xf1…`, and bits 28–0 are
unchanged. That is the whole node-level claim.

### Accepted but re-encoded — the value-driven switch

| Source | Bytes | Word | What the assembler did |
|---|---|---|---|
| `adds x0, x1, #0x1000` | `20 04 40 b1` | `0xb1400420` | chose `sh = 1` and `imm12 = 1`, silently |
| `adds x0, x1, #0x123000` | `20 8c 44 b1` | `0xb1448c20` | chose `sh = 1` and `imm12 = 291`, silently |

Both are `-lsl12` words. Naming `-lsl0` and stating either literal must be
`E-RANGE-001` (`N18e`), exactly as `N18a`/`N18d` record for `add`/`sub`.

### The aliases and the other nodes

| Source | Bytes | Word | What it is |
|---|---|---|---|
| `cmp x1, x2` | `3f 00 02 eb` | `0xeb02003f` | `subs xzr, x1, x2`; `Rd` fixed to 31 |
| `cmn x1, x2` | `3f 00 02 ab` | `0xab02003f` | `adds xzr, x1, x2` |
| `cmp x1, #5` | `3f 14 00 f1` | `0xf100143f` | `subs xzr, x1, #5` |
| `cmn x1, #5` | `3f 14 00 b1` | `0xb100143f` | `adds xzr, x1, #5` |
| `cmp x1, x2, lsl #3` | `3f 0c 02 eb` | `0xeb020c3f` | `subs xzr, x1, x2, lsl #3` |
| `adds xzr, x1, x2` | `3f 00 02 ab` | `0xab02003f` | the `cmn` word, reached with a destination operand |
| `adds w0, w1, w2` | `20 00 02 2b` | `0x2b020020` | `sf = 0` node |
| `subs w0, w1, w2` | `20 00 02 6b` | `0x6b020020` | `sf = 0` node |
| `adds x0, x1, w2, uxtw #3` | `20 4c 22 ab` | `0xab224c20` | extended S node (`option` + bit 21) |
| `subs x0, x1, w2, uxtw #3` | `20 4c 22 eb` | `0xeb224c20` | extended S node |
| `adds x0, sp, x2` | `e0 63 22 ab` | `0xab2263e0` | extended S node, `option = 011` |
| `subs x0, sp, x2` | `e0 63 22 eb` | `0xeb2263e0` | extended S node, `option = 011` |

`adds x0, x1, x2, ror #3` is rejected with the same message the shifted
`add`/`sub` nodes give (`shift = 11` is unallocated), and `adds x0, x1, sp` is
rejected (`expected compatible register, symbol or integer in range [0, 4095]`):
`sp` cannot be the second source of an immediate row.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 306 bytes,
`sha256:fdb731f0c8405a7d102d0b17e605a7fd691a4a4f18fc33d10004eb2f7f64902f`):

```text
  adds x0, x1, x2
  adds x3, x4, #4095
  adds x5, x6, #291, lsl #12
  adds x7, x8, x9, lsl #3
  adds x10, x11, x12, lsr #7
  adds x13, x14, x15, asr #63
  subs x16, x17, x18
  subs x19, x20, #4095
  subs x21, x22, #291, lsl #12
  subs x23, x24, x25, lsl #3
  subs x26, x27, x28, lsr #7
  subs x29, x30, #1
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is a register or an
immediate. `.text` is 48 bytes.

| Offset | Bytes | Word | Row | Fields |
|---|---|---|---|---|
| 0 | `20 00 02 ab` | `0xab020020` | `adds -lsl0` | `Rd` 0, `Rn` 1, `Rm` 2 |
| 4 | `83 fc 3f b1` | `0xb13ffc83` | `adds -imm12-lsl0` | `Rd` 3, `Rn` 4, `imm12` 4095 |
| 8 | `c5 8c 44 b1` | `0xb1448cc5` | `adds -imm12-lsl12` | `Rd` 5, `Rn` 6, `imm12` 291 |
| 12 | `07 0d 09 ab` | `0xab090d07` | `adds -imm6-lsl` | `Rd` 7, `Rn` 8, `Rm` 9, `imm6` 3 |
| 16 | `6a 1d 4c ab` | `0xab4c1d6a` | `adds -imm6-lsr` | `Rd` 10, `Rn` 11, `Rm` 12, `imm6` 7 |
| 20 | `cd fd 8f ab` | `0xab8ffdcd` | `adds -imm6-asr` | `Rd` 13, `Rn` 14, `Rm` 15, `imm6` 63 |
| 24 | `30 02 12 eb` | `0xeb120230` | `subs -lsl0` | `Rd` 16, `Rn` 17, `Rm` 18 |
| 28 | `93 fe 3f f1` | `0xf13ffe93` | `subs -imm12-lsl0` | `Rd` 19, `Rn` 20, `imm12` 4095 |
| 32 | `d5 8e 44 f1` | `0xf1448ed5` | `subs -imm12-lsl12` | `Rd` 21, `Rn` 22, `imm12` 291 |
| 36 | `17 0f 19 eb` | `0xeb190f17` | `subs -imm6-lsl` | `Rd` 23, `Rn` 24, `Rm` 25, `imm6` 3 |
| 40 | `7a 1f 5c eb` | `0xeb5c1f7a` | `subs -imm6-lsr` | `Rd` 26, `Rn` 27, `Rm` 28, `imm6` 7 |
| 44 | `dd 07 00 f1` | `0xf10007dd` | `subs -imm12-lsl0` | `Rd` 29, `Rn` 30, `imm12` 1 |

Output: 48 bytes,
`sha256:5aa58f45502aa26b2bc5ff0649c499dec87896e92b34a6da42c66ef6f4c472b7`,
`bytes_hex`
`200002ab83fc3fb1c58c44b1070d09ab6a1d4cabcdfd8fab300212eb93fe3ff1d58e44f1170f19eb7a1f5cebdd0700f1`.

The vector pins each decision independently:

- one instruction per row across both mnemonics, so a wrong `op` or `S` bit in
  any row cannot hide behind a neighbouring row's bytes;
- `imm12` at 4095 (all twelve bits set) on both mnemonics and at 291 with
  `sh = 1`, so the field and the pinned `sh` are both visible;
- all three shift keywords on both mnemonics, with `imm6` at 3, 7 and 63, so
  bits 23–22 and 15–10 move independently;
- distinct registers in every row, so a register-field slip cannot hide;
- `subs x29, x30, #1` exercises the low end of `imm12` on the `sh = 0` half.

## 4. What this fixes, and what it does not

Fixes:

- the twelve templates (`0xab000000` / `0xab400000` / `0xab800000`,
  `0xb1000000` / `0xb1400000`, `0xeb…`, `0xf1…`) and their slots, derived from
  the MRS fields by the generator;
- the rule: the flag-setting mnemonic is a form family and `S` is the node's,
  not a plan field; the `sh`/`shift`/`imm6` treatment is inherited from
  `ADR-0011` and `ADR-0015`;
- the negative evidence: `cmp` (`N01i`), the `sf = 0` node (`N01j`) and a
  literal outside the named `sh` half (`N18e`) are rejected.

Does not fix:

- **`cmp`/`cmn`**, and the other flag-setting aliases (`neg`, `negs`, `tst`).
- **The `sf = 0` S nodes**, i.e. every `w` row.
- **The extended S nodes**, `ADDS_64S_addsub_ext` / `SUBS_64S_addsub_ext`, and
  therefore `sp` as a source: `adds x0, sp, x2` is the extended node.
- **What the flags compute.** Semantics, not bytes.
- **The carry nodes.** `ADC`/`SBC`/`ADCS`/`SBCS` are a different family with a
  carry input, not these rows.

## 5. Result

The rows ship in `definitions/aarch64/0.9.0.json`, which repeats the
thirty-two earlier forms and adds twelve:

```text
definition  definitions/aarch64/0.9.0.json
namespace   monasm.isa.aarch64
version     0.9.0
forms       44
digest      sha256:99728cd9bd85b8b0768e700e15dd6263171d6261c385ac15ceeb5df6d2cafcff
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 48 bytes above with no fixup records, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P11-adds-subs-family` | twelve instructions, twelve forms | 48 bytes, `sha256:5aa58f45…` |
| `N01i-absent-cmp-alias` | `aarch64:cmp/x64-x64` | `E-FORM-001` |
| `N01j-absent-flag-32bit-form` | `aarch64:adds/w32-w32-w32-lsl0` | `E-FORM-001` |
| `N18e-adds-no-form-switch` | `imm12 = 4096` on `adds/x64-imm12-lsl0` | `E-RANGE-001` |
