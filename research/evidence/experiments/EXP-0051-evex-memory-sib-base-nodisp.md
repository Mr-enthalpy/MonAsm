# EXP-0051 -- the EVEX `vmovaps` memory rows with a `SIB` base and no displacement

- Date: 2026-11-06
- Question: how do the EVEX `vmovaps` memory rows encode `%rsp` and `%r12` as
  the base with `mod = 00` (no displacement) at `xmm`/`ymm`/`zmm` width, where
  do the vector bits sit, and which bases cannot use the shape?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.22.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P26-evex-mem-sib-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0051/P26.asm`
- Fixture source: `research/evidence/experiments/EXP-0051/fixture.asm`
- Decision: `ADR-0049`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps (%rsp), %xmm0` | `62 f1 7c 08 28 04 24` | 7 |
| `{evex} vmovaps (%r12), %xmm0` | `62 d1 7c 08 28 04 24` | 7 |
| `{evex} vmovaps %xmm2, (%rsp)` | `62 f1 7c 08 29 14 24` | 7 |
| `{evex} vmovaps %xmm2, (%r12)` | `62 d1 7c 08 29 14 24` | 7 |
| `{evex} vmovaps (%rsp), %ymm0` | `62 f1 7c 28 28 04 24` | 7 |
| `{evex} vmovaps (%r12), %ymm0` | `62 d1 7c 28 28 04 24` | 7 |
| `{evex} vmovaps %ymm2, (%rsp)` | `62 f1 7c 28 29 14 24` | 7 |
| `{evex} vmovaps %ymm2, (%r12)` | `62 d1 7c 28 29 14 24` | 7 |
| `{evex} vmovaps (%rsp), %zmm0` | `62 f1 7c 48 28 04 24` | 7 |
| `{evex} vmovaps (%r12), %zmm0` | `62 d1 7c 48 28 04 24` | 7 |
| `{evex} vmovaps %zmm2, (%rsp)` | `62 f1 7c 48 29 14 24` | 7 |
| `{evex} vmovaps %zmm2, (%r12)` | `62 d1 7c 48 29 14 24` | 7 |

`llvm-mc -disassemble` on `probes.txt` returns all sixteen unique byte strings
as the same source line.

The row is four prefix bytes, the opcode, a `ModRM` byte and the `SIB` byte,
and nothing else. `ModRM = 04` is `mod = 00`, `reg = 000`, `r/m = 100`;
`SIB = 24` is `scale = 00`, `index = 100`, `base = 100`. `r/m = 100` is what
sends the base to the `SIB`, and `mod = 00` with `base = 100` is what proves
there is no displacement: `base = 101` would mean "no base, `disp32`", so
`%rsp`/`%r12` are the only two five-bit values this shape can name.

`%r12` costs nothing. The EVEX `P0` byte already carries the base's fourth bit
as the inverted `B̄`, so `f1` → `d1` is the whole difference, exactly as on the
`disp8*N` rows of `EXP-0050`. The length decision is therefore
`62 f1 7c 08 28 00` (6, the `-base` row over `%rax`) →
`62 f1 7c 08 28 04 24` (7, this row): one byte for the `SIB`, none for a
displacement.

## 2. Where the fields sit

| Row family | Template | Vector slot | `disp` |
|---|---|---|---|
| `%rsp` | `62 f1 7c {08,28,48} 28/29 04 24` | `[43,3]` + `[12,1]`/`[15,1]` | none |
| `%r12` | `62 d1 7c {08,28,48} 28/29 04 24` | `[43,3]` + `[12,1]`/`[15,1]` | none |

The prefix does not grow, so `ModRM` stays at bit 40 and the vector slot stays
at `[43,3]` with its two inverted extension bits at `[12,1]` and `[15,1]` --
the same place the `-base` and `-base-disp*` rows put it. `%rsp` and `%r12`
differ in the fixed `P0` byte (`f1` vs `d1`), not in the layout, so a single
fixed-base row cannot serve both. There is no displacement slot to place.

## 3. Zero has exactly one encoding

| Source | Bytes |
|---|---|
| `{evex} vmovaps (%rsp), %xmm0` | `62 f1 7c 08 28 04 24` |
| `{evex} vmovaps 0(%rsp), %xmm0` | `62 f1 7c 08 28 04 24` |
| `{evex} vmovaps (%r12), %xmm0` | `62 d1 7c 08 28 04 24` |
| `{evex} vmovaps 0(%r12), %xmm0` | `62 d1 7c 08 28 04 24` |

`llvm-mc` canonicalizes `0(%rsp)` to `(%rsp)`: the assembler prints the
no-displacement source line for both spellings, and the bytes are identical.
That is why the shape needs its own row rather than a `disp8*N` row with
content `0` -- a `disp8*N` row would emit one more byte for the same address,
and there is no `disp8` encoding of a zero offset here.

## 4. The register window, and the bases that cannot use this shape

