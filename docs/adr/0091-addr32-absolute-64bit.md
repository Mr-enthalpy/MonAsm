# ADR-0091: the absolute `SIB = 25` shape behind `0x67` at the 64-bit value width

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P68` (the `0x67` absolute rows at the 64-bit value width, both
  directions)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `[40,32]` displacement offset now covers the 64-bit
  absolute shape behind `0x67`), `EC-06` (the mandatory `REX` byte sits at
  position 1 and only `R` is operand-owned; there is no `B` or `X`), `EC-07`
  (the 64-bit absolute shape carries `0x67` and `REX.W`, and no `0x66`),
  `EC-08` (the `0x67` family gains its 64-bit absolute rows behind the
  `SIB = 25` constant), `EC-37` (the `SIB = 25` byte has no operand-owned index
  or scale) and `EC-38` (the mandatory `REX` byte makes `R` a free bit, so one
  row per direction covers the whole value window)

## Context

`0.63.0` gave the absolute `SIB = 25` shape its `0x67` rows at the 32-bit value
width (`ADR-0090`), and `0.62.0` reached the no-base indexed shape at the
64-bit width (`ADR-0089`). `0.64.0` takes the 64-bit absolute sibling.

`EXP-0093` measures it with an explicit `addr32` prefix. The printer splits
that keyword onto its own line, so the instruction bytes are read from the
object file (`measure.py`):

1. **Both directions are nine bytes.** `addr32 movq 4660, %rax` is
   `67 48 8b 04 25 34 12 00 00`: `0x67` at byte 0, `REX = 48` at byte 1, the
   opcode at byte 2, `ModRM = 04` at byte 3, `SIB = 25` at byte 4 and four
   displacement bytes at 5–8. `addr32 movq %rax, 4660` is
   `67 48 89 04 25 34 12 00 00`.
2. **`REX.W` is mandatory and `R` is a free bit of the same byte.** There is no
   `REX`-less geometry, so `addr32 movq 4660, %r8` is
   `67 4c 8b 04 25 34 12 00 00` (`REX = 4c`) and one row per direction covers
   all sixteen value registers. There is no `REX.B` or `REX.X` bit, because
   there is no base and no index.
3. **The displacement is always four bytes.** `addr32 movq 0, %rax` is
   `67 48 8b 04 25 00 00 00 00` — nine bytes at offset zero — and the signed
   ends are `67 48 8b 04 25 00 00 00 80` (`-2147483648`) and
   `67 48 8b 04 25 ff ff ff 7f` (`2147483647`).
4. **`SIB = 25` is template content.** The byte is `25` at every value; only
   `ModRM.reg` and the displacement move. `addr32 movq 4660, %r15` is
   `67 4c 8b 3c 25 34 12 00 00` (`ModRM = 3c`).

The neighbours (`EXP-0093` §3): `movq 4660, %rax` is
`48 8b 04 25 34 12 00 00` (the `0.26.0` row, eight bytes),
`addr32 movl 4660, %eax` is `67 8b 04 25 …` and `addr32 movw 4660, %ax` is
`67 66 8b 04 25 …` (the `0.63.0` and 16-bit siblings),
`movq 8(,%rcx,1), %rax` is `48 8b 04 0d 08 00 00 00` (no-base indexed without
`0x67`), `movq 8(%eax,%ecx,1), %rax` is `67 48 8b 44 08 08` (base+index),
`movabs 4660, %rax` is `48 a1 34 12 00 00 00 00 00 00` and
`addr32 movabs 4660, %rax` is `67 48 a1` plus the same eight offset bytes
(eleven total — the prefix added a byte but did not shorten the offset, which
disagrees with a manual derivation of the `moffs` encoding, so `moffs` stays
deferred and unverified), and `addr32 movq 4660(%rip), %rax` is
`67 48 8b 05 34 12 00 00` (RIP-relative). `addr32 movq 4660, %eax` and
`addr32 movq 4660, %ax` are both rejected by `llvm-mc`
(`invalid operand for instruction`).

## Decision

1. **`0.64.0` appends two rows: one per direction.** The displacement is
   `disp32` and there is no address operand, and `REX.W` is mandatory, so there
   is no width or geometry axis beyond the direction.

   | Direction | `form_id` | Template | Length |
   |---|---|---|---|
   | load | `x86:mov/r64-addr32-abs32/legacy` | `67 48 8b 04 25 00 00 00 00` | 9 |
   | store | `x86:mov/addr32-abs32-r64/legacy` | `67 48 89 04 25 00 00 00 00` | 9 |

   The template's `SIB` byte is `25` (`scale = 00`, `index = 100`,
   `base = 101`); nothing in it is operand-owned.

2. **One geometry, one `REX` presence.** `0x67` is byte 0, `REX` byte 1, the
   opcode byte 2, `ModRM = 04` byte 3, `SIB = 25` byte 4 and the displacement
   `[40,32]` (signed). The value is `[10,1]` (`REX.R`) plus `[27,3]`
   (`ModRM.reg`) with no exclusion, because the row spans the whole 0-15
   window.

3. **The operand sequence has no address role:** `dest` or `src`
   (`x86.gpr64`/`r64`) and `disp` (`x86.imm`/`disp32`, signed). Supplying a
   `base`, `index` or `scale`, or omitting the `disp`, is `E-OPERAND-002`.

4. **No schema, loader or materializer change.** The rows use the same
   `x86.gpr64`/`r64` and `x86.imm`/`disp32` slots the absolute family already
   uses; `0x67`, `REX.W` and `SIB = 25` are template content.

## Consequences

- `0.64.0` is a 505-form document that byte-reproduces every `0.63.0` row.
  Its digest `sha256:fc98a834b7840d3f2383b05a5d2950966a81187234a080f24f7ad85ab6c07a4f`
  is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P68-gpr64-mov-addr32-abs32` has ten instructions
  and 90 bytes: the two rows plus `%r8` in both directions, a zero
  displacement, `-1`, both signed ends, `%r15` as the load value and `%r15` as
  the store value. Its `expected.bin` comes from `llvm-mc` + `llvm-objcopy`,
  never from the materializer.
