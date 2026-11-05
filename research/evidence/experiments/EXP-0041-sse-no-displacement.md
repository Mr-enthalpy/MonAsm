# EXP-0041 — the SSE memory operand with no displacement

- Date: 2026-11-05
- Question: how does an SSE load or store encode a base register with no
  displacement, which bases cannot use that shape, and is a missing displacement
  a different encoding from a zero one?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.12.0.json`
  (`sha256:a74ae09e3f9d2596f2e99edde80d6a487e8596efc05d87e59d6409f82ebf35ae`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P16-sse-no-disp.oracle.json`
- Source: `research/evidence/experiments/EXP-0041/P16.asm`
- Decision: `ADR-0039`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. `{evex}` forces the EVEX
family; without it `llvm-mc` emits VEX for `vmovaps` at `xmm` width.

| Source | Bytes | Length | Family |
|---|---|---|---|
| `movaps (%rax), %xmm0` | `0f 28 00` | 3 | legacy load, low/low |
| `movaps %xmm0, (%rax)` | `0f 29 00` | 3 | legacy store, low/low |
| `movaps (%rax), %xmm8` | `44 0f 28 00` | 4 | legacy load, `REX.R` |
| `movaps %xmm8, (%rax)` | `44 0f 29 00` | 4 | legacy store, `REX.R` |
| `movaps (%r8), %xmm0` | `41 0f 28 00` | 4 | legacy load, `REX.B` |
| `movaps %xmm0, (%r8)` | `41 0f 29 00` | 4 | legacy store, `REX.B` |
| `movaps (%r8), %xmm8` | `45 0f 28 00` | 4 | legacy load, `REX.R` + `REX.B` |
| `movaps %xmm8, (%r8)` | `45 0f 29 00` | 4 | legacy store, both |
| `vmovaps (%rax), %xmm0` | `c5 f8 28 00` | 4 | two-byte VEX load |
| `vmovaps %xmm0, (%rax)` | `c5 f8 29 00` | 4 | two-byte VEX store |
| `vmovaps (%rax), %xmm8` | `c5 78 28 00` | 4 | two-byte VEX load, `R̄ = 0` |
| `vmovaps (%r8), %xmm0` | `c4 c1 78 28 00` | 5 | three-byte VEX load, `B̄ = 0` |
| `vmovaps (%r8), %xmm8` | `c4 41 78 28 00` | 5 | three-byte VEX load, both |
| `vmovaps %xmm8, (%r8)` | `c4 41 78 29 00` | 5 | three-byte VEX store, both |
| `{evex} vmovaps (%rax), %xmm0` | `62 f1 7c 08 28 00` | 6 | EVEX load, low/low |
| `{evex} vmovaps (%r8), %xmm0` | `62 d1 7c 08 28 00` | 6 | EVEX load, `B̄ = 0` |
| `{evex} vmovaps (%rax), %xmm8` | `62 71 7c 08 28 00` | 6 | EVEX load, `R̄ = 0` |
| `{evex} vmovaps (%r8), %xmm8` | `62 51 7c 08 28 00` | 6 | EVEX load, both |
| `{evex} vmovaps %xmm8, (%r8)` | `62 51 7c 08 29 00` | 6 | EVEX store, both |

The `ModRM` byte is the last byte in every row and has `mod = 00`; `reg` holds
the `xmm` and `rm` the base. There is no displacement field to carry, so the
length is the prefix plus opcode plus `ModRM`.

## 2. No displacement and a zero displacement are one instruction, two lengths

`llvm-mc -disassemble` on raw byte strings (one line of `0x`-prefixed bytes per
case):

| Bytes | Length | `llvm-mc -disassemble` | Shape |
|---|---|---|---|
| `0f 28 00` | 3 | `movaps (%rax), %xmm0` | `mod = 00`, no displacement |
| `0f 28 40 00` | 4 | `movaps (%rax), %xmm0` | `mod = 01`, `disp8 = 0` |
| `62 f1 7c 08 28 00` | 6 | `vmovaps (%rax), %xmm0` | `mod = 00` |
| `62 f1 7c 08 28 40 00` | 7 | `vmovaps (%rax), %xmm0` | `mod = 01`, `disp8 = 0` |
| `0f 28 05 00 00 00 00` | 7 | `movaps (%rip), %xmm0` | `mod = 00`, `r/m = 101` |

The assembler also canonicalizes `movaps 0(%rax), %xmm0` to the three-byte
`0f 28 00`, so a source spelling cannot pin the width: the assembler chooses,
and an encoder that "prefers the short form" is making an `INV-02` decision.
The plan must name the width, so `0.12.0` gives it its own rows and the
`disp8` rows remain reachable with `disp = 0` (`EC-02`, `ADR-0039`).

## 3. Two base values are outside `mod = 00`

