# EXP-0047 -- extended bases for the 8/16-bit `mov` memory rows

- Date: 2026-11-05
- Question: how do the word and byte memory rows of `0.17.0` reach `r8`–`r15`,
  where does `REX.B` sit when a `0x66` byte precedes the `REX`, and which
  window does each row family own?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.18.0.json`
  (`sha256:e1281b0c11d7e2bed9bd1ec7fa5404dadca2c82959376cbe3edfd9ff56b9e33d`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P22-mov-mem-base-ext.oracle.json`
- Source: `research/evidence/experiments/EXP-0047/P22.asm`
- Fixture source: `research/evidence/experiments/EXP-0047/fixture.asm`
- Decision: `ADR-0045`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. The mnemonic and the
register name select the operand size; no directive is needed.

| Source | Bytes | Length |
|---|---|---|
| `movw %ax, 8(%r8)` | `66 41 89 40 08` | 5 |
| `movw 8(%r8), %ax` | `66 41 8b 40 08` | 5 |
| `movw %ax, 128(%r8)` | `66 41 89 80 80 00 00 00` | 8 |
| `movw 128(%r8), %ax` | `66 41 8b 80 80 00 00 00` | 8 |
| `movw %ax, 127(%r8)` | `66 41 89 40 7f` | 5 |
| `movw %ax, -128(%r8)` | `66 41 89 40 80` | 5 |
| `movw %ax, -129(%r8)` | `66 41 89 80 7f ff ff ff` | 8 |
| `movw %ax, 8(%r15)` | `66 41 89 47 08` | 5 |
| `movw 8(%r15), %ax` | `66 41 8b 47 08` | 5 |
| `movb %al, 8(%r8)` | `41 88 40 08` | 4 |
| `movb 8(%r8), %al` | `41 8a 40 08` | 4 |
| `movb %cl, 8(%r8)` | `41 88 48 08` | 4 |
| `movb 8(%r8), %cl` | `41 8a 48 08` | 4 |
| `movb %al, 128(%r8)` | `41 88 80 80 00 00 00` | 7 |
| `movb 128(%r8), %al` | `41 8a 80 80 00 00 00` | 7 |
| `movb %al, -129(%r8)` | `41 88 80 7f ff ff ff` | 7 |
| `movb %al, 8(%r15)` | `41 88 47 08` | 4 |
| `movb %spl, 8(%r8)` | `41 88 60 08` | 4 |
| `movb 8(%r8), %spl` | `41 8a 60 08` | 4 |
| `movb %bpl, 8(%r8)` | `41 88 68 08` | 4 |
| `movb 8(%r8), %dil` | `41 8a 78 08` | 4 |
| `movb %spl, 128(%r8)` | `41 88 a0 80 00 00 00` | 7 |
| `movb 128(%r8), %spl` | `41 8a a0 80 00 00 00` | 7 |
| `movb %spl, -129(%r8)` | `41 88 a0 7f ff ff ff` | 7 |
| `movb %spl, 8(%r15)` | `41 88 67 08` | 4 |

`llvm-mc -disassemble` on `probes.txt` returns all thirty-one unique byte
strings as the same source line. The displacement rules do not change: `127` and
`-128` stay one byte (`40 7f`, `40 80`), and `128`/`-129` are four-byte
displacements.

Two lengths matter:

- The word and low-byte rows grow by exactly one byte
  (`66 89 40 08` → `66 41 89 40 08`, `88 40 08` → `41 88 40 08`).
- The `40`-prefixed rows do not grow: `40 88 60 08` (`%spl`, base `%rax`) and
  `41 88 60 08` (`%spl`, base `%r8`) are both four bytes, one bit apart.

## 2. Where the fields sit

| Row family | Template | `ModRM.reg` | base (`ModRM.rm`) | `REX.B` | `disp` |
|---|---|---|---|---|---|
| word `66 41` | `66 REX op ModRM disp` | `[27,3]` | `[24,3]` | `[8,1]` | `[32,8]`/`[32,32]` |
| byte `41` | `REX op ModRM disp` | `[19,3]` | `[16,3]` | `[0,1]` | `[24,8]`/`[24,32]` |
| `40` (widened) | `REX op ModRM disp` | `[19,3]` | `[16,3]` | `[0,1]` | `[24,8]`/`[24,32]` |

