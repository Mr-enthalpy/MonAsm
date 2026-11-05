# EXP-0054 -- the EVEX `vmovaps` memory rows with a 32-bit absolute address

- Date: 2026-11-06
- Question: how do the EVEX `vmovaps` memory rows encode a 32-bit absolute
  address at `xmm`/`ymm`/`zmm` width, which `SIB` fields become constants, is
  the displacement optional, and how do the register-based neighbours differ?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.25.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P29-evex-mem-sib-absolute.oracle.json`
- Source: `research/evidence/experiments/EXP-0054/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0054/fixture.asm`
- Decision: `ADR-0052`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps 0x1234, %xmm0` | `62 f1 7c 08 28 04 25 34 12 00 00` | 11 |
| `{evex} vmovaps %xmm1, 0x1234` | `62 f1 7c 08 29 0c 25 34 12 00 00` | 11 |
| `{evex} vmovaps 0x0, %xmm2` | `62 f1 7c 08 28 14 25 00 00 00 00` | 11 |
| `{evex} vmovaps -4096, %xmm3` | `62 f1 7c 08 28 1c 25 00 f0 ff ff` | 11 |
| `{evex} vmovaps 0x7fffffff, %xmm31` | `62 61 7c 08 28 3c 25 ff ff ff 7f` | 11 |
| `{evex} vmovaps 0x1234, %ymm4` | `62 f1 7c 28 28 24 25 34 12 00 00` | 11 |
| `{evex} vmovaps %ymm5, 0x1234` | `62 f1 7c 28 29 2c 25 34 12 00 00` | 11 |
| `{evex} vmovaps 0x1000, %zmm6` | `62 f1 7c 48 28 34 25 00 10 00 00` | 11 |
| `{evex} vmovaps %zmm7, 0x1000` | `62 f1 7c 48 29 3c 25 00 10 00 00` | 11 |
| `{evex} vmovaps -1, %zmm30` | `62 61 7c 48 28 34 25 ff ff ff ff` | 11 |
| `{evex} vmovaps %xmm21, -2147483648` | `62 e1 7c 08 29 2c 25 00 00 00 80` | 11 |
| `{evex} vmovaps 0x0, %zmm31` | `62 61 7c 48 28 3c 25 00 00 00 00` | 11 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same address (printing `4660`/`4096` in decimal and `-2147483648` as such).

Every row is eleven bytes. `ModRM` is `04` and the `SIB` byte is `25` in every
one of them:

| Byte | Value | Fields |
|---|---|---|
| `ModRM` | `04` | `mod = 00`, `reg` = vector low bits, `r/m = 100` (`SIB` escape) |
| `SIB` | `25` | scale `00`, index `100` ("no index"), base `101` ("no base, `disp32`") |
| `disp32` | four bytes | signed address at `[56,32]` |

The `SIB` byte therefore has no operand-owned field at all: both register
fields are constants and the scale is constant zero.

## 2. Where the fields sit

| Field | Template bits | Placement |
|---|---|---|
| vector register | `[43,3]` plus `[12,1]`/`[15,1]` inverted | unchanged from `0.21.0`–`0.24.0` |
| `ModRM` | `[40,8]` | template: `04` (`mod = 00`, `r/m = 100`) |
| `SIB` | `[48,8]` | template: `25` (index `100`, base `101`, scale `00`) |
| `disp32` | `[56,32]` | the address itself, signed |

The vector slot keeps the same three placements as `ADR-0051`: this slice adds
no register field, so the five-bit window is carried by template bytes plus the
one field it already had.

| Source | `ModRM` | `P0` | Register bits |
|---|---|---|---|
| `0x1234, %xmm0` | `04` | `f1` | bits 4/3 = `1`/`1` inverted |
| `0x1234, %ymm8` | `04` | `71` | bits 4/3 = `1`/`0` inverted |
| `0x1234, %xmm20` | `24` | `e1` | low three bits `100`, bits 4/3 = `0`/`1` |
| `%xmm21, -2147483648` | `2c` | `e1` | low three bits `101`, bits 4/3 = `0`/`1` |
| `-1, %zmm30` | `34` | `61` | low three bits `110`, bits 4/3 = `0`/`1` |
| `0x7fffffff, %xmm31` | `3c` | `61` | low three bits `111`, bits 4/3 = `0`/`1` |

`[12,1]` is the register's fourth bit and `[15,1]` its third, both inverted,
exactly as the indexed rows use them for the destination and source.

## 3. The displacement is mandatory

