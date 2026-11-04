# EXP-0023 — the `cmp`/`cmn` alias rows: twelve nodes without an encoding, one `Rd` pin

- Date: 2026-11-04
- Question: which MRS nodes describe `cmp`/`cmn`; do the alias nodes carry bytes;
  what does each measured spelling encode; which register-31 roles exist; and
  does any spelling make two of our forms indistinguishable?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the legal spellings
  come from the MRS nodes and the assembler; what each row computes is not
  claimed here.

## 1. The nodes

The drop carries 611 `Instruction.InstructionAlias` nodes; twelve of them are
`CMP`/`CMN` over the add/sub nodes. Each has `name`, `operation_id`,
`condition`, `preferred`, `assembly` and `_meta`, and **no `encoding` key at
all** — `node.get("encoding")` is `null`. The alias therefore names a base node;
it cannot supply bit ranges.

`condition` is the same in all twelve:

```json
{"_type": "AST.BinaryOp", "left": {"value": "Rd"}, "op": "==",
 "right": {"_type": "Values.Value", "value": "'11111'"}}
```

and `preferred` is `{"_type": "AST.Bool", "value": true}` in all twelve.

| `operation_id` | Width | `encoded_in` keys (field in parentheses) | Assembly rules |
|---|---|---|---|
| `CMP_SUBS_addsub_imm` | 64 | `<Xn|SP>` (Rn), `<imm>` (imm12), `<shift>` (sh) | `XnSP_option__3`, `imm__17`, `optional_shift` |
| `CMN_ADDS_addsub_imm` | 64 | same | `XnSP_option__3`, `imm__17`, `optional_shift` |
| `CMP_SUBS_addsub_imm` | 32 | `<Wn|WSP>` (Rn), `<imm>` (imm12), `<shift>` (sh) | `WnWSP_option`, `imm__17`, `optional_shift` |
| `CMN_ADDS_addsub_imm` | 32 | same | `WnWSP_option`, `imm__17`, `optional_shift` |
| `CMP_SUBS_addsub_shift` | 64 | `<Xn>` (Rn), `<Xm>` (Rm), `<amount>` (imm6), `<shift>` (shift) | `XnOrXZR__12`, `XmOrXZR__4`, `optional_shift__3` |
| `CMN_ADDS_addsub_shift` | 64 | same | `XnOrXZR__12`, `XmOrXZR__4`, `optional_shift__3` |
| `CMP_SUBS_addsub_shift` | 32 | `<Wn>` (Rn), `<Wm>` (Rm), `<amount>` (imm6), `<shift>` (shift) | `WnOrWZR__3`, `WmOrWZR__2`, `optional_shift__2` |
| `CMN_ADDS_addsub_shift` | 32 | same | `WnOrWZR__3`, `WmOrWZR__2`, `optional_shift__2` |
| `CMP_SUBS_addsub_ext` | 64 | `<Xn|SP>` (Rn), `<R>` (option), `<m>` (Rm), `<amount>` (imm3), `<extend>` (option) | `XnSP_option__6`, `R_option__2`, `Rm_option`, `optional_extend__17` |
| `CMN_ADDS_addsub_ext` | 64 | same | `XnSP_option__6`, `R_option__2`, `Rm_option`, `optional_extend__17` |
| `CMP_SUBS_addsub_ext` | 32 | `<Wn|WSP>` (Rn), `<Wm>` (Rm), `<amount>` (imm3), `<extend>` (option) | `WnWSP_option__2`, `WmOrWZR__2`, `optional_extend__15` |
| `CMN_ADDS_addsub_ext` | 32 | same | `WnWSP_option__2`, `WmOrWZR__2`, `optional_extend__15` |

Two things matter for the generator. First, the six `(name, operation_id)` keys
each appear twice, once per width, so the width is the *only* discriminator; the
row's base node supplies `sf` and the base node name is the operation id with
the width component removed (`SUBS_64S_addsub_shift` → `SUBS_addsub_shift`).
Second, the 64-bit ext node maps **both** `<R>` and `<extend>` to `option` and
separately maps `<m>` to `Rm`, so the `encoded_in` map alone does not give the
slot list in operand order; the base node does.

The assembly rules are references, not bodies: the 2026-06 snapshot ships the
schema files but not the rule bodies for `XnSP_option__3`, `WnWSP_option`,
`XmOrXZR__4`, `R_option__2`, `optional_extend__17` and the rest. Their exact
acceptance is therefore `unverified`; the `encoded_in` field names and the
assembler are the usable evidence. That is why the generator reads the base
node and only checks `operation_id`, width, `condition` and `preferred` against
the alias.

