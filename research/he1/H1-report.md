# H1 report — identity closure (H1a + H1b addendum)

Stage: H1a (design §13, `ADR-0125`; decisions in `ADR-0127`)
Date: 2026-11-13
Review amendment: 2026-11-14 (H1a review: P1 wide-field encoding, P2 doctest
counterexample, CI identity and release steps)
Review follow-up: 2026-11-14 (P2 same-variant identity values; P3 evidence
counts, encoder wording and run identity)
H1b addendum: 2026-11-14 (§11; binding half landed on `he1/h1b-validated-plan`)
Base commit: `0948620f36893d17de56a913f72ced935fe50a98` (merged H0/H1-plan PR)
Branch: `he1/h1a-identity-core`

H1a is the first half of H1. It closes the executed `Definition`, defines the
parsed-plan identity, re-checks the parser rules a mutable DTO can bypass, and
hardens the validator's arithmetic. It did **not** add `ValidatedPlan`, `bind`,
the new `materialize`, `ExecutionReceipt`, `MaterializationFailure` or the CLI
failure split; §11 records the H1b addendum that does, and the boundary this
section describes is the H1a close, not the current tree.

## 1. Change scope

Product code changed in `fmp-model`, `fmp-validate`, `fmp-materialize` and the
CLI call sites. No definition, fixture, schema or `docs/fmp-v0/` byte changed.

| Path | Change | Why |
|---|---|---|
| `prototype/crates/fmp-model/src/definition.rs` | `Definition` fields private, `document` deleted, no `Clone`, accessors added; `Registry` stores `Vec<Arc<Definition>>`, `add` takes ownership, `find` returns `Arc<Definition>` | `ADR-0127` §1: a loaded definition is half an execution credential, and a stored digest cannot make mutable facts honest |
| `prototype/crates/fmp-model/src/identity.rs` | new: `plan-identity/0.1`, `plan_facts`, `ParsedPlanIdentity::of`, exhaustive destructuring, three pinned vectors, 73-row mutation table, 8 same-variant value rows | `ADR-0127` §2–§3: the identity must cover parsed facts, a new field must stop the build, and the value inside a variant must move the digest |
| `prototype/crates/fmp-model/src/plan.rs` | `Plan.document` → `legacy_document`; new `check_structure` | `ADR-0127` §4/§6: one legacy-only reader for the raw document, and the parser rules a `u32`/`String` cannot hold are re-checked |
| `prototype/crates/fmp-model/src/lib.rs` | exports `identity`/`ParsedPlanIdentity`; two `compile_fail` doctests (the second a complete-field literal) and one positive control | the closure is "this cannot be written", not "this returns an error" |
| `prototype/crates/fmp-validate/src/lib.rs` | `u64`/`u128`/`checked_*` for descriptor sums, overlap math, alignment, range bounds and register width; per-bit loops clipped to `form.bits()`; `page ⇒ pcrel_page` | `ADR-0127` §7: a full `u64` offset and a `u32` width must not overflow or loop; `Page` without `P` must not become an internal fault |
| `prototype/crates/fmp-materialize/src/lib.rs` | `fingerprint` reads `legacy_document` and accessors; digest comparison reads `definition.digest()`; `lookup` uses `forms()`; `write_field` extracts each placement from `u128` instead of masking the whole field | keeps the legacy fingerprint byte-identical while the fields close, and encodes fields wider than `i128` |
| `prototype/crates/fmp-cli/src/main.rs`, `tests/determinism.rs`, `tests/fixtures.rs`, `tests/planner_api.rs` | borrow `&definition` from `Arc<Definition>` | the registry now shares ownership |
| `prototype/crates/fmp-cli/tests/he1_identity_characterization.rs` | the in-memory definition-mutation test becomes `a_definition_edit_reloads_to_a_new_digest` | private fields make the old test uncompilable; the property is measured by editing the document and reloading |
| `prototype/crates/fmp-model/tests/he1_check_structure.rs` | new: 5 test functions, 9 mutations | X86-P71 odd/non-hex `payload_hex`, `align_bits`, `transform_shift`, `lsb`/`width`/`bits` |
| `prototype/crates/fmp-validate/tests/he1_validation_bounds.rs` | new: 4 test functions | `u32::MAX` width sum, two `u64::MAX`-class offsets, `page` + `none`, 64/128-bit register field |
| `prototype/crates/fmp-materialize/tests/he1_wide_register.rs` | new: 1 test function | 64/127/128/192-bit register fields through `materialize`, non-zero registers, exact bytes in debug and release |
| `prototype/crates/fmp-materialize/tests/he1_stage_boundaries.rs` | new: 4 test functions | measures which recorded negatives fail only after encoding |
| `tools/plan_identity.py` | new | independent Python encoder for the three vectors; `--check` compares them |
| `docs/adr/0127-execution-identity.md` | new | normative decisions, protocol tables, vectors, 15-row `internal(...)` table, post-encode set, dependency guard |
| `docs/architecture/he1-h1-plan.md` | header and one risk row | draft → accepted (H1a landed, H1b not started); wide-field risk records the validator and encoder halves |
| `docs/STATUS.md` | one HE-1 paragraph | H1a status and evidence pointer; no new hand-maintained count |
| `.github/workflows/gates.yml` | new hosted steps | `plan_identity.py --check` in `documents`; release runs of `he1_validation_bounds` and `he1_wide_register` in `workspace`, alongside the existing `cargo tree -p fmp-validate --edges normal` guard |
| `research/he1/H1-report.md` | new | this report |

