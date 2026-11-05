# EXP-0046 -- `mov` memory rows at 8 and 16 bits

- Date: 2026-11-05
- Question: does a memory operand at 8 or 16 bits reuse the 0.4.0 prefix and
  byte-register facts, where do `0x66` and `REX` sit relative to the `ModRM`
  byte, and which windows does the slice still defer?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.17.0.json`
  (`sha256:eb8370255811a2364550bf98ae106f8f972c9a3e54e94d1aeb98ddde921fbcd0`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P21-mov-mem-8-16.oracle.json`
- Source: `research/evidence/experiments/EXP-0046/P21.asm`
- Decision: `ADR-0044`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. The mnemonic and the
register name select the operand size; no directive is needed.

| Source | Bytes | Length |
|---|---|---|
| `movw %ax, 8(%rax)` | `66 89 40 08` | 4 |
| `movw 8(%rax), %ax` | `66 8b 40 08` | 4 |
| `movw %ax, 128(%rax)` | `66 89 80 80 00 00 00` | 7 |
| `movw 128(%rax), %ax` | `66 8b 80 80 00 00 00` | 7 |
| `movw %ax, 127(%rax)` | `66 89 40 7f` | 4 |
| `movw %ax, -128(%rax)` | `66 89 40 80` | 4 |
| `movw %ax, -129(%rax)` | `66 89 80 7f ff ff ff` | 7 |
| `movb %al, 8(%rax)` | `88 40 08` | 3 |
| `movb 8(%rax), %al` | `8a 40 08` | 3 |
| `movb %cl, 8(%rax)` | `88 48 08` | 3 |
| `movb %cl, 128(%rax)` | `88 88 80 00 00 00` | 6 |
| `movb -129(%rax), %cl` | `8a 88 7f ff ff ff` | 6 |
| `movb %ah, 8(%rax)` | `88 60 08` | 3 |
| `movb %ch, 8(%rax)` | `88 68 08` | 3 |
| `movb 8(%rax), %ah` | `8a 60 08` | 3 |
| `movb %ah, 127(%rax)` | `88 60 7f` | 3 |
| `movb %ah, -128(%rax)` | `88 60 80` | 3 |
| `movb %ch, 128(%rax)` | `88 a8 80 00 00 00` | 6 |
| `movb -129(%rax), %ah` | `8a a0 7f ff ff ff` | 6 |
| `movb %spl, 8(%rax)` | `40 88 60 08` | 4 |
| `movb %bpl, 8(%rax)` | `40 88 68 08` | 4 |
| `movb 8(%rax), %spl` | `40 8a 60 08` | 4 |
| `movb 8(%rax), %dil` | `40 8a 78 08` | 4 |
| `movb %spl, 128(%rax)` | `40 88 a0 80 00 00 00` | 7 |
| `movb %spl, -129(%rax)` | `40 88 a0 7f ff ff ff` | 7 |
| `movb 128(%rax), %bpl` | `40 8a a8 80 00 00 00` | 7 |

`llvm-mc -disassemble` on `probes.txt` returns each of the thirty-four unique
byte strings as the same source line. The displacement rows are plain signed
bytes: `7f` is `127`, `80` is `-128`, and `128`/`-129` are four-byte
displacements, exactly as at 64-bit width (`EC-02`).

## 2. Where the fields sit

The prefix order is `0x66` first, then `REX`, then the opcode, and the `ModRM`
byte moves with the prefixes:

| Row family | Template | `ModRM.reg` | base (`ModRM.rm`) | `disp` |
|---|---|---|---|---|
| `66 89`/`66 8b` | `66 op ModRM disp` | `[19,3]` | `[16,3]` | `[24,8]` |
| `88`/`8a` low, high | `op ModRM disp` | `[11,3]` | `[8,3]` | `[16,8]` |
| `40 88`/`40 8a` | `REX op ModRM disp` | `[19,3]` | `[16,3]` | `[24,8]` |

`llvm-mc -disassemble` prints `66 41 89 40 08` as `movw %ax, 8(%r8)`, so the
`66` byte is not a width operand the plan can carry, and the one byte of base
extension is the difference between `66 89 40 08` and `66 41 89 40 08`.

## 3. The byte register sets stay disjoint

| Set | Row | Example | Numbers |
|---|---|---|---|
| low byte, no REX | `mov/base-disp8-r8` | `88 40 08` = `movb %al, ...` | `0`-`3`, excludes `4`-`7` |
| high byte, no REX | `mov/base-disp8-r8h` | `88 60 08` = `movb %ah, ...` | `4`-`7`, excludes `0`-`3` |
| low byte, REX | `mov/base-disp8-r8-rex` | `40 88 60 08` = `movb %spl, ...` | `4`-`7`, excludes `0`-`3` |

