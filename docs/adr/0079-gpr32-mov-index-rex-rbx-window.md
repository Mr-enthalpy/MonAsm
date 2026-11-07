# ADR-0079: the 32-bit indexed `mov` rows take the `REX.RBX` window

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P56` (the window where all three registers are extended on the
  32-bit `mov` indexed rows, at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement axis reaches the three-bit `REX` row at
  the same `[32,8]`/`[32,32]` offsets), `EC-06` (one `REX` byte carries `R`, `B`
  and `X` together on these rows), `EC-37` (both memory operands take their
  fourth bit from the same prefix byte) and `EC-38` (the 32-bit window split
  gains its `RBX` member, completing the four register/memory combinations)

## Context

`0.50.0` and `0.51.0` split the 32-bit indexed `mov` rows into the
`REX.R`/`REX.B`/`REX.X` members and the `REX.BX` member (`ADR-0077`,
`ADR-0078`). The remaining combination is all three extension bits at once.
`EXP-0081` measures it and four facts come out:

1. **One `REX` byte carries `R`, `B` and `X`.** `movl 8(%r8,%r9,1), %r8d` is
   `47 8b 44 08 08`: `REX = 47` (`R = 1` at `[2,1]`, `X = 1` at `[1,1]`,
   `B = 1` at `[0,1]`), still at byte 0, so `ModRM` stays at byte 2 and `SIB`
   at byte 3.
2. **The register gains a fixed bit.** Unlike `0.51.0`, the register is now a
   four-bit slot (`[2,1]`+`[19,3]`) that excludes `0`–`7`; a value there would
   clear the bit the template fixes.
3. **`%r12` is legal on all three operands.** `movl 8(%r12,%r12,1), %r8d` is
   `47 8b 44 24 08` and `movl %r12d, 8(%r12,%r12,1)` is `47 89 64 24 08`.
   `%r15`/`%r15` with `%r15d` at x8 is `47 8b 7c ff 08`.
4. **`%rsp` is still not an index.** `llvm-mc` rejects `8(%rax,%rsp,1)`
   (`invalid base+index expression`); `%rsp` is a legal base behind `REX.RX`
   (`movl 8(%rsp,%r9,1), %r8d` is `46 8b 44 0c 08`).

## Decision

**`0.52.0` appends four rows: two directions × two displacement widths.** Each
row fixes `REX.R`, `REX.B` and `REX.X` together and narrows all three register
slots to `8`–`15`.

| Direction | Displacement | `form_id` | Template | Length |
|---|---|---|---|---|
| load | `disp8` | `x86:mov/r32-ext-base-ext-index-ext-disp8/legacy` | `47 8b 44 00 00` | 5 |
| store | `disp8` | `x86:mov/base-ext-index-ext-disp8-r32-ext/legacy` | `47 89 44 00 00` | 5 |
| load | `disp32` | `x86:mov/r32-ext-base-ext-index-ext-disp32/legacy` | `47 8b 84 00 00 00 00 00` | 8 |
| store | `disp32` | `x86:mov/base-ext-index-ext-disp32-r32-ext/legacy` | `47 89 84 00 00 00 00 00` | 8 |

The slots are the `0.51.0` geometry with the register extended as well:

| Slot | Kind / `target_type` | Placements | Excluded |
|---|---|---|---|
| register | `x86.gpr32` / `r32` | `[2,1]`, `[19,3]` | `0`–`7` |
| base | `x86.gpr64` / `rm64` | `[0,1]`, `[24,3]` | `0`–`7` |
| index | `x86.gpr64` / `sib_index` | `[1,1]`, `[27,3]` | `0`–`7` |
| scale | `x86.scale` / `scale2` | `[30,2]` | — (`4` is `E-RANGE-001`) |
| displacement | `x86.imm` / `disp8`·`disp32` | `[32,8]`·`[32,32]` | — |

Four properties follow:

- **Three fixed bits, one prefix byte.** A low value on any of the three
  register slots would clear a bit the template fixes, so `0`–`7` is
  `E-RANGE-004` (`N16ci`/`N16cj`/`N16ck`).
- **`%r12` is legal on all three operands** through the fixed bits; `%rsp` as
  an index remains rejected.
- **The length is the `form_id`.** Five bytes at `disp8`, eight at `disp32`.
- **The split is complete.** With this row the 32-bit indexed `mov` family has
  all four combinations of register/memory extension: none (`0.49.0`), one
  bit (`0.50.0`), both memory bits (`0.51.0`) and all three (`0.52.0`).

## Consequences

- `0.52.0` is a 413-form document with the canonical digest
  `sha256:4587b149e1119681ffefe011862343d8bccd0f52dbe7d278a0afb05517f7f7ae`, byte-reproducing every `0.51.0` row.
- Its positive fixture `X86-P56-gpr32-mov-index-rex-rbx-window` has ten
  instructions and 56 bytes: the four rows plus six corners (`%r12`/`%r12`,
  `%r15`/`%r15` with `%r15d` at x8, `%r12` as an index, `%r12` as a base, the
  x8 scale and a second extended triple with the x2 scale in the store
  direction). Its `input_sha256` is
  `c55c54a7a0287415f1712f131f530ec706520f6288458e74e6ed5fbc94b58aeb` and its
  `output_sha256` is
  `80f2ca77ca8cc154d476e9170861b2ec803be8e32edde00781296863602ff1cc`. The
  materializer's output is byte-identical to the oracle and its artifact
  fingerprint is
  `sha256:0f5aa5afd1ec7adf8d5e43e9ef12ae6ee222c35d95e070a0f12e3b38c0d15811`.
- Negatives pin the version boundary in both directions (`N01df`, `N01dg`), a
  missing index (`N02bv`), the scale field's end (`N03ze`), and the three
  window floors (`N16ci`, `N16cj`, `N16ck`).
- `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place; no new `EC` row
  and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr32`/`r32`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **One row with a free `REX` byte and `0`–`15` on every operand.** The lower
  combinations already have their own rows, and a free byte would let one
  operand shape pick between aliases (`INV-02`).
- **Fold `RBX` into the `BX` row.** The register would have to cross `8`
  while the row fixes only two bits, so the materializer would have to decide
  whether to set `REX.R` (`INV-02`, `INV-04`).
- **Accept a low value on a window slot.** That clears a bit the template
  fixes (`INV-07`).
- **Add the `0x67` prefix, the APX `d5` window or a symbol fixup now.** Each
  is a different form with its own prefix order, length or fixup record.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `47 8b 44 08 08` is the `RBX` window at five bytes | `llvm-mc -show-encoding`, `EXP-0081` §1 | high |
| `REX = 47` with `ModRM` at byte 2 and the fields at `[19,3]`/`[24,3]`/`[27,3]`/`[30,2]` | `llvm-mc -show-encoding`, `EXP-0081` §2 | high |
| `%r12` is reachable on the register, base and index | `llvm-mc -show-encoding`, `EXP-0081` §1 | high |
| `%rsp` is rejected as an index | `llvm-mc`, `EXP-0081` §3 | high |
| the `disp32` rows are eight bytes with `disp32` at `[32,32]` | `llvm-mc -show-encoding`, `EXP-0081` §1 | high |

## Review triggers

- The `0x67` address-size prefix is attempted.
- A symbol or relocation in a displacement is requested.
- The no-base indexed shape is attempted.
- The APX `d5` register window is attempted.
- An EVEX masking or broadcast shape is attempted on these rows.
- The corresponding `REX.RBX` rows for the 16-bit family are requested.
