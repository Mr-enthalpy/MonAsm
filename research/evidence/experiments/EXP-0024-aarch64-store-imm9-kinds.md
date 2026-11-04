# EXP-0024 — AArch64 store `imm9` kinds: pre-index, post-index and unscaled

- Date: 2026-11-04
- Question: what bits name the three store addressing kinds that `0.4.0` left
  out, do they reuse the load rows' `imm9` treatment, and does the store
  mnemonic determine the kind?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the field ranges
  come from the MRS nodes and the assembler; the `sp`/`xzr` reading of register
  31 is **not** tested here, because it changes no bit.

## 1. The nodes

`start+width` counts from bit 0 of the 32-bit word. Three store nodes carry the
`imm9` kinds; `STR_64_ldst_pos` is repeated from `EXP-0015` because the new rows
must leave it unchanged.

### `STR_64_ldst_immpre` → `aarch64:str/x64-base-imm9-pre`

### `STR_64_ldst_immpost` → `aarch64:str/x64-base-imm9-post`

### `STUR_64_ldst_unscaled` → `aarch64:stur/x64-base-imm9`

The three share one layout and differ only in bits 11–10:

| Field | start+width | pre | post | unscaled | Our use |
|---|---|---|---|---|---|
| `size` | 30+2 | `11` | `11` | `11` | fixed (8-byte access) |
| — | 28+2 | `11` | `11` | `11` | fixed |
| — | 27+1 | `1` | `1` | `1` | fixed |
| `VR` | 26+1 | `0` | `0` | `0` | fixed |
| — | 25+1 | `0` | `0` | `0` | fixed |
| — | 24+1 | `0` | `0` | `0` | fixed |
| `opc` | 22+2 | `00` | `00` | `00` | fixed (store) |
| — | 21+1 | `0` | `0` | `0` | fixed |
| `imm9` | 12+9 | `xxxxxxxxx` | `xxxxxxxxx` | `xxxxxxxxx` | slot `disp`, signed |
| — | 10+2 | `11` | `01` | `00` | fixed — the kind |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `src` (stored register) |

### `STR_64_ldst_pos` → `aarch64:str/x64-base-imm12` (unchanged, `0.4.0`)

`size = 11`, `opc = 00`, bit 24 = `1`, `imm12` at 10+12. The new rows are the
same three layouts as the `ldr`/`ldur` rows with `opc` at `00` instead of `01`
and `Rt` as the stored register, which is why no new slot shape is needed.

## 2. The kinds, measured

One instruction per run, `llvm-mc -triple=aarch64 -filetype=obj`, then
`llvm-objcopy -O binary --only-section=.text` and `llvm-objdump -d` for the
reading:

| Source | Bytes | Word | `llvm-objdump` |
|---|---|---|---|
| `str x0, [x1, #8]!` | `20 8c 00 f8` | `0xf8008c20` | `str x0, [x1, #0x8]!` |
| `str x0, [x1, #-256]!` | `20 0c 10 f8` | `0xf8100c20` | `str x0, [x1, #-0x100]!` |
| `str x0, [x1, #256]!` | — | — | **rejected** (`invalid operand`) |
| `str x0, [x1, #-257]!` | — | — | **rejected** (range `[-256, 255]`) |
| `str x0, [x1], #8` | `20 84 00 f8` | `0xf8008420` | `str x0, [x1], #0x8` |
| `str x0, [x1], #255` | `20 f4 0f f8` | `0xf80ff420` | `str x0, [x1], #0xff` |
| `str x0, [x1], #-256` | `20 04 10 f8` | `0xf8100420` | `str x0, [x1], #-0x100` |
| `str x0, [x1], #256` | — | — | **rejected** (range `[-256, 255]`) |
| `str x0, [x1], #-257` | — | — | **rejected** (range `[-256, 255]`) |
| `stur x0, [x1, #16]` | `20 01 01 f8` | `0xf8010120` | `stur x0, [x1, #0x10]` |
| `stur x0, [x1, #-1]` | `20 f1 1f f8` | `0xf81ff120` | `stur x0, [x1, #-0x1]` |
| `stur x0, [x1, #256]` | — | — | **rejected** (range `[-256, 255]`) |
| `stur x0, [x1, #-257]` | — | — | **rejected** (range `[-256, 255]`) |
| `stur x0, [x1, #32760]` | — | — | **rejected** (range `[-256, 255]`) |
| `str x0, [x1]` | `20 00 00 f9` | `0xf9000020` | `str x0, [x1]` |
| `str x0, [x1, #32760]` | `20 fc 3f f9` | `0xf93ffc20` | `str x0, [x1, #0x7ff8]` |
| `str x0, [x1, #1]` | `20 10 00 f8` | `0xf8001020` | `stur x0, [x1, #0x1]` |
| `str x0, [x1, #-8]` | `20 80 1f f8` | `0xf81f8020` | `stur x0, [x1, #-0x8]` |

Three facts fall out of the table.

**The store's `imm9` is the load's `imm9`.** The three kinds take `-256..255`
bytes and put the value straight into bits 20–12; the `ldr`/`ldur` rows of
`0.4.0` already use that range, and the store rows reuse it rather than
restating it.

**The kind bits are the only difference from the `imm12` row.** `str x0, [x1]`
is `0xf9000020` with bit 24 set and `imm12 = 0`; `str x0, [x1, #8]!` is
`0xf8008c20` with bit 24 clear, `11` in bits 11–10 and `8` in `imm9`. Two
different fields, so the kind cannot be a value of one offset operand.

