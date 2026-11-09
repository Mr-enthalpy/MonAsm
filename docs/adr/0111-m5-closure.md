# ADR-0111: M5 closes after seven coverage slices

- Status: accepted
- Date: 2026-11-09
- Settles: the scope of Phase 6 M5 and its final metrics
- Supersedes: none
- Superseded by: none
- Revises: the phase board and next-action prose of `docs/STATUS.md` (including
  gate G2); the §A.3 evidence row, the x86/AArch64/RV64 surface and fixture
  counts of `08_final_recommendation.md` §D, the §F.3 cost and the §H `M2`/`M5`
  rows; the x86 form count of `02_encoding_choices.md` §"v0 surface"; the parity
  counts of `09_planner_api.md` §5/§7 and `prototype/README.md`; the shipped
  definition ranges of `01_contract.md` §7.1; the oracle state in
  `tools/oracle/README.md`; the x86/AArch64/RV64 status prose of `README.md`

## Context

`ADR-0095` froze the contract set and left Phase 6 as five milestones. `M1`
(error-coverage), `M2` (oracle rerun harness), `M3` (Level 1 writer) and `M4`
(planner boundary) closed first. `M5` (coverage widening) then ran as seven
slices, one ADR each, in the order `S1`, `S2`, `S3`, `S6`, `S4`, `S5`, `S7`:

| Slice | ADR | Definition | Forms | Vector | Rejection fixture |
|---|---|---|---|---|---|
| `S1` | `ADR-0104` | `rv64/0.5.0` | 15 | `RV-P11` | `c.j`/`c.jalr` stay absent; `0.4.0` boundary `N01en` |
| `S2` | `ADR-0105` | `x86/0.69.0` | 519 | `X86-P75` | `ymm`/`zmm` windows absent (`N01eo`) |
| `S3` | `ADR-0106` | `x86/0.70.0` | 527 | `X86-P76` | `0.69.0` boundary `N01ep`; `xmm0`-`xmm7` on `-ext` is `N14w` |
| `S6` | `ADR-0107` | `x86/0.71.0` | 533 | `X86-P77` | `0.70.0` boundary `N01eq` |
| `S4` | `ADR-0108` | `x86/0.72.0` | 549 | `X86-P78` | `0.71.0` boundary `N01er`; high base/index deferred |
| `S5` | `ADR-0109` | `x86/0.73.0` | 561 | `X86-P79` | `0.72.0` boundary `N01es`; `%r8b`-`%r15b` deferred |
| `S7` | `ADR-0110` | `x86/0.74.0` | 564 | `X86-P80` | `2B /r` r/r absent (`N01ej`); `0.73.0` boundary `N01et` |

Each slice shipped byte vectors measured with `llvm-mc` 23.1.2 (plus the
materializer as the second source), an additive definition version whose
generator asserts the previous version is reproduced unchanged, and an
`E-FORM-001` fixture for the row or sibling it deliberately leaves out. In
`S3`, `S6`, `S4` and `S5` that fixture is the previous-version boundary, which
is exactly the row the slice adds; `S1`, `S2` and `S7` also reject a named
absent sibling.

The `M2` recovery backlog closed during the same period: the 29
`input-not-stored` records (20 AArch64, 9 RV64) were recovered from the
experiment listings or rebuilt from the recorded spellings and re-pinned by
`input_sha256`.

## Decision

1. **M5 closes with the seven slices.** No eighth slice is part of M5; a new
   widening request opens a new ADR and does not reopen this one.
2. **The definition set is frozen at the slice versions.** x86-64 `0.74.0`
   (564 forms, digest
   `sha256:27f337115cffe89c8d7028863e7748783247344ba4d8e622fa9c4345efdead58`),
   `rv64/0.5.0` (15 forms) and `aarch64/0.18.0` (180 forms). The total is 759
   forms, and `tools/check_definition.py` confirms every one is named by a
   positive fixture.
3. **The corpus is recorded.** 121 positive plans and 586 negative plans
   (580 `materialize`-phase plus 6 `read`-phase). `tools/oracle/rerun.py`
   re-derives `116/121` positive records byte-identically, with the five
   `manual-derivation` skips and no failures; there is no `input-not-stored`
   record left.
4. **The non-goals stay closed.** `moffs` (`A0`-`A3`), APX `d5`, EVEX
   masking/broadcast, AArch64 `EC-16` (`mov` alias) and `EC-18`
   (`cbz`/`tbz`), RV64 `c.j`/`c.jalr`, and FP/SIMD beyond SSE. The slice
   residue is also deferred: zero-displacement indexed shapes, high
   base/index windows, the S7 memory shapes and the `2B /r`
   register/register direction.
5. **The stale metrics are reconciled.** The phase board, the next-action
   prose and `08_final_recommendation.md` now use the numbers above; the x86
   form count in `02_encoding_choices.md` is 564; gate G2 counts 42 of 42
   `EC` rows.

## Consequences

- `STATUS.md` reports Phase 6 complete. A new session starts from a stable
  contract, a frozen definition set and a known corpus.
- Any further ISA widening is out of M5 and needs its own ADR with a measured
  vector and an absent-sibling rejection.
- The route decision (`ADR-0001`, Route C) is unchanged: the definition files
  remain small, versioned target facts, not a copy of an assembler.
- CI has not been re-run for the closure commit; the local gates are listed
  below. The CI status is therefore `unverified` for this commit.

## Alternatives rejected

- **Count M5 as complete after the first wave (`ADR-0098`-`ADR-0103`).**
  Rejected: that wave left the SSE indexed shapes, the byte-`mov` index
  windows and the register `sub` unmeasured, and the user accepted the
  seven-slice scope.
- **Fold the closure into `ADR-0110`.** Rejected: `ADR-0110` is the `sub`
  slice; the scope decision and the metric reconciliation are a separate
  decision and need their own record.
- **Update only `STATUS.md` and leave the recommendation document.** Rejected:
  `08_final_recommendation.md` states the Route C cost as form counts, so
  leaving 509/176/8 would make the cost argument wrong by construction.
- **Re-measure the whole corpus instead of re-pinning the recovered inputs.**
  Rejected: the recovery already re-ran the recorded commands and re-pinned
  `input_sha256`; a full re-measure would not add an independent source.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| x86-64 `0.74.0` has 564 forms and the recorded digest | `tools/check_definition.py` output | high |
| `rv64/0.5.0` has 15 forms, `aarch64/0.18.0` has 180 | `tools/check_definition.py` output | high |
| 121 positives, 586 negatives (580 + 6) | fixture directory counts and `planner_api.rs` | high |
| `rerun.py` re-derives `116/121` with 5 skips and 0 failures | `python tools/oracle/rerun.py` output | high |
| Every form is named by a positive fixture | `check_definition.py` form-coverage check | high |
| 42 `EC` rows, all frozen | `tools/check_ids.py` (`EC=42`) and `02_encoding_choices.md` | high |
| CI is green for this commit | not run | unverified |

## Review triggers

- A new ISA family or a new version of an existing definition is proposed;
  the closure numbers change and this ADR must be superseded, not edited.
- A recovered input fails `rerun.py`; the `116/121` claim becomes false and
  the failure must be triaged before any further widening.
- A non-goal is proposed for inclusion; it reopens the scope decision.
- The corpus counts diverge from `planner_api.rs`; the parity gate is the
  source of truth and the metric must be re-stated.
