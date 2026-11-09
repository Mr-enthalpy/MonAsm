# ADR-0121: a fixup writes one `operand_value` slot, in that slot's order

- Status: accepted
- Date: 2026-11-10
- Settles: which bits a `field_descriptor` may name, and in which order
- Supersedes: none
- Superseded by: none
- Revises: `03_fixup_model.md` §3 (the descriptor and one-writer rules) and §10;
  `01_contract.md` §10 and §13 step 7; the `E-FIXUP-001`/`E-FIXUP-005`/
  `E-FIXUP-006` rows of `04_errors.md` §2 and their counterexamples; the `N07`
  row of `06_validation_matrix.md`; adds `N07g` and `N07h` and updates the
  expected set of `N07`

## Context

`fmp/0.1` states a fixup as a site plus a `field_descriptor`, and the
materializer's `write_descriptor` places the value into exactly those bits. Three
rules that looked like one-writer checks were never implemented:

1. **The descriptor may only cover an `operand_value` slot.** Nothing stopped a
   descriptor from covering a `reg_number` slot. The encoder writes the register
   from the operand, the fixup writes the same bits afterwards, and the plan is
   accepted with one of its two statements silently discarded. This is the
   `INV-07` failure one layer below the operand checks: `N07c` catches a *value*
   operand plus a fixup, but a *register* operand plus a fixup went through.
2. **A descriptor range must sit inside one placement of that slot.** A range
   that straddles a placement boundary would write bits the slot does not own,
   which for x86 means opcode or `ModRM` bits.
3. **The descriptor order must match the slot's placement order.** The list is
   the value order (`03_fixup_model.md` §3). A descriptor that names the same
   bits in a different order emits a *different value* for the same operand, and
   the plan is accepted.

None of the three is expressible as the existing per-bit template check
(`E-FIXUP-006` on a non-zero template bit), because the form's template leaves
every variable bit at zero: the overwritten bits are not template content, they
are operand content.

The audit of `47a383b` reproduced all three on locally built plans before this
decision was written. The measured surface is small enough to state exactly:

- 75 fixups across the 128 positive plans. Every one covers exactly one
  `operand_value` slot, its bits are a subset of that slot's placements, and its
  descriptor order equals the slot's placement order — 75/75, no exception.
  The rule therefore rejects nothing that ships.
- Of the 605 `materialize`-phase negatives in the pre-change corpus (611
  negatives in all, 6 of them `read`-phase), three plans name a descriptor that is
  not the slot's own bit set: `N07` (a `reg_number` slot), `N07d` (a partial
  `disp` window) and `N07e` (a window past the form). Only `N07` gains a
  diagnostic; the other two are already rejected by `check_operand` and by
  `E-FIXUP-005`.
- No `operand_value` placement in any shipped definition sets `invert`; the
  12,288 inverted placements are all `reg_number` (the VEX/EVEX extension bits).
  The polarity rule is decided per placement, so a fixup that would have to
  honour an inverted placement is a two-writer case, not a field patch.

## Decision

1. **Ownership.** A fixup's covered bits must belong to exactly one slot and
   that slot must be `from: operand_value`. If a covered bit belongs to a
   `reg_number` slot, or to a slot with an inverted placement, the fixup shares
   the bits with the operand path: `E-FIXUP-006` at `/fixups/<i>` with
   `first = operand`, `second = <fixup_id>`. If the covered bits belong to zero
   slots, or to more than one, the descriptor does not name a field:
   `E-FIXUP-001` at `/fixups/<i>/field_descriptor` with
   `field = descriptor does not cover exactly one operand_value slot`.
2. **Containment and order.** Within that slot, every descriptor range must be
   contained in one placement, and the placements must appear in the slot's
   declared order. A range that crosses a placement boundary is
   `E-FIXUP-001` with `field = descriptor range is not contained in one placement
   of the slot`; a correct set of ranges in the wrong order is `E-FIXUP-001` with
   `field = descriptor order does not match the slot's placement order`.
