# ADR-0128 revision log (fourteenth through thirty-second revision)

> Historical evidence only. This file is not a contract, is never a build input,
> and must not be read as current normative text. The normative entry is
> `docs/adr/0128-package-and-bundle-contract.md`; its body and `Settles` list are
> authoritative. These notes were moved out of the ADR opening by the
> twenty-ninth revision so that a new implementer reads current decisions first.

The notes below are preserved from the twenty-ninth revision. Where they
conflict with the current ADR, the current ADR wins; in particular the
thirty-second revision splits `H(T)` into published-snapshot validity, identity
record well-formedness and current-definition matching, so a retired definition
is not claimed to be recomputable from the current tree, and makes
`GateEvidenceValid(B,T,e)` a conjunct of `Q(B,T,e)`. The thirty-first revision
had made the gate layered with `C(T)`, `H(T)`, `Q(B,T,e)` and
`P(B,T,e,M) = Q(B,T,e) ∧ AuthorizedMerge(B,T,e,M)`. The thirtieth revision had
replaced the tree-only `P(T)` with `P(B,T,e,M)`, kept `R(T)` tree-only, separated
the publication audit's three claims, and restored H3 to consuming the nine-key
bundle's ownership facts.

## Revision notes

- Revision: thirty-second revision, 2026-11-20, after the retired-identity and
  gate-evidence audit. It replaces `HistoryAudit(T)` with
  `AllPublishedSnapshotsValid(T) ∧ AllIdentityRecordsWellFormed(T) ∧
  CurrentDefinitionsMatchRegistry(T)`: package snapshots are recomputed for every
  registered version, identity records are checked for shape and uniqueness, and
  only identities a current spec still publishes are compared with a build. A
  retired `definition_digest` is therefore not claimed to be recomputable; its
  immutability is carried by `PreservesPublished`, the protected merge path and
  Git history, without expanding the registry format. It also adds
  `GateEvidenceValid(B,T,e) = (e.base = B) ∧ (e.tree = Tree(T)) ∧
  TrustedGateRevision(e) ∧ AuthorizedGateRun(e)` as a conjunct of `Q`, and adds
  the retired-definition, retired-identity-rewrite and gate-evidence tests.

- Revision: thirty-first revision, 2026-11-20, after the publication-predicate
  sufficiency, V-P evidence and ordinary-PR critical-path audit. It splits the
  gate into `ArtifactClosed(T) = A(T) ∧ NoOrphan(T)` and
  `PublishedHistoryValid(T) = RegistryExists ∧ RegistryWellFormed ∧ HistoryAudit`;
  makes `H(T)` false for a development tree with no registry; defines pre-merge
  `Q(B,T,e) = C(T) ∧ R(T) ∧ H(T) ∧ PreservesPublished(B,T)` separately from the
  post-merge verdict `P(B,T,e,M) = Q(B,T,e) ∧ AuthorizedMerge(B,T,e,M)`; adds the
  no-registry, tampered-retired-version and orphan-sealed counterexamples; and
  adds the ordinary-PR total critical-path metric to H2c while forbidding a green
  CI run from standing in for V-P.

- Revision: thirtieth revision, 2026-11-20, after the sealed-format,
  publication-audit-scope, build-postcondition and publication-order audit. It
  fixes the publication verdict as
  `P(B,T,e,M) = A(T) ∧ R(T) ∧ PreservesPublished(B,T) ∧ AuthorizedMerge(B,T,e,M)`;
  makes `R(T)` a tree-only predicate and moves base-registry preservation to
  `PreservesPublished`; separates current snapshot consistency, pre-merge
  changed-path authorization and provenance trust; states that H3 consumes the
  `form_owners` map and package covers already inside the nine-key bundle and
  adds only plan-compatibility rules and a verification entry; restates that a
  successful build implies only `A_β(T_r)`; and orders publication as N4b
  (format/audit/synthetic tests), N5a (protected merge mechanism) and N5b (first
  real publication).

- Revision: twenty-eighth revision, 2026-11-20, after the per-bundle-artifact,
  registry-field, evidence-history, snapshot-name and merge-mode audit. It splits
  `A(T)` into per-bundle `A_β(T)` and the whole-tree conjunction, so
  `BuildSucceeded(r, β)` implies only `A_β(T_r)`; defines
  `R(T) = R_packages ∧ R_identities` from registry fields only; confines the
  evidence-only digest example to an unpublished candidate; extends §1.3 name
  and case-fold rules to every entry a snapshot covers; and requires `mode(M)`
  from a platform merge record. The next revision removes the profile-label
  equality condition, adds the two conformance modes, and narrows the compat
  claim.

- Revision: twenty-seventh revision, 2026-11-20, after the predicate-conflict,
  acceptance-cycle, gate-provenance, H3-scope and PR-description audit. It splits
  artifact pairing, registry completeness and publication readiness into `A(T)`,
  `R(T)` and `P(T)`; separates the acceptance change (H2-0) from H2a; requires
  the verdict to record the provenance of the gate logic; and scopes the H3
  bundle entry's guarantee to its own callers. The next revision splits `A` per
  bundle and tightens `R`.

