# ADR-0077: the 32-bit indexed `mov` rows take the single `REX` windows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P54` (the `REX.R`, `REX.B` and `REX.X` windows on the 32-bit
  `mov` indexed rows, each fixing one extension bit, both directions at both
  displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement axis now reaches the `REX`-carrying
  32-bit indexed rows, where the prefix byte pushes `ModRM`, `SIB` and the
  displacement one byte later), `EC-06` (a `REX` byte is now present on these
  rows and each row fixes one extension bit), `EC-37` (the index's fourth bit
  is `REX.X` on the 32-bit rows as well) and `EC-38` (the 32-bit window split
  gains its `R`, `B` and `X` members, leaving only `BX` for a later slice)

## Context

`0.49.0` gave the 32-bit `mov` family its `REX`-less indexed rows (`ADR-0076`):
`movl 8(%rax,%rcx,1), %eax` is `8b 44 08 08`, four bytes with three-bit
register, base and index fields. The three extension bits were explicitly
deferred. `EXP-0079` measures all three one-bit windows and four facts come out:

1. **A `REX` byte appears and moves everything one byte later.**
   `movl 8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08` (`REX.R = 1`),
   `movl 8(%r8,%rcx,1), %eax` is `41 8b 44 08 08` (`REX.B = 1`) and
   `movl 8(%rax,%r9,1), %eax` is `42 8b 44 08 08` (`REX.X = 1`). The opcode
   moves to byte 1, `ModRM` to byte 2 and `SIB` to byte 3; the register is
   `[19,3]`, the base `[24,3]`, the index `[27,3]`, the scale `[30,2]` and the
   displacement `[32,8]`.
2. **Each window is disjoint from the low row.** The extended operand's value
   is `8`–`15`, whose low three bits are `0`–`7`; a value of `0`–`7` would
   clear the fixed `REX` bit, so those are the `0.49.0` form instead
   (`EC-38`).
3. **`%r12` is reachable in both memory windows.**
   `movl 8(%r12,%rcx,1), %eax` is `41 8b 44 0c 08` (`SIB.base = 100` behind
   `REX.B`) and `movl %eax, 8(%rax,%r12,1)` is `42 89 44 20 08`
   (`SIB.index = 100` behind `REX.X`). This is why the window values are the
   register number minus eight, not the `SIB`-encoded aliases.
4. **`%rsp`/`%rbp` remain legal bases in the `REX.R` window.**
   `movl 8(%rsp,%rcx,1), %r8d` is `44 8b 44 0c 08`. In the `REX.B` window
   they are `%r12`/`%r13` by definition (`8(%r12,%rcx,1)` and
   `8(%r13,%rsi,1)` are `41 8b 44 0c 08` / `41 8b 44 35 08`), so the base
   slot there excludes `0`–`7`. `%rsp` is still not an index anywhere
   (`llvm-mc`: `invalid base+index expression`), and the `REX.X` window's
   index slot excludes `0`–`7` (`4` included).

## Decision

**`0.50.0` appends twelve rows: three windows × two directions × two
displacement widths.** Each row fixes exactly one `REX` extension bit and
narrows the corresponding operand slot to `8`–`15`.

| Window | Direction | Displacement | `form_id` | Template | Length |
|---|---|---|---|---|---|
| `R` | load | `disp8` | `x86:mov/r32-ext-base-index-disp8/legacy` | `44 8b 44 00 00` | 5 |
| `R` | store | `disp8` | `x86:mov/base-index-disp8-r32-ext/legacy` | `44 89 44 00 00` | 5 |
| `R` | load | `disp32` | `x86:mov/r32-ext-base-index-disp32/legacy` | `44 8b 84 00 00 00 00 00` | 8 |
| `R` | store | `disp32` | `x86:mov/base-index-disp32-r32-ext/legacy` | `44 89 84 00 00 00 00 00` | 8 |
| `B` | load | `disp8` | `x86:mov/r32-base-ext-index-disp8/legacy` | `41 8b 44 00 00` | 5 |
| `B` | store | `disp8` | `x86:mov/base-ext-index-disp8-r32/legacy` | `41 89 44 00 00` | 5 |
| `B` | load | `disp32` | `x86:mov/r32-base-ext-index-disp32/legacy` | `41 8b 84 00 00 00 00 00` | 8 |
| `B` | store | `disp32` | `x86:mov/base-ext-index-disp32-r32/legacy` | `41 89 84 00 00 00 00 00` | 8 |
| `X` | load | `disp8` | `x86:mov/r32-base-index-ext-disp8/legacy` | `42 8b 44 00 00` | 5 |
| `X` | store | `disp8` | `x86:mov/base-index-ext-disp8-r32/legacy` | `42 89 44 00 00` | 5 |
| `X` | load | `disp32` | `x86:mov/r32-base-index-ext-disp32/legacy` | `42 8b 84 00 00 00 00 00` | 8 |
| `X` | store | `disp32` | `x86:mov/base-index-ext-disp32-r32/legacy` | `42 89 84 00 00 00 00 00` | 8 |

The slots are the `0.49.0` geometry shifted one byte (the `REX` byte at 0):

