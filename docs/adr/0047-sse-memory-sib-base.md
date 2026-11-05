# ADR-0047: The SSE `movaps`/`vmovaps` memory rows reach `%rsp` and `%r12` through fixed `SIB` rows

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P24` (the `SIB` base of the legacy and VEX `movaps` memory rows at `xmm` width)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0046` §Review triggers (the SSE `SIB` base it named) and
  `ADR-0037` §Consequences (the same deferral line)

## Context

`ADR-0036` gave the SSE memory rows a base window and `ADR-0037` extended it to
`r8`–`r15`, but both left `%rsp`/`%r12` out because the pair forces a `SIB`
byte. The legacy and VEX families behave alike here, and unlike their general
rows:

1. **`%rsp` spends one byte.** `movaps 8(%rax), %xmm0` is `0f 28 40 08`, four
   bytes; `movaps 8(%rsp), %xmm0` is `0f 28 44 24 08`, five. `ModRM` becomes
   `r/m = 100` and a `SIB` byte follows, so the displacement moves one byte
   later. A row that accepted both bases and inserted the `SIB` on seeing the
   value would make the instruction length an operand fact (`INV-04`).
2. **`%r12` spends one more on each family.** In legacy the base's fourth bit is
   `REX.B`: `41 0f 28 44 24 08`, six bytes. In VEX only the three-byte form can
   carry `B̄ = 0`, so the row is `c4 c1 78 28 44 24 08`, eight bytes, two more
   than the two-byte `c5 f8 28 40 08`.
3. **The `SIB` byte is `24` in both families.** `scale = 00`, `index = 100`
   (none), `base = 100`; the base's identity comes from the prefix bit, not from
   the `SIB`.
4. **The displacement and the register move with the prefix.** Legacy puts
   `ModRM` at bit 16 (`%rsp`) or 24 (`%r12`), so `dest` sits at `[19,3]` or
   `[27,3]` and `disp` at `[32,…]` or `[40,…]`. VEX puts `ModRM` at bit 24 or
   32, so `dest` sits at `[27,3]` or `[35,3]` and `disp` at `[40,…]` or
   `[48,…]`.
5. **The EVEX family is a different decision.** `%r12` already costs nothing
   extra there — `B̄` is in the four-byte prefix — so only the `SIB` byte
   changes. It is left for its own slice rather than folded in here.

`EXP-0049` measures all of the above with `llvm-mc` 23.1.2 on 2026-11-06, and
each of the twenty measured byte strings round-trips through
`llvm-mc -disassemble` to the same source line.

## Decision

**`0.20.0` appends sixteen fixed-base rows: for each of the two families
(legacy `movaps`, two-byte/three-byte VEX) and each direction, `disp8` and
`disp32` at `%rsp` and at `%r12`, keeping each family's existing register
window — `xmm0`–`xmm7` on the legacy rows, whose field is three bare bits, and
`xmm0`–`xmm15` on the VEX rows, whose slot already carries the inverted `R`
bit. The base is fixed in the template and the row carries only the register
and the displacement. No `EC` row is added: `EC-02`, `EC-35` and `EC-38`
already state the shape, and `EC-35`/`EC-38` are revised in place so the SSE
families join their statements.**

The appended rows, one per `(family, direction, width, base)`:

| Family | Load `disp8`/`disp32` | Store `disp8`/`disp32` | Template |
|---|---|---|---|
| legacy | `x86:movaps/xmm-{rsp,r12}-disp{8,32}/legacy` | `x86:movaps/{rsp,r12}-disp{8,32}-xmm/legacy` | `[41] 0f 28/29 44/84 24 disp` |
| VEX | `x86:vmovaps/xmm-{rsp,r12}-disp{8,32}/vex` | `x86:vmovaps/{rsp,r12}-disp{8,32}-xmm/vex` | `c5 f8` or `c4 c1 78`, `28/29 44/84 24 disp` |

Four properties follow:

- **The base is the form.** `%rsp` costs the `SIB` byte and `%r12` costs the
  `SIB` plus `REX.B` (legacy) or the three-byte VEX, so no operand value changes
  a length.
- **The field offsets follow the prefix count.** `dest`/`disp` sit at
  `[19,3]`/`[32,…]` on the legacy `%rsp` rows, `[27,3]`/`[40,…]` on the legacy
  `%r12` rows, `[27,3]`/`[40,…]` on the VEX `%rsp` rows and
  `[35,3]`/`[48,…]` on the VEX `%r12` rows.
- **The register window is inherited, not widened.** The legacy rows keep the
  three-bit field, so `movaps 8(%rsp), %xmm8` (`44 0f 28 44 24 08`) still has
  no row; the VEX rows keep the inverted `R` bit, so `vmovaps 8(%r12), %xmm9`
  is already `c4 41 78 28 4c 24 08` on the new row.
