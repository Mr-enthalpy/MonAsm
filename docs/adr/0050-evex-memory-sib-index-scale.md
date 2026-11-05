# ADR-0050: The EVEX `vmovaps` memory rows take a `SIB` index and scale

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P27` (the `SIB` index and scale of the EVEX `vmovaps` memory
  rows at `xmm`/`ymm`/`zmm` width)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0049` §Review triggers (the index/scale shape it named);
  `ADR-0035` §Consequences (the `mod = 00` shape it left absent)

## Context

`ADR-0049` closed the fixed-base `mod = 00` shape and named the next widening
in its first review trigger: `(%rsp,%rax,1)` is `62 f1 7c 08 28 04 04`, a
different `SIB` byte (`index = 000`). That byte is the indexed shape
`ADR-0035` gave the legacy `mov` families in `0.8.0`, and that decision left
`mod = 00` absent. The EVEX family now has all three displacement shapes at a
fixed base, so this slice repeats the `ADR-0035` shape with the base as an
operand instead of a template byte, and adds the no-displacement form the
legacy slice deferred.

Five facts come out of the measurements in `EXP-0052`:

1. **`r/m = 100` is the shape, not an operand value.** `ModRM` is `04`/`44`/
   `84` for the three displacement widths, and the `SIB` byte follows it. Base
   `4` and `12` are ordinary bases here (`%rsp`, `%r12`), which is the
   opposite of the non-`SIB` rows, where those two values had to be excluded.
2. **`X̄` is the index's fourth bit.** The EVEX `P0` byte already carries a
   complement bit at template bit 14, exactly where `REX.X` sits in the legacy
   family; it is now the index's high bit rather than an unused bit or a
   register-direct `ModRM.rm` bit. `(%rsp,%r12,1)` is
   `62 b1 7c 08 28 04 24` (`f1` → `b1`) while `(%rsp,%rax,1)` keeps `f1`, and
   `(%r8,%r12,1)` is `62 11 7c 28 28 04 20` (`R̄`, `X̄` and `B̄` all cleared).
3. **The index field excludes `4`, and only `4`.** `SIB.index = 100` with no
   extension bit means "no index"; `%r12` reaches the same three-bit field
   through `X̄ = 0`, so `12` is legal. `llvm-mc` refuses `(%rax,%rsp,1)` with
   `invalid base+index expression`.
4. **The scale is two bits of field content.** `00`/`01`/`10`/`11` are
   ×1/×2/×4/×8 at `SIB[7:6]`, the same field `ADR-0035` made content. EVEX
   changes neither the field nor the multiplier.
5. **`mod = 00` with `SIB.base = 101` is "no base, `disp32`".** `%rbp`/`%r13`
   (low three bits `101`) therefore cannot be the base of a no-displacement
   indexed row: `(%rbp,%rax,1)` canonicalizes to the `disp8*N` row with content
   `0`, `62 f1 7c 08 28 44 05 00` (eight bytes). The same canonicalization
   applies to a zero displacement over a legal base: `0(%rax,%rcx,1)` is
   `(%rax,%rcx,1)`, so the no-displacement row is the only encoding of a zero
   offset.

The measurements are `llvm-mc` 23.1.2 on 2026-11-06; every measured byte
string round-trips through `llvm-mc -disassemble` to the same source line.

## Decision

**`0.23.0` appends eighteen `SIB` rows: for each of the three widths (`xmm`,
`ymm`, `zmm`), each direction and each displacement shape (none, `disp8*N`,
`disp32`). Base, index, scale and displacement are one operand each; the
`ModRM` escape, the `SIB` byte, the compressed unit and the displacement
absence are template facts.**

The appended rows, one per `(width, direction, disp shape)`:

| Width | Load `form_id` | Store `form_id` | `ModRM` | Displacement |
|---|---|---|---|---|
| `xmm` | `x86:vmovaps/xmm-base-index/evex` | `x86:vmovaps/base-index-xmm/evex` | `04` | none (7 bytes) |
| `xmm` | `x86:vmovaps/xmm-base-index-disp8x16/evex` | `x86:vmovaps/base-index-disp8x16-xmm/evex` | `44` | `disp8x16` (8 bytes) |
| `xmm` | `x86:vmovaps/xmm-base-index-disp32/evex` | `x86:vmovaps/base-index-disp32-xmm/evex` | `84` | `disp32` (11 bytes) |
| `ymm` | the same three names with `ymm` in place of `xmm` | the same three names with `ymm` in place of `xmm` | the same three | `disp8x32` at the middle width |
| `zmm` | the same three names with `zmm` in place of `xmm` | the same three names with `zmm` in place of `xmm` | the same three | `disp8x64` at the middle width |

Six properties follow:

- **The layout does not move.** The prefix is four bytes, so `ModRM` stays at
  bit 40 and the vector slot stays at `[43,3]` with its two inverted extension
  bits at `[12,1]`/`[15,1]`, exactly as on the `-base` and fixed-base rows.
- **The `SIB` byte is operand-owned in full.** Base is `[48,3]` plus the
  inverted `B̄` at `[13,1]`; index is `[51,3]` plus the inverted `X̄` at
  `[14,1]`; the scale is `[54,2]`. Every bit of the byte is written by an
  operand, so the template holds `00` there.
