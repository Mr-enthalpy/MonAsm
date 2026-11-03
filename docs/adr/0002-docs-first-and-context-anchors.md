# ADR-0002: Docs-first with explicit context anchors

- Status: accepted
- Date: 2026-11-03
- Supersedes: none
- Superseded by: none

## Context

This research runs in long sessions with context compaction. The directive is
large and its constraints are easy to lose: an agent that has forgotten INV-02
will happily add a "pick the shorter encoding" convenience path. Prose in a chat
history is not a durable constraint.

## Decision

Four anchors, each with a single job:

1. `AGENTS.md` — short, always-loaded constraint sheet: the eight invariants, the
   hard rules, the forbidden actions, the repository map, and the definition of
   done.
2. `docs/STATUS.md` — resumable state: phase, gates, decisions, open questions,
   next action, verified environment facts.
3. `docs/fmp-v0/00_directive.md` — immutable source text, copied verbatim. It is
   never edited; everything else cites it.
4. `docs/adr/NNNN-*.md` — one decision per file, with status. Reversal requires a
   new ADR that marks the old one `superseded`.

Supporting mechanisms:

- **Single registry per ID family.** `INV-*` is declared in
  `01_contract.md`; `EC-*` in `02_encoding_choices.md`; `OD-*` in
  `05_open_decisions.md`; `N*` and `EXP-R*` in `06_validation_matrix.md`;
  `E-*` in `04_errors.md`. `tools/check_ids.py` enforces uniqueness and
  resolvability.
- **Counterexample or `TBD`.** A frozen field must cite the concrete failure
  that occurs when it is absent. This prevents "looks complete" documents.
- **Byte-stable fixtures.** `.gitattributes` disables text normalization for
  `fixtures/**` and `*.bin`, so determinism experiments are not polluted by
  line-ending conversion on Windows.
- **Disposable zones.** `research/external/` and `tools/oracle/out/` are
  gitignored and deletable.

## Consequences

- A fresh session can recover the full constraint set from two small files.
- Documents grow a maintenance cost: every ID must resolve, and every field
  needs a counterexample. `check_ids.py` makes the first cheap and mechanical.
- The directive stays authoritative even if we later disagree with it: we record
  disagreements as ADRs and open decisions rather than editing the source text.

## Alternatives considered

- Single monolithic design document: rejected, because partial updates silently
  invalidate cross-references and there is no registry to check.
- Chat-only memory: rejected outright; that is the failure mode this ADR exists
  to prevent.

## Review triggers

If `AGENTS.md` exceeds roughly 120 lines, split stable constraint text into
`docs/fmp-v0/01_contract.md` and keep only the invariants and prohibitions
inline.
