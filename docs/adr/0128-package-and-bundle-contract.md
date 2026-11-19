# ADR-0128: the package and bundle contract, and the H2 definition builder

- Status: proposed
- Date: 2026-11-14
- Review: this is a proposal, not a frozen decision. It stays `proposed` until
  the H2 planning PR is reviewed and merged; `accepted` is written only after
  that review, and H2a does not start before it.
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
- Settles: the `monasm-package/0.1`, `monasm-bundle-spec/0.1`,
  `monasm-lock/0.1`, `monasm-bundle/0.1` and `monasm-published/0.1` formats;
  immutable published package version directories and their append-only
  registry, including global `(package_id, version)` identity binding, the
  permanent `(namespace, version)` → `definition_digest` history, the movable
  `bundle_id` release line, and the separate publication-history audit; the
  self-contained nine-key `monasm-bundle/0.1` that recomputes its own definition
  and `bundle_digest` from the bytes it carries, and the lock pairing that
  separately verifies source paths, release evidence and the builder record —
  H3 needs no new sealed format for self-verification; the declared-versus-derived
  capability set;
  the release-shaped digest vector; the value-defined case diff; the digest
  layering and its byte-level preimages; the reservation of every frozen legacy
  definition name; the form/package/bundle extension inclusion and the per-package
  `read`; package target self-description and migration provenance, including
  legacy target consistency; the standalone definition identity used by
  `verify --package`; the
  mandatory package case and evidence gate with `bind`-only form-scope mutation
  and complete diagnostic sets, with static declaration validation separate from
  the executed first-rejecting-stage proof; the representable register domain for
  a field wider than 64 bits; exact Level 0/Level 1 machine-output projections;
  portable identifier, path-segment and artifact-filename lexical rules; the
  package-root and repository-relative domains of path collision; exact on-disk
  entry-name matching for every opened segment; the regular-file-only open with
  its handle-level type check; the derived-artifact lifecycle that retires a
  bundle's lock, sealed bundle and legacy snapshot with its last spec; the final
  legal operand domain
  (`D_form`, with exclusions and alignment applied) for boundary evidence; the
  plan×definition target-compatibility
  matrix; the single loaded-package value shared by digest, comparison, `read`
  and merge; the cycle-free first-publication order (build success, then the
  registry append, then both `--check`s, then commit) and the all-or-nothing
  first candidate that registers every spec selected at HEAD, in-memory output
  validation and the derived legacy cache with its equality-only bridge gate;
  the one canonical spelling of
  extension and capability arrays, with migration equivalence `TargetEq`
  comparing `enabled_extensions` as a set and every other target field strictly;
  the counted closure byte budget; package
  target covers versus bundle target selection; the H3 condition for accepting a
  subset target (a versioned build rule, a plan protocol, and a per-instruction
  owner/requirement source that always checks the owner's declared cover
  `E_package(owner(form(i))) ⊆ E_plan` and adds a per-form requirement only when
  its format version proves that requirement complete, with default rejection
  when the proof is absent);
  the injective full-`package_id` directory mapping and target-tip
  publication authority (`Published(B) ⊆ Published(H)` with tree-byte equality);
  the merge-freshness rule that a verdict is keyed on the base commit SHA, the
  tested candidate tree SHA and the merge mode, and must be re-established when
  any of them moves; the permanent
  `monasm-package/0.1` rejection of non-empty `exports.types`/`exports.profiles`
  with their semantics reserved to an explicit later package format; the ordered
  input pipeline (lexical path, no-follow open, handle type check, same-handle
  size hint, bounded read, parse); the rule that a build omits a legacy snapshot
  above its own read budget instead of writing an unreadable one;
  the closed non-empty dependency object and its fixed digest vector;
  base-registry-first changed-path containment; package/form
  ISA-family consistency; package ownership and conflict rules; which legacy
  definition version a re-homed form is compared against; transitive dependency
  closure and release-evidence status; the builder's error and exit behaviour;
  and the boundary between H2 and H3/H4
- Supersedes: none
- Superseded by: none
- Revises: `docs/architecture/he1-h2-plan.md` (adopts `H2-D1`–`H2-D12` with the
  measured corrections in Context and decisions 13 and 14)
- Confirms: the `packages/` and `bundles/` rows of `AGENTS.md`; they become real
  inputs from H2, still not runtime discovery paths
- Keeps in force: `ADR-0125` decisions 3 and 4 (a package author layer, a
  derived package count, and the centre-document rule changing only for the
  package path); `ADR-0127` for `Definition`, `bind`, `ValidatedPlan` and
  `MaterializationFailure`; `ADR-0126` for the payload/definition baseline;
  `fmp/0.1`, `definitions/`, `fixtures/`, `schema/` and `docs/fmp-v0/` stay
  frozen

## Context

H2's goal is that adding an instruction family lands in
`packages/<target>/<package_id>/<version>/**` instead of a hand-edited full
definition document (`ADR-0125` decision 1). The repository has no builder, no
package manifest and no explicit closure today: `Registry::load_dir` recursively
reads every JSON file under a directory (`fmp-model/src/definition.rs`), so
"which definitions are available" is decided by directory contents, not by an
explicit choice.

Three constraints shape the contract:

1. **The execution boundary does not move in H2.** `bind(Plan,
   Arc<Definition>)` stays the admission entry, `ValidatedPlan` stays the only
   input to `materialize`, and `Definition` stays closed (`ADR-0127`). H3 is the
   round that makes a bundle the binding input. H2 only adds a development-time
   builder and a bridge back to `Arc<Definition>`.
2. **The builder must not become a second definition authority.** Form rows,
   placements, templates, ranges and fixups are still checked by
   `fmp_model::definition::read`. The builder checks manifests, paths, the
   closure, ownership and canonicalisation; it does not re-implement the
   definition checker.
3. **Selection must not be directory discovery.** The design document (§4, §13)
   requires an explicit `BundleSpec` plus a dependency closure, and H3 requires
   that a damaged unselected package cannot change a frozen bundle. A builder
   that scans `packages/**` to resolve IDs violates that before H3 even starts.

Two measured facts then force the H2 slice pins, and they are the reason this
ADR cannot simply say "copy the newest row":

- **x86 `mov` rows changed format.** `definitions/x86_64/0.1.0.json` is
  `fmp-def/0.1`; `0.78.0.json` is `fmp-def/0.2`. For
  `x86:mov/rm-r64/legacy` and `x86:mov/r64-rm/legacy`, the `0.78.0` rows add
  `requires_extensions: []` and two REX placements per row: `{bit_offset:0,
  width:1}` for the `rm64` role and `{bit_offset:2, width:1}` for the `r64`
  role, in addition to the low-register placements. The bytes for `X86-P1` still
  agree because that fixture uses registers 0 and 3, but the rows are not equal.
  Treating `0.78.0` as the source would be a definition-semantics drift, which
  is exactly what the H2 exit criterion forbids.
- **rv64 target sets changed.** `definitions/rv64/0.1.0.json` declares
  `enabled_extensions: ["rv64i"]`; `0.6.0.json` declares `["rv64i","rv64c"]`.
  The `RV-P1`/`RV-P2` plans declare `["rv64i"]`. `fmp-def/0.1` compares the
  extension sets for equality (`fmp-validate/src/lib.rs`, `check_target`), so a
  bundle built from `0.6.0` would be rejected at `bind` with
  `E-TARGET-001` before any byte comparison.

aarch64 is the benign case, with one correction to the earlier draft: the
`x64-x64-x64-lsl0` and `x64-imm12-lsl0` rows are byte-identical in `0.1.0`,
`0.2.0` and `0.20.0`; `aarch64:add/x64-imm12-lsl12` does not exist in `0.1.0`
and is byte-identical in `0.2.0` and `0.20.0`. Every version declares
`enabled_extensions: []`, so the pinned `0.20.0` rows are the
fixture-verified rows.

## Decision

### 1. A package is a directory with one closed manifest

`packages/<target>/<package_id>/<version>/package.json` is the only entry point.
The target directory is a path component (`x86_64`, `aarch64`, `rv64`), not a
form-ID prefix; its lexical form and the injective mapping from the full
`package_id` to the `<package_id>` component are §1.3. The `<version>` component
is exactly the manifest's
`version` string; the spec's `packages[].path` and `packages[].version` must
agree with that component. A mismatch is `path-version-mismatch` (exit 1). The
manifest is `monasm-package/0.1` and is a closed object:

```json
{
  "package_format": "monasm-package/0.1",
  "package_id": "monasm.x86.mov-register",
  "version": "0.1.0",
  "target_profile": "monasm.target.x86_64",
  "definition_format": "fmp-def/0.1",
  "target_identity": {
    "isa_family": "x86",
    "isa_variant": "x86-64",
    "execution_mode": "64",
    "enabled_extensions": [],
    "byte_order": "little",
    "address_width": 64
  },
  "legacy_source": { "isa": "x86_64", "version": "0.1.0" },
  "requires_capabilities": ["field-placement/v1"],
  "dependencies": [],
  "exports": {
    "forms": [
      { "id": "x86:mov/r64-rm/legacy", "path": "forms/mov-r64-rm.json" },
      { "id": "x86:mov/rm-r64/legacy", "path": "forms/mov-rm-r64.json" }
    ],
    "types": [],
    "profiles": []
  }
}
```

| Key | Requirement |
|---|---|
| `package_format`, `package_id`, `version`, `target_profile`, `definition_format`, `target_identity`, `requires_capabilities`, `dependencies`, `exports.forms` | required |
| `legacy_source` | optional; migration provenance only |
| `exports.types`, `exports.profiles` | optional; reserved asset declarations, which must stay empty under `monasm-package/0.1` |

| Field | Counterexample when it is missing or unchecked |
|---|---|
| `package_format` | An older builder reads a newer manifest, ignores the field that changed the meaning, and builds a bundle the author did not describe. |
| `package_id` | Ownership has no owner to name; two packages cannot be distinguished in a lock. |
| `version` | The same package ID with changed content is indistinguishable from the old one; a lock cannot say which was selected. |
| `target_profile` | An x86 package is merged into an aarch64 target because the spec and the package never compared their target facts. |
| `definition_format` | The builder merges rows with a format the author did not name, so a `fmp-def/0.2` row is read by a `0.1` reader (or the reverse) and the rejection names the wrong fact. |
| `target_identity` | A package declares no target facts, so a new package has no way to be checked without a legacy file; the spec becomes the only target authority and a package can be merged into a mismatched target. |
| `legacy_source` | A re-homed package loses the reference for the row-equality test, and a copied row can claim a different execution target; "the newest file" silently retargets the comparison and hides a semantic change. |
| `requires_capabilities` | A package that needs a primitive the core does not execute is built as if it needed nothing; the builder cannot reject it before the snapshot is verified. A declared set that omits a capability the rows use, or lists one they do not, is `capability-mismatch` (§1.2). |
| `dependencies` | A transitive package has to be discovered by scanning, which is the behaviour H3 forbids. |
| `exports.forms` | A file in the package can be executed without being declared, or an undeclared file is silently included. |
| `exports.forms[].id` | The file's own `form_id` can differ from the declaration; swapping two files changes ownership without changing the manifest. |
| `exports.forms[].path` | The manifest cannot say which file holds the row, so the builder must guess or scan. |
| `exports.types`, `exports.profiles` | A package can declare a type/profile asset that neither the format nor the digest records; H4 cannot add semantics without changing the closed key set. |

Unknown and duplicate keys are rejected (`INV-07`). A missing key is rejected
when it is required and is legal only for the optional keys in the table above.
`exports.forms` is sorted strictly by `id`, and `dependencies` strictly by
`(package_id, version)`; a reordering is a different document and is rejected
rather than silently canonicalised. The two flat set fields,
`requires_capabilities` and `target_identity.enabled_extensions`, have exactly
one legal spelling: a strictly increasing, duplicate-free array under the
code-point order of its element strings — `["rv64c","rv64i"]`, never
`["rv64i","rv64c"]`; `["field-placement/v1"]`, never that string twice. Set
membership decides the capability and target relations, but a reversed or
duplicated array is a **format rejection** before any relation is evaluated:
`capability-lexical` for `requires_capabilities`, `extension-lexical` for
`enabled_extensions`, both exit 1. Without that rule two documents with the same
set would have different `source_package_digest` values and different identities,
so "the same extension set" would have no unique legal representation and a
comparison could not tell a spelling change from a semantic one. The rule is new
for package and spec inputs, so it does **not** re-spell a frozen legacy document:
`definitions/rv64/0.6.0.json` keeps its published `["rv64i","rv64c"]` bytes, and
a consumer compares extension arrays as sets (`check_target` collects both sides
into a `BTreeSet`); migration equivalence uses the same set comparison through
`TargetEq` (§1.1). Each `forms/*.json` holds exactly one form object; its
`form_id` must equal the declared `id`.

**A non-empty `dependencies` entry is a closed object.** Each element has
exactly `package_id`, `version` and `source_package_digest`; all three are
required, unknown keys and duplicate keys are rejected (`INV-07`), and an object
with a missing or extra key is a format rejection rather than an ignorable
annotation. `package_id` is the dotted identifier of §1.3, `version` is the
package version grammar of §1, and `source_package_digest` is the literal
`sha256:<64 lowercase hex>` text of §7.0. The digest is the dependency's
`source_package_digest`, not a definition or bundle digest: it names the exact
source snapshot the dependent package was written against. An entry that resolves
to a selected package must match all three values exactly; a nearest-version,
`latest` or range match is not a legal resolution (§4). `dependencies: []` is the
only empty form and `{}` is never legal. Counterexample if the shape were open and
advisory: an entry with `{"package_id": "monasm.x86.base", "version": "0.1.0"}`
would omit the digest, so after `monasm.x86.base` re-releases at the same version
with different bytes the dependent package would still verify against a snapshot
it never saw; a spelling such as `{"package_id": ..., "version": ..., "digest":
...}` would also enter `source_package_digest` while no reader knew which key the
closure check must trust.

`exports.forms` must be **non-empty**. `fmp_model::definition::read` rejects an
empty `forms` array (`fmp-model/src/definition.rs`, `bind_forms`), and
`monasm-package/0.1` rejects non-empty `exports.types`/`exports.profiles`
(the reserved-asset rule below), so a zero-form package has no definition the
H2 builder can produce or
verify. An empty `exports.forms` is `empty-package` (exit 1), not a legal
degenerate package. A type-only or profile-only package needs a later package
format and an explicit reader path; H2 does not pretend such an object is
buildable, and `oracle.status: "not-applicable"` is therefore rejected in a
release-ready H2 package (§7.1). `exports.types` and
`exports.profiles`, when written, use the same `{id, path}` shape and are sorted
strictly by `id`; each file holds exactly one type or profile object, whose own
`type_id`/`profile_id` must equal the declared `id`. They are reserved syntax:
H2 rejects a non-empty list as `unsupported-asset`. An absent optional list and an empty list are different
manifests with different source digests, but both declare zero assets; the lock
pins the spelling that was released.

#### 1.1 A published package version is an immutable source snapshot

Holding a `source_package_digest` in the spec is not enough if the directory it
names can change afterwards. The layout therefore makes the version component
the immutability boundary:

- a `packages/<target>/<package_id>/<version>/` directory is a **source snapshot**;
- a version is **published** when its entry exists in the registry of a merged
  commit. The publisher adds that entry in the same PR that first selects the
  version in a `bundles/specs/*.json`; the registry entry, not the current spec
  set, is the permanent record. The PR that first adds the entry may still create
  and adjust the candidate directory: the new entry is validated against that
  PR's final head snapshot, and only the merged snapshot is immutable;
- after publication, no file under that directory may be added, modified,
  renamed or deleted — including `README`, `NOTICE`, `evidence/` and
  `tests/cases.json`. A change is `published-package-modified` (exit 1).
  Publication is read from the registry at the **target-branch tip `B`**, not
  from the merge base, so a version published on the target branch after this
  branch forked is frozen here too (§8.1);
- new forms, fixed encodings or new evidence require a new sibling directory
  `packages/<target>/<package_id>/<new-version>/`, with its own manifest version and
  digest. The old directory stays byte-for-byte in place: while its selecting
  spec remains in the head tree, `verify --all --check` still rebuilds the old
  lock and sealed bundle;
- updating a spec to select the new version, adding the new registry entry and
  regenerating its lock/sealed bundle is a separate publisher decision. An
  ordinary package change does not edit any spec, lock, sealed bundle or
  registry entry;
- removing the last spec for a `bundle_id` retires its release. The same PR
  removes that bundle's derived artifacts — `bundles/locks/<bundle_id>.lock.json`,
  `bundles/sealed/<bundle_id>.bundle.json` and `bundles/legacy/<bundle_id>/` —
  while the package snapshot and its registry entry stay. The retired artifacts
  remain replayable at the commit that published them; H2 adds no archive
  format, because the permanent record of a release is the immutable package
  snapshot plus the registry entry, not a tree-resident sealed bundle that no
  spec selects (§8.4).

The CI changed-path gate first asks the **base published registry** — the
registry at the **target-branch tip `B`** (§8.3) — whether
the changed path lies inside an already published version directory; if so, any
changed file there fails the gate before `verify --package` runs (§8.1), and a
`package.json` added deeper in the head tree cannot reclassify it. Only a change
outside every base-registered directory is resolved to its nearest head
`package.json`. A version whose entry exists only
in the head registry is a **first publication**: it is a candidate during this PR
and is validated against the final snapshot instead of being rejected. Deleting
or renaming a base-published version directory is the same rejection, not a
silent package removal. This closes the two-step bypass: a first PR may retire
the last spec, but the registry entry becomes a base entry, so a later PR that
edits the old directory is still rejected. Deleting the base registry entry to
escape is itself `published-registry-modified` (§8.3), so the split cannot be
used to unpublish.

Evidence is part of the snapshot. Before publication, editing `tests/cases.json`
or a listed evidence file moves `evidence_digest` and `release_digest` while
leaving `definition_digest` alone (§7.1). After publication, the same edit is a
snapshot change (`published-package-modified`) and requires a new version, with
its own manifest and source digest. The "evidence-only" test therefore applies
to an unpublished candidate, never to a published directory.

Counterexample if this rule were absent: a package version `0.1.0` with digest
`D0` is selected by an old spec. An author adds a form in place and moves the
manifest to `0.2.0`, producing `D1`. The old spec still names the same directory
and `D0`, so `verify --all --check` fails until the author edits the global spec
or restores the old bytes. That is exactly the vertical coordination H2 is meant
to remove. With the immutable layout the author adds `0.2.0/`, the old spec still
rebuilds `0.1.0/D0`, and the publisher chooses when to select `0.2.0`.

The layout sketch in `he1-horizontal-extension.md` §6.1 is a roadmap, not an H2
format. Where it shows `tests/cases/*.json`, `evidence/sources.json`,
`fixup-profiles.json` or `constraints.json`, H2 narrows the subset to one
`tests/cases.json`, one `evidence/manifest.json` and no profile or constraint
asset; the other entries describe H3/H4 surfaces that this ADR does not
implement. The §6.2 manifest sketch also predates this contract: its bare-path
`exports.forms` and its missing `definition_format`/`target_identity` are
superseded by the closed manifest in §1, which is the only H2 shape.

#### 1.2 The declared capability set must equal the derived one

`requires_capabilities` is a claim about what the exported rows need, so a
whitelist alone is not enough: a package that declares nothing while its rows
use a primitive makes the field a comment, and a later consumer that trusts it
under-estimates the requirement. H2 therefore derives the set from the rows and
requires equality:

| Capability | Derived as required when |
|---|---|
| `field-placement/v1` | some exported form has at least one `slots[]` entry with a non-empty `placements` array — the row places a value at a `bit_offset`/`width` inside the template unit |
| `integer-domain/v1` | some slot has `from: "operand_value"`, i.e. the row encodes an integer operand under its `range` (`signed`, `bits`, `align_bits`) instead of a register or fixed field |

A declared set that differs from the derived set is `capability-mismatch`
(exit 1), in both directions: an undeclared requirement lets H3 under-provision,
and an unused declaration turns the field into a wish list that a reader cannot
distinguish from a real requirement.

The comparison is over members, not spellings. The declaration is already
restricted to the one strictly increasing, duplicate-free form of §1, and the
derived set is compared by membership. A document that names the right
capabilities in the wrong order, or repeats one, is `capability-lexical` (exit
1), not `capability-mismatch`: the semantic equality check never canonicalises a
non-canonical array, and no other spelling of the same set enters a digest.

The derivation has a consequence that the earlier draft avoided rather than
stated. `fmp_model::definition::read` requires every form to have a non-empty
`slots` array and every slot to have a non-empty `placements` array
(`fmp-model/src/definition.rs`, `bind_forms`/`bind_slot`), so **every legal
`fmp-def/0.1` form derives `field-placement/v1`**. A package with at least one
form therefore cannot declare `[]`: that declaration is `capability-mismatch`,
not a legal degenerate case. `integer-domain/v1` is the optional one, present
exactly when some slot has `from: "operand_value"`.

| Legal rows | Derived set |
|---|---|
| the two §1 register forms, `x86:mov/r64-rm/legacy` and `x86:mov/rm-r64/legacy` | `["field-placement/v1"]` |
| `x86:add/rm64-imm8/legacy` (one register slot, one `operand_value` slot) | `["field-placement/v1","integer-domain/v1"]` |

The first row is the end-to-end legal vector: a package exporting exactly those
two rows, with `target_identity` equal to the pinned x86 `0.1.0` target and
`requires_capabilities: ["field-placement/v1"]`, satisfies every package rule
stated here — manifest shape, path, this equation and `read` — and its derived
set equals its declaration. The same package with `[]` is rejected before
`read`. The §7.0 `{"form_id":"x86:example/form","template":"90"}`
bytes are **not** a legal form — they have no `slots` and the ID lacks the
`/legacy` family segment — so they are a digest-preimage vector only and are
never presented to `read` or to this derivation.

A slotless form is therefore not a way to get an empty set: `read` rejects it
first (`empty` slots, `E-DEF-001`), and H2 must not relax `read` to make a test
pass. The derivation is over `fmp-def/0.1` structure that H2 already parses, so
it is a total function of the read document, not a heuristic. H3 may extend the
table for new primitives; it may not weaken the equality, and a future
capability it cannot derive is a new format version, not an exemption.
`unsupported-capability` still rejects an unknown string before the derivation
runs.

#### 1.3 Identifiers, path segments and file names are ASCII and portable

§3 bounds *where* a file may be; it does not yet say which strings may name one.
Leaving that to the filesystem makes the same package produce different digests,
or a different class of diagnostic, on ext4, APFS and NTFS. Four grammars are
therefore fixed, and every identifier and path in a manifest, spec, lock or
registry is checked against them before any file is opened:

```text
ident    = ^[a-z][a-z0-9]*(\.[a-z][a-z0-9_-]*)+$
version  = ^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){2,}(-[a-z0-9]+([.-][a-z0-9]+)*)?$
pseg     = ^[a-z0-9_][a-z0-9_.-]*$
path     = pseg ("/" pseg)*
```

- `package_id`, `bundle_id`, `namespace`, `target_profile` and `profile_id` use
  `ident`: at least two segments, each starting with a lowercase letter, with
  `-`/`_` allowed inside a segment. `monasm.x86.mov-register`,
  `monasm.bundle.x86_64-mov` and `monasm.target.x86_64` are legal;
  `Monasm.X86.Mov`, `monasm..x86`, `monasm.x86.` and `..x86` are
  `identifier-lexical` (exit 1).
- An author-written `version` uses `version`: `0.1.0`, `0.2.0` and `0.1.0-h2`
  are legal; `0.1`, `01.0`, `0.1.0-H2` and `0.1.0-` are not. Three numeric
  components are required and a component may not carry a leading zero. The
  derived standalone version `standalone+<hex>` (§2.1) is outside this grammar
  and never appears in a manifest, spec, lock or path; a spec carrying it is
  already `reserved-identity`. `legacy_source.version` keeps the stricter
  numeric-only form of §3.
