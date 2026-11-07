# ADR-0088: the no-base indexed shape reaches the 32-bit value width

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P65` (the no-base indexed `movl` rows, both directions,
  `disp32` only, four `REX` windows)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `[32,32]`/`[40,32]` displacement offsets now cover the
  `movl` shape whose `disp32` is mandatory at every value), `EC-06` (the `REX`
  byte exists only when the value or the index is extended; there is no `B`
  bit), `EC-07` (the 32-bit width of this shape carries `0x67` and no `0x66`),
  `EC-08` (the `0x67` family gains its 32-bit value rows and the deferred list
  keeps the 64-bit `REX.W` rows, symbols, absolute `SIB = 25`, `moffs`, APX
  `d5`, EVEX masking and 64-bit address registers), `EC-37` (index `4` with
  `REX.X = 1` names `%r12d` on the 32-bit rows too) and `EC-38` (the family
  reaches the 32-bit value width with no base register)

## Context

`0.60.0` (`ADR-0087`) gave the `0x67 66` `movw` rows a no-base indexed shape:
`mod = 00` with `SIB.base = 101` frees the base slot and forces a `disp32`.
`EXP-0090` measures the same shape at the 32-bit value width, where the
`0x66` prefix disappears and with it one of the two geometries:

1. **The bare row is eight bytes.** `movl 8(,%ecx,1), %eax` is
   `67 8b 04 0d 08 00 00 00`: `0x67` at byte 0, the opcode at byte 1,
   `ModRM = 04` at byte 2, `SIB = 0d` at byte 3 and four displacement bytes at
   4–7. The row has no `base` role.
2. **`REX` shifts every field by eight bits.** `movl 8(,%ecx,1), %r8d` is
   `67 44 8b 04 0d …`, `movl 8(,%r9d,1), %eax` is `67 42 8b 04 0d …` and
   `movl 8(,%r9d,1), %r8d` is `67 46 8b 04 0d …`: `REX` sits at byte 1, so the
   opcode moves to byte 2, `ModRM` to byte 3, `SIB` to byte 4 and the
   displacement to bytes 5–8. There is no `REX.B` bit, because there is no
   base register to extend.
3. **The displacement is always four bytes.** `movl 0(,%ecx,1), %eax` is
   `67 8b 04 0d 00 00 00 00` — eight bytes at offset zero, not seven and not a
   dropped slot.
4. **Index `4` is a register on this shape.** `movl 8(,%r12d,1), %eax` is
   `67 42 8b 04 25 08 00 00 00`: `SIB = 25` is index `4` with `X = 1`, and the
   no-base meaning is `SIB.base = 101`. The bare and `44` rows still reject
   index `4`; the `42`/`46` rows have a window floor of `8`.

The neighbours (`EXP-0090` §3): `movl 8(%eax,%ecx,1), %eax` is
`67 8b 44 08 08` (base+index, five bytes), `movw 8(,%ecx,1), %ax` is
`67 66 8b 04 0d …` (the `0.60.0` sibling), `movl 8(,%rcx,1), %eax` is
`8b 04 0d …` (64-bit addressing, no `0x67`), `movl 4660, %eax` is
`8b 04 25 34 12 00 00` (absolute `SIB = 25`, no `0x67`) and
`movq 8(,%ecx,1), %rax` is `67 48 8b 04 0d …` (the `REX.W` value width,
deferred). `%esp` as an index and `%ax` with `movl` are both rejected by
`llvm-mc`.

## Decision

1. **`0.61.0` appends eight rows: four `REX` windows × two directions.** The
   displacement is `disp32` in every row, so there is no width axis.

   | Window | Direction | `form_id` | Template | Length |
   |---|---|---|---|---|
   | none | load | `x86:mov/r32-addr32-index-disp32/legacy` | `67 8b 04 05 00 00 00 00` | 8 |
   | none | store | `x86:mov/addr32-index-disp32-r32/legacy` | `67 89 04 05 00 00 00 00` | 8 |
   | `R` | load | `x86:mov/r32-ext-addr32-index-disp32/legacy` | `67 44 8b 04 05 00 00 00 00` | 9 |
   | `R` | store | `x86:mov/addr32-index-disp32-r32-ext/legacy` | `67 44 89 04 05 00 00 00 00` | 9 |
   | `X` | load | `x86:mov/r32-addr32-index-ext-disp32/legacy` | `67 42 8b 04 05 00 00 00 00` | 9 |
   | `X` | store | `x86:mov/addr32-index-ext-disp32-r32/legacy` | `67 42 89 04 05 00 00 00 00` | 9 |
   | `RX` | load | `x86:mov/r32-ext-addr32-index-ext-disp32/legacy` | `67 46 8b 04 05 00 00 00 00` | 9 |
   | `RX` | store | `x86:mov/addr32-index-ext-disp32-r32-ext/legacy` | `67 46 89 04 05 00 00 00 00` | 9 |

   The template's `SIB` byte is `05` (index field `0`, scale `00`, base
   `101`); the index and scale are operand-owned.

2. **Two geometries, one per `REX` presence.** A row without a `REX` byte has
   `0x67` at byte 0, the opcode at byte 1, `ModRM = 04` at byte 2 and `SIB` at
   byte 3, with the value at `[19,3]`, the index at `[27,3]`, the scale at
   `[30,2]` and the displacement at `[32,32]` (signed). A row that fixes
   `REX.R` at `[10,1]` or `REX.X` at `[9,1]` inserts the `REX` byte at
   position 1 and moves every later field eight bits: value `[27,3]`, index
   `[35,3]`, scale `[38,2]` and displacement `[40,32]` (signed).

3. **The operand sequence has no `base` role:** `dest` or `src`, `index`
   (`x86.gpr32`/`sib_index32`), `imm` (`x86.scale`/`scale2`) and `disp`
   (`x86.imm`/`disp32`, signed). A supplied `base` is `E-OPERAND-002`; a
   missing `index` is also `E-OPERAND-002`.

4. **Each row's window is enforced by exclusion.** On the `R`/`RX` rows the
   value slot carries `[10,1]`+`[27,3]` and excludes `0`–`7`; on the `X`/`RX`
   rows the index slot carries `[9,1]`+`[35,3]` and excludes `0`–`7`. The bare
   and `44` rows keep three-bit fields, and the index slot excludes `4` on the
   rows without `REX.X` (`E-RANGE-004`).

5. **No schema, loader or materializer change.** The rows use the same
   `x86.scale`, `x86.imm`/`disp32` and `x86.gpr32`/`sib_index32` slots the
   family already uses; `SIB.base = 101` is template content.

## Consequences

- `0.61.0` is a 497-form document that byte-reproduces every `0.60.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P65-gpr32-mov-index-addr32-no-base` has thirteen
  instructions and 112 bytes: the eight rows plus a zero displacement, a
  negative displacement, the x4 scale, `%r12d` under `REX.X` and
  `4660(,%r15d,8), %r15d`. Its `expected.bin` comes from `llvm-mc` +
  `llvm-objcopy`, never from the materializer.
- Eight negatives pin the version boundary in both directions, a missing
  index, a supplied base, the scale end, a value past its four-bit field and
  both index windows (`4` on a low row, `0` on an extended row).
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in
  place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Model the 32-bit rows as the `0.60.0` rows without the `0x66`.** Rejected:
  the absent prefix changes every later field offset and the length, so it is
  a different form; the materializer may not derive one from the other
  (`INV-02`, `INV-04`).
- **One row with a free `REX.R` bit and no `REX` byte when it is zero.**
  Rejected: the `REX` byte is either present in the template or absent; a
  single byte cannot disappear when an operand picks the low window, and the
  assembler never emits a redundant `0x40`.
- **Add a `disp8` variant.** Rejected by measurement: `SIB.base = 101` forces
  `mod = 00`, and zero keeps four displacement bytes.
- **Read index field `4` as "no index".** Rejected: `%r12d` is legal on the
  `X`/`RX` rows; the no-base meaning is `SIB.base = 101`.
- **Take the `REX.W` `movq` rows in the same slice.** Deferred to its own
  slice: `REX.W` is mandatory there, so `R` and `X` are free bits inside a byte
  that always exists, which is a different row decomposition and needs its own
  counterexamples.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 8b 04 0d 08 00 00 00` is the no-base low-index load at eight bytes | `llvm-mc -show-encoding`, `EXP-0090` §1 | high |
| `SIB.base = 101` forces a four-byte displacement at every value | `llvm-mc -show-encoding`, `EXP-0090` §1 (`0(,%ecx,1)`) | high |
| `44`/`42`/`46` are the `R`/`X`/`RX` windows and no `B` bit exists | `llvm-mc -show-encoding`, `EXP-0090` §2 | high |
| index `4` with `REX.X = 1` names `%r12d` (`SIB = 25`) | `llvm-mc`, `EXP-0090` §1 | high |
| the thirteen byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0090` §1 | high |
| the 64-bit-addressing and absolute forms omit `0x67` | `llvm-mc -show-encoding`, `EXP-0090` §3 | high |

## Review triggers

- A symbol or relocation in the `disp32` of this shape is requested.
- The `REX.W` no-base `movq` shape is proposed (`67 48`/`67 4c`/`67 4a`/`67 4e`).
- A no-base shape with a `disp8` is proposed.
- The absolute `SIB = 25` shape with `0x67`, or the `moffs` form, is attempted.
- A 64-bit address register is proposed with `0x67`.
