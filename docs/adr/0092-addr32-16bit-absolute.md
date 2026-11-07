# ADR-0092: the absolute `SIB = 25` shape behind `0x67 66` at the 16-bit value width

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P69` (the `0x67 66` absolute rows at the 16-bit value width,
  both directions, two value windows)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `[40,32]`/`[48,32]` displacement offsets now cover the
  16-bit absolute shape behind `0x67 66`), `EC-06` (the optional `REX` byte sits
  at position 2 behind the two prefixes, and only `R` is an operand bit; there
  is no `B` or `X`), `EC-07` (the 16-bit absolute shape carries `0x67` and
  `0x66`), `EC-08` (the `0x67` family gains its `0x67 66` absolute rows behind
  the `SIB = 25` constant), `EC-37` (the `SIB = 25` byte has no operand-owned
  index or scale) and `EC-38` (the 16-bit absolute rows need the bare/`R` split
  the 32-bit rows already use)

## Context

`0.64.0` reached the absolute `SIB = 25` shape behind `0x67` at the 64-bit
width (`ADR-0091`), and `0.60.0` reached the `0x67 66` no-base indexed shape
(`ADR-0087`). `0.65.0` takes the `0x67 66` absolute sibling: the same address
shape at the 16-bit value width, where the operand-size prefix precedes any
`REX` byte.

`EXP-0094` measures it with an explicit `addr32` prefix. The printer splits
that keyword onto its own line, so the instruction bytes are read from the
object file (`measure.py`):

1. **The bare rows are nine bytes.** `addr32 movw 4660, %ax` is
   `67 66 8b 04 25 34 12 00 00`: `0x67` at byte 0, `0x66` at byte 1, the opcode
   at byte 2, `ModRM = 04` at byte 3, `SIB = 25` at byte 4 and four
   displacement bytes at 5–8. `addr32 movw %ax, 4660` is
   `67 66 89 04 25 34 12 00 00`.
2. **`REX.R` shifts every field by eight bits.** `addr32 movw 4660, %r8w` is
   `67 66 44 8b 04 25 34 12 00 00`: the `REX` byte is at position 2, so the
   opcode is byte 3, `ModRM` byte 4, `SIB` byte 5 and the displacement bytes
   6–9. There is no `REX.B` or `REX.X` bit, because there is no base and no
   index.
3. **The displacement is always four bytes.** `addr32 movw 0, %ax` is
   `67 66 8b 04 25 00 00 00 00` — nine bytes at offset zero — and the signed
   ends are `67 66 8b 04 25 00 00 00 80` (`-2147483648`) and
   `67 66 8b 04 25 ff ff ff 7f` (`2147483647`).
4. **`SIB = 25` is template content.** The byte is `25` at every value; only
   `ModRM.reg` and the displacement move. `addr32 movw 4660, %r15w` is
   `67 66 44 8b 3c 25 34 12 00 00` (`ModRM = 3c`).

The neighbours (`EXP-0094` §3): `movw 4660, %ax` is
`66 8b 04 25 34 12 00 00` (the `0.28.0` absolute row, eight bytes),
`addr32 movl 4660, %eax` is `67 8b 04 25 …` and `addr32 movq 4660, %rax` is
`67 48 8b 04 25 …` (the `0.63.0` and `0.64.0` siblings),
`movw 8(,%ecx,1), %ax` is `67 66 8b 04 0d 08 00 00 00` (the `0.60.0` no-base
indexed row), `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08` (base+index),
`movabs 4660, %ax` is `66 a1 34 12 00 00 00 00 00 00` and
`addr32 movabs 4660, %ax` is `67 66 a1` plus the same eight offset bytes
(eleven total — the prefixes added bytes but did not shorten the offset, which
disagrees with a manual derivation of the `moffs` encoding, so `moffs` stays
deferred and unverified), and `addr32 movw 4660(%rip), %ax` is
`67 66 8b 05 34 12 00 00` (RIP-relative). `addr32 movw 4660, %eax` and
`addr32 movw 4660, %rax` are both rejected by `llvm-mc`
(`invalid operand for instruction`).

## Decision

1. **`0.65.0` appends four rows: two value windows × two directions.** The
   displacement is `disp32` and there is no address operand, so there is no
   width or geometry axis beyond the value window.

   | Window | Direction | `form_id` | Template | Length |
   |---|---|---|---|---|
   | none | load | `x86:mov/r16-addr32-abs32/legacy` | `67 66 8b 04 25 00 00 00 00` | 9 |
   | none | store | `x86:mov/addr32-abs32-r16/legacy` | `67 66 89 04 25 00 00 00 00` | 9 |
   | `R` | load | `x86:mov/r16-ext-addr32-abs32/legacy` | `67 66 44 8b 04 25 00 00 00 00` | 10 |
   | `R` | store | `x86:mov/addr32-abs32-r16-ext/legacy` | `67 66 44 89 04 25 00 00 00 00` | 10 |

   The template's `SIB` byte is `25` (`scale = 00`, `index = 100`,
   `base = 101`); nothing in it is operand-owned.

2. **Two geometries, one per `REX` presence.** A row without a `REX` byte has
   the value at `[27,3]` and the displacement at `[40,32]` (signed). A row that
   fixes `REX.R` at `[18,1]` inserts the `REX` byte at position 2 and moves
   every later field eight bits: value `[35,3]` and displacement `[48,32]`
   (signed).

3. **The operand sequence has no address role:** `dest` or `src`
   (`x86.gpr16`/`r16`) and `disp` (`x86.imm`/`disp32`, signed). Supplying a
   `base`, `index` or `scale`, or omitting the `disp`, is `E-OPERAND-002`.

4. **Each row's window is enforced by exclusion.** On the `R` rows the value
   slot carries `[18,1]`+`[35,3]` and excludes `0`–`7`; the bare rows keep a
   three-bit field at `[27,3]`.

5. **No schema, loader or materializer change.** The rows use the same
   `x86.gpr16`/`r16` and `x86.imm`/`disp32` slots the absolute family already
   uses; `0x67`, `0x66` and `SIB = 25` are template content.

## Consequences

- `0.65.0` is a 509-form document that byte-reproduces every `0.64.0` row.
  Its digest `sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a`
  is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P69-gpr16-mov-addr32-abs32` has ten instructions
  and 94 bytes: the four rows plus a zero displacement, `-1`, both signed
  ends, `%r15w` as the load value and `%r15w` as the store value. Its
  `expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from the
  materializer.
- Nine negatives pin the version boundary in both directions
  (`N01ef`/`N01eg`, `E-FORM-001`), a supplied base (`N02cq`,
  `E-OPERAND-002`), a missing displacement (`N02cr`, `E-OPERAND-002`), a
  32-bit operand on the `r16` row (`N02cs`, two `E-OPERAND-001`: kind and
  target type), the signed displacement end (`N03zr`, `E-RANGE-001`), both
  value-field ends (`N14ce` with sixteen on the four-bit extended slot and
  `N14cf` with eight on the bare three-bit slot, both `E-OPERAND-004`) and the
  extended window floor (`N16dg`, `E-RANGE-004`).
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in
  place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Derive these rows from the `0.64.0` rows by inserting `0x66`.** Rejected:
  the prefix shifts every later field and changes the length, so it is a
  different frozen form; the materializer may not derive one from the other
  (`INV-02`, `INV-04`).
- **One row with a free `REX.R` bit that drops the `REX` byte when zero.**
  Rejected: the `REX` byte is either in the template or absent; a byte cannot
  disappear when an operand picks the low window, and the assembler never
  emits a redundant `0x40`.
- **Model the address as a `disp` plus an implicit zero base.** Rejected:
  `SIB.index = 100`/`base = 101` is the no-register constant, not a base of
  zero; a plan that supplied a base must fail (`E-OPERAND-002`), and the
  meaning is entirely in the template.
- **Add a `disp8` variant.** Rejected by measurement: `SIB = 25` at
  `mod = 00` has no `disp8` form; zero keeps four displacement bytes.
- **Take the `moffs` form with `0x67 66` in the same slice.** Rejected: the
  offset width is unresolved (below), so it cannot be frozen.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 66 8b 04 25 34 12 00 00` is the bare absolute load at nine bytes | object bytes, `EXP-0094` §1 (printer splits `addr32`) | high |
| `67 66 44 8b 04 25 …` is the `REX.R` row at ten bytes and `SIB = 25` never changes | object bytes, `EXP-0094` §1/§4 | high |
| the displacement is four bytes at every value | object bytes, `EXP-0094` §3 | high |
| the ten byte strings decode back to `addr32 movw …` | `llvm-mc -disassemble`, `EXP-0094` §1 | high |
| the shape without `0x67`, the 32-bit/64-bit siblings, the indexed and base+index rows, `moffs` and RIP-relative are distinct | object bytes, `EXP-0094` §3 | high |
| `addr32 movw 4660, %eax`/`%rax` are rejected | `llvm-mc -show-encoding`, `EXP-0094` §3 | high |
| `0x67 66` keeps an eight-byte `moffs` offset in `llvm-mc` | object bytes, `EXP-0094` §3 | high (observed); the ISA reading is unverified |

## Review triggers

- A symbol or relocation in the `disp32` of this shape is requested.
- The `moffs` form with `0x67 66` is proposed; the measurement and a manual
  derivation disagree about the offset width, so it needs a second oracle.
- The `0x67 66` RIP-relative row is proposed.
- A 64-bit address register is proposed with `0x67`.
- APX `d5` or EVEX masking/broadcast is proposed for this family.
