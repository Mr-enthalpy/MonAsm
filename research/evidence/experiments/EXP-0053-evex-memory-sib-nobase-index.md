# EXP-0053 -- the EVEX `vmovaps` memory rows with an index and no base

- Date: 2026-11-06
- Question: how do the EVEX `vmovaps` memory rows encode an indexed address
  with no base at `xmm`/`ymm`/`zmm` width, is the `disp32` slot optional, where
  do the index and scale bits sit without a base operand, and which shapes must
  stay separate?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.24.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P28-evex-mem-sib-nobase-index.oracle.json`
- Source: `research/evidence/experiments/EXP-0053/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0053/fixture.asm`
- Decision: `ADR-0051`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps (,%rax), %xmm0` | `62 f1 7c 08 28 04 05 00 00 00 00` | 11 |
| `{evex} vmovaps (,%rax,4), %xmm1` | `62 f1 7c 08 28 0c 85 00 00 00 00` | 11 |
| `{evex} vmovaps 4660(,%rax,4), %xmm2` | `62 f1 7c 08 28 14 85 34 12 00 00` | 11 |
| `{evex} vmovaps -4096(,%r12,8), %xmm3` | `62 b1 7c 08 28 1c e5 00 f0 ff ff` | 11 |
| `{evex} vmovaps 2147483647(,%rcx,2), %xmm31` | `62 61 7c 08 28 3c 4d ff ff ff 7f` | 11 |
| `{evex} vmovaps 0(,%r13,4), %ymm9` | `62 31 7c 28 28 0c ad 00 00 00 00` | 11 |
| `{evex} vmovaps 4096(,%r15,2), %ymm10` | `62 31 7c 28 28 14 7d 00 10 00 00` | 11 |
| `{evex} vmovaps %xmm4, (,%rdx,8)` | `62 f1 7c 08 29 24 d5 00 00 00 00` | 11 |
| `{evex} vmovaps %ymm5, 8192(,%rsi)` | `62 f1 7c 28 29 2c 35 00 20 00 00` | 11 |
| `{evex} vmovaps %zmm6, -4(,%rdi,4)` | `62 f1 7c 48 29 34 bd fc ff ff ff` | 11 |
| `{evex} vmovaps 128(,%rax,2), %zmm30` | `62 61 7c 48 28 34 45 80 00 00 00` | 11 |
| `{evex} vmovaps %zmm31, 2147483632(,%r9,8)` | `62 21 7c 48 29 3c cd f0 ff ff ff 7f` | 11 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same source line.

Every row is eleven bytes: there is no shorter form. The `ModRM` byte is the
`SIB` escape and the byte after it names the index and the scale, but the base
field is the constant `101`, so the displacement slot is always present:

| Source | `ModRM` | `SIB` | `SIB` fields |
|---|---|---|---|
| `(,%rax)` | `04` | `05` | scale `00`, index `000`, base `101` |
| `(,%rax,4)` | `0c` | `85` | scale `10`, index `000`, base `101` |
| `4660(,%rax,4)` | `14` | `85` | same, `disp32 = 0x1234` |

`(,%rax)` and `(,%rax,4)` differ in `ModRM.reg` (the vector register, `000`
vs `001`) and in the `SIB` scale bits; both keep base `101` and four
displacement bytes, the first two of which are zero.

## 2. Where the fields sit

| Field | Template bits | Placement |
|---|---|---|
| vector register | `[43,3]` plus `[12,1]`/`[15,1]` inverted | unchanged from `0.21.0`–`0.23.0` |
| `ModRM` | `[40,8]` | template: `04` (`mod = 00`, `r/m = 100`) |
| `SIB.base` | `[48,3]` | template: `101` ("no base, `disp32`") |
| `SIB.index` | `[51,3]` plus `[14,1]` inverted `X̄` | four-bit operand, `4` excluded |
| `SIB.scale` | `[54,2]` | two bits of field content (`0…3`) |
| `disp32` | `[56,32]` | byte offset, signed |

The index and scale do not move relative to `ADR-0050`; only the base field
became constant:

| Source | Bytes | What changed |
|---|---|---|
| `(,%rax,4), %xmm1` | `62 f1 7c 08 28 0c 85 …` | index `0`: `X̄ = 1`, `SIB = 85` |
| `(,%rdx,8), %xmm4` | `62 f1 7c 08 29 24 d5 …` | index `2`, ×8: `SIB = d5` |
| `-4096(,%r12,8), %xmm3` | `62 b1 7c 08 28 1c e5 …` | index `12`: `X̄ = 0` (`f1` → `b1`) |
| `(,%r13,4), %ymm9` | `62 31 7c 28 28 0c ad …` | index `13`: `X̄ = 0`, `SIB` index `101` |
| `(,%r15,2), %ymm10` | `62 31 7c 28 28 14 7d …` | index `15`: `X̄ = 0`, `SIB` index `111` |
| `(,%rcx,2), %xmm31` | `62 61 7c 08 28 3c 4d …` | index `1`, `R̄ = R̄' = 0` |

`X̄` is still the index's fourth bit, exactly as on the `0.23.0` rows: `%r12`
clears it while `%rax` leaves it set. The base field is not written by any
operand, so `48`–`50` stay `101`.

## 3. The scale and the mandatory displacement

The top two `SIB` bits are the scale, over one index value:

