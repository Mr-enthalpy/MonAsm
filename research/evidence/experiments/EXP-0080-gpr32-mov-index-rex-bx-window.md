# EXP-0080 -- the 32-bit `mov` index rows with the `REX.BX` window

- Date: 2026-11-07
- Question: what does the `REX.BX` window cost on the 32-bit indexed `mov`,
  where both memory operands are extended at once?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.51.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P55-gpr32-mov-index-rex-bx-window.oracle.json`
- Source: `research/evidence/experiments/EXP-0080/probe.asm`
- Decision: `ADR-0078`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%r8,%r9,1), %eax` | `43 8b 44 08 08` | 5 |
| `movl %eax, 8(%r8,%r9,1)` | `43 89 44 08 08` | 5 |
| `movl 200(%r8,%r9,1), %eax` | `43 8b 84 08 c8 00 00 00` | 8 |
| `movl %eax, 200(%r8,%r9,1)` | `43 89 84 08 c8 00 00 00` | 8 |
| `movl 8(%r12,%r12,1), %eax` | `43 8b 44 24 08` | 5 |
| `movl 8(%r15,%r15,8), %edi` | `43 8b 7c ff 08` | 5 |
| `movl 8(%r8,%r12,1), %eax` | `43 8b 44 20 08` | 5 |
| `movl 8(%r12,%r9,1), %eax` | `43 8b 44 0c 08` | 5 |
| `movl 8(%r8,%r9,8), %eax` | `43 8b 44 c8 08` | 5 |
| `movl %edi, 8(%r10,%r11,2)` | `43 89 7c 5a 08` | 5 |

`llvm-mc -disassemble` on `probes.txt` returns all ten byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `REX` | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|
| `BX`, `disp8` | `43 8b 44 08 08` | `43` at byte 0 (`B = 1` at `[0,1]`, `X = 1` at `[1,1]`) | byte 1 | `44` at byte 2 (`mod = 01`, `reg = 0`, `r/m = 100`) | byte 3: scale `0`, index `1`, base `0` | `[32,8]` |
| `BX`, x8 | `43 8b 7c ff 08` | `43` | byte 1 | `7c` (`mod = 01`, `reg = 7`) | `ff`: scale `3` (`x8`), index `7`, base `7` | `[32,8]` |
| `BX`, store x2 | `43 89 7c 5a 08` | `43` | byte 1 | `7c` (`reg = 7`) | `5a`: scale `1` (`x2`), index `3`, base `2` | `[32,8]` |
| `BX`, `disp32` | `43 8b 84 08 c8 00 00 00` | `43` | byte 1 | `84` (`mod = 10`) | `08` | `[32,32]` |

