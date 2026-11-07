# EXP-0087 -- the `0x67 66` single-`REX` windows on the 32-bit indexed `mov`

- Date: 2026-11-07
- Question: what does one `REX` bit cost after the `0x67 66` prefix pair, and
  where does the `REX` byte sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.58.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P62-gpr16-mov-index-addr32-rex-windows.oracle.json`
- Source: `research/evidence/experiments/EXP-0087/probe.asm`
- Decision: `ADR-0085`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07. The twelve rows are the
three single-`REX` windows in both directions at both displacement widths.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%eax,%ecx,1), %r8w` | `67 66 44 8b 44 08 08` | 7 |
| `movw %r8w, 8(%eax,%ecx,1)` | `67 66 44 89 44 08 08` | 7 |
| `movw 8(%r8d,%ecx,1), %ax` | `67 66 41 8b 44 08 08` | 7 |
| `movw %ax, 8(%r8d,%ecx,1)` | `67 66 41 89 44 08 08` | 7 |
| `movw 8(%eax,%r9d,1), %ax` | `67 66 42 8b 44 08 08` | 7 |
| `movw %ax, 8(%eax,%r9d,1)` | `67 66 42 89 44 08 08` | 7 |
| `movw 200(%eax,%ecx,1), %r8w` | `67 66 44 8b 84 08 c8 00 00 00` | 10 |
| `movw %r8w, 200(%eax,%ecx,1)` | `67 66 44 89 84 08 c8 00 00 00` | 10 |
| `movw 200(%r8d,%ecx,1), %ax` | `67 66 41 8b 84 08 c8 00 00 00` | 10 |
| `movw %ax, 200(%r8d,%ecx,1)` | `67 66 41 89 84 08 c8 00 00 00` | 10 |
| `movw 200(%eax,%r9d,1), %ax` | `67 66 42 8b 84 08 c8 00 00 00` | 10 |
| `movw %ax, 200(%eax,%r9d,1)` | `67 66 42 89 84 08 c8 00 00 00` | 10 |
| `movw 8(%ebp,%ecx,1), %r15w` | `67 66 44 8b 7c 0d 08` | 7 |
| `movw 8(%r15d,%ebp,1), %dx` | `67 66 41 8b 54 2f 08` | 7 |
| `movw 8(%eax,%r15d,1), %dx` | `67 66 42 8b 54 38 08` | 7 |
| `movw 8(%eax,%ecx,8), %r15w` | `67 66 44 8b 7c c8 08` | 7 |

`llvm-mc -disassemble` on `probes.txt` returns all sixteen byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

The geometry extends the `0.57.0` geometry by one byte: `0x67` at byte 0,
`0x66` at byte 1, `REX` at byte 2, the opcode at byte 3, `ModRM` at byte 4 and
`SIB` at byte 5. The value register is `[35,3]`, the base `[40,3]`, the index
`[43,3]`, the scale `[46,2]` and the displacement `[48,8]` or `[48,32]`. The
fixed bit is `R` at `[18,1]`, `B` at `[16,1]` or `X` at `[17,1]`:

| Source | `REX` | `W` | `R` | `X` | `B` |
|---|---|---|---|---|---|
| `%r8w`, `%eax`, `%ecx` | `44` | 0 | 1 | 0 | 0 |
| `%ax`, `%r8d`, `%ecx` | `41` | 0 | 0 | 0 | 1 |
| `%ax`, `%eax`, `%r9d` | `42` | 0 | 0 | 1 | 0 |
| `%r15w`, `%ebp`, `%ecx` | `44` | 0 | 1 | 0 | 0 |
| `%dx`, `%r15d`, `%ebp` | `41` | 0 | 0 | 0 | 1 |
| `%dx`, `%eax`, `%r15d` | `42` | 0 | 0 | 1 | 0 |

