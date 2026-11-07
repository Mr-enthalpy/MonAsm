# ADR-0086: the `0x67 66` rows take the four two-`REX`-bit windows

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P63` (the four two-`REX`-bit windows on the `0x67 66` `movw`
  rows, both directions at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `[48,8]`/`[48,32]` displacement offsets now cover the
  two-bit windows), `EC-06` (two bits of the `REX` byte at position 2 extend two
  operands at once), `EC-07` (the operand-size prefix stays `0x66` at byte 1
  before `REX`), `EC-08` (every fixed-`REX`-bit window on the `0x67 66` family
  is now a row; the deferred list shrinks to the `REX.W` siblings and beyond),
  `EC-36` (the prefix order stays `0x67`, `0x66`, `REX`), `EC-37` (an extended
  index slot excludes `0`–`7` and index `12` composes with `REX.X`) and `EC-38`
  (the `addr32` 16-bit family reaches `%r8w`–`%r15w`, `%r8d`–`%r15d` and
  `%r12d`–`%r15d` in pairs)

## Context

`0.58.0` added the three single-`REX` windows on the bare `0x67 66` pair
(`ADR-0085`). `EXP-0088` measures the four multi-bit combinations (`RB`, `RX`,
`BX`, `RBX`), where two or three `REX` bits are fixed at once, and four facts
come out:

1. **Two or three bits of one byte extend that many operands at once.**
   `movw 8(%r8d,%ecx,1), %r8w` is `67 66 45 8b 44 08 08` (`REX.RB`): the value
   and the base are extended while the index stays low. `movw 8(%eax,%r9d,1),
   %r8w` is `67 66 46 8b 44 08 08` (`REX.RX`), `movw 8(%r8d,%r9d,1), %ax` is
   `67 66 43 8b 44 08 08` (`REX.BX`) and `movw 8(%r8d,%r9d,1), %r8w` is
   `67 66 47 8b 44 08 08` (`REX.RBX`).
2. **The geometry does not move.** `0x67` stays byte 0, `0x66` byte 1 and
   `REX` byte 2, so the opcode is byte 3, `ModRM` byte 4 and `SIB` byte 5:
   value `[35,3]`, base `[40,3]`, index `[43,3]`, scale `[46,2]` and
   displacement `[48,8]`/`[48,32]`. Only which slots carry a `[18,1]`/`[16,1]`/
   `[17,1]` bit changes.
3. **The address size stays 32 bits.** The base and index remain
   `x86.gpr32`/`rm32` and `x86.gpr32`/`sib_index32`; `REX.B` names `%r8d`–
   `%r15d`, never `%r8`–`%r15`. The value stays `x86.gpr16`/`r16`.
4. **Index `4` needs `REX.X` to name `%r12d`.** `movw 8(%r12d,%r13d,1), %r15w`
   is `67 66 47 8b 7c 2c 08`: `SIB = 2c` holds index `5` with `X = 1` and base
   `4` with `B = 1`. A row that leaves `X` at `0` still excludes index `4`
   (`E-RANGE-004`).

## Decision

1. **`0.59.0` appends sixteen rows: four bit combinations × two directions ×
   two displacement widths.** Each row is a `0.58.0` shape with a second fixed
   `REX` bit.

   | Bits | Direction | Displacement | `form_id` | Template | Length |
   |---|---|---|---|---|---|
   | `BX` | load | `disp8` | `x86:mov/r16-addr32-base-ext-index-ext-disp8/legacy` | `67 66 43 8b 44 00 00` | 7 |
   | `BX` | store | `disp8` | `x86:mov/addr32-base-ext-index-ext-disp8-r16/legacy` | `67 66 43 89 44 00 00` | 7 |
   | `BX` | load | `disp32` | `x86:mov/r16-addr32-base-ext-index-ext-disp32/legacy` | `67 66 43 8b 84 00 00 00 00 00` | 10 |
   | `BX` | store | `disp32` | `x86:mov/addr32-base-ext-index-ext-disp32-r16/legacy` | `67 66 43 89 84 00 00 00 00 00` | 10 |
   | `RB` | load | `disp8` | `x86:mov/r16-ext-addr32-base-ext-index-disp8/legacy` | `67 66 45 8b 44 00 00` | 7 |
   | `RB` | store | `disp8` | `x86:mov/addr32-base-ext-index-disp8-r16-ext/legacy` | `67 66 45 89 44 00 00` | 7 |
   | `RB` | load | `disp32` | `x86:mov/r16-ext-addr32-base-ext-index-disp32/legacy` | `67 66 45 8b 84 00 00 00 00 00` | 10 |
   | `RB` | store | `disp32` | `x86:mov/addr32-base-ext-index-disp32-r16-ext/legacy` | `67 66 45 89 84 00 00 00 00 00` | 10 |
   | `RX` | load | `disp8` | `x86:mov/r16-ext-addr32-base-index-ext-disp8/legacy` | `67 66 46 8b 44 00 00` | 7 |
   | `RX` | store | `disp8` | `x86:mov/addr32-base-index-ext-disp8-r16-ext/legacy` | `67 66 46 89 44 00 00` | 7 |
   | `RX` | load | `disp32` | `x86:mov/r16-ext-addr32-base-index-ext-disp32/legacy` | `67 66 46 8b 84 00 00 00 00 00` | 10 |
   | `RX` | store | `disp32` | `x86:mov/addr32-base-index-ext-disp32-r16-ext/legacy` | `67 66 46 89 84 00 00 00 00 00` | 10 |
   | `RBX` | load | `disp8` | `x86:mov/r16-ext-addr32-base-ext-index-ext-disp8/legacy` | `67 66 47 8b 44 00 00` | 7 |
   | `RBX` | store | `disp8` | `x86:mov/addr32-base-ext-index-ext-disp8-r16-ext/legacy` | `67 66 47 89 44 00 00` | 7 |
   | `RBX` | load | `disp32` | `x86:mov/r16-ext-addr32-base-ext-index-ext-disp32/legacy` | `67 66 47 8b 84 00 00 00 00 00` | 10 |
   | `RBX` | store | `disp32` | `x86:mov/addr32-base-ext-index-ext-disp32-r16-ext/legacy` | `67 66 47 89 84 00 00 00 00 00` | 10 |

2. **The placement of each bit is unchanged.** `REX.B` stays `[16,1]`,
   `REX.X` stays `[17,1]` and `REX.R` stays `[18,1]`; a slot they extend
   carries the bit plus its three-bit field: `[18,1]`+`[35,3]` for `REX.R`,
   `[16,1]`+`[40,3]` for `REX.B` and `[17,1]`+`[43,3]` for `REX.X`. A slot
   without a fixed bit stays a three-bit field, and the base/index keep their
   `x86.gpr32` kinds (`rm32`/`sib_index32`, index `4` excluded).
3. **The scale and displacement are the `0.58.0` fields.** Scale `[46,2]`
   (`0`–`3` = x1/x2/x4/x8, `4` is `E-RANGE-001`) and displacement
   `[48,8]`/`[48,32]` (`disp8`/`disp32`, signed).
4. **A value outside the row's window is rejected.** `0`–`7` on an extended
   operand is `E-RANGE-004` (that value belongs to a row with the bit clear);
   `8`–`15` on an operand the row keeps low is `E-OPERAND-004`. Nothing
   truncates and no row inserts a bit it does not fix.
5. **No schema, loader or materializer change.** `0.54.0` already composes
   multiple placements on one slot; the new rows only add placements.

## Consequences

- `0.59.0` is a 481-form document that byte-reproduces every `0.58.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P63-gpr16-mov-index-addr32-rex-two-bit-windows` has
  twenty instructions: the sixteen rows plus four corners (`%r12d` as a base
  with `%r15w`, `%r12d` as a base with `%r15d` as an index, `%r12d`/`%r13d`
  under `REX.RBX`, and the x8 scale). Its `expected.bin` comes from `llvm-mc` +
  `llvm-objcopy`, never from the materializer.
- Negatives pin the version boundary in both directions, three extended-window
  floors, a value past its four-bit field, the missing index, the scale end and
  index `4` on a row that leaves `REX.X` at `0`.
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-36`, `EC-37` and `EC-38` are revised
  in place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Fold all seven `REX` combinations into one row.** Rejected: a `REX` bit the
  row leaves at `0` cannot be set by an operand in this model (`INV-02`/
  `INV-07`), and the window-by-window family is how the earlier `mov` slices
  stayed reviewable.
