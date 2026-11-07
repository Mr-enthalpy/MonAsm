# EXP-0083 -- the single `REX` windows on the `0x67` 32-bit indexed `mov`

- Date: 2026-11-07
- Question: what does one `REX` bit cost after the `0x67` address-size prefix on
  the 32-bit indexed `mov`, and which operand does each bit extend?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.54.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P58-gpr32-mov-index-addr32-rex-windows.oracle.json`
- Source: `research/evidence/experiments/EXP-0083/probe.asm`
- Decision: `ADR-0081`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%eax,%ecx,1), %r8d` | `67 44 8b 44 08 08` | 6 |
| `movl %r8d, 8(%eax,%ecx,1)` | `67 44 89 44 08 08` | 6 |
| `movl 200(%eax,%ecx,1), %r8d` | `67 44 8b 84 08 c8 00 00 00` | 9 |
| `movl %r8d, 200(%eax,%ecx,1)` | `67 44 89 84 08 c8 00 00 00` | 9 |
| `movl 8(%r8d,%ecx,1), %eax` | `67 41 8b 44 08 08` | 6 |
| `movl %eax, 8(%r8d,%ecx,1)` | `67 41 89 44 08 08` | 6 |
| `movl 200(%r8d,%ecx,1), %eax` | `67 41 8b 84 08 c8 00 00 00` | 9 |
| `movl %eax, 200(%r8d,%ecx,1)` | `67 41 89 84 08 c8 00 00 00` | 9 |
| `movl 8(%eax,%r9d,1), %eax` | `67 42 8b 44 08 08` | 6 |
| `movl %eax, 8(%eax,%r9d,1)` | `67 42 89 44 08 08` | 6 |
| `movl 200(%eax,%r9d,1), %eax` | `67 42 8b 84 08 c8 00 00 00` | 9 |
| `movl %eax, 200(%eax,%r9d,1)` | `67 42 89 84 08 c8 00 00 00` | 9 |
| `movl 8(%r12d,%ecx,1), %eax` | `67 41 8b 44 0c 08` | 6 |
| `movl 8(%eax,%r12d,1), %eax` | `67 42 8b 44 20 08` | 6 |
| `movl 8(%ebp,%ecx,1), %r8d` | `67 44 8b 44 0d 08` | 6 |
| `movl 8(%r8d,%ecx,8), %eax` | `67 41 8b 44 c8 08` | 6 |

`llvm-mc -disassemble` on `probes.txt` returns all sixteen byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | Prefixes | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|
| `R`, `disp8` | `67 44 8b 44 08 08` | `67` at 0, `REX = 44` at 1 | byte 2 | `44` at byte 3 (`mod = 01`, `reg = 0`, `r/m = 100`) | byte 4: scale `0`, index `1`, base `0` | `[40,8]` |
| `B`, `disp8` | `67 41 8b 44 08 08` | `67`, `REX = 41` | byte 2 | `44` | `08` | `[40,8]` |
| `X`, `disp8` | `67 42 8b 44 08 08` | `67`, `REX = 42` | byte 2 | `44` | `08` | `[40,8]` |
| `R`, `disp32` | `67 44 8b 84 08 c8 00 00 00` | `67`, `REX = 44` | byte 2 | `84` (`mod = 10`) | `08` | `[40,32]` |
| `B`, x8 | `67 41 8b 44 c8 08` | `67`, `REX = 41` | byte 2 | `44` | `c8`: scale `3` (`x8`), index `1`, base `0` | `[40,8]` |
| `R`, `%ebp` base | `67 44 8b 44 0d 08` | `67`, `REX = 44` | byte 2 | `44` | `0d`: base `5` (`%ebp`) | `[40,8]` |