`40 88 60 08` and `88 60 08` have the same opcode and the same `ModRM` byte and
name different registers: the REX byte is template `40` on the third row and
its four bits are all zero, because the prefix's presence is what re-labels
numbers 4-7. The two slots that hold a register number are therefore not
interchangeable, and the definition keeps the `ADR-0029` exclusions verbatim.

## 4. The base window is unchanged

`mod = 01`/`10` with `r/m = 100` still spends the byte on a `SIB`, so `%rsp`
stays out of the new rows:

| Source | Bytes | Reading |
|---|---|---|
| `movw %ax, 8(%rsp)` | `66 89 44 24 08` | `r/m = 100`, SIB `24` |
| `movw %ax, 8(%r12)` | `66 41 89 44 24 08` | SIB plus `REX.B` |
| `movb %spl, 8(%rsp)` | `40 88 64 24 08` | SIB inside a REX row |

A base in `r8`-`r15` needs `REX.B` and one more byte, so `%r8` is not in the
three-bit window either:

| Source | Bytes | Deferred row |
|---|---|---|
| `movw %ax, 8(%r8)` | `66 41 89 40 08` | `-base-ext` word row |
| `movw %ax, 8(%r15)` | `66 41 89 47 08` | `-base-ext` word row |
| `movb %al, 8(%r8)` | `41 88 40 08` | `-base-ext` byte row |
| `movb %spl, 8(%r8)` | `41 88 60 08` | `-base-ext` byte row |

`movb %ah, 8(%r8)` is rejected: `can't encode 'ah' in an instruction requiring
EVEX/REX2/REX prefix`. The base extension would re-label the high-byte register
the plan named, so the pair is unencodable rather than one form with a choice.

## 5. What the slice defers

Four windows are measured here and left out of `0.17.0`:

- `-base-ext` rows: `66 41 89 40 08`, `41 88 40 08`. The extension costs a
  byte, so it is a separate form, as in `0.7.0` and `0.10.0`.
- `%rsp`/`%r12` SIB rows: `66 89 44 24 08`, `66 41 89 44 24 08`.
- `mod = 00`: `66 89 00` is `movw %ax, (%rax)` and `88 00` is
  `movb %al, (%rax)`; no GPR row has `mod = 00` at any width yet.
- four-bit registers: `66 44 89 40 08` is `movw %r8w, 8(%rax)` and
  `44 88 78 08` is `movb %r15b, 8(%rax)`, both needing `REX.R`.

## 6. The definition rows

`0.17.0` appends the sixteen rows enumerated in `ADR-0044`: four word rows,
four low-byte rows, four high-byte rows and four REX low-byte rows, each set
ordered load `disp8`, load `disp32`, store `disp8`, store `disp32`. The base is
`x86.gpr64`/`rm64` at `[16,3]` (word, REX byte) or `[8,3]` (REX-less byte),
excluding `4`. There is no new `EC` row: `EC-02`, `EC-27`, `EC-28`, `EC-36`
and `EC-38` already state every field.

## 7. The fixture

`X86-P21-mov-mem-8-16` is twenty-six instructions and 122 bytes. It covers
every row, both `disp8` ends (`127`, `-128`), the `disp32` promotions
(`128`, `-129`), `al`/`cl`, `ah`/`ch`, `spl`/`bpl`/`dil`, and both directions
at every width. `expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never
from our materializer; the oracle's `input_sha256` is `P21.asm`
(`5e6d3960...`) and its `output_sha256` is the 122-byte `.text`
(`5a57e901...`).

## 8. Negative coverage

- `N01an` names `x86:mov/base-disp8-r16/legacy` against `0.16.0`:
  `E-FORM-001`, the version boundary.
- `N02r` passes an `x86.gpr32` operand to the word row: `E-OPERAND-001` on
  `kind` and `target_type`.
- `N02s` passes `x86.gpr8h` to the `-rex` row: `E-OPERAND-001`, because a REX
  prefix re-labels numbers 4-7.
- `N16t` passes number `4` to the REX-less low-byte row: `E-RANGE-004`, the
  high-byte exclusion.
- `N16u` passes `%rsp` as the base: `E-RANGE-004`, because the register number
  would spend a `SIB` byte the row does not have.
- `N03g` passes content `128` to a `disp8` slot: `E-RANGE-001`, one past the
  signed byte.
- `N14t` passes base `8` to a three-bit base slot: `E-OPERAND-004`, the
  deferred `-base-ext` window failing loudly instead of truncating.
