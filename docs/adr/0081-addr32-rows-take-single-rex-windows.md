# ADR-0081: the `0x67` rows take the single `REX` windows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P58` (the `0x67` + one-`REX`-bit window on the 32-bit indexed
  `mov`, both directions at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement axis reaches `[40,8]`/`[40,32]` once both
  prefixes are present), `EC-06` (the `REX` byte follows `0x67` and each single
  bit extends one operand), `EC-08` (the `0x67`+`REX` windows are now rows, and
  the prefix order is fixed), `EC-37` (the index's fourth bit is `REX.X` at
  `[9,1]`) and `EC-38` (the `addr32` row splits into three single-bit value
  windows)

## Context

`ADR-0080` deferred the `0x67`+`REX` windows because they are new forms: the
address-size byte comes first and the `REX` byte second, so the geometry is not
the `0.53.0` geometry. `EXP-0083` measures the three single-bit windows and four
facts come out:

1. **`0x67` is byte 0 and `REX` is byte 1.** `movl 8(%eax,%ecx,1), %r8d` is
   `67 44 8b 44 08 08`: `0x67` at byte 0, `REX = 44` at byte 1, opcode at
   byte 2, `ModRM = 44` at byte 3, `SIB = 08` at byte 4 and `disp8` at byte 5.
   The two prefixes push the opcode two bytes later than the `0.53.0` rows.
2. **Each single bit extends exactly one operand.** `REX.R` (`44`) extends the
   value register: `8(%eax,%ecx,1), %r8d` is `67 44 8b 44 08 08`. `REX.B`
   (`41`) extends the base: `8(%r8d,%ecx,1), %eax` is `67 41 8b 44 08 08`.
   `REX.X` (`42`) extends the index: `8(%eax,%r9d,1), %eax` is
   `67 42 8b 44 08 08`. The other two operands stay three-bit fields.
3. **`%r12d` is legal on both memory operands, `%esp` is not an index.**
   `8(%r12d,%ecx,1), %eax` is `67 41 8b 44 0c 08` (`SIB.base = 100`) and
   `8(%eax,%r12d,1), %eax` is `67 42 8b 44 20 08` (`SIB.index = 100` with
   `REX.X = 1`). `llvm-mc` still rejects `8(%r8d,%esp,1)`.
4. **The extended slot excludes `0`–`7`.** A low value on the extended operand
   cannot be written by this row: `8(%eax,%ecx,1), %eax` is the `0.53.0` row
   (`67 8b 44 08 08`). The `0x67`+`REX` row is the next window, so a low value
   is `E-RANGE-004` and a value past three bits on a slot the row keeps low is
   `E-OPERAND-004`.

## Decision

1. **`0.54.0` appends twelve rows: three `REX` bits × two directions × two
   displacement widths.** Each row is the `0.53.0` shape with one `REX` byte
   between `0x67` and the opcode.

   | Direction | `REX` | Displacement | `form_id` | Template | Length |
   |---|---|---|---|---|---|
   | load | `R` | `disp8` | `x86:mov/r32-ext-addr32-base-index-disp8/legacy` | `67 44 8b 44 00 00` | 6 |
   | store | `R` | `disp8` | `x86:mov/addr32-base-index-disp8-r32-ext/legacy` | `67 44 89 44 00 00` | 6 |
   | load | `R` | `disp32` | `x86:mov/r32-ext-addr32-base-index-disp32/legacy` | `67 44 8b 84 00 00 00 00 00` | 9 |
   | store | `R` | `disp32` | `x86:mov/addr32-base-index-disp32-r32-ext/legacy` | `67 44 89 84 00 00 00 00 00` | 9 |
   | load | `B` | `disp8` | `x86:mov/r32-addr32-base-ext-index-disp8/legacy` | `67 41 8b 44 00 00` | 6 |
   | store | `B` | `disp8` | `x86:mov/addr32-base-ext-index-disp8-r32/legacy` | `67 41 89 44 00 00` | 6 |
   | load | `B` | `disp32` | `x86:mov/r32-addr32-base-ext-index-disp32/legacy` | `67 41 8b 84 00 00 00 00 00` | 9 |
   | store | `B` | `disp32` | `x86:mov/addr32-base-ext-index-disp32-r32/legacy` | `67 41 89 84 00 00 00 00 00` | 9 |
   | load | `X` | `disp8` | `x86:mov/r32-addr32-base-index-ext-disp8/legacy` | `67 42 8b 44 00 00` | 6 |
   | store | `X` | `disp8` | `x86:mov/addr32-base-index-ext-disp8-r32/legacy` | `67 42 89 44 00 00` | 6 |
   | load | `X` | `disp32` | `x86:mov/r32-addr32-base-index-ext-disp32/legacy` | `67 42 8b 84 00 00 00 00 00` | 9 |
   | store | `X` | `disp32` | `x86:mov/addr32-base-index-ext-disp32-r32/legacy` | `67 42 89 84 00 00 00 00 00` | 9 |

