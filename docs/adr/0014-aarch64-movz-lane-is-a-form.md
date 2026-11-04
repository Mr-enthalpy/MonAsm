# ADR-0014: AArch64 `movz` lane selection is a form, and `imm16` is field content

- Status: accepted
- Date: 2026-11-04
- Settles: `EC-30`, `A64-P7` (the scaled-immediate half of directive §6.2 item 7)
- Supersedes: none
- Superseded by: none

## Context

`A64-P7` asks for one scattered-bit-field or scaled-immediate case. The scattered
field is already carried by `adrp` (`immhi` at `[5,19]` and `immlo` at `[29,2]`,
`A64-P6`, `07_definition_format.md` §8.3), so the half still missing is a scaled
immediate. `A64-P2`
scales by a fixed `<< 12`; `movz` is the other shape: the multiplier is itself a
field, `hw` at 21+2, and it selects which 16-bit lane of the 64-bit destination the
`imm16` content lands in.

Three facts decide the shape.

1. **The MRS states four fields and no meaning.** `MOVZ_64_movewide` fixes `sf = 1`
   (bit 31), `opc = 10` (bits 30–29) and two literal runs (`100` at 26+3, `101` at
   23+3), and leaves `hw` (2 bits), `imm16` (16 bits) and `Rd` (5 bits) variable.
   `MOVK_64_movewide` and `MOVN_64_movewide` have the same layout with `opc = 11`
   and `opc = 00`. The drop omits descriptive content
   (`research/external/arm-mrs/README.md`), so the *meaning* of `hw` is not in it;
   the bits are.
2. **The assembly language spells the lane, and only four spellings exist.**
   `llvm-mc` 23.1.2 accepts `movz x0, #0x1234, lsl #0|#16|#32|#48` and rejects
   `lsl #8` with "expected 'lsl' with optional integer 0, 16, 32 or 48"
   (`EXP-0016` §2). The four rows are therefore not a taxonomy we invented; they
   are the four spellings the instruction has.
3. **The assembler does not fold a pre-scaled literal into a lane.**
   `movz x0, #0x10000` is rejected — "immediate must be an integer in range
   [0, 65535]" — so unlike `add`'s `#0x1000` (`EV-26`), there is no value-driven
   form switch to imitate here. The lane is syntax, and the immediate is the
   field.

Fact 2 is the boundary. If the table had one `movz` row whose `hw` came from an
operand, the plan would be stating an encoding field the assembly language does not
name, and two plans could reach the same bytes through spellings that do not exist.
If it had one `movz` row with `hw` pinned to `0`, the other three lanes would be
unreachable even though they are legal instructions; that is the "not implemented
versus not legal" conflation ADR-0012 rejected for `cond`.

## Decision

1. **Four forms, one per lane, in `definitions/aarch64/0.5.0.json`.**
   `aarch64:movz/x64-imm16-lsl0`, `…-lsl16`, `…-lsl32`, `…-lsl48`. The new
   document repeats the eleven `0.4.0` forms unchanged and adds these four;
   `0.1.0` … `0.4.0` stay frozen at their digests, so a plan that names a lane id
   against `0.4.0` is still `E-FORM-001`. The new digest is `sha256:9cec1688…`.
2. **The form fixes `hw` in its template.** The generator pins the MRS field
   explicitly: `hw = 0/1/2/3` becomes bit 21 and/or bit 22 of the word. `hw` is
   not an operand and not a fixup field, so no plan can disagree with the name.
3. **The slot holds `imm16` field content.** `role: imm`,
   `kind: aarch64.imm`, `target_type: imm16`,
   `{ "signed": false, "bits": 16, "align_bits": 0 }`, placement `[5,16]`. The
   value the instruction builds (`imm16 << 16*hw`) is a property of the row, as
   `add`'s `sh = 1` multiplies by 4096 and `bl`'s `imm26` counts instructions
   (`07_definition_format.md` §8.3). No slot-level scale is added.
