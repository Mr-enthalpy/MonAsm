# ADR-0012: An AArch64 condition select is an operand, not sixteen forms

- Status: accepted
- Date: 2026-11-04
- Settles: the carrier for the condition code (`EC-29`, added here), the remainder
  of `A64-P4`
- Supersedes: none
- Superseded by: none

## Context

`A64-P4` asks for a conditional branch. `B.cond` is a 32-bit word with exactly two
variable fields. The Arm MRS node `B_only_condbranch` states them: `cond` at
`0+4` and `imm19` at `5+19`, with `op0 = 010` at `29+3`, `101` at `26+3`, `00` at
`24+2` and `o0 = 0` at `4+1` fixed. The A64 ISA page for `B.cond` (revision
`2026-03_rel`) adds the meaning: `<cond>` is one of the sixteen standard
conditions, all sixteen are encoded, and `<label>` is a PC-relative offset in
±1 MB encoded as `imm19` times 4.

So the instruction is one shape whose bytes vary in a 4-bit condition and a
19-bit displacement. The displacement is already covered by the table's existing
pattern (`bl`'s `imm26`, ADR-0011's "the slot is the field"). The condition is
new, and `02_encoding_choices.md`'s classification has two candidates for it:

- `form variant` — sixteen `form_id`s that share a template and differ in one
  nibble, the way `x86:add/rm64-imm8` and `rm64-imm32` share a mnemonic and differ
  in a field;
- `operand type` — one form and a typed 4-bit operand, the way `wreg`/`xreg`
  carries `sf` (`EC-11`).

`EC-18` does not answer this. It records a *different* variation — `b.cond` vs
`cbz`/`cbnz` vs `tbz`/`tbnz` — where the opcode and the operand set both change.
Here nothing about the shape changes.

## Decision

1. **One form, `aarch64:b.cond/imm19`, in `definitions/aarch64/0.3.0.json`.** The
   new document repeats the five `0.2.0` forms unchanged and adds this one.
   `0.1.0` and `0.2.0` stay frozen; a plan that names the new id against either is
   `E-FORM-001` (`N01`).
2. **The condition is a slot, not part of the id.** `role: imm`,
   `kind: aarch64.cond`, `target_type: cond4`, `from: operand_value`,
   `range {signed: false, bits: 4, align_bits: 0}`, placement `[0,4]`. The plan
   states `{ "value": 1 }` to mean `ne`; the table has no opinion about which
   condition a plan should want.
3. **`imm` is the role, and `aarch64.cond` is a new kind.** The role decides the
   range code (`E-RANGE-001` for `imm`, `07_definition_format.md` §4), and a
   condition outside `0..15` is exactly an immediate that does not fit its field.
   `kind` is target-namespaced and free-form in both the plan schema and the
   loader, so no schema, loader or materializer change is needed; the kind is
   documentation, not code.
4. **No `excluded` list.** All sixteen values are architecture-defined; `AL`
   (1110) and `NV` (1111) are legal and `b.al` assembles to `0x5400002e`
   (`EXP-0014` §2). Rejecting them would be a rule the source does not state, and
   it would make the form narrower than the instruction without a reason. A plan
   that wants a conditional shape with an unconditional meaning gets exactly the
   bytes it asked for.
5. **The target is field content plus a fixup.** The slot is
   `aarch64.rel`/`imm19` and holds `imm19` as planned; a byte displacement is a
   `pcrel_begin` fixup with `value_transform: scale`, `transform_shift: 2` and
   `range_constraint {signed: true, bits: 19, align_bits: 2}`, the same shape as
   `bl` (`03_fixup_model.md`). No new transform, no page trick.
