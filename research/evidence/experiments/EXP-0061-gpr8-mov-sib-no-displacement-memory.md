# EXP-0061 -- the byte GPR `mov` rows take the `%rsp`/`%r12` `SIB` bases

- Date: 2026-11-07
- Question: what does the `mod = 00` byte `mov` shape cost when the base is
  `%rsp` or `%r12`, which register windows can inhabit it, and how does the
  fixed base show up in the row?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.32.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P36-gpr8-mov-mem-sib-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0061/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0061/fixture.asm`
- Decision: `ADR-0059`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movb (%rsp), %al` | `8a 04 24` | 3 |
| `movb (%r12), %al` | `41 8a 04 24` | 4 |
| `movb (%rsp), %ah` | `8a 24 24` | 3 |
| `movb (%rsp), %spl` | `40 8a 24 24` | 4 |
| `movb (%r12), %spl` | `41 8a 24 24` | 4 |
| `movb (%rsp), %r8b` | `44 8a 04 24` | 4 |
| `movb (%r12), %r8b` | `45 8a 04 24` | 4 |
| `movb %al, (%rsp)` | `88 04 24` | 3 |
| `movb %al, (%r12)` | `41 88 04 24` | 4 |
| `movb %ah, (%rsp)` | `88 24 24` | 3 |
| `movb %spl, (%rsp)` | `40 88 24 24` | 4 |
| `movb %spl, (%r12)` | `41 88 24 24` | 4 |
| `movb %r8b, (%rsp)` | `44 88 04 24` | 4 |
| `movb %r8b, (%r12)` | `45 88 04 24` | 4 |

`llvm-mc -disassemble` on `probes.txt` returns all fourteen byte strings as the
same register and base. The two `REX`-less `%rsp` rows are three bytes; every
`%r12` row and every prefixed `%rsp` row is four.

## 2. Where the fields sit

The shape is the `ADR-0058` frame with one more byte after `ModRM`:

| Row shape | Byte | Bits | Value | Fields |
|---|---|---|---|---|
| `REX`-less | opcode | `[0,8]` | `8a` / `88` | fixed per direction |
| | `ModRM` | `[8,8]` | `04` or `24` | `mod = 00`, `reg` = register at `[11,3]`, `r/m = 100` |
| | `SIB` | `[16,8]` | `24` | `scale = 00`, `index = 100` (no index), `base = 100` |
| `REX`-prefixed | `REX` | `[0,8]` | `40` / `41` / `44` / `45` | `REX.R` = register's fourth bit at `[2,1]`, `REX.B = 1` for `%r12` |
| | opcode | `[8,8]` | `8a` / `88` | fixed per direction |
| | `ModRM` | `[16,8]` | `04` or `24` | `mod = 00`, `reg` = register at `[19,3]`, `r/m = 100` |
| | `SIB` | `[24,8]` | `24` | the same three fields |

`SIB = 24` is `scale = 00`, `index = 100` and `base = 100`; with `mod = 00`
the base is `%rsp` when `REX.B = 0` and `%r12` when `REX.B = 1`. The `%rsp`
and `%r12` rows have identical opcode, `ModRM` and `SIB` bytes and differ only
in the `REX` byte or its absence.

### The seven base/register combinations

| Source | Bytes | Window | Register slot | Base |
|---|---|---|---|---|
| `movb (%rsp), %al` | `8a 04 24` | `%al`-`%bl` | `[11,3]`, excl `4`-`7` | fixed `%rsp` |
| `movb (%r12), %al` | `41 8a 04 24` | `%al`-`%bl` | `[19,3]`, excl `4`-`7` | fixed `%r12` |
| `movb (%rsp), %ah` | `8a 24 24` | `%ah`-`%bh` | `[11,3]`, excl `0`-`3` | fixed `%rsp` |
| `movb (%rsp), %spl` | `40 8a 24 24` | `%spl`-`%dil` | `[19,3]`, excl `0`-`3` | fixed `%rsp` |
| `movb (%r12), %spl` | `41 8a 24 24` | `%spl`-`%dil` | `[19,3]`, excl `0`-`3` | fixed `%r12` |
| `movb (%rsp), %r8b` | `44 8a 04 24` | `%r8b`-`%r15b` | `[2,1]`+`[19,3]`, excl `0`-`7` | fixed `%rsp` |
| `movb (%r12), %r8b` | `45 8a 04 24` | `%r8b`-`%r15b` | `[2,1]`+`[19,3]`, excl `0`-`7` | fixed `%r12` |

`movb (%rsp), %dil` is `40 8a 3c 24` and `movb (%r12), %r15b` is
`45 8a 3c 24`, so both ends of the prefixed windows are exercised. The
high-byte window has no `%r12` half; §4 measures the rejection.

## 3. The base is a row name, not an operand

The three shapes beside the plain-base row differ in length, so the plan must
name the one it wants (`INV-02`, `INV-04`):

| Source | Bytes | Length | Reading |
|---|---|---|---|
| `movb (%rax), %al` | `8a 00` | 2 | plain-base row (`0.31.0`) |
| `movb (%rsp), %al` | `8a 04 24` | 3 | this slice, `SIB = 24` |
| `movb 0(%rsp), %al` | `8a 44 24 00` | 4 | `disp8 = 0` row |
| `movb (%r12), %al` | `41 8a 04 24` | 4 | the same three bytes plus `REX.B` |