| Source | Bytes | Why not `mod = 00` |
|---|---|---|
| `movaps (%rsp), %xmm0` | `0f 28 04 24` | `r/m = 100` forces a `SIB` byte |
| `movaps (%r12), %xmm0` | `41 0f 28 04 24` | same, with `REX.B` |
| `movaps (%rbp), %xmm0` | `0f 28 45 00` | `r/m = 101` under `mod = 00` is `RIP + disp32` |
| `movaps (%r13), %xmm0` | `41 0f 28 45 00` | same, with `REX.B` |
| `vmovaps (%rbp), %xmm0` | `c5 f8 28 45 00` | same in VEX |
| `vmovaps (%r13), %xmm0` | `c4 c1 78 28 45 00` | same in three-byte VEX |
| `{evex} vmovaps (%rbp), %xmm0` | `62 f1 7c 08 28 45 00` | same in EVEX |
| `{evex} vmovaps (%r13), %xmm0` | `62 d1 7c 08 28 45 00` | same in EVEX, `B̄ = 0` |

The last four are `mod = 01` with `disp8 = 0`, not `mod = 00`; the RIP row in §2
is the same `r/m` value with the displacement the shape would have to carry.
`REX.B` does not
change the reading of `r/m = 101`, so base `5` and base `13` are outside the
no-displacement window in every family. A plan that names those bases must name
the `disp8` row with displacement `0`; the tables exclude them with
`E-RANGE-004` instead of rewriting the shape (`N16o`, `N16p`). `%rsp` and
`%r12` stay excluded for the `SIB` reason already recorded in `ADR-0028`
(`N16j`, `N16l`). The SSE RIP-relative form itself is still absent.

## 4. The register reach is the one `0.11.0` established

Nothing about a register's fourth bit is new here; the rows reuse the carriers
already measured in `EXP-0038`–`EXP-0040`:

- legacy forces the `REX` byte when either operand is high, so one window with
  `REX.R` spans every legal base (`44`/`45`), and a low `xmm` with a high base
  needs `REX.B` alone (`41`);
- two-byte VEX carries a high `xmm` in `R̄` at bit 15 and has no base bit, so a
  high base needs the three-byte `C4 C1 78` prefix, where `B̄` is bit 13;
- EVEX carries both, `R̄` at bit 15 for `ModRM.reg` and `B̄` at bit 13 for the
  base.

The measured `P0` values confirm the EVEX window: `f1` low/low, `d1` high base,
`71` high register, `51` both. The VEX probes confirm the inverted base bit:
`c4 c1 78 28 00` uses `P0 = c1` for a low base and `c4 41 78 28 00` uses `41`
for `%r8`.

## 5. The oracle

`P16.asm` is sixteen `movaps`/`vmovaps` mnemonics, with `{evex}` on the four
EVEX lines; no hand-assembled bytes. The source is 386 bytes, SHA-256
`58281cd839d80c816f70048c6f4cb960716f9ea051e65d0f721a4234e3c382dc`. `.text`
is 72 bytes, SHA-256
`3a38863cb3e00681b277948acc7fb3cfd74dace43c9cd5970ca77bcd4a313166`, and the
plan emits no fixup record.

The fixture fills every new row and every placement in it: the four legacy
windows in both directions with non-zero low bits (`%xmm2`, `%rcx`, `%xmm9`,
`%xmm10`, `%r9`), the two VEX prefixes with `R̄`/`B̄` set (`c5 78 28 02`,
`c4 41 78 28 13`, `c4 41 78 29 1a`), and the four EVEX `P0` values. The sizes
are 3, 3, 4, 4, 4, 4, 4, 4 (legacy), 4, 4, 5, 5 (VEX), 6, 6, 6, 6 (EVEX); each
matches the row the plan names, and no instruction has a displacement byte.

## 6. The rejections

- `N01ah` names `x86:movaps/xmm-base/legacy` against `0.11.0`: `E-FORM-001`.
  The no-displacement rows are `0.12.0` forms.
- `N14l` passes base `16` to the 4-bit base field: `E-OPERAND-004`,
  `field_bits = 4`.
- `N16o` passes `%rsp` to the low/low row: `E-RANGE-004`, `excluded = [4, 5]`.
  `%rsp` needs a `SIB` byte.
- `N16p` passes `%rbp` to the low/low row: `E-RANGE-004`. `mod = 00` with
  `r/m = 101` is RIP-relative, so the encoding it would produce is not the
  instruction the plan names.
- `N16q` passes a low base to `x86:movaps/xmm-base-ext/legacy`: `E-RANGE-004`.
  That row's `REX.B` is set, and the low bases belong to the three-byte rows.

## 7. What this does not claim

- The SSE RIP-relative form (`mod = 00`, `r/m = 101`) is still absent; the
  collision measured here is the reason it must be a separate decision.
- A base-only `SIB` row under these opcodes (`%rsp`, `%r12`), `mod = 00` for the
  GPR rows, the `0x67` address-size prefix, 8/16-bit memory widths, EVEX
  masking, `ymm`/`zmm`, `movapd`'s `0x66` form and `xmm16`–`xmm31` remain absent.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
