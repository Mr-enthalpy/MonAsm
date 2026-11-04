# ADR-0029: The operand-size prefix and the high-byte registers are form facts

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P5` (prefix rules) and the 8-bit register naming it carries
- Supersedes: none
- Superseded by: none

## Context

`X86-P5` asks for one prefix-rule vector. Two independent prefix rules decide
bytes in x86-64, and neither is visible in a mnemonic alone:

1. **`0x66` selects the 16-bit operand size.** The same opcode and the same
   `ModRM` byte name a different register width with and without it.
2. **A REX prefix re-labels byte registers 4–7.** `88 e5` and `40 88 e5` have
   the same opcode and the same `ModRM` byte but different source and
   destination registers.

`ADR-0008` settled that an encoding form is a `form_id` and that fields are
content; `ADR-0027` and `ADR-0028` applied that to addressing shapes. This ADR
applies it to the prefix byte and to the register kind it changes.

`llvm-mc 23.1.2` measures the following on 2026-11-05 (`-show-encoding` for the
first table, `-disassemble` for the rest):

| Source | Bytes | Reading |
|---|---|---|
| `movw %bx, %ax` | `66 89 d8` | `0x66` + `89 /r`, `reg = 011`, `r/m = 011` |
| `movw %si, %di` | `66 89 f7` | `reg = 110`, `r/m = 111` |
| `movw %dx, %cx` | `66 89 d1` | `reg = 010`, `r/m = 001` |
| `movw %ax, %ax` | `66 89 c0` | `reg = 000`, `r/m = 000` |
| `movb %ah, %ch` | `88 e5` | no prefix; `reg = 100` is `ah`, `r/m = 101` is `ch` |
| `movb %ch, %ah` | `88 ec` | the same two numbers, swapped |
| `movb %ah, %ah` | `88 e4` | `reg = r/m = 100` |
| `movb %al, %cl` | `88 c1` | `reg = 000` is `al`, `r/m = 001` is `cl` |
| `movb %spl, %bpl` | `40 88 e5` | REX `40`; the same `e5` now names `spl`/`bpl` |
| `movb %cl, %al` | `88 c8` | `reg = 001` is `cl`, `r/m = 000` is `al` |

`-disassemble` on the remaining field values, to pin the whole 3-bit domain:

| Bytes | Decodes as | Bytes | Decodes as |
|---|---|---|---|
| `88 e0` | `movb %ah, %al` | `40 88 e0` | `movb %spl, %al` |
| `88 e1` | `movb %ah, %cl` | `40 88 e1` | `movb %spl, %cl` |
| `88 e2` | `movb %ah, %dl` | `40 88 e2` | `movb %spl, %dl` |
| `88 e3` | `movb %ah, %bl` | `40 88 e3` | `movb %spl, %bl` |
| `88 e4` | `movb %ah, %ah` | `40 88 e4` | `movb %spl, %spl` |
| `88 e5` | `movb %ah, %ch` | `40 88 e5` | `movb %spl, %bpl` |
| `88 e6` | `movb %ah, %dh` | `40 88 e6` | `movb %spl, %sil` |
| `88 e7` | `movb %ah, %bh` | `40 88 e7` | `movb %spl, %dil` |
| `88 c4` | `movb %al, %ah` | `40 88 c4` | `movb %al, %spl` |
| `88 c5` | `movb %al, %ch` | `40 88 c5` | `movb %al, %bpl` |
| `88 c6` | `movb %al, %dh` | `40 88 c6` | `movb %al, %sil` |
| `88 c7` | `movb %al, %bh` | `40 88 c7` | `movb %al, %dil` |

| Bytes | Decodes as | Bytes | Decodes as |
|---|---|---|---|
| `66 89 c0` | `movw %ax, %ax` | `66 8b c0` | `movw %ax, %ax` |
| `66 89 c8` | `movw %cx, %ax` | `66 8b c8` | `movw %ax, %cx` |
| `66 89 d0` | `movw %dx, %ax` | `66 8b d0` | `movw %ax, %dx` |
| `66 89 d8` | `movw %bx, %ax` | `66 8b d8` | `movw %ax, %bx` |
| `66 89 e0` | `movw %sp, %ax` | `66 8b e0` | `movw %ax, %sp` |
| `66 89 e8` | `movw %bp, %ax` | `66 8b e8` | `movw %ax, %bp` |
| `66 89 f0` | `movw %si, %ax` | `66 8b f0` | `movw %ax, %si` |
| `66 89 f8` | `movw %di, %ax` | `66 8b f8` | `movw %ax, %di` |

Four facts decide the shape list:

1. **The width is not in the mnemonic and not in the operands.** `89 c3`
   (`movl %ebx, %eax`) and `66 89 c3` (`movw %bx, %ax`) carry the same
   `ModRM`; only the prefix byte differs. A plan that says "move `bx` to `ax`"
   has stated the register kind, but a single row that accepted both `gpr32` and
   `gpr16` operands would have to decide the prefix from the operand kind — a
   value-driven choice (`INV-02`).
2. **The prefix leads the instruction, and the one closest to the opcode
   decides the width.** `llvm-mc -disassemble` accepts `66 48 89 c0` and prints
   `movq %rax, %rax`, while `48 66 89 c0` prints `movw %ax, %ax`. A 16-bit row
   therefore cannot leave the prefix to a later stage: `0x66` is template byte 0
   of the form, not an operand.
3. **The high-byte registers share numbers 4–7 with the REX low-byte
   registers.** `88 e5` is `ah, ch`; `40 88 e5` is `spl, bpl`. The number 4–7
   in `ModRM.reg` or `ModRM.rm` names one of two different register sets
   depending on a prefix byte. No single kind can mean both.
4. **A redundant REX also reaches `al`–`bl`.** `40 88 c1` decodes as
   `movb %al, %cl`, the same instruction as `88 c1`. `EC-28` records the same
   situation for `40 89 d8` vs `89 d8` and pins the minimal prefix set as a
   definition rule, with no plan field allowed to request the redundant byte.
   If a REX row accepted 0–3 as well, one register pair would have two legal
   forms, and the plan's choice between them would be an encoding decision the
   table had not made.

`llvm-mc` rejects the illegal combinations rather than repairing them:

- `movb %ah, %spl`, `movb %spl, %ah` and `movb %ah, %r8b` all report
  `can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`.
- `movw %ax, %eax` reports `invalid operand for instruction`.

## Decision

1. **`X86-P5` ships as five rows in `definitions/x86_64/0.4.0.json`:** two
   16-bit directions, one high-byte row, and two low-byte rows (REX-less and
   REX).
   - `x86:mov/rm16-r16/legacy` (`66 89 /r`)
   - `x86:mov/r16-rm16/legacy` (`66 8B /r`)
   - `x86:mov/rm8h-r8h/legacy` (`88 /r`, high-byte)
   - `x86:mov/rm8-r8/legacy` (`88 /r`, low-byte, no REX)
   - `x86:mov/rm8-r8-rex/legacy` (`REX 88 /r`, low-byte)
2. **`0x66` is template, and the width is the register kind.** A `gpr16` row
   has `66` as its first template byte and only `x86.gpr16` slots; a 32-bit or
   64-bit plan cannot reach it. The `8B` direction is a second form, because
   the opcode direction is a form (`EC-27`).
3. **The high-byte register set is its own kind.** `x86.gpr8h` slots hold
   register numbers 4–7 and mean `ah`/`ch`/`dh`/`bh`; the row excludes 0–3,
   which are not high-byte registers.
4. **The low-byte set is `x86.gpr8`, split by prefix.** The REX-less row
   excludes 4–7 (they would encode `ah`–`bh`); the REX row excludes 0–3 (they
   would be the redundant `40` encoding of `al`–`bl`, `EC-28`). Each legal
   byte register has exactly one row.
5. **The rule is a definition check, not an encoder branch.** The loader
   rejects (`E-DEF-001`) a `x86.gpr8h` slot in a REX-prefixed template and a
   REX-less `x86.gpr8` slot that does not exclude 4–7. `check_definition.py`
   applies the same two rules to the files, so a table that violates them
   never reaches a plan. No code path inspects a register number to choose a
   prefix.
6. **`EC-36` records the decision.** The operand-size prefix and the high-byte
   re-labelling are one `EC` row, carried by `form variant`.
7. **Only `mov` register-to-register at `16`/`8` bits.** The `8A`/`8B`
   direction pair for 8-bit, `88`/`89` for memory operands, `0x67`, `0x66` on
   32-bit rows, `r8`–`r15` and `spl`–`dil` as 8-bit *base/destination memory*
   operands stay out. Each is a different form family (`EC-05`, `EC-06`,
   `EC-08`, `EC-09`).

## Consequences

- `X86-P5` moves from deferred to passing with a 20-byte fixture:
  `movw %bx,%ax`, `movw %si,%di`, a decode-verified `66 8b c3`, `movb %ah,%ch`,
  `movb %ch,%ah`, `movb %al,%cl`, `movb %spl,%bpl`, and `movb %ah,%ah`. The last
  three pin the disjointness the exclusion lists enforce.
- `N01z` is the `0.3.0` version boundary (`66 89 c0` absent there); `N02k`
  puts `x86.gpr8h`/`rm8h` operands on the REX row (`E-OPERAND-001` on both
  `kind` and `target_type`); `N16g` puts register 4 into the REX-less low-byte
  row (`E-RANGE-004`).
- The table grows from 17 to 22 rows, so `07_definition_format.md` §8.1 and
  the digest move with it, and the rule in §9 grows one row.
- Cost: the 8-bit surface is now three rows for one opcode direction. A future
  slice that adds `8A` doubles it; the alternative (one row with a
  `rex` modifier) would put a prefix decision in a plan field.

## Alternatives considered

- **One `mov/r8-r8` row with a `rex` modifier.** Rejected: the plan would
  state the prefix byte, and two plans for the same register pair could differ
  only in a redundant prefix (`EC-28`). The kind is the register set; the
  prefix follows from it.
- **One `mov/r8-r8` row and let the encoder add REX when the number is 4–7.**
  Rejected: that is exactly the value-driven prefix choice the source question
  names. `88 e5` and `40 88 e5` are different registers, so the encoder would
  silently rename the operand.
- **Name the high-byte registers as `x86.gpr8` with numbers 0–3.** Rejected:
  the plan's number would then not be the encoding's number, and no
  counterexample could distinguish `ah` from `spl` without a second field.
- **Use `0x66` as a `modifiers` entry.** Rejected: modifiers are semantic
  (`lock`, `rep`) and `04_errors.md` rejects an unused one with
  `E-OPERAND-003`. A prefix that changes the register width is the form, and
  `N19` already shows a modifier cannot carry a form fact.
- **Add `8A` for symmetry.** Rejected for this slice: `X86-P5`'s question is
  the prefix rule, and one measured direction is enough to hold it. The
  direction pair is `X86-P1`'s question and is already answered at 64 bits.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The sixteen `66 89`/`66 8b` decodes and the five assembled `movw` forms | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0031` §2 | high |
