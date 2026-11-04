# EXP-0021 — the 32-bit rows: `sf = 0`, the `w` register class, and `imm6` at 31

- Date: 2026-11-04
- Question: what changes between the `x` rows and the `w` rows; which register
  class each slot carries; what register 31 denotes; and where the 32-bit shift
  amount stops?
- Toolchain: `llvm-mc`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the legal spellings
  come from the MRS nodes and the assembler; what 32-bit arithmetic computes is
  not claimed here.

## 1. The nodes

`start+width` counts from bit 0 of the 32-bit word. The layouts are the ones
`EXP-0008` §2, `EXP-0019` §1 and `EXP-0020` §1 already record, with `sf` at 31+1
fixed to `0`. Nothing else differs; `op` and `S` keep the values their 64-bit
twins have.

### The four shifted nodes → `-lsl0` and `-imm6-*`

| Field | start+width | `ADD_32` | `SUB_32` | `ADDS_32` | `SUBS_32` | Our use |
|---|---|---|---|---|---|---|
| `sf` | 31+1 | `0` | `0` | `0` | `0` | **fixed by the node — the only bit that differs from the 64-bit twin** |
| `op` | 30+1 | `0` | `1` | `0` | `1` | fixed |
| `S` | 29+1 | `0` | `0` | `1` | `1` | fixed |
| `op1` | 28+1 | `0` | `0` | `0` | `0` | fixed |
| — | 25+3 | `101` | `101` | `101` | `101` | fixed |
| — | 24+1 | `1` | `1` | `1` | `1` | fixed |
| `shift` | 22+2 | `xx` | `xx` | `xx` | `xx` | **pinned** per row: `00`/`00`/`01`/`10` |
| — | 21+1 | `0` | `0` | `0` | `0` | fixed |
| `Rm` | 16+5 | `xxxxx` | `xxxxx` | `xxxxx` | `xxxxx` | slot `src2` (`31` = `wzr`) |
| `imm6` | 10+6 | `xxxxxx` | `xxxxxx` | `xxxxxx` | `xxxxxx` | **pinned to `000000`** on `-lsl0`; slot `imm` on `-imm6-*`, content `0..31` |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | `xxxxx` | `xxxxx` | slot `src` (`31` = `wzr`) |
| `Rd` | 0+5 | `xxxxx` | `xxxxx` | `xxxxx` | `xxxxx` | slot `dest` (`31` = `wzr`) |

The MRS `_meta.encoded_in` map spells all three register fields `<Wd>`,
`<Wn>` and `<Wm>` — never an `X` register and never `SP`.

### The four immediate nodes → `-imm12-lsl0` / `-lsl12`

| Field | start+width | `ADD_32`/`SUB_32` | `ADDS_32S`/`SUBS_32S` | Our use |
|---|---|---|---|---|
| `sf` | 31+1 | `0` | `0` | fixed by the node |
| `op` | 30+1 | `0`/`1` | `0`/`1` | fixed |
| `S` | 29+1 | `0` | `1` | fixed |
| — | 26+3 | `100` | `100` | fixed |
| — | 23+3 | `010` | `010` | fixed |
| `sh` | 22+1 | `x` | `x` | **pinned**: `0` on `-lsl0`, `1` on `-lsl12` |
| `imm12` | 10+12 | `xxxxxxxxxxxx` | `xxxxxxxxxxxx` | slot `imm`, unsigned |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | slot `src`; MRS spelling `<Wn|WSP>` (`31` = `wsp`) |
| `Rd` | 0+5 | `xxxxx` | `xxxxx` | slot `dest`; MRS spelling `<Wd|WSP>` on `ADD_32`/`SUB_32`, `<Wd>` on `ADDS_32S`/`SUBS_32S` (`31` = `wzr`) |

The destination spelling is the one field-level difference inside the immediate
pair: on the flag-setting 32-bit nodes `Rd` has no `WSP` alternative, and
§2 measures what that means for 31.

### Read, not used (the boundaries)

- `ADD_32_addsub_ext` / `SUB_32_addsub_ext` / `ADDS_32S_addsub_ext` /
  `SUBS_32S_addsub_ext`: the extended layout of `EXP-0018` §1 with `sf = 0`
  (bit 21 = `1`, `option` + `imm3`). Absent from `0.10.0`.
- `cmp`/`cmn`: still the two-operand alias family `ADR-0018` left out; the `w`
  spellings (`cmp w1, #5`, `cmn w1, #5`) are words of the `ADDS`/`SUBS`
  immediate nodes used as evidence in §2, not rows of their own.

