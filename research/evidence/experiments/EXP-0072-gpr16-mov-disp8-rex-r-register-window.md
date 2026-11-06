# EXP-0072 -- the 16-bit `disp8` rows take the `REX.R` register window

- Date: 2026-11-07
- Question: how does `%r8w`–`%r15w` reach the 16-bit `disp8` `mov` rows,
  where does the displacement byte sit once `REX` is present, and which bases
  become legal at `mod = 01`?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.43.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P47-gpr16-mov-mem-disp8-rex-r.oracle.json`
- Source: `research/evidence/experiments/EXP-0072/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0072/probe.asm` (the same
  fourteen lines)
- Decision: `ADR-0070`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%rax), %r8w` | `66 44 8b 40 08` | 5 |
| `movw 8(%rdi), %r15w` | `66 44 8b 7f 08` | 5 |
| `movw 8(%r8), %r8w` | `66 45 8b 40 08` | 5 |
| `movw 8(%r15), %r15w` | `66 45 8b 7f 08` | 5 |
| `movw %r8w, 8(%rax)` | `66 44 89 40 08` | 5 |
| `movw %r15w, 8(%rdi)` | `66 44 89 7f 08` | 5 |
| `movw %r8w, 8(%r8)` | `66 45 89 40 08` | 5 |
| `movw %r15w, 8(%r15)` | `66 45 89 7f 08` | 5 |
| `movw 8(%rsp), %r8w` | `66 44 8b 44 24 08` | 6 |
| `movw %r8w, 8(%rsp)` | `66 44 89 44 24 08` | 6 |
| `movw 8(%r12), %r8w` | `66 45 8b 44 24 08` | 6 |
| `movw %r8w, 8(%r12)` | `66 45 89 44 24 08` | 6 |
| `movw 8(%r12), %r15w` | `66 45 8b 7c 24 08` | 6 |
| `movw %r15w, 8(%r12)` | `66 45 89 7c 24 08` | 6 |

`llvm-mc -disassemble` on `probes.txt` returns all fourteen byte strings as the
same registers and base (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `0x66` | `REX` | Opcode | `ModRM` | Register | Base | Displacement |
|---|---|---|---|---|---|---|---|---|
| `REX.R`, low base | `66 44 8b 40 08` | byte 0 | `44` at `[8,8]` | byte 2 | `40` at `[24,8]` (`mod = 01`, `r/m = 0`) | `R` at `[10,1]`, `[27,3]` | `r/m` at `[24,3]` | byte 4 at `[32,8]` |
| `REX.RB` | `66 45 8b 40 08` | byte 0 | `45` at `[8,8]` | byte 2 | `40` at `[24,8]` (`mod = 01`, `r/m = 0`) | `R` at `[10,1]`, `[27,3]` | `r/m` at `[24,3]`, `B` at `[8,1]` | byte 4 at `[32,8]` |
| `REX.R`, `%rsp` | `66 44 8b 44 24 08` | byte 0 | `44` at `[8,8]` | byte 2 | `44` at `[24,8]` (`mod = 01`, `r/m = 100`) | `R` at `[10,1]`, `[27,3]` | fixed `SIB = 24` at byte 4 | byte 5 at `[40,8]` |
| `REX.RB`, `%r12` | `66 45 8b 44 24 08` | byte 0 | `45` at `[8,8]` | byte 2 | `44` at `[24,8]` (`mod = 01`, `r/m = 100`) | `R` at `[10,1]`, `[27,3]` | fixed `SIB = 24` at byte 4, `B` at `[8,1]` | byte 5 at `[40,8]` |

The `0x66` prefix is byte 0, so the `REX` byte is byte 1 and its bit 0
(`REX.B`) is `[8,1]`, while `REX.R` (bit 2 of that byte) is `[10,1]`.
`ModRM` is byte 3, so its `reg` field is `[27,3]` and its `mod` field is
`01`. The displacement follows the `ModRM` byte on the plain rows and the
`SIB` byte on the `SIB` rows.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the ones that
sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%rbp), %r8w` | `66 44 8b 45 08` | 5 | `%rbp` is a legal base at `mod = 01` (`r/m = 101`), unlike `mod = 00` |
| `movw 8(%r13), %r8w` | `66 45 8b 45 08` | 5 | the same behind `REX.B` |
| `movw 127(%rax), %r8w` | `66 44 8b 40 7f` | 5 | the signed byte's upper end |
| `movw -128(%rax), %r8w` | `66 44 8b 40 80` | 5 | the signed byte's lower end |
| `movw 128(%rax), %r8w` | `66 44 8b 80 80 00 00 00` | 8 | the assembler re-forms this as a `disp32` row, a separate slice |
| `movw 200(%rax), %r8w` | `66 44 8b 80 c8 00 00 00` | 8 | the same `disp32` shape |
| `movw (%rax), %r8w` | `66 44 8b 00` | 4 | the `mod = 00` row from `0.42.0` |
| `movw 8(%rsp,%rax), %r8w` | `66 44 8b 44 04 08` | 6 | `SIB` index, next axis |
| `movw 8(%rsp,%rax,4), %r8w` | `66 44 8b 44 84 08` | 6 | index plus scale |
| `movw 8(%rax), %ax` | `66 8b 40 08` | 5 | the low-register row, already frozen |
| `movw 8(%rax), %r16w` | `66 d5 40 8b 40 08` | 6 | APX `d5` register window, a separate slice |

`adjacent-encoding.txt` records all eleven lines; no line is rejected.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cn` | names `x86:mov/r16-ext-base-disp8/legacy` against `0.42.0` | `E-FORM-001` |
| `N01co` | names `x86:mov/base-disp8-r16-ext/legacy` against `0.42.0` | `E-FORM-001` |
| `N02bm` | drops the `disp` from `x86:mov/r16-ext-base-disp8/legacy` | `E-OPERAND-002` (`expected 3, found 2`) |
| `N03v` | `disp8 = 128` on the same row | `E-RANGE-001` |
| `N14aw` | register `16` on `x86:mov/r16-ext-base-disp8/legacy` | `E-OPERAND-004` |
| `N16bp` | register `0` on `x86:mov/r16-ext-base-ext-disp8/legacy` | `E-RANGE-004` |
| `N16bq` | base `%rsp` (`4`) on the plain row | `E-RANGE-004` |
| `N16br` | base `%rbp` (`5`) on the `-ext`-base row | `E-RANGE-004` |

