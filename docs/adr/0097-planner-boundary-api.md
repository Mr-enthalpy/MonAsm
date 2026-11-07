# ADR-0097: the planner boundary is a total, closed plan builder in `fmp-plan`

- Status: accepted
- Date: 2026-11-08
- Settles: the design half of `08_final_recommendation.md` §H M4 (planner
  boundary/API); the M4 exit gate still requires the implementation and its
  parity tests
- Supersedes: none
- Superseded by: none
- Revises: the M4 row of `08_final_recommendation.md` §H and the `AC-10` row of
  `06_validation_matrix.md`; adds `docs/fmp-v0/09_planner_api.md` and the
  **plan builder** row of `docs/glossary.md`

## Context

`01_contract.md` §1 names the boundary — the planner writes an FMP, the
materializer validates and executes it — and §3–§12 define the document. What
the set does not define is the *programmatic* form of the writing side. There is
no planner-side writer in this repository, so the documented authoring path is a
JSON document assembled by hand (`inference`: no planner is in the repository;
the contract only states the document). That has three measurable costs:

- **Drift with no guard.** A field the validator reads but the writer spells
  differently is invisible until a fixture fails. The positive corpus already
  requires oracle agreement (`fixtures.rs`), but nothing forces the *writer* to
  cover the same fields as the *reader*.
- **Silent defaults.** Hand-written JSON makes it easy to omit a field the
  reader treats as required or to insert a value the contract never made
  optional. `E-PLAN-006` catches the omission only after the fact.
- **No closed-set statement.** `ADR-0031` makes every object closed, but a
  hand-written writer carries no closed set of its own, so an unknown field is
  a typing accident rather than an impossibility.

M3 is complete (`ADR-0096`), so the materializer now emits both Level 0 and
Level 1. The M4 gate in `08_final_recommendation.md` §H is: *API tests reject
illegal plans at the same codes*. The cheapest way to make "the same codes"
true by construction is to have no second rule set at all: the writer must hand
its bytes to the same reader and validator. This ADR chooses that shape.

Two facts measured before deciding:

- `fmp_model::plan::read` binds every object through `Obj::closed`
  (`bind.rs`), retains `Unknown(String)` members in each closed enum so that
  `fmp-validate` can report `E-VERSION-001` on the document path, and returns
  the typed `Plan` used by `fmp_validate::check` and
  `fmp_materialize::materialize`.
- The corpus is 101 positives and 546 negatives; 540 negatives are
  `materialize`-phase and 6 are `read`-phase (`N15`, `N21a`, `N21b`, `N23a`,
  `N24a`, `N24b`). Scanning every `*.fmp.json` finds no draft field
  (`source_ref`, `source_trace`), no `symbol.type`, no `symbol.size`, no
  `section_relative` target, and no unknown enum member. `artifact` is `bytes`
  or `sections`; `section_kind` is `code` or `bss`; symbol `kind` is `defined` or
  `external`; `binding` is `local` or `global`; fixup targets are `symbol` or
  `absolute`; every transform, PC rule, resolution mode and pair role is a
  contract member. The `540` materialize-phase negatives are therefore all
  representable through a closed typed writer.

## Decision

1. **A new planner-side library crate, `fmp-plan`.** It sits in the workspace
   next to the materializer crates. Its dependency direction is one-way:
   `fmp-plan -> fmp-model` only. `fmp-model` never depends on it, and
   `fmp-validate`, `fmp-materialize` and the `fmp` binary never link it outside
   a test target. The builder therefore cannot become a second validator or a
   hidden runtime dependency of the materializer.
2. **The builder is total and typed.** `PlanBuilder::new` takes the seven
   required root members. `format_version` is pinned to `fmp/0.1` by the crate,
   not passed by the caller; a new format is a new crate version. Every required
   contract field is a constructor argument. Optional fields are `Option`, and a
   closed enum lists exactly the contract members. There is no `Default`, no
   `new_empty`, no partial builder and no failure mode in `build`.
3. **The builder has no planning authority and no validation.** It does not
   select a form, choose an encoding, expand, lay out, pad, relax, reorder,
   compute an offset, size, addend or range, resolve a symbol, synthesize a
   byte, default a field, sort a list or validate a value. `build` serializes
   caller facts to `fmp_model::json::Json`; `build_canonical` returns
   `fmp_model::canonical::canonical_bytes` of that value. Array order is
   caller-supplied because §12 ordering is a plan obligation and the validator
   already rejects a misordered list (`E-LAYOUT-004`); the builder must not
   repair one.
4. **"Same codes" is achieved by re-reading, not by re-checking.** The M4
   tests rebuild a fixture plan through the builder, serialize it, and feed the
   bytes back through `fmp_model::plan::read` and `fmp_materialize::materialize`.
   Because the reader and validator are unchanged, an illegal plan is rejected
   with the same code, JSON Pointer and detail-key set. A builder field that the
   validator reads but the builder drops or renames fails parity.
