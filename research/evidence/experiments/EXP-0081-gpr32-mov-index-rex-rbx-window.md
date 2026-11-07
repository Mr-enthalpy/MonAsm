# EXP-0081 -- the 32-bit `mov` index rows with the `REX.RBX` window

- Date: 2026-11-07
- Question: what does the `REX.RBX` window cost on the 32-bit indexed `mov`,
  where the register, the base and the index are all extended at once?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.52.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P56-gpr32-mov-index-rex-rbx-window.oracle.json`
- Source: `research/evidence/experiments/EXP-0081/probe.asm`
- Decision: `ADR-0079`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%r8,%r9,1), %r8d` | `47 8b 44 08 08` | 5 |
| `movl %r8d, 8(%r8,%r9,1)` | `47 89 44 08 08` | 5 |
| `movl 200(%r8,%r9,1), %r8d` | `47 8b 84 08 c8 00 00 00` | 8 |
| `movl %r8d, 200(%r8,%r9,1)` | `47 89 84 08 c8 00 00 00` | 8 |
| `movl 8(%r12,%r12,1), %r8d` | `47 8b 44 24 08` | 5 |
| `movl 8(%r15,%r15,8), %r15d` | `47 8b 7c ff 08` | 5 |
| `movl 8(%r8,%r12,1), %r8d` | `47 8b 44 20 08` | 5 |
| `movl 8(%r12,%r9,1), %r8d` | `47 8b 44 0c 08` | 5 |
| `movl 8(%r8,%r9,8), %r8d` | `47 8b 44 c8 08` | 5 |
| `movl %r15d, 8(%r10,%r11,2)` | `47 89 7c 5a 08` | 5 |

`llvm-mc -disassemble` on `probes.txt` returns all ten byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `REX` | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|
| `RBX`, `disp8` | `47 8b 44 08 08` | `47` at byte 0 (`R = 1` at `[2,1]`, `X = 1` at `[1,1]`, `B = 1` at `[0,1]`) | byte 1 | `44` at byte 2 (`mod = 01`, `reg = 0`, `r/m = 100`) | byte 3: scale `0`, index `1`, base `0` | `[32,8]` |
| `RBX`, x8 | `47 8b 7c ff 08` | `47` | byte 1 | `7c` (`mod = 01`, `reg = 7`) | `ff`: scale `3` (`x8`), index `7`, base `7` | `[32,8]` |
| `RBX`, store x2 | `47 89 7c 5a 08` | `47` | byte 1 | `7c` (`reg = 7`) | `5a`: scale `1` (`x2`), index `3`, base `2` | `[32,8]` |
| `RBX`, `disp32` | `47 8b 84 08 c8 00 00 00` | `47` | byte 1 | `84` (`mod = 10`) | `08` | `[32,32]` |

