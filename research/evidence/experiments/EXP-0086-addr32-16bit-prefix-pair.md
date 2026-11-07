# EXP-0086 -- the `0x67 66` 16-bit value rows on the 32-bit indexed `mov`

- Date: 2026-11-07
- Question: what does the `0x66` operand-size prefix add after `0x67` on the
  32-bit indexed `mov`, and where does the second prefix sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.57.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P61-gpr16-mov-index-addr32-prefix-pair.oracle.json`
- Source: `research/evidence/experiments/EXP-0086/probe.asm`
- Decision: `ADR-0084`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%eax,%ecx,1), %ax` | `67 66 8b 44 08 08` | 6 |
| `movw %ax, 8(%eax,%ecx,1)` | `67 66 89 44 08 08` | 6 |
| `movw 200(%eax,%ecx,1), %ax` | `67 66 8b 84 08 c8 00 00 00` | 9 |
| `movw %ax, 200(%eax,%ecx,1)` | `67 66 89 84 08 c8 00 00 00` | 9 |
| `movw 8(%ebp,%ecx,1), %ax` | `67 66 8b 44 0d 08` | 6 |
| `movw 8(%eax,%ebp,1), %ax` | `67 66 8b 44 28 08` | 6 |
| `movw 8(%eax,%ecx,8), %ax` | `67 66 8b 44 c8 08` | 6 |
| `movw 8(%eax,%ecx,1), %dx` | `67 66 8b 54 08 08` | 6 |

`llvm-mc -disassemble` on `probes.txt` returns all eight byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

The geometry is the `0.54.0` geometry: `0x67` at byte 0, `0x66` at byte 1, the
opcode at byte 2, `ModRM` at byte 3 and `SIB` at byte 4. The value register is
`[27,3]`, the base `[32,3]`, the index `[35,3]`, the scale `[38,2]` and the
displacement `[40,8]` or `[40,32]`. The `0x66` prefix takes the byte the `REX`
prefix occupies on the 32/64-bit rows, so no field moves. Because the bare pair
has no `REX` byte, the value, base and index are three-bit fields:

| Source | `ModRM` | `SIB` | Value | Base | Index |
|---|---|---|---|---|---|
| `%ax`, `%eax`, `%ecx` | `44` | `08` | `%ax` (0) | `%eax` (0) | `%ecx` (1) |
| `%ax`, `%ebp`, `%ecx` | `44` | `0d` | `%ax` (0) | `%ebp` (5) | `%ecx` (1) |
| `%ax`, `%eax`, `%ebp` | `44` | `28` | `%ax` (0) | `%eax` (0) | `%ebp` (5) |
| `%ax`, `%eax`, `%ecx` x8 | `44` | `c8` | `%ax` (0) | `%eax` (0) | `%ecx` (1), scale 3 |
| `%dx`, `%eax`, `%ecx` | `54` | `08` | `%dx` (2) | `%eax` (0) | `%ecx` (1) |

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%r8d,%ecx,1), %ax` | `67 66 41 8b 44 08 08` | 7 | needs `REX.B` at byte 2 (deferred window) |
| `movw 8(%eax,%ecx,1), %r8w` | `67 66 44 8b 44 08 08` | 7 | needs `REX.R` at byte 2 (deferred window) |
| `movw 8(%rax,%rcx,1), %ax` | `66 8b 44 08 08` | 5 | 64-bit addressing, no `0x67` |
| `movl 8(%eax,%ecx,1), %eax` | `67 8b 44 08 08` | 5 | the 32-bit value row |
| `movw 8(%esp,%ecx,1), %ax` | `67 66 8b 44 0c 08` | 6 | `%esp` as a base (`SIB.base = 100`) |
| `movw 8(%eax,%esp,1), %ax` | rejected | -- | `%esp` is not an index |
| `movw 8(%eax,%ecx,1), %eax` | rejected | -- | value register must be 16-bit |

`adjacent-encoding.txt` records the seven accepted lines and the two assembler
diagnostics. A `REX` window inserts the byte at position 2 and moves the
opcode, `ModRM`, `SIB` and displacement one byte later, which is why it is a
separate set of rows rather than an operand value.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dp` | names `x86:mov/r16-addr32-base-index-disp8/legacy` against `0.56.0` | `E-FORM-001` |
| `N01dq` | names `x86:mov/addr32-base-index-disp8-r16/legacy` against `0.56.0` | `E-FORM-001` |
| `N02cc` | drops the `index` from the `0x67 66` row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N02cd` | uses an `x86.gpr64`/`rm64` base, the 64-bit address register | two `E-OPERAND-001` |
| `N03zj` | scale `4`, past the two-bit field | `E-RANGE-001` |
| `N16ct` | index `4`, the `%esp`/`%rsp` slot | `E-RANGE-004` |
| `N14bt` | value register `8`, past its three-bit field | `E-OPERAND-004` |
| `N14bu` | base `8`, past its three-bit field | `E-OPERAND-004` |

The claims the ADR turns on: the prefix order is `0x67` then `0x66`, the second
prefix takes the `REX` byte's position, and a value that would need a `REX`
byte belongs to a different row. Nothing truncates and no row inserts a prefix
it does not fix.

## 5. The fixture

`X86-P61-gpr16-mov-index-addr32-prefix-pair` is eight instructions and 54
bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%eax,%ecx,1), %ax` | `67 66 8b 44 08 08` | 6 |
| 2 | `movw %ax, 8(%eax,%ecx,1)` | `67 66 89 44 08 08` | 6 |
| 3 | `movw 200(%eax,%ecx,1), %ax` | `67 66 8b 84 08 c8 00 00 00` | 9 |
| 4 | `movw %ax, 200(%eax,%ecx,1)` | `67 66 89 84 08 c8 00 00 00` | 9 |
| 5 | `movw 8(%ebp,%ecx,1), %ax` | `67 66 8b 44 0d 08` | 6 |
| 6 | `movw 8(%eax,%ebp,1), %ax` | `67 66 8b 44 28 08` | 6 |
| 7 | `movw 8(%eax,%ecx,8), %ax` | `67 66 8b 44 c8 08` | 6 |
| 8 | `movw 8(%eax,%ecx,1), %dx` | `67 66 8b 54 08 08` | 6 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`b4a154fc04347729200ede4c1247037bc90c52b0e66ab5514c0552c216211271`
(`probe.asm`) and its `output_sha256` is
`10c47fed39710702a6710262cb120a44ec832eeb45521ce47d2c3b677afe3cc1`
(the 54-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:389724b72665bb02e1f5ec0cd0766e96c3eae67b962355f3018df4cadce6625e`.

`0.57.0` has 453 forms and the canonical digest
`sha256:4b41ac755862f46d9e9e8bd574c399d8aa6a771cf93358772e590fae11314ca7`.

## 6. What the slice defers

- The `0x67 66` `REX` windows (`%r8w` values, `%r8d` addresses), which put a
  byte at position 2 and move every later field.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
- A 64-bit address register with `0x67`.
