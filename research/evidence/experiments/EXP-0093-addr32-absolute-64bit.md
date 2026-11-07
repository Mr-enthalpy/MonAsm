# EXP-0093 -- the absolute `SIB = 25` shape behind `0x67` at the 64-bit value width

- Date: 2026-11-08
- Question: what does the absolute `SIB = 25` address cost behind `0x67` when
  the value is 64-bit, and where do the value and displacement sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.64.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P68-gpr64-mov-addr32-abs32.oracle.json`
- Source: `research/evidence/experiments/EXP-0093/probe.asm`
- Decision: `ADR-0091`

## 1. The measurement

`llvm-mc -show-encoding` on 2026-11-08 splits the `addr32` keyword onto its own
line, so `measure.py` reads the instruction bytes from the object file
(`llvm-mc -filetype=obj` + `llvm-objcopy`) and asserts them; `show-encoding.txt`
keeps the printer's view for reference. The first two lines are the `0.64.0`
rows, the last eight are the corners.

| Source | Bytes | Length |
|---|---|---|
| `addr32 movq 4660, %rax` | `67 48 8b 04 25 34 12 00 00` | 9 |
| `addr32 movq %rax, 4660` | `67 48 89 04 25 34 12 00 00` | 9 |
| `addr32 movq 4660, %r8` | `67 4c 8b 04 25 34 12 00 00` | 9 |
| `addr32 movq %r8, 4660` | `67 4c 89 04 25 34 12 00 00` | 9 |
| `addr32 movq 0, %rax` | `67 48 8b 04 25 00 00 00 00` | 9 |
| `addr32 movq -1, %rax` | `67 48 8b 04 25 ff ff ff ff` | 9 |
| `addr32 movq 2147483647, %rax` | `67 48 8b 04 25 ff ff ff 7f` | 9 |
| `addr32 movq -2147483648, %rax` | `67 48 8b 04 25 00 00 00 80` | 9 |
| `addr32 movq 4660, %r15` | `67 4c 8b 3c 25 34 12 00 00` | 9 |
| `addr32 movq %r15, 4660` | `67 4c 89 3c 25 34 12 00 00` | 9 |

`llvm-mc -disassemble` on the ten byte strings returns all ten as
`addr32 movq …` with the same value registers and displacements
(`probes-disassembled.txt`), so the prefix is part of the decoded instruction
and not a tool artifact.

## 2. Where the fields sit

`SIB = 25` is `scale = 00`, `index = 100`, `base = 101`: with `mod = 00` that
is the absolute shape, so the row has no `base`, `index` or `scale` role and the
displacement is the whole address. The byte is template content at every value.

| Byte | 0 | 1 | 2 | 3 | 4 | 5-8 |
|---|---|---|---|---|---|---|
| Both rows | `0x67` | `REX` (`48`/`4c`) | opcode | `ModRM = 04` | `SIB = 25` | `disp32` |

`REX.W` is mandatory, so there is no `REX`-less geometry: `REX` is `48` for
`%rax`-`%rdi` and `4c` for `%r8`-`%r15`. `R` (`[10,1]`) plus `ModRM.reg`
(`[27,3]`) covers the whole 0-15 window with no exclusion.

| Row | value | displacement |
|---|---|---|
| both | `[10,1]` + `[27,3]` | `[40,32]`, signed |

The displacement is four bytes at every value: zero is
`67 48 8b 04 25 00 00 00 00` (nine bytes, no `disp8` shortening), and the
signed ends are `67 48 8b 04 25 00 00 00 80` and
`67 48 8b 04 25 ff ff ff 7f`. Only `ModRM.reg` and the `R` bit move: `%r15`
puts `ModRM = 3c` (`67 4c 8b 3c 25 34 12 00 00`). There is no `REX.B` or
`REX.X` bit, because there is no base and no index to extend.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take. Line 1 is the
`0.26.0` absolute row without `0x67`; lines 2 and 3 are the 32-bit and 16-bit
siblings; line 4 is the no-base indexed 64-bit row without `0x67`; line 5 is a
32-bit base+index pair with a 64-bit value; lines 6 and 7 are the `moffs`
forms; line 8 is RIP-relative.

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movq 4660, %rax` | `48 8b 04 25 34 12 00 00` | 8 | the absolute row without `0x67` |
| `addr32 movl 4660, %eax` | `67 8b 04 25 34 12 00 00` | 8 | 32-bit value sibling |
| `addr32 movw 4660, %ax` | `67 66 8b 04 25 34 12 00 00` | 9 | 16-bit value sibling |
| `movq 8(,%rcx,1), %rax` | `48 8b 04 0d 08 00 00 00` | 8 | no-base indexed row without `0x67` |
| `movq 8(%eax,%ecx,1), %rax` | `67 48 8b 44 08 08` | 6 | base+index, 32-bit address |
| `movabs 4660, %rax` | `48 a1 34 12 00 00 00 00 00 00` | 10 | `moffs` |
| `addr32 movabs 4660, %rax` | `67 48 a1 34 12 00 00 00 00 00 00` | 11 | `moffs` with `0x67` |
| `addr32 movq 4660(%rip), %rax` | `67 48 8b 05 34 12 00 00` | 8 | RIP-relative, not this shape |

