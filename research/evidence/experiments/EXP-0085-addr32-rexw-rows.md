# EXP-0085 -- the `0x67` `REX.W` rows on the 32-bit indexed `movq`

- Date: 2026-11-07
- Question: what does `REX.W` cost after the `0x67` address-size prefix on the
  32-bit indexed `mov`, and does it need a window family or one wide row?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.56.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P60-gpr64-mov-index-addr32-rex-w.oracle.json`
- Source: `research/evidence/experiments/EXP-0085/probe.asm`
- Decision: `ADR-0083`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movq 8(%eax,%ecx,1), %rax` | `67 48 8b 44 08 08` | 6 |
| `movq %rax, 8(%eax,%ecx,1)` | `67 48 89 44 08 08` | 6 |
| `movq 200(%eax,%ecx,1), %rax` | `67 48 8b 84 08 c8 00 00 00` | 9 |
| `movq %rax, 200(%eax,%ecx,1)` | `67 48 89 84 08 c8 00 00 00` | 9 |
| `movq 8(%r8d,%r9d,1), %r8` | `67 4f 8b 44 08 08` | 6 |
| `movq 8(%r12d,%r12d,1), %r12` | `67 4f 8b 64 24 08` | 6 |
| `movq 8(%r13d,%r13d,1), %r13` | `67 4f 8b 6c 2d 08` | 6 |
| `movq 8(%ebp,%ecx,1), %rax` | `67 48 8b 44 0d 08` | 6 |
| `movq 8(%eax,%r12d,1), %rax` | `67 4a 8b 44 20 08` | 6 |
| `movq 8(%r12d,%ecx,1), %rax` | `67 49 8b 44 0c 08` | 6 |
| `movq 8(%eax,%ecx,8), %rax` | `67 48 8b 44 c8 08` | 6 |
| `movq %r15, 8(%r15d,%ebp,1)` | `67 4d 89 7c 2f 08` | 6 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

The geometry is the `0.54.0` geometry: `0x67` at byte 0, `REX` at byte 1, the
opcode at byte 2, `ModRM` at byte 3 and `SIB` at byte 4. The value register is
`[10,1]`+`[27,3]`, the base `[8,1]`+`[32,3]`, the index `[9,1]`+`[35,3]`, the
scale `[38,2]` and the displacement `[40,8]` or `[40,32]`. `REX.W` is bit
`[11,1]` and is `1` in every row; `R`, `X` and `B` come from the operands:

| Source | `REX` | `W` | `R` | `X` | `B` |
|---|---|---|---|---|---|
| `%rax` low value, `%eax` base, `%ecx` index | `48` | 1 | 0 | 0 | 0 |
| `%r8` value, `%r8d` base, `%r9d` index | `4f` | 1 | 1 | 1 | 1 |
| `%rax` value, `%eax` base, `%r12d` index | `4a` | 1 | 0 | 1 | 0 |
| `%rax` value, `%r12d` base, `%ecx` index | `49` | 1 | 0 | 0 | 1 |

