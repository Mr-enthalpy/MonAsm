# EXP-0060 -- the byte GPR `mov` rows take the no-displacement memory shape

- Date: 2026-11-06
- Question: what does `mod = 00` add to the byte-width GPR `mov` memory rows,
  which bases can inhabit it, and what do the four register windows cost?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.31.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P35-gpr8-mov-mem-nodisp.oracle.json`
- Source: `research/evidence/experiments/EXP-0060/probe.asm`
- Fixture source: `research/evidence/experiments/EXP-0060/fixture.asm`
- Decision: `ADR-0058`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movb (%rax), %al` | `8a 00` | 2 |
| `movb %al, (%rax)` | `88 00` | 2 |
| `movb (%rax), %ah` | `8a 20` | 2 |
| `movb %ah, (%rax)` | `88 20` | 2 |
| `movb (%rax), %spl` | `40 8a 20` | 3 |
| `movb %spl, (%rax)` | `40 88 20` | 3 |
| `movb (%rax), %r8b` | `44 8a 00` | 3 |
| `movb %r8b, (%rax)` | `44 88 00` | 3 |
| `movb (%r8), %al` | `41 8a 00` | 3 |
| `movb (%r15), %r15b` | `45 8a 3f` | 3 |
| `movb (%rax), %dil` | `40 8a 38` | 3 |
| `movb (%r12), %spl` | `41 8a 24 24` | 4 |
| `movb (%rsp), %r8b` | `44 8a 04 24` | 4 |
| `movb 0(%rax), %al` | `8a 00` | 2 |

`llvm-mc -disassemble` on `probes.txt` returns all fourteen byte strings as the
same register and base. The last line shows that an explicit zero displacement
is *elided* to the same two bytes, which is why the row must be chosen by name
rather than by the presence of an operand (`INV-02`).

## 2. Where the fields sit

The frame has no displacement byte at all, so a row is either the opcode and
`ModRM` alone or one `REX` byte plus those two:

| Row shape | Byte | Bits | Value | Fields |
|---|---|---|---|---|
| `REX`-less | opcode | `[0,8]` | `8a` / `88` | fixed per direction |
| | `ModRM` | `[8,8]` | `00`-`3f` | `mod = 00`, `reg` = register at `[11,3]`, `r/m` = base at `[8,3]` |
| `REX`-prefixed | `REX` | `[0,8]` | `40` / `41` / `44` / `45` | `REX.R` = register's fourth bit at `[2,1]`, `REX.B` = base's at `[0,1]` |
| | opcode | `[8,8]` | `8a` / `88` | fixed per direction |
| | `ModRM` | `[16,8]` | `00`-`3f` | `mod = 00`, `reg` = register at `[19,3]`, `r/m` = base at `[16,3]` |

`mod` is zero in every row, so the `ModRM` byte is always below `40`. The
`disp8` twins beside these rows are three bytes (`8a 40 00`) and the `disp32`
twins six (`8a 80 00 00 00 00`), which is the whole point of a separate row.

### The four register windows

| Source | Bytes | Window | Register slot | Base slot |
|---|---|---|---|---|
| `movb (%rax), %al` | `8a 00` | `%al`-`%bl` | `[11,3]`, excl `4`-`7` | `[8,3]`, excl `4`, `5` |
| `movb (%rax), %ah` | `8a 20` | `%ah`-`%bh` | `[11,3]`, excl `0`-`3` | `[8,3]`, excl `4`, `5` |
| `movb (%rax), %spl` | `40 8a 20` | `%spl`-`%dil` | `[19,3]`, excl `0`-`3` | `[0,1]`+`[16,3]`, excl `4`, `5`, `12`, `13` |
| `movb (%rax), %r8b` | `44 8a 00` | `%r8b`-`%r15b` | `[2,1]`+`[19,3]`, excl `0`-`7` | `[0,1]`+`[16,3]`, excl `4`, `5`, `12`, `13` |

`movb (%r8), %al` is `41 8a 00`, `movb (%r15), %r15b` is `45 8a 3f` and
`movb (%rax), %dil` is `40 8a 38`, so both extension bits and both ends of
each register window are exercised. The two `REX`-less rows cannot reach
`%r8`-`%r15` at all, because their base slot is three bits.

## 3. Two bases that are not bases

At `mod = 00` the `r/m` value `101` is not a base: it selects RIP-relative
`disp32`. `llvm-mc` shows this by writing `%rbp` with `mod = 01` and a zero
byte, which is a different row:

| Source | Bytes | Length | Reading |
|---|---|---|---|
| `movb (%rbp), %al` | `8a 45 00` | 3 | `mod = 01`, `disp8 = 0` — the `disp8` row, not this one |
| `movb (%r13), %al` | `41 8a 45 00` | 4 | the same shape with `REX.B` |
| `movb 0(%rbp), %al` | `8a 45 00` | 3 | the written zero is the same shape |
| `movb (%rbp), %spl` | `40 8a 65 00` | 4 | `REX = 40` plus the displacement row |
| `movb (%r13), %r8b` | `45 8a 45 00` | 4 | both extension bits, still `mod = 01` |

So `%rbp` and `%r13` cannot inhabit the `mod = 00` rows: the base slot excludes
`5` and `13` and the pair keeps its `disp8 = 0` row.

The `r/m` value `100` is the other non-base: it means "a `SIB` byte follows",
and these rows carry no `SIB`:

| Source | Bytes | Length | Reading |
|---|---|---|---|
| `movb (%rsp), %al` | `8a 04 24` | 3 | `ModRM = 04`, `SIB = 24`, no displacement |
| `movb (%r12), %al` | `41 8a 04 24` | 4 | the same `SIB` byte with `REX.B = 1` |
| `movb (%rsp), %ah` | `8a 24 24` | 3 | `reg = 100`: high-byte window, same `SIB` |
| `movb (%r12), %spl` | `41 8a 24 24` | 4 | `REX = 41` relabels `4` and takes `%r12` |
| `movb (%rsp), %r8b` | `44 8a 04 24` | 4 | `REX = 44`, the extended register window |

`SIB = 24` is `scale = 00`, `index = 100` ("no index") and `base = 100`, and
`REX.B` alone decides whether it reads `%rsp` or `%r12`. Those four rows are a
later slice, so the eight rows decided here exclude `4` and `12` from the base
slot as well.

## 4. The neighbours

`adjacent.asm` measures the shapes this slice does not take:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movl (%rax), %eax` | `8b 00` | 2 | 32-bit analogue, same `mod = 00` frame |
| `movw (%rax), %ax` | `66 8b 00` | 3 | 16-bit analogue behind `66` |
| `movq (%rax), %rax` | `48 8b 00` | 3 | 64-bit analogue, `REX.W` |
| `movb (%rax), %r16b` | `d5 40 8a 00` | 4 | APX `d5` prefix, a different template |

`movb (%r13), %ah` is rejected by `llvm-mc` with `can't encode 'ah' in an
instruction requiring EVEX/REX2/REX prefix`: the `REX.B` byte that `%r13`
needs is exactly the byte that renames `%ah` to `%spl`. `adjacent-encoding.txt`
keeps the message. That is the same `EC-36` rule the `disp8`/`disp32` rows
already obey, and it is why the high-byte window has no `%rsp`/`%r12` half.

## 5. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01bo` | names `x86:mov/r8-base/legacy` against `0.30.0` | `E-FORM-001` |
| `N01bp` | names `x86:mov/base-r8-ext/legacy` against `0.30.0` | `E-FORM-001` |
| `N02aw` | carries `x86.gpr8h`/`r8h` on the low-window row | `E-OPERAND-001` on `kind` and `target_type` |
| `N02ax` | supplies a `disp` operand to a row with no displacement slot | `E-OPERAND-002` (`expected 2, found 3`) |
| `N14ae` | carries base `8` on a three-bit row | `E-OPERAND-004` on the base's `payload/reg` |
| `N16aj` | carries `%rbp` as the base | `E-RANGE-004` on the base's `payload/reg` |
| `N16ak` | carries `%r13` as the base | `E-RANGE-004` on the base's `payload/reg` |
| `N16al` | carries `%rsp` as the base | `E-RANGE-004` on the base's `payload/reg` |
| `N16am` | carries `%r12` as the base | `E-RANGE-004` on the base's `payload/reg` |

`N02ax` is the case that shows why there is no implicit zero: the row has two
slots, so a third operand is a count mismatch rather than a displacement that
the form would have to encode or discard.

## 6. The fixture

`X86-P35-gpr8-mov-mem-nodisp` is eight instructions and 20 bytes: one per row,
so both directions appear in all four register windows.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movb (%rax), %al` | `8a 00` | 2 |
| 2 | `movb %cl, (%rcx)` | `88 09` | 2 |
| 3 | `movb (%rdx), %ah` | `8a 22` | 2 |
| 4 | `movb %bh, (%rbx)` | `88 3b` | 2 |
| 5 | `movb (%rsi), %dil` | `40 8a 3e` | 3 |
| 6 | `movb %sil, (%rdi)` | `40 88 37` | 3 |
| 7 | `movb (%r8), %r8b` | `45 8a 00` | 3 |
| 8 | `movb %r15b, (%r9)` | `45 88 39` | 3 |

The bases stay inside the legal set (`%rax`, `%rcx`, `%rdx`, `%rbx`, `%rsi`,
`%rdi`, `%r8`, `%r9`), because `%rsp`/`%r12` need a `SIB` byte and
`%rbp`/`%r13` collide with `r/m = 101`. The registers span each window's ends
(`%al`, `%cl`, `%ah`, `%bh`, `%dil`, `%sil`, `%r8b`, `%r15b`), and line 7 is
the one row where both extension bits are set.

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`20819bb11421ddae4295a3700bde4a87a7000f06f25de77b22ecee41ee326f47`
(`fixture.asm`) and its `output_sha256` is
`5ad8a6f622515dcd5d66d21017bb595825f56c5381c0eed0803685ff2c34796e`
(the 20-byte `.text`). `llvm-mc -show-encoding` of `fixture.asm` records the
eight lines in `fixture-encoding.txt`, and the materializer's output is
byte-identical to the oracle.

## 7. What the slice defers

- The `%rsp`/`%r12` `SIB` rows at `mod = 00` (`8a 04 24`, `41 8a 04 24`).
- `REX.X` at byte width: a `SIB` index with an extended register.
- The `0x67` address-size prefix.
- A symbol or relocation in the displacement.
- `moffs` for the byte width: `a0`/`a2`, nine bytes.
- The APX register window (`d5 40 8a 00`): `%r16b`-`%r31b` are a different
  prefix and a different register field.
- The same shape under the 16-, 32- and 64-bit `mov` opcodes.