## 2. The spellings, measured

`llvm-mc -triple=aarch64 -show-encoding`, one line per table row.

### Accepted

| Source | Bytes | Word | Row |
|---|---|---|---|
| `add w0, w1, w2` | `20 00 02 0b` | `0x0b020020` | `add -lsl0` |
| `add w0, w1, w2, lsl #3` | `20 0c 02 0b` | `0x0b020c20` | `add -imm6-lsl` |
| `add w0, w1, w2, lsr #7` | `20 1c 42 0b` | `0x0b421c20` | `add -imm6-lsr` |
| `add w0, w1, w2, asr #31` | `20 7c 82 0b` | `0x0b827c20` | `add -imm6-asr` |
| `add w0, w1, #0` | `20 00 00 11` | `0x11000020` | `add -imm12-lsl0` |
| `add w0, w1, #4095` | `20 fc 3f 11` | `0x113ffc20` | `add -imm12-lsl0` |
| `add w0, w1, #1, lsl #12` | `20 04 40 11` | `0x11400420` | `add -imm12-lsl12` |
| `add w0, w1, #291, lsl #12` | `20 8c 44 11` | `0x11448c20` | `add -imm12-lsl12` |
| `sub w0, w1, w2` | `20 00 02 4b` | `0x4b020020` | `sub -lsl0` |
| `sub w0, w1, w2, lsl #3` | `20 0c 02 4b` | `0x4b020c20` | `sub -imm6-lsl` |
| `sub w0, w1, w2, lsr #7` | `20 1c 42 4b` | `0x4b421c20` | `sub -imm6-lsr` |
| `sub w0, w1, w2, asr #31` | `20 7c 82 4b` | `0x4b827c20` | `sub -imm6-asr` |
| `sub w0, w1, #0` | `20 00 00 51` | `0x51000020` | `sub -imm12-lsl0` |
| `sub w0, w1, #4095` | `20 fc 3f 51` | `0x513ffc20` | `sub -imm12-lsl0` |
| `sub w0, w1, #1, lsl #12` | `20 04 40 51` | `0x51400420` | `sub -imm12-lsl12` |
| `sub w0, w1, #291, lsl #12` | `20 8c 44 51` | `0x51448c20` | `sub -imm12-lsl12` |
| `adds w0, w1, w2` | `20 00 02 2b` | `0x2b020020` | `adds -lsl0` |
| `adds w0, w1, w2, lsl #3` | `20 0c 02 2b` | `0x2b020c20` | `adds -imm6-lsl` |
| `adds w0, w1, w2, lsr #7` | `20 1c 42 2b` | `0x2b421c20` | `adds -imm6-lsr` |
| `adds w0, w1, w2, asr #31` | `20 7c 82 2b` | `0x2b827c20` | `adds -imm6-asr` |
| `adds w0, w1, #0` | `20 00 00 31` | `0x31000020` | `adds -imm12-lsl0` |
| `adds w0, w1, #4095` | `20 fc 3f 31` | `0x313ffc20` | `adds -imm12-lsl0` |
| `adds w0, w1, #1, lsl #12` | `20 04 40 31` | `0x31400420` | `adds -imm12-lsl12` |
| `adds w0, w1, #291, lsl #12` | `20 8c 44 31` | `0x31448c20` | `adds -imm12-lsl12` |
| `subs w0, w1, w2` | `20 00 02 6b` | `0x6b020020` | `subs -lsl0` |
| `subs w0, w1, w2, lsl #3` | `20 0c 02 6b` | `0x6b020c20` | `subs -imm6-lsl` |
| `subs w0, w1, w2, lsr #7` | `20 1c 42 6b` | `0x6b421c20` | `subs -imm6-lsr` |
| `subs w0, w1, w2, asr #31` | `20 7c 82 6b` | `0x6b827c20` | `subs -imm6-asr` |
| `subs w0, w1, #0` | `20 00 00 71` | `0x71000020` | `subs -imm12-lsl0` |
| `subs w0, w1, #4095` | `20 fc 3f 71` | `0x713ffc20` | `subs -imm12-lsl0` |
| `subs w0, w1, #1, lsl #12` | `20 04 40 71` | `0x71400420` | `subs -imm12-lsl12` |
| `subs w0, w1, #291, lsl #12` | `20 8c 44 71` | `0x71448c20` | `subs -imm12-lsl12` |

