# EXP-0078 -- the 32-bit `mov` family with a `SIB` index and no prefix byte

- Date: 2026-11-07
- Question: what does the 32-bit `mov` index/scale shape cost where there is no
  `REX` byte at all, and where do `ModRM`, `SIB` and the displacement sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.49.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P53-gpr32-mov-index-low.oracle.json`
- Source: `research/evidence/experiments/EXP-0078/probe.asm`
- Decision: `ADR-0076`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%rax,%rcx,1), %eax` | `8b 44 08 08` | 4 |
| `movl 8(%rdi,%rsi,4), %edi` | `8b 7c b7 08` | 4 |
| `movl %eax, 8(%rax,%rcx,1)` | `89 44 08 08` | 4 |
| `movl %edi, 8(%rdi,%rsi,4)` | `89 7c b7 08` | 4 |
| `movl 8(%rsp,%rcx,1), %eax` | `8b 44 0c 08` | 4 |
| `movl 8(%rbp,%rsi,1), %eax` | `8b 44 35 08` | 4 |
| `movl %eax, 8(%rsp,%rcx,1)` | `89 44 0c 08` | 4 |
| `movl 200(%rax,%rcx,1), %eax` | `8b 84 08 c8 00 00 00` | 7 |
| `movl 200(%rdi,%rsi,4), %edi` | `8b bc b7 c8 00 00 00` | 7 |
| `movl %eax, 200(%rax,%rcx,1)` | `89 84 08 c8 00 00 00` | 7 |
| `movl 200(%rsp,%rcx,1), %eax` | `8b 84 0c c8 00 00 00` | 7 |
| `movl %eax, 200(%rbp,%rsi,1)` | `89 84 35 c8 00 00 00` | 7 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|
| `disp8` | `8b 44 08 08` | byte 0 | `44` at byte 1 (`mod = 01`, `reg = 0` at `[11,3]`, `r/m = 100`) | byte 2: scale `[22,2] = 0`, index `[19,3] = 1`, base `[16,3] = 0` | `[24,8]` |
| `disp8`, high | `8b 7c b7 08` | byte 0 | `7c` (`mod = 01`, `reg = 7`) | `b7`: scale `2` (`x4`), index `6`, base `7` | `[24,8]` |
| `disp8`, `%rsp` base | `8b 44 0c 08` | byte 0 | `44` | `0c`: scale `0`, index `1`, base `100` | `[24,8]` |
| `disp8`, `%rbp` base | `8b 44 35 08` | byte 0 | `44` | `35`: scale `0`, index `6`, base `101` | `[24,8]` |
| `disp32` | `8b 84 08 c8 00 00 00` | byte 0 | `84` (`mod = 10`, `r/m = 100`) | `08` | `[24,32]` |
| `disp32`, `%rsp` base | `8b 84 0c c8 00 00 00` | byte 0 | `84` | `0c` | `[24,32]` |

