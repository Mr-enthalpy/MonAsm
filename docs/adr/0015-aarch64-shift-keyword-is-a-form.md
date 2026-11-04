# ADR-0015: AArch64 shift keywords are forms and the amount is field content

- Status: accepted
- Date: 2026-11-04
- Settles: `EC-31`, `A64-P8` (directive §6.2 item 8), the shifted-register half of
  `EC-13`
- Supersedes: none
- Superseded by: none

## Context

`A64-P8` asks for one target-specific modifier case. The one the assembly language
offers on a register operand is the shift:
`add x0, x1, x2, lsl #3` (`ADD (shifted register)`, `ADD_64_addsub_shift`). It is
spelled as a modifier — a keyword and a number — so it is exactly where a plan
carrying "a modifier" would first be tempted to let the modifier write bits.

The MRS node leaves three fields variable: `shift` at 22+2, `imm6` at 10+6, and the
three registers (`Rm` 16+5, `Rn` 5+5, `Rd` 0+5); bit 21 is fixed to `0` and the
opcode bits are fixed, which is what separates this node from the extended-register
one (`EXP-0017` §1).

Three facts decide the shape.

1. **The keyword is the only spelling of the kind.** `llvm-mc` 23.1.2 accepts
   `lsl #n`, `lsr #n`, `asr #n` and nothing else in that position:
   `add x0, x1, x2, ror #3` is rejected, and so is `add x0, x1, x2, lsl #64`
   (`EXP-0017` §2). `add`/`sub` have no fourth value for `shift`: `11` is
   unallocated in this node. There is no numeric way to state the kind.
2. **The number is a field, and it is the whole field.** `lsl #3` writes `3` into
   `imm6`; the amount is `0…63` for the 64-bit width, and both ends were measured
   (`lsl #0` → `0x8b020020`, `lsl #63` → `0x8b02fc20`). The word is
   `shift` in bits 23–22 and `imm6` in bits 15–10, so an amount and a kind are two
   independent readings of the same instruction, not one of them derived from the
   other.
3. **A `modifiers` entry cannot write those bits.** `01_contract.md` §8 makes
   `operands[].modifiers` a guard: the definition permits a closed set of
   `{name, value}` pairs and the materializer reads only `slot.from`
   (`reg_number` or `operand_value`). Measured: the `-lsl0` row with
   `{"name": "lsl", "value": 3}` on `src2` is `E-OPERAND-003` (`N19`). If it were
   silently accepted, the plan would emit `0x8b020020` — a legal `add` with a
   different result — which is the "the value was ignored" failure `INV-07`
   forbids.

Fact 1 and fact 2 are the whole decision. The keyword picks a form (three rows,
like `movz`'s four lanes in ADR-0014); the number is an operand (like `imm16`
there, and like `imm19`/`cond` in ADR-0012).

## Decision

1. **Three forms in `definitions/aarch64/0.6.0.json`**:
   `aarch64:add/x64-x64-x64-imm6-lsl`, `…-imm6-lsr`, `…-imm6-asr`. `0.6.0` repeats
   the fifteen `0.5.0` forms unchanged and adds these three; `0.1.0` … `0.5.0`
   stay frozen at their digests, so naming a shift id against `0.5.0` is still
   `E-FORM-001`. The new digest is `sha256:1151944e…`.
2. **The form pins `shift`.** `lsl` = `0`, `lsr` = `1`, `asr` = `2`. The value is
   the form's, not the plan's: no plan field names it, so two plans cannot disagree
   about it.
3. **The amount is one slot.** `role: imm`, `kind: aarch64.imm`,
   `target_type: imm6`, `{ "signed": false, "bits": 6, "align_bits": 0 }`,
   placement `[10,6]`. It is field content, so the slot holds `0…63` and no
   scaling: the slot is the field (`07_definition_format.md` §8.3).
4. **The keyword is not a `modifier` entry.** A modifier is a guard in v0
   (`01_contract.md` §8); it may carry a variation the definition permits and it
   may not write a bit. Stating `lsl` twice — once in `form_id`, once in
   `modifiers` — would be two carriers for one decision, and stating it only in
   `modifiers` would leave the bits without a carrier. `N19` is the rejection.
