# EXP-0076 -- the 16-bit `mov` index/scale rows with `REX.B` and `REX.X`

- Date: 2026-11-07
- Question: what does it cost to keep the 16-bit indexed `mov` register in the
  low window while the base or the index reaches `%r8`–`%r15`, and where do
  `ModRM`, `SIB` and the displacement sit?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.47.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P51-gpr16-mov-index-ext-window.oracle.json`
- Source: `research/evidence/experiments/EXP-0076/probe.asm`
- Decision: `ADR-0074`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-07.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%r8,%rcx,1), %ax` | `66 41 8b 44 08 08` | 6 |
| `movw 8(%r15,%rdi,8), %di` | `66 41 8b 7c ff 08` | 6 |
| `movw 8(%rax,%r9,1), %ax` | `66 42 8b 44 08 08` | 6 |
| `movw 8(%rdi,%r15,8), %di` | `66 42 8b 7c ff 08` | 6 |
| `movw %ax, 8(%r8,%rcx,1)` | `66 41 89 44 08 08` | 6 |
| `movw %di, 8(%rdi,%r15,8)` | `66 42 89 7c ff 08` | 6 |
| `movw 200(%r8,%rcx,1), %ax` | `66 41 8b 84 08 c8 00 00 00` | 9 |
| `movw 200(%r15,%rdi,8), %di` | `66 41 8b bc ff c8 00 00 00` | 9 |
| `movw 200(%rax,%r9,1), %ax` | `66 42 8b 84 08 c8 00 00 00` | 9 |
| `movw 200(%rdi,%r15,8), %di` | `66 42 8b bc ff c8 00 00 00` | 9 |
| `movw %ax, 200(%r8,%rcx,1)` | `66 41 89 84 08 c8 00 00 00` | 9 |
| `movw %di, 200(%rdi,%r15,8)` | `66 42 89 bc ff c8 00 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns all twelve byte strings as the
same registers, bases, indexes and scales (`probes-disassembled.txt`).

## 2. Where the fields sit

| Row | Bytes | `0x66` | `REX` | Opcode | `ModRM` | `SIB` | Displacement |
|---|---|---|---|---|---|---|---|
| base window, `disp8` | `66 41 8b 44 08 08` | byte 0 | `41` at byte 1 (`B = 1` at `[8,1]`) | byte 2 | `44` at byte 3 (`mod = 01`, `reg = 0` at `[27,3]`, `r/m = 100`) | byte 4: scale `[38,2] = 0`, index `[35,3] = 1`, base `[32,3] = 0` | `[40,8]` |
| base window, high registers | `66 41 8b 7c ff 08` | byte 0 | `41` | byte 2 | `7c` (`mod = 01`, `reg = 7`, `r/m = 100`) | `ff`: scale `3`, index `7`, base `7` | `[40,8]` |
| index window, `disp8` | `66 42 8b 44 08 08` | byte 0 | `42` at byte 1 (`X = 1` at `[9,1]`) | byte 2 | `44` (`mod = 01`, `reg = 0`) | `08`: scale `0`, index `1`, base `0` | `[40,8]` |
| index window, high registers | `66 42 8b 7c ff 08` | byte 0 | `42` | byte 2 | `7c` (`mod = 01`, `reg = 7`) | `ff`: scale `3`, index `7` (`REX.X` plus `111` = `%r15`), base `7` | `[40,8]` |
| base window, `disp32` | `66 41 8b 84 08 c8 00 00 00` | byte 0 | `41` | byte 2 | `84` (`mod = 10`, `r/m = 100`) | `08` | `[40,32]` |
| index window, `disp32` | `66 42 8b bc ff c8 00 00 00` | byte 0 | `42` | byte 2 | `bc` (`mod = 10`, `reg = 7`) | `ff` | `[40,32]` |

The `REX` byte returns because the base or the index needs a fourth bit, so
`ModRM` is byte 3 and its `reg` field is `[27,3]`; `r/m = 100` announces the
`SIB` byte at byte 4, with `base` at `[32,3]`, `index` at `[35,3]` and the
scale at `[38,2]`. The displacement follows the `SIB` byte at `[40,8]` or
`[40,32]`, exactly where the `0.45.0` rows put it and one byte later than the
`0.46.0` rows.

## 3. The neighbours

`adjacent.asm` measures the shapes this slice does not take and the bases that
sit next to it:

| Source | Bytes | Length | What it is |
|---|---|---|---|
| `movw 8(%rax,%rsp,1), %ax` | rejected | -- | `%rsp` is not an index (`invalid base+index expression`) |
| `movw 8(%rax,%rcx,1), %r8w` | `66 44 8b 44 08 08` | 6 | the `0.45.0` `REX.R` row |
| `movw 8(%r8,%r9,1), %ax` | `66 43 8b 44 08 08` | 6 | the `REX.BX` window, left for its own slice |
| `movw 8(%r12,%rcx,1), %ax` | `66 41 8b 44 0c 08` | 6 | `SIB.base = 100` behind `REX.B` |
| `movw 8(%r13,%rcx,1), %ax` | `66 41 8b 44 0d 08` | 6 | `SIB.base = 101` at `mod = 01` |
| `movw 8(%rsp,%r9,1), %ax` | `66 42 8b 44 0c 08` | 6 | `SIB.base = 100` without `REX.B` |
| `movw 8(%rbp,%r9,1), %ax` | `66 42 8b 44 0d 08` | 6 | `%rbp` base at `mod = 01` |
| `movw 8(%rax,%r12,1), %ax` | `66 42 8b 44 20 08` | 6 | `REX.X` plus `SIB.index = 100` is `%r12` |
| `movw 127(%r8,%rcx,1), %ax` | `66 41 8b 44 08 7f` | 6 | the signed byte upper end |
| `movw -128(%r8,%rcx,1), %ax` | `66 41 8b 44 08 80` | 6 | the signed byte lower end |
| `movw 200(%r12,%rcx,1), %ax` | `66 41 8b 84 0c c8 00 00 00` | 9 | `%r12` base at `disp32` |
| `movw %ax, 8(%rsp,%r9,1)` | `66 42 89 44 0c 08` | 6 | the same base with a store direction |

`adjacent-encoding.txt` records the eleven accepted lines and the assembler
diagnostic for the `%rsp` index.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01cv` | names `x86:mov/r16-base-ext-index-disp8/legacy` against `0.46.0` | `E-FORM-001` |
| `N01cw` | names `x86:mov/base-index-ext-disp8-r16/legacy` against `0.46.0` | `E-FORM-001` |
| `N02bq` | drops the `index` from the `-base-ext` row | `E-OPERAND-002` (`expected 5, found 4`) |
| `N03z` | scale `4` on the `-base-ext` row, past the two-bit field | `E-RANGE-001` |
| `N14bd` | register `8` on the `-base-ext` row | `E-OPERAND-004` |
| `N14be` | base `8` on the `-index-ext` row | `E-OPERAND-004` |
| `N16by` | index `3` on the `-index-ext` row, below the window | `E-RANGE-004` |
| `N16bz` | base `3` on the `-base-ext` row, below the window | `E-RANGE-004` |

