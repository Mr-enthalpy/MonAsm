# EXP-0094 -- the absolute `SIB = 25` shape behind `0x67 66` at the 16-bit value width

- Date: 2026-11-08
- Question: what does the absolute `SIB = 25` address cost behind `0x67 66`,
  and where do the value and displacement sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.65.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P69-gpr16-mov-addr32-abs32.oracle.json`
- Source: `research/evidence/experiments/EXP-0094/probe.asm`
- Decision: `ADR-0092`

## 1. The measurement

`llvm-mc -show-encoding` on 2026-11-08 splits the `addr32` keyword onto its own
line, so `measure.py` reads the instruction bytes from the object file
(`llvm-mc -filetype=obj` + `llvm-objcopy`) and asserts them; `show-encoding.txt`
keeps the printer's view for reference. The first four lines are the `0.65.0`
rows, the last six are the corners.

| Source | Bytes | Length |
|---|---|---|
| `addr32 movw 4660, %ax` | `67 66 8b 04 25 34 12 00 00` | 9 |
| `addr32 movw %ax, 4660` | `67 66 89 04 25 34 12 00 00` | 9 |
| `addr32 movw 4660, %r8w` | `67 66 44 8b 04 25 34 12 00 00` | 10 |
| `addr32 movw %r8w, 4660` | `67 66 44 89 04 25 34 12 00 00` | 10 |
| `addr32 movw 0, %ax` | `67 66 8b 04 25 00 00 00 00` | 9 |
| `addr32 movw -1, %ax` | `67 66 8b 04 25 ff ff ff ff` | 9 |
| `addr32 movw 2147483647, %ax` | `67 66 8b 04 25 ff ff ff 7f` | 9 |
| `addr32 movw -2147483648, %ax` | `67 66 8b 04 25 00 00 00 80` | 9 |
| `addr32 movw 4660, %r15w` | `67 66 44 8b 3c 25 34 12 00 00` | 10 |
| `addr32 movw %r15w, 4660` | `67 66 44 89 3c 25 34 12 00 00` | 10 |

`llvm-mc -disassemble` on the ten byte strings returns all ten as
`addr32 movw …` with the same value registers and displacements
(`probes-disassembled.txt`), so the prefix pair is part of the decoded
instruction and not a tool artifact.

## 2. Where the fields sit

`SIB = 25` is `scale = 00`, `index = 100`, `base = 101`: with `mod = 00` that
is the absolute shape, so the row has no `base`, `index` or `scale` role and the
displacement is the whole address. The byte is template content at every value.

| Byte | 0 | 1 | 2 | 3 | 4 | 5-8 |
|---|---|---|---|---|---|---|
| Bare | `0x67` | `0x66` | opcode | `ModRM = 04` | `SIB = 25` | `disp32` |
| `REX.R` | `0x67` | `0x66` | `REX = 44` | opcode | `ModRM` | ... |

The `REX.R` row is ten bytes: `0x67` at 0, `0x66` at 1, `REX = 44` at 2, the
opcode at 3, `ModRM = 04` at 4, `SIB = 25` at 5 and the displacement at 6–9.
`R` (`[18,1]`) plus `ModRM.reg` (`[35,3]`) covers all sixteen values with the
low window excluded, so the extended row serves `%r8w`-`%r15w` and the bare row
serves `%ax`-`%di`.

| Row | value | displacement |
|---|---|---|
| bare | `[27,3]` | `[40,32]`, signed |
| `REX.R` | `[18,1]` + `[35,3]`, excluding `0`-`7` | `[48,32]`, signed |

The displacement is four bytes at every value: zero is
`67 66 8b 04 25 00 00 00 00` (nine bytes, no `disp8` shortening), and the
signed ends are `67 66 8b 04 25 00 00 00 80` and
`67 66 8b 04 25 ff ff ff 7f`. Only `ModRM.reg` and the `R` bit move: `%r15w`
puts `ModRM = 3c` (`67 66 44 8b 3c 25 34 12 00 00`). There is no `REX.B` or
`REX.X` bit, because there is no base and no index to extend.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take. Line 1 is the
`0.28.0` absolute row without `0x67`; lines 2 and 3 are the 32-bit and 64-bit
siblings; line 4 is the `0.60.0` no-base indexed 16-bit row; line 5 is a
base+index pair; lines 6 and 7 are the `moffs` forms; line 8 is RIP-relative.

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 4660, %ax` | `66 8b 04 25 34 12 00 00` | 8 | the absolute row without `0x67` |
| `addr32 movl 4660, %eax` | `67 8b 04 25 34 12 00 00` | 8 | 32-bit value sibling |
| `addr32 movq 4660, %rax` | `67 48 8b 04 25 34 12 00 00` | 9 | 64-bit value sibling |
| `movw 8(,%ecx,1), %ax` | `67 66 8b 04 0d 08 00 00 00` | 9 | no-base indexed row |
| `movw 8(%eax,%ecx,1), %ax` | `67 66 8b 44 08 08` | 6 | base+index |
| `movabs 4660, %ax` | `66 a1 34 12 00 00 00 00 00 00` | 10 | `moffs` |
| `addr32 movabs 4660, %ax` | `67 66 a1 34 12 00 00 00 00 00 00` | 11 | `moffs` with `0x67 66` |
| `addr32 movw 4660(%rip), %ax` | `67 66 8b 05 34 12 00 00` | 8 | RIP-relative, not this shape |

