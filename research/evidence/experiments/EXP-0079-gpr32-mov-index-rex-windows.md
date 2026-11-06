# EXP-0079 -- the 32-bit `mov` index rows with one `REX` extension bit

- Date: 2026-11-07
- Question: what do the `REX.R`, `REX.B` and `REX.X` windows cost on the 32-bit
  indexed `mov`, and where do `ModRM`, `SIB` and the displacement sit once the
  prefix byte appears?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.50.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P54-gpr32-mov-index-rex-windows.oracle.json`
- Source: `research/evidence/experiments/EXP-0079/probe.asm`
- Decision: `ADR-0077`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%rax,%rcx,1), %r8d` | `44 8b 44 08 08` | 5 |
| `movl %r8d, 8(%rax,%rcx,1)` | `44 89 44 08 08` | 5 |
| `movl 200(%rax,%rcx,1), %r8d` | `44 8b 84 08 c8 00 00 00` | 8 |
| `movl %r8d, 200(%rax,%rcx,1)` | `44 89 84 08 c8 00 00 00` | 8 |
| `movl 8(%r8,%rcx,1), %eax` | `41 8b 44 08 08` | 5 |
| `movl %eax, 8(%r8,%rcx,1)` | `41 89 44 08 08` | 5 |
| `movl 200(%r8,%rcx,1), %eax` | `41 8b 84 08 c8 00 00 00` | 8 |
| `movl %eax, 200(%r8,%rcx,1)` | `41 89 84 08 c8 00 00 00` | 8 |
| `movl 8(%rax,%r9,1), %eax` | `42 8b 44 08 08` | 5 |
| `movl %eax, 8(%rax,%r9,1)` | `42 89 44 08 08` | 5 |
| `movl 200(%rax,%r9,1), %eax` | `42 8b 84 08 c8 00 00 00` | 8 |
| `movl %eax, 200(%rax,%r9,1)` | `42 89 84 08 c8 00 00 00` | 8 |
| `movl 8(%r12,%rcx,1), %eax` | `41 8b 44 0c 08` | 5 |
| `movl %eax, 8(%rax,%r12,1)` | `42 89 44 20 08` | 5 |
| `movl 8(%rsp,%rcx,1), %r8d` | `44 8b 44 0c 08` | 5 |

`llvm-mc -disassemble` on `probes.txt` returns all fifteen byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `REX` | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|
| `R`, `disp8` | `44 8b 44 08 08` | `44` at byte 0 (`R = 1` at `[2,1]`) | byte 1 | `44` at byte 2 (`mod = 01`, `reg = 0` at `[19,3]`, `r/m = 100`) | byte 3: scale `[30,2] = 0`, index `[27,3] = 1`, base `[24,3] = 0` | `[32,8]` |
| `R`, high | `44 8b 7c b7 08` | `44` | byte 1 | `7c` (`mod = 01`, `reg = 7`) | `b7`: scale `2` (`x4`), index `6`, base `7` | `[32,8]` |
| `B`, `disp8` | `41 8b 44 08 08` | `41` at byte 0 (`B = 1` at `[0,1]`) | byte 1 | `44` at byte 2 | `08` | `[32,8]` |
| `B`, `%r12` base | `41 8b 44 0c 08` | `41` | byte 1 | `44` | `0c`: base `100` | `[32,8]` |
| `X`, `disp8` | `42 8b 44 08 08` | `42` at byte 0 (`X = 1` at `[1,1]`) | byte 1 | `44` at byte 2 | `08` | `[32,8]` |
| `X`, `%r12` index | `42 89 44 20 08` | `42` | byte 1 | `44` | `20`: index `100`, base `0` | `[32,8]` |
| `R`, `disp32` | `44 8b 84 08 c8 00 00 00` | `44` | byte 1 | `84` (`mod = 10`) | `08` | `[32,32]` |
| `B`, `disp32` | `41 8b 84 08 c8 00 00 00` | `41` | byte 1 | `84` | `08` | `[32,32]` |

