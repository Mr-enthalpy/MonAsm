# EXP-0092 -- the absolute `SIB = 25` shape behind `0x67`

- Date: 2026-11-08
- Question: what does the absolute `SIB = 25` address cost when `0x67` selects
  the 32-bit address width, and where do the value and displacement sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.63.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P67-gpr32-mov-addr32-abs32.oracle.json`
- Source: `research/evidence/experiments/EXP-0092/probe.asm`
- Decision: `ADR-0090`

## 1. The measurement

`llvm-mc -show-encoding` on 2026-11-08 splits the `addr32` keyword onto its own
line, so `measure.py` reads the instruction bytes from the object file
(`llvm-mc -filetype=obj` + `llvm-objcopy`) and asserts them; `show-encoding.txt`
keeps the printer's view for reference. The first four lines are the `0.63.0`
rows, the last six are the corners.

| Source | Bytes | Length |
|---|---|---|
| `addr32 movl 4660, %eax` | `67 8b 04 25 34 12 00 00` | 8 |
| `addr32 movl %eax, 4660` | `67 89 04 25 34 12 00 00` | 8 |
| `addr32 movl 4660, %r8d` | `67 44 8b 04 25 34 12 00 00` | 9 |
| `addr32 movl %r8d, 4660` | `67 44 89 04 25 34 12 00 00` | 9 |
| `addr32 movl 0, %eax` | `67 8b 04 25 00 00 00 00` | 8 |
| `addr32 movl -1, %eax` | `67 8b 04 25 ff ff ff ff` | 8 |
| `addr32 movl 2147483647, %eax` | `67 8b 04 25 ff ff ff 7f` | 8 |
| `addr32 movl -2147483648, %eax` | `67 8b 04 25 00 00 00 80` | 8 |
| `addr32 movl 4660, %r15d` | `67 44 8b 3c 25 34 12 00 00` | 9 |
| `addr32 movl %r15d, 4660` | `67 44 89 3c 25 34 12 00 00` | 9 |

`llvm-mc -disassemble` on the ten byte strings returns all ten as
`addr32 movl …` with the same value registers and displacements
(`probes-disassembled.txt`), so the prefix is part of the decoded instruction
and not a tool artifact.

## 2. Where the fields sit

`SIB = 25` is `scale = 00`, `index = 100`, `base = 101`: with `mod = 00` that
is the absolute shape, so the row has no `base`, `index` or `scale` role and the
displacement is the whole address. The byte is template content at every value.

| Byte | 0 | 1 | 2 | 3 | 4-7 |
|---|---|---|---|---|---|
| Bare | `0x67` | opcode | `ModRM = 04` | `SIB = 25` | `disp32` |
| `REX.R` | `0x67` | `REX` | opcode | `ModRM` | `disp32` |

| Row | value | displacement |
|---|---|---|
| bare | `[19,3]` | `[32,32]`, signed |
| `REX.R` | `[10,1]` + `[27,3]`, excluding `0`-`7` | `[40,32]`, signed |

The displacement is four bytes at every value: zero is
`67 8b 04 25 00 00 00 00` (eight bytes, no `disp8` shortening), and the signed
ends are `67 8b 04 25 00 00 00 80` and `67 8b 04 25 ff ff ff 7f`. Only
`ModRM.reg` and the displacement move: `%r15d` puts `ModRM = 3c`
(`67 44 8b 3c 25 34 12 00 00`). There is no `REX.B` or `REX.X` bit, because
there is no base and no index to extend.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take. The first line is
the `0.26.0` absolute row without `0x67`; the next two are the 64-bit and 16-bit
siblings; lines 4 and 5 are the indexed `0x67` rows (their 32-bit index already
emits `0x67`, so an extra `addr32` would double it); lines 6 and 7 are the
`moffs` forms; line 8 is RIP-relative.

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl 4660, %eax` | `8b 04 25 34 12 00 00` | 7 | the absolute row without `0x67` |
| `addr32 movq 4660, %rax` | `67 48 8b 04 25 34 12 00 00` | 9 | 64-bit value sibling |
| `addr32 movw 4660, %ax` | `67 66 8b 04 25 34 12 00 00` | 9 | 16-bit value sibling |
| `movl 8(,%ecx,1), %eax` | `67 8b 04 0d 08 00 00 00` | 8 | no-base indexed row |
| `movl 8(%eax,%ecx,1), %eax` | `67 8b 44 08 08` | 5 | base+index row |
| `movabs 4660, %eax` | `a1 34 12 00 00 00 00 00 00` | 9 | `moffs` |
| `movabs 4660, %rax` | `48 a1 34 12 00 00 00 00 00` | 10 | `moffs` with `REX.W` |
| `addr32 movl 4660(%rip), %eax` | `67 8b 05 34 12 00 00` | 7 | RIP-relative, not this shape |

