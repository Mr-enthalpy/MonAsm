# EXP-0084 -- the two fixed-`REX`-bit windows on the `0x67` 32-bit indexed `mov`

- Date: 2026-11-07
- Question: what do two fixed `REX` bits cost after the `0x67` address-size
  prefix on the 32-bit indexed `mov`, and how do they compose with the third?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.55.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P59-gpr32-mov-index-addr32-rex-two-bit-windows.oracle.json`
- Source: `research/evidence/experiments/EXP-0084/probe.asm`
- Decision: `ADR-0082`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%r8d,%r9d,1), %eax` | `67 43 8b 44 08 08` | 6 |
| `movl %eax, 8(%r8d,%r9d,1)` | `67 43 89 44 08 08` | 6 |
| `movl 200(%r8d,%r9d,1), %eax` | `67 43 8b 84 08 c8 00 00 00` | 9 |
| `movl %eax, 200(%r8d,%r9d,1)` | `67 43 89 84 08 c8 00 00 00` | 9 |
| `movl 8(%r8d,%ecx,1), %r8d` | `67 45 8b 44 08 08` | 6 |
| `movl %r8d, 8(%r8d,%ecx,1)` | `67 45 89 44 08 08` | 6 |
| `movl 200(%r8d,%ecx,1), %r8d` | `67 45 8b 84 08 c8 00 00 00` | 9 |
| `movl %r8d, 200(%r8d,%ecx,1)` | `67 45 89 84 08 c8 00 00 00` | 9 |
| `movl 8(%eax,%r9d,1), %r8d` | `67 46 8b 44 08 08` | 6 |
| `movl %r8d, 8(%eax,%r9d,1)` | `67 46 89 44 08 08` | 6 |
| `movl 200(%eax,%r9d,1), %r8d` | `67 46 8b 84 08 c8 00 00 00` | 9 |
| `movl %r8d, 200(%eax,%r9d,1)` | `67 46 89 84 08 c8 00 00 00` | 9 |
| `movl 8(%r8d,%r9d,1), %r8d` | `67 47 8b 44 08 08` | 6 |
| `movl %r8d, 8(%r8d,%r9d,1)` | `67 47 89 44 08 08` | 6 |
| `movl 200(%r8d,%r9d,1), %r8d` | `67 47 8b 84 08 c8 00 00 00` | 9 |
| `movl %r8d, 200(%r8d,%r9d,1)` | `67 47 89 84 08 c8 00 00 00` | 9 |
| `movl 8(%r12d,%r12d,1), %r12d` | `67 47 8b 64 24 08` | 6 |
| `movl 8(%r13d,%r13d,1), %r13d` | `67 47 8b 6c 2d 08` | 6 |
| `movl 8(%r8d,%r9d,8), %r15d` | `67 47 8b 7c c8 08` | 6 |
| `movl %r15d, 8(%r15d,%ebp,1)` | `67 45 89 7c 2f 08` | 6 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

The geometry is the `0.54.0` geometry: `0x67` at byte 0, `REX` at byte 1, the
opcode at byte 2, `ModRM` at byte 3 and `SIB` at byte 4. The register is
`[27,3]`, the base `[32,3]`, the index `[35,3]`, the scale `[38,2]` and the
displacement `[40,8]` or `[40,32]`. The `REX` byte carries `R` at `[10,1]`,
`X` at `[9,1]` and `B` at `[8,1]`:

| Byte | `43` (`BX`) | `45` (`RB`) | `46` (`RX`) | `47` (`RBX`) |
|---|---|---|---|---|
| `REX` | `B`, `X` | `R`, `B` | `R`, `X` | `R`, `B`, `X` |
| value register | low, `[27,3]` | `[10,1]`+`[27,3]` | `[10,1]`+`[27,3]` | `[10,1]`+`[27,3]` |
| base | `[8,1]`+`[32,3]` | `[8,1]`+`[32,3]` | low, `[32,3]` | `[8,1]`+`[32,3]` |
| index | `[9,1]`+`[35,3]` | low, `[35,3]` | `[9,1]`+`[35,3]` | `[9,1]`+`[35,3]` |
| `disp8` / `disp32` | `[40,8]` / `[40,32]` | same | same | same |