**The store mnemonic does not determine the kind.** `str x0, [x1, #1]` is
accepted and emits `0xf8001020`, which `llvm-objdump` reads back as
`stur x0, [x1, #0x1]`; `str x0, [x1, #-8]` emits `0xf81f8020` = `stur` at `-8`.
The assembler switches instruction on the offset's value, exactly as it does for
loads (`EXP-0015` §2), and that is the choice `INV-02` forbids at
materialization time.

The pre-index top end reports differently from the other two shapes: `#256` is
`invalid operand for instruction` rather than a range message, because the
assembler falls back to the positive-offset candidate and then cannot honour
the writeback. The value is still rejected, and the `imm9` bound is stated by
`stur` and by the post-index form.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 169 bytes,
`sha256:1769dfe96e8c3fa720208e01c5ba3bef6b81748580318e59509f88bc248fad82`):

```text
  str x0, [x1, #8]!
  str x2, [x3, #-256]!
  str x4, [x5], #8
  str x6, [x7], #255
  stur x8, [x9, #16]
  stur x10, [x11, #-1]
  str x12, [x13]
  str x14, [x15, #32760]
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is an immediate, so no
linker is involved. `.text` is 32 bytes.

| Offset | Bytes | Word | `llvm-objdump` | Plan `disp` |
|---|---|---|---|---|
| 0 | `20 8c 00 f8` | `0xf8008c20` | `str x0, [x1, #0x8]!` | `8` (`imm9`) |
| 4 | `62 0c 10 f8` | `0xf8100c62` | `str x2, [x3, #-0x100]!` | `-256` (`imm9`) |
| 8 | `a4 84 00 f8` | `0xf80084a4` | `str x4, [x5], #0x8` | `8` (`imm9`) |
| 12 | `e6 f4 0f f8` | `0xf80ff4e6` | `str x6, [x7], #0xff` | `255` (`imm9`) |
| 16 | `28 01 01 f8` | `0xf8010128` | `stur x8, [x9, #0x10]` | `16` (`imm9`) |
| 20 | `6a f1 1f f8` | `0xf81ff16a` | `stur x10, [x11, #-0x1]` | `-1` (`imm9`) |
| 24 | `ac 01 00 f9` | `0xf90001ac` | `str x12, [x13]` | `0` (`imm12`) |
| 28 | `ee fd 3f f9` | `0xf93ffdee` | `str x14, [x15, #0x7ff8]` | `4095` (`imm12`) |

Output: 32 bytes,
`sha256:d9c31730b949daf02ecd3eb4a01e9365cbdc183795d3409bb0b89cfd6c3d299c`,
`bytes_hex` `208c00f8620c10f8a48400f8e6f40ff8280101f86af11ff8ac0100f9eefd3ff9`.

The vector pins each field independently:

- `imm9` at both ends of both writeback kinds: pre `8` and `-256`, post `8` and
  `255`, so a sign-extension slip and an off-by-one bound both move bytes;
- the kind bits: `11`/`01`/`00` in bits 11–10 on the three new rows;
- `stur`'s two signs (`16`, `-1`), which no other row in the vector produces;
- the `imm12` row at both ends (`0`, `4095`), so a change to the store half that
  disturbed the offset row would be visible in the same 32 bytes;
- `opc = 00` throughout, as in `EXP-0015` §3.

## 4. What this fixes, and what it does not

Fixes:

- the three store templates and their slot placements, derived from the MRS
  fields by the generator;
- the statement that the store `imm9` shares the load row's unit, sign and
  range, with `align_bits = 0` because the slot holds the field;
- the store-side form-switch counterexample (`str x0, [x1, #1]` → `stur`), which
  `EC-14` now quotes next to the load-side one;
- the negative evidence: `-257` on the post-index row and `256` on `stur` are
  `E-RANGE-001`, and the pre-index id against `0.12.0` is `E-FORM-001`.

Does not fix:

- **register offset** (`Rm`/`option`/`S`, bit 21 = 1) and **literal** loads
  (`imm19`, no `Rn`): different operand sets, still absent (`E-FORM-001`,
  `N01b`).
- **the `w`/`b`/`h` store widths**: `size` and the register class change, so
  each is a row that does not exist yet.
- **an address in `disp`**: a store `:lo12:` into a scaled `imm12` is the same
  fixup-transform decision `EXP-0015` §4 deferred.
- **the meaning of register 31**: `Rn = 31` and `Rt = 31` are five-bit fields;
  the bytes do not distinguish `sp` from `xzr`, and this slice does not test it.

## 5. Result

The rows ship in `definitions/aarch64/0.13.0.json`, which repeats the 132
`0.12.0` forms and adds three:

```text
definition  definitions/aarch64/0.13.0.json
namespace   monasm.isa.aarch64
version     0.13.0
forms       135
digest      sha256:d3876dd37a8441057b586312b3bee410e39594c64806b2c5c59960c06f9c7a5f
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 32 bytes above with no fixup records, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P15-store-imm9-addressing` | eight instructions, five forms | 32 bytes, `sha256:d9c31730…` |
| `N03-str-imm9-post-disp-out-of-range` | `disp = -257` on `str/x64-base-imm9-post` | `E-RANGE-001`, `min -256`, `max 255` |
| `N03-stur-imm9-disp-out-of-range` | `disp = 256` on `stur/x64-base-imm9` | `E-RANGE-001`, `min -256`, `max 255` |
| `N01n-absent-store-imm9-form` | `str/x64-base-imm9-pre` against `0.12.0` | `E-FORM-001` |
