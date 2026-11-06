# ADR-0075: the low-register 16-bit `mov` indexed rows take the `REX.BX` window

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P52` (the window where the base and the index are both in
  `%r8`–`%r15` while the register stays in `%ax`–`%di`, both directions and
  both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the same displacement rule, now for the row with two
  extension bits), `EC-37` (the index slot reaches `%r12` through `REX.X` in
  this window as well) and `EC-38` (the window split gains its third member:
  base only, index only, both)

## Context

`0.47.0` gave the low-register 16-bit indexed `mov` rows one extension bit at
a time (`ADR-0074`): the `REX.B` base window and the `REX.X` index window.
The remaining shape in that family has both operands extended, e.g.
`movw 8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08`, and no row plans it.

`EC-38` fixes the rule: a row's register window is a property of the form. A
row whose register is low has no `REX.R`, and the `REX` byte it carries is
free to hold `X` and `B` as constants for the two memory operands. That makes
a third row per direction and width, not a widened slot: a slot that accepted
`0`–`15` for either operand would have to write its own `REX` bit, which is
the `0.45.0` shape (`INV-02`).

`EXP-0077` measures the shape and five facts come out:

1. **Both extension bits are fixed in one `REX` byte.** `movw 8(%r8,%r9,1),
   %ax` is `66 43 8b 44 08 08`: `REX = 43` (`W = 0`, `R = 0`, `X = 1`,
   `B = 1`), `ModRM = 44` (`mod = 01`, `reg = 0`, `r/m = 100`), `SIB = 08`
   (scale `0`, index `1`, base `0`) and the displacement at `[40,8]`.
2. **The window is `8`–`15` on both operands.** `movw 8(%r15,%r15,8), %di` is
   `66 43 8b 7c ff 08`: `reg = 7` at `[27,3]`, `SIB = ff` (scale `3`, index
   `7`, base `7`), so the low three bits are the value minus eight.
3. **`%r12` is legal on both operands here.** `movw 8(%r12,%r12,1), %ax` is
   `66 43 8b 44 24 08` (`SIB = 24`: scale `0`, index `100`, base `100`) and
   the store direction is `66 43 89 44 24 08`. This is the window that makes
   `SIB.base = 100` and `SIB.index = 100` both meaningful, because `REX.B` and
   `REX.X` are set.
4. **`%rsp` is still not an index.** `llvm-mc` rejects `8(%rax,%rsp,1)`, so
   the index slot's low window (`0`–`7`) is excluded and `4` is not reachable
   through it; `%r12` is a different value of the same slot.
5. **`%rbp` is legal as an index.** `movw 8(%r13,%rbp,1), %ax` is
   `66 41 8b 44 2d 08` (`REX.B` only, `SIB = 2d`: index `101`, base `101`) and
   `movw 8(%rbp,%r13,1), %ax` is `66 42 8b 44 2d 08` (`REX.X` only). The
   `SIB` index field carries the register number directly; only `%rsp` is
   special.

## Decision

**`0.48.0` appends four rows: two directions × two displacement widths.** Each
row fixes `REX = 43`, keeps the register at `[27,3]`, narrows both memory
slots to `8`–`15`, and puts the displacement at `[40,8]` or `[40,32]`.

| Direction | Displacement | `form_id` | Template | Length |
|---|---|---|---|---|
| load | `disp8` | `x86:mov/r16-base-ext-index-ext-disp8/legacy` | `66 43 8b 44 00 00` | 6 |
| store | `disp8` | `x86:mov/base-ext-index-ext-disp8-r16/legacy` | `66 43 89 44 00 00` | 6 |
| load | `disp32` | `x86:mov/r16-base-ext-index-ext-disp32/legacy` | `66 43 8b 84 00 00 00 00 00` | 9 |
| store | `disp32` | `x86:mov/base-ext-index-ext-disp32-r16/legacy` | `66 43 89 84 00 00 00 00 00` | 9 |

The slots are the `0.47.0` geometry with the base and index windows narrowed:

| Slot | Kind / `target_type` | Placements | Excluded |
|---|---|---|---|
| register | `x86.gpr16` / `r16` | `[27,3]` | — (`0`–`7` only by field width) |
| base | `x86.gpr64` / `rm64` | `[8,1]`, `[32,3]` | `0`–`7` |
| index | `x86.gpr64` / `sib_index` | `[9,1]`, `[35,3]` | `0`–`7` |
| scale | `x86.scale` / `scale2` | `[38,2]` | — (`4` is `E-RANGE-001`) |
| displacement | `x86.imm` / `disp8`·`disp32` | `[40,8]`·`[40,32]` | — |

Three properties follow:

- **The fourth bit is operand-owned on both operands.** Each extended slot
  lists its `REX` bit as the most significant placement and excludes the low
  window, so a plan value of `0`–`7` is `E-RANGE-004` rather than a silent
  clear of the fixed bit (`INV-07`, `N16ca`/`N16cb`).
- **The register cannot move.** `%ax`–`%di` only; register `8`–`15` is
  `E-OPERAND-004` (`N14bf`) and belongs to the `0.45.0` row, whose `REX.R = 1`
  also changes `REX` from `43` to `47`.
- **The length is the `form_id`.** Six bytes at `disp8`, nine at `disp32`,
  with the displacement always behind the `SIB` byte (`INV-04`).

## Consequences

- `0.48.0` is a 389-form document, byte-reproducing every `0.47.0` row.
- Its positive fixture `X86-P52-gpr16-mov-index-rex-bx-window` has twelve
  instructions and 90 bytes: both directions, both displacement widths, the
  `%r8`/`%r9` and `%r15`/`%r15` extremes, and a `%r12`/`%r12` pair. Its
  `input_sha256` is
  `5dc650423e5737666d6fb360a0c13aaacfd3c6bbdf9bc96fb9e38dc901f276dc` and
  `output_sha256` is `3cc9c66f5a3f49ce79713770738721bfd023981b25471c34a8604b2ae2cbbc47`.
- Negatives pin the version boundary in both directions (`N01cx`, `N01cy`), a
  missing index (`N02br`), the scale field's end (`N03za`), the register
  field's end (`N14bf`), and both window floors (`N16ca`, `N16cb`).
- `EC-02`, `EC-37` and `EC-38` are revised in place; no new `EC` row and no row
  is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr16`/`r16`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **Widen the `0.47.0` slots to `0`–`15` instead of adding rows.** The
  operand would then own `REX.B`/`REX.X` and the low case would gain a `40` or
  `41`/`42` prefix option, i.e. two byte strings for one instruction. One
  operand shape gets one frozen encoding (`INV-02`).
