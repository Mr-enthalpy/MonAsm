# ADR-0036: SSE memory operands are one family, and EVEX `disp8` is compressed

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P13` (the SSE family's memory operand) and `EC-38`, `EC-39`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0030` shipped one `movaps` register-direct shape in three encoding
families. The memory shape is the next vertical slice: `0F 28 /r` loads and
`0F 29 /r` stores, the same two opcodes under `C5 F8` (two-byte VEX) and
`62 F1 7C 08` (EVEX.128). `llvm-mc` 23.1.2 with `{evex}` forcing the family
(`EXP-0038`) measures:

| Source | Bytes |
|---|---|
| `movaps 8(%rax), %xmm0` | `0f 28 40 08` |
| `movaps 128(%rax), %xmm1` | `0f 28 88 80 00 00 00` |
| `movaps %xmm2, 8(%rax)` | `0f 29 50 08` |
| `movaps %xmm3, 128(%rbp)` | `0f 29 9d 80 00 00 00` |
| `vmovaps 8(%rax), %xmm4` | `c5 f8 28 60 08` |
| `vmovaps 128(%rax), %xmm5` | `c5 f8 28 a8 80 00 00 00` |
| `vmovaps %xmm6, 8(%rax)` | `c5 f8 29 70 08` |
| `vmovaps %xmm7, 128(%rbp)` | `c5 f8 29 bd 80 00 00 00` |
| `{evex} vmovaps 16(%rax), %xmm0` | `62 f1 7c 08 28 40 01` |
| `{evex} vmovaps -16(%rax), %xmm1` | `62 f1 7c 08 28 48 ff` |
| `{evex} vmovaps 2032(%rax), %xmm2` | `62 f1 7c 08 28 50 7f` |
| `{evex} vmovaps 8(%rax), %xmm3` | `62 f1 7c 08 28 98 08 00 00 00` |
| `{evex} vmovaps %xmm4, 16(%rax)` | `62 f1 7c 08 29 60 01` |
| `{evex} vmovaps %xmm5, 8(%rbp)` | `62 f1 7c 08 29 ad 08 00 00 00` |

Four facts come out of the measurements:

1. **The family is still the `form_id` component, and the direction is still the
   opcode.** `0F 28` and `0F 29` put the `xmm` register in `ModRM.reg` and the
   memory operand in `ModRM.rm`; the legacy, VEX and EVEX rows differ only in
   the prefix and in where `ModRM` and `disp` start. No operand value can
   select a family (`EC-09`) or a direction (`EC-27`), so each family needs a
   load row and a store row per displacement width.
2. **The base is three bits in all three families.** The legacy template has no
   `REX` byte: `movaps 8(%r8), %xmm0` is `41 0f 28 40 08`, one byte longer.
   Two-byte VEX has `R̄` for `ModRM.reg` but no `B` for `ModRM.rm`:
   `vmovaps 8(%r8), %xmm0` is `c4 c1 78 28 40 08`, a three-byte VEX. EVEX has
   a `B̄` bit, but it is **inverted**: `{evex} vmovaps 16(%r8), %xmm0` is
   `62 d1 7c 08 28 40 01`, with `P0 = d1` and `B̄ = 0`; placing the base's
   fourth bit raw into bit 13 would leave `P0 = f1` and encode `(%rax)`.
3. **`%rsp` still forces a `SIB` byte.** `{evex} vmovaps 8(%rsp), %xmm0` is
   `62 f1 7c 08 28 84 24 08 00 00 00`: `r/m = 100`, `SIB = 24`, then a
   `disp32` because `8` is not a multiple of `16`. The three families share the
   same exclusion, `base = 4` (`E-RANGE-004`), and the `SIB` shape itself stays
   out of this slice (`EC-35`).
4. **EVEX `disp8` is compressed.** With `L'L = 00` and `W = 0`, the unit is
   `N = 16` for `xmm`: the byte offset is `16 × content`. `16` is content `1`,
   `-16` is `ff`, and `2032` is content `127`; `8` is not a multiple of `16`,
   so the assembler uses `disp32` with the byte value `8`
   (`62 f1 7c 08 28 98 08 00 00 00`), and `2048` is outside the signed-8
   content range and also uses `disp32`. The compression is a property of the
   EVEX row, not a value the materializer may derive.

## Decision

**`0.9.0` adds twelve SSE memory rows: load and store × `disp8`/`disp32` ×
legacy/ VEX/ EVEX. The base and the `xmm` register stay three bits, and the
EVEX `disp8` operand carries the compressed field content under
`target_type: disp8x16`.**

