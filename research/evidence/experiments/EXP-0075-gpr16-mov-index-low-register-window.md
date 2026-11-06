# EXP-0075 -- the 16-bit `mov` index/scale rows without `REX`

- Date: 2026-11-07
- Question: what does the low-register (`REX`-less) indexed 16-bit `mov` row
  cost, where do `ModRM`, `SIB` and the displacement sit, and how do the
  three-bit windows and the `%rsp`/`%rbp` bases behave?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.46.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P50-gpr16-mov-index-low.oracle.json`
- Source: `research/evidence/experiments/EXP-0075/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0075/probe.asm` (the same
  twelve lines)
- Decision: `ADR-0073`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%rax,%rcx,1), %ax` | `66 8b 44 08 08` | 5 |
| `movw 8(%rdi,%rsi,4), %di` | `66 8b 7c b7 08` | 5 |
| `movw 8(%rsp,%rcx,1), %ax` | `66 8b 44 0c 08` | 5 |
| `movw 8(%rbp,%rcx,1), %ax` | `66 8b 44 0d 08` | 5 |
| `movw %ax, 8(%rax,%rcx,1)` | `66 89 44 08 08` | 5 |
| `movw %di, 8(%rdi,%rsi,4)` | `66 89 7c b7 08` | 5 |
| `movw 200(%rax,%rcx,1), %ax` | `66 8b 84 08 c8 00 00 00` | 8 |
| `movw 200(%rdi,%rsi,4), %di` | `66 8b bc b7 c8 00 00 00` | 8 |
| `movw 200(%rsp,%rcx,1), %ax` | `66 8b 84 0c c8 00 00 00` | 8 |
| `movw 200(%rbp,%rcx,1), %ax` | `66 8b 84 0d c8 00 00 00` | 8 |
| `movw %ax, 200(%rax,%rcx,1)` | `66 89 84 08 c8 00 00 00` | 8 |
| `movw %di, 200(%rdi,%rsi,4)` | `66 89 bc b7 c8 00 00 00` | 8 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `0x66` | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|
| `disp8`, low | `66 8b 44 08 08` | byte 0 | byte 1 | `44` at `[16,8]` (`mod = 01`, `reg` at `[19,3]`, `r/m = 100`) | byte 3: scale `[30,2] = 0`, index `[27,3] = 1`, base `[24,3] = 0` | `[32,8]` |
| `disp8`, high index/base | `66 8b 7c b7 08` | byte 0 | byte 1 | `7c` (`mod = 01`, `reg = 7`, `r/m = 100`) | `b7`: scale `2`, index `6`, base `7` | `[32,8]` |
| `disp8`, `%rsp` base | `66 8b 44 0c 08` | byte 0 | byte 1 | `44` (`mod = 01`, `r/m = 100`) | `0c`: scale `0`, index `1`, base `4` | `[32,8]` |
| `disp8`, `%rbp` base | `66 8b 44 0d 08` | byte 0 | byte 1 | `44` (`mod = 01`, `r/m = 100`) | `0d`: scale `0`, index `1`, base `5` | `[32,8]` |
| `disp32`, low | `66 8b 84 08 c8 00 00 00` | byte 0 | byte 1 | `84` (`mod = 10`, `r/m = 100`) | `08`: scale `0`, index `1`, base `0` | `[32,32]` |
| `disp32`, high index/base | `66 8b bc b7 c8 00 00 00` | byte 0 | byte 1 | `bc` (`mod = 10`, `reg = 7`, `r/m = 100`) | `b7`: scale `2`, index `6`, base `7` | `[32,32]` |

