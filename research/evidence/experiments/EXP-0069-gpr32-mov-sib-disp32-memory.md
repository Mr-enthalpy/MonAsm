# EXP-0069 -- the 32-bit `mov` family takes the `SIB` `disp32` shape

- Date: 2026-11-07
- Question: what does the `SIB` `disp32` shape cost at 32-bit width, how do
  `%rsp` and `%r12` differ, and where does the signed 32-bit range end?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.40.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P44-gpr32-mov-mem-sib-disp32.oracle.json`
- Source: `research/evidence/experiments/EXP-0069/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0069/fixture.asm`
- Decision: `ADR-0067`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07, at displacements `200`
and `100000`.

| Source | Bytes | Length |
|---|---|---|
| `movl 200(%rsp), %eax` | `8b 84 24 c8 00 00 00` | 7 |
| `movl 100000(%rsp), %edi` | `8b bc 24 a0 86 01 00` | 7 |
| `movl 200(%rsp), %r8d` | `44 8b 84 24 c8 00 00 00` | 8 |
| `movl 100000(%rsp), %r15d` | `44 8b bc 24 a0 86 01 00` | 8 |
| `movl %eax, 200(%rsp)` | `89 84 24 c8 00 00 00` | 7 |
| `movl %edi, 100000(%rsp)` | `89 bc 24 a0 86 01 00` | 7 |
| `movl %r8d, 200(%rsp)` | `44 89 84 24 c8 00 00 00` | 8 |
| `movl %r15d, 100000(%rsp)` | `44 89 bc 24 a0 86 01 00` | 8 |
| `movl 200(%r12), %eax` | `41 8b 84 24 c8 00 00 00` | 8 |
| `movl 100000(%r12), %edi` | `41 8b bc 24 a0 86 01 00` | 8 |
| `movl 200(%r12), %r8d` | `45 8b 84 24 c8 00 00 00` | 8 |
| `movl 100000(%r12), %r15d` | `45 8b bc 24 a0 86 01 00` | 8 |
| `movl %eax, 200(%r12)` | `41 89 84 24 c8 00 00 00` | 8 |
| `movl %edi, 100000(%r12)` | `41 89 bc 24 a0 86 01 00` | 8 |
| `movl %r8d, 200(%r12)` | `45 89 84 24 c8 00 00 00` | 8 |
| `movl %r15d, 100000(%r12)` | `45 89 bc 24 a0 86 01 00` | 8 |

`llvm-mc -disassemble` on `probes.txt` returns all sixteen byte strings as the
same registers and base.

The displacement range end is measured in both directions: `-2147483648` is
`8b 84 24 00 00 00 80` and `2147483647` is `8b 84 24 ff ff ff 7f`, both seven
bytes.

## 2. Where the fields sit

| Row | Bytes | `REX` | `ModRM` | `SIB` | Register | `disp32` |
|---|---|---|---|---|---|---|
| `%rsp`, low | `8b 84 24 c8 00 00 00` | none | `84` (`mod = 10`) | `24` | 0–7 at `[11,3]` | `[24,32]` |
| `%rsp`, `REX.R` | `44 8b 84 24 c8 00 00 00` | `R = 1` | `84` | `24` | 8–15 at `[2,1]`, `[19,3]` | `[32,32]` |
| `%r12`, low | `41 8b 84 24 c8 00 00 00` | `B = 1` | `84` | `24` | 0–7 at `[19,3]` | `[32,32]` |
| `%r12`, `REX.R` | `45 8b 84 24 c8 00 00 00` | `R = 1`, `B = 1` | `84` | `24` | 8–15 at `[2,1]`, `[19,3]` | `[32,32]` |

`mod = 10` in every row, so `r/m = 100` selects the `SIB` byte `24` (scale 0,
index 100, base 100) and the signed 32-bit displacement follows. The
displacement slot is `[24,32]` without a `REX` byte and `[32,32]` behind one,
as in the 8-, 16- and 64-bit `SIB` families.

### The base is a form property

| Source | Bytes | Why |
|---|---|---|
| `movl 200(%rsp), %eax` | `8b 84 24 c8 00 00 00` | `%rsp`, low register, no `REX` |
| `movl 200(%r12), %eax` | `41 8b 84 24 c8 00 00 00` | `%r12` is the same `SIB = 24`, plus `REX.B` |
| `movl 200(%rsp), %r8d` | `44 8b 84 24 c8 00 00 00` | `REX.R` for the register |
| `movl 200(%r12), %r8d` | `45 8b 84 24 c8 00 00 00` | both bits in one `REX` byte |

The two bases share the low three bits `100`, so `SIB` cannot tell them apart;
only `REX.B` can. That is why the base is fixed in the form and not an
operand: a plan names one of the eight rows.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl -2147483648(%rsp), %eax` | `8b 84 24 00 00 00 80` | 7 | the low `disp32` end |
| `movl 2147483647(%rsp), %eax` | `8b 84 24 ff ff ff 7f` | 7 | the high `disp32` end |
| `movl 128(%rsp), %eax` | `8b 84 24 80 00 00 00` | 7 | `128` belongs here, not to `disp8` |
| `movl 8(%rsp), %eax` | `8b 44 24 08` | 4 | the `disp8` row (`0.39.0`) |
| `movl (%rsp), %eax` | `8b 04 24` | 3 | the `mod = 00` row (`0.36.0`) |
| `movl (%r12), %eax` | `41 8b 04 24` | 4 | the same, `REX.B` |
| `movl 200(%rbp), %eax` | `8b 85 c8 00 00 00` | 6 | `%rbp` is a plain base, not `SIB` |
| `movl 200(%r13), %eax` | `41 8b 85 c8 00 00 00` | 7 | `%r13` with `REX.B = 1` |
| `movl 200(%rsp), %r16d` | `d5 40 8b 84 24 c8 00 00 00` | 9 | APX `d5` prefix |
| `movq 200(%rsp), %rax` | `48 8b 84 24 c8 00 00 00` | 8 | 64-bit analogue |
| `movw 200(%rsp), %ax` | `66 8b 84 24 c8 00 00 00` | 8 | 16-bit analogue |
| `movl 200(%rsp,%rax), %eax` | `8b 84 04 c8 00 00 00` | 7 | `SIB` index, next axis |
| `movl 200(%rsp,%rax,4), %eax` | `8b 84 84 c8 00 00 00` | 7 | index plus scale |

