# EXP-0044 — the EVEX compressed-displacement unit at `ymm`/`zmm` width

- Date: 2026-11-05
- Question: is the EVEX `disp8*N` unit a constant, which prefix field selects it,
  what are its range and promotion boundaries at 256 and 512 bits, and does
  VEX.256 memory need the same mechanism?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.15.0.json`
  (`sha256:305e96047cf870f963c7115ec1ecb205cdb48d83e629b67d5eb8db7720a014a4`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P19-sse-ymm-zmm-memory.oracle.json`
- Source: `research/evidence/experiments/EXP-0044/P19.asm`
- Decision: `ADR-0042`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. `{evex}` forces the
EVEX family at 256 bits, where the assembler would otherwise pick VEX; `zmm`
has no VEX form and needs no directive:

| Source | Bytes | Length |
|---|---|---|
| `{evex} vmovaps (%rax), %ymm0` | `62 f1 7c 28 28 00` | 6 |
| `{evex} vmovaps %ymm0, (%rax)` | `62 f1 7c 28 29 00` | 6 |
| `{evex} vmovaps (%r8), %ymm31` | `62 41 7c 28 28 38` | 6 |
| `{evex} vmovaps %ymm31, (%r8)` | `62 41 7c 28 29 38` | 6 |
| `{evex} vmovaps 32(%rax), %ymm0` | `62 f1 7c 28 28 40 01` | 7 |
| `{evex} vmovaps -32(%rax), %ymm0` | `62 f1 7c 28 28 40 ff` | 7 |
| `{evex} vmovaps 4064(%rax), %ymm0` | `62 f1 7c 28 28 40 7f` | 7 |
| `{evex} vmovaps -4096(%rax), %ymm0` | `62 f1 7c 28 28 40 80` | 7 |
| `{evex} vmovaps 28(%rax), %ymm0` | `62 f1 7c 28 28 80 1c 00 00 00` | 10 |
| `{evex} vmovaps 4096(%rax), %ymm0` | `62 f1 7c 28 28 80 00 10 00 00` | 10 |
| `{evex} vmovaps 32(%r8), %ymm31` | `62 41 7c 28 28 78 01` | 7 |
| `{evex} vmovaps %ymm31, -32(%r8)` | `62 41 7c 28 29 78 ff` | 7 |
| `{evex} vmovaps %ymm31, 28(%r8)` | `62 41 7c 28 29 b8 1c 00 00 00` | 10 |
| `vmovaps (%rax), %zmm0` | `62 f1 7c 48 28 00` | 6 |
| `vmovaps %zmm0, (%rax)` | `62 f1 7c 48 29 00` | 6 |
| `vmovaps (%r8), %zmm31` | `62 41 7c 48 28 38` | 6 |
| `vmovaps %zmm31, (%r8)` | `62 41 7c 48 29 38` | 6 |
| `vmovaps 64(%rax), %zmm0` | `62 f1 7c 48 28 40 01` | 7 |
| `vmovaps -64(%rax), %zmm0` | `62 f1 7c 48 28 40 ff` | 7 |
| `vmovaps 8128(%rax), %zmm0` | `62 f1 7c 48 28 40 7f` | 7 |
| `vmovaps -8192(%rax), %zmm0` | `62 f1 7c 48 28 40 80` | 7 |
| `vmovaps 60(%rax), %zmm0` | `62 f1 7c 48 28 80 3c 00 00 00` | 10 |
| `vmovaps 8192(%rax), %zmm0` | `62 f1 7c 48 28 80 00 20 00 00` | 10 |
| `vmovaps 64(%r8), %zmm31` | `62 41 7c 48 28 78 01` | 7 |
| `vmovaps %zmm31, -64(%r8)` | `62 41 7c 48 29 78 ff` | 7 |
| `vmovaps %zmm31, 60(%r8)` | `62 41 7c 48 29 b8 3c 00 00 00` | 10 |