With no prefix byte, `ModRM` is byte 1, so the register is `[11,3]` and the
whole `SIB` byte sits at `[16,24)`: scale `[22,2]`, index `[19,3]`, base
`[16,3]`. The displacement follows the `SIB` byte at `[24,8]` or `[24,32]`,
one byte earlier than the `0x66`-prefixed 16-bit rows and two earlier than the
`REX`-carrying 64-bit rows. The register, base and index fields are three bits
each; only the index excludes a value (`4`, the "no index" encoding).

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%rax,%rsp,1), %eax` | rejected | -- | `%rsp` is not an index (`invalid base+index expression`) |
| `movl 8(%rax,%rcx,1), %r8d` | `44 8b 44 08 08` | 5 | the `REX.R` register window |
| `movl 8(%r8,%rcx,1), %eax` | `41 8b 44 08 08` | 5 | the `REX.B` base window |
| `movl 8(%rax,%r9,1), %eax` | `42 8b 44 08 08` | 5 | the `REX.X` index window |
| `movl 8(%r8,%r9,1), %eax` | `43 8b 44 08 08` | 5 | the `REX.BX` window |
| `movl 8(%r12,%rcx,1), %eax` | `41 8b 44 0c 08` | 5 | `SIB.base = 100` behind `REX.B` (`%r12`, not `%rsp`) |
| `movl 8(%rax), %eax` | `8b 40 08` | 3 | the no-index base row |
| `movl 8(%r12), %eax` | `41 8b 44 24 08` | 5 | the no-index `SIB` base row |
| `movl 127(%rax,%rcx,1), %eax` | `8b 44 08 7f` | 4 | the signed byte upper end |
| `movl -128(%rax,%rcx,1), %eax` | `8b 44 08 80` | 4 | the signed byte lower end |
| `movq 8(%rax,%rcx,1), %rax` | `48 8b 44 08 08` | 5 | the 64-bit sibling (`REX.W`) |
| `movl 8(%rax,%rcx,1), %r16d` | `d5 40 8b 44 08 08` | 6 | the APX `d5` window |

`adjacent-encoding.txt` records the eleven accepted lines and the assembler
diagnostic for the `%rsp` index.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cz` | names `x86:mov/r32-base-index-disp8/legacy` against `0.48.0` | `E-FORM-001` |
| `N01da` | names `x86:mov/base-index-disp8-r32/legacy` against `0.48.0` | `E-FORM-001` |
| `N02bs` | drops the `index` from the load row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03zb` | scale `4` on the load row, past the two-bit field | `E-RANGE-001` |
| `N14bg` | register `8` on the load row | `E-OPERAND-004` |
| `N14bh` | base `8` on the store row | `E-OPERAND-004` |
| `N16cc` | index `4` on the store row | `E-RANGE-004` |

The claims the ADR turns on: the register and base fields are three bits, so
`8`–`15` must be rejected (those are the `REX` windows, which are separate
forms), and index `4` is the "no index" encoding, so accepting it would encode
a different addressing mode than the plan named.

`%rsp` is legal as a base here (`8b 44 0c 08`) and `%rbp` is too
(`8b 44 35 08`), which is why the base slot has no exclusion; `%r12` as a base
is `41 8b 44 0c 08`, the `REX.B` form, so the base window really is `0`–`7`.

## 5. The fixture

`X86-P53-gpr32-mov-index-low` is twelve instructions and 63 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%rax,%rcx,1), %eax` | `8b 44 08 08` | 4 |
| 2 | `movl 8(%rdi,%rsi,4), %edi` | `8b 7c b7 08` | 4 |
| 3 | `movl %eax, 8(%rax,%rcx,1)` | `89 44 08 08` | 4 |
| 4 | `movl %edi, 8(%rdi,%rsi,4)` | `89 7c b7 08` | 4 |
| 5 | `movl 8(%rsp,%rcx,1), %eax` | `8b 44 0c 08` | 4 |
| 6 | `movl 8(%rbp,%rsi,1), %eax` | `8b 44 35 08` | 4 |
| 7 | `movl %eax, 8(%rsp,%rcx,1)` | `89 44 0c 08` | 4 |
| 8 | `movl 200(%rax,%rcx,1), %eax` | `8b 84 08 c8 00 00 00` | 7 |
| 9 | `movl 200(%rdi,%rsi,4), %edi` | `8b bc b7 c8 00 00 00` | 7 |
| 10 | `movl %eax, 200(%rax,%rcx,1)` | `89 84 08 c8 00 00 00` | 7 |
| 11 | `movl 200(%rsp,%rcx,1), %eax` | `8b 84 0c c8 00 00 00` | 7 |
| 12 | `movl %eax, 200(%rbp,%rsi,1)` | `89 84 35 c8 00 00 00` | 7 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`a9443fe6c106a9e021203d7f420c6481d0f98dd077456e021faa21afd86aeae9`
(`probe.asm`) and its `output_sha256` is
`595b6d7550ed40f4e7c3cc0fc62ce33adf3ca44091164f7d46ff96607a9b138f`
(the 63-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:f4ef150ca93de09aed9850b64933f3671bee8ab67e54a3968d2b945953821905`.

`0.49.0` has 393 forms and the canonical digest
`sha256:5a7ec114d02101465839a60645c4cfb8b4527dab766a6c90f801e0b38161ccd0`.

## 6. What the slice defers

- The `REX.R`/`REX.B`/`REX.X`/`REX.BX` windows on the 32-bit indexed rows,
  whose shapes are `44 8b 44 08 08`, `41 8b 44 08 08`, `42 8b 44 08 08` and
  `43 8b 44 08 08`.
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The APX `d5` register window, whose shape here is `d5 40 8b 44 08 08`.