Because the extension bit is fixed by the row, the slot it widens also carries
a placement into that bit (`[18,1]`, `[16,1]` or `[17,1]`) and excludes `0`–`7`.
The other slots stay three bits; index `4` stays rejected.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%eax,%ecx,1), %ax` | `67 66 8b 44 08 08` | 6 | the bare pair (`0.57.0`) |
| `movl 8(%r8d,%r9d,1), %r8d` | `67 47 8b 44 08 08` | 6 | the 32-bit value row, `REX.RBX` |
| `movw 8(%rax,%rcx,1), %ax` | `66 8b 44 08 08` | 5 | 64-bit addressing, no `0x67` |
| `movw 8(%r12d,%ecx,1), %r12w` | `67 66 45 8b 64 0c 08` | 7 | `REX.RB`, a two-bit window (deferred) |
| `movw 8(%esp,%ecx,1), %ax` | `67 66 8b 44 0c 08` | 6 | `%esp` as a base (`SIB.base = 100`) |
| `movw 8(%eax,%esp,1), %ax` | rejected | -- | `%esp` is not an index |
| `movw 8(%eax,%ecx,1), %eax` | rejected | -- | value register must be 16-bit |

`adjacent-encoding.txt` records the five accepted lines and the two assembler
diagnostics. `%r12w` with `%r12d` fixing two bits at once is the next slice; a
single-bit row cannot express it.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dr` | names `x86:mov/r16-ext-addr32-base-index-disp8/legacy` against `0.57.0` | `E-FORM-001` |
| `N01ds` | names `x86:mov/addr32-base-index-disp8-r16-ext/legacy` against `0.57.0` | `E-FORM-001` |
| `N02ce` | drops the `index` from the `REX.R` row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N16cu` | value `0` on the `REX.R` row, below its window floor | `E-RANGE-004` |
| `N16cv` | base `0` on the `REX.B` row, below its window floor | `E-RANGE-004` |
| `N16cw` | index `0` on the `REX.X` row, below its window floor | `E-RANGE-004` |
| `N03zk` | scale `4`, past the two-bit field | `E-RANGE-001` |
| `N14bv` | value register `16`, past the four-bit field | `E-OPERAND-004` |

The claims the ADR turns on: the `REX` byte sits at position 2 after the
`0x67 66` pair, one fixed bit opens exactly one window, and the slot that the
bit widens rejects the low registers rather than truncating them.

## 5. The fixture

`X86-P62-gpr16-mov-index-addr32-rex-windows` is sixteen instructions and 130
bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%eax,%ecx,1), %r8w` | `67 66 44 8b 44 08 08` | 7 |
| 2 | `movw %r8w, 8(%eax,%ecx,1)` | `67 66 44 89 44 08 08` | 7 |
| 3 | `movw 8(%r8d,%ecx,1), %ax` | `67 66 41 8b 44 08 08` | 7 |
| 4 | `movw %ax, 8(%r8d,%ecx,1)` | `67 66 41 89 44 08 08` | 7 |
| 5 | `movw 8(%eax,%r9d,1), %ax` | `67 66 42 8b 44 08 08` | 7 |
| 6 | `movw %ax, 8(%eax,%r9d,1)` | `67 66 42 89 44 08 08` | 7 |
| 7 | `movw 200(%eax,%ecx,1), %r8w` | `67 66 44 8b 84 08 c8 00 00 00` | 10 |
| 8 | `movw %r8w, 200(%eax,%ecx,1)` | `67 66 44 89 84 08 c8 00 00 00` | 10 |
| 9 | `movw 200(%r8d,%ecx,1), %ax` | `67 66 41 8b 84 08 c8 00 00 00` | 10 |
| 10 | `movw %ax, 200(%r8d,%ecx,1)` | `67 66 41 89 84 08 c8 00 00 00` | 10 |
| 11 | `movw 200(%eax,%r9d,1), %ax` | `67 66 42 8b 84 08 c8 00 00 00` | 10 |
| 12 | `movw %ax, 200(%eax,%r9d,1)` | `67 66 42 89 84 08 c8 00 00 00` | 10 |
| 13 | `movw 8(%ebp,%ecx,1), %r15w` | `67 66 44 8b 7c 0d 08` | 7 |
| 14 | `movw 8(%r15d,%ebp,1), %dx` | `67 66 41 8b 54 2f 08` | 7 |
| 15 | `movw 8(%eax,%r15d,1), %dx` | `67 66 42 8b 54 38 08` | 7 |
| 16 | `movw 8(%eax,%ecx,8), %r15w` | `67 66 44 8b 7c c8 08` | 7 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`6cb55296b64d9feb165ea29494c81f0ae12a798cfceb98ff85105689b31fdb97`
(`probe.asm`) and its `output_sha256` is
`9c31d3fb894e21378df7f4abc8bda1ce4a9c9717b2b2281231d4dd2832cb608f`
(the 130-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:1d0ae87aec3a30c94850257edf941b5f2252948bc84e675add0d64550fd9cf97`.

`0.58.0` has 465 forms and the canonical digest
`sha256:8e7fc7e799ede398cb5d560b2ca43991c11cba518cadae45f84222bbf93994bf`.

## 6. What the slice defers

- The two-bit and three-bit `0x67 66` `REX` windows (`%r12w` with `%r12d` is
  `67 66 45 8b 64 0c 08`).
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
- A 64-bit address register with `0x67`.
