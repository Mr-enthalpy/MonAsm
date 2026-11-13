# ADR-0128: the package and bundle contract, and the H2 definition builder

- Status: proposed
- Date: 2026-11-14
- Review: this is a proposal, not a frozen decision. It stays `proposed` until
  the H2 planning PR is reviewed and merged; `accepted` is written only after
  that review, and H2a does not start before it.
- Revision: third revision, 2026-11-14, after a further P1/P2 audit:
  immutable published version directories, legacy target consistency, form-scope
  negative coverage with a complete diagnostic set, a cumulative per-package
  asset budget, aligned form/case limits, frozen digest preimage bytes with a
  cross-language vector, exact Level 0/Level 1 projections, and a dependency
  closure status separate from package structure.
- Settles: the `monasm-package/0.1`, `monasm-bundle-spec/0.1`,
  `monasm-lock/0.1` and `monasm-bundle/0.1` formats; immutable published package
  version directories; the digest layering and its byte-level preimages; package
  target self-description and migration provenance, including legacy target
  consistency; the standalone definition identity used by `verify --package`; the
  mandatory package case and evidence gate with form-scope mutation and complete
  diagnostic sets; exact Level 0/Level 1 machine-output projections; package
  target requirements versus bundle target selection; package/form ISA-family
  consistency; package ownership and conflict rules; which legacy definition
  version a re-homed form is compared against; the builder's error and exit
  behaviour; and the boundary between H2 and H3/H4
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
| `requires_capabilities` | A package that needs a primitive the core does not execute is built as if it needed nothing; the builder cannot reject it before the snapshot is verified. |
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
object; its `form_id` must equal the declared `id`. `exports.types` and
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
- once any committed `bundles/specs/*.json` lists that path, the snapshot is
  **published**;
- after publication, no file under that directory may be added, modified,
  renamed or deleted — including `README`, `NOTICE` and `evidence/`. A change is
  `published-package-modified` (exit 1);
- new forms, fixed encodings or new evidence require a new sibling directory
  `packages/<target>/<package>/<new-version>/`, with its own manifest version and
  digest. The old directory stays byte-for-byte in place, so every old lock and
  sealed bundle can still be rebuilt by `verify --all --check`;
- updating a spec to select the new version, and regenerating its lock/sealed
  bundle, is a separate publisher decision. An ordinary package change does not
  edit any spec, lock or sealed bundle;
- removing a spec retires a release but does not delete the snapshot. H2 does not
  add an archival or deletion tool; retiring the bytes themselves needs a later
  ADR.