Because the base is in the template, the row has one slot. A plan that supplies
a `base` operand is a count mismatch (`E-OPERAND-002`, `N02ay`), and a plan
that supplies a `disp` operand is the same error (`N02az`) rather than a zero
the row would have to encode or discard.

## 4. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movb (%r13), %ah` | rejected | — | `REX.B` renames `%ah` |
| `movb (%r12), %ah` | rejected | — | the same rule |
| `movb (%rsp), %r16b` | `d5 40 8a 04 24` | 5 | APX `d5` prefix |
| `movb (%rbp), %al` | `8a 45 00` | 3 | `mod = 01`, `disp8 = 0` |
| `movb (%rax), %al` | `8a 00` | 2 | plain-base row |
| `movb 8(%rsp), %al` | `8a 44 24 08` | 4 | `disp8` row |
| `movl (%rsp), %eax` | `8b 04 24` | 3 | 32-bit analogue |
| `movq (%rsp), %rax` | `48 8b 04 24` | 4 | 64-bit analogue, `REX.W` |
| `movb (%rsp), %r15b` | `44 8a 3c 24` | 4 | extended window |
| `movb %r15b, (%rsp)` | `44 88 3c 24` | 4 | extended store |

`adjacent-encoding.txt` keeps the two rejection messages:
`can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`. That is
the `EC-36` rule: the `REX.B` byte that `%r13`/`%r12` needs is exactly the byte
that renames `%ah` to `%spl`, so the high-byte window cannot pair with either
extended-base row.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bq` | names `x86:mov/r8-rsp/legacy` against `0.31.0` | `E-FORM-001` |
| `N01br` | names `x86:mov/r12-r8-ext/legacy` against `0.31.0` | `E-FORM-001` |
| `N01bs` | names `x86:mov/r8h-r12/legacy`, the row `EC-36` forbids | `E-FORM-001` |
| `N02ay` | supplies a `base` operand to a fixed-base row | `E-OPERAND-002` (`expected 1, found 2`) |
| `N02az` | supplies a `disp` operand to a row with no displacement slot | `E-OPERAND-002` (`expected 1, found 2`) |
| `N14af` | carries register `16` on a three-bit row | `E-OPERAND-004` |
| `N14ag` | carries register `8` on a three-bit row | `E-OPERAND-004` |
| `N16an` | carries register `0` on the `REX = 40` row | `E-RANGE-004` |

`N01bs` is the one that shows the slice is complete rather than merely absent:
the name is syntactically a `0.32.0` row, but no such row can exist.

## 6. The fixture

`X86-P36-gpr8-mov-mem-sib-nodisp` is fourteen instructions and 52 bytes: one per
row, so both directions appear over `%rsp` in four windows and over `%r12` in
three.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movb (%rsp), %al` | `8a 04 24` | 3 |
| 2 | `movb (%r12), %cl` | `41 8a 0c 24` | 4 |
| 3 | `movb (%rsp), %ah` | `8a 24 24` | 3 |
| 4 | `movb (%rsp), %dil` | `40 8a 3c 24` | 4 |
| 5 | `movb (%r12), %sil` | `41 8a 34 24` | 4 |
| 6 | `movb (%rsp), %r8b` | `44 8a 04 24` | 4 |
| 7 | `movb (%r12), %r15b` | `45 8a 3c 24` | 4 |
| 8 | `movb %al, (%rsp)` | `88 04 24` | 3 |
| 9 | `movb %cl, (%r12)` | `41 88 0c 24` | 4 |
| 10 | `movb %bh, (%rsp)` | `88 3c 24` | 3 |
| 11 | `movb %dil, (%rsp)` | `40 88 3c 24` | 4 |
| 12 | `movb %sil, (%r12)` | `41 88 34 24` | 4 |
| 13 | `movb %r8b, (%rsp)` | `44 88 04 24` | 4 |
| 14 | `movb %r15b, (%r12)` | `45 88 3c 24` | 4 |

Lines 1-7 are the seven load rows, lines 8-14 the seven store rows. The
registers span each window's ends (`%al`, `%cl`, `%ah`, `%bh`, `%dil`, `%sil`,
`%r8b`, `%r15b`), and lines 7 and 14 are the two rows where `REX.R = 1` and
`REX.B = 1` share one byte (`45`).

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`98f60bd151d02f2c8f46db1c4bf74a4be7d9d0fd05a759bf86a81e33b750ce8c`
(`fixture.asm`) and its `output_sha256` is
`4b76ef10702c9a543f6cb7df2ff08e48aa56b1cb8bef7c981d23167a94868151`
(the 52-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
fourteen lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- `REX.X` at byte width: a `SIB` index with an extended register.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- `moffs` for the byte width: `a0`/`a2`, nine bytes.
- The APX register window (`d5 40 8a 04 24`): `%r16b`-`%r31b` are a different
  prefix and a different register field.
- The same shape under the 16-, 32- and 64-bit `mov` opcodes.
- A `SIB` base other than `100`, which would make the base an operand again
  (`0.8.0` already owns that shape for the register-owned rows).
