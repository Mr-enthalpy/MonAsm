# ADR-0085: the `0x67 66` rows take the three single-`REX` windows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P62` (the three single-`REX` windows on the `0x67 66` `movw`
  rows, both directions at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement offsets move to `[48,8]`/`[48,32]` once
  the `REX` byte exists), `EC-06` (a `REX` byte at byte 2 carries one fixed
  extension bit and the other two stay operand fields), `EC-07` (the operand
  size prefix stays `0x66` at byte 1, before `REX`), `EC-08` (the `0x67 66`
  family gains its first `REX` windows), `EC-36` (the prefix order is `0x67`,
  `0x66`, `REX` before the opcode), `EC-37` (an extended index slot excludes
  `0`–`7`) and `EC-38` (the `addr32` 16-bit family reaches `%r8w`–`%r15w` and
  `%r8d`–`%r15d` one bit at a time)

## Context

`0.57.0` added the bare `0x67 66` pair: no `REX` byte, every register slot
three bits. The register file is wider than three bits, and `EXP-0087` measures
what a single `REX` bit costs:

1. **The `REX` byte sits at position 2.** `movw 8(%eax,%ecx,1), %r8w` is
   `67 66 44 8b 44 08 08`: seven bytes, `0x67` at byte 0, `0x66` at byte 1,
   `REX = 44` (`R`) at byte 2, the opcode at byte 3, `ModRM = 44` at byte 4,
   `SIB = 08` at byte 5 and `disp8` at byte 6.
2. **The two legacy prefixes keep their order.** `0x66` stays at byte 1, so
   the prefix order is `0x67`, `0x66`, `REX`. Only the fields after the new
   byte move: value `[35,3]`, base `[40,3]`, index `[43,3]`, scale `[46,2]`,
   displacement `[48,8]`/`[48,32]`.
3. **One bit opens one window each.** `REX.R` widens the value
   (`67 66 44 8b …`), `REX.B` the base (`67 66 41 8b 44 08 08`) and `REX.X`
   the index (`67 66 42 8b 44 08 08`). Each other register slot stays three
   bits and still rejects `8`+.
4. **The `disp32` rows are ten bytes.** `movw 200(%eax,%ecx,1), %r8w` is
   `67 66 44 8b 84 08 c8 00 00 00` with the four displacement bytes at
   `[48,32]`.
5. **Two bits at once are a different family.** `movw 8(%r12d,%ecx,1), %r12w`
   is `67 66 45 8b 64 0c 08` (`REX.RB`), which this slice does not take.

## Decision

1. **`0.58.0` appends twelve rows: three windows × two directions × two
   displacement widths.**

   | Window | Direction | Displacement | `form_id` | Template | Length |
   |---|---|---|---|---|---|
   | `REX.R` | load | `disp8` | `x86:mov/r16-ext-addr32-base-index-disp8/legacy` | `67 66 44 8b 44 00 00` | 7 |
   | `REX.R` | store | `disp8` | `x86:mov/addr32-base-index-disp8-r16-ext/legacy` | `67 66 44 89 44 00 00` | 7 |
   | `REX.R` | load | `disp32` | `x86:mov/r16-ext-addr32-base-index-disp32/legacy` | `67 66 44 8b 84 00 00 00 00 00` | 10 |
   | `REX.R` | store | `disp32` | `x86:mov/addr32-base-index-disp32-r16-ext/legacy` | `67 66 44 89 84 00 00 00 00 00` | 10 |
   | `REX.B` | load | `disp8` | `x86:mov/r16-addr32-base-ext-index-disp8/legacy` | `67 66 41 8b 44 00 00` | 7 |
   | `REX.B` | store | `disp8` | `x86:mov/addr32-base-ext-index-disp8-r16/legacy` | `67 66 41 89 44 00 00` | 7 |
   | `REX.B` | load | `disp32` | `x86:mov/r16-addr32-base-ext-index-disp32/legacy` | `67 66 41 8b 84 00 00 00 00 00` | 10 |
   | `REX.B` | store | `disp32` | `x86:mov/addr32-base-ext-index-disp32-r16/legacy` | `67 66 41 89 84 00 00 00 00 00` | 10 |
   | `REX.X` | load | `disp8` | `x86:mov/r16-addr32-base-index-ext-disp8/legacy` | `67 66 42 8b 44 00 00` | 7 |
   | `REX.X` | store | `disp8` | `x86:mov/addr32-base-index-ext-disp8-r16/legacy` | `67 66 42 89 44 00 00` | 7 |
   | `REX.X` | load | `disp32` | `x86:mov/r16-addr32-base-index-ext-disp32/legacy` | `67 66 42 8b 84 00 00 00 00 00` | 10 |
   | `REX.X` | store | `disp32` | `x86:mov/addr32-base-index-ext-disp32-r16/legacy` | `67 66 42 89 84 00 00 00 00 00` | 10 |

