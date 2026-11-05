# ADR-0051: The EVEX `vmovaps` memory rows accept an index with no base

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P28` (the no-base indexed `disp32` shape of the EVEX `vmovaps`
  memory rows at `xmm`/`ymm`/`zmm` width)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0050` §Review triggers (the no-base shape it named);
  `ADR-0035` §Consequences (the shape it left absent in the GPR family)

## Context

`ADR-0050` closed the indexed `SIB` shape and named the next widening in its
second review trigger: `disp32(,%rax,4)` has no base at all. That is the third
and last `SIB` base choice. `SIB.base` has three meanings at `mod = 00`:

- `000`–`111` except `101`: the base is that register;
- `101` with `mod = 00`: **no base**, and the encoding demands a `disp32`
  immediately after the `SIB` byte;
- the same `101` with `mod = 01`/`10`: an ordinary base (`%rbp`, `%r13`).

The EVEX family already spends `mod = 00` for the no-displacement rows
(`ADR-0049`, `ADR-0050`). This slice reuses those rows' `mod = 00` and
`r/m = 100` escapes with `SIB.base = 101`, which frees the base slot and forces
the 32-bit displacement back.

Five facts come out of the measurements in `EXP-0053`:

1. **The `disp32` slot is mandatory, even at zero.** `(,%rax,1)` is eleven bytes:
   `62 f1 7c 08 28 04 05 00 00 00 00`. There is no no-displacement variant of
   this shape, so `0` is a `disp32` of content `0`, not a dropped field.
   `llvm-mc` accepts the bare `(,%rax)` and emits the same four zero bytes.
2. **`SIB.base = 101` is a template fact, not an operand.** The byte is `05` at
   `[48,8]` before the index (`[51,3]`) and scale (`[54,2]`) write their bits,
   so bits 48–50 are constant `101` and the row has no `base` role.
3. **The index and scale do not move.** `X̄` at `[14,1]` is still the index's
   fourth bit and `[54,2]` is still the scale content: `-4096(,%r12,8), %xmm3` is
   `62 b1 7c 08 28 1c e5 00 f0 ff ff` and `(,%r13,4), %ymm9` is
   `62 31 7c 28 28 0c ad 00 00 00 00`.
4. **`disp32` is signed and sits at `[56,32]`.** `-4096` is
   `00 f0 ff ff` in that string; `2147483647` is the last legal content
   (`… 4d ff ff ff 7f`). `llvm-mc` also accepts `0x80000000` and wraps it to
   `00 00 00 80`, but the field is signed, so a plan carrying `2147483648` is
   `E-RANGE-001` (`N03k`) — the same strictness `N04e` applied to a negative
   unsigned payload.
5. **A bare absolute address is a different shape.** `vmovaps 0x1234, %xmm0`
   is `SIB = 25`: `index = 100` (the "no index" encoding) *and*
   `base = 101`, with no index operand and the same `disp32`. That is one more
   `SIB` combination, not a special case of this row, and it is deferred.

The measurements are `llvm-mc` 23.1.2 on 2026-11-06; every measured byte
string round-trips through `llvm-mc -disassemble` to the same source line.

## Decision

**`0.24.0` appends six rows: for each of the three widths (`xmm`, `ymm`, `zmm`)
and each direction, one `disp32` row with no `base` slot. The `SIB` byte's base
field is the constant `101`, the displacement is mandatory, and index, scale
and displacement are one operand each.**

The appended rows:

| Width | Load `form_id` | Store `form_id` | Length |
|---|---|---|---|
| `xmm` | `x86:vmovaps/xmm-index-disp32/evex` | `x86:vmovaps/index-disp32-xmm/evex` | 11 bytes |
| `ymm` | `x86:vmovaps/ymm-index-disp32/evex` | `x86:vmovaps/index-disp32-ymm/evex` | 11 bytes |
| `zmm` | `x86:vmovaps/zmm-index-disp32/evex` | `x86:vmovaps/index-disp32-zmm/evex` | 11 bytes |

Five properties follow:

- **The template is `62 f1 7c <L'L> <28|29> 04 05 00 00 00 00`.** `ModRM` stays
  `04` (`mod = 00`, `r/m = 100`) and the `SIB` byte carries the constant base
  `101`; the vector slot, `X̄` and the scale sit exactly where `ADR-0050` put
  them, and the displacement occupies `[56,32]`.
- **There is no `base` role.** The operand sequence is `dest`/`src`, `index`,
  `imm` (scale), `disp`. A plan that supplies a base is `E-OPERAND-002`
  (`N02ad`); a plan that omits the displacement is `E-OPERAND-002` in the other
  direction, because the slot is not optional.
