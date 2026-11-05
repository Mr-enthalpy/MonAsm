# EXP-0056 -- the 32-bit GPR `mov` rows with a 32-bit absolute address, in two register windows

- Date: 2026-11-06
- Question: how do the 32-bit GPR `mov` opcodes encode a 32-bit absolute
  address, where does the register sit in each register window, and which byte
  decides the length?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.27.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P31-gpr32-mov-abs32.oracle.json`
- Source: `research/evidence/experiments/EXP-0056/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0056/fixture.asm`
- Decision: `ADR-0054`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movl 0x1234, %eax` | `8b 04 25 34 12 00 00` | 7 |
| `movl %eax, 0x1234` | `89 04 25 34 12 00 00` | 7 |
| `movl 0x0, %eax` | `8b 04 25 00 00 00 00` | 7 |
| `movl -1, %eax` | `8b 04 25 ff ff ff ff` | 7 |
| `movl 0x7fffffff, %eax` | `8b 04 25 ff ff ff 7f` | 7 |
| `movl -2147483648, %edi` | `8b 3c 25 00 00 00 80` | 7 |
| `movl 0x1234, %esp` | `8b 24 25 34 12 00 00` | 7 |
| `movl 0x1234, %r8d` | `44 8b 04 25 34 12 00 00` | 8 |
| `movl %r8d, 0x1234` | `44 89 04 25 34 12 00 00` | 8 |
| `movl -1, %r15d` | `44 8b 3c 25 ff ff ff ff` | 8 |
| `movl %r10d, 0x0` | `44 89 14 25 00 00 00 00` | 8 |
| `movl 0x1234, %r12d` | `44 8b 24 25 34 12 00 00` | 8 |
| `movl 0x1234, %r13d` | `44 8b 2c 25 34 12 00 00` | 8 |
| `movl 0x1234, %r14d` | `44 8b 34 25 34 12 00 00` | 8 |

`llvm-mc -disassemble` on `probes.txt` returns all fourteen byte strings as the
same addresses, in the same order (`4660`, `4660`, `0`, `-1`, `2147483647`,
`-2147483648`, `4660`, `4660`, `4660`, `-1`, `0`, `4660`, `4660`, `4660`).

The first seven rows are seven bytes and carry no `REX` byte; the last seven
are eight bytes and carry `44`. `ModRM` is `04`-family and the `SIB` byte is
`25` in all of them.

## 2. Where the fields sit

The low window is seven bytes (56 bits):

| Byte | Bits | Value | Fields |
|---|---|---|---|
| opcode | `[0,8]` | `8b` (load) or `89` (store) | fixed per direction |
| `ModRM` | `[8,8]` | `04`/`0c`/`14`/`1c`/`24`/`2c`/`34`/`3c` | `mod = 00`, `r/m = 100`, `reg` = register |
| `SIB` | `[16,8]` | `25` | scale `00`, index `100` ("no index"), base `101` ("no base, `disp32`") |
| `disp32` | `[24,32]` | four bytes | signed address |

The extended window is eight bytes (64 bits) because the `REX` byte exists:

| Byte | Bits | Value | Fields |
|---|---|---|---|
| `REX` | `[0,8]` | `44` | `REX.W = 0`, `REX.R = 1`, `REX.X = 0`, `REX.B = 0` |
| opcode | `[8,8]` | `8b` (load) or `89` (store) | fixed per direction |
| `ModRM` | `[16,8]` | `04`/`0c`/`14`/`1c`/`24`/`2c`/`34`/`3c` | `mod = 00`, `r/m = 100`, `reg` = register low bits |
| `SIB` | `[24,8]` | `25` | same three constants |
| `disp32` | `[32,32]` | four bytes | signed address |

`REX.R` is the register's fourth bit at `[2,1]`, so the extended rows are
`[19,3]` plus `[2,1]`; the low rows have only the three-bit `[11,3]`, because
there is no byte to hold a fourth bit.

## 3. The window split

The same source instruction has two lengths, and only the register decides
which one:

| Source | `REX` | `ModRM` | Register bits | Length |
|---|---|---|---|---|
| `0x1234, %eax` | none | `04` | 000 | 7 |
| `-2147483648, %edi` | none | `3c` | 111 | 7 |
| `0x1234, %esp` | none | `24` | 100 | 7 |
| `0x1234, %r8d` | `44` | `04` | 1000 | 8 |
| `-1, %r15d` | `44` | `3c` | 1111 | 8 |
| `%r10d, 0x0` | `44` | `14` | 1010 | 8 |
| `0x1234, %r12d` | `44` | `24` | 1100 | 8 |
| `0x1234, %r13d` | `44` | `2c` | 1101 | 8 |
| `0x1234, %r14d` | `44` | `34` | 1110 | 8 |

Both directions agree: `movl %r8d, 0x1234` is `44 89 04 25 …` and
`movl %r10d, 0x0` is `44 89 14 25 …`; `movl %eax, 0x1234` is
`89 04 25 …` with no `REX` byte.

