# ADR-0065: the 32-bit `mov` family takes the `disp32` base shape

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P42` (the `mod = 10` 32-bit `mov` rows over a plain base,
  both directions, with a signed 32-bit displacement)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement axis now reaches the 32-bit `disp32` base
  rows) and `EC-38` (the 32-bit family's base reach now includes the `disp32`
  windows)

## Context

`0.37.0` gave the 32-bit `mov` family the plain-base `disp8` shape
(`ADR-0064`), but the family still cannot plan `movl 200(%rax), %eax`: the
displacement axis stops at one byte, while the byte, word and 64-bit families
already have both `disp8` and `disp32` base rows.

`EC-02` is the governing rule: a memory operand's displacement is none
(`mod = 00`), `disp8` (`mod = 01`) or `disp32` (`mod = 10`), and the choice is
a form rather than a value the encoder picks. `EC-38` adds the register-reach
axis: because a 32-bit legacy row has no `REX` byte, `%r8d`–`%r15d` and
`%r8`–`%r15` need their own rows.

`EXP-0067` measures the combination and four facts come out:

1. **`mod = 10` costs four displacement bytes.** `movl 200(%rax), %eax` is
   `8b 80 c8 00 00 00`: `ModRM = 80` (`mod = 10`, `reg = 000`, `r/m = 000`)
   and the signed displacement at bytes 2–5. The range is the full signed
   32-bit span: `-2147483648` is `8b 80 00 00 00 80` and `2147483647` is
   `8b 80 ff ff ff 7f`.
2. **The register/base windows are the same three as `disp8`.** The low row is
   `8b 80 c8 00 00 00`; `movl 200(%rax), %r8d` is `44 8b 80 c8 00 00 00`
   (`REX.R`); `movl 200(%r8), %eax` is `41 8b 80 c8 00 00 00` (`REX.B`); both
   together are `45 8b b9 c8 00 00 00` (`movl 200(%r9), %r15d`).
3. **`%rbp`/`%r13` are legal, and only `%rsp`/`%r12` stay out.** `r/m = 101`
   with `mod = 10` is an ordinary base, so `movl 200(%rbp), %eax` is
   `8b 85 c8 00 00 00`; `%rsp`/`%r12` need the `SIB` byte
   (`movl 200(%rsp), %eax` is `8b 84 24 c8 00 00 00`).
4. **`128` belongs here, not to `disp8`.** `movl 128(%rax), %eax` is
   `8b 80 80 00 00 00`, four displacement bytes, so the `disp8` range end is
   the row boundary.

`llvm-mc` keeps larger displacements on this row; `200` is the value the
fixture uses, and the range ends are measured directly.

## Decision

**`0.38.0` appends six rows — three reach windows per direction — with
`mod = 10` in the template, a signed 32-bit `disp` slot, and the base as a
4-bit operand in the two prefixed windows.**

| Direction | Reach | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | low/low | `x86:mov/r32-base-disp32/legacy` | `8b 80 00 00 00 00` | 6 | dest `x86.gpr32`/`r32` → `[11,3]`; base `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp `x86.imm`/`disp32` → `[16,32]` |
| store | low/low | `x86:mov/base-disp32-r32/legacy` | `89 80 00 00 00 00` | 6 | src `x86.gpr32`/`r32` → `[11,3]`; base `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp `x86.imm`/`disp32` → `[16,32]` |
| load | `REX.R` | `x86:mov/r32-ext-base-disp32/legacy` | `44 8b 80 00 00 00 00` | 7 | dest `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp `x86.imm`/`disp32` → `[24,32]` |
| store | `REX.R` | `x86:mov/base-disp32-r32-ext/legacy` | `44 89 80 00 00 00 00` | 7 | src `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp `x86.imm`/`disp32` → `[24,32]` |
| load | `REX.B` | `x86:mov/r32-base-ext-disp32/legacy` | `41 8b 80 00 00 00 00` | 7 | dest `x86.gpr32`/`r32` → `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0–7, 12); disp `x86.imm`/`disp32` → `[24,32]` |
| store | `REX.B` | `x86:mov/base-ext-disp32-r32/legacy` | `41 89 80 00 00 00 00` | 7 | src `x86.gpr32`/`r32` → `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0–7, 12); disp `x86.imm`/`disp32` → `[24,32]` |

Four properties follow:

- **The displacement size is the form.** `disp32` is these rows; `disp8` and
  `mod = 00` are other rows. A `disp8` operand on these rows is
  `E-OPERAND-001`, a value outside `-2147483648…2147483647` is `E-RANGE-001`,
  and a missing displacement is `E-OPERAND-002` (`INV-04`).
- **The register windows are the same three.** The low row keeps `reg = 0…7`
  and `base = 0…7`; the `REX.R` row carries `reg = 8…15` and a 4-bit base; the
  `REX.B` row carries `base = 8…15`. A `(register, base)` pair names one row.
- **Only the two `SIB` bases are excluded.** `%rbp`/`%r13` are ordinary bases
  at `mod = 10`; `%rsp`/`%r12` remain the next slice. The `REX.B` row also
  excludes `0`–`7`, which would clear its fixed `REX.B` bit.
- **The displacement slot moves with the prefix.** It is `[16,32]` in the
  unprefixed rows and `[24,32]` behind a `REX` byte, exactly as the byte, word
  and 64-bit families already place it.

## Consequences

- `0.38.0` is a 321-form document, byte-reproducing every `0.37.0` row.
- Its positive fixture `X86-P42-gpr32-mov-mem-disp32` has twelve instructions
  and 80 bytes: each of the six rows twice at `200`, so every window edge
  appears (`%eax`/`%edi`, `%r8d`/`%r15d`, and `%eax`/`%edi` over
  `%r8`/`%r15`).
- Negatives pin the version boundary in both directions (`N01cd`, `N01ce`), a
  missing displacement (`N02bh`), the range end (`N03s`), the 3-bit and 4-bit
  field ends (`N14aq`, `N14ap`), the two `SIB`-forcing bases (`N16bb`,
  `N16bc`), the `REX.R` window floor (`N16bd`) and the `REX.B` base floor
  (`N16be`).
- `EC-02` is revised in place: the displacement axis now reaches the 32-bit
  `disp32` base rows. `EC-38` is revised so its 32-bit paragraph covers the
  `disp32` windows. No new `EC` row appears and no row is renumbered.
- No schema, loader or materializer change: the rows use the existing
  `x86.gpr32`/`r32`, `x86.gpr64`/`rm64` and `x86.imm`/`disp32` kinds and the
  placement shapes the 64-bit `disp32` rows already use.

## Alternatives rejected

- **One row per direction with a 4-bit register and base plus a `REX` byte
  whenever a value needs it.** The instruction length would depend on operand
  values (`INV-04`), which is why the reach is split.
- **Let the rows accept `disp8` as well and shorten the encoding.** The
  length would depend on the displacement value; `EC-02` says the
  displacement size is a form.
- **Fold these rows into the `disp8` rows.** `disp32` reaches the values that
  `disp8` cannot, and the two forms differ by three bytes; `EC-02` keeps them
  separate.
- **Take the `%rsp`/`%r12` `SIB` `disp32` rows here.** They need a fixed-base
  row per base, direction and register window, and are a later slice.
- **Take the same shape at 16 or 8 bits.** Those families already have the
  `disp32` base rows; this slice changes only the 32-bit family.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8b 80 c8 00 00 00` at six bytes | `llvm-mc -show-encoding`, `EXP-0067` §1 | high |
| `44`/`41`/`45` grow the row to seven bytes | `llvm-mc -show-encoding`, `EXP-0067` §2 | high |
| the `disp32` range is the signed 32-bit span | `llvm-mc -show-encoding`, `EXP-0067` §1 | high |
| `%rbp`/`%r13` are legal at `mod = 10`, `%rsp`/`%r12` are not | `llvm-mc -show-encoding`, `EXP-0067` §3 | high |
| `128` is in this row, not the `disp8` row | `llvm-mc -show-encoding`, `EXP-0067` §3 | high |

## Review triggers

- A `disp8` operand is requested on these rows.
- The `%rsp`/`%r12` `SIB` `disp32` rows are requested.
- An index or scale operand is requested.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- The APX `d5` register window is attempted.
