# EXP-0088 -- the `0x67 66` multi-bit `REX` windows on the 32-bit indexed `mov`

- Date: 2026-11-08
- Question: what do two (or three) `REX` bits cost after the `0x67 66` prefix
  pair, and where do the fixed bits sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.59.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P63-gpr16-mov-index-addr32-rex-two-bit-windows.oracle.json`
- Source: `research/evidence/experiments/EXP-0088/probe.asm`
- Decision: `ADR-0086`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-08. The sixteen rows are the
four multi-bit windows (`RB`, `RX`, `BX`, `RBX`) in both directions at both
displacement widths; the last four are the corners.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%r8d,%ecx,1), %r8w` | `67 66 45 8b 44 08 08` | 7 |
| `movw %r8w, 8(%r8d,%ecx,1)` | `67 66 45 89 44 08 08` | 7 |
| `movw 8(%eax,%r9d,1), %r8w` | `67 66 46 8b 44 08 08` | 7 |
| `movw %r8w, 8(%eax,%r9d,1)` | `67 66 46 89 44 08 08` | 7 |
| `movw 8(%r8d,%r9d,1), %ax` | `67 66 43 8b 44 08 08` | 7 |
| `movw %ax, 8(%r8d,%r9d,1)` | `67 66 43 89 44 08 08` | 7 |
| `movw 8(%r8d,%r9d,1), %r8w` | `67 66 47 8b 44 08 08` | 7 |
| `movw %r8w, 8(%r8d,%r9d,1)` | `67 66 47 89 44 08 08` | 7 |
| `movw 200(%r8d,%ecx,1), %r8w` | `67 66 45 8b 84 08 c8 00 00 00` | 10 |
| `movw %r8w, 200(%r8d,%ecx,1)` | `67 66 45 89 84 08 c8 00 00 00` | 10 |
| `movw 200(%eax,%r9d,1), %r8w` | `67 66 46 8b 84 08 c8 00 00 00` | 10 |
| `movw %r8w, 200(%eax,%r9d,1)` | `67 66 46 89 84 08 c8 00 00 00` | 10 |
| `movw 200(%r8d,%r9d,1), %ax` | `67 66 43 8b 84 08 c8 00 00 00` | 10 |
| `movw %ax, 200(%r8d,%r9d,1)` | `67 66 43 89 84 08 c8 00 00 00` | 10 |
| `movw 200(%r8d,%r9d,1), %r8w` | `67 66 47 8b 84 08 c8 00 00 00` | 10 |
| `movw %r8w, 200(%r8d,%r9d,1)` | `67 66 47 89 84 08 c8 00 00 00` | 10 |
| `movw 8(%r12d,%ecx,1), %r15w` | `67 66 45 8b 7c 0c 08` | 7 |
| `movw 8(%r12d,%r15d,1), %dx` | `67 66 43 8b 54 3c 08` | 7 |
| `movw 8(%r12d,%r13d,1), %r15w` | `67 66 47 8b 7c 2c 08` | 7 |
| `movw 8(%r8d,%r9d,8), %r8w` | `67 66 47 8b 44 c8 08` | 7 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

The geometry is the `0.58.0` geometry: `0x67` at byte 0, `0x66` at byte 1,
`REX` at byte 2, the opcode at byte 3, `ModRM` at byte 4 and `SIB` at byte 5.
The value register is `[35,3]`, the base `[40,3]`, the index `[43,3]`, the
scale `[46,2]` and the displacement `[48,8]` or `[48,32]`. The fixed bits are
`R` at `[18,1]`, `B` at `[16,1]` and `X` at `[17,1]`:

| Source | `REX` | `W` | `R` | `X` | `B` |
|---|---|---|---|---|---|
| `%r8w`, `%r8d`, `%ecx` | `45` | 0 | 1 | 0 | 1 |
| `%r8w`, `%eax`, `%r9d` | `46` | 0 | 1 | 1 | 0 |
| `%ax`, `%r8d`, `%r9d` | `43` | 0 | 0 | 1 | 1 |
| `%r8w`, `%r8d`, `%r9d` | `47` | 0 | 1 | 1 | 1 |