There is no `REX` byte, so `ModRM` is byte 2 and its `reg` field is `[19,3]`;
`r/m = 100` announces the `SIB` byte at byte 3, with `base` at `[24,3]`,
`index` at `[27,3]` and `scale` at `[30,2]`. The displacement follows the
`SIB` byte, so the indexed rows move it from `[24,8]`/`[24,32]` to
`[32,8]`/`[32,32]` relative to the plain `disp8`/`disp32` rows.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the ones that
sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%rax,%rsp,1), %ax` | rejected | -- | `%rsp` is not an index (`invalid base+index expression`) |
| `movw 8(%rax,%rcx,1), %r8w` | `66 44 8b 44 08 08` | 6 | the `0.45.0` `REX.R` row |
| `movw 8(%r8,%rcx,1), %ax` | `66 41 8b 44 08 08` | 6 | the `REX.B` base window, a separate form |
| `movw 8(%rax,%r9,1), %ax` | `66 42 8b 44 08 08` | 6 | the `REX.X` index window, a separate form |
| `movw 8(%r8,%r9,1), %ax` | `66 43 8b 44 08 08` | 6 | the `REX.BX` window, a separate form |
| `movw 8(%rax), %ax` | `66 8b 40 08` | 4 | no index (`SIB` absent), already frozen |
| `movw 127(%rax,%rcx,1), %ax` | `66 8b 44 08 7f` | 5 | the signed byte upper end |
| `movw -128(%rax,%rcx,1), %ax` | `66 8b 44 08 80` | 5 | the signed byte lower end |
| `movw 8(%rax,%rcx,1), %r16w` | `66 d5 40 8b 44 08 08` | 7 | APX `d5` register window, a separate slice |
| `movw 200(%r8,%rcx,1), %ax` | `66 41 8b 84 08 c8 00 00 00` | 9 | the `REX.B` `disp32` row, a separate form |

`adjacent-encoding.txt` records the nine accepted lines and the assembler
diagnostic for the `%rsp` index.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01ct` | names `x86:mov/r16-base-index-disp8/legacy` against `0.45.0` | `E-FORM-001` |
| `N01cu` | names `x86:mov/base-index-disp8-r16/legacy` against `0.45.0` | `E-FORM-001` |
| `N02bp` | drops the `index` from `x86:mov/r16-base-index-disp8/legacy` | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03y` | scale `4` on the same row, past the two-bit field | `E-RANGE-001` |
| `N14ba` | register `16` on the same row | `E-OPERAND-004` |
| `N14bb` | register `8` on the same row, past the three-bit field | `E-OPERAND-004` |
| `N14bc` | base `8` on the same row, past the three-bit field | `E-OPERAND-004` |
| `N16bx` | index `4` (`%rsp`, the "no index" encoding) on the same row | `E-RANGE-004` |

The claims the ADR turns on: the row has no `REX` byte, so register `8` and
base `8` cannot be expressed — accepting them would clear a bit the row does
not have (`INV-07`); index `4` is the `SIB.index = 100` "no index" encoding;
scale `4` is past the two-bit field and would be a truncated `0`.

`%rbp` is deliberately not a negative on the base: it is legal at `mod = 01`,
because `r/m = 100` announces the `SIB` byte and `SIB.base = 101` is a base
with a displacement. `%rsp` is legal as a base for the same reason
(`SIB.base = 100`), which is why `N14bc` uses base `8` instead of base `4`.

## 5. The fixture

`X86-P50-gpr16-mov-index-low` is twelve instructions and 78 bytes: the four
rows, both displacement widths, two scales, low registers and bases, and the
`SIB`-announced `%rsp`/`%rbp` bases.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%rax,%rcx,1), %ax` | `66 8b 44 08 08` | 5 |
| 2 | `movw 8(%rdi,%rsi,4), %di` | `66 8b 7c b7 08` | 5 |
| 3 | `movw 8(%rsp,%rcx,1), %ax` | `66 8b 44 0c 08` | 5 |
| 4 | `movw 8(%rbp,%rcx,1), %ax` | `66 8b 44 0d 08` | 5 |
| 5 | `movw %ax, 8(%rax,%rcx,1)` | `66 89 44 08 08` | 5 |
| 6 | `movw %di, 8(%rdi,%rsi,4)` | `66 89 7c b7 08` | 5 |
| 7 | `movw 200(%rax,%rcx,1), %ax` | `66 8b 84 08 c8 00 00 00` | 8 |
| 8 | `movw 200(%rdi,%rsi,4), %di` | `66 8b bc b7 c8 00 00 00` | 8 |
| 9 | `movw 200(%rsp,%rcx,1), %ax` | `66 8b 84 0c c8 00 00 00` | 8 |
| 10 | `movw 200(%rbp,%rcx,1), %ax` | `66 8b 84 0d c8 00 00 00` | 8 |
| 11 | `movw %ax, 200(%rax,%rcx,1)` | `66 89 84 08 c8 00 00 00` | 8 |
| 12 | `movw %di, 200(%rdi,%rsi,4)` | `66 89 bc b7 c8 00 00 00` | 8 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`e6d5037a6edee765b59e609d5f2f2fd39040aecce73c08c98b7674eb6024a424`
(`probe.asm`) and its `output_sha256` is
`cf3b734c17dd61226541ab6e92281e679abf5a4ff3a5950616035212ccc2f29e`
(the 78-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:3c523943694f80125b9ed10ba794fa25d3c4147ab11298306508fb3d2d4b2725`.

`0.46.0` has 377 forms and the canonical digest
`sha256:44a396f348cc940bdf247c21e4752358d929df952ea0c7f2e5b5be14a63e2e9e`.

## 6. What the slice defers

- The `REX.B`/`REX.X`/`REX.BX` windows on the same indexed rows, which are the
  `0.45.0` forms.
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The APX `d5` register window (`66 d5 40 8b 44 08 08`).
