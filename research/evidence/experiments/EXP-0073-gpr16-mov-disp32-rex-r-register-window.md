# EXP-0073 -- the 16-bit `disp32` rows take the `REX.R` register window

- Date: 2026-11-07
- Question: how does `%r8w`–`%r15w` reach the 16-bit `disp32` `mov` rows,
  where does the four-byte displacement sit once `REX` is present, and which
  bases are legal at `mod = 10`?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.44.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P48-gpr16-mov-mem-disp32-rex-r.oracle.json`
- Source: `research/evidence/experiments/EXP-0073/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0073/probe.asm` (the same
  fourteen lines)
- Decision: `ADR-0071`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw 200(%rax), %r8w` | `66 44 8b 80 c8 00 00 00` | 8 |
| `movw 200(%rdi), %r15w` | `66 44 8b bf c8 00 00 00` | 8 |
| `movw 200(%r8), %r8w` | `66 45 8b 80 c8 00 00 00` | 8 |
| `movw 200(%r15), %r15w` | `66 45 8b bf c8 00 00 00` | 8 |
| `movw %r8w, 200(%rax)` | `66 44 89 80 c8 00 00 00` | 8 |
| `movw %r15w, 200(%rdi)` | `66 44 89 bf c8 00 00 00` | 8 |
| `movw %r8w, 200(%r8)` | `66 45 89 80 c8 00 00 00` | 8 |
| `movw %r15w, 200(%r15)` | `66 45 89 bf c8 00 00 00` | 8 |
| `movw 200(%rsp), %r8w` | `66 44 8b 84 24 c8 00 00 00` | 9 |
| `movw %r8w, 200(%rsp)` | `66 44 89 84 24 c8 00 00 00` | 9 |
| `movw 200(%r12), %r8w` | `66 45 8b 84 24 c8 00 00 00` | 9 |
| `movw %r8w, 200(%r12)` | `66 45 89 84 24 c8 00 00 00` | 9 |
| `movw 200(%r12), %r15w` | `66 45 8b bc 24 c8 00 00 00` | 9 |
| `movw %r15w, 200(%r12)` | `66 45 89 bc 24 c8 00 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns all fourteen byte strings as the
same registers and base (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `0x66` | `REX` | Opcode | `ModRM` | Register | Base | Displacement |
|---|---|---|---|---|---|---|---|---|
| `REX.R`, low base | `66 44 8b 80 c8 00 00 00` | byte 0 | `44` at `[8,8]` | byte 2 | `80` at `[24,8]` (`mod = 10`, `r/m = 0`) | `R` at `[10,1]`, `[27,3]` | `r/m` at `[24,3]` | `[32,32]` |
| `REX.RB` | `66 45 8b 80 c8 00 00 00` | byte 0 | `45` at `[8,8]` | byte 2 | `80` at `[24,8]` (`mod = 10`, `r/m = 0`) | `R` at `[10,1]`, `[27,3]` | `r/m` at `[24,3]`, `B` at `[8,1]` | `[32,32]` |
| `REX.R`, `%rsp` | `66 44 8b 84 24 c8 00 00 00` | byte 0 | `44` at `[8,8]` | byte 2 | `84` at `[24,8]` (`mod = 10`, `r/m = 100`) | `R` at `[10,1]`, `[27,3]` | fixed `SIB = 24` at byte 4 | `[40,32]` |
| `REX.RB`, `%r12` | `66 45 8b 84 24 c8 00 00 00` | byte 0 | `45` at `[8,8]` | byte 2 | `84` at `[24,8]` (`mod = 10`, `r/m = 100`) | `R` at `[10,1]`, `[27,3]` | fixed `SIB = 24` at byte 4, `B` at `[8,1]` | `[40,32]` |

The `0x66` prefix is byte 0, so the `REX` byte is byte 1 and its bit 0
(`REX.B`) is `[8,1]`, while `REX.R` (bit 2 of that byte) is `[10,1]`.
`ModRM` is byte 3, so its `reg` field is `[27,3]` and its `mod` field is
`10`. The four displacement bytes follow the `ModRM` byte on the plain rows
and the `SIB` byte on the `SIB` rows.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the ones that
sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 200(%rbp), %r8w` | `66 44 8b 85 c8 00 00 00` | 8 | `%rbp` is a legal base at `mod = 10` (`r/m = 101`), unlike `mod = 00` |
| `movw 200(%r13), %r8w` | `66 45 8b 85 c8 00 00 00` | 8 | the same behind `REX.B` |
| `movw 2147483647(%rax), %r8w` | `66 44 8b 80 ff ff ff 7f` | 8 | the signed 32-bit upper end |
| `movw -2147483648(%rax), %r8w` | `66 44 8b 80 00 00 00 80` | 8 | the signed 32-bit lower end |
| `movw 127(%rax), %r8w` | `66 44 8b 40 7f` | 5 | the `disp8` row, a separate shape |
| `movw 8(%rax), %r8w` | `66 44 8b 40 08` | 5 | the same `disp8` shape |
| `movw 200(%rsp,%rax), %r8w` | `66 44 8b 84 04 c8 00 00 00` | 9 | `SIB` index, next axis |
| `movw 200(%rsp,%rax,4), %r8w` | `66 44 8b 84 84 c8 00 00 00` | 9 | index plus scale |
| `movw 200(%rax), %ax` | `66 8b 80 c8 00 00 00` | 7 | the low-register row, already frozen |
| `movw 200(%rax), %r16w` | `66 d5 40 8b 80 c8 00 00 00` | 10 | APX `d5` register window, a separate slice |