No file under `definitions/`, `fixtures/`, `schema/` or `docs/fmp-v0/` changed.

## 2. Commands actually run

Run from the repository root unless the row says `prototype/`.

```text
git rev-parse HEAD
git rev-parse HEAD:prototype
cargo fmt --all -- --check                     # prototype/
cargo test --workspace                         # prototype/
cargo test --release -p fmp-validate --test he1_validation_bounds   # prototype/
cargo test --release -p fmp-materialize --test he1_wide_register    # prototype/
python tools/check_ids.py
python tools/check_definition.py
python tools/plan_identity.py --check
python tools/he1_baseline.py --check research/he1/compatibility-results.json
python tools/oracle/rerun.py --allow-skip-reason manual-derivation
cargo tree -p fmp-validate --edges normal      # prototype/
git diff --check
```

## 3. Results

| Command | Result |
|---|---|
| `git rev-parse HEAD` / `HEAD:prototype` | base `0948620f…`; code commit `d2cd7dd3…`; `prototype/` tree `e31c88ae…` (see *Run identity*) |
| `cargo fmt --check` | exit 0 |
| `cargo test --workspace` | 89 passed, 0 failed (inventory below) |
| `cargo test --release -p fmp-validate --test he1_validation_bounds` | 4 passed, 0 failed |
| `cargo test --release -p fmp-materialize --test he1_wide_register` | 1 passed, 0 failed |
| `cargo test -p fmp-materialize --test he1_wide_register` (debug) | 1 passed, 0 failed |
| `check_ids.py` | `OK (0 warning(s))`; declared `AC=10, E=48, EC=44, EXP=6, HE-AC=12, HE-T=20, INV=8, N=25, OD=15` |
| `check_definition.py` | `OK`; 104 documents, newest x86 `0.78.0` (632 forms), AArch64 `0.20.0` (185), RV64 `0.6.0` (24) |
| `plan_identity.py --check` | three pinned digests match (§5) |
| `he1_baseline.py --check` | `OK: payload projection identical`; `payload_root sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`; `definitions_root sha256:575b7c5f3817c4ed528b8e5dff02bb1fcb6d9024d17e79a79b64b9662635690e` |
| `oracle/rerun.py` | `122/128 re-derived, 6 skipped, 0 failed`; six `manual-derivation` skips |
| `cargo tree -p fmp-validate --edges normal` | no `fmp-materialize` edge (§8) |
| `git diff --check` | clean |

The baseline envelope was not compared: the current binary's implementation
receipt differs from the recording host's, which is the documented `ADR-0126`
behaviour. Both the recorded and the fresh `envelope_root` are
`sha256:dfd08fee9844058492138b23448073ec47d8eda42383e3f1b3e567db86a86fef`; the
gate value is the payload root.

### Run identity

The local numbers above and the hosted runs below refer to one `prototype/`
tree. This report is docs-only: it adds no product change and leaves that tree
untouched.

