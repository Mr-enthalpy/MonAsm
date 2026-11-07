# EXP-0091 -- the `0x67` no-base indexed shape at the 64-bit value width

- Date: 2026-11-08
- Question: what does the no-base indexed shape cost when the value is 64-bit,
  so `REX.W` forces the `REX` byte to exist, and where do the fields sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.62.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P66-gpr64-mov-index-addr32-no-base.oracle.json`
- Source: `research/evidence/experiments/EXP-0091/probe.asm`
- Decision: `ADR-0089`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-08. The first eight lines
are the `REX` combinations in both directions; the last five are the corners.

| Source | Bytes | Length |
|---|---|---|
| `movq 8(,%ecx,1), %rax` | `67 48 8b 04 0d 08 00 00 00` | 9 |
| `movq %rax, 8(,%ecx,1)` | `67 48 89 04 0d 08 00 00 00` | 9 |
| `movq 8(,%ecx,1), %r8` | `67 4c 8b 04 0d 08 00 00 00` | 9 |
| `movq %r8, 8(,%ecx,1)` | `67 4c 89 04 0d 08 00 00 00` | 9 |
| `movq 8(,%r9d,1), %rax` | `67 4a 8b 04 0d 08 00 00 00` | 9 |
| `movq %rax, 8(,%r9d,1)` | `67 4a 89 04 0d 08 00 00 00` | 9 |
| `movq 8(,%r9d,1), %r8` | `67 4e 8b 04 0d 08 00 00 00` | 9 |
| `movq %r8, 8(,%r9d,1)` | `67 4e 89 04 0d 08 00 00 00` | 9 |
| `movq 0(,%ecx,1), %rax` | `67 48 8b 04 0d 00 00 00 00` | 9 |
| `movq -8(,%ecx,1), %rax` | `67 48 8b 04 0d f8 ff ff ff` | 9 |
| `movq 8(,%ecx,4), %rax` | `67 48 8b 04 8d 08 00 00 00` | 9 |
| `movq 8(,%r12d,1), %rax` | `67 4a 8b 04 25 08 00 00 00` | 9 |
| `movq 4660(,%r15d,8), %r15` | `67 4e 8b 3c fd 34 12 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns all thirteen byte strings as the
same registers, indexes, scales and displacements
(`probes-disassembled.txt`).

## 2. Where the fields sit

`REX.W` is mandatory, so the `REX` byte exists in every row and there is no
`REX`-less geometry; `R` and `X` are free bits inside that one byte, not
separate templates. `SIB.base = 101` at `mod = 00` still means "no base,
`disp32`", so the shape has no `base` role and the displacement is present at
every value, including zero.

| Byte | 0 | 1 | 2 | 3 | 4 | 5-8 |
|---|---|---|---|---|---|---|
| Content | `0x67` | `REX` | opcode | `ModRM = 04` | `SIB` | `disp32` |

| Row | value | index | scale | displacement |
|---|---|---|---|---|
| `REX = 48` | `[27,3]`, `R = 0` | `[35,3]`, `X = 0` | `[38,2]` | `[40,32]` |
| `REX = 4c` | `[27,3]`, `R` at `[10,1]` | `[35,3]`, `X = 0` | `[38,2]` | `[40,32]` |
| `REX = 4a` | `[27,3]`, `R = 0` | `[35,3]`, `X` at `[9,1]` | `[38,2]` | `[40,32]` |
| `REX = 4e` | `[27,3]`, `R` at `[10,1]` | `[35,3]`, `X` at `[9,1]` | `[38,2]` | `[40,32]` |

