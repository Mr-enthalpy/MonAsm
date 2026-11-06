# EXP-0071 -- the 16-bit `mod = 00` rows take the `REX.R` register window

- Date: 2026-11-07
- Question: how does `%r8w`–`%r15w` reach the 16-bit `mod = 00` `mov` rows,
  what happens when both extension bits share one `REX` byte, and how do the
  `SIB` bases compose with the register window?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.42.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P46-gpr16-mov-mem-nodisp-rex-r.oracle.json`
- Source: `research/evidence/experiments/EXP-0071/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0071/probe.asm` (the same
  fourteen lines)
- Decision: `ADR-0069`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw (%rax), %r8w` | `66 44 8b 00` | 4 |
| `movw (%rdi), %r15w` | `66 44 8b 3f` | 4 |
| `movw (%r8), %r8w` | `66 45 8b 00` | 4 |
| `movw (%r15), %r15w` | `66 45 8b 3f` | 4 |
| `movw %r8w, (%rax)` | `66 44 89 00` | 4 |
| `movw %r15w, (%rdi)` | `66 44 89 3f` | 4 |
| `movw %r8w, (%r8)` | `66 45 89 00` | 4 |
| `movw %r15w, (%r15)` | `66 45 89 3f` | 4 |
| `movw (%rsp), %r8w` | `66 44 8b 04 24` | 5 |
| `movw %r8w, (%rsp)` | `66 44 89 04 24` | 5 |
| `movw (%r12), %r8w` | `66 45 8b 04 24` | 5 |
| `movw %r8w, (%r12)` | `66 45 89 04 24` | 5 |
| `movw (%r12), %r15w` | `66 45 8b 3c 24` | 5 |
| `movw %r15w, (%r12)` | `66 45 89 3c 24` | 5 |

