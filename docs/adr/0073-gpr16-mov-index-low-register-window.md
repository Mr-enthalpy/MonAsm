# ADR-0073: the 16-bit `mov` index/scale rows on the `REX`-less window

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P50` (the index, scale and low-register window over the 16-bit
  indexed `mov` rows, both directions and both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement sits behind the `SIB` byte on the
  `REX`-less indexed 16-bit rows), `EC-37` (the `SIB` index and scale also
  exist without `REX.X`, so the index is three bits and `4` means "no index"),
  `EC-38` (the `REX`-less family reaches the base and index through three-bit
  fields only)

## Context

`0.45.0` gave the 16-bit indexed `mov` rows the `%r8w`–`%r15w` register window
and a four-bit base and index (`ADR-0072`). Those rows carry a `REX` byte
because `REX.R` is fixed in the template. The plain `%ax`–`%di` rows of the
same shape are still missing: `movw 8(%rax,%rcx,1), %ax` is
`66 8b 44 08 08`, but no `0.45.0` row names it.

`EC-37` fixes the index/scale shape: the `SIB` byte's three fields are one
operand each (`base`, `index`, and a two-bit scale carried as field content),
and `index = 4` is the "no index" encoding. `EC-38` fixes the reach: the
`REX`-less legacy row has no extension bits, so its register and base windows
are three bits wide and `r8`–`r15` cannot be reached without a `REX` byte,
which would change the length and therefore the form.

`EXP-0075` measures the shapes and four facts come out:

1. **The rows are one byte shorter with no `REX` byte.** `movw
   8(%rax,%rcx,1), %ax` is `66 8b 44 08 08`: `ModRM = 44` (`mod = 01`,
   `reg = 0`, `r/m = 100`), `SIB = 08` (`scale = 0`, `index = 1`, `base = 0`)
   and the displacement at `[32,8]`. The `disp32` rows are eight bytes
   (`66 8b 84 08 c8 00 00 00`), with the displacement at `[32,32]`.
2. **The register, base and index fields are three bits each.** `movw
   8(%rdi,%rsi,4), %di` is `66 8b 7c b7 08`: `ModRM = 7c` (`reg = 7`,
   `r/m = 100`) and `SIB = b7` (`scale = 2`, `index = 6`, `base = 7`). There
   is no fourth bit to carry, so register `8` and base `8` are
   `E-OPERAND-004` (`N14bb`, `N14bc`), never a silent low three bits.
3. **`%rsp` and `%rbp` are legal bases.** `movw 8(%rsp,%rcx,1), %ax` is
   `66 8b 44 0c 08` (`SIB.base = 100`) and `movw 8(%rbp,%rcx,1), %ax` is
   `66 8b 44 0d 08` (`SIB.base = 101`). Both work because `r/m = 100`
   announces the `SIB` byte and the displacement keeps `mod = 01`.
4. **The index is three bits, and `%rsp` is still not an index.**
   `SIB.index = 100` with no `REX.X` means "no index"; `llvm-mc` rejects
   `8(%rax,%rsp,1)` with `invalid base+index expression`, so index `4` is
   `E-RANGE-004` (`N16bx`).

## Decision

**`0.46.0` appends four rows: two directions × two displacement widths, with
no `REX` byte, three-bit register, base and index fields, `4` excluded from the
index, the scale as two bits of field content and the signed displacement at
`[32,8]` or `[32,32]`.**

| Direction | Displacement | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | `disp8` | `x86:mov/r16-base-index-disp8/legacy` | `66 8b 44 00 00` | 5 | dest `x86.gpr16`/`r16` → `[19,3]`; base `x86.gpr64`/`rm64` → `[24,3]`; index `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm `x86.scale`/`scale2` → `[30,2]`; disp `x86.imm`/`disp8` → `[32,8]` |
| store | `disp8` | `x86:mov/base-index-disp8-r16/legacy` | `66 89 44 00 00` | 5 | src `x86.gpr16`/`r16` → `[19,3]`; base `x86.gpr64`/`rm64` → `[24,3]`; index `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm `x86.scale`/`scale2` → `[30,2]`; disp `x86.imm`/`disp8` → `[32,8]` |
| load | `disp32` | `x86:mov/r16-base-index-disp32/legacy` | `66 8b 84 00 00 00 00 00` | 8 | dest `x86.gpr16`/`r16` → `[19,3]`; base `x86.gpr64`/`rm64` → `[24,3]`; index `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm `x86.scale`/`scale2` → `[30,2]`; disp `x86.imm`/`disp32` → `[32,32]` |
| store | `disp32` | `x86:mov/base-index-disp32-r16/legacy` | `66 89 84 00 00 00 00 00` | 8 | src `x86.gpr16`/`r16` → `[19,3]`; base `x86.gpr64`/`rm64` → `[24,3]`; index `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm `x86.scale`/`scale2` → `[30,2]`; disp `x86.imm`/`disp32` → `[32,32]` |

Four properties follow:

- **The missing `REX` byte moves every field one byte earlier.** `ModRM` is
  byte 2, so its `reg` field is `[19,3]` and its `r/m = 100` announces the
  `SIB` byte at [24,8]: base `[24,3]`, index `[27,3]`, scale `[30,2]`, and the
  displacement at `[32,…]` instead of `[40,…]`. The width is the `form_id`,
  not an operand-driven choice (`INV-04`).
- **Three bits are the whole window.** `%rax`–`%rdi` are reachable;
  `%r8`–`%r15` need `REX.B`/`REX.R`/`REX.X`, which this row does not have, so
  those values are `E-OPERAND-004`. Reaching them is the `0.45.0` row, a
  different form (`EC-38`).
- **The index exclusions are the same as at the wider window.** `4` is the
  one excluded value, because it is the `SIB.index = 100` "no index"
  encoding; accepting it would silently drop the operand (`INV-07`).
  `%r12` is not reachable from this row at all, because its low three bits are
  `100` and there is no `REX.X`.
- **The scale is content, never a multiplier.** `0…3` are the bits for
  ×1/×2/×4/×8; `4` is `E-RANGE-001` (`N03y`), never a truncated `0`.

## Consequences

- `0.46.0` is a 377-form document, byte-reproducing every `0.45.0` row.
- Its positive fixture `X86-P50-gpr16-mov-index-low` has twelve instructions
  and 78 bytes: both directions at both displacement widths, two scales, low
  registers, low bases and the `SIB`-announced `%rsp`/`%rbp` bases.
  `input_sha256` is
  `e6d5037a6edee765b59e609d5f2f2fd39040aecce73c08c98b7674eb6024a424` and
  `output_sha256` is
  `cf3b734c17dd61226541ab6e92281e679abf5a4ff3a5950616035212ccc2f29e`.
- Negatives pin the version boundary in both directions (`N01ct`, `N01cu`),
  a missing index (`N02bp`), the scale field's end (`N03y`), the register
  window's target-type end and its three-bit field (`N14ba`, `N14bb`), the
  base's three-bit field (`N14bc`) and the `%rsp` index exclusion (`N16bx`).
- `EC-02`, `EC-37` and `EC-38` are revised in place. No new `EC` row appears
  and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr16`/`r16`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **Split the base or index into eight rows each.** The three-bit field is the
  window; a form per value would add no byte and no decision (`EC-38`).
