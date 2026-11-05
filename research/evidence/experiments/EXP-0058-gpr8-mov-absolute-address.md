# EXP-0058 -- the 8-bit GPR `mov` rows with a 32-bit absolute address

- Date: 2026-11-06
- Question: how do the 8-bit GPR `mov` opcodes encode a 32-bit absolute
  address, how many register windows does the same three-bit field open, and
  does the operand width narrow the address field?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.29.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P33-gpr8-mov-abs32.oracle.json`
- Source: `research/evidence/experiments/EXP-0058/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0058/fixture.asm`
- Decision: `ADR-0056`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movb 0x1234, %al` | `8a 04 25 34 12 00 00` | 7 |
| `movb %al, 0x1234` | `88 04 25 34 12 00 00` | 7 |
| `movb 0x1234, %cl` | `8a 0c 25 34 12 00 00` | 7 |
| `movb 0x1234, %dl` | `8a 14 25 34 12 00 00` | 7 |
| `movb 0x1234, %bl` | `8a 1c 25 34 12 00 00` | 7 |
| `movb 0x1234, %ah` | `8a 24 25 34 12 00 00` | 7 |
| `movb %ah, 0x1234` | `88 24 25 34 12 00 00` | 7 |
| `movb 0x1234, %ch` | `8a 2c 25 34 12 00 00` | 7 |
| `movb 0x1234, %dh` | `8a 34 25 34 12 00 00` | 7 |
| `movb 0x1234, %bh` | `8a 3c 25 34 12 00 00` | 7 |
| `movb 0x1234, %spl` | `40 8a 24 25 34 12 00 00` | 8 |
| `movb %spl, 0x1234` | `40 88 24 25 34 12 00 00` | 8 |
| `movb 0x1234, %bpl` | `40 8a 2c 25 34 12 00 00` | 8 |
| `movb 0x1234, %sil` | `40 8a 34 25 34 12 00 00` | 8 |
| `movb 0x1234, %dil` | `40 8a 3c 25 34 12 00 00` | 8 |
| `movb 0x1234, %r8b` | `44 8a 04 25 34 12 00 00` | 8 |
| `movb %r8b, 0x1234` | `44 88 04 25 34 12 00 00` | 8 |
| `movb 0x1234, %r9b` | `44 8a 0c 25 34 12 00 00` | 8 |
| `movb 0x1234, %r12b` | `44 8a 24 25 34 12 00 00` | 8 |
| `movb 0x1234, %r15b` | `44 8a 3c 25 34 12 00 00` | 8 |
| `movb %r15b, 0x1234` | `44 88 3c 25 34 12 00 00` | 8 |
| `movb -1, %al` | `8a 04 25 ff ff ff ff` | 7 |
| `movb 0x7f, %ah` | `8a 24 25 7f 00 00 00` | 7 |
| `movb -128, %bl` | `8a 1c 25 80 ff ff ff` | 7 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty-four byte strings as
the same registers and addresses, including `40 8a 24 25 …` as `%spl` and
`8a 24 25 …` as `%ah`.

## 2. Where the fields sit

The low (`%al`-`%bl`) and high (`%ah`-`%bh`) windows are seven bytes (56 bits)
and share one layout:

| Byte | Bits | Value | Fields |
|---|---|---|---|
| opcode | `[0,8]` | `8a` (load) or `88` (store) | fixed per direction |
| `ModRM` | `[8,8]` | `04`/`0c`/`14`/`1c` or `24`/`2c`/`34`/`3c` | `mod = 00`, `r/m = 100`, `reg` = register |
| `SIB` | `[16,8]` | `25` | scale `00`, index `100` ("no index"), base `101` ("no base, `disp32`") |
| `disp32` | `[24,32]` | four bytes | signed address |

The two `REX` windows are eight bytes (64 bits) and also share one layout:

