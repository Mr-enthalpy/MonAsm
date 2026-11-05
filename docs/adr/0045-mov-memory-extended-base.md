# ADR-0045: The 8/16-bit memory bases reach `r8`–`r15` through a `REX` byte

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P22` (the extended base of the 8/16-bit `mov` memory rows)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0044` §Review triggers (the `-base-ext` window it deferred) and
  `ADR-0034` §Decision 1 (the same window at 8 and 16 bits)

## Context

`ADR-0044` gave the 8/16-bit `mov` memory rows a three-bit base and named the
extension as its own decision. The four families do not behave alike, and the
difference is observable before any table changes:

1. **The word and REX-less low-byte rows pay a byte.** `movw %ax, 8(%rax)` is
   `66 89 40 08`, four bytes, with no `REX` byte at all; `movw %ax, 8(%r8)` is
   `66 41 89 40 08`, five. The same holds for `movb %al, 8(%rax)`
   (`88 40 08`) versus `movb %al, 8(%r8)` (`41 88 40 08`). A row that accepted
   both bases and inserted the `REX` byte on seeing a high value would make the
   instruction length depend on an operand value, and with it every following
   fragment offset (`INV-04`). The length decision must be the form's.
2. **The `40`-prefixed byte rows already carry the byte.** `movb %spl, 8(%rax)`
   is `40 88 60 08`; `movb %spl, 8(%r8)` is `41 88 60 08`. One bit differs and
   the length does not, because the `REX` byte is present for the register set
   (`ADR-0029`). Widening these rows in place reaches the high base for free.
3. **The high-byte rows can never extend.** `movb %ah, 8(%r8)` is rejected:
   `can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`. The
   `REX` byte that carries `REX.B` also re-labels numbers 4–7 from
   `ah`–`bh` to `spl`–`dil`, so the base extension and the register set cannot
   coexist. There is no legal encoding to defer, not a window to add.
4. **The `REX.B` bit is not always template bit 0.** In the word rows the
   `0x66` byte stays first (`ADR-0044`), so the `REX` byte is byte 1 and
   `REX.B` is bit 8. In the byte rows the `REX` byte is byte 0, so `REX.B` is
   bit 0. The placement differs by family; the bit's meaning does not.
5. **`%rsp` and `%r12` still force a `SIB` byte.** `movw %ax, 8(%rsp)` is
   `66 89 44 24 08` and `movb %spl, 8(%rsp)` is `40 88 64 24 08`; the high-base
   forms need the same window one register number higher
   (`66 41 89 44 24 08`, `41 88 64 24 08`). No `mov` memory row carries a `SIB`
   byte, so both bases stay out (`EC-35`).

`EXP-0047` measures all of the above with `llvm-mc` 23.1.2 on 2026-11-05, and
each of the thirty-one byte strings round-trips through `llvm-mc -disassemble`
to the same source line.

## Decision

**`0.18.0` adds eight `-base-ext` rows (word and REX-less low-byte, load/store ×
`disp8`/`disp32`) and widens the four `40`-prefixed byte rows from three to four
base bits in place. The byte axis is a two-by-two partition: the new rows carry
register numbers `0`–`3` and the widened `40` rows `4`–`7`, so every byte
register reaches both base windows through exactly one row. No `EC` row is
added: `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36` and `EC-38` already
state every field, and `EC-38` is revised in place so the GPR memory family
joins its reach statement.**

The eight appended rows:

| # | `form_id` | Template | Slots |
|---|---|---|---|
| 1 | `x86:mov/r16-base-ext-disp8/legacy` | `66418b4000` | dest `gpr16`/`r16` `[27,3]`; base `[8,1]`+`[24,3]` excl `0–7`,`12`; `disp8` `[32,8]` |
| 2 | `x86:mov/r16-base-ext-disp32/legacy` | `66418b8000000000` | dest; base; `disp32` `[32,32]` |
| 3 | `x86:mov/base-ext-disp8-r16/legacy` | `6641894000` | src `gpr16`/`r16` `[27,3]`; base; `disp8` `[32,8]` |
| 4 | `x86:mov/base-ext-disp32-r16/legacy` | `6641898000000000` | src; base; `disp32` `[32,32]` |
| 5 | `x86:mov/r8-base-ext-disp8/legacy` | `418a4000` | dest `gpr8`/`r8` `[19,3]` excl `4–7`; base `[0,1]`+`[16,3]` excl `0–7`,`12`; `disp8` `[24,8]` |
| 6 | `x86:mov/r8-base-ext-disp32/legacy` | `418a8000000000` | dest; base; `disp32` `[24,32]` |
| 7 | `x86:mov/base-ext-disp8-r8/legacy` | `41884000` | src `gpr8`/`r8` `[19,3]` excl `4–7`; base; `disp8` `[24,8]` |
| 8 | `x86:mov/base-ext-disp32-r8/legacy` | `41888000000000` | src; base; `disp32` `[24,32]` |

The four revised rows keep their `form_id` and template (`408a6000`,
`408aa000000000`, `40886000`, `4088a000000000`) and change only the base slot:
`[16,3]` becomes `[0,1]`+`[16,3]` and `excluded: [4]` becomes
`excluded: [4, 12]`. Bases `0`–`7` encode exactly as before (`REX.B = 0`), so
the revision adds reach without moving a byte.

Four properties follow:

