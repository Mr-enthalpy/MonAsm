# ADR-0044: The word and byte memory rows reuse the prefix and register-set facts

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P21` (8-bit and 16-bit `mov` memory rows)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0029` §Decision 7 and §Review triggers (the memory families it
  deferred)

## Context

`ADR-0029` made the operand-size prefix and the high-byte register set form
facts, but only for register-to-register operands: `movw %bx, %ax` and
`movb %ah, %ch` have rows, while every `mov` memory row is 64-bit. Its review
trigger names this slice: a memory operand at 8 or 16 bits, where `mod`,
`%rsp` and the byte-register sets meet. `ADR-0028` and `ADR-0035` settled the
addressing side; this ADR asks only whether the two 0.4.0 facts survive a memory
operand, or whether a memory operand needs a new `EC` row.

`EXP-0046` measures the shapes with `llvm-mc` 23.1.2 on 2026-11-05; every byte
string below was also fed to `llvm-mc -disassemble` and came back as the same
source line. Five measurements decide the row list:

1. **`0x66` is still template byte 0, ahead of any REX byte.**
   `movw %ax, 8(%rax)` is `66 89 40 08`; `movw %ax, 8(%r8)` is
   `66 41 89 40 08`, so the prefix order is `66` then `REX`, and the `ModRM`
   byte sits at bit 16 rather than bit 8. `66 41 89 40 08` disassembles as
   `movw %ax, 8(%r8)`, never as a byte or 32-bit form.
2. **The byte register set is still three rows.** `movb %al, 8(%rax)` is
   `88 40 08` (`reg = 000`), `movb %ah, 8(%rax)` is `88 60 08` (`reg = 100`)
   and `movb %spl, 8(%rax)` is `40 88 60 08` — the same `ModRM` byte with one
   prefix in front. The numbers 0–3, 4–7 without REX and 4–7 with REX are three
   disjoint sets, exactly as in the register-direct rows (`EC-36`).
3. **The REX byte of the `spl`–`dil` row carries no operand.** It is `40`:
   `spl`/`bpl`/`sil`/`dil` are the numbers 4–7 and need the prefix's presence,
   not any of its bits. The row's template fixes the byte; the base stays in
   the three low `ModRM.rm` bits.
4. **The displacement rules do not change.** `127` and `-128` are `7f`/`80` at
   every width (`movb %ah, 127(%rax)` is `88 60 7f`), and `128`/`-129` are
   `disp32` rows (`movb %al, 128(%rax)` is `88 80 80 00 00 00`). `disp8` is a
   plain signed byte at 8 and 16 bits (`EC-02`).
5. **The base window is the one the family already has.** `mod = 01` with
   `r/m = 100` still spends a `SIB` byte (`movw %ax, 8(%rsp)` is
   `66 89 44 24 08`), and a base in `r8`–`r15` still needs `REX.B`, which a
   no-REX row cannot pay for without naming a redundant prefix (`EC-28`):
   `movw %ax, 8(%r8)` is `66 41 89 40 08`, one byte longer than the same
   instruction on `%rax`.

`llvm-mc` still rejects the illegal combination instead of repairing it:
`movb %ah, 8(%r8)` reports `can't encode 'ah' in an instruction requiring
EVEX/REX2/REX prefix`, because the base extension would re-label the high-byte
register that the plan named.

## Decision

**`0.17.0` adds sixteen `mov` memory rows: four at 16-bit width and twelve at
8-bit width (three register sets × load/store × `disp8`/`disp32`). Every base
is the three-bit window `0`–`7` minus `%rsp`, and no row adds an `EC` row or
revises one.**

The rows, in the order they are appended:

| # | `form_id` | Template | Slots |
|---|---|---|---|
| 1 | `x86:mov/r16-base-disp8/legacy` | `668b4000` | dest `gpr16`/`r16` `[19,3]`; base `[16,3]` excl `4`; `disp8` `[24,8]` |
| 2 | `x86:mov/r16-base-disp32/legacy` | `668b8000000000` | dest; base; `disp32` `[24,32]` |
| 3 | `x86:mov/base-disp8-r16/legacy` | `66894000` | src `gpr16`/`r16`; base; `disp8` |
| 4 | `x86:mov/base-disp32-r16/legacy` | `66898000000000` | src; base; `disp32` |
| 5 | `x86:mov/r8-base-disp8/legacy` | `8a4000` | dest `gpr8`/`r8` `[11,3]` excl `4–7`; base `[8,3]` excl `4`; `disp8` `[16,8]` |
| 6 | `x86:mov/r8-base-disp32/legacy` | `8a8000000000` | same, `disp32` `[16,32]` |
| 7 | `x86:mov/base-disp8-r8/legacy` | `884000` | src `gpr8`/`r8`; base; `disp8` |
| 8 | `x86:mov/base-disp32-r8/legacy` | `888000000000` | src; base; `disp32` |
| 9 | `x86:mov/r8h-base-disp8/legacy` | `8a6000` | dest `gpr8h`/`r8h` `[11,3]` excl `0–3`; base; `disp8` |
| 10 | `x86:mov/r8h-base-disp32/legacy` | `8aa000000000` | dest; base; `disp32` |
| 11 | `x86:mov/base-disp8-r8h/legacy` | `886000` | src `gpr8h`/`r8h`; base; `disp8` |
| 12 | `x86:mov/base-disp32-r8h/legacy` | `88a000000000` | src; base; `disp32` |
| 13 | `x86:mov/r8-base-disp8-rex/legacy` | `408a6000` | dest `gpr8`/`r8` `[19,3]` excl `0–3`; base `[16,3]` excl `4`; `disp8` `[24,8]` |
| 14 | `x86:mov/r8-base-disp32-rex/legacy` | `408aa000000000` | same, `disp32` `[24,32]` |
| 15 | `x86:mov/base-disp8-r8-rex/legacy` | `40886000` | src `gpr8`/`r8`; base; `disp8` |
| 16 | `x86:mov/base-disp32-r8-rex/legacy` | `4088a000000000` | src; base; `disp32` |

