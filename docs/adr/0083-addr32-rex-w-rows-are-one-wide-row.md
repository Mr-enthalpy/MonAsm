# ADR-0083: the `0x67` `REX.W` rows are one wide row per shape

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P60` (the `0x67` + `REX.W` `movq` on the 32-bit indexed address
  shape, both directions at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement offsets move to `[40,8]`/`[40,32]` on the
  `REX.W` rows too), `EC-06` (`REX.W` is fixed by the template while `R`/`X`/`B`
  stay operand fields on the same byte), `EC-08` (the `0x67` `REX.W` sibling is
  one wide row, not a window family), `EC-37` (the index is `[9,1]`+`[35,3]` on
  the 32-bit address shape at 64-bit value width) and `EC-38` (the
  `REX`-carrying `addr32` row keeps four-bit register slots)

## Context

`ADR-0081` and `ADR-0082` built the 32-bit value rows behind `0x67` as window
families because their templates carry no `REX` byte: a low register cannot
write a bit that has no byte to live in, so each fixed-bit combination became
its own row. The 16-bit and 32-bit families follow the same rule.

The 64-bit value rows are different, and the existing `0.1.0`-era rows already
show it: `x86:mov/r64-base-index-disp8/legacy` is `48 8b 44 00 00` with the
value register at `[2,1]`+`[19,3]`, the base at `[0,1]`+`[24,3]` and the index
at `[1,1]`+`[27,3]`. `REX.W` forces the prefix byte to exist, so `R`, `X` and
`B` are operand fields in a byte the template already fixes; the form cannot
change length or prefix presence when it reads them. `EXP-0085` measures the
same shape with `0x67` in front:

1. **`0x67` then `REX = 48` is the low-register row.** `movq 8(%eax,%ecx,1),
   %rax` is `67 48 8b 44 08 08`: six bytes, `0x67` at byte 0, `REX.W` at
   byte 1, opcode at byte 2, `ModRM = 44` at byte 3, `SIB = 08` at byte 4 and
   `disp8` at byte 5.
2. **The same row writes `R`, `X` and `B` from the operands.**
   `movq 8(%r8d,%r9d,1), %r8` is `67 4f 8b 44 08 08` (`REX = 4f`),
   `movq 8(%r12d,%ecx,1), %rax` is `67 49 8b 44 0c 08` (`REX.B`),
   `movq 8(%eax,%r12d,1), %rax` is `67 4a 8b 44 20 08` (`REX.X`) and
   `movq 8(%eax,%ecx,1), %r8` is `67 4c 8b 44 08 08` (`REX.R`). All four are
   six bytes with the same geometry; no byte is added or removed.
3. **The address registers are 32-bit even though the value is 64-bit.**
   `%r12d` is a legal base (`67 49 8b 44 0c 08`) and a legal index
   (`67 4a 8b 44 20 08`), `%ebp` is a legal base (`67 48 8b 44 0d 08`) and
   `%esp` as an index is rejected by `llvm-mc`, exactly as on the 32-bit value
   rows. The value register is `%rax`–`%r15`.
4. **The `disp32` rows are nine bytes.** `movq 200(%eax,%ecx,1), %rax` is
   `67 48 8b 84 08 c8 00 00 00` with the four displacement bytes at
   `[40,32]`.

## Decision

1. **`0.56.0` appends four rows: two directions × two displacement widths.**
   Each row is the `0.54.0` shape with `REX.W` set in the template and the
   value slot widened to a four-bit register field.

   | Direction | Displacement | `form_id` | Template | Length |
   |---|---|---|---|---|
   | load | `disp8` | `x86:mov/r64-addr32-base-index-disp8/legacy` | `67 48 8b 44 00 00` | 6 |
   | store | `disp8` | `x86:mov/addr32-base-index-disp8-r64/legacy` | `67 48 89 44 00 00` | 6 |
   | load | `disp32` | `x86:mov/r64-addr32-base-index-disp32/legacy` | `67 48 8b 84 00 00 00 00 00` | 9 |
   | store | `disp32` | `x86:mov/addr32-base-index-disp32-r64/legacy` | `67 48 89 84 00 00 00 00 00` | 9 |

2. **The geometry is the `0.54.0` geometry.** `0x67` is byte 0 and `REX`
   byte 1, so the opcode is byte 2, `ModRM` byte 3 and `SIB` byte 4: value
   register `[10,1]`+`[27,3]`, base `[8,1]`+`[32,3]`, index `[9,1]`+`[35,3]`,
   scale `[38,2]` and displacement `[40,8]`/`[40,32]`.
3. **`REX.W` is template content, not an operand field.** Bit `[11,1]` is `1`
   in every row above; `R`/`X`/`B` remain placements of the value, base and
   index slots. A low register writes `0` into its bit and a high register
   writes `1`; neither changes the row, the length or the prefix order.
4. **The operand kinds follow the two widths.** The value is
   `x86.gpr64`/`r64`; the base is `x86.gpr32`/`rm32` and the index is
   `x86.gpr32`/`sib_index32` with `4` excluded (the `%esp` index), because
   `0x67` selects 32-bit address registers. A 64-bit base is
   `E-OPERAND-001`, a value past four bits is `E-OPERAND-004`, and scale `4`
   is `E-RANGE-001`.
5. **No schema, loader or materializer change.** The wide `r64` rows already
   ship; this slice adds four templates with the prefix and moves the bit
   offsets one byte later.

## Consequences

- `0.56.0` is a 449-form document that byte-reproduces every `0.55.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P60-gpr64-mov-index-addr32-rex-w` has twelve
  instructions: the four rows plus eight corners (`REX.RBX` with `%r8`,
  `%r12` on all three operands, `%r13` on all three, `%ebp` as a base,
  `%r12d` as an index, `%r12d` as a base, the x8 scale and a `%r15`/`%r15d`/
  `%ebp` store). Its `expected.bin` comes from `llvm-mc` + `llvm-objcopy`,
  never from the materializer.
- Negatives pin the version boundary in both directions, a missing index, a
  64-bit base, the scale end, the `%esp` index and the two four-bit field
  ends.
- `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC`
  row is added or renumbered.

## Alternatives rejected

- **Split the `REX.W` row into eight fixed-bit windows like the 32-bit value
  rows.** Rejected: `REX.W` already forces the `REX` byte, so the window split
  would multiply rows without moving a byte; a low and a high register are the
  same form with a different field value (`EC-06`, `EC-38`).
- **Use `x86.gpr64` for the base and index because the value is 64-bit.**
  Rejected by measurement: with `0x67` the address registers are `%eax`-sized
  (`67 48 8b 44 0c 08` names `%esp`), so a 64-bit base would encode different
  registers.
- **Add the `0x67` `movq` rows with two displacement widths that share the
  `disp8` template.** Rejected: the displacement width is part of the form
  (`EC-02`), so `disp8` and `disp32` are separate rows.
- **Add a symbol in the displacement now.** A relocation changes the field's
  meaning (`03_fixup_model.md`), and no `addr32` fixup row exists.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 48 8b 44 08 08` is the low-register `movq` load at six bytes | `llvm-mc -show-encoding`, `EXP-0085` §1 | high |
| `REX = 4f`/`49`/`4a`/`4c` name the same row with different registers | `llvm-mc -show-encoding`, `EXP-0085` §1 | high |
| `%r12d` works as base and index; `%esp` as an index is rejected | `llvm-mc`, `EXP-0085` §3 | high |
| the `disp32` rows are nine bytes with `disp32` at `[40,32]` | `llvm-mc -show-encoding`, `EXP-0085` §1 | high |
| the twelve byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0085` §1 | high |

## Review triggers

- A `0x67` row with a 64-bit address register is proposed.
- A symbol or relocation in an `addr32` displacement is requested.
- The no-base indexed shape or the `moffs` form is attempted with `0x67`.
- An EVEX or VEX row is proposed with an address-size prefix.
- A plan asks for `movq` with `0x67` and a 16-bit value or address width.
