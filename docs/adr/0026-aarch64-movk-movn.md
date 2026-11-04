# ADR-0026: the move-wide family gains `movk` and `movn`; the lane stays a form

- Status: accepted
- Date: 2026-11-05
- Settles: `A64-P19` (the two move-wide mnemonics `ADR-0014` left out)
- Supersedes: none
- Superseded by: none

## Context

`ADR-0014` added the four `movz` rows and left `movk`, `movn` and the `mov` alias
out with reasons. The first two are now measurable on exactly the node shape the
`movz` rows already use.

`MOVK_64_movewide` and `MOVN_64_movewide` are `MOVZ_64_movewide` with the two-bit
`opc` at 29+2 fixed differently: `10` is `movz`, `11` is `movk`, `00` is `movn`.
`sf` is `1`, `hw` is at 21+2, `imm16` at 5+16 and `Rd` at 0+5 on all three, so the
rows differ only in the bits the node already fixes. Measurements (`llvm-mc`
23.1.2, `EXP-0028`):

1. **`movk` writes the given lane.** `movk x0, #0x1234` is `0xf2824680` and the
   four lane spellings add `0x00200000` each (`lsl #16` → `0xf2a24680`,
   `lsl #32` → `0xf2c24680`, `lsl #48` → `0xf2e24680`), so `hw` is the lane and
   the operand is field content, exactly as on `movz`.
2. **`movn` is the same encoding with `opc = 00`.** `movn x0, #0x1234` is
   `0x92824680`, the `movz` word with the `opc` bits changed; the lane ladder is
   the same (`0x92a24680`, `0x92c24680`, `0x92e24680`). The operand is still the
   raw `imm16` field: the complement is the instruction's operation, not
   something the plan computes, so `imm16 = 0x1234` is what the row stores.
3. **Only `#0`, `#16`, `#32` and `#48` are lanes, and `imm16` stops at 65535.**
   `lsl #8` and `lsl #4` are `expected 'lsl' with optional integer 0, 16, 32 or
   48`; `#0x10000` and `#-1` are `immediate must be an integer in range
   [0, 65535]`. There is no pre-scaling path.
4. **`x31` is a legal destination.** `movk xzr, #0` is `0xf280001f` and
   `movn xzr, #0xffff` is `0x929fffff`, so `Rd` stays a plain `reg_number`; the
   meaning of 31 comes from the node's role, as on every other row.
5. **There is no `mov` row in the drop's encode nodes.** The `mov` mnemonic
   accepts a literal and picks the operation and lane from its value:
   `mov x0, #0x1234` is the `movz` word `0xd2824680` and `mov x0, #-1` is the
   `movn` word `0x92800000`. Since the choice tracks the operand's value, a
   `mov` row would make the materializer choose a form (`INV-02`), so it stays
   out.

## Decision

1. **Eight rows are added in `definitions/aarch64/0.17.0.json`**, four per
   mnemonic: `aarch64:movk/x64-imm16-lsl{0,16,32,48}` and the same four
   `aarch64:movn/…` rows. Each pins `hw` and reads `MOVK_64_movewide` or
   `MOVN_64_movewide`, whose `opc` fixes the operation.
2. **The lane is a form and `imm16` is field content.** The reasoning is
   `ADR-0014`'s: the lane changes bits the assembler spells with `lsl #16/#32/
   #48`, while `imm16` is one contiguous field the plan states directly. The
   suffix names the lane and never rescales the operand.
3. **The mnemonic is the form family, not an operand.** `opc` is fixed by the
   node (`10`/`11`/`00`), so no plan field names it; `movk`/`movn` are siblings
   of `movz` in the same way `sub` is a sibling of `add` (`ADR-0017`).
4. **The `mov` alias stays out.** It is a value-driven lowering of `movz`/
   `movn` (decision 5 of the context), which is the selection `INV-02` forbids.
   A plan that wants the bytes names `movz` or `movn` itself.
5. **The 32-bit `sf = 0` lanes stay out.** `movk w0, #0x1234, lsl #16` is
   `0x72a24680` and `movn w0, …` is `0x12a24680`, so the width is once more the
   node's and deserves its own measured row set (`ADR-0019`'s pattern), exactly
   as the `w` register offset did.
6. **No schema change and no Rust change.** The rows use the same `dest`
   (`aarch64.gpr64`/`x64`) and `imm` (`aarch64.imm`/`imm16`,
   `signed: false`, `bits: 16`) slots as the `movz` rows, and they add no role.

## Consequences

- `A64-P19` passes: `A64-P19-movwide` is twelve instructions over the eight new
  rows plus four boundary rows (`x31` as destination, `#0`, `#0xffff` at
  `lsl #48`, `#0` on `movn` at `lsl #48`), 48 bytes, and matches `llvm-mc`
  23.1.2 with no relocations (`EXP-0028` §4).
- The AArch64 table is 176 forms across seventeen documents, now from
  thirty-nine encode nodes plus the ten alias verification nodes.
- The AArch64 fixtures become twenty positive and fifty-seven negative.
- The move-wide family now has twelve 64-bit rows. What remains of it is the
  `sf = 0` half, which is a separate row set.

## Alternatives considered

- **One `movk` row per mnemonic with `hw` as an operand.** Rejected for the same
  reason as `ADR-0014`: `hw` decides bits 22–21, and an operand would let a plan
  write them; the four spellings would also collapse into one form whose meaning
  depends on a value.
- **A `mov` alias row.** Rejected: the alias chooses `movz`/`movn` and the lane
  from the literal, which is the value-driven selection `INV-02` forbids. If a
  planner ever needs it, it must make that choice and emit the concrete row.
- **Add the 32-bit lanes in the same slice.** Deferred, not refused: `sf = 0`
  changes bit 31 and the `imm16` field is `W`-width, which is the same
  width-versus-node decision `ADR-0019` made for the arithmetic rows.
- **Add `movk`/`movn` with an `excluded` list to reject 0.** Rejected: `#0` is a
  legal and useful `movk`/`movn` operand (`movk xzr, #0` = `0xf280001f`), so there
  is nothing to exclude.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The three nodes differ only in the two `opc` bits | MRS node dump, `EXP-0028` §1 | high |
| `hw` is the lane and `imm16` is field content in `0…65535` | the lane ladder and the boundary words, `EXP-0028` §2 | high |
| Only `lsl #0/#16/#32/#48` are accepted | two lane rejections, `EXP-0028` §3 | high |
| `movn` stores the raw `imm16`, not the complement | node fields plus measured words, `EXP-0028` §2 | high |
| `x31` is a plain register in `Rd` | `movk xzr, #0` and `movn xzr, #0xffff`, `EXP-0028` §2 | high |
| The `mov` alias is value-driven | `mov x0, #0x1234` → `0xd2824680`, `mov x0, #-1` → `0x92800000`, `EXP-0028` §2 | high |
| The twelve-instruction vector is 48 bytes | `EXP-0028` §4, `llvm-mc` + `llvm-objcopy`, no relocations | high |
| `-lsl8` is `E-FORM-001`, not a range error | no such row exists; our contract decision | high (mechanism), **our decision** |

## Review triggers

- The 32-bit `sf = 0` move-wide lanes land. `opc` keeps its meaning but the
  destination width changes to `w32`.
- A plan needs a `mov` alias. That would require an explicit planner-side
  lowering table and a new decision about who chooses the lane.
- `movz`/`movk`/`movn` gain a `b`/`h`/`s` variant or a non-`movewide` operation.
  Each is a different node and a different row set.