1. **The rows.** Four legacy rows (`0F 28`/`0F 29` × `disp8`/`disp32`), four
   VEX rows (`C5 F8 28`/`C5 F8 29` × the same), and four EVEX rows
   (`62 F1 7C 08 28`/`29` × `disp8x16`/`disp32`). `mod = 01`/`10`,
   `r/m = base`, and the opcode are template, so no operand value changes the
   instruction length.
2. **`base` is three bits and excludes `4`.** Placements are `[16,3]` legacy,
   `[24,3]` VEX and `[40,3]` EVEX; `kind: x86.gpr64`, `target_type: rm64`.
   `%rsp` is `E-RANGE-004`; `r8`–`r15` are `E-OPERAND-004` with
   `field_bits = 3`. Widening the base needs its own decision and cannot be a
   raw fourth bit: legacy needs a `REX` prefix, VEX needs the three-byte `C4`
   form, and EVEX needs an inversion mechanism (`EC-38`).
3. **`xmm` stays three bits.** The `dest`/`src` is `[19,3]` legacy, `[27,3]`
   VEX and `[43,3]` EVEX, `kind: x86.xmm`, `target_type: xmm`. `xmm8`–`xmm15`
   are `E-OPERAND-004`, as in `0.5.0`: the extension bit is `REX.R` in the
   legacy family, an inverted `R̄` in VEX (`c5 78`) and an inverted `R̄` in
   EVEX (`62 71`), so a raw fourth bit is wrong in two of the three families.
4. **The EVEX `disp8` operand is field content, unit 16.** `role: disp`,
   `kind: x86.imm`, `target_type: disp8x16`, `from: operand_value`,
   `range {signed: true, bits: 8, align_bits: 0}`, at `[48,8]`. The plan
   carries `1` for `16(%rax)` and `-1` for `-16(%rax)`, exactly as the scale
   row carries `1` for ×2 and the `imm12`-shifted row carries the `imm12`
   content. The materializer writes the field and never multiplies. The
   `disp32` row is the byte value, `target_type: disp32`, at `[48,32]`.
5. **The operand order is `dest`/`src`, `base`, `disp`.** `disp` is last, as in
   every x86 memory row; the materializer compares the role sequence for
   equality (`E-OPERAND-002`), so a store row cannot be fed a `dest`.

The twelve templates are:

| Family | Load `disp8` | Load `disp32` | Store `disp8` | Store `disp32` |
|---|---|---|---|---|
| legacy | `0f284000` | `0f288000000000` | `0f294000` | `0f298000000000` |
| VEX | `c5f8284000` | `c5f8288000000000` | `c5f8294000` | `c5f8298000000000` |
| EVEX | `62f17c08284000` (`disp8x16`) | `62f17c08288000000000` | `62f17c08294000` (`disp8x16`) | `62f17c08298000000000` |

## Consequences

- `0.9.0` is a 45-form document with digest
  `sha256:cc538253ba2d8a111ee16a8d5a8db1aa6efaaed75270889eed20f0f2f5ed6eb8`.
  `X86-P13-sse-memory` is its positive fixture: fourteen instructions, 96
  bytes, no fixup record, covering both directions, all three families, both
  displacement widths, the three EVEX content ends (`1`, `-1`, `127`) and the
  EVEX `disp32` promotion (`8(%rax)`, `8(%rbp)`).
- `N01ae` pins the version boundary (`E-FORM-001`), `N14e` pins `xmm8` on the
  3-bit register field, `N14f` and `N14g` pin `r8` on the 3-bit VEX and EVEX
  bases (the deferral), `N16j` pins `%rsp` as a base (`E-RANGE-004`), `N03d`
  pins EVEX content `128` (`E-RANGE-001`), and `N02m` pins a `dest` on a store
  row (`E-OPERAND-002`).
- `EC-38` is the encoding-choice row for family-dependent base reach;
  `EC-39` is the row for EVEX `disp8*N`. `EC-02`, `EC-09`, `EC-27` and
  `EC-35` gain cross-references; they do not change their carriers.
- `07_definition_format.md` §8.1 gains the twelve rows and the `0.9.0` digest
  row.
- Still absent: `r8`–`r15` as a base or an `xmm`, a `SIB` base under these
  opcodes, `r/m = 100` (the `%rsp`/`%r12` `SIB` shape), `mod = 00` memory
  operands, EVEX masking, `ymm`/`zmm`, the `0x66` `movapd` form, the
  three-byte VEX `C4` form, and the 8/16-bit SSE width.
