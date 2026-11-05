# ADR-0035: The SIB index and scale are operands, and `REX.X` extends the index

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P12` (the index/scale addressing shape) and `EC-37`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0034` shipped the extended base and left two things out on purpose:
`base + index*scale + disp` is a different `SIB` shape, and it is the only shape
that exercises `REX.X`. Measured with `llvm-mc` 23.1.2 (`EXP-0037`):

| Source | Bytes | `REX` | `ModRM` | `SIB` |
|---|---|---|---|---|
| `movq 8(%rax,%rcx,1), %rdx` | `48 8b 54 08 08` | `0100 1000` | `01 010 100` | `00 001 000` |
| `movq 8(%rax,%rcx,8), %rdx` | `48 8b 54 c8 08` | `W=1` | `01 010 100` | `11 001 000` |
| `movq 8(%r8,%r9,2), %r10` | `4f 8b 54 48 08` | `W=1 R=1 X=1 B=1` | `01 010 100` | `01 001 000` |
| `movq 8(%rax,%r12,4), %rdx` | `4a 8b 54 a0 08` | `X=1` | `01 010 100` | `10 100 000` |
| `movq 8(%r13,%r12,8), %rdx` | `4b 8b 54 e5 08` | `X=1 B=1` | `01 010 100` | `11 100 101` |
| `movq 8(%r12,%r13,8), %r15` | `4f 8b 7c ec 08` | `W=1 R=1 X=1 B=1` | `01 111 100` | `11 101 100` |

Four facts come out of the measurements:

1. **`r/m = 100` is the shape, not an operand value.** It announces a `SIB` byte
   even when the base is `%rsp` or `%r12`, so in this shape `4` and `12` are
   ordinary bases. That is the opposite of the base+displacement rows of
   `ADR-0034`, where the same two numbers had to be excluded.
2. **`SIB.index = 100` with `REX.X = 0` means "no index".** `48 8b 54 20 08`
   decodes as `movq 8(%rax,%riz), %rdx`: the index register silently disappears
   and the instruction means something else. `%rsp` can never be an index, and
   `llvm-mc` refuses `8(%rax,%rsp,1)` with `invalid base+index expression`.
   With `REX.X = 1` the same field is `%r12` (`4a 8b 54 a0 08`), so the
   exclusion is exactly `4`, not `4` and `12`.
3. **The scale field is two bits of field content.** `00`/`01`/`10`/`11` mean
   ×1/×2/×4/×8. The multiplier is a derived value (`1 << content`), so a plan
   that carried the multiplier would need the materializer to compute the field
   from it — an implicit encoding step (`INV-02`), and one that overflows the
   field for ×16.
4. **`REX.X` is the index's fourth bit**, placed at bit 1, the same way
   `REX.R`/`REX.B` carry the register and base (`ADR-0033`, `ADR-0034`).

## Decision

**`0.8.0` adds four `SIB` rows; base, index, scale and displacement are one
operand each, and the scale is carried as two bits of field content.**

1. **The rows.** `x86:mov/r64-base-index-disp8/legacy` (`488b440000`),
   `-base-index-disp32` (`488b840000000000`),
   `x86:mov/base-index-disp8-r64/legacy` (`4889440000`) and
   `-base-index-disp32-r64` (`4889840000000000`). `ModRM.r/m = 100`, `mod = 01`
   or `10`, and the `SIB` byte are template, so the instruction length never
   follows an operand value. `mod = 00` (no displacement) stays absent.
2. **`base` is four bits and excludes nothing.** `REX.B` is `[0,1]` and
   `SIB.base` is `[24,3]`; all sixteen values are legal here, including `4`
   (`%rsp`) and `12` (`%r12`), because the shape already answered the SIB
   question.
3. **`index` is four bits and excludes `4`.** `REX.X` is `[1,1]` and
   `SIB.index` is `[27,3]`, `target_type: sib_index`. `4` is `E-RANGE-004`
   (`N16i`); `12` is legal and reaches `%r12` through `REX.X = 1`.
4. **The scale is field content, `0…3`.** `role: imm`, `kind: x86.scale`,
   `target_type: scale2`, `from: operand_value`, `range {signed: false,
   bits: 2, align_bits: 0}`, at `[30,2]`. `aarch64.cond`/`cond4` is the
   precedent for carrying a fixed-position, non-arithmetic field under the
   `imm` role: the contract's `role` set is closed and a role exists to make
   position-dependent order explicit, which the `SIB` byte already does.
   `kind` still selects the encoder, so a plan that spells the scale
   `x86.imm` is `E-OPERAND-001` and never writes a bit.
5. **The operand order is `dest`/`src`, `base`, `index`, `imm` (scale), `disp`**,
   with `disp` last as in every other x86 memory row. The materializer compares
   the role sequence for equality, so the order is a form fact, not a
   convention an encoder may reorder (`E-OPERAND-002`).

## Consequences

- `0.8.0` is the first x86 table with `REX.X` exercised: a 33-form document
  with digest `sha256:e55f694ae29e90854c8352aba60202cbd060d6333aff2a69b2e54978910155f5`.
  `X86-P12-base-index-scale` is its positive fixture: the four scale contents
  over one base/index pair, three extension bits at once
  (`movq 8(%r8,%r9,2), %r10` = `4f 8b 54 48 08`), `%r12` as an index
  (`4a 8b 54 a0 08`), `%r12` as a base (`4f 8b 7c ec 08`), both disp32 rows,
  both directions, `%rsp` as a base and `%rbp` as an index (`EXP-0037`).
- `N16i` pins `index = 4` (`E-RANGE-004`), `N03c` pins the multiplier `8`
  against the two-bit field (`E-RANGE-001`), and `N01ad` pins the version
  boundary: the row does not exist in `0.7.0` (`E-FORM-001`).
- `EC-37` is the encoding-choice row for the shape; `EC-35` records that the
  SIB byte now has operand-owned fields; `EC-06` records that `X` is no longer
  the unused bit.
- `07_definition_format.md` §8.1 gains the four rows and the `0.8.0` digest
  row.
- Still absent: `mod = 00` (`SIB` with no displacement), a base-only `SIB` row
  (`index = 4` as a legal value), scaled-index rows at 8/16-bit or SSE widths,
  the `0x67` address-size prefix, and a `SIB` base of `101` with `mod = 00`
  (which means "no base" and needs a `disp32`).
