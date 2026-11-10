# HE-1 baseline (H0)

Recorded: 2026-11-10
Original baseline commit: `d0082f9f2d3da2786d8d1c0467d2793369ec9090` (`main`, clean tree)
Projection recording commit: `ebddbdb02c558baff9c44d90bbdead3e3db96175` (dirty tree)
Host: Windows Server 2025, `cargo 1.96.0 (30a34c682 2026-05-25)`, Python 3.8.10
Machine-readable snapshot: `research/he1/compatibility-results.json`
Frozen H0 snapshot: `research/he1/compatibility-h0-envelope.json`

The two commits are different facts and are named separately. The artifacts were
first recorded at `d0082f9`; the payload/envelope projection
(`ADR-0126`) was written later, while the tree was still dirty, so its
`provenance.projection_recording_commit` is the then-current
`ebddbdb`. Neither commit changes what was measured: both recordings print the
same `payload_root`, which is the property that matters.

This file is evidence, not a contract. The contract for "unchanged" is the JSON
snapshot; this text explains what it covers and what it does not.

`ADR-0126` split the artifact identity into a payload projection and an envelope
projection, because the first H0 recording hashed the whole artifact — including
`materializer_version` — and would therefore have reported a release bump as an
encoding change. The old file is kept byte-identical under the second name above,
so the H0 record itself is not rewritten.

## 1. What was captured

| Item | Count | Recorded as |
|---|---|---|
| Definition documents | 104 | `definitions.documents[]`: path, file SHA-256, namespace, version, format, ISA, form count, canonical digest |
| Newest document per ISA | 3 | `definitions.newest`: x86-64 `0.78.0`, AArch64 `0.20.0`, RV64 `0.6.0` |
| Positive fixtures | 128 | `artifacts.entries[]`: plan SHA-256, declared definition identity, full payload JSON, payload and envelope digests |
| Negative fixtures | 619 | `corpus.negatives` and `corpus.by_isa` |
| Oracle records | 128 | `oracle.kinds`: `assembler` 122, `manual+disassembly` 6 |
| Payload total | 1 digest | `artifacts.payload_root` — **the gate** |
| Envelope total | 1 digest | `artifacts.envelope_root` — a receipt for the recording build |

Per ISA:

| ISA | Positives | Negatives |
|---|---|---|
| x86-64 | 85 | 527 |
| AArch64 | 26 | 69 |
| RV64 | 17 | 23 |

Level split of the 128 positive artifacts: 127 at Level 0 (`bytes_hex`), 1 at
Level 1 (`X86-P71`, sections and symbols). The entry keeps the whole payload
object, so a change to sections, symbols, fixup records or `fingerprint` is
visible, not only a change to the bytes.

The two roots, both the SHA-256 of `fixture path \0 digest` over the sorted 128
entries:

| Root | Value |
|---|---|
| `payload_root` (artifact minus `materializer_version`) | `sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9` |
| `envelope_root` (whole artifact) | `sha256:dfd08fee9844058492138b23448073ec47d8eda42383e3f1b3e567db86a86fef` |

The second value is exactly the `artifact_root` recorded by the first H0
snapshot. That equality is the check that the projection change moved no meaning.

## 2. What "unchanged" means for later phases

Frozen by this baseline, for the legacy path:

1. The **payload** of every positive fixture: `bytes_hex` or `sections`,
   `symbols` when present, `fixups` in `fixup_record_order`, `size`, `level`,
   `fingerprint`, `format_version`. This is what `--check` compares.
2. Every definition document's file bytes and canonical digest. No phase
   rewrites a file under `definitions/`.
3. The legacy corpus counts and the negative phase split (`611` materialize,
   `8` read), which `planner_api.rs` asserts.
4. The oracle result: `122/128` re-derived, 6 `manual-derivation` skips, 0
   failures. The six are `X86-P1`, `X86-P4`, `X86-P5`, `X86-P9`, `X86-P10`,
   `X86-P83`; the tool computes them from `kind = manual+disassembly` in the
   record, so a seventh such record changes the count and must be registered.

Receipts, recorded but not frozen: `materializer_version`, `implementation`
(`name`, `version`, `binary_sha256`), `toolchain` and `provenance`. `--check`
never compares `implementation`, `toolchain`, `provenance` or `probes`. It
compares the envelope only when both sides name the same `implementation`,
because the envelope carries the build identity; the payload is compared
unconditionally.

`provenance` has three fields so that a recording is never mistaken for its
source: `original_baseline_commit` is the frozen H0 commit the artifacts were
first measured at (`d0082f9`, read from `compatibility-h0-envelope.json`, not
remembered by hand); `projection_recording_commit` is HEAD when this projection
was written (`ebddbdb`); `projection_recording_worktree` is `clean` or `dirty`.
They differ because a projection is recorded before the commit that contains it.

The three pinned digests in `prototype/crates/fmp-cli/tests/determinism.rs` are
**envelope** digests and stay that way (`ADR-0126` decision 7): they are the
narrow, cross-host, strict pin. A change to `materializer_version` moves those
three constants and every recorded per-entry `envelope.sha256` in one commit;
`payload_root` must not move.

