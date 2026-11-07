# EXP-0090 -- the `0x67` no-base indexed shape at the 32-bit value width

- Date: 2026-11-08
- Question: what does the no-base indexed shape cost when the value is 32-bit
  and the `0x67 66` pair reduces to `0x67`, and where do the fields sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.61.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P65-gpr32-mov-index-addr32-no-base.oracle.json`
- Source: `research/evidence/experiments/EXP-0090/probe.asm`
- Decision: `ADR-0088`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-08. The first eight lines are
the four `REX` windows in both directions; the last five are the corners.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(,%ecx,1), %eax` | `67 8b 04 0d 08 00 00 00` | 8 |
| `movl %eax, 8(,%ecx,1)` | `67 89 04 0d 08 00 00 00` | 8 |
| `movl 8(,%ecx,1), %r8d` | `67 44 8b 04 0d 08 00 00 00` | 9 |
| `movl %r8d, 8(,%ecx,1)` | `67 44 89 04 0d 08 00 00 00` | 9 |
| `movl 8(,%r9d,1), %eax` | `67 42 8b 04 0d 08 00 00 00` | 9 |
| `movl %eax, 8(,%r9d,1)` | `67 42 89 04 0d 08 00 00 00` | 9 |
| `movl 8(,%r9d,1), %r8d` | `67 46 8b 04 0d 08 00 00 00` | 9 |
| `movl %r8d, 8(,%r9d,1)` | `67 46 89 04 0d 08 00 00 00` | 9 |
| `movl 0(,%ecx,1), %eax` | `67 8b 04 0d 00 00 00 00` | 8 |
| `movl -8(,%ecx,1), %eax` | `67 8b 04 0d f8 ff ff ff` | 8 |
| `movl 8(,%ecx,4), %eax` | `67 8b 04 8d 08 00 00 00` | 8 |
| `movl 8(,%r12d,1), %eax` | `67 42 8b 04 25 08 00 00 00` | 9 |
| `movl 4660(,%r15d,8), %r15d` | `67 46 8b 3c fd 34 12 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns all thirteen byte strings as the
same registers, indexes, scales and displacements
(`probes-disassembled.txt`).

## 2. Where the fields sit

`SIB.base = 101` at `mod = 00` means "no base, `disp32`", so the shape has no
`base` role and the displacement is present at every value, including zero.
Without the `0x66` there are still two geometries, because the `REX` byte is
optional (there is no base register, so no `REX.B`):

| Row | 0x67 | `REX` | opcode | `ModRM` | `SIB` | `disp32` |
|---|---|---|---|---|---|---|
| no `REX` | byte 0 | -- | byte 1 | byte 2 | byte 3 | bytes 4-7 |
| `R`/`X`/`RX` | byte 0 | byte 1 | byte 2 | byte 3 | byte 4 | bytes 5-8 |

| Row | value | index | scale | displacement |
|---|---|---|---|---|
| no `REX` | `[19,3]` | `[27,3]` | `[30,2]` | `[32,32]` |
| `R`/`X`/`RX` | `[27,3]`, `R` at `[10,1]` | `[35,3]`, `X` at `[9,1]` | `[38,2]` | `[40,32]` |

`ModRM = 04` (mod `00`, rm `100`) announces the `SIB`; `SIB.base` is the
constant `101`, so the byte is `05` in the template and the index and scale
fill bits 3-5 and 6-7. Index `4` is a register here, not the "no index"
constant: `movl 8(,%r12d,1), %eax` is `67 42 8b 04 25 …`, with `SIB = 25`
(index `4`, `X = 1`, base `101`). On the rows without `REX.X`, index `4` is
still rejected (`E-RANGE-004`), and on the `X`/`RX` rows the index slot's floor
is `8`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%eax,%ecx,1), %eax` | `67 8b 44 08 08` | 5 | base+index |
| `movw 8(,%ecx,1), %ax` | `67 66 8b 04 0d 08 00 00 00` | 9 | the `0.60.0` `movw` sibling |
| `movl 8(,%rcx,1), %eax` | `8b 04 0d 08 00 00 00` | 7 | 64-bit addressing, no `0x67` |
| `movl 4660, %eax` | `8b 04 25 34 12 00 00` | 7 | absolute `SIB = 25`, no `0x67` |
| `movq 8(,%ecx,1), %rax` | `67 48 8b 04 0d 08 00 00 00` | 9 | `REX.W`, deferred to its own slice |
| `movl 8(,%esp,1), %eax` | rejected | -- | `%esp` is not an index |
| `movl 8(,%ecx,1), %ax` | rejected | -- | value register must be 32-bit |

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dx` | names `x86:mov/r32-addr32-index-disp32/legacy` against `0.60.0` | `E-FORM-001` |
| `N01dy` | names `x86:mov/addr32-index-disp32-r32/legacy` against `0.60.0` | `E-FORM-001` |
| `N02ci` | drops the `index` from the `REX.RX` row | `E-OPERAND-002` (`expected 4, found 3`) |
| `N02cj` | supplies a `base` the shape does not have | `E-OPERAND-002` (`expected 4, found 5`) |
| `N03zn` | scale `4`, past the two-bit field | `E-RANGE-001` |
| `N14by` | value register `16`, past the four-bit field | `E-OPERAND-004` |
| `N16dc` | index `4` on the row that leaves `REX.X` at `0` | `E-RANGE-004` |
| `N16dd` | index `0` on the `REX.RX` row, below its window floor | `E-RANGE-004` |

## 5. The fixture

`X86-P65-gpr32-mov-index-addr32-no-base` is thirteen instructions and 112 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(,%ecx,1), %eax` | `67 8b 04 0d 08 00 00 00` | 8 |
| 2 | `movl %eax, 8(,%ecx,1)` | `67 89 04 0d 08 00 00 00` | 8 |
| 3 | `movl 8(,%ecx,1), %r8d` | `67 44 8b 04 0d 08 00 00 00` | 9 |
| 4 | `movl %r8d, 8(,%ecx,1)` | `67 44 89 04 0d 08 00 00 00` | 9 |
| 5 | `movl 8(,%r9d,1), %eax` | `67 42 8b 04 0d 08 00 00 00` | 9 |
| 6 | `movl %eax, 8(,%r9d,1)` | `67 42 89 04 0d 08 00 00 00` | 9 |
| 7 | `movl 8(,%r9d,1), %r8d` | `67 46 8b 04 0d 08 00 00 00` | 9 |
| 8 | `movl %r8d, 8(,%r9d,1)` | `67 46 89 04 0d 08 00 00 00` | 9 |
| 9 | `movl 0(,%ecx,1), %eax` | `67 8b 04 0d 00 00 00 00` | 8 |
| 10 | `movl -8(,%ecx,1), %eax` | `67 8b 04 0d f8 ff ff ff` | 8 |
| 11 | `movl 8(,%ecx,4), %eax` | `67 8b 04 8d 08 00 00 00` | 8 |
| 12 | `movl 8(,%r12d,1), %eax` | `67 42 8b 04 25 08 00 00 00` | 9 |
| 13 | `movl 4660(,%r15d,8), %r15d` | `67 46 8b 3c fd 34 12 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`334d0828797d74dea2ed1dc1e8d91911d19f28077857d4fef58398f677579c03`
(`probe.asm`) and its `output_sha256` is
`d7aca8522f852486c08655bec11d0303343a03452db41fb589a777793f752c35`
(the 112-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:6ea257d9c202507494351be2d20aea78de4c25240eab380225399c666efd83b7`.

`0.61.0` has 497 forms and the canonical digest
`sha256:e5a57fc7f72d810283980e1c059ff4195b77b1bc3c5ff30ff830798d7dd91983`.

## 6. What the slice defers

- The `REX.W` `movq` variant (`67 48`/`67 4c`/`67 4a`/`67 4e`). Its `REX` byte
  is mandatory and `R`/`X` are free bits inside it, so it is a different row
  decomposition and gets its own slice.
- A symbol or relocation in the `disp32` of this shape.
- The absolute `SIB = 25` shape with `0x67` (`movl 4660, %eax` is emitted
  without `0x67`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
- A 64-bit address register with `0x67`.
