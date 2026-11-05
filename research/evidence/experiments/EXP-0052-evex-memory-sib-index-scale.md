# EXP-0052 -- the EVEX `vmovaps` memory rows with a `SIB` index and scale

- Date: 2026-11-06
- Question: how do the EVEX `vmovaps` memory rows encode an index and a scale
  at `xmm`/`ymm`/`zmm` width, where do the index and scale bits sit, which
  bases and index values cannot use the shape, and how do the three
  displacement widths interact with them?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.23.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P27-evex-mem-sib-index.oracle.json`
- Source: `research/evidence/experiments/EXP-0052/P27.asm`
- Fixture source: `research/evidence/experiments/EXP-0052/fixture.asm`
- Decision: `ADR-0050`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps (%rsp,%rax,1), %xmm0` | `62 f1 7c 08 28 04 04` | 7 |
| `{evex} vmovaps 16(%rsp,%rax,1), %xmm2` | `62 f1 7c 08 28 54 04 01` | 8 |
| `{evex} vmovaps 8(%rax,%rcx,1), %xmm5` | `62 f1 7c 08 28 ac 08 08 00 00 00` | 11 |
| `{evex} vmovaps (%rsp,%rax,8), %xmm1` | `62 f1 7c 08 28 0c c4` | 7 |
| `{evex} vmovaps -16(%rsp,%r12,2), %xmm3` | `62 b1 7c 08 28 5c 64 ff` | 8 |
| `{evex} vmovaps 32(%rsp,%rsi,4), %xmm4` | `62 f1 7c 08 28 64 b4 02` | 8 |
| `{evex} vmovaps %xmm0, (%rsp,%rax,1)` | `62 f1 7c 08 29 04 04` | 7 |
| `{evex} vmovaps %ymm1, 32(%rsp,%rax,1)` | `62 f1 7c 28 29 4c 04 01` | 8 |
| `{evex} vmovaps 64(%r12,%r12,2), %ymm9` | `62 11 7c 28 28 4c 64 02` | 8 |
| `{evex} vmovaps 96(%r8,%r9,4), %zmm17` | `62 81 7c 48 28 8c 88 60 00 00 00` | 11 |
| `{evex} vmovaps -64(%rsp,%rax,8), %zmm31` | `62 61 7c 48 28 7c c4 ff` | 8 |
| `{evex} vmovaps 128(%rsp,%r13,1), %zmm0` | `62 b1 7c 48 28 44 2c 02` | 8 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty-five unique byte
strings as the same source line.

The rows are the fixed-base `SIB` rows of `EXP-0051` with the `SIB` byte
opened up: `r/m = 100` announces it, `mod` is `00`/`01`/`10`, and the byte is
`scale | index | base`:

| Source | `ModRM` | `SIB` | `SIB` fields |
|---|---|---|---|
| `(%rsp,%rax,1)` | `04` | `04` | scale `00`, index `000`, base `100` |
| `16(%rsp,%rax,1)` | `54` | `04` | same, `mod = 01`, content `1` |
| `8(%rax,%rcx,1)` | `ac` | `08` | scale `00`, index `001`, base `000` |

The `SIB` byte replaces the fixed `24` of `(%rsp)`/`(%r12)`: the earlier rows
say `index = 100` ("no index"), this shape names an index. The length decision
is unchanged — one `SIB` byte, plus the displacement the `mod` field asks for.

## 2. Where the fields sit

| Field | Template bits | Placement |
|---|---|---|
| vector register | `[43,3]` plus `[12,1]`/`[15,1]` inverted | unchanged from `0.21.0`/`0.22.0` |
| `ModRM` | `[40,8]` | template: `04`, `44` or `84` |
| `SIB.base` | `[48,3]` plus `[13,1]` inverted `B̄` | four-bit operand, no exclusion on the `disp` rows |
| `SIB.index` | `[51,3]` plus `[14,1]` inverted `X̄` | four-bit operand, `4` excluded |
| `SIB.scale` | `[54,2]` | two bits of field content (`0…3`) |
| `disp8*N` | `[56,8]` | content `disp / N` |
| `disp32` | `[56,32]` | byte offset |