- **Fold the four combinations into the three single-bit rows.** Rejected: a
  single-bit row fixes one bit at `1` and the others at `0`; `43`/`45`/`46`/`47`
  fix two or three at `1`, which is not an operand value.
- **Take the `REX.W` siblings (`67 66 48`, …, `67 66 4f`) now.** Rejected for
  this slice: they change the value to 64 bits and need their own register
  kinds.
- **Put `REX` before `0x66`.** Rejected by measurement: `llvm-mc` emits
  `67 66 45 …`; moving the byte is a different stream.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 66 45 8b 44 08 08` is the `REX.RB` load at seven bytes | `llvm-mc -show-encoding`, `EXP-0088` §1 | high |
| `43`/`46`/`47` are the `BX`/`RX`/`RBX` bytes | `llvm-mc -show-encoding`, `EXP-0088` §1 | high |
| `REX` stays at byte 2, so the opcode is at byte 3 | `llvm-mc -show-encoding`, `EXP-0088` §2 | high |
| the `disp32` rows are ten bytes with `disp32` at `[48,32]` | `llvm-mc -show-encoding`, `EXP-0088` §1 | high |
| `%r12d` works as a base and as an index under the two-bit windows | `llvm-mc`, `EXP-0088` §3 | high |
| the twenty byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0088` §1 | high |

## Review triggers

- A `0x67 66` row with `REX.W` is attempted (`67 66 48`, `67 66 4c`,
  `67 66 4d`, `67 66 4f`).
- A symbol or relocation in an `addr32` displacement is requested.
- The no-base indexed shape or the `moffs` form is attempted with `0x67 66`.
- A `0x67 66` row with a 64-bit address register is proposed.
- An EVEX or VEX row is proposed with an address-size prefix.
