# EXP-0064 -- the 32-bit `mov` family takes its first base rows

- Date: 2026-11-07
- Question: what does the `mod = 00` plain-base shape cost at 32-bit width,
  which windows does the missing `REX` byte force, and how does it compare
  with the `abs32` and displacement shapes?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.35.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P39-gpr32-mov-mem-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0064/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0064/fixture.asm`
- Decision: `ADR-0062`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl (%rax), %eax` | `8b 00` | 2 |
| `movl (%rsi), %edi` | `8b 3e` | 2 |
| `movl %eax, (%rax)` | `89 00` | 2 |
| `movl %edi, (%rsi)` | `89 3e` | 2 |
| `movl (%rax), %r8d` | `44 8b 00` | 3 |
| `movl (%r9), %r15d` | `45 8b 39` | 3 |
| `movl %r8d, (%rax)` | `44 89 00` | 3 |
| `movl %r15d, (%r9)` | `45 89 39` | 3 |
| `movl (%r8), %eax` | `41 8b 00` | 3 |
| `movl (%r15), %edi` | `41 8b 3f` | 3 |
| `movl %eax, (%r8)` | `41 89 00` | 3 |
| `movl %edi, (%r15)` | `41 89 3f` | 3 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers and base.

## 2. Where the fields sit

| Row | Bytes | `REX` | `ModRM.reg` | `ModRM.rm` |
|---|---|---|---|---|
| low/low | `8b 00` | none | register 0–7 at `[11,3]` | base 0–7 at `[8,3]` |
| `REX.R` | `44 8b 00` | `R = 1` | register 8–15 at `[19,3]` | base 0–15 at `[16,3]`, `REX.B` at `[0,1]` |
| `REX.B` | `41 8b 00` | `B = 1` | register 0–7 at `[19,3]` | base 8–15 at `[16,3]`, `REX.B` at `[0,1]` |

`mod = 00` in every row: `ModRM = 00` in the low rows, and the base's low
three bits in the higher rows (`00`, `39`, `3f` in the fixture).

### The three windows

| Source | Bytes | `REX` | Why |
|---|---|---|---|
| `movl (%rax), %eax` | `8b 00` | none | no extension bit is needed |
| `movl (%r8), %eax` | `41 8b 00` | `B = 1` | the base is above `7` |
| `movl (%rax), %r8d` | `44 8b 00` | `R = 1` | the register is above `7` |
| `movl (%r9), %r15d` | `45 8b 39` | `R = 1`, `B = 1` | both are above `7` |

The low row cannot carry a base above `7`, because its `r/m` field is three
bits and it has no `REX` byte to write the fourth bit into. The `REX.R` row
accepts every base (`REX.B` is a slot), and the `REX.B` row accepts only
bases `8`–`15`. The three register/base windows are therefore disjoint, so a
`(register, base)` pair names exactly one row.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl (%rbp), %eax` | `8b 45 00` | 3 | `mod = 01`, `disp8 = 0` |
| `movl (%r13), %eax` | `41 8b 45 00` | 4 | the same with `REX.B = 1` |
| `movl (%rsp), %eax` | `8b 04 24` | 3 | `SIB` base |
| `movl (%r12), %eax` | `41 8b 04 24` | 4 | the same, `REX.B = 1` |
| `movl (%rip), %eax` | `8b 05 00 00 00 00` | 6 | `mod = 00`, `r/m = 101` is RIP-relative `disp32` |
| `movl 0(%rax), %eax` | `8b 00` | 2 | the assembler normalises an explicit zero |
| `movl 8(%rax), %eax` | `8b 40 08` | 3 | `disp8` base row, not this shape |
| `movq (%rax), %rax` | `48 8b 00` | 3 | 64-bit analogue (`0.33.0`) |
| `movw (%rax), %ax` | `66 8b 00` | 3 | 16-bit analogue, `0x66` prefix |
| `movb (%rax), %al` | `8a 00` | 2 | byte analogue (`0.31.0`) |
| `movl (%rax), %r16d` | `d5 40 8b 00` | 4 | APX `d5` prefix, `%r16d` |
| `movl %eax, 8(%r8)` | `41 89 40 08` | 4 | `disp8` store with `REX.B` |

`adjacent-encoding.txt` records all twelve lines; no line is rejected.
`%rbp`/`%r13` never reach this shape at `mod = 00`: their `r/m = 101` is
RIP-relative in 64-bit mode.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bx` | names `x86:mov/r32-base/legacy` against `0.34.0` | `E-FORM-001` |
| `N01by` | names `x86:mov/base-r32/legacy` against `0.34.0` | `E-FORM-001` |
| `N02bd` | supplies a `disp` operand to the low row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N14aj` | register `16` on the four-bit `REX.R` window | `E-OPERAND-004` |
| `N14ak` | register `8` on the 3-bit low row | `E-OPERAND-004` |
| `N16as` | base `%rsp` (`4`) on the low row | `E-RANGE-004` |
| `N16at` | base `%r12` (`12`) on the `REX.R` row | `E-RANGE-004` |
| `N16au` | register `0` on the `REX.R` row | `E-RANGE-004` |
| `N16av` | base `0` on the `REX.B` row | `E-RANGE-004` |

## 5. The fixture

`X86-P39-gpr32-mov-mem-nodisp` is twelve instructions and 32 bytes: each of
the six rows twice, at both ends of its window.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl (%rax), %eax` | `8b 00` | 2 |
| 2 | `movl (%rsi), %edi` | `8b 3e` | 2 |
| 3 | `movl %eax, (%rax)` | `89 00` | 2 |
| 4 | `movl %edi, (%rsi)` | `89 3e` | 2 |
| 5 | `movl (%rax), %r8d` | `44 8b 00` | 3 |
| 6 | `movl (%r9), %r15d` | `45 8b 39` | 3 |
| 7 | `movl %r8d, (%rax)` | `44 89 00` | 3 |
| 8 | `movl %r15d, (%r9)` | `45 89 39` | 3 |
| 9 | `movl (%r8), %eax` | `41 8b 00` | 3 |
| 10 | `movl (%r15), %edi` | `41 8b 3f` | 3 |
| 11 | `movl %eax, (%r8)` | `41 89 00` | 3 |
| 12 | `movl %edi, (%r15)` | `41 89 3f` | 3 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`088c1b4e7e7c8e395aab01fd4f538f4ec36e55fd1f898f68fa5b23d51d2d0fd2`
(`fixture.asm`) and its `output_sha256` is
`e29e5845843ce667da6d3e5c236062ee8d54e46445124335a40ce455e6cbb835`
(the 32-byte `.text`). The materializer's output is byte-identical to the
oracle.

## 6. What the slice defers

- The `%rsp`/`%r12` `SIB` bases at 32-bit width.
- The `disp8`/`disp32` base shapes, which do not exist yet.
- The `0x67` address-size prefix.
- A symbol or relocation in an address.
- The same shape at 16 and 8 bits.
- The APX `d5` register window (`%r16d`–`%r31d`).
