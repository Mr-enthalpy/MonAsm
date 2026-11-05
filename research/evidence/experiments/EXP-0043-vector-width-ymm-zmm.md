# EXP-0043 — vector width as a form fact, `ymm` and `zmm`

- Date: 2026-11-05
- Question: which prefix field carries the vector width, is width independent
  of the register number, which families can express which widths, and does a
  wider register change the instruction length?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.14.0.json`
  (`sha256:3126af72d83ec4ee8e0e34abfde924a73e7b41866fb2c3b8fc3152821d691a5b`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P18-sse-ymm-zmm.oracle.json`
- Source: `research/evidence/experiments/EXP-0043/P18.asm`
- Decision: `ADR-0041`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. The mnemonic is the same
in every row; only the register name and, where forced, the `{evex}` directive
differ:

| Source | Bytes | Length |
|---|---|---|
| `vmovaps %ymm1, %ymm0` | `c5 fc 28 c1` | 4 |
| `vmovaps %ymm0, %ymm8` | `c5 7c 28 c0` | 4 |
| `vmovaps %ymm7, %ymm15` | `c5 7c 28 ff` | 4 |
| `vmovaps %ymm8, %ymm0` | `c5 7c 29 c0` | 4 |
| `vmovaps %ymm15, %ymm7` | `c5 7c 29 ff` | 4 |
| `vmovaps %ymm8, %ymm8` | `c4 41 7c 28 c0` | 5 |
| `vmovaps %ymm15, %ymm14` | `c4 41 7c 28 f7` | 5 |
| `{evex} vmovaps %ymm1, %ymm0` | `62 f1 7c 28 28 c1` | 6 |
| `vmovaps %ymm16, %ymm0` | `62 b1 7c 28 28 c0` | 6 |
| `vmovaps %ymm0, %ymm31` | `62 61 7c 28 28 f8` | 6 |
| `vmovaps %ymm30, %ymm31` | `62 01 7c 28 28 fe` | 6 |
| `vmovaps %zmm1, %zmm0` | `62 f1 7c 48 28 c1` | 6 |
| `vmovaps %zmm8, %zmm0` | `62 d1 7c 48 28 c0` | 6 |
| `vmovaps %zmm16, %zmm0` | `62 b1 7c 48 28 c0` | 6 |
| `vmovaps %zmm0, %zmm31` | `62 61 7c 48 28 f8` | 6 |
| `vmovaps %zmm31, %zmm30` | `62 01 7c 48 28 f7` | 6 |

## 2. Width is one prefix field: `L` and `L'L`

`llvm-mc -disassemble` on raw byte strings (one line of `0x`-prefixed bytes per
case), holding the operands at `%ymm0`/`%zmm0` so only the prefix varies:

| Bytes | `llvm-mc -disassemble` | What changed |
|---|---|---|
| `c5 fc 28 c0` | `vmovaps %ymm0, %ymm0` | VEX `L = 1` |
| `c5 f8 28 c0` | `vmovaps %xmm0, %xmm0` | VEX `L = 0` (the `0.5.0` row) |
| `62 f1 7c 28 28 c0` | `vmovaps %ymm0, %ymm0` | EVEX `L'L = 10` |
| `62 f1 7c 08 28 c0` | `vmovaps %xmm0, %xmm0` | EVEX `L'L = 00` (the `0.5.0` row) |
| `62 f1 7c 48 28 c0` | `vmovaps %zmm0, %zmm0` | EVEX `L'L = 11` |

The VEX width is bit 2 of the second prefix byte (`fc` vs `f8`); the EVEX width
is bits 1–0 of `P2` (`28`/`08`/`48`). Every other prefix bit is identical, so
the width is a prefix field, not an operand value or a register property.

## 3. Width is independent of the register number

The three `P2` values on the same `31/30` operand pair:

| Bytes | `llvm-mc -disassemble` |
|---|---|
| `62 01 7c 28 28 f7` | `vmovaps %ymm31, %ymm30` |
| `62 01 7c 08 28 f7` | `vmovaps %xmm31, %xmm30` |
| `62 01 7c 48 28 f7` | `vmovaps %zmm31, %zmm30` |

Only `P2` changes, so the fifth register bit of `0.13.0` (`R̄'`/`X̄`/`R̄`/`B̄`)
carries over unchanged into the wider rows. A wider register is not a wider
register field.

## 4. The VEX.256 windows repeat the `0.11.0` `xmm` windows

`llvm-mc -disassemble` on the candidate bytes:

| Bytes | `llvm-mc -disassemble` | Meaning |
|---|---|---|
| `c5 78 28 c0` | `vmovaps %xmm0, %xmm8` | VEX.128, `R̄ = 0` gives the destination bit 3 |
| `c5 7c 28 c0` | `vmovaps %ymm0, %ymm8` | VEX.256, same `R̄` placement |
| `c5 7c 29 c0` | `vmovaps %ymm8, %ymm0` | opcode 29 puts the high source in `ModRM.reg` |
| `c4 41 7c 28 c0` | `vmovaps %ymm8, %ymm8` | three-byte `C4`, both registers high |
| `c4 41 7c 28 c8` | `vmovaps %ymm8, %ymm9` | same, distinct register numbers |

The low/low row keeps a two-byte prefix because the destination's fourth bit is
already in the inverted `R̄`. A high source with a low destination stays in two
bytes through opcode 29, and only both-high needs the three-byte `C4`. This is
the same set of windows `0.11.0` added for `xmm`, with `L` set; the table pins
the four-byte opcode-29 form so two implementations cannot differ in length
(`INV-02`).

## 5. The family limits

`llvm-mc` rejects the combinations the encoding cannot express:

| Source | Result |
|---|---|
| `movaps %ymm0, %ymm1` | `error: invalid operand for instruction` |
| `{vex} vmovaps %zmm1, %zmm0` | `error: unsupported instruction` |
| `{vex} vmovaps %ymm16, %ymm0` | `error: unsupported instruction` |
| `vmovaps %ymm32, %ymm0` | `error: invalid register name` |
| `vmovaps %zmm32, %zmm0` | `error: invalid register name` |

Legacy `movaps` has no width field at all, `zmm` exists only under EVEX, and a
two-byte VEX has only four register bits. `ymm` therefore has both VEX.256 and
EVEX.256 forms, exactly like `xmm`; `zmm` has only EVEX.512. An operand outside
the form's window is `E-OPERAND-001` (wrong width kind) or `E-OPERAND-004`
(register number past the field).

The memory shapes are measured but deliberately **not** added to `0.14.0`:

| Source | Bytes | Length |
|---|---|---|
| `vmovaps (%rax), %ymm16` | `62 e1 7c 28 28 00` | 6 |
| `vmovaps 32(%rax), %ymm16` | `62 e1 7c 28 28 40 01` | 7 |
| `vmovaps 28(%rax), %ymm16` | `62 e1 7c 28 28 80 1c 00 00 00` | 10 |

`32` is one `disp8*32` unit and `28` is not, so the compressed displacement
unit depends on the width (`EC-39` currently fixes `N = 16`). Adding these rows
would revise `EC-39` and is a separate slice; naming one now is `E-FORM-001`.

## 6. The oracle

`P18.asm` is sixteen `vmovaps` mnemonics and no hand-assembled bytes. The source
is 371 bytes, SHA-256
`d0569ae96453eaf03960133e234c052c2a02b3757f53b9040f656a7124408814`. `.text` is
84 bytes, SHA-256
`41953bb371c2cbf0ef82dcef923d97463a7b8e8ce993f4505d7cec3aea0cd088`, and the plan
emits no fixup record.

The fixture fills every new window in both directions: the three VEX.256 windows
(low/low with a high destination, opcode 29 with a high source, `C4` with both
high), the EVEX.256 row at `0`, `16`, `30` and `31`, and the EVEX.512 row at the
same values. Each instruction keeps the length of its family (4/4/5 for VEX, 6
for EVEX), so the wider register costs no byte.

## 7. The rejections

- `N01ai` names `x86:vmovaps/ymm-ymm/vex` against `0.13.0`: `E-FORM-001`. The
  version boundary.
- `N01aj` names `x86:movaps/ymm-ymm/legacy` against `0.14.0`: `E-FORM-001`.
  Legacy has no width field, so there is no such row at any version.
- `N02n` passes a `zmm` operand to `x86:vmovaps/ymm-ymm/evex`:
  `E-OPERAND-001` on both `kind` and `target_type`. Width is part of the kind.
- `N14p` passes `ymm16` to `x86:vmovaps/ymm-ymm/vex`: `E-OPERAND-004`,
  `field_bits = 4`. The VEX family boundary.
- `N14q` passes `zmm32` to `x86:vmovaps/zmm-zmm/evex`: `E-OPERAND-004`,
  `field_bits = 5`. The EVEX field end.

## 8. What this does not claim

- Memory forms at `ymm`/`zmm` width, EVEX masking and broadcast, and the
  `EVEX.vvvv`/`V'` carrier are still absent.
- `movapd`'s `0x66` form, `movups`, `vmovdqa`, and every mnemonic other than
  `movaps`/`vmovaps` remain absent.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
