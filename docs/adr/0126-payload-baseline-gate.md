# ADR-0126: the baseline gate compares payloads, and the envelope is a receipt

- Status: accepted
- Date: 2026-11-10
- Settles: which projection of the H0 artifact snapshot is a gate; how a
  materializer build is recorded; and whether the baseline runs in CI
- Supersedes: none
- Superseded by: none
- Revises: the `artifact_root` consequence of `ADR-0125`; the job set of
  `ADR-0124` (a fourth job, `baseline`); `tools/he1_baseline.py`;
  `research/he1/baseline.md`; `research/he1/H0-report.md`; the artifact identity
  row of `docs/architecture/he1-h1-plan.md`
- Keeps in force: `ADR-0123` for the artifact envelope; the three digests in
  `prototype/crates/fmp-cli/tests/determinism.rs`, now labelled envelope digests

## Context

H0 recorded every positive artifact as one object and hashed that object. That
was wrong in one specific way, and the same mistake was about to be inherited by
the H1 plan.

`Artifact::to_json()` writes `materializer_version` into both envelope levels
(`fmp-materialize/src/lib.rs:118` for Level 0, `:136` for Level 1). The recorded
`artifact_sha256` hashes the whole object (`tools/he1_baseline.py:166` in the H0
version of the tool) and `artifact_root` aggregates it. So the recorded identity
of every artifact contains the identity of the binary that recorded it.

