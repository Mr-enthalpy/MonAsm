# ADR-0016: an AArch64 extend keyword is a form, and the amount is field content with an excluded tail

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P9` (widening), `EC-32`, the extended-register half of `EC-13`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0015` closed the *shifted*-register node (`ADD_64_addsub_shift`). The same
mnemonic, `add x0, x1, w2, uxtw #3`, also names the *extended*-register node
(`ADD_64_addsub_ext`). The two nodes are one bit apart: `ADD_64_addsub_ext` fixes
`opt` at 22+2 to `00` and bit 21 to `1`, while `ADD_64_addsub_shift` leaves
`shift` variable at 22+2 and fixes bit 21 to `0` (`EXP-0018` §1). The extended
node leaves exactly three things variable: `option` at 13+3, `imm3` at 10+3, and
the three register fields.

Three measured facts decide the shape.

1. **The keyword set is closed, split by source width, and not numeric.** For a
   `w` source the assembler accepts `uxtb`, `uxth`, `uxtw`, `sxtb`, `sxth`,
   `sxtw` and nothing else; for an `x` source it accepts `uxtx` and `sxtx`.
   `add x0, x1, x2, uxtb #3` and `add x0, x1, w2, uxtx #3` are both rejected
   (`EXP-0018` §2). So the keyword determines both the 3-bit `option` value and
   the width of the register it consumes.
2. **The amount is the whole 3-bit field, and only five of its eight values
   exist.** `imm3` is the shift amount `0…4`; `#5` is rejected (`EXP-0018` §2).
   That is not a signed range: the field is three bits and values `101`, `110`,
   `111` are unallocated for add/sub extended. The field is therefore
   `bits: 3` (so `8` is outside the field) plus a closed `excluded` list
   `[5, 6, 7]` (`ADR-0009`).
3. **A modifier entry cannot write those bits.** As in `ADR-0015`, a
   `modifiers` entry is a guard (`01_contract.md` §8): it can permit a variation
   but it never fills a slot. The `option` value and the amount are both
   bit-affecting, so neither may be carried there.

Fact 1 is also why the register width cannot be a plan field. An `uxtx` on a `w`
register would need `option = 3` and a 32-bit class, and the two are the same
5-bit number in the encoding: if the class were not fixed by the row, that plan
would emit the `uxtx` word and report success, which is `INV-07`'s silent repair.
The class is part of the form, like the `w`/`x` split `EC-11` already describes.

## Decision

1. **Eight forms in `definitions/aarch64/0.7.0.json`**: one per `option` value.
   - `aarch64:add/x64-x64-w32-imm3-uxtb` … `-sxtw` (options `0`, `1`, `2`, `4`,
     `5`, `6`), `src2` is a `w` register;
   - `aarch64:add/x64-x64-x64-imm3-uxtx`, `…-sxtx` (options `3`, `7`), `src2` is
     an `x` register.

   `0.7.0` repeats the eighteen `0.6.0` forms unchanged and adds these eight;
   `0.1.0` … `0.6.0` stay frozen at their digests, so naming an extend id
   against `0.6.0` is still `E-FORM-001`. The new digest is
   `sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053`.
2. **The form pins `option`.** `uxtb` = `0`, `uxth` = `1`, `uxtw` = `2`,
   `uxtx` = `3`, `sxtb` = `4`, `sxth` = `5`, `sxtw` = `6`, `sxtx` = `7`. No plan
   field names it.
3. **The amount is one slot with a tail.** `role: imm`, `kind: aarch64.imm`,
   `target_type: imm3`, `{ "signed": false, "bits": 3, "align_bits": 0 }`,
   placement `[10,3]`, and `excluded: [5, 6, 7]`. `imm3 = 8` is `E-RANGE-001`
   (`N03-imm3`); `imm3 = 5` is `E-RANGE-004` (`N16c`), because the field fits it
   and the instruction does not define it. The excluded list is a lookup, not a
   predicate, exactly as `ADR-0009` requires.
