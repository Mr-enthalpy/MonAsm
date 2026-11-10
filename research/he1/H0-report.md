# H0 report — baseline and boundary

Stage: H0 (design §13, `ADR-0125`)
Date: 2026-11-10
Base commit: `d0082f9f2d3da2786d8d1c0467d2793369ec9090`
Projection recording commit: `ebddbdb02c558baff9c44d90bbdead3e3db96175` (§7)

## 1. Change scope

Product code: **none**. Nothing under `prototype/crates/*/src/` changed.

| Path | Change | Why |
|---|---|---|
| `research/he1/compatibility-results.json` | new | The baseline payload projection: 104 definitions, 128 artifact payloads, counts, oracle state, probes (`ADR-0126`) |
| `research/he1/compatibility-h0-envelope.json` | moved | The original H0 snapshot, byte-identical, kept as frozen envelope evidence when the gate moved to the payload projection (`ADR-0126`) |
| `research/he1/baseline.md` | new | What the snapshot covers, what "unchanged" means, its limits |
| `research/he1/H0-report.md` | new | This report |
| `tools/he1_baseline.py` | new | Records and checks the snapshot by running the real `fmp` binary; never a build input |
| `prototype/crates/fmp-cli/tests/he1_identity_characterization.rs` | new | Seven tests: four assert a hole HE-1/H3/H4 must close, one pins a constraint H1 must preserve (the legacy fingerprint reads a field the parser drops), two are controls (digest mismatch, non-object root). The deep-JSON finding is the Python probe, not a Rust test |
| `tools/test_he1_baseline.py` | new (§7) | 50 tests over synthetic snapshots: the comparator fails on a payload or count change, passes on a receipt change alone, still compares payloads when the receipt changes, and refuses a structurally invalid snapshot or anchor with exit 2 before materializing (§8–§10). It also recomputes every entry digest and derived count, proves a bare invocation cannot overwrite the frozen baseline, and records a failing toolchain subprocess as `unavailable` rather than raising. No binary needed, so CI runs it first |
| `docs/architecture/he1-horizontal-extension.md` | moved from the repository root | Adopts the design document; header now names `ADR-0125` and the `HE-AC`/`HE-T` registry role. Trailing whitespace stripped: 811 lines, no wording removed |
| `docs/adr/0125-he1-scope.md` | new | The scope decision and the conflict resolution |
| `AGENTS.md` | edited | Current round, repository map (`docs/fmp-0.2/`, `docs/architecture/`, `packages/`, `bundles/`, `research/he1/`), three added done-criteria bullets. The eight hard rules and "Never do" are untouched |
| `docs/STATUS.md` | edited | One HE-1 paragraph in the next-action section; the v0 phase board is unchanged |
| `tools/check_ids.py` | edited | Registers the `HE-AC` (12) and `HE-T` (20) families against the design document; adds `family_of()` so `HE-T01` resolves without a separator |

No change under `definitions/`, `fixtures/`, `schema/`, `docs/fmp-v0/` or the
Rust sources.

## 2. Commands actually run

Run from the repository root unless stated otherwise.

```text
git rev-parse HEAD
python tools/check_ids.py
python tools/check_definition.py
python tools/check_mrs.py
python tools/check_rv64_source.py
python tools/oracle/rerun.py --allow-skip-reason manual-derivation
cargo +1.96.0 fmt --all -- --check            # run in prototype/
cargo +1.96.0 test --workspace                # run in prototype/
cargo +1.96.0 test -p fmp-cli --test he1_identity_characterization
python tools/test_he1_baseline.py                 # the comparator's own tests
python tools/he1_baseline.py --record --probes    # records; probes are opt-in
python tools/he1_baseline.py --check research/he1/compatibility-results.json --anchor research/he1/baseline-anchor.json
git diff --cached --check                     # after staging
```

The build the baseline needs is
`cargo +1.96.0 build --bin fmp -p fmp-cli --manifest-path prototype/Cargo.toml`
from the repository root, or the same command with `working-directory:
prototype`; the root has no `Cargo.toml`, so the manifest path is not optional
(§7).

## 3. Results

