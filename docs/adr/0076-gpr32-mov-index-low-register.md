# ADR-0076: the 32-bit `mov` family takes the `REX`-less indexed rows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P53` (the `SIB` index and scale on the 32-bit `mov` memory rows
  whose register, base and index are all in the low window, both directions at
  both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement axis now reaches the 32-bit indexed rows,
  with no prefix byte in front of the opcode), `EC-37` (the `SIB` index/scale
  rule now covers the 32-bit family, not only the 16- and 64-bit ones) and
  `EC-38` (the 32-bit window split: the `REX`-less row reaches `0`–`7` on all
  three registers, and the `REX` windows are separate forms)

## Context

`0.48.0` closed the 16-bit indexed `mov` family (`ADR-0073`–`ADR-0075`) and
`ADR-0035` gave the 64-bit family indexed rows whose `REX` byte carries
`R`/`X`/`B` as operand-owned placements. The 32-bit family has the `SIB` bases
(`%rsp`/`%r12`, `ADR-0063`) and the `disp8`/`disp32` displacements
(`ADR-0064`/`ADR-0065`), but no row names an index: `movl
8(%rax,%rcx,1), %eax` is `8b 44 08 08` and nothing plans it.

`EC-37` fixes the rule: an index register and a scale factor need a `SIB` byte
(`r/m = 100`), the index is one `SIB` field with `100` meaning "no index", and
the scale is two bits of field content. `EC-38` fixes the reach: a row with no
`REX` byte has three-bit register fields, and reaching `%r8`–`%r15` is a
different form.

`EXP-0078` measures the shape and five facts come out:

1. **There is no prefix byte.** `movl 8(%rax,%rcx,1), %eax` is `8b 44 08 08`:
   four bytes, `ModRM = 44` at byte 1 (`mod = 01`, `reg = 0`, `r/m = 100`),
   `SIB = 08` at byte 2 (scale `0`, index `1`, base `0`) and the displacement
   at `[24,8]`. The register is `[11,3]`, the base `[16,3]`, the index
   `[19,3]` and the scale `[22,2]`.
2. **`%rsp`/`%rbp` are legal bases.** `movl 8(%rsp,%rcx,1), %eax` is
   `8b 44 0c 08` (`SIB.base = 100`) and `movl 8(%rbp,%rsi,1), %eax` is
   `8b 44 35 08` (`SIB.base = 101` at `mod = 01`), because `r/m = 100`
   announces the `SIB` byte.
3. **The index excludes `4`.** `llvm-mc` rejects `movl 8(%rax,%rsp,1), %eax`
   (`invalid base+index expression`): `SIB.index = 100` with no `REX.X` means
   "no index". `%r12` is not reachable from this row at all.
4. **The scale is field content.** `movl 8(%rdi,%rsi,4), %edi` is
   `8b 7c b7 08` (`SIB = b7`: scale `2` = ×4, index `6`, base `7`); `4` is
   past the two-bit field and is `E-RANGE-001`.
5. **The displacement is four bytes at `[24,32]`.**
   `movl 200(%rax,%rcx,1), %eax` is `8b 84 08 c8 00 00 00` and
   `movl 200(%rdi,%rsi,4), %edi` is `8b bc b7 c8 00 00 00`.

## Decision

**`0.49.0` appends four rows: two directions × two displacement widths.** Each
row keeps `reg`, base and index at three bits and excludes index `4`; the base
is unconstrained (`0`–`7`).

| Direction | Displacement | `form_id` | Template | Length |
|---|---|---|---|---|
| load | `disp8` | `x86:mov/r32-base-index-disp8/legacy` | `8b 44 00 00` | 4 |
| store | `disp8` | `x86:mov/base-index-disp8-r32/legacy` | `89 44 00 00` | 4 |
| load | `disp32` | `x86:mov/r32-base-index-disp32/legacy` | `8b 84 00 00 00 00 00` | 7 |
| store | `disp32` | `x86:mov/base-index-disp32-r32/legacy` | `89 84 00 00 00 00 00` | 7 |