- **Accept register `8` and clear the fourth bit.** That would emit the wrong
  register, a silent repair of an illegal operand (`INV-07`).
- **Accept index `4` and drop it.** That is the "no index" encoding, so the
  operand would vanish (`INV-07`).
- **Add a `REX` byte to reach `%r8`–`%r15`.** The length would depend on the
  operand values (`INV-04`); that is the `0.45.0` form.
- **Add the `0x67` address-size prefix or the APX `d5` window now.** Both are
  different forms with their own length and register rules, deferred to their
  own slices.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 8b 44 08 08` at five bytes | `llvm-mc -show-encoding`, `EXP-0075` §1 | high |
| `ModRM`/`SIB` sit at bytes 2/3 with the fields at `[19,3]`/`[24,3]`/`[27,3]`/`[30,2]` | `llvm-mc -show-encoding`, `EXP-0075` §2 | high |
| `%rsp`/`%rbp` are legal bases at `mod = 01` | `llvm-mc -show-encoding`, `EXP-0075` §1/§3 | high |
| `%rsp` is rejected as an index | `llvm-mc`, `EXP-0075` §3 | high |
| the `disp32` rows are eight bytes with `disp32` at `[32,32]` | `llvm-mc -show-encoding`, `EXP-0075` §1 | high |

## Review triggers

- The `REX.B`/`REX.X`/`REX.BX` windows on these rows are requested (they are
  the `0.45.0` forms).
- The `0x67` address-size prefix is attempted.
- The APX `d5` register window is attempted.
- A symbol or relocation in a displacement is requested.
- An EVEX/GPR masked form is attempted.