`SIB.base = 101` at `mod = 00` *is* the request for a 32-bit displacement, so
the field never disappears and a zero address still spends four bytes:

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps 0x0, %xmm2` | `62 f1 7c 08 28 14 25 00 00 00 00` | 11 |
| `{evex} vmovaps 0x1234, %xmm0` | `62 f1 7c 08 28 04 25 34 12 00 00` | 11 |
| `{evex} vmovaps 0x7fff, %ymm9` (fixture 4) | `62 71 7c 28 29 0c 25 ff 7f 00 00` | 11 |

The third row is the tell: `0x7fff` would fit a `disp8`, but the shape has no
`disp8` form, and the assembler writes the full field. The field ends are both
reachable:

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps 0x7fffffff, %xmm31` | `62 61 7c 08 28 3c 25 ff ff ff 7f` | 11 |
| `{evex} vmovaps %xmm21, -2147483648` | `62 e1 7c 08 29 2c 25 00 00 00 80` | 11 |
| `{evex} vmovaps -4096, %xmm3` | `62 f1 7c 08 28 1c 25 00 f0 ff ff` | 11 |
| `{evex} vmovaps -1, %zmm30` | `62 61 7c 48 28 34 25 ff ff ff ff` | 11 |

## 4. The neighbours and the rejections

The address can be written three other ways, and each is a different byte
string:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `{evex} vmovaps 0x1234(%rax), %xmm0` | `62 f1 7c 08 28 80 34 12 00 00` | 10 | base + `disp32`, no `SIB` |
| `{evex} vmovaps 0x1234(%rip), %xmm0` | `62 f1 7c 08 28 05 34 12 00 00` | 10 | `RIP`-relative, no `SIB` |
| `{evex} vmovaps 0x1234(,%rax,4), %xmm0` | `62 f1 7c 08 28 04 85 34 12 00 00` | 11 | index, no base (`ADR-0051`) |
| `{evex} vmovaps 0x1234, %xmm0` | `62 f1 7c 08 28 04 25 34 12 00 00` | 11 | absolute (this slice) |

The indexed row and the absolute row differ only in `SIB` bits 51–53:
`85` writes the index `000` with scale `10`, `25` has index `100` and scale
`00`. Base `101` and the four displacement bytes are the same in both.

`llvm-mc` truncates addresses it cannot represent rather than refusing them:

| Probe | Result |
|---|---|
| `{evex} vmovaps 0x80000000, %xmm0` | `62 f1 7c 08 28 04 25 00 00 00 80` (wraps) |
| `{evex} vmovaps 0x100000000, %xmm0` | `62 f1 7c 08 28 04 25 00 00 00 00` (wraps twice) |
| `{evex} vmovaps 0x1234, %xmm32` | `error: invalid register name` |

The field is signed 32-bit, so a plan carrying `2147483648` or
`0x100000000` is `E-RANGE-001` (`N03l`) rather than a wrapped address;
`-2147483648` is how the plan says the bytes `00 00 00 80`.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bb` | names `x86:vmovaps/xmm-abs32/evex` against `0.24.0` | `E-FORM-001` |
| `N01bc` | names `x86:vmovaps/abs32-zmm/evex` against `0.24.0` | `E-FORM-001` |
| `N02af` | supplies an `index` operand to the absolute row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N02ag` | carries the address as `disp8`/`x86.imm` | `E-OPERAND-001` on `target_type` |
| `N03l` | carries `disp32` content `2147483648` | `E-RANGE-001` |

## 6. The fixture

`X86-P29-evex-mem-sib-absolute` is six instructions and 66 bytes, all eleven
bytes: a load and a store at each width.

| Width | Load | Store |
|---|---|---|
| `xmm` | `0x1234, %xmm20` | `%xmm21, -4096` |
| `ymm` | `0x1000, %ymm8` | `%ymm9, 0x7fff` |
| `zmm` | `-1, %zmm31` | `%zmm30, -2147483648` |

The fixture pins the five-bit EVEX window at `xmm20`/`xmm21` and
`zmm30`/`zmm31`, a positive and a negative address, the signed end point
`-2147483648`, and `0x7fff`, a value that would fit a `disp8` but is still
written in four bytes.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`2ae4358da56356291fb3f7359f4a803004c4db2d2ab3d811781df52fee1ab266`
(`fixture.asm`) and its `output_sha256` is
`35a811913bdaca94a123bd24954b144d3c81b2c881259d36608ce81b7a4a31ad`
(the 66-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
six lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- A symbol or relocation in the address (`R_X86_64_32`, `R_X86_64_32S`): the
  displacement stops being content and becomes a fixup.
- The `0x67` address-size prefix: the same fields read as a 32-bit address
  model.
- The other EVEX SSE memory mnemonics (`vmovups`, `vmovdqa` and friends): the
  same shape with a different opcode byte.
- EVEX masking: `{k1}` writes the `aaa` field of `P2`.
- The absolute shape under the GPR and 8/16-bit `mov` opcodes
  (`48 8b 04 25 …`); `mov al, [0x1234]` re-opens `EC-05`, because `A0` is a
  second legal encoding of the same address.
