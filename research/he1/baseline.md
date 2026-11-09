# HE-1 baseline (H0)

Recorded: 2026-11-10
Commit: `d0082f9f2d3da2786d8d1c0467d2793369ec9090` (`main`, clean tree)
Host: Windows Server 2025, `cargo 1.96.0 (30a34c682 2026-05-25)`, Python 3.8.10
Machine-readable snapshot: `research/he1/compatibility-results.json`
Frozen H0 snapshot: `research/he1/compatibility-h0-envelope.json`

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
(`name`, `version`, `binary_sha256`), `toolchain` and `head`. `--check` never
compares `implementation`, `toolchain`, `head` or `probes`. It compares the
envelope only when both sides name the same `implementation`, because the
envelope carries the build identity; the payload is compared unconditionally.
The recorded `head` stays `d0082f9` — the commit the snapshot was measured at.

The three pinned digests in `prototype/crates/fmp-cli/tests/determinism.rs` are
**envelope** digests and stay that way (`ADR-0126` decision 7): they are the
narrow, cross-host, strict pin. A change to `materializer_version` moves those
three constants and every recorded per-entry `envelope.sha256` in one commit;
`payload_root` must not move.

## 3. How to reproduce

```text
cargo +1.96.0 build --bin fmp -p fmp-cli
python tools/he1_baseline.py --check research/he1/compatibility-results.json
python tools/he1_baseline.py --check research/he1/compatibility-results.json \
    --binary prototype/target/debug/fmp        # Linux, macOS
python tools/he1_baseline.py --probes           # re-record, probes included
```

The tool re-runs the real `fmp` binary, not a Python re-implementation, so the
snapshot is the product's output. `--check` exits 1 on any difference in a
payload, a digest or a count, prints every difference, and exits 2 on a usage or
I/O fault or on a snapshot schema it does not know. Re-recording is
`python tools/he1_baseline.py` (writes the same file); without `--probes` the
`probes` array is written empty.

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

- Captured on one host, and now replayed on a second one. Hosted `gates` run
  `42714224361` (job `H0 payload baseline`) built `fmp` on Ubuntu 24.04 and
  printed the same `payload_root`, so all 128 payloads were compared there and
  matched. Its `binary_sha256` differs from the recorder's, so the envelope was
  skipped with a printed reason — which is the designed behaviour, not a silent
  pass. Three hosts also run `cargo test --workspace` (run `42698924288`), but
  that is the Rust suite: it pins **three** envelope digests cross-host
  (`determinism.rs`), not the 128-payload comparison.
- The binary is a debug build. Release-vs-debug payload equality was not
  measured in H0; `EXP-R1`–`R6` cover repeat-run determinism, not profile
  equality.
- The snapshot proves the legacy payloads did not move. It does not prove they
  are correct; correctness remains with the two-source oracle gate.
- Local Python is 3.8.10; the `baseline` job runs the tool on 3.12, so its CI
  behaviour is measured there rather than here.