The prefix byte at 0 keeps the `0.50.0` geometry: `ModRM` at byte 2, so the
register is `[2,1]`+`[19,3]` and the whole `SIB` byte sits at `[24,32)`: base
`[0,1]`+`[24,3]`, index `[1,1]`+`[27,3]`, scale `[30,2]`. The displacement
follows at `[32,8]` or `[32,32]`. All three register slots list their `REX` bit
as the most significant placement, so `8`–`15` write the bit and the low three
field bits; `0`–`7` are excluded because they would clear it.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%rax,%rsp,1), %eax` | rejected | -- | `%rsp` is not an index (`invalid base+index expression`) |
| `movl 8(%r8,%r9,1), %eax` | `43 8b 44 08 08` | 5 | the `REX.BX` row (`0.51.0`) |
| `movl 8(%rax,%rcx,1), %r8d` | `44 8b 44 08 08` | 5 | the `REX.R` row (`0.50.0`) |
| `movl 8(%rax,%rcx,1), %eax` | `8b 44 08 08` | 4 | the `REX`-less row (`0.49.0`) |
| `movq 8(%r8,%r9,1), %r8` | `4f 8b 44 08 08` | 5 | the 64-bit `REX.W` + `REX.RBX` sibling |
| `movl 8(%rax,%rcx,1), %r16d` | `d5 40 8b 44 08 08` | 6 | the APX `d5` window |
| `movl 8(%r13,%r13,1), %r13d` | `47 8b 6c 2d 08` | 5 | `%r13` on all three operands |
| `movq 8(%r8,%r9,1), %rax` | `4b 8b 44 08 08` | 5 | the 64-bit `REX.W` + `REX.BX` sibling |
| `movl 8(%r13,%r9,1), %r8d` | `47 8b 44 0d 08` | 5 | `%r13` as a base (`SIB.base = 101`) |
| `movl 8(%r8,%r13,1), %r8d` | `47 8b 44 28 08` | 5 | `%r13` as an index (`SIB.index = 101`) |
| `movl 8(%rsp,%r9,1), %r8d` | `46 8b 44 0c 08` | 5 | `%rsp` as a base behind `REX.RX` |
| `movl %r12d, 8(%r12,%r12,1)` | `47 89 64 24 08` | 5 | `%r12` on all three operands |

`adjacent-encoding.txt` records the eleven accepted lines and the assembler
diagnostic for the `%rsp` index.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01df` | names `x86:mov/r32-ext-base-ext-index-ext-disp8/legacy` against `0.51.0` | `E-FORM-001` |
| `N01dg` | names `x86:mov/base-ext-index-ext-disp8-r32-ext/legacy` against `0.51.0` | `E-FORM-001` |
| `N02bv` | drops the `index` from the load row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03ze` | scale `4` on the load row, past the two-bit field | `E-RANGE-001` |
| `N16ci` | register `3` on the load row, below the window | `E-RANGE-004` |
| `N16cj` | base `3` on the load row, below the window | `E-RANGE-004` |
| `N16ck` | index `3` on the load row, below the window | `E-RANGE-004` |

The claims the ADR turns on: one `REX` byte can fix all three extension bits,
so every register slot is a four-bit slot whose top bit is fixed, and a low
value must be rejected rather than clear it; the row's geometry and length are
otherwise the same as `0.51.0`'s.

## 5. The fixture

`X86-P56-gpr32-mov-index-rex-rbx-window` is ten instructions and 56 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%r8,%r9,1), %r8d` | `47 8b 44 08 08` | 5 |
| 2 | `movl %r8d, 8(%r8,%r9,1)` | `47 89 44 08 08` | 5 |
| 3 | `movl 200(%r8,%r9,1), %r8d` | `47 8b 84 08 c8 00 00 00` | 8 |
| 4 | `movl %r8d, 200(%r8,%r9,1)` | `47 89 84 08 c8 00 00 00` | 8 |
| 5 | `movl 8(%r12,%r12,1), %r8d` | `47 8b 44 24 08` | 5 |
| 6 | `movl 8(%r15,%r15,8), %r15d` | `47 8b 7c ff 08` | 5 |
| 7 | `movl 8(%r8,%r12,1), %r8d` | `47 8b 44 20 08` | 5 |
| 8 | `movl 8(%r12,%r9,1), %r8d` | `47 8b 44 0c 08` | 5 |
| 9 | `movl 8(%r8,%r9,8), %r8d` | `47 8b 44 c8 08` | 5 |
| 10 | `movl %r15d, 8(%r10,%r11,2)` | `47 89 7c 5a 08` | 5 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`c55c54a7a0287415f1712f131f530ec706520f6288458e74e6ed5fbc94b58aeb`
(`probe.asm`) and its `output_sha256` is
`80f2ca77ca8cc154d476e9170861b2ec803be8e32edde00781296863602ff1cc`
(the 56-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:0f5aa5afd1ec7adf8d5e43e9ef12ae6ee222c35d95e070a0f12e3b38c0d15811`.

`0.52.0` has 413 forms and the canonical digest
`sha256:4587b149e1119681ffefe011862343d8bccd0f52dbe7d278a0afb05517f7f7ae`.

## 6. What the slice defers

- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The APX `d5` register window, whose shape here is `d5 40 8b 44 08 08`.
- EVEX masking and broadcast on these rows.
- The `REX.RBX` rows for the 16-bit family.