- Seven negatives pin the version boundary in both directions
  (`N01ed`/`N01ee`, `E-FORM-001`), a supplied base (`N02cn`, `E-OPERAND-002`),
  a missing displacement (`N02co`, `E-OPERAND-002`), a 32-bit operand on the
  `r64` row (`N02cp`, two `E-OPERAND-001`: kind and target type), the signed
  displacement end (`N03zq`, `E-RANGE-001`) and the four-bit value end
  (`N14cd`, `E-OPERAND-004`).
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in
  place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Derive these rows from the `0.63.0` rows by adding `REX.W`.** Rejected:
  the mandatory `REX` byte shifts the opcode and `ModRM`, and the value gains
  its fourth bit, so it is a different frozen form; the materializer may not
  derive one from the other (`INV-02`, `INV-04`).
- **Keep the four-row split of `0.63.0` (bare plus `R`).** Rejected: there is
  no bare geometry, because `REX.W` is part of every encoding; a row that
  excluded `0`–`7` would make half the legal registers unreachable.
- **One row with a free `REX.W` bit that drops the `REX` byte when zero.**
  Rejected: `W` is not an operand bit here, and a byte cannot disappear when a
  plan picks a narrow value width — that is a different row.
- **Model the address as a `disp` plus an implicit zero base.** Rejected:
  `SIB.index = 100`/`base = 101` is the no-register constant, not a base of
  zero; a plan that supplied a base must fail (`E-OPERAND-002`).
- **Add a `disp8` variant.** Rejected by measurement: `SIB = 25` at
  `mod = 00` has no `disp8` form; zero keeps four displacement bytes.
- **Take the `0x67 66` absolute sibling in the same slice.** Deferred to its
  own slice: the third prefix moves every later field again, so it needs its
  own counterexamples.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 48 8b 04 25 34 12 00 00` is the bare absolute load at nine bytes | object bytes, `EXP-0093` §1 (printer splits `addr32`) | high |
| `REX.R` (`67 4c …`) is the only value-window bit and `SIB = 25` never changes | object bytes, `EXP-0093` §1/§4 | high |
| the displacement is four bytes at every value | object bytes, `EXP-0093` §3 | high |
| the ten byte strings decode back to `addr32 movq …` | `llvm-mc -disassemble`, `EXP-0093` §1 | high |
| the shape without `0x67`, the 32-bit/16-bit siblings, the indexed and base+index rows, `moffs` and RIP-relative are distinct | object bytes, `EXP-0093` §3 | high |
| `addr32 movq 4660, %eax`/`%ax` are rejected | `llvm-mc -show-encoding`, `EXP-0093` §3 | high |
| `0x67` keeps an eight-byte `moffs` offset in `llvm-mc` | object bytes, `EXP-0093` §3 | high (observed); the ISA reading is unverified |

## Review triggers

- A symbol or relocation in the `disp32` of this shape is requested.
- The `0x67 66` absolute sibling (`67 66 8b 04 25 …`) is proposed.
- The `moffs` form with `0x67` is proposed; the measurement and a manual
  derivation disagree about the offset width, so it needs a second oracle.
- The RIP-relative `67 48 8b 05` row is proposed.
- A 64-bit address register is proposed with `0x67`.
