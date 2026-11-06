# EXP-0068 -- the 32-bit `mov` family takes the `SIB` `disp8` shape

- Date: 2026-11-07
- Question: what does the `SIB` `disp8` shape cost at 32-bit width, how do
  `%rsp` and `%r12` differ, and where does the signed byte range end?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.39.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P43-gpr32-mov-mem-sib-disp8.oracle.json`
- Source: `research/evidence/experiments/EXP-0068/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0068/fixture.asm`
- Decision: `ADR-0066`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07, at displacements `8`
and `100`.

| Source | Bytes | Length |
|---|---|---|
| `movl 8(%rsp), %eax` | `8b 44 24 08` | 4 |
| `movl 100(%rsp), %edi` | `8b 7c 24 64` | 4 |
| `movl 8(%rsp), %r8d` | `44 8b 44 24 08` | 5 |
| `movl 100(%rsp), %r15d` | `44 8b 7c 24 64` | 5 |
| `movl %eax, 8(%rsp)` | `89 44 24 08` | 4 |
| `movl %edi, 100(%rsp)` | `89 7c 24 64` | 4 |
| `movl %r8d, 8(%rsp)` | `44 89 44 24 08` | 5 |
| `movl %r15d, 100(%rsp)` | `44 89 7c 24 64` | 5 |
| `movl 8(%r12), %eax` | `41 8b 44 24 08` | 5 |
| `movl 100(%r12), %edi` | `41 8b 7c 24 64` | 5 |
| `movl 8(%r12), %r8d` | `45 8b 44 24 08` | 5 |
| `movl 100(%r12), %r15d` | `45 8b 7c 24 64` | 5 |
| `movl %eax, 8(%r12)` | `41 89 44 24 08` | 5 |
| `movl %edi, 100(%r12)` | `41 89 7c 24 64` | 5 |
| `movl %r8d, 8(%r12)` | `45 89 44 24 08` | 5 |
| `movl %r15d, 100(%r12)` | `45 89 7c 24 64` | 5 |

`llvm-mc -disassemble` on `probes.txt` returns all sixteen byte strings as the
same registers and base.

The displacement range end is measured in both directions: `-128` is
`8b 44 24 80` and `127` is `8b 44 24 7f`, both four bytes.

## 2. Where the fields sit

| Row | Bytes | `REX` | `ModRM` | `SIB` | Register | `disp8` |
|---|---|---|---|---|---|---|
| `%rsp`, low | `8b 44 24 08` | none | `44` (`mod = 01`) | `24` | 0–7 at `[11,3]` | `[24,8]` |
| `%rsp`, `REX.R` | `44 8b 44 24 08` | `R = 1` | `44` | `24` | 8–15 at `[2,1]`, `[19,3]` | `[32,8]` |
| `%r12`, low | `41 8b 44 24 08` | `B = 1` | `44` | `24` | 0–7 at `[19,3]` | `[32,8]` |
| `%r12`, `REX.R` | `45 8b 44 24 08` | `R = 1`, `B = 1` | `44` | `24` | 8–15 at `[2,1]`, `[19,3]` | `[32,8]` |

`mod = 01` in every row, so `r/m = 100` selects the `SIB` byte `24` (scale 0,
index 100, base 100) and the signed displacement follows. The displacement
slot is `[24,8]` without a `REX` byte and `[32,8]` behind one, as in the 8-,
16- and 64-bit `SIB` families.

### The base is a form property

| Source | Bytes | Why |
|---|---|---|
| `movl 8(%rsp), %eax` | `8b 44 24 08` | `%rsp`, low register, no `REX` |
| `movl 8(%r12), %eax` | `41 8b 44 24 08` | `%r12` is the same `SIB = 24`, plus `REX.B` |
| `movl 8(%rsp), %r8d` | `44 8b 44 24 08` | `REX.R` for the register |
| `movl 8(%r12), %r8d` | `45 8b 44 24 08` | both bits in one `REX` byte |

The two bases share the low three bits `100`, so `SIB` cannot tell them apart;
only `REX.B` can. That is why the base is fixed in the form and not an
operand: a plan names one of the eight rows.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl -128(%rsp), %eax` | `8b 44 24 80` | 4 | the low `disp8` end |
| `movl 127(%rsp), %eax` | `8b 44 24 7f` | 4 | the high `disp8` end |
| `movl 128(%rsp), %eax` | `8b 84 24 80 00 00 00` | 7 | `mod = 10`, `disp32` |
| `movl 200(%rsp), %eax` | `8b 84 24 c8 00 00 00` | 7 | the same, `200` |
| `movl (%rsp), %eax` | `8b 04 24` | 3 | the `mod = 00` row (`0.36.0`) |
| `movl 8(%rbp), %eax` | `8b 45 08` | 3 | `%rbp` is a plain base, not `SIB` |
| `movl 8(%r13), %eax` | `41 8b 45 08` | 4 | `%r13` with `REX.B = 1` |
| `movl 8(%rsp), %r16d` | `d5 40 8b 44 24 08` | 6 | APX `d5` prefix |
| `movq 8(%rsp), %rax` | `48 8b 44 24 08` | 5 | 64-bit analogue |
| `movw 8(%rsp), %ax` | `66 8b 44 24 08` | 5 | 16-bit analogue |
| `movl 8(%rsp,%rax), %eax` | `8b 44 04 08` | 4 | `SIB` index, next axis |
| `movl 8(%rsp,%rax,4), %eax` | `8b 44 84 08` | 4 | index plus scale |