The ten base nodes are already read by `0.11.0` rows:
`SUBS_64S_addsub_shift`/`SUBS_64S_addsub_imm`, `ADDS_64S_addsub_shift`/
`ADDS_64S_addsub_imm`, `SUBS_32_addsub_shift`/`SUBS_32S_addsub_imm`,
`ADDS_32_addsub_shift`/`ADDS_32S_addsub_imm`, `SUBS_64S_addsub_ext` and
`ADDS_64S_addsub_ext`.

## 2. The words

Every row was assembled and compared with the generator's template. `Rd` is
`0x1f` in every word; `Rn`/`Rm`/`imm` are the measured values.

| Form | Source | Word |
|---|---|---|
| `aarch64:cmp/x64-x64-lsl0` | `cmp x1, x2` | `0xeb02003f` |
| `aarch64:cmp/x64-x64-imm6-lsl` | `cmp x3, x4, lsl #5` | `0xeb04147f` |
| `aarch64:cmp/x64-x64-imm6-lsr` | `cmp x5, x6, lsr #7` | `0xeb461cbf` |
| `aarch64:cmp/x64-x64-imm6-asr` | `cmp x7, x8, asr #9` | `0xeb8824ff` |
| `aarch64:cmp/x64-imm12-lsl0` | `cmp x9, #5` | `0xf100153f` |
| `aarch64:cmp/x64-imm12-lsl12` | `cmp x10, #291, lsl #12` | `0xf1448d5f` |
| `aarch64:cmp/w32-w32-lsl0` | `cmp w11, w12` | `0x6b0c017f` |
| `aarch64:cmp/w32-w32-imm6-lsl` | `cmp w13, w14, lsl #15` | `0x6b0e3dbf` |
| `aarch64:cmp/w32-w32-imm6-lsr` | `cmp w15, w16, lsr #17` | `0x6b5045ff` |
| `aarch64:cmp/w32-w32-imm6-asr` | `cmp w17, w18, asr #19` | `0x6b924e3f` |
| `aarch64:cmp/w32-imm12-lsl0` | `cmp w19, #5` | `0x7100167f` |
| `aarch64:cmp/w32-imm12-lsl12` | `cmp w20, #291, lsl #12` | `0x71448e9f` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtb` | `cmp x21, w22, uxtb` | `0xeb3602bf` |
| `aarch64:cmp/x64-x64-w32-imm3-uxth` | `cmp x23, w24, uxth #1` | `0xeb3826ff` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtw` | `cmp x25, w26, uxtw #2` | `0xeb3a4b3f` |
| `aarch64:cmp/x64-x64-x64-imm3-uxtx` | `cmp x27, x28, uxtx #3` | `0xeb3c6f7f` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtb` | `cmp x29, w30, sxtb #4` | `0xeb3e93bf` |
| `aarch64:cmp/x64-x64-w32-imm3-sxth` | `cmp x0, w1, sxth` | `0xeb21a01f` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtw` | `cmp x2, w3, sxtw #1` | `0xeb23c45f` |
| `aarch64:cmp/x64-x64-x64-imm3-sxtx` | `cmp x4, x5, sxtx #2` | `0xeb25e89f` |
| `aarch64:cmn/x64-x64-lsl0` | `cmn x6, x7` | `0xab0700df` |
| `aarch64:cmn/x64-x64-imm6-lsl` | `cmn x8, x9, lsl #5` | `0xab09151f` |
| `aarch64:cmn/x64-x64-imm6-lsr` | `cmn x10, x11, lsr #7` | `0xab4b1d5f` |
| `aarch64:cmn/x64-x64-imm6-asr` | `cmn x12, x13, asr #9` | `0xab8d259f` |
| `aarch64:cmn/x64-imm12-lsl0` | `cmn x14, #5` | `0xb10015df` |
| `aarch64:cmn/x64-imm12-lsl12` | `cmn x15, #291, lsl #12` | `0xb1448dff` |
| `aarch64:cmn/w32-w32-lsl0` | `cmn w16, w17` | `0x2b11021f` |
| `aarch64:cmn/w32-w32-imm6-lsl` | `cmn w18, w19, lsl #15` | `0x2b133e5f` |
| `aarch64:cmn/w32-w32-imm6-lsr` | `cmn w20, w21, lsr #17` | `0x2b55469f` |
| `aarch64:cmn/w32-w32-imm6-asr` | `cmn w22, w23, asr #19` | `0x2b974edf` |
| `aarch64:cmn/w32-imm12-lsl0` | `cmn w24, #5` | `0x3100171f` |
| `aarch64:cmn/w32-imm12-lsl12` | `cmn w25, #291, lsl #12` | `0x31448f3f` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtb` | `cmn x26, w27, uxtb` | `0xab3b035f` |
| `aarch64:cmn/x64-x64-w32-imm3-uxth` | `cmn x28, w29, uxth #1` | `0xab3d279f` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtw` | `cmn x30, w0, uxtw #2` | `0xab204bdf` |
| `aarch64:cmn/x64-x64-x64-imm3-uxtx` | `cmn x1, x2, uxtx #3` | `0xab226c3f` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtb` | `cmn x3, w4, sxtb #4` | `0xab24907f` |
| `aarch64:cmn/x64-x64-w32-imm3-sxth` | `cmn x5, w6, sxth` | `0xab26a0bf` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtw` | `cmn x6, w7, sxtw #1` | `0xab27c4df` |
| `aarch64:cmn/x64-x64-x64-imm3-sxtx` | `cmn x8, x9, sxtx #2` | `0xab29e91f` |