Every word is its 64-bit twin with bit 31 cleared: `0x8b…` → `0x0b…`,
`0xcb…` → `0x4b…`, `0xab…` → `0x2b…`, `0xeb…` → `0x6b…`, and `0x91…`/`0xd1…`/
`0xb1…`/`0xf1…` → `0x11…`/`0x51…`/`0x31…`/`0x71…`. Bits 30–0 are unchanged.

### Register 31, measured in each role

| Source | Bytes | Word | What 31 denotes there |
|---|---|---|---|
| `add wzr, w1, w2` | `3f 00 02 0b` | `0x0b02003f` | `Rd` 31 = `wzr` (shifted node) |
| `add w0, wzr, w1` | `e0 03 01 0b` | `0x0b0103e0` | `Rn` 31 = `wzr` |
| `add w0, w1, wzr` | `20 00 1f 0b` | `0x0b1f0020` | `Rm` 31 = `wzr` |
| `add w0, wsp, #5` | `e0 17 00 11` | `0x110017e0` | `ADD_32` `Rn` 31 = `wsp` |
| `add wsp, w1, #5` | `3f 14 00 11` | `0x1100143f` | `ADD_32` `Rd` 31 = `wsp` |
| `sub wsp, w1, #5` | `3f 14 00 51` | `0x5100143f` | `SUB_32` `Rd` 31 = `wsp` |
| `adds w0, wsp, #5` | `e0 17 00 31` | `0x310017e0` | `ADDS_32S` `Rn` 31 = `wsp` |
| `adds wzr, w1, #5` | `3f 14 00 31` | `0x3100143f` | `ADDS_32S` `Rd` 31 = `wzr`; printed as `cmn w1, #5` |
| `cmp w1, #5` | `3f 14 00 71` | `0x7100143f` | `SUBS_32S` `Rd` 31 = `wzr` |

The bit pattern is the same 31 everywhere; the node's role says what it
denotes. Two spellings that name the *other* meaning are rejected by `llvm-mc`
even though the bits exist: `add wzr, w1, #5` and `adds wsp, w1, #5` are
`invalid operand for instruction`. Our rows take the register number and the
role, not the spelling (`ADR-0019` decision 4).

`add w0, wsp, w2, lsl #3` is accepted as `0xe0 4f 22 0b` = `0x0b224fe0`, which
is the **extended** node (`option = 010`, bit 21 = 1), not `ADD_32_addsub_shift`.
The same happens for the unshifted source: `add w0, wsp, w1` is
`0x0b2143e0`. So `wsp` as a register source does not select a shifted row.

### The shift amount stops at 31

| Source / word | Result |
|---|---|
| `add w0, w1, w2, lsl #31` | accepted, `0x0b027c20` |
| `add w0, w1, w2, lsl #32` | rejected: `expected 'sxtx' 'uxtx' or 'lsl' with optional integer in range [0, 4]` |
| `add w0, w1, w2, lsl #63` | rejected with the same message |
| word `0x0b028020` (`imm6 = 32`) | `llvm-mc -disassemble`: *invalid instruction encoding* |
| word `0x0b827c20` (`imm6 = 31`, `shift = 10`) | decodes as `add w0, w1, w2, asr #31` |

The field is six bits in the MRS, so the legal set is the field domain minus a
closed tail: `range.bits = 6`, `excluded: [32 … 63]`, and `imm6 = 32` is
`E-RANGE-004` (`N16d`), never a truncated shift.

### The other spellings

| Source | Result |
|---|---|
| `add w0, w1, x2` | rejected: `expected compatible register, symbol or integer in range [0, 4095]` |
| `add w0, w1, w2, uxtw #3` | accepted as the extended node, `0x0b224c20` |
| `add w0, w1, w2, ror #3` | rejected: `shift = 11` is unallocated |
| `add w0, w1, w2, lsl #0` | accepted, `0x0b020020` — the same word as `-lsl0`, the overlap `ADR-0015` records |
| `add w0, w1, #4096` | accepted as `0x11400420` (`sh = 1`, `imm12 = 1`), silently |
| `adds w0, w1, #4096` | accepted as `0x31400420`, silently |
| `subs w0, w1, #4096` | accepted as `0x71400420`, silently |

The last three are `-lsl12` words. Naming `-lsl0` and stating 4096 must stay
`E-RANGE-001` (`N18f`), exactly as `N18a`/`N18d`/`N18e` record for the 64-bit
rows.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 600 bytes,
`sha256:be9c5ff9cc5dd857039c7c78a30fb124e13c2f4b593afb164b14f010d75ffcb4`):

