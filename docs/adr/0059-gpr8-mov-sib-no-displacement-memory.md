# ADR-0059: the byte `mov` rows take the `SIB` bases at `mod = 00`

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P36` (the `mod = 00` byte-memory rows whose base is `%rsp` or
  `%r12`, in the four byte-register windows and both directions)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0058` §Review triggers (its first item, the `%rsp`/`%r12`
  `SIB` rows); `EC-35` (the `SIB` byte now appears at `mod = 00` in the byte
  family); `EC-06` (a `%r12` row fixes `REX.B` in its template)

## Context

`ADR-0058` gave the byte `mov` family the `mod = 00` shape but excluded four
bases: `%rbp`/`%r13` because `r/m = 101` is RIP-relative at that `mod`, and
`%rsp`/`%r12` because `r/m = 100` announces a `SIB` byte that shape has no room
for. `EC-35` had already made the `%rsp`/`%r12` pair a fixed-base row in every
other memory family — one row per base, base and `SIB` byte in the template —
and left this pair of `mod = 00` rows open.

`EXP-0061` measures the shape and four facts come out:

1. **The shape spends one `SIB` byte.** `movb (%rsp), %al` is `8a 04 24`:
   opcode, `ModRM = 04` (`mod = 00`, `r/m = 100`), `SIB = 24`. `%r12` is the
   same three bytes after a `REX` byte: `41 8a 04 24`. The `SIB` byte is
   `scale = 00`, `index = 100` ("no index") and `base = 100`, and only `REX.B`
   says whether that base reads `%rsp` or `%r12`.
2. **The byte is one longer than the plain-base row and one shorter than the
   `disp8` row.** `movb (%rsp), %al` is three bytes, `movb (%rax), %al` is two
   and `movb 0(%rsp), %al` is four (`8a 44 24 00`). A plan that wants the short
   encoding must name the row (`INV-02`).
3. **The high-byte window has no `%r12` half.** `movb (%r12), %ah` needs
   `REX.B`, and that prefix renames `%ah` to `%spl`; `llvm-mc` rejects the
   source with `can't encode 'ah' in an instruction requiring
   EVEX/REX2/REX prefix`. So the slice has seven base/register combinations
   and fourteen rows, not eight and sixteen.
4. **The four register windows and their slots are unchanged from
   `ADR-0058`.** The low window is `[11,3]` excluding `4`–`7` on the
   `REX`-less `%rsp` row and `[19,3]` on the `%r12` row; the high window is
   `[11,3]` excluding `0`–`3`; the `REX = 40` window is `[19,3]` excluding
   `0`–`3`; the extended window is `[2,1]` plus `[19,3]` excluding `0`–`7`.
   `movb (%rsp), %dil` is `40 8a 3c 24` and `movb (%r12), %r15b` is
   `45 8a 3c 24`, so both ends of the prefixed windows are exercised.

## Decision

**`0.32.0` appends fourteen rows: load and store, one per base (`%rsp`,
`%r12`) and register window, with the base and its `REX.B` bit fixed in the
template and `SIB = 24` in every row.**

| Register window | Base | `form_id` (load) | `form_id` (store) | Template | Length |
|---|---|---|---|---|---|
| `%al`–`%bl` | `%rsp` | `x86:mov/r8-rsp/legacy` | `x86:mov/rsp-r8/legacy` | `8a 04 24` / `88 04 24` | 3 |
| `%al`–`%bl` | `%r12` | `x86:mov/r8-r12/legacy` | `x86:mov/r12-r8/legacy` | `41 8a 04 24` / `41 88 04 24` | 4 |
| `%ah`–`%bh` | `%rsp` | `x86:mov/r8h-rsp/legacy` | `x86:mov/rsp-r8h/legacy` | `8a 24 24` / `88 24 24` | 3 |
| `%spl`–`%dil` | `%rsp` | `x86:mov/r8-rsp-rex/legacy` | `x86:mov/rsp-r8-rex/legacy` | `40 8a 24 24` / `40 88 24 24` | 4 |
| `%spl`–`%dil` | `%r12` | `x86:mov/r8-r12-rex/legacy` | `x86:mov/r12-r8-rex/legacy` | `41 8a 24 24` / `41 88 24 24` | 4 |
| `%r8b`–`%r15b` | `%rsp` | `x86:mov/r8-ext-rsp/legacy` | `x86:mov/rsp-r8-ext/legacy` | `44 8a 04 24` / `44 88 04 24` | 4 |
| `%r8b`–`%r15b` | `%r12` | `x86:mov/r8-ext-r12/legacy` | `x86:mov/r12-r8-ext/legacy` | `45 8a 04 24` / `45 88 04 24` | 4 |

