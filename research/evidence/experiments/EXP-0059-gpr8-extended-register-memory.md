# EXP-0059 -- the extended byte register in the GPR `mov` memory rows

- Date: 2026-11-06
- Question: how do the byte-width GPR `mov` memory rows reach `%r8b`-`%r15b`,
  which `REX` bits carry the register and the base, and does either one change
  the displacement?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.30.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P34-gpr8-ext-mem.oracle.json`
- Source: `research/evidence/experiments/EXP-0059/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0059/fixture.asm`
- Decision: `ADR-0057`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movb 8(%rax), %r8b` | `44 8a 40 08` | 4 |
| `movb 200(%rax), %r8b` | `44 8a 80 c8 00 00 00` | 7 |
| `movb 8(%rsp), %r8b` | `44 8a 44 24 08` | 5 |
| `movb 200(%rsp), %r8b` | `44 8a 84 24 c8 00 00 00` | 8 |
| `movb 8(%r8), %r8b` | `45 8a 40 08` | 4 |
| `movb 200(%r8), %r8b` | `45 8a 80 c8 00 00 00` | 7 |
| `movb 8(%r12), %r8b` | `45 8a 44 24 08` | 5 |
| `movb 200(%r12), %r8b` | `45 8a 84 24 c8 00 00 00` | 8 |
| `movb %r8b, 8(%rax)` | `44 88 40 08` | 4 |
| `movb %r8b, 200(%rax)` | `44 88 80 c8 00 00 00` | 7 |
| `movb %r8b, 8(%rsp)` | `44 88 44 24 08` | 5 |
| `movb %r8b, 200(%rsp)` | `44 88 84 24 c8 00 00 00` | 8 |
| `movb %r8b, 8(%r8)` | `45 88 40 08` | 4 |
| `movb %r8b, 200(%r8)` | `45 88 80 c8 00 00 00` | 7 |
| `movb %r8b, 8(%r12)` | `45 88 44 24 08` | 5 |
| `movb %r8b, 200(%r12)` | `45 88 84 24 c8 00 00 00` | 8 |
| `movb 8(%rbp), %r15b` | `44 8a 7d 08` | 4 |
| `movb 8(%r13), %r15b` | `45 8a 7d 08` | 4 |
| `movb -1(%rax), %r8b` | `44 8a 40 ff` | 4 |
| `movb 127(%r8), %r15b` | `45 8a 78 7f` | 4 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty byte strings as the
same register, base and displacement.

## 2. Where the fields sit

Every row starts with a `REX` byte, so the frame is one byte later than the
`REX`-less byte rows:

| Byte | Bits | Value | Fields |
|---|---|---|---|
| `REX` | `[0,8]` | `44` or `45` | `REX.R` = register's fourth bit at `[2,1]`, `REX.B` = base's at `[0,1]` |
| opcode | `[8,8]` | `8a` (load) or `88` (store) | fixed per direction |
| `ModRM` | `[16,8]` | `40`-`7f` / `80`-`bf` | `mod = 01` or `10`, `reg` = register at `[19,3]`, `r/m` = base at `[16,3]` |
| `SIB` | `[24,8]` | `24` | scale `00`, index `100` ("no index"), base `100` |
| `disp8` | `[24,8]` or `[32,8]` | one byte | signed displacement |
| `disp32` | `[24,32]` or `[32,32]` | four bytes | signed displacement |

`REX.R` is bit 2 and `REX.B` bit 0 of the first byte, so the register slot is
`[19,3]` plus `[2,1]` and the base slot is `[16,3]` plus `[0,1]`. `REX = 44`
is `REX.R = 1` alone and `REX = 45` sets both.

### One prefix byte, two extension bits

| Source | `REX` | `REX.R` | `REX.B` | Reading |
|---|---|---|---|---|
| `movb 8(%rax), %r8b` | `44` | 1 | 0 | extended register, low base |
| `movb 8(%r8), %r8b` | `45` | 1 | 1 | extended register, extended base |
| `movb 8(%rax), %spl` | `40` | 0 | 0 | relabelled 4-7 register, low base |
| `movb 8(%r12), %spl` | `41` | 0 | 1 | relabelled 4-7 register, `%r12` base |

The four rows are the four combinations the byte width allows. There is no
`42`/`43` row: `REX.X` is the `SIB` index bit and no byte row carries an index.

## 3. The three base windows

The displacement is the same disp8/disp32 pair the family already uses; the
base is what selects the row.

| Base | `ModRM` | `SIB` | Extra byte | Length |
|---|---|---|---|---|
| `%rax`-`%rdi` except `%rsp` | `mod = 01` / `10`, `r/m` = base | none | disp8 / disp32 | 4 / 7 |
| `%r8`-`%r15` except `%r12` | same, `REX.B = 1` | none | disp8 / disp32 | 4 / 7 |
| `%rsp` / `%r12` | `mod = 01` / `10`, `r/m = 100` | `24` | disp8 / disp32 | 5 / 8 |