| Source | Bytes |
|---|---|
| `{evex} vmovaps (%rsp), %xmm20` | `62 e1 7c 08 28 24 24` |
| `{evex} vmovaps (%r12), %ymm21` | `62 c1 7c 28 28 2c 24` |
| `{evex} vmovaps %zmm30, (%rsp)` | `62 61 7c 48 29 34 24` |

The EVEX vector slot is five bits (`[43,3]` plus the inverted `R̄`/`R̄'` bits),
so numbers 16-31 encode without a length change. A high register only clears
bits in the fixed `P0` byte: `xmm20` over `%rsp` makes it `e1`, `ymm21` over
`%r12` makes it `c1`, and `zmm30` over `%rsp` makes it `61`.

`%rbp`/`%r13` cannot reach this shape. `mod = 00` with `r/m = 101` is
RIP-relative, so the assembler keeps a displacement and no `SIB` byte:

| Source | Bytes | What it is |
|---|---|---|
| `{evex} vmovaps (%rbp), %xmm0` | `62 f1 7c 08 28 45 00` | `-base` row, `disp8 = 0` |
| `{evex} vmovaps (%r13), %xmm0` | `62 d1 7c 08 28 45 00` | `-base` row, `disp8 = 0` |

Both are seven bytes, the same length as this row, but they are the existing
`mod = 01`, `r/m = 101` shape with a zero displacement byte -- a different
`ModRM`, so not this row.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01av` | names `x86:vmovaps/xmm-rsp/evex` against `0.21.0` | `E-FORM-001` |
| `N01aw` | names `x86:vmovaps/xmm-rbp/evex`, a shape with no encoding | `E-FORM-001` |
| `N02z` | passes an `x86.gpr64` operand to an `xmm` row | two `E-OPERAND-001` |
| `N02aa` | supplies a `disp` operand to a row with no `disp` slot | `E-OPERAND-002` |
| `N14y` | passes register `32` to the five-bit EVEX slot | `E-OPERAND-004` |
| `N16z` | passes `%rsp` to the general `x86:vmovaps/xmm-base/evex` row | `E-RANGE-004` |

`{evex} vmovaps (%rsp), %xmm32` is `error: invalid register name` in
`llvm-mc`, which is the same end the five-bit field gives: the row accepts 0-31
and rejects 32. `{evex} vmovaps 16(%rsp), %xmm0` is
`62 f1 7c 08 28 44 24 01` and `{evex} vmovaps (%rsp,%rax,1), %xmm0` is
`62 f1 7c 08 28 04 04`; both are different shapes (`mod = 01` with `disp8*N`,
and `SIB = 04` with an index) and stay absent. `8(%rsp)` is not a multiple of
`N = 16`, so it promotes to `disp32`:
`62 f1 7c 08 28 84 24 08 00 00 00` (11 bytes).

## 6. The fixture

`X86-P26-evex-mem-sib-nodisp` is twelve instructions and 84 bytes: `(width,
direction, base)` with the base fixed per row. The `xmm` four run
`xmm0`-`xmm3`, the `ymm` four `ymm8`-`ymm11` and the `zmm` four
`zmm16`-`zmm19`, so the fixture pins all three widths, both bases and the
five-bit EVEX window.

| Width | Load rows | Store rows |
|---|---|---|
| `xmm` | `xmm0` (`%rsp`), `xmm1` (`%r12`) | `xmm2` (`%rsp`), `xmm3` (`%r12`) |
| `ymm` | `ymm8` (`%rsp`), `ymm9` (`%r12`) | `ymm10` (`%rsp`), `ymm11` (`%r12`) |
| `zmm` | `zmm16` (`%rsp`), `zmm17` (`%r12`) | `zmm18` (`%rsp`), `zmm19` (`%r12`) |

Every row is seven bytes, so the twelve add to 84. `expected.bin` comes from
`llvm-mc` + `llvm-objcopy`, never from our materializer; the oracle's
`input_sha256` is
`a9648531cbb111729a721108e7919b09f4a39a42fc1468276dbeb24ffb8a3fa0`
(`fixture.asm`) and its `output_sha256` is
`1423b8a9bd8b20a60e428aad0fa397432bf1a6a139c4320daee33c222203197c`
(the 84-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
twelve lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- Index and scale: `{evex} vmovaps (%rsp,%rax,1), %xmm0` is
  `62 f1 7c 08 28 04 04`; the `SIB` byte is `04` (`index = 000`), not `24`.
- `%rbp`/`%r13` at `mod = 00`: no encoding exists, so `(%rbp)`/`(%r13)` stay on
  the `-base` row with `disp8 = 0`.
- The other EVEX SSE memory mnemonics (`vmovups`, `vmovdqa` and friends): the
  same shape with a different opcode byte, a coverage slice with no new `EC`
  fact.
- EVEX masking: `{k1}` writes the `aaa` field of `P2`, a bit this shape does
  not carry.