The line 4 bytes are worth noting: the 32-bit index register `%ecx` already
makes the assembler emit `0x67`, and `0x66` follows for the 16-bit value. The
`0.60.0` row's template is `67 66 8b 04 05 00 00 00 00`, and `%ecx` raises the
`SIB` byte from `05` to `0d`, which is the measured line above.

The `moffs` line repeats the `EXP-0093` warning: `llvm-mc` prepends `0x67 66`
but keeps an eight-byte offset, so the encoding grows to eleven bytes instead
of shrinking. A manual derivation of the `moffs` encoding makes the offset
width follow the address size. The two disagree, so this slice records the
observation only and leaves `moffs` with `0x67 66` deferred and `unverified`.

`rejected.asm` holds two spellings `llvm-mc` refuses with
`error: invalid operand for instruction` (`rejected.txt`, which also keeps the
two `addr32` prefix lines the printer emitted before failing): `addr32 movw
4660, %eax` and `addr32 movw 4660, %rax`. The value width is carried by `0x66`
and the opcode, not by the address prefix.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01ef` | names `x86:mov/r16-addr32-abs32/legacy` against `0.64.0` | `E-FORM-001` |
| `N01eg` | names `x86:mov/addr32-abs32-r16/legacy` against `0.64.0` | `E-FORM-001` |
| `N02cq` | supplies a `base` the shape does not have | `E-OPERAND-002` (`expected 2, found 3`) |
| `N02cr` | omits the displacement | `E-OPERAND-002` (`expected 2, found 1`) |
| `N02cs` | passes a `x86.gpr32`/`r32` value | `E-OPERAND-001` twice (`kind`, `target_type`) |
| `N03zr` | displacement `2147483648`, past the signed 32-bit end | `E-RANGE-001` (`max 2147483647`) |
| `N14ce` | value register `16`, past the four-bit extended field | `E-OPERAND-004` (`field_bits 4`) |
| `N14cf` | value register `8`, past the bare three-bit field | `E-OPERAND-004` (`field_bits 3`) |
| `N16dg` | value register `0` on the `-ext` row | `E-RANGE-004` (`excluded 0…7`) |

`N14cf` and `N16dg` are the pair that separates the two geometries: the bare
row's field is three bits, so a register that fits the extended row does not
fit it, and the extended row's exclusion means the low window needs the bare
row.

## 5. The fixture

`X86-P69-gpr16-mov-addr32-abs32` is ten instructions and 94 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `addr32 movw 4660, %ax` | `67 66 8b 04 25 34 12 00 00` | 9 |
| 2 | `addr32 movw %ax, 4660` | `67 66 89 04 25 34 12 00 00` | 9 |
| 3 | `addr32 movw 4660, %r8w` | `67 66 44 8b 04 25 34 12 00 00` | 10 |
| 4 | `addr32 movw %r8w, 4660` | `67 66 44 89 04 25 34 12 00 00` | 10 |
| 5 | `addr32 movw 0, %ax` | `67 66 8b 04 25 00 00 00 00` | 9 |
| 6 | `addr32 movw -1, %ax` | `67 66 8b 04 25 ff ff ff ff` | 9 |
| 7 | `addr32 movw 2147483647, %ax` | `67 66 8b 04 25 ff ff ff 7f` | 9 |
| 8 | `addr32 movw -2147483648, %ax` | `67 66 8b 04 25 00 00 00 80` | 9 |
| 9 | `addr32 movw 4660, %r15w` | `67 66 44 8b 3c 25 34 12 00 00` | 10 |
| 10 | `addr32 movw %r15w, 4660` | `67 66 44 89 3c 25 34 12 00 00` | 10 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`d7289d73feb66b9dca4b04205b5b8c12646d3398e332f50789058ad13f19eeba`
(`probe.asm`) and its `output_sha256` is
`0d4d69060cfa0643fa540fb24684e9580c42326202ef83cea9ce68b700029405`
(the 94-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:f9dce2eb7ca828a399d3593c758dfe041532f9bfbee052c8603c7ce95f5bdbd8`.

`0.65.0` has 509 forms and the canonical digest
`sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a`.

## 6. What the slice defers

- A symbol or relocation in the `disp32`.
- The `moffs` form with `0x67 66` — the measurement and a manual derivation
  disagree about the offset width, so it needs a second oracle.
- The `0x67 66` RIP-relative row.
- A 64-bit address register with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