| Command | Result |
|---|---|
| `git rev-parse HEAD` | `d0082f9f2d3da2786d8d1c0467d2793369ec9090` — identical to the design's baseline |
| `check_ids.py` | `OK (0 warning(s))`; declared `AC=10, E=48, EC=44, EXP=6, HE-AC=12, HE-T=20, INV=8, N=25, OD=15` |
| `check_definition.py` | `OK`; 104 documents, newest x86 `0.78.0` (632 forms), AArch64 `0.20.0` (185), RV64 `0.6.0` (24) |
| `check_mrs.py` | `OK`: MRS drop and both file hashes match `ADR-0006` |
| `check_rv64_source.py` | `OK`: eight resolved-spec nodes and the RV64 `NOTICE` match `ADR-0007` |
| oracle rerun | `122/128 re-derived, 6 skipped, 0 failed`; `toolchain: llvm-mc 23.1.2`; skips are the six `manual-derivation` records |
| `cargo fmt --check` | clean (the new test file was formatted once with `cargo fmt --all`) |
| `cargo test --workspace` | 61 passed, 0 failed: `determinism` 6, `fixtures` 2, `he1_identity_characterization` 7, `planner_api` 10, `fmp_materialize` 9, `fmp_model` 22, `fmp_plan` 5 |
| `test_he1_baseline.py` | 38 passed, 0 failed — comparator, schema, anchor, record-mode, exit-code, discovery, timeout and structural-fault tests; no binary involved (19 at H0, 24 after §8, 38 after §9, 50 after §10) |
| `he1_baseline.py` | recorded 104 definitions / 128 positives / 619 negatives / 128 artifacts; `artifact_root sha256:dfd08fee9844058492138b23448073ec47d8eda42383e3f1b3e567db86a86fef` (that value is now the **envelope** root; the gate is `payload_root` — §6) |
| `he1_baseline.py --check` | `OK: payload projection identical`; `payload_root` unchanged; `envelope: identical (same implementation receipt)` |

Name the six skips: `X86-P1`, `X86-P4`, `X86-P5`, `X86-P9`, `X86-P10`,
`X86-P83`. They are `kind = manual+disassembly` by design; the tool derives the
count from the records, so a seventh cannot appear silently.

### Audit risks: reproduced or not

| Risk | Status | Evidence |
|---|---|---|
| A verified definition and its execution facts can diverge | **reproduced** | `a_loaded_definition_can_be_re_encoded_under_its_original_digest`: all templates replaced, digest and fingerprint unchanged, bytes changed |
| Plan identity does not cover the parsed operands | **reproduced** | `a_parsed_operand_can_change_under_a_stable_fingerprint`: fingerprint identical, bytes differ |
| The legacy fingerprint cannot be reproduced from the parsed plan | **reproduced as a constraint** | `a_legacy_fingerprint_covers_document_fields_the_parser_drops`: adding `source_trace` to the raw document leaves `Plan.instructions` identical and changes the fingerprint, because `fingerprint()` hashes `plan.document` (`fmp-materialize/src/lib.rs:920`) |
| An unselected definition file decides whether a plan materializes | **reproduced** | `an_unselected_file_in_the_definition_directory_breaks_loading`: one stray `*.json` → `E-DEF-001` for the whole load |
| A new ISA namespace requires changing the model crate | **reproduced** | `a_synthetic_namespace_is_rejected_by_the_loader`: `probe:insn/x` → `E-DEF-001`, "unknown ISA family" |
| Deep input is unbounded | **reproduced** | probe `deep-json`: exit `3221225725` (`0xC00000FD`), `thread 'main' has overflowed its stack` |
| Fixup pairing is under-checked | **not reproduced** | `check_fixup_pairs` and `check_fixup_ownership` exist and the corpus passes; H0 did not build a counterexample. Carried to H4 |
| Definition loading has a hash-then-read TOCTOU window | **not reproduced** | the CLI reads the file once and the digest is computed from the parsed document. This is a rule for the new loader, not a current defect |
| Numeric and resource limits are incomplete | **partially reproduced** | deep JSON crashes; the 1 MiB unknown-field probe rejects cleanly; the 64 MiB image bound was not re-probed |

