# EXP-0107 -- the extended register on the fixed-base legacy SSE rows

- Date: 2026-11-09
- Question: the four fixed-base legacy SSE `movaps` rows (`%rsp`/`%r12` ×
  load/store × `disp8`/`disp32`) hold only `xmm0`-`xmm7`. What does the same
  instruction cost when the register is `xmm8`-`xmm15`, and how far does every
  fixed field move?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.69.0.json`; the generated `0.70.0` is the
  product of this experiment
- Fixture oracle: `fixtures/x86_64/positive/X86-P76-sse-ext-fixed-base.oracle.json`
- Sources: `research/evidence/experiments/EXP-0107/probe.s`,
  `research/evidence/experiments/EXP-0107/X86-P76-sse-ext-fixed-base.s`
- Decision: `ADR-0106`

## 1. What is already pinned

`EC-35` fixes the fixed-base shape: `%rsp` forces `ModRM.rm = 100` and a `SIB`
byte whose base is also `100`, while `%r12` adds `REX.B`. `0.20.0` shipped the
legacy rows as `0f28442400`/`0f28842400000000` (`%rsp`) and
`410f28442400`/`410f28842400000000` (`%r12`), with the register at `[19,3]` and
`[27,3]` and the displacement at `[32,8]`/`[32,32]`/`[40,8]`/`[40,32]`; that
seven-bit window is exactly `xmm0`-`xmm7`.

`EC-38` already states the rule this experiment applies: a reach that would
change the instruction length is a `form_id` component, never a value the
materializer inserts from an operand (`INV-04`). The legacy rows have no `REX`
byte at all, so the register's fourth bit cannot be carried without one.

## 2. The measurement

`probe.s` is the eight instructions with the fixture's operands, assembled with
`llvm-mc -triple=x86_64`:

| Source | Bytes | Length |
|---|---|---|
| `movaps 8(%rsp), %xmm8` | `44 0f 28 44 24 08` | 6 |
| `movaps 8(%r12), %xmm9` | `45 0f 28 4c 24 08` | 6 |
| `movaps 128(%rsp), %xmm14` | `44 0f 28 b4 24 80 00 00 00` | 9 |
| `movaps 128(%r12), %xmm15` | `45 0f 28 bc 24 80 00 00 00` | 9 |
| `movaps %xmm10, 8(%rsp)` | `44 0f 29 54 24 08` | 6 |
| `movaps %xmm11, 8(%r12)` | `45 0f 29 5c 24 08` | 6 |
| `movaps %xmm12, 128(%rsp)` | `44 0f 29 a4 24 80 00 00 00` | 9 |
| `movaps %xmm13, 128(%r12)` | `45 0f 29 ac 24 80 00 00 00` | 9 |

The first byte is the `REX` byte the low row does not have. `%rsp` pays `44`
(`REX.R`); `%r12` pays `45` (`REX.R` and `REX.B`). `REX.R` is bit 2 of that
byte, so the register is one bit at `[2,1]` plus the three bits at `[27,3]`
(`ModRM.reg`). Everything after the prefix moves by one byte: `ModRM` at 24,
`SIB` at 32 and the displacement at `[40,8]`/`[40,32]`.

The load/store split stays `0F 28`/`0F 29`, and `disp8`/`disp32` stays a
`ModRM.mod` choice (`EC-02`), so the eight rows are the two existing axes
crossed with the register window.

## 3. The fixture

`X86-P76-sse-ext-fixed-base.s` is identical to `probe.s`. The eight
instructions are 6/6/9/9/6/6/9/9 bytes for 60 in all; there is no label and no
relocation. The oracle image is:

```
440f28442408 450f284c2408 440f28b42480000000 450f28bc2480000000
440f29542408 450f295c2408 440f29a42480000000 450f29ac2480000000
```

The input hash is
`b465ac746967c9ab8ede119518bf950c28b3abe8a585d2276d248d2ae7411c68`;
the output hash is
`d2fef597f7b2174b80f8ad83271369932d03582eaca6c70a5e7f0f825f1a7f63`,
size 60, 0 relocation records. Every operand is a register or a literal
displacement, so the plan carries no fixup.

`0.70.0` has 527 forms and digest
`sha256:02cbd866ce04b7584456bccf177c1aef7395a6b503240ddd1617be8e73f9eb2e`.
It repeats the 519 `0.69.0` forms unchanged.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01ep` | names `x86:movaps/xmm-ext-rsp-disp32/legacy` against `0.69.0` | `E-FORM-001` |
| `N02cy` | drops the `disp` from `x86:movaps/xmm-ext-r12-disp32/legacy` | `E-OPERAND-002` (`expected: 2`, `found: 1`) |
| `N03zt` | `disp8 = 128` on `x86:movaps/xmm-ext-rsp-disp8/legacy` | `E-RANGE-001` (`max 127`) |

The low rows keep their old window, so `N14w` (register 8 on a `0.20.0` row)
stays exactly as it was: the fix is a new row, not a widened slot.

## 5. What the slice defers

- The `xmm-ext` window on the general (non-`SIB`) legacy base rows is already
  `0.11.0`'s `xmm-ext-base-disp8`/`-disp32` shape; this slice only adds the two
  fixed `SIB` bases.
- `movups` and the other legacy SSE mnemonics; this slice widens `movaps` only.
- VEX and EVEX fixed-base rows already reach `xmm15`/`xmm31` at no extra
  length, because their register's fourth bit lives in the prefix that is
  already there.
