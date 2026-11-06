# ADR-0063: the 32-bit `mov` family takes the `%rsp`/`%r12` `SIB` bases

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P40` (the `mod = 00` `SIB` rows of the 32-bit `mov` family,
  over `%rsp` and `%r12`, both directions)
- Supersedes: none
- Superseded by: none
- Revises: `EC-35` (the `SIB` byte now has a `mod = 00` form in the 32-bit
  family as well) and `EC-38` (the 32-bit family's base reach now includes the
  two fixed-base windows)

## Context

`0.35.0` gave the 32-bit `mov` family its first base rows (`ADR-0062`), but
every one of them excludes `%rsp` and `%r12`: their low three bits are `100`,
so a plain `ModRM.r/m` would announce a `SIB` byte rather than name the base.
The family therefore cannot plan `movl (%rsp), %eax` at all, while the byte,
word, 64-bit and SSE families already reach both bases.

`EC-35` is the governing rule: a base whose number is `100` needs
`ModRM.r/m = 100` and a `SIB` byte whose `base` is also `100`, and because the
instruction's length changes, the base must be template content rather than an
operand. `EC-38` adds the second axis: a 32-bit row without a `REX` byte cannot
carry `%r8d`–`%r15d`, so the register reach is its own window split.

`EXP-0065` measures the combination and three facts come out:

1. **The `SIB` byte costs one byte.** `movl (%rsp), %eax` is `8b 04 24`:
   `ModRM = 04` (`mod = 00`, `reg = 000`, `r/m = 100`) and `SIB = 24`
   (`scale = 00`, `index = 100` meaning none, `base = 100`). `%r12` differs
   only in a fixed `REX.B` byte: `41 8b 04 24`.
2. **The register window still splits at `8`.** `movl (%rsp), %r8d` is
   `44 8b 04 24` (`REX.R = 1`) and `movl (%rsp), %r15d` is `44 8b 3c 24`; the
   `%r12` counterparts are `45 8b 04 24` and `45 8b 3c 24`, where `REX.B` is
   fixed and only `REX.R` is a slot.
3. **Each base needs its own row.** The base is not a slot: `%rsp` and `%r12`
   share the low three bits `100`, so with no `REX` byte the two instructions
   are otherwise identical and `REX.B` is the only bit that tells them apart.
   A base operand on these rows is `E-OPERAND-002`, and the general
   `0.35.0` rows keep excluding `4` and `12`.

`llvm-mc` normalises an explicit zero displacement on a `SIB` base
(`movl 0(%rsp), %eax` assembles to `8b 04 24`), so the plan names the row.

## Decision

**`0.36.0` appends eight rows — one per base, direction and register
window — with `ModRM = 04` and `SIB = 24` in the template, the base and its
`REX.B` fixed, and no displacement slot.**

| Direction | Base | Reach | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|---|
| load | `%rsp` | low | `x86:mov/r32-rsp/legacy` | `8b 04 24` | 3 | dest `x86.gpr32`/`r32` → `[11,3]` |
| store | `%rsp` | low | `x86:mov/rsp-r32/legacy` | `89 04 24` | 3 | src `x86.gpr32`/`r32` → `[11,3]` |
| load | `%r12` | low | `x86:mov/r32-r12/legacy` | `41 8b 04 24` | 4 | dest `x86.gpr32`/`r32` → `[19,3]` |
| store | `%r12` | low | `x86:mov/r12-r32/legacy` | `41 89 04 24` | 4 | src `x86.gpr32`/`r32` → `[19,3]` |
| load | `%rsp` | `REX.R` | `x86:mov/r32-ext-rsp/legacy` | `44 8b 04 24` | 4 | dest `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7) |
| store | `%rsp` | `REX.R` | `x86:mov/rsp-r32-ext/legacy` | `44 89 04 24` | 4 | src `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7) |
| load | `%r12` | `REX.R` | `x86:mov/r32-ext-r12/legacy` | `45 8b 04 24` | 4 | dest `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7) |
| store | `%r12` | `REX.R` | `x86:mov/r12-r32-ext/legacy` | `45 89 04 24` | 4 | src `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7) |

Four properties follow:

- **The base is the form, not an operand value.** `%rsp` is `SIB = 24` and
  `%r12` is `SIB = 24` plus `REX.B = 1`; the plan names the base through the
  `form_id`, so no value can insert a byte (`INV-04`).
- **The register window is still the form.** The low rows carry `reg = 0…7`
  in three bits; the `-ext` rows carry `reg = 8…15` through `REX.R` and
  exclude `0…7`, so a register names exactly one row.
- **Both bases keep the same `SIB` byte.** The four `%rsp` rows and the four
  `%r12` rows differ only in `REX.B`, which is why `%r12` costs four bytes at
  every window and `%rsp` three in the low row.
- **There is no displacement slot.** `disp` is `E-OPERAND-002`; the
  `disp8`/`disp32` `SIB` shapes remain the rows to come.

## Consequences

- `0.36.0` is a 309-form document, byte-reproducing every `0.35.0` row.
- Its positive fixture `X86-P40-gpr32-mov-mem-sib-nodisp` has sixteen
  instructions and 60 bytes: each of the eight rows twice, so each base,
  direction and register window appears at both ends (`%eax`/`%edi` and
  `%r8d`/`%r15d`).
- Negatives pin the version boundary in both directions (`N01bz`, `N01ca`), a
  `base` operand (`N02be`), a `disp` operand (`N02bf`), the 3-bit and 4-bit
  field ends (`N14am`, `N14al`) and the `REX.R` window floor (`N16aw`).
- `EC-35` is revised in place: the `SIB` byte now has a `mod = 00` form in the
  32-bit family as well. `EC-38` is revised so its 32-bit paragraph no longer
  says every row excludes `%rsp`/`%r12`; the plain-base rows do, and these
  eight rows are the other half. No new `EC` row appears and no row is
  renumbered.
- No schema, loader or materializer change: the rows use the existing
  `x86.gpr32`/`r32` kind and the placement shapes the byte and 64-bit fixed-base
  rows already use.

## Alternatives rejected

- **One row per base and direction with a 4-bit register slot.** The register's
  fourth bit would have to insert a `REX` byte when it is set, making the
  length depend on an operand value (`INV-04`).
- **Accept `%rsp`/`%r12` on the `0.35.0` plain-base rows and emit the `SIB`
  byte from the operand.** The same length problem, and `EC-35` already says
  the shape is the form.
- **One `%rsp`/`%r12` pair with a base operand.** `SIB.base` at `mod = 00` is
  a value `0…7`/`8…15` naming the base, but then the base is an operand that
  happens to pick among two templates, which is `INV-02`; the family's existing
  fixed-base rows are the precedent.
- **Take the `disp8`/`disp32` `SIB` shapes here.** The displacement axis is
  `EC-02` and those rows do not exist yet.
- **Take the same shape at 16 or 8 bits.** The word family splits around the
  `0x66` prefix and the byte family splits four ways on the high-byte rule;
  both are already fully covered for `mod = 00` and this slice does not touch
  them.
- **Take the `0x67` address-size prefix or the APX `d5` register window.**
  Neither is part of the base-reach question.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8b 04 24` / `89 04 24` at three bytes | `llvm-mc -show-encoding`, `EXP-0065` §1 | high |
| `41`/`44`/`45` grow the row to four bytes | `llvm-mc -show-encoding`, `EXP-0065` §2 | high |
| `ModRM = 04`, `SIB = 24`, no displacement | `llvm-mc -show-encoding`, `EXP-0065` §2 | high |
| `%rbp`/`%r13` stay on the zero-displacement shape | `llvm-mc -show-encoding`, `EXP-0065` §3 | high |
| a `(register, base)` pair names one row | the exclusion lists, `EXP-0065` §4 | high |

## Review triggers

- A displacement is requested on these rows.
- An index or scale operand is requested at 32-bit width.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in an address is requested.
- The same shape is attempted at 16 or 8 bits.
- The APX `d5` register window is attempted.