`X̄` is the index's fourth bit, and it is the same bit `EC-40` gives the
register-direct `ModRM.rm`:

| Source | Bytes | What changed |
|---|---|---|
| `(%rsp,%rax,1), %xmm0` | `62 f1 7c 08 28 04 04` | index `0`: `X̄ = 1` |
| `(%rsp,%r12,1), %xmm0` | `62 b1 7c 08 28 04 24` | index `12`: `X̄ = 0` (`f1` → `b1`) |
| `(%r8,%r12,1), %ymm8` | `62 11 7c 28 28 04 20` | base `8`, index `12`: `B̄ = X̄ = 0` |
| `(%r12,%r15,8), %xmm31` | `62 01 7c 08 28 3c fc` | base `12`, index `15`, scale ×8, `R̄' = 0` |
| `(%rbp,%r12,4), %xmm7` | `62 b1 7c 08 28 7c a5 00` | base `5` (low bits `101`), index `12`, ×4 |

The index field is three bits, so `12` is `X̄ = 0` with `index = 100`; `%rsp`
would be `index = 100` with `X̄ = 1`, which is the "no index" encoding, and
`llvm-mc` refuses `(%rax,%rsp,1)` with `invalid base+index expression`. The
base field is three bits too, but here `100` is just `%rsp`/`%r12`, because
`r/m = 100` already answered the `SIB` question.

## 3. The scale, and zero has exactly one encoding

The top two `SIB` bits are the scale, over one base/index pair:

| Source | Bytes | `SIB` | Content |
|---|---|---|---|
| `(%rsp,%rax,1), %xmm0` | `62 f1 7c 08 28 04 04` | `04` | `0` |
| `(%rsp,%rax,2), %xmm0` | `62 f1 7c 08 28 04 44` | `44` | `1` |
| `(%rsp,%rax,4), %xmm0` | `62 f1 7c 08 28 04 84` | `84` | `2` |
| `(%rsp,%rax,8), %xmm0` | `62 f1 7c 08 28 04 c4` | `c4` | `3` |

Only the top bits move, so the scale is content, not a form. The multiplier is
`1 << content`, and `16` is not a field value (the assembler says
`scale factor in address must be 1, 2, 4 or 8`).

A zero displacement over a legal base drops the displacement slot:

| Source | Bytes |
|---|---|
| `{evex} vmovaps (%rsp,%rax,1), %xmm0` | `62 f1 7c 08 28 04 04` |
| `{evex} vmovaps 0(%rsp,%rax,1), %xmm0` | `62 f1 7c 08 28 04 04` |
| `{evex} vmovaps (%rax,%rcx,1), %xmm0` | `62 f1 7c 08 28 04 08` |
| `{evex} vmovaps 0(%rax,%rcx,1), %xmm0` | `62 f1 7c 08 28 04 08` |

`llvm-mc` prints the no-displacement source line for both spellings and emits
the same seven bytes, so the no-displacement row is the only encoding of a
zero offset. The `disp8*N` row would add one more byte for the same address.

## 4. The bases and index values that cannot use the shape

`mod = 00` with `SIB.base = 101` means "no base, `disp32`", so `%rbp` and
`%r13` (low three bits `101`) cannot be the base of the no-displacement row:

| Source | Bytes | What it is |
|---|---|---|
| `{evex} vmovaps (%rbp,%rax,1), %xmm7` | `62 f1 7c 08 28 7c 05 00` | `disp8*N` row, content `0` |
| `{evex} vmovaps (%r13,%rax,1), %xmm7` | `62 d1 7c 08 28 7c 05 00` | same, `B̄ = 0` |
| `{evex} vmovaps (%rbp,%r12,4), %xmm7` | `62 b1 7c 08 28 7c a5 00` | same, index `12` and ×4 |

All three are eight bytes: `mod = 01`, `SIB = 05`/`a5`, and a zero
displacement byte. They are the `disp8*N` row, not a no-displacement row.