| Slot | Kind / `target_type` | Placements | Excluded |
|---|---|---|---|
| register | `x86.gpr32` / `r32` | `[11,3]` | — (`0`–`7` by field width) |
| base | `x86.gpr64` / `rm64` | `[16,3]` | — (`%rsp`/`%rbp` legal) |
| index | `x86.gpr64` / `sib_index` | `[19,3]` | `4` |
| scale | `x86.scale` / `scale2` | `[22,2]` | — (`4` is `E-RANGE-001`) |
| displacement | `x86.imm` / `disp8`·`disp32` | `[24,8]`·`[24,32]` | — |

Four properties follow:

- **The row is four bytes at `disp8` and seven at `disp32`.** No prefix byte
  means the `ModRM` is byte 1 and every field sits eight bits earlier than the
  `REX`-carrying 64-bit rows.
- **The register window is low only.** Register `8`–`15` needs `REX.R` and is
  `E-OPERAND-004` (`N14bg`); `movl 8(%rax,%rcx,1), %r8d` is
  `44 8b 44 08 08`, a different form.
- **The base window is low only.** Base `8`–`15` needs `REX.B` and is
  `E-OPERAND-004` (`N14bh`). `%r12` as a base is `41 8b 44 0c 08`, the
  `REX.B` form, not `%rsp`.
- **The index is three bits with `4` excluded** (`E-RANGE-004`, `N16cc`), never
  a silent "no index".

## Consequences

- `0.49.0` is a 393-form document, byte-reproducing every `0.48.0` row.
- Its positive fixture `X86-P53-gpr32-mov-index-low` has twelve instructions
  and 63 bytes: both directions, both displacement widths, the low 32-bit
  registers `%eax`/`%edi`, the plain bases `%rax`/`%rdi` and the
  `SIB`-announced `%rsp`/`%rbp` bases. Its `input_sha256` is
  `a9443fe6c106a9e021203d7f420c6481d0f98dd077456e021faa21afd86aeae9` and its
  `output_sha256` is
  `595b6d7550ed40f4e7c3cc0fc62ce33adf3ca44091164f7d46ff96607a9b138f`.
- Negatives pin the version boundary in both directions (`N01cz`, `N01da`), a
  missing index (`N02bs`), the scale field's end (`N03zb`), the register
  window (`N14bg`), the base window (`N14bh`) and the index exclusion
  (`N16cc`).
- `EC-02`, `EC-37` and `EC-38` are revised in place; no new `EC` row and no row
  is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr32`/`r32`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **One row that covers `0`–`15` on all three registers.** The `REX` byte
  would always be present, so the four-byte low case would gain a `40` prefix:
  a five-byte alias of a plan that could have four bytes. One operand shape
  gets one frozen encoding (`INV-02`).
- **Reuse the 64-bit indexed rows.** They carry `REX.W` (`48`) and are five
  and eight bytes; the 32-bit shape is four and seven with no prefix.
- **Accept index `4` and emit `SIB.index = 100`.** That means "no index", so
  the row would encode a different addressing mode than the plan named
  (`INV-07`).
- **Accept register or base `8`–`15` on this row.** The fourth bit has nowhere
  to go without a `REX` byte; truncating it would silently emit `%eax` for
  `%r8d` (`INV-07`).
- **Add the `REX.R`/`REX.B`/`REX.X`/`REX.BX` windows on the 32-bit indexed
  rows now.** Those are four more forms with operand-owned placements and get
  their own slices.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8b 44 08 08` at four bytes | `llvm-mc -show-encoding`, `EXP-0078` §1 | high |
| `ModRM` at byte 1 and the fields at `[11,3]`/`[19,3]`/`[16,3]`/`[22,2]` | `llvm-mc -show-encoding`, `EXP-0078` §2 | high |
| `%rsp`/`%rbp` are legal bases | `llvm-mc -show-encoding`, `EXP-0078` §1 | high |
| `%rsp` is rejected as an index | `llvm-mc`, `EXP-0078` §3 | high |
| the `disp32` rows are seven bytes with `disp32` at `[24,32]` | `llvm-mc -show-encoding`, `EXP-0078` §1 | high |

## Review triggers

- The 32-bit `REX` register windows are requested.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in a displacement is requested.
- The no-base indexed shape is attempted.
- The APX `d5` register window is attempted.
