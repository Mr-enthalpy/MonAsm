# EXP-0048 -- the 8/16-bit `mov` memory rows with a `SIB` base

- Date: 2026-11-06
- Question: how do the 8/16-bit `mov` memory rows encode `%rsp` and `%r12` as
  the base, where does the `SIB` byte put `ModRM` and the displacement, and
  which family can carry the high-byte set on such a base?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.19.0.json`
  (`sha256:dddc678fe0abc6fa03c2e61c8fcafef2570b496775a11a25e1ab29e01bfe5130`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P23-mov-mem-sib.oracle.json`
- Source: `research/evidence/experiments/EXP-0048/P23.asm`
- Fixture source: `research/evidence/experiments/EXP-0048/fixture.asm`
- Decision: `ADR-0046`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-06.

| Source | Bytes | Length |
|---|---|---|
| `movw 8(%rsp), %ax` | `66 8b 44 24 08` | 5 |
| `movw 8(%r12), %ax` | `66 41 8b 44 24 08` | 6 |
| `movw 128(%rsp), %ax` | `66 8b 84 24 80 00 00 00` | 8 |
| `movw 128(%r12), %ax` | `66 41 8b 84 24 80 00 00 00` | 9 |
| `movw %ax, 8(%rsp)` | `66 89 44 24 08` | 5 |
| `movw %ax, 8(%r12)` | `66 41 89 44 24 08` | 6 |
| `movw %ax, 128(%rsp)` | `66 89 84 24 80 00 00 00` | 8 |
| `movw %ax, 128(%r12)` | `66 41 89 84 24 80 00 00 00` | 9 |
| `movw 127(%r12), %ax` | `66 41 8b 44 24 7f` | 6 |
| `movw -128(%rsp), %ax` | `66 8b 44 24 80` | 5 |
| `movw %ax, -129(%r12)` | `66 41 89 84 24 7f ff ff ff` | 9 |
| `movb 8(%rsp), %al` | `8a 44 24 08` | 4 |
| `movb 8(%r12), %bl` | `41 8a 5c 24 08` | 5 |
| `movb 128(%rsp), %cl` | `8a 8c 24 80 00 00 00` | 7 |
| `movb 128(%r12), %dl` | `41 8a 94 24 80 00 00 00` | 8 |
| `movb %al, 8(%rsp)` | `88 44 24 08` | 4 |
| `movb %bl, 8(%r12)` | `41 88 5c 24 08` | 5 |
| `movb %cl, 128(%rsp)` | `88 8c 24 80 00 00 00` | 7 |
| `movb %dl, 128(%r12)` | `41 88 94 24 80 00 00 00` | 8 |
| `movb 127(%rsp), %cl` | `8a 4c 24 7f` | 4 |
| `movb 8(%rsp), %ah` | `8a 64 24 08` | 4 |
| `movb 128(%rsp), %bh` | `8a bc 24 80 00 00 00` | 7 |
| `movb %ah, 8(%rsp)` | `88 64 24 08` | 4 |
| `movb %ch, 128(%rsp)` | `88 ac 24 80 00 00 00` | 7 |
| `movb 8(%rsp), %spl` | `40 8a 64 24 08` | 5 |
| `movb 8(%r12), %bpl` | `41 8a 6c 24 08` | 5 |
| `movb 128(%rsp), %sil` | `40 8a b4 24 80 00 00 00` | 8 |
| `movb 128(%r12), %dil` | `41 8a bc 24 80 00 00 00` | 8 |
| `movb %spl, 8(%rsp)` | `40 88 64 24 08` | 5 |
| `movb %bpl, 8(%r12)` | `41 88 6c 24 08` | 5 |
| `movb %sil, 128(%rsp)` | `40 88 b4 24 80 00 00 00` | 8 |
| `movb %dil, 128(%r12)` | `41 88 bc 24 80 00 00 00` | 8 |

`llvm-mc -disassemble` on `probes.txt` returns all twenty-eight unique byte
strings as the same source line.

Every row spends one byte on the `SIB` (`24`: `base = 100`, `index = 100`,
`scale = 00`) and, for `%r12`, one more on `REX.B`. So the length decisions are
the same three as `0.3.0`/`0.7.0` made for `movq`, repeated inside the 8/16-bit
families: `%rsp` is one byte longer than a general base, `%r12` one more.

## 2. Where the fields sit