- Every declared path — `exports.forms[].path`, `exports.types[].path`,
  `exports.profiles[].path`, a spec's `packages[].path` and the `legacy_source`
  components — uses `path`; `legacy_source.isa` and `legacy_source.version` are
  further restricted by the component forms of §3. A `path` may be a **single
  segment**: a package-root file such as `NOTICE` or `README.md` (the fixed
  uppercase spellings below) or a top-level form file such as `add.json` is one
  segment, not a two-segment minimum. Where a shape is fixed,
  the surrounding rule says so: `packages[].path` has the
  `packages/<target>/<package_id>/<version>` shape of §1.1, and a form/type/profile
  path is relative to the package root. A path listed in
  `evidence/manifest.json` uses the same grammar; the fixed names `README.md` and
  `NOTICE` are the two accepted uppercase spellings and are the only exception to
  lowercase. No segment may be `.`
  or `..`, contain `..`, end with `.` or a space, or be a Windows device name
  (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`,
  case-insensitively, with or without an extension). A violation is
  `path-lexical` (exit 1), raised on the string before the file is opened.
- **A path collision is scoped to its root.** An asset path
  (`exports.forms/types/profiles[].path`) and an evidence path are relative to
  their own `packages/<target>/<package_id>/<version>/` directory. The fold rule is
  applied to those **relative** strings within one package, and across a closure
  only to the **repository-root-relative** path formed by joining the selected
  `packages[].path` with the relative asset path. Two paths that fold to the
  same string in the same domain are `path-lexical` (exit 1). Equal relative
  names under different package roots do **not** collide, because the joined
  paths differ before the file name:
  `packages/x86_64/monasm.x86.alu/0.1.0/forms/add.json` and
  `packages/x86_64/monasm.x86.vector/0.1.0/forms/add.json` are two files and
  both are legal. In particular:
  - inside one package, `forms/Add.json` and `forms/add.json` collide;
  - across a closure, two selected package roots that fold to the same
    repository path (for example `packages/x86_64/monasm.x86.alu/0.1.0` and
    `packages/x86_64/MONASM.X86.ALU/0.1.0`) collide, and a spec may not list one path
    twice;
  - the fold — not "the file happened to open" — must be the stated reason.
  The grammar admits only lowercase, so a document that follows §1.3 cannot
  trigger the fold rule; it exists because the builder does not assume every
  manifest it is handed came from this grammar. `README.md` and `NOTICE` are the
  two fixed uppercase spellings: when an evidence path names one of them, the
  name matches its on-disk spelling exactly and is the only exemption from the
  lowercase rule. They are not asset paths and never name a form, type or
  profile.
- Paths are matched exactly as written. The builder never lowercases, trims a
  trailing dot or space, or resolves an 8.3 alias; a path that matches only after
  such a repair is `path-lexical`, not a successful open.
- **The on-disk entry must have the declared spelling.** A declaration being
  lowercase-legal does not make the file on disk lowercase. A declared
  `forms/add.json` is satisfied only when the opened `forms` directory contains
  an entry named exactly `add.json`. On a case-insensitive APFS or NTFS volume
  the declared `add.json` would open `Add.json`; that is `path-lexical`
  (exit 1), not a success, and the verdict is the same on ext4. Every segment is
  checked this way, intermediate directories included. The path layer performs
  the check on the **already-open parent handle**: it enumerates that handle for
  an entry whose name is byte-for-byte equal to the declared segment and then
  opens that entry relative to the same handle with the no-follow rule of §3.
  It does not compare an absolute path string, and a separate probe before the
  open does not satisfy the rule.
  - Confirming the name and opening the entry must not leave a gap in which the
    directory entry is replaced. Opening "the same name" again is not enough:
    the implementation must either open the entry it just matched (a
    directory-entry handle or an identity check on the opened object) or detect
    that the object differs and reject with `path-escape` (exit 1). A path layer
    that only proves symlink refusal does not prove this; the V-P N1b gate
    includes the replacement case on every platform.
  - A platform that cannot perform an exact-name lookup relative to an open
    handle, or cannot bind the open to the matched entry, fails the V-P N1b gate;
    it must not accept the aliased name and must not fall back to a following
    open.
- `bundles/specs/<file>.json` is the spec, `bundles/locks/<file>.lock.json` the
  lock and `bundles/sealed/<file>.bundle.json` the sealed bundle, with `<file>`
  equal to the document's `bundle_id` in each case. A file whose `<file>`
  component does not equal the `bundle_id` it contains is
  `bundle-file-mismatch` (exit 1), so `--all` has exactly one filename per
  identity and renaming a spec cannot attach it to a different release. The
  legacy snapshot is `bundles/legacy/<bundle_id>/definition.json`.
- `packages/<target>/<package_id>/<version>/` requires `<package_id>` to equal
  the manifest's **full** `package_id` and `<version>` to equal the manifest's
  `version`. A `<package_id>` mismatch is `path-lexical`; a `<version>` mismatch
  is the `path-version-mismatch` of §1. The mapping
  `Path(target, package_id, version) = (target, package_id, version)` is
  injective: two distinct `package_id` values never share a directory. Using
  only the last dot-separated segment would not be injective —
  `monasm.x86.crypto` and `vendor.x86.crypto` would both map to
  `packages/x86_64/crypto/0.1.0/` and could not coexist without renaming one
  owner, so the namespace isolation `package_id` promises would not survive the
  directory layout. `pseg` already admits dots, so the full ID needs no escaping.
  `<target>` is a directory label only: it must satisfy `pseg`, but the builder
  does not compare it to `isa_family`, `target_profile` or a central table,
  because target facts are self-declared (§2) and a fourth H3 family must not
  need a directory mapping.

Counterexamples:

- A package declares both `forms/Add.json` and `forms/add.json`. On ext4 both
  exist and the source digest covers two files; on a case-insensitive APFS or
  NTFS volume the second write replaces the first, so the manifest names two
  paths but one file exists and `source_package_digest` differs by platform. The
  fold rule rejects the manifest everywhere with one `path-lexical`.
- Two packages both declare `forms/add.json` and both contain
  `tests/cases.json`. They are different files under different package roots, and
  a closure that selects both is legal. A check that compared the bare relative
  strings across the closure would reject ordinary composition; the joined
  repository paths are the closure domain.
- A spec selects `packages/x86_64/monasm.x86.alu/0.1.0` under one package ID
  and `packages/x86_64/MONASM.X86.ALU/0.1.0` under another. The roots fold to
  the same repository path, so the closure is `path-lexical` (exit 1); it is not
  two packages that happen to use a case-different directory.
- A manifest declares `forms/add.json` and the tree contains only
  `forms/Add.json`. Without an entry-name rule, ext4 reports a missing file
  (exit 2) while a case-insensitive APFS or NTFS volume opens it (exit 0). The
  exact-name check makes both `path-lexical` (exit 1); the same applies to an
  intermediate `Forms/` directory. This is distinct from declaring
  `forms/Add.json`, which the grammar rejects before any open.
- `forms/NUL.json` or `forms/aux` opens a device on Windows, or fails with an I/O
  error (exit 2), while another platform creates an ordinary file. The grammar
  rejects the name before the open, so the same document is a format rejection
  on every platform.
- `forms/add.json.` or a segment ending in a space is silently trimmed by
  Windows and aliases `forms/add.json`; the format forbids the trailing
  character instead of relying on the open to disagree.
- `bundles/specs/mov.json` containing
  `bundle_id: "monasm.bundle.x86.mov"`: the file and the document disagree, so
  `--all` cannot say which identity the file belongs to. `bundle-file-mismatch`
  makes the filename a checked fact rather than a convention.
- `packages/x86_64/monasm.x86.mov/0.1.0` containing
  `package_id: "monasm.x86.mov-register"`: `verify --package <path>` and the
  spec's `(package_id, path)` describe different owners. The full-ID rule ties
  them without a central package table.
- A `package_id` of `monasm.x86.` yields an empty final segment; the ID is not
  a legal dotted identifier and `identifier-lexical` rejects it before a path is
  formed. A `package_id` containing `/` or `..` is likewise rejected before it
  could escape the target directory.

### 2. Target facts are self-declared; `legacy_source` is migration provenance

Every package states its own execution target in `definition_format` and
`target_identity`. Those two fields are required and are part of the manifest,
so they enter `source_package_digest`; a package cannot inherit a target from a
central table, from the spec, or from a legacy file. The spec must agree with
every listed package, and a package that nothing selects can still be checked
against its own declarations (`verify --package`, §8).

`legacy_source` answers a different question. It is optional and records that
the package's rows were copied from a pinned legacy definition `(isa, version)`;
it is evidence about migration, not the source of the target identity. When it
is present it is part of the manifest, so it enters `source_package_digest`; an
author cannot retarget the comparison by editing a file that is not digested.
The builder resolves it to exactly `<root>/definitions/<isa>/<version>.json`,
where `isa` is the directory name (`x86_64`, `aarch64`, `rv64`), not the form
family. It does not search, does not pick the newest file and does not choose
among candidates. It compares every exported row against that exact document and
fails if the row is absent or not byte-equal. Counterexample if it searched: two
versions with the same file name in different directories would make the
comparison depend on traversal order.

**Row equality alone is not migration equivalence.** When `legacy_source` is
present, the builder also requires migration target equivalence, defined over the
parsed objects rather than their raw spelling:

```
TargetEq(A, B) = keys(A) = keys(B)
              ∧ (∀ k ≠ enabled_extensions: A_k = B_k)
              ∧ Set(A.enabled_extensions) = Set(B.enabled_extensions)
```

Every field except `enabled_extensions` (`isa_family`, `isa_variant`,
`execution_mode`, `byte_order`, `address_width` and any other field the legacy
target declares) must be canonically equal; `enabled_extensions` is compared by
set membership. The package's `definition_format` must also equal the legacy
document's, independently of `TargetEq`. This is forced by §1: a package must
spell the array in the one
canonical strictly increasing form, while a frozen legacy document keeps its
published bytes. `definitions/rv64/0.6.0.json` declares
`["rv64i","rv64c"]`; a package migrating one of its rows must declare
`["rv64c","rv64i"]`, and the two are the same target. Requiring raw array
equality would reject both spellings — the canonical one as `legacy-target-mismatch`
and the legacy one as `extension-lexical` — so no legal manifest could exist.

The package still declares its own target and its own digest; the legacy file is
not re-spelled and both identities keep their own rules. A mismatch in any other
field, or a differing extension member set, is `legacy-target-mismatch` (exit 1),
reported before the merged document is read. This does not make the legacy file
the target authority: a new package without `legacy_source` is checked only
against its declaration. It closes the gap where a copied row is byte-equal but
the package claims `execution_mode: "32"` or `address_width: 32`, so
"self-declared target" and "row equal" are both true while the migrated execution
semantics are not. A deliberate target change needs an explicit, versioned
compatibility record in a later format; H2 rejects it rather than inferring it.

A package that is not re-homed omits `legacy_source`. It is then checked by the
declared `target_identity`/`definition_format`, by `fmp_model::definition::read`
on the merged document, and by its own package tests; there is no legacy row to
compare, and the builder does not invent one. That is the path a new instruction
family uses even when no matching file exists in `definitions/`. The three H2
packages are re-homed, so they must write the field.

`definition_format` is a single value per package. A closure that mixes
`fmp-def/0.1` and `fmp-def/0.2` packages is rejected, even when their target
identities are equal: H2 performs no implicit conversion, because converting
rows would change their semantics and create a second definition authority. An
explicit, versioned conversion is H3 work; until then the author splits the
closure or rewrites the row openly.

### 2.1 `verify --package` derives a versioned standalone definition identity

`verify --package` does not read a spec, so it cannot borrow a bundle's
`namespace`/`version`. Leaving that identity to the implementation would let two
agents produce two digests for the same package and would let a temporary check
mint something that looks like a release. The identity is therefore fixed by the
`monasm-standalone/0.1` rule:

```text
namespace = "monasm.standalone." ++ package_id
version   = "standalone+" ++ lower_hex(source_package_digest without "sha256:")
domain    = "monasm-standalone/0.1"
```

The input is the package alone: the canonical manifest and the declared assets,
i.e. exactly the bytes that produce `source_package_digest`. The absolute path,
the package directory name, the current working directory, the clock, the spec
and any enumeration order are not inputs. Copying a package to another directory
and running from another working directory therefore yields the same standalone
identity and the same standalone `definition_digest`.

This identity is a development identity, not a release identity:

- The bundle builder rejects a spec whose `namespace` starts with
  `monasm.standalone.` or whose `version` starts with `standalone+`
  (`reserved-identity`, exit 1). A lock or sealed bundle can never name a
  standalone identity.
- A standalone definition is merged, sorted and read by
  `fmp_model::definition::read` exactly like a package contribution to a bundle,
  but its `definition_digest` is computed from the standalone document. It is
  never written to a lock, a sealed bundle or the H1 equivalence record.
- `verify --package`, the package conformance harness (§9.1) and any future
  author tool call the same function, so they agree by construction rather than
  by convention.

Counterexample if the identity were copied from a spec or invented per tool: two
unrelated packages could both check as `monasm.isa.x86` / `0.1.0-h2`, and a
standalone check could produce a digest that a reader mistakes for the released
bundle.

### 3. Paths are bounded to the package and the repository root

The lexical rules for identifiers, path segments and artifact file names are
§1.3; this section bounds the resolution of an already-legal path. Every
manifest path is a normalised relative path using `/`. Absolute paths, `..`,
empty segments, `.`, backslashes, NUL, URL schemes and drive letters are
rejected. The exact-entry-name rule of §1.3 is part of the same open, not a
preceding `stat`: a case-insensitive host must not turn a declared `add.json`
into the on-disk `Add.json`, and a replacement of that entry between the name
match and the open must not yield a different object. The bound is a property of
the **open**, not of a moment before it: no component on the path from `--root`
to an opened file may be a symlink or reparse point, and the builder never
traverses one. H2 package inputs contain no such links on that path; a package
that has one is `path-escape` (exit 1).

A metadata pre-check is **not** sufficient, even a non-following one.
`symlink_metadata()` can report `forms/` as a real directory, another process can
replace it with a link, and the following `read()` on the ordinary path then
traverses that link. That is the same check-then-use gap as
`canonicalize()`-then-`open()`, with one fewer step:

1. `symlink_metadata("pkg/forms")` → directory, check passes;
2. `forms/` is replaced by a link to a directory outside `--root`;
3. `open("pkg/forms/example.json")` follows the link and reads the outside file.

The contract therefore names the mechanism by its guarantee, not by a helper
call:

- each component is opened relative to an already-open directory handle with
  no-follow semantics, and the next step uses that handle rather than a
  re-derived path string; or
- the open itself carries a flag that makes the platform refuse to follow a link
  or reparse point, and the builder reads from the returned handle.

Either way the guarantee is about the object actually opened: the builder must
not re-open the same path afterwards "to read the bytes". A platform on which
the builder cannot express a no-follow open rejects the package with
`path-escape` instead of silently degrading to a following open. The format also
forbids links outright, so a link whose target is *inside* `--root` is still
`path-escape`; the builder does not resolve it and call the result bounded.

**Every opened leaf must be a regular file, checked on the handle.** A no-follow
open of a legal path can still land on an object that is not a regular file: in
a writable worktree `forms/add.json` may be a POSIX FIFO, a Unix socket or a
device node. None of those is a link, so `path-escape` does not fire; an
ordinary read on a FIFO with no writer blocks instead of returning bytes, and a
byte budget cannot bound an object that has no length. Intermediate components
must be directories and the leaf must be a **regular file**. The type is taken
from the **opened handle** (`fstat` on POSIX, `GetFileInformationByHandle` on
Windows), never from a path `stat` before the open, for the same check-then-use
reason as the entry-name rule. The POSIX package-input open carries
non-blocking semantics (`O_NONBLOCK`), so a FIFO without a writer cannot hang
the builder before the type is known; Windows exposes no filesystem FIFO, so
`FILE_TYPE_DISK` plus the regular-file attribute is the check there. A
non-regular leaf, a directory where a file is required, or a non-directory where
a directory is required, is `not-a-regular-file` (exit 1) — a deterministic
rejection of the object, not a host I/O failure (exit 2). This applies to every
file the builder opens: manifest, declared asset, case file, evidence file, spec,
lock, sealed bundle, legacy snapshot and `bundles/published.json`. The write
phase needs no counterpart: it writes a temporary sibling and renames it into
place (§8.3), so it never opens the previous entry.

H2 does not claim protection against an attacker who can rewrite the worktree
after a successful build, nor against a hostile `--root` itself; it does claim
that a successful build opened exactly the objects the checks describe. The
spec's `packages[].path` and the `--root` resolution obey the same rule; `--root`
may be canonicalised once to establish the base, but no component below it is
opened through a followed link. `legacy_source.isa` and `legacy_source.version`
are path components before they are concatenated into
`<root>/definitions/<isa>/<version>.json`, so they receive the same treatment:
`isa` must match `^[a-z0-9_]+$` and `version` must match
`^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){2,}$`. A value containing `/`, `\`, `..`,
`.` as a whole component, a drive letter, a URL scheme or NUL is rejected before
the path is formed; the builder does not normalise a value into legality.
`README.md`, `NOTICE`, `evidence/**` and `tests/**` may exist, but only declared
asset files (`form`, `type`, `profile`) enter the source digest;
`evidence/manifest.json` enters `evidence_digest` only.

Rust's portable `std::fs` has no no-follow open: `File::open` takes a path and
follows links, and `OpenOptionsExt::custom_flags` exposes a platform flag only
for the final component. The contract therefore permits at most one additional
product dependency whose entire role is this path layer, in addition to
`fmp-model` (§9). It must be pinned, offline and free of package-format
knowledge; it may not interpret a manifest, a definition or a digest. Whether a
candidate actually delivers the guarantee on Linux, macOS and Windows is not
assumed here: the publication-channel verdict's first deliverable is a standalone
platform feasibility PoC that must demonstrate it with intermediate-directory
links, final-file links, Windows reparse points, a swap between check and open,
and a POSIX FIFO leaf that must be rejected as `not-a-regular-file` without
blocking, or stop that verdict instead of shipping a following open. If a platform
cannot be satisfied, the hardened reader refuses untrusted package reads there with
`path-escape`; a build that succeeds on Linux but refuses every untrusted package
on Windows is a failed publication gate, not a passing one. The PoC does not gate
the author layer: a trusted-tree reader may land and be tested while the PoC is
still running (§8.5), but no artifact it produces may be published and the
hardened reader is not claimed to exist on that platform.

**The N1 PoC is a separate deliverable, and it lands before the hardened reader.**
The gate is not a design note that a later implementation tries to satisfy: the
PoC is the publication channel's first committed deliverable, and no hardened
package reader, closure reader or publication-capable build merges before its
results are recorded. It records, per
platform (Linux, macOS, Windows), the exact OS version, the toolchain and
path-layer crate version with its lockfile entry, the API or syscall each step
uses (for example an `openat`-family call with `O_NOFOLLOW`/`O_DIRECTORY`, or a
Windows handle open with `FILE_FLAG_OPEN_REPARSE_POINT`), the fault-injection
method for each case (a directory entry swapped between name match and open, a
case-alias entry such as `Forms/` or `Add.json`, a FIFO leaf where POSIX allows
it, a Windows reparse point), and the observed result per case. "Theoretically
possible with a no-follow open" is not evidence: a row without a platform
version, an API name or an observed result is missing, and a missing or
inconclusive row stops the publication verdict exactly like a failing one. One
green platform is never extrapolated to the other two.

### 4. The spec lists the full closure; the builder never scans packages

`bundles/specs/<bundle_id>.json` is `monasm-bundle-spec/0.1`:

```json
{
  "bundle_format": "monasm-bundle-spec/0.1",
  "bundle_id": "monasm.bundle.x86_64-mov",
  "target": {
    "profile_id": "monasm.target.x86_64",
    "identity": {
      "isa_family": "x86",
      "isa_variant": "x86-64",
      "execution_mode": "64",
      "enabled_extensions": [],
      "byte_order": "little",
      "address_width": 64
    }
  },
  "definition_format": "fmp-def/0.1",
  "namespace": "monasm.isa.x86",
  "version": "0.1.0-h2",
  "packages": [
    {
      "package_id": "monasm.x86.mov-register",
      "version": "0.1.0",
      "path": "packages/x86_64/monasm.x86.mov-register/0.1.0",
      "source_package_digest": "sha256:..."
    }
  ]
}
```

- Every `path` ends at a version directory whose name equals both the spec's
  `packages[].version` and the manifest's `version`. The builder checks this
  before opening the manifest (`path-version-mismatch`).

`packages` **is the full closure**, not a set of roots. The builder opens
exactly these paths and nothing else. The array is strictly ordered by
`(package_id, version)`; a reversed or duplicate entry is rejected before any
manifest is opened, never normalised into an equivalent spec. Each package's
`dependencies` are verification edges: every element is the closed
`{package_id, version, source_package_digest}` object of §1, and every edge must
resolve to a listed `(package_id, version)` with exactly the listed
`source_package_digest`. An edge
to a package outside the list is a missing-dependency error, never a scan
trigger. Two entries with the same `(package_id, version)` or the same `path` are
rejected even when their content is identical; identity is a release fact, not a
content comparison. At most one version of a `package_id` may appear: two
versions are rejected even
when their exports are disjoint, because the lock would record two owners for
one release identity. A listed package that nothing depends on is a legal root;
reachability is not required.

`--all` enumerates `bundles/specs/*.json` only. It never enumerates
`packages/**`, so adding or corrupting an unselected package cannot change an
old spec's lock or sealed bundle.

The spec's `target.identity` and `definition_format` must agree with every
listed package's declarations; they are compared as data, not derived from
`legacy_source`. `definition_format`, `target_profile`, `isa_family`,
`isa_variant`, `execution_mode`, `byte_order` and `address_width` must be equal.
`enabled_extensions` is different: a package's list is its declared cover and
the bundle's list is the selected target, so the package list must be a subset
of the bundle list, without a minimality claim (§4.1). Both lists are written in
the one canonical spelling of §1 — strictly increasing and duplicate-free; a
reversed or duplicated array is `extension-lexical` (exit 1) before the subset
test runs. The lock and sealed bundle copy the spec's array verbatim, so a second
spelling of the same target is a byte mismatch, not an alternative target.
Every package's `target_profile` must equal `target.profile_id`. A closure
whose packages disagree on the structural target fields or on
`definition_format` is rejected; the builder does not pick a winner and does
not convert a package. A package with `legacy_source` is additionally checked
against that pinned row, but the pin never supplies the target facts.
The builder writes the selected identity into the generated definition; it does
not consult a central Rust target table. That is the H3 precondition "a new
target does not edit a public whitelist".

Counterexamples: without the full list, the builder must discover dependencies
and an unselected corrupt package can break an old build (`HE-AC-05`); without
exact IDs, "latest" or a range picks a version the author did not name
(`HE-AC-04`, `HE-T08`); without paths, the builder must scan to find a package.

#### 4.1 A package declares a target cover; the bundle selects the target

The composition problem is concrete. Package A (`rv64i` arithmetic) declares
`enabled_extensions: ["rv64i"]`; package B (`rv64c` compressed) declares
`["rv64c","rv64i"]`. If the package list were the full target configuration, A
and B could never share a bundle, because the builder would demand that A's
manifest also say `rv64c`. Adding the compressed family would force every
already-published package to edit its manifest, changing `source_package_digest`
and re-releasing unrelated packages. That is the cross-package synchronisation
`ADR-0125` exists to remove.

The contract therefore separates the two facts:

| Fact | Declared by | Meaning |
|---|---|---|
| package `target_identity.enabled_extensions` | each package | the author's conservative declared cover: a set containing every exported row's requirement |
| bundle `target.identity.enabled_extensions` | the spec | the complete set selected for this bundle |

The declared set is a **cover, not a minimum**. The author asserts "a bundle
that selects this package must provide at least these extensions"; the builder
proves that the cover contains every row's requirement and fits inside the bundle
selection. It does not prove that the cover equals the union of the row
requirements, because it cannot: `fmp-def/0.1` forms carry no
`requires_extensions`, and even a `0.2` form's list is not defined to include the
base ISA or every profile fact. An equality rule would have to invent the missing
requirement.

Over-declaration is therefore legal, and it has a real effect: it narrows the
set of bundles that may select the package. A package whose rows all need only
`rv64i` but whose manifest declares `["rv64c","rv64i"]` cannot be selected by a
bundle whose target is `["rv64i"]`, even though every row would pass there. The
builder does not trim the declaration to the derived union, because that would
make `source_package_digest` describe a requirement the author did not write and
would let the package become selectable without an edit. A publisher who wants
the narrower requirement publishes a new package version that declares it.

The builder requires every package's declared cover to be a subset of the
selected bundle set, and requires the other target fields to be equal. A package
is not edited when a new, disjoint extension family joins the bundle; the new
package declares its own larger cover and the spec selects the union.

Under-declaration remains an error, and the form-to-package check is what
catches it. A bundle's wider selection cannot hide a package that under-declares
itself. The full rule is per exported form:

```text
E_form(f) ⊆ E_package ⊆ E_bundle      for every selected package P and f ∈ P.forms
```

`E_form(f)` is `form.requires_extensions` for `fmp-def/0.2`; it is `∅` for
`fmp-def/0.1`, whose form object has no such key (`FORM_FIELDS` rejects it).
`E_package` is `target_identity.enabled_extensions`; `E_bundle` is the spec's
`target.identity.enabled_extensions`. The equation says the declared cover
contains every form's proven requirement and the bundle contains the
declaration; neither inclusion is an equality. The builder computes the union of
`E_form(f)` over the package's exported rows and rejects a package whose union
is not covered by its own declaration (`form-extension-mismatch`, exit 1),
before it looks at the bundle. The package-to-bundle subset is then checked as
above.

**What the first inclusion proves, and what it does not.** For `fmp-def/0.1`
`E_form(f)` is empty for every form, so `⋃E_form ⊆ E_package` is vacuously true
and can never detect an ISA extension that the rows need but the manifest omits.
What H2 actually proves for a `0.1` package is `E_package ⊆ E_bundle`: the
declared cover fits the selected target, and the package cannot be selected by a
bundle that provides less than the author declared. A package with
`legacy_source` gains one further, independent constraint: its
`definition_format` must equal the pinned document's and its `target_identity`
must satisfy `TargetEq` (`enabled_extensions` compared as a set; every other
field canonically equal; §1.1, `legacy-target-mismatch`), which catches a
migration that silently
retargets a copied row, but still derives nothing from the row body about which
extensions the instruction really needs. A new package without `legacy_source`
rests on the author's declaration plus the cases and evidence in its own
directory. H2 must not close that gap by adding an ISA-specific derivation of
extension requirements: that would make the builder a second semantic authority
over the ISA, which `ADR-0125` forbids. The H2 acceptance report therefore says
explicitly that **"the package target cover relation is verified" does not mean
"the real ISA extension requirements are completely proved"**; only a later
versioned rule may narrow a cover, and until then any such narrowing is an
author edit with a new `source_package_digest`.

**`profile_id` is a nominal label, not a target identity.** The spec's
`target.profile_id` and each package's `target_profile` must be equal, but the
equality is a name check inside one bundle. Two specs may use the same
`profile_id` with different `target.identity` objects, and H2 treats them as
different targets: the identity that decides compatibility, enters the generated
document, the lock and the sealed bundle is the six-key `target.identity`, never
the profile name. H2 adds no cross-spec uniqueness rule for
`(profile_id, identity)` and no central profile table, because a name that is
allowed to differ per bundle must not be read as a global fact. A consumer that
needs a target identity keys on the full identity; a later phase that wants
`profile_id` to name exactly one global target has to add that rule through a
versioned format change and cannot assume H2 already publishes it. Counterexample
for reading the name as identity: two bundles both say
`monasm.target.x86_64` while selecting different `enabled_extensions`; a consumer
that looked up the profile name to decide compatibility would accept or reject
the same plan depending on which bundle it read first.

`fmp_model::definition::read` checks a form's `requires_extensions` against the
**generated definition's** target set, which is the bundle's. A package can
therefore be legal only after merging, while its own declared target does not
cover its rows. `verify --package` would reject it under the package's own
target, but `verify --all` would accept it, so the same package would have two
verdicts depending on which command ran. H2 closes that gap by reading each
selected package's own document, built from its own rows and its own
`target_identity`, before merging; a failure is the ordinary `read` rejection
for that package. The merged document is still read afterwards, and ownership,
identity and digest checks are unchanged.

Counterexample: a `fmp-def/0.2` package declares `["rv64i"]`, one of its forms
requires `["rv64c"]`, and the spec selects `["rv64c","rv64i"]`. Package ⊆ bundle
passes, and the merged `read` passes because the generated target carries
`rv64c`. `verify --package` on the same bytes fails, because the package's own
target is `["rv64i"]`. Adding `rv64c` to the manifest fixes it; the larger bundle
must not be the reason a row became legal. Under `fmp-def/0.1` the same mistake
is impossible to express at the form level, which is why the H2a test uses a
0.2 fixture for this rule and does not infer the rule from the three 0.1
packages.

Counterexample for the opposite direction: every row of a package requires only
`rv64i`, the manifest declares `["rv64c","rv64i"]`, and the spec selects
`["rv64c","rv64i"]`. Every check passes and the package is legal, but it cannot
be selected by an `rv64i`-only bundle. A reader that treated
`enabled_extensions` as "exactly what the rows need" would either trim the
declaration — changing the author's `source_package_digest` and making the
package selectable without an edit — or reject a bundle the author deliberately
covered. The contract keeps the declaration as the author's cover and states
that over-declaration only narrows selectability.

**H2 transition.** `bind` chooses the set relation from the **definition**
format, not the plan format (`fmp-validate/src/lib.rs` `check_target`): a
definition whose `definition_format` is `fmp-def/0.1` compares
`enabled_extensions` for equality, while `fmp-def/0.2` requires the plan's set to
be a subset of the definition's and checks each form's requirement later. So an
H2 bundle that generated an `fmp-def/0.1` document selecting a superset would
reject the existing reference plans. While the generated document is
`fmp-def/0.1`, H2 additionally requires the package's declared cover to equal the
bundle selection exactly; this is the transitional `h2-exact-target` check, not a
permanent package-contract rule. `fmp-def/0.2` documents already apply the subset
rule, and a future `fmp/0.2` plan format may define a new cell on the plan side.

**Exit condition.** H3 must define plan-level target compatibility so a plan may
target a subset of the definition/bundle set without rewriting the definition,
**and** a versioned build rule so the builder accepts such a selection under that
declared protocol, **and** the per-instruction evidence source below (a versioned
bundle map or another frozen, digest-bound source). All three are required: the
builder rejects an unequal `fmp-def/0.1` selection before any plan is bound, so a
plan protocol alone cannot lift the build-time check (the versioned-lift
paragraph below), and a subset relation without per-form or owner data cannot
reject the `c.addi`/`rv64i` plan. `monasm-bundle-spec/0.1` keeps its rejection
conclusion permanently. The lift must be in force before H5's
parallel-extension drills; if it is not, this ADR's package contract must be
revised by a new ADR before H5 starts. H2 does not claim the transitional
equality is the final composition rule, and it does not freeze a package
manifest that must be edited for every new extension family.

**Lifting is versioned, and the matrix is explicit.** Target compatibility is a
property of the (plan protocol, definition protocol) pair. The cells that exist
today are fixed, and H3 must preserve every one of them:

| plan | definition | relation |
|---|---|---|
| `fmp/0.1` | `fmp-def/0.1` | equal sets |
| `fmp/0.1` | `fmp-def/0.2` | plan set ⊆ definition set, plus each form's `requires_extensions` |

Only a **new plan protocol, together with the versioned build rule and the
per-instruction evidence source described below,** may add a cell and lift
`h2-exact-target`; the
existing `fmp/0.1` + `fmp-def/0.2` cell already uses the subset rule and must not
be re-rejected by an implementation that keys the rule on the plan format. The
`fmp/0.1` + `fmp-def/0.1` cell keeps equality, and no build option changes either
cell. Changing the equality rule for `fmp-def/0.1` requires a new versioned
contract, not deleting the existing check. H3 acceptance must run the same
package with different extension sets across the matrix: old cells keep their
results, and the new cell accepts a subset only where its own rule says so. A
build that passes after the check is deleted is not evidence for the new rule.

**H3's subset rule must prove per-instruction legality.** A plan-side
`E_plan ⊆ E_bundle` is necessary but not sufficient. Let a bundle select
`{rv64i, rv64c}`, with package A covering `{rv64i}` (`add`, `addi`) and package B
covering `{rv64c, rv64i}` (`c.addi`). A plan declaring `{rv64i}` satisfies the
subset relation and can still select `c.addi`, whose owner needs `rv64c`. The
selected form and its owner decide execution, not the bundle. H3 must therefore
check every selected instruction against the plan target:

```text
∀ i ∈ Plan.instructions: E_package(owner(form(i))) ⊆ E_plan
```

The left side is the **owner cover**, and it is always the baseline check.
`E_package(owner(f))` is the owning package's declared cover from the table at
the start of this section. The cover is conservative — it can reject a row that
would have needed less — but it cannot accept an instruction whose owner declared
more than the plan provides.

A **per-form requirement** `E_form(f)` may be checked as an additional conjunct.
It may replace the conservative cover only when the definition format version
that carries it defines the key as a complete statement of that form's target
compatibility, with evidence. Deriving a requirement from a mnemonic or an ISA
name is forbidden (`INV-01`, `INV-06`).

A per-form requirement that is not proven complete must never narrow the check.
Counterexample: a package declares `{rv64i, rv64c}`, `fmp-def/0.2`'s
`requires_extensions` for the selected form lists only `{rv64i}`, and the plan
declares `{rv64i}`. The per-form conjunct passes, yet the format does not define
the key as complete and the row may really need `rv64c`. Preferring the per-form
set would accept a form the owner cover rejects; the owner cover is therefore
required unconditionally, and the plan stays rejected until it declares `rv64c`
or the owner narrows its own declaration through a new
`source_package_digest`.

The existing `fmp-def/0.2` reader already checks a form's `requires_extensions`
against the **plan** set (`fmp-validate/src/lib.rs`, `E-TARGET-003`, step 6), so
that half is not the gap. The gaps are the remaining cases:

- `fmp-def/0.1` forms carry no requirement key, so the same `c.addi` plan passes
  the equality cell's subset replacement without a per-form check;
- even a `0.2` form's list is not defined to include the base ISA or every
  profile fact (§4.1), so a row that under-declares is caught only by the owner
  cover;
- a rule that compares the plan with the **bundle** instead of the plan target
  accepts the instruction for the wrong reason, because the bundle is wider by
  construction.

**`monasm-bundle/0.1` carries the facts; it does not apply the rule.** The sealed
bundle stores the merged definition, a sorted `packages` list whose entries also
carry the owner's declared cover (`enabled_extensions`, the same spelling the
manifest uses), and a `form_owners` list with exactly one
`{form_id, package_id}` row per merged form (§8.2). Together they give
the owner cover without reading package sources: the owner names the package,
and that package's declared cover is the `E_package` of the table above. Both
lists are inside the `bundle_digest` preimage (§7), so a cover or owner row cannot
change without changing the bundle identity.

What the artifact deliberately does **not** do is decide the subset relation. H2
builds no subset cell and runs no owner-cover check. A consumer that finds
a selected form missing from `form_owners`, an owner with no `packages` entry, or
a `packages` entry without `enabled_extensions` must treat the requirement as
**unproved** and reject; it may not read the absence as `∅` (see below).

Why the facts are frozen now rather than deferred: `monasm-bundle/0.1` has never
shipped, so there is no compatibility surface to preserve, and the alternative —
publish `0.1` as a bundle that provably cannot carry the H3 proof, then freeze a
second format whose only difference is data H2's builder already computes — would
add a version boundary with no semantic content. The counterexample is the one
below: with the map omitted, the `c.addi` plan is unprovable from any frozen H2
artifact, and the fix is a new bundle version rather than a new check. Freezing the
data now costs one extra key and one completeness rule; the rule is testable in H2
even though the consumer is H3 (§8.2).

Adding `fmp/0.2` alone is still not enough, because the plan validator sees
neither map: the owner-cover check is the new protocol's obligation. H3 reads
`form_owners` and the package cover from the bundle it already verifies and adds
the comparison; it does not need a second artifact, and it may not reinterpret the
map as something other than what §8.2 defines.

**An absent requirement means "unproved", not "needs nothing".** Treating a
missing `requires_extensions` as `∅` is the same mistake H2 refuses at the
package level: it converts unknown into "legal for every target" and lets any
subset plan select the form. For a legacy form copied from an `fmp-def/0.1`
document, the owner cover is the conservative declaration the map records. For a
form whose owner row or whose owner's cover is missing from the artifact a
consumer is reading, the default is to reject the subset composition with the new
protocol's own diagnostic (`target-subset-unproved`; it is not an `fmp/0.1` code).
A well-formed `monasm-bundle/0.1` cannot reach that state — completeness is a
format rule enforced by `--check` (§8.2) — so the case covers a damaged or
non-`0.1` artifact, and it is still a rejection rather than an empty set.
Exact-target compositions are unaffected, because every set there is equal and
the H2 rule already rejects a mismatch. H3 may accept such a form only after the
artifact supplies the proof.

**What H3 acceptance must show.** At least: the `c.addi` plan above is rejected
under the new cell; a plan whose target contains the owner cover is accepted; an
`fmp-def/0.1`/legacy form is decided from `form_owners` plus the owner cover, not
from a mnemonic; a form whose owner row is stripped from a rewritten artifact is
rejected rather than read as `∅`; and the two existing cells keep their H2
results. H2 does not implement the rule; what it freezes is the data the rule
reads, and the obligation is written here so that freezing the artifact does not
silently make H3 unprovable.

No `monasm-package/0.1` bump is required to lift the transition: the package
field already means "a cover of the extensions these rows require", and the
builder already checks the subset. H3 adds a new plan-protocol cell (with the
reference plans' target sets) and leaves the package manifest meaning, and the
two existing cells, unchanged. A new package format version is needed only if a
future target relationship is not expressible as a subset of the same extension
vocabulary.

**A new plan protocol alone does not lift the build-time check.** The builder
rejects an unequal `fmp-def/0.1` selection while it builds a spec, before any plan
is bound, so adding `fmp/0.2` cannot make such a spec build. Lifting has three
parts that must land together: a **versioned build rule** — a new
`monasm-bundle-spec` version, or an explicit versioned compatibility-relation
declaration that the builder reads — the plan-side cell above, and the
**per-instruction evidence source** (`form_owners` plus each package's declared
cover, both carried by `monasm-bundle/0.1` and bound by its digest, §8.2). The shipped
`monasm-bundle-spec/0.1` keeps its rejection conclusion permanently: the same spec
bytes must not flip from deterministic rejection (exit 1) to acceptance because
the builder was upgraded, since that would silently change what an old format
accepts. H3 acceptance must show, for a composition such as an `rv64i`-only
package with an `rv64c`/`rv64i` bundle: the old spec version still rejects the
unequal selection, the new build-rule version builds it, and the resulting bundle
binds a plan whose target set is the subset, while selecting a form whose owner
cover exceeds the plan target is rejected. The first assertion is what proves
`0.1` semantics did not drift; the second is what unblocks H5 at the builder
rather than only at the plan validator.

Counterexample if the requirement were stored as the bundle selection: adding
`rv64c` changes package A's source digest although A's rows did not change, and
the lock reports a new owner version for an unchanged instruction family.

#### 4.2 A form's ISA family must match the package target family

`fmp_model::definition::read` checks that a form ID uses a known family
(`x86`, `aarch64`, `riscv`), but it does not relate that family to
`target_identity.isa_family`. A manifest can therefore declare an `aarch64`
target while exporting `x86:mov/r64-rm/legacy`, and the merged document still
passes `read` because both facts are individually legal. The package would then
claim target isolation it does not have.

`monasm-package/0.1` fixes a general invariant, not a list of allowed families:

```text
family(form_id) == package.target_identity.isa_family
```

The builder extracts the prefix before `:` from every exported form ID and
compares it to the declared `isa_family` for equality. It does not enumerate
allowed families and does not consult a table. A mismatch is
`form-family-mismatch` (exit 1), reported before `read` is called. The same
check applies to a package's `exports.types`/`exports.profiles` when a later
package format gives them a family-bearing identity.

H2's `fmp_model::definition::read` still accepts only `x86`, `aarch64` and
`riscv`. That is the definition reader's existing check, not a new package
whitelist. When H3 extends the reader with a fourth family, a package exporting
`loongarch:add/...` with `target_identity.isa_family: "loongarch"` satisfies
this invariant without changing `monasm-package/0.1` or the builder. A genuine
alias, where the form family and the target family are different strings, is
declared by a versioned target profile rather than by adding a per-ISA branch.

Counterexample: a package with `isa_family: "aarch64"` exports an x86 form and
a matching spec; every individual check passes, the bundle target says
aarch64, and the machine form is x86. Only this equality rule rejects it.

### 5. Ownership is a table, and a conflict is an error even for identical rows

The build creates three read-only ownership tables:

```text
form_id    -> package_id + version + source_package_digest
type_id    -> package_id + version + source_package_digest   # reserved; non-empty rejected in 0.1
profile_id -> package_id + version + source_package_digest   # reserved; non-empty rejected in 0.1
```

Two packages exporting the same `form_id` fail the build even when the rows are
byte-identical (`HE-T07`, `HE-AC-09`). Last-wins would make merge order decide
which package owns the row. The same-key rule applies to every declared asset
table.

H2 executes only `form` assets. `exports.types` and `exports.profiles` are
declared in the closed manifest and enter `source_package_digest`, but a
non-empty list is rejected as `unsupported-asset`: the builder will not merge an
asset whose semantics neither this ADR nor `fmp_model::definition::read`
defines. A package that writes `"types": []` or `"profiles": []` is accepted and
records zero assets.

**The rejection is permanent for `monasm-package/0.1`.** A later builder that
"knows" the field does not make a non-empty list legal under this format: what a
document means is a property of its declared `package_format`, not of the
builder version that reads it. Otherwise the same unchanged `0.1` manifest would
change from rejected to accepted when the tool is upgraded, and a replay would
depend on which binary ran. H4 must therefore introduce an explicit later package
format (`monasm-package/0.2` or later) that states the type/profile semantics,
the ownership and conflict rules, the digest input and the validation a non-empty
list requires; `0.1` keeps `unsupported-asset` forever, exactly as
`monasm-bundle-spec/0.1` keeps its `h2-exact-target` rejection permanently
(§4.1). The reserved key names, the `{id, path}` shape, the ordering rule and the
digest input are fixed in `0.1` so the later format can reuse them without
reopening the closed key set; reusing the names is not permission to relax the
`0.1` rejection. What `0.1` freezes is the outer identity, ordering, digest input
and the rejection; the inner type/profile semantics (shared types, composed
profiles) remain H4's proposal.

Ownership rows for types and profiles are therefore reserved with the same
`{owner, version, source_package_digest}` shape but are never populated in H2.

### 6. Canonicalisation is build-time only

All outputs use `fmp_model::canonical` (sorted keys, no insignificant
whitespace, UTF-8 without BOM, no trailing newline). The merged `forms` array is
sorted by `form_id` code point. Slot, placement, modifier and excluded-array
order inside a row is preserved: that order carries bit-field meaning, and the
builder must not reorder it. This is **package-set normalisation**, not program
layout: instruction, fragment, section and fixup order stay the plan's.

The spec is a closed document whose `packages` array is already sorted by
`(package_id, version)` (§8.2). A different order is a different, invalid
document and is rejected; the builder never accepts and re-sorts an alternate
spelling. Directory-discovery order and internal set iteration never enter the
digest: the builder validates the declared order and hashes the sorted closure.
Counterexample: if a reversed spec were accepted as an equivalent input, the
format would have two legal spellings for one closure (`HE-T16`). H2 proves
order-independence by building the same legal spec under different creation and
read orders, not by accepting B+A as a second spec.

A published package version is also recorded in the append-only registry of
§8.3, so moving or reordering registry entries is rejected rather than treated
as another way to name the same release.

### 7. Digest layers, each with its own domain separator

#### 7.0 Preimage bytes are frozen

Every digest in this ADR is SHA-256 over one exact byte string. These rules are
part of `monasm-package/0.1`, not an implementation detail:

- a domain separator is ASCII without a newline, immediately followed by one
  `0x00` byte;
- `canonical(x)` is `fmp_model::canonical` over the parsed value: UTF-8 without
  BOM, keys sorted by code point, no insignificant whitespace, no trailing
  newline, integers only;
- a digest that appears as a JSON string value is the literal UTF-8 text
  `sha256:` followed by 64 lowercase hex characters. It is hashed as that text,
  never as 32 raw bytes and never as uppercase hex;
- the two bare-hash fields — `evidence/manifest.json` `files[].sha256` and a
  case `evidence.sha256` — are 64 lowercase hex characters without a prefix,
  and are the SHA-256 of the **raw committed file bytes**, including line
  endings and insignificant whitespace. They are never computed over parsed or
  canonicalised content. A CRLF/LF change, an indentation change or a trailing
  newline edit changes the digest; this applies to `NOTICE`, Markdown, oracle
  text and `tests/cases.json` alike;
- concatenation is byte concatenation; there are no length prefixes and no
  separators other than the ones written in the row.

The fixed vector below is a required H2a test in Rust and in Python. Both must
produce the stated values byte for byte; an implementation that feeds raw digest
bytes into the outer hash fails it.

**This vector is a preimage fixture, not a buildable package.** Its
`forms/example.json` is a deliberately minimal byte string:
`fmp_model::definition::read` rejects it because the form has no `slots` (and the
ID has no `/legacy`/`/vex`/`/evex` family segment), and its
`requires_capabilities: []` is therefore not a legal declaration for a package
with forms (§1.2). Any deterministic JSON bytes can serve as a SHA-256 input, so
the vector still pins the byte rules; it is never passed to `read`, never built,
and never counted as an example of a legal package. The legal end-to-end example
is the two-row §1 package in §1.2, which uses real x86 `0.1.0` rows and derives
`field-placement/v1`.

Manifest (`package.json`, canonical bytes on one line):

```json
{"definition_format":"fmp-def/0.1","dependencies":[],"exports":{"forms":[{"id":"x86:example/form","path":"forms/example.json"}],"profiles":[],"types":[]},"package_format":"monasm-package/0.1","package_id":"monasm.x86.example","requires_capabilities":[],"target_identity":{"address_width":64,"byte_order":"little","enabled_extensions":[],"execution_mode":"64","isa_family":"x86","isa_variant":"x86-64"},"target_profile":"monasm.target.x86_64","version":"0.1.0"}
```

Asset `forms/example.json` (canonical bytes):

```json
{"form_id":"x86:example/form","template":"90"}
```

The source record is `{"manifest": <the manifest above>, "assets": [{"kind":
"form", "path": "forms/example.json", "digest": "<asset digest>"}]}`. Its
canonical bytes are:

```json
{"assets":[{"digest":"sha256:dedb7fdf0544fde88996bcc92886284ac32930e99c0db6bce62ef60fedb71301","kind":"form","path":"forms/example.json"}],"manifest":{"definition_format":"fmp-def/0.1","dependencies":[],"exports":{"forms":[{"id":"x86:example/form","path":"forms/example.json"}],"profiles":[],"types":[]},"package_format":"monasm-package/0.1","package_id":"monasm.x86.example","requires_capabilities":[],"target_identity":{"address_width":64,"byte_order":"little","enabled_extensions":[],"execution_mode":"64","isa_family":"x86","isa_variant":"x86-64"},"target_profile":"monasm.target.x86_64","version":"0.1.0"}}
```

| Value | Expected |
|---|---|
| asset digest, `sha256(canonical(asset))` | `sha256:dedb7fdf0544fde88996bcc92886284ac32930e99c0db6bce62ef60fedb71301` |
| source preimage | ASCII `monasm-package/0.1`, one `0x00`, then the canonical record bytes, with no newline |
| `source_package_digest` | `sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0` |

This vector was computed independently with Python `hashlib` and .NET
`SHA256`; both produced the same 32-byte digest. It is a byte vector, not a
platform serialisation, and the prefix `sha256:` is inside the record text that
is hashed.

**A second fixed vector covers a non-empty `dependencies` array**, so the closed
dependency object of §1 is pinned at the byte level and not only in prose. The
dependency is `{"package_id":"monasm.x86.base","source_package_digest":
"sha256:231b9034ecbe6c9f806f7f2a647295e47a57cddcff47e4afacb24c98510648bf",
"version":"0.1.0"}` — canonical key order, and the digest is the
`source_package_digest` of the base package's own record, recomputed with the
same `monasm-package/0.1` preimage. The dependent manifest's canonical bytes are:

```json
{"definition_format":"fmp-def/0.1","dependencies":[{"package_id":"monasm.x86.base","source_package_digest":"sha256:231b9034ecbe6c9f806f7f2a647295e47a57cddcff47e4afacb24c98510648bf","version":"0.1.0"}],"exports":{"forms":[{"id":"x86:example/dependent","path":"forms/dependent.json"}],"profiles":[],"types":[]},"package_format":"monasm-package/0.1","package_id":"monasm.x86.dependent","requires_capabilities":[],"target_identity":{"address_width":64,"byte_order":"little","enabled_extensions":[],"execution_mode":"64","isa_family":"x86","isa_variant":"x86-64"},"target_profile":"monasm.target.x86_64","version":"0.1.0"}
```

Its form asset is `{"form_id":"x86:example/dependent","template":"90"}`.

| Value | Expected |
|---|---|
| dependency object, canonical bytes | `{"package_id":"monasm.x86.base","source_package_digest":"sha256:231b9034ecbe6c9f806f7f2a647295e47a57cddcff47e4afacb24c98510648bf","version":"0.1.0"}` |
| base package `source_package_digest` (the dependency's value) | `sha256:231b9034ecbe6c9f806f7f2a647295e47a57cddcff47e4afacb24c98510648bf` |
| dependent asset digest | `sha256:93e471b1fda937f2a3cab2b0de0d6131f347a4b967972960ca76bf4a4d7b0ccc` |
| dependent `source_package_digest` | `sha256:637edab0e19dc949bf44994d36fd703b97ecf3d9145d2648f22729b16f748251` |

Both digests were computed from the same bytes with Python `hashlib` and .NET
`SHA256`. The vector fails an implementation that renames the digest key,
drops it as optional, hashes raw digest bytes instead of the literal text, or
sorts `dependencies` by anything other than `(package_id, version)`.

| Digest | Input | Excludes | Counterexample if it were missing or collapsed |
|---|---|---|---|
| `source_package_digest` | `sha256(b"monasm-package/0.1" ++ 0x00 ++ canonical(record))`, where `record = {"manifest": manifest, "assets": [{"kind", "path", "digest"}]}` and assets are sorted by `path`; `digest` is the literal `sha256:<hex>` text from §7.0, never raw bytes; `kind` is `form`, `type` or `profile` | README, NOTICE, evidence manifest, tests, author path | Hashing only the manifest: swapping a form's template with the manifest unchanged leaves the package digest still. |
| `evidence_digest` | `sha256(b"monasm-evidence/0.1" ++ 0x00 ++ canonical(evidence/manifest.json))` when the file exists; `files[].sha256` is bare 64-lowercase-hex text per §7.0; its `files` list includes `tests/cases.json` for a release-ready package | unlisted README/NOTICE text, oracle log contents, author path; the case bytes are covered only through their manifest hash | Not hashing `tests/cases.json`: editing a plan or expectation leaves the same release identity covering two test sets. |
| `definition_digest` | `fmp_model::definition::read(merged_document).digest()`, which is exactly `sha256(canonical(merged_document))` with no domain separator | builder version, build time, host, source paths | Hashing only the package set: two different form rows produce the same bundle identity. |
| `bundle_digest` | `sha256(b"monasm-bundle/0.1" ++ 0x00 ++ canonical(bundle_metadata))`, where metadata is `{bundle_id, definition_digest, definition_format, namespace, version, target, packages: [{package_id, version, source_package_digest, enabled_extensions}], form_owners: [{form_id, package_id}]}`, packages sorted by package identity and owners by `form_id`; every nested digest is the literal `sha256:` text | the `bundle_digest` field itself, the builder receipt, package paths | Including the digest in its own preimage: the fixed point does not exist. Leaving `form_owners` or a package cover out: two bundles with the same definition but different owner/cover facts would share an identity, so the data H3 relies on would not be content-addressed and could be rewritten under a stable digest. |
| `release_digest` | `sha256(b"monasm-release/0.1" ++ 0x00 ++ canonical(release_metadata))`, where metadata is `{bundle_id, bundle_digest, definition_digest, packages: [{package_id, version, source_package_digest, evidence_digest}]}` sorted by package identity; every nested digest is the literal `sha256:` text. `evidence_digest` is present for every entry of a committed lock, which is written only for a release-ready closure (§7.1); the metadata shape admits its absence only for a development build, which is not a released identity | the definition rows themselves, the builder receipt, sealed bytes | Two releases that share a definition but ship different evidence have no distinguishing identity. |
| `builder` | `{name, version, build: Option<String>}`; lock and receipt only | the definition digest | Putting the builder version into `definition_digest`: a builder bump falsely reports definition drift (`HE-T19`). |

**`builder` records provenance; it does not prove it.** The field is outside
`definition_digest`, `bundle_digest` and the lock drift projection, so editing
`builder.version` or `builder.build` in a committed lock does not make
`verify --all --check` fail. That is deliberate — a toolchain upgrade must not
look like an execution change — but it bounds the claim: a lock names the builder
that wrote it, and the contract does not assert that the declared implementation
actually produced these bytes. A reproducibility claim needs two independent
builds; a trustworthy-provenance claim needs a separate build attestation or
release-artifact signature bound to `bundle_digest`/`release_digest`. Neither is
H2 work, and neither may be obtained by folding the builder version back into the
machine definition digest.

**`bundle_digest` is recomputable from the sealed bundle alone.** Every field of
the preimage is either a top-level key of `monasm-bundle/0.1` (`bundle_id`,
`definition_format`, `definition_digest`, `target`, `packages`, `form_owners`) or
a value the file carries inside `definition` (`namespace`, `version`), and §8.2
requires each of those to equal the definition document's value. A reader holding
only the sealed bytes therefore recomputes `definition_digest` as
`sha256(canonical(definition))`, checks `bundle_digest` against the metadata, and
compares `target.identity` with `definition.target` — no lock is needed to
establish the bundle's own identity.

The lock is still checked, but for different facts: package paths,
`evidence_digest`, `release_digest` and the builder receipt (§8). `verify --all
--check` rebuilds the pair from the spec and compares both, so a disagreement
between the sealed bundle and its lock is a difference (exit 1) even though each
is now self-verifying on its own. `bind` still takes a `Definition`, never a
bundle: self-verification establishes what the bundle says, not that a plan may
use it.

`evidence/manifest.json` is optional for a package under development and
required for a release-ready package (§7.1). Its shape is

```json
{
  "evidence_format": "monasm-evidence/0.1",
  "sources": [{ "path": "README.md", "note": "vendor manual, section 4.3" }],
  "oracle": { "status": "reproduced", "command": "llvm-mc ...", "skips": [] },
  "files": [{ "path": "NOTICE", "sha256": "..." }]
}
```

It is a closed object with exactly `evidence_format`, `sources`, `oracle` and
`files`. `sources` is sorted by `path`; every entry has exactly `path` and
`note`, and its `path` must also appear in `files`. `oracle` has exactly
`status`, `command` and `skips`; `status` is one of `reproduced`,
`manual-derivation` or `not-applicable`, `command` is a string (it carries the
reproducer or the manual rationale), and `skips` is sorted by `case_id`, each
entry having exactly `case_id` and `reason`. `files` is sorted by `path`; each
entry has exactly `path` and `sha256`. Unknown or duplicate keys are rejected.
The manifest covers `README.md`, `NOTICE`, source records, oracle records and
case evidence; it never covers a form, type or profile file. The builder
verifies that every listed file exists, stays inside the package and matches its
recorded hash; a mismatch is `evidence-mismatch` (exit 1). Editing a listed file
changes `evidence_digest` and `release_digest` only when the manifest is updated;
that keeps execution identity stable while making the audit trail reviewable.

#### 7.1 Evidence completeness for a releasable package

A package is **release-ready** when a committed spec lists it, when it is
checked with `verify --package --release`, or when `verify --all --check`
rebuilds it. `verify --package --release-evidence` enforces exactly this section
without claiming the dependency closure; `--release` adds the closure check of
§8. For a release-ready package the builder requires:

- `evidence/manifest.json` present and matching the shape above;
- `files` listing `tests/cases.json`, `NOTICE` (licence and attribution) and
  every case-evidence file referenced by `tests/cases.json`, each with a
  matching hash;
- at least one `sources` entry recording where the encoding facts came from. The
  entry's `path` is still a checked-in record inside the package (for example
  `evidence/legacy-source.md` or a manual extract); a migrated package records
  its `legacy_source` in `note`, while a new package points at a manual extract,
  vendor document, disassembly or independent assembler record under `evidence/`;
- `oracle.status` set, with `reproduced` carrying a command,
  `manual-derivation` carrying a rationale; `not-applicable` is reserved for a
  formless package, which `monasm-package/0.1` rejects (§1), so it is not a
  legal release value in H2; every skip carries a `case_id` and a reason;
- every positive and negative case in `tests/cases.json` (§9.1) carrying an
  `evidence` reference that resolves to a listed file.

Each `files[].sha256` is `sha256(raw_file_bytes)` per §7.0: line-ending,
indentation or trailing-newline edits are real changes, not normalised away. The
same rule applies to the case-level `evidence.sha256`.

A package that is **not release-ready** may omit `evidence/manifest.json`. In
that development mode `verify --package` checks each case's `evidence.path`
exists inside the package and equals the case's own `evidence.sha256`; it
computes no `evidence_digest`, and does not require `NOTICE`, `sources` or
`oracle.status`. A manifest that is present is authoritative even in
development mode: every case evidence must be listed and match, or the package
is `case-evidence-mismatch`. `--release-evidence` or `--release` with no manifest
is `evidence-incomplete` (exit 1), never a silent downgrade. Structure, assets,
`read` and the case contract are identical in the two modes; only this
release-evidence set differs.

A missing item in a release-ready package is `evidence-incomplete` (exit 1).
`evidence_digest` covers the
manifest, so `release_digest` distinguishes an incomplete release from a
complete one without moving `definition_digest`.

Because `tests/cases.json` is itself in `files`, the release identity covers the
case plans, expectations and coverage. Editing a case without updating the
manifest is `evidence-mismatch` (the recorded hash no longer matches), and
updating the manifest moves `evidence_digest` and `release_digest`. Neither edit
moves `source_package_digest` or `definition_digest`: the test contract is not a
form asset and not an execution rule, but it is part of what was released and
audited. Counterexample if the case file were unhashed: two releases could share
`release_digest` while testing different plans or expectations.

The builder does not execute the oracle. It checks presence, traceability and
hashes; the positive case compares machine output against the recorded
expectation, and the independent record is what a reviewer audits. H2 does not
claim that a recorded oracle was re-run on the build host; `tools/oracle/rerun.py`
still covers only the frozen legacy fixtures.

The builder asserts that `definition_format`, `namespace`, `version` and
`target.identity` in the bundle metadata equal the values in the generated
definition document; if they disagree, the build fails rather than recording
two identities.

Package `version` and definition `version` are different identities. A package
version bump that changes no row moves `source_package_digest` and
`bundle_digest` but not `definition_digest`; that is the intended split between
release identity and execution identity. Counterexample if the builder derived
one from the other: a no-op package release would look like an encoding change,
the same defect `ADR-0126` fixed for artifacts.

`release_digest` is the release identity: it moves when the selected package
set, the definition or the evidenced release files change, while
`definition_digest` names only the execution rules. The lock records both, so a
release can be audited without hashing documentation into the machine
definition.

### 8. Spec, lock, sealed bundle and legacy snapshot are different artifacts

- `bundles/specs/<bundle_id>.json` — `monasm-bundle-spec/0.1`, the author's
  explicit selection.
- `bundles/locks/<bundle_id>.lock.json` — `monasm-lock/0.1`, generated: the full
  bundle metadata (`bundle_id`, `definition_format`, `namespace`, `version`,
  `target`, `bundle_digest`, `definition_digest`, `release_digest`), the sorted
  package list with `path`, `source_package_digest` and `evidence_digest`
  (present for a release-ready package, §7.1), and `builder`.
- `bundles/sealed/<bundle_id>.bundle.json` — `monasm-bundle/0.1`, generated with
  exactly nine keys: `bundle_format`, `bundle_id`, `definition_format`, the
  canonical definition document under `definition`, `bundle_digest`,
  `definition_digest`, the closed bundle-level `target` `{profile_id, identity}`
  copied from the spec, the sorted `packages` list `{package_id, version,
  source_package_digest, enabled_extensions}`, and the sorted `form_owners` list
  `{form_id, package_id}` with exactly one row per merged form. It does not
  contain the builder receipt, `release_digest` or author paths. §8.2 fixes the
  completeness rules; §4.1 records that H3 applies the target-subset rule to
  these facts, and that H2 does not implement that rule.
- `bundles/legacy/<bundle_id>/definition.json` — generated when the canonical
  definition fits its 16 MiB read budget: the plain merged definition document,
  with no bundle envelope, so the existing `fmp materialize <plan> --definitions
  <dir>` path can load it. It is a derived development cache, not a release
  identity: it enters no digest, and its absence is legal. When it is committed,
  `verify --all --check` requires its canonical bytes to equal the definition
  document inside the checked sealed bundle (`legacy-snapshot-mismatch`, exit 1);
  that equality gate is not an identity input (§8.3). The write phase removes the
  previous copy before writing the new one, and a build never writes a snapshot
  larger than the read budget (§8.3): a larger canonical document is left
  uncached. `Registry::load_dir` recursively reads every `.json` under the
  directory and calls `definition::read`, so the sealed `.bundle.json` cannot be
  used here; point `--definitions` at the directory that contains only this
  snapshot.

The binary has three subcommands: `build` writes the lock and sealed bundle, plus
the legacy snapshot when the canonical document fits its read budget; `verify
--check` rebuilds the lock and sealed bundle in memory and compares them, and
compares a committed legacy snapshot with that rebuilt definition; and `digest
<package-path>` prints the computed `source_package_digest` so an author can write
it into the spec.
`verify --all` checks the bundle closures selected by `bundles/specs/*.json`;
`verify --published --check` audits the entire published registry without
selecting any package (§8.4); `verify --package <path>` checks one package
against its own manifest and does not read a spec, using the standalone identity
in §2.1. The package form checks
that `path` ends at the manifest's `version` directory, the closed key set, path
bounds, declared-vs-actual `form_id`, the form-family match (§4.2), sorted
arrays, reserved-asset emptiness, the capability allowlist, the declared
`definition_format`/`target_identity` against the merged document read by
`fmp_model::definition::read`, the pinned legacy row and legacy target when
`legacy_source` is present (§2), the cumulative asset budget (§12.1), and the
`tests/cases.json` contract (§9.1). It does not execute the cases; the
conformance harness does. It does not check ownership conflicts across packages,
because that needs a closure. It does not prove that a published snapshot is
unchanged; that is the changed-path gate in §8.1. `--release-evidence` and
`--release` additionally enforce §7.1. None of these adds a subcommand to `fmp`.

**Structure, release evidence and dependency closure are separate statuses.**
Every `verify --package` run reports both `structure` and `dependency_closure`.
`structure: verified` means the manifest, assets, `read`, cases and evidence
passed. `dependency_closure: verified` is possible only when the invocation also
supplies an explicit closure: `verify --all` uses the spec closure, and
`verify --package --closure <lock>` reads one selected lock. With no closure
input, a package whose `dependencies` array is empty is trivially
`dependency_closure: verified` (there is nothing to resolve), while a package
with a non-empty array is `dependency_closure: unverified`.

Release evidence is orthogonal. `verify --package --release-evidence` enforces
the complete §7.1 set (`NOTICE`, sources, oracle status, hashed case evidence and
`tests/cases.json`) without claiming a dependency closure. `--release` means
`--release-evidence` plus a verified closure: for a non-empty dependency array,
`--release` without `--closure` is `dependency-unverified` (exit 1), while
`--release-evidence` still exits 0 and prints `dependency_closure: unverified`.
A plain development run checks the case's own hashes (§7.1) and may also exit 0.
The standalone identity never depends on the closure, so neither status can
change `source_package_digest` or the generated `definition_digest`.

Supplying a closure does not mean trusting the file that names it. Closure
verification is **transitive**, not a direct-dependency check. Starting from the
selected package, for every `dependencies` entry, the verifier:

1. resolves the exact `(package_id, version)` entry in the lock or spec closure;
2. opens that entry's `path` under the same bounds as any package input (§12.1);
3. recomputes the package's `source_package_digest` from its manifest and
   assets, and requires equality with the closure entry and the depending
   package's declared digest;
4. recurses into that package's own `dependencies`, repeating until every
   reached package has been checked.

The lock or spec must therefore contain the whole transitive closure, not just
the direct edges. A missing entry, a package absent from `path`, a duplicate
identity with a different digest, a cycle, or any digest disagreement is
`dependency-mismatch` (exit 1). `verify --all --check` performs the same
recursive recomputation from the spec closure. A hand-written lock or spec digest
therefore cannot mint `dependency_closure: verified`; only re-reading the bytes
can. H2 packages declare no dependencies; the split and the re-read rule exist so
a later shared package cannot pass `--release` by asserting an edge it never
resolved.

**Cross-spec identity is unique.** `verify --all --check` treats the whole spec
set as one identity namespace. Two specs may not share a `bundle_id`
(`bundle-id-conflict`, exit 1) and may not share a `(namespace, version)` pair
(`definition-identity-conflict`, exit 1), even when their generated
`definition_digest` values would be equal. The reason is the existing execution
rule: `Registry::find()` requires `(namespace, version)` to name exactly one
definition and rejects two with `E-DEF-001`; two specs that both declare
`monasm.isa.x86` / `0.1.0-h2` would make a combined `Registry` ambiguous.
Identity is a release name, not a content comparison, so identical bytes do not
make the second declaration legal. H2's three specs use distinct bundle IDs and
identities. A later stage that wants two bundles to share a definition identity
must add an explicit mapping and a Registry change; H2 does not infer one.

Counterexample if only per-spec shape were checked: `a.json` and `b.json` both
declare `bundle_id: monasm.bundle.x86.example` but select different packages.
Both locks carry the same `bundle_id` with different `bundle_digest` and
`definition_digest`, so a consumer that resolves a bundle by ID cannot tell which
release it holds; if the artifact name derives from `bundle_id`, one file
overwrites the other and directory iteration order decides the survivor
(`INV-05`). For `(namespace, version)`, two specs can each verify individually
yet produce two definitions that `Registry::find` cannot distinguish.

**Frozen legacy definitions reserve their names.** The rules above cover H2's
own specs and registry, but `definitions/` predates H2 and is in neither.
`definitions/x86_64/0.1.0.json` already declares `monasm.isa.x86` / `0.1.0`; a
spec that reused those two strings while exporting a different row set would
produce a different `definition_digest` with no H2 collision and no registry row
to compare. A combined `Registry` would then hold two definitions with one
`(namespace, version)` (`E-DEF-001`), or directory order would decide which one
a reader finds.

H2 therefore treats the frozen legacy names as reserved:

- the reserved set is the set of `(namespace, version)` pairs read from
  `<root>/definitions/*/*.json`, built in sorted path order. Only those two
  strings are used; a pair claimed by two frozen files contributes one member, so
  membership never depends on iteration order; the set is recomputed on every run
  and never written, and it is not an input to `source_package_digest`,
  `definition_digest`, `bundle_digest` or `release_digest`;
- a spec whose `(namespace, version)` is in that set is `reserved-identity`
  (exit 1), the same rejection the standalone prefix uses. Reusing a legacy name
  with new bytes is not available in H2;
- a `monasm-published/0.1` `identities` row may not name a reserved pair. The
  registry records names H2 published; a legacy name was never H2's to bind;
- a matching file that cannot be read for those two name fields is a broken
  repository (exit 2), not a name that is silently skipped;
- H2 does not edit `definitions/`, so it offers no way to remove a name from the
  set.

Counterexample: a spec exports only the two mov rows under `monasm.isa.x86` /
`0.1.0`. No other H2 spec uses the pair and no registry row exists, so a
current-spec-only check sees no collision, yet the generated digest differs from
the frozen `definitions/x86_64/0.1.0.json`. Two different execution-rule
snapshots now answer to one definition name. The reserved set makes the spec
`reserved-identity`. H2's own bundles use a distinct version (`0.1.0-h2`), so
the rule costs no package a name.

**A definition identity is permanent; a bundle ID is a movable release line.**
The two names answer different questions and must not be conflated:

- `(namespace, version)` names a definition. Once a merged bundle has published
  it, the pair is permanently bound to that `definition_digest`, recorded in the
  registry (§8.3). A later spec may reuse the pair only with the identical
  digest, which in practice means republishing the same bytes; a different
  digest is `definition-identity-conflict` (exit 1), even after every spec that
  first used the pair has retired.
- `bundle_id` names a release line: a movable pointer to the current
  lock/sealed pair. Publishing `monasm.bundle.x86.example` at `0.1.0-h2` and
  later re-selecting a new package version under the same `bundle_id` is the
  ordinary publisher workflow. At most one live spec may carry the ID (§8), but
  the ID is not a content identity. The immutable **bundle content label** is
  the pair `(bundle_id, bundle_digest)`; its record is the committed lock and
  sealed bundle, which git history preserves and `verify --all --check` rebuilds
  at the commit that wrote them. A consumer that must have "the release I built"
  pins the digest, not the name.

The four digest layers answer four questions and are not interchangeable:

| Layer | Question it answers | Input | Stability |
|---|---|---|---|
| `definition_digest` | which execution rules does this definition document contain? | `canonical(merged_document)` | content-addressed; changes when any row changes |
| `bundle_digest` | which definition, package versions and package sources were selected? | `canonical(bundle_metadata)` | content-addressed; a spec that selects the same bytes always produces it |
| `release_digest` | which bundle was published with which complete evidence? | `canonical(release_metadata)`, every package entry carrying `evidence_digest` | evidence-complete release identity; changes when evidence changes even if rows do not |
| `builder` | which tool built this lock? | `{name, version, build?}` in the lock/receipt | provenance only; never enters the other three |

`(bundle_id, bundle_digest)` is the immutable **bundle content label**:
`bundle_id` may move to a new digest, so the pair is what names one content
selection. `release_digest` is the **evidence-complete release identity**: it is
what a release record pins when the audit evidence matters. H3 clients must say
which of the two they pin; pinning `bundle_id` alone pins a moving name, and
pinning `release_digest` when only machine bytes matter makes an evidence-only
change look like a different machine definition.

Counterexample if the layers were conflated: two releases select the same bundle
and definition but ship different `tests/cases.json` and evidence. Their
`bundle_digest` and `definition_digest` are equal; only `release_digest` differs.
A consumer that pinned `(bundle_id, bundle_digest)` would accept either evidence
set as the same release, and one that called `bundle_digest` "the release
identity" would report an evidence-only change as machine drift.

Counterexample if `(namespace, version)` were treated as movable: commit A
publishes `monasm.isa.x86` / `0.1.0-h2` with digest D1 and later retires it;
commit C publishes the same pair with D2 and no live spec conflicts, so a
current-spec-only check passes. Executing an old document is still safe, because
H1 binds the digest, but two different byte strings now both answer to "the
`0.1.0-h2` release", a replay of A and C cannot say which one the name meant, and
H3's runtime bundle selection would have to reopen an H2-frozen identity. The
registry makes C `definition-identity-conflict`. Reusing the *bundle* ID is not
the same case: that is the intended way to advance a release line, which is why
the immutable **bundle content label** is `(bundle_id, bundle_digest)` and not
`bundle_id` alone, while `release_digest` is the evidence-complete release
identity.

Lock and sealed bundle are committed release artifacts. CI runs
`fmp-definition verify --all --check`, rebuilds each spec in memory, compares the
sealed bundle byte-for-byte and the lock byte-for-byte **except `builder`**, and
compares a committed legacy snapshot with that rebuilt definition as a one-way
equality gate (§8.3). It
also runs `verify --published --check` (§8.4), which re-hashes every registry
entry including retired versions without selecting any package. The
changed-path job runs `verify --package <changed>` (structure) for every changed
package, `verify --package --release-evidence <changed>` for every changed
package, and the `package_conformance` test. A package whose `dependencies` is
empty also runs `verify --package --release <changed>`, so an ordinary
independent extension is held to the complete evidence bar before any publisher
selects it. A package with dependencies still gets the full evidence gate
through `--release-evidence`; its closure is verified when a spec selects it
(`--all --check`), or when the author runs `--release --closure <lock>` with an
explicit local closure. That distinction is what lets an ordinary dependent
package land without editing a global spec, while no dependent package can be
called release-verified without a re-read closure. The changed-path list is a CI
input only and never decides what the builder selects. The builder is a receipt:
it is shape-checked and printed, not compared, for the same reason `ADR-0126`
compares `payload/0.1` and not `envelope/0.1` — a correct rebuild on a different
commit must not fail the gate. Counterexample if the builder were compared: the
first commit after the lock changes `FMP_BUILD_ID` and the gate fails without any
definition change. A stale lock or sealed bundle in the compared fields is a
difference (exit 1), not a silent refresh. Counterexample if lock/sealed were
test-only: a published bundle could not be audited against the source that
produced it.

#### 8.1 The changed-path map has explicit deletion and rename rules

Mapping a changed file to "the nearest ancestor with `package.json`" is only
defined when that file still exists in the PR head. Deletion and rename need
their own rules, or a package can leave the gate silently. The gate distinguishes
the **base registry** — the entries published in the **target branch tip `B`** at
the moment the gate runs — from the **head registry**, the entries present in the
merged result tree `H` this PR proposes. Only a base entry makes a snapshot
immutable during this PR; a head-only entry is a **first publication** and is
validated, not rejected.

**The target-branch tip is the only authority for "already published".** The
merge base is not: it records where the branch forked, not what the target branch
publishes now. Let `Published(T)` be the set of version directories registered in
tree `T` and `TreeBytes_T(p)` the bytes of every file under directory `p` in `T`.
The gate runs against the PR's base-tip SHA `B` and the merged result `H` and
requires both:

```
Published(B) ⊆ Published(H)
∀ p ∈ Published(B): TreeBytes_B(p) = TreeBytes_H(p)
```

A version the target branch already publishes cannot be changed by this PR,
whatever commit the feature branch forked from. Counterexample if the merge base
were authoritative: `M0` contains `P/0.1.0` but has not published it; branch A
forks from `M0` and edits `P/0.1.0/README.md`; branch B publishes `P/0.1.0`,
appends the registry entry and merges to the target branch; A then merges. A's
merge base is still `M0`, whose registry lacks `P`, so a merge-base check treats
the edit as an unpublished candidate and accepts it. The other gates do not catch
it at merge time either: `source_package_digest` covers neither `README.md` nor
other auxiliary files. `snapshot_digest` does cover the whole directory, so
`verify --published --check` detects the edit on the next full-history audit
(§8.3, §8.4) — but detecting a violation after it merged is a different guarantee
from preventing it. Only the tip-based comparison rejects A before merge with
`published-package-modified`, and that prevention is why the changed-path gate
keeps its place even though the audit now sees auxiliary files. The merge base
remains usable for ancestry questions (which commits introduced a path) but never
for "which versions are published now".

**The verdict is valid only for the base commit and candidate tree it read.**
Let `B_checked` be the target-branch commit SHA whose registry and published
bytes the gate read, and `C_checked` the **tree SHA** of the merge result the
gate evaluated for that base and the PR head under the declared merge mode.
Record the mode too (`merge`, `squash`, `rebase` or `fast-forward`), because the
mode decides which tree a merge lands: `merge` lands
`merge-tree(B_checked, head)`, while `squash`, `rebase` and `fast-forward` land
the head tree when `B_checked` is an ancestor of the head. Commit SHAs are not
the comparison unit: every mode writes a different commit, and the ephemeral
`refs/pull/N/merge` commit is not the commit the platform finally writes. The
tree is what the gate can compare across all modes.

A merge lands commit `M` on the target branch. Let `B_landed` be the commit `M`
was applied to (first parent for a merge commit, the previous target tip for the
other modes) and `C_landed = Tree(M)`. The verdict authorizes the merge only
when:

```text
B_landed = B_checked
C_landed = C_checked
mode(M) = mode
```

The gate prints `(B_checked, C_checked, mode)`; an automated check on the landed
commit recomputes `C_landed` and `B_landed` and fails when either differs. The PR
head and merge-group commit are recorded for audit, but they are not the
authorization key, because the landed commit is a new SHA in every mode.

Without this, a correct run can still be stale in the worst way, and the tip rule
alone does not catch it:

1. branch A modifies `P/README.md` while `P/0.1.0` is unpublished; CI reads
   `B_A`, where `Published(B_A) = ∅`, and passes;
2. branch B appends the registry entry for `P/0.1.0` and merges, so the target
   tip becomes `B'` with `P/0.1.0 ∈ Published(B')`;
3. A merges on the old green result.

Evaluated against `(B', C_A')` the same diff is `published-package-modified`;
evaluated against `(B_A, C_A)` it was legal. The diff bytes did not change; only
the base moved, so `B_landed = B' ≠ B_checked` and the equations reject the
merge. Two mechanisms establish the equations without relying on a human to
merge the right commit:

