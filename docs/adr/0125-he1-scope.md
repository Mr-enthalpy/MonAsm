# ADR-0125: HE-1 is the next scope, and the v0 freeze keeps its full force

- Status: accepted
- Date: 2026-11-10
- Settles: what the next scope is, which existing rules it replaces, and what it
  deliberately leaves untouched
- Supersedes: none
- Superseded by: none
- Revises: `AGENTS.md` (repository map, definition of done, and the reading of
  "sync the central table"); `docs/STATUS.md` (next action); adopts
  `docs/architecture/he1-horizontal-extension.md` as the HE-1 design basis and as
  the registry document for the `HE-AC` and `HE-T` ID families; extends
  `tools/check_ids.py` with those two families
- Keeps in force: `ADR-0095` and `ADR-0123` for `fmp/0.1`; `ADR-0124` until
  `ADR-0126` adds the baseline job and `ADR-0130` revises the rest of the gate set

## Context

`docs/STATUS.md` says the v0 scope is frozen and that any further widening needs a
new scope ADR. This is that ADR, and it changes the *kind* of widening, not the
frozen surface.

The reason is not "more instructions are missing". H0 measured four places where a
new instruction family costs a change outside its own data, at `d0082f9`:

1. **A new ISA name is a code change.** `check_form_id` matches
   `"x86" | "aarch64" | "riscv"` and separately demands the x86 encoding-family
   segment (`fmp-model/src/definition.rs:714-756`).
2. **Loading is whole-tree.** `Registry::load_dir` recurses over every `*.json`
   under a directory and fails the entire load on one unusable file
   (`definition.rs:788-803`, `collect_json` at 829-851). A file no plan selects
   can still decide whether that plan materializes.
3. **A form row is a central-document edit.** `tools/check_definition.py`
   rebuilds a five-column row per form from `07_definition_format.md` §8 and
   requires the table set to equal the definition set exactly
   (`check_doc_table`: `set(rows) != set(expected)` fails), then requires every
   form of the newest table to be named by a positive fixture
   (`check_form_coverage`). Adding one row is therefore a JSON change plus a
   central table edit plus a fixture.
4. **Identity and execution share a mutable object.** `Definition` exposes
   `pub document`, `pub forms` and `pub digest` and derives `Clone`
   (`definition.rs:21-30`); `Definition`'s `digest` is a stored string that is not
   derived from `forms`. H0 pins the consequence with two tests: templates can be
   replaced under an unchanged digest, and `fingerprint` is computed from
   `plan.document` rather than the parsed operands
   (`tests/he1_identity_characterization.rs`).

The design document `docs/architecture/he1-horizontal-extension.md` (v0.1,
checked against `d0082f9f2d3da2786d8d1c0467d2793369ec9090`, same as this HEAD)
proposes the target shape: independent target packages, an offline definition
builder, an immutable definition bundle, a target-agnostic validation/encoding
core, package-level conformance tests, and fixup profiles as the second extension
boundary.

## Decision

1. **HE-1 is the scope.** The plan is H0 baseline → H1 identity closure → H2
   package author layer → H3 protocol and generic loading → H4 profiles and
   package conformance → H5 parallel extension drill. `HE-AC-01`–`HE-AC-12`
   (design §3) are the stop condition; `HE-T01`–`HE-T20` (design §14) are the
   minimum evidence. When all of them hold, the round ends; it does not roll into
   coverage work.
2. **Three extension classes, with three different change budgets.**
   - *Ordinary extension* — expressible with the primitives the core already
     executes (fixed templates, contiguous/scattered placements, inversion,
     ranges, alignment, exclusion sets, extension requirements, the existing
     absolute/PC-relative/page/hi-lo transforms). It may touch only
     `packages/<target>/<owned-package>/**`.
   - *Shared target asset change* — a register type, feature definition or target
     profile shared by packages. It touches the shared package and gets the
     reverse-dependency closure.
   - *Capability addition* — a deterministic field transformation the core cannot
     express. It needs a capability proposal, a core change and a full regression.
   The promise is class 1 only. It is *not* a promise that no future ISA ever
   needs a new primitive.
3. **The v0 freeze is untouched.** `docs/fmp-v0/**`, `definitions/**`,
   `fixtures/**`, `schema/fmp-v0.schema.json` and every `fmp/0.1` meaning keep
   their current status. `ADR-0095` ("frozen for the v0 scope") and `ADR-0123`
   stay in force for v0 and are not superseded. New surface is additive and
   versioned separately: `fmp/0.2` (`ADR-0129`), `monasm-package/0.1` and
   `monasm-bundle/0.1` (`ADR-0128`). Historical definition files are never
   rewritten in place.
4. **The centre-document rule changes only for the package path.** From H2 on, a
   package's forms, coverage and status are derived from package metadata and are
   not hand-copied into `STATUS.md`, `README.md`, `07_definition_format.md` §8, a
   global form table or a global ID counter. The legacy corpus keeps its
   hand-checked counts (`128` positives, `619` negatives, the `611`/`8` phase
   split) because those counts are evidence for `fmp/0.1`. No new rule may make a
   package contributor edit a central table, and no phase may re-centralize the
   package path on the grounds that the old rule demanded it.
