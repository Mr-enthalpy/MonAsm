# EXP-0082 -- the `0x67` address-size prefix on the 32-bit indexed `mov`

- Date: 2026-11-07
- Question: what does the `0x67` address-size prefix cost on the
  `REX`-less 32-bit indexed `mov`, where the base and index become 32-bit
  address registers?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.53.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P57-gpr32-mov-index-addr32-window.oracle.json`
- Source: `research/evidence/experiments/EXP-0082/probe.asm`
- Decision: `ADR-0080`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%eax,%ecx,1), %eax` | `67 8b 44 08 08` | 5 |
| `movl %eax, 8(%eax,%ecx,1)` | `67 89 44 08 08` | 5 |
| `movl 200(%eax,%ecx,1), %eax` | `67 8b 84 08 c8 00 00 00` | 8 |
| `movl %eax, 200(%eax,%ecx,1)` | `67 89 84 08 c8 00 00 00` | 8 |
| `movl 8(%esp,%ecx,1), %eax` | `67 8b 44 0c 08` | 5 |
| `movl 8(%ebp,%ecx,1), %eax` | `67 8b 44 0d 08` | 5 |
| `movl 8(%edi,%esi,4), %edi` | `67 8b 7c b7 08` | 5 |
| `movl 8(%eax,%ecx,8), %eax` | `67 8b 44 c8 08` | 5 |
| `movl -8(%eax,%ecx,1), %eax` | `67 8b 44 08 f8` | 5 |
| `movl 8(%edx,%ebx,2), %eax` | `67 8b 44 5a 08` | 5 |

`llvm-mc -disassemble` on `probes.txt` returns all ten byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | Prefix | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|
| `addr32`, `disp8` | `67 8b 44 08 08` | `67` at byte 0 | byte 1 | `44` at byte 2 (`mod = 01`, `reg = 0`, `r/m = 100`) | byte 3: scale `0`, index `1`, base `0` | `[32,8]` |
| `addr32`, x4 | `67 8b 7c b7 08` | `67` | byte 1 | `7c` (`mod = 01`, `reg = 7`) | `b7`: scale `2` (`x4`), index `6`, base `7` | `[32,8]` |
| `addr32`, x8 | `67 8b 44 c8 08` | `67` | byte 1 | `44` | `c8`: scale `3` (`x8`), index `1`, base `0` | `[32,8]` |
| `addr32`, negative | `67 8b 44 08 f8` | `67` | byte 1 | `44` | `08`: scale `0`, index `1`, base `0` | `[32,8]` = `-8` |
| `addr32`, `disp32` | `67 8b 84 08 c8 00 00 00` | `67` | byte 1 | `84` (`mod = 10`) | `08` | `[32,32]` |

