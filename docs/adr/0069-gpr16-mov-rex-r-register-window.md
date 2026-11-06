# ADR-0069: the 16-bit `mod = 00` `mov` rows take the `REX.R` register window

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P46` (the `%r8w`–`%r15w` register window over the 16-bit
  `mod = 00` `mov` rows, both directions, both base windows and both `SIB`
  bases)
- Supersedes: none
- Superseded by: none
- Revises: `EC-06` (the 16-bit register field now has a `REX.R` window on the
  base rows, not only on the `abs32` rows)

## Context

`0.41.0` gave the 16-bit `mov` family its `mod = 00` rows (`ADR-0068`), but
every one of them holds only `%ax`–`%di`: `movw (%rax), %r8w` is not
plannable. The register-direct and `abs32` rows already reach `%r8w`–`%r15w`
through `REX.R`, so the window exists on two other shapes and is missing on
this one.

`EC-06` is the governing rule: REX presence and the `W`/`R`/`X`/`B` bits are
part of the form, and a register class that needs a bit cannot share a row
with one that does not, because the instruction's length would depend on the
operand. `EC-38` keeps the base window separate: the low base rows reach
`0`–`7` and the `-ext` base rows reach `8`–`15`.

`EXP-0071` measures the shapes and four facts come out:

1. **`REX.R` extends the register field.** `movw (%rax), %r8w` is
   `66 44 8b 00`: the `0x66` prefix, `REX = 44` (`R = 1`), the opcode and
   `ModRM = 00`, with the register's fourth bit at `[10,1]` and its low three
   bits at `[27,3]`.
2. **Both extension bits share one byte.** `movw (%r8), %r8w` is
   `66 45 8b 00`: `REX = 45` is `R = 1` and `B = 1`, so the register and the
   base are both extended and the row length is unchanged at four bytes.
3. **The low register range is excluded.** A value `0`–`7` on an `-ext` row
   would clear the fixed `REX.R` bit and emit a different instruction, so the
   slot excludes it (`E-RANGE-004`).
4. **The `SIB` bases compose unchanged.** `movw (%rsp), %r8w` is
   `66 44 8b 04 24` and `movw (%r12), %r8w` is `66 45 8b 04 24`: the same
   `SIB = 24`, with `REX.B` separating the two bases and `REX.R` the register.

## Decision

**`0.42.0` appends eight rows: two directions × (one plain low-base row, one
plain `-ext`-base row and two fixed `SIB` bases), with `REX.R` fixed in the
template and the low register window excluded.**

| Direction | Base | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | plain, `0`–`7` | `x86:mov/r16-ext-base/legacy` | `66 44 8b 00` | 4 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) |
| store | plain, `0`–`7` | `x86:mov/base-r16-ext/legacy` | `66 44 89 00` | 4 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) |
| load | plain, `8`–`15` | `x86:mov/r16-ext-base-ext/legacy` | `66 45 8b 00` | 4 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12, 13) |
| store | plain, `8`–`15` | `x86:mov/base-ext-r16-ext/legacy` | `66 45 89 00` | 4 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12, 13) |
| load | `%rsp` | `x86:mov/r16-ext-rsp/legacy` | `66 44 8b 04 24` | 5 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base fixed to `%rsp` |
| store | `%rsp` | `x86:mov/rsp-r16-ext/legacy` | `66 44 89 04 24` | 5 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base fixed to `%rsp` |
| load | `%r12` | `x86:mov/r16-ext-r12/legacy` | `66 45 8b 04 24` | 5 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base fixed to `%r12` |
| store | `%r12` | `x86:mov/r12-r16-ext/legacy` | `66 45 89 04 24` | 5 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base fixed to `%r12` |

Four properties follow:

- **The register window is the form.** A low register on an `-ext` row is
  `E-RANGE-004`; a register past `15` is `E-OPERAND-004`. The row never
  widens or clears its fixed bit (`INV-04`).
- **The two extension bits share one byte.** `REX.R` is `[10,1]` and `REX.B`
  is `[8,1]`; on the combined rows both are fixed at `1`, which is why the
  template byte is `45`.
- **The base window stays separate.** The plain rows keep the `0`–`7` and
  `8`–`15` split from `0.41.0`; only the register field is new.
- **The `SIB` rows only gain `REX.R`.** The base is still fixed, because
  `%rsp` and `%r12` share `SIB = 24`.

## Consequences

- `0.42.0` is a 353-form document, byte-reproducing every `0.41.0` row.
- Its positive fixture `X86-P46-gpr16-mov-mem-nodisp-rex-r` has fourteen
  instructions and 62 bytes: the four plain rows twice, at both ends of the
  register window (`%r8w`/`%r15w`), plus the four fixed-base rows once at
  `%r8w` and the two `%r12` rows again at `%r15w`.
- Negatives pin the version boundary in both directions (`N01cl`, `N01cm`), a
  supplied displacement (`N02bl`), the register field's ends (`N14av`,
  `N16bm`), and the `%rsp`/`%rbp` base exclusions on the new rows (`N16bn`,
  `N16bo`).
- `EC-06` is revised in place. No new `EC` row appears and no row is
  renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr16`/`r16` and `x86.gpr64`/`rm64` kinds and the `REX.R` placement
  the `abs32` rows already use.

## Alternatives rejected

- **Let one row accept `0`–`15` and set `REX.R` when the value is high.**
  The length would depend on the operand (`INV-04`); `EC-06` says the REX
  presence is the form.
- **Fold the low-base and `-ext`-base rows together.** `REX.B` is fixed in
  the template, so the two base windows must stay disjoint (`EC-38`).
- **Add the register window to the `disp8`/`disp32` shapes here.** Those are
  separate displacement shapes and get their own slices.
- **Read the register number to choose `REX.R` or `REX.B`.** One byte carries
  both bits; the slots are separate and the encoder never chooses.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 44 8b 00` at four bytes | `llvm-mc -show-encoding`, `EXP-0071` §1 | high |
| `REX = 45` carries both bits at four bytes | `llvm-mc -show-encoding`, `EXP-0071` §2 | high |
| a low register on an `-ext` row is rejected | plan validation, `EXP-0071` §4 | high |
| `%rsp`/`%r12` differ only in `REX.B` | `llvm-mc -show-encoding`, `EXP-0071` §4 | high |

## Review triggers

- A `disp` operand is requested on these rows.
- The register window is requested on the `disp8`/`disp32` shapes.
- An index or scale operand is requested.
- The `0x67` address-size prefix is attempted.
- The APX `d5` register window is attempted.
