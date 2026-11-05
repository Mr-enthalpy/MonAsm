# EXP-0050 -- the EVEX `vmovaps` memory rows with a `SIB` base

- Date: 2026-11-06
- Question: how do the EVEX `vmovaps` memory rows encode `%rsp` and `%r12` as
  the base at `xmm`/`ymm`/`zmm` width, does the `SIB` byte move the vector slot,
  what does it cost in length, and which register window does the family reach
  on such a base?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.21.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P25-evex-mem-sib.oracle.json`
- Source: `research/evidence/experiments/EXP-0050/P25.asm`
- Fixture source: `research/evidence/experiments/EXP-0050/fixture.asm`
- Decision: `ADR-0048`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06. `N` is the width unit
(`16` at `xmm`, `32` at `ymm`, `64` at `zmm`).

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps 16(%rsp), %xmm0` | `62 f1 7c 08 28 44 24 01` | 8 |
| `{evex} vmovaps 16(%r12), %xmm0` | `62 d1 7c 08 28 44 24 01` | 8 |
| `{evex} vmovaps 128(%rsp), %xmm1` | `62 f1 7c 08 28 4c 24 08` | 8 |
| `{evex} vmovaps 128(%r12), %xmm1` | `62 d1 7c 08 28 4c 24 08` | 8 |
| `{evex} vmovaps %xmm2, 16(%rsp)` | `62 f1 7c 08 29 54 24 01` | 8 |
| `{evex} vmovaps %xmm2, 16(%r12)` | `62 d1 7c 08 29 54 24 01` | 8 |
| `{evex} vmovaps %xmm3, 128(%rsp)` | `62 f1 7c 08 29 5c 24 08` | 8 |
| `{evex} vmovaps %xmm3, 128(%r12)` | `62 d1 7c 08 29 5c 24 08` | 8 |
| `{evex} vmovaps 2048(%rsp), %xmm4` | `62 f1 7c 08 28 a4 24 00 08 00 00` | 11 |
| `{evex} vmovaps 2048(%r12), %xmm4` | `62 d1 7c 08 28 a4 24 00 08 00 00` | 11 |
| `{evex} vmovaps -16(%rsp), %xmm5` | `62 f1 7c 08 28 6c 24 ff` | 8 |
| `{evex} vmovaps -16(%r12), %xmm5` | `62 d1 7c 08 28 6c 24 ff` | 8 |
| `{evex} vmovaps 32(%rsp), %ymm0` | `62 f1 7c 28 28 44 24 01` | 8 |
| `{evex} vmovaps 32(%r12), %ymm0` | `62 d1 7c 28 28 44 24 01` | 8 |
| `{evex} vmovaps 4096(%rsp), %ymm1` | `62 f1 7c 28 28 8c 24 00 10 00 00` | 11 |
| `{evex} vmovaps 4096(%r12), %ymm1` | `62 d1 7c 28 28 8c 24 00 10 00 00` | 11 |
| `{evex} vmovaps %ymm2, 64(%rsp)` | `62 f1 7c 28 29 54 24 02` | 8 |
| `{evex} vmovaps %ymm2, 64(%r12)` | `62 d1 7c 28 29 54 24 02` | 8 |
| `{evex} vmovaps 64(%rsp), %zmm0` | `62 f1 7c 48 28 44 24 01` | 8 |
| `{evex} vmovaps 64(%r12), %zmm0` | `62 d1 7c 48 28 44 24 01` | 8 |
| `{evex} vmovaps 8192(%rsp), %zmm1` | `62 f1 7c 48 28 8c 24 00 20 00 00` | 11 |
| `{evex} vmovaps 8192(%r12), %zmm1` | `62 d1 7c 48 28 8c 24 00 20 00 00` | 11 |
| `{evex} vmovaps %zmm2, 128(%rsp)` | `62 f1 7c 48 29 54 24 02` | 8 |
| `{evex} vmovaps %zmm2, 128(%r12)` | `62 d1 7c 48 29 54 24 02` | 8 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty-seven unique byte
strings as the same source line.

