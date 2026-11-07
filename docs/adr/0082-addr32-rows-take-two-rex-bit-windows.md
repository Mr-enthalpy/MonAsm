# ADR-0082: the `0x67` rows take the two fixed-`REX`-bit windows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P59` (the `0x67` + two-`REX`-bit windows on the 32-bit indexed
  `mov`, both directions at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the same `[40,8]`/`[40,32]` displacement offsets now cover
  the two-bit windows), `EC-06` (two bits of one `REX` byte extend two operands
  at once), `EC-08` (every fixed-`REX`-bit window behind `0x67` is now a row and
  the deferred list shrinks to the `REX.W` siblings), `EC-37` (the index's
  fourth bit composes with `REX.R`/`REX.B` in the same byte) and `EC-38` (the
  `addr32` row now splits into eight windows, not four)

## Context

`ADR-0081` added the three single-bit windows and deferred the combinations
where two `REX` bits are fixed at once. `EXP-0084` measures all four of them
(`43`, `45`, `46`, `47`) and four facts come out:

1. **Two bits of one byte extend two operands at once.**
   `movl 8(%r8d,%r9d,1), %eax` is `67 43 8b 44 08 08` (`REX.BX`): the base and
   the index are extended while the value register stays low.
   `movl 8(%r8d,%ecx,1), %r8d` is `67 45 8b 44 08 08` (`REX.RB`),
   `movl 8(%eax,%r9d,1), %r8d` is `67 46 8b 44 08 08` (`REX.RX`) and
   `movl 8(%r8d,%r9d,1), %r8d` is `67 47 8b 44 08 08` (`REX.RBX`).
2. **The geometry does not move.** `0x67` is byte 0 and `REX` byte 1, so the
   opcode is byte 2, `ModRM` byte 3 and `SIB` byte 4: register `[27,3]`, base
   `[32,3]`, index `[35,3]`, scale `[38,2]` and displacement
   `[40,8]`/`[40,32]`. Only which slots carry a `[8,1]`/`[9,1]`/`[10,1]` bit
   changes.
3. **Each extended operand excludes `0`–`7`, each low operand stays three
   bits.** `movl 8(%eax,%r9d,1), %eax` is the `REX.X` row
   (`67 42 8b 44 08 08`), not the `REX.BX` row; the two-bit row cannot write a
   low base or index. A value past three bits on a slot the row keeps low is
   `E-OPERAND-004`.
4. **The extended memory operands still cannot be `%esp`, and `%r12d` works on
   both.** `llvm-mc` rejects `8(%r8d,%esp,1)`; `%r12d` as a base is
   `67 41 8b 44 0c 08` and as an index `67 42 8b 44 20 08`. On a `B` row the
   base `4` would name `%r12d`, so `%esp` is `E-RANGE-004` there, and the same
   holds for index `4` on an `X` row.

## Decision

1. **`0.55.0` appends sixteen rows: four bit combinations × two directions ×
   two displacement widths.** Each row is a `0.54.0` shape with a second fixed
   `REX` bit.

   | Direction | Bits | Displacement | `form_id` | Template | Length |
   |---|---|---|---|---|---|
   | load | `BX` | `disp8` | `x86:mov/r32-addr32-base-ext-index-ext-disp8/legacy` | `67 43 8b 44 00 00` | 6 |
   | store | `BX` | `disp8` | `x86:mov/addr32-base-ext-index-ext-disp8-r32/legacy` | `67 43 89 44 00 00` | 6 |
   | load | `BX` | `disp32` | `x86:mov/r32-addr32-base-ext-index-ext-disp32/legacy` | `67 43 8b 84 00 00 00 00 00` | 9 |
   | store | `BX` | `disp32` | `x86:mov/addr32-base-ext-index-ext-disp32-r32/legacy` | `67 43 89 84 00 00 00 00 00` | 9 |
   | load | `RB` | `disp8` | `x86:mov/r32-ext-addr32-base-ext-index-disp8/legacy` | `67 45 8b 44 00 00` | 6 |
   | store | `RB` | `disp8` | `x86:mov/addr32-base-ext-index-disp8-r32-ext/legacy` | `67 45 89 44 00 00` | 6 |
   | load | `RB` | `disp32` | `x86:mov/r32-ext-addr32-base-ext-index-disp32/legacy` | `67 45 8b 84 00 00 00 00 00` | 9 |
   | store | `RB` | `disp32` | `x86:mov/addr32-base-ext-index-disp32-r32-ext/legacy` | `67 45 89 84 00 00 00 00 00` | 9 |
   | load | `RX` | `disp8` | `x86:mov/r32-ext-addr32-base-index-ext-disp8/legacy` | `67 46 8b 44 00 00` | 6 |
   | store | `RX` | `disp8` | `x86:mov/addr32-base-index-ext-disp8-r32-ext/legacy` | `67 46 89 44 00 00` | 6 |
   | load | `RX` | `disp32` | `x86:mov/r32-ext-addr32-base-index-ext-disp32/legacy` | `67 46 8b 84 00 00 00 00 00` | 9 |
   | store | `RX` | `disp32` | `x86:mov/addr32-base-index-ext-disp32-r32-ext/legacy` | `67 46 89 84 00 00 00 00 00` | 9 |
   | load | `RBX` | `disp8` | `x86:mov/r32-ext-addr32-base-ext-index-ext-disp8/legacy` | `67 47 8b 44 00 00` | 6 |
   | store | `RBX` | `disp8` | `x86:mov/addr32-base-ext-index-ext-disp8-r32-ext/legacy` | `67 47 89 44 00 00` | 6 |
   | load | `RBX` | `disp32` | `x86:mov/r32-ext-addr32-base-ext-index-ext-disp32/legacy` | `67 47 8b 84 00 00 00 00 00` | 9 |
   | store | `RBX` | `disp32` | `x86:mov/addr32-base-ext-index-ext-disp32-r32-ext/legacy` | `67 47 89 84 00 00 00 00 00` | 9 |

