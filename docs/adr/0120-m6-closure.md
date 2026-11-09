# ADR-0120: M6 closes at 841 forms and 128 positives

- Status: accepted
- Date: 2026-11-10
- Settles: the scope of Phase 7 M6 and its final metrics
- Supersedes: none
- Superseded by: none
- Revises: the phase board, phase line and next-action prose of
  `docs/STATUS.md` (including gate G2); the §A.3 evidence rows, the §D.1/§D.2/
  §D.3 surfaces and fixture counts, the §F.3 cost and the §H `M2`/`M4`/`M6` rows
  of `08_final_recommendation.md`; the §8 digest list of
  `07_definition_format.md`; the §"v0 surface" counts of
  `02_encoding_choices.md`; the parity counts of `09_planner_api.md` §5/§7 and
  `prototype/README.md`; the shipped definition ranges of `01_contract.md`
  §7.1; the oracle state in `tools/oracle/README.md`; the status of
  `10_m6_plan.md`; the x86/AArch64/RV64 prose of `README.md`

## Context

`ADR-0112` opened M6 as coverage round 2: seven additive slices, one ADR each,
plus this closure. The planning target was 84 new rows, 843 forms, 128 positive
vectors and at least 607 negatives, with no contract change.

All seven slices landed: `S1` `ADR-0113` (`x86/0.75.0`), `S2` `ADR-0114`
(`0.76.0`), `S3` `ADR-0115` (`0.77.0`), `S4` `ADR-0116` (`0.78.0`), `S5`
`ADR-0117` (`rv64/0.6.0`), `S6` `ADR-0118` (`aarch64/0.19.0`) and `S7`
`ADR-0119` (`0.20.0`). Two slice ADRs recorded a row correction against the
plan, both measured rather than assumed:

- `S1` is fifteen rows, not sixteen. `sub` already had all three
  register/register widths in `0.74.0`; `add` had none, and the other four
  mnemonics had none, so the slice is `3 + 12` (`ADR-0113`).
- `S3` is five rows, not six. `REX.W B8+rd` takes a 64-bit immediate (`io`) and
  is `movabs`, which stays out; the five rows are `B8+rd` at 16/32 bits and
  `C7 /0` at 16/32/64 bits (`ADR-0115`).

`S7` also corrected the plan's error code: `cond = 16` is `E-RANGE-001`, not
`E-OPERAND-004` (`ADR-0119`, `N03a1`).

The round therefore lands 82 rows and not 84, and 841 forms and not 843. The
positive target of 128 is met exactly; the negative count of 611 exceeds the
plan's "at least 607".

## Decision

1. **M6 closes with the seven slices.** No eighth slice is part of M6; a new
   widening request opens a new ADR and does not reopen this one.
2. **The definition set is frozen at the slice versions.** x86-64 `0.78.0`
   (632 forms, digest
   `sha256:30cb9f13047ff742d8f53a20f93218a601302bd52814ad26364347cb85576a21`),
   `rv64/0.6.0` (24 forms, digest
   `sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585`)
   and `aarch64/0.20.0` (185 forms, digest
   `sha256:05033c9e1c5ca430d2922312cf7139c9bc4e8cc7c34364e24a455efa9a1df6cd`).
   The total is 841 forms across 104 documents (78 x86, 20 AArch64, 6 RV64),
   and `tools/check_definition.py` confirms every form is named by a positive
   fixture.
3. **The corpus is recorded.** 128 positive plans and 611 negative plans
   (605 `materialize`-phase plus the 6 `read`-phase negatives).
   `tools/oracle/rerun.py` re-derives `122/128` positive records
   byte-identically, with six `manual-derivation` skips and no failures. The
   six skips are `X86-P1`, `X86-P4`, `X86-P5`, `X86-P9`, `X86-P10` and
   `X86-P83`; `X86-P83` is the one the round added.
4. **The `EC` registry is 44 rows.** `EC-43` (`adr` vs `adrp`, `ADR-0118`) and
   `EC-44` (`mul` vs `madd`, `ADR-0119`) are the round's two additions;
   `EC-42` is revised in place twice (`ADR-0113`, `ADR-0116`) and the count is
   otherwise unchanged. All 44 rows stay `frozen` with a measured
   counterexample and a decided carrier.
5. **The measured difference is the plan's error, not the tables'.** The plan
   counted 84 rows because it expected a fourth `sub` register/register row at
   S1 and a sixth `mov` immediate row at S3. Both expectations were wrong
   against the opcode tables; the slice ADRs record the corrections and the
   closure follows the definitions (`ADR-0112` review trigger 3).
