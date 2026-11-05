# ADR-0038: The SSE register reaches `xmm8`–`xmm15` through per-family windows

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P15` (the extended SSE register), `EC-06` and `EC-09`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0037` widened the SSE base and left the `xmm` slot at three bits. The
register is the same question one slot over, and the answer is different in
every family. `llvm-mc` 23.1.2 measures the register-direct shape on 2026-11-05
(`EXP-0040`):

| Source | Bytes |
|---|---|
| `movaps %xmm1, %xmm0` | `0f 28 c1` |
| `movaps %xmm1, %xmm8` | `44 0f 28 c1` |
| `movaps %xmm9, %xmm0` | `41 0f 28 c1` |
| `movaps %xmm9, %xmm8` | `45 0f 28 c1` |
| `vmovaps %xmm1, %xmm0` | `c5 f8 28 c1` |
| `vmovaps %xmm1, %xmm8` | `c5 78 28 c1` |
| `vmovaps %xmm9, %xmm0` | `c5 78 29 c8` |
| `vmovaps %xmm9, %xmm8` | `c4 41 78 28 c1` |
| `{evex} vmovaps %xmm1, %xmm0` | `62 f1 7c 08 28 c1` |
| `{evex} vmovaps %xmm1, %xmm8` | `62 71 7c 08 28 c1` |
| `{evex} vmovaps %xmm9, %xmm0` | `62 d1 7c 08 28 c1` |
| `{evex} vmovaps %xmm9, %xmm8` | `62 51 7c 08 28 c1` |

The memory shape repeats the same fourth bits (`EXP-0040`):

| Source | Bytes |
|---|---|
| `movaps 8(%rax), %xmm8` | `44 0f 28 40 08` |
| `movaps 128(%r8), %xmm9` | `45 0f 28 88 80 00 00 00` |
| `movaps %xmm10, 8(%rax)` | `44 0f 29 50 08` |
| `movaps %xmm11, 128(%r8)` | `45 0f 29 98 80 00 00 00` |
| `vmovaps 8(%rax), %xmm8` | `c5 78 28 40 08` |
| `vmovaps 128(%r15), %xmm9` | `c4 41 78 28 8f 80 00 00 00` |
| `vmovaps %xmm10, 8(%rax)` | `c5 78 29 50 08` |
| `vmovaps %xmm12, 8(%r8)` | `c4 41 78 29 60 08` |
| `{evex} vmovaps 16(%rax), %xmm8` | `62 71 7c 08 28 40 01` |
| `{evex} vmovaps 16(%r8), %xmm8` | `62 51 7c 08 28 40 01` |
| `{evex} vmovaps %xmm12, 16(%r8)` | `62 51 7c 08 29 60 01` |

Four facts decide the shape:

1. **Legacy needs a `REX` byte, and it is the same byte for `R` and `B`.** The
   low row is three bytes (`0f 28 c1`). A high destination sets `REX.R`
   (`44 0f 28 c1`), a high source sets `REX.B` (`41 0f 28 c1`), and both set
   both (`45 0f 28 c1`). All extension windows are four bytes, so lengthening
   the row is not a value-dependent layout decision here: the window decides.
2. **VEX has two spare bits, but the two-byte form has only one of them on the
   register path.** Three-byte `C4` carries the inverted `R̄` at bit 15 and
   `B̄` at bit 13. Two-byte `C5` carries only `R̄`; its `ModRM.rm` stays three
   bits. `llvm-mc` puts a high destination in `ModRM.reg` under `C5 78 28`
   (`c5 78 28 c1`), but a high source under `C5 78 29` (`c5 78 29 c8`), where
   the store opcode moves the source into `ModRM.reg` and leaves the
   destination in the 3-bit `rm`. Both register-direct operands high then need
   the three-byte `C4 41 78 28` (`c4 41 78 28 c1`).
3. **That VEX split has a second legal encoding, which is the `INV-02`
   counterexample.** `vmovaps %xmm8, %xmm0` is `c5 78 29 c0` (four bytes), and
   `c4 c1 78 28 c0` is also a legal five-byte encoding of the same
   instruction; `llvm-mc -disassemble` reads both back identically. An
   implementation that preferred the `C4` form would emit a different length
   for the same plan. The table must pin one, and this ADR pins the one
   `llvm-mc` produces.
4. **EVEX is already long enough, and the two register operands sit in
   different fields.** `R̄` is bit 15 (`ModRM.reg`), `B̄` is bit 13
   (`ModRM.rm`): `vmovaps %xmm1, %xmm8` flips bit 15 (`f1` → `71`),
   `vmovaps %xmm9, %xmm0` flips bit 13 (`f1` → `d1`), and both high flips both
   (`f1` → `51`). Every register-direct and memory row keeps its length.

## Decision

**`0.11.0` widens `x86.xmm` to four bits. EVEX and the VEX/EVEX memory rows
widen in place; legacy register-direct gains three 4-byte windows, legacy
memory gains four 5/8-byte rows, and VEX register-direct gains two windows.
Every reach is a window with a disjoint `excluded` set, never a value test in
the materializer.**

1. **`x86.xmm` is one 4-bit kind, and the fourth bit is a placement.** It is
   `REX.R`/`REX.B` in legacy and the inverted `R̄`/`B̄` in VEX and EVEX. The
   register set does not change with the family, so the kind does not either.
