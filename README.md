# MonAsm

A deterministic materializer for a **Frozen Machine Plan (FMP)**.

FMP is the contract between an upstream planner and this repository. The planner
is responsible for instruction selection, operand legalization, encoding-form
selection, layout, and fixup planning. The materializer validates a frozen plan
and executes it: it emits bytes and fixup records, and rejects anything it cannot
execute exactly as written.

The materializer has no planning authority. That is the whole point.

## Status

**Phase 0 — documentation baseline.** No encoder is implemented yet.

| Area | State |
|---|---|
| Contract (`docs/fmp-v0/01_contract.md`) | draft, fields marked `TBD` where unproven |
| Schema (`schema/fmp-v0.schema.json`) | draft, not yet frozen |
| Prototype (`prototype/`) | empty workspace, Phase 3 |
| Oracles (`tools/oracle/`) | planned, Phase 0 gate G0 |
| Evidence (`research/evidence/`) | index started, XirAsm pinned |

Read `docs/STATUS.md` for the current phase, gate status, and next action.

## Reading order

1. `AGENTS.md` — working constraints and the eight invariants.
2. `docs/fmp-v0/00_directive.md` — immutable research directive (source of truth).
3. `docs/fmp-v0/01_contract.md` — the FMP v0 contract.
4. `docs/STATUS.md` — where the work stands.

## Repository layout

```text
docs/
  STATUS.md                  phase, gates, next action, open decisions
  glossary.md                terms used across the contract set
  fmp-v0/                    contract, encoding choices, fixups, errors, matrix
  adr/                       architecture decision records
schema/                      JSON Schema for FMP v0 (draft)
fixtures/{x86_64,aarch64,rv64}/ plan + expected bytes + oracle metadata
research/evidence/           source index, pinned revisions, experiment records
research/external/           disposable snapshots (gitignored, pinned by SHA)
prototype/                   Rust workspace (empty until Phase 3)
tools/oracle/                temporary oracle wrappers (llvm-mc, binutils)
tools/check_ids.py           documentation consistency check
```

## Invariants at a glance

INV-01 no implicit instruction selection · INV-02 no implicit encoding-form
selection · INV-03 no implicit expansion · INV-04 no implicit layout change ·
INV-05 no hidden environment dependency · INV-06 no metaprogramming ·
INV-07 strict rejection · INV-08 replayable and traceable.

Each invariant has a registry row in `docs/fmp-v0/01_contract.md` and must map to
an executable test before it can be marked verified.

## Checking the docs

```bash
python tools/check_ids.py
```

The check verifies that IDs (`INV-*`, `N*`, `EXP-R*`, `AC-*`, `EC-*`, `OD-*`,
`E-*`) are declared exactly once in their registry document, that references
resolve, and that every declared negative test appears in the validation matrix.

## Dependency posture

XirAsm and LLVM are **temporary**: oracles, knowledge sources, and audit targets
(see `docs/adr/0001-route-c-self-owned-core.md`). The product path must build and
run with both directories deleted.

## License

Apache License 2.0. See `LICENSE`.
