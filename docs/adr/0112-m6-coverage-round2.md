# ADR-0112: M6 is coverage round 2

- Status: accepted
- Date: 2026-11-09
- Settles: the Phase 7 M6 scope and its seven slices
- Supersedes: none
- Superseded by: none
- Revises: the phase board and next-action prose of `docs/STATUS.md`; the §H
  roadmap row of `08_final_recommendation.md`; adds `10_m6_plan.md`

## Context

Phase 6 closed with `ADR-0111`: 759 forms across x86-64 `0.74.0`, `rv64/0.5.0`
and `aarch64/0.18.0`, 121 positive and 586 negative plans, and `fmp/0.1`
frozen. That close-out deliberately left the integer surface as vertical
strips:

- x86 `add`/`sub` exist only at 64 bits, and `and`/`or`/`xor`/`cmp` do not
  exist at any width (scan of `0.74.0`: `add` 3, `sub` 6, no other ALU
  mnemonic);
- x86 has no `mov` immediate row; `ADR-0093` records `movl $ext, %eax` as a
  gap, not a decision;
- `sub` has no memory direction; `ADR-0110` defers `2B /r` and the `29 /r`
  memory shapes;
- RV64 has only `ld`/`sd` (`0.5.0`, 15 forms);
- AArch64 has no `adr`, `mul` or `csel` (`0.18.0`).

None of these is an open format question. Each is the same form/operand split
the existing rows already use, and each is absent from the pinned tables, so a
plan that names one is `E-FORM-001` today. The alternatives at this point are a
new artifact level (Level 2 containers, explicitly outside `fmp/0.1`), a
kernel-conformance milestone, or more integer surface. The user selected more
integer surface.

## Decision

1. **M6 is coverage round 2, seven slices plus a closure ADR.** The slices and
   their boundaries are fixed in `10_m6_plan.md`; every slice lands under its
   own ADR (`ADR-0113`-`ADR-0119`) and the closure is `ADR-0120`.
2. **The slices are:**

   | # | ADR | Slice | Definition | Rows |
   |---|---|---|---|---|
   | `S1` | `ADR-0113` | x86 ALU register/register at three widths | `x86/0.75.0` | 16 |
   | `S2` | `ADR-0114` | x86 ALU immediate at three widths | `x86/0.76.0` | 36 |
   | `S3` | `ADR-0115` | x86 `mov` immediate at 16/32/64 | `x86/0.77.0` | 6 |
   | `S4` | `ADR-0116` | x86 `sub` memory directions | `x86/0.78.0` | 12 |
   | `S5` | `ADR-0117` | RV64 load/store widths | `rv64/0.6.0` | 9 |
   | `S6` | `ADR-0118` | AArch64 `adr` | `aarch64/0.19.0` | 1 |
   | `S7` | `ADR-0119` | AArch64 `mul` and `csel` | `aarch64/0.20.0` | 4 |

   The plan carries 84 new rows and 7 new positive vectors. The exact row
   counts are fixed by each slice's ADR after its probe; the totals above are
   the planning target, not frozen numbers.
3. **No contract change.** `fmp/0.1` is unchanged; no new artifact level, no
   new slot kind, no new fixup rule. The only carrier changes are new `EC`
   rows in `02_encoding_choices.md` and one direction-rule revision of
   `EC-42`; every one is declared in the slice ADR before the rows land.
4. **The standing non-goals stay closed.** `moffs`, APX `d5`, EVEX masking and
   broadcast, AArch64 `EC-16` and `EC-18`, RV64 `c.j`/`c.jalr`, and FP/SIMD
   beyond SSE. The round's own deferrals (high register windows, SIB/index and
   zero-displacement memory shapes, 8-bit immediate windows, `movabs`, atomics,
   `tbz`/`tbnz`, `madd`/`msub`, `cset`/`cinc`) are listed per slice.
5. **Each slice keeps the M5 evidence rules.** A measured `llvm-mc` 23.1.2
   vector, the materializer as the second source, an additive definition whose
   generator repeats the previous version unchanged, a form-coverage check,
   and an `E-FORM-001` fixture for the row or sibling the slice leaves out.
6. **The closure records the real numbers.** `ADR-0120` updates `STATUS.md`,
   `08_final_recommendation.md` §H, the per-slice docs and the corpus counts,
   and reruns the full gate set before the round is called complete.

## Consequences

- The definition set ends at x86-64 `0.78.0`, `rv64/0.6.0` and
  `aarch64/0.20.0` if all seven slices land; the planned total is 843 forms
  (x86 634, AArch64 185, RV64 24).
- The corpus grows to at least 128 positives and 607 negatives; the closure
  ADR records the exact counts.
- A plan that needs the new rows must pin the new definition version; older
  versions stay readable and keep their old byte behaviour.
- `EC-42` now states the ALU direction rule once instead of only for `sub`;
  the `and`/`or`/`xor`/`cmp` and memory rows cite it instead of restating the
  choice.
- The round does not add a selector, a relaxation pass or a second encoding
  path. The materializer remains a lookup/check/write kernel.

## Alternatives rejected

- **Level 2 ELF/COFF/Mach-O output (`fmp/0.2`).** Rejected for M6: the
  directive's §5.3 says Level 2 is not necessary for v0 success, and it would
  require freezing section order, symbol order, relocation order, alignment
  and container metadata. It stays a candidate for a later milestone, after
  the integer surface is less ragged.
- **Kernel conformance (an independent reference emitter and boundary sweep).**
  Rejected for M6: it strengthens the Route C claim but adds no user-visible
  capability, and the existing oracle plus `check_definition.py` already cover
  the bytes. It stays a candidate for a verification milestone.
- **Reopen `EC-16`/`EC-18` in this round.** Rejected: the standing decision is
  that they stay closed; reopening them needs its own scope decision, not a
  side effect of an ALU/load-store round.
- **Complete the memory shapes of the new ALU mnemonics now.** Rejected: each
  memory family adds `SIB`/displacement geometry and would triple the slice;
  `sub` is the single memory slice this round, and the rest stays deferred.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `0.74.0` has `add` 3, `sub` 6 and no other ALU mnemonic | form-id scan of `definitions/x86_64/0.74.0.json` | high |
| `0.74.0` has no `mov` row with an immediate slot | form-id and slot scan; `ADR-0093` review triggers | high |
| `0.5.0` has 15 forms and only `ld`/`sd` for memory | `definitions/rv64/0.5.0.json` | high |
| `0.18.0` has no `adr`, `mul` or `csel` | form-id scan of `definitions/aarch64/0.18.0.json` | high |
| 84 new rows, 843 total, 128 positives | arithmetic over the slice plan | medium — the exact counts are fixed per slice |
| No contract change is needed | the slices use existing slot kinds, placements and `pcrel_begin`; `03_fixup_model.md` §4 | high |
| The standing non-goals are closed | `ADR-0094`, `ADR-0111` | high |

## Review triggers

- A slice needs a new slot kind, a new fixup rule or a new artifact level; that
  is a format decision and needs its own ADR before the slice.
- A standing non-goal is proposed; it reopens this scope decision.
- A slice's measured row count differs from the plan; the difference is
  recorded in that slice's ADR, and the closure numbers follow the
  definitions, not the plan.
- The integer surface is still the chosen direction at the closure; otherwise
  the next milestone is a new scope ADR, not an eighth slice.