Every row spends exactly one byte on the `SIB` (`24`: `base = 100`,
`index = 100`, `scale = 00`) and nothing else. `%r12` costs no extra prefix: the
EVEX `P0` byte already carries the base's fourth bit as the inverted `B̄`
(`f1` → `d1`), so both bases are the same length. That is the difference from
`EXP-0049`, where `%r12` added `REX.B` in the legacy family and forced the
three-byte VEX prefix in the VEX family.

The length decisions are therefore `%rsp`/`%r12` = general base + 1 for
`disp8*N` and + 1 for `disp32`: `62 f1 7c 08 28 40 01` (7) →
`62 f1 7c 08 28 44 24 01` (8), and `62 f1 7c 08 28 80 00 08 00 00` (10) →
`62 f1 7c 08 28 a4 24 00 08 00 00` (11).

## 2. Where the fields sit

| Row family | Template | Vector slot | `disp` |
|---|---|---|---|
| `%rsp` `disp8xN` | `62 f1 7c {08,28,48} 28/29 44 24 disp` | `[43,3]` + `[12,1]`/`[15,1]` | `[56,8]` |
| `%r12` `disp8xN` | `62 d1 7c {08,28,48} 28/29 44 24 disp` | `[43,3]` + `[12,1]`/`[15,1]` | `[56,8]` |
| `%rsp` `disp32` | `62 f1 7c {08,28,48} 28/29 84 24 disp32` | `[43,3]` + `[12,1]`/`[15,1]` | `[56,32]` |
| `%r12` `disp32` | `62 d1 7c {08,28,48} 28/29 84 24 disp32` | `[43,3]` + `[12,1]`/`[15,1]` | `[56,32]` |

The prefix does not grow, so `ModRM` stays at bit 40 and the vector slot stays
at `[43,3]` with its two inverted extension bits at `[12,1]` and `[15,1]` --
exactly where the `-base-disp*` rows put it. Only the displacement moves, by
the `SIB` byte: `[48,8]` → `[56,8]` and `[48,32]` → `[56,32]`. `%rsp` and
`%r12` differ in the fixed `P0` byte (`f1` vs `d1`), not in the layout, so a
single fixed-base row cannot serve both.

## 3. `disp8*N` content is unchanged by the `SIB`

| Source | Content byte | Meaning |
|---|---|---|
| `16(%rsp)`, `%xmm` | `01` | `16 / 16` |
| `128(%rsp)`, `%xmm` | `08` | `128 / 16` |
| `32(%rsp)`, `%ymm` | `01` | `32 / 32` |
| `64(%rsp)`, `%ymm` | `02` | `64 / 32` |
| `64(%rsp)`, `%zmm` | `01` | `64 / 64` |
| `128(%rsp)`, `%zmm` | `02` | `128 / 64` |
| `-16(%rsp)`, `%xmm` | `ff` | `-16 / 16` |

The `SIB` byte changes where the displacement sits, not what it means: `N` is
still the width unit (`EC-39`), so `16`/`32`/`64` are the same content `1` at
the three widths. A displacement that is not a multiple of `N` does not
truncate; it promotes to `disp32`:
`{evex} vmovaps 8(%rsp), %xmm0` is
`62 f1 7c 08 28 84 24 08 00 00 00` (11 bytes) with `8` spelled out in full.

## 4. The register window, and `%r13`

| Source | Bytes |
|---|---|
| `{evex} vmovaps 16(%rsp), %xmm20` | `62 e1 7c 08 28 64 24 01` |
| `{evex} vmovaps %ymm21, 32(%rsp)` | `62 e1 7c 28 29 6c 24 01` |
| `{evex} vmovaps 64(%r12), %zmm30` | `62 41 7c 48 28 74 24 01` |

