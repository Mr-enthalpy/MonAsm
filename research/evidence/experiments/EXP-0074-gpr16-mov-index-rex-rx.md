# EXP-0074 -- the 16-bit `mov` rows take a `SIB` index and scale

- Date: 2026-11-07
- Question: what does an index and scale cost on the 16-bit `mov` rows, can one
  `REX` byte carry all three extension bits, and where does the displacement
  sit behind the `SIB` byte?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.45.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P49-gpr16-mov-index-rex-rx.oracle.json`
- Source: `research/evidence/experiments/EXP-0074/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0074/probe.asm` (the same
  twelve lines)
- Decision: `ADR-0072`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%rax,%rcx,1), %r8w` | `66 44 8b 44 08 08` | 6 |
| `movw 8(%r15,%r13,8), %r15w` | `66 47 8b 7c ef 08` | 6 |
| `movw %r8w, 8(%rax,%rcx,1)` | `66 44 89 44 08 08` | 6 |
| `movw %r15w, 8(%r15,%r13,8)` | `66 47 89 7c ef 08` | 6 |
| `movw 8(%r8,%rdi,2), %r8w` | `66 45 8b 44 78 08` | 6 |
| `movw %r15w, 8(%rdi,%r12,4)` | `66 46 89 7c a7 08` | 6 |
| `movw 200(%rax,%rcx,1), %r8w` | `66 44 8b 84 08 c8 00 00 00` | 9 |
| `movw 200(%r15,%r13,8), %r15w` | `66 47 8b bc ef c8 00 00 00` | 9 |
| `movw %r8w, 200(%rax,%rcx,1)` | `66 44 89 84 08 c8 00 00 00` | 9 |
| `movw %r15w, 200(%r15,%r13,8)` | `66 47 89 bc ef c8 00 00 00` | 9 |
| `movw 200(%r8,%rdi,2), %r8w` | `66 45 8b 84 78 c8 00 00 00` | 9 |
| `movw %r15w, 200(%rdi,%r12,4)` | `66 46 89 bc a7 c8 00 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `0x66` | `REX` | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|---|
| `disp8`, `R` | `66 44 8b 44 08 08` | byte 0 | `44` at `[8,8]` (`R` at `[10,1]`) | byte 2 | `44` at `[24,8]` (`mod = 01`, `r/m = 100`) | byte 4: scale `[38,2] = 0`, index `[35,3] = 1`, base `[32,3] = 0` | `[40,8]` |
| `disp8`, `RXB` | `66 47 8b 7c ef 08` | byte 0 | `47` at `[8,8]` (`R`, `X`, `B`) | byte 2 | `7c` (`mod = 01`, `reg = 7`, `r/m = 100`) | `ef`: scale `3`, index `5`, base `7` | `[40,8]` |
| `disp8`, `RB` | `66 45 8b 44 78 08` | byte 0 | `45` at `[8,8]` (`R`, `B`) | byte 2 | `44` (`mod = 01`, `r/m = 100`) | `78`: scale `1`, index `7`, base `0` | `[40,8]` |
| `disp8`, `RX` | `66 46 89 7c a7 08` | byte 0 | `46` at `[8,8]` (`R`, `X`) | byte 2 | `7c` (`mod = 01`, `reg = 7`, `r/m = 100`) | `a7`: scale `2`, index `4` (with `X = 1` it is `%r12`), base `7` | `[40,8]` |
| `disp32`, `R` | `66 44 8b 84 08 c8 00 00 00` | byte 0 | `44` at `[8,8]` (`R`) | byte 2 | `84` (`mod = 10`, `r/m = 100`) | `08`: scale `0`, index `1`, base `0` | `[40,32]` |
| `disp32`, `RXB` | `66 47 8b bc ef c8 00 00 00` | byte 0 | `47` at `[8,8]` (`R`, `X`, `B`) | byte 2 | `bc` (`mod = 10`, `reg = 7`, `r/m = 100`) | `ef`: scale `3`, index `5`, base `7` | `[40,32]` |

The `0x66` prefix is byte 0, so the `REX` byte is byte 1 with `B` at `[8,1]`,
`X` at `[9,1]` and `R` at `[10,1]`; `ModRM` is byte 3, its `reg` field
`[27,3]`, and the `SIB` byte is byte 4 with `base` at `[32,3]`, `index` at
`[35,3]` and `scale` at `[38,2]`. The displacement follows the `SIB` byte, so
the indexed rows move it from `[32,8]`/`[32,32]` to `[40,8]`/`[40,32]`.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the ones that
sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw (,%rcx,4), %r8w` | `66 44 8b 04 8d 00 00 00 00` | 9 | no base (`SIB.base = 101`), a separate shape |
| `movw 8(%r13,%rcx,1), %r8w` | `66 45 8b 44 0d 08` | 6 | `%r13` is a legal base at `mod = 01` |
| `movw 127(%rax,%rcx,1), %r8w` | `66 44 8b 44 08 7f` | 6 | the signed byte upper end |
| `movw -128(%rax,%rcx,1), %r8w` | `66 44 8b 44 08 80` | 6 | the signed byte lower end |
| `movw 8(%rax,%rcx,1), %ax` | `66 8b 44 08 08` | 5 | the low-register row, already frozen |
| `movw 8(%rax,%rcx,1), %r16w` | `66 d5 40 8b 44 08 08` | 7 | APX `d5` register window, a separate slice |

