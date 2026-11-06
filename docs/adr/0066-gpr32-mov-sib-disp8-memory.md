# ADR-0066: the 32-bit `mov` family takes the `SIB` `disp8` shape

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P43` (the `mod = 01` 32-bit `mov` rows over the `%rsp`/`%r12`
  `SIB` bases, both directions, with a signed 8-bit displacement)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the `disp8` axis now reaches the 32-bit `SIB` bases) and
  `EC-35` (the 32-bit `%rsp`/`%r12` rows now have a `disp8` variant)

## Context

`0.36.0` gave the 32-bit `mov` family the `%rsp`/`%r12` bases at `mod = 00`
(`ADR-0063`) and `0.37.0` gave the plain bases the `disp8` shape
(`ADR-0064`), but the two have not been combined: the family cannot plan
`movl 8(%rsp), %eax`, because `r/m = 100` needs a fixed `SIB` byte that only
the `mod = 00` rows carry.

`EC-02` is the governing rule: a memory operand's displacement is none
(`mod = 00`), `disp8` (`mod = 01`) or `disp32` (`mod = 10`), and the choice is
a form rather than a value the encoder picks. `EC-35` says a `SIB` base is a
property of the form: the two bases share the low three bits `100`, so each
needs its own rows and the base cannot be a plan operand.

`EXP-0068` measures the combination and four facts come out:

1. **`mod = 01` keeps the `SIB` byte and appends one displacement byte.**
   `movl 8(%rsp), %eax` is `8b 44 24 08`: `ModRM = 44` (`mod = 01`,
   `reg = 000`, `r/m = 100`), `SIB = 24` (scale 0, index 100, base 100), and
   the signed displacement at `[24,8]`. `movl 8(%r12), %eax` is
   `41 8b 44 24 08`, the same three bytes behind a `REX.B` byte.
2. **The register window still splits.** The legacy row has no `REX` byte, so
   `%r8d`-`%r15d` need their own rows: `movl 8(%rsp), %r8d` is
   `44 8b 44 24 08` (`REX.R`), and `movl 8(%r12), %r8d` is
   `45 8b 44 24 08` (both bits). The displacement moves to `[32,8]` behind
   the `REX` byte.
3. **The range is the signed byte.** `-128` is `8b 44 24 80` and `127` is
   `8b 44 24 7f`; `128` needs `mod = 10` (`8b 84 24 80 00 00 00`), which is a
   different form.
4. **The base is still fixed in the form.** `%rsp` and `%r12` share `SIB = 24`
   and differ only in `REX.B`, so a plan cannot choose the base as an operand:
   it names one of the eight rows.

## Decision

**`0.39.0` appends eight rows — two bases × two directions × two register
windows — with `mod = 01` in the template, `SIB = 24`, and a signed 8-bit
`disp` slot.**

| Direction | Base | Register window | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|---|
| load | `%rsp` | low | `x86:mov/r32-rsp-disp8/legacy` | `8b 44 24 00` | 4 | dest `x86.gpr32`/`r32` → `[11,3]`; disp `x86.imm`/`disp8` → `[24,8]` |
| store | `%rsp` | low | `x86:mov/rsp-disp8-r32/legacy` | `89 44 24 00` | 4 | src `x86.gpr32`/`r32` → `[11,3]`; disp `x86.imm`/`disp8` → `[24,8]` |
| load | `%rsp` | `REX.R` | `x86:mov/r32-ext-rsp-disp8/legacy` | `44 8b 44 24 00` | 5 | dest `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[32,8]` |
| store | `%rsp` | `REX.R` | `x86:mov/rsp-disp8-r32-ext/legacy` | `44 89 44 24 00` | 5 | src `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[32,8]` |
| load | `%r12` | low | `x86:mov/r32-r12-disp8/legacy` | `41 8b 44 24 00` | 5 | dest `x86.gpr32`/`r32` → `[19,3]`; disp `x86.imm`/`disp8` → `[32,8]` |
| store | `%r12` | low | `x86:mov/r12-disp8-r32/legacy` | `41 89 44 24 00` | 5 | src `x86.gpr32`/`r32` → `[19,3]`; disp `x86.imm`/`disp8` → `[32,8]` |
| load | `%r12` | `REX.R` | `x86:mov/r32-ext-r12-disp8/legacy` | `45 8b 44 24 00` | 5 | dest `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[32,8]` |
| store | `%r12` | `REX.R` | `x86:mov/r12-disp8-r32-ext/legacy` | `45 89 44 24 00` | 5 | src `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[32,8]` |

Four properties follow:

- **The displacement size is the form.** `disp8` is these rows; `mod = 00` and
  `disp32` are other rows. A missing displacement is `E-OPERAND-002`, a value
  outside `-128…127` is `E-RANGE-001`, and a `disp32` operand on these rows is
  `E-OPERAND-001` (`INV-04`).
- **The base is a form property.** No row carries a `base` operand: `%rsp`
  and `%r12` are in the `form_id` and the template's `SIB` and `REX.B` bits.
- **The register window is two wide.** Low rows reach `0`–`7`; the `-ext`
  rows reach `8`–`15` and exclude the low registers, because a low value would
  clear the fixed `REX.R` bit.
- **Only the displacement moves with the prefix.** It is `[24,8]` in the
  unprefixed rows and `[32,8]` behind a `REX` byte, exactly as the 8-, 16- and
  64-bit `SIB` families place it.

## Consequences

- `0.39.0` is a 329-form document, byte-reproducing every `0.38.0` row.
- Its positive fixture `X86-P43-gpr32-mov-mem-sib-disp8` has sixteen
  instructions and 76 bytes: each of the eight rows twice, at displacement
  `8` and `100`, so both register-window ends appear (`%eax`/`%edi` and
  `%r8d`/`%r15d`).
- Negatives pin the version boundary in both directions (`N01cf`, `N01cg`), a
  missing displacement (`N02bi`), the range end (`N03t`), the low and `-ext`
  field ends (`N14ar`, `N14as`), and the `-ext` register floor (`N16bf`).
- `EC-02` and `EC-35` are revised in place. No new `EC` row appears and no row
  is renumbered.
- No schema, loader or materializer change: the rows use the existing
  `x86.gpr32`/`r32` and `x86.imm`/`disp8` kinds and the placement shapes the
  `0.36.0` `SIB` rows already use.

## Alternatives rejected

- **One row per base with a `base` operand and a 4-bit register.** The base
  would then be a value, but `%rsp` and `%r12` need different `REX.B` bytes,
  so the length would depend on the operand (`INV-04`).
- **Let the rows accept `disp32` as well and widen when needed.** The length
  would depend on the displacement value; `EC-02` says the size is a form.
- **Fold these rows into the plain-base `disp8` rows.** `r/m = 100` needs the
  fixed `SIB` byte, which the plain rows do not carry.
- **Take the `%rsp`/`%r12` `disp32` rows here.** They are the next slice and
  differ by three displacement bytes.
- **Add an index or scale operand.** `SIB = 24` has `index = 100` (none) and
  `scale = 0`; an index is a separate axis.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8b 44 24 08` at four bytes | `llvm-mc -show-encoding`, `EXP-0068` §1 | high |
| `41`/`44`/`45` grow the row to five bytes | `llvm-mc -show-encoding`, `EXP-0068` §2 | high |
| the `disp8` range is `-128…127` | `llvm-mc -show-encoding`, `EXP-0068` §3 | high |
| `128` switches to `mod = 10` | `llvm-mc -show-encoding`, `EXP-0068` §3 | high |
| `%rsp` and `%r12` differ only in `REX.B` | `llvm-mc -show-encoding`, `EXP-0068` §2 | high |

## Review triggers

- A `disp32` operand is requested on these rows.
- The `%rsp`/`%r12` `SIB` `disp32` rows are requested.
- An index or scale operand is requested.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- The APX `d5` register window is attempted.