The EVEX vector slot is five bits (`[43,3]` plus the inverted `R̄`/`R̄'` bits),
so numbers 16-31 encode without a length change. A high register only clears
bits in the fixed `P0` byte: `xmm20` and `ymm21` over `%rsp` both make it `e1`,
and `zmm30` over `%r12` makes it `41` (`d1` with `R̄ = 0` and `R̄' = 0`).

`%rbp`/`%r13` are untouched. `{evex} vmovaps 16(%r13), %xmm0` is
`62 d1 7c 08 28 45 01`: no `SIB` byte, the existing `-base-disp8x16` row with
`base = 101`, and `B̄ = 0` for the fourth bit. Neither base forces this shape.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01at` | names `x86:vmovaps/xmm-rsp-disp8x16/evex` against `0.20.0` | `E-FORM-001` |
| `N01au` | names `x86:vmovaps/xmm-rsp/evex`, the absent `mod = 00` `SIB` shape | `E-FORM-001` |
| `N02x` | passes an `x86.gpr64` operand to an `xmm` row | two `E-OPERAND-001` |
| `N02y` | supplies a third `base` operand to a fixed-base row | `E-OPERAND-002` |
| `N03j` | passes `disp8x16` content `128` | `E-RANGE-001` |
| `N14x` | passes register `32` to the five-bit EVEX slot | `E-OPERAND-004` |

`{evex} vmovaps 16(%rsp), %xmm32` is `error: invalid register name` in
`llvm-mc`, which is the same end the five-bit field gives: the row accepts
0-31 and rejects 32. `{evex} vmovaps (%rsp), %xmm0` is
`62 f1 7c 08 28 04 24` and `{evex} vmovaps 16(%rsp,%rax,1), %xmm0` is
`62 f1 7c 08 28 44 04 01`; both are different `SIB` shapes and stay absent.

## 6. The fixture

`X86-P25-evex-mem-sib` is twenty-four instructions and 228 bytes: `(width,
direction, displacement form, base)` with the base fixed per row. The `xmm`
eight run `xmm0`-`xmm7`, the `ymm` eight `ymm8`-`ymm15` and the `zmm` eight
`zmm16`-`zmm23`, so the fixture pins all three widths, both bases, both
displacement forms and the five-bit EVEX window.

| Width | Load rows | Store rows | Displacements |
|---|---|---|---|
| `xmm` | `xmm0`-`xmm3` | `xmm4`-`xmm7` | `16`, `2048` |
| `ymm` | `ymm8`-`ymm11` | `ymm12`-`ymm15` | `32`, `4096` |
| `zmm` | `zmm16`-`zmm19` | `zmm20`-`zmm23` | `64`, `8192` |

`disp8*N` content is `1` for `16`/`32`/`64` and `2` for `32`/`64`/`128`; the
`disp32` rows spell the full `2048`/`4096`/`8192`. `expected.bin` comes from
`llvm-mc` + `llvm-objcopy`, never from our materializer; the oracle's
`input_sha256` is `0b639b4030dcdf...` (`fixture.asm`) and its `output_sha256`
is `eb1a58047018...` (the 228-byte `.text`). `llvm-mc -show-encoding` of
`fixture.asm` records the twenty-four lines in `fixture-encoding.txt`, and the
materializer's output is byte-identical to the oracle.

## 7. What the slice defers

- `mod = 00`: `{evex} vmovaps (%rsp), %xmm0` is `62 f1 7c 08 28 04 24` and
  `{evex} vmovaps (%r12), %xmm0` is `62 d1 7c 08 28 04 24`; the same `SIB`
  with no displacement, still waiting for the no-displacement decision.
- Index and scale: `{evex} vmovaps 16(%rsp,%rax,1), %xmm0` is
  `62 f1 7c 08 28 44 04 01`; the `SIB` byte is `04` (`index = 000`), not this
  shape.
- The other EVEX SSE memory mnemonics (`vmovups`, `vmovdqa` and friends): the
  same shape with a different opcode byte, a coverage slice with no new `EC`
  fact.
- EVEX masking: `{k1}` writes the `aaa` field of `P2`, a bit this shape does
  not carry.