`RB` fixes `R` and `B`, `RX` fixes `R` and `X`, `BX` fixes `B` and `X`, and
`RBX` fixes all three. Because each extension bit is fixed by the row, the slot
it widens also carries a placement into that bit and excludes `0`–`7`. The
slots a row leaves low stay three bits; index `4` stays rejected unless
`REX.X = 1`, which names `%r12d`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%eax,%ecx,1), %ax` | `67 66 8b 44 08 08` | 6 | the bare pair (`0.57.0`) |
| `movw 8(%eax,%ecx,1), %r8w` | `67 66 44 8b 44 08 08` | 7 | `REX.R` (`0.58.0`) |
| `movw 8(%r8d,%ecx,1), %ax` | `67 66 41 8b 44 08 08` | 7 | `REX.B` (`0.58.0`) |
| `movw 8(%eax,%r9d,1), %ax` | `67 66 42 8b 44 08 08` | 7 | `REX.X` (`0.58.0`) |
| `movl 8(%r8d,%r9d,1), %r8d` | `67 47 8b 44 08 08` | 6 | the 32-bit value row, `REX.RBX` |
| `movw 8(%rax,%rcx,1), %ax` | `66 8b 44 08 08` | 5 | 64-bit addressing, no `0x67` |
| `movw 8(%r12d,%r12d,1), %r12w` | `67 66 47 8b 64 24 08` | 7 | index `4` needs `REX.X` |
| `movw 8(%esp,%ecx,1), %ax` | `67 66 8b 44 0c 08` | 6 | `%esp` as a base (`SIB.base = 100`) |
| `movw 8(%eax,%esp,1), %ax` | rejected | -- | `%esp` is not an index |
| `movw 8(%r8d,%r9d,1), %eax` | rejected | -- | value register must be 16-bit |

`adjacent-encoding.txt` records the eight accepted lines and the two assembler
diagnostics. The `%r12w`/`%r12d` line is `REX.RBX` (`47`), because index `4`
would mean "no index" without `REX.X`; the row model reaches it through the
`X` bit plus field `4`.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dt` | names `x86:mov/r16-ext-addr32-base-ext-index-disp8/legacy` against `0.58.0` | `E-FORM-001` |
| `N01du` | names `x86:mov/addr32-base-ext-index-disp8-r16-ext/legacy` against `0.58.0` | `E-FORM-001` |
| `N02cf` | drops the `index` from the `REX.RBX` row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N16cx` | value `0` on the `REX.RB` row, below its window floor | `E-RANGE-004` |
| `N16cy` | base `0` on the `REX.BX` row, below its window floor | `E-RANGE-004` |
| `N16cz` | index `0` on the `REX.RX` row, below its window floor | `E-RANGE-004` |
| `N03zl` | scale `4`, past the two-bit field | `E-RANGE-001` |
| `N14bw` | value register `16`, past the four-bit field | `E-OPERAND-004` |

The claims the ADR turns on: two (or three) fixed bits extend that many operands
at once without moving the geometry, and every widened slot rejects the low
registers rather than truncating them.

## 5. The fixture

`X86-P63-gpr16-mov-index-addr32-rex-two-bit-windows` is twenty instructions and
164 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%r8d,%ecx,1), %r8w` | `67 66 45 8b 44 08 08` | 7 |
| 2 | `movw %r8w, 8(%r8d,%ecx,1)` | `67 66 45 89 44 08 08` | 7 |
| 3 | `movw 8(%eax,%r9d,1), %r8w` | `67 66 46 8b 44 08 08` | 7 |
| 4 | `movw %r8w, 8(%eax,%r9d,1)` | `67 66 46 89 44 08 08` | 7 |
| 5 | `movw 8(%r8d,%r9d,1), %ax` | `67 66 43 8b 44 08 08` | 7 |
| 6 | `movw %ax, 8(%r8d,%r9d,1)` | `67 66 43 89 44 08 08` | 7 |
| 7 | `movw 8(%r8d,%r9d,1), %r8w` | `67 66 47 8b 44 08 08` | 7 |
| 8 | `movw %r8w, 8(%r8d,%r9d,1)` | `67 66 47 89 44 08 08` | 7 |
| 9 | `movw 200(%r8d,%ecx,1), %r8w` | `67 66 45 8b 84 08 c8 00 00 00` | 10 |
| 10 | `movw %r8w, 200(%r8d,%ecx,1)` | `67 66 45 89 84 08 c8 00 00 00` | 10 |
| 11 | `movw 200(%eax,%r9d,1), %r8w` | `67 66 46 8b 84 08 c8 00 00 00` | 10 |
| 12 | `movw %r8w, 200(%eax,%r9d,1)` | `67 66 46 89 84 08 c8 00 00 00` | 10 |
| 13 | `movw 200(%r8d,%r9d,1), %ax` | `67 66 43 8b 84 08 c8 00 00 00` | 10 |
| 14 | `movw %ax, 200(%r8d,%r9d,1)` | `67 66 43 89 84 08 c8 00 00 00` | 10 |
| 15 | `movw 200(%r8d,%r9d,1), %r8w` | `67 66 47 8b 84 08 c8 00 00 00` | 10 |
| 16 | `movw %r8w, 200(%r8d,%r9d,1)` | `67 66 47 89 84 08 c8 00 00 00` | 10 |
| 17 | `movw 8(%r12d,%ecx,1), %r15w` | `67 66 45 8b 7c 0c 08` | 7 |
| 18 | `movw 8(%r12d,%r15d,1), %dx` | `67 66 43 8b 54 3c 08` | 7 |
| 19 | `movw 8(%r12d,%r13d,1), %r15w` | `67 66 47 8b 7c 2c 08` | 7 |
| 20 | `movw 8(%r8d,%r9d,8), %r8w` | `67 66 47 8b 44 c8 08` | 7 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`71cf019c74e144e1b12aa8b341d8c04436e2242a140e2a8dccfe35b68d1f2562`
(`probe.asm`) and its `output_sha256` is
`97b087b42680dad549e22647d230be76772551a36144394d0014f82bb26b8a03`
(the 164-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:75f292493e1a037d9daff8a7e0bfb4f502dfa385150a685f6cc1a76b80171ddc`.

`0.59.0` has 481 forms and the canonical digest
`sha256:bf7e54f512d27e83a3834b95ec4dc75767ee86d619ec833dee2a7cf13637826f`.

## 6. What the slice defers

- The `REX.W` siblings after the `0x67 66` pair (`67 66 48`–`67 66 4f`).
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
- A 64-bit address register with `0x67`.