- Revision: twenty-sixth revision, 2026-11-19, after the bridging-API,
  unpublished-snapshot, evidence-label and predicate audit. It moves the legacy
  bridge out of the bundle type into
  `fmp_definition::compat::as_legacy_definition`, gives it a lifecycle equal to
  the H1 `bind` and no reverse conversion, and renames the bundle type to
  `CheckedBundle` so its name claims only structure and closure checks. It
  requires a published-directory audit to reject every unreferenced non-regular
  entry instead of skipping it, reconciles the evidence and risk rows with the
  §8.5 phase split, and separates `BuildSucceeded(r)` from
  `ArtifactsConsistent(T)` — the latter is split again by the twenty-eighth
  revision into `A_β(T)` and `A(T)`.

- Revision: twenty-fifth revision, 2026-11-19, after the empty-domain,
  platform-evidence and scaling-summary audit. It scopes the `empty-form-domain`
  rejection to slots that must encode a numeric value, so an `operand_value` slot
  that stays reachable through a fixup or a symbol is not rejected; it records the
  2026-11-19 branch-protection observations (403, empty ruleset list) as missing
  evidence rather than as proof that no protection exists; and it keeps the
  author-layer metric and the publication-channel scaling metric separate.

- Revision: twenty-fourth revision, 2026-11-19, after the requirement-
  completeness, first-publication and summary-consistency audit. The H3
  target-subset rule is disambiguated: the owner package's declared cover is
  mandatory (`E_package(owner(form(i))) ⊆ E_plan` for every selected
  instruction), and a per-form requirement adds a conjunct but never replaces
  the conservative cover until a versioned format proves the requirement
  complete. First V-P activation re-verifies and registers every spec selected
  at HEAD in one first-publication candidate, not only the initial x86 slice.
  The normative summary no longer carries the superseded sealed-companion rule,
  and the changed-path example now separates prevention before merge from
  detection after merge.
- Prior revision: twenty-third revision, 2026-11-19, after the scheduling and
  frozen-format audit. Several decisions change shape, not wording.
  First, H2 is judged by **two separate acceptance verdicts**: an author-layer
  verdict that needs no external platform fact, and a publication-channel verdict
  that carries the hardened reader, the registry, the merge-freshness proof and
  the history audit. The author layer may proceed while the publication channel's
  prerequisites are still open; no artifact may be called published, immutable or
  trusted until the publication verdict passes.
  Second, `monasm-bundle/0.1` stops being a companion that omits facts its own
  digest covers. Because nothing has shipped, the format is fixed **once**, as a
  self-contained artifact: it carries the bundle-level `target`, the declared
  per-package cover, and a complete `form_owners` map, so `bundle_digest` is
  recomputable from the file and H3 consumes these facts instead of introducing
  another bundle version. The round-21 companion rule and the round-22 seven-key
  set are superseded here, explicitly, rather than left as two descriptions a
  reader has to arbitrate.
  The registry entry also gains a `snapshot_digest` over every regular file in the
  published version directory, so published evidence, cases and `NOTICE` are no
  longer protected by the merge gate alone; the remaining trust boundary is stated
  in §8.4.
  Finally, the boundary-positive rule handles degenerate legal domains by
  cardinality (§9.1), so a one- or two-element `D_form` no longer demands an
  interior value that does not exist.
- Prior revision: twenty-second revision, 2026-11-18, after the key-set, publication-
  gate, registry-coordination and builder-provenance audit: `monasm-bundle/0.1`
  had one closed key set of seven keys, with `packages` as the package list and
  **no** bundle-level `target` (superseded by this revision's self-contained
  nine-key form), and the text that called the
  list `sources` or said the sealed bundle carries the spec's `target` is
  removed rather than left for a reader to arbitrate; the publication verdict's N5
  node does not close on a green CI run but only on a recorded merge mechanism
  plus an executed stale-CI counterexample, and otherwise stops at that gate; independent package
  authoring and independent publishing are separate claims, with H2 promising
  correct serialized publication rather than coordination-free parallel
  publishing; and `builder` is documented as an informational provenance record
  whose change can pass `--all --check`, not as proof that the declared
  implementation produced the bundle.
