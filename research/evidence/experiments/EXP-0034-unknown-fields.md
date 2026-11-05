# EXP-0034 — Unknown fields are rejected, not ignored

- Date: 2026-11-05
- Question: what does an older materializer do with a plan or definition written
  by a newer planner that carries a field the format does not declare?
- Toolchain: Rust 1.96.0; `cargo test -p fmp-cli --test fixtures` and
  `cargo test -p fmp-model`
- Decision: `OD-05` / `ADR-0031`

## 1. Plan side

Two plans differ from `X86-P1`'s first instruction only by one extra field:

| Fixture | Added field | Result |
|---|---|---|
| `fixtures/x86_64/negative/N21a-unknown-root-field.fmp.json` | `"future_hint": { "planner": "0.2", … }` at the root | `E-PLAN-003`, path `""`, detail keys `field`, `object`; read phase rejects, no definition is looked up |
| `fixtures/x86_64/negative/N21b-unknown-instruction-field.fmp.json` | `"encoding_family": "legacy"` on `instructions[0]` | `E-PLAN-003`, path `/instructions/0`, detail keys `field`, `object` |

The unmodified instruction is `x86:mov/rm-r64/legacy` with `rax`/`rbx`, which the
`X86-P1` oracle records as `48 89 d8` (`EXP-0005`). Adding the field does not
change that result, because no bytes are emitted: the plan stops at read time.
The reader's `Obj::closed` checks every object, so the same rule applies to
nested objects (target, definition, output, section, fragment, symbol,
instruction, operand, fixup, provenance) without a per-object list here.

## 2. Definition side

`fmp_model::definition::read` maps every structural fault to `E-DEF-001`. The
unit test `definition::tests::unknown_definition_field_is_rejected` inserts
`"future_form_family": 1` at the definition root and asserts `E-DEF-001` with the
field name in the message. The table is not loaded partially: there is no
"known forms only" mode.

## 3. Extension names

`enabled_extensions` is not a free-form extension list. The plan's set must equal
the definition's set (`E-TARGET-001`). `N06` measures both directions that exist
in v0: an x86 plan that omits `avx`/`avx512f`/`avx512vl` against `0.5.0`, and an
RV64 plan that omits `rv64c` against `0.2.0`. An unknown extension name produces
the same mismatch rather than being accepted as a hint.

## 4. Reading

Ignoring an unknown field is not a neutral choice. A newer planner could add a
field intending to change a byte, and an older materializer would silently emit
the old encoding while reporting success — the under-frozen failure `INV-02`
forbids. Rejecting it makes the version boundary explicit: a new field requires a
new `format_version` (plan) or table `version` (definition), and an older
materializer stops at `E-PLAN-001`/`E-DEF-002`.
