# ADR-0034: The memory base is four bits, and `%rsp`/`%r12` are SIB shapes

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P11` (the extended base register) and the `EC-35` base half
- Supersedes: none
- Superseded by: none

## Context

`ADR-0033` widened the six register-direct 64-bit rows to four bits and left the
base+displacement family at three, because the base is not just a `ModRM` field:

| Source | Bytes | `ModRM` | `SIB` |
|---|---|---|---|
| `movq 8(%r8), %rax` | `49 8b 40 08` | `01 000 000` | — |
| `movq 8(%r12), %rax` | `49 8b 44 24 08` | `01 000 100` | `24` |
| `movq 8(%r13), %rax` | `49 8b 45 08` | `01 000 101` | — |
| `movq 8(%rsp), %rax` | `48 8b 44 24 08` | `01 000 100` | `24` |

`r8`–`r11`, `r13`, `r14` and `r15` differ from the existing rows only by
`REX.B`, which is bit 0 — the same placement `ADR-0033` already established.
`r12` and `rsp` do not: their low three bits are `100`, so `r/m = 100` and the
byte after `ModRM` is a `SIB`, whose base field is also `100`; the two registers
are told apart by `REX.B` alone (`49` versus `48`). The SIB byte is therefore
shape, not content: a row that accepted both values and inserted the SIB when it
saw `100` would change the instruction length from an operand value, and would
make the fixup offset and every following fragment offset depend on it
(`INV-04`).

There is also a `mod` interaction: `r13` is `101`, and `mod = 00` with
`r/m = 101` is the `RIP`-relative shape (`ADR-0027`). The v0 base+displacement
rows only carry `mod = 01` (`disp8`) and `mod = 10` (`disp32`), so `r13` is
unambiguous there; a future no-displacement (`mod = 00`) row would have to
exclude it, exactly as it excludes `rsp`.

## Decision

**The base and the `ModRM.reg` operand of a base+displacement row are four bits;
the SIB byte stays a form fact.**

1. **The eight general rows widen, and exclude the two SIB-forcing bases.** In
   `0.7.0`, `x86:mov/r64-base-disp8/legacy`, `-base-disp32`, `base-disp8-r64` and
   `base-disp32-r64` gain `excluded: [4, 12]` and four-bit `base`, `dest`/`src`
   slots: `REX.B` is `[0,1]` and the low three bits `[16,3]` for `base`;
   `REX.R` is `[2,1]` and the low three bits `[19,3]` for the register operand.
   Accepting `4` or `12` there would emit a different shape (`E-RANGE-004`).
2. **`%rsp` keeps its four fixed-base rows and `%r12` gets four of its own.**
   `x86:mov/r64-rsp-disp8/legacy`, `-rsp-disp32`, `rsp-disp8-r64` and
   `rsp-disp32-r64` keep `REX = 0x48`. The new
   `x86:mov/r64-r12-disp8/legacy`, `-r12-disp32`, `r12-disp8-r64` and
   `r12-disp32-r64` are the same rows with `REX = 0x49`; they have no `base`
   slot, because the base is a template constant, exactly like `%rsp`.
   The register operand slot still widens (`REX.R`, `[2,1]` + `[19,3]`).
3. **One encoding per `(form, operands)`, as in `ADR-0033`.** `movq 8(%r12), %rax`
   names `-r12-disp8`; `movq 8(%rsp), %rax` names `-rsp-disp8`; neither can be
   produced through a general row, and no operand bit can turn one into the
   other.
4. **`REX.X` stays unexercised.** It extends the `SIB` index, and v0 has no
   index operand. `base + index*scale + disp` is a new operand shape
   (one slot per encoded field, `ADR-0008`), a new scale field, and the rule
   that index `4` means "no index" while index `12` is `r12` with `REX.X = 1`.
   It needs its own encoding-choice row and ADR; it does not ride along here.

## Consequences

- `0.7.0` is the first x86 table with sixteen base+displacement rows and a new
  digest. `X86-P11-base-extended` is its positive fixture: `r8`–`r15` bases in
  both directions at both widths, including `%r12` through its own rows and
  `%rsp` unchanged (`EXP-0036`).
- `N16h` pins `base = 12` on a general row (`E-RANGE-004`, the `%r12`
  exclusion) and `N01ac` pins the version boundary: `r12`-base rows do not exist
  in `0.6.0` (`E-FORM-001`).
- `EC-35` stays `frozen` and now records that the `r12` half of the SIB
  question is shipped; `EC-06` records that `B` now reaches a memory base and
  `R` reaches a base+disp register operand, leaving only `X`.
- `07_definition_format.md` §8.1 gains the twelve widened rows and the four
  `r12` rows; the table remains keyed by `form_id` with the newest version in
  force, so it is the `0.7.0` reading that `check_definition.py` compares.
