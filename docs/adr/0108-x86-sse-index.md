# ADR-0108: the legacy and VEX SSE families gain the indexed shape

- Status: accepted
- Date: 2026-11-09
- Settles: `X86-P78` (the sixteen indexed `movaps`/`vmovaps` rows and their
  byte vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-37` of `02_encoding_choices.md` (the `SIB` choice now names the
  SSE rows); the reading-aid table and `0.72.0` paragraph of
  `07_definition_format.md` §8.1; the x86 table of `06_validation_matrix.md`;
  adds `definitions/x86_64/0.72.0.json`, `EXP-0109` and the
  `X86-P78`/`N01er`/`N02da`/`N03zu` fixtures

## Context

`0.20.0` gave the legacy SSE rows the fixed `%rsp`/`%r12` `SIB` pair
(`ADR-0047`), and `0.21.0` gave EVEX the general indexed shape. The legacy and
VEX families have no general `base + index` operand: `%rip`, fixed bases and
plain bases exist, but `8(%rax,%rcx,4)` has no row.

`EC-37` already fixes the `SIB` mechanics: `ModRM.rm = 100`, `SIB.index = 100`
with `REX.X = 0` means "no index", and the scale is two bits. `EC-38` fixes the
reach: the register's fourth bit is a form component when it changes the
length. `EXP-0109` measures the shape at both windows:

- legacy low: `movaps 8(%rax,%rcx,4), %xmm1` = `0f 28 4c 88 08` (5 B);
- legacy high: `movaps 8(%rax,%rcx,4), %xmm8` = `44 0f 28 44 88 08` (6 B);
- VEX low: `vmovaps …` = `c5 f8 28 4c 88 08` (6 B);
- VEX high: `vmovaps …` = `c5 78 28 44 88 08` (6 B), same length.

The high window is therefore a separate row in both families: legacy pays a
`REX.R` byte (a length change), and VEX flips `R̄` in a prefix that is already
present (same length, different template byte). Inserting either from a
register value would violate `INV-04`.

## Decision

1. **Sixteen new rows.** `0.72.0` appends, for each of {`xmm`, `xmm-ext`} ×
   {load, store} × {`disp8`, `disp32`} × {legacy, VEX}:
   `x86:movaps/xmm-base-index-disp8/legacy` and its siblings, named after the
   existing `xmm-ext-base-disp8` pattern. The generator lists them explicitly.
2. **Slots are the measured ones.** Value register in `ModRM.reg`
   (`[19,3]` legacy low; `[27,3]` behind a `REX`/VEX byte) plus, for the high
   window, `REX.R` at `[2,1]` (legacy) or `R̄` at `[15,1]` inverted (VEX),
   with `xmm0`-`xmm7` excluded. `base` is `x86.gpr64`/`rm64` at `[24,3]` or
   `[32,3]`; `index` is `x86.gpr64`/`sib_index` at `[27,3]`/`[35,3]` with `4`
   excluded; the scale is `x86.scale`/`scale2` at `[30,2]`/`[38,2]`; the
   displacement is `x86.imm`/`disp8` or `/disp32` at `[32,…]`/`[40,…]`.
3. **The base and index stay low.** Both are three-bit fields, so the
   `REX.X`/`REX.B` and `X̄`/`B̄` bits stay at their template values. Reaching
   `%r8`-`%r15` is the next window and is not part of this slice (a
   `c4` three-byte VEX for the VEX family, an extra `REX` bit for the legacy
   one).
4. **VEX rows require `["avx"]`; legacy rows require `[]`.** The legacy rows
   are SSE, the VEX rows are AVX, and `requires_extensions` already carries
   that split.
5. **`0.72.0` is additive and immutable.** It repeats the 533 `0.71.0` forms
   byte-for-byte, and the generator asserts the reproduction before it writes
   the new version. The digest is
   `sha256:15fbacc2e014b9c135762f53a8b55b8c7d5dc21e9ff665ee5a0259437d70bf11`.

## Consequences

- `X86-P78-sse-index` is the 116-byte vector of sixteen instructions, no label
  and no relocation. The input hash is
  `9c51d4ddf64b68e5e0cf7e223b09f56aee6f0988513bca06433cbd037e0292c4` and the
  output hash is
  `9124dc848eeb6d3581de40523f89ba403871ac20453ec1ea6d598b081ddd7ab6`.
- `N01er` pins the `0.71.0` boundary, `N02da` the operand count
  (`expected: 5`, `found: 4`) and `N03zu` the signed-8 end at the new
  displacement placement.
- The corpus grows to 119 positives and 580 negatives; every one of the 549
  forms in `0.72.0` is named by a positive fixture (`check_definition.py`).
- `0.71.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **One row per mnemonic with a four-bit base/index field.** Rejected: the
  fourth bits are separate `REX`/VEX bits, and setting them changes the
  template (the legacy byte appears, the VEX prefix grows to three bytes), so
  the length would depend on operands (`INV-04`).
- **Share one row between the low and high `xmm` windows.** Rejected: the
  legacy high window needs a `REX.R` byte that the low row does not have; the
  value would choose the length.
- **Add the zero-displacement shape too.** Rejected: `disp8`/`disp32` already
  widen the row count sixteen-fold; the `mod = 00` shape is a third length and
  stays deferred with the high base/index windows.
- **Copy the EVEX rows and clear the masking fields.** Rejected: EVEX carries
  inverted bits in a four-byte prefix (`62 …`), so neither the lengths nor the
  placements carry over; the legacy/VEX bytes were measured directly.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The sixteen instructions are 5/5/8/8/6/6/9/9/6/6/9/9/6/6/9/9 bytes | `llvm-mc` object bytes, `EXP-0109` §2 | high |
| `SIB = 88` and the index/scale placements | placement arithmetic on the measured bytes | high |
| Legacy high pays `REX.R = 44`; VEX high flips `c5 f8` to `c5 78` | measured bytes, `EXP-0109` §2 | high |
| `0.72.0` repeats `0.71.0` unchanged | generator assertion and digest | high |
| `N01er` is `E-FORM-001`, `N02da` `E-OPERAND-002`, `N03zu` `E-RANGE-001` | fixture gate, `EXP-0109` §4 | high |

## Review triggers

- The high base or high index window is proposed; legacy needs `REX.B`/
  `REX.X`, VEX needs the three-byte `c4` prefix, and both change the template.
- The zero-displacement indexed shape is proposed; it is `mod = 00` with
  `SIB.base = 101` meaning "no base", a different length and meaning.
- Another SSE mnemonic is proposed for the indexed shape; the opcode byte
  changes and the row must be measured.
- Scale `1`/`2`/`8` (`SIB.scale = 0/1/3`) is proposed; the field is already
  two bits, so no new row is needed, but a fixture must cover the other legal
  values.