The claims the ADR turns on: the register field is three bits, so register `8`
must be rejected rather than cleared; the extended operand's slot excludes the
low window, so a low value cannot silently clear the fixed `REX.B`/`REX.X`;
and the non-extended operand is still three bits, so a value past `7` is
`E-OPERAND-004`.

`%rsp` is legal as a base in both windows (`66 42 8b 44 0c 08`), and `%r12` is
legal as a base in the `-base-ext` window (`66 41 8b 44 0c 08`) and as an index
in the `-index-ext` window (`66 42 8b 44 20 08`), which is why the negatives
use base `3`/index `3` rather than the `SIB`-encoded values.

## 5. The fixture

`X86-P51-gpr16-mov-index-ext-window` is twelve instructions and 90 bytes.

| # | Source | Bytes | Length |
|---|---|---|---|
| 1 | `movw 8(%r8,%rcx,1), %ax` | `66 41 8b 44 08 08` | 6 |
| 2 | `movw 8(%r15,%rdi,8), %di` | `66 41 8b 7c ff 08` | 6 |
| 3 | `movw 8(%rax,%r9,1), %ax` | `66 42 8b 44 08 08` | 6 |
| 4 | `movw 8(%rdi,%r15,8), %di` | `66 42 8b 7c ff 08` | 6 |
| 5 | `movw %ax, 8(%r8,%rcx,1)` | `66 41 89 44 08 08` | 6 |
| 6 | `movw %di, 8(%rdi,%r15,8)` | `66 42 89 7c ff 08` | 6 |
| 7 | `movw 200(%r8,%rcx,1), %ax` | `66 41 8b 84 08 c8 00 00 00` | 9 |
| 8 | `movw 200(%r15,%rdi,8), %di` | `66 41 8b bc ff c8 00 00 00` | 9 |
| 9 | `movw 200(%rax,%r9,1), %ax` | `66 42 8b 84 08 c8 00 00 00` | 9 |
| 10 | `movw 200(%rdi,%r15,8), %di` | `66 42 8b bc ff c8 00 00 00` | 9 |
| 11 | `movw %ax, 200(%r8,%rcx,1)` | `66 41 89 84 08 c8 00 00 00` | 9 |
| 12 | `movw %di, 200(%rdi,%r15,8)` | `66 42 89 bc ff c8 00 00 00` | 9 |

`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from our
materializer; the oracle's `input_sha256` is
`f0ec514ffdf8b3778ba3e3f10751c6e014bd1bfb5d8d674651e6465da52e92fb`
(`probe.asm`) and its `output_sha256` is
`a3ef1ce4b2d73280b701be00aaef0b559f4b552322f561aaef1feb47145d51ea`
(the 90-byte `.text`). The materializer's output is byte-identical to the
oracle and its artifact fingerprint is
`sha256:ab5fba1ab9d1333d6e24b3b15a13c46db0df8133fb4c51092942a7e3dd0330f8`.

`0.47.0` has 385 forms and the canonical digest
`sha256:0894646319c6f42071b0fd9d24417e27246a49343144540c80d05e49da7045c3`.

## 6. What the slice defers

- The `REX.BX` window (base and index both in `%r8`–`%r15`), whose shape is
  `66 43 8b 44 08 08`.
- The `0x67` address-size prefix.
- A symbol or relocation in a displacement.
- The no-base indexed shape (`SIB.base = 101` plus `mod = 00`).
- The APX `d5` register window.
