# ADR-0041: Vector width is a form fact, `ymm` and `zmm`

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P18` (the vector register at `ymm` and `zmm` width) and the
  width half of `EC-09`
- Supersedes: none
- Superseded by: none

## Context

`0.13.0` reaches `xmm0`–`xmm31`, but every vector row is 128-bit: the templates
carry `VEX.L = 0` or `EVEX.L'L = 00`, and `x86.xmm` is the only vector kind. The
same opcode at the same family can encode three widths, distinguished only by
that one prefix field, so a plan that says `vmovaps` has not yet said how many
bits move. `llvm-mc` 23.1.2 measures the register-direct shapes on 2026-11-05
(`EXP-0043`):

| Source | Bytes | Length |
|---|---|---|
| `vmovaps %ymm1, %ymm0` | `c5 fc 28 c1` | 4 |
| `vmovaps %ymm0, %ymm8` | `c5 7c 28 c0` | 4 |
| `vmovaps %ymm8, %ymm0` | `c5 7c 29 c0` | 4 |
| `vmovaps %ymm8, %ymm8` | `c4 41 7c 28 c0` | 5 |
| `{evex} vmovaps %ymm1, %ymm0` | `62 f1 7c 28 28 c1` | 6 |
| `vmovaps %ymm31, %ymm30` | `62 01 7c 28 28 f7` | 6 |
| `vmovaps %zmm1, %zmm0` | `62 f1 7c 48 28 c1` | 6 |
| `vmovaps %zmm31, %zmm30` | `62 01 7c 48 28 f7` | 6 |
| `vmovaps (%rax), %ymm16` | `62 e1 7c 28 28 00` | 6 |
| `vmovaps 32(%rax), %ymm16` | `62 e1 7c 28 28 40 01` | 7 |
| `vmovaps 28(%rax), %ymm16` | `62 e1 7c 28 28 80 1c 00 00 00` | 10 |

Four facts decide the shape:

1. **Width is one field inside the family's existing prefix.** In VEX it is `L`
   (byte 2 bit 2): `c5 fc 28 c1` is 256-bit and `c5 f8 28 c1` is 128-bit, with
   every other prefix bit identical. In EVEX it is `L'L` (P2 bits 1–0): `P2 = 28`
   is 256-bit and `P2 = 48` is 512-bit, while `P2 = 08` is the `0.13.0` 128-bit
   row. `llvm-mc -disassemble` on the three P2 values reads
   `vmovaps %ymm0, %ymm0`, `vmovaps %zmm0, %zmm0` and `vmovaps %xmm0, %xmm0`.
2. **Width is independent of the register number.** `62 01 7c 28 28 f7` and
   `62 01 7c 08 28 f7` differ only in P2 and decode as `%ymm31, %ymm30` and
   `%xmm31, %xmm30`. The five register bits of `0.13.0` therefore carry over
   unchanged; a wider row is not a wider register field.
3. **`zmm` exists only under EVEX.** `{vex} vmovaps %zmm1, %zmm0` is
   `error: unsupported instruction` (`EC-09`), and legacy `movaps` rejects a
   `ymm` operand as `invalid operand for instruction`. `ymm` has both a VEX.256
   and an EVEX.256 form, exactly like `xmm` (`ADR-0030`).
4. **The VEX.256 windows repeat the `0.11.0` `xmm` windows.** The low/low row
   already carries the destination's fourth bit in the inverted `R̄`, so
   `%ymm0, %ymm8` stays four bytes (`c5 7c 28 c0`). A high source with a low
   destination is four bytes through opcode 29 (`c5 7c 29 c0`), while the
   also-legal `c4 c1 7c 28 c0` is five; both-high needs the three-byte `C4`
   prefix (`c4 41 7c 28 c0`). As in `ADR-0038`, the table pins the four-byte
   opcode-29 form so two honest implementations cannot differ in length
   (`INV-02`).

## Decision

**`0.14.0` adds five register-direct rows and two operand kinds, `x86.ymm` and
`x86.zmm`. The mnemonic and the family stay what they were; the width is a new
`form_id` component and the template pins `L`/`L'L`. A plan never selects a
width by an operand value, a modifier or a target feature.**