The two prefix bytes push the opcode to byte 2, so `ModRM` is byte 3 and `SIB`
byte 4: register `[27,3]`, base `[32,3]`, index `[35,3]`, scale `[38,2]`. The
`REX` byte sits at `[8,8)`: `R` at `[10,1]`, `X` at `[9,1]`, `B` at `[8,1]`.
Each single bit extends exactly one operand (`R` the value register, `B` the
base, `X` the index); the displacement follows at `[40,8]` or `[40,32]`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%eax,%esp,1), %eax` | rejected | -- | `%esp` is not an index |
| `movl 8(%r8d,%esp,1), %eax` | rejected | -- | `%esp` is not an index on an extended base either |
| `movl 8(%r8,%rcx,1), %eax` | `41 8b 44 08 08` | 5 | 64-bit addressing `REX.B`, no `0x67` |
| `movl 8(%rax,%r9,1), %eax` | `42 8b 44 08 08` | 5 | 64-bit addressing `REX.X` |
| `movl 8(%r8d,%r9d,1), %r8d` | `67 47 8b 44 08 08` | 6 | `0x67` + `REX.RBX` (deferred) |
| `movl 8(%eax,%ecx,1), %r8d` | `67 44 8b 44 08 08` | 6 | the `REX.R` row |
| `movl 8(%eax,%r9d,1), %r8d` | `67 46 8b 44 08 08` | 6 | `0x67` + `REX.RX` (deferred) |
| `movq 8(%r8d,%r9d,1), %rax` | `67 4b 8b 44 08 08` | 6 | `0x67` + `REX.WBX` (deferred) |
| `movq 8(%eax,%ecx,1), %rax` | `67 48 8b 44 08 08` | 6 | `0x67` + `REX.W` (deferred) |
| `movl 8(%r13d,%r13d,1), %r13d` | `67 47 8b 6c 2d 08` | 6 | `%r13d` on all three operands (deferred) |
| `movl 8(%edx,%ebx,2), %r8d` | `67 44 8b 44 5a 08` | 6 | `REX.R` with `%edx`/`%ebx` at x2 |
| `movl 8(%r8d,%ecx,1), %r8d` | `67 45 8b 44 08 08` | 6 | `0x67` + `REX.RB` (deferred) |

`adjacent-encoding.txt` records the ten accepted lines and the two assembler
diagnostics. The `REX` byte is a single byte between the two prefixes and the
opcode, so a second fixed bit needs its own row.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dj` | names `x86:mov/r32-ext-addr32-base-index-disp8/legacy` against `0.53.0` | `E-FORM-001` |
| `N01dk` | names `x86:mov/addr32-base-index-disp8-r32-ext/legacy` against `0.53.0` | `E-FORM-001` |
| `N02by` | drops the `index` from the `REX.B` row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03zg` | scale `4` on the `REX.X` row, past the two-bit field | `E-RANGE-001` |
| `N16cm` | value register `3` on the `REX.R` row, the excluded low window | `E-RANGE-004` |
| `N16cn` | base `3` on the `REX.B` row | `E-RANGE-004` |
| `N16co` | index `3` on the `REX.X` row | `E-RANGE-004` |
| `N14bn` | base `8` on the `REX.R` row, past its three-bit field | `E-OPERAND-004` |
| `N14bo` | index `8` on the `REX.B` row, past its three-bit field | `E-OPERAND-004` |

The claims the ADR turns on: `0x67` precedes `REX`, each single bit extends one
operand, the extended slot excludes the low window, and a value that would need
a second fixed bit is rejected rather than truncated.

## 5. The fixture

`X86-P58-gpr32-mov-index-addr32-rex-windows` is sixteen instructions and
114 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%eax,%ecx,1), %r8d` | `67 44 8b 44 08 08` | 6 |
| 2 | `movl %r8d, 8(%eax,%ecx,1)` | `67 44 89 44 08 08` | 6 |
| 3 | `movl 200(%eax,%ecx,1), %r8d` | `67 44 8b 84 08 c8 00 00 00` | 9 |
| 4 | `movl %r8d, 200(%eax,%ecx,1)` | `67 44 89 84 08 c8 00 00 00` | 9 |
| 5 | `movl 8(%r8d,%ecx,1), %eax` | `67 41 8b 44 08 08` | 6 |
| 6 | `movl %eax, 8(%r8d,%ecx,1)` | `67 41 89 44 08 08` | 6 |
| 7 | `movl 200(%r8d,%ecx,1), %eax` | `67 41 8b 84 08 c8 00 00 00` | 9 |
| 8 | `movl %eax, 200(%r8d,%ecx,1)` | `67 41 89 84 08 c8 00 00 00` | 9 |
| 9 | `movl 8(%eax,%r9d,1), %eax` | `67 42 8b 44 08 08` | 6 |
| 10 | `movl %eax, 8(%eax,%r9d,1)` | `67 42 89 44 08 08` | 6 |
| 11 | `movl 200(%eax,%r9d,1), %eax` | `67 42 8b 84 08 c8 00 00 00` | 9 |
| 12 | `movl %eax, 200(%eax,%r9d,1)` | `67 42 89 84 08 c8 00 00 00` | 9 |
| 13 | `movl 8(%r12d,%ecx,1), %eax` | `67 41 8b 44 0c 08` | 6 |
| 14 | `movl 8(%eax,%r12d,1), %eax` | `67 42 8b 44 20 08` | 6 |
| 15 | `movl 8(%ebp,%ecx,1), %r8d` | `67 44 8b 44 0d 08` | 6 |
| 16 | `movl 8(%r8d,%ecx,8), %eax` | `67 41 8b 44 c8 08` | 6 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`b3b59d90a7100e0c55122f7ba7064af04a5f568b772f12a60303e5785ef64156`
(`probe.asm`) and its `output_sha256` is
`5d3468e3a910c546df42118b42ea83e0cf5660c48ae45a2dcba41d8ac63c43ff`
(the 114-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:15dd75a2919675d5cbe07d3eed9f2f20341a67d98f46b75ddd250bab63360c1c`.

`0.54.0` has 429 forms and the canonical digest
`sha256:4513f6a9b15293f96bb79e46dbd477ea7cc051e3fb33a9a9ce3792e8ac6fa8cd`.

## 6. What the slice defers

- The two-bit `addr32` windows (`67 43`, `67 45`, `67 46`, `67 47`).
- The `0x67` `REX.W` siblings (`67 48`, `67 4c`, `67 4d`, `67 4f`).
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