The `SIB` byte is the same in all four windows (`08` = scale `0`, index `1`,
base `0` for the low `%ecx`/`%eax` operands); only which slot reads a `REX`
bit changes.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the registers
that sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 8(%r8d,%esp,1), %eax` | rejected | -- | `%esp` is not an index |
| `movl 8(%esp,%r9d,1), %eax` | `67 42 8b 44 0c 08` | 6 | `%esp` as a base on the `X` row (`SIB.base = 100`, `REX.B = 0`) |
| `movl 8(%eax,%r9d,1), %eax` | `67 42 8b 44 08 08` | 6 | the `REX.X` single-bit row |
| `movl 8(%r8d,%ecx,1), %eax` | `67 41 8b 44 08 08` | 6 | the `REX.B` single-bit row |
| `movl 8(%r8d,%r9d,1), %eax` | `67 43 8b 44 08 08` | 6 | the `REX.BX` row (this slice) |
| `movl 8(%r8,%r9,1), %r8d` | `47 8b 44 08 08` | 5 | 64-bit addressing `REX.RBX` |
| `movq 8(%r8d,%r9d,1), %rax` | `67 4b 8b 44 08 08` | 6 | `0x67` + `REX.WBX` (deferred) |
| `movl 8(%r12d,%ebp,1), %eax` | `67 41 8b 44 2c 08` | 6 | `%r12d` base with `%ebp` index (`REX.B`) |
| `movl 8(%ebp,%r12d,1), %eax` | `67 42 8b 44 25 08` | 6 | `%ebp` base with `%r12d` index (`REX.X`) |
| `movl 8(%edx,%ebx,1), %eax` | `67 8b 44 1a 08` | 5 | the bare `0x67` row |

`adjacent-encoding.txt` records the nine accepted lines and the one assembler
diagnostic. The two-bit windows differ from their single-bit neighbours only in
the `REX` byte, and the `%esp` base is writable only while the base bit is
clear.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01dl` | names `x86:mov/r32-addr32-base-ext-index-ext-disp8/legacy` against `0.54.0` | `E-FORM-001` |
| `N01dm` | names `x86:mov/addr32-base-ext-index-ext-disp8-r32-ext/legacy` against `0.54.0` | `E-FORM-001` |
| `N02bz` | drops the `index` from the `REX.BX` row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03zh` | scale `4` on the `REX.RX` row, past the two-bit field | `E-RANGE-001` |
| `N16cp` | value register `3` on the `REX.RB` row, the excluded low window | `E-RANGE-004` |
| `N16cq` | base `3` on the `REX.BX` row | `E-RANGE-004` |
| `N16cr` | index `3` on the `REX.RX` row | `E-RANGE-004` |
| `N14bp` | value register `8` on the `REX.BX` row, past its three-bit field | `E-OPERAND-004` |
| `N14bq` | base `8` on the `REX.RX` row, past its three-bit field | `E-OPERAND-004` |

The claims the ADR turns on: two bits of one byte extend two operands, each
extended slot excludes the low window, and a value that would need a bit the
row leaves clear is rejected rather than truncated.

## 5. The fixture

`X86-P59-gpr32-mov-index-addr32-rex-two-bit-windows` is twenty instructions and
144 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%r8d,%r9d,1), %eax` | `67 43 8b 44 08 08` | 6 |
| 2 | `movl %eax, 8(%r8d,%r9d,1)` | `67 43 89 44 08 08` | 6 |
| 3 | `movl 200(%r8d,%r9d,1), %eax` | `67 43 8b 84 08 c8 00 00 00` | 9 |
| 4 | `movl %eax, 200(%r8d,%r9d,1)` | `67 43 89 84 08 c8 00 00 00` | 9 |
| 5 | `movl 8(%r8d,%ecx,1), %r8d` | `67 45 8b 44 08 08` | 6 |
| 6 | `movl %r8d, 8(%r8d,%ecx,1)` | `67 45 89 44 08 08` | 6 |
| 7 | `movl 200(%r8d,%ecx,1), %r8d` | `67 45 8b 84 08 c8 00 00 00` | 9 |
| 8 | `movl %r8d, 200(%r8d,%ecx,1)` | `67 45 89 84 08 c8 00 00 00` | 9 |
| 9 | `movl 8(%eax,%r9d,1), %r8d` | `67 46 8b 44 08 08` | 6 |
| 10 | `movl %r8d, 8(%eax,%r9d,1)` | `67 46 89 44 08 08` | 6 |
| 11 | `movl 200(%eax,%r9d,1), %r8d` | `67 46 8b 84 08 c8 00 00 00` | 9 |
| 12 | `movl %r8d, 200(%eax,%r9d,1)` | `67 46 89 84 08 c8 00 00 00` | 9 |
| 13 | `movl 8(%r8d,%r9d,1), %r8d` | `67 47 8b 44 08 08` | 6 |
| 14 | `movl %r8d, 8(%r8d,%r9d,1)` | `67 47 89 44 08 08` | 6 |
| 15 | `movl 200(%r8d,%r9d,1), %r8d` | `67 47 8b 84 08 c8 00 00 00` | 9 |
| 16 | `movl %r8d, 200(%r8d,%r9d,1)` | `67 47 89 84 08 c8 00 00 00` | 9 |
| 17 | `movl 8(%r12d,%r12d,1), %r12d` | `67 47 8b 64 24 08` | 6 |
| 18 | `movl 8(%r13d,%r13d,1), %r13d` | `67 47 8b 6c 2d 08` | 6 |
| 19 | `movl 8(%r8d,%r9d,8), %r15d` | `67 47 8b 7c c8 08` | 6 |
| 20 | `movl %r15d, 8(%r15d,%ebp,1)` | `67 45 89 7c 2f 08` | 6 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`f1c1be782db3cb087a26cf99308c12c46cf34b92846d0b0c505197fe14d243ec`
(`probe.asm`) and its `output_sha256` is
`2151a2a9e84db3ceb9dfd6d9cb71bdd41001a4e15fc19fbf4fb001c9897bc136`
(the 144-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:b066b81984a4aafee2fe60d0ebb3f4f45f7c277cca891bddec931ebf2fc77279`.

`0.55.0` has 445 forms and the canonical digest
`sha256:e4fe01184a25274242c3eb9cf29b411d48d2d629cd2befbcbd274ef6384618fc`.

## 6. What the slice defers

- The `0x67` `REX.W` siblings (`67 48`, `67 4c`, `67 4d`, `67 4f`).
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The `moffs` form with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
