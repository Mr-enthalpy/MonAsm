# EXP-0055 -- the 64-bit GPR `mov` rows with a 32-bit absolute address

- Date: 2026-11-06
- Question: how do the 64-bit GPR `mov` opcodes encode a 32-bit absolute
  address, which fields stay constant, how does the register window work, and
  what is the second legal encoding (`moffs`)?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.26.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P30-gpr-mov-abs32.oracle.json`
- Source: `research/evidence/experiments/EXP-0055/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0055/fixture.asm`
- Decision: `ADR-0053`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movq 0x1234, %rax` | `48 8b 04 25 34 12 00 00` | 8 |
| `movq %rax, 0x1234` | `48 89 04 25 34 12 00 00` | 8 |
| `movq 0x0, %rax` | `48 8b 04 25 00 00 00 00` | 8 |
| `movq -1, %rax` | `48 8b 04 25 ff ff ff ff` | 8 |
| `movq 0x7fffffff, %rax` | `48 8b 04 25 ff ff ff 7f` | 8 |
| `movq 0x1234, %r8` | `4c 8b 04 25 34 12 00 00` | 8 |
| `movq %r15, 0x1234` | `4c 89 3c 25 34 12 00 00` | 8 |
| `movq -2147483648, %rdi` | `48 8b 3c 25 00 00 00 80` | 8 |
| `movabsq 0x1234, %rax` | `48 a1 34 12 00 00 00 00 00 00` | 10 |
| `movabsq %rax, 0x1234` | `48 a3 34 12 00 00 00 00 00 00` | 10 |

`llvm-mc -disassemble` on `probes.txt` returns the first eight byte strings as
the same eight addresses, in the same order (`4660`, `4660`, `0`, `-1`,
`2147483647`, `4660`, `4660`, `-2147483648`).

Every `SIB`-absolute row is eight bytes. `ModRM` is `04` and the `SIB` byte is
`25` in all of them:

| Byte | Value | Fields |
|---|---|---|
| `REX` | `48` or `4c` | `REX.W` plus `REX.R` from the register |
| opcode | `8b` (load) or `89` (store) | fixed per direction |
| `ModRM` | `04`/`0c`/`14`/`1c`/`24`/`2c`/`34`/`3c` | `mod = 00`, `r/m = 100` (`SIB` escape), `reg` = register low bits |
| `SIB` | `25` | scale `00`, index `100` ("no index"), base `101` ("no base, `disp32`") |
| `disp32` | four bytes | signed address at `[32,32]` |

The `SIB` byte therefore has no operand-owned field at all: both register
fields are constants and the scale is constant zero.

## 2. Where the fields sit

| Field | Template bits | Placement |
|---|---|---|
| `REX.R` | `[2,1]` | the register's fourth bit, raw |
| `ModRM.reg` | `[19,3]` | the register's low three bits |
| `ModRM`/`SIB` | `[16,8]`/`[24,8]` | template: `04` and `25` |
| `disp32` | `[32,32]` | the address itself, signed |

`REX.W` is template bit 3 of byte 0, so the low registers keep `48` and only
the fourth bit moves. The register slot is four bits wide and written raw:

| Source | `REX` | `ModRM` | Register bits |
|---|---|---|---|
| `0x1234, %rax` | `48` | `04` | 0000 |
| `-2147483648, %rdi` | `48` | `3c` | 0111 |
| `0x1234, %r8` | `4c` | `04` | 1000 |
| `0x1234, %r9` | `4c` | `0c` | 1001 |
| `%r10, 0x0` | `4c` | `14` | 1010 |
| `%r15, 0x1234` | `4c` | `3c` | 1111 |

Both directions use the same four-bit window: `movq %r8, 0x1234` is
`4c 89 04 25 …` and `movq %r10, 0x1234` is `4c 89 14 25 …`.

`%r16` is outside the field: `movq 0x1234, %r16` assembles to
`d5 48 8b 04 25 34 12 00 00` — an APX `d5` prefix, a different shape this
slice does not carry, so a plan carrying `16` is `E-OPERAND-004` (`N14z`).

## 3. `moffs` is the second legal encoding, and it is longer

`movabsq` reaches the `A0`–`A3` opcodes, which take an eight-byte absolute
address:

| Source | Bytes | Length |
|---|---|---|
| `movabsq 0x1234, %rax` | `48 a1 34 12 00 00 00 00 00 00` | 10 |
| `movabsq %rax, 0x1234` | `48 a3 34 12 00 00 00 00 00 00` | 10 |

Two bytes longer than the `SIB` form for the same source instruction. The
assembler is willing to pick it by itself:

| Probe | Result |
|---|---|
| `movq 0x80000000, %rax` | `48 a1 00 00 00 00 80 00 00 00` (switches to `moffs`) |
| `movq 0x100000000, %rax` | `48 a1 00 00 00 00 00 01 00 00 00` (switches to `moffs`) |