## 4. Compatibility differences

- **Legacy payloads:** none. `payload_root` was recorded and re-checked
  identical, and the new `envelope_root` equals the `artifact_root` first
  recorded, so the projection change moved no meaning (`ADR-0126`);
  `definitions/` and `fixtures/` are byte-identical to `d0082f9`.
- **Documented behaviour:** none changed. Four new tests *pass by asserting the
  current hole*; they are labelled as characterization tests and will be flipped
  in H1/H3/H4. A green run here is not a property claim. The definition
  re-encode test cannot be flipped in place once `Definition` fields are private
  (H1a), so it is replaced by a `compile_fail` constraint plus a
  `reload-changes-digest` test rather than flipped (`§8`). One is a constraint —
  the legacy fingerprint sees raw-document fields the parser drops — and asserts
  a property H1 must preserve. The other two are controls: a digest mismatch and
  a non-object root, both rejected today.
- **Tooling:** `check_ids.py` now reports two more ID families and enforces them.
  Previously unmanaged IDs (`HE-AC-01`…`HE-AC-12`, `HE-T01`…`HE-T20`) are now
  declared-once and reference-checked. No existing ID's status changed.
- **Documentation:** the design document moved out of the repository root and
  lost trailing whitespace only. `AGENTS.md` and `STATUS.md` gained pointers; no
  v0 statement was weakened. `ADR-0095`, `ADR-0123` and `ADR-0124` are not
  superseded.
- **Build:** unchanged; no crate was added in H0.

## 5. Status of the open claims

Two rows were `unverified` when H0 was written and became measurable once the
branch was pushed; they are kept in place, with the upgrade named, rather than
deleted.

1. **Cross-host determinism — verified after the H0 commit.** Hosted run
   `42698924288` (workflow `determinism`) ran `cargo test --workspace`, including
   the 128-artifact digest comparisons and the characterization tests (six at
   that run), on
   `ubuntu-latest`, `macos-latest` and `windows-latest`: three jobs, all green.
   This upgrades the earlier statement, which rested on run `42681104791` and
   `EXP-R3` alone.
2. **Debug vs release payload equality.** The snapshot used a debug binary.
   `EXP-R1`–`R6` cover repeat runs, not build-profile equality.
3. **Hosted CI on these commits — verified after the H0 commit.** Run
   `42698924814` (`gates`) is green: `check_ids.py`, `check_definition.py`, the
   whitespace range `d0082f9..HEAD`, `cargo fmt --check`,
   `cargo test --workspace` and `oracle/rerun.py --allow-skip-reason
   manual-derivation` on Python 3.12 and `llvm-mc 23.1.2`. `check_mrs.py` and
   `check_rv64_source.py` remain local-only by `ADR-0124`, because the hosted
   runner has no `research/external/`.
4. **Python parity for the baseline tool.** `check_ids.py` and
   `check_definition.py` run on 3.12 in CI. `tools/he1_baseline.py` did not, until
   `ADR-0126` added the `baseline` job, which runs `--check` on Python 3.12 with
   the binary that job builds. Its first hosted result belongs to the PR that
   adds it, not to this H0 record.
5. **Fixup pairing and numeric limits.** Two audit risks stayed unreproduced and
   one was only partially probed, as listed in §3. They are H4 work, not H0
   findings.
6. **Oracle asset provenance.** The LLVM asset's Sigstore signature is still
   unverified; `ADR-0124` records this and H0 did not change it.

## 6. Corrections from the PR review (`ADR-0126`)

Three statements in this report were wrong, and one measurement rule was too
coarse. They are corrected here instead of being silently rewritten, because the
baseline is evidence and its history matters.