`adjacent-encoding.txt` records all thirteen lines; no line is rejected.
`llvm-mc` normalises `movl 0(%rsp), %eax` to the `mod = 00` row (`8b 04 24`),
so a zero displacement cannot reach the `disp32` rows through the assembler.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01ch` | names `x86:mov/r32-rsp-disp32/legacy` against `0.39.0` | `E-FORM-001` |
| `N01ci` | names `x86:mov/rsp-disp32-r32/legacy` against `0.39.0` | `E-FORM-001` |
| `N02bj` | omits the `disp` operand | `E-OPERAND-002` (`expected 2, found 1`) |
| `N03u` | supplies `disp = 2147483648`, one past the signed 32-bit field | `E-RANGE-001` |
| `N14at` | register `16` on the four-bit `REX.R` window | `E-OPERAND-004` |
| `N14au` | register `8` on the 3-bit low row | `E-OPERAND-004` |
| `N16bg` | register `0` on the `REX.R` row | `E-RANGE-004` |

The `disp8` claim is measured the same way: a copy of the fixture whose first
`disp` operand carries `target_type: disp8` is rejected with one
`E-OPERAND-001` at `/instructions/0/operands/1/target_type`
(`expected=disp32, found=disp8`), so the displacement width is the form and
not a value the row re-encodes.

## 5. The fixture

`X86-P44-gpr32-mov-mem-sib-disp32` is sixteen instructions and 124 bytes: each
of the eight rows twice, at displacement `200` and `100000`.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 200(%rsp), %eax` | `8b 84 24 c8 00 00 00` | 7 |
| 2 | `movl 100000(%rsp), %edi` | `8b bc 24 a0 86 01 00` | 7 |
| 3 | `movl 200(%rsp), %r8d` | `44 8b 84 24 c8 00 00 00` | 8 |
| 4 | `movl 100000(%rsp), %r15d` | `44 8b bc 24 a0 86 01 00` | 8 |
| 5 | `movl %eax, 200(%rsp)` | `89 84 24 c8 00 00 00` | 7 |
| 6 | `movl %edi, 100000(%rsp)` | `89 bc 24 a0 86 01 00` | 7 |
| 7 | `movl %r8d, 200(%rsp)` | `44 89 84 24 c8 00 00 00` | 8 |
| 8 | `movl %r15d, 100000(%rsp)` | `44 89 bc 24 a0 86 01 00` | 8 |
| 9 | `movl 200(%r12), %eax` | `41 8b 84 24 c8 00 00 00` | 8 |
| 10 | `movl 100000(%r12), %edi` | `41 8b bc 24 a0 86 01 00` | 8 |
| 11 | `movl 200(%r12), %r8d` | `45 8b 84 24 c8 00 00 00` | 8 |
| 12 | `movl 100000(%r12), %r15d` | `45 8b bc 24 a0 86 01 00` | 8 |
| 13 | `movl %eax, 200(%r12)` | `41 89 84 24 c8 00 00 00` | 8 |
| 14 | `movl %edi, 100000(%r12)` | `41 89 bc 24 a0 86 01 00` | 8 |
| 15 | `movl %r8d, 200(%r12)` | `45 89 84 24 c8 00 00 00` | 8 |
| 16 | `movl %r15d, 100000(%r12)` | `45 89 bc 24 a0 86 01 00` | 8 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`9f0e62d964222c508af5690b08ec5717d351926cddc0107a2f87e5b672097347`
(`fixture.asm`) and its `output_sha256` is
`de51cff2cc2a4b6035b821b62d41fe76f3ebaac46ec9beba0947d6154b9ee3fc`
(the 124-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:48e2bb488dac9ff21639d8ebb6ae1d300a38cf0d4591bd1facf509138f5d8872`.

## 6. What the slice defers

- An index or scale operand.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- The same shape at 16 and 8 bits.
- The APX `d5` register window (`%r16d`–`%r31d`).