- a **merge queue** that builds a merge-group candidate on the current target
  tip, runs the gate on that candidate, and merges exactly that candidate,
  rebuilding the group when the target moves; then `B_checked` is the group's
  base, `C_checked` the group tree, and `M` the group commit, so the equations
  hold by construction; or
- **merging the recorded candidate** onto the recorded base with an operation git
  refuses when the base moved — a fast-forward of the candidate commit, or an
  equivalent protected-branch merge that writes exactly that commit. The landed
  tree is `C_checked` by construction, and a moved target makes the operation
  fail instead of landing a different tree.

**Required up-to-date checks are not equivalent to either.** They make the
platform re-run checks when the base advances, which bounds staleness, but they
do not promise that the commit finally written has the tree that was tested, and
a merge commit's SHA necessarily differs from the ephemeral test-merge ref. A
setting that merely says "require branches to be up to date" therefore cannot be
cited as proof of `C_landed = C_checked`. If the repository uses that path, it
must additionally merge the recorded candidate (or run the gate on the final
candidate and merge exactly that candidate); otherwise the check is detection
only and does not authorize a publication.

The gate must print the triple and the automated check must consume it. A
verdict without the triple is not evidence; reusing a verdict whose `B_checked`
or `C_checked` no longer describes the merge is forbidden; and a manual merge
that bypasses the protected path is not a legal publication. A post-merge run on
the target branch that recomputes `Tree(M)` and `B_landed` adds detectability, but
it does not replace the equations.

This is a repository-setting requirement, and a document cannot prove a setting
by itself. The publication-channel verdict (§8.5) therefore reads the effective
branch protection or merge queue through the platform API and records the
evidence: the endpoints queried, the effective configuration, and the merge
operation the repository actually permits. **A 403, an empty ruleset list, or a
setting the API will not return is not evidence that no protection exists**; it is
an evidence step that has not been obtained, and the verdict fails until the
mechanism is shown. The ADR neither asserts nor assumes that the current
repository already has it.

**A green CI run on the planning PR is not that evidence.** N5 cannot be closed
by pointing at successful checks: they were produced for some `(B_checked,
C_checked, mode)`, and a workflow that would happily merge a different tree has
not been tested by them. The publication-channel acceptance must therefore (a)
record the effective mechanism it actually found through the API — merge queue, or
a merge operation that writes the recorded candidate and refuses a moved base —
and (b) run the stale-CI counterexample end to end on a scratch repository or an
equivalent sandbox: a green verdict for base `B_A` and tree `C_A`, a publication
that moves the target tip, and a merge attempt that must be rejected and re-run
rather than land `C_A` on the new base. A dry description of the equations, or a
settings page quoted without the operation, does not satisfy (b).

If the mechanism cannot be demonstrated, the publication verdict stops at N5 and
the publication gate stays open. A post-merge audit on the target branch remains
detection only and may not be substituted for the pre-merge authorization;
shipping H2 with "we will notice afterwards" is the failure this gate exists to
prevent. Author-layer work is not blocked by that outcome (§8.5): it simply may
not claim a published artifact.