5. **`imm6 = 0` on `-imm6-lsl` is the same word as `-lsl0`** (`0x8b020020`). Both
   remain. `-lsl0` was frozen in `0.1.0` as the row for a plan that states no
   shift, and the assembly language itself treats the two spellings as one
   instruction: `llvm-mc -show-encoding` prints `add x0, x1, x2, lsl #0` back as
   `add x0, x1, x2`. Excluding `0` from `-imm6-lsl` instead would make the
   operand's *value* decide the form, which is the selection `INV-02` forbids
   (`N18`); a form selection is a planner's decision, not a materializer rule,
   and the table must not encode one.
6. **`sub`, the 32-bit rows and the extend family are not included.** `sub` is
   another node; the `w` rows are the `sf = 0` variants (`EC-11`); the extend
   family is `ADD_64_addsub_ext` with `option` (3 bits) and `imm3` (3 bits), whose
   source operand may be a `w` register (`add x0, x1, w2, uxtw #3` →
   `0x8b224c20`). That is a different node with a different operand-width rule,
   so it gets its own ADR (`EC-13`'s extended half stays uncovered until then);
   naming `aarch64:add/x64-x64-w64-uxtw-imm3` is `E-FORM-001` (`N01e`).
7. **The two failure directions use existing codes.** An amount outside the field
   (`64`) is `E-RANGE-001` (`N03`); a modifier that tries to carry the shift is
   `E-OPERAND-003` (`N19`). No code is new.

## Consequences

- `A64-P8` passes: `A64-P8-shift-modifier` is six instructions (24 B) over the
  three rows — `lsl #3`, `lsr #7`, `asr #63`, `lsl #63` on a second register
  triple, `lsl #0` and `lsr #0` — and its bytes match `llvm-mc` 23.1.2
  (`EXP-0017` §2–§3).
- `EC-31` is registered and frozen: the counterexample is `add x0, x1, x2, lsl #3`
  vs `add x0, x1, x2, lsr #3`, which share every operand and every register field
  and differ only in `shift` and `imm6`, so no operand value or `expected_size`
  separates them.
- The AArch64 set is 9 positive and 16 negative fixtures; `0.6.0` is the fourth
  document whose only new rows are the ones its version introduced, and the
  generator's frozen-digest assertions prove no earlier row moved.
- No schema, error-code or Rust change is needed: the rows use the existing
  `fmp-def/0.1` fields, and the fixture gate picked `0.6.0` up through
  `Registry::load_dir`.
- `EC-08`, `EC-10` and `EC-26` name `operand modifier` as the carrier for
  `addr_size`, `lock`/`rep` and `aq`/`rl`. They stay `draft`, and this ADR does
  not settle them: a modifier that carries a *bit-affecting value* would need its
  own decision (a form that names the variation, like this one, or a new `from`
  member that lets a modifier fill a slot). v0 has neither.

## Alternatives considered

- **A modifier that writes the bits** (`{"name": "lsl", "value": 3}` on `src2`,
  with a slot `from: "modifier_value"`). Rejected: `01_contract.md` §8 says a
  modifier is a guard, and adding a `from` member would make a modifier a second
  carrier for one number while the definition format keeps `from` a closed
  two-member set (`07_definition_format.md` §4). It is also the only feature in
  this slice that would need a Rust change, for a decision an operand already
  expresses.
- **One row with the kind as a numeric operand** (`shift2` operand, `0…2`,
  excluding `3`). Rejected: the assembly language has no numeric spelling for the
  kind, `shift = 11` is unallocated in this node, and the plan would be stating an
  encoding field the ISA does not name — ADR-0014's argument against a `hw`
  operand, one field over.
- **One row per amount** (64 rows × 3 kinds). Rejected: the amount is field
  content, not a decision; 192 rows of near-identical templates would bury the
  one bit pattern that matters.
- **Exclude `0` from `-imm6-lsl`** so that each word has exactly one row. Rejected:
  it makes the operand's value choose the form (`INV-02`, `N18`), and it would
  give the three kinds inconsistent ranges (`-imm6-lsr`/`-imm6-asr` need `0`).
- **Carry the amount as `disp` or `target`** so that a range code comes for free.
  Rejected: the amount shifts a register value; it is neither an address
  displacement nor a branch target, and `07_definition_format.md` §4 fixes the
  code by `role` (`E-RANGE-001` for `imm`, `E-RANGE-002` for `target`).
- **Include the extend family in this slice** (8 `option` values, `imm3`).
  Deferred, not refused: it is a different node, its `lsl`-less spelling is a
  different keyword set, and its source operand width is a separate decision.