The twin check is direct, because `cmp`/`cmn` are the `subs`/`adds` words with
`Rd = 31`:

| Source | Word |
|---|---|
| `subs xzr, x1, x2` | `0xeb02003f` = `cmp x1, x2` |
| `subs xzr, x1, #5` | `0xf100143f` = `cmp x1, #5` |
| `adds xzr, x1, x2` | `0xab02003f` = `cmn x1, x2` |
| `adds xzr, x1, #5` | `0xb100143f` = `cmn x1, #5` |
| `subs xzr, x1, w2, uxtb #3` | `0xeb220c3f` = `cmp x1, w2, uxtb #3` |
| `adds xzr, x1, w2, uxtb #3` | `0xab220c3f` = `cmn x1, w2, uxtb #3` |
| `subs xzr, x1, x2, lsl #3` | `0xeb020c3f` = `cmp x1, x2, lsl #3` |
| `adds xzr, x1, #291, lsl #12` | `0xb1448c3f` = `cmn x1, #291, lsl #12` |

The amount is optional on the extended rows: `uxtb` and `uxtb #0` are the same
word, and `llvm-mc` prints `#0` back as nothing.

## 3. Register 31 and the spellings

| Source or word | Result |
|---|---|
| `cmp sp, #5` | `0xf10017ff` — 31 in `Rn` is `sp` |
| `cmp wsp, #5` | `0x710017ff` |
| `cmp sp, x2` | `0xeb2263ff` — the extended node (bit 21 = 1, `option = 011`) |
| `cmp x1, xzr` | `0xeb1f003f` — 31 in `Rm` is `xzr` |
| `cmp w1, wzr` | `0x6b1f003f` |
| `cmp x1, sp` | rejected: `expected compatible register, symbol or integer in range [0, 4095]` |
| `cmp x1, sp, lsl #3` | rejected with the same message — no shifted row with `sp` as `Rm` |
| `cmp wsp, w2, lsl #3` | `0x6b224fff` — the **extended** 32-bit word (bit 21 = 1), not the shifted row |
| `cmp x1, x2, uxtb #0` | rejected: `expected '[su]xt[bhw]' with optional integer in range [0, 4]` |
| `cmp x1, w2, uxtx #3` | accepted, `0xeb226c3f` — the same word as `cmp x1, x2, uxtx #3` |
| `subs xzr, x1, w2, uxtx #0` | accepted, `0xeb22603f`; printed back as `cmp x1, w2, uxtx` |
| `add x0, x1, w2, uxtx #0` | rejected: `expected '[su]xt[bhw]' with optional integer in range [0, 4]` |

Two measured spellings must not reach the table. `cmp wsp, w2, lsl #3` is legal
but encodes the 32-bit extended node, so it is not the `w32-w32-imm6-lsl` row —
the assembler silently switches on `wsp`, exactly as `EXP-0022` §2 measured for
`sub x0, sp, x1, lsl #2`. And `cmp x1, w2, uxtx #3` is accepted although the
`uxtx` keyword names an `x` source; the register number is the same 5-bit field,
so this is a spelling-only permissiveness of the alias path (the `subs` spelling
with `xzr` shows the same). `ADR-0016`'s width rule is kept: a `w32` `src2` on a
`-uxtx` row is `E-OPERAND-001`, not a second way to reach the same word.