| Field | Value |
|---|---|
| `base_commit` | `0948620f36893d17de56a913f72ced935fe50a98` |
| `tested_commit` | `d2cd7dd3e1b41071d2784fc47bc7ca80b4e8a1d6` (same-variant identity test) |
| `tested_tree` | `e31c88aef8ca31997dac44e9688fd69ce2485e57` = `git rev-parse d2cd7dd:prototype` |
| `dirty_worktree` | no: local gates were run on the committed tree, `git status --short` empty |
| `dirty_patch_digest` | not applicable (no uncommitted change at test time) |
| CI merge ref | `24adefee57dc933016948311e4337ba267d73bd5` (`refs/pull/2/merge`, head `d2cd7dd`) |
| `gates` run | [43476855490](https://github.com/Mr-enthalpy/MonAsm/actions/runs/43476855490): documents `132062792336`, workspace `132062791671`, H0 baseline `132062792376`, oracle `132062792280` — all success |
| `determinism` run | [43476855500](https://github.com/Mr-enthalpy/MonAsm/actions/runs/43476855500): ubuntu `132062792184`, macos `132062791559`, windows `132062791987` — all success |

### Test inventory

`cargo test --workspace` runs these binaries and doctests:

| Suite | Tests | What H1a added or changed |
|---|---|---|
| `fmp-model` unit | 33 | 3 definition tests (`a_definition_reloads_to_the_same_digest`, `a_canonically_equal_definition_loads_to_the_same_digest`, `the_registry_shares_one_immutable_definition`) and 8 identity tests (below) |
| `fmp-model` doctests | 3 | two `compile_fail` (field assignment, complete-field struct literal) and one positive control |
| `he1_check_structure` | 5 | `a_data_fragment_with_odd_length_hex_is_rejected_by_check_structure`, `a_data_fragment_with_non_hex_payload_is_rejected_by_check_structure`, `an_alignment_outside_the_parser_bound_is_rejected_by_check_structure`, `a_transform_shift_outside_the_parser_bound_is_rejected_by_check_structure`, `a_field_range_outside_the_parser_bound_is_rejected_by_check_structure` |
| `he1_validation_bounds` | 4 | `a_descriptor_width_sum_cannot_overflow`, `two_huge_fixup_offsets_do_not_overflow`, `a_page_transform_without_a_page_pc_rule_is_rejected`, `a_wide_register_field_does_not_overflow_the_width_check` |
| `he1_wide_register` | 1 | `a_wide_register_field_encodes_the_same_bytes_in_every_build` |
| `fmp-materialize` unit | 9 | unchanged |
| `he1_stage_boundaries` | 4 | `a_digest_mismatch_is_post_encode`, `a_fixup_alignment_failure_is_post_encode`, `a_fixup_range_failure_is_post_encode`, `an_expected_size_mismatch_is_rejected_before_encoding` |
| `fmp-plan` | 5 | unchanged |
| `fmp-cli` `determinism` | 6 | accessor migration only |
| `fmp-cli` `fixtures` | 2 | accessor migration only |
| `fmp-cli` `he1_identity_characterization` | 7 | one test replaced (see §1); the other six are unchanged in meaning |
| `fmp-cli` `planner_api` | 10 | accessor migration only |

The eight identity tests are:

- `the_three_protocol_vectors_are_stable`
- `the_algorithm_name_is_the_domain_separator`
- `provenance_is_not_part_of_the_identity`
- `the_legacy_document_is_not_part_of_the_identity`
- `a_changed_operand_changes_the_identity`
- `an_unknown_variant_is_payload_carrying_and_distinct`
- `same_variant_values_change_the_identity` (8 rows: register number, symbol
  id, absolute target, symbol target, `Some` payload, vector element, order,
  count)
- `plan_identity_covers_every_parsed_field` (73 mutations)

## 4. What H1a proves and what it does not

**Proved by a run.** The definition API is closed (both doctests fail to
compile, both turn red when a scratch copy makes all six fields `pub`, and the
positive control compiles and reads the accessors); a document edit reloads to a
different digest and the untouched plan is rejected at
`/definition_identity/digest` with `E-DEF-001`; `check_structure` rejects the
nine structural mutations with the parser's own code, Pointer and detail keys;
the validator returns in bounded time for two `u32::MAX` widths and two
`u64::MAX`-class offsets; `page` without `pcrel_page` is a static
`E-FIXUP-001`; a register field of 64, 127, 128 or 192 bits encodes the exact
expected bytes with a non-zero register in both debug and release; the
identity's three vectors match an independent Python encoder, all 73
field/enum mutations and the 8 same-variant value rewrites move the digest, and
the register row goes red when `Payload::Register(_)` is encoded as a constant
zero (fault injection, implementation restored); and the 128 recorded payloads
still materialize identically.

**Not proved.** H1a is not an execution credential. Until H1b exists, a caller
can still call the old two-argument `materialize` with any `&Plan` and any
`&Definition`; `bind` does not exist, so `check_structure` is not yet on the
product path — the tests call it directly. `ParsedPlanIdentity` is not compared
against anything in the product yet. The `internal(...)` table is an audit of
today's code, not a reclassification: twelve branches remain `Internal` in H1b,
one is closed by §7.2, and two are host-domain failures that H1b must not route
through `Internal`.

## 5. The three identity vectors

The protocol is normative in `ADR-0127` §3; the full `minimal` facts hex is
pinned there (376 bytes). The digests are:

| Vector | `sha256` digest | Facts |
|---|---|---|
| `minimal` | `sha256:a48faecec39dd1de38f13b4868559f307b575a95a0aa241a01caa325400422c4` | 376 bytes |
| `data-fragment` | `sha256:9da5a3318e943bcbd5c9c32366708922b68a5e7e7c67a0b3d48a9c7b1a68eec2` | one `.text` section, one `Data("90")` fragment |
| `unknown-variants` | `sha256:1a07ae98cba50f7ee65b36bbe2bb1684eaa0885f728270b9baa39824a2a4632a` | every `Unknown` variant and every covered `Some` **except** `source_ref` (all three vectors use `None`) |

`source_ref = Some(...)` is therefore not in the fixed cross-language set. It is
covered by the Rust mutation table (`definition.source_ref`), so the branch is
tested, but only in one implementation. H1a review corrected the claim instead
of changing the three frozen vectors.

`tools/plan_identity.py --check` rebuilds the three fact trees from the protocol
text and compares the digests. Rust and Python were written independently from
the same tables, so agreement catches a transcription error, an implicit length
or a language-specific layout assumption. It does **not** catch a misreading
shared by both; the exhaustive destructuring, the 73-row mutation table and the
8 same-variant value rows are the controls for that.

## 6. Where the post-encode negatives actually fail

`he1_stage_boundaries.rs` asserts both columns for each recorded negative:

| Fixture | Code | `check` | `materialize` |
|---|---|---|---|
| `N13-expected-digest-mismatch` | `E-BYTE-001` | empty | `E-BYTE-001` |
| `N20-loadlit-fixup-misaligned` | `E-RANGE-003` | empty | `E-RANGE-003` |
| `N04b-rel32-absolute-out-of-range` | `E-FIXUP-003` | empty | `E-FIXUP-003` |
| `N04f-absolute-address-in-imm8-field` | `E-FIXUP-003` | empty | `E-FIXUP-003` |
| `N05-expected-size-mismatch` | `E-SIZE-001` | `E-SIZE-001` | `E-SIZE-001` |
| `N05b-huge-expected-size` | `E-SIZE-001` + `E-LAYOUT-003` | rejected | rejected |

The measured set is **four fixtures, three codes**. The H0 statement "only
`E-SIZE-001`/`E-BYTE-001` fail after encoding" counted codes, not fixtures, and
included a static rejection. Only the four rows above are candidates for the
value-level snapshots H1b adds; the other negatives keep the
code + Pointer + detail-key-set gate.

## 7. Numeric hardening and register width

| Site | Before | After |
|---|---|---|
| `cover_state` slot end/intersection | `u32` | `u64` |
| `check_fixup_descriptor` field end, width sum, overlap | `u32` | `u64` |
| `check_fixup_overlap` absolute bit position | `u64` `offset * 8 + lsb` | `u128` (`u64::MAX * 8 + u32` is representable) |
| `check_one_writer` / `check_fixup_ownership` bit loops | up to `u32::MAX` bits | clipped to `form.bits()` |
| register field width | `1u64 << field_bits` (debug panic at 64) | `1u128.checked_shl(field_bits)` |
| register field encoding (`write_field`) | `value & mask(width_bits)`, then `masked >> remaining` in `i128` | each placement read directly from the low 128 bits of `u128`; higher bits are the value's sign bit |
| alignment unit and signed/unsigned bounds | unchecked `1i128 << n` | `checked_shl`; an unrepresentable bound no longer panics |

The register-width reproduction builds two synthetic `fmp-def/0.1` tables whose
`reg_number` slot sums to 64 bits (two 32-bit placements, 8-byte template) and
128 bits (two 64-bit placements, 16-byte template). `reg_number` slots may not
declare `range`, and the loader bounds each placement to 64 bits, not the sum,
so both widths are legal definition facts. Both tables load, and `check` on a
plan using them returns no `E-OPERAND-004` and does not panic. The fix is the
`u128` comparison, not a load-time `width_bits` bound: the width is legal and
only the comparison was unsafe. `definitions/**` is frozen and no shipped slot
is that wide, so the table is built in the test.

The H1a review found that this covered only the validator. `write_field` still
masked the whole field and shifted an `i128`: at 127 bits `(1i128 << 127) - 1`
panicked in debug, and at 192 bits `>> 128` wrapped in release and wrote the
value into the **first** 64-bit placement as well as the last. The new
`a_wide_register_field_encodes_the_same_bytes_in_every_build` reproduces both
against the reviewed tree and asserts the exact bytes after the fix, for
64/127/128/192-bit fields with non-zero registers. A zero register would hide
the release defect, because the wrongly filled chunk is also zero. No
arbitrary-precision integer is introduced: register values are `u64`, and bits
above 127 are the value's sign bit.

The `u32::MAX` width sum test is a second-line-of-defence proof. Under D13 the
same input is structurally illegal and must be rejected by `check_structure`
with `E-PLAN-002` once H1b puts it on the path; H1a calls `check` directly to
prove the arithmetic terminates.

## 8. Dependency direction

`cargo tree -p fmp-validate --edges normal` on this host:

```text
fmp-validate v0.0.0
└── fmp-model v0.0.0
    └── sha2 v0.10.9
        └── cfg-if v1.0.4
        └── cpufeatures v0.2.17
        └── digest v0.10.7
            └── block-buffer v0.10.4
            └── crypto-common v0.1.7
```

No `fmp-materialize` edge. `.github/workflows/gates.yml` now greps the same
command and fails the `workspace` job if the edge appears. `--edges normal`
excludes dev-dependencies on purpose: a test-only edge is allowed, the shipped
graph is what the check owns.

## 9. Compatibility

- **Payloads:** none moved. `payload_root` is unchanged
  (`sha256:3f6d177d…ffefad9`), so all 128 positive payloads are byte-identical.
- **Definitions:** none moved. `definitions_root` is unchanged
  (`sha256:575b7c5f…35690e`); `check_definition.py` still sees 104 documents.
- **Negatives:** the 619 code + Pointer + detail-key triples are unchanged; the
  new rejections (`check_structure`, `page ⇒ pcrel_page`) are not reachable from
  a legal fixture, and the tests that exercise them assemble the illegal state in
  memory.
- **Oracle:** `122/128` re-derived, 6 `manual-derivation` skips, 0 failed — the
  same split as H0. The definition files did not change; the encoder did: the
  wide-field extraction in `write_field` was fixed, and the 128 existing
  payloads still materialize to the same bytes.
- **API:** `Definition` no longer implements `Clone`, exposes `document`, or
  allows field assignment; `Registry::find` returns `Arc<Definition>` instead of
  `&Definition`. This is a source-level break, deliberately: `ADR-0127` §1 and
  plan D1 reduce the cost by not renaming the type. The FMP document surface is
  unchanged.
- **Tooling:** one new Python script and one new CI step; no error code was
  added. `E-PLAN-001`, `E-PLAN-002` and `E-FIXUP-001` were already registered.

## 10. Next at the H1a close

H1b (`docs/architecture/he1-h1-plan.md` §3.2–§3.4, §4.2, §6):

- `ValidatedPlan` with private fields and no `Clone`; `bind(Plan, Arc<Definition>)`
  runs `check_structure`, compares `(namespace, version, digest)`, then `check`;
- `materialize(&ValidatedPlan)` returns `Materialization { artifact, receipt }`;
- `MaterializationFailure` splits `PostEncodeAssertion`, `Internal` and
  `HostFailure`; the two host-domain branches never use `Internal`;
- the CLI failure split and the deprecated facade that routes through `bind`;
- the same structural inputs replayed end to end, plus namespace-only,
  version-only and digest-compatibility mismatches;
- value-level snapshots only for the four fixtures measured in §6.

At the H1a close the old `materialize` still re-ran its own digest comparison and
a `Plan` could still reach it unbound. §11 records how H1b removed both facts.

## 11. H1b addendum — the binding half (2026-11-14)

Stage: H1b (`ADR-0125`, `ADR-0127`; plan `docs/architecture/he1-h1-plan.md`
§3.2–§3.4, §4.2, §5, §6 second row)
Branch: `he1/h1b-validated-plan`
Base: `4d3f8de` (merged H1a PR)
Tree: `7df6f48` plus this report; the audit fix in that commit is the last
change to the materializer code under test.

H1b makes `ValidatedPlan` the only executable input, returns the artifact with
an `ExecutionReceipt`, splits materialization failures by who is at fault, and
keeps the historical two-argument entry working by routing it through `bind`.
It closes the last H1 acceptance item (a traceable build label) and the
acceptance result is recorded in §11.8.

### 11.1 Change scope

| Path | Change | Why |
|---|---|---|
| `prototype/crates/fmp-validate/src/lib.rs` | `DefinitionIdentity`, `BindIdentity`, `ValidatedPlan` (private fields, no `Clone`, no constructor), `bind`, `check_definition_identity`; three `compile_fail` doctests plus one positive control | `ADR-0127` D11/D13/D15: the credential is unforgeable, and the implementation identity lives in the materializer, not here |
| `prototype/crates/fmp-validate/tests/he1_bind.rs` | 6 tests: structural-vs-`check` stage replay, huge offsets, `page` precondition, namespace/version/digest mismatches, bound-definition identity | H1a called `check_structure`/`check` directly; H1b replays the same inputs through the public entry |
| `prototype/crates/fmp-materialize/src/lib.rs` | `materialize(&ValidatedPlan)`, `materialize_with_allocator`, `Materialization` (`verify_receipt`), `ExecutionReceipt`, `ImplementationIdentity`, `PayloadIdentity`, `payload_digest`, `HostFault` (`ImageReservation`, `ImageLength`), `MaterializationFailure`, `allocate_image`; `encode_instruction`/`apply`/`source` reclassified; deprecated `legacy` module | `ADR-0127` §3, §8, §9 and plan D4/D5/D9: one input, one receipt, three failure classes, no `Rejected`; the audit fix makes the injected allocator's exact-length contract enforceable before encoding |
| `prototype/crates/fmp-materialize/tests/he1_execution.rs` | 13 tests: provenance/document identity split, mutated operand, fingerprint-as-cache-key, `source_trace` bind identity, payload projection, build receipt, injected allocator reservation failure, short and long images, `verify_receipt`, both facade rejections | the identity table of plan §5 plus the allocator contract and receipt pairing, measured rather than inferred |
| `prototype/crates/fmp-materialize/tests/he1_stage_boundaries.rs` | `bind` replay plus value-level snapshots for the four measured post-encode fixtures | `ADR-0127` §9 |
| `prototype/crates/fmp-materialize/tests/he1_wide_register.rs` | calls `bind` + `materialize` instead of the removed two-argument entry | the wide-field evidence now goes through the credential |
| `prototype/crates/fmp-cli/src/main.rs` | `Failure::{Internal, Host}`, pure `exit_code`, `report`, `classify`; 2 unit tests | `ADR-0127` §3.4: an implementation bug is not a rejected plan |
| `prototype/crates/fmp-cli/tests/support/mod.rs` | shared `execute`/`artifact`/`diagnostics`; every gate test binds first | there is no remaining two-argument path |
| `prototype/crates/fmp-cli/tests/fixtures.rs`, `planner_api.rs`, `determinism.rs`, `he1_identity_characterization.rs` | routed through `support`; no count changed | parity and determinism gates must exercise the new entry |
| `prototype/crates/fmp-cli/tests/cli_failure.rs` | 3 process tests: bind rejection exits 1 with the diagnostic array; post-encode N13 assertion exits 1 with `E-BYTE-001` and empty stdout; usage exits 2 without an array | the split is a property of the real binary, not only of `exit_code`; the audit asked for the post-encode path end to end |
| `docs/architecture/he1-h1-plan.md`, `docs/STATUS.md`, this report | status and evidence | the plan is no longer "H1b not started" |
| `.github/workflows/gates.yml`, `.github/workflows/determinism.yml` | compile the materializer with `FMP_BUILD_ID` = the PR head SHA (or the pushed commit) | `HE-T20`/`ADR-0127` D9: the receipt must name a source revision when a hosted build makes one |

No file under `definitions/`, `fixtures/`, `schema/` or `docs/fmp-v0/` changed.
`ADR-0127` also did not change: H1b implements §8 and §9 as written. The one
implementation choice the ADR leaves open is the width of a host request:
`HostFault::ImageReservation { requested: u64 }` keeps the plan's `u64`, so a
size the host cannot even represent is still a host limit rather than an
`Internal` fault.

### 11.2 Commands actually run

Run from the repository root unless the row says `prototype/`.

```text
cargo fmt --all -- --check                                              # prototype/
cargo test --workspace                                                  # prototype/
cargo test --workspace --doc                                            # prototype/
cargo test --release -p fmp-validate --test he1_validation_bounds       # prototype/
cargo test --release -p fmp-materialize --test he1_wide_register        # prototype/
cargo build --bin fmp -p fmp-cli                                        # prototype/
cargo build --release --bin fmp -p fmp-cli                              # prototype/
python tools/check_ids.py
python tools/check_definition.py
python tools/plan_identity.py --check
python tools/he1_baseline.py --check research/he1/compatibility-results.json
python tools/he1_baseline.py --check research/he1/compatibility-results.json --binary prototype/target/release/fmp.exe
python tools/oracle/rerun.py --allow-skip-reason manual-derivation
git diff --check
```

### 11.3 Results

| Command | Result |
|---|---|
| `cargo fmt --check` | exit 0 |
| `cargo test --workspace` | 119 passed, 0 failed across 20 suites: 110 unit/integration tests plus 9 doctests (16 test targets + 4 doctest targets) |
| `cargo test --workspace --doc` | the same 9 doctests: 6 `compile_fail`, 3 positive controls |
| `he1_validation_bounds` (release) | 4 passed, 0 failed |
| `he1_wide_register` (release) | 1 passed, 0 failed |
| `check_ids.py` | `OK (0 warning(s))`; `AC=10, E=48, EC=44, EXP=6, HE-AC=12, HE-T=20, INV=8, N=25, OD=15` |
| `check_definition.py` | `OK`; 104 documents, newest x86 `0.78.0` (632 forms), AArch64 `0.20.0` (185), RV64 `0.6.0` (24) |
| `plan_identity.py --check` | exit 0; the three pinned digests still match |
| `he1_baseline.py --check` | `OK: payload projection identical`; `payload_root sha256:3f6d177d…ffefad9`; `definitions_root sha256:575b7c5f…35690e`; the envelope is skipped because the local binary digest differs from the recorder's |
| same command with `--binary` on the release build | `OK: payload projection identical`; the same `payload_root` and `definitions_root`; the release binary digest is `edc2c5fde6f9`, so all 128 release payloads equal the debug-recorded snapshot byte for byte |
| `oracle/rerun.py` | `122/128 re-derived, 6 skipped, 0 failed`; six `manual-derivation` skips |
| `git diff --check` | exit 0 |
| CI `gates`, run `43487661759` on `3b26bb1` | `workspace tests`, `document and definition gates`, `H0 payload baseline`, `oracle rerun` — all `success`; the runner reproduced `OK: payload projection identical` with both roots unchanged and `122/128, 6 skipped, 0 failed` |
| CI `determinism`, run `43487662063` on `3b26bb1` | `ubuntu-latest`, `macos-latest`, `windows-latest` — all `success` |
| CI `gates`, run `43496573107` on `7df6f48` | `workspace tests`, `document and definition gates`, `H0 payload baseline`, `oracle rerun` — all `success`; this is the final tree, including the allocator fix and the N13 CLI test |
| CI `determinism`, run `43496573111` on `7df6f48` | `ubuntu-latest`, `macos-latest`, `windows-latest` — all `success` |

**Doctest control.** Making `ValidatedPlan`'s three fields `pub` and deriving
`Clone` in a scratch copy turned exactly the two intended `compile_fail` tests
red (`Test compiled successfully, but it's marked compile_fail`) while the
positive control and the `BindIdentity::implementation()` negative stayed green;
the file was restored and all four pass again. The `fmp-materialize` negative
names the removed two-argument call, and its positive control shares the
`fmp_materialize::materialize` import, so a broken import cannot be mistaken for
a rejected signature.

### 11.4 Test inventory

`fmp-validate/tests/he1_bind.rs` (6):
`the_negatives_are_rejected_at_the_stage_their_boundary_requires`,
`a_type_legal_offset_is_rejected_by_check_through_bind`,
`a_page_transform_without_a_page_pc_rule_is_rejected_by_bind`,
`a_declared_namespace_must_match_the_bound_definition`,
`a_declared_version_must_match_the_bound_definition`,
`bind_reports_the_definition_it_bound`.

`fmp-materialize/tests/he1_execution.rs` (13):
`plan_identity_ignores_provenance`,
`plan_identity_ignores_the_legacy_document`,
`a_mutated_operand_changes_the_plan_identity`,
`a_legacy_fingerprint_is_not_a_trusted_cache_key`,
`a_bind_identity_does_not_identify_the_legacy_artifact`,
`payload_digest_follows_the_bytes`,
`receipt_names_the_build_that_ran`,
`an_image_reservation_failure_is_a_host_failure`,
`a_short_image_is_a_host_failure`,
`a_long_image_is_a_host_failure`,
`verify_receipt_notices_an_edited_artifact`,
`legacy_facade_rejects_a_digest_mismatch`,
`a_definition_identity_mismatch_is_rejected_by_the_legacy_facade`.

`fmp-materialize/tests/he1_stage_boundaries.rs` (4, now through `bind`):
`a_digest_mismatch_is_post_encode`,
`a_fixup_alignment_failure_is_post_encode`,
`a_fixup_range_failure_is_post_encode`,
`an_expected_size_mismatch_is_rejected_before_encoding`.

`fmp-cli/tests/cli_failure.rs` (3):
`a_binding_rejection_exits_one_with_the_diagnostic_array`,
`a_post_encode_assertion_exits_one_with_the_diagnostic_array`,
`a_usage_fault_exits_two_without_a_diagnostic_array`.
`fmp-cli/src/main.rs` unit tests (2):
`the_exit_code_separates_rejection_from_internal_fault`,
`a_post_encode_assertion_stays_on_the_plan_channel`.

### 11.5 Compatibility

- **Payloads:** none moved. `payload_root` is unchanged
  (`sha256:3f6d177d…ffefad9`), so all 128 positive payloads are byte-identical.
- **Definitions:** none moved. `definitions_root` is unchanged
  (`sha256:575b7c5f…35690e`); `check_definition.py` still sees 104 documents.
- **Negatives:** the 619 code + Pointer + detail-key triples are unchanged. Four
  fixtures gained a value-level assertion under the same code and Pointer:
  `N13` (`declared` `sha256:000…000`, `actual`
  `sha256:d17f36bd44115fe593938b561817d7d2e86f7dfeecedf40827be4b9012a310a7`),
  `N20` (`required_align` 2, `value` 2), `N04b` (`min` -2147483648, `max`
  2147483647, `value` 4294963195) and `N04f` (`min` -128, `max` 127, `value`
  4096). The other 615 stay on the triple gate.
- **Oracle:** unchanged at `122/128` with six `manual-derivation` skips. No
  definition or encoder-output file changed.
- **API:** this is a deliberate source break. `fmp_materialize::materialize` now
  takes `&ValidatedPlan` and returns `Result<Materialization,
  MaterializationFailure>`; the two-argument shape is only available as the
  deprecated `fmp_materialize::legacy::materialize`, which returns
  `Result<Artifact, LegacyFailure>` so a host fault keeps its classification.
  `Failure` in the CLI gained `Internal` and `Host`. `HostFault` gained
  `ImageLength { requested, actual }` and `Materialization` gained
  `verify_receipt()`. The FMP document surface is unchanged and no error code
  was added.
- **Receipt:** `payload_digest` is `sha256` over the `payload/0.1` projection
  (artifact JSON without `materializer_version`), and the digest's algorithm
  name is `payload/0.1`. It is deliberately not `canonical_digest(to_json())`.
- **CLI output:** the CLI still prints only the artifact. The receipt exists
  in-process; emitting it as a protocol object is H3's decision.

### 11.6 What H1b proves, and what it does not

Proved by a test or a compile-time property:

- `bind` is the only producer of `ValidatedPlan`, and `materialize` accepts
  nothing else; the negative is a `compile_fail` doctest and the positive
  control shares the import path;
- `bind` runs `check_structure` first, then the full
  `(namespace, version, digest)` comparison, then `check`; structural damage
  stops before the validator's arithmetic;
- `BindIdentity` covers the parsed plan and the bound table only; a
  `source_trace`-only change binds identically while the payload digest moves;
- a parsed-operand change moves `ParsedPlanIdentity` and the receipt while the
  legacy fingerprint stays put;
- a host allocation failure is `HostFailure`, not `Internal` and not a
  rejection, and the same plan succeeds with a working allocator;
- an allocator that returns fewer or more bytes than `declared_size` is
  `HostFailure::ImageLength { requested, actual }` before any fragment is
  written, and no artifact is produced;
- `verify_receipt()` is true for a fresh pair and false after the artifact bytes
  are edited;
- the receipt names `fmp-materialize`, records `build: None` when
  `FMP_BUILD_ID` is absent from the build, and records the injected label when
  it is present; CI compiles with the PR head SHA and refuses an empty label;
- the real CLI exits 1 for a `bind` rejection and for the N13 post-encode
  assertion (empty stdout, `E-BYTE-001` at `/instructions/0/expected_digest`),
  and 2 for usage, with different stderr channels.

Not proved here:

- **A real internal fault.** No test forces one. The `Internal` channel is
  covered by the pure `exit_code`/`classify` unit test and by the runtime
  arm; forcing a fault would require corrupting a validated plan or a test-only
  switch.
- **A real exhausted host.** The allocator path is injected. That is the
  opposite of a hidden switch (`INV-05`), but it is not evidence about a
  particular machine's memory.
- **Byte-identical diagnostic arrays for all 619 negatives.** Only the four
  measured post-encode fixtures have value snapshots.
- **H2–H4 and plans outside the corpus.** H1 acceptance says nothing about
  packages, bundles, the horizontal-extension classes, or a plan that is not one
  of the fixtures.

### 11.7 Next

H1 acceptance, in this order:

1. Push the branch, open the PR and run the three-host `workspace`, `documents`,
   `baseline` and `oracle` jobs. **Done.** PR #3 (`3b26bb1`): `gates` run
   `43487661759` passes `workspace tests`, `document and definition gates`,
   `H0 payload baseline` (`OK: payload projection identical`, both roots
   unchanged) and `oracle rerun` (`122/128`, 6 skipped, 0 failed);
   `determinism` run `43487662063` passes on ubuntu, macos and windows.
2. Decide `FMP_BUILD_ID`: either set it in CI and record the receipt, or state
   in the acceptance record that `build: None` is the accepted H1 state.
   **Decided: set in CI.** `gates.yml` (`workspace`, `baseline`) and
   `determinism.yml` (`cross-host`) compile with
   `FMP_BUILD_ID = ${{ github.event.pull_request.head.sha || github.sha }}`, so
   a PR build names the reviewed commit and a push build names the pushed one;
   a local build still records `None`. The value is compile-time, and Cargo
   recompiles when it changes (measured with a scratch test: the receipt and
   `option_env!` both reported the injected value, then both returned to
   `None`). `receipt_names_the_build_that_ran` compares the compiled identity
   with the **run-time** variable, and each CI job refuses an empty label before
   it compiles, so dropping the variable fails the job instead of silently
   producing `build: None`. The failing direction was checked: a binary built
   without the label, run with one, fails the test (`left: None`, `right:
   Some("3333…")`).
3. Measure debug/release payload equality instead of leaving it unmeasured.
   **Done for the corpus.** `he1_baseline.py --check` against the release build
   reports `OK: payload projection identical`, the same `payload_root` and
   `definitions_root`, and a distinct binary digest (`edc2c5fde6f9`), so the 128
   release payloads equal the debug-recorded snapshot. This is corpus equality,
   not a proof about plans outside the fixtures.
4. Only then write the H1 acceptance result; H1b being green locally is not that
   result. **Done, below.**

### 11.8 H1 acceptance

H1 is accepted on `7df6f48` (2026-11-14). The criteria are `HE-AC-06` together
with `HE-T02`, `HE-T03`, `HE-T04` and the unchanged payload root
(`docs/architecture/he1-horizontal-extension.md` §13/§14;
`docs/architecture/he1-h1-plan.md` completion definition):

| Criterion | Evidence |
|---|---|
| `HE-AC-06`: a validated definition and plan cannot be changed through public fields, and the output identity names the executed object | `Definition` is closed (`H1a`); `ValidatedPlan` has private fields, no `Clone`, no constructor and one producer (`bind`); three `compile_fail` doctests; `a_mutated_operand_changes_the_plan_identity`; `a_bind_identity_does_not_identify_the_legacy_artifact` |
| `HE-T02`: modifying the source DTO cannot reuse an existing credential | `he1_bind.rs` replays the mutated inputs; `ValidatedPlan` cannot be rebuilt from one |
| `HE-T03`: tampered definition content with the declared digest | `a_definition_edit_reloads_to_a_new_digest`; `legacy_facade_rejects_a_digest_mismatch`; `a_definition_identity_mismatch_is_rejected_by_the_legacy_facade` |
| `HE-T04`: validate A, execute B | not expressible: `materialize` takes only `&ValidatedPlan`, and the plan and definition travel together |
| Payloads unchanged | `payload_root sha256:3f6d177d…ffefad9`, `definitions_root sha256:575b7c5f…35690e`, `122/128` oracle with six `manual-derivation` skips |
| Receipt names the build | CI compiles with `FMP_BUILD_ID = 7df6f4814154cd8243dd563fabb602341b43ca39`; the job log prints it, and `receipt_names_the_build_that_ran` fails when the run-time label is not in the compiled identity |
| Three hosts | `gates` run `43496573107` (workspace, document/definition, baseline, oracle) and `determinism` run `43496573111` (ubuntu, macos, windows) |
| Debug/release equality | the release binary reproduces the same `payload_root` as the debug-recorded snapshot |

The acceptance takes effect with this PR; the phase board still shows H2–H4
open.

### 11.9 Pre-merge audit fix

The audit of `ac69320` accepted the architecture and found one boundary hole
worth fixing before merge: `materialize_with_allocator` was public but did not
check the callback's length. A short image would panic on the first fragment
write; a long image would return extra bytes under a receipt, producing N+1
bytes where the frozen plan declared N. The fix is
`HostFault::ImageLength { requested, actual }`; `emit` compares `image.len()`
with `section.declared_size` before writing any fragment. It is a host failure:
no artifact, no plan rejection, and no new error code.

The same audit noted that `Materialization`'s public artifact can be edited
after execution, so the receipt and the bytes can drift. `verify_receipt()`
recomputes the payload projection and compares it with the recorded digest; the
pair is still not frozen, but the drift is now detectable before persistence.
`ImplementationIdentity::build` is documented as a source revision, not a
binary identity: a binary or build-manifest digest belongs to the stage that
persists receipts, so this report does not claim full binary identity.

The audit also asked for the post-encode channel to be measured in the real
process, not only through `MaterializationFailure::PostEncodeAssertion`:
`cli_failure.rs` now runs N13 and asserts exit 1, empty stdout and one
`E-BYTE-001` at `/instructions/0/expected_digest`. It still does not force
`Internal`; that remains covered by the pure classification test, as §11.6
says.

Evidence: `a_short_image_is_a_host_failure`, `a_long_image_is_a_host_failure`,
`verify_receipt_notices_an_edited_artifact`,
`a_post_encode_assertion_exits_one_with_the_diagnostic_array`; the workspace is
119 passed / 0 failed; CI is green on `7df6f48` (`gates` `43496573107`,
`determinism` `43496573111`). Nothing under `definitions/`, `fixtures/`,
`schema/` or `docs/fmp-v0/` changed; both roots stayed put and the oracle stayed
`122/128`.