```text
  add w0, w1, w2
  add w3, w4, #4095
  add w5, w6, #291, lsl #12
  add w7, w8, w9, lsl #3
  add w10, w11, w12, lsr #7
  add w13, w14, w15, asr #31
  sub w16, w17, w18
  sub w19, w20, #4095
  sub w21, w22, #291, lsl #12
  sub w23, w24, w25, lsl #3
  sub w26, w27, w28, lsr #7
  sub w29, w30, #1
  adds w0, w1, w2
  adds w3, w4, #4095
  adds w5, w6, #291, lsl #12
  adds w7, w8, w9, lsl #3
  adds w10, w11, w12, lsr #7
  adds w13, w14, w15, asr #31
  subs w16, w17, w18
  subs w19, w20, #4095
  subs w21, w22, #291, lsl #12
  subs w23, w24, w25, lsl #3
  subs w26, w27, w28, lsr #7
  subs w29, w30, #1
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is a register or an
immediate. `.text` is 96 bytes.

| Offset | Bytes | Word | Row | Fields |
|---|---|---|---|---|
| 0 | `20 00 02 0b` | `0x0b020020` | `add -lsl0` | `Rd` 0, `Rn` 1, `Rm` 2 |
| 4 | `83 fc 3f 11` | `0x113ffc83` | `add -imm12-lsl0` | `Rd` 3, `Rn` 4, `imm12` 4095 |
| 8 | `c5 8c 44 11` | `0x11448cc5` | `add -imm12-lsl12` | `Rd` 5, `Rn` 6, `imm12` 291 |
| 12 | `07 0d 09 0b` | `0x0b090d07` | `add -imm6-lsl` | `Rd` 7, `Rn` 8, `Rm` 9, `imm6` 3 |
| 16 | `6a 1d 4c 0b` | `0x0b4c1d6a` | `add -imm6-lsr` | `Rd` 10, `Rn` 11, `Rm` 12, `imm6` 7 |
| 20 | `cd 7d 8f 0b` | `0x0b8f7dcd` | `add -imm6-asr` | `Rd` 13, `Rn` 14, `Rm` 15, `imm6` 31 |
| 24 | `30 02 12 4b` | `0x4b120230` | `sub -lsl0` | `Rd` 16, `Rn` 17, `Rm` 18 |
| 28 | `93 fe 3f 51` | `0x513ffe93` | `sub -imm12-lsl0` | `Rd` 19, `Rn` 20, `imm12` 4095 |
| 32 | `d5 8e 44 51` | `0x51448ed5` | `sub -imm12-lsl12` | `Rd` 21, `Rn` 22, `imm12` 291 |
| 36 | `17 0f 19 4b` | `0x4b190f17` | `sub -imm6-lsl` | `Rd` 23, `Rn` 24, `Rm` 25, `imm6` 3 |
| 40 | `7a 1f 5c 4b` | `0x4b5c1f7a` | `sub -imm6-lsr` | `Rd` 26, `Rn` 27, `Rm` 28, `imm6` 7 |
| 44 | `dd 07 00 51` | `0x510007dd` | `sub -imm12-lsl0` | `Rd` 29, `Rn` 30, `imm12` 1 |
| 48 | `20 00 02 2b` | `0x2b020020` | `adds -lsl0` | `Rd` 0, `Rn` 1, `Rm` 2 |
| 52 | `83 fc 3f 31` | `0x313ffc83` | `adds -imm12-lsl0` | `Rd` 3, `Rn` 4, `imm12` 4095 |
| 56 | `c5 8c 44 31` | `0x31448cc5` | `adds -imm12-lsl12` | `Rd` 5, `Rn` 6, `imm12` 291 |
| 60 | `07 0d 09 2b` | `0x2b090d07` | `adds -imm6-lsl` | `Rd` 7, `Rn` 8, `Rm` 9, `imm6` 3 |
| 64 | `6a 1d 4c 2b` | `0x2b4c1d6a` | `adds -imm6-lsr` | `Rd` 10, `Rn` 11, `Rm` 12, `imm6` 7 |
| 68 | `cd 7d 8f 2b` | `0x2b8f7dcd` | `adds -imm6-asr` | `Rd` 13, `Rn` 14, `Rm` 15, `imm6` 31 |
| 72 | `30 02 12 6b` | `0x6b120230` | `subs -lsl0` | `Rd` 16, `Rn` 17, `Rm` 18 |
| 76 | `93 fe 3f 71` | `0x713ffe93` | `subs -imm12-lsl0` | `Rd` 19, `Rn` 20, `imm12` 4095 |
| 80 | `d5 8e 44 71` | `0x71448ed5` | `subs -imm12-lsl12` | `Rd` 21, `Rn` 22, `imm12` 291 |
| 84 | `17 0f 19 6b` | `0x6b190f17` | `subs -imm6-lsl` | `Rd` 23, `Rn` 24, `Rm` 25, `imm6` 3 |
| 88 | `7a 1f 5c 6b` | `0x6b5c1f7a` | `subs -imm6-lsr` | `Rd` 26, `Rn` 27, `Rm` 28, `imm6` 7 |
| 92 | `dd 07 00 71` | `0x710007dd` | `subs -imm12-lsl0` | `Rd` 29, `Rn` 30, `imm12` 1 |

Output: 96 bytes,
`sha256:7f4b3b968f707622f009685b4080af538fa04f8b18bfaae330b683317599706e`,
`bytes_hex`
`2000020b83fc3f11c58c4411070d090b6a1d4c0bcd7d8f0b3002124b93fe3f51d58e4451170f194b7a1f5c4bdd0700512000022b83fc3f31c58c4431070d092b6a1d4c2bcd7d8f2b3002126b93fe3f71d58e4471170f196b7a1f5c6bdd070071`.

The vector pins each decision independently:

- one instruction per row, so a wrong `sf`/`op`/`S` bit in any row cannot hide
  behind a neighbouring row's bytes;
- `imm12` at 4095 (all twelve bits set) and at 291 with `sh = 1`, so the field
  and the pinned `sh` are both visible;
- all three shift keywords on all four mnemonics, with `imm6` at 3, 7 and 31,
  so bits 23–22 and 15–10 move independently and the top legal `imm6` is
  exercised;
- distinct registers 0–30 in every row, so a register-field slip cannot hide;
  register 31 is left to §2 because `llvm-mc` refuses two of its `w`
  spellings (`add wzr, w1, #5`, `adds wsp, w1, #5`);
