# ADR-0087: the `0x67 66` rows take the no-base indexed shape

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P64` (the no-base indexed `0x67 66` `movw` rows, both
  directions, `disp32` only)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `[48,32]` displacement offset now covers a shape whose
  `disp32` is mandatory at every value, including zero), `EC-06` (the `REX`
  byte exists only when the value or the index is extended, and there is no
  `B` bit to fix), `EC-08` (the `0x67 66` family gains rows with no base role
  and the deferred list shrinks to the `REX.W` siblings, which no assembler
  emits, plus symbols, `moffs`, APX `d5`, EVEX masking and 64-bit address
  registers), `EC-37` (index `4` is a register here, not the "no index"
  constant, because `SIB.base = 101` carries the no-base meaning) and `EC-38`
  (the family reaches a shape with no base register at all)

## Context

The `0x67 66` family (`0.57.0`–`0.59.0`) has only base+index rows: `ModRM.rm`
is `100`, `SIB.base` names a register. `EXP-0089` measures the shape the
deferred list named next, and four facts come out:

1. **`SIB.base = 101` at `mod = 00` frees the base slot.** `movw 8(,%ecx,1),
   %ax` is `67 66 8b 04 0d 08 00 00 00`: `ModRM = 04` announces the `SIB`,
   `SIB = 0d` holds index `1` with `base = 101`, and the displacement is the
   last four bytes. The row has no `base` role at all.
2. **The displacement is always four bytes.** `mod = 00` with `SIB.base = 101`
   *is* the `disp32` request, so `movw (,%ecx,1), %ax` is
   `67 66 8b 04 0d 00 00 00 00` — nine bytes at offset zero, not eight and not
   a dropped slot. There is no `disp8` variant to add.
3. **`REX` exists only for `R` and `X`.** `movw 8(,%ecx,1), %r8w` is
   `67 66 44 8b 04 0d …`, `movw 8(,%r9d,1), %ax` is `67 66 42 8b 04 0d …` and
   `movw 8(,%r9d,1), %r8w` is `67 66 46 8b 04 0d …`. There is no `REX.B`
   window, because there is no base register for it to extend.
4. **Index `4` is a register on this shape.** `movw 8(,%r12d,1), %ax` is
   `67 66 42 8b 04 25 08 00 00 00`: `SIB = 25` is index `4` plus `X = 1`, and
   the "no base" meaning is carried by `SIB.base = 101`, not by the index
   field. The bare `42` row still rejects index `4` (the low three bits of
   `%r12d` are `4`, so the row's window floor excludes `0`–`7`).

The shape sits next to, but is not, three neighbours (`EXP-0089` §3):
`movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08` (base+index), `movl
8(,%r9d,1), %eax` is `67 42 8b 04 0d …` (32-bit value) and `movw 8(,%rcx,1),
%ax` is `66 8b 04 0d …` (64-bit address, no `0x67`). `%esp` as an index and a
32-bit value register are both rejected by `llvm-mc`.

The `REX.W` siblings (`67 66 48`–`67 66 4f`), still listed as deferred, are
not assembler output: `movq 8(%eax,%ecx,1), %rax` is `67 48 8b 44 08 08`, and
the only way to force a redundant `0x66` is the `data16` directive, which
`llvm-mc` emits as its *own* instruction — the object bytes are
`66 67 48 8b 44 08 08`, with the prefix before `0x67`, never the `67 66 48`
order a row would claim. So the `REX.W` item has no asm→obj oracle and is not
taken here (see `EXP-0089` §6).

## Decision

1. **`0.60.0` appends eight rows: four `REX` windows × two directions.** The
   displacement is `disp32` in every row, so there is no width axis.

   | Window | Direction | `form_id` | Template | Length |
   |---|---|---|---|---|
   | none | load | `x86:mov/r16-addr32-index-disp32/legacy` | `67 66 8b 04 05 00 00 00 00` | 9 |
   | none | store | `x86:mov/addr32-index-disp32-r16/legacy` | `67 66 89 04 05 00 00 00 00` | 9 |
   | `R` | load | `x86:mov/r16-ext-addr32-index-disp32/legacy` | `67 66 44 8b 04 05 00 00 00 00` | 10 |
   | `R` | store | `x86:mov/addr32-index-disp32-r16-ext/legacy` | `67 66 44 89 04 05 00 00 00 00` | 10 |
   | `X` | load | `x86:mov/r16-addr32-index-ext-disp32/legacy` | `67 66 42 8b 04 05 00 00 00 00` | 10 |
   | `X` | store | `x86:mov/addr32-index-ext-disp32-r16/legacy` | `67 66 42 89 04 05 00 00 00 00` | 10 |
   | `RX` | load | `x86:mov/r16-ext-addr32-index-ext-disp32/legacy` | `67 66 46 8b 04 05 00 00 00 00` | 10 |
   | `RX` | store | `x86:mov/addr32-index-ext-disp32-r16-ext/legacy` | `67 66 46 89 04 05 00 00 00 00` | 10 |

   The template's `SIB` byte is `05` (index field `0`, scale `00`, base
   `101`); the index and scale are operand-owned.

2. **Two geometries, one per `REX` presence.** A row without a `REX` byte has
   no byte 2: `0x67` at byte 0, `0x66` at byte 1, the opcode at byte 2,
   `ModRM = 04` at byte 3 and `SIB` at byte 4, with the value at `[27,3]`, the
   index at `[35,3]`, the scale at `[38,2]` and the displacement at `[40,32]`
   (signed). A row that fixes `REX.R` at `[18,1]` or `REX.X` at `[17,1]`
   inserts the `REX` byte at position 2 and moves every later field eight
   bits: value `[35,3]`, index `[43,3]`, scale `[46,2]` and displacement
   `[48,32]` (signed), exactly the `0.59.0` geometry.

3. **The operand sequence has no `base` role:** `dest` or `src`, `index`
   (`x86.gpr32`/`sib_index32`), `imm` (`x86.scale`/`scale2`) and `disp`
   (`x86.imm`/`disp32`, signed). A supplied `base` is `E-OPERAND-002`; a
   missing `index` is also `E-OPERAND-002`.

4. **Each row's window is enforced by exclusion.** On the `R`/`RX` rows the
   value slot carries `[18,1]`+`[35,3]` and excludes `0`–`7`; on the `X`/`RX`
   rows the index slot carries `[17,1]`+`[43,3]` and excludes `0`–`7`. The
   bare and `42`/`44` rows keep three-bit fields, and the index slot excludes
   `4` on the rows without `REX.X` (`E-RANGE-004`).

5. **No schema, loader or materializer change.** The rows use the same
   `x86.scale`, `x86.imm`/`disp32` and `x86.gpr32`/`sib_index32` slots the
   family already uses; `SIB.base = 101` is template content.

## Consequences

- `0.60.0` is a 489-form document that byte-reproduces every `0.59.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P64-gpr16-mov-index-addr32-no-base` has thirteen
  instructions and 125 bytes: the eight rows plus a zero displacement, a
  negative displacement, the x4 scale, `%r12d` under `REX.X` and
  `4660(,%r15d,8), %r15w`. Its `expected.bin` comes from `llvm-mc` +
  `llvm-objcopy`, never from the materializer.
- Eight negatives pin the version boundary in both directions, a missing
  index, a supplied base, the scale end, a value past its four-bit field and
  both index windows (`4` on a low row, `0` on an extended row).
- `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC`
  row is added or renumbered.

## Alternatives rejected

- **Model "no base" as an optional base operand on the existing rows.**
  Rejected: the absence changes `ModRM.rm` (`44` → `04`) and the `SIB` base
  (`101`), so it is a different form, and the materializer may not pick a
  shape from an operand (`INV-02`, `INV-04`).
- **Add a `disp8` variant.** Rejected by measurement: `SIB.base = 101` forces
  `mod = 00`, and `0(,%ecx,1)` keeps four displacement bytes.
- **Read index field `4` as "no index".** Rejected: on this shape `%r12d` is
  legal and must stay nameable; the no-base meaning is `SIB.base = 101`.
- **Take the `REX.W` siblings now.** Rejected: no assembly spelling produces
  `67 66 48 …` (`data16` emits a standalone `0x66` before `0x67`), so the
  vector would have no independent oracle.
- **Drop `0x67` because the address is absolute.** Rejected: `0x67` is the
  form; `66 8b 04 0d …` is the 64-bit-addressing row and must stay a different
  form.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 66 8b 04 0d 08 00 00 00` is the no-base low-index load at nine bytes | `llvm-mc -show-encoding`, `EXP-0089` §1 | high |
| `SIB.base = 101` forces a four-byte displacement at every value | `llvm-mc -show-encoding`, `EXP-0089` §1 (`0(,%ecx,1)`) | high |
| `44`/`42`/`46` are the `R`/`X`/`RX` windows and no `B` bit exists | `llvm-mc -show-encoding`, `EXP-0089` §2 | high |
| index `4` with `REX.X = 1` names `%r12d` (`SIB = 25`) | `llvm-mc`, `EXP-0089` §1 | high |
| the thirteen byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0089` §1 | high |
| `data16 movq …` yields `66 67 48 8b 44 08 08`, not `67 66 48 …` | `llvm-mc -filetype=obj` + `llvm-objcopy`, `EXP-0089` §6 | high |

## Review triggers

- A symbol or relocation in the `disp32` of this shape is requested.
- A no-base shape with a `disp8` is proposed.
- A `REX.W` no-base row is proposed (`67 66 48`/`67 66 4a`/`67 66 4e`).
- The absolute `SIB = 25` shape with `0x67`, or the `moffs` form, is attempted.
- A 64-bit address register is proposed with `0x67`.
