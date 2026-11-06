# ADR-0071: the 16-bit `disp32` `mov` rows take the `REX.R` register window

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P48` (the `%r8w`–`%r15w` register window over the 16-bit
  `disp32` `mov` rows, both directions, both base windows and both `SIB`
  bases)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `disp32` shape now has a `REX.R` window at 16-bit
  width), `EC-06` (the register field's `REX.R` window now also exists on the
  `disp32` rows), `EC-38` (the base window is unchanged but the register
  window is now separate from it)

## Context

`0.43.0` gave the 16-bit `disp8` `mov` rows the `%r8w`–`%r15w` register
window (`ADR-0070`). The `disp32` shape still holds only `%ax`–`%di`:
`movw 200(%rax), %r8w` is not plannable, although `movw 200(%rax), %ax` is
`66 8b 80 c8 00 00 00` and `movw 8(%rax), %r8w` is `66 44 8b 40 08`.

`EC-02` fixes the displacement shape: `mod = 10` with four signed bytes at
the row's own offset. `EC-06` fixes the register window: the `REX.R` bit is
part of the form, so a low register value cannot share a row with an
extended one. `EC-38` keeps the base window separate; at `mod = 10` the base
window matches `mod = 01`: `%rbp`/`%r13` are legal bases because `r/m = 101`
means a base with a displacement.

`EXP-0073` measures the shapes and four facts come out:

1. **The `disp32` field moves with the `REX` byte.** `movw 200(%rax), %r8w`
   is `66 44 8b 80 c8 00 00 00`: the `0x66` prefix, `REX = 44` (`R = 1`),
   the opcode, `ModRM = 80` (`mod = 10`, `reg = 0`, `r/m = 0`) and the
   displacement at `[32,32]`. The register's fourth bit is `[10,1]` and its
   low three bits `[27,3]`, as on the shorter rows.
2. **Both extension bits share one byte.** `movw 200(%r8), %r8w` is
   `66 45 8b 80 c8 00 00 00`: `REX = 45` is `R = 1` and `B = 1`, and the row
   stays eight bytes.
3. **The `SIB` rows add one byte.** `movw 200(%rsp), %r8w` is
   `66 44 8b 84 24 c8 00 00 00` and `movw 200(%r12), %r8w` is
   `66 45 8b 84 24 c8 00 00 00`, with the displacement at `[40,32]`.
4. **The displacement end is four bytes.** `2147483647` is
   `ff ff ff 7f` and `-2147483648` is `00 00 00 80`; `2147483648` is
   rejected by the assembler, so it is `E-RANGE-001`, never a silent wrap.

## Decision

**`0.44.0` appends eight rows: two directions × (one plain low-base row, one
plain `-ext`-base row and two fixed `SIB` bases), with `REX.R` fixed in the
template, the low register window excluded, and the signed `disp32` at
`[32,32]` (plain) or `[40,32]` (`SIB`).**

| Direction | Base | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | plain, `0`–`7` | `x86:mov/r16-ext-base-disp32/legacy` | `66 44 8b 80 00 00 00 00` | 8 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp `x86.imm`/`disp32` → `[32,32]` |
| store | plain, `0`–`7` | `x86:mov/base-disp32-r16-ext/legacy` | `66 44 89 80 00 00 00 00` | 8 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp `x86.imm`/`disp32` → `[32,32]` |
| load | plain, `8`–`15` | `x86:mov/r16-ext-base-ext-disp32/legacy` | `66 45 8b 80 00 00 00 00` | 8 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12); disp `x86.imm`/`disp32` → `[32,32]` |
| store | plain, `8`–`15` | `x86:mov/base-ext-disp32-r16-ext/legacy` | `66 45 89 80 00 00 00 00` | 8 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12); disp `x86.imm`/`disp32` → `[32,32]` |
| load | `%rsp` | `x86:mov/r16-ext-rsp-disp32/legacy` | `66 44 8b 84 24 00 00 00 00` | 9 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp32` → `[40,32]` |
| store | `%rsp` | `x86:mov/rsp-disp32-r16-ext/legacy` | `66 44 89 84 24 00 00 00 00` | 9 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp32` → `[40,32]` |
| load | `%r12` | `x86:mov/r16-ext-r12-disp32/legacy` | `66 45 8b 84 24 00 00 00 00` | 9 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp32` → `[40,32]` |
| store | `%r12` | `x86:mov/r12-disp32-r16-ext/legacy` | `66 45 89 84 24 00 00 00 00` | 9 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp32` → `[40,32]` |

Four properties follow:

- **The register window is the form.** A low register on an `-ext` row is
  `E-RANGE-004`; a register past `15` is `E-OPERAND-004`.
- **The displacement is still four bytes.** `-2147483648…2147483647` fits
  the slot; `2147483648` is `E-RANGE-001`, never a silent wrap.
- **The base window matches `mod = 01`.** `%rbp`/`%r13` are legal bases;
  only `%rsp` (`r/m = 100`) needs the fixed `SIB` row. The `-ext` row still
  excludes `0`–`7` (the fixed `REX.B` bit) and `%r12`.
- **The `SIB` rows only gain `REX.R`.** The base stays fixed, because `%rsp`
  and `%r12` share `SIB = 24`, and the displacement moves from `[32,32]` to
  `[40,32]`.

## Consequences

- `0.44.0` is a 369-form document, byte-reproducing every `0.43.0` row.
- Its positive fixture `X86-P48-gpr16-mov-mem-disp32-rex-r` has fourteen
  instructions and 118 bytes: the four plain rows twice, at both ends of the
  register window (`%r8w`/`%r15w`), plus the four fixed-base rows once at
  `%r8w` and the two `%r12` rows again at `%r15w`.
- Negatives pin the version boundary in both directions (`N01cp`, `N01cq`),
  a missing displacement (`N02bn`), the displacement end (`N03w`), the
  register field's ends (`N14ax`, `N16bs`), and the `%rsp`/`%rbp` base cases
  on the new rows (`N16bt`, `N16bu`).
- `EC-02`, `EC-06` and `EC-38` are revised in place. No new `EC` row appears
  and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr16`/`r16`, `x86.gpr64`/`rm64` and `x86.imm`/`disp32` kinds and the
  `REX.R` placement the `abs32` rows already use.

## Alternatives rejected

- **Let one row accept `0`–`15` and set `REX.R` when the value is high.**
  The length would depend on the operand (`INV-04`); `EC-06` says the REX
  presence is the form.
- **Fold the low-base and `-ext`-base rows together.** `REX.B` is fixed in
  the template, so the two base windows must stay disjoint (`EC-38`).
- **Widen the displacement slot past the signed 32-bit span.** That is a
  different form and would make `2147483648` succeed silently (`INV-07`).
- **Reuse the `disp8` template with four displacement bytes inserted.** The
  `ModRM` byte differs (`80` vs `40`), so it is a distinct row.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 44 8b 80 c8 00 00 00` at eight bytes | `llvm-mc -show-encoding`, `EXP-0073` §1 | high |
| `REX = 45` carries both bits at eight bytes | `llvm-mc -show-encoding`, `EXP-0073` §2 | high |
| the `SIB` rows are nine bytes with `disp32` at `[40,32]` | `llvm-mc -show-encoding`, `EXP-0073` §3 | high |
| `2147483648` is rejected by the assembler | `llvm-mc -show-encoding`, `EXP-0073` §4 | high |

## Review triggers

- An index or scale operand is requested.
- The `0x67` address-size prefix is attempted.
- The APX `d5` register window is attempted.
- A symbol or relocation in a displacement is requested.
