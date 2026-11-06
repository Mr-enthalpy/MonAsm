# EXP-0067 -- the 32-bit `mov` family takes the `disp32` base shape

- Date: 2026-11-07
- Question: what does the `mod = 10` shape cost at 32-bit width, where does the
  signed 32-bit range end, and which windows does it share with `disp8`?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.38.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P42-gpr32-mov-mem-disp32.oracle.json`
- Source: `research/evidence/experiments/EXP-0067/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0067/fixture.asm`
- Decision: `ADR-0065`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07, all at displacement
`200`.

| Source | Bytes | Length |
|---|---|---|
| `movl 200(%rax), %eax` | `8b 80 c8 00 00 00` | 6 |
| `movl 200(%rsi), %edi` | `8b be c8 00 00 00` | 6 |
| `movl %eax, 200(%rax)` | `89 80 c8 00 00 00` | 6 |
| `movl %edi, 200(%rsi)` | `89 be c8 00 00 00` | 6 |
| `movl 200(%rax), %r8d` | `44 8b 80 c8 00 00 00` | 7 |
| `movl 200(%r9), %r15d` | `45 8b b9 c8 00 00 00` | 7 |
| `movl %r8d, 200(%rax)` | `44 89 80 c8 00 00 00` | 7 |
| `movl %r15d, 200(%r9)` | `45 89 b9 c8 00 00 00` | 7 |
| `movl 200(%r8), %eax` | `41 8b 80 c8 00 00 00` | 7 |
| `movl 200(%r15), %edi` | `41 8b bf c8 00 00 00` | 7 |
| `movl %eax, 200(%r8)` | `41 89 80 c8 00 00 00` | 7 |
| `movl %edi, 200(%r15)` | `41 89 bf c8 00 00 00` | 7 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers and base.

The range ends are measured directly: `2147483647` is `8b 80 ff ff ff 7f` and
`-2147483648` is `8b 80 00 00 00 80`, both six bytes.

## 2. Where the fields sit

| Row | Bytes | `REX` | `ModRM` | Register | Base | `disp32` |
|---|---|---|---|---|---|---|
| low | `8b 80 c8 00 00 00` | none | `80` (`mod = 10`) | 0–7 at `[11,3]` | 0–7 at `[8,3]` | `[16,32]` |
| `REX.R` | `44 8b 80 c8 00 00 00` | `R = 1` | `80` | 8–15 at `[2,1]`, `[19,3]` | 0–15 at `[0,1]`, `[16,3]` | `[24,32]` |
| `REX.B` | `41 8b 80 c8 00 00 00` | `B = 1` | `80` | 0–7 at `[19,3]` | 8–15 at `[0,1]`, `[16,3]` | `[24,32]` |

`mod = 10` in every row, so the `ModRM.r/m` field is an ordinary base and the
signed displacement follows. The displacement slot is `[16,32]` without a
`REX` byte and `[24,32]` behind one, as in the byte, word and 64-bit
families.

### The three windows

| Source | Bytes | Why |
|---|---|---|
| `movl 200(%rax), %eax` | `8b 80 c8 00 00 00` | low register, low base, no `REX` |
| `movl 200(%rax), %r8d` | `44 8b 80 c8 00 00 00` | `REX.R = 1` for the register |
| `movl 200(%r8), %eax` | `41 8b 80 c8 00 00 00` | `REX.B = 1` for the base |
| `movl 200(%r9), %r15d` | `45 8b b9 c8 00 00 00` | both bits in one `REX` byte |

The windows are disjoint, as at `mod = 00` and `mod = 01`. The `REX.B` row
again excludes the low bases, because a low value would clear the fixed
`REX.B` bit and emit `40 8b 80 c8 00 00 00` -- a different instruction
(`N16be`).

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 2147483647(%rax), %eax` | `8b 80 ff ff ff 7f` | 6 | the high `disp32` end |
| `movl -2147483648(%rax), %eax` | `8b 80 00 00 00 80` | 6 | the low `disp32` end |
| `movl 128(%rax), %eax` | `8b 80 80 00 00 00` | 6 | `128` belongs to this row, not `disp8` |
| `movl 8(%rax), %eax` | `8b 40 08` | 3 | the `disp8` row (`0.37.0`) |
| `movl (%rax), %eax` | `8b 00` | 2 | the `mod = 00` row (`0.35.0`) |
| `movl 200(%rbp), %eax` | `8b 85 c8 00 00 00` | 6 | `%rbp` is ordinary at `mod = 10` |
| `movl 200(%r13), %eax` | `41 8b 85 c8 00 00 00` | 7 | `%r13` with `REX.B = 1` |
| `movl 200(%rsp), %eax` | `8b 84 24 c8 00 00 00` | 7 | `SIB` shape, next slice |
| `movl 200(%r12), %eax` | `41 8b 84 24 c8 00 00 00` | 8 | `SIB` shape with `REX.B` |
| `movq 200(%rax), %rax` | `48 8b 80 c8 00 00 00` | 7 | 64-bit analogue (`0.33.0`) |
| `movw 200(%rax), %ax` | `66 8b 80 c8 00 00 00` | 7 | 16-bit analogue |
| `movl 200(%rax), %r16d` | `d5 40 8b 80 c8 00 00 00` | 8 | APX `d5` prefix |

