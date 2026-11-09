# ADR-0109: the indexed byte `mov` in the three no-new-prefix windows

- Status: accepted
- Date: 2026-11-09
- Settles: `X86-P79` (the twelve indexed byte `mov` rows and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-36` of `02_encoding_choices.md` (the byte-window rule gains the
  indexed rows); the reading-aid table and `0.73.0` paragraph of
  `07_definition_format.md` §8.1; the x86 table of `06_validation_matrix.md`;
  adds `definitions/x86_64/0.73.0.json`, `EXP-0110` and the
  `X86-P79`/`N01es`/`N02db`/`N03zv` fixtures

## Context

The 8-bit `mov` shipped its plain-base rows at `0.4.0` and its fixed
`%rsp`/`%r12` rows by `0.19.0`, but it has no general `SIB` base+index shape.
The four byte-register windows are fixed by `EC-06`/`EC-36`: numbers 0-3 in the
REX-less low row, 4-7 in the high-byte row, 4-7 in the `REX = 40` row, and
`%r8b`-`%r15b` behind `REX.R`. The rows are disjoint by `excluded`.

`EXP-0110` measures the indexed shape at `8/128(%rax,%rcx,4)`:

- `%al` window: `movb 8(%rax,%rcx,4), %al` = `8a 44 88 08` (4 B);
- `%ah` window: `movb 8(%rax,%rcx,4), %ah` = `8a 64 88 08` (4 B);
- `%spl` window: `movb 8(%rax,%rcx,4), %spl` = `40 8a 64 88 08` (5 B).

Only the `%spl` window carries a prefix, and it is the same `40` its plain-base
row already has. The `%r8b` window would need `REX.R` (`44`), a fourth
template, and is out of this slice.

## Decision

1. **Twelve rows.** `0.73.0` appends, for each window × {load, store} ×
   {`disp8`, `disp32`}: `x86:mov/r8-base-index-disp8/legacy`,
   `x86:mov/base-index-disp8-r8/legacy`,
   `x86:mov/r8h-base-index-disp8/legacy`,
   `x86:mov/base-index-disp8-r8h/legacy`,
   `x86:mov/r8-base-index-disp8-rex/legacy`,
   `x86:mov/base-index-disp8-r8-rex/legacy`, and the four `disp32` siblings.
   The `-rex` suffix is the existing spelling for the `40`-prefixed window.
2. **Slots follow the measured bytes.** Value register in `ModRM.reg` at
   `[11,3]` (the REX-less rows) or `[19,3]` (the `-rex` rows), with the
   window's exclusion: `[4,5,6,7]` for `r8`, `[0,1,2,3]` for `r8h` and
   `r8-rex`. Base `x86.gpr64`/`rm64` at `[16,3]`/`[24,3]`; index
   `x86.gpr64`/`sib_index` at `[19,3]`/`[27,3]` with `4` excluded; scale
   `x86.scale`/`scale2` at `[22,2]`/`[30,2]`; displacement
   `x86.imm`/`disp8` or `/disp32` at `[24,…]`/`[32,…]`.
3. **The base and index stay low.** Three-bit fields, so no `REX.B`/`REX.X`
   appears; reaching `%r8`-`%r15` is a separate window with a different
   template.
4. **The `%r8b`-`%r15b` window is deliberately absent.** It needs `REX.R`,
   so it cannot reuse these rows; a plan that names it is a missing form.
5. **`0.73.0` is additive and immutable.** It repeats the 549 `0.72.0` forms
   byte-for-byte, and the generator asserts the reproduction before it writes
   the new version. The digest is
   `sha256:dfe7c9385b5a6a8636d8a54252ba72e3630aee3573b7e71062c4d7f8777d4237`.

## Consequences

- `X86-P79-movb-index` is the 70-byte vector of twelve instructions, no label
  and no relocation. The input hash is
  `815efc78474aef7e5e37dd5bdcb2604b89ebb6effa4066cfc2eb70e47a8fffb1` and the
  output hash is
  `59a618ac3881b25cded5814481662c5b8bc11af250f1d3ac6cb245cb4afe2678`.
- `N01es` pins the `0.72.0` boundary, `N02db` the operand count
  (`expected: 5`, `found: 4`) and `N03zv` the signed-8 end.
- The corpus grows to 120 positives and 583 negatives; every one of the 561
  forms in `0.73.0` is named by a positive fixture (`check_definition.py`).
- `0.72.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **Give `r8` four bits and let the materializer pick the window.** Rejected:
  the window changes the template (a `40` byte, or a different register-name
  class), so the length and bytes would depend on the operand (`INV-04`).
- **Reuse the `r8h` row for `%spl`.** Rejected: `%ah` and `%spl` share a
  register number but not a `kind`/`target_type`; `EC-36` already requires two
  rows (`ADR-0029`), and the `40` byte differs.
- **Add all four windows now.** Rejected: `%r8b` needs `REX.R` (`44`), which
  is a new template and the next window on the axis; the slice keeps the
  three that add no prefix.
- **Add the zero-displacement shape too.** Rejected: `mod = 00` is a third
  length, deferred as in `ADR-0108`.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The twelve instructions are 4/4/7/7/4/4/7/7/5/5/8/8 bytes | `llvm-mc` object bytes, `EXP-0110` §2 | high |
| `SIB = 88` and the index/scale placements | placement arithmetic on the measured bytes | high |
| `%spl` pays `40`; `%ah` does not | measured bytes, `EXP-0110` §2 | high |
| `%r8b` would need `44` | measured `41 8a 04 88`/`42 8a 04 88` in `EXP-0110` §5 | high |
| `0.73.0` repeats `0.72.0` unchanged | generator assertion and digest | high |
| `N01es` is `E-FORM-001`, `N02db` `E-OPERAND-002`, `N03zv` `E-RANGE-001` | fixture gate, `EXP-0110` §4 | high |

## Review triggers

- The `%r8b`-`%r15b` window is proposed; `REX.R` adds the fourth template.
- A high base or high index is proposed; `REX.B`/`REX.X` change the template.
- The zero-displacement indexed shape is proposed; it is `mod = 00`, a third
  length.
- A 16-bit or 64-bit indexed row is proposed; the `66`/`REX.W` byte changes
  the template, so it cannot copy these placements.
