# EXP-0109 -- the legacy and VEX SSE indexed shape

- Date: 2026-11-09
- Question: the legacy `movaps` and VEX `vmovaps` rows cover `%rip`, fixed
  `%rsp`/`%r12` bases and plain bases, but no general `SIB` base+index shape.
  What does `8(%rax,%rcx,4)` cost at both register windows, and where do the
  index, scale and displacement sit behind each family's prefix?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.71.0.json`; the generated `0.72.0` is the
  product of this experiment
- Fixture oracle: `fixtures/x86_64/positive/X86-P78-sse-index.oracle.json`
- Sources: `research/evidence/experiments/EXP-0109/probe.s`,
  `research/evidence/experiments/EXP-0109/X86-P78-sse-index.s`
- Decision: `ADR-0108`

## 1. What is already pinned

`EC-37` fixes the `SIB` byte: `ModRM.rm = 100` selects it, `SIB.index = 100`
with `REX.X = 0` means "no index", and the scale is two bits. `EC-38` fixes the
reach per family: the legacy row has no `REX` byte in its low window, VEX puts
the register's fourth bit in the prefix, and a reach that changes length is a
form. `0.20.0` shipped the `%rsp`/`%r12` SSE `SIB` pair, and `0.21.0` did the
same for EVEX; the general index operand exists only in the EVEX rows.

The low base/index window is the three-bit field, so `REX.B`/`REX.X` and
`B̄`/`X̄` never move; the only variable is the value register's fourth bit, and
that is where the two windows split.

## 2. The measurement

`probe.s` is twenty instructions: the four zero-displacement shapes, then
`disp8`/`disp32` at both windows for legacy and VEX, load and store.

| Source | Bytes | Length |
|---|---|---|
| `movaps 8(%rax,%rcx,4), %xmm1` | `0f 28 4c 88 08` | 5 |
| `movaps %xmm1, 8(%rax,%rcx,4)` | `0f 29 4c 88 08` | 5 |
| `movaps 128(%rax,%rcx,4), %xmm2` | `0f 28 94 88 80 00 00 00` | 8 |
| `movaps %xmm2, 128(%rax,%rcx,4)` | `0f 29 94 88 80 00 00 00` | 8 |
| `movaps 8(%rax,%rcx,4), %xmm8` | `44 0f 28 44 88 08` | 6 |
| `movaps %xmm8, 8(%rax,%rcx,4)` | `44 0f 29 44 88 08` | 6 |
| `movaps 128(%rax,%rcx,4), %xmm9` | `44 0f 28 8c 88 80 00 00 00` | 9 |
| `movaps %xmm9, 128(%rax,%rcx,4)` | `44 0f 29 8c 88 80 00 00 00` | 9 |
| `vmovaps 8(%rax,%rcx,4), %xmm1` | `c5 f8 28 4c 88 08` | 6 |
| `vmovaps %xmm1, 8(%rax,%rcx,4)` | `c5 f8 29 4c 88 08` | 6 |
| `vmovaps 128(%rax,%rcx,4), %xmm2` | `c5 f8 28 94 88 80 00 00 00` | 9 |
| `vmovaps %xmm2, 128(%rax,%rcx,4)` | `c5 f8 29 94 88 80 00 00 00` | 9 |
| `vmovaps 8(%rax,%rcx,4), %xmm8` | `c5 78 28 44 88 08` | 6 |
| `vmovaps %xmm8, 8(%rax,%rcx,4)` | `c5 78 29 44 88 08` | 6 |
| `vmovaps 128(%rax,%rcx,4), %xmm9` | `c5 78 28 8c 88 80 00 00 00` | 9 |
| `vmovaps %xmm9, 128(%rax,%rcx,4)` | `c5 78 29 8c 88 80 00 00 00` | 9 |

The `SIB` byte is `0x88` throughout: scale `2` (×4), index `1` (`%rcx`), base
`0` (`%rax`). The legacy high window pays the `44` `REX.R` byte; the VEX high
window only flips byte 1 from `f8` to `78` (`R̄`), so both windows cost the same
six/nine bytes under VEX.

## 3. The fixture

`X86-P78-sse-index.s` is sixteen instructions over `8/128(%rax,%rcx,4)`, one
per row, at registers `xmm0`-`xmm15`. Sizes are
5/5/8/8/6/6/9/9/6/6/9/9/6/6/9/9 for 116 bytes; there is no label and no
relocation.

The input hash is
`9c51d4ddf64b68e5e0cf7e223b09f56aee6f0988513bca06433cbd037e0292c4`;
the output hash is
`9124dc848eeb6d3581de40523f89ba403871ac20453ec1ea6d598b081ddd7ab6`,
size 116, 0 relocation records.

`0.72.0` has 549 forms and digest
`sha256:15fbacc2e014b9c135762f53a8b55b8c7d5dc21e9ff665ee5a0259437d70bf11`.
It repeats the 533 `0.71.0` forms unchanged.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01er` | names `x86:movaps/xmm-ext-base-index-disp32/legacy` against `0.71.0` | `E-FORM-001` |
| `N02da` | drops the base from `x86:movaps/xmm-base-index-disp8/legacy` | `E-OPERAND-002` (`expected: 5`, `found: 4`) |
| `N03zu` | `disp8 = 128` on `x86:movaps/xmm-ext-base-index-disp8/legacy` | `E-RANGE-001` (`max 127`) |

## 5. What the slice defers

- The zero-displacement (`mod = 00`) indexed shape: the four rows measured in
  `probe.s` are not in the table; the slice ships `disp8`/`disp32` only.
- High base (`%r8`-`%r15`) and high index (`%r8`-`%r15`): those need
  `REX.B`/`REX.X` (legacy) or `B̄`/`X̄` (VEX, three-byte prefix), which changes
  the template and is the next window on the same axis.
- The EVEX indexed rows already exist (they carry the inverted bits in the
  four-byte prefix); this slice only fills the legacy and VEX families.
- Other legacy/VEX SSE mnemonics (`movups`, arithmetic): the opcode changes,
  so each needs its own measurement.
