# ADR-0042: The EVEX compressed-displacement unit is a form fact

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P19` (EVEX memory forms at `ymm` and `zmm` width) and `EC-39`
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0041` §Consequences (the memory shapes it deferred)

## Context

`0.14.0` reaches `xmm`/`ymm`/`zmm` when both operands are registers
(`ADR-0041`), but every memory row is still 128-bit. `ADR-0041` measured three
256/512-bit memory shapes and deferred them because they break `EC-39`'s
sentence "`N = 16` for `xmm`". `llvm-mc` 23.1.2 measures the full set on
2026-11-05 (`EXP-0044`):

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps (%rax), %ymm0` | `62 f1 7c 28 28 00` | 6 |
| `{evex} vmovaps 32(%rax), %ymm0` | `62 f1 7c 28 28 40 01` | 7 |
| `{evex} vmovaps 4064(%rax), %ymm0` | `62 f1 7c 28 28 40 7f` | 7 |
| `{evex} vmovaps -4096(%rax), %ymm0` | `62 f1 7c 28 28 40 80` | 7 |
| `{evex} vmovaps 28(%rax), %ymm0` | `62 f1 7c 28 28 80 1c 00 00 00` | 10 |
| `{evex} vmovaps 4096(%rax), %ymm0` | `62 f1 7c 28 28 80 00 10 00 00` | 10 |
| `vmovaps 64(%rax), %zmm0` | `62 f1 7c 48 28 40 01` | 7 |
| `vmovaps 8128(%rax), %zmm0` | `62 f1 7c 48 28 40 7f` | 7 |
| `vmovaps -8192(%rax), %zmm0` | `62 f1 7c 48 28 40 80` | 7 |
| `vmovaps 60(%rax), %zmm0` | `62 f1 7c 48 28 80 3c 00 00 00` | 10 |
| `vmovaps 8192(%rax), %zmm0` | `62 f1 7c 48 28 80 00 20 00 00` | 10 |
| `{evex} vmovaps (%r8), %ymm31` | `62 41 7c 28 28 38` | 6 |
| `vmovaps 64(%r8), %zmm31` | `62 41 7c 48 28 78 01` | 7 |

Three facts decide the shape:

1. **The unit is the vector width, and the width is already in the row.** The
   same compressed byte `0x01` decodes as `16` bytes at `P2 = 08`, `32` at
   `P2 = 28` and `64` at `P2 = 48`. `llvm-mc -disassemble` on `62 f1 7c 08 28 40
   01`, `62 f1 7c 28 28 40 01` and `62 f1 7c 48 28 40 01` prints `16(%rax)`,
   `32(%rax)` and `64(%rax)`: one field content, three displacements, selected
   by the prefix byte the row already pins. `ADR-0041` fixed that byte, so no
   new choice appears — but the *unit* is not derivable from the operand.
2. **The unit is not a function of the displacement value.** `32` is one unit at
   `ymm` and `28` is not, so the value picks the row (`disp8*N` vs `disp32`),
   not the scale. `4064` is `content 127` at `N = 32` and out of range at
   `N = 16`, so a row that accepted a byte offset would have to divide by a
   number it read from the prefix it is about to write.
3. **The reach and the addressing rules carry over unchanged.** The base is the
   same four-bit `rm64` slot with `excluded: [4, 12]` for the `disp` rows and
   `[4, 5, 12, 13]` for the no-disp rows (`EC-02`, `EC-35`, `EC-38`), the
   `B̄` placement is the same `[13, 1]` inverted, and the vector operand keeps
   the five-bit EVEX slots of `0.13.0` (`R̄'` at 12, `R̄` at 15, `ModRM.reg` at
   43). Widening the register from `xmm` to `zmm` changes no slot.

## Decision

**`0.15.0` adds twelve EVEX memory rows — six at `ymm`, six at `zmm` — and
revises `EC-39` in place: `N` is a property of the form, carried by the
displacement slot's `target_type` (`disp8x16`, `disp8x32`, `disp8x64`). It is
never derived by dividing a byte offset at materialization time.**

Each width repeats the six `0.13.0` `xmm` memory shapes, in this order:

1. `x86:vmovaps/ymm-base-disp8x32/evex` (`62f17c28284000`), dest `ymm`,
   `disp8x32` content `−128 … 127` at `[48, 8]`.
2. `x86:vmovaps/ymm-base-disp32/evex` (`62f17c28288000000000`), dest `ymm`,
   `disp32` at `[48, 32]`.