Four properties follow, and each is a restatement of a 0.4.0 or 0.3.0 fact
rather than a new one:

- **The width is still the prefix and the kind.** A row is word or byte by its
  template and by the kind of its register slot; an `x86.gpr32` operand on a
  word row is `E-OPERAND-001`, and no operand value selects a width.
- **The byte sets are still disjoint.** The REX-less rows exclude 4–7 and the
  `-rex` rows exclude 0–3, so each byte register has exactly one row
  (`EC-28`). `check_definition.py` enforces the same two rules it already
  enforced for the register-direct rows.
- **The `-rex` byte rows keep a three-bit base.** The REX byte is required by
  the register set, not by the base, so placing `REX.B` there would make the
  low window pay for a byte it does not need. The base window stays `0`–`7`
  minus `%rsp`, the same window as the 0.3.0 rows.
- **The addressing fields move with the prefix.** In a `66` row the `ModRM`
  byte is at bit 16 and the displacement at 24; in a REX-less byte row they are
  at 8 and 16; in a `-rex` row they are back at 16 and 24. Nothing is derived
  from a register number or a length.

## Consequences

- `0.17.0` is a 119-form document with digest
  `sha256:eb8370255811a2364550bf98ae106f8f972c9a3e54e94d1aeb98ddde921fbcd0`.
- Its positive fixture `X86-P21-mov-mem-8-16` is twenty-six instructions and
  122 bytes: every row, both `disp8` ends, the `disp32` promotions at
  `128`/`-129`, the three byte register sets, and the word rows at both
  directions.
- Seven negatives pin the new rows: `N01an` (the `0.16.0` boundary), `N02r` (a
  32-bit operand on a word row), `N02s` (`ah` on the `-rex` row), `N16t`
  (number 4 on the REX-less byte row), `N16u` (`%rsp` base), `N03g` (content
  `128`) and `N14t` (base `r8`, outside the three-bit window).
- No schema or Rust change. The loader's `ADR-0029` checks already cover the
  new templates.
- The next slices on this axis are the windows this one defers: the
  `-base-ext` rows (`66 41 89 40 08`, `41 88 40 08`), the `%rsp`/`%r12` SIB
  rows (`66 89 44 24 08`), `mod = 00` for the GPR rows, and the 4-bit byte and
  word registers (`44 88 40 08` is `movb %r8b, 8(%rax)`).

## Alternatives rejected

- **One `mov` memory row per direction with a width operand.** The width is
  the prefix byte the row would have to choose from an operand value
  (`INV-02`), and the register kinds already differ.
- **Start the new rows at a four-bit base.** A no-REX row has no byte to put
  `REX.B` in; adding one always would emit `40`/`41` for `%rax`, the redundant
  prefix `EC-28` forbids. The extension must be its own form, as it was in
  `0.7.0` and `0.10.0`.
- **One byte row for the whole `0`–`7` range with a `rex` modifier.** The
  modifier would be the plan's prefix choice, and `88 60 08` versus
  `40 88 60 08` name different registers. `ADR-0029` rejected the same shape.
- **Let the REX byte of the `spl`–`dil` rows also carry the base extension.**
  It is legal, but it would give `%r8` a row while `%rax` on the same register
  set has a shorter one, and the same base would be encodable with `spl` but
  not with `al`. One base window per register set is the smaller statement.
- **Defer 8-bit and ship only 16-bit.** The `0x66` rows are the easy half; the
  question the review trigger names is how the byte register sets meet a
  `ModRM` byte that also holds a memory reference, and that is the 8-bit half.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 89 40 08`, `66 8b 40 08`, `66 41 89 40 08`, `66 45 8b 40 08` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0046` §1–§2 | high |
| `88`/`8a` at `reg = 0`, `4` and `4`+`40` prefix; `reg = 5`, `7` decode as `cl`, `ch`, `bpl`, `dil` | `llvm-mc -disassemble`, `EXP-0046` §2 | high |
| `disp8` content `127`/`-128` and the `disp32` promotions `128`/`-129` at all three widths | `llvm-mc -show-encoding`, `EXP-0046` §3 | high |
| `%rsp` base adds a `SIB` byte at word width (`66 89 44 24 08`) | `llvm-mc -show-encoding`, `EXP-0046` §4 | high |
| `movb %ah, 8(%r8)` is rejected with the REX/high-byte message | `llvm-mc` error text, `EXP-0046` §5 | high |
| The `0x66` prefix precedes the REX byte and the `ModRM` byte moves with it | the byte strings above; no operand value writes either byte | high |

## Review triggers

- The extended windows are attempted: `66 41 89 40 08` and `41 88 40 08` need
  `-base-ext` rows whose template fixes `REX.B = 1`, and the `%r12` exclusions
  of `ADR-0034` apply.
- `r8b`–`r15b` or `r8w`–`r15w` are attempted: the register slot needs a fourth
  bit (`REX.R`) and the row's `field_bits` becomes four.
- `mod = 00` is attempted for a GPR row: `66 89 00` is `movw %ax, (%rax)` and
  `88 00` is `movb %al, (%rax)`; the `%rbp`/`%r13` collision of `ADR-0039`
  applies.
- The immediate-to-memory forms (`C6`/`C7`) are attempted: they are a different
  direction family (`EC-04`, `EC-27`), not a width of these rows.
- The `0x67` address-size prefix is attempted: that is `EC-08` and a different
  row family.