| Slot | Kind / `target_type` | Placements | Excluded |
|---|---|---|---|
| register | `x86.gpr32` / `r32` | `[19,3]` (`[2,1]`, `[19,3]` on the `R` row) | `0`–`7` on the `R` row only |
| base | `x86.gpr64` / `rm64` | `[24,3]` (`[0,1]`, `[24,3]` on the `B` row) | `0`–`7` on the `B` row only |
| index | `x86.gpr64` / `sib_index` | `[27,3]` (`[1,1]`, `[27,3]` on the `X` row) | `4` on the `R`/`B` rows, `0`–`7` on the `X` row |
| scale | `x86.scale` / `scale2` | `[30,2]` | — (`4` is `E-RANGE-001`) |
| displacement | `x86.imm` / `disp8`·`disp32` | `[32,8]`·`[32,32]` | — |

Four properties follow:

- **The fourth bit is operand-owned on the extended slot.** Each window slot
  lists its `REX` bit as the most significant placement, so a value of `8`–`15`
  writes the bit the template fixes to `1` and the low three bits into the
  field. A value of `0`–`7` is `E-RANGE-004` (`N16cd`/`N16ce`/`N16cf`) rather
  than a silent clear (`INV-07`).
- **The other operands stay low.** On the `R` row, base and index are `0`–`7`
  (index `4` excluded); on the `B` row the register is `0`–`7` and the index
  `0`–`7` except `4`; on the `X` row the register and base are `0`–`7`.
  Register `8`–`15` on the `B`/`X` rows is `E-OPERAND-004` and belongs to a
  different row.
- **`%r12` is legal in both memory windows** through the fixed bit; `%rsp` as
  an index is still `E-RANGE-004`.
- **The length is the `form_id`.** Five bytes at `disp8`, eight at `disp32`.

## Consequences

- `0.50.0` is a 405-form document with the canonical digest
  `sha256:6f38e272ef1464b5067053c7a10d744adee19699fbe4ecbc0928fb3c8f7da75a`,
  byte-reproducing every `0.49.0` row.
- Its positive fixture `X86-P54-gpr32-mov-index-rex-windows` has fifteen
  instructions and 93 bytes: the twelve rows plus the `%r12` base, the `%r12`
  index and the `%rsp` base. Its `input_sha256` is
  `6e15ae95cec1673e538c2b3721bd29c58085ea1fd046a8fd3d53bc6d2dc145d9` and its
  `output_sha256` is
  `fcb2ccc6befba68d9be798a9dc73afb8e25f8ae059beb70b04917bb2b42c2e26`. The
  materializer's output is byte-identical to the oracle and its artifact
  fingerprint is
  `sha256:d8429016d9ac7d7c4cd1622ad6d234587e03f748243792f6a316cbca103596ea`.
- Negatives pin the version boundary in both directions (`N01db`, `N01dc`), a
  missing index (`N02bt`), the scale field's end (`N03zc`), the non-extended
  operands staying low (register `8` on the `REX.B` row, `N14bi`; base `8` on
  the `REX.X` row, `N14bj`), and the three window floors (`N16cd`, `N16ce`,
  `N16cf`).
- `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place; no new `EC` row
  and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr32`/`r32`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **One row with the `REX` byte always present and `0`–`15` on every
  operand.** The low case would then gain a `40` prefix, a five-byte alias of
  the four-byte `0.49.0` form: one operand shape gets one frozen encoding
  (`INV-02`).
- **Combine the three windows into one row per direction and width.** `R`,
  `B` and `X` are different byte strings for different plans, and a single
  row would have to choose which bit to set from the operand values
  (`INV-02`, `INV-04`).
- **Accept a low value on a window slot.** That clears a bit the template
  fixes, so the row would encode a different register than the plan named
  (`INV-07`).
- **Add the `REX.BX` window now.** A row with two fixed extension bits is a
  fourth member of the split and gets its own measurement (`43 8b 44 08 08`).
- **Add the `0x67` prefix or the APX `d5` window.** Both are different forms
  with their own prefix order and length.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `44 8b 44 08 08` is the `REX.R` window at five bytes | `llvm-mc -show-encoding`, `EXP-0079` §1 | high |
| `41 8b 44 08 08` / `42 8b 44 08 08` are the `B`/`X` windows | `llvm-mc -show-encoding`, `EXP-0079` §1 | high |
| `ModRM` at byte 2 and the fields at `[19,3]`/`[24,3]`/`[27,3]`/`[30,2]` | `llvm-mc -show-encoding`, `EXP-0079` §2 | high |
| `%r12` is reachable as base and as index on these rows | `llvm-mc -show-encoding`, `EXP-0079` §1 | high |
| `%rsp` is rejected as an index | `llvm-mc`, `EXP-0079` §3 | high |
| the `disp32` rows are eight bytes with `disp32` at `[32,32]` | `llvm-mc -show-encoding`, `EXP-0079` §1 | high |

## Review triggers

- The `REX.BX` window on the 32-bit indexed rows is attempted.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in a displacement is requested.
- The no-base indexed shape is attempted.
- The APX `d5` register window is attempted.