- **The windows are disjoint.** Every `-base-ext` row excludes `0`–`7` (their
  `REX.B = 0` encodings belong to the short row) and `12`; the widened `40` rows
  accept `0`–`7` and `8`–`15` minus `4` and `12`. On the byte axis the register
  set is the second half of the partition: the new rows carry numbers `0`–`3`
  and exclude `4`–`7`, while the widened `40` rows carry `4`–`7` and exclude
  `0`–`3`. `movb %spl, 8(%r8)` therefore names the `40` row and
  `movb %al, 8(%r8)` the `-base-ext` row, each with exactly one encoding.
- **The word rows are one byte longer.** `-base-ext` is a form, not a modifier:
  the `REX` byte is in the template, so the displacement moves from `[24,…]`
  to `[32,…]` with it.
- **The high-byte rows stay three bits.** No `-base-ext` row takes
  `x86.gpr8h`; a plan that needs both is `E-FORM-001` at best, because
  `llvm-mc` cannot encode it either.
- **The SIB base is still absent.** `%rsp`/`%r12` remain `E-RANGE-004` on every
  new and revised row.

The definition gates also learn where a `REX` byte can be. `check_definition.py`
and the Rust loader read `template[0]` to decide whether an `x86.gpr8h` slot is
legal, which is true for every row before `0.18.0`; the new word rows are the
first with `66` in front of the `REX` byte, so both now skip a leading `0x66`
before looking for the `REX`. A `66 41 88 …` row carrying `x86.gpr8h` would
otherwise pass a check whose premise it violates. A unit test pins the new
shape; no existing template changes behaviour (their byte 1 is an opcode, not a
`REX` prefix).

## Consequences

- `0.18.0` is a 127-form document with digest
  `sha256:e1281b0c11d7e2bed9bd1ec7fa5404dadca2c82959376cbe3edfd9ff56b9e33d`.
- Its positive fixture `X86-P22-mov-mem-base-ext` covers all twelve rows, both
  `disp8` ends, both `disp32` promotions, a low base on a widened `40` row, and
  the high registers `r8`, `r9`, `r13`, `r14` and `r15`.
- Negatives pin the two windows (`0`–`7` on an extension row, `%r12` there,
  base `8` on the short rows), the version boundary against `0.17.0`, and the
  high-byte refusal (`x86.gpr8h` has no extension row).
- `07_definition_format.md` §8.1 gains the eight rows, records the four revised
  base cells, and appends the `0.18.0` digest row and narrative.
- `02_encoding_choices.md` gains the eight surface rows, updates the four `-rex`
  rows' base description, and revises `EC-38` in place.
- No schema change; the loader change is the `REX`-detection rule above.

## Alternatives rejected

- **One row per family that inserts `REX` when the base is high.** The length
  would depend on an operand value (`INV-04`), and `40 88 40 08` decodes as
  `movb %spl, 8(%rax)`: the short and long templates differ in a bit the row
  would have to choose.
- **A `rex` modifier on the base operand.** A modifier may not write bits
  (`ADR-0015`), and the prefix choice would be the plan's, not the form's.
- **Extend the high-byte rows with `REX.B`.** `llvm-mc` rejects
  `movb %ah, 8(%r8)`; the prefix re-labels the very register the row names.
- **Let the byte `-base-ext` rows carry numbers `0`–`7`.** Then `spl`–`dil`
  with a high base would have two rows with the same bytes (`41 88 60 08`): the
  new row and the widened `40` row. Splitting the register set keeps each
  `(register, base)` pair on one row; it also keeps the high-byte exclusion
  where `ADR-0029` put it.
- **Widen the word and byte bases in place with a fixed `REX = 40`.** Every
  `%rax`-base word instruction would gain a redundant `40`, which `EC-28`
  forbids; the template cannot hold both lengths.
- **Include `%rsp`/`%r12` by giving the rows a `SIB` byte.** That is the shape
  `ADR-0028`/`ADR-0034` kept as its own form (and `ADR-0035` made operand
  fields); adding it here would rewrite every template on two axes at once.
- **Reach `r8b`–`r15b`/`r8w`–`r15w` in the same slice.** That is `REX.R`
  (`[27,3]`→`[26,4]` or `[19,3]`→`[18,4]`), a register decision rather than a
  base one, and it needs its own counterexample for the high-byte interaction.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 41 89 40 08`, `66 41 8b 40 08`, `66 41 89 47 08` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0047` §1–§2 | high |
| `41 88 40 08`, `41 8a 40 08`, `41 88 60 08`, `41 8a 60 08` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0047` §1–§3 | high |
| `REX.B` is bit 8 after `66` and bit 0 in the `41` rows | the byte strings above; `66` is template byte 0 in every word row | high |
| `movb %ah, 8(%r8)` is rejected with the REX/high-byte message | `llvm-mc` error text, `EXP-0047` §5 | high |
| `%rsp`/`%r12` add a `SIB` byte at both widths | `llvm-mc -show-encoding`, `EXP-0047` §4 | high |
| `disp8`/`disp32` boundaries are unchanged from `0.17.0` | `llvm-mc -show-encoding`, `EXP-0047` §2 | high |

## Review triggers

- The `%rsp`/`%r12` SIB shape is attempted: `66 41 89 44 24 08` needs a row
  whose template carries `SIB = 24`.
- `r8b`–`r15b` or `r8w`–`r15w` is attempted: every row on this axis gains
  `REX.R` and the register slot becomes four bits.
- `mod = 00` is attempted for a GPR memory row: `66 41 89 00` is
  `movw %ax, (%r8)`, and the `%rbp`/`%r13` collision applies.
- A high-byte memory operand with a high base is attempted: it has no encoding,
  and the row that accepts it would name a different register.
