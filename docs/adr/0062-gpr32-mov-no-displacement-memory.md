# ADR-0062: the 32-bit `mov` family takes its first base rows

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P39` (the `mod = 00` 32-bit `mov` rows over a plain base,
  both directions)
- Supersedes: none
- Superseded by: none
- Revises: `EC-38` (the 32-bit family now has a base-reach window as well as
  a register-reach window)

## Context

The 32-bit `mov` family has only `abs32` rows so far: `8b 04 25 disp32` and
`89 04 25 disp32`, each split into a low and an extended-register row
(`0.27.0`, `ADR-0054`). It has no base rows at all, so `movl (%rax), %eax`
cannot be planned.

`EC-38` already states the governing rule: a legacy row has no `REX` byte, so
a register number above `7` changes the instruction's *length* and therefore
must be a different row. That rule was applied to the register field of the
`abs32` rows; this slice applies it to a base as well.

`EXP-0064` measures the shape and three facts come out:

1. **Without a `REX` byte the row is two bytes.** `movl (%rax), %eax` is
   `8b 00`: `ModRM = 00` (`mod = 00`, `reg = 000`, `r/m = 000`), no prefix and
   no displacement.
2. **A high register or a high base grows the row by one byte.** `movl (%rax),
   %r8d` is `44 8b 00` (`REX.R = 1`), `movl (%r8), %eax` is `41 8b 00`
   (`REX.B = 1`), and `movl (%r9), %r15d` is `45 8b 39` (both).
3. **The two extension bits are disjoint windows, and they make three rows.**
   The low row carries the 3-bit `ModRM.reg` field and the 3-bit `r/m` field;
   the `REX.R` row carries `reg = 8…15` and a 4-bit base; the `REX.B` row
   carries `reg = 0…7` and `base = 8…15`. A `(register, base)` pair names
   exactly one row.

The base exclusions follow the shapes the family already has. `%rsp` (`4`)
needs the `SIB` byte and `%rbp` (`5`) has `r/m = 101` at `mod = 00`, which in
64-bit mode is the RIP-relative `disp32` shape:
`movl (%rsp), %eax` is `8b 04 24`, `movl (%rbp), %eax` is `8b 45 00`
(`mod = 01`, `disp8 = 0`) and `movl (%rip), %eax` is `8b 05 00 00 00 00`.
`%r12` (`12`) shares `%rsp`'s low three bits. `llvm-mc` normalises an explicit
zero displacement on a plain base (`movl 0(%rax), %eax` assembles to
`8b 00`), so the plan names the row rather than the assembler picking one.

## Decision

**`0.35.0` appends six rows — one per direction and reach window — with
`mod = 00` in the template and no displacement slot.**

| Direction | Reach | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | low/low | `x86:mov/r32-base/legacy` | `8b 00` | 2 | dest `x86.gpr32`/`r32` → `[11,3]`; base `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) |
| load | `REX.R` | `x86:mov/r32-ext-base/legacy` | `44 8b 00` | 3 | dest `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) |
| load | `REX.B` | `x86:mov/r32-base-ext/legacy` | `41 8b 00` | 3 | dest `x86.gpr32`/`r32` → `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0–7, 12, 13) |
| store | low/low | `x86:mov/base-r32/legacy` | `89 00` | 2 | src `x86.gpr32`/`r32` → `[11,3]`; base `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) |
| store | `REX.R` | `x86:mov/base-r32-ext/legacy` | `44 89 00` | 3 | src `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) |
| store | `REX.B` | `x86:mov/base-ext-r32/legacy` | `41 89 00` | 3 | src `x86.gpr32`/`r32` → `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0–7, 12, 13) |

Four properties follow:

- **The reach is the form, not an operand value.** No row inserts a prefix on
  seeing a high value; the `0x41`/`0x44` byte is template content (`INV-04`).
- **The windows are disjoint.** The low row holds `reg = 0…7` and `base =
  0…7`; the `REX.R` row excludes `reg = 0…7`; the `REX.B` row excludes `base =
  0…7`. One `(register, base)` pair therefore names exactly one row.
- **Both four-bit fields ride one `REX` byte.** In the `REX.R` row the base's
  fourth bit is `REX.B` at `[0,1]`, which is why `movl (%r9), %r15d` is
  `45 8b 39`; in the `REX.B` row the register stays in the 3-bit field
  because `REX.R` is fixed at `0`.
- **There is no displacement slot.** `disp` is `E-OPERAND-002`, not an implied
  zero; the `disp8`/`disp32` shapes remain the `abs32` and base+disp rows to
  come.

## Consequences

- `0.35.0` is a 301-form document, byte-reproducing every `0.34.0` row.
- Its positive fixture `X86-P39-gpr32-mov-mem-nodisp` has twelve instructions
  and 32 bytes: each of the six rows twice, so every window edge appears —
  `%eax`/`%edi` in the low row, `%r8d`/`%r15d` in the `REX.R` row and
  `%eax`/`%edi` over `%r8`/`%r15` in the `REX.B` row.
- Negatives pin the version boundary in both directions (`N01bx`, `N01by`), a
  `disp` operand (`N02bd`), the 3-bit field end (`N14ak`), the 4-bit field
  end (`N14aj`), the `%rsp` and `%r12` bases (`N16as`, `N16at`), register `0`
  on the `REX.R` row (`N16au`) and base `0` on the `REX.B` row (`N16av`).
- `EC-38` is revised in place: the 32-bit family now has a base-reach window
  and a three-row split, not only a register-reach window. No new `EC` row
  appears and no row is renumbered.
- No schema, loader or materializer change: the rows use the existing
  `x86.gpr32`/`r32` and `x86.gpr64`/`rm64` kinds and the placement shape the
  `abs32` and byte rows already use.

## Alternatives rejected

- **One row with a 4-bit base and a `REX` byte whenever a value needs it.**
  The instruction length would then depend on an operand value, which is
  `INV-04`.
- **Two rows, folding the extended base into the `REX.R` row only.** Then
  `movl (%r8), %eax` (low register, high base) would have no row — the same
  gap the byte family still carries. The third row costs one template and
  closes it.
- **Let the `REX.B` row accept low bases and emit `40 8b 00`.** A redundant
  `REX` prefix duplicates the low row, and `EC-28` pins the minimal prefix
  set; the base window stays excluded instead.
- **Take the `%rsp`/`%r12` `SIB` bases here.** They need a fixed-base row per
  base, the shape `ADR-0059`/`ADR-0061` already used; that is the next slice.
- **Take the `disp8`/`disp32` base shapes.** The displacement axis is `EC-02`
  and the rows do not exist yet.
- **Take the same shape at 16 or 8 bits.** The 16-bit family splits by base
  window around a `0x66` prefix and the byte family splits four ways; each is
  a separate design question.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8b 00` / `89 00` at two bytes | `llvm-mc -show-encoding`, `EXP-0064` §1 | high |
| `44`/`41`/`45` grow the row to three bytes | `llvm-mc -show-encoding`, `EXP-0064` §2 | high |
| `ModRM = 00` (`mod = 00`), no displacement | `llvm-mc -show-encoding`, `EXP-0064` §2 | high |
| `%rsp` needs `SIB`, `%rbp`/`%r13` are RIP-relative | `llvm-mc -show-encoding`, `EXP-0064` §3 | high |
| a `(register, base)` pair names one row | the disjoint exclusion lists, `EXP-0064` §4 | high |

## Review triggers

- A displacement or a `SIB` operand is requested on these rows.
- The `%rsp`/`%r12` `SIB` bases are requested at 32-bit width.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in an address is requested.
- The same shape is attempted at 16 or 8 bits.
- The APX `d5` register window is attempted.