The template's `44` implies `REX.R = 1`, so the extended row cannot carry
`%eax`–`%edi`: the register slot is four bits wide and excludes `0`–`7`
(`E-RANGE-004`, `N16ad`). `%r16d` is outside either field:
`movl 0x1234, %r16d` assembles to `d5 40 8b 04 25 34 12 00 00` and
`%r31d` to `d5 44 8b 3c 25 34 12 00 00` — an APX `d5` prefix, a different
shape this slice does not carry, so `16` is `E-OPERAND-004` (`N14aa`).

## 4. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq 0x1234, %rax` | `48 8b 04 25 34 12 00 00` | 8 | 64-bit GPR row (`0.26.0`) |
| `movq %rax, 0x1234` | `48 89 04 25 34 12 00 00` | 8 | 64-bit GPR row (`0.26.0`) |
| `movw 0x1234, %ax` | `66 8b 04 25 34 12 00 00` | 8 | operand-size prefix |
| `movw %ax, 0x1234` | `66 89 04 25 34 12 00 00` | 8 | operand-size prefix |
| `movb 0x1234, %al` | `8a 04 25 34 12 00 00` | 7 | `8a` opcode |
| `movb %al, 0x1234` | `88 04 25 34 12 00 00` | 7 | `88` opcode |
| `movb %ah, 0x1234` | `88 24 25 34 12 00 00` | 7 | `ModRM.reg = 100` is `%ah`, no `REX` |
| `movabsl 0x1234, %eax` | `a1 34 12 00 00 00 00 00 00` | 10 | `moffs`, second legal encoding |
| `movabsb 0x1234, %al` | `a0 34 12 00 00 00 00 00 00` | 10 | `moffs`, second legal encoding |
| `movl 0x1234, %r16d` | `d5 40 8b 04 25 34 12 00 00` | 9 | APX prefix |
| `movl 0x1234, %r31d` | `d5 44 8b 3c 25 34 12 00 00` | 9 | APX prefix |
| `movl -1, %r8d` | `44 8b 04 25 ff ff ff ff` | 8 | ext window, signed end |
| `movl 0x7fffffff, %r8d` | `44 8b 04 25 ff ff ff 7f` | 8 | ext window, signed end |

The `%ah` row is worth noting: `88 24 25` reads as `ModRM.reg = 100`, which in
the low byte register set is `%ah` rather than `%esp`, so the byte-register
slice has a register set that is neither `%al`–`%dil` nor `%r8b`–`%r15b`.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bg` | names `x86:mov/r32-abs32/legacy` against `0.26.0` | `E-FORM-001` |
| `N01bh` | names `x86:mov/abs32-r32-ext/legacy` against `0.26.0` | `E-FORM-001` |
| `N02aj` | supplies a `base` operand to the absolute row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N02ak` | carries the address as `disp8`/`x86.imm` | `E-OPERAND-001` on `target_type` |
| `N02al` | carries `x86.gpr64`/`r64` on an `r32` row | `E-OPERAND-001` on `kind` and `target_type` |
| `N03n` | carries `disp32` content `2147483648` | `E-RANGE-001` |
| `N14aa` | carries register `16` on the extended row | `E-OPERAND-004` on `payload/reg` |
| `N16ad` | carries register `0` on the extended row | `E-RANGE-004` on `payload/reg` |

## 6. The fixture

`X86-P31-gpr32-mov-abs32` is six instructions and 45 bytes: four seven-byte
and two eight-byte rows, so it is the first fixture whose instructions are not
all one length.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movl 0x1234, %eax` | `8b 04 25 34 12 00 00` | 7 |
| 2 | `movl %eax, 0x1234` | `89 04 25 34 12 00 00` | 7 |
| 3 | `movl -1, %r8d` | `44 8b 04 25 ff ff ff ff` | 8 |
| 4 | `movl %r15d, 0x1234` | `44 89 3c 25 34 12 00 00` | 8 |
| 5 | `movl -2147483648, %edi` | `8b 3c 25 00 00 00 80` | 7 |
| 6 | `movl %r10d, 0x0` | `44 89 14 25 00 00 00 00` | 8 |

The fixture pins both directions, both windows, a positive address, `0`, `-1`
and the signed end point `-2147483648`, whose bytes are `00 00 00 80`.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`6420e26c0735526f1a65b10f7ec261556397f468298e5aa104395d58174b5c76`
(`fixture.asm`) and its `output_sha256` is
`4ff07a6ff2c12bbfed0c8b0e10bd06c1cf455a440a3d8b9e8755725d26c3c81b`
(the 45-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
six lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- The 16- and 8-bit absolute rows: `66 8b`, and the three `movb` register sets
  (including `%ah` at `88 24 25 …`, with no `REX` byte).
- The `0x67` address-size prefix: the same fields read as a 32-bit address
  model.
- A symbol or relocation in the address (`R_X86_64_32`, `R_X86_64_32S`): the
  displacement stops being content and becomes a fixup.
- `moffs` for this width: `a1`/`a3` with an eight-byte address, `EC-05` as a
  new row rather than a second spelling.
- The APX register window (`d5 40 …` / `d5 44 …`): `%r16d`–`%r31d` are a
  different prefix and a different register field.
- The absolute address under the other x86 opcode families (`add`, `cmp`, the
  SSE and EVEX families at other mnemonic bytes).
