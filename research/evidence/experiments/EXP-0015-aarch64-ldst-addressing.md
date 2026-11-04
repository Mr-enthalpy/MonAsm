# EXP-0015 — AArch64 64-bit load/store: four addressing kinds and the offset field

- Date: 2026-11-04
- Question: which encoding bits name the addressing kind, what unit does the
  offset field take in each kind, and does the mnemonic determine the form?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the field ranges
  come from the MRS nodes and the assembler; the `sp`/`xzr` reading of register
  31 is **not** tested here, because it changes no bit.

## 1. The nodes

`start+width` counts from bit 0 of the 32-bit word. Five nodes carry the four
immediate addressing kinds for `x`-width loads and stores; the two that are not
in the table are listed after them, with the reason.

### `LDR_64_ldst_pos` → `aarch64:ldr/x64-base-imm12`

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `size` | 30+2 | `11` | fixed (8-byte access) |
| — | 28+2 | `11` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `1` | fixed — this bit is the unsigned-offset kind |
| `opc` | 22+2 | `01` | fixed (load) |
| `imm12` | 10+12 | `xxxxxxxxxxxx` | slot `disp`, unsigned |
| `Rn` | 5+5 | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | slot `dest` |

### `LDR_64_ldst_immpre` → `aarch64:ldr/x64-base-imm9-pre`

### `LDR_64_ldst_immpost` → `aarch64:ldr/x64-base-imm9-post`

### `LDUR_64_ldst_unscaled` → `aarch64:ldur/x64-base-imm9`

The three share one layout and differ only in bits 11–10:

| Field | start+width | pre | post | unscaled | Our use |
|---|---|---|---|---|---|
| `size` | 30+2 | `11` | `11` | `11` | fixed |
| — | 28+2 | `11` | `11` | `11` | fixed |
| — | 27+1 | `1` | `1` | `1` | fixed |
| `VR` | 26+1 | `0` | `0` | `0` | fixed |
| — | 25+1 | `0` | `0` | `0` | fixed |
| — | 24+1 | `0` | `0` | `0` | fixed |
| `opc` | 22+2 | `01` | `01` | `01` | fixed (load) |
| — | 21+1 | `0` | `0` | `0` | fixed |
| `imm9` | 12+9 | `xxxxxxxxx` | `xxxxxxxxx` | `xxxxxxxxx` | slot `disp`, signed |
| — | 10+2 | `11` | `01` | `00` | fixed — the kind |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `dest` |

### `STR_64_ldst_pos` → `aarch64:str/x64-base-imm12`

Same layout as `LDR_64_ldst_pos` with `opc = 00` and `Rt` as the stored register.

### Not in the table

- `LDR_64_ldst_regoff` / `STR_64_ldst_regoff`: `bit 21 = 1`, and the offset is
  `Rm` (16+5) plus `option` (13+3) plus `S` (12+1), with `10` in bits 11–10. Four
  fields instead of one, so a different operand set.
- `LDR_64_loadlit`: `imm19` at 5+19 and `Rt`, no `Rn`; a literal load, not a
  base+offset one.
- The `imm9` store kinds (`STR_64_ldst_immpre`/`immpost`, `STUR_64_ldst_unscaled`)
  exist in the drop and are the same shapes with `opc = 00`; they are left out of
  v0 (`ADR-0013` decision 5), so naming one is `E-FORM-001`.

## 2. The kinds, measured

One instruction per run, `llvm-mc -triple=aarch64 -filetype=obj`, then
`llvm-objcopy -O binary --only-section=.text` and `llvm-objdump -d` for the
reading:

| Source | Bytes | Word | `llvm-objdump` |
|---|---|---|---|
| `ldr x0, [x1]` | `20 00 40 f9` | `0xf9400020` | `ldr x0, [x1]` |
| `ldr x0, [x1, #16]` | `20 08 40 f9` | `0xf9400820` | `ldr x0, [x1, #0x10]` |
| `ldr x0, [x1, #32760]` | `20 fc 7f f9` | `0xf97ffc20` | `ldr x0, [x1, #0x7ff8]` |
| `ldr x0, [x1, #32768]` | — | — | **rejected** |
| `ldr x0, [x1, #8]!` | `20 8c 40 f8` | `0xf8408c20` | `ldr x0, [x1, #0x8]!` |
| `ldr x0, [x1, #-256]!` | `20 0c 50 f8` | `0xf8500c20` | `ldr x0, [x1, #-0x100]!` |
| `ldr x0, [x1, #256]!` | — | — | **rejected** |
| `ldr x0, [x1], #8` | `20 84 40 f8` | `0xf8408420` | `ldr x0, [x1], #0x8` |
| `ldr x0, [x1], #255` | `20 f4 4f f8` | `0xf84ff420` | `ldr x0, [x1], #0xff` |
| `ldr x0, [x1], #-257` | — | — | **rejected** |
| `ldur x0, [x1]` | `20 00 40 f8` | `0xf8400020` | `ldur x0, [x1]` |
| `ldur x0, [x1, #16]` | `20 00 41 f8` | `0xf8410020` | `ldur x0, [x1, #0x10]` |
| `ldur x0, [x1, #255]` | `20 f0 4f f8` | `0xf84ff020` | `ldur x0, [x1, #0xff]` |
| `ldur x0, [x1, #-256]` | `20 00 50 f8` | `0xf8500020` | `ldur x0, [x1, #-0x100]` |
| `ldur x0, [x1, #256]` | — | — | **rejected** |
| `str x0, [x1]` | `20 00 00 f9` | `0xf9000020` | `str x0, [x1]` |
| `str x0, [x1, #32760]` | `20 fc 3f f9` | `0xf93ffc20` | `str x0, [x1, #0x7ff8]` |
| `str x0, [x1, #32768]` | — | — | **rejected** |
| `ldr x0, [x1, x2]` | `20 68 62 f8` | `0xf8626820` | `ldr x0, [x1, x2]` (not in v0) |

