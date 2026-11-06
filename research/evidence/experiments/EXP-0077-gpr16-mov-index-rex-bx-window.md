# EXP-0077 -- the 16-bit `mov` index/scale rows with `REX.B` and `REX.X` together

- Date: 2026-11-07
- Question: what does the 16-bit indexed `mov` shape cost when the base and the
  index are both in `%r8`–`%r15` while the register stays in `%ax`–`%di`, and
  where do `ModRM`, `SIB` and the displacement sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.48.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P52-gpr16-mov-index-rex-bx-window.oracle.json`
- Source: `research/evidence/experiments/EXP-0077/probe.asm`
- Decision: `ADR-0075`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%r8,%r9,1), %ax` | `66 43 8b 44 08 08` | 6 |
| `movw 8(%r15,%r15,8), %di` | `66 43 8b 7c ff 08` | 6 |
| `movw %ax, 8(%r8,%r9,1)` | `66 43 89 44 08 08` | 6 |
| `movw %di, 8(%r15,%r15,8)` | `66 43 89 7c ff 08` | 6 |
| `movw 8(%r12,%r12,1), %ax` | `66 43 8b 44 24 08` | 6 |
| `movw %ax, 8(%r12,%r12,1)` | `66 43 89 44 24 08` | 6 |
| `movw 200(%r8,%r9,1), %ax` | `66 43 8b 84 08 c8 00 00 00` | 9 |
| `movw 200(%r15,%r15,8), %di` | `66 43 8b bc ff c8 00 00 00` | 9 |
| `movw %ax, 200(%r8,%r9,1)` | `66 43 89 84 08 c8 00 00 00` | 9 |
| `movw %di, 200(%r15,%r15,8)` | `66 43 89 bc ff c8 00 00 00` | 9 |
| `movw 200(%r12,%r12,1), %ax` | `66 43 8b 84 24 c8 00 00 00` | 9 |
| `movw %ax, 200(%r12,%r12,1)` | `66 43 89 84 24 c8 00 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `0x66` | `REX` | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|---|
| window, `disp8` | `66 43 8b 44 08 08` | byte 0 | `43` at byte 1 (`X = 1` at `[9,1]`, `B = 1` at `[8,1]`) | byte 2 | `44` at byte 3 (`mod = 01`, `reg = 0` at `[27,3]`, `r/m = 100`) | byte 4: scale `[38,2] = 0`, index `[35,3] = 1`, base `[32,3] = 0` | `[40,8]` |
| window, high registers | `66 43 8b 7c ff 08` | byte 0 | `43` | byte 2 | `7c` (`mod = 01`, `reg = 7`, `r/m = 100`) | `ff`: scale `3`, index `7`, base `7` | `[40,8]` |
| window, `%r12`/`%r12` | `66 43 8b 44 24 08` | byte 0 | `43` | byte 2 | `44` (`mod = 01`, `reg = 0`) | `24`: scale `0`, index `100`, base `100` | `[40,8]` |
| window, `disp32` | `66 43 8b 84 08 c8 00 00 00` | byte 0 | `43` | byte 2 | `84` (`mod = 10`, `r/m = 100`) | `08` | `[40,32]` |
| window, `%r12` `disp32` | `66 43 8b 84 24 c8 00 00 00` | byte 0 | `43` | byte 2 | `84` (`mod = 10`) | `24` | `[40,32]` |

`REX = 43` is `0100_0011`: `W = 0`, `R = 0`, `X = 1`, `B = 1`. The register is
three bits at `[27,3]` and the two memory operands are four-bit slots whose most
significant bit is the `REX` bit: base `[8,1]` + `[32,3]`, index `[9,1]` +
`[35,3]`. The displacement follows the `SIB` byte at `[40,8]` or `[40,32]`,
exactly where the `0.45.0`/`0.47.0` rows put it.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%rax,%rsp,1), %ax` | rejected | -- | `%rsp` is not an index (`invalid base+index expression`) |
| `movw 8(%rax,%rcx,1), %ax` | `66 8b 44 08 08` | 5 | the `0.46.0` `REX`-less row |
| `movw 8(%r8,%rcx,1), %ax` | `66 41 8b 44 08 08` | 6 | the `0.47.0` `REX.B` window |
| `movw 8(%rax,%r9,1), %ax` | `66 42 8b 44 08 08` | 6 | the `0.47.0` `REX.X` window |
| `movw 8(%r8,%r9,1), %r8w` | `66 47 8b 44 08 08` | 6 | the `0.45.0` `REX.R`/`X`/`B` row (`REX = 47`) |
| `movw 127(%r8,%r9,1), %ax` | `66 43 8b 44 08 7f` | 6 | the signed byte upper end |
| `movw -128(%r8,%r9,1), %ax` | `66 43 8b 44 08 80` | 6 | the signed byte lower end |
| `movw 8(%rbp,%r13,1), %ax` | `66 42 8b 44 2d 08` | 6 | `%rbp` as a base, `%r13` as an index (`REX.X` only) |
| `movw 8(%r13,%rbp,1), %ax` | `66 41 8b 44 2d 08` | 6 | `%r13` as a base (`REX.B` only), `%rbp` as an index |
| `movw 8(%rsp,%r9,1), %ax` | `66 42 8b 44 0c 08` | 6 | `SIB.base = 100` behind `REX.X` only |
| `movw 8(%r12,%r13,1), %ax` | `66 43 8b 44 2c 08` | 6 | `SIB.base = 100` behind `REX.B`, `%r13` index |
| `movw 8(%r8,%r9,1), %r16w` | `66 d5 43 8b 44 08 08` | 7 | the APX `d5` window |