`rejected.asm` holds two spellings `llvm-mc` refuses with
`error: invalid operand for instruction` (`rejected.txt`, which also keeps the
two `addr32` prefix lines the printer emitted before failing): `addr32 movl
4660, %rax` (a 32-bit opcode with a 64-bit value register) and `addr32 movl
4660, %ax` (16-bit). The value width is carried by the opcode, not by the
address prefix.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01eb` | names `x86:mov/r32-addr32-abs32/legacy` against `0.62.0` | `E-FORM-001` |
| `N01ec` | names `x86:mov/addr32-abs32-r32/legacy` against `0.62.0` | `E-FORM-001` |
| `N02cm` | supplies a `base` the shape does not have | `E-OPERAND-002` (`expected 2, found 3`) |
| `N03zp` | displacement `2147483648`, past the signed 32-bit end | `E-RANGE-001` (`max 2147483647`) |
| `N14cb` | value register `16`, past the four-bit extended field | `E-OPERAND-004` (`field_bits 4`) |
| `N14cc` | value register `8`, past the bare three-bit field | `E-OPERAND-004` (`field_bits 3`) |
| `N16df` | value register `0` on the `-ext` row | `E-RANGE-004` (`excluded 0…7`) |

`N14cc` is what separates the two geometries: the bare row's field is three
bits, so a register that fits the extended row does not fit it.

## 5. The fixture

`X86-P67-gpr32-mov-addr32-abs32` is ten instructions and 84 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `addr32 movl 4660, %eax` | `67 8b 04 25 34 12 00 00` | 8 |
| 2 | `addr32 movl %eax, 4660` | `67 89 04 25 34 12 00 00` | 8 |
| 3 | `addr32 movl 4660, %r8d` | `67 44 8b 04 25 34 12 00 00` | 9 |
| 4 | `addr32 movl %r8d, 4660` | `67 44 89 04 25 34 12 00 00` | 9 |
| 5 | `addr32 movl 0, %eax` | `67 8b 04 25 00 00 00 00` | 8 |
| 6 | `addr32 movl -1, %eax` | `67 8b 04 25 ff ff ff ff` | 8 |
| 7 | `addr32 movl 2147483647, %eax` | `67 8b 04 25 ff ff ff 7f` | 8 |
| 8 | `addr32 movl -2147483648, %eax` | `67 8b 04 25 00 00 00 80` | 8 |
| 9 | `addr32 movl 4660, %r15d` | `67 44 8b 3c 25 34 12 00 00` | 9 |
| 10 | `addr32 movl %r15d, 4660` | `67 44 89 3c 25 34 12 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`b1c7282ab1a257fff90574e3b19cc3f7d5883c646a4df0cc13c3c4f98edea9e0`
(`probe.asm`) and its `output_sha256` is
`1aa7df24bd58c2227355a85006a8e4fc658143c1dc0d1b116d331b6e21479279`
(the 84-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:e9cb5241f8e94ecce8b32092fec9bc6ce4cade8dc5e1b30769be97c044f28452`.

`0.63.0` has 503 forms and the canonical digest
`sha256:72c7e8f2fcf4c73ad816d7de274d9b46edec7d9ef99b4834c27140d83d6c91e8`.

## 6. What the slice defers

- A symbol or relocation in the `disp32`.
- The `REX.W` absolute sibling (`67 48 8b 04 25 …`) and the `0x67 66` one
  (`67 66 8b 04 25 …`).
- The `moffs` form with `0x67`.
- The RIP-relative `67 8b 05` row.
- A 64-bit address register with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
