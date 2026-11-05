# EXP-0040 — the SSE register at `xmm8`–`xmm15`, and two legal VEX spellings

- Date: 2026-11-05
- Question: how do the legacy, VEX and EVEX families encode a `movaps` /
  `vmovaps` register operand in `xmm8`–`xmm15`, which prefix bit carries the
  fourth bit of each register, and does one source have more than one legal
  encoding?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.11.0.json`
  (`sha256:d9669be62267ecd90d69dc9f936bcb947948b8c1ec7c7ba0670eb63f32de0570`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P15-sse-xmm-ext.oracle.json`
- Source: `research/evidence/experiments/EXP-0040/P15.asm`
- Decision: `ADR-0038`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. `{evex}` forces the EVEX
family; without it `llvm-mc` emits VEX for `vmovaps` at `xmm` width.

| Source | Bytes | Length | Family |
|---|---|---|---|
| `movaps %xmm1, %xmm0` | `0f 28 c1` | 3 | legacy register-direct, both low |
| `movaps %xmm1, %xmm8` | `44 0f 28 c1` | 4 | legacy, `REX.R` |
| `movaps %xmm9, %xmm0` | `41 0f 28 c1` | 4 | legacy, `REX.B` |
| `movaps %xmm9, %xmm8` | `45 0f 28 c1` | 4 | legacy, `REX.R` + `REX.B` |
| `vmovaps %xmm1, %xmm0` | `c5 f8 28 c1` | 4 | two-byte VEX, both low |
| `vmovaps %xmm1, %xmm8` | `c5 78 28 c1` | 4 | two-byte VEX, `R̄ = 0` |
| `vmovaps %xmm9, %xmm0` | `c5 78 29 c8` | 4 | two-byte VEX, opcode `29`, `R̄ = 0` |
| `vmovaps %xmm9, %xmm8` | `c4 41 78 28 c1` | 5 | three-byte VEX, `R̄`/`B̄` |
| `{evex} vmovaps %xmm1, %xmm0` | `62 f1 7c 08 28 c1` | 6 | EVEX, both low |
| `{evex} vmovaps %xmm1, %xmm8` | `62 71 7c 08 28 c1` | 6 | EVEX, `R̄ = 0` |
| `{evex} vmovaps %xmm9, %xmm0` | `62 d1 7c 08 28 c1` | 6 | EVEX, `B̄ = 0` |
| `{evex} vmovaps %xmm9, %xmm8` | `62 51 7c 08 28 c1` | 6 | EVEX, `R̄`/`B̄` |
| `movaps 8(%rax), %xmm8` | `44 0f 28 40 08` | 5 | legacy load, `REX.R`, `disp8` |
| `movaps 128(%r8), %xmm9` | `45 0f 28 88 80 00 00 00` | 8 | legacy load, `REX.R` + `REX.B`, `disp32` |
| `movaps %xmm10, 8(%rax)` | `44 0f 29 50 08` | 5 | legacy store, `REX.R`, `disp8` |
| `movaps %xmm11, 128(%r8)` | `45 0f 29 98 80 00 00 00` | 8 | legacy store, `REX.R` + `REX.B`, `disp32` |
| `vmovaps 8(%rax), %xmm8` | `c5 78 28 40 08` | 5 | VEX load, `R̄ = 0`, `disp8` |
| `vmovaps 128(%r15), %xmm9` | `c4 41 78 28 8f 80 00 00 00` | 9 | three-byte VEX load, `R̄`/`B̄`, `disp32` |
| `vmovaps %xmm10, 8(%rax)` | `c5 78 29 50 08` | 5 | VEX store, `R̄ = 0`, `disp8` |
| `vmovaps %xmm12, 8(%r8)` | `c4 41 78 29 60 08` | 6 | three-byte VEX store, `R̄`/`B̄`, `disp8` |
| `{evex} vmovaps 16(%rax), %xmm8` | `62 71 7c 08 28 40 01` | 7 | EVEX load, content `1` |
| `{evex} vmovaps 16(%r8), %xmm8` | `62 51 7c 08 28 40 01` | 7 | EVEX load, `R̄`/`B̄`, content `1` |
| `{evex} vmovaps %xmm12, 16(%r8)` | `62 51 7c 08 29 60 01` | 7 | EVEX store, `R̄`/`B̄`, content `1` |

The register is `ModRM.reg` in every load and in the EVEX register-direct row,
and `ModRM.rm` in every store and in the EVEX register-direct source. What
carries the fourth bit is the family's prefix.

## 2. Legacy uses one `REX` byte for both registers

`REX.R` is bit 2 and `REX.B` is bit 0 of the `0x40` prefix. The three byte rows
show the pattern directly: `44` is `REX.R`, `41` is `REX.B`, `45` is both, and
`0f 28 c1` has no `REX` at all. The two register fields do not change position
between the three windows: `ModRM.reg` is the destination in all of them and
`ModRM.rm` is the source.

The memory rows use the same two bits for two different operands. In
`movaps %xmm11, 128(%r8)` the `REX` byte is `45`: `REX.R` takes the `xmm`
source (`reg = 3`, so `xmm11`) and `REX.B` takes the base (`r/m = 0`, so `r8`).
One row can therefore carry a 4-bit `xmm` and a 4-bit base, which is why the
four new memory rows do not multiply into a register window times a base
window.

## 3. VEX has two spare bits in three-byte form; two-byte form has one