`adjacent-encoding.txt` records the eleven accepted lines and the assembler
diagnostic for the `%rsp` index.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cx` | names `x86:mov/r16-base-ext-index-ext-disp8/legacy` against `0.47.0` | `E-FORM-001` |
| `N01cy` | names `x86:mov/base-ext-index-ext-disp8-r16/legacy` against `0.47.0` | `E-FORM-001` |
| `N02br` | drops the `index` from the load row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03za` | scale `4` on the load row, past the two-bit field | `E-RANGE-001` |
| `N14bf` | register `8` on the load row | `E-OPERAND-004` |
| `N16ca` | base `3` on the store row, below the window | `E-RANGE-004` |
| `N16cb` | index `3` on the store row, below the window | `E-RANGE-004` |

The claims the ADR turns on: the register field is three bits, so register `8`
must be rejected rather than cleared; both extended slots exclude the low
window, so a low base or index cannot silently clear the fixed `REX.B`/`REX.X`;
and the scale slot is still two bits of field content.

`%rsp` is legal as a base in this window (`8(%rsp,%r9,1), %ax` is
`66 42 8b 44 0c 08`), and `%r12` is legal as both base and index
(`66 43 8b 44 24 08`, and `8(%r12,%r13,1), %ax` is `66 43 8b 44 2c 08`), which
is why the window floors are base `3`/index `3` rather than the `SIB`-encoded
values.

## 5. The fixture

`X86-P52-gpr16-mov-index-rex-bx-window` is twelve instructions and 90 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%r8,%r9,1), %ax` | `66 43 8b 44 08 08` | 6 |
| 2 | `movw 8(%r15,%r15,8), %di` | `66 43 8b 7c ff 08` | 6 |
| 3 | `movw %ax, 8(%r8,%r9,1)` | `66 43 89 44 08 08` | 6 |
| 4 | `movw %di, 8(%r15,%r15,8)` | `66 43 89 7c ff 08` | 6 |
| 5 | `movw 8(%r12,%r12,1), %ax` | `66 43 8b 44 24 08` | 6 |
| 6 | `movw %ax, 8(%r12,%r12,1)` | `66 43 89 44 24 08` | 6 |
| 7 | `movw 200(%r8,%r9,1), %ax` | `66 43 8b 84 08 c8 00 00 00` | 9 |
| 8 | `movw 200(%r15,%r15,8), %di` | `66 43 8b bc ff c8 00 00 00` | 9 |
| 9 | `movw %ax, 200(%r8,%r9,1)` | `66 43 89 84 08 c8 00 00 00` | 9 |
| 10 | `movw %di, 200(%r15,%r15,8)` | `66 43 89 bc ff c8 00 00 00` | 9 |
| 11 | `movw 200(%r12,%r12,1), %ax` | `66 43 8b 84 24 c8 00 00 00` | 9 |
| 12 | `movw %ax, 200(%r12,%r12,1)` | `66 43 89 84 24 c8 00 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`5dc650423e5737666d6fb360a0c13aaacfd3c6bbdf9bc96fb9e38dc901f276dc`
(`probe.asm`) and its `output_sha256` is
`3cc9c66f5a3f49ce79713770738721bfd023981b25471c34a8604b2ae2cbbc47`
(the 90-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:79d27bd8efceb88d86628875679d1293e71cda9d8a10b7b0f762f5442b2ef9dc`.

`0.48.0` has 389 forms and the canonical digest
`sha256:552b82733ac35ec9d6270dbab21bef8b19f3de800f25fc7f9c0654c4eb6189ff`.

## 6. What the slice defers

- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The APX `d5` register window, whose shape here is `66 d5 43 8b 44 08 08`.
