# EXP-0066 -- the 32-bit `mov` family takes the `disp8` base shape

- Date: 2026-11-07
- Question: what does the `mod = 01` shape cost at 32-bit width, which
  register and base windows reach it, and which bases become legal that were
  excluded at `mod = 00`?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.37.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P41-gpr32-mov-mem-disp8.oracle.json`
- Source: `research/evidence/experiments/EXP-0066/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0066/fixture.asm`
- Decision: `ADR-0064`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%rax), %eax` | `8b 40 08` | 3 |
| `movl 8(%rsi), %edi` | `8b 7e 08` | 3 |
| `movl %eax, 8(%rax)` | `89 40 08` | 3 |
| `movl %edi, 8(%rsi)` | `89 7e 08` | 3 |
| `movl 8(%rax), %r8d` | `44 8b 40 08` | 4 |
| `movl 8(%r9), %r15d` | `45 8b 79 08` | 4 |
| `movl %r8d, 8(%rax)` | `44 89 40 08` | 4 |
| `movl %r15d, 8(%r9)` | `45 89 79 08` | 4 |
| `movl 8(%r8), %eax` | `41 8b 40 08` | 4 |
| `movl 8(%r15), %edi` | `41 8b 7f 08` | 4 |
| `movl %eax, 8(%r8)` | `41 89 40 08` | 4 |
| `movl %edi, 8(%r15)` | `41 89 7f 08` | 4 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers and base.

The displacement range end is measured in both directions: `-128` is
`8b 40 80` and `127` is `8b 40 7f`, both three bytes.

## 2. Where the fields sit

| Row | Bytes | `REX` | `ModRM` | Register | Base | `disp8` |
|---|---|---|---|---|---|---|
| low | `8b 40 08` | none | `40` (`mod = 01`) | 0–7 at `[11,3]` | 0–7 at `[8,3]` | `[16,8]` |
| `REX.R` | `44 8b 40 08` | `R = 1` | `40` | 8–15 at `[2,1]`, `[19,3]` | 0–15 at `[0,1]`, `[16,3]` | `[24,8]` |
| `REX.B` | `41 8b 40 08` | `B = 1` | `40` | 0–7 at `[19,3]` | 8–15 at `[0,1]`, `[16,3]` | `[24,8]` |

`mod = 01` in every row, so the `ModRM.r/m` field is an ordinary base and the
signed displacement follows. The displacement slot is `[16,8]` without a
`REX` byte and `[24,8]` behind one, as in the byte, word and 64-bit families.

### The three windows

| Source | Bytes | Why |
|---|---|---|
| `movl 8(%rax), %eax` | `8b 40 08` | low register, low base, no `REX` |
| `movl 8(%rax), %r8d` | `44 8b 40 08` | `REX.R = 1` for the register |
| `movl 8(%r8), %eax` | `41 8b 40 08` | `REX.B = 1` for the base |
| `movl 8(%r9), %r15d` | `45 8b 79 08` | both bits in one `REX` byte |

