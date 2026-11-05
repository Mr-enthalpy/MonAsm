# EXP-0057 -- the 16-bit GPR `mov` rows with a 32-bit absolute address

- Date: 2026-11-06
- Question: how do the 16-bit GPR `mov` opcodes encode a 32-bit absolute
  address behind the `66` prefix, where does the register sit in each register
  window, and does the operand width narrow the address field?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.28.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P32-gpr16-mov-abs32.oracle.json`
- Source: `research/evidence/experiments/EXP-0057/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0057/fixture.asm`
- Decision: `ADR-0055`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movw 0x1234, %ax` | `66 8b 04 25 34 12 00 00` | 8 |
| `movw %ax, 0x1234` | `66 89 04 25 34 12 00 00` | 8 |
| `movw 0x0, %ax` | `66 8b 04 25 00 00 00 00` | 8 |
| `movw -1, %ax` | `66 8b 04 25 ff ff ff ff` | 8 |
| `movw 0x7fff, %ax` | `66 8b 04 25 ff 7f 00 00` | 8 |
| `movw -32768, %di` | `66 8b 3c 25 00 80 ff ff` | 8 |
| `movw 0x1234, %sp` | `66 8b 24 25 34 12 00 00` | 8 |
| `movw 0x1234, %r8w` | `66 44 8b 04 25 34 12 00 00` | 9 |
| `movw %r8w, 0x1234` | `66 44 89 04 25 34 12 00 00` | 9 |
| `movw -1, %r15w` | `66 44 8b 3c 25 ff ff ff ff` | 9 |
| `movw %r10w, 0x0` | `66 44 89 14 25 00 00 00 00` | 9 |
| `movw 0x1234, %r12w` | `66 44 8b 24 25 34 12 00 00` | 9 |
| `movw 0x1234, %r13w` | `66 44 8b 2c 25 34 12 00 00` | 9 |
| `movw 0x1234, %r14w` | `66 44 8b 34 25 34 12 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns all fourteen byte strings as the
same addresses, in the same order (`4660`, `4660`, `0`, `-1`, `32767`,
`-32768`, `4660`, `4660`, `4660`, `-1`, `0`, `4660`, `4660`, `4660`).

The first seven rows are eight bytes; the last seven are nine and carry `44`.
Every row starts with `66`, `ModRM` is `04`-family and the `SIB` byte is `25`.

## 2. Where the fields sit

The low window is eight bytes (64 bits):

| Byte | Bits | Value | Fields |
|---|---|---|---|
| `66` | `[0,8]` | `66` | operand-size prefix |
| opcode | `[8,8]` | `8b` (load) or `89` (store) | fixed per direction |
| `ModRM` | `[16,8]` | `04`/`0c`/`14`/`1c`/`24`/`2c`/`34`/`3c` | `mod = 00`, `r/m = 100`, `reg` = register |
| `SIB` | `[24,8]` | `25` | scale `00`, index `100` ("no index"), base `101` ("no base, `disp32`") |
| `disp32` | `[32,32]` | four bytes | signed address |

The extended window is nine bytes (72 bits) because the `REX` byte exists:

| Byte | Bits | Value | Fields |
|---|---|---|---|
| `66` | `[0,8]` | `66` | operand-size prefix |
| `REX` | `[8,8]` | `44` | `REX.W = 0`, `REX.R = 1`, `REX.X = 0`, `REX.B = 0` |
| opcode | `[16,8]` | `8b` (load) or `89` (store) | fixed per direction |
| `ModRM` | `[24,8]` | `04`/`0c`/…/`3c` | `mod = 00`, `r/m = 100`, `reg` = register low bits |
| `SIB` | `[32,8]` | `25` | same three constants |
| `disp32` | `[40,32]` | four bytes | signed address |

The prefix comes first: `movw 0x1234, %r8w` is `66 44 8b …`, never `44 66 8b
…`. `REX.R` is the register's fourth bit at `[10,1]`, so the extended rows are
`[27,3]` plus `[10,1]`; the low rows have only the three-bit `[19,3]`.

### The address does not narrow with the operand

The `66` prefix names the operand width and leaves the address a full 32-bit
field:

| Source | Address bytes | Value |
|---|---|---|
| `movw -1, %ax` | `ff ff ff ff` | `-1` |
| `movw -32768, %di` | `00 80 ff ff` | `-32768` sign-extended |
| `movw 0x7fff, %ax` | `ff 7f 00 00` | `32767` |
| `movw 0x7fffffff, %ax` | `ff ff ff 7f` | `2147483647` |

The field is signed 32-bit content, so `0x80000000` leaves the row:
`movw 0x80000000, %ax` assembles to `movabsw`
(`66 a1 00 00 00 80 00 00 00 00`, ten bytes) and the store to `66 a3`. That is
the `EC-05` second encoding, not a wider `disp32`, and a plan may not take it.

## 3. The window split

| Source | `REX` | `ModRM` | Register bits | Length |
|---|---|---|---|---|
| `0x1234, %ax` | none | `04` | 000 | 8 |
| `-32768, %di` | none | `3c` | 111 | 8 |
| `0x1234, %sp` | none | `24` | 100 | 8 |
| `0x1234, %r8w` | `44` | `04` | 1000 | 9 |
| `-1, %r15w` | `44` | `3c` | 1111 | 9 |
| `%r10w, 0x0` | `44` | `14` | 1010 | 9 |
| `0x1234, %r12w` | `44` | `24` | 1100 | 9 |
| `0x1234, %r13w` | `44` | `2c` | 1101 | 9 |
| `0x1234, %r14w` | `44` | `34` | 1110 | 9 |

The template's `44` implies `REX.R = 1`, so the extended row cannot carry
`%ax`–`%di`: the register slot is four bits wide and excludes `0`–`7`
(`E-RANGE-004`, `N16ae`).

## 4. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq 0x1234, %rax` | `48 8b 04 25 34 12 00 00` | 8 | 64-bit GPR row (`0.26.0`) |
| `movq %rax, 0x1234` | `48 89 04 25 34 12 00 00` | 8 | 64-bit GPR row (`0.26.0`) |
| `movl 0x1234, %eax` | `8b 04 25 34 12 00 00` | 7 | 32-bit GPR row (`0.27.0`) |
| `movl %eax, 0x1234` | `89 04 25 34 12 00 00` | 7 | 32-bit GPR row (`0.27.0`) |
| `movb 0x1234, %al` | `8a 04 25 34 12 00 00` | 7 | `8a` opcode, no prefix |
| `movb %al, 0x1234` | `88 04 25 34 12 00 00` | 7 | `88` opcode, no prefix |
| `movb %ah, 0x1234` | `88 24 25 34 12 00 00` | 7 | `ModRM.reg = 100` is `%ah` |
| `movabsw 0x1234, %ax` | `66 a1 34 12 00 00 00 00 00 00` | 10 | `moffs`, second legal encoding |
| `movw 0x1234, %r16w` | `66 d5 40 8b 04 25 34 12 00 00` | 10 | APX `d5` prefix between `66` and the opcode |
| `movw 0x1234, %r31w` | `66 d5 44 8b 3c 25 34 12 00 00` | 10 | APX, register 31 |
| `movw -1, %r8w` | `66 44 8b 04 25 ff ff ff ff` | 9 | ext window, signed end |
| `movw 0x7fff, %r8w` | `66 44 8b 04 25 ff 7f 00 00` | 9 | ext window, positive end |
| `movw %r10w, 0x0` | `66 44 89 14 25 00 00 00 00` | 9 | ext window, zero |

