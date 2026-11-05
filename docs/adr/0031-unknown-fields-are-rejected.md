# ADR-0031: Unknown fields are rejected at every level

- Status: accepted
- Date: 2026-11-05
- Settles: `OD-05` (unknown fields and extensions)
- Supersedes: none
- Superseded by: none

## Context

`01_contract.md` §3 said unknown fields are rejected "unless they are inside a
versioned extension object (`OD-05`)". That escape hatch was the open question:
a newer planner could emit a plan with a field this materializer has never seen,
and the reader had to either reject it or carry it without understanding it. The
three candidate answers were:

- **A** reject every unknown field;
- **B** allow `x_*`-namespaced fields and ignore them;
- **C** allow a version-gated extension object.

The evidence needed was a plan written by a newer planner read by an older
materializer. The reader already enforces closed field sets at every level
(`Obj::closed`), so A was the only option that did not add a second parsing
regime.

## Decision

**A. Every object is closed. An unknown field is rejected, never carried,
ignored or interpreted.**

- In a plan, the first unknown field is `E-PLAN-003`; the path is the object that
  carries it (`""` for the root, `/instructions/0` for the first instruction) and
  the detail keys are `field` and `object`.
- In a definition, the same structural fault is `E-DEF-001`, because the
  definition loader maps every structural fault to its one code.
- There is no `x_*` namespace and no version-gated extension object in
  `fmp/0.1`. A field that changes what the materializer must do is a format
  change: it bumps `format_version` (new plan) or `version` (new table), and an
  older materializer rejects it with `E-PLAN-001` or `E-DEF-002`.
- `enabled_extensions` is **not** an extension mechanism. It is part of
  `target_identity`, and the plan's set must equal the definition's set
  (`E-TARGET-001`, `N06`); an unknown extension name is a mismatch, not an
  accepted hint.

The counterexample is `fixtures/x86_64/negative/N21a-unknown-root-field` and
`N21b-unknown-instruction-field`: the same plan with one extra field is rejected
at read time, while the plan without it materializes. Ignoring the field would
let a newer planner believe it had stated a byte-affecting decision that this
materializer silently discarded — the under-frozen failure `INV-02` forbids.

## Consequences

- `N21` is added to the validation matrix; both fixtures are read-phase and
  compare the complete diagnostic identity.
- `01_contract.md` §3 now states the rule without an extension-object exception,
  and §14 no longer lists `OD-05`.
- No code change: the strict reader already behaved this way. The ADR turns the
  behaviour into a contract decision and pins it with a fixture.
- A future extension point must be designed as a new `format_version`, not as an
  ignored field; this keeps the "older reader rejects newer plan" property
  explicit.