Because `REX.W` forces the prefix byte to exist, a low and a high register are
the same form with a different field value: `67 48` widens to `67 4f` without
changing the row, the length or the prefix order.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq 8(%eax,%esp,1), %rax` | rejected | -- | `%esp` is not an index |
| `movq 8(%rax,%rcx,1), %rax` | `48 8b 44 08 08` | 5 | 64-bit addressing, no `0x67` |
| `movq 8(%r8,%r9,1), %r8` | `4f 8b 44 08 08` | 5 | 64-bit addressing `REX.RBX` |
| `movl 8(%eax,%ecx,1), %eax` | `67 8b 44 08 08` | 5 | the 32-bit value row |
| `movq 8(%esp,%ecx,1), %rax` | `67 48 8b 44 0c 08` | 6 | `%esp` as a base (`SIB.base = 100`) |
| `movq 8(%eax,%ecx,1), %r8` | `67 4c 8b 44 08 08` | 6 | `REX.R` on the same row |
| `movq 8(%eax,%r9d,1), %rax` | `67 4a 8b 44 08 08` | 6 | `REX.X` on the same row |
| `movq 8(%r8d,%ecx,1), %rax` | `67 49 8b 44 08 08` | 6 | `REX.B` on the same row |
| `movq 8(%eax,%ecx,1), %eax` | rejected | -- | value register must be 64-bit |

`adjacent-encoding.txt` records the seven accepted lines and the two
assembler diagnostics. Every `REX` variant is six bytes with the same template;
the prefix and the byte count do not depend on the register values.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dn` | names `x86:mov/r64-addr32-base-index-disp8/legacy` against `0.55.0` | `E-FORM-001` |
| `N01do` | names `x86:mov/addr32-base-index-disp8-r64/legacy` against `0.55.0` | `E-FORM-001` |
| `N02ca` | drops the `index` from the `REX.W` row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N02cb` | uses an `x86.gpr64`/`rm64` base, the 64-bit address register | two `E-OPERAND-001` |
| `N03zi` | scale `4`, past the two-bit field | `E-RANGE-001` |
| `N16cs` | index `4`, the `%esp`/`%rsp` slot | `E-RANGE-004` |
| `N14br` | value register `16`, past its four-bit field | `E-OPERAND-004` |
| `N14bs` | index `16`, past its four-bit field | `E-OPERAND-004` |

The claims the ADR turns on: `REX.W` does not add a row per register window,
the address registers stay 32-bit under `0x67`, and a value that would need a
bit the row leaves clear is rejected rather than truncated.

## 5. The fixture

`X86-P60-gpr64-mov-index-addr32-rex-w` is twelve instructions and 78 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movq 8(%eax,%ecx,1), %rax` | `67 48 8b 44 08 08` | 6 |
| 2 | `movq %rax, 8(%eax,%ecx,1)` | `67 48 89 44 08 08` | 6 |
| 3 | `movq 200(%eax,%ecx,1), %rax` | `67 48 8b 84 08 c8 00 00 00` | 9 |
| 4 | `movq %rax, 200(%eax,%ecx,1)` | `67 48 89 84 08 c8 00 00 00` | 9 |
| 5 | `movq 8(%r8d,%r9d,1), %r8` | `67 4f 8b 44 08 08` | 6 |
| 6 | `movq 8(%r12d,%r12d,1), %r12` | `67 4f 8b 64 24 08` | 6 |
| 7 | `movq 8(%r13d,%r13d,1), %r13` | `67 4f 8b 6c 2d 08` | 6 |
| 8 | `movq 8(%ebp,%ecx,1), %rax` | `67 48 8b 44 0d 08` | 6 |
| 9 | `movq 8(%eax,%r12d,1), %rax` | `67 4a 8b 44 20 08` | 6 |
| 10 | `movq 8(%r12d,%ecx,1), %rax` | `67 49 8b 44 0c 08` | 6 |
| 11 | `movq 8(%eax,%ecx,8), %rax` | `67 48 8b 44 c8 08` | 6 |
| 12 | `movq %r15, 8(%r15d,%ebp,1)` | `67 4d 89 7c 2f 08` | 6 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`fe4978b67d2bb09a39ca2565127810ce031f4cc5125ebb0bbc3ba30e07620869`
(`probe.asm`) and its `output_sha256` is
`e8860e37deb5a930b0aae3885caf3fd1e9c7529a8a7866f7e15ea92a48ae29c3`
(the 78-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:ee0926b9747c03df56910f2bf0c7f8b2b0a4226f697817dd6f8603fb25b04a21`.

`0.56.0` has 449 forms and the canonical digest
`sha256:d039c97253fbdefba9c68c4fdab0d3310d17b809b8ba29fc268e6d8458f2ef87`.

## 6. What the slice defers

- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
- A 16-bit value or address width with `0x67`.
- A 64-bit address register with `0x67`.
