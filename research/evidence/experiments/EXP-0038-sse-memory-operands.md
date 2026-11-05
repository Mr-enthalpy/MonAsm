# EXP-0038 — x86-64 SSE memory operands, and the EVEX `disp8*N` field

- Date: 2026-11-05
- Question: how do the legacy, VEX and EVEX families encode `movaps`/`vmovaps`
  with a base and a displacement, which bits carry the base, and how does the
  EVEX `disp8` byte relate to the byte offset?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.9.0.json`
  (`sha256:cc538253ba2d8a111ee16a8d5a8db1aa6efaaed75270889eed20f0f2f5ed6eb8`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P13-sse-memory.oracle.json`
- Source: `research/evidence/experiments/EXP-0038/P13.asm`
- Probes: `research/evidence/experiments/EXP-0038/P13probe.asm`,
  `research/evidence/experiments/EXP-0038/P13evex.asm`
- Decision: `ADR-0036`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. `{evex}` forces the EVEX
family; without it `llvm-mc` emits VEX for `vmovaps` at `xmm` width.

| Source | Bytes | Family | `disp` |
|---|---|---|---|
| `movaps 8(%rax), %xmm0` | `0f 28 40 08` | legacy load | `disp8` = `08` |
| `movaps 128(%rax), %xmm1` | `0f 28 88 80 00 00 00` | legacy load | `disp32` = `80 00 00 00` |
| `movaps %xmm2, 8(%rax)` | `0f 29 50 08` | legacy store | `disp8` = `08` |
| `movaps %xmm3, 128(%rbp)` | `0f 29 9d 80 00 00 00` | legacy store | `disp32` = `80 00 00 00` |
| `vmovaps 8(%rax), %xmm4` | `c5 f8 28 60 08` | VEX load | `disp8` = `08` |
| `vmovaps 128(%rax), %xmm5` | `c5 f8 28 a8 80 00 00 00` | VEX load | `disp32` = `80 00 00 00` |
| `vmovaps %xmm6, 8(%rax)` | `c5 f8 29 70 08` | VEX store | `disp8` = `08` |
| `vmovaps %xmm7, 128(%rbp)` | `c5 f8 29 bd 80 00 00 00` | VEX store | `disp32` = `80 00 00 00` |
| `{evex} vmovaps 16(%rax), %xmm0` | `62 f1 7c 08 28 40 01` | EVEX load | `disp8` = `01` (content `1`) |
| `{evex} vmovaps -16(%rax), %xmm1` | `62 f1 7c 08 28 48 ff` | EVEX load | `disp8` = `ff` (content `-1`) |
| `{evex} vmovaps 2032(%rax), %xmm2` | `62 f1 7c 08 28 50 7f` | EVEX load | `disp8` = `7f` (content `127`) |
| `{evex} vmovaps 8(%rax), %xmm3` | `62 f1 7c 08 28 98 08 00 00 00` | EVEX load | `disp32` = `08 00 00 00` |
| `{evex} vmovaps %xmm4, 16(%rax)` | `62 f1 7c 08 29 60 01` | EVEX store | `disp8` = `01` (content `1`) |
| `{evex} vmovaps %xmm5, 8(%rbp)` | `62 f1 7c 08 29 ad 08 00 00 00` | EVEX store | `disp32` = `08 00 00 00` |

The direction is the opcode: `0F 28` is the load (`ModRM.reg` is the
destination) and `0F 29` is the store (`ModRM.reg` is the source). The family is
the prefix, and it moves `ModRM` and `disp`: legacy `ModRM` at byte 2,
two-byte VEX at byte 3 and EVEX at byte 5.

## 2. The base is three bits in all three families

The base is `ModRM.rm` in every row, but no family can carry a fourth bit in
the same shape:

| Probe | Bytes | What it shows |
|---|---|---|
| `movaps 8(%r8), %xmm0` | `41 0f 28 40 08` | legacy needs a `REX` byte (`REX.B`) |
| `vmovaps 8(%r8), %xmm0` | `c4 c1 78 28 40 08` | two-byte `C5` has no `B`; the assembler switches to three-byte `C4` |
| `{evex} vmovaps 16(%r8), %xmm0` | `62 d1 7c 08 28 40 01` | EVEX has `B̄` at bit 13, but inverted: `P0 = d1`, `B̄ = 0` |

