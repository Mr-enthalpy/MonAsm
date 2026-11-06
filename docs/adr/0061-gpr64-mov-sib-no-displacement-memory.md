# ADR-0061: the 64-bit `mov` rows take the `SIB` bases at `mod = 00`

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P38` (the `mod = 00` 64-bit `mov` rows whose base is `%rsp` or
  `%r12`, both directions)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0060` §Review triggers (its first item, the `%rsp`/`%r12`
  `SIB` rows); `EC-35` (the `SIB` byte now appears at `mod = 00` in the
  64-bit family too)

## Context

`ADR-0060` gave the 64-bit `mov` family the `mod = 00` shape but excluded four
bases: `%rbp`/`%r13` because `r/m = 101` is RIP-relative at that `mod`, and
`%rsp`/`%r12` because `r/m = 100` announces a `SIB` byte the two rows have no
room for. `EC-35` had already made the `%rsp`/`%r12` pair a fixed-base row in
every other memory family — one row per base, base and `SIB` byte in the
template — and `ADR-0059` had just done the same for the byte family's
`mod = 00` shape.

`EXP-0063` measures the shape and four facts come out:

1. **The shape spends one `SIB` byte.** `movq (%rsp), %rax` is `48 8b 04 24`
   and `movq (%r12), %rax` is `49 8b 04 24`: four bytes, with `ModRM = 04`
   (`mod = 00`, `reg = 000`, `r/m = 100`) and `SIB = 24` (`scale = 00`,
   `index = 100` meaning none, `base = 100`).
2. **The `%rsp` and `%r12` rows differ only in `REX.B`.** The base is not an
   operand, so `REX.B` can be a template constant: `48` for `%rsp`, `49` for
   `%r12`. The register keeps the four-bit field (`REX.R` at `[2,1]` plus
   `[19,3]`), so `movq (%rsp), %r8` is `4c 8b 04 24` and
   `movq (%r12), %r8` is `4d 8b 04 24`.
3. **One row per base and direction covers all sixteen registers.** Because
   `REX.R` is a slot and the base is fixed, there is no register window split,
   unlike the byte and 16-bit families.
4. **The displacement axis is untouched.** `movq 8(%rsp), %rax` is
   `48 8b 44 24 08` and `movq 8(%r12), %rax` is `49 8b 44 24 08` — the
   existing `disp8` rows (`EC-02`, `EC-35`), not this slice.

## Decision

**`0.34.0` appends four rows — one per base and direction — with the base and
the `SIB` byte in the template.**

| Direction | `form_id` | Template | Length | Slots |
|---|---|---|---|---|
| load | `x86:mov/r64-rsp/legacy` | `48 8b 04 24` | 4 | dest `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` |
| store | `x86:mov/rsp-r64/legacy` | `48 89 04 24` | 4 | src `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` |
| load | `x86:mov/r64-r12/legacy` | `49 8b 04 24` | 4 | dest `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` |
| store | `x86:mov/r12-r64/legacy` | `49 89 04 24` | 4 | src `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` |

Three properties follow:

- **The base is not an operand.** A plan that supplies a `base` or `disp`
  operand is `E-OPERAND-002`, not a value the row would compare or encode.
- **`REX.W` and `REX.B` are template constants.** Neither depends on an
  operand, so neither row can lose the 64-bit width or the base's fourth bit
  (`INV-04`).
- **`REX.R` is the only bit the operand owns**, exactly as in the plain-base
  rows of `ADR-0060`; the register field therefore stays four bits wide.

## Consequences

- `0.34.0` is a 295-form document, byte-reproducing every `0.33.0` row.
- Its positive fixture `X86-P38-gpr64-mov-mem-sib-nodisp` has eight
  instructions and 32 bytes: both bases and both directions over `%rax` and
  `%r8`, so every `REX.R` value the template allows appears (`48`/`4c` under
  `%rsp`, `49`/`4d` under `%r12`).
- Negatives pin the version boundary in both directions (`N01bv`, `N01bw`), a
  `base` operand (`N02bb`), a `disp` operand (`N02bc`), and register `16` past
  the four-bit field (`N14ai`).
- `EC-35` is revised in place: the `SIB` byte now appears at `mod = 00` in the
  64-bit family, as it already did in the byte family. No new `EC` row
  appears and no row is renumbered.
- No schema, loader or materializer change: the rows are one-slot forms with
  the base fixed in the template, the shape `ADR-0059` already used.

## Alternatives rejected

- **Give the row a base operand and let `REX.B` carry it.** Then `%rsp` and
  `%r12` need one row that reads the base's value to set a template bit, and
  `%rbp`/`%r13` cannot join it at all; `EC-35` already fixes one row per base.
- **Fold `%rsp`/`%r12` into the plain-base rows with a conditional `SIB`.**
  The length would then depend on a value, which is `INV-04`.
- **Take the `disp8`/`disp32` `SIB` rows here.** They already exist
  (`x86:mov/r64-rsp-disp8/legacy` and its siblings); this slice is the
  displacement-free shape only.
- **Take the same shape at 32, 16 or 8 bits.** The byte family already has it
  (`ADR-0059`); the 32-bit family has no base rows yet and the 16-bit family
  splits by base window, so each is a separate design question.
- **Take the `0x67` address-size prefix, `REX.X` with an index, or `moffs`.**
  None is part of this shape.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `48 8b 04 24` / `49 8b 04 24` at four bytes | `llvm-mc -show-encoding`, `EXP-0063` §1 | high |
| the two bases differ only in `REX.B` (`48`/`49`) | `llvm-mc -show-encoding`, `EXP-0063` §2 | high |
| `REX.R` carries the register (`4c 8b 04 24`) | `llvm-mc -show-encoding`, `EXP-0063` §2 | high |
| `SIB = 24` and `ModRM = 04` | `llvm-mc -show-encoding`, `EXP-0063` §2 | high |
| `%rbp`/`%r13` stay on the `disp8` rows | `llvm-mc -show-encoding`, `EXP-0063` §3 | high |

## Review triggers

- The `disp8`/`disp32` `SIB` rows are asked to accept a zero displacement.
- The `REX.X` index or scale is requested at 64-bit width.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- `moffs` for the 64-bit width is requested.
- The APX `d5` register window is attempted.
- The same shape is attempted at 32 or 16 bits.