6. **The non-goals stay closed.** `moffs` (`A0`-`A3`), APX `d5`, EVEX
   masking/broadcast, AArch64 `EC-16` (`mov` alias) and `EC-18`
   (`cbz`/`tbz`), RV64 `c.j`/`c.jalr`, and FP/SIMD beyond SSE. The round's own
   residue stays deferred too: the high register windows of the 32/16-bit and
   memory rows, SIB/index and zero-displacement memory shapes, the 8-bit
   immediate windows, the memory forms of the new ALU mnemonics, `adc`/`sbb`,
   `test`, `neg`/`not`, RV64 `fence`/atomics/compressed loads, and AArch64
   `madd`/`msub` with a non-zero `Ra` and `cset`/`cinc`.
7. **The stale metrics are reconciled.** This ADR updates the phase board and
   gate G2 to 44 `EC` rows, the surfaces and fixture counts of
   `08_final_recommendation.md` §A.3/§D, the Route C cost in §F.3, the roadmap
   rows in §H, the parity counts in `09_planner_api.md` and
   `prototype/README.md`, the shipped ranges in `01_contract.md` §7.1, the
   oracle state in `tools/oracle/README.md`, and the x86 surface count and the
   RV64 slice note in `02_encoding_choices.md`.

## Consequences

- `STATUS.md` reports Phase 7 complete. A new session starts from a stable
  contract, a frozen definition set and a known corpus.
- The M6 difference from the plan is 2 rows and 2 forms, both attributable to
  the two slice corrections; no other count moved.
- `02_encoding_choices.md`'s x86 table is stated as an excerpt of the early
  surface rather than the full table: it lists 417 rows, while the shipped
  table is 632 forms. `07_definition_format.md` §8.1 is the complete,
  checker-verified record and already was; the 02 sentence now says so instead
  of implying the excerpt is the table. The RV64 note says the same for its
  ten-row table.
- Any further ISA widening is out of M6 and needs its own ADR with a measured
  vector and an absent-sibling rejection.
- The route decision (`ADR-0001`, Route C) is unchanged: the definition files
  remain small, versioned target facts, not a copy of an assembler.
- CI has not been re-run for the closure commit; the local gates are listed
  below. The CI status is therefore `unverified` for this commit.

## Alternatives rejected

- **Restore the plan's 84 rows by adding the two expected rows.** Rejected:
  `sub`'s register/register row already exists in `0.74.0` (adding it again
  would duplicate a `form_id`), and `REX.W B8+rd` is `movabs`, a standing
  non-goal. The plan's count was wrong, not the table.
- **Fold the closure into `ADR-0119`.** Rejected: `ADR-0119` is the `mul`/`csel`
  slice; the scope decision and the metric reconciliation are a separate
  decision and need their own record.
- **Update only `STATUS.md` and leave the recommendation document.** Rejected:
  `08_final_recommendation.md` states the Route C cost as form counts, so
  leaving 564/180/15 would make the cost argument wrong by construction.
- **Rewrite the whole `02_encoding_choices.md` x86 table to 632 rows.**
  Rejected: `07_definition_format.md` §8.1 is already the complete table and
  is machine-checked against the JSON; duplicating it in a prose document
  doubles the maintenance without adding a check. The 02 table is labelled an
  excerpt instead.
- **Leave Phase 7 "in progress" until CI runs.** Rejected: the local gates are
  the same set used for every earlier slice, and the convention is to mark CI
  `unverified` in the ADR rather than hold the phase open.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| x86-64 `0.78.0` has 632 forms, `rv64/0.6.0` 24, `aarch64/0.20.0` 185 | `tools/check_definition.py` output | high |
| The three digests are the ones recorded above | `tools/check_definition.py` output | high |
| 104 definition documents (78 + 20 + 6) | directory counts under `definitions/` | high |
| 128 positives and 611 negatives (605 + 6) | fixture directory counts and `planner_api.rs` | high |
| `rerun.py` re-derives `122/128` with 6 skips and 0 failures | `python tools/oracle/rerun.py` output | high |
| The six skips are the six named records | `rerun.py` output, `SKIP` lines | high |
| Every form is named by a positive fixture | `check_definition.py` form-coverage check | high |
| 44 `EC` rows, all frozen | `tools/check_ids.py` (`EC=44`) and 44 table rows in `02_encoding_choices.md` | high |
| The plan's 84 rows / 843 forms were never reachable | `ADR-0113` and `ADR-0115` measured corrections | high |
| CI is green for this commit | not run | unverified |

## Review triggers

- A new ISA family or a new version of an existing definition is proposed;
  the closure numbers change and this ADR must be superseded, not edited.
- A skipped record starts to re-derive, or a re-deriving record starts to
  fail; the `122/128` claim becomes false and the failure must be triaged
  before any further widening.
- A non-goal is proposed for inclusion; it reopens the scope decision.
- The corpus counts diverge from `planner_api.rs`; the parity gate is the
  source of truth and the metric must be re-stated.
- The `02_encoding_choices.md` x86 excerpt is proposed as a complete table;
  that is a new document decision, not a count fix.