The `ymm` and `zmm` blocks are the same twenty-six instructions with one byte
changed: `P2` is `28` for 256 bits and `48` for 512. Every other byte of the
paired rows is identical.

## 2. One field content, three displacements: `P2` is the unit

`llvm-mc -disassemble` on one line of `0x`-prefixed bytes per case
(`p2.txt`), holding the displacement byte at `0x01`:

| Bytes | `llvm-mc -disassemble` | `P2` | Unit |
|---|---|---|---|
| `62 f1 7c 08 28 40 01` | `vmovaps 16(%rax), %xmm0` | `08` | 16 |
| `62 f1 7c 28 28 40 01` | `vmovaps 32(%rax), %ymm0` | `28` | 32 |
| `62 f1 7c 48 28 40 01` | `vmovaps 64(%rax), %zmm0` | `48` | 64 |

and the same three prefix bytes with no displacement
(`62 f1 7c 08 28 00`, `62 f1 7c 28 28 00`, `62 f1 7c 48 28 00`) decode as
`vmovaps (%rax)` at `xmm`, `ymm` and `zmm`. The displaced and undisplaced
families agree that `P2` carries the width and nothing else in these encodings
changes.

The unit is therefore the vector width, which `ADR-0041` already fixed in the
row. But the unit cannot be *derived* from the operand list: the plan names a
row, and the row's `P2` is a definition byte the materializer writes, not a value
it may read back to choose a divisor (`INV-02`).

## 3. The range and the promotion boundary

`llvm-mc -disassemble` on `disp.txt`:

| Bytes | `llvm-mc -disassemble` | Content |
|---|---|---|
| `62 f1 7c 28 28 40 01` | `vmovaps 32(%rax), %ymm0` | `1` |
| `62 f1 7c 28 28 40 7f` | `vmovaps 4064(%rax), %ymm0` | `127` |
| `62 f1 7c 28 28 40 80` | `vmovaps -4096(%rax), %ymm0` | `-128` |
| `62 f1 7c 28 28 40 ff` | `vmovaps -32(%rax), %ymm0` | `-1` |
| `62 f1 7c 48 28 40 01` | `vmovaps 64(%rax), %zmm0` | `1` |
| `62 f1 7c 48 28 40 7f` | `vmovaps 8128(%rax), %zmm0` | `127` |
| `62 f1 7c 48 28 40 80` | `vmovaps -8192(%rax), %zmm0` | `-128` |
| `62 f1 7c 48 28 40 ff` | `vmovaps -64(%rax), %zmm0` | `-1` |
| `62 f1 7c 28 28 80 00 10 00 00` | `vmovaps 4096(%rax), %ymm0` | `disp32` |
| `62 f1 7c 48 28 80 00 20 00 00` | `vmovaps 8192(%rax), %zmm0` | `disp32` |

So the compressed slot holds `−128 … 127` at every width, and the byte offsets
it can express are `−4096 … 4064` at `N = 32` and `−8192 … 8128` at `N = 64`.
One past each end (`4096`, `8192`) is a ten-byte `disp32` row, and so is a value
the unit cannot divide (`28` at `N = 32`, `60` at `N = 64`). A plan that names
the compressed row with `128` is out of range; it is never silently re-formed as
`disp32` (`N03e`).

## 4. Reach and addressing carry over unchanged

| Bytes | `llvm-mc -disassemble` | What it shows |
|---|---|---|
| `62 41 7c 28 28 38` | `vmovaps (%r8), %ymm31` | `B̄` (bit 13), `R̄` (bit 15) and `R̄'` (bit 12) all carry a one in one instruction |
| `62 41 7c 28 28 78 01` | `vmovaps 32(%r8), %ymm31` | the same with `mod=01` and content `1` |
| `62 41 7c 48 28 28 38` | `vmovaps (%r8), %zmm31` | only `P2` differs from the `ymm` row |
| `62 41 7c 28 29 38` | `vmovaps %ymm31, (%r8)` | opcode 29 puts the stored register in `ModRM.reg` |