## 3. How to reproduce

```text
cargo +1.96.0 build --bin fmp -p fmp-cli --manifest-path prototype/Cargo.toml
python tools/he1_baseline.py --check research/he1/compatibility-results.json
python tools/he1_baseline.py --check research/he1/compatibility-results.json \
    --binary prototype/target/debug/fmp        # Linux, macOS
python tools/test_he1_baseline.py               # the comparator's own tests
python tools/he1_baseline.py --probes           # re-record, probes included
```

The build command names the workspace manifest because the repository root has
no `Cargo.toml`; without `--manifest-path` or a `cd prototype/`, the first line
fails. `CI` sets `working-directory: prototype` instead, which is the same build.

The tool re-runs the real `fmp` binary, not a Python re-implementation, so the
snapshot is the product's output. `--check` exits 1 on any difference in a
payload, a digest or a count, prints every difference, and exits 2 on a usage or
I/O fault, on a snapshot schema it does not know, or on a snapshot whose structure
is not the one the recorder writes (a JSON array or `null`, a missing
`artifacts`, an entry without `payload_sha256`, a wrongly typed `implementation`).
**A fault never exits 1**: otherwise a missing binary or a corrupt snapshot would
look exactly like a real payload regression. Re-recording is
`python tools/he1_baseline.py` (writes the same file); without `--probes` the
`probes` array is written empty.

`tools/test_he1_baseline.py` is the comparator's own gate: 24 tests over
synthetic snapshots, no Rust binary and no `definitions/` scan. It fixes the
properties that would otherwise be re-learned in production: a payload change
fails, a count change fails, a receipt change alone passes, **a receipt change
does not stop the payload from being compared**, and a structurally invalid
snapshot is refused with exit 2 before the 128 materializations. The receipt bug
was the first draft of `ADR-0126`'s split; the structural check was the third
review round. CI runs the suite before building `fmp`.

`--binary` wins over discovery; discovery tries `prototype/target/debug/fmp.exe`
then `prototype/target/debug/fmp`. If neither exists the tool prints the build
command and exits 2 — no host is a special case.

`tools/he1_baseline.py` is a development tool: the product build never reads it.
Since `ADR-0126` it is also a hosted gate (`baseline` in `gates.yml`), which
builds the binary on Ubuntu and runs `--check` there. That job compares payloads
only: its binary digest differs from the recorder's, so the envelope is skipped
with a printed reason.

## 4. Probes

Probes are opt-in (`--probes`) and never compared. Every subprocess has a
timeout, and a timeout is recorded as `outcome: "timeout"` rather than raised.

| Probe | Input | Observed | Reading |
|---|---|---|---|
| `deep-json` | 20 000 nested arrays | exit `3221225725` (`0xC00000FD`), stderr `thread 'main' has overflowed its stack` | The JSON reader has no depth bound. **Measured gap** for `HE-T13`; H4 owes a bounded rejection. |
| `unknown-field-1mib` | a valid positive plus one 1 MiB unknown member | exit 1, `E-PLAN-003` naming the field | The closed-object rule holds at size; no payload leak. |

The first probe is why they are not on by default: a routine regression run
should not trigger a known stack overflow or wait on a child that may hang.

## 5. Limits of this baseline

- Captured on one host, and replayed on a second one. Hosted `gates` run
  `42714224361` (job `H0 payload baseline`) built `fmp` on Ubuntu 24.04 and
  printed the same `payload_root`, so all 128 payloads were compared there and
  matched. Its `binary_sha256` differs from the recorder's, so the envelope was
  skipped with a printed reason — which is the designed behaviour, not a silent
  pass. Three hosts also run `cargo test --workspace` (run `42698924288`), but
  that is the Rust suite: it pins **three** envelope digests cross-host
  (`determinism.rs`), not the 128-payload comparison.
- The 8 negative comparator experiments in `ADR-0126` were manual. They are now
  `tools/test_he1_baseline.py`, including the one the first manual pass missed
  (implementation receipt differs **and** the payload still changes → fail).
  Manual experiments are kept in `ADR-0126` as the record; the tests are the
  gate.
- The comparator test proves the *comparator* does not silently skip. It cannot
  prove the snapshot covers a fact the tool never reads. Coverage of the payload
  is bounded by `artifact_entry()`'s projection, which is the whole artifact
  minus `materializer_version`.
- The `deep-json` probe is recorded on Windows and reads `0xC00000FD`. Linux and
  macOS report the same fault with a different exit status or a signal; the probe
  records the outcome, not a portable code, and `--check` never compares probes.
- The binary is a debug build. Release-vs-debug payload equality was not
  measured in H0; `EXP-R1`–`R6` cover repeat-run determinism, not profile
  equality. The build also has `FMP_BUILD_ID = None`, so the implementation
  receipt cannot yet trace a hosted artifact back to a build; both are H1
  acceptance caveats, not H0 passes.
- The snapshot proves the legacy payloads did not move. It does not prove they
  are correct; correctness remains with the two-source oracle gate.
- Local Python is 3.8.10; the `baseline` job runs the tool on 3.12, so its CI
  behaviour is measured there rather than here.
