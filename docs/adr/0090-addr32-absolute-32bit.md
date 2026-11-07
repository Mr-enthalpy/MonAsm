# ADR-0090: the absolute `SIB = 25` shape behind `0x67`

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P67` (the `0x67` absolute rows at the 32-bit value width,
  both directions, two value windows)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `[32,32]`/`[40,32]` displacement offsets now cover the
  absolute shape behind `0x67`), `EC-06` (the `REX` byte sits at position 1
  and only `R` is an operand bit; there is no `B` or `X`), `EC-07` (the
  32-bit absolute shape carries `0x67` and no `0x66`), `EC-08` (the `0x67`
  family gains its absolute rows behind the `SIB = 25` constant), `EC-37`
  (the `SIB = 25` byte has no operand-owned index or scale) and `EC-38`
  (the absolute row's only register window is the value's fourth bit)

## Context

`0.26.0` gave the GPR `mov` rows an absolute-address shape: `ModRM = 04`
announces a `SIB` byte, `SIB = 25` (`index = 100`, `base = 101`) names neither
a register nor a base, and the `disp32` is the whole address (`ADR-0053`).
`0.62.0` reaches the no-base indexed shape at three value widths but leaves
the absolute `SIB = 25` shape without `0x67`.

`EXP-0092` measures the absolute shape with an explicit `addr32` prefix. The
printer splits that keyword onto its own line, so the instruction bytes are
read from the object file (`measure.py`):

1. **The bare row is eight bytes.** `addr32 movl 4660, %eax` is
   `67 8b 04 25 34 12 00 00`: `0x67` at byte 0, the opcode at byte 1,
   `ModRM = 04` at byte 2, `SIB = 25` at byte 3 and four displacement bytes at
   4–7. There is no `base`, `index` or `scale` role.
2. **`REX.R` shifts every field by eight bits.** `addr32 movl 4660, %r8d` is
   `67 44 8b 04 25 34 12 00 00`: `REX` sits at byte 1, so the opcode is byte
   2, `ModRM` byte 3, `SIB` byte 4 and the displacement bytes 5–8. There is no
   `REX.B` or `REX.X` bit, because there is no base and no index.
3. **The displacement is always four bytes.** `addr32 movl 0, %eax` is
   `67 8b 04 25 00 00 00 00` — eight bytes at offset zero — and the signed
   ends are `67 8b 04 25 00 00 00 80` (`-2147483648`) and
   `67 8b 04 25 ff ff ff 7f` (`2147483647`).
4. **`SIB = 25` is template content.** The byte is `25` at every value; only
   `ModRM.reg` and the displacement move. `addr32 movl 4660, %r15d` is
   `67 44 8b 3c 25 34 12 00 00` (`ModRM = 3c`).

The neighbours (`EXP-0092` §3): `movl 4660, %eax` is `8b 04 25 34 12 00 00`
(the `0.26.0` row, seven bytes), `addr32 movq 4660, %rax` is
`67 48 8b 04 25 34 12 00 00` and `addr32 movw 4660, %ax` is
`67 66 8b 04 25 34 12 00 00` (the 64-bit and 16-bit siblings),
`movl 8(,%ecx,1), %eax` is `67 8b 04 0d …` (the `0.61.0` no-base indexed
row) and `movl 8(%eax,%ecx,1), %eax` is `67 8b 44 08 08` (base+index).
`movabs 4660, %eax` is `a1 34 12 00 00 00 00 00 00` and `movabs 4660, %rax`
is `48 a1 34 12 00 00 00 00 00 00` (the `moffs` forms), and
`addr32 movl 4660(%rip), %eax` is `67 8b 05 34 12 00 00` (RIP-relative, not
this shape). `addr32 movl 4660, %rax` and `addr32 movl 4660, %ax` are both
rejected by `llvm-mc` (`invalid operand for instruction`).

## Decision

1. **`0.63.0` appends four rows: two value windows × two directions.** The
   displacement is `disp32` and there is no address operand, so there is no
   width or geometry axis beyond the value window.

   | Window | Direction | `form_id` | Template | Length |
   |---|---|---|---|---|
   | none | load | `x86:mov/r32-addr32-abs32/legacy` | `67 8b 04 25 00 00 00 00` | 8 |
   | none | store | `x86:mov/addr32-abs32-r32/legacy` | `67 89 04 25 00 00 00 00` | 8 |
   | `R` | load | `x86:mov/r32-ext-addr32-abs32/legacy` | `67 44 8b 04 25 00 00 00 00` | 9 |
   | `R` | store | `x86:mov/addr32-abs32-r32-ext/legacy` | `67 44 89 04 25 00 00 00 00` | 9 |

   The template's `SIB` byte is `25` (`scale = 00`, `index = 100`,
   `base = 101`); nothing in it is operand-owned.

2. **Two geometries, one per `REX` presence.** A row without a `REX` byte has
   `0x67` at byte 0, the opcode at byte 1, `ModRM = 04` at byte 2 and `SIB` at
   byte 3, with the value at `[19,3]` and the displacement at `[32,32]`
   (signed). A row that fixes `REX.R` at `[10,1]` inserts the `REX` byte at
   position 1 and moves every later field eight bits: value `[27,3]` and
   displacement `[40,32]` (signed).

3. **The operand sequence has no address role:** `dest` or `src`
   (`x86.gpr32`/`r32`) and `disp` (`x86.imm`/`disp32`, signed). Supplying a
   `base`, `index` or `scale` is `E-OPERAND-002`.

4. **Each row's window is enforced by exclusion.** On the `R` rows the value
   slot carries `[10,1]`+`[27,3]` and excludes `0`–`7`; the bare rows keep a
   three-bit field at `[19,3]`.

5. **No schema, loader or materializer change.** The rows use the same
   `x86.gpr32`/`r32` and `x86.imm`/`disp32` slots the absolute family already
   uses; `0x67` and `SIB = 25` are template content.

## Consequences

- `0.63.0` is a 503-form document that byte-reproduces every `0.62.0` row.
  Its digest is recorded in `07_definition_format.md` §8 and in the fixture
  oracle.
- The positive fixture `X86-P67-gpr32-mov-addr32-abs32` has ten instructions
  and 84 bytes: the four rows plus a zero displacement, `-1`, both signed
  ends, `%r15d` as the load value and `%r15d` as the store value. Its
  `expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from the
  materializer.
