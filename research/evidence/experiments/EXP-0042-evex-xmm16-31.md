# EXP-0042 — the EVEX vector register at `xmm16`–`xmm31`

- Date: 2026-11-05
- Question: which EVEX prefix bits carry the fifth vector-register bit, does the
  same bit mean something else in a memory form, and does reaching `xmm16`–
  `xmm31` change the instruction length?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.13.0.json`
  (`sha256:79eabc2d19a7cf3cac84c857afd6a11b4f15063c7526f17f8782ace0b5ea3431`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P17-sse-xmm16-31.oracle.json`
- Source: `research/evidence/experiments/EXP-0042/P17.asm`
- Decision: `ADR-0040`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. `llvm-mc` picks EVEX
whenever an operand is `xmm16` or above, so the family is forced by the operand
rather than by a directive:

| Source | Bytes | Length |
|---|---|---|
| `vmovaps %xmm16, %xmm0` | `62 b1 7c 08 28 c0` | 6 |
| `vmovaps %xmm0, %xmm16` | `62 e1 7c 08 28 c0` | 6 |
| `vmovaps %xmm24, %xmm0` | `62 91 7c 08 28 c0` | 6 |
| `vmovaps %xmm0, %xmm24` | `62 61 7c 08 28 c0` | 6 |
| `vmovaps %xmm31, %xmm30` | `62 01 7c 08 28 f7` | 6 |
| `vmovaps %xmm30, %xmm31` | `62 01 7c 08 28 fe` | 6 |
| `vmovaps %xmm31, %xmm16` | `62 81 7c 08 28 c7` | 6 |
| `vmovaps (%rax), %xmm16` | `62 e1 7c 08 28 00` | 6 |
| `vmovaps %xmm16, (%rax)` | `62 e1 7c 08 29 00` | 6 |
| `vmovaps (%r8), %xmm31` | `62 41 7c 08 28 38` | 6 |
| `vmovaps %xmm31, (%r8)` | `62 41 7c 08 29 38` | 6 |
| `vmovaps 2032(%rax), %xmm16` | `62 e1 7c 08 28 40 7f` | 7 |
| `vmovaps %xmm16, 2032(%rax)` | `62 e1 7c 08 29 40 7f` | 7 |
| `vmovaps -16(%rax), %xmm24` | `62 61 7c 08 28 40 ff` | 7 |
| `vmovaps %xmm24, -16(%rax)` | `62 61 7c 08 29 40 ff` | 7 |
| `vmovaps 8(%rax), %xmm31` | `62 61 7c 08 28 b8 08 00 00 00` | 10 |
| `vmovaps %xmm31, 8(%rax)` | `62 61 7c 08 29 b8 08 00 00 00` | 10 |
| `vmovaps 2056(%r8), %xmm16` | `62 c1 7c 08 28 80 08 08 00 00` | 10 |

## 2. `ModRM.reg` is five bits: `R̄` and `R̄'`

The destination of the register-direct row is `ModRM.reg`, and its value above
15 comes from two inverted prefix bits:

- `vmovaps %xmm16, %xmm0` has `P0 = b1`. Interpreting the two physical bits:
  `R̄' = 1` and `R̄ = 1`; both inverted give `0`, so `reg = 0`, the low
  destination. The `1` bits are the "not set" state.
- `vmovaps %xmm0, %xmm16` has `P0 = e1`: `R̄' = 0` and `R̄ = 1`, so
  `reg = 16`.
- `vmovaps %xmm24, %xmm0` has `P0 = 91`: the destination's `R̄`/`R̄'` bits are
  both physical `1` (`reg = 0`) and the source's `X̄`/`B̄` bits are both
  physical `0` (`rm = 24`).
- `xmm24` as a destination is `P0 = 61`: both physical bits `0`, `reg = 24`.
- `vmovaps %xmm30, %xmm31` keeps `P0 = 01` and adds `ModRM.reg = 7`
  (`62 01 7c 08 28 fe`), the same prefix that gives the source-31 row.

`R̄'` sits at `P0` bit 4 and `R̄` at `P0` bit 7; both are inverted, exactly like
the fourth bit in `0.11.0`. The physical bit order in the template is fixed:
bit 4 of the register is `R̄'`, bit 3 is `R̄`, bits 2–0 are `ModRM.reg`.

`llvm-mc -disassemble` on raw byte strings (one line of `0x`-prefixed bytes per
case):

| Bytes | `llvm-mc -disassemble` | What changed |
|---|---|---|
| `62 01 7c 08 28 f7` | `vmovaps %xmm31, %xmm30` | the measured row |
| `62 f1 7c 08 28 f7` | `vmovaps %xmm7, %xmm6` | both register bits written raw, not inverted |
| `62 11 7c 08 28 f7` | `vmovaps %xmm31, %xmm14` | `R̄'` dropped, so the destination loses bit 4 |
| `62 41 7c 08 28 f7` | `vmovaps %xmm15, %xmm30` | `X̄` left at its template value |

The first two show the polarity: writing `01` (the decoded value) instead of the
complemented pair turns `31/30` into `7/6`. The third shows why the placement is
needed: without `R̄'`, the destination keeps `ModRM.reg = 6` but loses bit 4 and
reads `14` instead of `30`.

## 3. `ModRM.rm` is five bits in register form: `B̄` and `X̄`

The source of the register-direct row is `ModRM.rm`. Its fourth and fifth bits
are `B̄` (`P0` bit 5) and `X̄` (`P0` bit 6), again inverted:

- `vmovaps %xmm31, %xmm30` is `62 01 … f7`: `P0 = 01` has `X̄` and `B̄`
  physical `0`, so `rm = 7` gains bits 4 and 3 and reads `31`, while
  `ModRM.reg = 6` reads `30`.
- Raising the physical `X̄` bit (`P0 = 41`) gives `62 41 7c 08 28 f7` =
  `%xmm15, %xmm30`: the source loses bit 4 and drops by 16.
- Raising the physical `B̄` bit instead (`P0 = 21`) gives `62 21 7c 08 28 c0` =
  `%xmm16, %xmm24`: the source loses bit 3.
- With both source bits physical `0` and both destination bits physical `0`
  (`P0 = 01`, `c0`), the row is `62 01 7c 08 28 c0` = `%xmm24, %xmm24`.

So the register-direct source reaches `31` when both of its prefix bits are
physical `0`, and the same `P0` bit is the one `EC-35`/`ADR-0035` assigns to a
`SIB` index in a memory form. The form's `mod` fixes which meaning applies; it
is never inferred from an operand (`INV-05`).

## 4. The memory shapes do not use `X̄`

Every measured memory row keeps `X̄ = 1` and `B̄` set only for `%r8` as the
base. There is no `SIB` row under these opcodes, so `X̄` has no index to extend:

| Shape | Bytes | `P0` | `xmm` in `ModRM.reg` |
|---|---|---|---|
| `vmovaps (%rax), %xmm16` | `62 e1 7c 08 28 00` | `e1` (`R̄' = 0`, `R̄ = 1`) | `16` |
| `vmovaps (%r8), %xmm31` | `62 41 7c 08 28 38` | `41` (`R̄' = 0`, `R̄ = 0`, `B̄ = 0`) | `31` |
| `vmovaps 2032(%rax), %xmm16` | `62 e1 7c 08 28 40 7f` | `e1` | `16` |
| `vmovaps -16(%rax), %xmm24` | `62 61 7c 08 28 40 ff` | `61` (`R̄' = 0`, `R̄ = 0`) | `24` |
| `vmovaps 8(%rax), %xmm31` | `62 61 7c 08 28 b8 08 00 00 00` | `61` | `31` |
| `vmovaps 2056(%r8), %xmm16` | `62 c1 7c 08 28 80 08 08 00 00` | `c1` (`B̄ = 0` for `%r8`, `X̄ = 1`) | `16` |

The `disp8*16` content is a multiple of 16: `2032 = 127 × 16`, `-16 = -1 × 16`.
`8` and `2056` are not multiples of 16, so `llvm-mc` promotes them to `disp32`
(the two ten-byte rows). This is the same `EC-38`/`EC-39` behavior measured in
`EXP-0038`, not a new choice.

## 5. Legacy and VEX cannot reach the value

`llvm-mc` rejects `xmm32` outright, and `movaps` (the legacy mnemonic) rejects
`xmm16`; only `vmovaps` accepts it, and it does so with EVEX:

| Source | Result |
|---|---|
| `vmovaps %xmm32, %xmm0` | `error: invalid register name` |
| `movaps %xmm16, %xmm0` | `error: invalid operand for instruction` |
| `vmovaps %xmm16, %xmm0` | `62 b1 7c 08 28 c0` (EVEX) |

The legacy prefix has one `REX` byte with `R`/`B` only, and a two-byte VEX has
`R` only; neither has a second extension bit. A five-bit field therefore exists
only on the EVEX rows. `xmm16` on a VEX row is `E-OPERAND-004` with
`field_bits = 4` (`N14o`), and on the older EVEX rows it is the same code with
`field_bits = 4` (`N14m`).

## 6. The oracle

`P17.asm` is sixteen `vmovaps` mnemonics and no hand-assembled bytes. The source
is 399 bytes, SHA-256
`14ff36adf656db650777089970fdba33266c322f0822855af93da00614ec9265`. `.text` is
112 bytes, SHA-256
`031dd545745db514785d57346f6faefae9aa2dd39ae5c2160f40c461687fdfc2`, and the plan
emits no fixup record.

The fixture fills every widened slot in both directions: `16`, `24`, `30` and
`31` as `ModRM.reg`; `30`, `31` and `16` as `ModRM.rm`; the memory shapes at
`%xmm16`, `%xmm24` and `%xmm31`; both `disp8*16` contents; and the two `disp32`
promotions. Every instruction is the same length as its low-register twin
(6/6/7/10), so the fifth bit costs no byte.

## 7. The rejections

- `N14m` passes `xmm16` to `x86:vmovaps/xmm-xmm/evex` in `0.12.0`:
  `E-OPERAND-004`, `field_bits = 4`. The version boundary.
- `N14n` passes `xmm32` to the same row in `0.13.0`: `E-OPERAND-004`,
  `field_bits = 5`. The field end.
- `N14o` passes `xmm16` to `x86:vmovaps/xmm-xmm/vex` in `0.13.0`:
  `E-OPERAND-004`, `field_bits = 4`. The family boundary: VEX has no second
  extension bit even on the newest table.

## 8. What this does not claim

- `ymm`/`zmm`, EVEX masking and broadcast, and the `EVEX.vvvv` carrier are still
  absent.
- A `SIB` base or index under these opcodes, an SSE RIP-relative row, `mod = 00`
  for the GPR rows, the `0x67` prefix, 8/16-bit memory widths, and `movapd`'s
  `0x66` form remain absent.
- A memory row with a `SIB` index would have to decide `X̄`'s meaning from the
  form, and that form does not exist yet.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
