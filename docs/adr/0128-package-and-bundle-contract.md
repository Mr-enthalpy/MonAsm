# ADR-0128: the package and bundle contract, and the H2 definition builder

- Status: proposed
- Date: 2026-11-14
- Review: this is a proposal, not a frozen decision. It stays `proposed` until
  the H2 planning PR is reviewed and merged; `accepted` is written only after
  that review, and H2a does not start before it.
- Revision: eighth revision, 2026-11-16, after the cross-history and
  composition audit: the case diff is defined over the two **final values**, so
  a member addition reports the member and only a kind change reports the
  container; an H2 definition name may not collide with a frozen legacy
  `definitions/` identity; every exported form's extension requirement must be
  inside the package requirement, and the package inside the bundle, with a
  per-package `read` before the merge; the slotless form in §7.0 is labelled as
  a digest preimage rather than a legal Definition; the publication audit's
  guarantee is narrowed to the executable assets and identity; the digest
  layers are named by the question each answers; and the path work is an H2a
  platform feasibility gate. The seventh revision's open-time no-follow rule,
  definition-name history, movable `bundle_id` and derived capability set
  remain in force.
- Settles: the `monasm-package/0.1`, `monasm-bundle-spec/0.1`,
  `monasm-lock/0.1`, `monasm-bundle/0.1` and `monasm-published/0.1` formats;
  immutable published package version directories and their append-only
  registry, including global `(package_id, version)` identity binding, the
  permanent `(namespace, version)` → `definition_digest` history, the movable
  `bundle_id` release line, and the separate publication-history audit; the
  declared-versus-derived capability set; the release-shaped digest vector; the
  value-defined case diff; the digest layering and its byte-level
  preimages; the reservation of every frozen legacy definition name; the
  form/package/bundle extension inclusion and the per-package `read`; package
  target self-description and migration provenance, including legacy target
  consistency; the standalone definition identity used by `verify --package`; the
  mandatory package case and evidence gate with `bind`-only form-scope mutation
  and complete diagnostic sets; exact Level 0/Level 1 machine-output projections;
  package target requirements versus bundle target selection; package/form
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
`packages/<target>/<owned-package>/<version>/**` instead of a hand-edited full
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

`packages/<target>/<package>/<version>/package.json` is the only entry point.
The target directory is a path component (`x86_64`, `aarch64`, `rv64`), not a
form-ID prefix. The `<version>` component is exactly the manifest's `version`
string; the spec's `packages[].path` and `packages[].version` must agree with
that component. A mismatch is `path-version-mismatch` (exit 1). The manifest is
`monasm-package/0.1` and is a closed object:

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
| `exports.types`, `exports.profiles` | optional; reserved asset declarations, must be empty in H2 |

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
rather than silently canonicalised. Each `forms/*.json` holds exactly one form
object; its `form_id` must equal the declared `id`.

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

- a `packages/<target>/<package>/<version>/` directory is a **source snapshot**;
- a version is **published** when its entry exists in the registry of a merged
  commit. The publisher adds that entry in the same PR that first selects the
  version in a `bundles/specs/*.json`; the registry entry, not the current spec
  set, is the permanent record. The PR that first adds the entry may still create
  and adjust the candidate directory: the new entry is validated against that
  PR's final head snapshot, and only the merged snapshot is immutable;
- after publication, no file under that directory may be added, modified,
  renamed or deleted — including `README`, `NOTICE`, `evidence/` and
  `tests/cases.json`. A change is `published-package-modified` (exit 1);
- new forms, fixed encodings or new evidence require a new sibling directory
  `packages/<target>/<package>/<new-version>/`, with its own manifest version and
  digest. The old directory stays byte-for-byte in place: while its selecting
  spec remains in the head tree, `verify --all --check` still rebuilds the old
  lock and sealed bundle; after the last spec is retired, the snapshot, lock and
  sealed bundle remain committed and replayable at the old commit, but the
  head-tree `--all` run no longer has a selection for them;
- updating a spec to select the new version, adding the new registry entry and
  regenerating its lock/sealed bundle is a separate publisher decision. An
  ordinary package change does not edit any spec, lock, sealed bundle or
  registry entry;
- removing a spec retires a release but deletes neither the snapshot nor its
  registry entry. H2 does not add an archival or deletion tool; retiring the
  bytes themselves needs a later ADR.

The CI changed-path gate resolves each `packages/**` change in the head tree and,
for a deletion, in the base tree. It then asks the **base published registry**
(§8.3) whether that snapshot was already published. If so, any changed file fails
the gate before `verify --package` runs (§8.1). A version whose entry exists only
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
present, the builder also requires the package's `definition_format` and its
whole `target_identity` object to equal the pinned legacy document's values, not
just be individually legal. The comparison is canonical equality of the parsed
objects (`isa_family`, `isa_variant`, `execution_mode`, `enabled_extensions`,
`byte_order`, `address_width` and any field the legacy target declares). A
mismatch is `legacy-target-mismatch` (exit 1), reported before the merged
document is read. This does not make the legacy file the target authority: the
package still declares its target, and a new package without `legacy_source` is
checked only against its declaration. It closes the gap where a copied row is
byte-equal but the package claims `execution_mode: "32"` or
`address_width: 32`, so "self-declared target" and "row equal" are both true
while the migrated execution semantics are not. A deliberate target change
needs an explicit, versioned compatibility record in a later format; H2 rejects
it rather than inferring it.

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