`movabsw` is ten bytes: the prefix, the `a1`/`a3` opcode and an eight-byte
address, which is the 64-bit-mode `moffs` width even for a 16-bit operand.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bi` | names `x86:mov/r16-abs32/legacy` against `0.27.0` | `E-FORM-001` |
| `N01bj` | names `x86:mov/abs32-r16-ext/legacy` against `0.27.0` | `E-FORM-001` |
| `N02am` | supplies a `base` operand to the absolute row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N02an` | carries the address as `disp8`/`x86.imm` | `E-OPERAND-001` on `target_type` |
| `N02ao` | carries `x86.gpr32`/`r32` on an `r16` row | `E-OPERAND-001` on `kind` and `target_type` |
| `N03o` | carries `disp32` content `2147483648` | `E-RANGE-001` |
| `N14ab` | carries register `16` on the extended row | `E-OPERAND-004` on `payload/reg` |
| `N16ae` | carries register `0` on the extended row | `E-RANGE-004` on `payload/reg` |

## 6. The fixture

`X86-P32-gpr16-mov-abs32` is six instructions and 51 bytes: four eight-byte
and two nine-byte rows.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 0x1234, %ax` | `66 8b 04 25 34 12 00 00` | 8 |
| 2 | `movw %ax, 0x1234` | `66 89 04 25 34 12 00 00` | 8 |
| 3 | `movw -1, %r8w` | `66 44 8b 04 25 ff ff ff ff` | 9 |
| 4 | `movw %r15w, 0x1234` | `66 44 89 3c 25 34 12 00 00` | 9 |
| 5 | `movw -32768, %di` | `66 8b 3c 25 00 80 ff ff` | 8 |
| 6 | `movw %r10w, 0x0` | `66 44 89 14 25 00 00 00 00` | 9 |

The fixture pins both directions, both windows, a positive address, `0`, `-1`
and the signed end point `-32768`, whose bytes are `00 80 ff ff`.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`18ffb4e92b465fc9ce617092cf57cfd8d484d626ce2d91a3a2920f3d7fb34828`
(`fixture.asm`) and its `output_sha256` is
`b250a1c7318e37c213edbfd0b7fba56510c54c688fbabb14767a933fff557be8`
(the 51-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
six lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- The 8-bit absolute rows: `8a`/`88` and the three `movb` register sets,
  including `%ah` at `88 24 25 …` and the `REX`-gated `%spl`–`%dil` family.
- The `REX.B` combination at this width: an extended base *and* an extended
  register share the one `REX` byte (`66 45 8b …`).
- The `0x67` address-size prefix: the same fields read as a 32-bit address
  model.
- A symbol or relocation in the address (`R_X86_64_32`, `R_X86_64_32S`).
- `moffs` for this width: `66 a1`/`66 a3` with an eight-byte address.
- The APX register window (`66 d5 40 …` / `66 d5 44 …`): `%r16w`–`%r31w` are a
  different prefix and a different register field.
- The absolute address under the other x86 opcode families.
