# ADR-0037: The SSE base reaches `r8`–`r15` through a per-family window

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P14` (the extended SSE base), the `EC-38` carrier and `EC-40`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0036` left the SSE base at three bits and named the widening as its own
decision: the legacy row has no `REX` byte, two-byte VEX has no `B` bit, and
EVEX's `B̄` is inverted. `llvm-mc` 23.1.2 measures the three families on
2026-11-05 (`EXP-0039`):

| Source | Bytes |
|---|---|
| `movaps 8(%r8), %xmm0` | `41 0f 28 40 08` |
| `movaps 128(%r15), %xmm1` | `41 0f 28 8f 80 00 00 00` |
| `movaps %xmm2, 8(%r9)` | `41 0f 29 51 08` |
| `movaps %xmm3, 128(%r10)` | `41 0f 29 9a 80 00 00 00` |
| `vmovaps 8(%r8), %xmm4` | `c4 c1 78 28 60 08` |
| `vmovaps 128(%r15), %xmm5` | `c4 c1 78 28 af 80 00 00 00` |
| `vmovaps %xmm6, 8(%r11)` | `c4 c1 78 29 73 08` |
| `vmovaps %xmm7, 128(%r13)` | `c4 c1 78 29 bd 80 00 00 00` |
| `{evex} vmovaps 16(%r8), %xmm0` | `62 d1 7c 08 28 40 01` |
| `{evex} vmovaps -16(%r14), %xmm1` | `62 d1 7c 08 28 4e ff` |
| `{evex} vmovaps 2032(%r15), %xmm2` | `62 d1 7c 08 28 57 7f` |
| `{evex} vmovaps 8(%r8), %xmm3` | `62 d1 7c 08 28 98 08 00 00 00` |
| `{evex} vmovaps %xmm4, 16(%r9)` | `62 d1 7c 08 29 61 01` |
| `{evex} vmovaps %xmm5, 8(%r15)` | `62 d1 7c 08 29 af 08 00 00 00` |

Two facts decide the shape:

1. **In two families the reach changes the instruction length.** Legacy grows a
   `REX` byte (`0f 28 40 08` for `8(%rax)` becomes `41 0f 28 40 08` for
   `8(%r8)`); two-byte VEX grows a third byte (`c5 f8 28 40 08` becomes
   `c4 c1 78 28 40 08`). A row that accepted both the low and the high base and
   inserted the longer prefix when it saw a high value would make the
   instruction length depend on an operand value, and with it every following
   fragment offset (`INV-04`). The check is not merely theoretical:
   `llvm-mc -disassemble` reads `40 0f 28 40 08` as `movaps 8(%rax), %xmm0` — the
   redundant `REX` is the same instruction — so a single legacy template cannot
   tell the windows apart by width alone; the form must.
2. **EVEX is already long enough.** Its four-byte prefix carries `B̄`, so
   `{evex} vmovaps 16(%rax), %xmm0` and `16(%r8)` are both seven bytes:
   `62 f1 7c 08 28 40 01` versus `62 d1 7c 08 28 40 01`. The bit is inverted
   (`B̄ = 0` means the extension is on), which is why a raw write would emit
   `P0 = f1` and silently encode `(%rax)`.

The `xmm` register is the same question one slot over. `xmm8` needs `REX.R` in
the legacy family, an inverted `R̄` in VEX and EVEX, and in the legacy family
it would double the number of windows again. It is not part of this slice.

## Decision

**`0.10.0` widens the SSE base to four bits in all three families. EVEX widens
in place; legacy and VEX gain eight `-base-ext` rows. A placement may declare
`"invert": true`, which writes its chunk complemented.**

1. **The four EVEX rows widen in place.** Their `form_id` and template do not
   change (`62 f1 7c 08 28 /r` / `29 /r`), so the low-base encoding is untouched.
   The `base` slot becomes `[13,1]` inverted + `[40,3]` and `excluded: [4, 12]`:
   `%rsp` and `%r12` still force a `SIB` byte that no SSE row carries.
2. **The eight `-base-ext` rows.** Legacy load/store × `disp8`/`disp32`
   (`40 0F 28 /r`, `40 0F 29 /r`) put the base at `[0,1]` (`REX.B`) and
   `[24,3]`; VEX load/store × `disp8`/`disp32` (`C4 C1 78 28 /r`, `29 /r`) put
   it at `[13,1]` inverted and `[32,3]`. Both windows exclude `0`–`7` and `12`,
   so the low and extension rows are disjoint and exactly one row can encode a
   given base.
3. **`placement.invert` is the polarity mechanism.** The definition declares
   that a chunk is written complemented; the materializer XORs the chunk with
   its width mask and makes no decision. The alternative — a special-case rule
   keyed to EVEX bit 13 — would put an encoding fact in code and make the
   definition decorative (`ADR-0004`, `EC-40`).
4. **The `xmm` slot stays three bits.** `xmm8` on any SSE memory row remains
   `E-OPERAND-004`. Widening it needs its own slice, because the legacy family
   would gain a `REX.R` window on top of the `REX.B` one.

The twelve affected templates:

| Family | Load `disp8` | Load `disp32` | Store `disp8` | Store `disp32` |
|---|---|---|---|---|
| legacy (ext) | `400f284000` | `400f288000000000` | `400f294000` | `400f298000000000` |
| VEX (ext) | `c4c178284000` | `c4c178288000000000` | `c4c178294000` | `c4c178298000000000` |
| EVEX (widened) | `62f17c08284000` | `62f17c08288000000000` | `62f17c08294000` | `62f17c08298000000000` |

## Consequences

- `0.10.0` is a 53-form document with digest
  `sha256:0c10ff1c373eea2fe6098e67da3047081b34a5779d9ec492c47069ac73613442`.
  Its positive fixture `X86-P14-sse-base-ext` is fourteen instructions and 104
  bytes: both directions, all three families, both displacement widths, the
  EVEX compressed contents `1`, `-1` and `127`, and the EVEX `disp32`
  promotion at `8(%r8)`.
- `N01af` pins the version boundary (`E-FORM-001` against `0.9.0`), `N14h` pins
  base `16` on a 4-bit field (`E-OPERAND-004`), `N16k` pins a low base on an
  extension row and `N16l` pins `%r12` there (`E-RANGE-004`). `N14e`–`N14g`
  stay at `0.9.0`: they are the counterexample that the shared 3-bit field
  could not reach `r8`.
- `EC-38` keeps `frozen` with a wider carrier: the reach is the `-base-ext`
  window plus the disjoint `excluded` sets. `EC-40` is new and frozen: the
  inversion is `placement.invert`. `EC-06` gains the SSE base as another
  `REX.B` user.
- `07_definition_format.md` §4.1 declares `invert`, and §8.1 gains the eight
  rows plus the four widened EVEX cells and the `0.10.0` digest row.
- Still absent: `xmm8`–`xmm15`, a `SIB` base under these opcodes (`%rsp`,
  `%r12`), `mod = 00` memory operands, EVEX masking, `ymm`/`zmm`, the `0x66`
  `movapd` form, and the 8/16-bit SSE width.