Two facts fall out of the table.

**The unit is the field's, not the byte's.** `ldr x0, [x1, #16]` puts `2` in
`imm12` while `ldur x0, [x1, #16]` puts `16` in `imm9`. `#32760` is `4095` in
`imm12`: the field is `0..4095` and the access size is the multiplier, so the
largest representable offset is 32760 bytes and `#32768` has no encoding.

**The mnemonic does not determine the kind.** `ldr x0, [x1, #1]` is accepted and
emits `0xf8401020`, which `llvm-objdump` reads back as `ldur x0, [x1, #0x1]`;
`ldr x0, [x1, #-8]` emits `0xf85f8020` = `ldur x0, [x1, #-0x8]`. The assembler
picks the unscaled form when the byte offset neither is a multiple of 8 nor fits
the scaled field. That is a *different instruction*, chosen from the operand's
value — `INV-02`'s exact failure — and it is why the kind has to be a
`form_id` (`EC-14`, `ADR-0013`).

## 3. The vector

Input (LF, trailing newline, two leading spaces; 118 bytes,
`sha256:80cb4897cfb7826323ce6bf59096e6d80286c01b7bf45981dfd4820b31b2265b`):

```text
  ldr x0, [x1]
  ldr x2, [x3, #32760]
  ldr x4, [x5, #8]!
  ldr x6, [x7], #-8
  ldur x8, [x9, #-256]
  str x10, [x11]
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is an immediate, so no
linker is involved. `.text` is 24 bytes.

| Offset | Bytes | Word | `llvm-objdump` | Plan `disp` |
|---|---|---|---|---|
| 0 | `20 00 40 f9` | `0xf9400020` | `ldr x0, [x1]` | `0` (`imm12`) |
| 4 | `62 fc 7f f9` | `0xf97ffc62` | `ldr x2, [x3, #0x7ff8]` | `4095` (`imm12`) |
| 8 | `a4 8c 40 f8` | `0xf8408ca4` | `ldr x4, [x5, #0x8]!` | `8` (`imm9`) |
| 12 | `e6 84 5f f8` | `0xf85f84e6` | `ldr x6, [x7], #-0x8` | `-8` (`imm9`) |
| 16 | `28 01 50 f8` | `0xf8500128` | `ldur x8, [x9, #-0x100]` | `-256` (`imm9`) |
| 20 | `6a 01 00 f9` | `0xf900016a` | `str x10, [x11]` | `0` (`imm12`) |

Output: 24 bytes,
`sha256:3f0ecd8652a642925cd995b22de0f6a7d70961b8276bfeb2d01e61f1c61481c0`,
`bytes_hex` `200040f962fc7ff9a48c40f8e6845ff8280150f86a0100f9`.

The vector pins each field independently:

- `imm12` at both ends: `0` and `4095` (`#32760`), on a load and a store;
- `imm9` at a positive and a negative value with different bits
  (`8` → `0x008`, `-8` → `0x1f8`, `-256` → `0x100`), so a sign-extension slip
  moves bytes the others do not;
- the kind bits: `1` at bit 24 for the offset rows, `11`/`01`/`00` in bits 11–10
  for pre/post/unscaled;
- `opc`: `01` for the five loads and `00` for the store.

## 4. What this fixes, and what it does not

Fixes:

- the five templates and their slot placements, derived from the MRS fields by
  the generator;
- the unit rule: `disp` is field content, `imm12` counting 8-byte units and
  `imm9` counting signed bytes, with `align_bits = 0` on both;
- the two ranges: `imm12` `0..4095` and `imm9` `-256..255` (`E-RANGE-001`);
- the negative evidence: `4096` on `imm12` and `-257` on `imm9` are rejected,
  and the absent register-offset id is `E-FORM-001`.

Does not fix:

- **an address in `disp`.** A `:lo12:` into a scaled `imm12` needs
  `(A & 0xfff) >> 3` and an alignment rule; that is a fixup-transform decision,
  and no fixture here has a fixup.
- **the store's `imm9` kinds, register offset, literal loads, and the `w`/`b`/`h`
  widths.** Each is a different `size`/`opc`/operand set, so each is a row that
  does not exist yet (`E-FORM-001`).
- **the meaning of register 31.** `Rn = 31` and `Rt = 31` are five-bit fields;
  whether they name `sp`, `xzr` or nothing is a decode fact the bytes do not
  distinguish, and this slice does not test it.

## 5. Result

The rows ship in `definitions/aarch64/0.4.0.json`, which repeats the six earlier
forms and adds five:

```text
definition  definitions/aarch64/0.4.0.json
namespace   monasm.isa.aarch64
version     0.4.0
forms       11
digest      sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 24 bytes above with no fixup records, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P3-ldst-addressing` | six instructions, five forms | 24 bytes, `sha256:3f0ecd86…` |
| `N03-imm12-disp-out-of-range` | `disp = 4096` on `ldr/x64-base-imm12` | `E-RANGE-001`, `min 0`, `max 4095` |
| `N03-imm9-disp-out-of-range` | `disp = -257` on `ldur/x64-base-imm9` | `E-RANGE-001`, `min -256`, `max 255` |
| `N01b-absent-register-offset-form` | `ldr/x64-base-regoff` | `E-FORM-001` |
