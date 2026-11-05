# ADR-0039: A no-displacement SSE memory operand is a form

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P16` (the no-displacement SSE memory operand) and the third
  width of `EC-02`
- Supersedes: none
- Superseded by: none

## Context

`0.11.0` reaches an SSE memory operand only through `mod = 01` (`disp8`) and
`mod = 10` (`disp32`). A base with no displacement is a third `mod` shape, and
`llvm-mc` 23.1.2 measures it on 2026-11-05 (`EXP-0041`):

| Source | Bytes | Family |
|---|---|---|
| `movaps (%rax), %xmm0` | `0f 28 00` | legacy load |
| `movaps (%r8), %xmm0` | `41 0f 28 00` | legacy load, `REX.B` |
| `movaps (%rax), %xmm8` | `44 0f 28 00` | legacy load, `REX.R` |
| `movaps (%r8), %xmm8` | `45 0f 28 00` | legacy load, both |
| `movaps %xmm0, (%rax)` | `0f 29 00` | legacy store |
| `movaps %xmm8, (%r8)` | `45 0f 29 00` | legacy store, both |
| `vmovaps (%rax), %xmm0` | `c5 f8 28 00` | two-byte VEX |
| `vmovaps (%r8), %xmm0` | `c4 c1 78 28 00` | three-byte VEX, `B̄` |
| `vmovaps (%rax), %xmm8` | `c5 78 28 00` | two-byte VEX, `R̄` |
| `vmovaps (%r8), %xmm8` | `c4 41 78 28 00` | three-byte VEX, both |
| `vmovaps %xmm8, (%r8)` | `c4 41 78 29 00` | three-byte VEX store |
| `{evex} vmovaps (%rax), %xmm0` | `62 f1 7c 08 28 00` | EVEX |
| `{evex} vmovaps (%r8), %xmm0` | `62 d1 7c 08 28 00` | EVEX, `B̄` |
| `{evex} vmovaps (%rax), %xmm8` | `62 71 7c 08 28 00` | EVEX, `R̄` |
| `{evex} vmovaps (%r8), %xmm8` | `62 51 7c 08 28 00` | EVEX, both |
| `{evex} vmovaps %xmm8, (%r8)` | `62 51 7c 08 29 00` | EVEX store |

Four facts decide the shape:

1. **No displacement and a zero displacement are different encodings.** The
   assembler emits `0f 28 00` (3 bytes) for `movaps (%rax), %xmm0`, and it also
   canonicalizes `movaps 0(%rax), %xmm0` to that same three-byte form, because
   nothing in the source pins a width. But `0f 28 40 00` (4 bytes) is a legal
   encoding of the same instruction with `mod = 01` and `disp8 = 0`, and
   `llvm-mc -disassemble` reads both `0f 28 00` and `0f 28 40 00` as
   `movaps (%rax), %xmm0`. The same pair exists in EVEX
   (`62 f1 7c 08 28 00` versus `62 f1 7c 08 28 40 00`). A plan that named only
   the operands and let the materializer choose the shorter form would violate
   `INV-02`, so the width is a form, exactly as `disp8` and `disp32` are.
2. **`r/m = 101` is still RIP under `mod = 00`.** `movaps (%rbp), %xmm0` is
   `0f 28 45 00` and `movaps (%r13), %xmm0` is `41 0f 28 45 00`: both use
   `mod = 01` with `disp8 = 0`, because `mod = 00`, `r/m = 101` is
   `RIP + disp32` (`EC-34`). `REX.B` does not change that, so base `5` and
   base `13` are outside the no-displacement row. The SSE RIP-relative form
   itself remains a separate decision and is not added here.
3. **`r/m = 100` still forces a `SIB` byte.** `movaps (%rsp), %xmm0` is
   `0f 28 04 24` and `movaps (%r12), %xmm0` is `41 0f 28 04 24`. The no-
   displacement row therefore excludes base `4` and base `12`; a base-only
   `SIB` row is still absent (`EC-35`, `ADR-0028`).
4. **The register reach from `0.11.0` carries over unchanged.** A legacy high
   `xmm` already forces the `REX` byte, so `REX.B` carries a high base for free
   and one row covers every base the shape allows; a low `xmm` with a high base
   needs its own `REX.B` row. Two-byte VEX already carries a high `xmm` in `R̄`;
   only a high base needs the three-byte `C4` prefix. EVEX carries both bits in
   its existing prefix.

## Decision

**`0.12.0` adds twelve `mod = 00` SSE memory rows: six legacy, four VEX and two
EVEX. The row carries the base and the register; there is no displacement slot,
and every legal base belongs to exactly one window.**

1. **Legacy low/low.** `0f 28 00` (load) and `0f 29 00` (store), with the `xmm`
   at `[27,3]` limited to `0`–`7` and the base at `[24,3]` with
   `excluded: [4, 5]`.
2. **Legacy high `xmm`, any legal base.** `44 0f 28 00` and `44 0f 29 00` carry
   `REX.R` at `[2,1]`; the `xmm` is `[2,1]` + `[27,3]` with `excluded: [0…7]`,
   and the base is a 4-bit `[0,1]` + `[24,3]` slot with
   `excluded: [4, 5, 12, 13]`. One row covers base `0`–`15` minus the `SIB` and
   RIP collisions; `REX.B` is free because `REX.R` already forced the byte.
3. **Legacy low `xmm`, high base.** `41 0f 28 00` and `41 0f 29 00` carry
   `REX.B` at `[0,1]`; the `xmm` stays 3 bits and the base is
   `[0,1]` + `[24,3]` with `excluded: [0…7, 12, 13]`. The low base stays with
   the 3-byte rows, so the two windows cannot both accept a value.
4. **VEX low base.** `c5 f8 28 00` (load) and `c5 f8 29 00` (store) keep the
   two-byte prefix and accept `xmm` `0`–`15` through `R̄` at `[15,1]` inverted;
   the base is `[24,3]` with `excluded: [4, 5]`.
5. **VEX high base.** `c4 c1 78 28 00` and `c4 c1 78 29 00` move `ModRM` to
   bits 32–39; the `xmm` is `[15,1]` inverted + `[35,3]`, and the base is
   `[13,1]` inverted + `[32,3]` with `excluded: [12, 13]`.
6. **EVEX.** One load and one store, `62 f1 7c 08 28 00` and
   `62 f1 7c 08 29 00`: the `xmm` is `[15,1]` inverted + `[43,3]` (`0`–`15`) and
   the base is `[13,1]` inverted + `[40,3]` with `excluded: [4, 5, 12, 13]`.

The row, not the value, selects the encoding. `%rsp`/`%r12` and
`%rbp`/`%r13` are `E-RANGE-004` on the no-displacement rows; a plan that wants
those bases names the existing `disp8` row with displacement `0`, which is the
encoding `llvm-mc` produces. `INV-02` is satisfied because the plan names the
width, and `INV-04` because the materializer never reads the base to choose a
`mod`.

## Consequences

- `0.12.0` is a 74-form document with digest
  `sha256:a74ae09e3f9d2596f2e99edde80d6a487e8596efc05d87e59d6409f82ebf35ae`.
  Its positive fixture `X86-P16-sse-no-disp` is sixteen
  instructions and 72 bytes: all four legacy window combinations, both legacy
  directions, the low- and high-base VEX shapes in both directions, and the
  EVEX low/low, high-base, high-register and both-high shapes.
- `N01ah` pins the version boundary (`E-FORM-001` against `0.11.0`), `N14l`
  pins base `16` on the 4-bit base field, `N16o` pins `%rsp` and `N16p` pins
  `%rbp` on the low/low row, and `N16q` pins a low base on the legacy high-base
  row.
- `EC-02` gains its third width: no displacement (`mod = 00`) joins `disp8`
  (`mod = 01`) and `disp32` (`mod = 10`), with `0f 28 00` versus
  `0f 28 40 00` as the counterexample. No new `EC` row is needed; the carrier is
  the same `form variant` the displacement choice already had.
- `07_definition_format.md` §8.1 gains the twelve rows and the `0.12.0` digest
  row.
- Still absent: a base-only `SIB` row under these opcodes (`%rsp`, `%r12`), an
  SSE RIP-relative row (`mod = 00`, `r/m = 101`), `mod = 00` for the GPR rows,
  the `0x67` prefix, 8/16-bit memory widths, EVEX masking, `ymm`/`zmm`,
  `movapd`'s `0x66` form and `xmm16`–`xmm31`.