The other end of the range is the compressed unit. It is still `16`/`32`/`64`
per width, and a displacement that is not a multiple of `N` promotes to
`disp32` rather than truncating:

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps 2032(%rsp,%rax,1), %xmm6` | `62 f1 7c 08 28 74 04 7f` | 8 (content `127`) |
| `{evex} vmovaps 2048(%rsp,%rax,1), %xmm6` | `62 f1 7c 08 28 b4 04 00 08 00 00` | 11 (`disp32`) |
| `{evex} vmovaps 8(%rax,%rcx,1), %xmm5` | `62 f1 7c 08 28 ac 08 08 00 00 00` | 11 (`disp32`) |
| `{evex} vmovaps -8192(%rax,%rcx,1), %zmm0` | `62 f1 7c 48 28 44 08 80` | 8 (content `-128`) |
| `{evex} vmovaps 8192(%rax,%rcx,1), %zmm0` | `62 f1 7c 48 28 84 08 00 20 00 00` | 11 (`disp32`) |

The EVEX vector slot is five bits, so the whole register file is reachable at
no length cost: `xmm31`, `zmm17` and `ymm9` appear in the table above, and a
high register only clears `R̄`/`R̄'` in `P0`.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01ax` | names `x86:vmovaps/xmm-base-index/evex` against `0.22.0` | `E-FORM-001` |
| `N01ay` | names `x86:vmovaps/base-index-zmm/evex` against `0.22.0` | `E-FORM-001` |
| `N02ab` | carries the scale as `x86.imm`/`scale2` | `E-OPERAND-001` |
| `N02ac` | supplies a `disp` operand to the no-displacement row | `E-OPERAND-002` |
| `N16aa` | passes index `4` (`%rsp`) to the `sib_index` slot | `E-RANGE-004` |
| `N16ab` | passes base `5` (`%rbp`) to the no-displacement row | `E-RANGE-004` |

`{evex} vmovaps (%rsp,%rax,1), %xmm32` is `error: invalid register name`, and
`{evex} vmovaps (%rsp,%rax,16), %xmm0` is
`error: scale factor in address must be 1, 2, 4 or 8`.

## 6. The fixture

`X86-P27-evex-mem-sib-index` is eighteen instructions and 156 bytes: each width
contributes load and store at each displacement shape, so the sizes per width
are 7, 8, 11, 7, 8, 11. The `xmm` six run `xmm20`–`xmm25`, the `ymm` six
`ymm9`–`ymm15`, the `zmm` six `zmm26`–`zmm31`; the fixture uses all four scale
contents, base `%rsp`/`%rbp`/`%r8`/`%r12` and index
`%rax`/`%rcx`/`%rdx`/`%r9`/`%r12`/`%r13`/`%r15`.

| Width | Load rows | Store rows |
|---|---|---|
| `xmm` | `xmm20` (none), `xmm21` (`disp8x16`), `xmm22` (`disp32`) | `xmm23` (none), `xmm24` (`disp8x16`), `xmm25` (`disp32`) |
| `ymm` | `ymm9` (none), `ymm10` (`disp8x32`), `ymm12` (`disp32`) | `ymm13` (none), `ymm14` (`disp8x32`), `ymm15` (`disp32`) |
| `zmm` | `zmm31` (none), `zmm30` (`disp8x64`), `zmm29` (`disp32`) | `zmm28` (none), `zmm27` (`disp8x64`), `zmm26` (`disp32`) |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`026935ad937cf03ed9e970d5cd4de53cf368f9a073e9ec362252d6a1010571f6`
(`fixture.asm`) and its `output_sha256` is
`79ca417d74df12f25e48edd28a31cac022801f3b4e490f46f25706af2cd6956e`
(the 156-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
eighteen lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- `%rbp`/`%r13` at `mod = 00`: no encoding exists; they stay on the
  `disp8*N = 0` row.
- The no-base indexed shape `disp32(,%rax,4)`: `SIB.base = 101` with
  `mod = 00` is exactly that addressing form, and it needs a `disp32` slot.
- A zero index (`index = 100` with `X̄ = 1`) as an operand: that is the
  no-index `SIB` byte `24`, which the fixed-base rows already own.
- The other EVEX SSE memory mnemonics (`vmovups`, `vmovdqa` and friends): the
  same shape with a different opcode byte.
- EVEX masking: `{k1}` writes the `aaa` field of `P2`.
- The `0x67` address-size prefix: it re-reads the same `SIB` fields as 32-bit
  registers.