`adjacent-encoding.txt` records all twelve lines; no line is rejected.
`llvm-mc` normalises `movl 0(%rsp), %eax` to the `mod = 00` row (`8b 04 24`),
so a zero displacement cannot reach the `disp8` rows through the assembler.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cf` | names `x86:mov/r32-rsp-disp8/legacy` against `0.38.0` | `E-FORM-001` |
| `N01cg` | names `x86:mov/rsp-disp8-r32/legacy` against `0.38.0` | `E-FORM-001` |
| `N02bi` | omits the `disp` operand | `E-OPERAND-002` (`expected 2, found 1`) |
| `N03t` | supplies `disp = 128`, one past the signed byte | `E-RANGE-001` |
| `N14ar` | register `16` on the four-bit `REX.R` window | `E-OPERAND-004` |
| `N14as` | register `8` on the 3-bit low row | `E-OPERAND-004` |
| `N16bf` | register `0` on the `REX.R` row | `E-RANGE-004` |

The `disp32` claim is measured the same way: a copy of the fixture whose first
`disp` operand carries `target_type: disp32` is rejected with one
`E-OPERAND-001` at `/instructions/0/operands/1/target_type`
(`expected=disp8, found=disp32`), so the displacement width is the form and
not a value the row re-encodes.

## 5. The fixture

`X86-P43-gpr32-mov-mem-sib-disp8` is sixteen instructions and 76 bytes: each
of the eight rows twice, at displacement `8` and `100`.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 8(%rsp), %eax` | `8b 44 24 08` | 4 |
| 2 | `movl 100(%rsp), %edi` | `8b 7c 24 64` | 4 |
| 3 | `movl 8(%rsp), %r8d` | `44 8b 44 24 08` | 5 |
| 4 | `movl 100(%rsp), %r15d` | `44 8b 7c 24 64` | 5 |
| 5 | `movl %eax, 8(%rsp)` | `89 44 24 08` | 4 |
| 6 | `movl %edi, 100(%rsp)` | `89 7c 24 64` | 4 |
| 7 | `movl %r8d, 8(%rsp)` | `44 89 44 24 08` | 5 |
| 8 | `movl %r15d, 100(%rsp)` | `44 89 7c 24 64` | 5 |
| 9 | `movl 8(%r12), %eax` | `41 8b 44 24 08` | 5 |
| 10 | `movl 100(%r12), %edi` | `41 8b 7c 24 64` | 5 |
| 11 | `movl 8(%r12), %r8d` | `45 8b 44 24 08` | 5 |
| 12 | `movl 100(%r12), %r15d` | `45 8b 7c 24 64` | 5 |
| 13 | `movl %eax, 8(%r12)` | `41 89 44 24 08` | 5 |
| 14 | `movl %edi, 100(%r12)` | `41 89 7c 24 64` | 5 |
| 15 | `movl %r8d, 8(%r12)` | `45 89 44 24 08` | 5 |
| 16 | `movl %r15d, 100(%r12)` | `45 89 7c 24 64` | 5 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`86ae489c2148196abaf2290e7910558b2e676a43bb68cda498d3377b90d06125`
(`fixture.asm`) and its `output_sha256` is
`c020eceea4eede46355e31fb45f29b6be2c5fc34e20e407dfd29072ffe7a3bd7`
(the 76-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:2abf01787f5f36deddf2fa5da078bcc0b507c8eef85dec98c8725d02149a9b82`.

## 6. What the slice defers

- The `%rsp`/`%r12` `disp32` rows.
- An index or scale operand.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- The same shape at 16 and 8 bits.
- The APX `d5` register window (`%r16d`–`%r31d`).