Four properties follow:

- **The base is not an operand.** The row fixes it, exactly as the `disp8` and
  `disp32` `%rsp`/`%r12` rows already do, so a plan that supplies a `base`
  operand is `E-OPERAND-002` (`N02aw`). Supplying `%rax` instead of `%rsp` is
  not a rejected value but a different row.
- **`REX.B` is a template bit, not a slot.** The six `%r12` rows write `41`
  or `45` with `B = 1`; the `%rsp` rows write `B = 0`. No slot reads or
  writes `[0,1]`, so the base cannot be changed from the plan (`INV-04`).
- **`SIB = 24` is the whole address.** `scale = 00`, `index = 100` and
  `base = 100` are constants in the template. The row has no `index`, `scale`
  or `disp` slot, so any of those operands is `E-OPERAND-002`.
- **The register slot keeps its window's width and exclusion.** The two
  `REX`-less `%rsp` rows use `[11,3]`; the four `REX`-prefixed `%rsp`/`%r12`
  rows use `[19,3]`; the extended rows add `[2,1]`. The `REX` byte is already
  present, so no `gpr8` slot has to exclude `4`–`7` for its own sake — that
  rule applies only to `REX`-less templates.

## Consequences

- `0.32.0` is a 289-form document, byte-reproducing every `0.31.0` row.
- Its positive fixture `X86-P36-gpr8-mov-mem-sib-nodisp` has fourteen
  instructions and 52 bytes: one per row, three bytes for the two `REX`-less
  `%rsp` rows and four for the other twelve. Each `%rsp` row and its `%r12`
  twin differ only in the first byte; the high-byte pair is absent by the
  `EC-36` rule.
- Negatives pin the version boundary in both directions (`N01bq`, `N01br`), a
  `base` operand on a fixed-base row (`N02ay`), a `disp` operand on a row with
  no displacement slot (`N02az`), `%r12` with `%ah` leaving no row (`N01bs`),
  register `16`/`8` at the window ends (`N14af`, `N14ag`), and register `0` on
  the `REX = 40` row (`N16an`).
- `EC-35` is revised in place: `mod = 00` now has the same fixed-base `SIB`
  rows the other shapes have. `EC-06` gains one sentence for the template
  `REX.B`. No new `EC` row appears and no row is renumbered.
- No schema, loader or materializer change: the rows are one-slot forms of the
  shape `x86:vmovaps/xmm-rsp/evex` already used.

## Alternatives rejected

- **Let the plain-base row accept `%rsp`/`%r12` and insert a `SIB` byte from
  the operand value.** The length would then depend on a value, which is
  `INV-04`; `EC-35` already forbids it, and `llvm-mc` writes two distinct
  shapes rather than one that grows.
- **Give the row a `base` slot and an operand-owned `SIB` byte.** The `SIB`
  byte would have to carry `index = 100` and `scale = 00` as exclusions, and
  the plan could choose a different base; the frozen base is what keeps the
  row one byte shorter than the operand-owned `0.8.0` shape.
- **Take `%r12` and `%ah` in one row by clearing `REX.B`.** That row would
  encode `(%rsp), %ah`, not the source the plan names; `llvm-mc` rejects the
  combination outright.
- **Fold the `%r12` rows into the `%rsp` rows by taking `REX.B` from an
  operand.** There is no base operand to read it from, and inventing one
  reintroduces the implicit choice above.
- **Take the `REX.X` index and scale at byte width in this slice.** A
  `SIB.index` other than `100` is a different address shape with its own
  operand and exclusions; one shape per ADR.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8a 04 24` / `41 8a 04 24` / `8a 24 24` at three or four bytes | `llvm-mc -show-encoding`, `EXP-0061` §1 | high |
| `SIB = 24` is `scale = 00`, `index = 100`, `base = 100` | `llvm-mc -show-encoding`, `EXP-0061` §2 | high |
| `REX.B` alone distinguishes `%rsp` from `%r12` | `llvm-mc -show-encoding`, `EXP-0061` §2 | high |
| `%r12` + `%ah` has no encoding | `llvm-mc` rejection, `EXP-0061` §4 | high |
| the register windows and exclusions are unchanged | `llvm-mc -show-encoding`, `EXP-0061` §1, §3 | high |

## Review triggers

- A `SIB` index or scale is requested at byte width.
- The `REX.X` bit is given a placement at byte width.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- `moffs` for the byte width is requested.
- The APX `d5` register window is attempted.
- A width other than eight bits takes the no-displacement shape.
- The high-byte window is asked for an extended base despite `EC-36`.
