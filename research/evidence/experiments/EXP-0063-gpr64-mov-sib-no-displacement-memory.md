# EXP-0063 -- the 64-bit `mov` rows take the `SIB` bases at `mod = 00`

- Date: 2026-11-07
- Question: what does the `mod = 00` shape cost when the base is `%rsp` or
  `%r12`, which bits stay fixed, and how does it compare with the two
  displacement rows?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.34.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P38-gpr64-mov-mem-sib-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0063/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0063/fixture.asm`
- Decision: `ADR-0061`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movq (%rsp), %rax` | `48 8b 04 24` | 4 |
| `movq (%rsp), %r8` | `4c 8b 04 24` | 4 |
| `movq %rax, (%rsp)` | `48 89 04 24` | 4 |
| `movq %r8, (%rsp)` | `4c 89 04 24` | 4 |
| `movq (%r12), %rax` | `49 8b 04 24` | 4 |
| `movq (%r12), %r8` | `4d 8b 04 24` | 4 |
| `movq %rax, (%r12)` | `49 89 04 24` | 4 |
| `movq %r8, (%r12)` | `4d 89 04 24` | 4 |

`llvm-mc -disassemble` on `probes.txt` returns all eight byte strings as the
same register and base. Every row is four bytes: the `REX` byte, the opcode,
the `ModRM` that announces the `SIB`, and the `SIB`.

## 2. Where the fields sit

| Byte | Bits | Value | Fields |
|---|---|---|---|
| `REX` | `[0,8]` | `48`/`4c` (`%rsp`), `49`/`4d` (`%r12`) | `W = 1` and `B` are fixed per row; `R` = register's fourth bit at `[2,1]` |
| opcode | `[8,8]` | `8b` / `89` | fixed per direction |
| `ModRM` | `[16,8]` | `04` | `mod = 00`, `reg` = register at `[19,3]`, `r/m = 100` (announces the `SIB`) |
| `SIB` | `[24,8]` | `24` | `scale = 00`, `index = 100` (none), `base = 100` (the `SIB` base) |

`REX.W` is the 64-bit width, `REX.B` is the base's fourth bit, and the `SIB`
byte is a constant; all three are template content. `REX.R` is the only bit
the operand owns, so one row per base and direction covers all sixteen
registers.

### The two bases

| Source | Bytes | `REX` | Difference |
|---|---|---|---|
| `movq (%rsp), %rax` | `48 8b 04 24` | `48` | `R = 0`, `B = 0` |
| `movq (%r12), %rax` | `49 8b 04 24` | `49` | `B = 1` |
| `movq (%rsp), %r8` | `4c 8b 04 24` | `4c` | `R = 1`, `B = 0` |
| `movq (%r12), %r8` | `4d 8b 04 24` | `4d` | `R = 1`, `B = 1` |

The opcode, `ModRM` and `SIB` bytes are identical across all four rows; only
the `REX` byte moves. `movq (%rsp), %r15` is `4c 8b 3c 24` and
`movq (%r12), %r15` is `4d 8b 3c 24`, the top of the register field.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq (%rbp), %rax` | `48 8b 45 00` | 4 | `mod = 01`, `disp8 = 0` |
| `movq (%r13), %rax` | `49 8b 45 00` | 4 | the same with `REX.B = 1` |
| `movq 8(%rsp), %rax` | `48 8b 44 24 08` | 5 | `disp8` `SIB` row |
| `movq 8(%r12), %rax` | `49 8b 44 24 08` | 5 | the same, `REX.B = 1` |
| `movq (%rsp), %r16` | `d5 48 8b 04 24` | 5 | APX `d5` prefix, `%r16` |
| `movl (%rsp), %eax` | `8b 04 24` | 3 | 32-bit analogue, no `REX` |
| `movw (%rsp), %ax` | `66 8b 04 24` | 4 | 16-bit analogue, `66` prefix |
| `movb (%rsp), %al` | `8a 04 24` | 3 | byte analogue (`0.32.0`) |
| `movq (%rax), %rax` | `48 8b 00` | 3 | plain-base row (`0.33.0`) |

`adjacent-encoding.txt` records all eleven lines; no line is rejected.
`%rbp`/`%r13` never reach this shape: at `mod = 00` their `r/m = 101` is
RIP-relative, so `llvm-mc` writes `mod = 01` with `disp8 = 0` instead.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bv` | names `x86:mov/r64-rsp/legacy` against `0.33.0` | `E-FORM-001` |
| `N01bw` | names `x86:mov/r12-r64/legacy` against `0.33.0` | `E-FORM-001` |
| `N02bb` | supplies a `base` operand to the row | `E-OPERAND-002` (`expected 1, found 2`) |
| `N02bc` | supplies a `disp` operand to the row | `E-OPERAND-002` (`expected 1, found 2`) |
| `N14ai` | carries register `16` on the four-bit field | `E-OPERAND-004` |

## 5. The fixture

`X86-P38-gpr64-mov-mem-sib-nodisp` is eight instructions and 32 bytes: both
bases and both directions over `%rax` and `%r8`.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movq (%rsp), %rax` | `48 8b 04 24` | 4 |
| 2 | `movq (%rsp), %r8` | `4c 8b 04 24` | 4 |
| 3 | `movq %rax, (%rsp)` | `48 89 04 24` | 4 |
| 4 | `movq %r8, (%rsp)` | `4c 89 04 24` | 4 |
| 5 | `movq (%r12), %rax` | `49 8b 04 24` | 4 |
| 6 | `movq (%r12), %r8` | `4d 8b 04 24` | 4 |
| 7 | `movq %rax, (%r12)` | `49 89 04 24` | 4 |
| 8 | `movq %r8, (%r12)` | `4d 89 04 24` | 4 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`86d27dad9d68b0abc219f2d6eaf745506352b24f67dc59937fad7b1e06ef04ee`
(`fixture.asm`) and its `output_sha256` is
`d87ed6ef0fbbfe983b202faff0c435271cab591b2bab1d6e375e9df073c0d9fd`
(the 32-byte `.text`). The materializer's output is byte-identical to the
oracle.

## 6. What the slice defers

- The `REX.X` index and scale at 64-bit width.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- `moffs` at 64-bit width.
- The APX `d5` register window (`%r16`–`%r31`).
- The same shape at 32 and 16 bits: the 32-bit family has no `base` operand
  rows yet, and the 16-bit family splits by base window.
