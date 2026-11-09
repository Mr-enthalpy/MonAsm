# ADR-0105: SSE `%rip`-relative rows are six forms

- Status: accepted
- Date: 2026-11-09
- Settles: `X86-P75` (the six SSE `%rip`-relative rows and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-34` of `02_encoding_choices.md` (the decision stays `form
  variant`; the clause that names only the GPR `mov` rows now names the SSE
  rows too); the reading-aid table and `0.69.0` paragraph of
  `07_definition_format.md` §8.1; the x86 table of `06_validation_matrix.md`;
  adds `definitions/x86_64/0.69.0.json`, `EXP-0106` and the
  `X86-P75`/`N01eo`/`N02cx`/`N04i` fixtures

## Context

`0.68.0` has the `movaps`/`vmovaps` xmm load and store at the base+`disp8`,
base+`disp32`, `%rsp`/`%r12`, and index shapes, but every one of them carries a
`base` slot. A plan that wants to load through the instruction pointer has no
row: `x86:movaps/xmm-riprel32/legacy` does not exist, and naming it is
`E-FORM-001`.

`EC-34` already fixes the encoding decision: `mod = 00` with `r/m = 101` is
RIP + `disp32`, and the same `r/m` under `mod = 01`/`10` names a base. `0.2.0`
shipped the GPR pair with one `x86.rel`/`riprel32` target slot at `[24,32]`.
`EXP-0106` measures the SSE pair in the three families: the opcode is `0F 28`/
`0F 29` (legacy), `c5 f8 28`/`c5 f8 29` (VEX) and `62 f1 7c 08 28`/
`62 f1 7c 08 29` (EVEX), always with `ModRM = 05` and a 32-bit displacement
that is the last field of the instruction.

## Decision

1. **Six forms, not one parameterised memory row.** `0.69.0` appends
   `x86:movaps/xmm-riprel32/legacy`,
   `x86:movaps/riprel32-xmm/legacy`,
   `x86:vmovaps/xmm-riprel32/vex`,
   `x86:vmovaps/riprel32-xmm/vex`,
   `x86:vmovaps/xmm-riprel32/evex` and
   `x86:vmovaps/riprel32-xmm/evex`. The legacy pair keeps `0F 28`/`0F 29`, the
   VEX pair `c5 f8 28`/`c5 f8 29` and the EVEX pair `62 f1 7c 08 28`/
   `62 f1 7c 08 29`. The load/store split is `EC-27`'s existing rule; this ADR
   does not reopen it.
2. **The target slot is the one `0.2.0` already pins.** Each new row replaces
   the base and displacement slots with one `x86.rel`/`riprel32` slot:
   `from: operand_value`, `range {signed: true, bits: 32, align_bits: 0}`,
   `pc_reference_rule: pcrel_end`, `value_transform: identity`. The placement is
   `[24,32]` on the legacy pair, `[32,32]` on the VEX pair and `[48,32]` on the
   EVEX pair, because the displacement is the last 32 bits after a 2-, 3- or
   4-byte prefix plus opcode and `ModRM` (`EXP-0106` §3).
3. **The extension requirement follows the family.** The legacy pair is `[]`,
   the VEX pair `["avx"]`, and the EVEX pair `["avx","avx512f","avx512vl"]`,
   matching the existing `vmovaps` xmm rows under `fmp-def/0.2`.
4. **`0.69.0` is additive and immutable.** It repeats the 513 `0.68.0` forms
   byte-for-byte; the generator asserts the reproduction before it writes the
   new version. The digest is
   `sha256:94dee360550537cbefed798bcc4e7d790b9a879391e0b6a47ecf24a819a6b596`.
5. **The `ymm`/`zmm` windows stay absent.** Their `L`/`L'L` width selection is a
   different byte-affecting decision, so `x86:vmovaps/ymm-riprel32/vex` is
   `E-FORM-001` (`N01eo`) rather than an inferred widening of these rows.

## Consequences

- `X86-P75-sse-riprel32` is the 70-byte vector: six instructions plus 16 bytes
  of padding and four data bytes, all targeting `L1` at offset 66. The oracle
  input hash is
  `60868d0c7ab9fd9f59d35d2f90c528deceb1e798d574d27f165c47376e6890f9` and the
  output hash is
  `32cbce4a1d1a0b312c527fad2d0f7b03596bd2d0e3281c5fd0abd825363f55da` with 0
  relocation records.
- `N02cx` pins the operand count (`expected: 2`, `found: 1`), and `N04i`
  repeats `N04e`'s signed-32 end at the EVEX displacement placement.
- The corpus grows to 116 positives and 571 negatives; every one of the 519
  forms in `0.69.0` is named by a positive fixture (`check_definition.py`).
- `0.68.0` remains readable and unchanged, so a plan pinned to it cannot see
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **One `x86:movaps/xmm-mem/legacy` row with an optional base.** Rejected: the
  presence of a base is `ModRM.mod` and `ModRM.rm`, a byte-affecting encoding
  choice; one row would have to decide it from the operand list (`INV-02`), and
  RIP has no GPR number to spell.
- **Put the `riprel32` slot at `[24,32]` in all three families.** Rejected:
  `EXP-0106` §3 measures the field at bit 24/32/48 as the prefix grows; a single
  placement would overwrite `c5`/`62` on the longer rows.
- **Add `ymm`/`zmm` RIP-relative rows in the same slice.** Rejected: the width
  is a separate `L`/`L'L` decision, and S2's scope is the xmm window only.
- **Reuse `pcrel_begin`.** Rejected: x86 measures the displacement from the end
  of the instruction (`03_fixup_model.md` §4); `pcrel_begin` would move every
  target by the instruction length.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The six instructions are 7/7/8/8/10/10 bytes with `ModRM = 05` | `llvm-mc` object bytes, `EXP-0106` §2 | high |
| The displacement is the last 32 bits of each instruction | placement arithmetic and the `reloc_riprel_4byte` offsets | high |
| `pcrel_end` with `addend = 0` reproduces the six displacements | `X86-P75` fixture gate, `EXP-0106` §3 | high |
| `0.69.0` repeats `0.68.0` unchanged | generator assertion and digest | high |
| `N01eo` is `E-FORM-001`, `N02cx` `E-OPERAND-002`, `N04i` `E-RANGE-002` | fixture gate, `EXP-0106` §4 | high |

## Review triggers

- A `ymm`/`zmm` `%rip`-relative row is proposed; it needs its own width
  decision and cannot reuse the xmm placements.
- A `movups`/`movdqa` RIP-relative row is proposed; the opcode changes and the
  new row must be measured, not copied from `movaps`.
- The `0x67` address-size prefix meets a RIP-relative row; `ADR-0084` owns the
  prefix order and this ADR does not move the field.
