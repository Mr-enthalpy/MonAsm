# EXP-0089 -- the `0x67 66` no-base indexed shape on the 32-bit indexed `mov`

- Date: 2026-11-08
- Question: what does the `0x67 66` `movw` family cost when the address has an
  index and no base, and where do the fields sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.60.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P64-gpr16-mov-index-addr32-no-base.oracle.json`
- Source: `research/evidence/experiments/EXP-0089/probe.asm`
- Decision: `ADR-0087`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-08. The first eight lines are
the four `REX` windows in both directions; the last five are the corners.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(,%ecx,1), %ax` | `67 66 8b 04 0d 08 00 00 00` | 9 |
| `movw %ax, 8(,%ecx,1)` | `67 66 89 04 0d 08 00 00 00` | 9 |
| `movw 8(,%ecx,1), %r8w` | `67 66 44 8b 04 0d 08 00 00 00` | 10 |
| `movw %r8w, 8(,%ecx,1)` | `67 66 44 89 04 0d 08 00 00 00` | 10 |
| `movw 8(,%r9d,1), %ax` | `67 66 42 8b 04 0d 08 00 00 00` | 10 |
| `movw %ax, 8(,%r9d,1)` | `67 66 42 89 04 0d 08 00 00 00` | 10 |
| `movw 8(,%r9d,1), %r8w` | `67 66 46 8b 04 0d 08 00 00 00` | 10 |
| `movw %r8w, 8(,%r9d,1)` | `67 66 46 89 04 0d 08 00 00 00` | 10 |
| `movw 0(,%ecx,1), %ax` | `67 66 8b 04 0d 00 00 00 00` | 9 |
| `movw -8(,%ecx,1), %ax` | `67 66 8b 04 0d f8 ff ff ff` | 9 |
| `movw 8(,%ecx,4), %ax` | `67 66 8b 04 8d 08 00 00 00` | 9 |
| `movw 8(,%r12d,1), %ax` | `67 66 42 8b 04 25 08 00 00 00` | 10 |
| `movw 4660(,%r15d,8), %r15w` | `67 66 46 8b 3c fd 34 12 00 00` | 10 |

`llvm-mc -disassemble` on `probes.txt` returns all thirteen byte strings as the
same registers, indexes, scales and displacements (`probes-disassembled.txt`).

## 2. Where the fields sit

`SIB.base = 101` at `mod = 00` means "no base, `disp32`", so the shape has no
`base` role and the displacement is present at every value, including zero.
Because the `REX` byte is optional here (there is no base register, so no
`REX.B`), there are two geometries:

| Row | 0x67 | 0x66 | `REX` | opcode | `ModRM` | `SIB` | `disp32` |
|---|---|---|---|---|---|---|---|
| no `REX` | byte 0 | byte 1 | -- | byte 2 | byte 3 | byte 4 | bytes 5-8 |
| `R`/`X`/`RX` | byte 0 | byte 1 | byte 2 | byte 3 | byte 4 | byte 5 | bytes 6-9 |

| Row | value | index | scale | displacement |
|---|---|---|---|---|
| no `REX` | `[27,3]` | `[35,3]` | `[38,2]` | `[40,32]` |
| `R`/`X`/`RX` | `[35,3]`, `R` at `[18,1]` | `[43,3]`, `X` at `[17,1]` | `[46,2]` | `[48,32]` |