The two-byte `C5` prefix has `R̄` only, and on the register path its `ModRM.rm`
is still three bits. `llvm-mc` reaches a high destination by putting it in
`ModRM.reg` and inverting `R̄` (`c5 78 28 c1`), but a high source cannot go into
the three-bit `rm`. It solves that by moving the source into `ModRM.reg` and
using the store opcode: `vmovaps %xmm9, %xmm0` is `c5 78 29 c8`, where
`reg = 1` (`xmm9` with `R̄ = 0`) and `rm = 0` (`xmm0`). When both registers are
high, the instruction needs three-byte `C4`, which carries `R̄` and `B̄`:
`c4 41 78 28 c1`.

That split is not a free choice, because the same instruction has a second
legal spelling.

## 4. `vmovaps %xmm8, %xmm0` has two legal encodings

`llvm-mc -disassemble` on the raw strings:

| Bytes | `llvm-mc -disassemble` | Comment |
|---|---|---|
| `c5 78 29 c0` | `vmovaps %xmm8, %xmm0` | what the assembler emits, 4 bytes |
| `c4 c1 78 28 c0` | `vmovaps %xmm8, %xmm0` | also legal, 5 bytes |

`c4 c1 78 28 c0` puts the destination `xmm0` in `ModRM.reg` (`reg = 0` with
`R̄ = 1`, no extension) and the source `xmm8` in `ModRM.rm` (`rm = 0` with
`B̄ = 0`, extension on), while `c5 78 29 c0` uses the store opcode and swaps
which field holds which: `ModRM.reg` is the source `xmm8` (`R̄ = 0`) and
`ModRM.rm` the destination `xmm0`. Both decode to the same source instruction
and differ only in length. An encoder that preferred the `C4` form would emit
five bytes for a plan that the other honest implementation encodes in four, so
the table must pin one. `ADR-0038` pins the opcode-29 form, which is what
`llvm-mc` produces, and the row `x86:vmovaps/xmm-xmm-src-ext/vex` is the only row
that accepts a high source with a low destination.

## 5. EVEX carries the two registers in different bits

EVEX already has both extension bits, and they are inverted: `R̄` is bit 15 of
`P0`, `B̄` is bit 13. The destination is `ModRM.reg`, so it uses `R̄`; the
source is `ModRM.rm`, so it uses `B̄`. The four register-direct probes change
exactly those bits and nothing else:

- `f1` → `71` for `%xmm1, %xmm8` (`R̄ = 0`);
- `f1` → `d1` for `%xmm9, %xmm0` (`B̄ = 0`);
- `f1` → `51` for `%xmm9, %xmm8` (both).

Every row keeps its length: the register-direct form stays six bytes and the
`disp8*16` memory form stays seven. The memory probes confirm the same rule at
`P0`: `62 71 …` has a high destination, `62 51 …` has a high destination and a
high base, and `62 51 … 29 …` has a high source and a high base.

## 6. The oracle

`P15.asm` is twenty-three `movaps`/`vmovaps` mnemonics, with `{evex}` on the
seven EVEX lines; no hand-assembled bytes. The source is 578 bytes, SHA-256
`84e9e8c60c87314a3a25761ff740c9c0514040c56f844e4e5803caa249cdf366`. `.text`
is 128 bytes, SHA-256
`8b90dc8584225038019f697a6cbf490520cb8a54297069456b99c7731d299305`, and the
plan emits no fixup record. The fixture's expected bytes are this `.text`.

The sizes are 3, 4, 4, 4 (legacy register-direct), 4, 4, 4, 5 (VEX
register-direct), 6, 6, 6, 6 (EVEX register-direct), 5, 8, 5, 8 (legacy
memory), 5, 9, 5, 6 (VEX memory), 7, 7, 7 (EVEX memory); every one matches the
row the plan names.

## 7. The rejections

- `N01ag` names `x86:movaps/xmm-ext-xmm/legacy` against `0.10.0`:
  `E-FORM-001`. The register-extension rows are `0.11.0` forms.
- `N14i` passes `xmm16` to the 4-bit window: `E-OPERAND-004`,
  `field_bits = 4`. The fifth bit does not exist.
- `N14j` passes `xmm8` to the 3-bit legacy register-direct row:
  `E-OPERAND-004`. The low row has no `REX` byte and cannot carry it.
- `N14k` passes a high source to the two-byte VEX row:
  `E-OPERAND-004`. The source is `ModRM.rm`, which stays three bits there.
- `N16m` passes a low destination to a legacy register-extension row:
  `E-RANGE-004`, `excluded = [0…7]`.
- `N16n` passes a low source to the VEX source-extension row:
  `E-RANGE-004`, `excluded = [0…7]`.
- `N14e`/`N14f`/`N14g` still pin the `0.9.0`/`0.10.0` memory rows: `xmm8` on
  a 3-bit memory slot is `E-OPERAND-004`, and the widened memory rows keep
  their new values disjoint from the low rows.

## 8. What this does not claim

- `xmm16`–`xmm31` are absent. EVEX `R'`/`B'`/`X'` carry a fifth register bit;
  no row places them.
- A `SIB` base under these opcodes (`%rsp`, `%r12` with `r/m = 100`),
  `mod = 00` memory operands, EVEX masking, `ymm`/`zmm`, `movapd`'s `0x66`
  form and the 8/16-bit SSE width are absent.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
