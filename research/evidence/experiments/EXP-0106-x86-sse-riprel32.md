# EXP-0106 -- the SSE `%rip`-relative rows

- Date: 2026-11-09
- Question: how do the `movaps`/`vmovaps` xmm load and store encode when the
  memory operand is RIP-relative, and where does the 32-bit displacement sit in
  the legacy, VEX and EVEX encodings?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.68.0.json`; the generated `0.69.0` is the
  product of this experiment
- Fixture oracle: `fixtures/x86_64/positive/X86-P75-sse-riprel32.oracle.json`
- Sources: `research/evidence/experiments/EXP-0106/probe.s`,
  `research/evidence/experiments/EXP-0106/X86-P75-sse-riprel32.s`
- Decision: `ADR-0105`

## 1. What is already pinned

`EC-34` fixes the RIP-relative shape as a `form variant`: `mod = 00` with
`r/m = 101` is RIP + `disp32`, while the same `r/m` under `mod = 01`/`10` names a
base register. `0.2.0` shipped the two `mov` rows (`x86:mov/r64-riprel32/legacy`
and `x86:mov/riprel32-r64/legacy`, template `488b0500000000` / `48890500000000`)
with one `x86.rel`/`riprel32` target slot at `[24,32]`. `03_fixup_model.md` §4
defines `pcrel_end` as "address immediately after the instruction", and
`X86-P6` measures that rule at `addend = 0`.

The six SSE memory rows already in the table are base+`disp32` rows:
`x86:movaps/xmm-base-disp32/legacy` is `0f288000000000` with a `base` slot at
`[16,3]` and a `disp` slot at `[24,32]`. The `%rip` form is the same instruction
with `ModRM.rm` changed from the base register to `101`, so no base operand is
left and the displacement stays the last 32 bits.

## 2. The measurement

`probe.s` is the six instructions with a literal `16(%rip)` displacement,
assembled with `llvm-mc -triple=x86_64`:

| Source | Bytes | Length |
|---|---|---|
| `movaps 16(%rip), %xmm0` | `0f 28 05 10 00 00 00` | 7 |
| `movaps %xmm0, 16(%rip)` | `0f 29 05 10 00 00 00` | 7 |
| `vmovaps 16(%rip), %xmm0` | `c5 f8 28 05 10 00 00 00` | 8 |
| `vmovaps %xmm0, 16(%rip)` | `c5 f8 29 05 10 00 00 00` | 8 |
| `{evex} vmovaps 16(%rip), %xmm0` | `62 f1 7c 08 28 05 10 00 00 00` | 10 |
| `{evex} vmovaps %xmm0, 16(%rip)` | `62 f1 7c 08 29 05 10 00 00 00` | 10 |

The legacy pair is `0F 28`/`0F 29` with `ModRM = 05`; the VEX pair is the
two-byte `c5 f8` prefix with the same `ModRM`; the EVEX pair forces the four-byte
`62 f1 7c 08` prefix with `{evex}` and keeps the same `ModRM`. In every pair the
only difference between load and store is the opcode byte, which is `EC-27`'s
`form variant` split. `llvm-mc -show-encoding` reports one `reloc_riprel_4byte`
fixup per line, at byte 3/4/6 from the start of the instruction, which is the
same "last 32 bits" statement.

## 3. The fixture

`X86-P75-sse-riprel32.s` puts the six instructions first and places the local
label `L1` after 16 bytes of `.space` and four data bytes, so `L1` is at offset
66. The six instruction lengths are 7/7/8/8/10/10, so `pcrel_end` yields
59/52/44/36/26/16. The oracle image is 70 bytes:

```
0f28053b000000 0f290534000000 c5f828052c000000 c5f8290524000000
62f17c0828051a000000 62f17c08290510000000
00000000000000000000000000000000 aabbccdd
```

The input hash is
`60868d0c7ab9fd9f59d35d2f90c528deceb1e798d574d27f165c47376e6890f9`;
the output hash is
`32cbce4a1d1a0b312c527fad2d0f7b03596bd2d0e3281c5fd0abd825363f55da`,
size 70, 0 relocation records.

The plan states the same bytes through six `pcrel_end` fixups. The
`field_descriptor` follows the form: `[24,32]` for the legacy pair, `[32,32]`
for the VEX pair and `[48,32]` for the EVEX pair. That difference is the whole
point of the experiment: the same eight-bit `ModRM` sits at bit 16 in the
legacy row, at bit 24 in the two-byte VEX row and at bit 40 in the four-byte
EVEX row, so a single `[24,32]` placement would overwrite the prefix on the
longer families.

`0.69.0` has 519 forms and digest
`sha256:94dee360550537cbefed798bcc4e7d790b9a879391e0b6a47ecf24a819a6b596`.
It repeats the 513 `0.68.0` forms unchanged.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01eo` | names the absent `ymm` sibling `x86:vmovaps/ymm-riprel32/vex` against `0.69.0` | `E-FORM-001` |
| `N02cx` | drops the `target` from `x86:movaps/xmm-riprel32/legacy` | `E-OPERAND-002` (`expected: 2`, `found: 1`) |
| `N04i` | literal `riprel32 = 2147483648` on the EVEX load | `E-RANGE-002` (`max 2147483647`) |

`N01eo` is the deliberately absent sibling: the `ymm`/`zmm` memory rows exist
only as base+disp forms, and this slice does not add a RIP-relative width
window. `N04i` repeats `N04e` on the EVEX row, so the range rule is checked at
the placement the EVEX pair actually uses.

## 5. What the slice defers

- `ymm` and `zmm` `%rip`-relative windows; the VEX `L`/`W` and EVEX `L'L`
  width selection is a separate byte-affecting decision.
- `movups` and the other SSE mnemonics; this slice only widens `movaps` and
  `vmovaps`.
- The `addr32` form (`0x67` prefix); `ADR-0084` owns that prefix and `S6`
  measures it separately.