| The twenty-four `88`/`40 88` decodes over numbers 0–7 | `llvm-mc -disassemble`, `EXP-0031` §2 | high |
| `66 48 89 c0` is `movq`, `48 66 89 c0` is `movw` | `llvm-mc -disassemble`, `EXP-0031` §2 | high |
| `ah` is rejected with `spl` or `r8b` | `llvm-mc` error text, `EXP-0031` §2 | high |
| `40 88 c1` decodes as `al, cl` | `llvm-mc -disassemble`, `EXP-0031` §2 | high |
| `66` and `40` are one-byte prefixes before the opcode | the decoded strings above; the byte counts | high |
| A 16-bit `%sp` is encodable in a register-direct `ModRM` | `66 89 e0` decodes as `movw %sp, %ax`; `mod = 11` has no SIB byte | high |

## Review triggers

- A memory operand at 16 or 8 bits is attempted: `mod = 00`/`01`/`10` interacts
  with `%rsp` and the SIB byte exactly as `ADR-0028` describes, and the 8-bit
  base/destination registers `spl`–`dil` need REX inside the memory form.
- `r8`–`r15` byte registers are attempted: the REX row needs `REX.R`/`REX.B`
  slots, and `EC-06`/`EC-08` become the governing rows.
- A redundant-prefix rule (`EC-28`) is given a form: this ADR's disjointness
  argument assumes one row per register, so a second encoding of `al`–`bl`
  must be a separate plan choice with its own negative test.
- `0x66` is proposed as a modifier or an operand: re-open `EC-36`, because the
  prefix changes the meaning of a register field rather than a value.