| Byte | Bits | Value | Fields |
|---|---|---|---|
| `REX` | `[0,8]` | `40` or `44` | `REX.R` is the register's fourth bit; `W`, `X`, `B` are `0` |
| opcode | `[8,8]` | `8a` (load) or `88` (store) | fixed per direction |
| `ModRM` | `[16,8]` | `04`-family or `24`-family | `mod = 00`, `r/m = 100`, `reg` = register low bits |
| `SIB` | `[24,8]` | `25` | same three constants |
| `disp32` | `[32,32]` | four bytes | signed address |

`REX.R` is bit 2 of the first byte, so the extended slot is `[19,3]` plus
`[2,1]`. The template's `REX = 44` therefore cannot carry `%al`-`%dil`, and a
plan that names register `0` there would encode `%r8b` at the same byte.

### The address does not narrow with the operand

| Source | Address bytes | Value |
|---|---|---|
| `movb -1, %al` | `ff ff ff ff` | `-1` |
| `movb -128, %bl` | `80 ff ff ff` | `-128` sign-extended |
| `movb 0x7f, %ah` | `7f 00 00 00` | `127` |
| `movb 0x7fffffff, %al` | `ff ff ff 7f` | `2147483647` |

`0x80000000` is the interesting case, because the two answers differ:

| Source | Bytes | Length | Form taken |
|---|---|---|---|
| `movb 0x80000000, %al` | `a0 00 00 00 80 00 00 00 00` | 9 | `movabsb` |
| `movb %al, 0x80000000` | `a2 00 00 00 80 00 00 00 00` | 9 | `movabsb` |
| `movb %r8b, 0x80000000` | `44 88 04 25 00 00 00 80` | 8 | stays on the `88` row |

`llvm-mc` has no `moffs` form for `%r8b` here, so it keeps the `SIB` row and
writes the same four bytes. Both outputs carry `00 00 00 80`, the two's
complement of `-2147483648`, which is what the field holds; the assembler's
choice of a nine-byte `moffs` form for the low window is `EC-05`'s second
encoding, not a wider `disp32`, and a plan may not take it.

## 3. The four windows

The same three-bit field names two different register sets, so the byte width
has four windows rather than two:

| Window | `REX` | `ModRM` | Numbers | Length |
|---|---|---|---|---|
| `%al`-`%bl` | none | `04`-`1c` | `0`-`3` | 7 |
| `%ah`-`%bh` | none | `24`-`3c` | `4`-`7` | 7 |
| `%spl`-`%dil` | `40` | `24`-`3c` | `4`-`7` | 8 |
| `%r8b`-`%r15b` | `44` | `04`-`3c` | `8`-`15` | 8 |

The `40` window is what makes the split necessary: without `REX`, `reg = 100`
is `%ah`; with `REX = 40`, the same bit pattern is `%spl`. A row that accepted
both would have to read the register number to decide the length (`INV-04`), so
the window is the form and each row's slot excludes the other half
(`E-RANGE-004`, `N16af`).

## 4. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 0x1234, %ax` | `66 8b 04 25 34 12 00 00` | 8 | 16-bit row (`0.28.0`) |
| `movl 0x1234, %eax` | `8b 04 25 34 12 00 00` | 7 | 32-bit row (`0.27.0`) |
| `movq 0x1234, %rax` | `48 8b 04 25 34 12 00 00` | 8 | 64-bit row (`0.26.0`) |
| `movabsb 0x1234, %al` | `a0 34 12 00 00 00 00 00 00` | 9 | `moffs`, second legal encoding |
| `movabsb 4294967295, %al` | `a0 ff ff ff ff 00 00 00 00` | 9 | `moffs` takes an eight-byte address |
| `movb 0x1234, %r16b` | `d5 40 8a 04 25 34 12 00 00` | 9 | APX `d5` prefix before the opcode |
| `movb 0x1234, %r31b` | `d5 44 8a 3c 25 34 12 00 00` | 9 | APX, register 31 |

