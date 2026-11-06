# ADR-0060: the 64-bit `mov` rows take the no-displacement memory shape

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P37` (the `mod = 00` memory shape of the 64-bit GPR `mov`
  rows, both directions, over the plain-base window)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0059` §Review triggers (its seventh item, "a width other than
  eight bits takes the no-displacement shape"); `EC-35` (the 64-bit
  plain-base rows now carry the same `%rsp`/`%r12` exclusion)

## Context

`ADR-0058` and `ADR-0059` gave the byte `mov` family the `mod = 00` shape in
two steps: first the plain-base window, then the `%rsp`/`%r12` `SIB` pair.
The 64-bit family (`x86:mov/rm-r64/legacy` and its memory rows) still starts
at `mod = 01`: `movq 8(%rax), %rax` is `48 8b 40 08`, and there is no row for
`movq (%rax), %rax`. `ADR-0059` recorded that gap as its seventh review
trigger.

`EXP-0062` measures the shape on the 64-bit rows, and four facts come out:

1. **The row is three bytes and ends at the `ModRM`.** `movq (%rax), %rax` is
   `48 8b 00`: `REX.W` at `[0,8]`, opcode `8b` at `[8,8]`, `ModRM = 00` at
   `[16,8]` (`mod = 00`, `reg = 000`, `r/m = 000`). The store mirror is
   `48 89 00`.
2. **Both register fields are four bits wide and already exist.** The
   `REX.W` byte is in every 64-bit template, so `REX.R` at `[2,1]` carries the
   destination's fourth bit and `REX.B` at `[0,1]` the base's; `movq (%r8), %r8`
   is `4d 8b 00` and `movq (%r9), %r15` is `4d 8b 39`. No row splits by
   register or base window, unlike the byte and 16-bit families.
3. **The base excludes four values.** `%rsp`/`%r12` need the `SIB` byte that
   `mod = 00` has no room for (`48 8b 04 24`, `49 8b 04 24`), and
   `%rbp`/`%r13` at `r/m = 101` are the RIP-relative shape, which is the
   separate `x86:mov/r64-riprel32/legacy` row (`48 8b 05 00 00 00 00`).
   `llvm-mc` writes `movq (%rbp), %rax` as `48 8b 45 00`, `mod = 01`.
4. **The displacement axis now costs three lengths.** `movq (%rax), %rax` is
   three bytes, `movq 8(%rax), %rax` four (`48 8b 40 08`) and
   `movq 0x1234(%rax), %rax` seven (`48 8b 80 34 12 00 00`). `llvm-mc`
   normalises an explicit zero displacement on a plain base to the short
   form (`0(%rax)` assembles to `48 8b 00`, not `48 8b 40 00`), which is
   exactly why the plan must name the row rather than let the assembler
   pick (`INV-02`).

## Decision

**`0.33.0` appends two rows, one per direction, with `REX = 48` in the
template.**

| Direction | `form_id` | Template | Length | Slots |
|---|---|---|---|---|
| load | `x86:mov/r64-base/legacy` | `48 8b 00` | 3 | dest `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`, excl `4, 5, 12, 13` |
| store | `x86:mov/base-r64/legacy` | `48 89 00` | 3 | src `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`, excl `4, 5, 12, 13` |

Three properties follow:

- **`REX.W` is a template constant.** It does not depend on an operand, so
  neither row can lose it (`INV-04`). `REX.R` and `REX.B` are the only bits the
  operands own.
- **The base slot is four bits with four exclusions, not two.** `%rbp`/`%r13`
  are excluded by `EC-34` and `%rsp`/`%r12` by `EC-35`; each excluded value has
  its own row (the RIP-relative row today, the `%rsp`/`%r12` `SIB` rows in a
  later slice).
- **No `disp` slot exists.** A plan that supplies one is
  `E-OPERAND-002` (`N02ba`), not a zero the row would encode or discard.

## Consequences

- `0.33.0` is a 291-form document, byte-reproducing every `0.32.0` row.
- Its positive fixture `X86-P37-gpr64-mov-mem-nodisp` has six instructions and
  18 bytes: both directions over `%rax` (`REX.R = 0`, `REX.B = 0`) and `%r8`
  (both bits set), and over `%r9` with `%r15`, the top of both four-bit
  fields.
- Negatives pin the version boundary in both directions (`N01bt`, `N01bu`), a
  `disp` operand (`N02ba`), register `16` past the four-bit field (`N14ah`),
  and the four excluded bases `%rsp`, `%rbp`, `%r12`, `%r13` (`N16ao`–`N16ar`).
- `EC-35` is revised in place: the 64-bit plain-base rows now exclude
  `%rsp`/`%r12` like every other family that has the shape. No new `EC` row
  appears and no row is renumbered.
- No schema, loader or materializer change: the rows are two-slot forms of the
  shape `x86:mov/r64-base-disp8/legacy` already used, minus the displacement.

## Alternatives rejected

- **Let the `disp8` row accept a `disp` of zero and emit `mod = 00`.** The
  length would then depend on a value, which is `INV-04`, and `llvm-mc` writes
  two distinct shapes rather than one that shrinks.
- **Fold all four displacement shapes into one row with a displacement slot
  that chooses its own width.** `EC-02` already forbids it: the plan names the
  variant.
- **Give the row a `SIB` byte for `%rsp`/`%r12` in this slice.** The `SIB`
  base is fixed per row (`ADR-0059`), so it would be two more rows per
  direction; one address shape per ADR.
- **Also take the same shape at 32 and 16 bits.** The 32-bit family has no
  `base` operand at all yet (only the `abs32` rows), and the 16-bit family
  splits by base window (`66 8b 40 00` vs `66 41 8b 40 00`); each is a
  separate design question.
- **Take the `0x67` address-size prefix or `moffs` here.** Neither is part of
  this shape.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `48 8b 00` / `48 89 00` at three bytes | `llvm-mc -show-encoding`, `EXP-0062` §1 | high |
| `REX.R`/`REX.B` carry the fourth bits (`4d 8b 39`) | `llvm-mc -show-encoding`, `EXP-0062` §2 | high |
| `%rbp`/`%r13` at `mod = 00` are RIP-relative | `llvm-mc -show-encoding`, `EXP-0062` §3 | high |
| `%rsp`/`%r12` need the `SIB` byte | `llvm-mc -show-encoding`, `EXP-0062` §3 | high |
| the three displacement lengths are 3/4/7 | `llvm-mc -show-encoding`, `EXP-0062` §3 | high |

## Review triggers

- The `%rsp`/`%r12` `SIB` bases are requested at `mod = 00` in this family.
- The `REX.X` index or scale is requested at 64-bit width.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- `moffs` for the 64-bit width is requested.
- The APX `d5` register window is attempted.
- The same shape is attempted at 32 or 16 bits.