The `moffs` line is worth a warning: `llvm-mc` prepends `0x67` but keeps an
eight-byte offset, so the encoding grows to eleven bytes instead of shrinking
to nine. A manual derivation of the `moffs` encoding makes the offset width
follow the address size, which would give nine bytes. The two disagree, so this
slice records the observation only and leaves `moffs` with `0x67` deferred and
`unverified`.

`rejected.asm` holds two spellings `llvm-mc` refuses with
`error: invalid operand for instruction` (`rejected.txt`, which also keeps the
two `addr32` prefix lines the printer emitted before failing): `addr32 movq
4660, %eax` (a 64-bit opcode with a 32-bit value register) and `addr32 movq
4660, %ax` (16-bit). The value width is carried by the opcode and `REX.W`, not
by the address prefix.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01ed` | names `x86:mov/r64-addr32-abs32/legacy` against `0.63.0` | `E-FORM-001` |
| `N01ee` | names `x86:mov/addr32-abs32-r64/legacy` against `0.63.0` | `E-FORM-001` |
| `N02cn` | supplies a `base` the shape does not have | `E-OPERAND-002` (`expected 2, found 3`) |
| `N02co` | omits the displacement | `E-OPERAND-002` (`expected 2, found 1`) |
| `N02cp` | passes a `x86.gpr32`/`r32` value | `E-OPERAND-001` twice (`kind`, `target_type`) |
| `N03zq` | displacement `2147483648`, past the signed 32-bit end | `E-RANGE-001` (`max 2147483647`) |
| `N14cd` | value register `16`, past the four-bit field | `E-OPERAND-004` (`field_bits 4`) |

`N02cp` is the one case that reports two diagnostics: the kind and the target
type are separate leaves, and a 32-bit operand misses both. `N02co` is the
counterexample for the displacement role: `SIB = 25` carries the whole address,
so a plan without a `disp` has no address at all and must not be repaired with
a zero.

## 5. The fixture

`X86-P68-gpr64-mov-addr32-abs32` is ten instructions and 90 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `addr32 movq 4660, %rax` | `67 48 8b 04 25 34 12 00 00` | 9 |
| 2 | `addr32 movq %rax, 4660` | `67 48 89 04 25 34 12 00 00` | 9 |
| 3 | `addr32 movq 4660, %r8` | `67 4c 8b 04 25 34 12 00 00` | 9 |
| 4 | `addr32 movq %r8, 4660` | `67 4c 89 04 25 34 12 00 00` | 9 |
| 5 | `addr32 movq 0, %rax` | `67 48 8b 04 25 00 00 00 00` | 9 |
| 6 | `addr32 movq -1, %rax` | `67 48 8b 04 25 ff ff ff ff` | 9 |
| 7 | `addr32 movq 2147483647, %rax` | `67 48 8b 04 25 ff ff ff 7f` | 9 |
| 8 | `addr32 movq -2147483648, %rax` | `67 48 8b 04 25 00 00 00 80` | 9 |
| 9 | `addr32 movq 4660, %r15` | `67 4c 8b 3c 25 34 12 00 00` | 9 |
| 10 | `addr32 movq %r15, 4660` | `67 4c 89 3c 25 34 12 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`870a0ae3d24964dd11212ca506cefe0df1072f5a6bd39ae8397e20c98db3ebcf`
(`probe.asm`) and its `output_sha256` is
`ceff0da3eb4fb5bca203ba0685073e7b2669a3a21992561b4b5f1f2ce97689b3`
(the 90-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:e01f62712cf1d059d33344925ab734ab8cc1622b74ea1e126efb78d97154871f`.

`0.64.0` has 505 forms and the canonical digest
`sha256:fc98a834b7840d3f2383b05a5d2950966a81187234a080f24f7ad85ab6c07a4f`.

## 6. What the slice defers

- A symbol or relocation in the `disp32`.
- The `0x67 66` absolute sibling (`67 66 8b 04 25 …`).
- The `moffs` form with `0x67` — the measurement and a manual derivation
  disagree about the offset width, so it needs a second oracle.
- The RIP-relative `67 48 8b 05` row.
- A 64-bit address register with `0x67`.
- The APX `d5` register window and EVEX masking/broadcast.
