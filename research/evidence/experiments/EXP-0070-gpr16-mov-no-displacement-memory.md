# EXP-0070 -- the 16-bit `mov` family takes its base rows

- Date: 2026-11-07
- Question: what does the `mod = 00` shape cost at 16-bit width, which bases
  become legal that `mod = 01` cannot hold, and how do the `%rsp`/`%r12` bases
  behave?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.41.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P45-gpr16-mov-mem-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0070/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0070/fixture.asm`
- Decision: `ADR-0068`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw (%rax), %ax` | `66 8b 00` | 3 |
| `movw (%r8), %ax` | `66 41 8b 00` | 4 |
| `movw (%r15), %ax` | `66 41 8b 07` | 4 |
| `movw (%rsp), %ax` | `66 8b 04 24` | 4 |
| `movw (%r12), %ax` | `66 41 8b 04 24` | 5 |
| `movw %ax, (%rax)` | `66 89 00` | 3 |
| `movw %ax, (%r8)` | `66 41 89 00` | 4 |
| `movw %ax, (%r15)` | `66 41 89 07` | 4 |
| `movw %ax, (%rsp)` | `66 89 04 24` | 4 |
| `movw %ax, (%r12)` | `66 41 89 04 24` | 5 |

`llvm-mc -disassemble` on `probes.txt` returns all ten byte strings as the same
registers and base.

## 2. Where the fields sit

| Row | Bytes | `0x66` | `REX` | Opcode | `ModRM` | Register | Base |
|---|---|---|---|---|---|---|---|
| plain, low | `66 8b 00` | byte 0 | none | byte 1 | byte 2 at `[16,8]` | `[19,3]` | `r/m` at `[16,3]` |
| plain, `REX.B` | `66 41 8b 00` | byte 0 | `41` at `[8,8]` | byte 2 | byte 3 at `[24,8]` | `[27,3]` | `r/m` at `[24,3]`, `B` at `[8,1]` |
| `%rsp` | `66 8b 04 24` | byte 0 | none | byte 1 | byte 2 (`mod = 00`, `r/m = 100`) | `[19,3]` | fixed `SIB = 24` at byte 3 |
| `%r12` | `66 41 8b 04 24` | byte 0 | `41` at `[8,8]` | byte 2 | byte 3 (`mod = 00`, `r/m = 100`) | `[27,3]` | fixed `SIB = 24` at byte 4, `B` at `[8,1]` |

The `0x66` prefix comes first, then `REX`, so a prefix byte shifts every later
field by one. A `REX` byte shifts the register field from `[19,3]` to `[27,3]`
and the plain base from `[16,3]` to `[24,3]`; this is why the `-ext` rows carry
the second placement shape rather than the first.

### The base is a form property on the `SIB` rows

| Source | Bytes | Why |
|---|---|---|
| `movw (%rsp), %ax` | `66 8b 04 24` | `r/m = 100`, `SIB = 24` |
| `movw (%r12), %ax` | `66 41 8b 04 24` | the same `SIB = 24`, plus `REX.B` |

The two bases share the low three bits `100`, so `SIB` cannot tell them apart;
only `REX.B` can. That is why the base is fixed in the form and not an operand:
a plan names one of the two rows.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw (%rbp), %ax` | `66 8b 45 00` | 4 | `r/m = 101` at `mod = 00` is `rip`-relative, so the assembler uses `mod = 01` and a zero displacement |
| `movw (%r13), %ax` | `66 41 8b 45 00` | 5 | the same behind `REX.B` |
| `movw (%rsp), %r8w` | `66 44 8b 04 24` | 5 | `REX.R` register window, a separate axis |
| `movw (%r12), %r8w` | `66 45 8b 04 24` | 5 | both `REX` bits in one byte |
| `movw 0(%rax), %ax` | `66 8b 00` | 3 | `llvm-mc` normalises a zero displacement to `mod = 00` |
| `movl (%rax), %eax` | `8b 00` | 2 | 32-bit analogue |
| `movq (%rax), %rax` | `48 8b 00` | 3 | 64-bit analogue |
| `movb (%rax), %al` | `8a 00` | 2 | 8-bit analogue |
| `movw (%rsp,%rax), %ax` | `66 8b 04 04` | 4 | `SIB` index, next axis |
| `movw (%rsp,%rax,4), %ax` | `66 8b 04 84` | 4 | index plus scale |

`adjacent-encoding.txt` records all ten lines; no line is rejected.
`llvm-mc` normalises `movw 0(%rax), %ax` to the `mod = 00` row (`66 8b 00`),
so a zero displacement cannot reach a `disp8` row through the assembler.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cj` | names `x86:mov/r16-base/legacy` against `0.40.0` | `E-FORM-001` |
| `N01ck` | names `x86:mov/base-r16/legacy` against `0.40.0` | `E-FORM-001` |
| `N02bk` | supplies a `disp` to `x86:mov/r16-rsp/legacy` | `E-OPERAND-002` (`expected 1, found 2`) |
| `N16bh` | base `%rsp` (`4`) on the low plain row | `E-RANGE-004` |
| `N16bi` | base `%r12` (`12`) on the `-ext` plain row | `E-RANGE-004` |
| `N16bj` | base `%rax` (`0`) on the `-ext` plain row | `E-RANGE-004` |
| `N16bk` | base `%rbp` (`5`) on the low plain row | `E-RANGE-004` |
| `N16bl` | base `%r13` (`13`) on the `-ext` plain row | `E-RANGE-004` |

The `disp` claim is the one the ADR turns on: a row with no displacement slot
has one operand, so supplying `disp(8)` is `expected 1, found 2` — the value
never reaches an encoder and cannot widen the row.

## 5. The fixture

`X86-P45-gpr16-mov-mem-nodisp` is twelve instructions and 46 bytes: the four
plain-base rows twice, at `%rax`/`%rdi` and `%r8`/`%r15`, and the four
fixed-base rows once each.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw (%rax), %ax` | `66 8b 00` | 3 |
| 2 | `movw (%rdi), %ax` | `66 8b 07` | 3 |
| 3 | `movw (%r8), %ax` | `66 41 8b 00` | 4 |
| 4 | `movw (%r15), %ax` | `66 41 8b 07` | 4 |
| 5 | `movw %ax, (%rax)` | `66 89 00` | 3 |
| 6 | `movw %ax, (%rdi)` | `66 89 07` | 3 |
| 7 | `movw %ax, (%r8)` | `66 41 89 00` | 4 |
| 8 | `movw %ax, (%r15)` | `66 41 89 07` | 4 |
| 9 | `movw (%rsp), %ax` | `66 8b 04 24` | 4 |
| 10 | `movw %ax, (%rsp)` | `66 89 04 24` | 4 |
| 11 | `movw (%r12), %ax` | `66 41 8b 04 24` | 5 |
| 12 | `movw %ax, (%r12)` | `66 41 89 04 24` | 5 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`32da4986df5d506a87f7ddabab9cb3ac32adaf2887ee0ebcb90a54ab6de199ec`
(`fixture.asm`) and its `output_sha256` is
`609c7c8a59dc6cd29a3ac95e06789a37636505867e74664714deb32e654b3181`
(the 46-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:d00bce73e8dba85fab226287b5e838bc6b588892aa7786533b8e9ca71f19a978`.

## 6. What the slice defers

- The `REX.R` 16-bit register window (`%r8w`–`%r15w`), which `movw (%rsp), %r8w`
  shows as `66 44 8b 04 24`.
- An index or scale operand.
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The same shape at 64 and 8 bits where a window is still missing.
- The APX `d5` register window.