The CI changed-path gate resolves each `packages/**` change in the head tree and,
for a deletion, in the base tree. If the resolved snapshot is published and any
of its files changed, the gate fails before `verify --package` runs (§8.1).
Deleting or renaming a published version directory is the same rejection, not a
silent package removal.

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
rejected. Before opening a file, the builder checks that the canonicalised path
is still under the package root; on Windows it rejects a reparse-point escape.
The spec's `packages[].path` is checked against `--root` the same way.
`legacy_source.isa` and `legacy_source.version` are path components before they
are concatenated into `<root>/definitions/<isa>/<version>.json`, so they receive
the same treatment: `isa` must match `^[a-z0-9_]+$` and `version` must match
`^[0-9]+(\.[0-9]+)+$`. A value containing `/`, `\`, `..`, `.` as a whole
component, a drive letter, a URL scheme or NUL is rejected before the path is
formed; the builder does not normalise a value into legality.
`README.md`, `NOTICE`, `evidence/**` and `tests/**` may exist, but only declared
asset files (`form`, `type`, `profile`) enter the source digest;
`evidence/manifest.json` enters `evidence_digest` only.

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
exactly these paths and nothing else. Each package's `dependencies` are
verification edges: every edge must resolve to a listed `(package_id, version)`
with exactly the listed `source_package_digest`. An edge to a package outside
the list is a missing-dependency error, never a scan trigger. Two entries with
the same `(package_id, version)` or the same `path` are rejected even when their
content is identical; identity is a release fact, not a content comparison. At
most one version of a `package_id` may appear: two versions are rejected even
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

The spec's package order and directory-discovery order never enter the digest;
the builder sorts the closure by `(package_id, version)` first. Counterexample:
if spec order entered the digest, A+B and B+A would produce two bundle
identities for one execution fact (`HE-T16`).

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
  and are hashed as that text;
- concatenation is byte concatenation; there are no length prefixes and no
  separators other than the ones written in the row.

The fixed vector below is a required H2a test in Rust and in Python. Both must
produce the stated values byte for byte; an implementation that feeds raw digest
bytes into the outer hash fails it.

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
| `release_digest` | `sha256(b"monasm-release/0.1" ++ 0x00 ++ canonical(release_metadata))`, where metadata is `{bundle_id, bundle_digest, definition_digest, packages: [{package_id, version, source_package_digest, evidence_digest?}]}` sorted by package identity; every nested digest is the literal `sha256:` text | the definition rows themselves, the builder receipt, sealed bytes | Two releases that share a definition but ship different evidence have no distinguishing identity. |
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

A package is **release-ready** when a committed spec lists it or when it is
checked with `verify --package --release`. The ordinary-extension CI gate uses
`--release` (§8.1), so a new package is held to this bar before any publisher
selects it. For a release-ready package the builder requires:

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
  `manual-derivation` carrying a rationale, and `not-applicable` legal only when
  the package exports no forms; every skip carries a `case_id` and a reason;
- every positive and negative case in `tests/cases.json` (§9.1) carrying an
  `evidence` reference that resolves to a listed file.

A missing item is `evidence-incomplete` (exit 1). `evidence_digest` covers the
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
`verify --package <path>` checks one package against its own manifest and does
not read a spec, using the standalone identity in §2.1. The package form checks
that `path` ends at the manifest's `version` directory, the closed key set, path
bounds, declared-vs-actual `form_id`, the form-family match (§4.2), sorted
arrays, reserved-asset emptiness, the capability allowlist, the declared
`definition_format`/`target_identity` against the merged document read by
`fmp_model::definition::read`, the pinned legacy row and legacy target when
`legacy_source` is present (§2), the cumulative asset budget (§12.1), and the
`tests/cases.json` contract (§9.1). It does not execute the cases; the
conformance harness does. It does not check ownership conflicts across packages,
because that needs a closure. It does not prove that a published snapshot is
unchanged; that is the changed-path gate in §8.1. `--release` additionally
enforces §7.1. None of these adds a subcommand to `fmp`.

**Structure and dependency closure are separate statuses.** Every
`verify --package` run reports both `structure` and `dependency_closure`.
`structure: verified` means the manifest, assets, `read`, cases and evidence
passed. `dependency_closure: verified` is possible only when the invocation also
supplies an explicit closure: `verify --all` uses the spec closure, and
`verify --package --closure <lock>` reads one selected lock. With no closure
input, a package whose `dependencies` array is empty is trivially
`dependency_closure: verified` (there is nothing to resolve), while a package
with a non-empty array is `dependency_closure: unverified`. In `--release` mode
the latter is `dependency-unverified` (exit 1); a development run may still exit
0 for the structure claim but prints the unverified status. The standalone
identity never depends on the closure, so this status cannot change
`source_package_digest` or the generated `definition_digest`. H2 packages
declare no dependencies; the split exists so a later shared-type package cannot
pass `--release` by asserting an edge it never resolved.

Lock and sealed bundle are committed release artifacts. CI runs
`fmp-definition verify --all --check`, rebuilds each spec in memory, compares the
sealed bundle byte-for-byte and the lock byte-for-byte **except `builder`**. CI
also extracts every changed path under `packages/**`, maps it to its package root
and runs `fmp-definition verify --package --release <directory>` once per
package; that list is a CI input only and never decides what the builder selects.
The builder is a receipt: it is shape-checked and printed, not compared, for the
same reason `ADR-0126` compares `payload/0.1` and not `envelope/0.1` — a correct
rebuild on a different commit must not fail the gate. Counterexample if the
builder were compared: the first commit after the lock changes `FMP_BUILD_ID`
and the gate fails without any definition change. A stale lock or sealed bundle
in the compared fields is a difference (exit 1), not a silent refresh.
Counterexample if lock/sealed were test-only: a published bundle could not be
audited against the source that produced it.

#### 8.1 The changed-path map has explicit deletion and rename rules

Mapping a changed file to "the nearest ancestor with `package.json`" is only
defined when that file still exists in the PR head. Deletion and rename need
their own rules, or a package can leave the gate silently:

- **Modified or added file:** resolve the nearest ancestor `package.json` in the
  head tree. Its directory must be a version directory whose name equals the
  manifest's `version`; a mismatch is `path-version-mismatch` (exit 1). If none
  exists, fail with `unmapped-package-path` (exit 1); do not skip the path. If the
  base tree has the same version directory and any spec lists it, the snapshot is
  published and any modification is `published-package-modified` (exit 1).
- **Deleted file or directory:** resolve the version directory in the **base**
  tree. If that directory is published, any deletion inside it — including
  `package.json`, `NOTICE` or a form — is `published-package-modified` (exit 1);
  it is never a silent removal. If it is unpublished, the deletion is allowed
  only when the same PR removes or updates every spec that lists it, and
  `verify --all --check` proves no live reference remains. A deletion of an
  unpublished root that a spec still lists fails the build.
- **Rename or move:** check both the old and the new root. Moving a published
  version directory is `published-package-modified` (exit 1); a new version is a
  new sibling directory, not a move. Moving an unpublished package directory
  without changing `package_id` changes its `path`, so the spec entry must change
  too if it is later selected; moving a package across target directories must
  also keep §4.2 satisfied. A rename that changes `package_id` is a new release
  identity, not a free move, and the old identity must be removed from every
  spec.
- **A `packages/**` change that produces no package root** (for example a stray
  file directly under `packages/`, or a deletion whose base root cannot be
  found) is `unmapped-package-path`, exit 1. It is never silently ignored.

The CI path list remains an input to which packages are checked, never an input
to what the builder selects. Deleting an unselected package still runs the
removal check; deleting a selected package fails `verify --all --check`.

### 9. The builder generates bytes and lets `fmp_model` read them

The builder merges the declared form objects into a definition document, sorts
`forms` by `form_id`, serialises canonically, and calls
`fmp_model::definition::read`. `read` remains the only authority for form
fields, slot placement, template length, duplicate IDs and target shape. The
builder wraps a rejection as its own `BuildError`, preserving the underlying
diagnostic text. It does not construct `Definition` directly and does not call
`Registry::load_dir`.

`verify --package` follows the same rule: it merges the declared assets into a
document with the package's `definition_format`, calls `read`, and compares
pinned rows only when `legacy_source` is present. It never writes a lock or
sealed bundle, so a package author can run it before any spec exists.

`fmp-definition`'s product dependency is `fmp-model` only. The package
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
  trees. The set of differing JSON Pointers must be exactly `{mutates}`; any
  other difference, a no-op mutation, or a mutation that changes `form_id` is
  `case-mutation-mismatch` (exit 1). This stops an author from changing half the
  plan and calling the result a form test.

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
  `HostFailure` is `case-materialize-fault` (exit 2), never a pass.

For `scope: "form"`, every declared and observed path must be `/instructions/0`
or start with `/instructions/0/`; any other path is `case-error-scope` (exit 1).
For `scope: "plan"` any path is allowed. A wildcard, "any error", or a root-level
error such as a wrong `format_version` therefore cannot satisfy a form's
negative coverage. Coverage is counted only from `scope: "form"` negatives:
every exported form needs at least one positive and at least one such negative,
or the package is `uncovered-form`.

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
`manual-derivation`), `path` and `sha256`; the path must be listed in
`evidence/manifest.json`, and `tests/cases.json` itself must also be listed
there (§7.1), so `evidence_digest` covers the case plan and coverage.

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
`cargo run -p fmp-definition -- verify --package --release <changed>` runs for
the changed-path set (§8.1). A structurally valid row whose opcode was flipped
fails the positive case's byte comparison even when `read` accepts it. If an
author also edits the expected bytes, the case must cite independent evidence,
and §7.1 checks that the evidence is present, listed and hashed; the builder does
not claim to have re-run the oracle. This limit is stated rather than hidden: the
gate blocks accidental and unilateral encoding errors, and the reviewable oracle
record is what a second party audits.

`verify --package` alone checks structure, manifest, cases and evidence; it does
not encode, so it cannot by itself distinguish two opcodes. The merge gate is the
**pair**: `verify --package --release` and `package_conformance` on the same
changed package. A package that passes the first and fails the second does not
pass the gate, and the ordinary-extension CI job fails. This split is what keeps
the product binary's dependency graph at `fmp-model` only; it is not a weaker
gate.

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
| Deterministic rejection | manifest shape (required/optional keys), path escape, missing/duplicate/cyclic dependency, two versions of one package ID, digest mismatch, ownership conflict, row mismatch, legacy target mismatch, form-family mismatch, unknown capability, non-empty reserved asset, evidence mismatch or incompleteness, missing/uncovered case, case/plan/form binding, case baseline or mutation, incomplete diagnostic set, wrong expectation projection, unmapped package path, published snapshot modification, path/version mismatch, reserved identity, closure aggregate limit, `read` rejection, resource limit | 1 |
| Host / I/O / internal | unreadable file, unwritable lock, internal invariant break, materializer `Internal`/`HostFailure` during conformance | 2 |
| Success | build or verify passed, digest printed | 0 |

The enum names these rejections (`unsupported-capability`, `unsupported-asset`,
`version-conflict`, `aggregate-limit`, `legacy-row-mismatch`,
`legacy-target-mismatch`, `evidence-mismatch`, `evidence-incomplete`,
`missing-cases`, `uncovered-form`, `case-evidence-mismatch`,
`case-plan-identity`, `case-form-mismatch`, `case-error-scope`,
`case-baseline-invalid`, `case-mutation-mismatch`,
`case-diagnostics-mismatch`, `case-expect-shape`, `form-family-mismatch`,
`reserved-identity`, `path-version-mismatch`, `published-package-modified`,
`unmapped-package-path`, `dependency-unverified`); they are `BuildError`
variants, not `fmp/0.1` diagnostic codes. `case-materialize-fault` is the
conformance harness's name for an unexpected `Internal`/`HostFailure`; it is
never a passing case and reports exit 2, the host/internal class.

The `fmp` CLI's 0/1/2 meanings are unchanged. Package-build errors never enter
`bind`'s diagnostic array.

### 12. Bounds are explicit

H2 bounds the builder's own inputs; it does not claim to fix deep-JSON
robustness:

- manifest ≤ 1 MiB; form, type or profile file ≤ 1 MiB;
- `tests/cases.json` ≤ 16 MiB; `evidence/manifest.json` ≤ 1 MiB; a spec or lock
  ≤ 1 MiB each; the pinned legacy definition file read for row comparison
  ≤ 16 MiB;
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
  evidence manifest, spec and lock the builder parses.

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
  must name a positive baseline, mutate exactly one operand field, and match the
  complete observed `(code, path)` set; a wrong `expected_digest` may be a
  plan-scope test but cannot cover a form.
- Digest preimages, the Level 0/Level 1 projections and the package budgets are
  frozen at the byte and key level, with a cross-language vector, so a Rust and a
  Python implementation cannot silently disagree.
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
- **Content-address the package directory by `source_package_digest`.** Rejected
  for H2: an author cannot know the path before writing the files, the spec
  becomes unreadable, and a digest-named path still needs a version for review.
  The version directory pins the same snapshot with a human-reviewable name.
- **Accept any negative error as form coverage.** Rejected: a wrong
  `expected_digest` or a root-level format error would satisfy the count without
  touching an operand or modifier. Coverage requires a baseline mutation and
  `scope: "form"` (§9.1).
- **Treat an absent `symbols` key as `[]`.** Rejected: it hides whether
  `include_symbol_table` was honoured and makes the harness normalise two
  different artifacts into one (§15).
- **Let `verify --package` claim the dependency closure from manifest shape
  alone.** Rejected: it cannot prove existence or digest equality. The closure
  status stays `unverified` without an explicit closure (§8).
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
  H2 rejects unknown strings at build time; runtime negotiation stays H3.
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
| The digest fixed vector is stable across two implementations | the vector in §7.0; Python `hashlib` and .NET `SHA256` both produced `1afee65c…` | high (measured twice) |
| x86 `0.1.0` and `0.78.0` `mov` rows differ | canonical JSON comparison of the two rows; `0.78.0` adds `requires_extensions` and REX placements at bits 0/2 | high (measured on this host; not yet a Rust test) |
| aarch64 selected rows are equal across the pinned and newest versions | canonical JSON comparison: the two `lsl0` rows are equal in `0.1.0`/`0.2.0`/`0.20.0`; `lsl12` is absent in `0.1.0` and equal in `0.2.0`/`0.20.0` | high (measured) |
| rv64 selected rows are equal, but `0.6.0` target set differs | canonical JSON comparison; `0.6.0` is `["rv64i","rv64c"]`, the plans are `["rv64i"]`, and `check_target` requires equality for `fmp-def/0.1` | high (measured) |
| `fmp-def/0.2` requires `requires_extensions` and rejects it in `0.1` | `bind_form` selects `FORM_FIELDS_V0_2` and `req`s the key; `FORM_FIELDS` rejects it as unknown | high (read) |
| `check_form_id` accepts any known family but does not compare it to `target_identity.isa_family` | `fmp-model/src/definition.rs` `check_form_id` matches `x86`/`aarch64`/`riscv` and returns; `bind_target` reads `isa_family` independently | high (read) |
| Builder determinism, digest reproduction, row equality and byte equality | not implemented | **unverified** — H2a/H2b must measure them |
| `verify --package`, the standalone identity, the case/plan/form binding, the release evidence hash and the changed-path gate (including deletion/rename) | not implemented | **unverified** — H2a |
| The generic `family(form_id) == isa_family` rule and its cross-ISA negative | not implemented; `check_form_id` only checks the family in isolation | **unverified** — H2a |
| Unknown-capability rejection, reserved-asset rejection, version-conflict rule and aggregate limits | not implemented | **unverified** — H2a |
| Evidence completeness, `evidence_digest` and `release_digest` | not implemented | **unverified** — H2a owns the mechanism; H2b adds assets only |
| Case, evidence, spec and lock byte/count budgets, including the cumulative per-package asset budget | not implemented | **unverified** — H2a |
| Immutable published version directories, legacy target consistency, form-scope mutation coverage, complete diagnostic matching and level-specific projections | not implemented | **unverified** — H2a |
| Dependency-closure status distinct from package structure | not implemented | **unverified** — H2a |
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
- Someone edits a file inside a version directory already listed by a committed
  spec: stop. That is `published-package-modified`; the author must add a sibling
  version and the publisher selects it separately.
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