- **The index still excludes `4`.** `SIB.index = 100` with `X̄ = 1` is the "no
  index" encoding, so `%rsp` is `E-RANGE-004` (`N16ac`); `12` remains legal.
- **The scale is field content `0…3`.** Same slot as `ADR-0050`, same refusal
  when a plan spells it `x86.imm` (`E-OPERAND-001`, `N02ae`).
- **`disp32` is signed 32-bit content.** Plans carry bytes, never a multiplied
  value; `2147483648` is `E-RANGE-001` (`N03k`).

## Consequences

- `0.24.0` is a 231-form document.
- Its positive fixture `X86-P28-evex-mem-sib-nobase-index` has six instructions
  and 66 bytes, one per row, all eleven bytes.
- Negatives pin the version boundary against `0.23.0` in both directions
  (`N01az`, `N01ba`), a supplied `base` operand (`N02ad`), the scale carried as
  `x86.imm` (`N02ae`), past-the-end `disp32` content (`N03k`) and index `4`
  (`N16ac`).
- No schema, loader or materializer change: the row is the `ADR-0050` shape
  with three constant bits and one more slot, and both the `E-OPERAND-002`
  count check and the `E-RANGE-004` exclusion already exist.
- `02_encoding_choices.md` gains the six surface rows and revises `EC-02`,
  `EC-35`, `EC-37` and `EC-40` in place; no new `EC` row is added, because the
  index, scale and polarity decisions are the same rows' facts.
- Still absent on this axis: the absolute `SIB = 25` shape, `%rbp`/`%r13` as a
  base with `mod = 00` (no encoding), the other EVEX SSE memory mnemonics,
  EVEX masking, the `0x67` address-size prefix, and index/scale under the GPR
  and 8/16-bit `mov` opcodes.

## Alternatives rejected

- **Fold the absolute shape (`SIB = 25`) into the same row over an optional
  index.** An operand may not be optional (`INV-02`); "no index" is a different
  byte, and with `disp32` the two shapes differ in bit 51–53 only. It becomes
  its own row when it is taken.
- **Reuse the `-base-index-disp32` row with a fixed base.** That row accepts all
  sixteen base values and would let a plan name `%rax` where the encoding needs
  `101`; a base operand that must be `5` or `13` is not a base operand.
- **Drop the displacement when it is zero.** `llvm-mc` emits four zero bytes for
  `(,%rax,1)`; a shorter row would be a second encoding of the same address and
  would move `INV-04`'s length decision into the materializer.
- **Accept `2147483648` and wrap it.** The field is signed 32-bit; wrapping is a
  silent repair (`INV-07`), and `-2147483648` is the plan's way to say the same
  bytes.
- **Carry the multiplier instead of the scale content.** Two bits cannot hold
  `16`, and computing `1 << content` is an implicit encoding step (`INV-02`).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `62 f1 7c 08 28 04 05 00 00 00 00` and its round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0053` §1 | high |
| `SIB = 05` (base `101`) with index at `[51,3]` and scale at `[54,2]` | the byte strings; `EXP-0053` §2 | high |
| `-4096(,%r12,8), %xmm3` = `… 1c e5 …` and `(,%r13,4), %ymm9` = `… 0c ad …` | `llvm-mc -show-encoding`, `EXP-0053` §2 | high |
| `disp32` at `[56,32]`, `-4096` = `00 f0 ff ff` | `llvm-mc -show-encoding`, `EXP-0053` §3 | high |
| `0x80000000` is wrapped by `llvm-mc` to `00 00 00 80` | `llvm-mc` output, `EXP-0053` §4 | high |
| `0x1234` absolute is `SIB = 25` with no index operand | `llvm-mc -show-encoding`, `EXP-0053` §5 | high |
| Index `4` and scale `16` are refused by `llvm-mc` | `llvm-mc` error text, `EXP-0053` §4 | high |

## Review triggers

- An absolute address is requested (`vmovaps 0x1234, %xmm0`): `SIB = 25` is a
  shape with neither base nor index operand.
- `%rbp`/`%r13` are requested as a base with `mod = 00` and an index: no
  encoding exists; the `disp8*N = 0` row is the only option (eight bytes).
- A second EVEX SSE mnemonic is attempted (`vmovups`, `vmovdqa`): the same
  shape with a different opcode byte, a coverage slice with no new `EC` fact.
- EVEX masking is attempted: `{k1}` writes the `aaa` field, a bit this shape
  does not carry.
- The `0x67` address-size prefix is attempted: it re-reads the same `SIB`
  fields as 32-bit registers, a different address model.
