# ADR-0068: the 16-bit `mov` family takes its base rows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P45` (the `mod = 00` 16-bit `mov` rows over a plain base and
  over the `%rsp`/`%r12` `SIB` bases, both directions)
- Supersedes: none
- Superseded by: none
- Revises: `EC-35` (the `SIB` byte now has a `mod = 00` form in the 16-bit
  family as well) and `EC-38` (the 16-bit family's base reach now has a
  `mod = 00` window, and `REX.B` still changes the length)

## Context

The 16-bit `mov` family reached memory only through `mod = 01` and `mod = 10`
(`0.8.0`, `ADR-0044`, `ADR-0045`, `ADR-0046`): `movw 8(%rax), %ax` is
`66 8b 40 08` and `movw 8(%rsp), %ax` is `66 8b 44 24 08`. It has no
`mod = 00` rows, so `movw (%rax), %ax` cannot be planned. The 8-, 32- and
64-bit families each gained their `mod = 00` rows later (`ADR-0058`,
`ADR-0060`–`ADR-0063`); the 16-bit family was the one left behind.

`EC-38` is the governing rule: a legacy row has no `REX` byte, so a register
number above `7` changes the instruction's *length* and therefore needs its
own row. `EC-35` is the `SIB` rule: `%rsp` and `%r12` share the low three bits
`100`, so each needs its own fixed-base rows and the base cannot be a plan
operand.

`EXP-0070` measures the shapes and four facts come out:

1. **`mod = 00` drops the displacement and, for a plain base, keeps
   `r/m = base`.** `movw (%rax), %ax` is `66 8b 00`: the `0x66` operand-size
   prefix, `ModRM = 00` (`mod = 00`, `reg = 000`, `r/m = 000`). The base is a
   slot at `[16,3]`.
2. **`REX.B` still costs a byte.** `movw (%r8), %ax` is `66 41 8b 00` and
   `movw (%r15), %ax` is `66 41 8b 07`: four bytes, with the `REX` byte after
   the `0x66` prefix, so the base slot moves to `[8,1]` + `[24,3]`.
3. **At `mod = 00` `%rbp`/`%r13` are *not* plain bases.** `r/m = 101` means
   `rip`-relative (or `disp32` behind `REX.B`), so `movw (%rbp), %ax` is
   `66 8b 45 00` (`mod = 01`, a zero displacement) and `movw (%r13), %ax` is
   `66 41 8b 45 00`. They stay out of these rows.
4. **The `SIB` bases are fixed in the form.** `movw (%rsp), %ax` is
   `66 8b 04 24` and `movw (%r12), %ax` is `66 41 8b 04 24`: `ModRM = 04` and
   `SIB = 24`, the same shape the 8-, 32- and 64-bit families use, with
   `REX.B` the only difference between the two bases.

## Decision

**`0.41.0` appends eight rows — four over a plain base (two directions × two
base windows) and four over the fixed `%rsp`/`%r12` bases (two directions × two
bases) — with `mod = 00` in the template and no displacement slot.**

| Direction | Base | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | plain, `0`–`7` | `x86:mov/r16-base/legacy` | `66 8b 00` | 3 | dest `x86.gpr16`/`r16` → `[19,3]`; base `x86.gpr64`/`rm64` → `[16,3]` (excl 4, 5) |
| store | plain, `0`–`7` | `x86:mov/base-r16/legacy` | `66 89 00` | 3 | src `x86.gpr16`/`r16` → `[19,3]`; base `x86.gpr64`/`rm64` → `[16,3]` (excl 4, 5) |
| load | plain, `8`–`15` | `x86:mov/r16-base-ext/legacy` | `66 41 8b 00` | 4 | dest `x86.gpr16`/`r16` → `[27,3]`; base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12, 13) |
| store | plain, `8`–`15` | `x86:mov/base-ext-r16/legacy` | `66 41 89 00` | 4 | src `x86.gpr16`/`r16` → `[27,3]`; base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12, 13) |
| load | `%rsp` | `x86:mov/r16-rsp/legacy` | `66 8b 04 24` | 4 | dest `x86.gpr16`/`r16` → `[19,3]`; base fixed to `%rsp` |
| store | `%rsp` | `x86:mov/rsp-r16/legacy` | `66 89 04 24` | 4 | src `x86.gpr16`/`r16` → `[19,3]`; base fixed to `%rsp` |
| load | `%r12` | `x86:mov/r16-r12/legacy` | `66 41 8b 04 24` | 5 | dest `x86.gpr16`/`r16` → `[19,3]`; base fixed to `%r12` |
| store | `%r12` | `x86:mov/r12-r16/legacy` | `66 41 89 04 24` | 5 | src `x86.gpr16`/`r16` → `[19,3]`; base fixed to `%r12` |

