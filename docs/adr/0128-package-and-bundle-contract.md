# ADR-0128: the package and bundle contract, and the H2 definition builder

- Status: accepted
- Date: 2026-11-14
- Settles: the `monasm-package/0.1`, `monasm-bundle-spec/0.1`,
  `monasm-lock/0.1` and `monasm-bundle/0.1` formats; the digest layering; package
  ownership and conflict rules; which legacy definition version a re-homed form
  is compared against; the builder's error and exit behaviour; and the boundary
  between H2 and H3/H4
- Supersedes: none
- Superseded by: none
- Revises: `docs/architecture/he1-h2-plan.md` (adopts `H2-D1`–`H2-D12` with the
  two measured corrections in decisions 13 and 14)
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
`packages/<target>/<owned-package>/**` instead of a hand-edited full definition
document (`ADR-0125` decision 1). The repository has no builder, no package
manifest and no explicit closure today: `Registry::load_dir` recursively reads
every JSON file under a directory (`fmp-model/src/definition.rs`), so "which
definitions are available" is decided by directory contents, not by an explicit
choice.

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

aarch64 is the benign case: `A64-P1`, `A64-P2-add-imm12` and
`A64-P2-add-imm12-lsl12` select rows that are byte-identical in `0.1.0`/`0.2.0`
and `0.20.0`, and every version declares `enabled_extensions: []`.

## Decision

### 1. A package is a directory with one closed manifest

`packages/<target>/<package>/package.json` is the only entry point. The target
directory is a path component (`x86_64`, `aarch64`, `rv64`), not a form-ID
prefix. The manifest is `monasm-package/0.1` and is a closed object:

```json
{
  "package_format": "monasm-package/0.1",
  "package_id": "monasm.x86.mov-register",
  "version": "0.1.0",
  "target_profile": "monasm.target.x86_64",
  "legacy_source": { "isa": "x86_64", "version": "0.1.0" },
  "requires_capabilities": ["field-placement/v1"],
  "dependencies": [],
  "exports": {
    "forms": [
      { "id": "x86:mov/r64-rm/legacy", "path": "forms/mov-r64-rm.json" },
      { "id": "x86:mov/rm-r64/legacy", "path": "forms/mov-rm-r64.json" }
    ]
  }
}
```

| Field | Counterexample when it is missing or unchecked |
|---|---|
| `package_format` | An older builder reads a newer manifest, ignores the field that changed the meaning, and builds a bundle the author did not describe. |
| `package_id` | Ownership has no owner to name; two packages cannot be distinguished in a lock. |
| `version` | The same package ID with changed content is indistinguishable from the old one; a lock cannot say which was selected. |
| `target_profile` | An x86 package is merged into an aarch64 target because the spec and the package never compared their target facts. |
| `legacy_source` | The row-equality test has no fixed reference; "the newest file" silently retargets the comparison and hides a semantic change. |
| `requires_capabilities` | A package that needs a primitive the core does not execute is built as if it needed nothing; H3 cannot report `unsupported-capability`. |
| `dependencies` | A transitive package has to be discovered by scanning, which is the behaviour H3 forbids. |
| `exports.forms` | A file in the package can be executed without being declared, or an undeclared file is silently included. |
| `exports.forms[].id` | The file's own `form_id` can differ from the declaration; swapping two files changes ownership without changing the manifest. |
| `exports.forms[].path` | The manifest cannot say which file holds the row, so the builder must guess or scan. |

Unknown, missing and duplicate keys are rejected (`INV-07`). `exports.forms`
is sorted strictly by `id`, and `dependencies` strictly by `(package_id,
version)`; a reordering is a different document and is rejected rather than
silently canonicalised. Each `forms/*.json` holds exactly one form object; its
`form_id` must equal the declared `id`.

### 2. `legacy_source` is the pin, and it is inside the digested manifest