The two claims the ADR turns on: `128` is `E-RANGE-001`, never a silent
widening to `disp32` (`INV-04`); and a register value `0`–`7` on an `-ext`
row is `E-RANGE-004`, because the encoder never sets `REX.R` from the value.

`%rbp` is deliberately not a negative on the plain low-base row: it is a
legal base at `mod = 01` (`66 44 8b 45 08`), and `N16br` catches it only on
the `-ext` row, where it would clear the fixed `REX.B` bit.

## 5. The fixture

`X86-P47-gpr16-mov-mem-disp8-rex-r` is fourteen instructions and 76 bytes:
the four plain rows twice, at the `%r8w` and `%r15w` ends of the register
window, and the four fixed-base rows once at `%r8w` plus the two `%r12` rows
again at `%r15w`.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%rax), %r8w` | `66 44 8b 40 08` | 5 |
| 2 | `movw 8(%rdi), %r15w` | `66 44 8b 7f 08` | 5 |
| 3 | `movw 8(%r8), %r8w` | `66 45 8b 40 08` | 5 |
| 4 | `movw 8(%r15), %r15w` | `66 45 8b 7f 08` | 5 |
| 5 | `movw %r8w, 8(%rax)` | `66 44 89 40 08` | 5 |
| 6 | `movw %r15w, 8(%rdi)` | `66 44 89 7f 08` | 5 |
| 7 | `movw %r8w, 8(%r8)` | `66 45 89 40 08` | 5 |
| 8 | `movw %r15w, 8(%r15)` | `66 45 89 7f 08` | 5 |
| 9 | `movw 8(%rsp), %r8w` | `66 44 8b 44 24 08` | 6 |
| 10 | `movw %r8w, 8(%rsp)` | `66 44 89 44 24 08` | 6 |
| 11 | `movw 8(%r12), %r8w` | `66 45 8b 44 24 08` | 6 |
| 12 | `movw %r8w, 8(%r12)` | `66 45 89 44 24 08` | 6 |
| 13 | `movw 8(%r12), %r15w` | `66 45 8b 7c 24 08` | 6 |
| 14 | `movw %r15w, 8(%r12)` | `66 45 89 7c 24 08` | 6 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`055317d45bc9872d1b026509a3b10b4cc4a0e1248886191c6eb9a536b0929a13`
(`probe.asm`) and its `output_sha256` is
`728dd651633c69d8601926f936d0e57fbe1424d3b8db9be63b871e40d0d4e2fb`
(the 76-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:fa6785768e1f7955ea46d8d70292636e7713b34fe2d3eac4c521484c3fc095e4`.

`0.43.0` has 361 forms and the canonical digest
`sha256:da40c8548f75b6dd0f509ff1b10e9b3e633c69a7a3a26d660d6bd87c58a1a54c`.

## 6. What the slice defers

- The `disp32` shape with the `REX.R` register window
  (`66 44 8b 80 80 00 00 00`).
- An index or scale operand (`66 44 8b 44 04 08`, `66 44 8b 44 84 08`).
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The same shape at 8 and 64 bits where a window is still missing.
- The APX `d5` register window (`66 d5 40 8b 40 08`).