**The base registry decides containment first.** Before the head tree is used to
resolve a `package.json` ancestor, the gate checks whether the changed path lies
under a **base-registered version directory** (`Published(B)`). If it does, the
change is `published-package-modified` (exit 1) no matter what the head tree
contains below that directory; a nested `package.json` added inside a published
snapshot is therefore itself a modification of that snapshot, not a
reclassification of the files around it. Only a change outside every
base-registered directory is mapped by the head-side rule below. This ordering is
what keeps a deeper manifest from masking an ancestor that the base registry has
already frozen.

- **Modified or added file outside every base-registered directory:** resolve the
  nearest ancestor `package.json` in the head tree. Its directory must be a
  version directory whose name equals the
  manifest's `version`; a mismatch is `path-version-mismatch` (exit 1). If none
  exists, fail with `unmapped-package-path` (exit 1); do not skip the path. If
  the version directory is in the **base registry**, it is already published and
  any modification is `published-package-modified` (exit 1). If it is absent
  from the base registry, it is a candidate: creating or editing it is legal, and
  adding its first registry entry in this same PR is also legal, provided that
  entry is sorted, selected by a head spec, and matches the final head `path`,
  `version` and recomputed `source_package_digest`; otherwise
  `published-registry-invalid` (exit 1). The final head bytes are the snapshot
  that becomes immutable when this PR merges. A spec that no longer lists the
  path does not clear this check.
- **Deleted file or directory:** resolve the version directory in the **`B`**
  tree. If that directory is in the base registry, any deletion inside it —
  including `package.json`, `NOTICE`, `tests/cases.json` or a form — is
  `published-package-modified` (exit 1); it is never a silent removal. If it is
  not in the base registry, the deletion is allowed only when the same PR removes
  or updates every spec that lists it, and `verify --all --check` proves no live
  reference remains. A deletion of an unpublished root that a spec still lists
  fails the build. A head-only registry entry whose path no longer resolves is
  `published-registry-invalid`; removing that head-only entry in the same PR is
  legal because it was never published in the base.
- **Rename or move:** check both the old and the new root. Moving a version
  directory that is in the base registry is `published-package-modified`
  (exit 1); a new version is a new sibling directory, not a move. Moving a
  candidate that is not in the base registry is legal only when its spec entry
  and any head registry entry use the final path, and §4.2 still holds. A rename
  that changes `package_id` is a new release identity, not a free move, and the
  old identity must be removed from every spec.
- **A `packages/**` change that produces no package root** (for example a stray
  file directly under `packages/`, or a deletion whose base root cannot be
  found) is `unmapped-package-path`, exit 1. It is never silently ignored.
- **A `bundles/published.json` change** is checked against the base registry:
  removing, editing, reordering or replacing a **base** entry is
  `published-registry-modified` (exit 1). Inserting a new entry is legal only
  when the resulting array is sorted by `path`, the entry is selected by a head
  spec, and it matches the package at its `path` and the recomputed digest;
  otherwise `published-registry-invalid` (exit 1). An entry that exists only in the head
  registry is this PR's first publication; it is validated against the head
  snapshot, and the merge makes it a base entry for the next PR. Removing a
  head-only entry is legal only when no head spec selects its path. A new entry
  that repeats another entry's `(package_id, version)` under a different `path`
  or digest is `published-registry-invalid` (§8.3). A selected head path without
  an entry is `published-registry-incomplete` (exit 1).

Counterexample for the base/head split: the PR that creates
`packages/x86_64/monasm.x86.mov-register/0.1.0/` must also add its registry
entry. If the gate treated any head entry as immutability, the entry would
forbid the very files it registers and no package could ever be born. If the
gate ignored the head registry instead, a PR could add an entry plus a
mismatched directory in one step; the path/digest validation above is what
rejects that. Deleting a base entry to escape is already
`published-registry-modified`, so the split does not reopen the retirement
bypass.

Counterexample for global uniqueness: the `target` directory is only a label, so
spec A selects `monasm.x86.mov` `0.1.0` at `packages/x86_64/monasm.x86.mov/0.1.0`
with digest D₁, and spec B selects the same `package_id`/`version` at
`packages/amd64/monasm.x86.mov/0.1.0` with digest D₂. Within one target directory
the injective path rule of §1.3 already forbids two paths for one identity; across
labels it does not, and each closure is internally consistent with a unique path,
so a path-only registry accepts both rows. The same logical version now has two
published contents, and a reader naming `monasm.x86.mov`/`0.1.0` can get either
definition depending on which bundle was loaded. The `(package_id, version)` rule
in §8.3 rejects the second entry.

The CI path list remains an input to which packages are checked, never an input
to what the builder selects. Deleting an unselected package still runs the
removal check; deleting a selected package fails `verify --all --check`.

#### 8.2 Spec, lock and sealed bundle are closed objects

All three are closed: unknown keys and duplicate keys are rejected (`INV-07`),
arrays are sorted as stated, and every digest value is the literal
`sha256:<64 lowercase hex>` text from §7.0. The format key is `bundle_format`
for the spec and the sealed bundle and `lock_format` for the lock, and each
carries a distinct format identifier.

**Spec** (`monasm-bundle-spec/0.1`) has exactly `bundle_format`, `bundle_id`,
`target`, `definition_format`, `namespace`, `version`, `packages`.
`target` has exactly `profile_id`, `identity`; `identity` has exactly the six
keys in §4.1, and its `enabled_extensions` uses the canonical strictly
increasing, duplicate-free spelling of §1 (`extension-lexical`, exit 1,
otherwise). `packages` is non-empty, strictly sorted by `(package_id,
version)` with no duplicates, and each entry has exactly `package_id`, `version`,
`path`, `source_package_digest`. A reversed or equal-key entry is rejected; the
builder never re-sorts an alternate spelling. The lock carries the same closed
`target` object copied from the spec, so the target has one spelling per release,
and `--check` compares those bytes rather than re-canonicalising an array. The
sealed bundle also stores the bundle-level `target` `{profile_id, identity}`, so
the `bundle_digest` preimage is complete inside the file and a consumer can
recompute it without the lock (§7, §8.2). The bundle-level target exists in two
places, the spec and the sealed file, and the lock repeats it; §8.2 requires the
sealed `target.identity` to equal `definition.target`, so the identity has one
spelling and the copies cannot disagree silently. That completeness is the
contract, not an oversight: the sealed key set is exactly the nine keys listed
below, and `sources` in it is an unknown key (exit 1).

```json
{
  "bundle_format": "monasm-bundle-spec/0.1",
  "bundle_id": "monasm.bundle.x86.example",
  "target": {
    "profile_id": "monasm.target.x86_64",
    "identity": {
      "isa_family": "x86",
      "isa_variant": "x86-64",
      "execution_mode": "64",
      "enabled_extensions": [],
      "byte_order": "little",
      "address_width": 64
    }
  },
  "definition_format": "fmp-def/0.1",
  "namespace": "monasm.isa.x86",
  "version": "0.1.0-h2",
  "packages": [
    {
      "package_id": "monasm.x86.example",
      "version": "0.1.0",
      "path": "packages/x86_64/monasm.x86.example/0.1.0",
      "source_package_digest": "sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0"
    }
  ]
}
```

**Lock** (`monasm-lock/0.1`) has exactly `lock_format`, `bundle_id`,
`definition_format`, `namespace`, `version`, `target`, `bundle_digest`,
`definition_digest`, `release_digest`, `packages`, `builder`. Its `target` is
the same closed object as the spec's. Each package entry
has exactly `package_id`, `version`, `path`, `source_package_digest` and
`evidence_digest`; a lock is written only for a release-ready closure, so
`evidence_digest` is required. `builder` has exactly `name`, `version` and an
optional `build`; when there is no build identifier the key is **omitted**,
never written as `null`. The lock drift projection is the canonical bytes of the
lock after removing `builder`; `builder` is shape-checked and printed, not
compared.

**Sealed bundle** (`monasm-bundle/0.1`) has exactly `bundle_format`, `bundle_id`,
`definition_format`, `definition_digest`, `bundle_digest`, `target`,
`definition`, `packages`, `form_owners`. `definition` is the merged definition
document of §9 (not a second envelope). `target` is the closed
`{profile_id, identity}` object copied from the spec; its `profile_id` is a
nominal bundle-local label and its `identity` must equal `definition.target`
field for field, so the bundle-level target exists in exactly one spelling in the
file and the same identity is not written twice with different bytes. Each
`packages` entry has exactly `package_id`, `version`, `source_package_digest` and
`enabled_extensions` — the owning package's declared cover, copied unchanged and
sorted under the one-array rule (§1.3), never derived or trimmed. There is no
`path`, `builder`, `release_digest` or `evidence_digest`, so `verify --check`
compares its bytes exactly, with no excluded key.

`form_owners` is a sorted array of `{form_id, package_id}`, sorted by `form_id`,
with **exactly one row per form in `definition`** and no row for a form that is
not there. Its rules:

- every `form_id` in the merged definition appears once, and every `package_id`
  names an entry in `packages`; a missing row, a duplicate row, a row for an
  absent form or an owner outside `packages` is `bundle-owner-incomplete`
  (exit 1);
- the row is attributed by the package that *exports* the form during the merge,
  not inferred from the `form_id` string, an ISA name or a mnemonic (`INV-01`,
  `INV-06`); ownership is already computed to enforce form ⊆ package ⊆ bundle
  (§4.1), so the row records a decision the builder made, not a new derivation;
- a form exported by two packages is the existing ownership conflict, rejected
  before the map is written, so the map cannot need a tie-break;
- `packages[].enabled_extensions` is the cover for every form that package owns.
  Under `fmp-def/0.1` it is the only requirement. A versioned definition format
  whose forms carry their own requirement adds that requirement as an additional
  conjunct, and may replace the cover only when that format version proves the
  per-form key complete for target compatibility; until then the cover stays
  mandatory (§4.1).

Both `form_owners` and the per-package cover are inside the `bundle_digest`
preimage (§7), so a rewritten map is a different bundle identity rather than a
same-digest edit. Completeness is checked when the bundle is built and whenever
`--check` compares it; H2 builds no subset cell, and the map is not a claim that
any particular plan is compatible with the target.

**A sealed bundle verifies itself, and is still compared with its lock.** Every
field of the `bundle_digest` preimage is in the file (§7), so a consumer
recomputes `definition_digest = sha256(canonical(definition))`, recomputes
`bundle_digest` over the metadata the file carries, and requires both to equal the
recorded values; that is a self-contained check of the bundle's identity. The pair
check is separate and does not disappear: `verify --all --check` rebuilds the lock
and the sealed bundle from the spec and requires the copies to agree, so a lock
that disagrees with the sealed bundle on `target`, `definition_digest`, `packages`
or the bundle `bundle_digest` is a difference (exit 1). A consumer that has both
artifacts must check both directions; a consumer with only the sealed file gets a
weaker but real guarantee — the bundle's own identity — and no evidence of which
package paths, `evidence_digest` or `release_digest` produced it.

`bind` still takes a `Definition`, never a bundle. Self-verification establishes
what the bundle says about itself; it does not establish that a plan may use those
rules, which stays with the caller's target check.

The following fixed vectors pin the bundle and release metadata bytes. They use
the §7.0 preimage fixture (`monasm.x86.example`, source digest
`sha256:1afee65c…`) and the pinned x86 `0.1.0` definition digest from
`tools/check_definition.py`
(`sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad`).
The fixture is not a buildable package (§7.0), so these vectors fix the metadata
shape and the domain separators, not a real bundle's identity; they are not a
claim that this is the final H2 bundle identity.

```text
bundle metadata canonical =
{"bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","definition_format":"fmp-def/0.1","form_owners":[],"namespace":"monasm.isa.x86","packages":[{"enabled_extensions":[],"package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}],"target":{"identity":{"address_width":64,"byte_order":"little","enabled_extensions":[],"execution_mode":"64","isa_family":"x86","isa_variant":"x86-64"},"profile_id":"monasm.target.x86_64"},"version":"0.1.0-h2"}
bundle_digest = sha256:a9bc3395c783e029aaeb8f362a2f806ade40cf8d965137096b26b13ac20dc5cc

release metadata canonical =
{"bundle_digest":"sha256:a9bc3395c783e029aaeb8f362a2f806ade40cf8d965137096b26b13ac20dc5cc","bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","packages":[{"package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}]}
release_digest = sha256:2416911a9c80357c40410a73db27cd1a966c73a72d354f651c95208e596ad3ad
```

The fixture declares an empty owner map and an empty cover because it has no
exported forms (§7.0); a real bundle must carry one `form_owners` row per merged
form (§8.2), so these vectors pin the key spelling, the sorting rule and the
domain separators, not a buildable identity.

Both values were computed with Python `hashlib` over the ASCII domain separator
(`monasm-bundle/0.1` or `monasm-release/0.1`), one `0x00` byte and the canonical
bytes shown. A Rust implementation and a Python check must reproduce them; a
change to the metadata shape or to the `sha256:` text rule is a format-version
change, not an edit to this vector.

The release vector deliberately omits `evidence_digest` because it uses the
§7.0 development example, which has no evidence manifest. Every entry of a
committed lock carries `evidence_digest` (§7.1), so a released bundle's
`release_digest` includes it and differs from this development-shape value. The
vector fixes the preimage shape and the omitted-key spelling, not a releasable
bundle's final identity.

A second vector fixes the **release-shaped** metadata, where every package entry
carries `evidence_digest` because that is what a committed lock holds. It uses
the same package, definition and bundle, so `bundle_digest` is unchanged —
bundle metadata never contains evidence. The evidence manifest's four file
hashes are the raw-byte hashes of these fixtures:

```text
NOTICE                    5743f7fcbdc81aa8600dca2f8bb33dd2eca8b401fbe27a015d88d746864c46c3
  = sha256("MonAsm example package. SPDX-License-Identifier: Apache-2.0\n")
evidence/legacy-source.md 520113bc00bd2912112e819e0338a65192ba25802986a691021a27cf7b38088c
  = sha256("x86_64/0.1.0: x86:mov/rm-r64/legacy, x86:mov/r64-rm/legacy\n")
tests/cases.json          fa00a63d0185a6087c8cffd3ba5e232575222d7651b13caf068c8aafc0afcc10
  = sha256("{\"cases_format\":\"monasm-cases/0.1\",\"cases\":[]}\n")
evidence/case-1.json      1200459233341d292198e50574e7690b0bb3b5ed6bc5f0d3553dffe3571df469
  = sha256("{\"case_id\":\"x86-example-pos\",\"oracle\":\"llvm-mc\"}\n")
```

The `tests/cases.json` fixture is a two-field byte string used only as a digest
input; a real release needs a case per exported form (§9.1), and this vector does
not claim that fixture is one. What it pins is the layering: the manifest bytes,
the `evidence_digest` preimage, and the release metadata with the key present.

```text
evidence manifest canonical =
{"evidence_format":"monasm-evidence/0.1","files":[{"path":"NOTICE","sha256":"5743f7fcbdc81aa8600dca2f8bb33dd2eca8b401fbe27a015d88d746864c46c3"},{"path":"evidence/case-1.json","sha256":"1200459233341d292198e50574e7690b0bb3b5ed6bc5f0d3553dffe3571df469"},{"path":"evidence/legacy-source.md","sha256":"520113bc00bd2912112e819e0338a65192ba25802986a691021a27cf7b38088c"},{"path":"tests/cases.json","sha256":"fa00a63d0185a6087c8cffd3ba5e232575222d7651b13caf068c8aafc0afcc10"}],"oracle":{"command":"tools/oracle/rerun.py --case X86-P1","skips":[],"status":"reproduced"},"sources":[{"note":"x86_64/0.1.0 rows","path":"evidence/legacy-source.md"}]}
evidence_digest = sha256:e94738716ffc56d6f1a865c463fee4afae03835d51ef234bff2c213e321f931a

release metadata canonical =
{"bundle_digest":"sha256:a9bc3395c783e029aaeb8f362a2f806ade40cf8d965137096b26b13ac20dc5cc","bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","packages":[{"evidence_digest":"sha256:e94738716ffc56d6f1a865c463fee4afae03835d51ef234bff2c213e321f931a","package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}]}
release_digest = sha256:45a4004eef811f70a02b796e8b2b8ca4cce0626c189567b2e5e9d00f0ee98767
```

Both implementations must reproduce the development vector and this one. The
difference between them is exactly whether the package entry carries
`evidence_digest`, so a tool that writes the development shape into a committed
lock fails on bytes rather than silently releasing a bundle whose evidence is
outside its release identity.

#### 8.3 The published-version registry is the permanent immutability record

`bundles/published.json` is a closed, append-only registry. It is maintained by
the release process, not by an ordinary package author, and it is the permanent
answer to "was this version ever published?", and "which definition did this
identity name?", independent of the current specs.

```json
{
  "published_format": "monasm-published/0.1",
  "published": [
    {
      "path": "packages/x86_64/monasm.x86.example/0.1.0",
      "package_id": "monasm.x86.example",
      "version": "0.1.0",
      "source_package_digest": "sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0",
      "snapshot_digest": "sha256:…"
    }
  ],
  "identities": [
    {
      "definition_digest": "sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad",
      "namespace": "monasm.isa.x86",
      "version": "0.1.0-h2"
    }
  ]
}
```

The object has exactly `published_format`, `published` and `identities`. Each
`published` entry has exactly `path`, `package_id`, `version`,
`source_package_digest` and `snapshot_digest`, sorted strictly by `path`; each
`identities` entry has exactly `definition_digest`, `namespace` and `version`,
sorted strictly by `(namespace, version)`. Either array may be empty. The sample
abbreviates `snapshot_digest`; the stored value is the literal `sha256:<64
lowercase hex>` text, as everywhere else (§7.0). Three uniqueness rules hold
across the whole registry, not only within one bundle closure:

- `path` is unique;
- `(package_id, version)` is unique;
- the first **merged** entry for a `(package_id, version)` permanently binds that
  identity to its `path` and `source_package_digest`. A later merged entry that
  reuses the pair with a different `path` or a different digest is
  `published-registry-invalid` (exit 1), never a second release of the same
  logical version.

A spec may reference an existing entry by the same `path` and
`source_package_digest` in any number of bundles; that is one published version
selected by several bundles, not two publications. Unknown or duplicate keys are
rejected (`INV-07`).

**First publication registers every existing development bundle in one
candidate.** The commit that creates `bundles/published.json` is not a place to
publish only the slice that happens to be the current milestone. It enumerates
every `bundles/specs/*.json` present at its own head, re-verifies each selected
package closure through the hardened reader a published build uses, and registers
every `published` row (`path`, `package_id`, `version`,
`source_package_digest`, `snapshot_digest`) and every `identities` row in the
same candidate. The completeness rule makes this mandatory rather than
stylistic: a spec that publishes without a row is
`published-registry-incomplete`, so registering only x86 while an AArch64 or
RV64 spec already exists cannot pass `verify --all --check`. The migration has
one legal shape whether the publication channel lands before or after the other
targets' specs: the first candidate is the whole head spec set, and a spec that
lands afterwards publishes itself in its own later PR. Development artifacts
built before V-P are re-verified by the hardened reader rather than trusted
(§8.5 rule 4), so an artifact that predates the channel is not registered on
the strength of its V-A build alone.

**`snapshot_digest` covers the whole published directory, not only the execution
assets.** The `source_package_digest` deliberately excludes `README.md`, `NOTICE`,
`tests/` and `evidence/` (§7), so it cannot answer "is this version directory
byte-identical to what was published?". The registry therefore records a second,
independent value:

```text
snapshot_digest = sha256(b"monasm-snapshot/0.1" ++ 0x00 ++ canonical(files))
files           = [{path, sha256}] for every regular file under the version
                  directory, `path` relative to that directory, sorted by `path`
```

`sha256` is bare 64-lowercase-hex text (§7.0), because this value is not an
`fmp/0.1` diagnostic input. Directories are not entries; the reader already
rejects symlinks, reparse points and non-regular leaves, so the file set is
exactly what a package reader can open. The digest is computed by `build
--release` from the version directory it just validated and printed for the
publisher, who copies it into the registry entry; it is not derived from
`source_package_digest`, `definition_digest`, `bundle_digest` or `release_digest`,
and none of those digest inputs changes because of it.

`verify --published --check` recomputes it for every entry and requires equality;
a mismatch is `snapshot-mismatch` (exit 1). That makes a modification of a
published `README.md`, `NOTICE`, case file or evidence file a registry-level
failure rather than something only the changed-path gate can see. The cost is
honest and bounded: each version directory is subject to the same per-package
byte budget as a closure (§12), and the audit's re-read bytes now cover the whole
directory, which is part of the 1,000-version measurement and its threshold.

What this still does not prove is **who** produced first the snapshot: the digest
binds the committed bytes to the recorded value, not the recorded value to an
author's intent. A publish-time attestation or artifact signature is a separate
mechanism (§7), and the registry is not one.

The `identities` array is the matching history for definition names, because the
package registry cannot answer "was `monasm.isa.x86` / `0.1.0-h2` ever published,
and with which bytes?" after its spec retires:

- the pair `(namespace, version)` is unique in the array, and its first **merged**
  entry permanently binds the name to that `definition_digest`; a later bundle
  that declares the same pair with a different digest is
  `definition-identity-conflict` (exit 1), even though no live spec still uses
  the pair;
- re-publishing the identical `definition_digest` under the same pair is legal
  and adds no second entry — byte-identical definitions are one identity, so a
  retired-and-reintroduced bundle needs no new row;
- a spec that publishes a bundle must have its `(namespace, version)` registered
  by the time `verify --all --check` runs, with the digest the merged document
  actually produces; a missing row is `published-registry-incomplete` (exit 1)
  and a digest disagreement is `definition-identity-conflict` (exit 1);
- a row may not name a pair in the reserved legacy set (§8); a row that does is
  `reserved-identity` (exit 1), because a legacy name was never H2's to bind and
  a registry entry would assert an ownership H2 does not have;
- both arrays follow the same append-only rules: inserting a new row in sorted
  position is the only legal change to a base registry, and removing, editing,
  reordering or replacing a base row is `published-registry-modified` (exit 1).
  A head-only row may be withdrawn when no head spec publishes that identity;
- `bundle_id` deliberately has no table. It is a movable release-line name
  (§8), so recording it would assert an immutability the contract does not
  claim. The immutable **bundle content label** is `(bundle_id, bundle_digest)`,
  carried by the committed lock and sealed bundle; `release_digest` is the
  evidence-complete release identity (§8).

- A version is **published** once its entry is in the registry of a merged
  commit. The current spec set does not decide publication after the fact.
- A publisher adds the registry entry in the same PR that first selects the
  version in a spec. During that PR the entry is a **candidate first
  publication**: the gate does not treat it as immutability for the files the
  same PR creates, but it must validate against the final head snapshot. After
  merge it is a base entry and the snapshot is immutable.
- `verify --all --check` requires every head-selected path to have a head entry;
  a missing entry is `published-registry-incomplete` (exit 1). An entry present
  in the target-branch tip `B` may remain after every spec retires, and must
  remain; that is exactly the `Published(B) ⊆ Published(H)` half of §8.1.
- A base entry may not be removed, edited, reordered or replaced. Any change to
  the base registry other than inserting a new entry in sorted position is
  `published-registry-modified` (exit 1). A new entry must be selected by at
  least one head spec and must match the package at its `path`; otherwise it is
  `published-registry-invalid` (exit 1). A head-only entry may be removed in the
  same PR only when no head spec selects its path. The `identities` rows follow
  the same rules, with `definition-identity-conflict` for a reused name and a
  different digest.
- Each entry's `source_package_digest` must equal the digest recomputed from the
  package at `path`, and its `snapshot_digest` must equal the digest recomputed
  over the whole version directory. A mismatch is `published-registry-invalid`
  (exit 1) for the source digest and `snapshot-mismatch` (exit 1) for the
  snapshot; any byte change under a base-published path is also
  `published-package-modified` (exit 1) when the changed-path gate sees it.
- The registry is a publication fact, not a selection input. Neither array enters
  `source_package_digest`, `definition_digest`, `bundle_digest` or
  `release_digest`, `snapshot_digest` enters none of them either, and the registry
  can never add a package to a bundle. The `identities` digest is checked against
  the built definition, never fed into it.
- Retiring a release removes a spec but never removes the snapshot or its
  registry entry. Deleting both in one PR is `published-registry-modified`, not
  a legal retirement.

**The registry is one file, and the audit cost grows with history.** H2 keeps
`bundles/published.json` as a single append-only file, so a publication edits one
path: two in-flight first publications coordinate on it, the loser rebases and
re-runs both `--check`s, and neither merges a registry edit it did not validate —
the same rebase shape as §8.1, not a merge queue for the file.

The full-history audit is `O(N_published)` in re-read packages plus every
snapshot file, independent of
the changed set, and that is the price of the permanent record. H2 accepts it as
a **measured cost, not a proven scalability property**. The publication channel
must build a
synthetic registry of about 1,000 published versions and record, for three runs
each, (a) an ordinary package change (`verify --package` plus the changed-path
gate), (b) a bundle publication (`build` and both `--check`s) and (c) the
full-history audit (`verify --published --check`, including re-hashing every
`snapshot_digest`): wall time, peak memory and
bytes read, with the machine, OS and toolchain version. Its acceptance
report records the measured curve, states the documented threshold — a version
count, a wall-time budget or a bytes-read budget — at which the single-file
registry and the full re-read audit must be revisited, and fixes a per-job CI
cost bound so the history-only job cannot silently dominate the required checks.
Crossing a recorded threshold or a CI budget overrun is the trigger for a new ADR
on sharding, incremental audit or a different registry format; it is not a
scaling property H2 may claim, and three representative packages are no evidence
that the global registry scales.

**Two scalability claims are separate, and H2 makes only the first.** They must
not be merged into "the publication flow scales":

- **Independent package authoring.** An author adds a version directory under
  their own `package_id`, writes their own spec and merges without editing another
  package or a global selection file. H2 establishes the basis — per-package
  version directories, explicit specs, no global package index, a changed-path
  gate that verifies exactly the changed package — and H5 is where concurrent
  real authors prove it end to end. H2 does not claim that proof in advance.
- **Independent publishing.** Two first publications can proceed without any
  central coordination. H2 does **not** provide this: both edit the one
  append-only `bundles/published.json`, so one publisher must rebase and re-run
  both checks after the other lands. The contract guarantees correctness under
  that serialization, not parallel throughput, and the full-history audit adds a
  cost proportional to published history. A sharded registry, an incremental
  audit or an out-of-band publication record is future work with its own ADR;
  none of them is assumed here.

The publication verdict's report therefore records concrete CI latency and
resource budgets for the
publication jobs — build, both `--check`s and the ~1,000-version audit — next to
the threshold above, and states the conditions that force sharding or incremental
audit. A localized package-change path is not evidence that the end-to-end
publication path has no central bottleneck.

**That is a scale boundary, not a performance footnote.** H2 implements
independent package development and deterministic composition; it does not claim,
and must not be read as claiming, that independent package *publication* scales
horizontally. One append-only file plus a full-history audit is the designed
limit, and any requirement for many teams to publish ISA packages concurrently is
future architecture work with its own ADR — not a tuning exercise inside H2. A
report that lists this only under "risks" would understate it: the boundary is
part of what the contract promises, and an acceptance claim that omits it is
false.

**First publication has no registry cycle.** A registry row for a definition
needs the `definition_digest`, which only a build produces; requiring the row
before the build would make the first publication impossible. The order is
therefore fixed:

```text
author writes the candidate <version>/ directory
  -> digest / verify --package computes source_package_digest
  -> author writes the spec with that digest
  -> build <spec> writes the candidate lock / sealed / legacy from the new bytes
  -> publisher appends the published row and the identities row
  -> verify --all --check and verify --published --check
  -> commit
```

`build` does not require a registry row for the path it builds. It consults the
registry only as a guard — a base-published path with changed bytes is still
`published-package-modified` — and it prints the `definition_digest` the
publisher needs for the `identities` row. It never writes the registry. The
requirement that every head-selected path has a head row belongs to
`verify --all --check`, which runs after the append; first publication is
therefore a successful `build` followed by the checks, not a fixed point.

Three moments are distinct and must not be collapsed:

1. **Candidate output.** `build` exits 0 and the lock, sealed bundle and legacy
   snapshot exist in the working tree. Nothing is published and the registry is
   untouched.
2. **Registry append.** The publisher inserts the `published` and `identities`
   rows into `bundles/published.json`, using the `definition_digest` the build
   printed. This is a working-tree edit after a successful build; while the PR is
   open the rows are candidate first publications, not publication.
3. **Publication.** The merged commit. Only then does a row become a base entry
   and the snapshot become immutable.

Both checks run between 2 and 3 and only with the rows already present:
`verify --all --check` (which requires a head row for every head-selected path)
and `verify --published --check`, and both must pass before the publisher
commits. A failed build stops the sequence at 1, so it cannot leave a row behind;
a failing check stops it before 3, so it cannot publish. The row is never
written "after a passing `--check`": `--all --check` needs the row, so that order
would be unsatisfiable and would recreate the registry cycle this section removes.

**`build` validates every output in memory and only then replaces files.** It
computes the lock, sealed bundle, legacy snapshot and every digest in memory, and
runs `read` and the byte comparison there, before it creates any output file. A
deterministic rejection (exit 1) happens before the first temporary file, so it
writes nothing and removes nothing. The write phase then removes the previous
legacy snapshot and replaces the lock, the sealed bundle and finally that
snapshot, each through a temporary sibling in the destination directory, a flush
and a rename.

**A build never writes a legacy snapshot it could not later read.** The closure
and sealed bundle budgets are far larger than the snapshot's 16 MiB read budget
(§12), so a legal bundle can produce a canonical definition above it. `build`
decides from the canonical bytes it has already computed in memory: at most
16 MiB, it writes the snapshot as above; above 16 MiB, it **omits** the snapshot,
removes any previous copy in the same write phase, and still exits 0, noting the
omission in its human-readable output. Omission is a function of the bytes, not of
the filesystem or of an earlier build, so two builds of one closure agree, and no
digest or release identity changes: the sealed bundle is the release artifact and
absence of the cache is legal. Failing the build instead is rejected because a
closure inside the §12 budgets would then be unbuildable, making a published
limit depend on a development cache. A hand-committed snapshot above 16 MiB
remains `resource-limit` (exit 1) on `--check`, because the builder cannot read it
under its own budget; `build` never produces one, so for any accepted input
`build` success implies `--all --check` passes on the tree it wrote.

An I/O or internal failure during this phase (exit 2) may leave a temporary file,
a missing snapshot, or a **pair of files from different builds**: a new lock with
the old sealed bundle, or the reverse. H2 does not claim a multi-file atomic
transaction, and it does not claim the disk never holds that state. What it
claims is that the state is **detectable and never a release**: the lock and the
sealed bundle each record `bundle_digest` and `definition_digest`, so a mixed
pair fails `verify --all --check`, and exit 2 already means "not built". A
partial write that `--check` accepts cannot exist, because acceptance requires
the committed bytes to equal a fresh rebuild of the same closure. An interrupted
write therefore leaves only two consistent states — both new (a valid build with
the cache possibly missing) or both old (the previous build, with the new files
not yet renamed into place) — plus states that `--check` rejects.

**Output directories are trusted inputs with a checked path, not a sandbox.**
`bundles/locks/`, `bundles/sealed/` and `bundles/legacy/` are
publisher-controlled repository paths; H2 does not claim to defend against
another process swapping a directory between the check and the rename. What it
does require is that the §3 no-follow rule covers **every output parent segment**
under `--root`: a committed symlink or reparse point anywhere on the path to the
temporary file is `path-escape` (exit 1) and nothing is written; the temporary
file is created in the destination directory and renamed over the exact expected
entry name of §1.3. Repository contents therefore cannot redirect a write out of
the tree. That is the boundary H2 states, and N1 tests it with a symlinked output
directory.

`verify --all --check` reads the committed lock and sealed bundle through a
bounded reader and compares bytes **as they stream** against the in-memory
rebuild: the lock is limited by the 1 MiB lock budget and the sealed bundle by
the 80 MiB budget of §12. Neither is loaded with an unbounded `read_to_end`, and
a committed file longer than its budget is `resource-limit` (exit 1) — the same
deterministic rejection a package input gets, not a host error. A committed
legacy snapshot is read the same way, within 16 MiB, for the equality gate below;
it is never parsed as a second definition authority and never `read_to_end`.

`verify --all --check` proves the release artifacts: the committed lock and the
sealed bundle, rebuilt from the exact selected closure. It does **not** put the
legacy snapshot into any digest: that snapshot is not part of `bundle_digest`,
`definition_digest` or `release_digest` (§7), and its absence is legal. But a
committed snapshot is still a claim about this bundle — the tree ships a
`definition.json` that `fmp materialize --definitions` will load — so the check
also **compares it with the definition document inside the just-verified sealed
bundle**: the committed file must be byte-identical to the canonical
serialization of the sealed bundle's `definition` object. Different bytes are
`legacy-snapshot-mismatch` (exit 1). The snapshot is read through the same bounded
reader and 16 MiB budget as a pinned legacy definition (§12), never as an identity
input. The direction is one-way: a tree whose bridge disagrees with its release
pair fails, and no bundle identity ever depends on the cache.

That equality gate closes the gap a digest cannot: the sealed definition and the
CLI-readable definition must be the same document, so editing only
`bundles/legacy/<bundle_id>/definition.json` — no spec, lock, sealed bundle or
package change — makes `verify --all --check` red even though every recorded
digest still matches. Counterexample if the snapshot were left out of the check: a
correct build, then one changed opcode in the committed snapshot, then a green
`--check`, and the documented compatibility path reads a definition the release
pair does not contain.

Removing it before the rewrite and writing it last keeps the interrupted-write
story simple: an exit-2 write leaves it absent, which passes because absence is
legal, so the next `--definitions` read fails loudly instead of returning the
previous build's rows. A stale snapshot from an interrupted write now fails the
equality gate instead of being silently readable; both outcomes are "not a
successful release". Counterexample if the legacy snapshot were written in place
before the lock: a crash after the new lock and sealed bundle but before the
legacy write leaves a snapshot from the previous build next to a consistent new
release pair, and the equality gate reports it rather than letting a developer
attribute old rows to the new bundle. Counterexample if `--check` had to rebuild
the legacy snapshot from source: the release gate would depend on a derived
cache's provenance and a cache regeneration would become a release event. The
equality gate does neither; it compares the committed bytes with the definition
already rebuilt for the sealed bundle, so there is no second build path. Git
supplies repository-level atomicity; `build` supplies "exit 0 means every output
was validated before any was written".

Counterexample if `build` required its own registry row: the row needs
`definition_digest`, which needs the build, so a first publication could never
start. Counterexample if `build` wrote outputs as it computed them: a failure
after the lock but before the sealed bundle leaves a lock that names a
`bundle_digest` no current sealed file has, and a reader that trusted the exit
code or the lock alone would report a release that was never built.