Four properties follow:

- **The displacement is absent, not zero.** `mod = 00` is a form; a `disp`
  operand on these rows is `E-OPERAND-002` (`expected 1, found 2`), and a
  `disp8` value would need a `mod = 01` row (`INV-04`).
- **The base is an operand only on the plain rows.** The `SIB` rows fix it,
  because `%rsp` and `%r12` share `SIB = 24`.
- **The base-reach window is two wide.** The low rows reach `0`–`7`; the `-ext`
  rows reach `8`–`15` and exclude the low bases, because a low value would
  clear the fixed `REX.B` bit.
- **The `0x66` prefix moves every offset by one byte.** In the unprefixed rows
  the register field is `[19,3]` and the plain base `[16,3]`; a `REX` byte
  pushes both one further, so the `REX.R`/`REX.B` rows place the register at
  `[27,3]` and the base at `[24,3]`, with the first `REX` bit at `[8,1]`. That
  is the only structural difference from the 32-bit `mod = 00` rows.

## Consequences

- `0.41.0` is a 345-form document, byte-reproducing every `0.40.0` row.
- Its positive fixture `X86-P45-gpr16-mov-mem-nodisp` has twelve instructions
  and 46 bytes: the four plain-base rows twice (at `%rax`/`%rdi` and
  `%r8`/`%r15`) and the four fixed-base rows once each.
- Negatives pin the version boundary in both directions (`N01cj`, `N01ck`), a
  supplied displacement (`N02bk`), the `%rsp` and `%r12` bases on a plain row
  (`N16bh`, `N16bi`), the low-base floor on the `-ext` row (`N16bj`), and the
  `%rbp`/`%r13` bases that `mod = 00` cannot hold (`N16bk`, `N16bl`).
- `EC-35` and `EC-38` are revised in place. No new `EC` row appears and no row
  is renumbered.
- No schema, loader or materializer change: the rows use the existing
  `x86.gpr16`/`r16` and `x86.gpr64`/`rm64` kinds and the placement shapes the
  `0.8.0` 16-bit rows already use.

## Alternatives rejected

- **Let these rows accept a zero `disp8` and encode `mod = 01`.** The same
  instruction would then have two names and the length would depend on the
  operand, which `EC-02` forbids.
- **Fold `%rsp`/`%r12` into the plain rows with a `base` operand.** The base
  would need the `SIB` byte, so the length would change with the operand
  (`INV-04`).
- **Add the `REX.R` register window (`%r8w`–`%r15w`) here.** That is a
  register-reach axis, not a base axis, and belongs to its own slice.
- **Reorder the prefix so the `REX` byte comes first.** The ISA places `0x66`
  before `REX`; the byte order is a frozen fact, not a choice.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 8b 00` at three bytes | `llvm-mc -show-encoding`, `EXP-0070` §1 | high |
| `66 41` grows the row to four bytes | `llvm-mc -show-encoding`, `EXP-0070` §2 | high |
| `%rbp`/`%r13` need a displacement at `mod = 00` | `llvm-mc -show-encoding`, `EXP-0070` §3 | high |
| `%rsp` and `%r12` differ only in `REX.B` | `llvm-mc -show-encoding`, `EXP-0070` §4 | high |
| the `0x66` prefix precedes `REX` | `llvm-mc -show-encoding`, `EXP-0070` §1–§2 | high |

## Review triggers

- A `disp` operand is requested on these rows.
- The `REX.R` 16-bit register window (`%r8w`–`%r15w`) is requested.
- An index or scale operand is requested.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- The APX `d5` register window is attempted.
