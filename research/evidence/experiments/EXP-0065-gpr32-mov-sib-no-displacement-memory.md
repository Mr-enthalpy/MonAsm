# EXP-0065 -- the 32-bit `mov` family takes the `%rsp`/`%r12` `SIB` bases

- Date: 2026-11-07
- Question: what does the `mod = 00` `SIB` shape cost at 32-bit width, how do
  the two bases differ, and which register windows can join them?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.36.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P40-gpr32-mov-mem-sib-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0065/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0065/fixture.asm`
- Decision: `ADR-0063`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl (%rsp), %eax` | `8b 04 24` | 3 |
| `movl (%rsp), %edi` | `8b 3c 24` | 3 |
| `movl %eax, (%rsp)` | `89 04 24` | 3 |
| `movl %edi, (%rsp)` | `89 3c 24` | 3 |
| `movl (%r12), %eax` | `41 8b 04 24` | 4 |
| `movl (%r12), %edi` | `41 8b 3c 24` | 4 |
| `movl %eax, (%r12)` | `41 89 04 24` | 4 |
| `movl %edi, (%r12)` | `41 89 3c 24` | 4 |
| `movl (%rsp), %r8d` | `44 8b 04 24` | 4 |
| `movl (%rsp), %r15d` | `44 8b 3c 24` | 4 |
| `movl %r8d, (%rsp)` | `44 89 04 24` | 4 |
| `movl %r15d, (%rsp)` | `44 89 3c 24` | 4 |
| `movl (%r12), %r8d` | `45 8b 04 24` | 4 |
| `movl (%r12), %r15d` | `45 8b 3c 24` | 4 |
| `movl %r8d, (%r12)` | `45 89 04 24` | 4 |
| `movl %r15d, (%r12)` | `45 89 3c 24` | 4 |

`llvm-mc -disassemble` on `probes.txt` returns all sixteen byte strings as the
same registers and base.

## 2. Where the fields sit

| Row | Bytes | `REX` | `ModRM` | `SIB` | Register |
|---|---|---|---|---|---|
| `%rsp`, low | `8b 04 24` | none | `04` | `24` | 0–7 at `[11,3]` |
| `%r12`, low | `41 8b 04 24` | `B = 1` | `04` | `24` | 0–7 at `[19,3]` |
| `%rsp`, `-ext` | `44 8b 04 24` | `R = 1` | `04` | `24` | 8–15 at `[2,1]`, `[19,3]` |
| `%r12`, `-ext` | `45 8b 04 24` | `R = 1`, `B = 1` | `04` | `24` | 8–15 at `[2,1]`, `[19,3]` |

`mod = 00` and `r/m = 100` in every row: the `SIB` byte is announced by
`ModRM.r/m` and carries `scale = 00`, `index = 100` (meaning none) and
`base = 100` (`%rsp`/`%r12`).

### The two bases

| Source | Bytes | `REX` | Why |
|---|---|---|---|
| `movl (%rsp), %eax` | `8b 04 24` | none | `SIB.base = 100` |
| `movl (%r12), %eax` | `41 8b 04 24` | `B = 1` | the same `SIB`, one `REX` bit |
| `movl (%rsp), %r8d` | `44 8b 04 24` | `R = 1` | the register is above `7` |
| `movl (%r12), %r8d` | `45 8b 04 24` | `R = 1`, `B = 1` | both |

