# EXP-0036 — x86-64 `r8`–`r15` as a memory base, and the `%r12` SIB shape

- Date: 2026-11-05
- Question: how does a base+displacement operand reach the extended GPRs, and
  what does the base number's low three bits do to the shape?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.7.0.json`
  (`sha256:8c40c948a3a103b7d0668a4539f5cc8bc95e3cdba12b62c0c6a00bbc2ee92f1c`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P11-base-extended.oracle.json`
- Source: `research/evidence/experiments/EXP-0036/P11.asm`
- Decision: `ADR-0034`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05:

| Source | Bytes | `REX` | `ModRM` | `SIB` |
|---|---|---|---|---|
| `movq 8(%r8), %rax` | `49 8b 40 08` | `0100 1001` `W=1 B=1` | `01 000 000` | — |
| `movq 8(%r9), %rax` | `49 8b 41 08` | `W=1 B=1` | `01 000 001` | — |
| `movq 8(%r13), %rax` | `49 8b 45 08` | `W=1 B=1` | `01 000 101` | — |
| `movq 8(%r12), %rax` | `49 8b 44 24 08` | `W=1 B=1` | `01 000 100` | `24` |
| `movq 8(%rsp), %rax` | `48 8b 44 24 08` | `W=1 B=0` | `01 000 100` | `24` |
| `movq 128(%r12), %rax` | `49 8b 84 24 80 00 00 00` | `W=1 B=1` | `10 000 100` | `24` |

The base number is four bits: the low three go to `ModRM.r/m` (`[16,3]`), the
fourth to `REX.B` (`[0,1]`). `r8`–`r11` and `r13`–`r15` are therefore the old row
with one prefix bit set. `r12` is not: its low three bits are `100`, the same as
`%rsp`, so `mod = 01`/`10` with `r/m = 100` is followed by a `SIB` byte whose
base field is also `100`; the only difference between the `%rsp` and `%r12`
encodings is `REX.B` (`0x48` vs `0x49`).

## 2. Why `%r12` is a form and not an operand value

If the general rows accepted `12` and inserted a SIB byte when they saw
`base & 7 == 4`, the encoded length would change from an operand value: 4 bytes
versus 5 at `disp8`, 7 versus 8 at `disp32`. That is `INV-04` (no implicit layout
change) and it would move every later fragment offset. `0.7.0` therefore:

- excludes `4` and `12` from the general rows (`E-RANGE-004`), and
- carries four fixed-base `%r12` rows whose `REX` byte is `0x49` and whose `SIB`
  is `24` in the template, exactly as the `%rsp` rows carry `0x48` and `24`.

The register operand slot still widens: `movq 8(%rsp), %r9` is
`4c 8b 4c 24 08` (`REX.R = 1`), and `movq 8(%r12), %r9` is `4d 8b 4c 24 08`.

## 3. The oracle

`P11.asm` is seventeen `mov` mnemonics with no hand-assembled bytes. `.text` is
93 bytes and the plan emits no record. Output SHA-256
`9cb771540e5da04bce8afb9df35e5d06c32bfe3fe1ba006a11ac3c5499ca5ad0`.

Every displacement in the source fits the width of the form the plan names
(`8`, `-1`, `127` for `disp8`; `128` for `disp32`), so `llvm-mc`'s own choice of
`mod` coincides with the named form; no promotion is being relied on. The plan
does not ask the materializer to choose between the two forms.

## 4. The rejections

`N16h` names `0.7.0`'s `x86:mov/r64-base-disp8/legacy` with `base.reg = 12`.
The value fits the 4-bit field but the shape needs a SIB byte, so the plan is
rejected before any byte is written:

```text
E-RANGE-004  /instructions/0/operands/1/payload/reg
             target_type=rm64 value=12 excluded=[4, 12]
```

`N01ac` names `x86:mov/r64-r12-disp8/legacy` against `0.6.0`, where that row does
not exist: `E-FORM-001`. This is the version boundary, not a silent fallback to
a general row.

## 5. What this does not claim

- `REX.X` is still unexercised. It extends a `SIB` index, and no v0 row has an
  index operand; `base + index*scale + disp` is a separate shape with its own
  scale field and the `index = 4` ("no index") rule.
- `mod = 00` (no displacement) is not a v0 row, so the `r13`/`r/m = 101`
  collision with RIP has no fixture here; it is exercised by the `0.2.0`
  RIP-relative rows instead.
- The 8-bit and 16-bit rows still keep 3-bit register fields.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
