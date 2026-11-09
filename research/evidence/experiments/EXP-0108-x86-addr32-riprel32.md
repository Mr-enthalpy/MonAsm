# EXP-0108 -- the `0x67` prefix on the `%rip`-relative rows

- Date: 2026-11-09
- Question: the six GPR `mov` `%rip`-relative rows (`r16`/`r32`/`r64` ×
  load/store) carry no base or index. What does `0x67` do to them, where does
  the prefix sit relative to `0x66` and `REX`, and does the displacement stay
  the last 32 bits?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.70.0.json`; the generated `0.71.0` is the
  product of this experiment
- Fixture oracle: `fixtures/x86_64/positive/X86-P77-addr32-riprel32.oracle.json`
- Sources: `research/evidence/experiments/EXP-0108/probe.s`,
  `research/evidence/experiments/EXP-0108/X86-P77-addr32-riprel32.s`
- Decision: `ADR-0107`

## 1. What is already pinned

`EC-34` fixes the `%rip`-relative shape: `ModRM.mod = 00`, `ModRM.rm = 101`,
`disp32` from the end of the instruction (`pcrel_end`), and the value register
in `ModRM.reg` (`REX.R` for `r8`-`r15`). `0.6.0` shipped the `r64` pair and
`0.69.0` added the SSE pair, all at the plain encoding.

`EC-08` fixes the prefix: `0x67` is template byte 0, before any `REX`, and it
selects 32-bit address registers for a base and an index. The `%rip` form has
neither a base nor an index operand, so the only thing the prefix can rename is
the reference itself: `%eip` instead of `%rip`.

## 2. The measurement

`probe.s` is the six instructions at a literal `16(%rip)` displacement:

| Source | Bytes | Length |
|---|---|---|
| `addr32 movl 16(%rip), %eax` | `67 8b 05 10 00 00 00` | 7 |
| `addr32 movl %eax, 16(%rip)` | `67 89 05 10 00 00 00` | 7 |
| `addr32 movq 16(%rip), %rax` | `67 48 8b 05 10 00 00 00` | 8 |
| `addr32 movq %rax, 16(%rip)` | `67 48 89 05 10 00 00 00` | 8 |
| `addr32 movw 16(%rip), %ax` | `67 66 8b 05 10 00 00 00` | 8 |
| `addr32 movw %ax, 16(%rip)` | `67 66 89 05 10 00 00 00` | 8 |

The order is `0x67`, then the size prefix (`0x66` for the word row), then
`REX.W` (`0x48`), then the opcode. The displacement is still the last four
bytes, so the target placement is `[24,32]` for the seven-byte rows and
`[32,32]` for the eight-byte ones. `0x67` does not change the value operand's
width; `movw`/`movl`/`movq` keep `0x66`/none/`REX.W`.

## 3. The fixture

`X86-P77-addr32-riprel32.s` is the same six instructions naming one local label
after 16 bytes of `.space`; `L1` lands at offset 62. Each `pcrel_end`
displacement is `62 - (offset + length)`:

| Instruction | Offset | End | Displacement |
|---|---|---|---|
| `movl` load | 0 | 7 | 55 (`0x37`) |
| `movl` store | 7 | 14 | 48 (`0x30`) |
| `movq` load | 14 | 22 | 40 (`0x28`) |
| `movq` store | 22 | 30 | 32 (`0x20`) |
| `movw` load | 30 | 38 | 24 (`0x18`) |
| `movw` store | 38 | 46 | 16 (`0x10`) |

The image is 66 bytes (46 instruction bytes, 16 fill bytes, 4 data bytes):

```
678b0537000000 67890530000000 67488b0528000000
6748890520000000 67668b0518000000 6766890510000000
00000000000000000000000000000000 aabbccdd
```

The input hash is
`f1c995b4acd639b2c577fcf34498c53c965acc55ff10c4c48af83efaf1da7962`;
the output hash is
`9bda3dc77fa5b3abec9b6ac4e3e4a742c1f0d127fd13dec1c198c045c0fb2987`,
size 66, 0 relocation records (every fixup is `resolve_in_place`).

`0.71.0` has 533 forms and digest
`sha256:2858c0f163b1239b37f7be9ba294d8d81748038987a154afac66c2b63b4d2c5b`.
It repeats the 527 `0.70.0` forms unchanged.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01eq` | names `x86:mov/r64-addr32-riprel32/legacy` against `0.70.0` | `E-FORM-001` |
| `N02cz` | drops the target from `x86:mov/r32-addr32-riprel32/legacy` | `E-OPERAND-002` (`expected: 2`, `found: 1`) |
| `N04j` | literal `2147483648` on the signed-32 target | `E-RANGE-002` |

The plain `%rip` rows keep their own `0.6.0`/`0.69.0` forms, so a plan that
wants the prefixed shape names the new row instead of asking the materializer
to insert `0x67`.

## 5. What the slice defers

- The 8-bit value rows (`movb`): there is no `movb` `%rip`-relative row in the
  table, so the prefixed sibling is absent too.
- `%rip`-relative rows of other opcodes (`add`, `cmp`, `sub`, ...): this slice
  widens `mov` only.
- The `0x67` prefix combined with a base or index already has its own rows
  (`0.53.0`-`0.62.0`); this experiment only covers the base-less, index-less
  shape.
- `moffs` (`A0`-`A3`) remains out of scope.