4. **The width is the form's, not the plan's.** The six `w`-source rows carry
   `kind: aarch64.gpr32` / `target_type: w32` on `src2`; the two `x`-source rows
   carry `aarch64.gpr64` / `x64`. Stating a `w` operand on `-imm3-uxtx` is
   `E-OPERAND-001` (`N02b`) — a rejection, not a reinterpretation, because the
   field cannot record the difference.
5. **`imm3 = 0` stays legal.** The assembler prints `uxtb #0` back as `uxtb`
   (`EXP-0018` §2), so "amount 0" is a legal spelling of the same word; excluding
   it would make the operand's value choose the form, the `INV-02` failure
   `ADR-0015` decision 5 rejected for `imm6`.
6. **The `lsl` spelling is not in this node.** `lsl` names the shifted-register
   rows (`ADR-0015`); the assembler rejects `lsl` on a `w` source, and `uxtx` /
   `sxtx` are the extended spellings for an `x` source. An `x` source with `lsl`
   is `aarch64:add/x64-x64-x64-imm6-lsl`; an `x` source with `uxtx` is this
   slice's `-imm3-uxtx`. They differ in bit 21 and in `option`, so the planner
   naming a form is the only way to pick.
   The `-imm3-uxtx`/`-imm3-sxtx` rows are *not* redundant with `-lsl0`: `uxtx #0`
   is semantically an identity extend, but it is a different word (`0x8b226020`
   vs `0x8b020020`), and the table records bytes, not semantics.
7. **`sub`, `adds`/`subs` and the 32-bit node are out.** `SUB_64_addsub_ext` is
   the same layout with `op = 1`; `S = 1` is the flag-setting variant; the
   `sf = 0` node is `ADD_32_addsub_ext`. Naming
   `aarch64:sub/x64-x64-w32-imm3-uxtb` is `E-FORM-001` (`N01f`).
8. **No new error code.** `E-RANGE-001`, `E-RANGE-004`, `E-OPERAND-001` and
   `E-FORM-001` all already exist and each already has a fixture of another
   shape.

## Consequences

- `A64-P9` passes: `A64-P9-extend-modifier` is eight instructions (32 B), one per
  `option`, with all three registers distinct in every row so each field moves
  independently, and with `imm3` at both ends (`0` and `4`) on both register
  classes. Its bytes match `llvm-mc` 23.1.2 (`EXP-0018` §3).
- `EC-32` is registered and frozen. The counterexample is `uxtb` vs `uxth` on the
  same registers: both are 4 bytes and differ only in bits 15–13, so no operand
  ordering or `expected_size` separates them. The second counterexample is the
  register class: the bytes for `option = 3` are the same whether the plan calls
  the source `w` or `x`, so the class must be the form's.
- The AArch64 set is 10 positive and 20 negative fixtures; `0.7.0` is the third
  document whose only new rows are the ones its version introduced.
- No schema, error-code or Rust change is needed: `aarch64.gpr32` is a new kind
  string of the target-namespaced form the schema already allows, and the slot's
  `excluded` list is `fmp-def/0.1` (`ADR-0009`).

## Alternatives considered

- **One row with a numeric `option` operand** (`0…7`). Rejected: the assembly
  language has no numeric spelling for the keyword, and the operand would have to
  be paired with a register-class rule that no slot can state — an `option = 3`
  plan carrying a `w` operand would emit a legal word.
- **Sixteen rows** (eight options × two classes). Rejected: six of the eight
  keywords have exactly one legal class, so the extra eight rows would be forms
  the assembler rejects; the table would carry a choice that does not exist.
- **`imm3` as a full `0…7` range** with the rejected values left to the encoder.
  Rejected: `5`, `6`, `7` have no encoding, and accepting one would emit a word
  that is not the instruction the plan named — `E-RANGE-004` is the lookup that
  says so.
- **Include `sub`/`adds`/`subs`/the 32-bit node in the same slice.** Deferred,
  not refused: they are other nodes with their own `op`/`S`/`sf` pins, and each
  deserves its own counterexample.
- **A `modifiers` entry for the keyword** (`{"name": "uxtw", "value": 3}`).
  Rejected for the reason `N19` records: a modifier is a guard, and the option
  bits would have no writer.
