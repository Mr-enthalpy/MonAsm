# EXP-0049 -- the SSE `movaps`/`vmovaps` memory rows with a `SIB` base

- Date: 2026-11-06
- Question: how do the legacy `movaps` and VEX `vmovaps` memory rows encode
  `%rsp` and `%r12` as the base at `xmm` width, where does the `SIB` byte put
  `ModRM` and the displacement, and which register window does each family
  reach on such a base?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.20.0.json`
  (`sha256:b8bd1ed3ed38d71f6b19cc1854c9252df13850127c4e9433981a3a45f49d0f99`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P24-sse-mem-sib.oracle.json`
- Source: `research/evidence/experiments/EXP-0049/P24.asm`
- Fixture source: `research/evidence/experiments/EXP-0049/fixture.asm`
- Decision: `ADR-0047`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movaps 8(%rsp), %xmm0` | `0f 28 44 24 08` | 5 |
| `movaps 8(%r12), %xmm0` | `41 0f 28 44 24 08` | 6 |
| `movaps %xmm0, 8(%rsp)` | `0f 29 44 24 08` | 5 |
| `movaps %xmm0, 8(%r12)` | `41 0f 29 44 24 08` | 6 |
| `movaps 128(%rsp), %xmm0` | `0f 28 84 24 80 00 00 00` | 8 |
| `movaps 128(%r12), %xmm0` | `41 0f 28 84 24 80 00 00 00` | 9 |
| `movaps %xmm0, 128(%rsp)` | `0f 29 84 24 80 00 00 00` | 8 |
| `movaps %xmm0, 128(%r12)` | `41 0f 29 84 24 80 00 00 00` | 9 |
| `movaps 127(%rsp), %xmm7` | `0f 28 7c 24 7f` | 5 |
| `movaps -128(%r12), %xmm7` | `41 0f 28 7c 24 80` | 6 |
| `vmovaps 8(%rsp), %xmm0` | `c5 f8 28 44 24 08` | 6 |
| `vmovaps 8(%r12), %xmm0` | `c4 c1 78 28 44 24 08` | 8 |
| `vmovaps %xmm0, 8(%rsp)` | `c5 f8 29 44 24 08` | 6 |
| `vmovaps %xmm0, 8(%r12)` | `c4 c1 78 29 44 24 08` | 8 |
| `vmovaps 128(%rsp), %xmm0` | `c5 f8 28 84 24 80 00 00 00` | 9 |
| `vmovaps 128(%r12), %xmm0` | `c4 c1 78 28 84 24 80 00 00 00` | 10 |
| `vmovaps %xmm0, 128(%rsp)` | `c5 f8 29 84 24 80 00 00 00` | 9 |
| `vmovaps %xmm0, 128(%r12)` | `c4 c1 78 29 84 24 80 00 00 00` | 10 |
| `vmovaps 127(%rsp), %xmm7` | `c5 f8 28 7c 24 7f` | 6 |
| `vmovaps -128(%r12), %xmm7` | `c4 c1 78 28 7c 24 80` | 8 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty unique byte strings as
the same source line.

Every row spends one byte on the `SIB` (`24`: `base = 100`, `index = 100`,
`scale = 00`). The legacy family spends `REX.B` (`41`) on top for `%r12`; the
VEX family cannot hold `%r12` in the two-byte prefix at all, so it spends the
extra `c4 78` byte pair instead. The length decisions are therefore
`%rsp` = general base + 1 and `%r12` = general base + 2 in both families:
`0f 28 40 08` (4) → `0f 28 44 24 08` (5) → `41 0f 28 44 24 08` (6), and
`c5 f8 28 40 08` (5) → `c5 f8 28 44 24 08` (6) →
`c4 c1 78 28 44 24 08` (8).

## 2. Where the fields sit

| Row family | Template | `ModRM.reg` | `disp` |
|---|---|---|---|
| legacy `%rsp` | `0f 28/29 ModRM 24 disp` | `[19,3]` | `[32,8]`/`[32,32]` |
| legacy `%r12` | `41 0f 28/29 ModRM 24 disp` | `[27,3]` | `[40,8]`/`[40,32]` |
| VEX `%rsp` | `c5 f8 28/29 ModRM 24 disp` | `[27,3]` | `[40,8]`/`[40,32]` |
| VEX `%r12` | `c4 c1 78 28/29 ModRM 24 disp` | `[35,3]` | `[48,8]`/`[48,32]` |

The `SIB` byte pushes everything after `ModRM` one byte later than on the
`-base-disp*` rows: `ModRM` moves from bit 16 to 24 in the legacy family and
from 24 to 32 in the VEX family, and the displacement moves with it. `ModRM`
is not at a fixed offset inside a family — the `41` or the extra VEX byte is
part of the template — so a single fixed-base row cannot serve both `%rsp` and
`%r12`.

## 3. The VEX rows still reach `xmm8`-`xmm15`

| Source | Bytes |
|---|---|
| `vmovaps 8(%rsp), %xmm9` | `c5 78 28 4c 24 08` |
| `vmovaps 8(%r12), %xmm9` | `c4 41 78 28 4c 24 08` |
| `vmovaps 8(%rsp), %xmm15` | `c5 78 28 7c 24 08` |
| `vmovaps 8(%r12), %xmm15` | `c4 41 78 28 7c 24 08` |

The VEX slot already carries the inverted `R` bit (bit 15 of the prefix), so a
register number 8-15 clears it and the row reaches the whole 16-register file
without a length change. The legacy rows carry a bare three-bit field, so they
stop at `xmm7`: `movaps 8(%rsp), %xmm8` is `44 0f 28 44 24 08` and
`movaps 8(%r12), %xmm8` is `45 0f 28 44 24 08`, both needing `REX.R` on a row
that does not have it. The fixture pins this asymmetry: its legacy eight run
`xmm0`-`xmm7` and its VEX eight run `xmm8`, `xmm9`, `xmm14`, `xmm15`.

## 4. What the slice defers

- `mod = 00`: `movaps (%rsp), %xmm0` is `0f 28 04 24` and
  `movaps (%r12), %xmm0` is `41 0f 28 04 24`; the same `SIB` with no
  displacement byte, still waiting for the no-displacement decision.
- Index and scale: `movaps 8(%rsp,%rax,1), %xmm0` is `0f 28 44 04 08` and
  `vmovaps 8(%rsp,%rax,1), %xmm0` is `c5 f8 28 44 04 08`; the `SIB` byte is
  `04` (`index = 000`), not this shape.
- EVEX: `{evex} vmovaps 8(%rsp), %xmm0` is
  `62 f1 7c 08 28 84 24 08 00 00 00` — `disp32`, because 8 is not a multiple of
  16 — and `%r12` only flips `P0` to `62 d1`. The base costs no extra prefix
  byte there, so it is a different decision.
- `ymm`/`zmm`: `vmovaps 8(%rsp), %ymm0` is `c5 fc 28 44 24 08`, the same shape
  with `L = 1`, and `vmovaps 8(%r12), %ymm0` is `c4 c1 7c 28 44 24 08`.
- `%rbp`/`%r13` are untouched: `movaps 8(%rbp), %xmm0` is `0f 28 45 08` and
  `movaps 8(%r13), %xmm0` is `41 0f 28 45 08`, the existing `-base-disp*` and
  `-base-ext-disp*` rows.
- `movaps 8(%rsp), %xmm16` is `error: invalid operand for instruction`; the
  legacy mnemonic has no EVEX form, so the question does not arise here.

## 5. The definition rows

`0.20.0` appends sixteen rows, one per `(family, direction, width, base)`
combination: legacy load/store and VEX load/store, each at `disp8` and `disp32`
and at both fixed bases. The base is part of the template, not a slot, so the
row carries only the register and the displacement — the same shape `0.3.0`
used for `movq`, `0.7.0` for `%r12` and `0.19.0` for the 8/16-bit `mov` rows.

## 6. The fixture

`X86-P24-sse-mem-sib` is sixteen instructions and 120 bytes: one per row,
`disp8` content `8` and `disp32` content `128`. `expected.bin` comes from
`llvm-mc` + `llvm-objcopy`, never from our materializer; the oracle's
`input_sha256` is `fixture.asm` (`93dabe03...`) and its `output_sha256` is the
120-byte `.text` (`a8419c5c...`). `llvm-mc -show-encoding` of `fixture.asm`
records the sixteen lines in `fixture-encoding.txt`, and the materializer's
output is byte-identical to the oracle.

## 7. Negative coverage

- `N01ar` names `x86:movaps/xmm-rsp-disp8/legacy` against `0.19.0`:
  `E-FORM-001`, the version boundary.
- `N01as` names `x86:movaps/xmm-rsp/legacy`, the `mod = 00` shape that does
  not exist: `E-FORM-001`.
- `N02v` passes an `x86.gpr64` operand to an `xmm` row: two `E-OPERAND-001`,
  on `kind` and `target_type`.
- `N02w` supplies a third `base` operand to a fixed-base row:
  `E-OPERAND-002`, expected 2 found 3.
- `N03i` passes displacement content `128` to a `disp8` slot: `E-RANGE-001`.
- `N14w` passes register `8` to the legacy three-bit field: `E-OPERAND-004`.