- **The base window has one gap.** All sixteen values are legal on the
  `disp8*N` and `disp32` rows. On the no-displacement rows `5` and `13` are
  `E-RANGE-004`, because `SIB.base = 101` at `mod = 00` means "no base" and
  demands a `disp32`; those bases keep the `disp8*N = 0` row.
- **The index excludes `4`.** It is four bits (0–15), one placement into the
  `SIB` field and one into `X̄`; `4` is `E-RANGE-004`, and `12` is legal.
- **The scale is field content, `0…3`.** `role: imm`, kind `x86.scale`,
  `target_type: scale2`, `from: operand_value`, `range {signed: false, bits: 2,
  align_bits: 0}`. A plan that spells it `x86.imm` is `E-OPERAND-001`; the
  materializer never computes `1 << content` (`INV-02`).
- **The operand order is `dest`/`src`, `base`, `index`, `imm` (scale), `disp`**,
  with `disp` last, as on every other x86 memory row (`ADR-0035` decision 5).
  A plan that reorders the roles is `E-OPERAND-002`.

## Consequences

- `0.23.0` is a 225-form document with digest
  `sha256:507e55c84cc80cf8bd9be10a6c6e4f7cff4999084fb41b3138df60b68a283962`.
- Its positive fixture `X86-P27-evex-mem-sib-index` has eighteen instructions
  and 156 bytes, one per row; each width contributes a 7-byte, an 8-byte and an
  11-byte instruction in load/store pairs.
- Negatives pin the version boundary against `0.22.0` (both directions), the
  scale carried as `x86.imm`, an extra `disp` operand on the no-displacement
  row, index `4`, and base `5` on the no-displacement row.
- No schema, loader or materializer change: the rows use the operand-owned
  `SIB` shape `0.8.0` introduced, and the EVEX prefix already carries the
  inverted `B̄`/`X̄` bits `0.13.0`/`0.21.0` placed.
- `02_encoding_choices.md` gains the eighteen surface rows and revises `EC-02`,
  `EC-35`, `EC-37` and `EC-40` in place; no new `EC` row is added, because the
  index/scale choice is `EC-37`'s and the polarity is `EC-40`'s.
- Still absent on this axis: `%rbp`/`%r13` at `mod = 00` (no encoding), the
  no-base `disp32(,%index,scale)` shape, the other EVEX SSE memory mnemonics,
  EVEX masking, and the `0x67` address-size prefix.

## Alternatives rejected

- **One row over a `has_index` modifier.** A modifier may not write bits or
  change length (`ADR-0015`, `INV-04`); the `SIB` byte's presence is a
  structural fact, and index `4` is a different byte from "no index".
- **Fixed-index rows for `%rsp`/`%r12` only.** In the `SIB` shape all sixteen
  base values and fifteen index values are ordinary operands, so fixing them
  would multiply rows without adding a fact (`ADR-0035` decision 2).
- **Carry the multiplier `1/2/4/8` instead of the field content.** The
  materializer would have to compute `1 << content` (`INV-02`), and a
  multiplier `16` cannot be represented in two bits (`E-RANGE-001`).
- **Give `%rbp`/`%r13` a no-displacement indexed row.** `SIB.base = 101` at
  `mod = 00` is the no-base form; a row that accepted `5` or `13` there would
  emit a `disp32` slot it does not have.
- **Make the no-displacement row carry a zero `disp8*N`.** `llvm-mc` emits
  seven bytes with no displacement for `0(%rax,%rcx,1)`; a displacement row
  would produce a different, longer byte string for the same source.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `62 f1 7c 08 28 04 04`, `62 b1 7c 08 28 04 24`, `62 11 7c 28 28 04 20` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0052` §1 | high |
| `ModRM` `04`/`44`/`84`; `SIB` at bits 48–55; displacement at 56 | the byte strings; `EXP-0052` §2 | high |
| Scale `00`/`01`/`10`/`11` = ×1/×2/×4/×8 at `[54,2]` | `llvm-mc -show-encoding`, `EXP-0052` §1 and §3 | high |
| `X̄` (template bit 14, inverted) is the index's fourth bit | `%rsp`/`%r8`/`%r12` index probes, `EXP-0052` §2 | high |
| Index `4` is rejected by `llvm-mc` (`invalid base+index expression`) | `llvm-mc` error text, `EXP-0052` §4 | high |
| `(%rbp,%rax,1)` is `62 f1 7c 08 28 44 05 00`, the `disp8*N = 0` row | `llvm-mc -show-encoding`, `EXP-0052` §4 | high |
| `0(%rax,%rcx,1)` canonicalizes to `(%rax,%rcx,1)`, seven bytes | `llvm-mc -show-encoding`, `EXP-0052` §3 | high |

## Review triggers

- `%rbp`/`%r13` are requested at `mod = 00` with an index: no encoding exists,
  so the request has to settle for the `disp8*N = 0` form (eight bytes).
- A no-base indexed address is requested (`disp32(,%rax,4)`): `SIB.base = 101`
  at `mod = 00` is exactly that shape, and it needs a `disp32` the new rows do
  not carry.
- A second EVEX SSE mnemonic is attempted (`vmovups`, `vmovdqa`): the same
  shape with a different opcode byte, a coverage slice with no new `EC` fact.
- EVEX masking is attempted: `{k1}` writes the `aaa` field, a bit this shape
  does not carry.
- The `0x67` address-size prefix is attempted: it re-reads the same `SIB`
  fields as 32-bit registers, a different address model.