- **The general rows keep their exclusions.** `-base-disp*` still excludes `4`
  and `-base-ext-disp*` still excludes `12`, so the fixed-base rows and the
  general rows are disjoint and one `(register, base)` pair names one row.
- **`mod = 00` stays absent.** `movaps (%rsp), %xmm0` is `0f 28 04 24` and
  `movaps (%r12), %xmm0` is `41 0f 28 04 24`; they need the no-displacement
  decision (`ADR-0039`), not this one.

## Consequences

- `0.20.0` is a 171-form document with digest
  `sha256:b8bd1ed3ed38d71f6b19cc1854c9252df13850127c4e9433981a3a45f49d0f99`.
- Its positive fixture `X86-P24-sse-mem-sib` has sixteen instructions and
  120 bytes, one per row: the legacy eight run `xmm0`–`xmm7`, the VEX eight
  `xmm8`–`xmm15`.
- Negatives pin the version boundary against `0.19.0`, the absent
  no-displacement row, an operand-class mismatch, the extra `base` operand the
  fixed-base shape refuses, the `disp8` content end and the legacy three-bit
  register field.
- `07_definition_format.md` §8.1 gains the sixteen rows, the `0.20.0` digest
  row and narrative; `02_encoding_choices.md` gains the surface rows and revises
  `EC-35` and `EC-38` in place.
- No schema, loader or materializer change: the rows use the fixed-base shape
  `0.3.0` introduced and the `SIB` byte is part of the template.
- Still absent on this axis: the EVEX `SIB` base, the `ymm`/`zmm` memory rows,
  the legacy `REX.R` register window with a fixed base, `mod = 00`, an index or
  scale under these opcodes, and the SSE RIP-relative row.

## Alternatives rejected

- **One row per family with a four-bit base and a mandatory `SIB`.** A general
  base would start paying a `SIB` byte it does not spend (`EC-35`), so every
  existing SSE memory byte would change.
- **A `sib` modifier or a `base` operand that selects the shape.** A modifier may
  not write bits (`ADR-0015`) and the length would become a plan choice
  (`INV-04`).
- **Give `%rsp` and `%r12` one row each across both families.** The legacy and
  VEX templates differ in length and in where `ModRM` sits, so one row cannot
  carry both prefixes without an operand-selected prefix.
- **Fold the EVEX family in.** `%r12` costs no extra prefix byte there, so the
  counterexample (a length change) does not exist; mixing the two would make the
  decision statement ambiguous.
- **Include the legacy `xmm8`–`xmm15` window.** `REX.R` is a register decision;
  adding it would move the register slot again while the base slot is also
  moving. The VEX rows need no such choice: their `R` bit is already in the
  template, so they reach the whole file here.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `0f 28 44 24 08`, `41 0f 28 44 24 08`, `0f 29 44 24 08` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0049` §1 | high |
| `c5 f8 28 44 24 08`, `c4 c1 78 28 44 24 08`, `c4 c1 78 29 44 24 08` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0049` §1 | high |
| `dest`/`disp` sit at `19/32`, `27/40`, `27/40`, `35/48` by template prefix count | the byte strings above; `EXP-0049` §2 | high |
| `SIB = 24` and `%r12` differs only in `REX.B`/`B̄` | `llvm-mc -show-encoding`, `EXP-0049` §2 | high |
| `movaps (%rsp), %xmm0` is `0f 28 04 24` (a different, `mod = 00` shape) | `llvm-mc -show-encoding`, `EXP-0049` §4 | high |
| `disp8` ends are `127`/`-128` and `128`/`-129` are `disp32` | `llvm-mc -show-encoding`, `EXP-0049` §1 | high |
| The VEX rows reach `xmm8`–`xmm15` (`c5 78`, `c4 41 78`) while the legacy rows stop at `xmm7` | `llvm-mc -show-encoding`, `EXP-0049` §3 | high |

## Review triggers

- The EVEX `SIB` base is attempted: `{evex} vmovaps 8(%rsp), %xmm0` is
  `62 f1 7c 08 28 84 24 08 00 00 00` and `%r12` only flips `P0` to `62 d1`.
- A `ymm`/`zmm` `SIB` base is attempted: `vmovaps 8(%rsp), %ymm0` is
  `c5 fc 28 44 24 08`, the same shape with `L = 1`.
- The legacy `xmm8`–`xmm15` window is attempted with a fixed base:
  `44 0f 28 44 24 08` needs `REX.R` on a row that does not carry it.
- `mod = 00` is attempted for these opcodes: `0f 28 04 24` is the zero
  displacement with the same `SIB`, and `%rbp`/`%r13` need the `disp8` zero form.
- An index or scale is attempted: `8(%rsp,%rax,1)` is `0f 28 44 04 08`, a
  different `SIB` byte (`index = 000`), not this shape.
- The SSE RIP-relative row is attempted: `movaps 8(%rip), %xmm0` needs
  `r/m = 101` and a `rel32` operand, not a base register.