The two bases share the low three bits `100`, so the `SIB` byte is identical
and `REX.B` is the only bit that tells them apart. Because the base is not an
operand, each base needs its own row, and a `base` operand is
`E-OPERAND-002`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl (%rbp), %eax` | `8b 45 00` | 3 | `mod = 01`, `disp8 = 0` |
| `movl (%r13), %eax` | `41 8b 45 00` | 4 | the same with `REX.B = 1` |
| `movl (%rip), %eax` | `8b 05 00 00 00 00` | 6 | `mod = 00`, `r/m = 101` is RIP-relative `disp32` |
| `movl 0(%rsp), %eax` | `8b 04 24` | 3 | the assembler normalises an explicit zero |
| `movl 8(%rsp), %eax` | `8b 44 24 08` | 4 | `disp8` `SIB` row, not this shape |
| `movl 8(%r12), %r8d` | `45 8b 44 24 08` | 5 | `disp8` `SIB` row with both bits |
| `movq (%rsp), %rax` | `48 8b 04 24` | 4 | 64-bit analogue (`0.34.0`) |
| `movw (%rsp), %ax` | `66 8b 04 24` | 4 | 16-bit analogue, `0x66` prefix |
| `movb (%rsp), %al` | `8a 04 24` | 3 | byte analogue (`0.32.0`) |
| `movl (%rsp), %r16d` | `d5 40 8b 04 24` | 5 | APX `d5` prefix, `%r16d` |
| `movl (%rax), %eax` | `8b 00` | 2 | the plain-base `0.35.0` row |
| `movl %eax, 8(%r12)` | `41 89 44 24 08` | 5 | `disp8` store with `REX.B` |

`adjacent-encoding.txt` records all twelve lines; no line is rejected.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bz` | names `x86:mov/r32-rsp/legacy` against `0.35.0` | `E-FORM-001` |
| `N01ca` | names `x86:mov/rsp-r32/legacy` against `0.35.0` | `E-FORM-001` |
| `N02be` | supplies a `base` operand to a fixed-base row | `E-OPERAND-002` (`expected 1, found 2`) |
| `N02bf` | supplies a `disp` operand there | `E-OPERAND-002` (`expected 1, found 2`) |
| `N14al` | register `16` on the four-bit `-ext` window | `E-OPERAND-004` |
| `N14am` | register `8` on the 3-bit low row | `E-OPERAND-004` |
| `N16aw` | register `0` on the `-ext` row | `E-RANGE-004` |

## 5. The fixture

`X86-P40-gpr32-mov-mem-sib-nodisp` is sixteen instructions and 60 bytes:
each of the eight rows twice, at both ends of its window.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl (%rsp), %eax` | `8b 04 24` | 3 |
| 2 | `movl (%rsp), %edi` | `8b 3c 24` | 3 |
| 3 | `movl %eax, (%rsp)` | `89 04 24` | 3 |
| 4 | `movl %edi, (%rsp)` | `89 3c 24` | 3 |
| 5 | `movl (%r12), %eax` | `41 8b 04 24` | 4 |
| 6 | `movl (%r12), %edi` | `41 8b 3c 24` | 4 |
| 7 | `movl %eax, (%r12)` | `41 89 04 24` | 4 |
| 8 | `movl %edi, (%r12)` | `41 89 3c 24` | 4 |
| 9 | `movl (%rsp), %r8d` | `44 8b 04 24` | 4 |
| 10 | `movl (%rsp), %r15d` | `44 8b 3c 24` | 4 |
| 11 | `movl %r8d, (%rsp)` | `44 89 04 24` | 4 |
| 12 | `movl %r15d, (%rsp)` | `44 89 3c 24` | 4 |
| 13 | `movl (%r12), %r8d` | `45 8b 04 24` | 4 |
| 14 | `movl (%r12), %r15d` | `45 8b 3c 24` | 4 |
| 15 | `movl %r8d, (%r12)` | `45 89 04 24` | 4 |
| 16 | `movl %r15d, (%r12)` | `45 89 3c 24` | 4 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`f252615fe6e7b1dfbe1908390831546f5c1e2e20c86ea916f0ce3fe621f2b4dc`
(`fixture.asm`) and its `output_sha256` is
`36adfe8e333c0ccbecc546667cd022d13c0e8d48ce55dee6c73e7d34187be346`
(the 60-byte `.text`). The materializer's output is byte-identical to the
oracle.

## 6. What the slice defers

- The `disp8`/`disp32` `SIB` shapes.
- An index or scale operand at 32-bit width.
- The `0x67` address-size prefix.
- A symbol or relocation in an address.
- The same shape at 16 and 8 bits.
- The APX `d5` register window (`%r16d`–`%r31d`).