The remaining role rows measured in the vector are:

| Form | Source | Word |
|---|---|---|
| `aarch64:cmp/x64-imm12-lsl0` | `cmp sp, #5` | `0xf10017ff` |
| `aarch64:cmp/w32-imm12-lsl0` | `cmp wsp, #5` | `0x710017ff` |
| `aarch64:cmp/x64-x64-x64-imm3-uxtx` | `cmp sp, x2` | `0xeb2263ff` |
| `aarch64:cmn/x64-imm12-lsl0` | `cmn sp, #5` | `0xb10017ff` |
| `aarch64:cmn/x64-x64-x64-imm3-uxtx` | `cmn sp, x2` | `0xab2263ff` |
| `aarch64:cmp/x64-x64-lsl0` | `cmp x1, xzr` | `0xeb1f003f` |
| `aarch64:cmp/w32-w32-lsl0` | `cmp w1, wzr` | `0x6b1f003f` |

## 4. The vector

Input (LF, trailing newline, two leading spaces; 1416 bytes,
`sha256:0e02e49d69da9305f11edd10a78fd4636a05d366333147968c0a0490f6a04fe6`):
the forty rows above, one per form, followed by the seven role rows. It is the
same text `A64-P14-cmp-cmn-family.oracle.json` pins by hash; the `.s` file is
not kept (`fixtures/README.md`).

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is a register or an
immediate. `.text` is 188 bytes,
`sha256:d1568373925a65551e8b9fecc1308050f2387e0cd77de994c8e33c971a03ab4c`,
`bytes_hex`
`3f0002eb7f1404ebbf1c46ebff2488eb3f1500f15f8d44f17f010c6bbf3d0e6bff45506b3f4e926b7f1600719f8e4471bf0236ebff2638eb3f4b3aeb7f6f3cebbf933eeb1fa021eb5fc423eb9fe825ebdf0007ab1f1509ab5f1d4bab9f258dabdf1500b1ff8d44b11f02112b5f3e132b9f46552bdf4e972b1f1700313f8f44315f033bab9f273dabdf4b20ab3f6c22ab7f9024abbfa026abdfc427ab1fe929abff1700f1ff170071ff6322ebff1700b1ff6322ab3f001feb3f001f6b`.

The vector pins each decision independently:

- one instruction per new row, so a wrong `shift`/`sh`/`option` bit in any row
  cannot hide behind a neighbouring row's bytes;
- all six layouts (shifted, immediate, extended) on both widths, with `imm3` at
  0, 1, 2, 3 and 4 and `imm6` at 5, 7, 9, 15, 17 and 19;
- every row has two distinct register numbers, and the pair moves through the
  file, so a register-field slip cannot hide;
- both immediate halves: `#5` on `-lsl0` and `#291, lsl #12` (0x123000) on
  `-lsl12`;
- seven rows for register 31: `Rn` = 31 on the immediate and extended layouts
  (`sp`/`wsp`) and `Rm` = 31 on the shifted layout (`xzr`/`wzr`), so the role
  rule is in the bytes and not only in prose.

## 5. What this fixes, and what it does not

Fixes:

- the forty templates (`0xeb…`/`0xab…` `x64`, `0x6b…`/`0x2b…` `w32`, `0xf1…`/
  `0xb1…`/`0x71…`/`0x31…` immediate) and their slots, derived from the ten base
  nodes by the generator with `Rd` pinned to 31;
- the pairing rule: an alias row names one base node through `operation_id` and
  copies its width, so a row cannot be built from the wrong width or the wrong
  `S`/`op` node;
- the `E-OPERAND-002` counterexample: a `cmp`/`cmn` row takes two operands, so a
  plan carrying `dest` is `expected: 2, found: 3` (`N02e`);
- the version boundary: `N01i` and `N01m` name an alias against `0.11.0`, and
  `E-FORM-001` is the code even though `0.12.0` has the form.

Does not fix:

- **The 32-bit extended alias rows.** Their base rows are still out (ADR-0020
  decision 7), so `cmp wsp, w2, uxtb` is `E-FORM-001` rather than a row; the
  alias never appears without its base.
- **The assembly-rule bodies** named by the alias nodes; the snapshot does not
  ship them, so their exact acceptance stays `unverified`.
- **What the rows compute.** Semantics, not bytes.