4. **The lane is not a `modifier`.** `operands[].modifiers` is a validated guard —
   a sorted subset of the slot's permitted set, checked with `E-OPERAND-003` — and
   the materializer only reads `slot.from` (`reg_number` or `operand_value`), so a
   modifier cannot write bits. A `{"name": "lsl", "value": 16}` entry would be a
   bit-carrier spelled differently, which is the argument ADR-0012 used for `cond`.
5. **`movk`, `movn` and the 32-bit `movz` are not included.** They are the same
   shape with `opc = 11`, `opc = 00` and `sf = 0`; each gets its own `form_id`
   when a slice asks for it, never a shared row (the ADR-0011 decision 7 rule).
   Naming `aarch64:movz/w0-imm16-lsl0` or a `movk` id is `E-FORM-001`, and the
   `w` case is a measured instruction (`movz w0, #0x1234` → `0x52824680`), so the
   rejection is "absent from this table", not "illegal". The `mov` alias is left
   out for a different reason: it *does* choose the lane from the literal's value
   (`mov x0, #0x12340000` → the `hw = 1` word, `EXP-0016` §2), so a `mov` row
   would be a value-driven form selection, and `EC-16` has not decided it.
6. **The two failure directions are the existing codes.** A pre-scaled literal on
   a lane row (`0x12340000` on `-lsl16`) is `E-RANGE-001`, not a switch to
   `-lsl32` (`N18c`); a lane the ISA does not have (`-lsl8`) is `E-FORM-001`
   (`N01d`). Neither code is new.

## Consequences

- `A64-P7` passes: `A64-P7-movz-lane` is five instructions (20 B) over all four
  rows, with the same `imm16 = 0x1234` on `-lsl0` and `-lsl16` so the two words
  differ only in bits 22–21, plus `imm16 = 0xffff` in the top lane and the two
  endpoints `0` and `4660`. Its bytes match `llvm-mc` 23.1.2 (`EXP-0016` §2–§3).
- `EC-30` is registered and frozen: the counterexample is that `movz x0, #1` and
  `movz x0, #1, lsl #16` put the same field content in `imm16` and differ only in
  `hw`, so an operand value and `expected_size` cannot tell them apart.
- The AArch64 set is 8 positive and 13 negative fixtures. Nothing about the x86 or
  RV64 documents moves.
- No schema, error-code or Rust change is needed: `fmp-def/0.1` already expresses
  the rows and the fixture gate picked `0.5.0` up through `Registry::load_dir`.
- `definitions/aarch64/NOTICE` needs no change; the notice is per directory, not
  per version.

## Alternatives considered

- **One row with `hw` as an operand** (`aarch64:movz/x64-imm16-hw2`, value 0…3).
  Rejected: `hw` is the lane selector, not an assembly-language operand; the
  assembler has no spelling that states it, and the plan would carry an encoding
  field that `form_id` should own (`ADR-0004`, `INV-02`). It would also let a plan
  say `hw = 2` on an id whose name says nothing about the lane.
- **One row with `hw` pinned to 0.** Rejected: the `lsl #16/#32/#48` instructions
  exist and would become `E-FORM-001`, which reports "illegal" for "not in this
  table" (ADR-0012's objection to sixteen `b.cond` rows shipping one).
- **A slot-level `scale_bits` chosen by the operand.** Rejected: the same
  `{ "value": n }` would mean different lanes on one row, and `hw` is a field, not
  a multiplier the slot could carry; the same reasoning as ADR-0011/ADR-0013.
- **A `modifiers` entry `{"name": "lsl", "value": 16}`.** Rejected: modifiers are
  a guard, never an encoder input (`01_contract.md` §8), so the bits would still
  need a carrier and there would then be two carriers for one decision.
- **One row for the `mov` alias family (`EC-16`).** Rejected: `mov` may lower to
  `movz`, `movn`, `orr` or a register move, which is its own draft decision; this
  slice ships one member of that family and does not pretend to decide the alias.
- **Fold the pre-scaled literal into the lane** (accept `movz x0, #0x12340000`
  and pick `hw = 1`). Rejected: that is `INV-02` with the same shape as `add`'s
  `#0x1000` switch (`EV-26`), and `N18c` is its failure mode.
