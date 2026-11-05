# ADR-0057: the extended byte register reaches the byte `mov` memory rows

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P34` (the r8–r15 window under the byte-width `mov` memory rows,
  where `REX.R` and `REX.B` share one prefix byte)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0056` §Review triggers (its first item, the `REX.B` combination
  at byte width); `EC-06` (`REX.R` and `REX.B` in one byte);
  `EC-38` (the register window as a `form_id` component)

## Context

`ADR-0056` appended the eight-bit absolute-address rows and left one byte-width
gap named first in its review triggers: the extended register. The byte memory
family today reaches `%al`–`%bl` (no `REX`), `%ah`–`%bh` (no `REX`, its own
kind), and `%spl`–`%dil` (`REX = 40`/`41`), but every byte row stops at register
`7`. `%r8b`–`%r15b` reach memory only through the absolute rows.

`EXP-0059` measures the shape and four facts come out:

1. **`REX.R` is the register's fourth bit and `REX.B` the base's, in one byte.**
   `movb 8(%rax), %r8b` is `44 8a 40 08` (four bytes) and
   `movb 8(%r8), %r8b` is `45 8a 40 08`: `44` is `REX.R = 1` with
   `REX.B = 0`, `45` sets both. `movb 8(%r13), %r15b` is `45 8a 7d 08` — the
   same `45`, the register in `ModRM.reg` (`7` = `%r15b`'s low three bits) and
   the base in `ModRM.rm` (`5` = `%r13`'s low three bits).
2. **The three base windows the family already has stay three.** A plain base
   is `mod = 01` with the displacement byte (`44 8a 40 08`), `%rsp` needs
   `ModRM.r/m = 100` plus `SIB = 24` (`44 8a 44 24 08`, five bytes), and `%r12`
   is the same `SIB` byte with `REX.B = 1` (`45 8a 44 24 08`). `%rbp` and
   `%r13` need no extra row because `mod = 01` is the family's floor:
   `movb 8(%rbp), %r15b` is `44 8a 7d 08`.
3. **The displacement is the same disp8/disp32 pair as the rest of the
   family.** `movb 200(%rax), %r8b` is `44 8a 80 c8 00 00 00` (seven bytes) and
   `movb 200(%rsp), %r8b` is `44 8a 84 24 c8 00 00 00` (eight). The `SIB` byte
   is `24` in both SIB rows: scale `00`, index `100` ("no index") and base
   `100`, so `REX.B` is what selects `%rsp` against `%r12`.
4. **Register `8`–`15` and base `8`–`15` both need `REX`, and `%ah` cannot
   join them.** `movb 8(%rax), %ah` is `8a 60 08` (no `REX`), while
   `movb 8(%r8), %ah` is rejected by `llvm-mc` with `can't encode 'ah' in an
   instruction requiring EVEX/REX2/REX prefix`. So the extended rows are
   `x86.gpr8` only, exactly as `ADR-0029`/`EC-36` already require.

Two shapes are *not* taken. The `mod = 00` no-displacement byte row
(`movb (%rax), %r8b` is `44 8a 00`, three bytes) does not exist for any byte
register window — a pre-existing gap this slice does not touch — and `%r16b`
needs the APX `d5` prefix (`d5 40 8a 40 08`).

## Decision

**`0.30.0` appends twelve rows: load and store for the `%r8b`–`%r15b` window in
the three base windows the family already has, each at disp8 and disp32.**

| Direction | Base window | `form_id` | Template | Length |
|---|---|---|---|---|
| load | plain | `x86:mov/r8-ext-base-disp8/legacy` | `44 8a 40 00` | 4 |
| load | plain | `x86:mov/r8-ext-base-disp32/legacy` | `44 8a 80 00 00 00 00` | 7 |
| load | `%rsp` | `x86:mov/r8-ext-rsp-disp8/legacy` | `44 8a 44 24 00` | 5 |
| load | `%rsp` | `x86:mov/r8-ext-rsp-disp32/legacy` | `44 8a 84 24 00 00 00 00` | 8 |
| load | `%r12` | `x86:mov/r8-ext-r12-disp8/legacy` | `45 8a 44 24 00` | 5 |
| load | `%r12` | `x86:mov/r8-ext-r12-disp32/legacy` | `45 8a 84 24 00 00 00 00` | 8 |
| store | plain | `x86:mov/base-disp8-r8-ext/legacy` | `44 88 40 00` | 4 |
| store | plain | `x86:mov/base-disp32-r8-ext/legacy` | `44 88 80 00 00 00 00` | 7 |
| store | `%rsp` | `x86:mov/rsp-disp8-r8-ext/legacy` | `44 88 44 24 00` | 5 |
| store | `%rsp` | `x86:mov/rsp-disp32-r8-ext/legacy` | `44 88 84 24 00 00 00 00` | 8 |
| store | `%r12` | `x86:mov/r12-disp8-r8-ext/legacy` | `45 88 44 24 00` | 5 |
| store | `%r12` | `x86:mov/r12-disp32-r8-ext/legacy` | `45 88 84 24 00 00 00 00` | 8 |

Five properties follow:

- **The register slot is four bits: `REX.R` at `[2,1]` plus `ModRM.reg` at
  `[19,3]`, with `0`–`7` excluded.** The template's `REX.R = 1` is the bit the
  slot's top bit writes, so a value below `8` would clear it and emit the
  `%spl`–`%dil` row's prefix (`E-RANGE-004`, `N16ag`).
- **The plain-base rows still take a four-bit base: `REX.B` at `[0,1]` plus
  `ModRM.rm` at `[16,3]`, excluding `4` and `12`.** The template's `REX = 44`
  grows to `45` when the base is `%r8`–`%r15`; that is the base slot's top bit,
  not a new row, which is why `movb 8(%r8), %r8b` and
  `movb 8(%rax), %r8b` are one row with different `REX.B`.
- **The two `SIB` rows are what keep `%rsp` and `%r12` one row apart.** Both
  carry `SIB = 24`; the only difference is the template's `REX.B`, so `%rsp`
  is the `44` template and `%r12` the `45` one. There is no base slot: the two
  bit patterns are disjoint by template, so neither can be reached from the
  other row.
- **The displacement keeps the family's two widths.** `disp8` sits at `[24,8]`
  on the plain-base rows and `[32,8]` on the `SIB` rows; `disp32` at `[24,32]`
  and `[32,32]`. Content is signed, as everywhere in the family.
- **The high-byte kind is absent by construction.** Every row here is
  `REX`-prefixed, so the loader's `ADR-0029` rule rejects an `x86.gpr8h` slot
  at definition load (`E-DEF-001`), and a plan supplying `x86.gpr8h`/`r8h` is
  `E-OPERAND-001` on both axes (`N02at`).

## Consequences

- `0.30.0` is a 267-form document, byte-reproducing every `0.29.0` row.
- Its positive fixture `X86-P34-gpr8-ext-mem` has twelve instructions and 74
  bytes: one per row, both directions in all three base windows, six four- and
  five-byte instructions beside six seven- and eight-byte ones. The registers
  span the window (`%r8b`, `%r9b`, `%r10b`, `%r11b`, `%r14b`, `%r15b`) so the
  four-bit field is exercised at both ends, and the `45` templates appear both
  with a plain extended base (`%r8`, `%r12`).
- Negatives pin the version boundary in both directions (`N01bm`, `N01bn`),
  the high-byte kind on a `-ext` row (`N02at`), a `disp8` operand on a
  `disp32` row (`N02au`), the `disp32` end point (`N03q`), register `16`
  (`N14ad`), register `0` on a `-ext` row (`N16ag`), `%rsp` as the base of a
  non-`SIB` row (`N16ah`) and `%r12` likewise (`N16ai`).
- `EC-06` and `EC-38` are revised in place; no new `EC` row appears. `EC-02`
  is untouched: these rows use displacement widths the family already has.
- No schema, loader or materializer change: the rows are the same three-slot
  shape as `x86:mov/r8-base-disp8-rex/legacy`, with the register slot widened
  from three bits to four.

## Alternatives rejected

- **Let `%r8b`–`%r15b` ride the existing `-rex` rows by widening their
  register slot.** The template's `REX.R` is `0`, so the slot's top bit would
  rewrite the prefix to `44`/`45` — a row whose `form_id` says `%spl`–`%dil`
  would emit `%r8b`–`%r15b`. The bytes would be right for the register the
  plan asked for and wrong for the row the plan named (`INV-02`).
- **Collapse `%rsp` and `%r12` into one `SIB` row with a two-value base slot.**
  It works, but it is the only row in the family whose base slot is neither a
  contiguous window nor a constant, and the existing family keeps one row per
  `(register window, base window)` pair. Splitting matches the
  `-rsp`/`-r12` names the other windows already use.
- **Add the `mod = 00` no-displacement rows here.** They are missing for
  `%al`–`%bl` and `%spl`–`%dil` too; taking them in this slice would widen two
  axes at once and leave the ADR's counterexample (`%ah` on an extended row)
  tangled with a second one.
- **Carry `x86.gpr8h` on the extended rows.** `llvm-mc` refuses the source
  outright, and the loader already refuses the slot (`E-DEF-001`).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `44 8a 40 08` / `45 8a 40 08` at disp8, `44 8a 80 …` at disp32 | `llvm-mc -show-encoding`, `EXP-0059` §1 | high |
| `REX.R` at `[2,1]`, `REX.B` at `[0,1]`, `ModRM.reg` at `[19,3]`, `ModRM.rm` at `[16,3]` | the byte strings; `EXP-0059` §2 | high |
| `SIB = 24` selects `%rsp`/`%r12` by `REX.B` alone | `llvm-mc -show-encoding` and `-disassemble`, `EXP-0059` §3 | high |
| `%rbp`/`%r13` need no extra row at `mod = 01` | `llvm-mc -show-encoding`, `EXP-0059` §3 | high |
| `%ah` is illegal with any `REX` prefix | `llvm-mc` rejection, `EXP-0059` §4 | high |
| `%r16b` needs the APX `d5` prefix | `llvm-mc -show-encoding`, `EXP-0059` §4 | high |
| the `mod = 00` byte row exists but is absent from the family | `llvm-mc -show-encoding`, `EXP-0059` §4 | high |

## Review triggers

- The `mod = 00` no-displacement byte rows are attempted: they are missing for
  every register window, not only the extended one.
- `REX.X` is needed at byte width: a `SIB` index with an extended register.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- `moffs` for the byte width is requested: `a0`/`a2`, nine bytes.
- The APX `d5` register window is attempted.
