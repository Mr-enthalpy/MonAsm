# AGENTS.md — MonAsm working constraints

This file is the context anchor. Read it first, then `docs/STATUS.md`, then the
document it points to. If this file disagrees with another document, this file
wins. If it disagrees with `docs/fmp-v0/00_directive.md` about intent, the
directive wins.

## What this repository is

MonAsm builds a **deterministic materializer** for a **Frozen Machine Plan
(FMP)**: a versioned contract carrying machine facts that have already been
decided (instruction selection, operand legality, encoding form, layout,
fixups). The materializer only validates and executes that plan.

Long-term target (ADR-0001): **Route C**, a self-owned minimal encoding kernel
with versioned target definitions. XirAsm and LLVM are temporary oracles and
knowledge sources only. They must never become a runtime dependency of the
materializer.

The current round is **HE-1 — Horizontal Extension Ready** (`ADR-0125`): target
packages, an immutable definition bundle, a target-agnostic core and package-level
conformance, so an ordinary instruction-family extension lands in
`packages/<target>/<owned-package>/**` without touching the core. `fmp/0.1` and
every shipped definition stay frozen; the round ends at HE-1 acceptance and does
not roll into coverage work.

## The eight invariants (full text: `docs/fmp-v0/00_directive.md` §3)

- INV-01 No implicit instruction selection at materialization time.
- INV-02 No implicit encoding-form selection.
- INV-03 No implicit instruction expansion.
- INV-04 No implicit layout modification: no padding, relaxation, trampolines.
- INV-05 No hidden environment dependency: host, time, randomness, hash order.
- INV-06 No metaprogramming: no macros, scripts, callbacks, expression evaluation.
- INV-07 Strict rejection: illegal input is an error, never a silent repair.
- INV-08 Replayable and traceable: plan + definition + toolchain version + options.

## Hard rules

1. **Docs before code.** No implementation lands before the contract section it
   implements exists and is referenced by ID.
2. **Every field needs a counterexample.** A field without a concrete failure
   that occurs when it is missing is marked `TBD`, never `frozen`.
3. **No fabricated evidence.** Unverified claims are labelled `inference` or
   `unverified`. Never cite a file, API, line number, or version you have not read.
4. **Evidence over naming.** Never infer behavior from a function name
   (`encode()`, `emit()`, `fixup()`). Trace the call path or run an experiment.
5. **Two independent sources per positive vector.** Our output plus an
   independent oracle (llvm-mc, binutils, manual derivation). Never validate a
   function against itself.
6. **Contract before coverage.** Never trade contract validation for more ISA
   coverage. Vertical slices only.
7. **Decisions become ADRs.** Reversing an accepted ADR requires a new ADR that
   marks the old one `superseded`.
8. **Keep the disposable zones disposable.** `tools/oracle/` and
   `research/external/` must be deletable without breaking the product build.

## Never do

- Never let the materializer choose, shorten, relax, extend, pad, or reorder.
- Never add a fallback path that makes an illegal plan succeed.
- Never store bytes as a substitute for decisions, unless the contract says so.
- Never re-open the assembler survey; the comparison phase is closed.

## Repository map

| Path | Purpose |
|---|---|
| `docs/fmp-v0/` | Contract set; `00_directive.md` is immutable source text |
| `docs/fmp-0.2/` | `fmp/0.2` surface (from H3); `docs/fmp-v0/` is never edited for it |
| `docs/adr/` | Architecture decision records |
| `docs/architecture/` | HE-1 design and acceptance text; `he1-horizontal-extension.md` declares the `HE-AC`/`HE-T` families |
| `docs/STATUS.md` | Phase, gate status, next action |
| `schema/` | Machine-readable FMP schema (draft) |
| `definitions/` | Pinned encoding definitions (`x86_64/0.1.0.json` is canonical) |
| `packages/` | Target packages (from H2, `ADR-0128`); an ordinary extension's whole change |
| `bundles/` | Explicit bundle specs and locks (from H2); never discovered by scanning |
| `fixtures/` | Per-ISA plans, expected bytes, oracle metadata |
| `research/` | Evidence index and disposable external snapshots |
| `research/he1/` | HE-1 baseline and per-phase reports; evidence only, never a build input |
| `prototype/` | Rust workspace; empty until Phase 3 |
| `tools/` | Oracles, doc consistency (`check_ids.py`) and definition consistency (`check_definition.py`) |

## Definition of done for any change

- Every ID used by the change is declared in its registry document.
- `python tools/check_ids.py` passes.
- `python tools/check_definition.py` passes when `definitions/` changes.
- New behavior has a negative test, or an explicit "not applicable" reason.
- An **ordinary extension** (HE-1 class 1, `ADR-0125`) changes only
  `packages/<target>/<owned-package>/**`; it must not edit the core, the protocol
  schema, a central form table, `STATUS.md` counts or another package.
- A change that reverses a family an accepted ADR closed needs its own ADR, even
  when it ships as a package.
- The legacy corpus keeps its hand-checked counts; package counts are generated
  (`ADR-0125` decision 4). Do not introduce a third, hand-maintained count.