The prefix byte at 0 pushes the opcode to byte 1, so `ModRM` is byte 2 and the
whole `SIB` byte sits at `[24,32)`: base `[24,3]`, index `[27,3]`, scale
`[30,2]`. The value register is `[19,3]` and the displacement follows at
`[32,8]` or `[32,32]`. This is the `0.51.0` geometry with `0x67` in place of
the `REX` byte; the base and index name `%eax`–`%edi`, not `%rax`–`%rdi`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%eax,%esp,1), %eax` | rejected | -- | `%esp` is not an index (`invalid base+index expression`) |
| `movl 8(%rax,%rcx,1), %eax` | `8b 44 08 08` | 4 | 64-bit addressing, no prefix |
| `movl 8(%r8d,%r9d,1), %r8d` | `67 47 8b 44 08 08` | 6 | `0x67` then `REX.RBX` (deferred) |
| `movl 8(%eax,%ecx,1), %r8d` | `67 44 8b 44 08 08` | 6 | `0x67` then `REX.R` (deferred) |
| `movl 8(%r8,%rcx,1), %eax` | `41 8b 44 08 08` | 5 | 64-bit addressing `REX.B` |
| `movl 8(%esp), %eax` | `67 8b 44 24 08` | 5 | `%esp` base without an index (`SIB.base = 100`) |
| `movl 8(%eax), %eax` | `67 8b 40 08` | 5 | bare `%eax` base, no `SIB` |
| `movl 8(%r12d,%r12d,1), %r8d` | `67 47 8b 44 24 08` | 6 | `0x67` + `REX.RBX` on `%r12d` |
| `movl 8(%eax,%ebp,1), %eax` | `67 8b 44 28 08` | 5 | `%ebp` is a legal index (`SIB.index = 101`) |
| `movq 8(%eax,%ecx,1), %rax` | `67 48 8b 44 08 08` | 6 | `0x67` then `REX.W` (deferred) |
| `movl 8(%r13d,%r13d,1), %r13d` | `67 47 8b 6c 2d 08` | 6 | `%r13d` on all three operands |

`adjacent-encoding.txt` records the ten accepted lines and the assembler
diagnostic for the `%esp` index. The measurement pins the prefix order:
`0x67` precedes any `REX` byte (`67 47 ...`), so an `addr32` `REX` window is a
new form and not an operand value.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dh` | names `x86:mov/r32-addr32-base-index-disp8/legacy` against `0.52.0` | `E-FORM-001` |
| `N01di` | names `x86:mov/addr32-base-index-disp8-r32/legacy` against `0.52.0` | `E-FORM-001` |
| `N02bw` | drops the `index` from the load row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N02bx` | base is `x86.gpr64`/`rm64` instead of `x86.gpr32`/`rm32` | `E-OPERAND-001` (kind and target_type) |
| `N03zf` | scale `4` on the load row, past the two-bit field | `E-RANGE-001` |
| `N16cl` | index `4` on the load row, the "no index" encoding | `E-RANGE-004` |
| `N14bl` | base `8` on the load row, past the three-bit field | `E-OPERAND-004` |
| `N14bm` | index `8` on the load row, past the three-bit field | `E-OPERAND-004` |

The claims the ADR turns on: `0x67` is a form byte, the base and index are
32-bit address registers (`x86.gpr32`, three bits), and a value that would
need the deferred `REX` window is rejected rather than truncated.

## 5. The fixture

`X86-P57-gpr32-mov-index-addr32-window` is ten instructions and 56 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%eax,%ecx,1), %eax` | `67 8b 44 08 08` | 5 |
| 2 | `movl %eax, 8(%eax,%ecx,1)` | `67 89 44 08 08` | 5 |
| 3 | `movl 200(%eax,%ecx,1), %eax` | `67 8b 84 08 c8 00 00 00` | 8 |
| 4 | `movl %eax, 200(%eax,%ecx,1)` | `67 89 84 08 c8 00 00 00` | 8 |
| 5 | `movl 8(%esp,%ecx,1), %eax` | `67 8b 44 0c 08` | 5 |
| 6 | `movl 8(%ebp,%ecx,1), %eax` | `67 8b 44 0d 08` | 5 |
| 7 | `movl 8(%edi,%esi,4), %edi` | `67 8b 7c b7 08` | 5 |
| 8 | `movl 8(%eax,%ecx,8), %eax` | `67 8b 44 c8 08` | 5 |
| 9 | `movl -8(%eax,%ecx,1), %eax` | `67 8b 44 08 f8` | 5 |
| 10 | `movl 8(%edx,%ebx,2), %eax` | `67 8b 44 5a 08` | 5 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`206a660a1b1acbccdafc5578ff400fc9abbd3be7397f1e08b3fa1b3066dc9df2`
(`probe.asm`) and its `output_sha256` is
`1aa6ee42b4f922df655eb5d2258f4ed887b3b3f42c7caf294533889f8dc7c96f`
(the 56-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:f6f222c98b065fe9081e45854a623dc3359d60359db8726a7766f0ada9dafcf9`.

`0.53.0` has 417 forms and the canonical digest
`sha256:9c4c913f51e0e74710f416cd03d1547e6d4af4f2b678c1f1c4ae46f5722ff52b`.

## 6. What the slice defers

- The `0x67`+`REX` windows (`67 47 8b 44 08 08`, `67 44 8b 44 08 08`).
- `%r8d`–`%r15d` as base or index.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