Concrete failure: bump `MATERIALIZER_VERSION` from `0.0.0` to `0.1.0` with no
change to any encoder. All 128 `artifact_sha256` values change, `--check` fails,
and `HE-AC-10` ("all existing valid fixtures keep their machine code, sections,
symbols and fixup payload semantics") appears violated by a release bump. The
only exits are to re-record — which destroys the answer to the one question the
baseline exists to answer — or to stop checking. `research/he1/baseline.md`
already claimed that build metadata is not part of the frozen content, so the
tool contradicted its own document.

Two further failures were found while fixing that one:

1. **The planned implementation identity could not distinguish builds.** The H1
   plan proposed `env!("CARGO_PKG_NAME")` and `env!("CARGO_PKG_VERSION")` in
   `fmp-model`. Those expand to `fmp-model` and the workspace version, which is
   `0.0.0` (`prototype/Cargo.toml`). Two different commits would produce byte-
   identical "implementation identities". That does not satisfy `HE-T20`.
2. **The H0 evidence classification was wrong.** `H0-report.md` said five of the
   six characterization tests document a hole. The file actually holds four gap
   tests, one digest-mismatch control and one non-object-root control; the deep
   JSON finding comes from the Python probe, not from a Rust test.

## Decision

1. **Three layers, each with its own versioned projection name.** They answer
   three different questions, so they cannot share one digest.
   - `payload/0.1` — the artifact with `materializer_version` removed: `bytes_hex`
     or `sections`, `symbols`, `fixups`, `fingerprint`, `level`, `size`,
     `format_version`. **This is the gate.** Counterexample if it were missing: a
     fixup record changes its target or addend while the bytes stay put, and a
     "did anything move?" check that hashed only `bytes_hex` would pass.
   - `envelope/0.1` — the whole artifact object, `materializer_version` included.
     Recorded, and compared only when the two implementations name the same
     receipt. Counterexample if it were the gate: the release bump above.
   - `implementation` — `{name, version, binary_sha256}`. Recorded, never
     compared. Counterexample if it were compared: no two builds, and therefore
     no two hosts, could ever be compared at all.
2. **The snapshot schema is `monasm.he1.baseline/0.2`, and `--check` refuses what
   it does not know.** An unknown schema exits 2 with an explanation instead of
   comparing a subset of fields. A check that silently compares less is worse
   than a check that fails.
3. **The old snapshot is kept as frozen evidence, not overwritten.**
   `research/he1/compatibility-h0-envelope.json` is the H0 file moved by
   `git mv`, bytes unchanged, schema `monasm.he1.baseline/0.1`. The new
   `research/he1/compatibility-results.json` is the gate. The link between them
   is measured: the new `envelope_root`
   `sha256:dfd08fee9844058492138b23448073ec47d8eda42383e3f1b3e567db86a86fef`
   equals the old `artifact_root` exactly. So the split moved no meaning, and the
   new gate value is `payload_root`
   `sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`.
4. **Probes are opt-in and bounded.** `--probes` runs them; without it they do
   not run, and `probes` is recorded but never compared. Every subprocess has a
   timeout, and a timeout is recorded as `outcome: "timeout"` rather than raised.
   One probe feeds a 20 000-deep JSON document to a reader that overflows its
   stack (`0xC00000FD`), so a routine regression run must not trigger it.
5. **The binary is found portably.** `--binary` wins; otherwise
   `prototype/target/debug/fmp.exe` (Windows) then `prototype/target/debug/fmp`
   (Linux, macOS); if neither exists the tool prints the build command and exits
   2. No host is a special case in the code.
6. **The payload comparison is a hosted job.** `gates.yml` gains `baseline`
   (Ubuntu 24.04): install the pinned toolchain, `cargo +1.96.0 build --bin fmp
   -p fmp-cli`, then `python tools/he1_baseline.py --check
   research/he1/compatibility-results.json --binary
   prototype/target/debug/fmp`. This revises `ADR-0124` decision 1, which
   enumerated three jobs, and `ADR-0125`'s statement that adding CI jobs waits
   for `ADR-0130`. The job compares payloads only; the envelope is skipped with
   a printed reason because the CI binary digest differs from the recorder's.
   That limitation is stated in the workflow comment, not hidden.
7. **`determinism.rs` keeps its pinned digests, and they stay envelope digests.**
   Three fixtures keep the strictest available cross-host check, including
   `materializer_version`. The consequence is a procedure, recorded here so it is
   not rediscovered as a bug: a change to `materializer_version` moves all three
   constants and every recorded `envelope_sha256` in the same commit, and
   `payload_root` must not move. A commit that moves `payload_root` is a payload
   change and needs its own compatibility statement.

## Consequences

- `ADR-0125`'s consequence bullet records `artifact_root`. That value is now the
  **envelope** root of the frozen H0 snapshot; the gate value is `payload_root`.
  Nothing in `fmp/0.1`, `definitions/` or `fixtures/` changes.
- The H1 `artifact_digest` must be the **payload** digest, using the same
  projection and its own version name. `ADR-0127` inherits that constraint; the
  H1 plan states it and no longer proposes `canonical_digest(artifact.to_json())`.
- A release bump is now a one-commit operation with a verifiable property: the
  payload root is unchanged, so the bump is provably not an encoding change.
- `H0-report.md` and the characterization-test module comment are corrected to
  4 gaps + 2 controls, and the deep-JSON row now names the Python probe as its
  source.
- The hosted `baseline` job gives Linux evidence for the 128-payload comparison.
  Before this ADR, the only such evidence was one Windows host, and "the Rust
  suite is green on three hosts" was a different claim.
- `tools/he1_baseline.py` is no longer a development-only habit: it is a gate,
  so its failure modes are part of the contract. Exit 1 is a difference, exit 2
  is a usage or I/O fault or an unknown schema.

## Alternatives rejected

- **Keep one digest and re-record on every version bump.** Rejected: the
  baseline would no longer be able to answer whether an encoding changed, which
  is its only purpose.
- **Hash only `bytes_hex`.** Rejected: sections, symbols and fixup records are
  part of `HE-AC-10` and would stop being covered.
- **Always compare the envelope.** Rejected: that is the defect this ADR
  corrects, and it makes the gate fail for a correct release.
- **Drop the envelope entirely.** Rejected: three cross-host fixtures keep a
  strict pin through `determinism.rs`; deleting the layer would remove the only
  place where the receipt-bearing projection is checked.
- **Keep the probes on by default and ignore their result.** Rejected: this is
  what H0 did — every routine run triggered a known stack overflow and waited on
  a potentially hanging child.
- **Take the implementation identity from `fmp-model`'s build variables.**
  Rejected: workspace version `0.0.0`, and the name would be the model crate, not
  the materializer.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `materializer_version` is inside the hashed artifact | read `fmp-materialize/src/lib.rs:118`, `:136`, and the H0 `artifact_sha256` line | high |
| The split preserved the old meaning | new `envelope_root` equals old `artifact_root`, `sha256:dfd08fee…a86fef` | high |
| The gate catches a payload change | tampered `payload_sha256` → exit 1; tampered `payload.bytes_hex` → exit 1 | high (measured, this host) |
| The gate catches a structural change | one entry removed → `artifacts/entries: length 127 -> 128`, exit 1; `corpus.negatives` 618 → exit 1 | high (measured) |
| A version bump does not fail the gate | `implementation` replaced with `fmp-materialize/9.9.9` → `OK: payload projection identical`, envelope skipped, exit 0 | high (measured) |
| The envelope still participates when the receipt matches | tampered `envelope.sha256` with an identical receipt → exit 1 | high (measured) |
| Skipping the envelope does not skip the payload | `implementation` replaced **and** `payload.bytes_hex` tampered → exit 1 | high (measured) |
| An unknown schema is refused | schema `…/0.1` → exit 2, no comparison | high (measured) |
| Portable discovery and probe opt-in work | `--binary` exercised; probe run under `--probes` only | high (Windows); `unverified` on Linux/macOS until the `baseline` job runs |
| `determinism.rs` pins envelope digests | read `tests/determinism.rs:158`, `:163`, `:168`; the test hashes `artifact.to_json()` at `:63` | high |
| The CI job passes | not yet run | `unverified` |

The first draft of the split contained its own version of the defect it was
fixing: when the implementation receipts differed, the comparison filtered diffs
by path prefix and dropped **every** per-entry difference, not only the envelope
digest. The `implementation` + `payload` control above is what caught it. It is
recorded here because the failure mode — a filter that is correct at the top
level and too broad one level down — is easy to reintroduce.

## Review triggers

- Someone wants to compare the envelope across implementations: stop. That
  re-couples build identity to payload identity and needs a new ADR.
- `materializer_version` changes: follow decision 7 in one commit, re-pin the
  three `determinism.rs` constants, re-record the envelope, and confirm
  `payload_root` did not move.
- A member is added to the artifact envelope: classify it as payload or receipt
  first. There is no third answer, and an unclassified member silently joins
  the payload projection.
- The `baseline` job starts passing while ignoring the envelope: check that it
  printed `envelope: not compared` or `envelope: identical`. A silent skip is a
  gate hole.
