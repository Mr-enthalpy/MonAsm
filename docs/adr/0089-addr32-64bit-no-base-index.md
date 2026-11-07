# ADR-0089: the no-base indexed shape reaches the 64-bit value width

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P66` (the no-base indexed `movq` rows, both directions,
  `disp32` only)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `[40,32]` displacement offset covers the `movq` shape
  whose `disp32` is mandatory at every value), `EC-06` (`REX.W` is template
  content and `R`/`X` are free bits of the same byte; there is no `B` bit),
  `EC-07` (the 64-bit width carries `0x67`, `REX.W` and no `0x66`), `EC-08`
  (the `0x67` family reaches the 64-bit value width and the deferred list
  keeps symbols, absolute `SIB = 25`, `moffs`, APX `d5`, EVEX masking and
  64-bit address registers), `EC-37` (index `4` with `REX.X = 1` names
  `%r12d` on the 64-bit rows too) and `EC-38` (the family reaches 64-bit
  values with no base register)

## Context

`0.61.0` (`ADR-0088`) gave the `0x67` no-base indexed shape its 32-bit value
width with four `REX` windows. `EXP-0091` measures the 64-bit value width,
where `REX.W` forces the `REX` byte to exist and therefore changes the row
decomposition:

1. **`REX.W` is template content.** `movq 8(,%ecx,1), %rax` is
   `67 48 8b 04 0d 08 00 00 00`: `0x67` at byte 0, `REX = 48` at byte 1, the
   opcode at byte 2, `ModRM = 04` at byte 3, `SIB = 0d` at byte 4 and four
   displacement bytes at 5–8. Every row is nine bytes; there is no
   `REX`-less geometry.
2. **`R` and `X` are free bits inside that byte.** `movq 8(,%ecx,1), %r8` is
   `67 4c 8b 04 0d …` (`R = 1`), `movq 8(,%r9d,1), %rax` is
   `67 4a 8b 04 0d …` (`X = 1`) and `movq 8(,%r9d,1), %r8` is
   `67 4e 8b 04 0d …` (`R = X = 1`). Because the byte is already present, one
   row per direction covers all sixteen value registers and all sixteen
   indexes; there are no `-ext` windows.
3. **The displacement is always four bytes.** `movq 0(,%ecx,1), %rax` is
   `67 48 8b 04 0d 00 00 00 00` — nine bytes at offset zero.
4. **Index `4` with `REX.X = 0` is still the "no index" constant.** The index
   slot carries `[9,1]`+`[35,3]` and excludes `4`, so `%r12d` is legal
   (`67 4a 8b 04 25 08 00 00 00`, `SIB = 25`) and index `4` is
   `E-RANGE-004`.

The neighbours (`EXP-0091` §3): `movq 8(%eax,%ecx,1), %rax` is
`67 48 8b 44 08 08` (base+index, six bytes), `movw 8(,%ecx,1), %ax` is
`67 66 8b 04 0d …` and `movl 8(,%ecx,1), %eax` is `67 8b 04 0d …` (the
`0.60.0`/`0.61.0` siblings), `movq 8(,%rcx,1), %rax` is `48 8b 04 0d …` and
`movq 4660, %rax` is `48 8b 04 25 34 12 00 00` (no `0x67`), and
`movq 8(,%r12,1), %rax` is `4a 8b 04 25 08 00 00 00` (64-bit index register,
no `0x67`). `%esp` as an index and `%eax` with `movq` are both rejected by
`llvm-mc`.

## Decision

1. **`0.62.0` appends two rows, one per direction.** The displacement is
   `disp32` and the `REX` byte is always present, so there is neither a width
   axis nor a window axis.

   | Direction | `form_id` | Template | Length |
   |---|---|---|---|
   | load | `x86:mov/r64-addr32-index-disp32/legacy` | `67 48 8b 04 05 00 00 00 00` | 9 |
   | store | `x86:mov/addr32-index-disp32-r64/legacy` | `67 48 89 04 05 00 00 00 00` | 9 |

   The template's `SIB` byte is `05` (index field `0`, scale `00`, base
   `101`); the index and scale are operand-owned, and `W` is the template's
   `REX` bit 3 (`0x48`).

2. **One geometry.** `0x67` at byte 0, `REX` at byte 1, the opcode at byte 2,
   `ModRM = 04` at byte 3 and `SIB` at byte 4, so the value is `[10,1]` plus
   `[27,3]`, the index `[9,1]` plus `[35,3]`, the scale `[38,2]` and the
   displacement `[40,32]` (signed).

3. **The operand sequence has no `base` role:** `dest` or `src`
   (`x86.gpr64`/`r64`), `index` (`x86.gpr32`/`sib_index32`, excluding `4`),
   `imm` (`x86.scale`/`scale2`) and `disp` (`x86.imm`/`disp32`, signed). A
   supplied `base` is `E-OPERAND-002`; a missing `index` is also
   `E-OPERAND-002`.

4. **No schema, loader or materializer change.** The rows use the same
   `x86.scale`, `x86.imm`/`disp32` and `x86.gpr32`/`sib_index32` slots the
   family already uses, and the `r64` slot with `[10,1]`+`[27,3]` matches the
   `0.56.0` `movq` rows. `SIB.base = 101` and `REX.W` are template content.

## Consequences

- `0.62.0` is a 499-form document that byte-reproduces every `0.61.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P66-gpr64-mov-index-addr32-no-base` has thirteen
  instructions and 117 bytes: both rows plus `R`, `X` and `R`+`X` values and
  indexes, a zero displacement, a negative displacement, the x4 scale,
  `%r12d` under `REX.X` and `4660(,%r15d,8), %r15`. Its `expected.bin` comes
  from `llvm-mc` + `llvm-objcopy`, never from the materializer.
- Eight negatives pin the version boundary in both directions, a missing
  index, a supplied base, the scale end, a value and an index past the
  four-bit field, and index `4` on the low `REX.X` row.
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in
  place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Add four `REX` windows as in `0.61.0`.** Rejected: `REX.W` forces the byte
  to exist, so `R` and `X` are free bits of one row, not separate templates;
  separate rows would duplicate the same encodings and pretend an operand
  value selects a form (`INV-02`).
- **Add a `disp8` variant.** Rejected by measurement: `SIB.base = 101` forces
  `mod = 00`, and zero keeps four displacement bytes.
- **Read index field `4` as "no index".** Rejected: `%r12d` is legal through
  `REX.X = 1`; the no-base meaning is `SIB.base = 101`.
- **Fold these rows into the 32-bit rows.** Rejected: `REX.W` changes the
  opcode width and is template content, and the 32-bit bare row has no `REX`
  byte at all (`INV-02`, `INV-04`).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 48 8b 04 0d 08 00 00 00` is the no-base low-index `movq` load at nine bytes | `llvm-mc -show-encoding`, `EXP-0091` §1 | high |
| `0x4c`/`0x4a`/`0x4e` are the same row with `R`, `X` and both set | `llvm-mc -show-encoding`, `EXP-0091` §2 | high |
| `SIB.base = 101` forces a four-byte displacement at every value | `llvm-mc -show-encoding`, `EXP-0091` §1 (`0(,%ecx,1)`) | high |
| index `4` with `REX.X = 1` names `%r12d` (`SIB = 25`) | `llvm-mc`, `EXP-0091` §1 | high |
| the thirteen byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0091` §1 | high |
| the 64-bit-addressing and absolute forms omit `0x67` | `llvm-mc -show-encoding`, `EXP-0091` §3 | high |

## Review triggers

- A symbol or relocation in the `disp32` of this shape is requested.
- A `disp8` no-base shape is proposed.
- The absolute `SIB = 25` shape with `0x67`, or the `moffs` form, is attempted.
- A 64-bit address register is proposed with `0x67`.
