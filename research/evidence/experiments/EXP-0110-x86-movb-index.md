# EXP-0110 -- the indexed byte `mov` in its three no-new-prefix windows

- Date: 2026-11-09
- Question: the 8-bit `mov` has four byte-register windows (`%al`-`%dl`,
  `%ah`-`%dh`, `%spl`-`%dil` behind `REX`, and `%r8b`-`%r15b` behind `REX.R`),
  but no indexed memory shape. Which windows reach `8(%rax,%rcx,4)` without a
  new prefix byte, and where do the index/scale/displacement sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.72.0.json`; the generated `0.73.0` is the
  product of this experiment
- Fixture oracle: `fixtures/x86_64/positive/X86-P79-movb-index.oracle.json`
- Sources: `research/evidence/experiments/EXP-0110/X86-P79-movb-index.s`
- Decision: `ADR-0109`

## 1. What is already pinned

`EC-06`/`EC-36` fix the four byte windows: the REX-less row holds numbers 0-3
(`%al`-`%dl`), the high-byte row numbers 4-7 (`%ah`-`%dh`), the `REX = 40` row
re-labels 4-7 to `%spl`-`%dil`, and a fourth-bit window (`%r8b`-`%r15b`) needs
`REX.R`, which is present only in `-ext` rows. The rows are disjoint by
`excluded`, so one register names exactly one window.

`EC-37` fixes the `SIB` byte; the byte `mov` indexed shape does not exist yet,
only the plain-base and fixed `%rsp`/`%r12` shapes from `0.17.0`-`0.19.0`.

## 2. The measurement

`X86-P79-movb-index.s` is the twelve fixture instructions:

| Source | Bytes | Length |
|---|---|---|
| `movb 8(%rax,%rcx,4), %al` | `8a 44 88 08` | 4 |
| `movb %bl, 8(%rax,%rcx,4)` | `88 5c 88 08` | 4 |
| `movb 128(%rax,%rcx,4), %cl` | `8a 8c 88 80 00 00 00` | 7 |
| `movb %dl, 128(%rax,%rcx,4)` | `88 94 88 80 00 00 00` | 7 |
| `movb 8(%rax,%rcx,4), %ah` | `8a 64 88 08` | 4 |
| `movb %bh, 8(%rax,%rcx,4)` | `88 7c 88 08` | 4 |
| `movb 128(%rax,%rcx,4), %ch` | `8a ac 88 80 00 00 00` | 7 |
| `movb %dh, 128(%rax,%rcx,4)` | `88 b4 88 80 00 00 00` | 7 |
| `movb 8(%rax,%rcx,4), %spl` | `40 8a 64 88 08` | 5 |
| `movb %bpl, 8(%rax,%rcx,4)` | `40 88 6c 88 08` | 5 |
| `movb 128(%rax,%rcx,4), %sil` | `40 8a b4 88 80 00 00 00` | 8 |
| `movb %dil, 128(%rax,%rcx,4)` | `40 88 bc 88 80 00 00 00` | 8 |

The `SIB` byte is `0x88` throughout (scale 2 = ×4, index 1 = `%rcx`, base 0 =
`%rax`). Only the `%spl` window pays a prefix byte (`40`), and it is the same
one its plain-base row already has. The `%r8b` window is not here: its
`REX.R = 44` byte would put it in a fourth template.

## 3. The fixture

`X86-P79-movb-index.s` is the twelve rows, one per window and direction at
`8`/`128(%rax,%rcx,4)`. Sizes are 4/4/7/7/4/4/7/7/5/5/8/8 for 70 bytes; there
is no label and no relocation.

The input hash is
`815efc78474aef7e5e37dd5bdcb2604b89ebb6effa4066cfc2eb70e47a8fffb1`;
the output hash is
`59a618ac3881b25cded5814481662c5b8bc11af250f1d3ac6cb245cb4afe2678`,
size 70, 0 relocation records.

`0.73.0` has 561 forms and digest
`sha256:dfe7c9385b5a6a8636d8a54252ba72e3630aee3573b7e71062c4d7f8777d4237`.
It repeats the 549 `0.72.0` forms unchanged.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01es` | names `x86:mov/r8h-base-index-disp32/legacy` against `0.72.0` | `E-FORM-001` |
| `N02db` | drops the base from `x86:mov/r8-base-index-disp8/legacy` | `E-OPERAND-002` (`expected: 5`, `found: 4`) |
| `N03zv` | `disp8 = 128` on `x86:mov/r8-base-index-disp8-rex/legacy` | `E-RANGE-001` (`max 127`) |

## 5. What the slice defers

- The `%r8b`-`%r15b` window: it needs `REX.R` (or the fourth bit in the same
  `REX` byte as `REX.W` for `r8`-`r15` bases/indexes), a different template.
- The zero-displacement (`mod = 00`) indexed shape: the slice ships
  `disp8`/`disp32` only, as with S4.
- High base/index (`%r8`-`%r15`): measured separately (`41 8a 04 88` for a high
  base, `42 8a 04 88` for a high index) but not part of this slice.
- 16-bit (`r16`) and 64-bit (`r64`) indexed rows: the `66`/`REX.W` prefixes
  change the template and are separate slices.
