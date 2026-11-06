# ADR-0064: the 32-bit `mov` family takes the `disp8` base shape

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P41` (the `mod = 01` 32-bit `mov` rows over a plain base,
  both directions, with a signed 8-bit displacement)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement axis now reaches the 32-bit base rows)
  and `EC-38` (the 32-bit family's base reach now includes the `disp8`
  windows)

## Context

`0.35.0` gave the 32-bit `mov` family its first base rows (`ADR-0062`) and
`0.36.0` added the `%rsp`/`%r12` `SIB` pair (`ADR-0063`), but every one of
them is the `mod = 00` shape: the displacement is absent. The family cannot
plan `movl 8(%rax), %eax` at all, while the byte, word and 64-bit families
already have `disp8` and `disp32` base rows.

`EC-02` is the governing rule: a memory operand's displacement is none
(`mod = 00`), `disp8` (`mod = 01`) or `disp32` (`mod = 10`), and the choice is
a form rather than a value the encoder picks. `EC-38` adds the register-reach
axis: because a 32-bit legacy row has no `REX` byte, `%r8d`–`%r15d` and
`%r8`–`%r15` need their own rows.

`EXP-0066` measures the combination and four facts come out:

1. **`mod = 01` costs one byte.** `movl 8(%rax), %eax` is `8b 40 08`:
   `ModRM = 40` (`mod = 01`, `reg = 000`, `r/m = 000`) and the signed
   displacement at byte 2. The range is `-128…127`; `-128` is `8b 40 80` and
   `127` is `8b 40 7f`.
2. **The register/base windows are the same three as `mod = 00`.** The low row
   is `8b 40 08`; `movl 8(%rax), %r8d` is `44 8b 40 08` (`REX.R`);
   `movl 8(%r8), %eax` is `41 8b 40 08` (`REX.B`); both together are
   `45 8b 79 08` (`movl 8(%r9), %r15d`).
3. **`%rbp`/`%r13` are legal here, unlike at `mod = 00`.** `r/m = 101` with
   `mod = 01` is an ordinary base, so `movl 8(%rbp), %eax` is `8b 45 08`. Only
   `%rsp`/`%r12` stay out, because they need the `SIB` byte
   (`movl 8(%rsp), %eax` is `8b 44 24 08`).
4. **`disp8` is not `disp32`.** `movl 128(%rax), %eax` is
   `8b 80 80 00 00 00` (`mod = 10`, four displacement bytes), so the range
   end is the row boundary, not a value the row re-encodes.

`llvm-mc` normalises `movl 0(%rax), %eax` to the `mod = 00` row (`8b 00`), so
a zero displacement is the `0.35.0` row rather than this one. The plan names
the row.

## Decision

**`0.37.0` appends six rows — three reach windows per direction — with
`mod = 01` in the template, a signed 8-bit `disp` slot, and the base as a
4-bit operand in the two prefixed windows.**

| Direction | Reach | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | low/low | `x86:mov/r32-base-disp8/legacy` | `8b 40 00` | 3 | dest `x86.gpr32`/`r32` → `[11,3]`; base `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp `x86.imm`/`disp8` → `[16,8]` |
| store | low/low | `x86:mov/base-disp8-r32/legacy` | `89 40 00` | 3 | src `x86.gpr32`/`r32` → `[11,3]`; base `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp `x86.imm`/`disp8` → `[16,8]` |
| load | `REX.R` | `x86:mov/r32-ext-base-disp8/legacy` | `44 8b 40 00` | 4 | dest `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp `x86.imm`/`disp8` → `[24,8]` |
| store | `REX.R` | `x86:mov/base-disp8-r32-ext/legacy` | `44 89 40 00` | 4 | src `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp `x86.imm`/`disp8` → `[24,8]` |
| load | `REX.B` | `x86:mov/r32-base-ext-disp8/legacy` | `41 8b 40 00` | 4 | dest `x86.gpr32`/`r32` → `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0–7, 12); disp `x86.imm`/`disp8` → `[24,8]` |
| store | `REX.B` | `x86:mov/base-ext-disp8-r32/legacy` | `41 89 40 00` | 4 | src `x86.gpr32`/`r32` → `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0–7, 12); disp `x86.imm`/`disp8` → `[24,8]` |

Four properties follow:

- **The displacement size is the form.** `disp8` is these rows; `disp32` and
  `mod = 00` are other rows. A `disp32` operand on these rows is
  `E-OPERAND-001`, a value outside `-128…127` is `E-RANGE-001`, and a missing
  displacement is `E-OPERAND-002` (`INV-04`).
- **The register windows are the same three.** The low row keeps `reg = 0…7`
  and `base = 0…7`; the `REX.R` row carries `reg = 8…15` and a 4-bit base;
  the `REX.B` row carries `base = 8…15`. A `(register, base)` pair names one
  row.
- **Only the two `SIB` bases are excluded.** `%rbp`/`%r13` are ordinary bases
  at `mod = 01`; `%rsp`/`%r12` remain the next slice.
- **The displacement slot moves with the prefix.** It is `[16,8]` in the
  unprefixed rows and `[24,8]` behind a `REX` byte, exactly as the byte, word
  and 64-bit families already place it.

## Consequences

- `0.37.0` is a 315-form document, byte-reproducing every `0.36.0` row.
- Its positive fixture `X86-P41-gpr32-mov-mem-disp8` has twelve instructions
  and 44 bytes: each of the six rows twice, so every window edge appears
  (`%eax`/`%edi`, `%r8d`/`%r15d`, and `%eax`/`%edi` over `%r8`/`%r15`).
- Negatives pin the version boundary in both directions (`N01cb`, `N01cc`), a
  missing displacement (`N02bg`), the range end (`N03r`), the 3-bit and 4-bit
  field ends (`N14ao`, `N14an`), the two `SIB`-forcing bases (`N16ax`,
  `N16ay`), the `REX.R` window floor (`N16az`) and the `REX.B` base floor
  (`N16ba`).
- `EC-02` is revised in place: the displacement axis now reaches the 32-bit
  base rows. `EC-38` is revised so its 32-bit paragraph covers the `disp8`
  windows. No new `EC` row appears and no row is renumbered.
- No schema, loader or materializer change: the rows use the existing
  `x86.gpr32`/`r32`, `x86.gpr64`/`rm64` and `x86.imm`/`disp8` kinds and the
  placement shapes the 64-bit `disp8` rows already use.

## Alternatives rejected

- **One row per direction with a 4-bit register and base plus a `REX` byte
  whenever a value needs it.** The instruction length would depend on operand
  values (`INV-04`), which is the whole reason the reach is split.
- **Let the rows accept `disp32` as well and pick `mod = 10` on a value.**
  The length would depend on the displacement value; `EC-02` says the
  displacement size is a form.
- **Fold the `disp8` rows into the `disp32` rows.** `disp8` saves three bytes
  and is a distinct encoding form; `EC-02` keeps them separate.
- **Take the `%rsp`/`%r12` `SIB` `disp8` rows here.** They need a fixed-base
  row per base, direction and register window, and are the next slice.
- **Take the same shape at 16 or 8 bits.** Those families already have the
  `disp8` base rows; this slice changes only the 32-bit family.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8b 40 08` / `89 40 08` at three bytes | `llvm-mc -show-encoding`, `EXP-0066` §1 | high |
| `44`/`41`/`45` grow the row to four bytes | `llvm-mc -show-encoding`, `EXP-0066` §2 | high |
| the `disp8` range is `-128…127` | `llvm-mc -show-encoding`, `EXP-0066` §1 | high |
| `%rbp`/`%r13` are legal at `mod = 01`, `%rsp`/`%r12` are not | `llvm-mc -show-encoding`, `EXP-0066` §3 | high |
| `128` leaves the row for `mod = 10` | `llvm-mc -show-encoding`, `EXP-0066` §3 | high |

## Review triggers

- A `disp32` operand is requested on these rows.
- The `%rsp`/`%r12` `SIB` `disp8` rows are requested.
- An index or scale operand is requested.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- The APX `d5` register window is attempted.