Writing a base's fourth bit raw into bit 13 would leave `P0 = f1` and encode
`16(%rax)`, not `16(%r8)`. The shared shape is therefore a 3-bit base in all
three families. The same argument keeps `xmm` three bits: the extension is
`REX.R` in legacy (`movaps 8(%rax), %xmm8` = `44 0f 28 40 08`), an inverted
`R̄` in VEX (`c5 78`) and an inverted `R̄` in EVEX (`62 71`).

`%rsp` is excluded in every family because it forces a `SIB` byte:
`{evex} vmovaps 8(%rsp), %xmm0` is `62 f1 7c 08 28 84 24 08 00 00 00`
(`r/m = 100`, `SIB = 24`, then `disp32 = 8`). `%rbp` is an ordinary base:
`8(%rbp)` under EVEX is only promoted because `8` is not a multiple of `16`,
not because of the register.

## 3. EVEX `disp8` is compressed

At `xmm` width with `W = 0`, the EVEX `disp8` unit is `N = 16`. The content is
the byte offset divided by 16, and the field is signed 8 bits:

| Byte offset | `disp8` byte | Content |
|---|---|---|
| `16` | `01` | `1` |
| `32` | `02` | `2` |
| `128` | `08` | `8` |
| `256` | `10` | `16` |
| `-16` | `ff` | `-1` |
| `2032` | `7f` | `127` |
| `8` | — | `disp32` (`08 00 00 00`) |
| `2048` | — | `disp32` (`00 08 00 00`) |

`8` is not a multiple of 16, and `2048` would need content `128`, which is
outside signed 8 bits. In both cases `llvm-mc` uses `disp32` with the byte
value. The plan must name the row it wants: the `disp8x16` row carries the
content `1` for 16 bytes, while the `disp32` row carries the byte `8`. The
materializer never divides, multiplies or promotes.

## 4. The oracle

`P13.asm` is fourteen `movaps`/`vmovaps` mnemonics, with `{evex}` on the six
EVEX lines; no hand-assembled bytes. The source is 844 bytes, SHA-256
`6ea0dd8828a9e92d5d9bb5813dda11936a9ae41e2028f894c64698177f49fbdf`. `.text`
is 96 bytes, SHA-256
`ff1502f30e775a9b3c4901c358a5ac8555b793797e4aa522f992189377d2ee45`, and the
plan emits no fixup record. The fixture's expected bytes are this `.text`.

Every displacement in the source fits the row the plan names: `8`/`128` for
the legacy and VEX `disp8`/`disp32` rows, content `1`/`-1`/`127` for the EVEX
`disp8x16` rows, and byte `8` for the EVEX `disp32` rows. The only promotion
is the assembler's choice for `8(%rax)` and `8(%rbp)` in EVEX; those two lines
are the `disp32` rows in the plan.

## 5. The rejections

- `N01ae` names the new legacy row against `0.8.0`, where it does not exist:
  `E-FORM-001`.
- `N14e` passes `xmm8` to the 3-bit `xmm` slot of a VEX store row:
  `E-OPERAND-004`, `field_bits = 3`.
- `N14f` passes `r8` to the 3-bit VEX base: `E-OPERAND-004`,
  `field_bits = 3`. `C5` cannot carry the bit; the plan does not get a `C4`
  form by accident.
- `N16j` passes `%rsp` as a legacy base: `E-RANGE-004`, `excluded = [4]`.
- `N14g` passes `r8` to the 3-bit EVEX base: `E-OPERAND-004`. This pins the
  deferral: the materializer does not write a raw fourth bit into the inverted
  `B̄` position.
- `N03d` passes content `128` to a `disp8x16` slot: `E-RANGE-001`,
  `min = -128`, `max = 127`. The value is content, not a byte offset.
- `N02m` passes a `dest` operand to a store row: `E-OPERAND-002`; the role
  sequence is `src, base, disp`.

## 6. What this does not claim

- `r8`–`r15` as a base, and `xmm8`–`xmm15`, are not encoded by these rows.
  Widening needs a family-specific mechanism (legacy `REX`, VEX `C4`, EVEX
  inversion) and a separate decision.
- A `SIB` base under these opcodes (`%rsp`/`%r12` with `r/m = 100`), `mod = 00`
  memory operands, EVEX masking, `ymm`/`zmm`, `movapd`'s `0x66` form and the
  three-byte VEX `C4` form are absent.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