The prefix byte at 0 keeps the `0.50.0` geometry: `ModRM` at byte 2, so the
register is `[19,3]` and the whole `SIB` byte sits at `[24,32)`: base `[24,3]`,
index `[27,3]`, scale `[30,2]`. The displacement follows at `[32,8]` or
`[32,32]`. Both memory slots list their `REX` bit as the most significant
placement, so `8`–`15` write the bit and the low three field bits; `0`–`7` are
excluded because they would clear it. The register stays three bits, so `8`–`15`
is `E-OPERAND-004`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%rax,%rsp,1), %eax` | rejected | -- | `%rsp` is not an index (`invalid base+index expression`) |
| `movl 8(%rax,%r9,1), %eax` | `42 8b 44 08 08` | 5 | the `REX.X` row |
| `movl 8(%r8,%rcx,1), %eax` | `41 8b 44 08 08` | 5 | the `REX.B` row |
| `movl 8(%rax,%rcx,1), %eax` | `8b 44 08 08` | 4 | the `REX`-less row |
| `movl 8(%rax,%rcx,1), %r8d` | `44 8b 44 08 08` | 5 | the `REX.R` row |
| `movl 8(%r12,%r12,1), %r8d` | `47 8b 44 24 08` | 5 | the `REX.RBX` row (deferred) |
| `movl 8(%r8,%r9,1), %r8d` | `47 8b 44 08 08` | 5 | `REX.RBX` with low field bits |
| `movl 8(%rax,%rcx,1), %r16d` | `d5 40 8b 44 08 08` | 6 | the APX `d5` window |
| `movq 8(%r8,%r9,1), %rax` | `4b 8b 44 08 08` | 5 | the 64-bit sibling (`REX.W` + `REX.BX`) |
| `movl 8(%r13,%r9,1), %eax` | `43 8b 44 0d 08` | 5 | `%r13` as a base (`SIB.base = 101`) |
| `movl 8(%r8,%r13,1), %eax` | `43 8b 44 28 08` | 5 | `%r13` as an index (`SIB.index = 101`) |
| `movl 8(%rsp,%r9,1), %eax` | `42 8b 44 0c 08` | 5 | `%rsp` as a base behind `REX.X` |

`adjacent-encoding.txt` records the eleven accepted lines and the assembler
diagnostic for the `%rsp` index.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dd` | names `x86:mov/r32-base-ext-index-ext-disp8/legacy` against `0.50.0` | `E-FORM-001` |
| `N01de` | names `x86:mov/base-ext-index-ext-disp8-r32/legacy` against `0.50.0` | `E-FORM-001` |
| `N02bu` | drops the `index` from the load row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03zd` | scale `4` on the load row, past the two-bit field | `E-RANGE-001` |
| `N14bk` | register `8` on the load row (the register stays low) | `E-OPERAND-004` |
| `N16cg` | base `3` on the load row, below the window | `E-RANGE-004` |
| `N16ch` | index `3` on the load row, below the window | `E-RANGE-004` |

The claims the ADR turns on: both memory slots are four-bit slots whose top bit
is a fixed `REX` bit, so a low value must be rejected rather than clear it; and
the register is still a three-bit field, so `8` is `E-OPERAND-004` and belongs
to a different row.

## 5. The fixture

`X86-P55-gpr32-mov-index-rex-bx-window` is ten instructions and 56 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%r8,%r9,1), %eax` | `43 8b 44 08 08` | 5 |
| 2 | `movl %eax, 8(%r8,%r9,1)` | `43 89 44 08 08` | 5 |
| 3 | `movl 200(%r8,%r9,1), %eax` | `43 8b 84 08 c8 00 00 00` | 8 |
| 4 | `movl %eax, 200(%r8,%r9,1)` | `43 89 84 08 c8 00 00 00` | 8 |
| 5 | `movl 8(%r12,%r12,1), %eax` | `43 8b 44 24 08` | 5 |
| 6 | `movl 8(%r15,%r15,8), %edi` | `43 8b 7c ff 08` | 5 |
| 7 | `movl 8(%r8,%r12,1), %eax` | `43 8b 44 20 08` | 5 |
| 8 | `movl 8(%r12,%r9,1), %eax` | `43 8b 44 0c 08` | 5 |
| 9 | `movl 8(%r8,%r9,8), %eax` | `43 8b 44 c8 08` | 5 |
| 10 | `movl %edi, 8(%r10,%r11,2)` | `43 89 7c 5a 08` | 5 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`db74d0de338ae505089df4b8e496aa2c6ee35a91d6c20844e590a6f26bf03f7a`
(`probe.asm`) and its `output_sha256` is
`1f0301f410a6a72ae4786bd6803ba9911ce8a1dde075d79ab744913a61c91fdb`
(the 56-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:e99d2bdb31d83a0ca14618e72a1928f252bf2482e99e206733d48bba48205198`.

`0.51.0` has 409 forms and the canonical digest
`sha256:e73395dffc494d13d0b142cbba0e4c55a40d19bcd68a6b793025156bbcb41bc5`.

## 6. What the slice defers

- The `REX.RBX` window on these rows, whose shapes are `47 8b 44 24 08` and
  `47 8b 44 08 08`.
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The APX `d5` register window, whose shape here is `d5 40 8b 44 08 08`.
- EVEX masking and broadcast on these rows.