`movw 8(%rax,%rsp,1), %r8w` is rejected by the assembler
(`invalid base+index expression`), which is the negative `N16bv` rather than an
adjacent encoding. `adjacent-encoding.txt` records the six accepted lines.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cr` | names `x86:mov/r16-ext-base-index-disp8/legacy` against `0.44.0` | `E-FORM-001` |
| `N01cs` | names `x86:mov/base-index-disp8-r16-ext/legacy` against `0.44.0` | `E-FORM-001` |
| `N02bo` | drops the `index` from `x86:mov/r16-ext-base-index-disp8/legacy` | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03x` | scale `4` on the same row, past the two-bit field | `E-RANGE-001` |
| `N14ay` | register `16` on the same row | `E-OPERAND-004` |
| `N14az` | base `16` on the same row | `E-OPERAND-004` |
| `N16bv` | index `4` (`%rsp`, the "no index" encoding) on the same row | `E-RANGE-004` |
| `N16bw` | register `0` on `x86:mov/r16-ext-base-index-disp8/legacy` | `E-RANGE-004` |

The claims the ADR turns on: index `4` is the `SIB.index = 100` "no index"
encoding, so accepting it would drop an operand (`INV-07`); scale `4` is past
the two-bit field and would be a truncated `0`; and a register value `0`–`7` on
an `-ext` row is `E-RANGE-004`, because the encoder never sets `REX.R` from the
value.

`%rbp` is deliberately not a negative on the base: it is legal at `mod = 01`,
because `r/m = 100` announces the `SIB` byte and `SIB.base = 101` is a base
with a displacement.

## 5. The fixture

`X86-P49-gpr16-mov-index-rex-rx` is twelve instructions and 90 bytes: the four
rows across the four scale factors, both ends of the register window, low and
high bases and low and high indexes, at both displacement widths.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%rax,%rcx,1), %r8w` | `66 44 8b 44 08 08` | 6 |
| 2 | `movw 8(%r15,%r13,8), %r15w` | `66 47 8b 7c ef 08` | 6 |
| 3 | `movw %r8w, 8(%rax,%rcx,1)` | `66 44 89 44 08 08` | 6 |
| 4 | `movw %r15w, 8(%r15,%r13,8)` | `66 47 89 7c ef 08` | 6 |
| 5 | `movw 8(%r8,%rdi,2), %r8w` | `66 45 8b 44 78 08` | 6 |
| 6 | `movw %r15w, 8(%rdi,%r12,4)` | `66 46 89 7c a7 08` | 6 |
| 7 | `movw 200(%rax,%rcx,1), %r8w` | `66 44 8b 84 08 c8 00 00 00` | 9 |
| 8 | `movw 200(%r15,%r13,8), %r15w` | `66 47 8b bc ef c8 00 00 00` | 9 |
| 9 | `movw %r8w, 200(%rax,%rcx,1)` | `66 44 89 84 08 c8 00 00 00` | 9 |
| 10 | `movw %r15w, 200(%r15,%r13,8)` | `66 47 89 bc ef c8 00 00 00` | 9 |
| 11 | `movw 200(%r8,%rdi,2), %r8w` | `66 45 8b 84 78 c8 00 00 00` | 9 |
| 12 | `movw %r15w, 200(%rdi,%r12,4)` | `66 46 89 bc a7 c8 00 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`8123b0a50e7d0c1cb471258dffd01eaa0336e2b9076b41574edc20eedcf5dd33`
(`probe.asm`) and its `output_sha256` is
`69fc575b15b585f3651bd84a3757403f1445fac20e80ba26ae5bd0b7f3e7f499`
(the 90-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:2d2089c3ce39dd303ebbcf23c11a2cb296ad1f0da365a706a38a426cb92c91b7`.

`0.45.0` has 373 forms and the canonical digest
`sha256:9adaf50a6798c7b4bd5f0090f9860de30e360994c45138f017a3c1298e5fc2d8`.

## 6. What the slice defers

- The low-register indexed rows, which need a `REX`-less prefix variant.
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`66 44 8b 04 8d 00 00 00 00`).
- The APX `d5` register window (`66 d5 40 8b 44 08 08`).