Every manifest path is a normalised relative path using `/`. Absolute paths,
`..`, empty segments, `.`, backslashes, NUL, URL schemes and drive letters are
rejected. The bound is a property of the **open**, not of a moment before it: no
component on the path from `--root` to an opened file may be a symlink or
reparse point, and the builder never traverses one. H2 package inputs contain no
such links on that path; a package that has one is `path-escape` (exit 1).

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
`path-escape`; the builder does not resolve it and call the result bounded. H2
does not claim protection against an attacker who can rewrite the worktree after
a successful build, nor against a hostile `--root` itself; it does claim that a
successful build opened exactly the objects the checks describe. The spec's
`packages[].path` and the `--root` resolution obey the same rule; `--root` may be
canonicalised once to establish the base, but no component below it is opened
through a followed link. `legacy_source.isa` and `legacy_source.version`
are path components before they are concatenated into
`<root>/definitions/<isa>/<version>.json`, so they receive the same treatment:
`isa` must match `^[a-z0-9_]+$` and `version` must match
`^[0-9]+(\.[0-9]+)+$`. A value containing `/`, `\`, `..`, `.` as a whole
component, a drive letter, a URL scheme or NUL is rejected before the path is
formed; the builder does not normalise a value into legality.
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
assumed here: H2a's first review node is a platform feasibility gate that must
demonstrate it with intermediate-directory links, final-file links, Windows reparse
points and a swap between check and open, or stop the round instead of shipping a
following open. If a platform cannot be satisfied, the builder refuses package
reads there with `path-escape`; a build that succeeds on Linux but refuses every
package on Windows is a failed H2a gate, not a passing one.

### 4. The spec lists the full closure; the builder never scans packages

`bundles/specs/<bundle>.json` is `monasm-bundle-spec/0.1`:

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
      "path": "packages/x86_64/mov-register/0.1.0",
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
`dependencies` are verification edges: every edge must resolve to a listed
`(package_id, version)` with exactly the listed `source_package_digest`. An edge
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
`enabled_extensions` is different: a package's list is a requirement and the
bundle's list is the selected target, so the package list must be a subset of
the bundle list (§4.1). Every package's `target_profile` must equal
`target.profile_id`. A closure whose packages disagree on the structural target
fields or on `definition_format` is rejected; the builder does not pick a winner
and does not convert a package. A package with `legacy_source` is additionally
checked against that pinned row, but the pin never supplies the target facts.
The builder writes the selected identity into the generated definition; it does
not consult a central Rust target table. That is the H3 precondition "a new
target does not edit a public whitelist".

Counterexamples: without the full list, the builder must discover dependencies
and an unselected corrupt package can break an old build (`HE-AC-05`); without
exact IDs, "latest" or a range picks a version the author did not name
(`HE-AC-04`, `HE-T08`); without paths, the builder must scan to find a package.

#### 4.1 A package declares a target requirement; the bundle selects the target

The composition problem is concrete. Package A (`rv64i` arithmetic) declares
`enabled_extensions: ["rv64i"]`; package B (`rv64c` compressed) declares
`["rv64i","rv64c"]`. If the package list were the full target configuration, A
and B could never share a bundle, because the builder would demand that A's
manifest also say `rv64c`. Adding the compressed family would force every
already-published package to edit its manifest, changing `source_package_digest`
and re-releasing unrelated packages. That is the cross-package synchronisation
`ADR-0125` exists to remove.

The contract therefore separates the two facts:

| Fact | Declared by | Meaning |
|---|---|---|
| package `target_identity.enabled_extensions` | each package | the minimum extension set the package's rows require |
| bundle `target.identity.enabled_extensions` | the spec | the complete set selected for this bundle |

The builder requires every package's requirement to be a subset of the selected
bundle set, and requires the other target fields to be equal. A package is not
edited when a new, disjoint extension family joins the bundle; the new package
declares its own larger requirement and the spec selects the union.

That subset rule alone is not enough, because a bundle's wider selection can
hide a package that under-declares itself. The full rule is per exported form:

```text
E_form(f) ⊆ E_package ⊆ E_bundle      for every selected package P and f ∈ P.forms
```

`E_form(f)` is `form.requires_extensions` for `fmp-def/0.2`; it is `∅` for
`fmp-def/0.1`, whose form object has no such key (`FORM_FIELDS` rejects it).
`E_package` is `target_identity.enabled_extensions`; `E_bundle` is the spec's
`target.identity.enabled_extensions`. The builder computes the union of
`E_form(f)` over the package's exported rows and rejects a package whose union
is not a subset of its own declaration (`form-extension-mismatch`, exit 1),
before it looks at the bundle. The package-to-bundle subset is then checked as
above.

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
requires `["rv64c"]`, and the spec selects `["rv64i","rv64c"]`. Package ⊆ bundle
passes, and the merged `read` passes because the generated target carries
`rv64c`. `verify --package` on the same bytes fails, because the package's own
target is `["rv64i"]`. Adding `rv64c` to the manifest fixes it; the larger bundle
must not be the reason a row became legal. Under `fmp-def/0.1` the same mistake
is impossible to express at the form level, which is why the H2a test uses a
0.2 fixture for this rule and does not infer the rule from the three 0.1
packages.

**H2 transition.** `fmp-def/0.1` plans compare `enabled_extensions` for set
equality at `bind` (`check_target`), so an H2 bundle that selected a superset
would reject the existing reference plans. While `definition_format` is
`fmp-def/0.1`, H2 additionally requires the package requirement to equal the
bundle selection exactly; this is the transitional `h2-exact-target` check, not
a permanent package-contract rule. `fmp-def/0.2` already applies the subset
rule, and a future `fmp/0.2` plan format must make the same distinction on the
plan side.

**Exit condition.** H3 must define plan-level target compatibility so a plan may
target a subset of the definition/bundle set without rewriting the definition.
That H3 result is what lifts `h2-exact-target`. It must be in force before H5's
parallel-extension drills; if it is not, this ADR's package contract must be
revised by a new ADR before H5 starts. H2 does not claim the transitional
equality is the final composition rule, and it does not freeze a package
manifest that must be edited for every new extension family.

No `monasm-package/0.1` bump is required to lift the transition: the package
field already means "the extensions these rows require", and the builder already
checks the subset. H3 changes the *plan-side* comparison (and the reference
plans' target sets), not the meaning of the package manifest. A new package
format version is needed only if a future target relationship is not expressible
as a subset of the same extension vocabulary.

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
check applies to a package's `exports.types`/`exports.profiles` when H4 gives
them a family-bearing identity.

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
type_id    -> package_id + version + source_package_digest   # reserved; non-empty rejected in H2
profile_id -> package_id + version + source_package_digest   # reserved; H4 owns the semantics
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
records zero assets. This is a real reservation: the key, the `{id, path}`
shape, the ordering rule and the digest input are fixed now, so H4 adds
semantics without changing the manifest key set. It is not a promise that H2
executes or emits those assets; a non-empty list fails closed. Only the outer
identity, ordering, digest input and rejection semantics are frozen: the inner
type/profile semantics (shared types, composed profiles) are H4's proposal, and
if H4 needs a different structure it must evolve the format version rather than
treat this placeholder shape as verified semantics.

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

| Digest | Input | Excludes | Counterexample if it were missing or collapsed |
|---|---|---|---|
| `source_package_digest` | `sha256(b"monasm-package/0.1" ++ 0x00 ++ canonical(record))`, where `record = {"manifest": manifest, "assets": [{"kind", "path", "digest"}]}` and assets are sorted by `path`; `digest` is the literal `sha256:<hex>` text from §7.0, never raw bytes; `kind` is `form`, `type` or `profile` | README, NOTICE, evidence manifest, tests, author path | Hashing only the manifest: swapping a form's template with the manifest unchanged leaves the package digest still. |
| `evidence_digest` | `sha256(b"monasm-evidence/0.1" ++ 0x00 ++ canonical(evidence/manifest.json))` when the file exists; `files[].sha256` is bare 64-lowercase-hex text per §7.0; its `files` list includes `tests/cases.json` for a release-ready package | unlisted README/NOTICE text, oracle log contents, author path; the case bytes are covered only through their manifest hash | Not hashing `tests/cases.json`: editing a plan or expectation leaves the same release identity covering two test sets. |
| `definition_digest` | `fmp_model::definition::read(merged_document).digest()`, which is exactly `sha256(canonical(merged_document))` with no domain separator | builder version, build time, host, source paths | Hashing only the package set: two different form rows produce the same bundle identity. |
| `bundle_digest` | `sha256(b"monasm-bundle/0.1" ++ 0x00 ++ canonical(bundle_metadata))`, where metadata is `{bundle_id, definition_digest, definition_format, namespace, version, target, packages: [{package_id, version, source_package_digest}]}` sorted by package identity; every nested digest is the literal `sha256:` text | the `bundle_digest` field itself, the builder receipt, package paths | Including the digest in its own preimage: the fixed point does not exist. |
| `release_digest` | `sha256(b"monasm-release/0.1" ++ 0x00 ++ canonical(release_metadata))`, where metadata is `{bundle_id, bundle_digest, definition_digest, packages: [{package_id, version, source_package_digest, evidence_digest}]}` sorted by package identity; every nested digest is the literal `sha256:` text. `evidence_digest` is present for every entry of a committed lock, which is written only for a release-ready closure (§7.1); the metadata shape admits its absence only for a development build, which is not a released identity | the definition rows themselves, the builder receipt, sealed bytes | Two releases that share a definition but ship different evidence have no distinguishing identity. |
| `builder` | `{name, version, build: Option<String>}`; lock and receipt only | the definition digest | Putting the builder version into `definition_digest`: a builder bump falsely reports definition drift (`HE-T19`). |

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

- `bundles/specs/<bundle>.json` — `monasm-bundle-spec/0.1`, the author's
  explicit selection.
- `bundles/locks/<bundle>.lock.json` — `monasm-lock/0.1`, generated: the full
  bundle metadata (`bundle_id`, `definition_format`, `namespace`, `version`,
  `target`, `bundle_digest`, `definition_digest`, `release_digest`), the sorted
  package list with `path`, `source_package_digest` and `evidence_digest`
  (present for a release-ready package, §7.1), and `builder`.
- `bundles/sealed/<bundle>.bundle.json` — `monasm-bundle/0.1`, generated:
  `bundle_format`, `bundle_id`, the canonical definition document,
  `bundle_digest`, `definition_digest`, and the sorted `sources` list
  `{package_id, version, source_package_digest}`. It does not contain the builder
  receipt, `release_digest` or author paths.
- `bundles/legacy/<bundle>/definition.json` — generated: the plain merged
  definition document, with no bundle envelope, so the existing
  `fmp materialize <plan> --definitions <dir>` path can load it. It is a
  development bridge, not a release identity. `Registry::load_dir` recursively
  reads every `.json` under the directory and calls `definition::read`, so the
  sealed `.bundle.json` cannot be used here; point `--definitions` at the
  directory that contains only this snapshot.

The binary has three subcommands: `build` writes the lock, sealed bundle and
legacy snapshot; `verify` rebuilds in memory; and `digest <package-path>` prints
the computed `source_package_digest` so an author can write it into the spec.
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
sealed bundle byte-for-byte and the lock byte-for-byte **except `builder`**. It
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
the **base registry** (entries already published at the merge base) from the
**head registry** (the entries this PR proposes). Only a base entry makes a
snapshot immutable during this PR; a head-only entry is a **first publication**
and is validated, not rejected.

- **Modified or added file:** resolve the nearest ancestor `package.json` in the
  head tree. Its directory must be a version directory whose name equals the
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
- **Deleted file or directory:** resolve the version directory in the **base**
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
`packages/x86_64/mov-register/0.1.0/` must also add its registry entry. If the
gate treated any head entry as immutability, the entry would forbid the very
files it registers and no package could ever be born. If the gate ignored the
head registry instead, a PR could add an entry plus a mismatched directory in one
step; the path/digest validation above is what rejects that. Deleting a base
entry to escape is already `published-registry-modified`, so the split does not
reopen the retirement bypass.

Counterexample for global uniqueness: spec A selects `monasm.x86.mov` `0.1.0`
at `packages/x86_64/mov-a/0.1.0` with digest D₁, and spec B selects the same
`package_id`/`version` at `packages/x86_64/mov-b/0.1.0` with digest D₂. Each
closure is internally consistent and each path is unique, so a path-only registry
accepts both rows. The same logical version now has two published contents, and a
reader naming `monasm.x86.mov`/`0.1.0` can get either definition depending on
which bundle was loaded. The `(package_id, version)` rule in §8.3 rejects the
second entry.

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
keys in §4.1. `packages` is non-empty, strictly sorted by `(package_id,
version)` with no duplicates, and each entry has exactly `package_id`, `version`,
`path`, `source_package_digest`. A reversed or equal-key entry is rejected; the
builder never re-sorts an alternate spelling.

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
      "path": "packages/x86_64/example/0.1.0",
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
`definition_format`, `definition_digest`, `bundle_digest`, `definition`,
`packages`. `definition` is the merged definition document of §9 (not a second
envelope), and each `packages` entry has exactly `package_id`, `version`,
`source_package_digest`. There is no `path`, `builder`, `release_digest` or
`evidence_digest`, so `verify --check` compares its bytes exactly, with no
excluded key.

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
{"bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","definition_format":"fmp-def/0.1","namespace":"monasm.isa.x86","packages":[{"package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}],"target":{"identity":{"address_width":64,"byte_order":"little","enabled_extensions":[],"execution_mode":"64","isa_family":"x86","isa_variant":"x86-64"},"profile_id":"monasm.target.x86_64"},"version":"0.1.0-h2"}
bundle_digest = sha256:b6d925747e41428db2e6dd31d72d7bd05739ab8d552fb53bcd73402af54931fd

release metadata canonical =
{"bundle_digest":"sha256:b6d925747e41428db2e6dd31d72d7bd05739ab8d552fb53bcd73402af54931fd","bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","packages":[{"package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}]}
release_digest = sha256:4e3d44a86a966b7d1829d823c6aad00f92cc08a567eee7d23e70e4ecfa6bf8cc
```

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
{"bundle_digest":"sha256:b6d925747e41428db2e6dd31d72d7bd05739ab8d552fb53bcd73402af54931fd","bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","packages":[{"evidence_digest":"sha256:e94738716ffc56d6f1a865c463fee4afae03835d51ef234bff2c213e321f931a","package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}]}
release_digest = sha256:ba60e8bab8f15ae57972ee24510798fc7721430fa4508dc810011a753a8d3235
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
      "path": "packages/x86_64/example/0.1.0",
      "package_id": "monasm.x86.example",
      "version": "0.1.0",
      "source_package_digest": "sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0"
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
`published` entry has exactly `path`, `package_id`, `version` and
`source_package_digest`, sorted strictly by `path`; each `identities` entry has
exactly `definition_digest`, `namespace` and `version`, sorted strictly by
`(namespace, version)`. Either array may be empty. Three uniqueness rules hold
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
  with the digest the merged document actually produces; a missing row is
  `published-registry-incomplete` (exit 1) and a digest disagreement is
  `definition-identity-conflict` (exit 1);
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
  in the base tree may remain after every spec retires, and must remain.
- A base entry may not be removed, edited, reordered or replaced. Any change to
  the base registry other than inserting a new entry in sorted position is
  `published-registry-modified` (exit 1). A new entry must be selected by at
  least one head spec and must match the package at its `path`; otherwise it is
  `published-registry-invalid` (exit 1). A head-only entry may be removed in the
  same PR only when no head spec selects its path. The `identities` rows follow
  the same rules, with `definition-identity-conflict` for a reused name and a
  different digest.
- Each entry's `source_package_digest` must equal the digest recomputed from the
  package at `path`. A mismatch is `published-registry-invalid` (exit 1), and
  any byte change under a base-published path is also
  `published-package-modified` (exit 1).
- The registry is a publication fact, not a selection input. Neither array enters
  `source_package_digest`, `definition_digest`, `bundle_digest` or
  `release_digest`, and it can never add a package to a bundle. The `identities`
  digest is checked against the built definition, never fed into it.
- Retiring a release removes a spec but never removes the snapshot or its
  registry entry. Deleting both in one PR is `published-registry-modified`, not
  a legal retirement.

Counterexample if the registry were replaced by "the current specs": PR A
removes the last spec that selects `0.1.0/`, then PR B modifies that directory.
Both the base and head trees of PR B contain no selecting spec, so a spec-only
check would call the snapshot unpublished and accept the edit. The registry
entry survives PR A, so PR B still fails `published-package-modified`.

Counterexample if first publication were treated as immutability: the H2a PR
creates `packages/x86_64/mov-register/0.1.0/` and its first registry entry
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
  closure?" It reads only the paths selected by `bundles/specs/*.json`, plus the
  registry facts needed to decide publication and validity for those paths. It
  never opens an unselected package, so an unselected package cannot change its
  result (`HE-AC-05`).
- **Publication-history audit** (`verify --published --check`) answers "is every
  published entry still valid?" It reads every entry in
  `bundles/published.json`, including versions that no current spec selects, and
  checks the closed shape, sorted order, unique `path`, unique
  `(package_id, version)`, the identity binding, that the path exists and is a
  version directory, that the manifest's `package_id`/`version` match the entry,
  and that the recomputed `source_package_digest` equals the recorded one. It
  also checks the `identities` rows: unique and sorted `(namespace, version)`,
  one digest per name, no row naming a reserved legacy pair (§8), and — for a
  name that a current spec still publishes — agreement with the digest the
  current build produces; disagreement is `definition-identity-conflict`
  (exit 1), a missing row for a published spec is
  `published-registry-incomplete` (exit 1). A package-entry mismatch is
  `published-registry-invalid` (exit 1); a directory/manifest version disagreement
  is `path-version-mismatch` (exit 1). The audit never selects a package into a
  bundle and never changes a lock or sealed bundle. The changed-path gate (§8.1)
  reports the underlying file edit as `published-package-modified`; the audit
  reports the registry effect, not the file edit. The audit applies the §12
  per-package byte and count budgets to each entry it re-reads; it has no closure
  aggregate because it is not a bundle.

CI runs both. If only `--all --check` ran, a retired version with no selecting
spec would never be re-hashed. If the audit were folded into `--all`, every
bundle build would read every historical package and an unrelated retired package
could break an old spec, which is the discovery coupling H2 removes.

**The audit's guarantee is bounded, and the contract states the bound.** It
proves that the published manifest, the declared executable assets and the
`(package_id, version)`/`(namespace, version)` identities are unchanged, because
those are what `source_package_digest` covers (§5, §7.0). It does **not**
independently prove that every byte under a published version directory is
unchanged: `source_package_digest` deliberately excludes `README.md`, `NOTICE`,
`evidence/**` and `tests/cases.json`, and the registry stores neither
`evidence_digest` nor a full file list. A retired package whose
`tests/cases.json` and `evidence/manifest.json` are edited and re-hashed
consistently keeps the same `source_package_digest`, so `verify --published
--check` alone cannot see it.

Whole-directory immutability is enforced at the merge path instead: the
changed-path gate (§8.1) rejects any added, modified, renamed or deleted file
under a base-registered version directory, and the merged bytes remain in git
history. An edit that bypassed both the gate and review is outside what this
command attests.

Adding a `snapshot_digest` over the full published file list would close the gap
inside the audit, because the registry is append-only and the value could be
recomputed. H2 does not add it: it would need a defined file-set rule (whether
`package.json`, evidence and later-added files are in the set), a new registry
field and a second digest per version, and the gate already rejects every such
edit in the normal path. The narrower claim is deliberate; a later format that
must prove whole-snapshot equality can add the field and widen it.

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
document with the package's `definition_format`, calls `read`, and compares
pinned rows only when `legacy_source` is present. It never writes a lock or
sealed bundle, so a package author can run it before any spec exists.

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
  `fmp/0.1` failure, including a wrong `expected_digest`, a bad section layout,
  a target mismatch or a definition-identity error. It is validated and
  executed, but it does not count toward a form's negative coverage.
- `scope: "form"` is the illegal-neighbourhood test for one exported form. It
  must name a `baseline_case_id` that is a positive case in the same file with
  the same `form_id` and `instruction_id`, and a single `mutates` pointer. A
  missing baseline, a baseline of another kind, form or instruction, or a
  `scope: "form"` case without both keys is `case-baseline-invalid` (exit 1).
- `mutates` must match
  `^/instructions/0/operands/[0-9]+/(payload(/[^/]+)*|kind|target_type|modifiers(/[0-9]+)?)$`.
  That is the form-constraint surface: an operand value, operand kind, target
  type or modifier. A mutation at `expected_digest`, `form_id`, `offset`,
  `section_id`, `expected_size`, `output_contract` or `definition_identity` is
  not a form-neighbourhood test; it must use `scope: "plan"` or is
  `case-mutation-mismatch` (exit 1).
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
  `expect_error.stage` must be `bind`. `stage: "materialize"` on a form-scope
  case is `case-error-scope` (exit 1). Post-encode assertions are not
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

`stage` is `bind` or `materialize`. `diagnostics` is a non-empty array sorted by
`(path, code)`, unique, and each entry is a closed object over exactly `code`
and `path`. The harness projects the observed diagnostics to `(code, path)`,
sorts them by `(path, code)`, and requires **set equality** with the declared
array: same length, same members, no duplicates. One matching error among
others is a failure (`case-diagnostics-mismatch`, exit 1). Detail maps are not
part of the case contract; the complete set of `(code, path)` pairs is.

The observed set is the full array returned for that stage:

- `stage: "bind"`: `plan::read` must accept the document; `bind` returns all
  diagnostics. Any array, including an empty one, is compared as-is.
- `stage: "materialize"`: `bind` must return zero diagnostics. Only
  `PostEncodeAssertion(diagnostics)` can satisfy the case; `Internal` or
  `HostFailure` is `case-materialize-fault` (exit 2), never a pass. This stage is
  legal only for `scope: "plan"`; a form-scope case using it is
  `case-error-scope` (exit 1).

For `scope: "form"`, every declared and observed path must be `/instructions/0`
or start with `/instructions/0/`; any other path is `case-error-scope` (exit 1).
In addition, the required set must contain at least one path on the mutated
operand surface as defined above. A wildcard, "any error", a root-level error
such as a wrong `format_version`, or an `E-BYTE-001`/`E-SIZE-001` artifact
assertion therefore cannot satisfy a form's negative coverage. For
`scope: "plan"` any path is allowed. Coverage is counted only from `scope:
"form"` negatives: every exported form needs at least one positive and at least
one such negative, or the package is `uncovered-form`.

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
plans. It also validates the declared `stage`, the sorted unique `diagnostics`
array and the `case-error-scope` rule. It does not execute `bind` or
`materialize`, because the product binary depends only on `fmp-model`. The
`package_conformance` test in `fmp-definition/tests/` builds each package under
its standalone identity (§2.1) and executes every case with the dev-dependency
graph, matching the complete observed diagnostic set. It enumerates
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
| Package structure verified | `verify --package` accepted the manifest, assets, cases and evidence | any declared dependency was resolved |
| Dependency closure verified | every dependency matched an explicit closure entry by ID, version and digest | H2 packages declare any dependencies |
| Package machine-code test passed | `package_conformance` matched the declared expectation and the complete diagnostic set | an independent tool was run |
| Evidence traceable | the manifest lists the files and every hash matches | the recorded oracle result is true |
| Independent oracle re-verified | an external tool was actually re-run and compared on this host | H2 does this for new packages |

None of the first five implies the last. H2 records evidence and executes the
declared cases; it does not claim a fresh oracle run for a new package.

H2 does not add per-ISA branches to the harness. It dispatches from
`tests/cases.json` and `package.json` only (`HE-T14`).

#### 9.2 `monasm-cases/0.1` is H2's model, not a universal one

`monasm-cases/0.1` deliberately promises only what H2 can execute: one
`fmp/0.1` plan, exactly one instruction, and a negative neighbourhood expressed
as one operand-surface mutation. It does not define:

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
  coverage.

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
| Deterministic rejection | manifest shape (required/optional keys), empty forms, path escape or a symlink/reparse point on a package path, declared-vs-derived capability mismatch, a form requirement outside the package declaration (`form-extension-mismatch`), missing/duplicate/cyclic dependency, dependency digest mismatch, two versions of one package ID, cross-spec `bundle_id` or definition-identity conflict, reuse of a reserved legacy definition name, digest mismatch, ownership conflict, row mismatch, legacy target mismatch, form-family mismatch, unknown capability, non-empty reserved asset, evidence mismatch or incompleteness, missing/uncovered case, unsupported case format, case/plan/form binding, case baseline or mutation, form-scope materialize stage, form-scope diagnostic not on the mutated operand, incomplete diagnostic set, wrong expectation projection, unmapped package path, published snapshot modification, registry modification, global identity duplication, incompleteness or invalidity, path/version mismatch, reserved identity, closure aggregate limit, `read` rejection, resource limit | 1 |
| Host / I/O / internal | unreadable file, unwritable lock, internal invariant break, materializer `Internal`/`HostFailure` during conformance | 2 |
| Success | build or verify passed, digest printed | 0 |

The enum names these rejections (`unsupported-capability`, `capability-mismatch`,
`unsupported-asset`,
`version-conflict`, `aggregate-limit`, `legacy-row-mismatch`,
`legacy-target-mismatch`, `evidence-mismatch`, `evidence-incomplete`,
`missing-cases`, `uncovered-form`, `empty-package`, `case-evidence-mismatch`,
`case-plan-identity`, `case-form-mismatch`, `case-error-scope`,
`case-format-unsupported`, `case-baseline-invalid`, `case-mutation-mismatch`,
`case-diagnostics-mismatch`, `case-expect-shape`, `form-family-mismatch`,
`form-extension-mismatch`, `reserved-identity`, `path-version-mismatch`,
`path-escape`,
`published-package-modified`, `published-registry-modified`,
`published-registry-incomplete`, `published-registry-invalid`,
`bundle-id-conflict`, `definition-identity-conflict`, `unmapped-package-path`,
`dependency-unverified`, `dependency-mismatch`); they
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
  ≤ 1 MiB each; the pinned legacy definition file read for row comparison
  ≤ 16 MiB; `bundles/published.json` ≤ 16 MiB and ≤ 65 536 entries;
- exported forms per package ≤ 1024; declared assets per package ≤ 2048; cases
  per package ≤ 4096; evidence files per package ≤ 4096;
- manifest plus declared asset bytes per package ≤ 16 MiB, enforced by the
  cumulative read in §12.1;
- total evidence bytes per package ≤ 16 MiB;
- packages per closure ≤ 1024; total package bytes per closure ≤ 64 MiB;
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

An over-limit input is a deterministic rejection (exit 1). The builder checks
the file length from metadata before opening and reading it, so a case or
evidence file cannot bypass the per-package budget just because no spec selects
the package. The depth budget is
enforced **before and during** parsing, not by parsing first and measuring the
result: the builder scans the bytes iteratively (counting `{`/`[` outside string
literals) and refuses a document that would exceed the budget before it calls
`fmp_model::json::parse`, whose descent is recursive. A document smaller than
1 MiB with tens of thousands of nesting levels is a required negative; it must
be rejected without recursing to the stack limit. This is the builder's own
input budget; it is not a claim that `fmp` is robust to deep JSON, and a parser
stack overflow from a 20 000-deep document remains H4 (`HE-T13`). H2's package
inputs are developer-controlled.

#### 12.1 The per-package asset budget is cumulative and enforced while reading

Each manifest and form/type/profile file is read through a bounded reader. The
builder adds every byte it actually reads to one per-package counter and
rejects as soon as the next read would cross 16 MiB. File metadata is a hint,
not the check: a file can grow between `stat` and `read`, and a symlink or
reparse target can report a different size. The reader therefore stops at the
remaining budget and treats a short or overlong read as `resource-limit` (exit
1). The counter is reset for each package; it is not the closure total.

Counterexample if only the per-file limit existed: 2048 files of 1 MiB each pass
every per-file check and make the builder read 2 GiB for one package. A single
`verify --package` run has no closure total, so the cumulative counter is the
only bound that applies.

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
  at build time only.
- No implicit conversion between `fmp-def/0.1` and `fmp-def/0.2`; a mixed
  closure is rejected, and an explicit versioned conversion is H3 work.
- No execution or emission of `type`/`profile` assets; a non-empty declaration
  is rejected (H4).
- No `bind(VerifiedBundle, ...)` and no `fmp-validate → fmp-definition`
  dependency (H3).
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
  present, its `definition_format` and full `target_identity` must equal the
  pinned legacy document's. A deliberately retargeted package is rejected rather
  than inferred from matching rows.
- Form coverage is an illegal-neighbourhood claim, not a count. A negative case
  must name a positive baseline, mutate exactly one operand field, be rejected by
  `bind`, and name a diagnostic on the mutated operand or its parent object. A
  wrong `expected_digest` or an `E-BYTE-001`/`E-SIZE-001` artifact assertion may
  be a plan-scope test but cannot cover a form.
- Publication is recorded in an append-only registry, so a version remains
  immutable after its last spec retires. A later PR cannot reclassify an old
  snapshot as unpublished by deleting a spec. A version can be created and first
  published in one PR, because only base entries make it immutable, but the
  merged snapshot is validated against the entry. A `(package_id, version)`
  names one path and one source digest forever, so two bundles cannot publish
  two different contents under the same logical version.
- Bundle verification and publication-history auditing are separate commands.
  `verify --all --check` keeps unselected packages out of a bundle build, while
  `verify --published --check` still re-hashes retired versions. Neither can
  silently take over the other's job.
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
  checks described. The mechanism is a platform capability, so H2a's first gate
  proves it on Linux, macOS and Windows rather than assuming a portable call.
- A form's extension requirement must already be inside its own package's
  declaration, and the package inside the bundle's selection. A wider bundle
  cannot make an under-declared package legal: the package is read under its own
  target before the merge, so `verify --package` and `verify --all` agree on it.
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
- The publication audit's claim is bounded to the executable assets and
  identity. Whole-directory immutability is enforced by the changed-path gate and
  recorded by git history, not re-attested by `verify --published --check`; H2
  says so instead of implying a snapshot proof it does not have.
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
  H3's plan-side compatibility lifts it before H5.
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
  add the subset-based plan target rule without changing the package, spec or
  lock formats; the plan format is the H3 surface that changes.

## Alternatives rejected

- **Scan `packages/**` and build a global `(id, version)` index.** Rejected: a
  damaged unselected package would affect an old build, contradicting
  `HE-AC-05`, and selection would be directory-driven (`INV-05`).
- **Overwrite `packages/<target>/<package>/` in place and update every spec on a
  package change.** Rejected: an ordinary author would again edit global specs and
  locks, which is the coordination H2 exists to remove. The version directory is
  the immutability boundary.
- **Use the current spec set as the publication record.** Rejected: retiring the
  last spec would erase the evidence that a version was published, so a later PR
  could edit the old snapshot. §8.3 keeps an append-only registry that survives
  retirement.
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
- **Let `verify --published --check` imply whole-directory immutability.**
  Rejected: `source_package_digest` excludes README, NOTICE, evidence and cases,
  so the audit cannot attest those bytes. H2 narrows the claim to executable
  assets and identity and leaves whole-snapshot enforcement to the changed-path
  gate and git history; adding a full `snapshot_digest` is a later format (§8.4).
- **Assume a portable `std::fs` call satisfies the no-follow bound.** Rejected:
  `File::open` follows links, so a package read would silently degrade on every
  platform. The path layer is an explicit, pinned dependency or direct platform
  call, and H2a must prove it on all three platforms before the builder grows
  (§3, §6).
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
| The bundle/release vectors follow the frozen domain separators | §8.2; Python `hashlib` recomputed `b6d92574…` and `4e3d44a8…` from the canonical bytes | high (measured) |
| `definition::read` rejects an empty `forms` array | `fmp-model/src/definition.rs` `bind_forms` returns "a definition must declare at least one form" | high (read) |
| `files[].sha256` is a raw-byte hash, not a canonical-content hash | §7.0 rule; no parser is involved in the builder's file hashing | high (specified; H2a must test CRLF/whitespace) |
| x86 `0.1.0` and `0.78.0` `mov` rows differ | canonical JSON comparison of the two rows; `0.78.0` adds `requires_extensions` and REX placements at bits 0/2 | high (measured on this host; not yet a Rust test) |
| aarch64 selected rows are equal across the pinned and newest versions | canonical JSON comparison: the two `lsl0` rows are equal in `0.1.0`/`0.2.0`/`0.20.0`; `lsl12` is absent in `0.1.0` and equal in `0.2.0`/`0.20.0` | high (measured) |
| rv64 selected rows are equal, but `0.6.0` target set differs | canonical JSON comparison; `0.6.0` is `["rv64i","rv64c"]`, the plans are `["rv64i"]`, and `check_target` requires equality for `fmp-def/0.1` | high (measured) |
| `fmp-def/0.2` requires `requires_extensions` and rejects it in `0.1` | `bind_form` selects `FORM_FIELDS_V0_2` and `req`s the key; `FORM_FIELDS` rejects it as unknown | high (read) |
| `check_form_id` accepts any known family but does not compare it to `target_identity.isa_family` | `fmp-model/src/definition.rs` `check_form_id` matches `x86`/`aarch64`/`riscv` and returns; `bind_target` reads `isa_family` independently | high (read) |
| Builder determinism, digest reproduction, row equality and byte equality | not implemented | **unverified** — H2a/H2b must measure them |
| `verify --package`, the standalone identity, the case/plan/form binding, the release evidence hash and the changed-path gate (including deletion/rename) | not implemented | **unverified** — H2a |
| The generic `family(form_id) == isa_family` rule and its cross-ISA negative | not implemented; `check_form_id` only checks the family in isolation | **unverified** — H2a |
| Unknown-capability rejection, reserved-asset rejection, version-conflict rule and aggregate limits | not implemented | **unverified** — H2a |
| Evidence completeness, `evidence_digest` and `release_digest`, including development-mode direct case hashing versus the release manifest | not implemented | **unverified** — H2a owns the mechanism; H2b adds assets only |
| Case, evidence, spec and lock byte/count budgets, including the cumulative per-package asset budget | not implemented | **unverified** — H2a |
| Immutable published version directories, legacy target consistency, form-scope mutation coverage, complete diagnostic matching and level-specific projections | not implemented | **unverified** — H2a |
| Published-version registry, retirement survival and registry edit detection | not implemented | **unverified** — H2a |
| First publication in the creating PR, with base-only immutability | specified; the old base-or-head rule would have rejected the creating PR | **specified, not implemented** — H2a |
| Global `(package_id, version)` uniqueness and the permanent path/digest binding | specified; per-closure uniqueness cannot exclude two paths for one logical version | **specified, not implemented** — H2a |
| Cross-spec `bundle_id` and `(namespace, version)` uniqueness | `Registry::find` returns `E-DEF-001` when two definitions share `(namespace, version)` (`fmp-model/src/definition.rs` 843–865); the builder does not yet reject the pair at spec level | **unverified** — H2a |
| No-follow package reads (no symlink or reparse point on the resolved path under `--root`) | specified as a property of the open: a metadata pre-check followed by a path open is explicitly insufficient, and the implementation has no package reader yet | **specified, not implemented** — H2a |
| Publication-history audit separate from `verify --all --check` | specified; no command exists | **unverified** — H2a |
| Definition-identity history in the registry (`identities`) and permanent `(namespace, version)` → `definition_digest` binding | specified; no registry exists | **specified, not implemented** — H2a |
| `requires_capabilities` derived from row structure and required to equal the declaration | specified; `bind_forms` requires non-empty `slots` and `bind_slot` non-empty `placements`, so every legal `fmp-def/0.1` form derives `field-placement/v1`; no implementation | **specified, not implemented** — H2a |
| Release-shaped fixed vector with `evidence_digest` present (`evidence_digest` `e9473871…`, `release_digest` `ba60e8ba…`) | computed with Python over the bytes shown, not yet reproduced by a Rust implementation | **unverified on the Rust side** — H2a |
| Value-defined case diff (member edit → member pointer; kind change → position; array length → array) | specified; no harness | **specified, not implemented** — H2a |
| Form ⊆ package ⊆ bundle extension inclusion and the per-package `read` before merge | specified; `bind_forms` checks a 0.2 form against the merged target, so the merged-only check is the gap | **specified, not implemented** — H2a |
| Reserved legacy definition names from `definitions/*/*.json` | specified; the index is readable today, the builder has no reserved-set check | **specified, not implemented** — H2a |
| The publication audit's guarantee is bounded to executable assets and identity | specified; whole-directory immutability is enforced by the changed-path gate, not by the audit | **specified, not implemented** — H2a |
| The no-follow open is achievable on Linux, macOS and Windows | not proved; `std::fs` has no portable no-follow open, so H2a N1 must measure a path layer on all three platforms | **unverified** — H2a N1 gate |
| Form-scope negatives are `bind`-only and point at the mutated operand | specified; `fmp-materialize/src/lib.rs` emits `E-BYTE-001` at `/instructions/0/expected_digest` after encoding, so the counterexample is real | **specified, not implemented** — H2a |
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
- Someone accepts a non-empty `exports.types` or `exports.profiles` in H2: stop.
  H2 does not define their semantics and must fail closed.
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
- Someone verifies a path by calling `symlink_metadata()` and then opening the
  same path string, or treats a canonicalise/check step as the guarantee: stop.
  The no-follow property belongs to the open, not to a preceding check (§3).
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
  stop. Deletions and renames must be resolved against the base tree or fail.
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
  package's `definition_format` and full `target_identity` must equal the pinned
  document, or the migration is not proven.
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
