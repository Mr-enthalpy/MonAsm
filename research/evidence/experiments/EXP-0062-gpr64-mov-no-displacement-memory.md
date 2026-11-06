# EXP-0062 -- the 64-bit `mov` rows take the `mod = 00` memory shape

- Date: 2026-11-07
- Question: what does the `mod = 00` shape cost on the 64-bit `mov` rows,
  which register fields carry the operands, which bases cannot use it, and how
  does it compare with the two displacement rows?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.33.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P37-gpr64-mov-mem-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0062/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0062/fixture.asm`
- Decision: `ADR-0060`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movq (%rax), %rax` | `48 8b 00` | 3 |
| `movq (%r8), %r8` | `4d 8b 00` | 3 |
| `movq (%r9), %r15` | `4d 8b 39` | 3 |
| `movq (%rdi), %rsi` | `48 8b 37` | 3 |
| `movq (%rsi), %rdi` | `48 8b 3e` | 3 |
| `movq %rax, (%rax)` | `48 89 00` | 3 |
| `movq %r8, (%r8)` | `4d 89 00` | 3 |
| `movq %r15, (%r9)` | `4d 89 39` | 3 |
| `movq %rsi, (%rdi)` | `48 89 37` | 3 |
| `movq %rdi, (%rsi)` | `48 89 3e` | 3 |

`llvm-mc -disassemble` on `probes.txt` returns all ten byte strings as the same
register and base. Every row is three bytes; no row here spends a displacement
byte.

## 2. Where the fields sit

| Byte | Bits | Value | Fields |
|---|---|---|---|
| `REX` | `[0,8]` | `48` / `4c` / `49` / `4d` | `W = 1` always; `R` = register's fourth bit at `[2,1]`; `B` = base's fourth bit at `[0,1]` |
| opcode | `[8,8]` | `8b` / `89` | fixed per direction |
| `ModRM` | `[16,8]` | `00`–`3f` | `mod = 00`, `reg` = register at `[19,3]`, `r/m` = base at `[16,3]` |

`REX.W = 1` is the whole 64-bit width decision and it is the same byte in
every row, so it is a template constant. `REX.R` and `REX.B` are the only bits
the operands own, and one row covers all sixteen registers and all sixteen
bases.

### The four register/base combinations

| Source | Bytes | Register | Base | `REX` |
|---|---|---|---|---|
| `movq (%rax), %rax` | `48 8b 00` | `%rax` (0) | `%rax` (0) | `R = 0`, `B = 0` |
| `movq (%r8), %r8` | `4d 8b 00` | `%r8` (8) | `%r8` (8) | `R = 1`, `B = 1` |
| `movq (%rdi), %rsi` | `48 8b 37` | `%rsi` (6) | `%rdi` (7) | `R = 0`, `B = 0`, low bits only |
| `movq (%r9), %r15` | `4d 8b 39` | `%r15` (15) | `%r9` (9) | `R = 1`, `B = 1`, both low fields `001`/`111` |

`movq (%rdi), %rsi` is `48 8b 37`: `ModRM = 37` is `mod = 00`, `reg = 110`
(`%rsi`) and `r/m = 111` (`%rdi`). Nothing in the row reads the operand value
to choose a `REX` bit; the bits are slots.

## 3. The three lengths and the four excluded bases

| Source | Bytes | Length | Reading |
|---|---|---|---|
| `movq (%rax), %rax` | `48 8b 00` | 3 | this slice |
| `movq 0(%rax), %rax` | `48 8b 00` | 3 | `llvm-mc` normalises the explicit zero to the short form |
| `movq 8(%rax), %rax` | `48 8b 40 08` | 4 | `disp8` row (`mod = 01`) |
| `movq 0x1234(%rax), %rax` | `48 8b 80 34 12 00 00` | 7 | `disp32` row (`mod = 10`) |
| `movq 0x1234, %rax` | `48 8b 04 25 34 12 00 00` | 8 | absolute `SIB = 25` row |

The normalisation is worth stating plainly: `llvm-mc` assembles `0(%rax)` to
the three-byte form, so the source spelling does not select the `disp8` row.
Our `disp8` row still has a legal `disp8 = 0` content (`48 8b 40 00`), but it
is a row the plan names, not a shape the assembler produces from that source.
The oracle for the `disp8` row is `movq 8(%rax), %rax`, not `0(%rax)`.

