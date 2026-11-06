# ADR-0072: the 16-bit `mov` memory rows take a `SIB` index and scale

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P49` (the index, scale and `REX.X` window over the 16-bit
  indexed `mov` rows, both directions and both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the displacement now sits behind the `SIB` byte on the
  indexed 16-bit rows), `EC-06` (`REX.X` now reaches a 16-bit row),
  `EC-37` (the `SIB` index and scale now also exist at 16-bit width),
  `EC-38` (the indexed rows carry the whole base window in one row)

## Context

`0.44.0` gave the 16-bit `disp8`/`disp32` `mov` rows the `%r8w`–`%r15w`
register window (`ADR-0070`, `ADR-0071`). Those rows carry a `REX` byte
because `REX.R` is fixed in the template, so the same byte can also carry
`REX.B` and `REX.X` at no length cost. The rows still hold only one base
value each, and `movw 8(%rax,%rcx,1), %r8w` is not plannable, although it is
`66 44 8b 44 08 08`.

`EC-37` already fixes the index/scale shape: the `SIB` byte's three fields are
one operand each (`base`, `index`, and a two-bit scale carried as field
content), the index's fourth bit is a prefix bit, and `index = 4` — the "no
index" encoding — is the excluded value. `EC-06` fixes the `REX` placement:
the prefix byte is part of the form, so an extension bit either exists in the
template or is a slot, never a length decision.

`EXP-0074` measures the shapes and four facts come out:

1. **One `REX` byte carries all three extension bits.** `movw
   8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08`: `REX = 44` (`R = 1`),
   `ModRM = 44` (`mod = 01`, `reg = 0`, `r/m = 100`), `SIB = 08` (`scale = 0`,
   `index = 1`, `base = 0`) and the displacement at `[40,8]`.
   `movw 8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08`: `REX = 47` is
   `R = 1`, `X = 1`, `B = 1`, and the row is still six bytes.
2. **The base is one four-bit slot.** `movw 8(%r8,%rdi,2), %r8w` is
   `66 45 8b 44 78 08` (`REX = 45`, `B = 1`, `SIB = 78` with base `0`) and
   `movw %r15w, 8(%rdi,%r12,4)` is `66 46 89 7c a7 08` (`REX = 46`, `X = 1`,
   `SIB = a7` with base `7`, index `4`), so `REX.B` and `SIB.base` together
   reach all sixteen bases without a form split.
3. **`%r12` is an index, `%rsp` is not.** `SIB.index = 100` with `REX.X = 0`
   means "no index"; with `REX.X = 1` it is `%r12`. `llvm-mc` rejects
   `8(%rax,%rsp,1)` with `invalid base+index expression`.
4. **The displacement moves behind the `SIB` byte, never widens with the
   scale.** The `disp8` rows put the signed byte at `[40,8]` (`127` is `7f`,
   `-128` is `80`) and the `disp32` rows put four bytes at `[40,32]`; the
   scale is only the two `SIB` bits `0…3` for ×1/×2/×4/×8.

## Decision

**`0.45.0` appends four rows: two directions × two displacement widths, with
`REX.R` fixed in the template, the low register window excluded, a four-bit
base (`REX.B` + `SIB.base`), a four-bit index (`REX.X` + `SIB.index`, `4`
excluded), the scale as two bits of field content and the signed
displacement at `[40,8]` or `[40,32]`.**

| Direction | Displacement | `form_id` | Template | Length | Slots |
|---|---|---|---|---|---|
| load | `disp8` | `x86:mov/r16-ext-base-index-disp8/legacy` | `66 44 8b 44 00 00` | 6 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm `x86.scale`/`scale2` → `[38,2]`; disp `x86.imm`/`disp8` → `[40,8]` |
| store | `disp8` | `x86:mov/base-index-disp8-r16-ext/legacy` | `66 44 89 44 00 00` | 6 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm `x86.scale`/`scale2` → `[38,2]`; disp `x86.imm`/`disp8` → `[40,8]` |
| load | `disp32` | `x86:mov/r16-ext-base-index-disp32/legacy` | `66 44 8b 84 00 00 00 00 00` | 9 | dest `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm `x86.scale`/`scale2` → `[38,2]`; disp `x86.imm`/`disp32` → `[40,32]` |
| store | `disp32` | `x86:mov/base-index-disp32-r16-ext/legacy` | `66 44 89 84 00 00 00 00 00` | 9 | src `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0–7); base `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm `x86.scale`/`scale2` → `[38,2]`; disp `x86.imm`/`disp32` → `[40,32]` |

