# ADR-0074: the low-register 16-bit `mov` indexed rows take the `REX.B` and `REX.X` windows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P51` (the base and index extension windows over the 16-bit
  indexed `mov` rows whose register stays in `%ax`–`%di`, both directions and
  both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement moves behind the `REX` byte again on these
  rows), `EC-37` (the base or the index, not both, carries a fourth bit), and
  `EC-38` (the window split: a `REX` byte for the base or the index keeps the
  register at three bits)

## Context

`0.46.0` gave the 16-bit `mov` index/scale rows the `REX`-less low-register
window (`ADR-0073`) and `0.45.0` gave the `%r8w`–`%r15w` register window a
four-bit base and index (`ADR-0072`). Between them sits a shape neither row
names: a low register with an extended base or an extended index, e.g.
`movw 8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08`, but no row plans it.

`EC-38` fixes the rule: each encoding family reaches a register window with the
extension bits its prefix carries. A row whose register is low has no `REX.R`,
but its base or its index can still gain a fourth bit from a `REX` byte whose
remaining bits are constant; the operand that gains it is the form's property,
not a value the encoder chooses (`INV-02`).

`EXP-0076` measures the shapes and five facts come out:

1. **The `REX.B` base window is one fixed bit.** `movw 8(%r8,%rcx,1), %ax` is
   `66 41 8b 44 08 08`: `REX = 41` (`B = 1`), `ModRM = 44` (`mod = 01`,
   `reg = 0`, `r/m = 100`), `SIB = 08` (scale `0`, index `1`, base `0`) and the
   displacement at `[40,8]`. The register stays three bits at `[27,3]`.
2. **The `REX.X` index window is one fixed bit.** `movw 8(%rax,%r9,1), %ax` is
   `66 42 8b 44 08 08` (`REX = 42`, `X = 1`), and the index's low three bits
   carry the rest: `movw 8(%rdi,%r15,8), %di` is `66 42 8b 7c ff 08`
   (`SIB = ff`: scale `3`, index `7`, base `7`).
3. **`%rsp`/`%r12`/`%rbp`/`%r13` stay legal bases.** `movw 8(%r12,%rcx,1), %ax`
   is `66 41 8b 44 0c 08` (`SIB.base = 100` behind `REX.B`),
   `movw 8(%rsp,%r9,1), %ax` is `66 42 8b 44 0c 08` (`SIB.base = 100`, no
   `REX.B`), and `movw 8(%rbp,%r9,1), %ax` is `66 42 8b 44 0d 08`
   (`SIB.base = 101` at `mod = 01`).
4. **The index exclusion is unchanged.** `SIB.index = 100` still means "no
   index"; `llvm-mc` rejects `8(%rax,%rsp,1)`, so index `4` is
   `E-RANGE-004`. With `REX.X = 1` the same low bits are `%r12`:
   `movw 8(%rax,%r12,1), %ax` is `66 42 8b 44 20 08`.
5. **The displacement follows the `SIB` byte.** The `disp32` rows are nine
   bytes with four bytes at `[40,32]`:
   `66 41 8b 84 08 c8 00 00 00` and `66 42 8b 84 08 c8 00 00 00`.

## Decision

**`0.47.0` appends eight rows: two windows × two directions × two displacement
widths.** The `-base-ext` rows fix `REX.B = 1` and narrow the base slot to
`8`–`15`; the `-index-ext` rows fix `REX.X = 1` and narrow the index slot to
`8`–`15`. Every row keeps the register at `[27,3]` (low window only), the base
at `[32,3]`, the index at `[35,3]`, the scale at `[38,2]` and the signed
displacement at `[40,8]` or `[40,32]`.

| Direction | Window | Displacement | `form_id` | Template | Length |
|---|---|---|---|---|---|
| load | `REX.B` base | `disp8` | `x86:mov/r16-base-ext-index-disp8/legacy` | `66 41 8b 44 00 00` | 6 |
| store | `REX.B` base | `disp8` | `x86:mov/base-ext-index-disp8-r16/legacy` | `66 41 89 44 00 00` | 6 |
| load | `REX.B` base | `disp32` | `x86:mov/r16-base-ext-index-disp32/legacy` | `66 41 8b 84 00 00 00 00 00` | 9 |
| store | `REX.B` base | `disp32` | `x86:mov/base-ext-index-disp32-r16/legacy` | `66 41 89 84 00 00 00 00 00` | 9 |
| load | `REX.X` index | `disp8` | `x86:mov/r16-base-index-ext-disp8/legacy` | `66 42 8b 44 00 00` | 6 |
| store | `REX.X` index | `disp8` | `x86:mov/base-index-ext-disp8-r16/legacy` | `66 42 89 44 00 00` | 6 |
| load | `REX.X` index | `disp32` | `x86:mov/r16-base-index-ext-disp32/legacy` | `66 42 8b 84 00 00 00 00 00` | 9 |
| store | `REX.X` index | `disp32` | `x86:mov/base-index-ext-disp32-r16/legacy` | `66 42 89 84 00 00 00 00 00` | 9 |