The value does not fit the signed 32-bit field, so `llvm-mc` changes the form
and the length. A plan may not: `0x80000000` carried as `disp32` content is
`E-RANGE-001` (`N03m`), and the `moffs` row does not exist at all
(`N01bf`). That is `EC-05`, frozen by this slice with the `form variant`
carrier.

## 4. The other widths and the neighbours

The address can be written three other ways under the same `mov` mnemonic, and
each is a different byte string:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq 0x1234(%rax), %rax` | `48 8b 80 34 12 00 00` | 7 | base + `disp32`, no `SIB` |
| `movq 0x1234(%rip), %rax` | `48 8b 05 34 12 00 00` | 7 | `RIP`-relative, no `SIB` |
| `movq 0x1234(,%rax,4), %rax` | `48 8b 04 85 34 12 00 00` | 8 | index, no base |
| `movq 0x1234, %rax` | `48 8b 04 25 34 12 00 00` | 8 | absolute (this slice) |

The indexed row and the absolute row differ only in the `SIB` byte: `85`
writes index `000` with scale `10`, `25` has index `100` and scale `00`. Base
`101` and the four displacement bytes are the same in both.

The narrower absolute rows are the same shape with different prefixes, and the
32-bit one is not a single row:

| Source | Bytes | Length |
|---|---|---|
| `movl 0x1234, %eax` | `8b 04 25 34 12 00 00` | 7 |
| `movl %eax, 0x1234` | `89 04 25 34 12 00 00` | 7 |
| `movl 0x1234, %r8d` | `44 8b 04 25 34 12 00 00` | 8 |
| `movw 0x1234, %ax` | `66 8b 04 25 34 12 00 00` | 8 |
| `movw %ax, 0x1234` | `66 89 04 25 34 12 00 00` | 8 |
| `movb 0x1234, %al` | `8a 04 25 34 12 00 00` | 7 |
| `movb %al, 0x1234` | `88 04 25 34 12 00 00` | 7 |
| `movb %ah, 0x1234` | `88 24 25 34 12 00 00` | 7 |

`movl 0x1234, %r8d` is eight bytes because the `REX` byte exists only for the
high registers, so the 32-bit family needs its own `-ext` form. The 16- and
8-bit rows carry a prefix or a different register set; both are separate
slices.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bd` | names `x86:mov/r64-abs32/legacy` against `0.25.0` | `E-FORM-001` |
| `N01be` | names `x86:mov/abs32-r64/legacy` against `0.25.0` | `E-FORM-001` |
| `N01bf` | names `x86:mov/r64-moffs64/legacy` against `0.26.0` | `E-FORM-001` |
| `N02ah` | supplies a `base` operand to the absolute row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N02ai` | carries the address as `disp8`/`x86.imm` | `E-OPERAND-001` on `target_type` |
| `N03m` | carries `disp32` content `2147483648` | `E-RANGE-001` |
| `N14z` | carries register `16` | `E-OPERAND-004` on `payload/reg` |

## 6. The fixture

`X86-P30-gpr-mov-abs32` is six instructions and 48 bytes, all eight bytes: both
directions at a low and a high register, plus the signed ends.

| # | Source | Bytes |
|---|---|---|
| 1 | `movq 0x1234, %rax` | `48 8b 04 25 34 12 00 00` |
| 2 | `movq %rax, 0x1234` | `48 89 04 25 34 12 00 00` |
| 3 | `movq -1, %r15` | `4c 8b 3c 25 ff ff ff ff` |
| 4 | `movq %r8, 0x1234` | `4c 89 04 25 34 12 00 00` |
| 5 | `movq -2147483648, %rdi` | `48 8b 3c 25 00 00 00 80` |
| 6 | `movq %r10, 0x0` | `4c 89 14 25 00 00 00 00` |

The fixture pins both directions, the `REX.R` bit on (`%r8`/`%r10`/`%r15`) and
off (`%rax`/`%rdi`), a positive address, `0`, `-1` and the signed end point
`-2147483648`, whose bytes are `00 00 00 80`.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`fa4f4f7c73ae84159f1804df0968107d7c7a9331679744a0ae437b4c53945836`
(`fixture.asm`) and its `output_sha256` is
`4ed75958b838dacfb75704bd25243c14cc47ed4bb346a8ec8d4f202cdb9ddc18`
(the 48-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
six lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- The 32-bit `-ext` shape: `44 8b 04 25 …` for `%r8d`–`%r15d` beside
  `8b 04 25 …` for `%eax`–`%edi` is a length decision.
- The 16- and 8-bit absolute rows: `66 8b` and the three `movb` register sets
  (including `%ah` at `88 24 25 …`, with no `REX` byte).
- The `0x67` address-size prefix: the same fields read as a 32-bit address
  model.
- A symbol or relocation in the address (`R_X86_64_32`, `R_X86_64_32S`): the
  displacement stops being content and becomes a fixup.
- `moffs` for any other width: `EC-05` re-opens as a new row, not a second
  spelling.
- The absolute address under the other x86 opcode families (`add`, `cmp`, the
  SSE and EVEX families at other mnemonic bytes).