`2147483648(%rax)` is rejected by the assembler
(`displacement 2147483648 is not within [-2147483648, 2147483647]`), which is
the negative `N03w` rather than an adjacent encoding.
`adjacent-encoding.txt` records the ten accepted lines.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cp` | names `x86:mov/r16-ext-base-disp32/legacy` against `0.43.0` | `E-FORM-001` |
| `N01cq` | names `x86:mov/base-disp32-r16-ext/legacy` against `0.43.0` | `E-FORM-001` |
| `N02bn` | drops the `disp` from `x86:mov/r16-ext-base-disp32/legacy` | `E-OPERAND-002` (`expected 3, found 2`) |
| `N03w` | `disp32 = 2147483648` on the same row | `E-RANGE-001` |
| `N14ax` | register `16` on `x86:mov/r16-ext-base-disp32/legacy` | `E-OPERAND-004` |
| `N16bs` | register `0` on `x86:mov/r16-ext-base-ext-disp32/legacy` | `E-RANGE-004` |
| `N16bt` | base `%rsp` (`4`) on the plain row | `E-RANGE-004` |
| `N16bu` | base `%rbp` (`5`) on the `-ext`-base row | `E-RANGE-004` |

The two claims the ADR turns on: `2147483648` is `E-RANGE-001`, never a silent
wrap (`INV-07`); and a register value `0`–`7` on an `-ext` row is
`E-RANGE-004`, because the encoder never sets `REX.R` from the value.

`%rbp` is deliberately not a negative on the plain low-base row: it is a
legal base at `mod = 10` (`66 44 8b 85 c8 00 00 00`), and `N16bu` catches it
only on the `-ext` row, where it would clear the fixed `REX.B` bit.

## 5. The fixture

`X86-P48-gpr16-mov-mem-disp32-rex-r` is fourteen instructions and 118 bytes:
the four plain rows twice, at the `%r8w` and `%r15w` ends of the register
window, and the four fixed-base rows once at `%r8w` plus the two `%r12` rows
again at `%r15w`.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 200(%rax), %r8w` | `66 44 8b 80 c8 00 00 00` | 8 |
| 2 | `movw 200(%rdi), %r15w` | `66 44 8b bf c8 00 00 00` | 8 |
| 3 | `movw 200(%r8), %r8w` | `66 45 8b 80 c8 00 00 00` | 8 |
| 4 | `movw 200(%r15), %r15w` | `66 45 8b bf c8 00 00 00` | 8 |
| 5 | `movw %r8w, 200(%rax)` | `66 44 89 80 c8 00 00 00` | 8 |
| 6 | `movw %r15w, 200(%rdi)` | `66 44 89 bf c8 00 00 00` | 8 |
| 7 | `movw %r8w, 200(%r8)` | `66 45 89 80 c8 00 00 00` | 8 |
| 8 | `movw %r15w, 200(%r15)` | `66 45 89 bf c8 00 00 00` | 8 |
| 9 | `movw 200(%rsp), %r8w` | `66 44 8b 84 24 c8 00 00 00` | 9 |
| 10 | `movw %r8w, 200(%rsp)` | `66 44 89 84 24 c8 00 00 00` | 9 |
| 11 | `movw 200(%r12), %r8w` | `66 45 8b 84 24 c8 00 00 00` | 9 |
| 12 | `movw %r8w, 200(%r12)` | `66 45 89 84 24 c8 00 00 00` | 9 |
| 13 | `movw 200(%r12), %r15w` | `66 45 8b bc 24 c8 00 00 00` | 9 |
| 14 | `movw %r15w, 200(%r12)` | `66 45 89 bc 24 c8 00 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`9e2fca709419c2cf033030e75fc593e4f09e655a9254d00c121a90e47e5da842`
(`probe.asm`) and its `output_sha256` is
`657d9c5955267f67507861be7b9764085e82b4e7d4fab6e84c41be894f323680`
(the 118-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:e29bf74d165b482f9de8b7a841c39a15b8e3ff23ac3157f5ab7c7d183b2b40fc`.

`0.44.0` has 369 forms and the canonical digest
`sha256:4361f534bd04064d9ce0b89e8d5f6ad077ceb4a8c890b103efc16899e887c922`.

## 6. What the slice defers

- An index or scale operand (`66 44 8b 84 04 c8 00 00 00`).
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The same shape at 8 and 64 bits where a window is still missing.
- The APX `d5` register window (`66 d5 40 8b 80 c8 00 00 00`).
