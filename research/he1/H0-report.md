# H0 report — baseline and boundary

Stage: H0 (design §13, `ADR-0125`)
Date: 2026-11-10
Base commit: `d0082f9f2d3da2786d8d1c0467d2793369ec9090`

## 1. Change scope

Product code: **none**. Nothing under `prototype/crates/*/src/` changed.

| Path | Change | Why |
|---|---|---|
| `research/he1/compatibility-results.json` | new | The baseline payload projection: 104 definitions, 128 artifact payloads, counts, oracle state, probes (`ADR-0126`) |
| `research/he1/compatibility-h0-envelope.json` | moved | The original H0 snapshot, byte-identical, kept as frozen envelope evidence when the gate moved to the payload projection (`ADR-0126`) |
| `research/he1/baseline.md` | new | What the snapshot covers, what "unchanged" means, its limits |
| `research/he1/H0-report.md` | new | This report |
| `tools/he1_baseline.py` | new | Records and checks the snapshot by running the real `fmp` binary; never a build input |
| `prototype/crates/fmp-cli/tests/he1_identity_characterization.rs` | new | Six tests: four assert a hole HE-1/H3/H4 must close, one is the digest-mismatch control, one is the non-object-root control (corrected by `ADR-0126`; the deep-JSON finding is the Python probe, not a Rust test) |
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
python tools/he1_baseline.py --probes             # records; probes are opt-in
python tools/he1_baseline.py --check research/he1/compatibility-results.json
git diff --cached --check                     # after staging
```

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
| `cargo test --workspace` | 60 passed, 0 failed: `determinism` 6, `fixtures` 2, `he1_identity_characterization` 6, `planner_api` 10, `fmp_materialize` 9, `fmp_model` 22, `fmp_plan` 5 |
| `he1_baseline.py` | recorded 104 definitions / 128 positives / 619 negatives / 128 artifacts; `artifact_root sha256:dfd08fee9844058492138b23448073ec47d8eda42383e3f1b3e567db86a86fef` (that value is now the **envelope** root; the gate is `payload_root` — §6) |
| `he1_baseline.py --check` | `OK: identical` — re-run reproduces the snapshot exactly |

Name the six skips: `X86-P1`, `X86-P4`, `X86-P5`, `X86-P9`, `X86-P10`,
`X86-P83`. They are `kind = manual+disassembly` by design; the tool derives the
count from the records, so a seventh cannot appear silently.

### Audit risks: reproduced or not

| Risk | Status | Evidence |
|---|---|---|
| A verified definition and its execution facts can diverge | **reproduced** | `a_loaded_definition_can_be_re_encoded_under_its_original_digest`: all templates replaced, digest and fingerprint unchanged, bytes changed |
| Plan identity does not cover the parsed operands | **reproduced** | `a_parsed_operand_can_change_under_a_stable_fingerprint`: fingerprint identical, bytes differ |
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
  in H1/H3/H4. A green run here is not a property claim. The other two are
  controls: a digest mismatch and a non-object root, both rejected today.
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
   the 128-artifact digest comparisons and the six characterization tests, on
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
   is four gaps plus two controls:

   | Test | Class | Closes in |
   |---|---|---|
   | `a_loaded_definition_can_be_re_encoded_under_its_original_digest` | gap | H1 |
   | `a_parsed_operand_can_change_under_a_stable_fingerprint` | gap | H1 |
   | `an_unselected_file_in_the_definition_directory_breaks_loading` | gap | H3 |
   | `a_synthetic_namespace_is_rejected_by_the_loader` | gap | H3 |
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

Controls run after the correction, on this host (`fmp` debug build 0.0.0):

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

## Next

H1 — identity closure (`ADR-0127`): private verified objects, a bound
`ValidatedPlan`, one fact source per identity, separate plan/definition/artifact/
implementation identities, and the legacy facade that cannot bypass the checks.
Exit: no supported API can make execution facts and a verified identity
disagree. H1 flips two of the four gap tests (the definition re-encode and the
stable fingerprint); the other two close in H3 (unselected file, ISA allowlist),
and the deep-JSON probe finding is H4. The implementation plan, with its ten
decisions (D1–D10), is `docs/architecture/he1-h1-plan.md`.