`llvm-mc -disassemble` on `probes.txt` returns all fourteen byte strings as the
same registers and base (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `0x66` | `REX` | Opcode | `ModRM` | Register | Base |
|---|---|---|---|---|---|---|---|
| `REX.R`, low base | `66 44 8b 00` | byte 0 | `44` at `[8,8]` | byte 2 | byte 3 at `[24,8]` | `R` at `[10,1]`, `[27,3]` | `r/m` at `[24,3]` |
| `REX.RB` | `66 45 8b 00` | byte 0 | `45` at `[8,8]` | byte 2 | byte 3 at `[24,8]` | `R` at `[10,1]`, `[27,3]` | `r/m` at `[24,3]`, `B` at `[8,1]` |
| `REX.R`, `%rsp` | `66 44 8b 04 24` | byte 0 | `44` at `[8,8]` | byte 2 | byte 3 (`mod = 00`, `r/m = 100`) | `R` at `[10,1]`, `[27,3]` | fixed `SIB = 24` at byte 4 |
| `REX.RB`, `%r12` | `66 45 8b 04 24` | byte 0 | `45` at `[8,8]` | byte 2 | byte 3 (`mod = 00`, `r/m = 100`) | `R` at `[10,1]`, `[27,3]` | fixed `SIB = 24` at byte 4, `B` at `[8,1]` |

The `0x66` prefix is byte 0, so the `REX` byte is byte 1 and its bit 0
(`REX.B`) is `[8,1]`, while `REX.R` (bit 2 of that byte) is `[10,1]`. `ModRM`
is byte 3, so its `reg` field is `[27,3]`. This is the same register placement
the `x86:mov/r16-ext-abs32/legacy` rows already use.

### Both extension bits share one byte

| Source | Bytes | `REX` | Register | Base |
|---|---|---|---|---|
| `movw (%r8), %r8w` | `66 45 8b 00` | `45` = `R` + `B` | `%r8w` (`R = 1`) | `%r8` (`B = 1`) |
| `movw (%r15), %r15w` | `66 45 8b 3f` | `45` = `R` + `B` | `%r15w` (`R = 1`) | `%r15` (`B = 1`) |

One `REX` byte extends both ends, so the combined rows stay four bytes; only
the fixed template byte differs from the low-base rows (`45` instead of `44`).

### The `SIB` bases compose unchanged

| Source | Bytes | Why |
|---|---|---|
| `movw (%rsp), %r8w` | `66 44 8b 04 24` | `r/m = 100`, `SIB = 24`, `REX.R` |
| `movw (%r12), %r8w` | `66 45 8b 04 24` | the same `SIB = 24`, plus `REX.B` |
| `movw (%r12), %r15w` | `66 45 8b 3c 24` | the same, with the register at `%r15w` |

The `SIB` byte does not change with the register, so the base remains a form
property and the register stays the only operand.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw (%rbp), %r8w` | `66 44 8b 45 00` | 5 | `r/m = 101` at `mod = 00` is `rip`-relative, so the assembler uses `mod = 01` and a zero displacement |
| `movw (%r13), %r8w` | `66 45 8b 45 00` | 5 | the same behind `REX.B` |
| `movw (%rax), %r16w` | `66 d5 40 8b 00` | 5 | APX `d5` register window, a separate slice |
| `movw 8(%rax), %r8w` | `66 44 8b 40 08` | 5 | `disp8` shape with the register window, deferred |
| `movw 200(%rax), %r8w` | `66 44 8b 80 c8 00 00 00` | 8 | `disp32` shape, deferred |
| `movw 8(%rsp), %r8w` | `66 44 8b 44 24 08` | 6 | `SIB` plus `disp8`, deferred |
| `movl (%rax), %r8d` | `44 8b 00` | 3 | 32-bit analogue, already frozen |
| `movq (%rax), %r8` | `4c 8b 00` | 3 | 64-bit analogue, already frozen |
| `movb (%rax), %r8b` | `44 8a 00` | 3 | 8-bit analogue, already frozen |
| `movw (%rsp,%rax), %r8w` | `66 44 8b 04 04` | 5 | `SIB` index, next axis |
| `movw (%rsp,%rax,4), %r8w` | `66 44 8b 04 84` | 5 | index plus scale |

`adjacent-encoding.txt` records all eleven lines; no line is rejected.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cl` | names `x86:mov/r16-ext-base/legacy` against `0.41.0` | `E-FORM-001` |
| `N01cm` | names `x86:mov/base-r16-ext/legacy` against `0.41.0` | `E-FORM-001` |
| `N02bl` | supplies a `disp` to `x86:mov/r16-ext-rsp/legacy` | `E-OPERAND-002` (`expected 1, found 2`) |
| `N14av` | register `16` on `x86:mov/r16-ext-base/legacy` | `E-OPERAND-004` |
| `N16bm` | register `0` on the `REX.R` row | `E-RANGE-004` |
| `N16bn` | base `%rsp` (`4`) on the `REX.R` low-base row | `E-RANGE-004` |
| `N16bo` | base `%rbp` (`5`) on the `REX.RB` row | `E-RANGE-004` |

The register-window claim is the one the ADR turns on: `16` is past the
four-bit field (`E-OPERAND-004`), and `0` would clear the fixed `REX.R` bit
(`E-RANGE-004`) — the encoder never chooses the bit from the value.

## 5. The fixture

`X86-P46-gpr16-mov-mem-nodisp-rex-r` is fourteen instructions and 62 bytes:
the four plain rows twice, at the `%r8w` and `%r15w` ends of the register
window, and the four fixed-base rows once at `%r8w` plus the two `%r12` rows
again at `%r15w`.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw (%rax), %r8w` | `66 44 8b 00` | 4 |
| 2 | `movw (%rdi), %r15w` | `66 44 8b 3f` | 4 |
| 3 | `movw (%r8), %r8w` | `66 45 8b 00` | 4 |
| 4 | `movw (%r15), %r15w` | `66 45 8b 3f` | 4 |
| 5 | `movw %r8w, (%rax)` | `66 44 89 00` | 4 |
| 6 | `movw %r15w, (%rdi)` | `66 44 89 3f` | 4 |
| 7 | `movw %r8w, (%r8)` | `66 45 89 00` | 4 |
| 8 | `movw %r15w, (%r15)` | `66 45 89 3f` | 4 |
| 9 | `movw (%rsp), %r8w` | `66 44 8b 04 24` | 5 |
| 10 | `movw %r8w, (%rsp)` | `66 44 89 04 24` | 5 |
| 11 | `movw (%r12), %r8w` | `66 45 8b 04 24` | 5 |
| 12 | `movw %r8w, (%r12)` | `66 45 89 04 24` | 5 |
| 13 | `movw (%r12), %r15w` | `66 45 8b 3c 24` | 5 |
| 14 | `movw %r15w, (%r12)` | `66 45 89 3c 24` | 5 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`e71e5686d1f7916b0ad80f6c277280538ba74511d763c409503fa72a7f7d5e61`
(`probe.asm`) and its `output_sha256` is
`e05a6ea83e4087f624bd0ce3069b335827618dbb1ba6e9884d10168202c3673d`
(the 62-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:7751cca5f185d7450d4ae60375af7364458160de5a4caf4ecdba5638364525f5`.

## 6. What the slice defers

- The `disp8`/`disp32` shapes with the `REX.R` register window
  (`66 44 8b 40 08`, `66 44 8b 80 c8 00 00 00`).
- An index or scale operand (`66 44 8b 04 04`, `66 44 8b 04 84`).
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The same shape at 8 and 64 bits where a window is still missing.
- The APX `d5` register window (`66 d5 40 8b 00`).