`%rbp` and `%r13` need no extra row: `mod = 01` is the family's floor, so
`movb 8(%rbp), %r15b` is `44 8a 7d 08` and `movb 8(%r13), %r15b` is
`45 8a 7d 08`. The `SIB` byte `24` is `scale = 00`, `index = 100` ("no
index") and `base = 100`, so `REX.B` alone is what reads it as `%rsp` or
`%r12`; `45 8a 44 24 08` is `%r12` and `44 8a 44 24 08` is `%rsp`.

## 4. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movb (%rax), %r8b` | `44 8a 00` | 3 | `mod = 00`, no displacement — no byte row carries it |
| `movb (%r8), %r8b` | `45 8a 00` | 3 | the same shape with `REX.B` |
| `movb 8(%rax), %r16b` | `d5 40 8a 40 08` | 5 | APX `d5` prefix, a different template |
| `movb 8(%rax), %ah` | `8a 60 08` | 4 | high-byte register, no `REX` byte |
| `movb 8(%rax), %spl` | `40 8a 60 08` | 4 | relabelled 4-7 register |
| `movb 8(%r12), %spl` | `41 8a 64 24 08` | 5 | `REX.B` with the relabelled register |
| `movl 8(%rax), %r8d` | `44 8b 40 08` | 4 | 32-bit analogue, same `REX` |
| `movq 8(%rax), %r8` | `4c 8b 40 08` | 4 | 64-bit analogue, `REX.W + REX.R` |
| `movw 8(%rax), %r8w` | `66 44 8b 40 08` | 5 | 16-bit analogue behind `66` |
| `movb 8(%rax), %al` | `8a 40 08` | 4 | the low window, no `REX` byte |
| `movb 8(%r8), %al` | `41 8a 40 08` | 4 | plain register with `REX.B` |

`movb 8(%r8), %ah` is rejected by `llvm-mc` with `can't encode 'ah' in an
instruction requiring EVEX/REX2/REX prefix`, and `adjacent-encoding.txt` keeps
the message.

The `mod = 00` shape is worth naming: `44 8a 00` is a third legal encoding of
`movb (%rax), %r8b`, three bytes rather than four, and no byte-width row
carries it at any register window. It is deferred with the rest of the family,
not introduced here.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bm` | names `x86:mov/r8-ext-base-disp8/legacy` against `0.29.0` | `E-FORM-001` |
| `N01bn` | names `x86:mov/r12-disp32-r8-ext/legacy` against `0.29.0` | `E-FORM-001` |
| `N02at` | carries `x86.gpr8h`/`r8h` on an extended row | `E-OPERAND-001` on `kind` and `target_type` |
| `N02au` | carries the displacement as `disp8` on a `disp32` row | `E-OPERAND-001` on `target_type` |
| `N02av` | supplies a `base` operand to a `SIB` row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N03q` | carries `disp32` content `2147483648` | `E-RANGE-001` |
| `N14ad` | carries register `16` | `E-OPERAND-004` on `payload/reg` |
| `N16ag` | carries register `0` on an extended row | `E-RANGE-004` on `payload/reg` |
| `N16ah` | carries `%rsp` as the base of a plain-base row | `E-RANGE-004` on the base's `payload/reg` |
| `N16ai` | carries `%r12` as the base of a plain-base row | `E-RANGE-004` on the base's `payload/reg` |

`N16ag` is the case that shows why the extended rows cannot be folded into the
`%spl`-`%dil` rows: the template's `REX.R = 1` is the slot's top bit, so a
value below `8` would clear it and emit `40`/`41` — the other window's prefix.

## 6. The fixture

`X86-P34-gpr8-ext-mem` is twelve instructions and 74 bytes: one per row, so
both directions appear in all three base windows at both displacement widths.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movb 8(%rax), %r8b` | `44 8a 40 08` | 4 |
| 2 | `movb 200(%r8), %r15b` | `45 8a b8 c8 00 00 00` | 7 |
| 3 | `movb 8(%rsp), %r9b` | `44 8a 4c 24 08` | 5 |
| 4 | `movb 200(%rsp), %r14b` | `44 8a b4 24 c8 00 00 00` | 8 |
| 5 | `movb 8(%r12), %r10b` | `45 8a 54 24 08` | 5 |
| 6 | `movb 200(%r12), %r11b` | `45 8a 9c 24 c8 00 00 00` | 8 |
| 7 | `movb %r8b, 8(%rax)` | `44 88 40 08` | 4 |
| 8 | `movb %r15b, 200(%r8)` | `45 88 b8 c8 00 00 00` | 7 |
| 9 | `movb %r9b, 8(%rsp)` | `44 88 4c 24 08` | 5 |
| 10 | `movb %r14b, 200(%rsp)` | `44 88 b4 24 c8 00 00 00` | 8 |
| 11 | `movb %r10b, 8(%r12)` | `45 88 54 24 08` | 5 |
| 12 | `movb %r11b, 200(%r12)` | `45 88 9c 24 c8 00 00 00` | 8 |

The fixture pins all twelve rows, the four-bit register field at both ends
(`%r8b` / `%r9b` / `%r10b` / `%r11b` / `%r14b` / `%r15b`), `REX = 45` with a
plain extended base (line 2) as well as with `%r12` (lines 5, 6), and both
displacement widths in every window.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`fbef6d94f7271cef25e51e514c493151434b0bcbdd0cb7cb61c17f7d811ac399`
(`fixture.asm`) and its `output_sha256` is
`9d10760a4199b0470e25b3f7f0d506f0580b4f4a10adaec7f4817d9479c16528`
(the 74-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
twelve lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

The first draft of the fixture used `movb 8(%r8), %r10b` for the `%r12` row.
`%r8` is a *plain* base with `REX.B = 1`, not the `SIB` base, so the line
measured four bytes (`45 8a 50 08`) instead of five and the oracle came out at
72. `fixture.asm` now gives the plain-base `disp32` line the `%r8` base and
keeps `%r12` for the two `SIB` lines.

## 7. What the slice defers

- The `mod = 00` no-displacement byte rows (`44 8a 00`), absent for every
  register window.
- `REX.X` at byte width: a `SIB` index with an extended register.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- `moffs` for the byte width: `a0`/`a2`, nine bytes.
- The APX register window (`d5 40 …` / `d5 44 …`): `%r16b`-`%r31b` are a
  different prefix and a different register field.
- The absolute address under the other x86 opcode families.