3. `x86:vmovaps/base-disp8x32-ymm/evex` (`62f17c28294000`), src `ymm`, opcode
   `29`.
4. `x86:vmovaps/base-disp32-ymm/evex` (`62f17c28298000000000`), src `ymm`,
   opcode `29`.
5. `x86:vmovaps/ymm-base/evex` (`62f17c282800`), `mod=00`, no displacement.
6. `x86:vmovaps/base-ymm/evex` (`62f17c282900`), `mod=00`, opcode `29`.
7. `x86:vmovaps/zmm-base-disp8x64/evex` (`62f17c48284000`), dest `zmm`,
   `disp8x64` content `−128 … 127`.
8. `x86:vmovaps/zmm-base-disp32/evex` (`62f17c48288000000000`), dest `zmm`.
9. `x86:vmovaps/base-disp8x64-zmm/evex` (`62f17c48294000`), src `zmm`.
10. `x86:vmovaps/base-disp32-zmm/evex` (`62f17c48298000000000`), src `zmm`.
11. `x86:vmovaps/zmm-base/evex` (`62f17c482800`), `mod=00`.
12. `x86:vmovaps/base-zmm/evex` (`62f17c482900`), `mod=00`.

The `ymm` and `zmm` rows differ only in `P2` (`28` vs `48`), exactly as the
register-direct rows of `ADR-0041` do. A plan that passes a `zmm` operand to a
`ymm` row is `E-OPERAND-001`; one that names `disp8x16` on an `N = 32` row is
also `E-OPERAND-001`; a content of `128` is `E-RANGE-001`.

## Consequences

- `0.15.0` is a 91-form document with digest
  `sha256:305e96047cf870f963c7115ec1ecb205cdb48d83e629b67d5eb8db7720a014a4`.
- Its positive fixture `X86-P19-sse-ymm-zmm-memory` is twenty-six instructions
  and 192 bytes: every one of the twelve rows, both `disp8*N` extremes
  (`−4096`/`4064` at `ymm`, `−8192`/`8128` at `zmm`), both `disp32`
  promotions (`28`/`4096` and `60`/`8192`), and the `r8`+`ymm31`/`zmm31`
  combination that exercises `B̄`, `R̄` and `R̄'` in one instruction.
- `EC-39` keeps its carrier columns and gains the per-form `N`: the row is the
  only place the unit can live, because the row is what pins the width.
- No schema or Rust change. `target_type` is an opaque name compared for exact
  equality, and `disp8x16` already proved that the slot's value is the field
  content rather than a byte offset (`align_bits: 0`, `0.9.0` fixture).
- VEX.256 memory is **not** added, and it needs no new contract fact:
  `vmovaps (%rax), %ymm0` is `c5 fc 28 00` and `32(%rax)` is `c5 fc 28 40 20` —
  a plain `disp8` byte with no multiplication (`EC-02`, `EC-35`, `EC-38`).
  Naming `x86:vmovaps/ymm-base-disp8/vex` is `E-FORM-001` until a later slice
  adds it as coverage.
- Still absent: EVEX masking and broadcast, the `vvvv`/`V'` carrier, `movapd`,
  `movups`, and every mnemonic other than `movaps`/`vmovaps`.

## Alternatives rejected

- **One `disp8` slot with `N` derived from the row's width at materialization.**
  The materializer would read `P2` to choose a divisor and would then write
  that same byte — a choice over an encoding fact at materialization time
  (`INV-02`). Measured counterexample: `0x01` means `16`, `32` and `64` under
  the three `P2` values, so the divisor cannot be recovered from the plan's
  operand list, which is all a validator may use. A second failure follows: the
  same plan with content `127` is in range at `N = 32` (`4064`) and out of
  range at `N = 16` (`2032` is representable, `4064` is not), so a shared slot
  would reject a legal plan or silently truncate it.
- **A byte-offset operand with `align_bits: 5`/`6` in place of `disp8x32`/
  `disp8x64`.** `align_bits` is a validator assertion that the value is a
  multiple of the unit; it does not divide. The `0.9.0` `disp8x16` row states
  `align_bits: 0` and content `1` for `16(%rax)` precisely because the value is
  the field, not the offset, and `8(%rax)` must promote to `disp32` rather than
  round down (`N03d`, `EC-39`).
- **A `disp8x16` row plus a plan-side multiplier.** The multiplier would be an
  operand that writes no bit and selects no form (`OD-11`), and the materializer
  would still have to pick which rows accept it.