6. **The two failure directions get the codes the roles already imply.** A
   condition outside `0..15` is `E-RANGE-001`; a branch beyond ±1 MB is
   `E-RANGE-002` (`N04`'s code). Neither is repaired: the cond is never masked
   and the branch is never widened to `b`/`bl`.
7. **`bl`-style block shape is not reused.** `b.cond` is 4 bytes and imm19-scaled;
   `bl` is imm26-scaled. They are separate rows, and a plan cannot reach one by
   naming the other.

## Why not sixteen forms

The classification in `02_encoding_choices.md` asks, in order, whether the
difference is implied by the form name, then by a typed operand, then whether it
is a range issue. Sixteen forms answer "yes" to the first question by
construction — but the price is that every condition becomes a table row and the
plan stops saying "branch if equal" and starts saying "use the equal form". Two
consequences make that the wrong trade:

- The table would grow with the condition alphabet, not with the instruction
  surface: `csel`, `csinc`, `ccmp`, `fcsel` and every later condition-consuming
  slice would need sixteen rows each, and a plan for an untested condition would
  be `E-FORM-001` for no architectural reason.
- The sixteen rows would be identical apart from bits 0–3, so a definition bug in
  one row would be invisible in the other fifteen while `expected_digest` kept
  passing for plans that used them.

An operand keeps one row, one template and one range check, and it makes the
plan's intent readable: `{"value": 0}` is `eq` because the field is `cond`, not
because an id spelled it.

## Consequences

- `A64-P4` becomes passing: `A64-P4-b-cond` is a three-instruction vector
  (`b.eq` +4, `b.ne` −4, `b.gt` −8) whose bytes `20000054 e1ffff54 ccffff54`
  match `llvm-mc` 23.1.2 (`EXP-0014` §3). The three conditions differ in the low
  nibble and the three displacements in bits 5–23, so one vector pins both fields
  and their independence.
- `definitions/aarch64/0.3.0.json` is a superset of `0.2.0` with six forms; the
  digest is recorded in `07_definition_format.md` §8 and in `EXP-0014` §6. The
  frozen `0.1.0` and `0.2.0` digests are asserted by the generator, so a
  perturbation fails the run instead of shipping.
- `EC-29` is a new row: the condition is a byte-affecting decision, its carrier is
  `operand type`, and the counterexample is the measured `b.eq`/`b.ne` pair, which
  differ in one nibble. `EC-18` stays `draft`: the `b.cond` half now ships, the
  `cbz`/`tbz` halves are still absent.
- Two negatives: `N03` gains a `cond = 16` case (masking it would produce `eq`,
  which is a different branch) and `N04` gains an `imm19` displacement of
  `262144` (`E-RANGE-002`).
- No schema, error-code or Rust change: `kind` is free-form, `from:
  operand_value` with a `range` already exists, and range checks are per slot.
- `0.3.0` is a new document rather than a mutation of `0.2.0`, so a plan built
  against `0.2.0` keeps its exact digest and cannot silently acquire a new form.

## Alternatives considered

- **Sixteen `form_id`s (`aarch64:b.eq/imm19`, …).** Rejected above: it replaces a
  typed operand with sixteen near-identical rows and makes the condition a
  property of the table rather than of the plan.
- **Sixteen forms, shipping only `b.eq`.** Rejected for the same reason plus an
  extra one: the v0 surface rule ("a variant that is absent cannot be selected")
  would turn an ordinary `b.ne` into a form-absence error, which conflates "not
  implemented" with "not legal".
- **A `modifier` (`{"name": "cond", "value": 1}`).** Rejected: modifiers are for
  variations the form permits on top of its shape (`lsl`, `lock`, `addr_size`);
  a modifier that *is* a 4-bit field is an operand spelled with a different key,
  and it would split the condition between two plan locations.
- **`excluded: [14, 15]` so that only "real" conditions are encodable.**
  Rejected: the ISA defines all sixteen, `b.al` is a measured legal encoding, and
  the exclusion would be a design opinion recorded as a legality rule. The table
  may not be narrower than the instruction without saying why, and there is no
  why.
- **A `cond` slot with `from: operand_value` but role `target`.** Rejected: the
  role selects the range code, and a condition is not a displacement, so
  `E-RANGE-002` would be the wrong diagnosis for `cond = 16`.
- **Reuse `bl` and treat `b.cond` as a `bl` variant with a condition operand.**
  Rejected: different field (`imm26` vs `imm19`), different opcode, different
  link semantics; one row would mean two templates under one id.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `cond` is bits 0–3 and `imm19` is bits 5–23; the other bits are fixed | Arm MRS `B_only_condbranch` encoding values, read | high |
| All sixteen conditions are defined and encoded; the label range is ±1 MB with `imm19` × 4 | Arm A64 ISA, `B.cond`, revision `2026-03_rel`, read at the public mirror; restated in `EXP-0014` §1, no passage copied | high |
| The sixteen conditions differ only in bits 0–3 | `EXP-0014` §2: sixteen assembler runs, one per condition, all accepted | high |
| `b.eq` +4 is `0x54000020`, `b.ne` +4 is `0x54000021`, `b.al` +4 is `0x5400002e` | `EXP-0014` §2, measured | high |
| The reachable byte range is −1048576…+1048572; ±1048576 is rejected | `EXP-0014` §3, measured at both ends | high |
| The three-instruction vector is `20000054 e1ffff54 ccffff54` | `EXP-0014` §3, `llvm-mc` + `llvm-objcopy`, no relocations emitted | high |
| `cond = 16` masked to 4 bits becomes `eq` | arithmetic (`16 & 0xF = 0`, and `cond = 0` is `EQ`); not measured because no assembler spells it | inference |

## Review triggers

- A slice needs `cbz`/`cbnz`/`tbz`/`tbnz`. Those are `EC-18` variants: different
  opcodes and different operand sets, so they are new rows, not this row with an
  operand.
- A slice needs `csel`/`csinc`/`ccmp`. They carry the same `aarch64.cond` kind; if
  the kind's domain or spelling has to change, that is a new ADR superseding this
  one, not a widening here.
- A plan must be rejected for naming `AL`/`NV`. That needs a stated reason and an
  `excluded` list (ADR-0009), which reverses decision 4.
- AArch64 gains a branch whose displacement is not `imm19`-scaled. It gets its
  own row with its own `range_constraint`; the target slot is field content, so a
  shared row would be two templates.