5. **The builder exposes the frozen v0 surface, not the whole schema.** It
   excludes the three `draft` fields (`source_ref`, `source_trace`,
   `symbol.type`), the unverified `section_relative` fixup target, and the
   schema-only `symbol.size`. Excluding a field here does not make the document
   invalid and retires no code: the document path still accepts what the
   contract permits.
6. **`PlanBuilder::from_model` is a re-emission helper with a typed failure.**
   It is lossless over the frozen v0 surface and drops only the excluded fields.
   It returns `Result<_, Unrepresentable>` rather than panicking when a bound
   plan carries a value the closed builder cannot express (an unknown enum
   member, a `section_relative` target, or a non-default `fixup_record_order`,
   which is `E-VERSION-001`). It succeeds on every
   plan `plan::read` accepts — 101 positives plus 540 `materialize`-phase
   negatives, 641 documents — so the parity gate is 101/101 and 540/540 with no
   exception list. The six `read`-phase negatives never produce a `Plan` and are
   covered by the structural-exclusion check instead.
7. **The M4 exit gate is six tests** in
   `prototype/crates/fmp-cli/tests/planner_api.rs`: positive parity over all
   101 positives (bytes, record count, recorded Level 1 envelope), negative
   parity over all 540 `materialize`-phase negatives (code, path, detail keys),
   from-scratch authoring for at least one positive per ISA plus `X86-P71`, a
   closed-key-set check on a maximal document, a structural-exclusion check for
   the six `read`-phase negatives, and a determinism check (two builds, one
   canonical byte string). The test lives in `fmp-cli` because that crate
   already loads the registry and the fixture tree; `fmp-plan` stays free of
   both.
8. **The `symbol.size` mismatch is recorded, not repaired here.** The schema's
   symbol object allows `size`; `01_contract.md` §9 does not define it; and
   `fmp-model` accepts but does not bind it (`SYMBOL_FIELDS` includes both `type`
   and `size`, while `bind_symbol` reads neither). The builder follows the
   contract. `09_planner_api.md` §8 records the defect so a later ADR can either
   add the field as `draft` or remove it from the schema and the accepted set.

## Consequences

- The planner side gains a writer that cannot express a partial document, an
  unknown field, or an unknown enum member. Those are type errors instead of
  late diagnostics.
- The materializer gains no code path, no dependency and no second source of
  truth. `fmp materialize` still reads bytes exactly as before.
- The parity test is a real drift guard in both directions: a reader field that
  the builder omits shows up as a parity failure, and a builder convenience that
  changes a value shows up as an oracle or diagnostic mismatch.
- Re-emitting a plan with a draft field is intentionally lossy: the fingerprint
  of the re-emitted document differs by that field. No corpus fixture carries
  one, and no output decision depends on it (`INV-05`).
- The API surface is small and dataless: adding a definition version or a form
  changes strings a caller passes, not the library.

## Alternatives rejected

- **A hand-written JSON layer with no types.** Rejected: it is the status quo,
  and it cannot state a closed set or make a partial document unrepresentable.
  The drift and default costs in Context stay unaddressed.
- **A validating builder that rejects illegal plans itself.** Rejected: it
  creates a second rule set. "Same codes" would then depend on the two rule sets
  staying aligned by discipline, and `E-PLAN-*`/`E-VERSION-*` would have two
  producers. Re-reading through the shipped reader keeps one authority.
- **Put the builder in `fmp-model`.** Rejected: the reader would then share a
  crate with an authoring path and could acquire a dependency on it. The
  materializer's dependency graph must stay planner-free, and the one-way edge
  is the enforceable form of that.
- **Make the builder enumerate `form_id` values.** Rejected: it would freeze one
  definition version into the library and turn a catalog update into a library
  release. `form_id` stays a string the planner writes; `E-FORM-001` stays the
  validator's check.
- **Expose the draft fields for "completeness".** Rejected: `ADR-0095` keeps
  them out of the v0 frozen surface, and two of them are not even retained by
  `fmp-model::Plan`. A field with no counterexample is not frozen, so the
  builder must not present it as if it were.
- **Make `from_model` always succeed by adding a catch-all variant.** Rejected:
  a `Custom(String)` slot is the unknown-member escape that `ADR-0031` closed.
  Returning a typed error keeps the closed set honest and still lets the corpus
  pass.
- **Skip the from-scratch test because `from_model` covers the corpus.**
  Rejected: parity through `from_model` would only prove the helper emits what
  the reader already accepted. The from-scratch case is what proves the API is
  usable by a planner that has no bound model in hand.