1. **`x86:vmovaps/ymm-ymm/vex`** (`c5fc28c0`, VEX.256). `dest` is
   `[15,1]` inverted (`R̄`, bit 3) + `[27,3]`, `src` is `[24,3]`.
2. **`x86:vmovaps/ymm-ymm-src-ext/vex`** (`c57c29c0`). Opcode 29 puts the source
   in `ModRM.reg`: `dest` is `[24,3]`, `src` is `[15,1]` inverted + `[27,3]`
   with `excluded: [0…7]`.
3. **`x86:vmovaps/ymm-ymm-both-ext/vex`** (`c4417c28c0`, three-byte VEX).
   `dest` is `[15,1]` inverted + `[35,3]`, `src` is `[13,1]` inverted +
   `[32,3]`, both with `excluded: [0…7]`.
4. **`x86:vmovaps/ymm-ymm/evex`** (`62f17c2828c0`, EVEX.256). The slots are the
   `0.13.0` five-bit ones: `dest` `[12,1]` inverted + `[15,1]` inverted +
   `[43,3]`, `src` `[14,1]` inverted + `[13,1]` inverted + `[40,3]`.
5. **`x86:vmovaps/zmm-zmm/evex`** (`62f17c4828c0`, EVEX.512). Same slots, kinds
   `x86.zmm`/`zmm`.

The kind, not the row, names the storage class: `x86.ymm` and `x86.zmm` are
distinct from `x86.xmm` because the same register number is a different-width
register. A plan that passes a `zmm` operand to a `ymm` row is `E-OPERAND-001`,
and one that passes `ymm16` to the four-bit VEX window is `E-OPERAND-004`.

## Consequences

- `0.14.0` is a 79-form document with digest
  `sha256:3126af72d83ec4ee8e0e34abfde924a73e7b41866fb2c3b8fc3152821d691a5b`.
  Its positive fixture `X86-P18-sse-ymm-zmm` is sixteen instructions and 84
  bytes: the three VEX.256 windows, the four EVEX.256 shapes including
  `ymm16`–`ymm31`, and five EVEX.512 shapes including `zmm16` and `zmm31`.
- `N01ai` is the version boundary (`ymm` row against `0.13.0`), `N01aj` the
  family boundary (legacy `movaps` has no `ymm` form), `N02n` a `zmm` operand
  on a `ymm` row, `N14p` `ymm16` on the four-bit VEX window and `N14q` `zmm32`
  against the five-bit EVEX field.
- `EC-09` is revised in place: it already carries "the family is a form fact",
  and width is the same prefix-choice decision with one more dimension. No new
  `EC` row is added and the frozen count stays at 31 of 40.
- No schema or Rust change is needed. The loader treats `kind` and
  `target_type` as opaque names except for the two 8-bit x86 kinds, and
  `fmp-validate` compares them for exact equality (`E-OPERAND-001`).
- Memory forms at these widths are a separate slice: `vmovaps 32(%rax), %ymm16`
  is a compressed `disp8*32` content `1`, and the `zmm` unit is 64, so
  `EC-39`'s `N = 16` statement would have to grow. Those rows stay absent and
  naming one is `E-FORM-001`.
- Still absent: EVEX masking and broadcast, the EVEX `vvvv`/`V'` carrier,
  `movapd`'s `0x66` form, and `ymm`/`zmm` memory shapes.

## Alternatives rejected

- **Width as an operand modifier** (`{"name": "width", "value": "ymm"}`). A
  modifier is a guard that may not write bits (`01_contract.md` §8), and a
  width token would make the materializer choose the prefix field from an
  operand, which is `INV-02`.
- **Width as a target feature** (`avx512vl` for 256-bit). The extension set is
  a per-plan equality check (`ADR-0031`), not a per-instruction selector, and it
  cannot distinguish 128 from 256 or two EVEX rows.
- **One `x86.vector` kind with a width field in the payload.** Two plans that
  differ only in width would bind to the same kind, and the slot could no longer
  reject a mismatched width; it would also let a value select the form
  (`OD-11`).