Counterexample if the registry were replaced by "the current specs": PR A
removes the last spec that selects `0.1.0/`, then PR B modifies that directory.
Both the base and head trees of PR B contain no selecting spec, so a spec-only
check would call the snapshot unpublished and accept the edit. The registry
entry survives PR A, so PR B still fails `published-package-modified`.

Counterexample if first publication were treated as immutability: the x86
publication PR
creates `packages/x86_64/monasm.x86.mov-register/0.1.0/` and its first registry entry
together. A rule that rejects any file under a head-registered path rejects the
package's own creation, so the format could only be published by a second PR that
adds the files after the entry — which the digest check forbids. The base-only
rule lets one PR create and register the version, and the head validation makes
the merged bytes the immutable ones.

Counterexample if only packaged versions were registered: A publishes
`monasm.isa.x86` / `0.1.0-h2` with D1, B retires the spec, C publishes the same
pair with D2. B removed the only spec, so a current-spec check in C sees no
collision; the package registry is untouched because no package changed. Without
the `identities` row, two byte strings are both "the `0.1.0-h2` release", and a
replay of A and C cannot be told apart by the name the format published. With
the row, C's build fails `definition-identity-conflict`. Registering the
`bundle_id` instead would not help: the same ID is expected to advance to a new
definition when the publisher selects a new package version, so the conflict
would fire on the normal workflow.

#### 8.4 Bundle verification and publication history are separate commands

Two questions must not be conflated:

- **Bundle verification** (`verify --all --check`) answers "does each current
  spec rebuild its committed lock and sealed bundle from the exact selected
  closure, and does a committed legacy snapshot equal that definition?" It reads
  the paths selected by `bundles/specs/*.json`, the directory entries under
  `bundles/locks/`, `bundles/sealed/` and `bundles/legacy/` that enforce the
  one-to-one artifact rule below, and the registry facts needed to decide
  publication and validity for those paths. It never opens an unselected package,
  so an unselected package cannot change its result (`HE-AC-05`).
- **Publication-history audit** (`verify --published --check`) answers "is every
  published entry still valid?" It reads every entry in
  `bundles/published.json`, including versions that no current spec selects, and
  checks the closed shape, sorted order, unique `path`, unique
  `(package_id, version)`, the identity binding, that the path exists and is a
  version directory, that the manifest's `package_id`/`version` match the entry,
  that the recomputed `source_package_digest` equals the recorded one, and that
  the recomputed `snapshot_digest` covers the same bytes as the recorded value. It
  also checks the `identities` rows: unique and sorted `(namespace, version)`,
  one digest per name, no row naming a reserved legacy pair (§8), and — for a
  name that a current spec still publishes — agreement with the digest the
  current build produces; disagreement is `definition-identity-conflict`
  (exit 1), a missing row for a published spec is
  `published-registry-incomplete` (exit 1). A package-entry mismatch is
  `published-registry-invalid` (exit 1); a directory/manifest version disagreement
  is `path-version-mismatch` (exit 1). The audit never selects a package into a
  bundle and never changes a lock or sealed bundle. The changed-path gate (§8.1)
  still reports the underlying file edit as `published-package-modified`; the audit
  reaches the same bytes through `snapshot_digest` and reports
  `snapshot-mismatch`, so neither gate depends on the other to notice the edit. The audit applies the §12
  per-package byte and count budgets to each entry it re-reads; it has no closure
  aggregate because it is not a bundle.

CI runs both once the publication channel exists. If only `--all --check` ran, a retired version with no selecting
spec would never be re-hashed. If the audit were folded into `--all`, every
bundle build would read every historical package and an unrelated retired package
could break an old spec, which is the discovery coupling H2 removes.

The audit's cost therefore grows with published history rather than with the
changed set. §8.3 fixes the 1,000-version measurement and the threshold that
triggers a new ADR, so neither gate may be described as a constant-cost check.

**A derived artifact exists only while its spec exists.** A lock, a sealed
bundle and a legacy snapshot are outputs of one spec, not independent releases.
When a PR removes the last `bundles/specs/<bundle_id>.json`, the same PR removes
`bundles/locks/<bundle_id>.lock.json`, `bundles/sealed/<bundle_id>.bundle.json`
and `bundles/legacy/<bundle_id>/`. `verify --all --check` enforces the
one-to-one rule in both directions: every lock, sealed bundle and legacy
snapshot in the tree names a spec that exists in the same tree, and each spec
still needs its committed lock and sealed bundle, so a missing one fails the
check as before. An artifact with no spec is `orphan-bundle-artifact` (exit 1).
The rule is about directory entries, not package selection: it never opens an
unselected package and changes no digest, so `HE-AC-05` is unaffected. Retired
bytes stay replayable at the commit that published them, and the permanent
record — the immutable package snapshot and its registry entry — is untouched.

Counterexample if the rule were left out: the last spec for `bundle_id` is
removed but its sealed bundle stays in the tree. `--all --check` skips it
because no spec selects it, and `--published --check` never reads locks or
sealed bundles at all, so a hand-edited or stale sealed file would sit in the
repository looking like a release while no gate rebuilds it or can say whether
its bytes are the ones that were published. A reader that pointed at it would be
trusting an unselected artifact whose status the contract never defined.
Defining an archive format instead is rejected for H2: it would add a second
lifecycle and a second gate for bytes whose only remaining reader is git
history, and the package snapshot plus registry already carry every permanent
fact (§8.3).

**The audit's guarantee is whole-directory, and the contract states what it still
does not prove.** `verify --published --check` re-hashes every regular file under
each published version directory through `snapshot_digest` (§8.3), so editing a
retired package's `tests/cases.json`, `evidence/**`, `NOTICE` or `README.md`
changes the computed value and fails the audit with `snapshot-mismatch` (exit 1),
independently of any changed-path gate. The `source_package_digest` check remains
narrower on purpose: it names the execution input, while the snapshot names the
release directory.

Two things stay outside what the registry can attest:

- **who produced the first snapshot.** The digest binds committed bytes to the
  recorded value; it does not bind that value to an author's intent, a builder
  implementation or a review. A publish-time attestation or artifact signature is
  a separate mechanism, and `builder` is not one (§7).
- **history rewrite.** Appending is checked against the parent commit's registry
  and the changed-path gate rejects edits under a published path (§8.1). A
  force-push that rewrites the branch, or a direct push that bypasses the gate,
  defeats both. Preventing that is the platform's job and is exactly what the
  publication-channel verdict must demonstrate (§8.5), not something an in-repo
  digest can prove.

The changed-path gate is therefore still required — it rejects the edit before it
lands and reports `published-package-modified` — but it is no longer the only
thing standing between a published file and a silent modification. An in-repo
check that could only detect changes when a separate, externally configured gate
allowed it to see them would be a weaker claim than "the registry records an
immutable snapshot", and H2 does not make that weaker claim.

#### 8.5 Two acceptance verdicts, not one gate

The H2 work bundles capabilities that do not depend on each other. Reading a
package from a trusted working tree and computing the same bytes from the same
inputs is one capability; ingesting an untrusted tree without following a link,
proving that the merged commit is the tested candidate, and auditing permanent
history is another. The first is a data-model and determinism claim; the second
is a publication-safety claim whose prerequisites include platform facts that no
in-repo test can manufacture.

H2 is therefore accepted through **two verdicts**, recorded separately:

- **V-A, author layer.** `monasm-package/0.1` shape and lexical rules, reading a
  package from a trusted tree, closure and dependency digest checks, merge and
  ownership, the four digest layers with their fixed vectors, cases and evidence
  protocol, conformance, Level 0/1 projections, build determinism and byte
  equality, the build write phase with its bounded streaming comparison, the
  legacy-snapshot equality gate, `verify --package` and `verify --all --check`
  over the committed specs. V-A has no external prerequisite and does not wait
  for V-P.
- **V-P, publication channel.** The hardened reader (open-time no-follow, exact
  directory-entry names, replacement-race binding, regular-file-only leaves) with
  its three-platform PoC, `bundles/published.json` with `identities` and
  `snapshot_digest`, append-only and retirement rules, the full-history audit,
  the changed-path gate, the merge-freshness proof with the executed stale-CI
  counterexample (§8.1), and the ~1,000-version measurement with its threshold.

The ordering rules are part of the contract, because either misordering would be
a false claim:

1. V-A work may proceed while V-P prerequisites are open. A single external API
   returning 403 must not block the data model, the digests, the determinism
   tests or the first real package.
2. No artifact is **published**, and no wording calls one immutable, trusted or
   released, until V-P passes. Until then a lock, sealed bundle or legacy
   snapshot is a development artifact: reproducible, checked for internal
   consistency, and explicitly not a publication record.
3. `bundles/published.json` does not exist before V-P. Creating it early would
   assert an immutability the channel cannot yet enforce, and `verify --published
   --check` is not a CI gate before then. While no registry exists on either the
   base commit `B` or the head `H`, `verify --all --check` verifies the lock,
   the sealed bundle and the legacy equality gate and reports every selected path
   as a **development artifact**; it does not report
   `published-registry-incomplete`, because nothing claims to be published. A
   branch whose base `B` has a registry cannot use that state: deleting or
   bypassing it is `published-registry-modified`, and from then on every
   head-selected path needs a head row (§8.1, §8.3).
4. A development artifact is not promoted by relabelling. The first V-P
   publication rebuilds its inputs through the hardened reader, or re-verifies
   them with it, even when the bytes are identical to a V-A build. The first
   candidate is **all-or-nothing over its head spec set**: it registers every
   selected package closure and definition identity in that one commit, not only
   the initial x86 slice (§8.3).
5. V-P failure stops the publication claim and the H2 exit, not the author layer.
   No post-merge audit, green CI run or after-the-fact review may substitute for
   a V-P prerequisite (§8.1).

This is a scheduling split, not a weaker security rule. Every no-follow, naming
and race requirement keeps its full strength; what changes is that only the
publication claim depends on them, and that claim is not made until they are
demonstrated.

### 9. The builder generates bytes and lets `fmp_model` read them

The builder merges the declared form objects into a definition document, sorts
`forms` by `form_id`, serialises canonically, and calls
`fmp_model::definition::read`. Before that merge it builds each selected
package's document from that package's own rows and its own `target_identity`,
and reads it under the package's `definition_format` (§4.1), so a package that
is only legal because the bundle selected more extensions is rejected rather
than silently admitted. `read` remains the only authority for form
fields, slot placement, template length, duplicate IDs and target shape. The
builder wraps a rejection as its own `BuildError`, preserving the underlying
diagnostic text. It does not construct `Definition` directly and does not call
`Registry::load_dir`.

`verify --package` follows the same rule: it merges the declared assets into a
document with the package's `definition_format`, calls
`fmp_model::definition::read`, and compares
pinned rows only when `legacy_source` is present. It never calls a case's
`fmp_model::plan::read`, `bind` or `materialize`, and never writes a lock or
sealed bundle, so a package author can run it before any spec exists.

**Every digest and every consumer sees one loaded package.** A package is read
once, through the no-follow opens of §3, into one immutable in-memory value:
the canonical manifest, the declared asset bytes and their per-file hashes. That
value is the sole input to `source_package_digest`, to the `legacy_source` row
and target comparison, to the per-package `read` of §4.1, and to the merge that
produces the definition. The builder does not re-open a path after hashing it,
does not hash one buffer and merge another, and does not read a package once for
`verify --package` and again for the bundle. The pinned legacy definition is
loaded once in the same way, and both the target comparison and the row
comparison consume that one value.

Counterexample: the builder reads `forms/mov.json` as A and computes
`source_package_digest = D0`, then an editor or build script replaces the file
with B before the merge. A second open reads B, the merged definition contains
B's opcode, and the lock records D0. The lock now attests a source digest for
bytes the definition never contained; replaying from the published bytes gives
D1 and cannot reproduce the bundle. With one loaded value the second read does
not exist: a change before the read is part of the bytes that are hashed and
merged, and a change after it cannot be observed by this build.

`fmp-definition`'s product dependencies are `fmp-model` and at most one pinned
path-safety layer whose only job is the no-follow open of §3. It does not depend
on `fmp-validate` or `fmp-materialize`, and the path layer does not parse a
package, a definition or a digest. The package
conformance harness lives in `fmp-definition/tests/` and uses dev-dependencies
on `fmp-validate`, `fmp-materialize` and `fmp-plan`; that does not change the
product graph. A runtime dependency on the materializer would let the builder
"verify" by encoding, which is a second authority and mixes the development and
execution phases.

#### 9.1 Package cases and evidence are a merge gate

`read` proves that a row is structurally legal; it cannot prove that an opcode or
a register field matches the hardware. A package gate that stops at `read` would
accept a syntactically valid row with the wrong opcode. The ordinary-extension
gate therefore has two parts: the builder validates the case contract, and the
conformance harness executes it.

**Discovery.** A package with a non-empty `exports.forms` must contain
`tests/cases.json`, `monasm-cases/0.1`, at its root. That exact path is the only
discovery point; there is no central case list, no per-ISA test registry and no
filename convention beyond this one. A package without the file is rejected with
`missing-cases` (exit 1), and a form with no case is `uncovered-form` (exit 1).

```json
{
  "cases_format": "monasm-cases/0.1",
  "cases": [
    {
      "case_id": "riscv-add-rs2-low",
      "form_id": "riscv:add/rd-rs1-rs2",
      "instruction_id": "I0001",
      "kind": "positive",
      "plan": {
        "format_version": "fmp/0.1",
        "target_identity": {
          "isa_family": "riscv",
          "isa_variant": "rv64",
          "execution_mode": "n/a",
          "enabled_extensions": ["rv64i"],
          "feature_constraints": [],
          "byte_order": "little",
          "address_width": 64
        },
        "definition_identity": {
          "namespace": "$standalone",
          "version": "$standalone",
          "digest": "$standalone"
        },
        "output_contract": {
          "artifact": "bytes",
          "section_order": [".text"],
          "fixup_record_order": "section_id,offset,fixup_id",
          "include_symbol_table": false,
          "emit_fixups": true
        },
        "sections": [
          {
            "section_id": ".text",
            "section_kind": "code",
            "image_backed": true,
            "declared_size": 4,
            "fragments": [
              { "offset": 0, "size": 4, "kind": "instruction", "instruction_id": "I0001" }
            ]
          }
        ],
        "symbols": [],
        "instructions": [
          {
            "instruction_id": "I0001",
            "section_id": ".text",
            "offset": 0,
            "form_id": "riscv:add/rd-rs1-rs2",
            "operands": [
              { "role": "dest", "kind": "riscv.xreg", "target_type": "xreg", "payload": { "reg": 10 }, "modifiers": [] },
              { "role": "src", "kind": "riscv.xreg", "target_type": "xreg", "payload": { "reg": 11 }, "modifiers": [] },
              { "role": "src2", "kind": "riscv.xreg", "target_type": "xreg", "payload": { "reg": 12 }, "modifiers": [] }
            ],
            "expected_size": 4
          }
        ],
        "fixups": []
      },
      "expect": { "format_version": "fmp/0.1", "level": 0, "bytes_hex": "…", "size": 4, "fixups": [] },
      "evidence": {
        "kind": "oracle",
        "path": "evidence/riscv-add.oracle.txt",
        "sha256": "…"
      }
    },
    {
      "case_id": "riscv-add-rs2-range",
      "form_id": "riscv:add/rd-rs1-rs2",
      "instruction_id": "I0001",
      "kind": "negative",
      "scope": "form",
      "baseline_case_id": "riscv-add-rs2-low",
      "mutates": "/instructions/0/operands/2/payload/reg",
      "plan": { "…": "the baseline plan with src2 reg 32" },
      "expect_error": {
        "stage": "bind",
        "diagnostics": [
          {
            "code": "E-OPERAND-004",
            "path": "/instructions/0/operands/2/payload/reg"
          }
        ]
      },
      "evidence": {
        "kind": "manual-derivation",
        "path": "evidence/riscv-rs2-range.manual.md",
        "sha256": "…"
      }
    }
  ]
}
```

The document is closed: exactly `cases_format` and `cases`; cases are sorted by
`case_id` and unique. A positive case has exactly `case_id`, `form_id`,
`instruction_id`, `kind`, `plan`, `expect` and `evidence`. A negative case has
exactly `case_id`, `form_id`, `instruction_id`, `kind`, `scope`, `plan`,
`expect_error` and `evidence`, plus `baseline_case_id` and `mutates` when
`scope` is `form`. `scope` on a positive case, or `expect` on a negative one, is
a schema error. Every `form_id` must be exported by the package, and every
exported form needs at least one positive case and at least one `scope: "form"`
negative case.

**The plan is a complete `fmp/0.1` document.** There is no separate DTO and no
translation layer. Its `definition_identity` must be exactly the sentinel
`{"namespace":"$standalone","version":"$standalone","digest":"$standalone"}`;
any other value is `case-plan-identity` (exit 1). The harness replaces the
sentinel with the §2.1 standalone identity, calls `fmp_model::plan::read`, and
executes the rest of the document verbatim. `fmp-plan` may be used to generate
the inline text, but it is never the interpreter of a shipped case.

**The declared form must be the executed form.** `plan.instructions` has exactly
one entry; its `instruction_id` equals `case.instruction_id` and its `form_id`
equals `case.form_id`. A mismatch is `case-form-mismatch` (exit 1). This is what
prevents a case from claiming form B while the plan actually encodes form A.
Positive cases must use that instruction's encoding, and their expected
projection is compared after `materialize`.

**Negative cases declare a scope and a complete diagnostic set.** `scope` is
`form` or `plan`:

- `scope: "plan"` is an ordinary rejection. It may target any deterministic
  `fmp/0.1` failure the case document can express, including a wrong
  `expected_digest`, a bad section layout, a target mismatch, or a value
  `fmp/0.1` cannot represent. A definition-identity mismatch is **not**
  expressible as a case: every case's `definition_identity` must be the
  `$standalone` sentinel, and the harness substitutes the correct standalone
  identity, so a wrong digest is `case-plan-identity` (exit 1) before execution
  and no case-level override exists. The H2 binding test that mutates a derived
  plan's digest carries that negative instead (§4.1). It declares
  `stage: "read"` when `fmp_model::plan::read` is the
  rejecting stage, and `"bind"` or `"materialize"` when the document reads and a
  later stage rejects. It is validated and executed, but it does not count toward
  a form's negative coverage.
- `scope: "form"` is the illegal-neighbourhood test for one exported form. It
  must name a `baseline_case_id` that is a positive case in the same file with
  the same `form_id` and `instruction_id`, and a single `mutates` pointer. A
  missing baseline, a baseline of another kind, form or instruction, or a
  `scope: "form"` case without both keys is `case-baseline-invalid` (exit 1).
- `mutates` must match
  `^/instructions/0/operands/[0-9]+/(payload(/[^/]+)*|kind|target_type|modifiers(/[0-9]+(/name|/value)?)?)$`.
  That is the form-constraint surface: an operand value, operand kind, target
  type or modifier. A mutation at `expected_digest`, `form_id`, `offset`,
  `section_id`, `expected_size` or `output_contract` is not a form-neighbourhood
  test; it must use `scope: "plan"` or is `case-mutation-mismatch` (exit 1). A
  mutation at `definition_identity` is neither: the sentinel rule and harness
  substitution make an identity mismatch inexpressible, so it belongs to the
  derived-plan binding test, not to any case scope.
- A modifier is an object `{"name": …, "value": …}`, so changing only its value
  has the pointer `/instructions/0/operands/<n>/modifiers/<i>/value`; that is a
  legal single mutation, as is `…/modifiers/<i>/name` when the name change leaves
  the pair unpermitted. The validator reports an unpermitted modifier at the
  modifiers array (`E-OPERAND-003` at `…/modifiers`), which is an ancestor of
  either pointer and therefore satisfies the location rule below. A kind change
  at one modifier reports `…/modifiers/<i>`, which the pattern admits as well;
  adding or removing a modifier changes the array length, so the diff reports the
  array itself (`…/modifiers`), and that is a shape change rather than a
  field-value change.
- The harness compares the baseline plan and the case plan as canonical JSON
  trees. The difference is defined over the two **final values**, not over the
  authoring operations that produced them, and one recursive function fixes it
  so two implementations report the same pointer set:
  1. equal values produce no pointer;
  2. two values of different JSON kinds (object, array, string, number,
     boolean, null) → the pointer of that position, because the value itself
     was replaced;
  3. two objects → for every key present in only one of them, the pointer of
     that key (the whole value under it is the difference); for every key in
     both, the recursive result;
  4. two arrays of different length → the pointer of the array itself, because
     the shape changed; equal length → the recursive result for each index;
  5. two scalars of the same kind that differ → the pointer of that position.

  The function cannot recover which edit was performed. Rewriting a whole
  object in an editor and changing one of its members produce the same pair of
  documents and therefore the same pointers, and the format does not try to
  distinguish them. Two consequences fix the earlier ambiguity:

  - `{"payload":{"reg":10}}` → `{"payload":{"reg":11}}` reports
    `/instructions/0/operands/2/payload/reg`, **not** `/…/payload`;
  - `{"payload":{"reg":10}}` → `{"payload":{"value":10}}` reports
    `{/instructions/0/operands/2/payload/reg, /instructions/0/operands/2/payload/value}`,
    which is two differences and therefore not a single mutation.

  Adding or removing one object member reports that member's pointer, not the
  object; changing an array length reports the array; only a **kind change** at
  a position reports the position itself. A fixed vector pins the last case:
  `{"payload":{"reg":10}}` → `{"payload":10}` reports
  `/instructions/0/operands/2/payload`. The result is a property of the two
  documents, not of a diff library's traversal order.
- The set of differing JSON Pointers must be exactly `{mutates}`; any other
  difference, a no-op mutation, a mutation that changes `form_id`, or a
  two-pointer difference of the kind above is `case-mutation-mismatch` (exit 1).
  This stops an author from changing half the plan and calling the result a form
  test. A mutation whose intended semantic is "replace the payload object" must
  therefore be expressed as a change that leaves exactly one pointer — for
  example replacing the payload's kind, or changing one of its members — or it
  is not a legal form-scope mutation.
- A `scope: "form"` case must be rejected by **`bind`**, so its
  `expect_error.stage` must be `bind`. `stage: "read"` or `"materialize"` on a
  form-scope case is `case-error-scope` (exit 1): a value the reader refuses
  never reaches an operand-slot decision, and a post-encode assertion is not
  operand-legality evidence.
- At least one declared `(code, path)` must point at the mutated operand
  surface: `path` equals `mutates`, or is a prefix of `mutates` bounded at a `/`
  and no shorter than `/instructions/0/operands/<n>` (the operand object, its
  payload object or its modifiers array). A diagnostic only at
  `/instructions/0/expected_digest`, `/expected_size`, `/definition_identity` or
  another instruction field is `case-error-scope` (exit 1) and does not count as
  form coverage.
- A form-scope case may not declare `E-BYTE-001` or `E-SIZE-001`. Those check
  emitted bytes or size, not whether an operand is legal. The concrete
  counterexample is a legal `reg = 0` → `reg = 1` mutation that leaves the old
  `expected_digest`: `bind` accepts it, encoding produces different bytes and
  materialization returns `E-BYTE-001` at
  `/instructions/0/expected_digest` (`fmp-materialize/src/lib.rs`,
  `expected_digest` check). Such a case is `scope: "plan"` or invalid as
  form-scope; it must not satisfy `uncovered-form`.

`expect_error` is a closed object over exactly `stage` and `diagnostics`:

```json
{
  "stage": "bind",
  "diagnostics": [
    { "code": "E-OPERAND-004", "path": "/instructions/0/operands/2/payload/reg" }
  ]
}
```

`stage` is `read`, `bind` or `materialize`. `diagnostics` is a non-empty array
sorted by
`(path, code)`, unique, and each entry is a closed object over exactly `code`
and `path`. The `package_conformance` harness projects the observed diagnostics
to `(code, path)`,
sorts them by `(path, code)`, and requires **set equality** with the declared
array: same length, same members, no duplicates. One matching error among
others is a failure (`case-diagnostics-mismatch`, exit 1). Detail maps are not
part of the case contract; the complete set of `(code, path)` pairs is.

The observed set is the full array returned for that stage:

- `stage: "read"`: after the sentinel substitution the harness calls
  `fmp_model::plan::read`; it must reject the document, and the observed set is
  the singleton `(code, path)` of the single `Diagnostic` `read` returns (the
  reader reports one fault, not a collected array). A document `read` accepts is
  `case-error-scope` (exit 1). This stage is legal only for `scope: "plan"`; a
  form-scope case using it is `case-error-scope` (exit 1).
- `stage: "bind"`: `plan::read` must accept the document; `bind` returns all
  diagnostics. Any array, including an empty one, is compared as-is.
- `stage: "materialize"`: `bind` must return zero diagnostics. Only
  `PostEncodeAssertion(diagnostics)` can satisfy the case; `Internal` or
  `HostFailure` is `case-materialize-fault` (exit 2), never a pass. This stage is
  legal only for `scope: "plan"`; a form-scope case using it is
  `case-error-scope` (exit 1).

Those three bullets are one rule: **the declared stage is the first stage that
rejects the document.** A plan-scope case whose declared stage accepts, or whose
earlier stage already rejects, is `case-error-scope` (exit 1) and is evidence for
nothing. `read` is not a second name for `bind`, and a read rejection cannot be
dressed as a bind rejection: `bind` never receives a `Plan` the reader refused.

**A declared stage is a static claim until conformance executes it.**
`verify --package` checks only the declaration's static contract: the value is
one of `read`/`bind`/`materialize`, a form-scope case declares `bind`, a
plan-scope case uses a stage its scope permits, `diagnostics` is non-empty,
sorted, unique and closed over `code`/`path`, the `mutates` pointer is on the
allowed operand surface, and the baseline-to-case diff is a single pointer. It
does **not** call `plan::read`, `bind` or `materialize`, so it cannot prove which
stage rejects first or that the observed set equals the declared set.
`package_conformance` executes the case and proves both. A case that declares
`stage: "bind"` while `plan::read` actually rejects it passes the static document
check and must fail conformance with `case-error-scope`; it is never valid
coverage, and the two verification statuses are reported separately (§9.1 split
of duties).

For `scope: "form"`, every declared and observed path must be `/instructions/0`
or start with `/instructions/0/`; any other path is `case-error-scope` (exit 1).
In addition, the required set must contain at least one path on the mutated
operand surface as defined above. A wildcard, "any error", a root-level error
such as a wrong `format_version`, or an `E-BYTE-001`/`E-SIZE-001` artifact
assertion therefore cannot satisfy a form's negative coverage. For
`scope: "plan"` any path is allowed. Coverage is counted only from `scope:
"form"` negatives: every exported form needs at least one positive and at least
one such negative, or the package is `uncovered-form`. A plan-scope case adds no
coverage at any stage: `stage: "read"` does not let a form-scope rule be satisfied
by a reader rejection.

**Representative forms carry boundary evidence, within what the plan can
represent.** One positive and one illegal neighbour proves that a form is not
wholly absent; it does not prove the operand domain. The domain splits in two:

- `D_Representable` is what `fmp/0.1`'s `plan::read` can hold. `payload.reg` is
  a `u64` (`fmp-model/src/plan.rs` `bind_payload`), so `{"reg": -1}` is a
  `plan::read` rejection — `E-PLAN-002` at the operand's `payload/reg` — and no
  `Plan` exists for `bind` to see. A modifier value is an integer, string or
  boolean.
- `D_form` is what the selected slot accepts. `D_form ⊆ D_Representable`.

Only a value in `D_Representable \ D_form` can be a `scope: "form"` negative,
because only that value reaches `bind`. A value outside `D_Representable` is a
`scope: "plan"` case with `stage: "read"`: the declared diagnostics are the
reader's own, it never counts as form coverage, and treating it as a form
negative would ask for a `Plan` the reader refuses to build. The three stages
exist so that each rejection is recorded where it happens; collapsing `read`
into `bind` would either lose the case or name a stage that cannot run.

For every shipped form with an immediately encoded or otherwise bounded operand,
boundary cases are taken from the **final legal domain**, not the raw encoded
range. For a slot with range `[L, U]`, alignment `a` (`align_bits`) and excluded
set `E`:

```
D_form = { x ∈ D_Representable | L ≤ x ≤ U, x ≡ 0 (mod 2^a) } \ E
```

For a register, `L = 0`, `U = 2^w − 1` clipped to `u64::MAX`, and `a = 0`; this is
the `D_reg` above.

- Positives are taken from `D_form` by **cardinality**, so a degenerate legal
  domain does not demand a value that does not exist. A raw endpoint that is
  excluded or unaligned is not a positive.

  | `D_form` size | Required positives |
  |---|---|
  | 0 | none — the form is unusable and the builder rejects it (`empty-form-domain`, exit 1) instead of asking for a case no plan can satisfy |
  | 1 | the single legal value, which is both minimum and maximum |
  | 2 | both legal values |
  | 3 or more | the minimum, the maximum and one representative interior value, distinct from both |

  Measured examples: `x86:mov/rm8h-r8h/legacy` has `w = 3` and `E = {0,1,2,3}`,
  so `4` and `7` are the positives and `0..3` are form negatives;
  `aarch64:add/w32-w32-w32-imm6-lsl` excludes `32..63`, so `31` is the positive
  maximum and `32` is a form negative; `riscv:c.addi/rd-imm6` excludes `rd = 0`,
  so `1` is the positive minimum and `0` is a form negative.
- An empty `D_form` is a property of the encoded form, not of a plan: rejecting it
  at build time keeps the case protocol satisfiable, and the rejection happens
  before any case is generated or any coverage counted. A form that legitimately
  accepts no value needs an explicit later format statement about what it is for;
  `monasm-package/0.1` has none, so such a form cannot be published.
- A representable excluded value is a `scope: "form"` negative rejected by
  `E-RANGE-004` at the mutated operand.
- An adjacent out-of-range value (`min−1`/`max+1`, or `2^w` for a register) is a
  form negative only when `D_Representable` can hold it and it is not in
  `D_form`; otherwise it is a `stage: "read"` plan negative or not testable. It is
  never declared as a `bind` negative the reader would have rejected first.
- For a register field, the encoded width `w` is the sum of its placement widths
  and may exceed 64 bits (`ADR-0127` §7.1 bounds each placement, not the sum; the
  H1 test `prototype/crates/fmp-materialize/tests/he1_wide_register.rs` loads and
  encodes 64-, 127-, 128- and 192-bit fields). `payload.reg` is still a `u64`, so
  `D_reg = ([0, 2^w − 1] ∩ [0, 2^64 − 1]) \ E`; the cardinality rule above applies
  to `D_reg` as well, so a fully excluded narrow field is `empty-form-domain` and a
  domain with one surviving value is tested once rather than twice:
  - `w < 64`: the positives are the smallest and largest members of `D_reg`
    (typically `0` and `2^w − 1` when neither is excluded); `2^w` is a form
    negative when representable.
  - `w = 64`: the positives are the smallest and largest members of `D_reg`;
    `2^64` is not representable, so the second form negative is a representable
    excluded value or a wrong `target_type`/operand kind.
  - `w > 64`: the positives are the smallest and largest members of `D_reg`
    (typically `0` and `u64::MAX`); `2^w − 1` and `2^w` are unrepresentable, so no
    `max + 1` is required or legal. An excluded value or a wrong
    `target_type`/operand kind is the form negative; a wide slot without an
    excluded value has no numeric form negative at all and must not invent one.
  There is no representable `0 − 1`: a negative register number is a plan-scope
  `stage: "read"` negative. A package-level boundary protocol test must exercise
  the 127- and 192-bit slots through `read`/`bind`/`materialize`, so the H2 author
  layer cannot silently shrink the encoding capability H1 already proved; that
  test supplements, and does not replace, the narrow-field boundary cases of the
  three shipped packages.
- A modifier is a set of permitted `(name, value)` pairs, not a contiguous
  integer interval. Test one permitted pair and one representable but unpermitted
  pair; do not invent `min−1`/`max+1` arithmetic for it.
- The evidence file records the fields the observed diagnostic actually carries.
  An immediate outside its `[min, max]` is rejected by `E-RANGE-001` (or
  `E-RANGE-002` for a target operand), which emits `min`, `max`, `value` and,
  for a non-target, `target_type`, so those are recorded. A register beyond its
  field is rejected by `E-OPERAND-004`, which emits `target_type`, `value` and
  `field_bits`, and the encoded bound `2^field_bits − 1` is derived from
  `field_bits`; when `field_bits ≥ 64` that bound exceeds `u64::MAX`, so the
  representable maximum is `u64::MAX` and the case never claims to test `2^w`.
  The diagnostic has no `min`/`max` key. An excluded value is rejected by
  `E-RANGE-004`, which emits `target_type`, `value` and `excluded`. A case does
  not require fields the validator does not emit.

Each boundary case otherwise uses the same `scope:"form"`/`bind`/complete-
diagnostic contract above, and an illegal value must be rejected at the mutated
operand. The pass condition remains the `(code, path)` set, so
`monasm-cases/0.1` is unchanged and no detail key enters the comparison. This is
evidence for the slices H2 actually ships, not a claim that every ISA boundary is
proved; a missing boundary case fails the slice acceptance but does not create a
new coverage error code.

A positive case records the exact machine-output projection defined in §15:
Level 0 is `{format_version, level, bytes_hex, size, fixups}`; Level 1 is
`{format_version, level, sections, symbols?, fixups}`. `expect` is a closed
object whose key set must equal the projection for the case's level and, at
Level 1, the plan's `output_contract.include_symbol_table`; a wrong key set is
`case-expect-shape` (exit 1). Missing and empty are different: `symbols: []` is
present, an absent `symbols` is not an empty array, and the harness never
normalises one into the other. `fingerprint` and `materializer_version` are
never in the projection, and a case that declares either is `case-expect-shape`.
Every case carries `evidence` with exactly `kind` (`oracle` or
`manual-derivation`), `path` and `sha256`. In a release-ready package the path
must be listed in `evidence/manifest.json`, and `tests/cases.json` itself must
also be listed there (§7.1), so `evidence_digest` covers the case plan and
coverage. In development mode without a manifest, `verify --package` checks the
case's own `sha256` against the raw file bytes instead; a manifest that is
present is authoritative in both modes.

**Split of duties.** `verify --package` validates the case document: schema,
coverage of every exported form by a positive and a `scope: "form"` negative,
ordering, evidence references and hashes, the `baseline_case_id` link, the
`mutates` pointer grammar, and the structural diff between baseline and case
plans. Its stage-related checks are **static only**: `stage` is one of the three
values, a form-scope case declares `bind`, a plan-scope case uses a stage its
scope permits, `diagnostics` is a non-empty sorted unique closed array, declared
paths obey the static scope rule, and the declared diagnostic count is non-zero.
It does not execute `plan::read`, `bind` or `materialize`, because the product
binary depends only on `fmp-model`; therefore it cannot prove which stage rejects
first or that the observed set matches. The
`package_conformance` test in `fmp-definition/tests/` builds each package under
its standalone identity (§2.1) and executes every case with the dev-dependency
graph, proving the actual first rejecting stage and matching the complete
observed diagnostic set. It enumerates
`packages/*/*/*/package.json` at test time;
that enumeration is test-only, never feeds bundle selection and cannot change a
bundle digest, so it does not reopen `HE-AC-05`.

