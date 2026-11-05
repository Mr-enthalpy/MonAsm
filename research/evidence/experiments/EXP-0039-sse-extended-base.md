# EXP-0039 — the SSE base at `r8`–`r15`, and inverted extension bits

- Date: 2026-11-05
- Question: how do the legacy, VEX and EVEX families encode a `movaps` /
  `vmovaps` memory operand whose base is `r8`–`r15`, and what changes in the
  prefix when the base crosses the three-bit boundary?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.10.0.json`
  (`sha256:0c10ff1c373eea2fe6098e67da3047081b34a5779d9ec492c47069ac73613442`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P14-sse-base-ext.oracle.json`
- Source: `research/evidence/experiments/EXP-0039/P14.asm`
- Probe: `research/evidence/experiments/EXP-0039/P14probe.asm`
- Decision: `ADR-0037`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. `{evex}` forces the EVEX
family; without it `llvm-mc` emits VEX for `vmovaps` at `xmm` width.

| Source | Bytes | Family |
|---|---|---|
| `movaps 8(%r8), %xmm0` | `41 0f 28 40 08` | legacy load, `disp8` |
| `movaps 128(%r15), %xmm1` | `41 0f 28 8f 80 00 00 00` | legacy load, `disp32` |
| `movaps %xmm2, 8(%r9)` | `41 0f 29 51 08` | legacy store, `disp8` |
| `movaps %xmm3, 128(%r10)` | `41 0f 29 9a 80 00 00 00` | legacy store, `disp32` |
| `vmovaps 8(%r8), %xmm4` | `c4 c1 78 28 60 08` | VEX load, `disp8` |
| `vmovaps 128(%r15), %xmm5` | `c4 c1 78 28 af 80 00 00 00` | VEX load, `disp32` |
| `vmovaps %xmm6, 8(%r11)` | `c4 c1 78 29 73 08` | VEX store, `disp8` |
| `vmovaps %xmm7, 128(%r13)` | `c4 c1 78 29 bd 80 00 00 00` | VEX store, `disp32` |
| `{evex} vmovaps 16(%r8), %xmm0` | `62 d1 7c 08 28 40 01` | EVEX load, content `1` |
| `{evex} vmovaps -16(%r14), %xmm1` | `62 d1 7c 08 28 4e ff` | EVEX load, content `-1` |
| `{evex} vmovaps 2032(%r15), %xmm2` | `62 d1 7c 08 28 57 7f` | EVEX load, content `127` |
| `{evex} vmovaps 8(%r8), %xmm3` | `62 d1 7c 08 28 98 08 00 00 00` | EVEX load, `disp32` |
| `{evex} vmovaps %xmm4, 16(%r9)` | `62 d1 7c 08 29 61 01` | EVEX store, content `1` |
| `{evex} vmovaps %xmm5, 8(%r15)` | `62 d1 7c 08 29 af 08 00 00 00` | EVEX store, `disp32` |

The base is still `ModRM.rm` and the `xmm` register is still `ModRM.reg`; what
changes is the prefix byte in front of the opcode.

## 2. Legacy and VEX grow a byte; EVEX does not

| Probe | Bytes | Length | What it shows |
|---|---|---|---|
| `movaps 8(%rax), %xmm0` | `0f 28 40 08` | 4 | no `REX` needed |
| `movaps 8(%r8), %xmm0` | `41 0f 28 40 08` | 5 | `REX.B = 1`, one byte longer |
| `vmovaps 8(%rax), %xmm0` | `c5 f8 28 40 08` | 5 | two-byte VEX, no `B` |
| `vmovaps 8(%r8), %xmm0` | `c4 c1 78 28 40 08` | 6 | three-byte VEX, one byte longer |
| `{evex} vmovaps 16(%rax), %xmm0` | `62 f1 7c 08 28 40 01` | 7 | `P0 = f1` |
| `{evex} vmovaps 16(%r8), %xmm0` | `62 d1 7c 08 28 40 01` | 7 | `P0 = d1`, same length |

In the legacy family the `REX` byte is `0x40` plus `REX.B` at bit 0, so
`8(%r8)` is `(0x40 | 1) 0f 28 40 08`. In three-byte VEX the `B̄` bit is bit 5 of
the second prefix byte, and it is active-low: `c1` has `B̄ = 0` (extension on)
while `e1` has `B̄ = 1` (no extension). EVEX is the same active-low rule at
bit 13 of `P0`: `d1` has `B̄ = 0`, `f1` has `B̄ = 1`.

## 3. Polarity is not optional

Disassembling the four candidate byte strings settles what a raw fourth bit
would do:

| Bytes | `llvm-mc -disassemble` | Comment |
|---|---|---|
| `40 0f 28 40 08` | `movaps 8(%rax), %xmm0` | redundant `REX` is the same instruction |
| `41 0f 28 40 08` | `movaps 8(%r8), %xmm0` | the extension bit is observable |
| `c4 e1 78 28 40 08` | `vmovaps 8(%rax), %xmm0` | `B̄ = 1` |
| `c4 c1 78 28 40 08` | `vmovaps 8(%r8), %xmm0` | `B̄ = 0` |
| `62 f1 7c 08 28 40 01` | `vmovaps 16(%rax), %xmm0` | `B̄ = 1` |
| `62 d1 7c 08 28 40 01` | `vmovaps 16(%r8), %xmm0` | `B̄ = 0` |

Writing base bit 3 raw into bit 13 of `P0` therefore turns `(%r8)` into
`(%rax)`: a well-formed, legal instruction for the wrong operand. The
definition has to say that the chunk is complemented, and the materializer must
not know which family it is writing. That is `placement.invert`
(`EC-40`).

The legacy `40` prefix also shows why the window cannot be a value test even
though the length is the only difference: `40 0f 28 40 08` is not an error, it
is `8(%rax)`. A single row that wrote the extension bit raw whenever the base
was high would still emit the low-base bytes for the low base, but accepting
both values in one row would make a legal instruction (the redundant `REX`
form) unreachable by the definition and the plan, and it would leave the choice
of template to an operand value (`INV-04`). Hence two disjoint rows.

## 4. `%r12` and `xmm8` stay out

| Probe | Bytes | Why it is absent |
|---|---|---|
| `movaps 8(%r12), %xmm0` | `41 0f 28 44 24 08` | `r/m = 100` forces a `SIB` byte (`24`) |
| `vmovaps 8(%r12), %xmm0` | `c4 c1 78 28 44 24 08` | same `SIB` |
| `{evex} vmovaps 8(%r12), %xmm0` | `62 d1 7c 08 28 84 24 08 00 00 00` | same `SIB`, then `disp32` |
| `movaps 8(%r8), %xmm8` | `45 0f 28 40 08` | needs `REX.R` as well as `REX.B` |
| `vmovaps 8(%r8), %xmm8` | `c4 41 78 28 40 08` | inverted `R̄ = 0` |
| `{evex} vmovaps 16(%r8), %xmm8` | `62 51 7c 08 28 40 01` | inverted `R̄ = 0` |

`%r12` is excluded from both windows (`E-RANGE-004`), exactly as `%rsp` is, and
the `SIB` shape is still not a form under these opcodes. `xmm8` would add a
second extension bit to every family, and in legacy it would multiply the
window count by four (`REX.R` × `REX.B`); it is deferred to its own slice,
which landed as `ADR-0038` / `EXP-0040`.

`8(%r9)` and `-8(%r10)`/`-16(%r10)` were also measured as ordinary bases:
`41 0f 28 41 08`, `c4 c1 78 28 41 08`, `62 d1 7c 08 28 81 08 00 00 00` (EVEX
`disp32` because `8` is not a multiple of `16`), `41 0f 28 7a f8`,
`c4 c1 78 28 7a f8` and `62 d1 7c 08 28 7a ff`.

## 5. The oracle

`P14.asm` is fourteen `movaps`/`vmovaps` mnemonics, with `{evex}` on the six
EVEX lines; no hand-assembled bytes. The source is 383 bytes, SHA-256
`d8d716fe3306ac484d18b71f2faa74695c2069204cdba1b876b6d599d063c231`. `.text`
is 104 bytes, SHA-256
`c03acc3809baafc002afcb8ce8e1c2604080b11f309fd554d199b1f625a9b940`, and the
plan emits no fixup record. The fixture's expected bytes are this `.text`.

The sizes are 5, 8, 5, 8 (legacy), 6, 9, 6, 9 (VEX), 7, 7, 7, 10, 7, 10 (EVEX);
every one matches the row the plan names, and no instruction relies on a
promotion the materializer would have to make.

## 6. The rejections

- `N01af` names `x86:movaps/xmm-base-ext-disp8/legacy` against `0.9.0`:
  `E-FORM-001`. The extension row is a `0.10.0` form.
- `N14h` passes base `16` to the 4-bit window: `E-OPERAND-004`,
  `field_bits = 4`. The fifth bit does not exist.
- `N16k` passes base `0` (`rax`) to an extension row: `E-RANGE-004`,
  `excluded = [0…7, 12]`. The low base names a low row.
- `N16l` passes `%r12` to an extension row: `E-RANGE-004`; `%r12` still forces
  a `SIB` byte that no SSE row carries.
- The `0.9.0` negatives stay valid: `N14f` and `N14g` still pass `r8` to a
  3-bit base in that version (`E-OPERAND-004`), and `N14e` still pins `xmm8`.

## 7. What this does not claim

- `xmm8`–`xmm15` are not encoded by these rows; the `xmm` slot is still three
  bits.
- A `SIB` base under these opcodes (`%rsp`, `%r12` with `r/m = 100`),
  `mod = 00` memory operands, EVEX masking, `ymm`/`zmm`, `movapd`'s `0x66`
  form and the 8/16-bit SSE width are absent.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