3. **The check does not double-report.** A descriptor that leaves the form
   (`E-FIXUP-005`) already names the same bytes; the ownership check skips it
   rather than adding a second diagnostic. A descriptor that covers only part of
   the slot stays with `check_operand` (`E-FIXUP-001` at the operand path), which
   is where "this operand is only half written" belongs.
4. **The template check reports once per fixup.** A fixup that overlaps a
   non-zero template bit reports `E-FIXUP-006` once, not once per set bit. The
   fault is "this fixup writes over a template value"; the number of set bits is
   an artefact of the field's width and made the diagnostic set depend on the
   encoding of the instruction.
5. **The form, not `expected_size`, is the bit authority.** The bounds check now
   uses `form.size() * 8`. `expected_size` is compared with `form.size()`
   statically (`ADR-0122`), so the two agree whenever the fixup checks run.

## Consequences

- A plan can no longer name a fixup for a register field or for opcode bits. The
  only writable field is the one the value operand would have written, which is
  what "the fixup supplies the operand's value" means.
- `N07` now yields two diagnostics: `E-FIXUP-006` at `/fixups/0` and the
  existing `E-FIXUP-001` at `/instructions/0/operands/0`. The fixture records
  both; suppressing either would hide a distinct fault.
- `N07g` (RV64 `beq`, descriptor reversed) and `N07h` (AArch64 `b.cond`,
  descriptor spanning the `imm` and `target` slots) are the fixtures for rules 1
  and 3. Both are accepted-and-emitted plans before this ADR.
- Definition authors get a constraint they can check locally: every
  `operand_value` slot's placements are the only writable windows of that form,
  and their list order is the value order.
- A future slice that wants an inverted `operand_value` placement (for example a
  pre-inverted displacement) must define how a fixup supplies the polarity. That
  is a new decision, not a relaxation of this one.

## Alternatives rejected

- **Widen `E-FIXUP-006` to cover "fixup on any non-template bit".** Rejected:
  the code would then also report fields that no operand writes, and the reader
  could not tell "two writers" from "no writer". The two faults have different
  repairs.
- **Reject by comparing the descriptor with the slot's placement list for
  equality.** Rejected: it would forbid a legitimate subrange (`N07d`'s shape,
  which `check_operand` already rejects as a partial write) and it would make
  the diagnostic depend on list identity rather than on the bits covered. Bits
  are the contract; the list is a spelling.
- **Fold the order rule into `E-FIXUP-005` (bounds).** Rejected: the bits are in
  bounds and inside the slot; the fault is the mapping from value bits to
  placement bits, which is `E-FIXUP-001`'s subject.
- **Check ownership at emission.** Rejected: emission runs only after steps 1–7
  are clean, and a rule enforced only at emission cannot explain itself through
  the static diagnostic set (`01_contract.md` §13).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| 75/75 positive fixups cover exactly one non-inverted `operand_value` slot, in order | scan over `fixtures/*/positive/*.fmp.json` against the definition named by each plan | high |
| No shipped `operand_value` placement uses `invert`; all 12,288 inverted placements are `reg_number` | scan over `definitions/*/*.json` | high |
| `N07d`/`N07e` stay at their recorded diagnostics | `cargo test -p fmp-cli --test fixtures` after the change | high |
| `N07` is the only existing negative that gains a diagnostic | the same scan over the materialize-phase negatives | high |
| `N07g` and `N07h` were accepted and emitted before the change | `fmp materialize` built from `47a383b` in a clean worktree: `N07g` emitted `63 00 b5 00`, `N07h` emitted `00 00 00 54`, both with exit code 0 | high |
| The ownership rule rejects nothing that ships | 75/75 scan plus a green `cargo test --workspace` | high |

## Review triggers

- A definition gains an `operand_value` slot with `invert: true`, or a
  multi-placement `operand_value` slot whose order is not the value order.
- A new fixup kind needs to write a field that no operand writes. That is a new
  slot role and needs its own ADR.
- A positive vector is proposed whose descriptor is a strict subrange of its
  slot; this ADR keeps that case with `check_operand`, so the rule must be
  restated rather than silently loosened.