**CI.** `cargo test -p fmp-definition --test package_conformance` runs in the
workspace gate and covers every package, including one no spec selects.
`cargo run -p fmp-definition -- verify --package --release-evidence <changed>`
runs for every changed package, so a dependent package still gets the complete
evidence bar. A package whose `dependencies` is empty also runs
`--release <changed>`; a dependent package is release-verified through
`--all --check` or an explicit `--closure` (§8), so the author gate does not
require a global spec edit. A structurally valid row whose
opcode was flipped fails the positive case's byte comparison even when `read`
accepts it. If an author also edits the expected bytes, the case must cite
independent evidence, and §7.1 checks that the evidence is present, listed and
hashed; the builder does not claim to have re-run the oracle. This limit is stated rather than hidden: the
gate blocks accidental and unilateral encoding errors, and the reviewable oracle
record is what a second party audits.

`verify --package` alone checks structure, manifest, cases and evidence; it does
not encode, so it cannot by itself distinguish two opcodes. The merge gate is the
**pair**: `verify --package --release-evidence` and `package_conformance` on the
same
changed package. A package that passes the first and fails the second does not
pass the gate, and the ordinary-extension CI job fails. This split is what keeps
the product binary's dependency graph at `fmp-model` plus the §3 path layer, with
no dependency on the validator or the materializer; it is not a weaker gate.

**Reporting status is not one bit.** The H2 report and every package report must
label these claims separately:

| Claim | What it means | What it does not mean |
|---|---|---|
| Definition structure verified | `fmp_model::definition::read` accepted the merged document | an opcode or operand range is correct |
| Package structure verified | `verify --package` accepted the manifest, assets and evidence | any declared dependency was resolved, or any case executed |
| Case document statically valid | `verify --package` accepted the case schema, scope/`stage` declaration form, `mutates` grammar, diagnostic shape and static `case-error-scope` rules | that `plan::read`, `bind` or `materialize` actually rejects at the declared stage |
| Case stage and diagnostics verified | `package_conformance` executed the case, observed the declared stage as the first rejecting stage, and matched the complete `(code, path)` set | an independent tool was run |
| Dependency closure verified | every dependency matched an explicit closure entry by ID, version and digest | H2 packages declare any dependencies |
| Package machine-code test passed | `package_conformance` matched the declared expectation and the complete diagnostic set | an independent tool was run |
| Evidence traceable | the manifest lists the files and every hash matches | the recorded oracle result is true |
| Independent oracle re-verified | an external tool was actually re-run and compared on this host | H2 does this for new packages |

None of the first seven implies the last. H2 records evidence and executes the
declared cases; it does not claim a fresh oracle run for a new package.

H2 does not add per-ISA branches to the harness. It dispatches from
`tests/cases.json` and `package.json` only (`HE-T14`).

#### 9.2 `monasm-cases/0.1` is H2's model, not a universal one

`monasm-cases/0.1` deliberately promises only what H2 can execute: one
`fmp/0.1` plan, exactly one instruction, a negative observed at the first stage
that rejects (`read`, `bind` or `materialize`), and a form neighbourhood
expressed as one operand-surface mutation. It does not define:

- `fmp/0.2` plans (H3): a case with an unknown plan `format_version` is
  rejected, not translated;
- zero-operand forms (H3): there is no operand pointer to mutate, so the
  `scope: "form"` rule cannot be satisfied. H2 packages export forms with
  operands; a zero-operand form needs a new case model, not a plan-scope
  negative disguised as coverage;
- multi-instruction plans or paired-fixup scenarios (H4): the one-instruction
  rule is part of this format, not an implementation shortcut;
- post-encode artifact assertions (H4): a form-scope negative must be a `bind`
  rejection at the mutated operand; `E-BYTE-001`/`E-SIZE-001` and fixup
  assertions are plan-scope evidence or need a later scenario model, never form
  coverage;
- definition-identity negatives: the only legal `definition_identity` is the
  `$standalone` sentinel and the harness substitutes the correct identity, so a
  digest mismatch is a binding-test concern, not a case kind, and the format adds
  no per-case override.

The case document declares `cases_format`; the builder rejects any value other
than `monasm-cases/0.1` with `case-format-unsupported` (exit 1). H3/H4 must add
`monasm-cases/0.2` (or an explicitly versioned scenario format) with its own
coverage rule, and a package selects it by version. Reusing `0.1` silently for
`fmp/0.2` or multi-instruction cases is forbidden. The case-format version is
independent of `package_format`, so adding that support does not rename packages
or move `source_package_digest`; it does require a new `tests/cases.json`
contract and harness path.

### 10. The legacy bridge is one method, and it is H2-only

`VerifiedBundle` exposes:

```rust
pub fn definition(&self) -> Arc<Definition>;
pub fn definition_digest(&self) -> &str;
pub fn bundle_digest(&self) -> &str;
pub fn lock_json(&self) -> Json;
pub fn bundle_json(&self) -> Json;
```

`bind` still takes `Arc<Definition>`; H2 does not add a bundle parameter. The
`definition()` bridge exists so the H2 equivalence tests and the legacy
`--definitions <dir>` path can execute the generated table. H3 replaces it with
a bundle-bound `bind`; this ADR does not describe it as a long-term API.

### 11. Errors and exit codes are the builder's own

`fmp-definition` returns a `BuildError` enum. It does not add `E-*` codes and
does not pretend to be `fmp/0.1` diagnostics.

| Class | Examples | Exit |
|---|---|---|
| Deterministic rejection | manifest shape (required/optional keys), identifier/path lexical violation, a reversed or duplicated `enabled_extensions`/`requires_capabilities` array, artifact filename mismatch, empty forms, path escape, a symlink/reparse point on a package path or on an output parent path under `--root`, an opened leaf that is not a regular file (FIFO, socket, device, a directory where a file is required, or a non-directory where a directory is required), or an opened entry whose name differs from the declared segment, declared-vs-derived capability mismatch, a form requirement outside the package declaration (`form-extension-mismatch`), a form whose final legal operand domain is empty (`empty-form-domain`), a sealed bundle whose `form_owners` is incomplete, duplicated or names an absent form or a package outside `packages` (`bundle-owner-incomplete`), missing/duplicate/cyclic dependency, dependency digest mismatch, two versions of one package ID, cross-spec `bundle_id` or definition-identity conflict, reuse of a reserved legacy definition name, digest mismatch, ownership conflict, row mismatch, committed legacy snapshot differing from the sealed definition (`legacy-snapshot-mismatch`), legacy target mismatch, form-family mismatch, unknown capability, non-empty reserved asset, evidence mismatch or incompleteness, missing/uncovered case, unsupported case format, case/plan/form binding, case baseline or mutation, case scope/stage mismatch (form-scope `read`/`materialize`, or a declared stage that is not the first rejecting stage), form-scope diagnostic not on the mutated operand, incomplete diagnostic set, wrong expectation projection, unmapped package path, published snapshot modification, registry modification, global identity duplication, incompleteness or invalidity, snapshot digest mismatch, path/version mismatch, reserved identity, closure aggregate limit, `read` rejection, resource limit (including a committed lock, sealed bundle or legacy snapshot over its byte budget), orphan bundle artifact | 1 |
| Host / I/O / internal | unreadable file, unwritable lock, internal invariant break, materializer `Internal`/`HostFailure` during conformance | 2 |
| Success | build or verify passed, digest printed | 0 |

The enum names these rejections (`unsupported-capability`, `capability-mismatch`,
`unsupported-asset`,
`version-conflict`, `aggregate-limit`, `resource-limit`, `legacy-row-mismatch`,
`legacy-target-mismatch`, `legacy-snapshot-mismatch`,
`evidence-mismatch`, `evidence-incomplete`,
`missing-cases`, `uncovered-form`, `empty-package`, `case-evidence-mismatch`,
`case-plan-identity`, `case-form-mismatch`, `case-error-scope`,
`case-format-unsupported`, `case-baseline-invalid`, `case-mutation-mismatch`,
`case-diagnostics-mismatch`, `case-expect-shape`, `form-family-mismatch`,
`form-extension-mismatch`, `reserved-identity`, `path-version-mismatch`,
`path-escape`, `identifier-lexical`, `path-lexical`, `extension-lexical`,
`capability-lexical`, `bundle-file-mismatch`, `bundle-owner-incomplete`,
`empty-form-domain`,
`published-package-modified`, `published-registry-modified`,
`published-registry-incomplete`, `published-registry-invalid`,
`snapshot-mismatch`,
`bundle-id-conflict`, `definition-identity-conflict`, `unmapped-package-path`,
`dependency-unverified`, `dependency-mismatch`, `not-a-regular-file`,
`orphan-bundle-artifact`); they
are `BuildError` variants, not `fmp/0.1` diagnostic codes.
`case-materialize-fault` is the conformance harness's name for an unexpected
`Internal`/`HostFailure`; it is never a passing case and reports exit 2, the
host/internal class.

The `fmp` CLI's 0/1/2 meanings are unchanged. Package-build errors never enter
`bind`'s diagnostic array.

### 12. Bounds are explicit

H2 bounds the builder's own inputs; it does not claim to fix deep-JSON
robustness:

- manifest ≤ 1 MiB; form, type or profile file ≤ 1 MiB;
- `tests/cases.json` ≤ 16 MiB; `evidence/manifest.json` ≤ 1 MiB; a spec or lock
  ≤ 1 MiB each; a committed sealed bundle ≤ 80 MiB — the 64 MiB closure budget
  plus a 16 MiB envelope allowance for `target`, the sorted `packages` list with
  each package's cover, `form_owners` and the definition wrapper — read only
  through the bounded streaming comparison of §8.3. The allowance is a bound on
  the output, not a proof that every closure fits: a closure whose merged form
  count makes the envelope exceed 80 MiB is rejected with `resource-limit` before
  any write, because the bound is part of what a buildable closure is. The
  per-package form and asset caps keep the owner list proportional to the
  definition, so the case is a corner, not the normal path.
  The pinned legacy definition file read for row comparison and the
  committed bridge snapshot read for the §8.3 equality gate each ≤ 16 MiB
  (this bound applies to the cache, not to the bundle: a build whose canonical
  definition exceeds it omits the snapshot instead of writing an unreadable one,
  §8.3); `bundles/published.json` ≤ 16 MiB and ≤ 65 536 entries;
- a published version directory ≤ 64 MiB and ≤ 8192 regular files, which bounds
  the `snapshot_digest` file set and the audit's per-entry re-read;
- exported forms per package ≤ 1024; declared assets per package ≤ 2048; cases
  per package ≤ 4096; evidence files per package ≤ 4096;
- manifest plus declared asset bytes per package ≤ 16 MiB, enforced by the
  cumulative read in §12.1;
- total evidence bytes per package ≤ 16 MiB;
- packages per closure ≤ 1024; total package-root bytes read per closure
  ≤ 64 MiB, charged by §12.2;
- total declared assets per closure ≤ 65 536; total cases per closure ≤ 65 536;
  total evidence files per closure ≤ 65 536;
- one path ≤ 1024 bytes; dependency depth ≤ 64;
- JSON nesting depth ≤ 64 for every manifest, form/type/profile file, case file,
  evidence manifest, spec, lock and the published registry the builder parses.

The form/case counts are aligned: 1024 forms need at least 2048 cases (one
positive and one `scope: "form"` negative each), and the 4096-case limit leaves
room for plan-scope negatives. A 16 MiB case file is roughly 4 KiB per case at
the maximum, which fits a complete one-instruction `fmp/0.1` document plus its
expectation; the earlier 1 MiB value could not hold the mandatory cases for even
a few hundred forms.

An over-limit input is a deterministic rejection (exit 1). Every input follows
one order, and no step is reordered:

1. lexical validation of the declared path (§1.3);
2. the no-follow open relative to already-open directory handles (§3);
3. the type check on the opened handle (`not-a-regular-file` for a non-regular
   leaf or a wrong-typed component);
4. a size hint from the **same** handle;
5. a bounded read that accumulates the bytes it actually reads and stops at the
   remaining budget (§12.1);
6. parsing.

The metadata size is only a hint that lets the builder fail early; it is never
the boundary, because a file can change between the type check and the read. The
cumulative counter in §12.1 is what enforces the budget, so a case or evidence
file cannot bypass the per-package budget just because no spec selects the
package. The depth budget is
enforced **before and during** parsing, not by parsing first and measuring the
result: the builder scans the bytes iteratively (counting `{`/`[` outside string
literals) and refuses a document that would exceed the budget before it calls
`fmp_model::json::parse`, whose descent is recursive. A document smaller than
1 MiB with tens of thousands of nesting levels is a required negative; it must
be rejected without recursing to the stack limit. This is the builder's own
input budget; it is not a claim that `fmp` is robust to deep JSON, and a parser
stack overflow from a 20 000-deep document remains H4 (`HE-T13`). H2's package
inputs are developer-controlled.

These budgets assume **regular files**. A FIFO, socket or device node has no
bounded length, so a size check cannot bound it and a read may never return. §3
therefore rejects a non-regular leaf as `not-a-regular-file` (exit 1) on the
opened handle, before any budget is applied; a metadata size is also not used to
decide the type, for the same check-then-use reason as the no-follow rule.

#### 12.1 The per-package asset budget is cumulative and enforced while reading

Each manifest and form/type/profile file is read through a bounded reader. The
builder adds every byte it actually reads to one per-package counter and
rejects as soon as the next read would cross 16 MiB. File metadata is a hint,
not the check: a file can grow between the type check and the read. The reader
therefore stops at the remaining budget and treats a short or overlong read as
`resource-limit` (exit 1). The counter is reset for each package; it is not the
closure total.

Counterexample if only the per-file limit existed: 2048 files of 1 MiB each pass
every per-file check and make the builder read 2 GiB for one package. A single
`verify --package` run has no closure total, so the cumulative counter is the
only bound that applies.

#### 12.2 The per-closure budget has one counter and one counted set

A command that opens a selected package root keeps **one closure counter** for
the whole run, in addition to the per-package counters. It charges the byte count
of every file it reads from a package root, counting each distinct path once:

- `package.json`;
- every declared form, type and profile asset it reads;
- `tests/cases.json`;
- `evidence/manifest.json`;
- every file the evidence manifest lists and the command reads — `NOTICE`,
  `README.md`, oracle text and the case evidence files it names.

Nothing else is charged: the spec, the lock, `bundles/published.json`, the pinned
legacy definition read for row comparison, and the builder's own outputs have
their own per-file bounds in §12 and are not package-root bytes.

The counted set is fixed by these rules, not by whichever files a shortcut
happens to open. `build`, `verify --all` and the release gates read the whole
list above; a command that reads less charges less, and no command may read more
than 64 MiB of package-root bytes in one run. A path is charged **once per
package root per run**, even if the command opens it twice (for example a form
asset that the evidence manifest also lists): paying twice for one file would
make the limit depend on which fields mention a path. A package reached along
two dependency paths is charged once because the spec lists every closure member
exactly once and a repeated `packages[].path` is already `path-lexical` (§8.2);
a diamond has one shared directory, not two.

Rejection happens **at the read that would cross the limit**: the reader stops at
the remaining budget and returns `aggregate-limit` (exit 1) before consuming the
crossing bytes. Metadata is a hint, not the check, for the reason given in
§12.1. The 16 MiB per-package asset counter and the 16 MiB evidence counter stay
independent, so a package cannot be shielded by staying under its own limits
while the closure total grows.

Counterexample if the closure total charged only manifests and form assets: each
of three packages carries 12 MiB of cases plus 12 MiB of evidence, all inside the
per-package limits, yet the command reads 72 MiB under a nominal 64 MiB closure
cap; eight such packages read 192 MiB. The required negative therefore uses
**several** packages, each inside its own limits, whose sum crosses 64 MiB — a
single-package overflow tests §12.1, not this rule.

### 13. The x86 slice is pinned to `0.1.0`, not the newest definition

The x86 package exports `x86:mov/r64-rm/legacy` and
`x86:mov/rm-r64/legacy`, copied from `x86_64/0.1.0`, and the spec emits
`fmp-def/0.1` with `enabled_extensions: []` and version `0.1.0-h2`. The reason
is measured in Context: the `0.78.0` rows add `requires_extensions` and REX
placements, so they are not the rows `X86-P1` was verified against. The
low-register fixture still produces the same bytes, but H2 claims **row
equality**, not "the bytes happen to match"; using `0.78.0` would fail the
former while passing the latter.

This means the x86 slice does not exercise `fmp-def/0.2`. The untouched legacy
`0.78.0` definition and the H1 gates keep that path covered; migrating the
package format to `0.2` is a later decision, not an H2 requirement.

### 14. The rv64 slice is pinned to `0.1.0`, and aarch64 to `0.20.0`

The rv64 package exports `riscv:add/rd-rs1-rs2` and
`riscv:addi/rd-rs1-imm12` from `rv64/0.1.0`. `0.6.0` declares
`["rv64i","rv64c"]`, while `RV-P1`/`RV-P2` declare `["rv64i"]`; `fmp-def/0.1`
requires set equality, so `0.6.0` would be rejected at `bind` regardless of
bytes. The aarch64 package exports the three `add` forms from `0.20.0`; the two
`lsl0` rows are equal to `0.1.0`, the `lsl12` row first appears in `0.2.0`, and
all three are equal in `0.2.0` and `0.20.0`. The target set is `[]`.

The general rule for any future slice: pin the **newest definition version
whose selected rows are byte-equal to the evidence and whose target identity
matches the reference plan**. If the newest version fails either test, pin the
version that passes and record why in the package report and, for a migrating
package, its `legacy_source`.

### 15. Machine output is an exact, level-specific projection

The comparison key is a projection of the materializer's JSON envelope, not
`payload/0.1` and not the whole envelope. The harness builds one of the two
closed objects below and compares it as a JSON value. It never adds a key,
drops an extra key, or turns an absent optional key into an empty array.

#### 15.1 Level 0

Exactly these keys, no others:

| Key | Value |
|---|---|
| `format_version` | string, `fmp/0.1` |
| `level` | integer, `0` |
| `bytes_hex` | lowercase hex string of the whole artifact |
| `size` | integer, byte length |
| `fixups` | array of fixup records |

`Artifact::level_zero_json()` also emits `fingerprint` and
`materializer_version`; the projection drops both. It never emits `symbols`, so
a Level 0 case that declares `symbols` is `case-expect-shape`, not an empty
symbol table. This is measured against `fmp-materialize/src/lib.rs`
`level_zero_json`, not inferred from the function name.

#### 15.2 Level 1

Exactly these keys, no others:

| Key | Presence |
|---|---|
| `format_version` | always |
| `level` | always; integer `1` |
| `sections` | always; the array `Artifact::to_json()` emits, including each section's optional `base_address` and its `bytes_hex` |
| `symbols` | exactly when the case plan's `output_contract.include_symbol_table` is `true`; absent otherwise |
| `fixups` | always |

An empty symbol table with `include_symbol_table: true` is `symbols: []`; with
`false`, `symbols` is absent. Those are different JSON values. The projection
drops `fingerprint` and `materializer_version`; a case that declares either is
`case-expect-shape`.

#### 15.3 Comparison and equivalence

For each reference fixture, the equivalence test reads the legacy plan, replaces
only `definition_identity` with the bundle's `{namespace, version, digest}`,
re-parses with `fmp_model::plan::read`, binds to `VerifiedBundle::definition()`,
materialises, and compares the same level-specific projection. The positive
case in `tests/cases.json` compares its `expect` object the same way.

It does **not** compare `fingerprint` or `materializer_version`.
`fingerprint` covers `plan.legacy_document`, which contains the declared
definition identity (`ADR-0127` D12); a different bundle identity necessarily
moves it. `payload_digest` includes `fingerprint` and is therefore not the
comparison key here. The report must state which projection was compared so a
payload mismatch is not misreported as a byte mismatch.

This is a regression check against the frozen legacy artifact, not a new
independent oracle. The existing per-fixture `manual-derivation` records and
`tools/oracle/rerun.py` remain the independent source; H2 does not claim that
comparing the materializer with itself proves the bytes.

### 16. What H2 deliberately does not do

- No `fmp/0.2` plan format, namespaced ISA identity or zero-operand form (H3).
- No runtime bundle reader, runtime capability negotiation or unselected-package
  isolation at materialisation time (H3). H2 rejects unknown capability strings
  at build time only. The format is frozen with every fact H3's checks need —
  bundle-level `target`, each package's declared cover and `form_owners` — so H3
  implements consumption, not a replacement format (§7, §8.2).
- No implicit conversion between `fmp-def/0.1` and `fmp-def/0.2`; a mixed
  closure is rejected, and an explicit versioned conversion is H3 work.
- No execution or emission of `type`/`profile` assets; a non-empty declaration
  is rejected, and `monasm-package/0.1` keeps that rejection permanently — H4
  needs an explicit later package format (§5).
- No `bind(VerifiedBundle, ...)` and no `fmp-validate → fmp-definition`
  dependency (H3).
- No target-subset acceptance in H2. `monasm-bundle/0.1` carries the facts the H3
  rule reads — `form_owners` and each package's declared cover — but H2 runs no
  owner-cover check and adds no subset cell; a definition format whose
  per-form requirement is absent still relies on the conservative cover (§4.1).
- No claim that a bundle is executable because it verifies. `bundle_digest` is
  recomputable from the sealed file alone, and that proves what the bundle says,
  not that a plan may use it; `bind` takes a `Definition`, never a bundle, and the
  target check stays with the caller (§7, §8.2).
- No claim that V-A output is published. Until the publication-channel verdict
  passes, a lock, sealed bundle or legacy snapshot is a development artifact;
  `bundles/published.json` does not exist and no command calls the output
  immutable or trusted (§8.5).
- No claim that `snapshot_digest` proves provenance. It binds committed bytes to
  a recorded value so a published directory cannot change unnoticed; it does not
  prove who produced the first value, and it cannot survive a history rewrite or a
  bypassed merge gate (§8.3, §8.4).
- No claim about the repository's branch-protection or merge-queue settings from
  a document; the publication-channel verdict reads the effective setting through
  the platform API and records the evidence. A 403, an empty ruleset list or an
  unreadable setting is a missing evidence step, not proof that no protection
  exists (§8.1, §8.5).
- No claim that a green CI run closes the publication gate. N5 needs the
  mechanism recorded and the stale-CI counterexample executed; otherwise the
  publication-channel verdict stops there, and a post-merge audit is detection,
  never authorization (§8.1, §8.5).
- No claim that the single-file published registry scales. The 1,000-version
  measurement and its threshold are a recorded cost and a trigger for a later
  ADR, not a proven property (§8.3).
- No claim that independent package authoring and independent publishing scale
  together. H2 provides the authoring basis and correct serialized publication;
  uncoordinated parallel publishing is not guaranteed and needs a later ADR
  (§8.3).
- No claim that `builder` proves provenance. It records which implementation
  wrote the lock; it is excluded from the definition identity, and a change to it
  can pass `--all --check`. Trusted build provenance needs a separate attestation
  or artifact signature (§7).
- No claim from documentation that the N1 no-follow guarantee is achievable on a
  platform, or that three platforms behave alike: the PoC is a separate
  prerequisite deliverable with recorded per-platform results (§3).
- No archive format or archive gate for a retired bundle: its lock, sealed
  bundle and legacy snapshot leave the tree with its last spec, and git history
  is the replay record (§8.4).
- No fixup profiles, non-zero addends, Hi/Lo pairing or field-ownership
  semantics (H4).
- No deep-JSON fuzzing or full input-robustness programme (H4).
- No case format beyond `monasm-cases/0.1`: no `fmp/0.2` cases, no zero-operand
  form coverage and no multi-instruction fixup scenario. Those need an explicitly
  versioned `monasm-cases/0.2` (H3/H4, §9.2).
- No real same-ISA A/B packages or parallel workflows (H5).
- No migration of the 104 definitions or 619 negatives; no bulk form renaming.

## Consequences

- A new instruction family can land as a package directory plus a spec entry
  when the publisher selects it; before that, `verify --package` validates the
  package on its own. The builder checks the manifest, the closure, ownership and
  canonical form, and `read` checks the definition semantics. No central form
  table is edited; package counts are generated, not hand-copied into `STATUS.md`
  (`ADR-0125` decision 4).
- A published package version is an immutable source snapshot. An author adding
  forms creates a sibling `<new-version>/` directory and leaves every selected
  version byte-for-byte in place, so an old spec still rebuilds its old lock. A
  publisher selects the new version later; the author's PR does not edit a global
  spec or lock.
- A migrated package proves more than byte-equal rows: when `legacy_source` is
  present, its `definition_format` must equal the pinned legacy document's and
  its `target_identity` must satisfy `TargetEq` — every field strictly equal
  except `enabled_extensions`, which is compared as a set (`§1.1`). A
  deliberately retargeted package is rejected rather than inferred from matching
  rows.
- Form coverage is an illegal-neighbourhood claim, not a count. A negative case
  must name a positive baseline, mutate exactly one operand field, be rejected by
  `bind`, and name a diagnostic on the mutated operand or its parent object. A
  wrong `expected_digest` or an `E-BYTE-001`/`E-SIZE-001` artifact assertion may
  be a plan-scope test but cannot cover a form.
- One illegal neighbour is not the whole operand domain. A form with an
  immediately encoded or otherwise bounded operand also carries boundary cases
  taken from the final legal domain `D_form = {x ∈ D_Representable | L ≤ x ≤ U,
  x ≡ 0 (mod 2^a)} \ E`, not the raw encoded range: positive values are chosen by
  the domain's cardinality — one value, both endpoints, or minimum, maximum and an
  interior value — so an excluded or unaligned endpoint is never a positive and a
  degenerate domain never demands a value that does not exist. An empty domain is
  `empty-form-domain` (exit 1). A representable excluded value is
  a form negative; an out-of-range value is a form negative only when the plan can
  represent it. A register field's encoded width `w` comes from `field_bits` and
  may exceed 64; its domain is
  `D_reg = ([0, 2^w − 1] ∩ [0, 2^64 − 1]) \ E`, so for `w ≥ 64` the maximum
  positive is `u64::MAX` and `2^w` is never a test input. A negative register is
  a plan-scope `stage: "read"` rejection rather than a form negative
  (`D_form ⊆ D_Representable`).
  The evidence records the detail keys the relevant diagnostic emits — `min`,
  `max`, `value` for `E-RANGE-001`/`E-RANGE-002`, and `target_type`, `value`,
  `field_bits` or `excluded` for `E-OPERAND-004`/`E-RANGE-004` — and never a key
  that diagnostic does not produce; the pass condition stays the `(code, path)`
  set and `monasm-cases/0.1` is unchanged (§9.1).
- Publication is recorded in an append-only registry, so a version remains
  immutable after its last spec retires. A later PR cannot reclassify an old
  snapshot as unpublished by deleting a spec. A version can be created and first
  published in one PR, because only base entries make it immutable, but the
  merged snapshot is validated against the entry. A `(package_id, version)`
  names one path and one source digest forever, so two bundles cannot publish
  two different contents under the same logical version.
- Bundle verification and publication-history auditing are separate commands.
  `verify --all --check` keeps unselected packages out of a bundle build, while
  `verify --published --check` still re-hashes retired versions, including every
  file their `snapshot_digest` covers. Neither can
  silently take over the other's job.
- The sealed bundle verifies its own identity and is still compared with its lock.
  Every field of the `bundle_digest` preimage is in the file, so a reader
  recomputes both digests without a lock; the pair check catches a lock and a
  sealed bundle that disagree on the target, the definition or the package set.
  `bind` never accepts a bundle, and verifying one is not a permission to use it.
- Publication is a verdict, not a property of a build. Until the publication
  channel passes, output is a development artifact and the registry does not
  exist, so no wording may call it immutable; afterwards a `snapshot_digest`
  makes every byte of a published version directory checkable in-repo (§8.4,
  §8.5).
- The registry's audit cost is measured before it is relied on. The publication
  channel records the
  1,000-version time, memory and bytes-read curve for a package change, a
  publication and a full audit, plus the threshold for revisiting the single-file
  design, so scale is a budgeted cost rather than an assumed property.
- Independent authoring and independent publishing are separate claims. H2 gives
  authors version directories and explicit specs, so ordinary package work needs
  no central edit; it does not give publishers a coordination-free path, because
  every first publication writes the same append-only registry file. Correctness
  under that serialization is promised; parallel publishing throughput is not
  (§8.3).
- `builder` is a provenance record with a bounded claim. It is deliberately
  outside the definition identity and the drift projection, so it can change
  without failing `--all --check`; the contract therefore does not assert that
  the declared implementation produced the bundle, and trusted provenance needs a
  separate attestation or artifact signature (§7).
- The path layer's feasibility is evidence, not an assumption. The N1 PoC is a
  standalone prerequisite of the publication channel with per-platform OS
  versions, toolchain and API names, fault-injection methods and observed
  results; it lands before the hardened reader, not before the author layer (§8.5).
- Two verdicts replace one gate. The author layer — package model, trusted-tree
  reading, digests, determinism, cases, conformance — can land and be tested while
  the publication prerequisites are still open; the publication channel — hardened
  reader, registry, merge freshness, history audit — carries every claim about
  published, immutable or trusted artifacts, and H2 does not exit until it passes
  (§8.5).
- A lock, sealed bundle or legacy snapshot exists only while its spec exists.
  Removing the last spec removes those derived artifacts from the tree, and
  `verify --all --check` rejects a surviving orphan, so no unselected release
  artifact is left in an undefined state. The snapshot and registry entry remain
  the permanent record, and git history keeps the retired bytes replayable.
- A publication verdict is keyed on the base commit SHA, the tested candidate
  tree SHA and the merge mode, not on a pair of commit SHAs. A green result is
  not a property of a branch that survives the target moving: when another PR
  publishes a version and merges first, the old verdict no longer describes the
  merge, and the publication is authorized only by a run whose base and tree are
  the ones actually landed. The cost is a merge queue or an operation that writes
  the recorded candidate; required up-to-date checks alone do not establish it.
  N5 closes only when the effective mechanism is recorded and the stale-CI
  counterexample has been executed; if neither can be shown, the publication
  verdict stops at that
  gate, because a post-merge audit is detection and cannot authorize a merge.
- H3 pays an artifact change for target subsets. `monasm-bundle/0.1` records its
  selected `packages` and the merged definition, not per-form owners or covers, so
  a subset plan cannot be checked against it. H3's versioned bundle or frozen
  companion source carries that proof, and a form without one is rejected rather
  than read as needing no extension (§4.1).
- `monasm-package/0.1` rejects non-empty `exports.types`/`exports.profiles`
  permanently, so acceptance cannot silently widen with a builder upgrade. H4
  pays one explicit package-format version for type/profile semantics instead of
  reinterpreting documents that already exist; the key names and digest input are
  already reserved, so that version does not reopen `0.1`'s closed key set.
- A legal closure is never made unbuildable by the optional legacy cache. When
  the canonical definition exceeds the cache's 16 MiB read budget, `build` omits
  the snapshot and removes a previous copy, and `--all --check` accepts the
  absence it already treated as legal; the sealed bundle remains the artifact
  and no digest moves.
- The spec set has one `bundle_id` and one `(namespace, version)` per release
  identity. Two specs cannot collide on a lock path or produce two definitions
  that `Registry::find` cannot distinguish. A retired definition name cannot be
  recycled under different bytes: the registry keeps the `(namespace, version)`
  history, while `bundle_id` stays a movable release line whose immutable
  content label is `(bundle_id, bundle_digest)` and whose evidence-complete
  release identity is `release_digest`.
- A frozen legacy definition name is not available to H2. The builder reserves
  every `(namespace, version)` in `definitions/`, so an H2 bundle cannot produce
  a second document under `monasm.isa.x86` / `0.1.0`; the existing 104 files are
  read-only and no package edits them.
- Package reads never follow a symlink or reparse point, and the rule is stated
  as a property of the open rather than of a preceding metadata check, so a
  concurrent replacement cannot make the builder read a file that none of the
  checks described. The mechanism is a platform capability, so the publication
  channel's first gate
  proves it on Linux, macOS and Windows rather than assuming a portable call.
- A legal path does not guarantee an ordinary file: a FIFO, socket or device node
  is not a link, so it passes the path rules and can block or escape every byte
  budget. The opened leaf's type is therefore checked on the handle and a
  non-regular object is `not-a-regular-file` (exit 1); the POSIX open is
  non-blocking until the type is known, so the rejection is deterministic rather
  than a hang.
- Identifiers, path segments and artifact file names are ASCII, lowercase and
  portable, and are checked before any open. A name that one filesystem aliases,
  folds, trims or maps to a device is a deterministic format rejection on every
  platform, not an I/O failure on one of them (§1.3).
- Path collisions are scoped to a root, so independent packages compose. Two
  packages may both ship `forms/add.json` and `tests/cases.json`; the closure
  domain is the repository-relative joined path, and only a root alias (two
  selected roots folding to one repository path) or a repeated spec path is
  `path-lexical` (§1.3).
- A declared path matches only the on-disk entry with the same spelling. The
  exact-name check happens on the already-open parent handle, so a
  case-insensitive volume cannot make `add.json` resolve to `Add.json`. The open
  is bound to the entry that was matched: if that entry is replaced between the
  match and the open, the builder either opens the matched object or rejects the
  replacement rather than reading an unexamined file. A host where the declared
  lowercase path and the stored mixed-case path disagree yields `path-lexical` on
  every platform, not a platform-dependent success (§1.3, §3). This is what lets
  one package input produce one build verdict on Linux, macOS and Windows.
- A package is read once into one immutable value; the source digest, the
  legacy row and target comparison, the per-package `read` and the merge all
  consume that value. A recorded digest therefore cannot describe bytes the
  definition did not use, and a file changed between stages cannot produce a
  bundle that fails to replay (§9).
- First publication is cycle-free and has one order: `build` exits 0, the
  publisher appends the registry rows, both `--check`s pass, and the commit
  merges. `build` validates every output in memory before replacing a file and
  never writes the registry, so a failed build leaves no row and no published
  partial artifact; the legacy snapshot is a derived cache that the same build
  regenerates, its absence is legal, and a committed copy is compared with the
  sealed definition as a one-way equality gate (`legacy-snapshot-mismatch`) that
  never enters a digest (§8.3).
- An interrupted write (exit 2) can leave a temporary file and a lock/sealed pair
  from different builds, but never a state `verify --all --check` accepts: the
  guarantee is detectability, not a multi-file atomic rename. Output directories
  are trusted, yet every output parent segment under `--root` obeys the same
  no-follow rule as an input, and the committed lock and sealed bundle are
  compared as a bounded stream inside the 1 MiB and 80 MiB budgets (§8.3, §12).