| Row family | Template | `ModRM.reg` | `disp` |
|---|---|---|---|
| word `%rsp` | `66 8b/89 ModRM 24 disp` | `[19,3]` | `[32,8]`/`[32,32]` |
| word `%r12` | `66 41 8b/89 ModRM 24 disp` | `[27,3]` | `[40,8]`/`[40,32]` |
| low byte `%rsp` | `8a/88 ModRM 24 disp` | `[11,3]` | `[24,8]`/`[24,32]` |
| low byte `%r12` | `41 8a/88 ModRM 24 disp` | `[19,3]` | `[32,8]`/`[32,32]` |
| high byte `%rsp` | `8a/88 ModRM 24 disp` | `[11,3]` | `[24,8]`/`[24,32]` |
| `40` byte `%rsp` | `40 8a/88 ModRM 24 disp` | `[19,3]` | `[32,8]`/`[32,32]` |
| `40` byte `%r12` | `41 8a/88 ModRM 24 disp` | `[19,3]` | `[32,8]`/`[32,32]` |

The `SIB` byte pushes everything after `ModRM` one byte later than on the
`-base-disp*` rows: the word rows move the displacement from bit 24 to 32 (or
40 with `REX`), and the byte rows from 16 to 24 (or 32). `ModRM` itself is not
at a fixed offset inside a family — the `66` and the `REX` are both template
bytes — which is why the word `%r12` row reads its register at `[27,3]` and the
low-byte `%r12` row at `[19,3]`, exactly as the `0.18.0` `-base-ext` rows do.

## 3. Only three families can carry a high base

| Register numbers | `%rsp` base | `%r12` base |
|---|---|---|
| `0`–`3` (`al`–`bl`) | `88`/`8a` row, no `REX` | `41 88`/`41 8a` row |
| `4`–`7` (`spl`–`dil`) | `40 88`/`40 8a` row | `41 88`/`41 8a` row |
| `4`–`7` (`ah`–`bh`) | `88`/`8a` high-byte row | no encoding |

`movb %ah, 8(%r12)` is rejected with
`can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`, because
the `REX.B` byte that names `%r12` also renames `ah` to `spl`. The high-byte
family therefore gets two `%rsp` rows per direction and width and no `%r12`
row at all. `0.18.0` already recorded the same asymmetry on the general rows;
this slice only makes the `SIB` half of it explicit.

## 4. What the slice defers

- `movw %ax, 8(%esp)` assembles as `67 66 89 44 24 08`: a 32-bit base spends an
  address-size prefix instead of `REX`, so it is a different mnemonic family
  and stays out (`0x67` is still deferred).
- `mod = 00`: no GPR memory row has it at any width, so `(%rsp)` and `(%r12)`
  are still absent; the smallest displacement is the `disp8` row with content
  `0`.
- Four-bit registers: `66 44 89 40 08` is `movw %r8w, 8(%rax)` and
  `44 88 40 08` is `movb %r8b, 8(%rax)`; they need `REX.R` on rows that do not
  carry it yet.
- Index and scale: the `SIB` byte of these rows has `index = 100` (none) and
  `scale = 00`; `8(%rsp,%rax,1)` is a different form, not this one.

## 5. The definition rows

`0.19.0` appends twenty-eight rows, one per `(family, direction, width, base)`
combination: word load/store, REX-less low-byte load/store, high-byte
load/store (`%rsp` only) and `40`-prefixed byte load/store, each at `disp8` and
`disp32` and at both fixed bases. The base is part of the template, not a slot,
so the row carries only the register and the displacement — the same shape
`0.3.0` used for `movq` and `0.7.0` for `%r12`.

## 6. The fixture

`X86-P23-mov-mem-sib` is twenty-eight instructions and 178 bytes: one per row,
`disp8` content `8` and `disp32` content `128`. `expected.bin` comes from
`llvm-mc` + `llvm-objcopy`, never from our materializer; the oracle's
`input_sha256` is `fixture.asm` (`0f9fb342...`) and its `output_sha256` is the
178-byte `.text` (`fcc30907...`). `llvm-mc -disassemble` round-trips all
twenty-eight byte strings.

## 7. Negative coverage

- `N01ap` names `x86:mov/r16-rsp-disp8/legacy` against `0.18.0`:
  `E-FORM-001`, the version boundary.
- `N01aq` names `x86:mov/r8h-r12-disp8/legacy`, which has no encoding:
  `E-FORM-001`, the high-byte refusal.
- `N02u` passes a `x86.gpr16` operand to a byte row: two `E-OPERAND-001`, on
  `kind` and `target_type`.
- `N03h` passes displacement content `128` to a `disp8` slot: `E-RANGE-001`.
- `N14v` passes register `8` to the three-bit byte field: `E-OPERAND-004`.
- `N16y` passes number `0` to a `40` row, whose window is `4`–`7`:
  `E-RANGE-004`.