`legacy_source` names the legacy definition `(isa, version)` that the package's
rows were copied from. It is part of the manifest, so it enters
`source_package_digest`; an author cannot retarget the comparison by editing a
file that is not digested. The builder resolves it to exactly
`<root>/definitions/<isa>/<version>.json`, where `isa` is the directory name
(`x86_64`, `aarch64`, `rv64`), not the form family. It does not search, does not
pick the newest file and does not choose among candidates. It compares every
exported row against that exact document and fails if the row is absent or not
byte-equal. Counterexample if it searched: two versions with the same file name
in different directories would make the comparison depend on traversal order.

A non-migrating package may omit the field. The three H2 packages must write it.

### 3. Paths are bounded to the package and the repository root

Every manifest path is a normalised relative path using `/`. Absolute paths,
`..`, empty segments, `.`, backslashes, NUL, URL schemes and drive letters are
rejected. Before opening a file, the builder checks that the canonicalised path
is still under the package root; on Windows it rejects a reparse-point escape.
The spec's `packages[].path` is checked against `--root` the same way.
`README.md`, `NOTICE`, `evidence/**` and `tests/**` may exist, but only declared
form files enter the source digest.

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
      "path": "packages/x86_64/mov-register",
      "source_package_digest": "sha256:..."
    }
  ]
}
```

`packages` **is the full closure**, not a set of roots. The builder opens
exactly these paths and nothing else. Each package's `dependencies` are
verification edges: every edge must resolve to a listed `(package_id, version)`
with exactly the listed `source_package_digest`. An edge to a package outside
the list is a missing-dependency error, never a scan trigger. Two entries with
the same `(package_id, version)` or the same `path` are rejected even when their
content is identical; identity is a release fact, not a content comparison. A
listed package that nothing depends on is a legal root; reachability is not
required.

`--all` enumerates `bundles/specs/*.json` only. It never enumerates
`packages/**`, so adding or corrupting an unselected package cannot change an
old spec's lock or sealed bundle.

The spec's `target.identity` and `definition_format` must match every listed
package's `legacy_source` definition, and every package's `target_profile` must
equal `target.profile_id`. A closure whose packages disagree on the target
identity or definition format is rejected; the builder does not pick a winner.
The builder writes the identity into the generated definition; it does not
consult a central Rust target table. That is the H3 precondition "a new target
does not edit a public whitelist".

Counterexamples: without the full list, the builder must discover dependencies
and an unselected corrupt package can break an old build (`HE-AC-05`); without
exact IDs, "latest" or a range picks a version the author did not name
(`HE-AC-04`, `HE-T08`); without paths, the builder must scan to find a package.

### 5. Ownership is a table, and a conflict is an error even for identical rows

The build creates three read-only ownership tables:

```text
form_id    -> package_id + version + source_package_digest
type_id    -> package_id + version + source_package_digest   # format only in H2
profile_id -> package_id + version + source_package_digest   # H4 owns the semantics
```

Two packages exporting the same `form_id` fail the build even when the rows are
byte-identical (`HE-T07`, `HE-AC-09`). Last-wins would make merge order decide
which package owns the row. H2 checks only `form_id`; the `type_id` and
`profile_id` keys are written into the format and digest so H4 can add their
semantics without a format change.

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

### 7. Four digest layers, each with its own domain separator

| Digest | Input | Excludes | Counterexample if it were missing or collapsed |
|---|---|---|---|
| `source_package_digest` | `sha256("monasm-package/0.1\0" ++ canonical(manifest) ++ for each export sorted by path: "\0form\0" ++ path ++ "\0" ++ sha256(canonical(form object)))` | README, NOTICE, evidence, tests, author path | Hashing only the manifest: swapping a form's template with the manifest unchanged leaves the package digest still. |
| `definition_digest` | `fmp_model::definition::read(merged_document).digest()` | builder version, build time, host, source paths | Hashing only the package set: two different form rows produce the same bundle identity. |
| `bundle_digest` | `sha256("monasm-bundle/0.1\0" ++ canonical(bundle_metadata))`, where metadata is `{bundle_id, definition_digest, definition_format, namespace, version, target, packages: [{package_id, version, source_package_digest}]}` sorted by package identity | the `bundle_digest` field itself, the builder receipt, package paths | Including the digest in its own preimage: the fixed point does not exist. |
| `builder` | `{name, version, build: Option<String>}`; lock and receipt only | the definition digest | Putting the builder version into `definition_digest`: a builder bump falsely reports definition drift (`HE-T19`). |

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

### 8. Spec, lock and sealed bundle are three different artifacts

- `bundles/specs/<bundle>.json` — `monasm-bundle-spec/0.1`, the author's
  explicit selection.
- `bundles/locks/<bundle>.lock.json` — `monasm-lock/0.1`, generated: the full
  bundle metadata (`bundle_id`, `definition_format`, `namespace`, `version`,
  `target`, `bundle_digest`, `definition_digest`), the sorted package list with
  `path` and `source_package_digest`, and `builder`.
- `bundles/sealed/<bundle>.bundle.json` — `monasm-bundle/0.1`, generated:
  `bundle_format`, `bundle_id`, the canonical definition document,
  `bundle_digest`, `definition_digest`, and the sorted `sources` list
  `{package_id, version, source_package_digest}`. It does not contain the builder
  receipt or author paths.

The binary has three subcommands: `build` writes the lock and sealed bundle,
`verify` rebuilds in memory, and `digest <package-path>` prints the computed
`source_package_digest` so an author can write it into the spec. None of them
adds a subcommand to `fmp`.

Lock and sealed bundle are committed release artifacts. CI runs
`fmp-definition verify --all --check`, rebuilds each spec in memory, compares the
sealed bundle byte-for-byte and the lock byte-for-byte **except `builder`**. The
builder is a receipt: it is shape-checked and printed, not compared, for the
same reason `ADR-0126` compares `payload/0.1` and not `envelope/0.1` — a correct
rebuild on a different commit must not fail the gate. Counterexample if the
builder were compared: the first commit after the lock changes `FMP_BUILD_ID`
and the gate fails without any definition change. A stale lock or sealed bundle
in the compared fields is a difference (exit 1), not a silent refresh.
Counterexample if lock/sealed were test-only: a published bundle could not be
audited against the source that produced it.

### 9. The builder generates bytes and lets `fmp_model` read them

The builder merges the declared form objects into a definition document, sorts
`forms` by `form_id`, serialises canonically, and calls
`fmp_model::definition::read`. `read` remains the only authority for form
fields, slot placement, template length, duplicate IDs and target shape. The
builder wraps a rejection as its own `BuildError`, preserving the underlying
diagnostic text. It does not construct `Definition` directly and does not call
`Registry::load_dir`.

`fmp-definition`'s product dependency is `fmp-model` only. The package
conformance harness lives in `fmp-definition/tests/` and uses dev-dependencies
on `fmp-validate`, `fmp-materialize` and `fmp-plan`; that does not change the
product graph. A runtime dependency on the materializer would let the builder
"verify" by encoding, which is a second authority and mixes the development and
execution phases.

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
| Deterministic rejection | manifest shape, path escape, missing/duplicate/cyclic dependency, digest mismatch, ownership conflict, row mismatch, `read` rejection, resource limit | 1 |
| Host / I/O / internal | unreadable file, unwritable lock, internal invariant break | 2 |
| Success | build or verify passed, digest printed | 0 |

The `fmp` CLI's 0/1/2 meanings are unchanged. Package-build errors never enter
`bind`'s diagnostic array.

### 12. Bounds are explicit

H2 bounds the builder's own inputs; it does not claim to fix deep-JSON
robustness:

- manifest ≤ 1 MiB; form file ≤ 1 MiB;
- exported forms per package ≤ 4096; packages per closure ≤ 1024;
- one path ≤ 1024 bytes; dependency depth ≤ 64.

An over-limit input is a deterministic rejection (exit 1). A parser stack
overflow from a 20 000-deep document remains H4 (`HE-T13`); H2's package inputs
are developer-controlled.

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
bytes. The aarch64 package exports the three `add` forms from `0.20.0`; the
rows are equal to the fixture-verified rows and the target set is `[]`.

The general rule for any future slice: pin the **newest definition version
whose selected rows are byte-equal to the evidence and whose target identity
matches the reference plan**. If the newest version fails either test, pin the
version that passes and record why in the package's `legacy_source` and report.

### 15. Byte equivalence is a machine-output projection, not `payload/0.1`

For each reference fixture, the equivalence test reads the legacy plan, replaces
only `definition_identity` with the bundle's `{namespace, version, digest}`,
re-parses with `fmp_model::plan::read`, binds to `VerifiedBundle::definition()`,
materialises, and compares `format_version`, `level`, `bytes_hex`/`sections`,
`symbols` and `fixups`.

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
- No runtime bundle reader, unknown-capability rejection or unselected-package
  isolation at materialisation time (H3).
- No `bind(VerifiedBundle, ...)` and no `fmp-validate → fmp-definition`
  dependency (H3).
- No fixup profiles, non-zero addends, Hi/Lo pairing or field-ownership
  semantics (H4).
- No deep-JSON fuzzing or full input-robustness programme (H4).
- No real same-ISA A/B packages or parallel workflows (H5).
- No migration of the 104 definitions or 619 negatives; no bulk form renaming.

## Consequences

- A new instruction family can land as a package directory plus a spec entry.
  The builder checks the manifest, the closure, ownership and canonical form,
  and `read` checks the definition semantics. No central form table is edited;
  package counts are generated, not hand-copied into `STATUS.md`
  (`ADR-0125` decision 4).
- `definitions/` and `fixtures/` do not move. The 128 payloads, the 104
  definition documents, the `payload_root` and the `definitions_root` keep their
  H1 values; a package build is a separate artifact.
- The H2 slice pins are data, not preferences: x86 `0.1.0`, aarch64 `0.20.0`,
  rv64 `0.1.0`. A future slice may choose differently only by the rule in
  decision 14 and must record the row and target comparison.
- The builder is offline and deterministic: no network, no author-directory
  reads, no package hooks, no execution of package scripts (`INV-05`).
- H3 can replace `VerifiedBundle::definition()` with a bundle-bound `bind`
  without changing the package, spec or lock formats.

## Alternatives rejected

- **Scan `packages/**` and build a global `(id, version)` index.** Rejected: a
  damaged unselected package would affect an old build, contradicting
  `HE-AC-05`, and selection would be directory-driven (`INV-05`).
- **Let the builder resolve dependencies recursively from IDs.** Rejected: the
  spec would no longer contain the closure, and a missing dependency would
  trigger a scan instead of a rejection.
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
| x86 `0.1.0` and `0.78.0` `mov` rows differ | canonical JSON comparison of the two rows; `0.78.0` adds `requires_extensions` and REX placements at bits 0/2 | high (measured on this host; not yet a Rust test) |
| aarch64 selected rows are equal across the pinned and newest versions | canonical JSON comparison of the three `add` rows | high (measured) |
| rv64 selected rows are equal, but `0.6.0` target set differs | canonical JSON comparison; `0.6.0` is `["rv64i","rv64c"]`, the plans are `["rv64i"]`, and `check_target` requires equality for `fmp-def/0.1` | high (measured) |
| `fmp-def/0.2` requires `requires_extensions` and rejects it in `0.1` | `bind_form` selects `FORM_FIELDS_V0_2` and `req`s the key; `FORM_FIELDS` rejects it as unknown | high (read) |
| Builder determinism, digest reproduction, row equality and byte equality | not implemented | **unverified** — H2a/H2b must measure them |
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