`movq (%rbp), %rax` is `48 8b 45 00` — `mod = 01` with `disp8 = 0` — because
`mod = 00` with `r/m = 101` is RIP-relative `disp32`, the separate
`x86:mov/r64-riprel32/legacy` row. `%rsp`/`%r12` are the other pair:
`movq (%rsp), %rax` is `48 8b 04 24` and `movq (%r12), %rax` is
`49 8b 04 24`, four bytes with a `SIB` byte and `REX.B` as the only
difference. So the base slot excludes `4`, `5`, `12` and `13`.

## 4. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq (%rsp), %rax` | `48 8b 04 24` | 4 | `SIB = 24`, base `%rsp` |
| `movq (%r12), %rax` | `49 8b 04 24` | 4 | the same `SIB`, `REX.B = 1` |
| `movq (%rbp), %rax` | `48 8b 45 00` | 4 | `mod = 01`, `disp8 = 0` |
| `movq (%r13), %rax` | `49 8b 45 00` | 4 | the same with `REX.B = 1` |
| `movq (%rax), %r16` | `d5 48 8b 00` | 4 | APX `d5` prefix, `%r16` |
| `movl (%rax), %eax` | `8b 00` | 2 | 32-bit analogue, no `REX` |
| `movw (%rax), %ax` | `66 8b 00` | 3 | 16-bit analogue, `66` prefix |
| `movb (%rax), %al` | `8a 00` | 2 | byte analogue (`0.31.0`) |
| `movq %rax, (%rsp)` | `48 89 04 24` | 4 | store over the `SIB` base |
| `movq %rax, (%r12)` | `49 89 04 24` | 4 | store, `REX.B = 1` |

`adjacent-encoding.txt` records all thirteen lines, including the explicit
`0(%rax)` that `llvm-mc` writes as `48 8b 00`; no line is rejected.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bt` | names `x86:mov/r64-base/legacy` against `0.32.0` | `E-FORM-001` |
| `N01bu` | names `x86:mov/base-r64/legacy` against `0.32.0` | `E-FORM-001` |
| `N02ba` | supplies a `disp` operand to the row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N14ah` | carries register `16` on the four-bit field | `E-OPERAND-004` |
| `N16ao` | base register `4` (`%rsp`) | `E-RANGE-004` |
| `N16ap` | base register `5` (`%rbp`) | `E-RANGE-004` |
| `N16aq` | base register `12` (`%r12`) | `E-RANGE-004` |
| `N16ar` | base register `13` (`%r13`) | `E-RANGE-004` |

## 6. The fixture

`X86-P37-gpr64-mov-mem-nodisp` is six instructions and 18 bytes: both
directions over `%rax` and `%r8` (the two `REX.R`/`REX.B` combinations), and
over `%r9` with `%r15` (the top of both four-bit fields).

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movq (%rax), %rax` | `48 8b 00` | 3 |
| 2 | `movq (%r8), %r8` | `4d 8b 00` | 3 |
| 3 | `movq (%r9), %r15` | `4d 8b 39` | 3 |
| 4 | `movq %rax, (%rax)` | `48 89 00` | 3 |
| 5 | `movq %r8, (%r8)` | `4d 89 00` | 3 |
| 6 | `movq %r15, (%r9)` | `4d 89 39` | 3 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`b937c57bc88d23e8ec707a9d114dc1249f481976dcc78143511114269e32decd`
(`fixture.asm`) and its `output_sha256` is
`8c1624a4d2865f2c02865636082e1bae9a7c8923c0f71f7e43996ef980dcbc26`
(the 18-byte `.text`). The materializer's output is byte-identical to the
oracle.

## 7. What the slice defers

- The `%rsp`/`%r12` `SIB` bases at `mod = 00` in this family.
- The `REX.X` index and scale at 64-bit width.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- `moffs` at 64-bit width.
- The APX `d5` register window (`%r16`–`%r31`).
- The same shape at 32 and 16 bits: the 32-bit family has no `base` operand
  rows yet, and the 16-bit family splits by base window.