| Source | Bytes | `SIB` | Content |
|---|---|---|---|
| `(,%rax,1), %xmm0` | `62 f1 7c 08 28 04 05 …` | `05` | `0` |
| `(,%rax,2), %xmm0` | `62 f1 7c 08 28 04 45 …` | `45` | `1` |
| `(,%rax,4), %xmm0` | `62 f1 7c 08 28 04 85 …` | `85` | `2` |
| `(,%rax,8), %xmm0` | `62 f1 7c 08 28 04 c5 …` | `c5` | `3` |

Only the top bits move, so the scale is content, not a form. The multiplier is
`1 << content`, and `16` is not a field value (the assembler says
`scale factor in address must be 1, 2, 4 or 8`).

Unlike the with-base rows, a zero offset does not drop the displacement slot:

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps (,%rax), %xmm0` | `62 f1 7c 08 28 04 05 00 00 00 00` | 11 |
| `{evex} vmovaps 0(,%rax,1), %xmm0` | `62 f1 7c 08 28 04 05 00 00 00 00` | 11 |
| `{evex} vmovaps (%rsp,%rax,1), %xmm0` | `62 f1 7c 08 28 04 04` | 7 (with base) |

The with-base row is `ADR-0050`'s; the no-base row has no seven-byte form at
all, because `SIB.base = 101` at `mod = 00` *is* the displacement request.

## 4. The field ends and the rejections

`disp32` is signed, and the two ends are reachable:

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps 2147483647(,%rcx,2), %xmm31` | `62 61 7c 08 28 3c 4d ff ff ff 7f` | 11 |
| `{evex} vmovaps -4096(,%r12,8), %xmm3` | `62 b1 7c 08 28 1c e5 00 f0 ff ff` | 11 |
| `{evex} vmovaps -4(,%rdi,4), %zmm6` | `62 f1 7c 48 29 34 bd fc ff ff ff` | 11 |

`llvm-mc` also accepts `0x80000000` and wraps it to `00 00 00 80`
(`{evex} vmovaps 2147483648, %xmm0`), but the field is signed 32-bit, so a plan
carrying `2147483648` is `E-RANGE-001` (`N03k`); `-2147483648` is how the plan
says the same bytes.

The address expression itself is bounded the same way as `ADR-0050`:

| Probe | Result |
|---|---|
| `{evex} vmovaps (,%rsp,1), %xmm0` | `error: invalid base+index expression` |
| `{evex} vmovaps (,%rax,16), %xmm0` | `error: scale factor in address must be 1, 2, 4 or 8` |
| `{evex} vmovaps (,%rax,1), %xmm32` | `error: invalid register name` |
| `{evex} vmovaps 0(%rbp,%rax,1), %xmm0` | `62 f1 7c 08 28 44 05 00` — the with-base `disp8*N = 0` row |

The last line is the `0.23.0` row, not this one: a base that is `%rbp` cannot
take `mod = 00` with an index, so the assembler keeps `mod = 01` and a zero
displacement byte.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01az` | names `x86:vmovaps/xmm-index-disp32/evex` against `0.23.0` | `E-FORM-001` |
| `N01ba` | names `x86:vmovaps/index-disp32-zmm/evex` against `0.23.0` | `E-FORM-001` |
| `N02ad` | supplies a `base` operand to the no-base row | `E-OPERAND-002` (`expected 4, found 5`) |
| `N02ae` | carries the scale as `x86.imm`/`scale2` | `E-OPERAND-001` |
| `N03k` | carries `disp32` content `2147483648` | `E-RANGE-001` |
| `N16ac` | passes index `4` (`%rsp`) to the `sib_index` slot | `E-RANGE-004` |

## 6. The fixture

`X86-P28-evex-mem-sib-nobase-index` is six instructions and 66 bytes, all
eleven bytes: a load and a store at each width.

| Width | Load | Store |
|---|---|---|
| `xmm` | `(,%rax,1)`, `disp32 = 0` | `%xmm21, 4660(,%r12,4)` |
| `ymm` | `-4096(,%r13,8)`, `%ymm8` | `%ymm9, 8192(,%r15,2)` |
| `zmm` | `128(,%rcx,1)`, `%zmm31` | `%zmm30, 2147483647(,%rsi,2)` |

The fixture uses all four scale contents, index numbers `0`, `1`, `6`, `12`,
`13` and `15` (so both the `SIB` field and `X̄` move), the five-bit EVEX window
at `xmm20`/`xmm21` and `zmm30`/`zmm31`, a negative displacement and the signed
`disp32` end point.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`9a9471e3f66b61c6e89c47a6157109f0ecda70ea1bc56a16a2f91a3fbecf003f`
(`fixture.asm`) and its `output_sha256` is
`660b25b821f6fcd4184da97f93d46ecde2a41aa1942e6eef60cbd9becfbb01a7`
(the 66-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the six
lines in `fixture-encoding.txt`, and the materializer's output is byte-identical
to the oracle.

## 7. What the slice defers

- The absolute address shape (`vmovaps 0x1234, %xmm0`): `SIB = 25` has
  `index = 100` *and* `base = 101`, so it has neither an index nor a base
  operand. Measured in `abs.asm`:
  `62 f1 7c 08 28 04 25 34 12 00 00`.
- `%rbp`/`%r13` as a base at `mod = 00` with an index: no encoding exists; they
  stay on the with-base `disp8*N = 0` row.
- A zero index (`index = 100` with `X̄ = 1`) as an operand: that is the
  no-index `SIB` byte, which the fixed-base and absolute rows own.
- The other EVEX SSE memory mnemonics (`vmovups`, `vmovdqa` and friends): the
  same shape with a different opcode byte.
- EVEX masking: `{k1}` writes the `aaa` field of `P2`.
- The `0x67` address-size prefix: it re-reads the same `SIB` fields as 32-bit
  registers.