- `sub w29, w30, #1` exercises the low end of `imm12` on the `sh = 0` half.

## 4. What this fixes, and what it does not

Fixes:

- the twenty-four templates (`0x0b000000`/`0x0b400000`/`0x0b800000`, `0x11…`,
  `0x4b…`, `0x51…`, `0x2b…`, `0x31…`, `0x6b…`, `0x71…`) and their slots,
  derived from the eight MRS nodes by the generator;
- the rules: the width is the form family and `sf` is the node's; every
  register slot is `aarch64.gpr32`/`w32`; 31 stays a plain `reg_number` whose
  role is the node's; the 32-bit `imm6` carries the excluded tail `32..63`;
- the negative evidence: a `w` row absent from `0.9.0` (`N01k`), `x64`
  operands on a `w` row (`N02c`), `imm6 = 32` (`N16d`), and a literal outside
  the named `sh` half (`N18f`).

Does not fix:

- **The extended 32-bit nodes**, `ADD_32_addsub_ext` and its three siblings,
  and therefore `wsp` as a shifted source: `add w0, wsp, w1` is the extended
  node.
- **`cmp`/`cmn`**, in either width (`ADR-0018`).
- **What 32-bit arithmetic computes.** Semantics, not bytes.
- **The carry nodes.** `ADC`/`SBC`/`ADCS`/`SBCS` have a carry input and are a
  different family.

## 5. Result

The rows ship in `definitions/aarch64/0.10.0.json`, which repeats the
forty-four `0.9.0` forms unchanged and adds twenty-four:

```text
definition  definitions/aarch64/0.10.0.json
namespace   monasm.isa.aarch64
version     0.10.0
forms       68
digest      sha256:e958d69b4ba93222e7621a1f5c3ebd056ce929e2974a961a03abb7b66f0b247b
```

(The digest is the canonical form `01_contract.md` §12 defines, printed by the
generator and re-checked by `tools/check_definition.py`.)

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 96 bytes above with no fixup records, and rejects:

- a plan naming a `w` form against `0.9.0` (`E-FORM-001`, `N01k`);
- an `x64` operand on a `w` row (`E-OPERAND-001` on `kind` and `target_type`,
  `N02c`);
- `imm6 = 32` on a 32-bit shifted row (`E-RANGE-004`, `N16d`);
- `4096` on `add/w32-imm12-lsl0` (`E-RANGE-001`, `N18f`).