The windows are disjoint, as at `mod = 00`: the low row holds `reg = 0…7` and
`base = 0…7`, the `REX.R` row excludes the low registers, and the `REX.B` row
excludes the low bases. The exclusion is load-bearing, not cosmetic: with a
low base accepted on the `REX.B` row, the base's `REX.B` placement would clear
the fixed template bit and emit `40 8b 40 08` -- a valid encoding of a
different instruction. `N16ba` pins the exclusion.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl -128(%rax), %eax` | `8b 40 80` | 3 | the low `disp8` end |
| `movl 127(%rax), %eax` | `8b 40 7f` | 3 | the high `disp8` end |
| `movl 128(%rax), %eax` | `8b 80 80 00 00 00` | 6 | `mod = 10`, `disp32` |
| `movl 200(%rax), %eax` | `8b 80 c8 00 00 00` | 6 | the same, `200` |
| `movl (%rax), %eax` | `8b 00` | 2 | the `mod = 00` row (`0.35.0`) |
| `movl 8(%rbp), %eax` | `8b 45 08` | 3 | `%rbp` is ordinary at `mod = 01` |
| `movl 8(%r13), %eax` | `41 8b 45 08` | 4 | `%r13` with `REX.B = 1` |
| `movl 8(%rsp), %eax` | `8b 44 24 08` | 4 | `SIB` shape, next slice |
| `movl 8(%r12), %eax` | `41 8b 44 24 08` | 5 | `SIB` shape with `REX.B` |
| `movq 8(%rax), %rax` | `48 8b 40 08` | 4 | 64-bit analogue (`0.33.0`) |
| `movw 8(%rax), %ax` | `66 8b 40 08` | 4 | 16-bit analogue |
| `movl 8(%rax), %r16d` | `d5 40 8b 40 08` | 5 | APX `d5` prefix |

`adjacent-encoding.txt` records all twelve lines; no line is rejected.
`llvm-mc` normalises `movl 0(%rax), %eax` to the `mod = 00` row (`8b 00`), so
a zero displacement cannot reach the `disp8` rows through the assembler.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cb` | names `x86:mov/r32-base-disp8/legacy` against `0.36.0` | `E-FORM-001` |
| `N01cc` | names `x86:mov/base-disp8-r32/legacy` against `0.36.0` | `E-FORM-001` |
| `N02bg` | omits the `disp` operand | `E-OPERAND-002` (`expected 3, found 2`) |
| `N03r` | supplies `disp = 128`, one past the signed byte | `E-RANGE-001` |
| `N14an` | register `16` on the four-bit `REX.R` window | `E-OPERAND-004` |
| `N14ao` | register `8` on the 3-bit low row | `E-OPERAND-004` |
| `N16ax` | base `%rsp` on the low row | `E-RANGE-004` |
| `N16ay` | base `%r12` on the `REX.R` row | `E-RANGE-004` |
| `N16az` | register `0` on the `REX.R` row | `E-RANGE-004` |
| `N16ba` | base `0` on the `REX.B` row | `E-RANGE-004` |

The `disp32` claim is measured the same way: a copy of the fixture whose
first `disp` operand carries `target_type: disp32` is rejected with one
`E-OPERAND-001` at `/instructions/0/operands/2/target_type`
(`expected=disp8, found=disp32`), so the displacement width is the form and
not a value the row re-encodes.

## 5. The fixture

`X86-P41-gpr32-mov-mem-disp8` is twelve instructions and 44 bytes: each of
the six rows twice, at both ends of its windows.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%rax), %eax` | `8b 40 08` | 3 |
| 2 | `movl 8(%rsi), %edi` | `8b 7e 08` | 3 |
| 3 | `movl %eax, 8(%rax)` | `89 40 08` | 3 |
| 4 | `movl %edi, 8(%rsi)` | `89 7e 08` | 3 |
| 5 | `movl 8(%rax), %r8d` | `44 8b 40 08` | 4 |
| 6 | `movl 8(%r9), %r15d` | `45 8b 79 08` | 4 |
| 7 | `movl %r8d, 8(%rax)` | `44 89 40 08` | 4 |
| 8 | `movl %r15d, 8(%r9)` | `45 89 79 08` | 4 |
| 9 | `movl 8(%r8), %eax` | `41 8b 40 08` | 4 |
| 10 | `movl 8(%r15), %edi` | `41 8b 7f 08` | 4 |
| 11 | `movl %eax, 8(%r8)` | `41 89 40 08` | 4 |
| 12 | `movl %edi, 8(%r15)` | `41 89 7f 08` | 4 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`cd62903ceefe9666309839575710954c4dcfe6d6bf2fa975765bd4bf5b1a97d1`
(`fixture.asm`) and its `output_sha256` is
`f364e91c462381cec2df1bd7610ad7efe7b2b13ca4e7b83da3a08ed786ab1268`
(the 44-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:a5295df28545b250a5bf89bc37f4bcd408e7d530dd31b5cc871654ea507b213c`.

## 6. What the slice defers

- The `%rsp`/`%r12` `SIB` `disp8` rows.
- The `disp32` base rows and the `disp8`/`disp32` `SIB` rows.
- An index or scale operand.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- The same shape at 16 and 8 bits.
- The APX `d5` register window (`%r16d`–`%r31d`).