- A package's `enabled_extensions` is a conservative declared cover, not a
  minimal set. Over-declaration is legal and only narrows which bundles may
  select the package; under-declaration is `form-extension-mismatch`, and
  trimming the declaration to the derived union is not allowed (§4.1).
- A form's extension requirement must already be inside its own package's
  declaration, and the package inside the bundle's selection. A wider bundle
  cannot make an under-declared package legal: the package is read under its own
  target before the merge, so `verify --package` and `verify --all` agree on it.
- `profile_id` is a nominal label inside one bundle: it must equal the package's
  `target_profile`, but compatibility, identity and digests use the six-key
  `target.identity`. Two bundles may share the name with different identities, and
  H2 adds no global profile table (§4.1).
- `requires_capabilities` is a checked fact, not a comment: the builder derives
  the set from the row structure and rejects a declaration that differs in either
  direction, so a later consumer cannot under-provision a package that silently
  omitted a primitive. For `fmp-def/0.1` this means every legal package declares
  `field-placement/v1`; a slotless form is not a legal way to declare nothing.
- The case diff is defined over the two final documents, so the reported pointer
  set is a function of the values: a member edit reports the member, a kind
  change reports the position, and an array length change reports the array. A
  mutation that changes two members is rejected as two differences, regardless of
  how the author performed it.
- A case names the first stage that rejects: `read` when `plan::read` refuses the
  document, `bind` or `materialize` otherwise. Naming it is a static declaration;
  only `package_conformance` proves it is actually the first rejecting stage —
  `verify --package` never executes the plan. A value such as `{"reg":-1}` thus
  has a legal plan-scope representation without being dressed as form coverage,
  and a form-scope case stays `bind`-only (§9.1).
- The publication audit's claim is bounded to the executable assets and
  identity. Whole-directory immutability is enforced by the changed-path gate,
  which compares the **target-branch tip `B`** against the merged result `H`
  (`Published(B) ⊆ Published(H)` and equal tree bytes for every published path),
  and recorded by git history, not re-attested by `verify --published --check`;
  H2 says so instead of implying a snapshot proof it does not have. Using the
  merge base here would miss a version published on the target branch after the
  feature branch forked.
- Digest preimages, the Level 0/Level 1 projections and the package budgets are
  frozen at the byte and key level, with a cross-language vector, so a Rust and a
  Python implementation cannot silently disagree.
- A development package can be structure-verified without `NOTICE`, `sources` or
  an evidence manifest; `--release-evidence`, `--release` and spec selection
  require the complete set, so the weaker mode never becomes a release claim.
  The case's own hash is checked against raw file bytes in either mode.
- A package with dependencies is not blocked by the author gate: structure,
  conformance and the full evidence set run without a spec, while release
  verification additionally requires a spec closure or `--closure <lock>` and
  re-reads the whole transitive dependency graph. Asserting a
  digest in a hand-written lock is not enough to claim the closure.
- A zero-form package is rejected as `empty-package`; the manifest never
  advertises an object that `definition::read` cannot build. Type-only packages
  wait for a later format version rather than passing as an empty definition.
- A package is self-describing: `definition_format` and `target_identity` are
  manifest facts, so a family that never existed in `definitions/` still has a
  target to be checked against. `legacy_source` remains a migration record, not
  a prerequisite.
- A package that no spec selects is still mechanically checked: `verify
  --package` uses a versioned standalone identity, and the conformance harness
  executes every declared case without a central test list. A wrong opcode in a
  structurally valid row does not pass the ordinary-extension gate.
- A package declares the extensions its rows require, while the spec selects the
  bundle target. A new instruction family can join a bundle without editing an
  unrelated package, provided the bundle selection is a superset. The H2
  `h2-exact-target` equality is a stated transition, not a permanent rule;
  H3's plan-side compatibility lifts it before H5. The lift is versioned and the
  existing (plan, definition) cells are fixed: `fmp/0.1` + `fmp-def/0.1` keeps
  equality, `fmp/0.1` + `fmp-def/0.2` keeps the subset-plus-form rule, and only a
  new plan protocol adds a cell and lifts the transition. Keying the relation on
  the plan format instead of the definition format would wrongly reject the
  already-legal `fmp/0.1` + `fmp-def/0.2` cell, and no build flag substitutes for
  the new protocol (§4.1).
- The H3 lift has a build-side door and a plan-side door, and both must open.
  `monasm-bundle-spec/0.1` keeps rejecting an unequal `fmp-def/0.1` selection
  forever; a new plan format alone cannot make that spec build, and the builder
  version is not an implicit format upgrade (§4.1).
- A published version directory is frozen by the base registry at the
  target-branch tip `B` before any head-side discovery, so adding a nested
  `package.json` inside it is itself a modification, not a reclassification of
  the files around it (§8.1).
- Form-family consistency is a string equality, not a package-format whitelist.
  A fourth ISA added to `fmp_model::definition::read` in H3 needs no edit to
  `monasm-package/0.1` or to a central builder table.
- `exports.types` and `exports.profiles` are reserved in the closed manifest
  and source digest; H2 rejects non-empty lists, so the key set does not change
  when H4 adds semantics.
- `definition_digest` names execution rules; `release_digest` additionally names
  the selected packages, the case contract and their evidence. Documentation and
  test-case edits can move the release identity without moving the machine
  definition; a case edit must update the evidence manifest, or the release gate
  fails.
- `definitions/` and `fixtures/` do not move. The 128 payloads, the 104
  definition documents, the `payload_root` and the `definitions_root` keep their
  H1 values; a package build is a separate artifact.
- The H2 slice pins are data, not preferences: x86 `0.1.0`, aarch64 `0.20.0`,
  rv64 `0.1.0`. A future slice may choose differently only by the rule in
  decision 14 and must record the row and target comparison.
- The builder is offline and deterministic: no network, no author-directory
  reads, no package hooks, no execution of package scripts (`INV-05`).
- H3 can replace `VerifiedBundle::definition()` with a bundle-bound `bind` and
  add the subset-based plan target rule together with the versioned owner or
  per-form requirement source (§4.1). The package and spec formats need not
  change; the sealed bundle artifact is versioned, and the plan format is the H3
  surface that changes.

## Alternatives rejected

- **Scan `packages/**` and build a global `(id, version)` index.** Rejected: a
  damaged unselected package would affect an old build, contradicting
  `HE-AC-05`, and selection would be directory-driven (`INV-05`).
- **Overwrite `packages/<target>/<package_id>/` in place and update every spec on a
  package change.** Rejected: an ordinary author would again edit global specs and
  locks, which is the coordination H2 exists to remove. The version directory is
  the immutability boundary.
- **Use the current spec set as the publication record.** Rejected: retiring the
  last spec would erase the evidence that a version was published, so a later PR
  could edit the old snapshot. §8.3 keeps an append-only registry that survives
  retirement.
- **Publish `monasm-bundle/0.1` without the facts its own digest covers, and
  freeze a runtime format in H3.** Rejected: the file would be a companion whose
  embedded `bundle_digest` no consumer can recompute, and H3 would need a second
  bundle version whose only difference is `target`, the covers and
  `form_owners` — data H2's builder already computes. Nothing has shipped, so the
  format is fixed once, self-contained, and H3 consumes it (§7, §8.2).
- **Add `target` and owner data without binding them.** Rejected: metadata outside
  the digest is rewritable under a stable identity, so H3 would read facts the
  bundle does not actually commit to. `form_owners`, the covers and `target` are
  all inside the `bundle_digest` preimage, and completeness is a format rejection
  (`bundle-owner-incomplete`) rather than a convention (§8.2).
- **Trust one green platform for the no-follow layer, or treat the gate as a
  design statement.** Rejected: "theoretically possible with a no-follow open" is
  not evidence, and a platform that fails only at builder time has already sunk
  the layer. The N1 PoC is a standalone prerequisite with recorded per-platform
  results (§3). It gates the publication channel, not the author layer (§8.5).
- **Shard the registry or fold the audit into `--all` now.** Rejected for H2:
  both add a second format or lifecycle, or re-couple bundle verification to
  history, before the measured cost exists. H2 records the 1,000-version curve
  and a threshold; crossing it is the trigger for a new ADR (§8.3).
- **Accept a green CI run, or a post-merge audit, as the publication gate.**
  Rejected: the run belongs to some `(B_checked, C_checked, mode)`, and only the
  platform mechanism plus the stale-CI counterexample shows that the landed
  commit is the tested tree. A post-merge audit can detect a bad landing but
  cannot prevent it (§8.1).
- **Describe the append-only registry as coordination-free publishing.**
  Rejected: every first publication edits one file, so two publishers serialize
  on a rebase and a re-validation. H2 claims correct serialization, not parallel
  publication throughput; that needs a later, separately reviewed design (§8.3).
- **Recover provenance by putting the builder version into the definition
  digest.** Rejected: a toolchain upgrade would look like an execution change
  (`HE-T19`), and the field still would not prove which implementation ran.
  Provenance needs a separate attestation or signature (§7).
- **Trust a green publication result until the branch is merged.** Rejected: the
  verdict is keyed on a base commit and a candidate tree, and the target tip can
  gain a publication after that read. Reusing the result would let a branch edit
  a directory that became published in the meantime, and no other gate looks at
  those bytes. A merge queue or an operation that writes the recorded candidate
  re-establishes the key (§8.1); a post-merge audit alone is detectability, not
  prevention.
- **Treat required up-to-date checks as equivalent to a merge queue.** Rejected:
  they re-run checks when the base advances but do not promise that the landed
  commit has the tested tree, and the landed merge commit is a new SHA. The
  authorization key is `(B_checked, C_checked, mode)`; a setting page cannot prove
  `C_landed = C_checked` (§8.1).
- **Accept a plan target subset by checking `E_plan ⊆ E_bundle` only.** Rejected:
  it accepts `c.addi` for an `rv64i`-only plan when the bundle also selects
  `rv64c`. The selected instruction's owner must be covered by the plan target;
  the bundle is wider by construction (§4.1).
- **Read a missing `requires_extensions` as the empty set.** Rejected: it turns
  "unproved" into "legal for every configuration", which is exactly the
  under-declaration the package cover exists to reject. A legacy form without a
  versioned owner or requirement proof is rejected for subset plans (§4.1).
- **Treat a non-empty `exports.types`/`exports.profiles` as legal once a newer
  builder knows the field.** Rejected: the same unchanged `monasm-package/0.1`
  document would then be rejected by one tool version and accepted by the next,
  so replay would depend on the binary. Acceptance belongs to the declared
  `package_format`; H4 needs an explicit later format version (§5).
- **Fail the build when the canonical definition exceeds 16 MiB.** Rejected: the
  closure and sealed bundle budgets are larger, so a legal bundle would become
  unbuildable and the effective limit would be set by an optional development
  cache. The cache is omitted instead (§8.3).
- **Write an oversized legacy snapshot and let `--check` reject it.** Rejected:
  `build` would produce a tree that its own check cannot accept, and the failure
  would surface only after the publisher committed. `build` never writes a
  snapshot above its read budget (§8.3).
- **Keep a retired bundle's lock and sealed bundle in the tree as an implicit
  archive.** Rejected: `--all --check` only rebuilds what a spec selects and
  `--published --check` never reads locks or sealed bundles, so the file would
  keep the name of a release while no gate could say whether its bytes are the
  published ones. Retirement removes the derived artifacts; git history is the
  archive (§8.4).
- **Add a `bundles/archive/` format and a third gate for retired bundles.**
  Rejected for H2: it defines a second lifecycle and a second verification path
  for artifacts whose permanent facts — the package snapshot and the registry
  entry — are already recorded. A later format can add archival if a reader
  needs it.
- **Let the byte budget or a `stat` size bound a special file.** Rejected: a FIFO
  or device node has no length, and an ordinary read can block until a writer
  appears, so no budget applies; the type must come from the opened handle and
  the POSIX open must be non-blocking until it is known (§3, §12).
- **Treat any registry entry as immutability, including one added by this PR.**
  Rejected: a version could never be created and first published in the same PR,
  and the alternative — add the entry in a later PR — makes the entry unprovable
  because its digest has no package yet. §8.1 protects base entries and validates
  head-only first publications instead.
- **Require `(package_id, version)` uniqueness only inside a bundle closure.**
  Rejected: two internally valid specs could publish the same logical version at
  different paths with different digests, so a plan naming the version would get
  two different definitions depending on which bundle was loaded. The registry
  enforces global uniqueness and a permanent path/digest binding (§8.3).
- **Canonicalise then open each package file.** Rejected: the filesystem can
  replace a component between the two calls. The package format forbids links and
  reparse points inside a version directory, and a read may instead be
  handle-relative with no-follow semantics (§3).
- **Check each component with non-following metadata, then open by path.**
  Rejected for the same reason at one step earlier: `symlink_metadata()` can
  report a real directory that is replaced by a link before `open()`, so the two
  calls are still a check-then-use gap. The contract names the open's guarantee
  instead (§3).
- **Keep definition identity unique only among the current specs.** Rejected:
  retiring a spec would let a later PR republish the same `(namespace, version)`
  with different bytes, so one release name would answer to two definitions and a
  replay could not say which was meant. The registry keeps the identity history
  (§8.3) while `bundle_id` stays a movable release line.
- **Record `bundle_id` in the registry as an immutable identity.** Rejected: the
  publisher is expected to advance `monasm.bundle.x86_64-mov` to a new definition
  when a new package version is selected, so the entry would reject the normal
  workflow. The immutable content label is `(bundle_id, bundle_digest)`;
  `release_digest` is the evidence-complete release identity (§8, §8.3).
- **Let an H2 spec reuse a frozen `definitions/` name for a different row set.**
  Rejected: `Registry::find` requires one definition per `(namespace, version)`,
  and the frozen file already owns `monasm.isa.x86` / `0.1.0`. Reusing it would
  create two execution-rule snapshots under one name with no registry row to
  catch the second. The builder reserves the legacy set (§8) and H2 uses a new
  version, as its own bundles do with `0.1.0-h2`.
- **Rely on the bundle's larger extension set to legalise a package's rows.**
  Rejected: the merged `read` would pass while `verify --package` fails, so the
  same package would have two verdicts. The form must be inside the package and
  the package inside the bundle, and each selected package is read under its own
  target first (§4.1).
- **Recover the author's editing operation from the two case plans.** Rejected:
  the documents do not record whether a member was edited or its object was
  replaced, so two tools would infer different pointers. The difference is
  defined over final values; a mutation that changes two members is two
  differences and is rejected, and an operation-level format would need an
  explicit mutation record that `monasm-cases/0.1` does not have (§9.1).
- **Let `verify --published --check` imply provenance.** Rejected: the audit
  recomputes `snapshot_digest` over every file, so it *can* attest that the
  committed directory still matches the recorded value, but it cannot attest who
  produced the first value or that a gate was not bypassed. H2 states exactly that
  boundary (§8.4) instead of claiming the digest proves origin.
- **Decide "already published" from the merge base.** Rejected: the merge base is
  where the branch forked, so a version published on the target branch afterwards
  would be invisible and an edit to it would pass as a candidate. The gate uses
  the target-branch tip `B`, requires `Published(B) ⊆ Published(H)` and equal tree
  bytes for every `p ∈ Published(B)`, and keeps the merge base for ancestry only
  (§8.1).
- **Assume a portable `std::fs` call satisfies the no-follow bound.** Rejected:
  `File::open` follows links, so a package read would silently degrade on every
  platform. The path layer is an explicit, pinned dependency or direct platform
  call, and the V-P PoC must prove it on all three platforms before the hardened
  reader grows (§3, §6, §8.5).
- **Whitelist `requires_capabilities` without deriving it.** Rejected: a package
  that omits a capability its rows use passes the whitelist and understates its
  requirements to H3. The declared set must equal the derived set (§1.2).
- **Let a JSON library decide which pointer a case mutation differs at.**
  Rejected: replacing a value with a different kind, adding an object member and
  changing an array length are reported at different levels by different
  libraries, so two implementations could accept different case files. §9.1
  fixes the recursive rule over final values: a kind change reports the position,
  a member addition reports the member, and only an array length change reports
  the container.
- **Fold the publication-history audit into `verify --all`.** Rejected: every
  bundle build would touch every retired package, so an unrelated old package
  could break a current spec. The audit is its own command and never selects a
  package (§8.4).
- **Allow two specs to share a `bundle_id` or `(namespace, version)`.**
  Rejected: the lock path would collide, and `Registry::find` already rejects two
  definitions with one identity. H2 keeps release identities distinct and leaves
  any future sharing to an explicit mapping (§8).
- **Content-address the package directory by `source_package_digest`.** Rejected
  for H2: an author cannot know the path before writing the files, the spec
  becomes unreadable, and a digest-named path still needs a version for review.
  The version directory pins the same snapshot with a human-reviewable name.
- **Accept any negative error as form coverage.** Rejected: a wrong
  `expected_digest`, an `E-SIZE-001` at `expected_size`, or a root-level format
  error would satisfy the count without touching an operand or modifier.
  Coverage requires a baseline mutation, a `bind` rejection and a diagnostic on
  the mutated operand surface (§9.1).
- **Treat an absent `symbols` key as `[]`.** Rejected: it hides whether
  `include_symbol_table` was honoured and makes the harness normalise two
  different artifacts into one (§15).
- **Let `verify --package` claim the dependency closure from manifest shape
  alone.** Rejected: it cannot prove existence or digest equality. The closure
  status stays `unverified` without an explicit closure (§8).
- **Trust the digests a lock or spec already contains.** Rejected: a hand-written
  closure could name a dependency that is absent or changed. `--closure` and
  `--all` re-read each listed package and recompute `source_package_digest`
  before reporting `dependency_closure: verified` (§8).
- **Require the full release evidence manifest from every development package.**
  Rejected: it makes an ordinary author assemble `NOTICE`, sources and oracle
  status before the package can be structure-checked, while `--release-evidence`
  (and `--release`) already enforces the complete set. Development mode checks
  the case's own hash; a present manifest is still authoritative (§7.1).
- **Allow a formless package because `definition::read` could be bypassed.**
  Rejected: `read` is the only definition authority, and it rejects an empty
  `forms` array. A formless manifest would advertise an object no H2 build can
  produce; it is `empty-package` (§1).
- **Reuse `monasm-cases/0.1` for `fmp/0.2`, zero-operand or multi-instruction
  cases.** Rejected: the one-instruction and operand-mutation rules would be
  silently reinterpreted. A new case-format version must state its own coverage
  (§9.2).
- **Let the builder resolve dependencies recursively from IDs.** Rejected: the
  spec would no longer contain the closure, and a missing dependency would
  trigger a scan instead of a rejection.
- **Derive `definition_format` and `target_identity` from `legacy_source`.**
  Rejected: a new package has no legacy file, and two compatible targets written
  in different `fmp-def` versions could not be combined. Target facts are
  self-declared; the pin only checks migration.
- **Leave `exports.types`/`profiles` to a later format version.** Rejected: the
  ADR would claim a closed format and a seamless H4 extension at once. Reserving
  the syntax and rejecting non-empty lists is the narrower promise.
- **Treat `requires_capabilities` as a comment in H2.** Rejected: a package
  needing a primitive the core does not execute could enter a verified bundle.
  H2 rejects unknown strings at build time, derives the set from the rows and
  rejects a declaration that differs (§1.2); runtime negotiation stays H3.
- **Use `verify --all` as the only package gate.** Rejected: it enumerates
  specs, so a package that no publisher has selected would never be checked. The
  independent `verify --package` path is required.
- **Borrow a bundle's namespace/version for a standalone check.** Rejected: a
  package that is not in a spec has no bundle, and copying a released identity
  would let two packages check as the same definition. The `monasm-standalone/0.1`
  rule derives a distinct identity from the package digest.
- **Use `read` as the only package gate.** Rejected: `read` proves structural
  legality, not that the opcode or register field matches the hardware. The
  mandatory case contract and its execution are required (§9.1).
- **Treat the package's `enabled_extensions` as the full bundle target.**
  Rejected: adding one extension family would force every already-published
  package to edit its manifest and re-release, reintroducing cross-package
  synchronisation (§4.1).
- **Require `enabled_extensions` to equal the union of the form requirements.**
  Rejected: `fmp-def/0.1` forms carry no requirement key and a `0.2` form's list
  is not a complete target, so equality would fabricate a base-ISA rule or reject
  legal conservative declarations. H2 proves `⋃E_form ⊆ E_package ⊆ E_bundle`;
  exactness needs a later versioned definition of a complete requirement (§4.1).
- **Let the builder normalise a name the host filesystem accepts.** Rejected:
  lowercasing, trimming a trailing dot or space, or resolving an 8.3 alias would
  make the accepted name depend on the platform. §1.3 rejects the string and
  keeps the digest identical everywhere.
- **Compare bare relative asset paths across a package closure.** Rejected:
  `forms/add.json` and `tests/cases.json` are fixed positions that every package
  may use, so the rule would reject the ordinary two-author composition H2 exists
  to enable. Collisions are checked on relative strings inside one package and on
  repository-relative joined paths across a closure (§1.3).
- **Pre-check the declared name against the directory listing, then open by
  path.** Rejected: the two calls are another check-then-use gap, and on a
  case-insensitive volume the open still resolves `Add.json`. The exact-name
  lookup happens on the already-open parent handle (§1.3, §3).
- **Accept the on-disk case-different name on a case-insensitive host.** Rejected:
  the same package input would build on NTFS and fail on ext4, so the digest and
  the verdict would be host facts (`INV-05`). The mismatch is `path-lexical`
  everywhere (§1.3).
- **Lift `h2-exact-target` by deleting the equality check in the builder.**
  Rejected: existing `fmp/0.1` plans would silently change meaning with no
  version marker. The subset rule arrives with a new plan/definition protocol,
  and only plans that adopt it get the subset verdict (§4.1).
- **Rely on the new plan protocol alone for the lift, or let a builder upgrade
  change an old spec's verdict.** Rejected: the builder rejects the unequal
  selection before any plan is bound, so `fmp/0.2` alone leaves the same spec
  failing; and a `monasm-bundle-spec/0.1` file that was a deterministic rejection
  must not become an acceptance under newer software (§4.1).
- **Resolve a published-path change by the nearest head `package.json` first.**
  Rejected: a `package.json` added deeper inside a published snapshot would
  reclassify the edit as a different, unpublished root. Base-registry containment
  is decided first, so the edit stays `published-package-modified` (§8.1).
- **Treat one illegal neighbour as a form's complete operand domain.** Rejected:
  a single out-of-range value does not show that the minimum, the maximum and
  the adjacent illegal value behave. The shipped bounded forms carry boundary
  cases; the comparison rule stays `(code, path)` and no new error code is added
  (§9.1).
- **Take the raw `[min, max]` endpoints as boundary positives.** Rejected: an
  endpoint can be excluded or unaligned, so requiring it would demand a case that
  must fail. `x86:mov/rm8h-r8h/legacy` excludes `0..3` from a 3-bit field, and
  `aarch64:add/w32-w32-w32-imm6-lsl` excludes `32..63`; their positives come from
  `D_form`, not from the encoded range (§9.1).
- **Compare `enabled_extensions` as raw arrays in migration equality.** Rejected:
  §1 requires the canonical strictly increasing spelling, while a frozen legacy
  file keeps its published order (`definitions/rv64/0.6.0.json` is
  `["rv64i","rv64c"]`). Raw equality would reject the canonical spelling as
  `legacy-target-mismatch` and the legacy spelling as `extension-lexical`, so no
  legal package could migrate a row. `TargetEq` compares that one field as a set
  and every other field strictly (§1.1).
- **Require `min−1`/`max+1` for a register field.** Rejected: `payload.reg` is a
  `u64`, so a negative register never becomes a `Plan` and `bind` cannot reject
  it. `D_form ⊆ D_Representable`: the lower boundary is a plan-scope negative.
  The upper form negative is `2^w` only when `w < 64`; for `w ≥ 64` it is a
  representable excluded register or a wrong operand type, never an
  unrepresentable `2^w` (§9.1).
- **Assume the plan's register domain is `[0, 2^w − 1]` for every `w`.**
  Rejected: H1 `he1_wide_register.rs` proves 64/127/128/192-bit fields bind and
  encode, but `payload.reg` is still a `u64`; for `w ≥ 64` the maximum
  representable value is `u64::MAX` and `2^w` is not a test input. Treating the
  field width as the plan domain would demand impossible cases and could shrink
  the capability H1 already proved (§9.1).
- **Let `verify --package` claim the declared stage is the one that rejects.**
  Rejected: that command does not call `plan::read`, `bind` or `materialize`, so
  a case declaring `stage: "bind"` can pass it while the reader actually rejects
  the plan. Only `package_conformance` can prove the first rejecting stage and
  the complete observed set; the report records the static and executed statuses
  separately (§9.1).
- **Record `min`/`max` details that `E-OPERAND-004` does not emit.** Rejected:
  the diagnostic carries `target_type`, `value` and `field_bits`; requiring a
  `min`/`max` key would make every case fail against the validator's actual
  output. The upper bound is derived from `field_bits`, and the pass condition
  stays `(code, path)` (§9.1).
- **State that a plan-scope case can test a definition-identity mismatch.**
  Rejected: the only legal `definition_identity` is the `$standalone` sentinel and
  the harness substitutes the correct identity, so a wrong digest is
  `case-plan-identity` before execution. The derived-plan binding test carries
  that negative; no per-case override is added (§9.1).
- **Allow only `…/modifiers/<i>` in `mutates`.** Rejected: a modifier is an
  object with `name` and `value`, so a single value change reports
  `…/modifiers/<i>/value`; the old pattern made the common case inexpressible
  (§9.1).
- **Read the target relation from the plan format.** Rejected: `check_target`
  keys the subset rule on the definition format, so `fmp/0.1` + `fmp-def/0.2`
  is already a legal subset cell. A plan-format test would re-reject it and
  change H1 behaviour without a version marker (§4.1).
- **Write the path production as two or more segments.** Rejected: `NOTICE` and
  `README.md` are single-segment package-root files required by the release
  evidence gate. The production is `pseg ("/" pseg)*`, with the fixed uppercase
  names as the only exception (§1.3).
- **Match a name, then open it again by path.** Rejected: the entry can be
  replaced between the two calls, so the opened object need not be the one the
  name check described. The open is bound to the matched entry, or the
  replacement is rejected (§1.3, §3).
- **Re-open a package path after hashing it, or hash and merge from different
  buffers.** Rejected: a file changed between the two stages yields a lock whose
  source digest describes bytes the merged definition never contained. One loaded
  value feeds both (§9).
- **Let `build` require the registry row it helps create, or write that row.**
  Rejected: the row needs the `definition_digest` the build produces, so the
  first publication would deadlock; and a builder-written registry would mix
  generation with publication. `build` success, then the append, then both
  `--check`s, then the merge is the only cycle-free order (§8.3).
- **Write the registry row after a passing `--check`.** Rejected: `--all
  --check` requires a head row for every head-selected path, so a row written
  afterwards could never make that check pass. It also confuses candidate output,
  registry append and publication; only the merged commit publishes (§8.3).
- **Make `--check` rebuild the legacy snapshot.** Rejected: it would let a derived
  development cache decide a release gate, and a cache regeneration would become
  a release event. The check instead compares the committed snapshot with the
  definition it already rebuilt for the sealed bundle; the write phase removes
  the stale snapshot first and writes it last, so an interrupted write leaves it
  absent rather than stale (§8.3).
- **Leave a committed legacy snapshot out of every check because it is not an
  identity.** Rejected: the tree then ships a `--definitions` file that no release
  artifact reproduces, and a green `--check` would attest a compatibility path
  the release pair contradicts. Equality is a one-way gate and never a digest
  input (§8.3).
- **Measure JSON depth after parsing.** Rejected: the parser recurses, so a
  20 000-deep document overflows before the measurement runs. The budget is
  enforced iteratively before `fmp_model::json::parse` is called (§12).
- **Leave `tests/cases.json` out of the evidence digest.** Rejected: the same
  `release_digest` could then name two different test sets or expectations.
  Hashing the case file in `evidence/manifest.json` moves only the release
  identity, not the definition identity (§7.1).
- **Let a case declare a `form_id` without binding it to the plan.** Rejected:
  coverage becomes a manifest count, not proof that the form was exercised. The
  single instruction and error-path rules bind the claim to execution (§9.1).
- **Use an abstract "plan facts" object as the case input.** Rejected: each
  implementer would interpret the mapping differently. The case carries a
  complete `fmp/0.1` document and substitutes only the standalone identity
  sentinel (§9.1).
- **Keep `stage` at `bind`/`materialize` and express a read rejection as a
  `bind` case.** Rejected: `bind` never receives a `Plan` the reader refused, so
  either the case cannot run or it names a stage that never executed. A
  `plan::read` rejection is a plan-scope `stage: "read"` case and stays outside
  form coverage (§9.1).
- **Claim a multi-file atomic write, or "the disk cannot hold a mixed pair".**
  Rejected: a lock rename can succeed while the sealed rename fails. H2 claims
  detectability and never a successful release for that state, which is what
  `verify --all --check` tests (§8.3).
- **Make `profile_id` a global target identity with one row per name.**
  Rejected: it would need a central ISA table and would make two bundles with the
  same name but different `enabled_extensions` a contradiction H2 cannot resolve.
  The label is bundle-local and the six-key identity is the fact (§4.1).
- **Keep a three-family table in `monasm-package/0.1`.** Rejected: the mappings
  are plain string equalities; a table would force a package-format change for a
  fourth ISA added in H3 (§4.2).
- **Copy the newest definition row and compare only bytes.** Rejected: x86
  `0.78.0` rows are not the rows `X86-P1` was verified against; bytes agreeing
  for registers 0 and 3 does not make the rows equal (`HE-AC-11`).
- **Reuse the legacy definition digest for the bundle.** Rejected: a package is
  a subset with a different namespace/version and a different form order; the
  digest must name the generated document, not the legacy file.
- **Put the builder version into the definition digest.** Rejected: a builder
  bump would look like definition drift (`HE-T19`).
- **Make the builder a thin wrapper over the materializer's encoder.**
  Rejected: it would create a second authority and blur the
  development/execution split.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The repository has no `packages/`, `bundles/` or `fmp-definition` | directory listing and `prototype/Cargo.toml` members | high (measured) |