1. **Test classification.** §1 and §4 said five of six tests document a hole. It
   is four gaps plus two controls, and a second review added a seventh test that
   is a constraint:

   | Test | Class | Closes in |
   |---|---|---|
   | `a_loaded_definition_can_be_re_encoded_under_its_original_digest` | gap | H1 |
   | `a_parsed_operand_can_change_under_a_stable_fingerprint` | gap | H1 |
   | `an_unselected_file_in_the_definition_directory_breaks_loading` | gap | H3 |
   | `a_synthetic_namespace_is_rejected_by_the_loader` | gap | H3 |
   | `a_legacy_fingerprint_covers_document_fields_the_parser_drops` | constraint (added in §7) | preserved by H1 |
   | `a_plan_naming_another_definition_digest_is_rejected` | control | — |
   | `the_plan_reader_rejects_a_non_object_top_level` | control | — |

   The deep-JSON finding is not one of these tests. It is the `deep-json` probe
   in `tools/he1_baseline.py`, and it belongs to H4.
2. **The digest mixed payload and build identity.** `artifact_sha256` hashed the
   whole envelope, which contains `materializer_version`, so a release bump would
   have moved all 128 digests with no change to any encoder. `--check` now
   compares the payload projection; the old value survives as the
   `envelope_root` of `research/he1/compatibility-h0-envelope.json`, and the new
   `envelope_root` reproduces it exactly. The gate value is `payload_root`
   `sha256:3f6d177d…ffefad9`.
3. **`--check` was not portable and triggered a known crash.** The default binary
   was hard-coded to `fmp.exe`, and the probes ran by default with no timeout
   even though their results were not compared. Discovery now tries `.exe` then
   the bare name, probes are behind `--probes`, and every subprocess has a
   timeout.

Controls run after the correction, on this host (`fmp` debug build 0.0.0). §7
turns them into `tools/test_he1_baseline.py`, which runs in CI; the table stays
as the record of what was measured by hand:

| Mutation of the recorded snapshot | Expected | Observed |
|---|---|---|
| `payload_sha256` of entry 0 | fail | exit 1, one diff |
| `payload.bytes_hex` of entry 0 | fail | exit 1, one diff |
| `implementation` only (`9.9.9`) | pass, envelope skipped | exit 0, `OK: payload projection identical` |
| `implementation` **and** `payload.bytes_hex` | fail | exit 1 (the payload is still compared) |
| `envelope.sha256` with an identical receipt | fail | exit 1 |
| one entry removed | fail | exit 1, `length 127 -> 128` |
| `corpus.negatives` 619 → 618 | fail | exit 1 |
| schema rewritten to `…/0.1` | usage error | exit 2, no comparison |

Hosted replay: `gates` run `42714224361` (job `H0 payload baseline`) built `fmp`
on Ubuntu 24.04 with Python 3.12 and printed the same `payload_root`; its
`binary_sha256` differs from this host's, so the envelope was skipped by design.
That is the first evidence that the 128 payloads are host- and build-independent,
as opposed to the three envelope digests `determinism.rs` pins.

## 7. Second review round (`ebddbdb`)

The review of `ebddbdb` found no new defect in the H0 evidence itself, but it
found two places where the record could mislead and two H1 design conflicts that
would only surface during implementation. This round changes no product Rust
code; it corrects the baseline tool, its tests and the documents.

1. **A fault looked exactly like a diff.** The tool documented exit 1 as "the
   baseline moved" and exit 2 as "usage or I/O fault", but every fault path was
   `raise SystemExit("...")`, which Python exits as 1. A missing binary, a
   corrupt snapshot, an unknown schema and a real payload regression were
   therefore indistinguishable. Faults now raise one `Fault` type, `main()` maps
   it to 2, and exit 1 is reserved for a recorded difference. The recorded
   snapshot is read and validated before any materialization, so a bad snapshot
   costs one second, not 128 subprocesses.
2. **The comparator had no regression test.** The eight controls above were run
   by hand once. `tools/test_he1_baseline.py` makes them 19 tests at this round
   (24 after §8) over two synthetic snapshots — no binary, no `definitions/` scan
   — and the `baseline`
   job runs it before installing the toolchain. It pins the property the first
   draft of the split broke: **a changed implementation receipt does not stop the
   payload from being compared**.