2. **The fixed bit is template content; the rest are operand fields.** In the
   `REX.R` rows `R` is `1` at `[18,1]`, so the value slot at `[35,3]` excludes
   `0`–`7`. In the `REX.B` rows `B` is `1` at `[16,1]`, so the base slot at
   `[40,3]` excludes `0`–`7`. In the `REX.X` rows `X` is `1` at `[17,1]`, so
   the index slot at `[43,3]` excludes `0`–`7` (which already covers the `4`
   slot).

3. **The window still carries 32-bit address registers.** The base and index
   are `x86.gpr32`/`rm32` and `x86.gpr32`/`sib_index32`; a `REX.B` or `REX.X`
   bit names `%r8d`–`%r15d`, not `%r8`–`%r15`. The value is
   `x86.gpr16`/`r16`, so a `REX.R` bit names `%r8w`–`%r15w`.

4. **No schema, loader or materializer change.** The rows are the `0.54.0`
   single-`REX` shape with the value and address widths of `0.57.0`; the same
   `excluded` and `placements` machinery already covers both.

## Consequences

- `0.58.0` is a 465-form document that byte-reproduces every `0.57.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P62-gpr16-mov-index-addr32-rex-windows` has twelve
  instructions (the twelve rows) plus four corners (`%r15w` with `%ebp`,
  `%r15d` as a base, `%r15d` as an index and the x8 scale). Its `expected.bin`
  comes from `llvm-mc` + `llvm-objcopy`, never from the materializer.
- Negatives pin the version boundary in both directions, each window's floor
  (`N16`-style) and each three-bit field end, plus the missing index and the
  scale end.
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-36`, `EC-37` and `EC-38` are revised
  in place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Fold all seven `REX` combinations into one row.** Rejected: a `REX` bit
  that the row leaves at `0` cannot be set by an operand in this model
  (`INV-02`/`INV-07`), and the window-by-window family is how the earlier
  `mov` slices stayed reviewable.
- **Put `REX` before `0x66`.** Rejected by measurement: `llvm-mc` emits
  `67 66 44 …`, and moving the byte is a different stream.
- **Take the two-bit windows now.** Rejected for this slice: `%r12w`/`%r12d`
  is `67 66 45 …`, which fixes two bits and belongs to the next version.
- **Use `x86.gpr64` for the extended base or index.** Rejected by measurement:
  `0x67` selects 32-bit address registers; `%r8d` is the base in
  `67 66 41 8b 44 08 08`.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 66 44 8b 44 08 08` is the `REX.R` load at seven bytes | `llvm-mc -show-encoding`, `EXP-0087` §1 | high |
| `REX` is at byte 2, so the opcode is at byte 3 | `llvm-mc -show-encoding`, `EXP-0087` §2 | high |
| `REX.B` names the base and `REX.X` the index | `llvm-mc -show-encoding`, `EXP-0087` §3 | high |
| the `disp32` rows are ten bytes with `disp32` at `[48,32]` | `llvm-mc -show-encoding`, `EXP-0087` §1 | high |
| the sixteen byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0087` §1 | high |
| `%r12w` with `%r12d` needs two bits (`67 66 45 …`) | `llvm-mc`, `EXP-0087` §5 | high |

## Review triggers

- A `0x67 66` row with two or three `REX` bits is attempted.
- A symbol or relocation in an `addr32` displacement is requested.
- The no-base indexed shape or the `moffs` form is attempted with `0x67`.
- A `0x67 66` row with a 64-bit address register is proposed.
- An EVEX or VEX row is proposed with an address-size prefix.
