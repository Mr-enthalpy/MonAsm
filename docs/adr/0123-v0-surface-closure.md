# ADR-0123: `section_relative` is rejected, and a symbol must sit inside its section

- Status: accepted
- Date: 2026-11-10
- Settles: the two remaining `fmp/0.1` surface holes the audit found
- Supersedes: none
- Superseded by: none
- Revises: `03_fixup_model.md` §2.1 and §10; `01_contract.md` §9 and §10;
  `04_errors.md` §2 (`E-SYMBOL-003`, `E-FIXUP-002`) and their counterexamples;
  `06_validation_matrix.md` (`N08`, `N24`); adds `N24j` and `N24k`

## Context

Two plan statements were accepted without a rule behind them.

1. **`target.kind: section_relative` had an implementation and no measurement.**
   `03_fixup_model.md` §2.1 marks the kind `inference`/`unverified`: it says the
   value is "the named section's base address, plus the addend", and no fixture,
   oracle run or slice uses it. The materializer nevertheless resolved it: for
   `resolve_in_place` it looked up `sections[].base_address` and emitted `base +
   addend`, refusing `E-FIXUP-002` when the section had no base. That is a
   second, unmeasured semantics living in the emitter — the plan states a kind
   whose meaning the contract does not fix, and the bytes depend on it.
2. **A defined symbol's offset was not bounded.** `E-SYMBOL-003` required only
   that `section_id` name a section. `{ "section_id": ".text", "offset": 4096 }`
   in a 5-byte section was accepted and resolved to an address far outside the
   section. With `section_relative` closed, `symbol` is the *only* way to name an
   address inside a section, so its bound is the only bound left; leaving it open
   means the format has no way to state an in-section address that is guaranteed
   to exist.

Both are format-surface decisions rather than encoding facts, which is why this
is one ADR: they close the same hole from two sides.

## Decision

1. **`section_relative` is refused in `fmp/0.1`.** A plan that names it is
   `E-VERSION-001` at `/fixups/<i>/target/kind` with
   `feature = target.kind:section_relative` and `format_version = fmp/0.1`, in
   both resolution modes. The schema keeps the kind — the plan grammar can name
   it — but the materializer cannot honour it.
2. **The validator no longer looks up a base address for it,** and `source()`
   treats the arm as an internal invariant (`E-INTERNAL-001`), because a plan
   that reached emission with this kind would mean the validator did not run.
3. **A defined symbol's offset must be `<= section.declared_size`.** Equality is
   legal: it is the one-past-the-end label two positive vectors already use
   (`A64-P6` `S1` at 4104 in a 4104-byte `.text`, `RV-P8` `S1` at 4096 in a
   4096-byte `.text`). A larger offset, a missing `offset`, or a `section_id`
   that names no section is `E-SYMBOL-003` at `/symbols/<i>` with `symbol_id`.
4. **The plan must use `symbol` for an in-section address.** `absolute` carries
   an address with no section and no offset; `section_relative` is refused. If a
   later slice needs a section base address, it measures the semantics first and
   supersedes this ADR.

## Consequences

- The emitter loses a code path. `FixupTarget::SectionRelative` is now
  unreachable from a validated plan, so no plan can obtain bytes from an
  unmeasured rule.
- `N24j` is the `section_relative` fixture and `N24k` the out-of-range symbol
  fixture. Both are otherwise valid plans with one fault.
- `N24f` (a defined symbol whose section does not exist) keeps its diagnostic;
  the bound adds a second way to reach the same code, not a new code.
- The planner boundary agrees with the contract: `fmp-plan` already reports
  `section_relative` as unrepresentable (`09_planner_api.md` §6). The parity test
  now checks that the builder's refusal pointer is the pointer the materializer
  rejects, instead of silently skipping the fixture.
- `E-FIXUP-002` keeps its `base_address` trigger for `symbol` and `absolute`
  targets (§2 of the registry); only the `section_relative` clause is removed.

## Alternatives rejected

- **Keep `section_relative` and add a fixture.** Rejected: a fixture would pin
  the *materializer's* guess, not the format's meaning. The contract has no
  measured counterexample for "a section's address" as a fixup target, and the
  five `OD-02` cases do not need it. Adding coverage before the contract is the
  one thing `AGENTS.md` forbids.
- **Mark it deprecated but keep resolving it.** Rejected: a deprecated feature
  that still emits bytes is a feature. Acceptance would still depend on it.
- **Reject `section_relative` only in `resolve_in_place`.** Rejected: an
  `emit_relocation` record would carry a target the format cannot define; the
  record shape names a symbol or an absolute address, not a section.
- **Allow `offset` up to `u64::MAX` and let the fixup range check catch it.**
  Rejected: a symbol at 4096 in a 5-byte section is not a range failure, it is a
  location that does not exist. The range check has no frame to compare against.
- **Require `offset < declared_size`.** Rejected: it would reject the
  one-past-the-end label, which two shipped positives use and which a linker
  needs for "end of this section".

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| No v0 fixture uses `section_relative` | scan over `fixtures/**/*.fmp.json` for `"kind": "section_relative"`: only `N24j` (this change) | high |
| The pre-change materializer resolved `section_relative` to `base_address + addend` | `47a383b` `fmp-materialize/src/lib.rs` `source()`: the arm reads `section.base_address` and returns `E-FIXUP-002` when absent | high |
| Two positives place a symbol at exactly `declared_size` | scan over the positive corpus: `A64-P6` (`S1`, 4104/4104) and `RV-P8` (`S1`, 4096/4096) | high |
| The pre-change validator accepted an out-of-range offset | `47a383b` `check_symbols`: the condition is `section(section_id).is_some()` | high |
| `fmp-plan` already refuses the kind | `PlanBuilder::from_model` returns `Unrepresentable` at `/fixups/0/target/kind` | high |
| The parity test now cross-checks that refusal | `rebuild_negative` in `planner_api.rs`; green | high |

## Review triggers

- A slice needs a section base address as a fixup target. It must measure the
  semantics (relocation record, linked image) and supersede this ADR.
- A positive vector wants a symbol offset beyond `declared_size`, for example a
  common symbol. That is a different symbol kind and needs its own decision.
- A definition file ships a section-symbol use that assumes a base address; the
  rejection is then the wrong surface and the ADR must be revisited.