- **Accept a low base or index on this row.** That clears a bit the template
  fixes, so the row would emit `%rax`–`%rdi` for a plan that named `%r8`–
  `%r15`, or the reverse: a silent repair (`INV-07`).
- **Split `X` and `B` across two `REX` bytes.** There is only one `REX` byte
  in the encoding, and its position is `0.47.0`'s.
- **Add the `0x67` address-size prefix or the APX `d5` window now.** Both are
  different forms with their own prefix order and length; the `d5` form of
  this shape is `66 d5 43 8b 44 08 08` and needs its own measurement.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 43 8b 44 08 08` at six bytes | `llvm-mc -show-encoding`, `EXP-0077` §1 | high |
| `%r15`/`%r15` with ×8 is `66 43 8b 7c ff 08` | `llvm-mc -show-encoding`, `EXP-0077` §1 | high |
| `%r12` is legal as base and as index on this row | `llvm-mc -show-encoding`, `EXP-0077` §1 | high |
| `%rsp` is rejected as an index | `llvm-mc`, `EXP-0077` §3 | high |
| `%rbp` is legal as an index | `llvm-mc -show-encoding`, `EXP-0077` §3 | high |
| the `disp32` rows are nine bytes with `disp32` at `[40,32]` | `llvm-mc -show-encoding`, `EXP-0077` §1 | high |

## Review triggers

- The `0x67` address-size prefix is attempted.
- The APX `d5` register window is attempted.
- A symbol or relocation in a displacement is requested.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`) is attempted.
- An EVEX/GPR masked form is attempted.