Four properties follow:

- **The base is one window, not two.** `REX.B` is a slot on the same byte the
  `REX.R` template already carries, so `%rax` and `%r15` share a row. `%rsp`
  and `%r12` are legal because a `SIB` byte is present at `mod = 01`/`10`;
  `%rbp`/`%r13` are legal because `r/m = 100` is the `SIB` announcement and
  `SIB.base = 101` is a base with a displacement.
- **The index is `REX.X` plus three `SIB` bits.** `4` is the one excluded
  value: `REX.X = 0` would mean "no index", so accepting it would silently
  drop the operand (`INV-07`). `%r12` stays legal because its low three bits
  are `100` and `REX.X = 1`.
- **The scale is content, never a multiplier.** `0…3` are the bits for
  ×1/×2/×4/×8; `4` is `E-RANGE-001`, never a truncated `0` (`INV-07`).
- **The displacement is still a signed field.** `disp8` sits at `[40,8]` and
  `disp32` at `[40,32]`; the width is the `form_id`, not an operand-driven
  choice (`INV-04`).

## Consequences

- `0.45.0` is a 373-form document, byte-reproducing every `0.44.0` row.
- Its positive fixture `X86-P49-gpr16-mov-index-rex-rx` has twelve
  instructions and 90 bytes: both directions at both displacement widths,
  the four scale factors, both ends of the register window, low and high
  bases and low and high indexes. `input_sha256` is
  `8123b0a50e7d0c1cb471258dffd01eaa0336e2b9076b41574edc20eedcf5dd33`,
  `output_sha256` is
  `69fc575b15b585f3651bd84a3757403f1445fac20e80ba26ae5bd0b7f3e7f499`.
- Negatives pin the version boundary in both directions (`N01cr`, `N01cs`),
  a missing index (`N02bo`), the scale field's end (`N03x`), the register
  field's end (`N14ay`), the `%rsp` index exclusion (`N16bv`), the fixed
  `REX.R` bit (`N16bw`) and the base field's end (`N14az`).
- `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place. No new `EC` row
  appears and no row is renumbered.
- No schema, loader or materializer change: the rows reuse the existing
  `x86.gpr16`/`r16`, `x86.gpr64`/`rm64`, `x86.gpr64`/`sib_index`,
  `x86.scale`/`scale2` and `x86.imm`/`disp8`/`disp32` kinds.

## Alternatives rejected

- **One row per base or index window.** `REX.B` and `REX.X` are slots on a
  byte the row already pays for; splitting the windows would add rows without
  changing a single byte (`EC-38`).
- **Accept index `4` and drop it.** That is a silent repair of an illegal
  operand, and `SIB.index = 100` with `REX.X = 0` means "no index" (`INV-07`).
- **Carry the multiplier instead of the field content.** The materializer
  would have to compute `1 << content` (an implicit encoding step, `INV-02`)
  and could not express ×16; the field content `4` is `E-RANGE-001`.
- **Let one row choose `disp8` or `disp32` from the value.** The instruction
  length would depend on the operand (`INV-04`); the displacement width is
  the `form_id`.
- **Add the `0x67` address-size prefix or the APX `d5` window now.** Both are
  different forms with their own length and register rules, deferred to their
  own slices.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 44 8b 44 08 08` at six bytes | `llvm-mc -show-encoding`, `EXP-0074` §1 | high |
| `REX = 47` carries `R`, `X` and `B` at six bytes | `llvm-mc -show-encoding`, `EXP-0074` §1 | high |
| the base is one four-bit window | `llvm-mc -show-encoding`, `EXP-0074` §2 | high |
| `%r12` is an index and `%rsp` is rejected | `llvm-mc`, `EXP-0074` §3 | high |
| the `disp32` rows are nine bytes with `disp32` at `[40,32]` | `llvm-mc -show-encoding`, `EXP-0074` §4 | high |

## Review triggers

- The low-register indexed row is requested (it needs a `REX`-less variant).
- The `0x67` address-size prefix is attempted.
- The APX `d5` register window is attempted.
- A symbol or relocation in a displacement is requested.
- An EVEX/GPR masked form is attempted.