- Seven negatives pin the version boundary in both directions
  (`N01eb`/`N01ec`, `E-FORM-001`), a supplied base operand (`N02cm`,
  `E-OPERAND-002`), the signed 32-bit displacement end (`N03zp`,
  `E-RANGE-001`), both value-field ends (`N14cb` with sixteen on the four-bit
  extended slot and `N14cc` with eight on the bare three-bit slot, both
  `E-OPERAND-004`) and the extended window floor (`N16df`, `E-RANGE-004`).
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in
  place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Derive these rows from the `0.26.0` absolute rows by prepending `0x67`.**
  Rejected: the prefix shifts every later field and changes the length, so it
  is a different frozen form; the materializer may not derive one from the
  other (`INV-02`, `INV-04`).
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
- **Take the 64-bit and 16-bit siblings in the same slice.** Deferred to
  their own slices: the `REX.W` row moves `R` into the mandatory byte and the
  `0x67 66` row adds a third prefix, so each needs its own counterexamples.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 8b 04 25 34 12 00 00` is the bare absolute load at eight bytes | object bytes, `EXP-0092` §1 (printer splits `addr32`) | high |
| `67 44 8b 04 25 …` is the `REX.R` row and `SIB = 25` never changes | object bytes, `EXP-0092` §1/§4 | high |
| the displacement is four bytes at every value | object bytes, `EXP-0092` §3 | high |
| the ten byte strings decode back to `addr32 movl …` | `llvm-mc -disassemble`, `EXP-0092` §1 | high |
| the shape without `0x67`, the 64-bit/16-bit siblings, the indexed rows, `moffs` and RIP-relative are distinct | object bytes, `EXP-0092` §3 | high |
| `addr32 movl 4660, %rax`/`%ax` are rejected | `llvm-mc -show-encoding`, `EXP-0092` §3 | high |

## Review triggers

- A symbol or relocation in the `disp32` of this shape is requested.
- The `REX.W` (`67 48`) or `0x67 66` absolute sibling is proposed.
- The `moffs` form with `0x67` is attempted.
- A 64-bit address register is proposed with `0x67`.
- The RIP-relative `67 8b 05` row is proposed.