The APX rows also drop the `REX` byte, because `d5` carries the extension bits
itself: `%r16b` is `d5 40 8a …`, nine bytes, a different template.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bk` | names `x86:mov/r8-abs32/legacy` against `0.28.0` | `E-FORM-001` |
| `N01bl` | names `x86:mov/abs32-r8-ext/legacy` against `0.28.0` | `E-FORM-001` |
| `N02ap` | supplies a `base` operand to the absolute row | `E-OPERAND-002` (`expected 2, found 3`) |
| `N02aq` | carries the address as `disp8`/`x86.imm` | `E-OPERAND-001` on `target_type` |
| `N02ar` | carries `x86.gpr16`/`r16` on an `r8` row | `E-OPERAND-001` on `kind` and `target_type` |
| `N02as` | carries `x86.gpr8h`/`r8h` on the low-byte row | `E-OPERAND-001` twice and `E-RANGE-004` on `payload/reg` |
| `N03p` | carries `disp32` content `2147483648` | `E-RANGE-001` |
| `N14ac` | carries register `16` on the extended row | `E-OPERAND-004` on `payload/reg` |
| `N16af` | carries register `0` on the `REX = 40` row | `E-RANGE-004` on `payload/reg` |

`N02as` is the case that shows the high-byte kind is a separate name on *both*
axes: the kind is not `x86.gpr8` and the target type is not `r8`, and the value
`4` is also excluded from the low window, so three errors are reported.

## 6. The fixture

`X86-P33-gpr8-mov-abs32` is eight instructions and 60 bytes: one per row, so
both directions appear in every window.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movb 0x1234, %al` | `8a 04 25 34 12 00 00` | 7 |
| 2 | `movb %bl, 0x0` | `88 1c 25 00 00 00 00` | 7 |
| 3 | `movb 0x1234, %ah` | `8a 24 25 34 12 00 00` | 7 |
| 4 | `movb %dh, -1` | `88 34 25 ff ff ff ff` | 7 |
| 5 | `movb 0x7f, %spl` | `40 8a 24 25 7f 00 00 00` | 8 |
| 6 | `movb %dil, -32768` | `40 88 3c 25 00 80 ff ff` | 8 |
| 7 | `movb 0x7fffffff, %r8b` | `44 8a 04 25 ff ff ff 7f` | 8 |
| 8 | `movb %r15b, 0x1234` | `44 88 3c 25 34 12 00 00` | 8 |

The fixture pins all four windows in both directions, `0`, `-1`, `127`, the
signed end points `-32768` and `2147483647`, and the relabelled `%spl`/`%dil`
beside the extended `%r8b`/`%r15b`.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`21323476cd2e7d7e8d44cecdee524503a789c7a7fca4a83c5b27d25cc57dde01`
(`fixture.asm`) and its `output_sha256` is
`46b3918fe091ea87db5b79f82784ccee9fa7316524eecd884e4d72237b1ea41e`
(the 60-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
eight lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

The first draft of the extended row placed `REX.R` at bit 10 — the offset it
has at 16-bit width, where `66` occupies byte 0. The materializer produced
`44 8e 04 25 …` (the `REX.R` write landed inside the opcode byte) and the
fixture gate rejected it against the oracle. The measured byte strings give the
correct offset, bit 2, and `generate_0290.py` carries a comment saying where
`REX.R` sits in this family.

## 7. What the slice defers

- The `REX.B` combination at byte width: an extended base with `%r8b`-`%r15b`
  shares one `REX` byte, and `%ah` can never join it.
- The `0x67` address-size prefix: the same fields read as a 32-bit address
  model.
- A symbol or relocation in the address (`R_X86_64_32`, `R_X86_64_32S`).
- `moffs` for the byte width: `a0`/`a2` with an eight-byte address.
- The APX register window (`d5 40 …` / `d5 44 …`): `%r16b`-`%r31b` are a
  different prefix and a different register field.
- The absolute address under the other x86 opcode families.