2. **The three legacy register-direct windows.** All use `40 0F 28 /r`:
   `xmm-ext-xmm` puts `REX.R` at `[2,1]` and excludes dest `0`–`7`;
   `xmm-xmm-ext` puts `REX.B` at `[0,1]` and excludes src `0`–`7`;
   `xmm-ext-xmm-ext` does both and excludes both. Per-slot `excluded` lists
   cannot express the cross product "(dest low and src low)", so the all-low
   corner stays with the existing 3-byte `0f28c0` row and the extension windows
   are three, not one.
3. **The four legacy memory rows.** `40 0F 28 /r` (load) and `40 0F 29 /r`
   (store), each `disp8` and `disp32`, with the `xmm` at `[2,1]` + `[27,3]`
   and `excluded: [0…7]`. The `REX` byte that carries `REX.R` carries `REX.B`
   for free, so the base is a single 4-bit `[0,1]` + `[24,3]` slot with
   `excluded: [4, 12]`: one row covers base `0`–`15` minus `%rsp` and `%r12`,
   and the low memory rows keep their 3-bit `xmm`. `%r12` still forces a
   `SIB` byte and stays `E-RANGE-004`.
4. **The two VEX register-direct windows.** `xmm-xmm-src-ext` is
   `C5 78 29 /r` with dest `[24,3]` (`0`–`7`) and src `[15,1]` inverted +
   `[27,3]` (`8`–`15`); `xmm-xmm-both-ext` is `C4 41 78 28 /r` with dest
   `[15,1]` inverted + `[35,3]` and src `[13,1]` inverted + `[32,3]`, both
   excluded to `8`–`15`. The existing two-byte row keeps dest 4-bit and source
   3-bit, so the three windows are disjoint by which operand is high.
5. **The EVEX family and the VEX/EVEX memory rows widen in place.** Their
   `form_id` and template do not change. EVEX register-direct dest gains
   `[15,1]` inverted and src `[13,1]` inverted; every EVEX memory `xmm` gains
   `[15,1]` inverted; every VEX memory `xmm` gains `[15,1]` inverted. A low
   register writes `0` into the raw `REX` bit or `1` into the inverted one, so
   the `0.10.0` bytes do not change.
6. **The window, not the value, still selects the row.** A plan names one
   `form_id`; the materializer looks the operand up in that row's `excluded`
   list and never widens, shortens or re-forms the instruction (`INV-02`,
   `INV-04`). A high `xmm` on a 3-bit row is `E-OPERAND-004` (`N14j`, `N14k`),
   a low `xmm` on an extension row is `E-RANGE-004` (`N16m`, `N16n`), and
   `xmm16` is `E-OPERAND-004` (`N14i`).

The nine new templates:

| Window | Template | Bytes |
|---|---|---|
| legacy dest-high | `400f28c0` | 4 |
| legacy src-high | `400f28c0` | 4 |
| legacy both-high | `400f28c0` | 4 |
| VEX src-high, dest-low (`29 /r`) | `c5f829c0` | 4 |
| VEX both-high (`C4`, `28 /r`) | `c4e17828c0` | 5 |
| legacy dest-high base `disp8` | `400f284000` | 5 |
| legacy dest-high base `disp32` | `400f288000000000` | 8 |
| legacy src-high base `disp8` | `400f294000` | 5 |
| legacy src-high base `disp32` | `400f298000000000` | 8 |

The fourteen changed-in-place rows are the VEX register-direct dest, the EVEX
register-direct dest and src, the four low VEX memory `xmm` slots, the four
EVEX memory `xmm` slots and the four VEX `-base-ext` memory `xmm` slots
(fifteen slot changes across fourteen forms).

## Consequences

- `0.11.0` is a 62-form document with digest
  `sha256:d9669be62267ecd90d69dc9f936bcb947948b8c1ec7c7ba0670eb63f32de0570`.
  Its positive fixture `X86-P15-sse-xmm-ext` is 23 instructions and 128 bytes:
  every register window in all three families, the `REX`, `R̄` and `B̄`
  placements, both memory directions, both displacement widths, and the EVEX
  compressed `disp8*16` contents.
- `N01ag` pins the version boundary (`E-FORM-001` against `0.10.0`), `N14i`
  pins `xmm16` on the 4-bit field, `N14j` pins `xmm8` on the 3-bit legacy
  register-direct row, `N14k` pins a high source on the two-byte VEX row,
  `N16m` pins a low destination on a legacy extension row and `N16n` pins a
  low source on the VEX source-extension row.
- `EC-06` gains `REX.R` and `REX.B` as `xmm` extension bits and stops saying
  the SSE `xmm` slot stays three bits. `EC-09` gains the register reach and
  the opcode-29 counterexample. No new `EC` row is needed: the carrier is the
  same `form variant` the family already had.
- `07_definition_format.md` §8.1 gains the nine rows, the fourteen changed
  slot cells and the `0.11.0` digest row.
- Still absent: `xmm16`–`xmm31` (EVEX `R'`/`B'`/`X'`), a `SIB` base under
  these opcodes (`%rsp`, `%r12`), `mod = 00` memory operands, EVEX masking,
  `ymm`/`zmm`, the `0x66` `movapd` form, and the 8/16-bit SSE width.
