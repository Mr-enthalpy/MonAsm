# ADR-0070: the 16-bit `disp8` `mov` rows take the `REX.R` register window

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P47` (the `%r8w`–`%r15w` register window over the 16-bit
  `disp8` `mov` rows, both directions, both base windows and both `SIB`
  bases)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement shape now has a `REX.R` window at
  16-bit width), `EC-06` (the register field's `REX.R` window now also
  exists on the `disp8` rows), `EC-38` (the base window is unchanged but the
  register window is now separate from it)

## Context

`0.42.0` gave the 16-bit `mod = 00` `mov` rows the `%r8w`–`%r15w` register
window (`ADR-0069`). The `disp8` shape still holds only `%ax`–`%di`:
`movw 8(%rax), %r8w` is not plannable, although `movw 8(%rax), %ax` is
`66 8b 40 08` and `movw (%rax), %r8w` is `66 44 8b 00`.

`EC-02` fixes the displacement shape: `mod = 01` with a signed byte at the
row's own offset. `EC-06` fixes the register window: the `REX.R` bit is
part of the form, so a low register value cannot share a row with an
extended one. `EC-38` keeps the base window separate, and at `mod = 01` the
base window differs from `mod = 00`: `%rbp`/`%r13` are legal bases because
`r/m = 101` now means a base with a displacement, not `rip`-relative.

`EXP-0072` measures the shapes and four facts come out:

1. **The `disp8` field moves with the `REX` byte.** `movw 8(%rax), %r8w` is
   `66 44 8b 40 08`: the `0x66` prefix, `REX = 44` (`R = 1`), the opcode,
   `ModRM = 40` (`mod = 01`, `reg = 0`, `r/m = 0`) and the displacement
   `08` at `[32,8]`. The register's fourth bit is `[10,1]` and its low three
   bits `[27,3]`, as on the `mod = 00` rows.
2. **Both extension bits share one byte.** `movw 8(%r8), %r8w` is
   `66 45 8b 40 08`: `REX = 45` is `R = 1` and `B = 1`, and the row stays
   five bytes.
3. **The `SIB` rows add one byte.** `movw 8(%rsp), %r8w` is
   `66 44 8b 44 24 08` and `movw 8(%r12), %r8w` is `66 45 8b 44 24 08`, with
   the displacement at `[40,8]`.
4. **The displacement end is a byte.** `127` is `7f` and `-128` is `80`;
   `128` is re-formed by the assembler as a `disp32` row
   (`66 44 8b 80 80 00 00 00`), which is a different row and not a choice
   this one may make (`INV-04`).

## Decision

**`0.43.0` appends eight rows: two directions × (one plain low-base row, one
plain `-ext`-base row and two fixed `SIB` bases), with `REX.R` fixed in the
template, the low register window excluded, and the signed `disp8` at
`[32,8]` (plain) or `[40,8]` (`SIB`).**

| Direction | Base | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | plain, `0`–`7` | `x86:mov/r16-ext-base-disp8/legacy` | `66 44 8b 40 00` | 5 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp `x86.imm`/`disp8` → `[32,8]` |
| store | plain, `0`–`7` | `x86:mov/base-disp8-r16-ext/legacy` | `66 44 89 40 00` | 5 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp `x86.imm`/`disp8` → `[32,8]` |
| load | plain, `8`–`15` | `x86:mov/r16-ext-base-ext-disp8/legacy` | `66 45 8b 40 00` | 5 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12); disp `x86.imm`/`disp8` → `[32,8]` |
| store | plain, `8`–`15` | `x86:mov/base-ext-disp8-r16-ext/legacy` | `66 45 89 40 00` | 5 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0–7, 12); disp `x86.imm`/`disp8` → `[32,8]` |
| load | `%rsp` | `x86:mov/r16-ext-rsp-disp8/legacy` | `66 44 8b 44 24 00` | 6 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[40,8]` |
| store | `%rsp` | `x86:mov/rsp-disp8-r16-ext/legacy` | `66 44 89 44 24 00` | 6 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[40,8]` |
| load | `%r12` | `x86:mov/r16-ext-r12-disp8/legacy` | `66 45 8b 44 24 00` | 6 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[40,8]` |
| store | `%r12` | `x86:mov/r12-disp8-r16-ext/legacy` | `66 45 89 44 24 00` | 6 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); disp `x86.imm`/`disp8` → `[40,8]` |

Four properties follow:

- **The register window is the form.** A low register on an `-ext` row is
  `E-RANGE-004`; a register past `15` is `E-OPERAND-004`.
- **The displacement is still a byte.** `-128…127` fits the slot;
  `128` is `E-RANGE-001`, never a silent widening to `disp32`.
- **The base window is looser than at `mod = 00`.** `%rbp`/`%r13` are legal
  bases here, because `mod = 01` gives `r/m = 101` a displacement; only
  `%rsp` (`r/m = 100`) needs the fixed `SIB` row. The `-ext` row still
  excludes `0`–`7` (the fixed `REX.B` bit) and `%r12` (which needs the
  fixed `SIB` row).
- **The `SIB` rows only gain `REX.R`.** The base stays fixed, because `%rsp`
  and `%r12` share `SIB = 24`.

## Consequences

- `0.43.0` is a 361-form document, byte-reproducing every `0.42.0` row.
- Its positive fixture `X86-P47-gpr16-mov-mem-disp8-rex-r` has fourteen
  instructions and 76 bytes: the four plain rows twice, at both ends of the
  register window (`%r8w`/`%r15w`), plus the four fixed-base rows once at
  `%r8w` and the two `%r12` rows again at `%r15w`.
- Negatives pin the version boundary in both directions (`N01cn`, `N01co`),
  a missing displacement (`N02bm`), the displacement end (`N03v`), the
  register field's ends (`N14aw`, `N16bp`), and the `%rsp`/`%rbp` base cases
  on the new rows (`N16bq`, `N16br`).
- `EC-02`, `EC-06` and `EC-38` are revised in place. No new `EC` row appears
  and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr16`/`r16`, `x86.gpr64`/`rm64` and `x86.imm`/`disp8` kinds and the
  `REX.R` placement the `abs32` rows already use.

## Alternatives rejected

- **Let one row accept `0`–`15` and set `REX.R` when the value is high.**
  The length would depend on the operand (`INV-04`); `EC-06` says the REX
  presence is the form.
- **Fold the low-base and `-ext`-base rows together.** `REX.B` is fixed in
  the template, so the two base windows must stay disjoint (`EC-38`).
- **Give the `disp8` slot a wider range and re-form to `disp32` when it
  overflows.** That is relaxation, which `INV-04` forbids; `128` is a
  different row.
- **Add the same window to the `disp32` shape here.** It is a separate
  displacement shape and gets its own slice.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 44 8b 40 08` at five bytes | `llvm-mc -show-encoding`, `EXP-0072` §1 | high |
| `REX = 45` carries both bits at five bytes | `llvm-mc -show-encoding`, `EXP-0072` §2 | high |
| the `SIB` rows are six bytes with `disp8` at `[40,8]` | `llvm-mc -show-encoding`, `EXP-0072` §3 | high |
| `128` is re-formed as `disp32` by the assembler | `llvm-mc -show-encoding`, `EXP-0072` §4 | high |

## Review triggers

- A `disp32` operand is requested with the register window.
- An index or scale operand is requested.
- The `0x67` address-size prefix is attempted.
- The APX `d5` register window is attempted.