`llvm-mc -disassemble` reads `66 41 89 40 08` as `movw %ax, 8(%r8)` and
`66 41 89 47 08` as `movw %ax, 8(%r15)`, so the base's fourth bit is shared with
the `0x66`-prefixed byte, not with `ModRM`. The three byte rows put the same bit
at template bit 0.

## 3. The byte register split is the other half of the window

A `REX` byte does not re-label numbers 0–3 (`al`/`cl`/`dl`/`bl` stay), only 4–7
(`spl`/`bpl`/`sil`/`dil`). That divides the byte rows into two families, and
`0.18.0` gives each half one base window:

| Register numbers | Base `0`–`7` | Base `8`–`15` |
|---|---|---|
| `0`–`3` (`al`–`bl`) | REX-less `88`/`8a` row | new `41 88`/`41 8a` `-base-ext` row |
| `4`–`7` (`spl`–`dil`) | `40 88`/`40 8a` row | the same row widened in place |
| `4`–`7` (`ah`–`bh`) | `88`/`8a` high-byte row | no encoding |

`41 88 60 08` reads as `movb %spl, 8(%r8)` and is exactly the widened `40` row;
`41 88 40 08` reads as `movb %al, 8(%r8)` and is the new `-base-ext` row. The
high-byte cell is empty: `movb %ah, 8(%r8)` is rejected with
`can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`.

## 4. What the slice defers

- `%rsp`/`%r12` still spend a `SIB` byte:

| Source | Bytes |
|---|---|
| `movw %ax, 8(%rsp)` | `66 89 44 24 08` |
| `movw %ax, 8(%r12)` | `66 41 89 44 24 08` |
| `movb %al, 8(%rsp)` | `88 44 24 08` |
| `movb %al, 8(%r12)` | `41 88 44 24 08` |
| `movb %spl, 8(%rsp)` | `40 88 64 24 08` |
| `movb %spl, 8(%r12)` | `41 88 64 24 08` |

- `mod = 00`: no GPR memory row has it at any width.
- Four-bit registers: `44 88 40 08` is `movb %r8b, 8(%rax)` and
  `66 44 89 40 08` is `movw %r8w, 8(%rax)`, both needing `REX.R`.

## 5. The definition rows

`0.18.0` appends the eight `-base-ext` rows of `ADR-0045` (word load/store ×
`disp8`/`disp32`, then REX-less low-byte load/store × `disp8`/`disp32`) and
widens the four `40` rows in place. The word rows place the base at `[8,1]` +
`[24,3]`; the byte rows at `[0,1]` + `[16,3]`. Every extension row excludes
`0`–`7` and `12`; the widened rows exclude `4` and `12`, so a low base keeps
its old bytes.

## 6. The fixture

`X86-P22-mov-mem-base-ext` is eighteen instructions and 100 bytes. It covers
all twelve rows, the `disp8` ends `127`/`-128`, the `disp32` promotions
`128`/`-129`, bases `r8`–`r11`, `r13`–`r15`, a low base on a widened `40` row
(`40 88 60 08`), and both directions of each family. `expected.bin` comes from
`llvm-mc` + `llvm-objcopy`, never from our materializer; the oracle's
`input_sha256` is `fixture.asm` (`3473cfec...`) and its `output_sha256` is the
100-byte `.text` (`df40d588...`).

## 7. Negative coverage

- `N01ao` names `x86:mov/r16-base-ext-disp8/legacy` against `0.17.0`:
  `E-FORM-001`, the version boundary.
- `N16v` passes base `0` to an extension row: `E-RANGE-004`, the disjoint
  windows.
- `N16w` passes `%r12` to a word extension row: `E-RANGE-004`, the `SIB` byte.
- `N16x` passes `%r12` to a widened `40` row: `E-RANGE-004`, the same byte.
- `N14u` passes base `16` to the four-bit field: `E-OPERAND-004`.
- `N02t` passes `x86.gpr8h` number `4` to a byte extension row:
  `E-OPERAND-001` on `kind` and `target_type`, plus `E-RANGE-004` because the
  row's set is `0`–`3`.