The prefix byte at 0 pushes `ModRM` to byte 2, so the register is `[19,3]` and
the whole `SIB` byte sits at `[24,32)`: base `[24,3]`, index `[27,3]`, scale
`[30,2]`. The displacement follows at `[32,8]` or `[32,32]`, one byte later
than the `REX`-less `0.49.0` rows. The extended operand's slot lists the fixed
`REX` bit as its most significant placement, so `8`–`15` write the bit and the
low three field bits; `0`–`7` are excluded because they would clear it.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%rax,%rsp,1), %eax` | rejected | -- | `%rsp` is not an index (`invalid base+index expression`) |
| `movl 8(%rdi,%rsi,4), %r15d` | `44 8b 7c b7 08` | 5 | the `REX.R` upper register with the x4 scale |
| `movl %r15d, 8(%rdi,%rsi,4)` | `44 89 7c b7 08` | 5 | the store direction |
| `movl 8(%r13,%rsi,1), %eax` | `41 8b 44 35 08` | 5 | `%r13` as a base behind `REX.B` |
| `movl 8(%rbp,%rsi,1), %eax` | `8b 44 35 08` | 4 | `%rbp` is a base on the `REX`-less row, not the `REX.B` row |
| `movl 8(%r12,%r13,1), %eax` | `43 8b 44 2c 08` | 5 | the `REX.BX` window (deferred) |
| `movl 8(%r8,%r9,1), %eax` | `43 8b 44 08 08` | 5 | the `REX.BX` window with the low field bits |
| `movl 8(%rax,%rcx,1), %r16d` | `d5 40 8b 44 08 08` | 6 | the APX `d5` window |
| `movq 8(%rax,%rcx,1), %r8` | `4c 8b 44 08 08` | 5 | the 64-bit sibling (`REX.W` + `REX.R`) |
| `movl 8(%rax,%rcx,1), %eax` | `8b 44 08 08` | 4 | the `REX`-less `0.49.0` row |
| `movl 8(%rax), %r8d` | `44 8b 40 08` | 4 | the no-index `REX.R` row |
| `movl 8(%r8), %eax` | `41 8b 40 08` | 4 | the no-index `REX.B` row |

`adjacent-encoding.txt` records the eleven accepted lines and the assembler
diagnostic for the `%rsp` index.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01db` | names `x86:mov/r32-ext-base-index-disp8/legacy` against `0.49.0` | `E-FORM-001` |
| `N01dc` | names `x86:mov/base-ext-index-disp8-r32/legacy` against `0.49.0` | `E-FORM-001` |
| `N02bt` | drops the `index` from the `REX.R` load row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03zc` | scale `4` on the `REX.R` load row, past the two-bit field | `E-RANGE-001` |
| `N14bi` | register `8` on the `REX.B` store row (the register stays low) | `E-OPERAND-004` |
| `N14bj` | base `8` on the `REX.X` store row (the base stays low) | `E-OPERAND-004` |
| `N16cd` | register `3` on the `REX.R` row, below the window | `E-RANGE-004` |
| `N16ce` | base `3` on the `REX.B` row, below the window | `E-RANGE-004` |
| `N16cf` | index `3` on the `REX.X` row, below the window | `E-RANGE-004` |

The claims the ADR turns on: each window slot is a four-bit slot whose top bit
is the fixed `REX` bit, so a low value must be rejected rather than clear it;
and the operands that the row keeps low are still three-bit fields, so `8` is
`E-OPERAND-004` and belongs to a different row.

## 5. The fixture

`X86-P54-gpr32-mov-index-rex-windows` is fifteen instructions and 93 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%rax,%rcx,1), %r8d` | `44 8b 44 08 08` | 5 |
| 2 | `movl %r8d, 8(%rax,%rcx,1)` | `44 89 44 08 08` | 5 |
| 3 | `movl 200(%rax,%rcx,1), %r8d` | `44 8b 84 08 c8 00 00 00` | 8 |
| 4 | `movl %r8d, 200(%rax,%rcx,1)` | `44 89 84 08 c8 00 00 00` | 8 |
| 5 | `movl 8(%r8,%rcx,1), %eax` | `41 8b 44 08 08` | 5 |
| 6 | `movl %eax, 8(%r8,%rcx,1)` | `41 89 44 08 08` | 5 |
| 7 | `movl 200(%r8,%rcx,1), %eax` | `41 8b 84 08 c8 00 00 00` | 8 |
| 8 | `movl %eax, 200(%r8,%rcx,1)` | `41 89 84 08 c8 00 00 00` | 8 |
| 9 | `movl 8(%rax,%r9,1), %eax` | `42 8b 44 08 08` | 5 |
| 10 | `movl %eax, 8(%rax,%r9,1)` | `42 89 44 08 08` | 5 |
| 11 | `movl 200(%rax,%r9,1), %eax` | `42 8b 84 08 c8 00 00 00` | 8 |
| 12 | `movl %eax, 200(%rax,%r9,1)` | `42 89 84 08 c8 00 00 00` | 8 |
| 13 | `movl 8(%r12,%rcx,1), %eax` | `41 8b 44 0c 08` | 5 |
| 14 | `movl %eax, 8(%rax,%r12,1)` | `42 89 44 20 08` | 5 |
| 15 | `movl 8(%rsp,%rcx,1), %r8d` | `44 8b 44 0c 08` | 5 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`6e15ae95cec1673e538c2b3721bd29c58085ea1fd046a8fd3d53bc6d2dc145d9`
(`probe.asm`) and its `output_sha256` is
`fcb2ccc6befba68d9be798a9dc73afb8e25f8ae059beb70b04917bb2b42c2e26`
(the 93-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:d8429016d9ac7d7c4cd1622ad6d234587e03f748243792f6a316cbca103596ea`.

`0.50.0` has 405 forms and the canonical digest
`sha256:6f38e272ef1464b5067053c7a10d744adee19699fbe4ecbc0928fb3c8f7da75a`.

## 6. What the slice defers

- The `REX.BX` window on these rows, whose shapes are `43 8b 44 08 08` and
  `43 8b 44 2c 08`.
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The APX `d5` register window, whose shape here is `d5 40 8b 44 08 08`.