2. **The placement of each bit is unchanged.** `REX.B` stays `[8,1]`,
   `REX.X` stays `[9,1]` and `REX.R` stays `[10,1]`; the slot they extend
   carries the bit plus its three-bit field:
   `[10,1]`+`[27,3]` for `REX.R`, `[8,1]`+`[32,3]` for `REX.B` and
   `[9,1]`+`[35,3]` for `REX.X`. The slot without a fixed bit stays a
   three-bit field with no extra bit, and the base/index keep their
   `x86.gpr32` kinds (`rm32`/`sib_index32`, index `4` excluded).
3. **The scale and displacement are the `0.54.0` fields.** Scale `[38,2]`
   (`0`–`3` = x1/x2/x4/x8, `4` is `E-RANGE-001`) and displacement
   `[40,8]`/`[40,32]` (`disp8`/`disp32`, signed).
4. **A value outside the row's window is rejected.** `0`–`7` on an extended
   operand is `E-RANGE-004` (that value belongs to a row with the bit clear);
   `8`–`15` on an operand the row keeps low is `E-OPERAND-004`. Nothing
   truncates and no row inserts a bit it does not fix.
5. **No schema, loader or materializer change.** `0.54.0` already composes
   multiple placements on one slot; the new rows only add placements.

## Consequences

- `0.55.0` is a 445-form document that byte-reproduces every `0.54.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P59-gpr32-mov-index-addr32-rex-two-bit-windows` has
  twenty instructions: the sixteen rows plus four corners (`%r12d` on all
  three operands, `%r13d` on all three operands, the x8 scale with `%r15d`, and
  a store with `%r15d`/`%ebp`). Its `expected.bin` comes from `llvm-mc` +
  `llvm-objcopy`, never from the materializer.
- Negatives pin the version boundary in both directions, a missing index, the
  scale end, three extended-window floors and the two three-bit field ends.
- `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC`
  row is added or renumbered.

## Alternatives rejected

- **One row accepting low and extended values on each operand and choosing the
  fixed bits from the operand values.** Rejected: the row, the prefix and the
  length would be chosen from an operand (`INV-02`, `INV-04`), and
  `67 43 8b 44 08 08` and `67 42 8b 44 08 08` are different instructions.
- **Fold the four combinations into the three single-bit rows.** Rejected: a
  single-bit row fixes one bit at `1` and the others at `0`; `43`/`45`/`46`/`47`
  fix two at `1`, which is not an operand value.
- **Add the `0x67` `REX.W` siblings (`67 48`, `67 4c`, `67 4d`, `67 4f`) now.**
  They change the value width to 64 bits and need their own register kinds; a
  different slice.
- **Add a symbol in the displacement now.** A relocation changes the field's
  meaning (`03_fixup_model.md`), and no `addr32` fixup row exists.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 43 8b 44 08 08` is the `REX.BX` load at six bytes | `llvm-mc -show-encoding`, `EXP-0084` §1 | high |
| `45`/`46`/`47` are the `RB`/`RX`/`RBX` bytes | `llvm-mc -show-encoding`, `EXP-0084` §1 | high |
| the opcode stays at byte 2, `ModRM` 3 and `SIB` 4 | `llvm-mc -show-encoding`, `EXP-0084` §2 | high |
| `%esp` is rejected as an index; `%r12d` works as base and index | `llvm-mc`, `EXP-0084` §3 | high |
| the twenty byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0084` §1 | high |

## Review triggers

- An `0x67` row with `REX.W` is attempted (`67 48`, `67 4c`, `67 4d`,
  `67 4f`).
- A symbol or relocation in an `addr32` displacement is requested.
- The no-base indexed shape or the `moffs` form is attempted with `0x67`.
- An EVEX or VEX row is proposed with an address-size prefix.
- `%esp` as a base or index is requested with an extended window.