Four properties follow:

- **The register is not in the window.** `%ax`–`%di` only; register `8`–`15`
  would need `REX.R`, which these rows do not carry, so it is
  `E-OPERAND-004` (`N14bd`). That is the `0.45.0` row, a different form.
- **The extended operand's fourth bit is operand-owned.** The slot lists the
  `REX` bit as its most significant placement (`[8,1]` for the base, `[9,1]`
  for the index) exactly as the `0.45.0` slots do, and the low window is
  excluded from that slot, so the row cannot be handed a value that would
  clear the fixed bit (`E-RANGE-004`, `N16by`/`N16bz`).
- **The other operand stays three bits.** On a `-base-ext` row the index is
  `0`–`7` except `4`; on an `-index-ext` row the base is `0`–`7`. A value that
  does not fit is `E-OPERAND-004` (`N14be`), never a silent low three bits.
- **The displacement is behind the `SIB` byte again.** One prefix byte more
  than the `0.46.0` rows, so the displacement moves from `[32,…]` to
  `[40,…]`; the width is the `form_id` (`INV-04`).

## Consequences

- `0.47.0` is a 385-form document, byte-reproducing every `0.46.0` row.
- Its positive fixture `X86-P51-gpr16-mov-index-ext-window` has twelve
  instructions and 90 bytes: both windows, both directions, both displacement
  widths, the base at `%r8`/`%r15` and the index at `%r9`/`%r15`. Its
  `input_sha256` is
  `f0ec514ffdf8b3778ba3e3f10751c6e014bd1bfb5d8d674651e6465da52e92fb` and
  `output_sha256` is
  `a3ef1ce4b2d73280b701be00aaef0b559f4b552322f561aaef1feb47145d51ea`.
- Negatives pin the version boundary in both windows (`N01cv`, `N01cw`), a
  missing index (`N02bq`), the scale field's end (`N03z`), the register
  field's end (`N14bd`), the low base's field end (`N14be`), and both window
  floors (`N16by`, `N16bz`).
- `EC-02`, `EC-37` and `EC-38` are revised in place; `EC-06` is not (the `REX`
  byte's geometry is unchanged). No new `EC` row and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr16`/`r16`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **Let one `-ext` row accept `0`–`15` for the extended operand.** The `REX`
  byte would then always be present, so `movw 8(%rax,%rcx,1), %ax` would gain
  a `40` prefix: a six-byte alias of the five-byte `0.46.0` row, and the plan
  could name either byte string for one instruction. One operand shape gets
  one frozen encoding, so the window is a slot exclusion and the low case
  stays on its own row.
- **Accept a low base on a `-base-ext` row and set `REX.B` anyway.** That
  emits `%r8`–`%r15` for a plan that named `%rax`–`%rdi`, a silent repair
  (`INV-07`).
- **Accept index `4` on an `-index-ext` row.** `SIB.index = 100` with
  `REX.X = 1` is `%r12`, not "no index"; accepting `4` would emit `%r12` for
  `%rsp` (`INV-07`).
- **Add the `REX.BX` window now.** Both extension bits at once is its own
  pair of operand windows and gets its own slice.
- **Add the `0x67` address-size prefix or the APX `d5` window now.** Both are
  different forms with their own length and register rules.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 41 8b 44 08 08` at six bytes | `llvm-mc -show-encoding`, `EXP-0076` §1 | high |
| `66 42 8b 44 08 08` for the index window | `llvm-mc -show-encoding`, `EXP-0076` §1 | high |
| `ModRM`/`SIB` at bytes 2/3 with the fields at `[27,3]`/`[32,3]`/`[35,3]`/`[38,2]` | `llvm-mc -show-encoding`, `EXP-0076` §2 | high |
| `%r12`/`%rsp`/`%rbp` are legal bases | `llvm-mc -show-encoding`, `EXP-0076` §1/§3 | high |
| `%rsp` is rejected as an index | `llvm-mc`, `EXP-0076` §3 | high |
| the `disp32` rows are nine bytes with `disp32` at `[40,32]` | `llvm-mc -show-encoding`, `EXP-0076` §1 | high |

## Review triggers

- The `REX.BX` window on this shape is requested.
- The `0x67` address-size prefix is attempted.
- The APX `d5` register window is attempted.
- A symbol or relocation in a displacement is requested.
- An EVEX/GPR masked form is attempted.