5. **Reversing an accepted ADR still needs an ADR.** A package-local decision slug
   may add rows inside a family an existing ADR admitted; it may not reopen a
   family an ADR closed (`ADR-0025`'s `b`/`h` widths, `ADR-0115`'s `movabs`,
   `ADR-0094`'s absent families). Such a slice needs its own ADR first, even if it
   ships as a package.
6. **The legacy path stays, without becoming a bypass.** Every old *entry point*
   keeps working through a version-pinned adapter; no adapter may skip the
   structural, identity or capability checks the new path enforces (`ADR-0127`).
   "Entry point" here means the published surface: the `fmp/0.1` document format,
   the artifact envelope and the `fmp` CLI's observable behaviour (arguments,
   exit codes, stderr diagnostics). It does **not** promise Rust library source
   compatibility: `fmp-materialize`'s function signatures may change, and the H1
   plan states that explicitly. A caller outside this repository that links the
   crate has to migrate; a script that runs `fmp materialize` does not.
7. **Explicit non-goals for this round**: complete ISA coverage, a semantic IR,
   instruction selection, layout solving, ABI lowering, a full object-file
   backend, a dynamic plugin platform, a macro/expression language, a real fourth
   ISA, and reopening the assembler survey or the language choice. The synthetic
   target probe proves the absence of an ISA allowlist; it is not hardware
   support.

## Consequences

- H0 records the baseline that every later phase is compared against:
  `research/he1/compatibility-results.json`, `payload_root`
  `sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`
  over 128 positive artifacts, 104 definition documents, `122/128` oracle
  re-derivations and six `manual-derivation` skips. `ADR-0126` splits the digest:
  the *payload* root above is the gate, and
  `sha256:dfd08fee9844058492138b23448073ec47d8eda42383e3f1b3e567db86a86fef` —
  the value first recorded here — is now the *envelope* root of the frozen
  `research/he1/compatibility-h0-envelope.json`.
- `HE-AC` and `HE-T` become machine-checked ID families: their single declaration
  site is the design document's §3 and §14 tables, and `check_ids.py` now requires
  every reference to resolve to one of those rows.
- `AGENTS.md` gains the new directories in its map and states that the central
  table clause applies to the legacy corpus only; its eight hard rules and the
  directive are unchanged.
- The old corpus remains the compatibility oracle: a package that re-homes an
  existing family must reproduce the legacy bytes exactly before it is accepted.
- `ADR-0124`'s review trigger is honoured, not bypassed: `ADR-0126` adds the
  baseline job, and adding the package jobs to CI happens in `ADR-0130`.
- A capability gap is reported as `unsupported-capability` with a measured
  counterexample. Raw-byte escape hatches and "ask LLVM at runtime" are excluded
  by `ADR-0001` and stay excluded.

## Alternatives rejected

- **Continue coverage rounds without the base.** Rejected: the four measured
  concentration points do not shrink with more rows; each new family pays them
  again.
- **Split code into more crates and call it done.** Rejected by the design's own
  criterion: crate count is not evidence. H5 measures merge independence, not
  directory counts.
- **Rewrite the materializer as a general constraint solver or expression
  engine.** Rejected: the executor is not the bottleneck, and a rule language
  would move implicit decisions back into the core.
- **Migrate all 104 definition documents at once.** Rejected: no regression
  isolation, and it contradicts the small-PR rule in the design §13.1.
- **Keep hand-syncing the central tables.** Rejected: that is the collaboration
  cost this ADR removes, and it is precisely the "old rule" the round is allowed
  to replace — through this ADR, not silently.
- **Make `fmp/0.2` the only format and convert v0 plans.** Rejected: it would
  change old payload identity and violate the compatibility class table in the
  design §15.1.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| HEAD is the design's baseline commit | `git rev-parse HEAD` = `d0082f9f2d3da2786d8d1c0467d2793369ec9090` | high |
| The design's seven source citations resolve at that commit | read `definition.rs:21-30`, `714-756`, `788-803`; `fmp-materialize/src/lib.rs:557-633`, `919-936`; `schema/fmp-v0.schema.json:48-52`; `check_definition.py` `check_doc_table`/`check_form_coverage` | high |
| A loaded definition can be re-encoded under its original digest | `a_loaded_definition_can_be_re_encoded_under_its_original_digest` passes on the unmodified code | high |
| Fingerprint does not cover parsed operands | `a_parsed_operand_can_change_under_a_stable_fingerprint` passes | high |
| One unselected `*.json` breaks the whole load | `an_unselected_file_in_the_definition_directory_breaks_loading` passes | high |
| A synthetic namespace is rejected by the loader | `a_synthetic_namespace_is_rejected_by_the_loader` passes | high |
| Deep JSON ends the process | `tools/he1_baseline.py` probe: `fmp materialize` on 20 000 nested arrays exits `3221225725` (`0xC00000FD`, stack overflow) | high (measured, Windows host only) |
| Legacy payloads are stable | `research/he1/compatibility-results.json`, 128 artifacts, `payload_root` re-checked identical (`ADR-0126`) | high |
| The corpus counts are 128/619 with a 611/8 phase split | `tools/he1_baseline.py` counts; the split is asserted by `planner_api.rs` and green | high |
| Legacy behaviour is identical on other hosts | CI `42681104791` is green for the three jobs, but H0 did not re-run it | unverified in this round |

## Review triggers

- A phase needs to change a `fmp/0.1` meaning, a `definitions/**` file or a legacy
  payload: stop, new ADR, compatibility class first.
- A package needs a primitive the core does not execute: capability proposal; do
  not add a name-based branch.
- Someone proposes hand-editing a central table to "stay consistent" with the old
  rule: this ADR is the answer.
- HE-1 acceptance passes: stop. Further coverage needs its own scope ADR and its
  own package task, not a continuation of this one.