| `Definition` is closed and `bind` takes `Arc<Definition>` | `ADR-0127` §1; `fmp-validate/src/lib.rs`; `fmp-model/src/definition.rs` | high (read) |
| `fmp_model::canonical` is the canonical JSON/digest implementation | `fmp-model/src/canonical.rs` | high (read) |
| `definition_digest` is `sha256(canonical(document))` with no domain separator | `fmp-model/src/definition.rs` line 252 calls `canonical::canonical_digest(document)` | high (read) |
| Level 0 has no `symbols`; Level 1 emits `symbols` only when the table is included | `fmp-materialize/src/lib.rs` `level_zero_json` and `to_json`; the call site sets `symbols` from `plan.output.include_symbol_table` | high (read) |
| The digest fixed vector is stable across two implementations | the §7.0 vector; Python `hashlib` and .NET `SHA256` both produced `1afee65c…` | high (measured twice) |
| The bundle/release vectors follow the frozen domain separators | §8.2; Python `hashlib` recomputed `a9bc3395…` and `2416911a…` from the canonical bytes after `form_owners` and the package cover joined the preimage | high (measured) |
| `definition::read` rejects an empty `forms` array | `fmp-model/src/definition.rs` `bind_forms` returns "a definition must declare at least one form" | high (read) |
| `files[].sha256` is a raw-byte hash, not a canonical-content hash | §7.0 rule; no parser is involved in the builder's file hashing | high (specified; H2a must test CRLF/whitespace) |
| x86 `0.1.0` and `0.78.0` `mov` rows differ | canonical JSON comparison of the two rows; `0.78.0` adds `requires_extensions` and REX placements at bits 0/2 | high (measured on this host; not yet a Rust test) |
| aarch64 selected rows are equal across the pinned and newest versions | canonical JSON comparison: the two `lsl0` rows are equal in `0.1.0`/`0.2.0`/`0.20.0`; `lsl12` is absent in `0.1.0` and equal in `0.2.0`/`0.20.0` | high (measured) |
| rv64 selected rows are equal, but `0.6.0` target set differs | canonical JSON comparison; `0.6.0` is `["rv64i","rv64c"]`, the plans are `["rv64i"]`, and `check_target` requires equality for `fmp-def/0.1` | high (measured) |
| A frozen legacy extension array is not in the canonical package spelling | `definitions/rv64/0.6.0.json` declares `["rv64i","rv64c"]`; §1's canonical spelling is `["rv64c","rv64i"]`; `fmp-validate/src/lib.rs` `check_target` compares both sides as `BTreeSet` | high (read and measured) |
| `TargetEq` (set equality of `enabled_extensions`, strict equality elsewhere) is satisfiable; raw array equality is not | specified; no builder exists; a canonical package migrating an `rv64/0.6.0` row would fail both a raw-array legacy check and `extension-lexical` under the opposite spelling | **specified, not implemented** — H2a |
| Form exclusions hit raw boundary endpoints | `x86:mov/rm8h-r8h/legacy` has a 3-bit field and `excluded [0,1,2,3]`; `aarch64:add/w32-w32-w32-imm6-lsl` excludes `32..63`; `riscv:c.addi/rd-imm6` excludes `0` | high (read) |
| Boundary positives come from `D_form`, not the raw range, and their count follows its cardinality (0 → `empty-form-domain`, 1, 2, ≥3) | specified; no package cases exist; the raw endpoints of the three examples are illegal | **specified, not implemented** — H2a/H2c |
| `fmp-def/0.2` requires `requires_extensions` and rejects it in `0.1` | `bind_form` selects `FORM_FIELDS_V0_2` and `req`s the key; `FORM_FIELDS` rejects it as unknown | high (read) |
| `check_form_id` accepts any known family but does not compare it to `target_identity.isa_family` | `fmp-model/src/definition.rs` `check_form_id` matches `x86`/`aarch64`/`riscv` and returns; `bind_target` reads `isa_family` independently | high (read) |
| Builder determinism, digest reproduction, row equality and byte equality | not implemented | **unverified** — H2a/H2b must measure them |
| `verify --package`, the standalone identity, the case/plan/form binding, the release evidence hash and the changed-path gate (including deletion/rename) | not implemented | **unverified** — H2a |
| The generic `family(form_id) == isa_family` rule and its cross-ISA negative | not implemented; `check_form_id` only checks the family in isolation | **unverified** — H2a |
| Unknown-capability rejection, reserved-asset rejection, version-conflict rule and aggregate limits | not implemented | **unverified** — H2a |
| Evidence completeness, `evidence_digest` and `release_digest`, including development-mode direct case hashing versus the release manifest | not implemented | **unverified** — H2a owns the mechanism; H2c adds assets only |
| Case, evidence, spec and lock byte/count budgets, including the cumulative per-package asset budget and the single per-closure counter of §12.2 | not implemented | **unverified** — H2a |
| Immutable published version directories, legacy target consistency, form-scope mutation coverage, complete diagnostic matching and level-specific projections | not implemented | **unverified** — H2a (legacy/form-scope/projections), V-P (published directories) |
| Published-version registry, retirement survival and registry edit detection | not implemented | **unverified** — H2a |
| First publication in the creating PR, with base-only immutability | specified; the old base-or-head rule would have rejected the creating PR | **specified, not implemented** — H2a |
| Published-set authority is the target-branch tip `B`, not the merge base: `Published(B) ⊆ Published(H)` and equal tree bytes for every published path | specified; no changed-path mapper exists; the cross-branch publish-then-edit regression is untested | **specified, not implemented** — H2a |
| Package directory segment equals the full `package_id`, so the path mapping is injective | specified; no mapper exists; two IDs with the same last segment are untested | **specified, not implemented** — H2a |
| Global `(package_id, version)` uniqueness and the permanent path/digest binding | specified; per-closure uniqueness cannot exclude two paths for one logical version; V-P's registry does not exist yet | **specified, not implemented** — V-P |
| Cross-spec `bundle_id` and `(namespace, version)` uniqueness | `Registry::find` returns `E-DEF-001` when two definitions share `(namespace, version)` (`fmp-model/src/definition.rs` 843–865); the builder does not yet reject the pair at spec level | **unverified** — H2a |
| No-follow package reads (no symlink or reparse point on the resolved path under `--root`) | specified as a property of the open: a metadata pre-check followed by a path open is explicitly insufficient, and the implementation has no package reader yet | **specified, not implemented** — H2a |
| Publication-history audit separate from `verify --all --check` | specified; no command exists | **unverified** — H2a |
| Definition-identity history in the registry (`identities`) and permanent `(namespace, version)` → `definition_digest` binding | specified; no registry exists | **specified, not implemented** — H2a |
| `requires_capabilities` derived from row structure and required to equal the declaration | specified; `bind_forms` requires non-empty `slots` and `bind_slot` non-empty `placements`, so every legal `fmp-def/0.1` form derives `field-placement/v1`; no implementation | **specified, not implemented** — H2a |
| Release-shaped fixed vector with `evidence_digest` present (`evidence_digest` `e9473871…`, `release_digest` `45a4004e…`) | computed with Python over the bytes shown, not yet reproduced by a Rust implementation | **unverified on the Rust side** — H2a |
| Value-defined case diff (member edit → member pointer; kind change → position; array length → array) | specified; no harness | **specified, not implemented** — H2a |
| Form ⊆ package ⊆ bundle extension inclusion and the per-package `read` before merge | specified; `bind_forms` checks a 0.2 form against the merged target, so the merged-only check is the gap | **specified, not implemented** — H2a |
| Reserved legacy definition names from `definitions/*/*.json` | specified; the index is readable today, the builder has no reserved-set check | **specified, not implemented** — H2a |
| The publication audit covers every file in a published version directory, while still not proving provenance | `snapshot_digest` is recomputed by `verify --published --check` over every regular file; a mismatch is `snapshot-mismatch`. Who produced the first value, and a history rewrite or bypassed gate, remain outside the digest | **specified, not implemented** — V-P |
| The single-file registry's audit cost is recorded at ~1,000 published versions, with a threshold that triggers a later ADR | not measured; the registry does not exist; V-P must run three runs each for a package change, a publication and a full audit (including snapshot re-hashing), recording time, memory and bytes read | **unverified** — V-P |
| The no-follow open is achievable on Linux, macOS and Windows | not proved; `std::fs` has no portable no-follow open, so the V-P N1b PoC must measure a path layer on all three platforms as a standalone deliverable that records OS version, toolchain/API, fault injection and per-case result before the hardened reader | **unverified** — V-P N1b |
| Identifier, path-segment and artifact-filename rules are format rejections before any open | specified; the builder has no package reader | **unverified** — H2a |
| The same relative asset path in two different package roots is legal, and a folded root alias or repeated spec path is `path-lexical` | specified; no closure reader exists | **unverified** — H2a |
| A declared lowercase path does not open a case-different on-disk entry, on intermediate directory or final file | specified as part of the open; no path layer exists | **unverified** — H2a N1 gate (Linux, macOS, Windows) |
| Opening is bound to the directory entry that was name-checked, so a replacement between the two is not read | specified; no path layer exists; not yet measured on any platform | **unverified** — H2a N1 gate |
| `payload.reg` is a `u64`, so a negative register number is a `plan::read` rejection | `fmp-model/src/plan.rs` `bind_payload` calls `bind::u64_in`; `bind.rs` `u64_in` accepts only `0..=u64::MAX` | high (read) |
| `check_target` keys the set relation on the definition format, not the plan format | `fmp-validate/src/lib.rs` `subset_rule = model.definition.definition_format() == DEFINITION_FORMAT_V0_2` | high (read) |
| `E-OPERAND-004` carries `target_type`, `value` and `field_bits`, and `E-RANGE-004` carries `target_type`, `value` and `excluded` | `fmp-validate/src/lib.rs` `check_operand` and `excluded_diagnostic` | high (read) |
| A modifier is `{name, value}`, so a single value change reports `…/modifiers/<i>/value` | `fmp-model/src/plan.rs` `bind_modifier` closes the object on `name` and `value` | high (read) |
| Boundary evidence uses the final legal domain `D_form = {x ∈ D_Representable, L≤x≤U, x≡0 (mod 2^a)} \ E` (registers: `D_reg`), never a raw endpoint the form excludes, and records only emitted diagnostic fields | specified; the three packages and their cases do not exist; `x86:mov/rm8h-r8h/legacy`, `aarch64:add/w32-w32-w32-imm6-lsl` and `riscv:c.addi/rd-imm6` exclude their raw endpoints | **unverified** — H2a/H2b |
| A register field wider than 64 bits binds and encodes 64/127/128/192-bit placements | `prototype/crates/fmp-materialize/tests/he1_wide_register.rs` calls `fmp_validate::bind` and `fmp_materialize::materialize` for each width and asserts bytes | high (measured by the H1 test) |
| `verify --package` validates only the static case contract; `package_conformance` proves the first rejecting stage and the complete diagnostic set | specified; no package reader or conformance harness exists; a `stage: "bind"` case that `read` rejects passes the static check and must fail conformance | **specified, not implemented** — H2a |
| The plan×definition matrix keeps `fmp/0.1` + `fmp-def/0.1` equality and `fmp/0.1` + `fmp-def/0.2` subset, and only a new plan protocol plus a versioned build rule lifts `h2-exact-target` | existing two cells read from `check_target`; the new-plan cell and the versioned build rule do not exist; `monasm-bundle-spec/0.1` has no builder yet | **partly measured, H3 gate** |
| One loaded package value feeds the source digest, row/target comparison, per-package `read` and merge | specified; no reader exists | **unverified** — H2a |
| First publication bootstraps without a registry cycle, and `build` validates every output before writing | specified; the order is build success → append rows → both `--check`s → commit, and publication is the merged commit; no builder exists | **unverified** — H2a |
| `--check` proves the lock and sealed bundle, and compares a committed legacy snapshot with the sealed definition as a one-way equality gate (absence legal, no digest input) | specified; the write phase removes `<legacy>/definition.json` first and writes it last, so an interrupted write leaves it absent, not stale; no builder exists | **specified, not implemented** — H2a |
| A committed legacy snapshot whose bytes differ from the sealed definition is `legacy-snapshot-mismatch` (exit 1) | specified; the gate compares canonical bytes without rebuilding the cache; no `--check` exists | **specified, not implemented** — H2a |
| A definition-identity mismatch is not expressible as a `monasm-cases/0.1` case | the case requires the `$standalone` sentinel and the harness substitutes the correct identity, so a wrong digest is `case-plan-identity`; the derived-plan binding test carries the negative | **specified; reader behaviour read** — H2a |
| The base registry (target-branch tip `B`) decides published-path containment before head-side `package.json` discovery | specified; no changed-path mapper exists, so a nested manifest masking an ancestor is untested | **specified, not implemented** — V-P |
| A version published on the target branch after a feature branch forked still freezes that branch's edits | specified; the counterexample is a fork from `M0`, publication of `P/0.1.0` on the target branch, then an edit to `P/0.1.0/README.md`; tip-based `Published(B) ⊆ Published(H)` plus tree-byte equality rejects it, and `snapshot_digest` independently detects the edit in the audit | **specified, not implemented** — V-P |
| A publication verdict authorizes only the `(B_checked, C_checked, mode)` triple it read: a stale green result cannot authorize a merge after another PR publishes first | specified; requires a merge queue or an operation that writes the recorded candidate, and V-P must prove the setting through the platform API; no workflow or settings evidence exists | **specified, not implemented** — V-P N5 |
| H3 target subsets check `E_package(owner(form(i))) ⊆ E_plan` for every selected instruction, from `form_owners` plus the owner's declared cover, and add a per-form conjunct only when the format proves that requirement complete; a form without a proof is rejected | specified; `monasm-bundle/0.1` carries the owner map and covers, but H2 builds no subset cell and no H3 plan or consumer exists; the `c.addi`/`rv64i` case is untested | **specified, not implemented** — H3 |
| `monasm-bundle/0.1` is self-verifying: `bundle_digest` is recomputed from the file's own `target`, per-package `enabled_extensions`, `form_owners` and `definition` | specified; the §7 preimage is complete inside the nine-key file, the lock is checked separately for paths, evidence and builder, and the §8 vectors were recomputed from that preimage; no sealed bundle or consumer exists | **specified, not implemented** — H2a (build), H3 (consume) |
| Required up-to-date checks alone do not prove the landed tree equals the tested tree; a 403 or empty ruleset list is missing evidence, not absence of protection | specified; an API read attempt during review returned 403 and the ruleset query was inconclusive, and no merge-queue evidence has been recorded | **unobtained; V-P must record API evidence** |
| N5 cannot close on a green CI run: the effective merge mechanism must be recorded and the stale-CI counterexample executed, or the publication verdict stops at the gate | specified; `Gates`/`Determinism` succeeded on the planning PR, but a green run is a verdict for its own `(B_checked, C_checked, mode)` and does not demonstrate the mechanism; no counterexample has been run | **unobtained; V-P N5** |
| `monasm-bundle/0.1` has exactly nine keys, carries the bundle-level `target`, each package's `enabled_extensions` and a complete `form_owners` map, and its `bundle_digest` is recomputable from the file | specified; this revision replaced the round-21 companion rule and the round-22 seven-key set; no sealed bundle exists, so the key-set, owner-map and self-verification tests are unrun | **specified, not implemented** — H2a |
| `builder` records provenance but does not prove it; a change to `builder.version`/`build` can pass `--all --check` | specified; the drift projection excludes `builder` and no digest covers it; no lock exists, so the counterexample is unrun | **specified, not implemented** — H2a |
| `monasm-package/0.1` rejects non-empty `exports.types`/`exports.profiles` permanently, independent of the builder version; a later format version owns the semantics | specified; no builder exists, and no later package format is written | **specified, not implemented** — H2a |
| Input budgets apply in one order — lexical path, no-follow open, handle type check, same-handle size hint, bounded read, parse — and metadata size is never the boundary | specified; no reader exists; a file that grows between type check and read is covered by the cumulative counter | **specified, not implemented** — H2a |
| A build never writes a legacy snapshot above its 16 MiB read budget; a legal closure above it builds with the snapshot omitted and passes `--all --check` | specified; no builder exists; the synthetic over-16 MiB definition case is untested | **specified, not implemented** — H2a |
| Only a regular file is accepted at an opened leaf, checked on the handle, and a POSIX FIFO is rejected without blocking | specified; no path layer exists; the N1 gate must create a FIFO at a declared asset path on Linux/macOS and require `not-a-regular-file` (exit 1) rather than a blocking read or exit 2 | **specified, not implemented** — H2a N1 gate |
| A retired bundle's lock, sealed bundle and legacy snapshot leave the tree with its last spec, and `--all --check` rejects an orphan | specified; no builder and no `--all --check` exist; the one-to-one rule is untested | **specified, not implemented** — H2a |
| Extension and capability arrays have one strictly increasing, duplicate-free spelling | specified; `extension-lexical`/`capability-lexical` are format rejections before the set relation | **specified, not implemented** — H2a |
| The 64 MiB closure budget charges every package-root byte read, once per path, and rejects at the crossing read | specified; the counted set is manifest, declared assets, cases, evidence manifest and listed evidence files; no reader exists | **specified, not implemented** — H2a |
| For `fmp-def/0.1`, `E_form = ∅`, so only `E_package ⊆ E_bundle` is proved; a `legacy_source` package adds target consistency, not a form-derived requirement | specified; `FORM_FIELDS` rejects `requires_extensions` in 0.1, and no builder exists | **specified, not implemented** — H2a |
| `enabled_extensions` is a conservative declared cover, not a minimal required set | specified; `fmp-def/0.1` forms have no requirement key and no builder exists | **unverified** — H2a |
| Form-scope negatives are `bind`-only and point at the mutated operand | specified; `fmp-materialize/src/lib.rs` emits `E-BYTE-001` at `/instructions/0/expected_digest` after encoding, so the counterexample is real | **specified, not implemented** — H2a |
| A `plan::read` rejection has a legal case representation (`scope: "plan"` + `stage: "read"`), and the declared stage must be the first stage that rejects | `fmp-model/src/plan.rs` `read` returns `Result<Plan, Diagnostic>` and `bind_payload` calls `bind::u64_in`, so `{"reg":-1}` is `E-PLAN-002` at `/instructions/0/operands/<n>/payload/reg` before `bind`; no harness | **specified, reader behaviour read** — H2a |
| `profile_id` is a nominal label inside one bundle; identity is the six-key `target.identity` | specified; no spec or bundle exists, and no cross-spec `(profile_id, identity)` rule is added | **specified, not implemented** — H2a |
| Output parents under `--root` obey the no-follow rule, and the committed lock/sealed bundle are compared through a bounded streaming reader | specified; no writer and no path layer exist, so the `path-escape` and over-budget rejections are untested | **specified, not implemented** — H2a N1 |
| An interrupted write may leave a mixed lock/sealed pair, and such a pair never passes `--check` | specified; the write phase and `--check` do not exist | **specified, not implemented** — H2a |
| Dependency-closure status distinct from package structure, including transitive re-reading of a `--closure` lock, cycles and the dependent-package author path | not implemented | **unverified** — H2a |
| Release evidence as a separate `--release-evidence` gate | not implemented | **unverified** — H2a |
| Closed spec/lock/sealed shapes, `builder` omission and the lock drift projection | not implemented | **unverified** — H2a |
| `empty-package` rejection and the rejection of `monasm-cases/0.1` for `fmp/0.2`/zero-operand cases | not implemented | **unverified** — H2a |
| Pre-parse JSON depth rejection | not implemented; H0 probe only shows the existing recursive parser can overflow | **unverified** — H2a must add the iterative budget |
| Deep-JSON robustness | H0 probe reproduced a stack overflow; H2 does not change the parser | **unverified / out of H2** — H4 |

## Review triggers

- Someone adds a package by editing `STATUS.md`, a central form table or
  `check_definition.py`: stop. The package path is digest- and manifest-driven;
  a central count is the old workflow (`ADR-0125` decision 4).
- Someone makes the builder read a package not listed in the spec: stop. That
  reintroduces discovery and breaks `HE-AC-05` before H3.
- Someone makes the spec's `source_package_digest` optional or derived silently
  by `build`: stop. The author's selection must be visible in the spec, and the
  lock must record exactly what was selected.
- Someone compares `payload_digest` or `fingerprint` as the H2 byte-equivalence
  key: stop. The projection is machine output; the definition identity is
  expected to differ.
- Someone replaces the `legacy_source` pin with "newest": stop. The x86 and
  rv64 measurements are the counterexamples.
- Someone moves the package conformance harness into a runtime crate or adds a
  product dependency from `fmp-definition` to `fmp-materialize`: stop. That
  creates a second definition authority.
- Someone makes `legacy_source` required for a package that is not a migration:
  stop. Target facts are self-declared; requiring a legacy file recreates the
  dependency this ADR removes.
- Someone converts `fmp-def/0.1` rows to `0.2` inside the builder: stop. Mixed
  closures are rejected; conversion is explicit H3 work.
- Someone accepts a non-empty `exports.types` or `exports.profiles` in H2, or
  relaxes `monasm-package/0.1` because a newer builder "knows" the field: stop.
  H2 does not define their semantics, and acceptance belongs to the declared
  `package_format`; a later builder upgrade must not widen an unchanged `0.1`
  document (§5).
- Someone uses `verify --all` as the only package gate: stop. It enumerates
  specs, so a new unselected package would never be verified.
- Someone lets a development package skip its case hash check, or lets
  `--release-evidence`/`--release` proceed without an evidence manifest: stop.
  Development mode checks the case's own `sha256`; the release gates require the
  complete set (§7.1).
- Someone reports `dependency_closure: verified` from a lock or spec digest
  without re-reading the dependency bytes, or checks only direct dependencies:
  stop. §8 requires a transitive re-read.
- Someone decides "published" from the current specs instead of
  `bundles/published.json`: stop. The two-step retirement bypass is the
  counterexample (§8.3).
- Someone decides "already published" from the merge base rather than the
  target-branch tip `B`, or accepts a published path whose bytes changed in `H`:
  stop. `Published(B) ⊆ Published(H)` and equal tree bytes are the whole
  invariant; a version published after the branch forked is still frozen (§8.1).
- Someone reuses a green publication result without checking that its recorded
  base commit and candidate tree are the ones being merged: stop. The verdict is
  keyed on `(B_checked, C_checked, mode)`; a target tip or merge mode that moved
  invalidates it, and no other gate looks at those bytes (§8.1).
- Someone cites "required branches to be up to date" as proof that the landed
  tree equals the tested tree, treats a 403 or an empty ruleset list as proof
  that no protection exists, or closes N5 on a green CI run or a post-merge
  audit: stop. Up-to-date checks bound base staleness, not tree identity; the
  mechanism plus the stale-CI counterexample is the evidence, and without it the
  publication verdict stops (§8.1, §8.5).
- Someone gives `monasm-bundle/0.1` a `sources` key, removes a key the digest
  covers, or describes the file as "verified through its lock": stop. The sealed
  key set is the nine keys in §8.2, `packages` is the package-list name,
  `form_owners` has exactly one row per form, and the digest preimage is complete
  inside the file (§7, §8.2).
- Someone adds `target`, `form_owners` or a package cover outside the
  `bundle_digest` preimage, or treats a missing owner row as an empty requirement:
  stop. Data outside the digest is rewritable under a stable identity, and an
  absent row means "unproved", not `∅`; `bundle-owner-incomplete` is a format
  rejection (§4.1, §7, §8.2).
- Someone treats a passing author-layer verdict as a publication, creates
  `bundles/published.json` before the publication channel passes, or promotes a
  development artifact by relabelling it: stop. V-A and V-P are separate verdicts;
  no artifact is published, immutable or trusted until V-P passes, and the first
  publication re-verifies through the hardened reader (§8.5).
- Someone describes `snapshot_digest` as provenance, or uses it to replace the
  changed-path gate and the merge-freshness proof: stop. It binds committed bytes
  to a recorded value; who produced the first value, and a history rewrite or a
  bypassed gate, are outside what an in-repo digest can attest (§8.3, §8.4).
- Someone treats `builder` as proof that the declared implementation produced
  the bundle, or folds `builder` back into the definition digest to make it one:
  stop. It is an informational provenance record; trusted provenance needs a
  separate attestation or signature (§7).
- Someone lets a consumer accept a sealed bundle's `bundle_digest` without
  recomputing it from the bytes the file carries, or passes a bare sealed file to
  `bind` as permission: stop. Every preimage field is in the file, so the value is
  recomputable; recomputation proves what the bundle says, not that a plan may use
  it, and `bind` still takes a `Definition` (§7, §8.2).
- Someone presents the single-file registry or the full-history audit as a proven
  scalability property, drops the 1,000-version budget, or crosses a recorded
  threshold without a new ADR: stop. It is a measured, accepted cost with a
  written trigger, and it is a scale boundary for *publication*, not a claim that
  independent package development does not scale (§8.3).
- Someone claims that independent authoring implies coordination-free parallel
  publishing, or removes the rebase-and-revalidate rule because the package
  change path is localized: stop. The registry is one shared file; H2 promises
  correct serialization, not parallel publication throughput (§8.3).
- Someone demotes the N1 PoC to a plan note, or accepts "theoretically possible"
  as three-platform evidence: stop. The PoC is a separate prerequisite deliverable
  of the publication channel with recorded platform, toolchain, API,
  fault-injection and result rows; it does not gate the author layer (§3, §8.5).
- Someone lifts `h2-exact-target` by adding `fmp/0.2` and checking only
  `E_plan ⊆ E_bundle`: stop. Every selected instruction must satisfy
  `E_package(owner(form(i))) ⊆ E_plan`, from `form_owners` plus the owner's
  declared cover, and a per-form conjunct may replace that cover only when the
  format proves the requirement complete; H2 freezes those facts but runs no
  subset cell (§4.1).
- Someone reads a legacy form's absent `requires_extensions` as the empty set and
  lets any subset plan select it: stop. Absent means unproved; the subset
  composition is rejected until the artifact supplies the proof (§4.1).
- Someone names the package directory from the last dot-separated segment of
  `package_id`: stop. The component equals the full `package_id`, so
  `monasm.x86.crypto` and `vendor.x86.crypto` can coexist; the last-segment
  mapping is not injective (§1.3).
- Someone accepts a FIFO, socket or device node as a package or artifact input, or
  decides the type from a path `stat` or a size: stop. A legal no-follow open can
  land on a non-regular object, and a read on it can block outside every budget;
  the type comes from the opened handle (§3, §12).
- Someone lets `build` write a legacy snapshot above its 16 MiB read budget, or
  makes an oversized canonical definition fail the build: stop. The snapshot is
  an optional cache; `build` omits it and `--check` accepts the absence, so the
  two commands cannot disagree about a legal closure (§8.3, §12).
- Someone leaves a retired spec's lock, sealed bundle or legacy snapshot in the
  tree and calls it an archive: stop. An unselected sealed file is rebuilt by no
  gate, so its status is undefined; retiring the last spec removes the derived
  artifacts, and git history is the archive (§8.4).
- Someone verifies a path by calling `symlink_metadata()` and then opening the
  same path string, or treats a canonicalise/check step as the guarantee: stop.
  The no-follow property belongs to the open, not to a preceding check (§3).
- Someone compares declared paths only case-sensitively, or lets a trailing
  dot/space, a Windows device name or a non-ASCII segment reach an open: stop.
  §1.3 makes the name a format rule with one diagnostic on every platform.
- Someone compares bare relative asset paths across a package closure: stop.
  Equal `forms/add.json` names under different package roots are legal; the
  closure domain is the repository-relative joined path, and only a folded root
  alias or a repeated spec path collides (§1.3).
- Someone accepts a case-insensitive open, compares an absolute path string, or
  probes the directory before opening it: stop. The declared segment must equal
  the opened entry name byte-for-byte, checked on the already-open parent handle
  (§1.3, §3).
- Someone matches the name and then re-opens the path without binding the open to
  the matched entry: stop. A replacement in the gap reads an object no check
  described; either open the matched entry or reject the replacement (§1.3, §3).
- Someone requires at least two path segments, or rejects a single-segment
  `NOTICE`: stop. The production is `pseg ("/" pseg)*`, and `README.md`/`NOTICE`
  are the fixed uppercase exceptions (§1.3).
- Someone lifts `h2-exact-target` by removing the equality check, makes a
  `fmp/0.1` + `fmp-def/0.1` pair accept a subset, or keys the relation on the
  plan format and re-rejects `fmp/0.1` + `fmp-def/0.2`: stop. The existing cells
  stay fixed and only a new plan protocol **together with the versioned build
  rule** adds one (§4.1).
- Someone lets a builder upgrade accept a `monasm-bundle-spec/0.1` selection that
  it rejected before, or claims a new `fmp/0.2` plan format alone lifts the
  build-time check: stop. The lift needs a versioned build rule, and the old spec
  keeps its rejection conclusion (§4.1).
- Someone lets a nested `package.json` reclassify a change inside a
  base-registered version directory: stop. Base-registry containment is decided
  before head discovery, and any change inside the snapshot is
  `published-package-modified` (§8.1).
- Someone counts one illegal neighbour as a bounded operand's whole domain, or
  moves `field_bits`/`value` evidence into the pass comparison: stop. Boundary
  cases stay inside `D_Representable` and are taken from `D_form`, and the pass
  condition stays the `(code, path)` set (§9.1).
- Someone requires a raw range endpoint as a positive when that endpoint is
  excluded or unaligned: stop. Positives are the minimum and maximum of `D_form`
  plus an interior value; `aarch64:add/w32-w32-w32-imm6-lsl` has `31`, not `63`,
  as its positive maximum (§9.1).
- Someone makes a negative register number a `scope:"form"` case, reports it at
  `stage: "bind"`, or records `min`/`max` that `E-OPERAND-004` does not emit:
  stop. A negative register is a plan-scope `stage: "read"` rejection; the register
  encoded bound comes from `field_bits`, and for `w ≥ 64` the representable
  maximum is `u64::MAX` (§9.1).
- Someone requires `2^w` or `2^w − 1` for a slot whose encoded width exceeds 64,
  or caps the author layer at 64 bits because `payload.reg` is a `u64`: stop.
  H1's `he1_wide_register.rs` proves 127/192-bit fields bind and encode; the
  boundary cases use `0`/`u64::MAX` plus an excluded value or wrong operand type
  (§9.1).
- Someone declares a stage that is not the first stage that rejects, or gives a
  form-scope case `stage: "read"` or `"materialize"`: stop. The stages are a
  sequence, `bind` never sees a `Plan` the reader refused, and a reader rejection
  is not form coverage (§9.1).
- Someone reports `verify --package` as having proved the declared stage, or
  treats a statically valid `stage: "bind"` case as executed evidence: stop.
  That command never calls `plan::read`/`bind`/`materialize`; only
  `package_conformance` proves the first rejecting stage and the full observed
  diagnostic set, and the two statuses are reported separately (§9.1).
- Someone writes a plan-scope case that claims a definition-identity mismatch, or
  adds a per-case identity override so that one is expressible: stop. The only
  legal value is the `$standalone` sentinel and the harness substitutes the
  correct identity; the derived-plan binding test carries that negative (§9.1).
- Someone allows only `…/modifiers/<i>` in `mutates`, or rejects
  `…/modifiers/<i>/value`: stop. A single modifier value change is a legal form
  mutation, and the validator's array-level diagnostic is its ancestor (§9.1).
- Someone re-opens a package path after computing its digest, or hashes one
  buffer and merges another: stop. One loaded value feeds the digest, the row
  comparison, the per-package `read` and the merge (§9).
- Someone makes `build` require the registry row it helps create, or lets
  `build` write the registry: stop. First publication is build, then append,
  then both `--check`s, then commit (§8.3).
- Someone writes the registry row only after a passing `--check`, or treats the
  merge of the creating PR as anything other than the publication moment: stop.
  `verify --all --check` requires the row, so that order cannot run, and an
  unmerged row is only a candidate (§8.3).
- Someone makes `--check` rebuild the legacy snapshot, or drops its equality gate
  because the snapshot is not an identity: stop. The gate compares committed bytes
  with the rebuilt sealed definition and never rebuilds the cache; absence is
  legal, but a present-and-different snapshot is `legacy-snapshot-mismatch`
  (§8.3, §7).
- Someone restates the write guarantee as "an interrupted write cannot leave a
  mixed lock/sealed pair", or adds a multi-file atomicity claim: stop. The
  guarantee is detectability — a mixed pair fails `verify --all --check` and is
  never a successful release (§8.3).
- Someone writes an output file through a parent that was not checked for a
  symlink or reparse point, or trusts the output directory as a sandbox: stop.
  Output directories are trusted but every parent segment under `--root` obeys
  the §3 no-follow rule (§8.3).
- Someone compares the committed sealed bundle with an unbounded `read_to_end`,
  or lets an over-budget committed file become a host error: stop. The comparison
  streams against the in-memory rebuild within the 1 MiB lock and 80 MiB sealed
  budgets, and the excess is `resource-limit` (§8.3, §12).
- Someone accepts a reversed or duplicated `enabled_extensions` or
  `requires_capabilities` array because the set is unchanged: stop. The array has
  one spelling and the violation is `extension-lexical`/`capability-lexical`
  (§1, §1.2).
- Someone counts only manifest and asset bytes toward the 64 MiB closure budget,
  or charges a diamond dependency twice: stop. The counter charges every
  package-root byte the command reads, once per path, and rejects at the crossing
  read (§12.2).
- Someone treats `enabled_extensions` as exactly the union of the form
  requirements, or trims an over-declared cover: stop. The declared set is a
  conservative cover and exactness is a later format (§4.1).
- Someone reports "the target cover relation is verified" as "the ISA extension
  requirements are completely proved", or adds an ISA-specific derivation to make
  `fmp-def/0.1`'s empty `E_form` look meaningful: stop. For 0.1 only
  `E_package ⊆ E_bundle` is proved, and the ISA authority stays outside the
  builder (§4.1).
- Someone keys compatibility, a definition lookup or a digest on `profile_id`
  alone, or requires one global meaning for a profile name: stop. `profile_id`
  is a nominal label equal to the package's `target_profile` inside one bundle;
  the identity is the six-key `target.identity`, and no cross-spec uniqueness for
  `(profile_id, identity)` exists in H2 (§4.1).
- Someone lets a retired `(namespace, version)` come back with a different
  `definition_digest`, or treats `bundle_id` as an immutable release identity:
  stop. The definition name is permanent and the bundle ID is a movable release
  line whose immutable content label is `(bundle_id, bundle_digest)`; the
  evidence-complete release identity is `release_digest` (§8, §8.3).
- Someone lets an H2 spec reuse a name from `definitions/`, or binds such a name
  in the registry: stop. The frozen legacy names are reserved and the check is
  `reserved-identity`, not a special case (§8).
- Someone accepts `requires_capabilities` as written without deriving the set
  from the rows, or adds a capability H2 cannot derive: stop. Declared must equal
  derived; a new primitive is a new format version (§1.2).
- Someone adds a test that expects a slotless form to pass `read`, or relaxes
  `read` to make the §7.0 preimage fixture buildable: stop. That fixture is a
  hash input only; every legal form has slots and placements (§1.2, §7.0).
- Someone lets a form's `requires_extensions` be covered only by the bundle, or
  removes the per-package `read`: stop. The package is read under its own target
  before the merge, and form ⊆ package ⊆ bundle holds per package (§4.1).
- Someone lets a diff library pick the case-mutation pointer level, or treats a
  whole-object replacement as the container pointer when the members differ:
  stop. The difference is defined over final values, so a member edit is a member
  pointer and a two-member change is two differences (§9.1).
- Someone claims `verify --published --check` proves whole-directory immutability:
  stop. It proves the executable assets and identity; the changed-path gate and
  git history carry the rest (§8.4).
- Someone counts an `E-BYTE-001`/`E-SIZE-001` materialize failure, or any
  diagnostic not on the mutated operand, as form coverage: stop. Form-scope
  negatives are `bind` rejections at the mutated operand surface (§9.1).
- Someone accepts an empty `exports.forms` because the merged document would
  "still read": stop. `definition::read` rejects it; the package is
  `empty-package` (§1).
- Someone reuses `monasm-cases/0.1` for `fmp/0.2`, a zero-operand form or a
  multi-instruction fixup scenario: stop. A new case-format version is required
  (§9.2).
- Someone derives the standalone namespace/version from the path, the working
  directory or a spec: stop. The `monasm-standalone/0.1` rule must be
  reproducible and distinct from a release identity.
- Someone lets a package with forms merge without `tests/cases.json`, or accepts
  a form with no positive case: stop. `read` does not check an opcode.
- Someone treats the package `enabled_extensions` as the full bundle selection:
  stop. That forces an unrelated package edit for every new extension family.
- Someone accepts a form whose family differs from the package
  `isa_family`: stop. `read` checks the family in isolation; the package must
  check the correspondence.
- Someone parses first and measures depth afterwards: stop. The recursive parser
  is the thing the budget protects.
- Someone skips a `packages/**` change because no `package.json` was found:
  stop. Deletions and renames must be resolved against the target-branch tip
  `B` or fail.
- Someone leaves `tests/cases.json` out of the evidence manifest for a
  release-ready package: stop. The release identity must cover the test
  contract, and a case edit without a manifest update must fail.
- Someone lets a case declare form B while its plan executes form A, or accepts
  a negative case whose error path is outside `/instructions/0`: stop. Coverage
  must be evidence of execution, not a manifest count.
- Someone adds an `x86`/`aarch64`/`riscv` allowlist to the package builder:
  stop. The rule is `family(form_id) == isa_family`; the definition reader owns
  the set of families it can parse.
- Someone edits a file inside a version directory in the **base** published
  registry: stop. That is `published-package-modified`; the author must add a
  sibling version and the publisher selects it separately.
- Someone treats a head-only registry entry as immutability for the PR that adds
  it: stop. A version must be creatable and first-publishable in one PR; only
  base entries are frozen, and the head entry is validated against the final
  snapshot (§8.1).
- Someone enforces `(package_id, version)` uniqueness only inside a closure, or
  lets a second entry reuse the pair at another path or digest: stop. The
  registry identity is global and permanently bound to its first entry (§8.3).
- Someone lets two specs share a `bundle_id` or a `(namespace, version)`: stop.
  The lock path collides and `Registry::find` cannot distinguish the definitions
  (§8).
- Someone canonicalises then opens a package file, or accepts a symlink or
  reparse point on the path from `--root` to the opened file: stop. The no-follow
  bound must hold for the whole read (§3).
- Someone audits only spec-selected entries, or folds the publication-history
  audit into `verify --all --check`: stop. Retired versions must stay checked
  without entering a bundle closure (§8.4).
- Someone compares only form rows when `legacy_source` is present: stop. The
  package's `definition_format` must equal the pinned document's, and its
  `target_identity` must satisfy `TargetEq`: every field equal except
  `enabled_extensions`, which is compared as a set, or the migration is not
  proven (§1.1). Comparing that one field as a raw array makes a canonical
  package and a frozen legacy file mutually unsatisfiable.
- Someone lets `expected_digest`, `format_version` or a root-level error satisfy
  a form's negative coverage, or accepts one matching diagnostic among others:
  stop. Only a `scope: "form"` baseline mutation with complete diagnostic-set
  equality counts.
- Someone changes a digest preimage, the `sha256:` text rule or the fixed vector
  without a package-format version bump: stop. Old and new implementations would
  disagree on the same bytes.
- Someone normalises an absent `symbols` to `[]`, adds `size` to the Level 1
  projection, or drops `fingerprint` handling into the harness: stop. §15 fixes
  each level's key set exactly.
- Someone reports `dependency_closure: verified` for a package with dependencies
  but no explicit closure: stop. Structure and closure are separate claims.