Because the `REX` byte is always present, one row per direction covers all
sixteen value registers and all sixteen indexes; `0x48` is the low pair, `0x4c`
sets `R`, `0x4a` sets `X` and `0x4e` sets both. Index `4` with `REX.X = 0` is
still the "no index" constant, so the index slot excludes `4`: `%r12d` is
legal through `REX.X = 1` (`movq 8(,%r12d,1), %rax` is
`67 4a 8b 04 25 …`, `SIB = 25`), and `movq 8(,%esp,1), %rax` is rejected.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq 8(%eax,%ecx,1), %rax` | `67 48 8b 44 08 08` | 6 | base+index |
| `movw 8(,%ecx,1), %ax` | `67 66 8b 04 0d 08 00 00 00` | 9 | the `0.60.0` `movw` sibling |
| `movl 8(,%ecx,1), %eax` | `67 8b 04 0d 08 00 00 00` | 8 | the `0.61.0` `movl` sibling |
| `movq 8(,%rcx,1), %rax` | `48 8b 04 0d 08 00 00 00` | 8 | 64-bit addressing, no `0x67` |
| `movq 4660, %rax` | `48 8b 04 25 34 12 00 00` | 8 | absolute `SIB = 25`, no `0x67` |
| `movq 8(,%r12,1), %rax` | `4a 8b 04 25 08 00 00 00` | 8 | 64-bit index register, no `0x67` |
| `movq 8(,%esp,1), %rax` | rejected | -- | `%esp` is not an index |
| `movq 8(,%ecx,1), %eax` | rejected | -- | value register must be 64-bit |

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dz` | names `x86:mov/r64-addr32-index-disp32/legacy` against `0.61.0` | `E-FORM-001` |
| `N01ea` | names `x86:mov/addr32-index-disp32-r64/legacy` against `0.61.0` | `E-FORM-001` |
| `N02ck` | drops the `index` from the load row | `E-OPERAND-002` (`expected 4, found 3`) |
| `N02cl` | supplies a `base` the shape does not have | `E-OPERAND-002` (`expected 4, found 5`) |
| `N03zo` | scale `4`, past the two-bit field | `E-RANGE-001` |
| `N14bz` | value register `16`, past the four-bit field | `E-OPERAND-004` |
| `N14ca` | index register `16`, past the four-bit field | `E-OPERAND-004` |
| `N16de` | index `4` with `REX.X = 0` | `E-RANGE-004` |

## 5. The fixture

`X86-P66-gpr64-mov-index-addr32-no-base` is thirteen instructions and 117
bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movq 8(,%ecx,1), %rax` | `67 48 8b 04 0d 08 00 00 00` | 9 |
| 2 | `movq %rax, 8(,%ecx,1)` | `67 48 89 04 0d 08 00 00 00` | 9 |
| 3 | `movq 8(,%ecx,1), %r8` | `67 4c 8b 04 0d 08 00 00 00` | 9 |
| 4 | `movq %r8, 8(,%ecx,1)` | `67 4c 89 04 0d 08 00 00 00` | 9 |
| 5 | `movq 8(,%r9d,1), %rax` | `67 4a 8b 04 0d 08 00 00 00` | 9 |
| 6 | `movq %rax, 8(,%r9d,1)` | `67 4a 89 04 0d 08 00 00 00` | 9 |
| 7 | `movq 8(,%r9d,1), %r8` | `67 4e 8b 04 0d 08 00 00 00` | 9 |
| 8 | `movq %r8, 8(,%r9d,1)` | `67 4e 89 04 0d 08 00 00 00` | 9 |
| 9 | `movq 0(,%ecx,1), %rax` | `67 48 8b 04 0d 00 00 00 00` | 9 |
| 10 | `movq -8(,%ecx,1), %rax` | `67 48 8b 04 0d f8 ff ff ff` | 9 |
| 11 | `movq 8(,%ecx,4), %rax` | `67 48 8b 04 8d 08 00 00 00` | 9 |
| 12 | `movq 8(,%r12d,1), %rax` | `67 4a 8b 04 25 08 00 00 00` | 9 |
| 13 | `movq 4660(,%r15d,8), %r15` | `67 4e 8b 3c fd 34 12 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`b872f69999fcd98afc667976d3cc108c230049551dfd538d4b2807febabda364`
(`probe.asm`) and its `output_sha256` is
`adafa7fc9a4253737b155c253659f86922e6172bb34ebf2ab365055f996fdd65`
(the 117-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:0809d80334740b8527de5c89cdec15766f1aae73d3e88fee83a9c2995a9ea63a`.

`0.62.0` has 499 forms and the canonical digest
`sha256:bbcd8062c84580e208c1cbf275254593a7d937fd7de28fde19e7dc5c5049e3b3`.

## 6. What the slice defers

- A symbol or relocation in the `disp32` of this shape.
- The absolute `SIB = 25` shape with `0x67` (`movq 4660, %rax` is emitted
  without `0x67`).
- A 64-bit address register with `0x67` (`movq 8(,%r12,1), %rax` is emitted
  without `0x67`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