`ModRM = 04` (mod `00`, rm `100`) announces the `SIB`; `SIB.base` is the
constant `101`, so the byte is `05` in the template and the index and scale
fill bits 3-5 and 6-7. Index `4` is a register here, not the "no index"
constant: `movw 8(,%r12d,1), %ax` is `67 66 42 8b 04 25 …`, with `SIB = 25`
(index `4`, `X = 1`, base `101`). On the rows without `REX.X`, index `4` is
still rejected (`E-RANGE-004`), and on the `X`/`RX` rows the index slot's floor
is `8`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%eax,%ecx,1), %ax` | `67 66 8b 44 08 08` | 6 | base+index (`0.57.0`) |
| `movl 8(,%r9d,1), %eax` | `67 42 8b 04 0d 08 00 00 00` | 9 | 32-bit value, same shape |
| `movw 8(,%rcx,1), %ax` | `66 8b 04 0d 08 00 00 00` | 8 | 64-bit addressing, no `0x67` |
| `movw 4660, %ax` | `66 8b 04 25 34 12 00 00` | 8 | absolute `SIB = 25`, no `0x67` |
| `movq 8(,%r9,1), %rax` | `4a 8b 04 0d 08 00 00 00` | 8 | `REX.WRX`, no `0x67` |
| `movw 8(,%esp,1), %ax` | rejected | -- | `%esp` is not an index |
| `movw 8(,%r9d,1), %eax` | rejected | -- | value register must be 16-bit |

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dv` | names `x86:mov/r16-addr32-index-disp32/legacy` against `0.59.0` | `E-FORM-001` |
| `N01dw` | names `x86:mov/addr32-index-disp32-r16/legacy` against `0.59.0` | `E-FORM-001` |
| `N02cg` | drops the `index` from the `REX.RX` row | `E-OPERAND-002` (`expected 4, found 3`) |
| `N02ch` | supplies a `base` the shape does not have | `E-OPERAND-002` (`expected 4, found 5`) |
| `N03zm` | scale `4`, past the two-bit field | `E-RANGE-001` |
| `N14bx` | value register `16`, past the four-bit field | `E-OPERAND-004` |
| `N16da` | index `4` on the row that leaves `REX.X` at `0` | `E-RANGE-004` |
| `N16db` | index `0` on the `REX.RX` row, below its window floor | `E-RANGE-004` |

## 5. The fixture

`X86-P64-gpr16-mov-index-addr32-no-base` is thirteen instructions and 125 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(,%ecx,1), %ax` | `67 66 8b 04 0d 08 00 00 00` | 9 |
| 2 | `movw %ax, 8(,%ecx,1)` | `67 66 89 04 0d 08 00 00 00` | 9 |
| 3 | `movw 8(,%ecx,1), %r8w` | `67 66 44 8b 04 0d 08 00 00 00` | 10 |
| 4 | `movw %r8w, 8(,%ecx,1)` | `67 66 44 89 04 0d 08 00 00 00` | 10 |
| 5 | `movw 8(,%r9d,1), %ax` | `67 66 42 8b 04 0d 08 00 00 00` | 10 |
| 6 | `movw %ax, 8(,%r9d,1)` | `67 66 42 89 04 0d 08 00 00 00` | 10 |
| 7 | `movw 8(,%r9d,1), %r8w` | `67 66 46 8b 04 0d 08 00 00 00` | 10 |
| 8 | `movw %r8w, 8(,%r9d,1)` | `67 66 46 89 04 0d 08 00 00 00` | 10 |
| 9 | `movw 0(,%ecx,1), %ax` | `67 66 8b 04 0d 00 00 00 00` | 9 |
| 10 | `movw -8(,%ecx,1), %ax` | `67 66 8b 04 0d f8 ff ff ff` | 9 |
| 11 | `movw 8(,%ecx,4), %ax` | `67 66 8b 04 8d 08 00 00 00` | 9 |
| 12 | `movw 8(,%r12d,1), %ax` | `67 66 42 8b 04 25 08 00 00 00` | 10 |
| 13 | `movw 4660(,%r15d,8), %r15w` | `67 66 46 8b 3c fd 34 12 00 00` | 10 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`411d20729c21d72baf94443a5c2d75ced5dbae2718e8ff0e0ffd64dd76cb6641`
(`probe.asm`) and its `output_sha256` is
`d1c9a143fb638c0a66cdb92745312417be3696024461818af6cffd29bb879152`
(the 125-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:39fa4109a8541c382dba24af96fbf57f11ba86f461c2fdc912e83fe6f57de630`.

`0.60.0` has 489 forms and the canonical digest
`sha256:f951de4cc1532c3df5a8f715343d8a9e7a4b3ba302df49c9fa3fa2f85a45d7b1`.

## 6. What the slice defers

- The `REX.W` siblings (`67 66 48`–`67 66 4f`). `llvm-mc` never emits the
  redundant `0x66` under `REX.W`: `movq 8(%eax,%ecx,1), %rax` is
  `67 48 8b 44 08 08`, and `data16 movq …` emits `0x66` as its own instruction,
  so the object bytes are `66 67 48 8b 44 08 08` -- prefix before `0x67`,
  never `67 66 48 …`. The item therefore has no asm→obj oracle and stays
  deferred rather than becoming a row.
- A symbol or relocation in the `disp32` of this shape.
- The absolute `SIB = 25` shape with `0x67` (`movw 4660, %ax` is emitted
  without `0x67`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
- A 64-bit address register with `0x67`.