2. **The geometry is the `0.51.0` geometry shifted by one byte.** `0x67` is
   byte 0 and `REX` byte 1, so the opcode is byte 2, `ModRM` byte 3 and `SIB`
   byte 4: register `[27,3]`, base `[32,3]`, index `[35,3]`, scale `[38,2]` and
   displacement `[40,8]`/`[40,32]`.
3. **The `REX` bit is the most significant placement of the extended slot.** On
   the `R` row the register is `[10,1]`+`[27,3]`; on the `B` row the base is
   `[8,1]`+`[32,3]`; on the `X` row the index is `[9,1]`+`[35,3]`. Each
   extended slot excludes `0`–`7`. The two operands the row keeps low stay
   three-bit slots, and the base/index keep their `x86.gpr32` kinds
   (`rm32`/`sib_index32`).
4. **A value outside the row's window is rejected.** `0`–`7` on the extended
   operand is `E-RANGE-004`; a nonzero value in the `REX` bit itself is a
   different form, not an operand value. `8`–`15` on an operand the row keeps
   low is `E-OPERAND-004`. Nothing truncates and nothing inserts a second `REX`
   bit.
5. **No schema, loader or materializer change.** `target_type` stays a free
   string matched between plan and definition, and the existing field-width and
   exclusion checks cover the new placements.

## Consequences

- `0.54.0` is a 429-form document that byte-reproduces every `0.53.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P58-gpr32-mov-index-addr32-rex-windows` has sixteen
  instructions and 114 bytes: the twelve rows plus four corners (`%r12d` as a
  base, `%r12d` as an index, `%ebp` as a base on the `REX.R` row and the x8
  scale on the `REX.B` row). Its `expected.bin` comes from `llvm-mc` +
  `llvm-objcopy`, never from the materializer.
- Negatives pin the version boundary in both directions, a missing index, the
  scale field's end, the three extended windows' floors and the two
  three-bit field ends.
- `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC`
  row is added or renumbered.

## Alternatives rejected

- **One row that accepts both low and extended values and sets a `REX` bit when
  it sees a high register.** Rejected: the row and the instruction length would
  be chosen from an operand value (`INV-02`, `INV-04`), and `67 8b 44 08 08`
  and `67 44 8b 44 08 08` are different instructions.
- **Put `REX` before `0x67`.** Rejected by measurement: `llvm-mc` emits
  `67 47 8b ...`, and the prefix order is architectural, not a byte order the
  encoder may pick.
- **Fold the `addr32` and 64-bit `REX` rows into one family.** Rejected: the
  same `REX` byte names different register sets (`%r8d` vs `%r8`), so the
  address-size byte is part of the form (`ADR-0080`).
- **Add the `REX.BX`, `REX.RB` and `REX.RBX` `addr32` windows now.** They are
  different forms with two fixed bits; each needs its own row, and mixing them
  into this slice would triple the table.
- **Add a symbol in the displacement now.** A relocation changes the field's
  meaning (`03_fixup_model.md`), and no `addr32` fixup row exists.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 44 8b 44 08 08` is the `REX.R` load at six bytes | `llvm-mc -show-encoding`, `EXP-0083` §1 | high |
| `0x67`, `REX`, opcode, `ModRM`, `SIB`, `disp8` occupy bytes 0–5 | `llvm-mc -show-encoding`, `EXP-0083` §2 | high |
| `REX.R`/`REX.B`/`REX.X` extend exactly the value/base/index operand | `llvm-mc -show-encoding`, `EXP-0083` §1 | high |
| `%r12d` is legal on both memory operands; `%esp` is still rejected as an index | `llvm-mc`, `EXP-0083` §3 | high |
| the `disp32` rows are nine bytes with `disp32` at `[40,32]` | `llvm-mc -show-encoding`, `EXP-0083` §1 | high |
| the sixteen byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0083` §1 | high |

## Review triggers

- An `0x67` row with two fixed `REX` bits is attempted (`67 43`, `67 45`,
  `67 46`, `67 47`).
- A symbol or relocation in an `addr32` displacement is requested.
- The no-base indexed shape or the `moffs` form is attempted with `0x67`.
- An EVEX or VEX row is proposed with an address-size prefix.
- `%r12d`–`%r15d` as base or index is requested together with a second `REX`
  bit.