`adjacent-encoding.txt` records all twelve lines; no line is rejected.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cd` | names `x86:mov/r32-base-disp32/legacy` against `0.37.0` | `E-FORM-001` |
| `N01ce` | names `x86:mov/base-disp32-r32/legacy` against `0.37.0` | `E-FORM-001` |
| `N02bh` | omits the `disp` operand | `E-OPERAND-002` (`expected 3, found 2`) |
| `N03s` | supplies `disp = 2147483648`, one past the signed span | `E-RANGE-001` |
| `N14ap` | register `16` on the four-bit `REX.R` window | `E-OPERAND-004` |
| `N14aq` | register `8` on the 3-bit low row | `E-OPERAND-004` |
| `N16bb` | base `%rsp` on the low row | `E-RANGE-004` |
| `N16bc` | base `%r12` on the `REX.R` row | `E-RANGE-004` |
| `N16bd` | register `0` on the `REX.R` row | `E-RANGE-004` |
| `N16be` | base `0` on the `REX.B` row | `E-RANGE-004` |

The `disp8` claim is measured the same way: a copy of the fixture whose first
`disp` operand carries `target_type: disp8` is rejected with one
`E-OPERAND-001` at `/instructions/0/operands/2/target_type`
(`expected=disp32, found=disp8`), so the displacement width is the form and
not a value the row re-encodes.

## 5. The fixture

`X86-P42-gpr32-mov-mem-disp32` is twelve instructions and 80 bytes: each of
the six rows twice at `200`, at both ends of its windows.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 200(%rax), %eax` | `8b 80 c8 00 00 00` | 6 |
| 2 | `movl 200(%rsi), %edi` | `8b be c8 00 00 00` | 6 |
| 3 | `movl %eax, 200(%rax)` | `89 80 c8 00 00 00` | 6 |
| 4 | `movl %edi, 200(%rsi)` | `89 be c8 00 00 00` | 6 |
| 5 | `movl 200(%rax), %r8d` | `44 8b 80 c8 00 00 00` | 7 |
| 6 | `movl 200(%r9), %r15d` | `45 8b b9 c8 00 00 00` | 7 |
| 7 | `movl %r8d, 200(%rax)` | `44 89 80 c8 00 00 00` | 7 |
| 8 | `movl %r15d, 200(%r9)` | `45 89 b9 c8 00 00 00` | 7 |
| 9 | `movl 200(%r8), %eax` | `41 8b 80 c8 00 00 00` | 7 |
| 10 | `movl 200(%r15), %edi` | `41 8b bf c8 00 00 00` | 7 |
| 11 | `movl %eax, 200(%r8)` | `41 89 80 c8 00 00 00` | 7 |
| 12 | `movl %edi, 200(%r15)` | `41 89 bf c8 00 00 00` | 7 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`8205f590bf8a0ae999f82ae7f7a7081f4e024a183c071f888917cfaeecf433a6`
(`fixture.asm`) and its `output_sha256` is
`6de815507ac8e73844efe42c8a14deb3a93a122aee8d52a4ca239bc3617a7f41`
(the 80-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:eb9940037899802fc4e74a7276ec605eaf5b1f30842d928815b9a6521d8ceebc`.

## 6. What the slice defers

- The `%rsp`/`%r12` `SIB` `disp8` and `disp32` rows.
- An index or scale operand.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- The same shape at 16 and 8 bits.
- The APX `d5` register window (`%r16d`–`%r31d`).