3. **`head` conflated two commits.** `compatibility-h0-envelope.json` records
   `head = d0082f9` (the artifacts' commit) and the projection records
   `ebddbdb` (the commit that wrote it). Both are now named:
   `provenance.original_baseline_commit` is read from the frozen snapshot, and
   `provenance.projection_recording_commit` / `…_worktree` describe this
   recording. The payload root did not move.
4. **The documented build command did not run.** `baseline.md` and this report
   printed `cargo +1.96.0 build --bin fmp -p fmp-cli`, but the repository root has
   no `Cargo.toml`. The command now carries
   `--manifest-path prototype/Cargo.toml`; CI's `working-directory: prototype` is
   the same build.
5. **A seventh characterization test, and it is a constraint.** The H1 plan
   promised to delete `Plan.document` while keeping `fingerprint()` byte-
   identical. Reading the code showed this cannot hold: the parser accepts and
   drops `Instruction.source_trace`, and allows `symbol.type`/`symbol.size`
   without retaining them, but `fingerprint()` hashes the raw document
   (`fmp-materialize/src/lib.rs:920`). The new test injects `source_trace` into a
   fixture's raw JSON, asserts the parsed `Instruction` is unchanged, and asserts
   the fingerprint changed. It passes by documenting a constraint, not a gap:
   H1 must keep the raw document as a read-only legacy input (H1 plan `D12`).
6. **The H1 plan's identity layering was unimplementable.** It put
   `ImplementationIdentity` in `fmp-materialize` while `bind()` — in
   `fmp-validate` — was to return an identity containing it, which would need
   `fmp-validate → fmp-materialize` and close a crate cycle. The plan now splits
   `BindIdentity` (validator) from `ExecutionReceipt` (materializer), which is
   `D11`. Both are absorbed in `docs/architecture/he1-h1-plan.md`; no H1 code was
   started.

Re-measured on the second round: 61 workspace tests (7 characterization),
19 comparator tests, `payload_root`
`sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`
unchanged, `envelope_root` unchanged. The five existing gap/control tests and
their verdicts did not change.

## 8. Third review round (`ccdc7a3`)

The third review accepted the H0 evidence and the H1 direction, and requested
four changes before `ADR-0127` can be frozen. None of them touches product Rust
code; this round changes the baseline tool, its self-tests, and the H1 plan.

1. **A structurally invalid snapshot still exited 1.** `require_schema()` called
   `recorded.get("schema")` without first checking that the decoded JSON was an
   object, so a snapshot of `[]` or `null` raised an uncaught `AttributeError`
   and Python exited 1 — the code that means "the baseline moved". A new
   `validate_snapshot()` checks the root object, the three sub-objects,
   `artifacts.count`, every entry's `fixture`/`payload_sha256`/`payload`, and the
   implementation receipt's string fields, and raises `Fault` (exit 2) before the
   128 subprocesses start. This is still not a blanket `except Exception`: each
   check names the shape it requires.
2. **Five structural-fault tests were added** (24 total now): `[]`, `null`, a
   missing `artifacts`, a wrongly typed `implementation`, and an entry without
   `payload_sha256`. Each asserts exit 2 and the fault message, so the old
   behaviour would fail the suite.
3. **The H1 plan had misclassified allocation failure.** It claimed the
   materializer cannot produce a host failure because its product path has no
   I/O. `emit()` already calls `bytes.try_reserve_exact(size)` at
   `fmp-materialize/src/lib.rs:400`, with a comment at `:397-399` saying the
   failure is "a host limit, not a plan property"; allocation failure depends on
   host resources. `MAX_IMAGE_BYTES` already exists at
   `fmp-validate/src/lib.rs:18` (checked at `:285`), and design §8.3 requires a
   separate `HostFailure`. `D4` now keeps three variants —
   `PostEncodeAssertion`, `Internal`, `HostFailure(HostFault)` — with an
   injectable `allocate_image` seam for the test; the CLI maps `HostFailure` to
   exit 2.
4. **`BindIdentity` was described as if it identified the whole artifact.**
   Plan A and plan B = A plus `source_trace` have equal `ParsedPlanIdentity` and
   `DefinitionIdentity`, but different legacy `fingerprint` values and therefore
   different `payload_digest`s, because `fingerprint` is an `Artifact` field.
   `D3`/`D12` now say `BindIdentity` is a parse/bind identity, not a replay or
   cache key; full identity needs the `ExecutionReceipt`. A two-plan regression
   test is planned.
5. **The H1a/H1b split contradicted the compiler.** Private `Definition` fields
   make the current definition-mutability test stop compiling. Its conversion
   (`compile_fail` plus a reload-changes-digest runtime test) is now owned by
   H1a; H1b flips only the fingerprint test. Each commit can then pass the
   workspace tests on its own.

Re-measured after this round: 61 workspace tests (7 characterization), 24
comparator tests, `payload_root`
`sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`
unchanged, `envelope: identical`. The hosted result for this round is the run
attached to the PR after the push, not part of the recorded snapshot.

## 9. Fourth review round (`66d5e14`)

The fourth review accepted the H0 evidence and the H1 direction, and requested
revisions before `ADR-0127` can be frozen. No product Rust code changed in
this round either.

1. **A re-recording could silently redefine the baseline.** The tool's default
   output path *was* the frozen snapshot, so a later commit could change an
   encoded artifact, re-record, and still pass the comparator. Recording is now
   explicit (`--record`); a bare invocation and `--check --record` are usage
   faults (exit 2), and `--out` is only valid with `--record`. A second file,
   `research/he1/baseline-anchor.json` (schema
   `monasm.he1.baseline-anchor/0.1`), pins only `payload_root`; `--check` requires
   the recorded snapshot to equal it. A mismatch is a **diff** (exit 1), a
   missing or malformed anchor is a **fault** (exit 2), and moving the anchor
   needs a compatibility ADR. The envelope root is deliberately not anchored: it
   contains `materializer_version`, so anchoring it would forbid a legitimate
   build-version change.
2. **Snapshot structure validation was still incomplete.** `validate_snapshot()`
   now checks `projections`, `definitions.count`/`documents`, `corpus.positives`/
   `negatives`/`by_isa`, `oracle.kinds`, both roots as `sha256:` digests, every
   entry's `fixture`/`plan_sha256`/`fingerprint`/`level`/`size`/`definition`/
   `payload_sha256`/`payload`/`envelope`, `artifacts.count == len(entries)`, and
   recomputes both roots from the entries. The envelope is checked
   unconditionally: current CI's implementation receipt differs from the
   recorder's, so `comparison_projection()` would drop it, and a deleted envelope
   would otherwise look like a clean payload match. Structural failures all exit
   2 before materialization.
3. **A public mutable `Plan` could be wrapped as `ValidatedPlan` without full
   structural checks.** `plan::read` rejects odd-length or non-lowercase-hex
   `payload_hex`, but `check_fragments` only compares `hex.len() / 2` with
   `fragment.size`, and `decode_hex()` indexes `pair[1]`. Since `Plan`,
   `Section`, `Fragment` and `FragmentBody` are public and mutable, the
   X86-P71 data fragment `"aabbccdd"` can be changed in memory to `"aabbccdd0"`
   (length 9, `9 / 2 == 4`) and reach an index-out-of-bounds panic; `"zzzzzzzz"`
   would be silently decoded as zero bytes. The H1 plan now adds
   `plan::check_structure(&Plan)` as the first step of `bind`, with those two
   X86-P71 negative tests in H1a (`D13`, plan §3.2/§4.2). The counterexample is
   source-derived and is labelled as such until the two tests run.
4. **`Internal` shared the plan-rejection exit.** The frozen error spec defines
   `E-INTERNAL-001` as an implementation-invariant violation, not user input, and
   the CLI reserves exit 1 for a rejected plan. The plan now routes
   `MaterializationFailure::Internal` through a distinct internal-fault channel
   at exit 2, with `exit_code()` unit-tested; `PostEncodeAssertion` and `bind`
   rejection stay at exit 1.
5. **The §8 phase boundary repeated an existing limit.** `MAX_IMAGE_BYTES`
   already exists in `fmp-validate`; H4 is now described as validating and
   completing resource limits (parse depth, new package formats), not introducing
   the 64 MiB image bound.

Re-measured after this round: 61 workspace tests (7 characterization), 38
comparator tests, `payload_root`
`sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`
unchanged. The recorded snapshot itself was not re-recorded; only its validation
and the independent anchor were added. The hosted result for this round is the
run attached to the PR after the push.

## 10. Fifth review round (`cb1e4ad`)

The fifth review confirmed the H0 evidence, accepted the H1 direction, and found
one H1 plan blocker plus two comparator robustness gaps. No product Rust code
changed in this round either.

1. **`check_structure` covered two string rules, not every parser bound the DTO
   type cannot enforce.** `FieldRange.lsb` (0–127), `FieldRange.width` (1–64),
   `RangeConstraint.bits` (1–64), `RangeConstraint.align_bits` (0–12) and
   `Fixup.transform_shift` (0–63) are all `u32`/`Option<u32>` in the DTO, so a
   mutated `Plan` can carry values `plan::read` would reject. `align_bits = 128`
   reaches `1i128 << align_bits`; `bits = 0` underflows `bits - 1`; a huge
   descriptor width makes the validator's `u32` width sum overflow and can drive
   a very large bit loop. D13 now lists all five bounds in a
   parser-invariant/DTO-type/validator-invariant table, requires
   `check_structure` before any validator shift or sum, and adds six
   source-derived regression tests: `align_bits = 128`, `transform_shift = 128`,
   illegal `lsb`/`width`/`bits`, and a `u32::MAX` width-sum case. H1a also
   hardens the validator's descriptor arithmetic to `u64`/`checked_add` as a
   second line of defence. The counterexamples are source-derived, not yet run.
2. **An entry's content was not checked against its recorded digest.**
   `validate_snapshot()` used to accept `payload.bytes_hex` edited without
   updating `payload_sha256`, and would then report the difference as baseline
   drift (exit 1) rather than a corrupt snapshot (exit 2). It now recomputes
   `payload_sha256 = SHA256(canonical(payload))` and
   `envelope.sha256 = SHA256(canonical(payload + materializer_version))` for
   every entry before comparing roots.
3. **Derived counts were not checked against their arrays.** The tool now
   requires `definitions.count == len(documents)`, each `newest` path to exist in
   `documents`, `corpus.positives`/`negatives` to equal the `by_isa` sums,
   `artifacts.count` to equal `corpus.positives`, `oracle.kinds` to sum to
   `corpus.positives`, and `manual_derivation` to match its oracle kind. The
   synthetic fixtures were rebuilt from their payloads and counts, so they are
   internally consistent instead of only shape-valid.
4. **A failing toolchain subprocess escaped as exit 1.** `toolchain()` indexed
   `stdout.splitlines()[0]` without checking the return code; a `cargo --version`
   that failed wrote only to stderr and raised `IndexError`, which Python exits
   as 1. `toolchain_version()` now returns `unavailable: exit N: ...` or
   `unavailable: empty stdout`, and a failing subprocess is tested. Definition
   and oracle JSON are also required to be objects before `.get()`.

Re-measured after this round: 61 workspace tests (7 characterization), 50
comparator tests, `payload_root`
`sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`
unchanged. The recorded snapshot was not re-recorded. The hosted result for this
round is the run attached to the PR after the push.

## Next

H1 — identity closure (`ADR-0127`): private verified objects, a bound
`ValidatedPlan`, one fact source per identity, separate plan/definition/artifact/
implementation identities, and the legacy facade that cannot bypass the checks.
Exit: no supported API can make execution facts and a verified identity
disagree. H1a converts the definition re-encode test into a `compile_fail`
constraint plus a reload-changes-digest test, because private fields make the
current test uncompilable; H1b flips the stable-fingerprint test. The other two
gap tests close in H3 (unselected file, ISA allowlist), the legacy-fingerprint
constraint is preserved rather than flipped, and the deep-JSON probe finding is
H4. The implementation plan, with its thirteen decisions (D1–D13), is
`docs/architecture/he1-h1-plan.md`. H1a also owns `plan::check_structure` and its
two DTO counterexample tests, so the binding path cannot trust a plan merely
because it was once parsed.