The base slot is the `0.10.0`/`0.12.0` four-bit window with the same
exclusions: `%rsp`/`%r12` on the displacement rows (`mod=01`/`10` needs a `SIB`
byte for them) and `%rsp`/`%rbp`/`%r12`/`%r13` on the `mod=00` rows (where
`r/m=101` is the RIP-relative escape). The vector slot is the `0.13.0` five-bit
one, so `ymm16`–`ymm31` and `zmm16`–`zmm31` reach without a longer instruction.

## 5. VEX.256 memory is a different mechanism, and it is not in the table

`llvm-mc -show-encoding` on `vex256.asm`:

| Source | Bytes | Length |
|---|---|---|
| `vmovaps (%rax), %ymm0` | `c5 fc 28 00` | 4 |
| `vmovaps 32(%rax), %ymm0` | `c5 fc 28 40 20` | 5 |
| `vmovaps 28(%rax), %ymm0` | `c5 fc 28 40 1c` | 5 |

VEX has no compressed displacement: `32` is the plain byte `0x20` and `28` is
`0x1c`, both `disp8` in the `0.9.0` sense. Adding these rows would add coverage,
not a contract fact (`EC-02`, `EC-35`, `EC-38` already cover it), so `0.15.0`
leaves them out and naming one is `E-FORM-001` (`N01al`).

## 6. The oracle

`P19.asm` is twenty-six `vmovaps` mnemonics and no hand-assembled bytes. The
source is 743 bytes, SHA-256
`a66fc88cb310ea2c79e871fd042c3ede9edd1f9d75f61324df52560e575f2278`. `.text` is
192 bytes, SHA-256
`407f90f137a16d8edcf193017ea24f68b0c4ec3a34323521524a2d8a654c107c`, and the plan
emits no fixup record.

`fixture_p19.py` transcribes the source into
`X86-P19-sse-ymm-zmm-memory.fmp.json` one instruction per line, so the plan and
the oracle describe the same bytes and the offsets are computed rather than
typed. The fixture covers all twelve new rows: the no-displacement pair, the
`disp8*N` pair at all four extreme field contents (`1`, `-1`, `127`, `-128`),
the `disp32` pair with one value the unit cannot divide and one value just past
the compressed range, and the `r8` + `ymm31`/`zmm31` combination.

## 7. The rejections

- `N01ak` names `x86:vmovaps/ymm-base-disp8x32/evex` against `0.14.0`:
  `E-FORM-001`. The version boundary.
- `N01al` names `x86:vmovaps/ymm-base-disp8/vex` against `0.15.0`:
  `E-FORM-001`. VEX.256 memory has no row at any version.
- `N02o` passes a `zmm` operand to `x86:vmovaps/ymm-base-disp8x32/evex`:
  `E-OPERAND-001` on both `kind` and `target_type`. Width is part of the kind on
  memory rows too.
- `N02p` passes a `disp8x16` displacement to the `disp8x32` row:
  `E-OPERAND-001` on the `disp`'s `target_type`. The value `1` would be a legal
  field content under the wrong unit, so the unit has to be compared, not
  inferred.
- `N03e` passes content `128` to the `disp8x32` row: `E-RANGE-001`,
  `min = -128`, `max = 127`. The compressed field does not grow with `N`.
- `N14r` passes `ymm32` to the `disp8x32` row: `E-OPERAND-004`,
  `field_bits = 5`. The EVEX field end is the same at every width.

## 8. What this does not claim

- EVEX masking, broadcast, `{z}`, `{rn-sae}`, the `vvvv`/`V'` carrier, and the
  tuple types that are not Full Vector (half/quarter/scalar and their `N`) are
  absent. Only the shapes `0.13.0` carried for `xmm` exist at 256/512 bits.
- Legacy and VEX memory at `ymm`/`zmm` width: legacy has no width field, and VEX
  memory is measured in §5 but deliberately not added.
- `movapd`, `movups`, `vmovdqa`, `vmovdqu` and every mnemonic other than
  `movaps`/`vmovaps` remain absent.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
