# ADR-0078: the 32-bit indexed `mov` rows take the `REX.BX` window

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P55` (the window where both memory operands are extended on the
  32-bit `mov` indexed rows, at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement axis reaches the two-bit `REX` row, where
  the prefix moves `ModRM`, `SIB` and the displacement one byte later),
  `EC-06` (one `REX` byte now carries two extension bits on these rows),
  `EC-37` (both memory operands take their fourth bit from the same prefix
  byte) and `EC-38` (the 32-bit window split gains its `BX` member)

## Context

`0.50.0` gave the 32-bit indexed `mov` rows their single `REX` windows
(`ADR-0077`): `REX.R`, `REX.B` and `REX.X` each fixed one extension bit while
the other memory operand stayed in `0`–`7`. `EXP-0080` measures the remaining
window, where both memory operands are extended and the register stays low.
Four facts come out:

1. **One `REX` byte carries both bits.** `movl 8(%r8,%r9,1), %eax` is
   `43 8b 44 08 08`: `REX = 43` (`B = 1` at `[0,1]`, `X = 1` at `[1,1]`,
   `R = 0`) still at byte 0, so `ModRM` stays at byte 2 and `SIB` at byte 3.
2. **The `SIB` fields are unchanged.** Base `[24,3]` and index `[27,3]` keep
   their low three bits; only the excluded window is `0`–`7`, exactly as on
   the single-bit rows.
3. **`%r12` is legal on both operands.** `movl 8(%r12,%r12,1), %eax` is
   `43 8b 44 24 08`, where `SIB.base = 100` and `SIB.index = 100` are both
   meaningful behind the two fixed bits. `%r15`/`%r15` at x8 is
   `43 8b 7c ff 08`.
4. **`%rsp` is still not an index.** `llvm-mc` rejects
   `8(%rax,%rsp,1)` (`invalid base+index expression`), and the low value `4`
   stays inside the `0`–`7` exclusion.

## Decision

**`0.51.0` appends four rows: two directions × two displacement widths.** Each
row fixes `REX.B` and `REX.X` together and narrows base and index to `8`–`15`;
the register stays three bits at `[19,3]`.

| Direction | Displacement | `form_id` | Template | Length |
|---|---|---|---|---|
| load | `disp8` | `x86:mov/r32-base-ext-index-ext-disp8/legacy` | `43 8b 44 00 00` | 5 |
| store | `disp8` | `x86:mov/base-ext-index-ext-disp8-r32/legacy` | `43 89 44 00 00` | 5 |
| load | `disp32` | `x86:mov/r32-base-ext-index-ext-disp32/legacy` | `43 8b 84 00 00 00 00 00` | 8 |
| store | `disp32` | `x86:mov/base-ext-index-ext-disp32-r32/legacy` | `43 89 84 00 00 00 00 00` | 8 |

The slots are the `0.50.0` geometry with both memory operands extended:

| Slot | Kind / `target_type` | Placements | Excluded |
|---|---|---|---|
| register | `x86.gpr32` / `r32` | `[19,3]` | — (value `8`–`15` is `E-OPERAND-004`) |
| base | `x86.gpr64` / `rm64` | `[0,1]`, `[24,3]` | `0`–`7` |
| index | `x86.gpr64` / `sib_index` | `[1,1]`, `[27,3]` | `0`–`7` |
| scale | `x86.scale` / `scale2` | `[30,2]` | — (`4` is `E-RANGE-001`) |
| displacement | `x86.imm` / `disp8`·`disp32` | `[32,8]`·`[32,32]` | — |

Four properties follow:

- **Two fixed bits, one prefix byte.** A low base or index would clear a bit
  the template fixes, so `0`–`7` on either memory slot is `E-RANGE-004`
  (`N16cg`/`N16ch`).
- **The register is still three bits.** Value `8`–`15` is `E-OPERAND-004`
  (`N14bk`) and belongs to a row that fixes `REX.R`.
- **`%r12` is legal on both operands** through the fixed bits; `%rsp` as an
  index remains rejected.
- **The length is the `form_id`.** Five bytes at `disp8`, eight at `disp32`.

## Consequences

- `0.51.0` is a 409-form document with the canonical digest
  `sha256:e73395dffc494d13d0b142cbba0e4c55a40d19bcd68a6b793025156bbcb41bc5`, byte-reproducing every `0.50.0` row.
- Its positive fixture `X86-P55-gpr32-mov-index-rex-bx-window` has ten
  instructions and 56 bytes: the four rows plus six corners (`%r12`/`%r12`,
  `%r15`/`%r15` at x8, `%r12` as an index, `%r12` as a base, the x8 scale and
  a second extended pair with the x2 scale in the store direction). Its
  `input_sha256` is
  `db74d0de338ae505089df4b8e496aa2c6ee35a91d6c20844e590a6f26bf03f7a` and its
  `output_sha256` is
  `1f0301f410a6a72ae4786bd6803ba9911ce8a1dde075d79ab744913a61c91fdb`. The
  materializer's output is byte-identical to the oracle and its artifact
  fingerprint is `sha256:e99d2bdb31d83a0ca14618e72a1928f252bf2482e99e206733d48bba48205198`.
- Negatives pin the version boundary in both directions (`N01dd`, `N01de`), a
  missing index (`N02bu`), the scale field's end (`N03zd`), register `8`
  (`N14bk`), and the two window floors (`N16cg`, `N16ch`).
- `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place; no new `EC` row
  and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr32`/`r32`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **One row with a free `REX` byte and `0`–`15` on every operand.** The low
  cases would gain a `40`–`42` prefix, aliases of the four-byte `0.49.0` row
  and the five-byte `0.50.0` rows; one operand shape gets one frozen encoding
  (`INV-02`).
- **Extend the single-bit rows instead of adding a `BX` row.** The four
  single-bit rows fix exactly one bit, and letting the other memory operand
  cross `8` would require the row to choose whether to set its bit
  (`INV-02`, `INV-04`).
- **Accept a low value on a window slot.** That clears a bit the template
  fixes (`INV-07`).
- **Add the `0x67` prefix, the APX `d5` window or a symbol fixup now.** Each
  is a different form with its own prefix order, length or fixup record.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `43 8b 44 08 08` is the `BX` window at five bytes | `llvm-mc -show-encoding`, `EXP-0080` §1 | high |
| `REX = 43` with `ModRM` at byte 2 and the fields at `[19,3]`/`[24,3]`/`[27,3]`/`[30,2]` | `llvm-mc -show-encoding`, `EXP-0080` §2 | high |
| `%r12` is reachable as base and as index | `llvm-mc -show-encoding`, `EXP-0080` §1 | high |
| `%rsp` is rejected as an index | `llvm-mc`, `EXP-0080` §3 | high |
| the `disp32` rows are eight bytes with `disp32` at `[32,32]` | `llvm-mc -show-encoding`, `EXP-0080` §1 | high |

## Review triggers

- The `0x67` address-size prefix is attempted.
- A symbol or relocation in a displacement is requested.
- The no-base indexed shape is attempted.
- The APX `d5` register window is attempted.
- An EVEX masking or broadcast shape is attempted on these rows.
