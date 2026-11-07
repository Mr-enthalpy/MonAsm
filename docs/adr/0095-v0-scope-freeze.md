# ADR-0095: the contract set is frozen for the v0 scope

- Status: accepted
- Date: 2026-11-08
- Settles: `AC-10` (the executable next step) and the Phase 5 convergence gate
- Supersedes: none
- Superseded by: none
- Revises: the `Status:` line of `01_contract.md`, `02_encoding_choices.md`,
  `03_fixup_model.md`, `04_errors.md`, `05_open_decisions.md`,
  `06_validation_matrix.md` and `07_definition_format.md`

## Context

The contract set still opens with `Status: **draft**`, from the Phase 2 wording.
That word no longer describes the state: every field the three v0 slices use is
frozen with a counterexample, all 40 `EC` rows are frozen, every `OD` row is
accepted, all eight invariants are `verified`, the corpus has 100 positive and
537 negative fixtures, and `EXP-R3` passes on three CI hosts. Leaving the status
as `draft` makes two false statements: that a reader cannot rely on the in-scope
surface, and that nothing is decided.

At the same time, not every field is frozen. Four plan fields (`source_ref`,
`source_trace`, `symbol.type`, `symbol_order`) are optional and either never
affect output or exist only for the deferred Level 1 output; they have no v0
counterexample. `section_relative` is named by the contract but no fixture
exercises it and its semantics remain `inference`/`unverified`
(`03_fixup_model.md` §2.1). Calling the whole set "frozen" would assert evidence
that does not exist, which `AGENTS.md` rule 2 forbids.

## Decision

1. The contract set status becomes **"frozen for the v0 scope"**. This means:
   - the in-scope surface in `01_contract.md` §3–§12 is decided, tested, and may
     be implemented against;
   - `02_encoding_choices.md`'s 40 `EC` rows are frozen;
   - `04_errors.md`'s 43 active codes are the declared error surface;
   - `06_validation_matrix.md`'s `AC` table is the acceptance record;
   - `07_definition_format.md` is frozen for the shipped target tables.
2. The four `draft` fields stay `draft` and are recorded as **out of v0 scope**.
   They are not marked frozen, and a plan that omits them is valid.
3. `section_relative` stays `unverified` and is recorded as **out of v0 scope**.
   A plan that uses it is not covered by the v0 evidence.
4. Level 1 output (`artifact: sections`, `include_symbol_table: true`) is
   explicitly out of v0 scope. It remains legal in the schema so a later slice
   can opt in without a format bump, and it is rejected at Level 0 as
   `E-VERSION-001`.
5. No Rust source, definition document, fixture, or schema file changes as part
   of this ADR. The `schema/examples/` corrections made in the same Phase 5 pass
   fix stale names and digests only; they do not change the schema or any
   definition.
6. The Phase 5 deliverable is `08_final_recommendation.md`. The directive's §15
   example names `05_final_recommendation.md`, but `05` is already the
   `05_open_decisions.md` registry; only the filename deviates, not the §17
   content.

## Consequences

- A reader of `docs/fmp-v0/` can treat the in-scope surface as a contract.
- A reader cannot mistake a `draft` field or `section_relative` for validated
  behaviour; both are named as out of scope.
- Phase 6 starts from a stable reference, so a later widening ADR compares against
  a fixed text instead of a moving draft.
- The word "draft" may still appear in the JSON schema's `x-status`; the schema
  is a machine-readable projection of this document set and its status follows
  this ADR. The four optional fields remain marked `x-status: draft` in the
  schema, matching decision 2.

## Alternatives rejected

- **Leave the status `draft`.** Rejected: it understates a completed contract and
  invents uncertainty where tests exist.
- **Mark everything frozen.** Rejected: it would mark fields without a
  counterexample, violating `AGENTS.md` rule 2 and overstating `section_relative`.
- **Remove the draft fields and `section_relative` from the contract.** Rejected:
  they are either needed by the deferred Level 1 output or already named by the
  envelope; deleting them would create a second, untracked format question.