- Prior revision: twenty-first revision, 2026-11-18 (superseded by this
  revision's self-contained sealed form), after the sealed-bundle,
  registry-scale and N1-prerequisite audit: `monasm-bundle/0.1` was a companion
  artifact of its lock, not a self-verifying snapshot — its `bundle_digest`
  preimage includes the bundle-level `target` (with `profile_id`) that the sealed
  file does not store, so a consumer recomputes the value from the lock plus the
  sealed bytes and never trusts the embedded claim, and H3 must verify the pair
  or introduce a versioned sealed format; the single-file registry keeps its
  full-history audit as a measured `O(N_published)` cost with a 1,000-version
  budget and a recorded threshold that triggers a later ADR, not as a proven
  scalability property; and the three-platform N1 PoC is a standalone
  prerequisite deliverable with recorded platform, toolchain, API,
  fault-injection and per-case results before any builder code.
- Prior revision: twentieth revision, 2026-11-18, after the target-subset and
  merge-mechanics audit: H3 may accept a subset plan only after proving every
  selected instruction against the plan target
  (`E_owner(form(i)) ⊆ E_plan`), which needs a versioned bundle owner/cover map
  or another frozen source — the then-current `monasm-bundle/0.1` shape could
  not supply it, and a form
  without a proof is rejected rather than read as needing nothing; a publication
  verdict is keyed on the base commit SHA and the tested candidate **tree** SHA
  plus the merge mode, not on a pair of commit SHAs, so required up-to-date
  checks alone are not accepted as tree-identity proof; and the HE-1 overview's
  package/bundle examples are aligned with this ADR.
- Prior revision: nineteenth revision, 2026-11-18, after the merge-timing and
  version-boundary audit: a publication verdict authorizes only the
  `(B_checked, H_checked)` pair it read, so an accepted publication requires
  `B_checked = B_merge` and `H_checked = H_merge`, enforced by a merge queue or
  strict up-to-date required checks and proved through the platform API;
  `monasm-package/0.1` rejects non-empty `exports.types`/`exports.profiles`
  permanently, with their semantics reserved to an explicit later package format;
  the input order is fixed as lexical path, no-follow open, handle-level type
  check, same-handle size hint, bounded read, parse; and a build omits the legacy
  snapshot rather than writing one above its own 16 MiB read budget.
- Prior revision: eighteenth revision, 2026-11-18, after the resource and artifact
  lifecycle audit: only a regular file is accepted at an opened leaf — FIFO,
  socket and device nodes are rejected as `not-a-regular-file` on the opened
  handle, and the POSIX input open is non-blocking until the type is known; and a
  retired bundle's lock, sealed bundle and legacy snapshot leave the tree with
  its last spec, with `--all --check` rejecting an orphan, so no unselected
  release artifact keeps an undefined status.
- Prior revision: seventeenth revision, 2026-11-18, after the path-injectivity and
  publication-authority audit: the package directory segment is the **full**
  `package_id`, so the path mapping is injective and two owners whose IDs share a
  last segment can coexist at one version; "already published" is decided at the
  **target-branch tip `B`**, not the merge base, with
  `Published(B) ⊆ Published(H)` and equal tree bytes for every published path;
  a non-empty `dependencies` array is a closed three-key object with a fixed
  digest vector; and `verify --package` is stated as executing
  `fmp_model::definition::read` while never executing a case's
  `plan::read`/`bind`/`materialize`.
- Prior revision: sixteenth revision, 2026-11-18, after the migration-equivalence
  and boundary-domain audit: `legacy_source` target equality is `TargetEq` —
  every field strictly equal except `enabled_extensions`, which is compared as a
  set — so a canonically ordered package can migrate a frozen legacy document
  whose array is spelled differently; and boundary positives are taken from the
  final legal domain `D_form` (range, alignment and exclusions applied), never
  from a raw endpoint that the form excludes.
- Prior revision: fifteenth revision, 2026-11-18, separated the static stage
  declaration check from the executed first-rejecting-stage proof, so reports
  record both statuses separately, and restated the register domain as
  `D_reg = ([0, 2^w−1] ∩ [0, 2^64−1]) \ E` so slots wider than 64 bits keep the
  H1-verified encoding capability and are tested without an unrepresentable
  `2^w`.
- Prior revision: fourteenth revision, 2026-11-17, required a committed legacy
  snapshot to be byte-identical to the canonical sealed definition
  (`legacy-snapshot-mismatch`) while entering no digest and remaining optional,
  removed the inexpressible definition-identity case, required a versioned build
  rule as well as a new plan protocol to lift `h2-exact-target`, and decided
  base-registry containment before head-side `package.json` discovery.
- Prior revisions: the thirteenth (plan-scope `stage: "read"` and the
  first-rejecting-stage rule, interrupted-write detectability, output parents
  trusted but no-follow-checked, bounded lock/sealed read, bundle-local
  `profile_id`), the twelfth (first-publication order, derived legacy cache,
  canonical set spelling, counted closure budget, the `E_form = ∅` acceptance
  caveat), the eleventh (representability-scoped boundary evidence, the
  plan×definition matrix, a single-modifier `mutates`, one-segment paths,
  entry-replacement in the N1 gate) and the tenth and earlier (package-root
  collisions, exact on-disk entry names, the versioned `h2-exact-target` lift,
  ASCII identifier/path grammar, single loaded package value, cycle-free first
  publication, conservative declared cover, value-defined case diff, legacy name
  reservation, the publication audit's whole-directory coverage without a
  provenance claim, open-time no-follow) remain in force.
