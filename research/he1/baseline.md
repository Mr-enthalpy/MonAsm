# HE-1 baseline (H0)

Recorded: 2026-11-10
Commit: `d0082f9f2d3da2786d8d1c0467d2793369ec9090` (`main`, clean tree)
Host: Windows Server 2025, `cargo 1.96.0 (30a34c682 2026-05-25)`, Python 3.8.10
Machine-readable snapshot: `research/he1/compatibility-results.json`

This file is evidence, not a contract. The contract for "unchanged" is the JSON
snapshot; this text explains what it covers and what it does not.

## 1. What was captured

| Item | Count | Recorded as |
|---|---|---|
| Definition documents | 104 | `definitions.documents[]`: path, file SHA-256, namespace, version, format, ISA, form count, canonical digest |
| Newest document per ISA | 3 | `definitions.newest`: x86-64 `0.78.0`, AArch64 `0.20.0`, RV64 `0.6.0` |
| Positive fixtures | 128 | `artifacts.entries[]`: plan SHA-256, declared definition identity, full artifact JSON |
| Negative fixtures | 619 | `corpus.negatives` and `corpus.by_isa` |
| Oracle records | 128 | `oracle.kinds`: `assembler` 122, `manual+disassembly` 6 |
| Artifact payload total | 1 digest | `artifacts.artifact_root` |

Per ISA:

| ISA | Positives | Negatives |
|---|---|---|
| x86-64 | 85 | 527 |
| AArch64 | 26 | 69 |
| RV64 | 17 | 23 |

Level split of the 128 positive artifacts: 127 at Level 0 (`bytes_hex`), 1 at
Level 1 (`X86-P71`, sections and symbols). The entry keeps the whole artifact
object, so a change to sections, symbols, fixup records or `fingerprint` is
visible, not only a change to the bytes.

`artifact_root` = `sha256:dfd08fee9844058492138b23448073ec47d8eda42383e3f1b3e567db86a86fef`,
the SHA-256 of `fixture path \0 artifact sha256` over the sorted 128 entries.

## 2. What "unchanged" means for later phases

Frozen by this baseline, for the legacy path:

1. Every artifact member for every positive fixture: `bytes_hex` or `sections`,
   `symbols` when present, `fixups` in `fixup_record_order`, `size`, `level`,
   `fingerprint`.
2. Every definition document's file bytes and canonical digest. No phase
   rewrites a file under `definitions/`.
3. The legacy corpus counts and the negative phase split (`611` materialize,
   `8` read), which `planner_api.rs` asserts.
4. The oracle result: `122/128` re-derived, 6 `manual-derivation` skips, 0
   failures. The six are `X86-P1`, `X86-P4`, `X86-P5`, `X86-P9`, `X86-P10`,
   `X86-P83`; the tool computes them from `kind = manual+disassembly` in the
   record, so a seventh such record changes the count and must be registered.

Not frozen: `materializer_version` and the binary identity. Those are build
receipts. `research/he1/compatibility-results.json` records them under
`toolchain`, and `--check` deliberately ignores `toolchain` and the recorded
`head` when comparing: later phases run at a different commit and a different
binary by design. The recorded `head` stays `d0082f9` — the commit the snapshot
was measured at — and H0 itself changes no product code.

## 3. How to reproduce

```text
cargo +1.96.0 build --bin fmp -p fmp-cli
python tools/he1_baseline.py --check research/he1/compatibility-results.json
```

The tool re-runs the real `fmp` binary, not a Python re-implementation, so the
snapshot is the product's output. `--check` exits 1 on any difference in a
payload, a digest or a count, and prints every difference. Re-recording is
`python tools/he1_baseline.py` (writes the same file).

`tools/he1_baseline.py` is a development tool: the product build never reads it,
and deleting it only loses the `--check` convenience, not the recorded evidence.

## 4. Probes

Two probes run the real binary on inputs outside the corpus. They are
observations; they are excluded from `--check` because a probe changing is a
finding to report, not a compatibility break.

| Probe | Input | Observed | Reading |
|---|---|---|---|
| `deep-json` | 20 000 nested arrays | exit `3221225725` (`0xC00000FD`), stderr `thread 'main' has overflowed its stack` | The JSON reader has no depth bound. **Measured gap** for `HE-T13`; H4 owes a bounded rejection. |
| `unknown-field-1mib` | a valid positive plus one 1 MiB unknown member | exit 1, `E-PLAN-003` naming the field | The closed-object rule holds at size; no payload leak. |

## 5. Limits of this baseline

- Captured on one host, but re-checked on three: hosted run `42698924288` ran
  `cargo test --workspace`, including the 128-artifact digest comparisons, on
  `ubuntu-latest`, `macos-latest` and `windows-latest`, all green. That is the
  `EXP-R3` second-host observation for this commit.
- The binary is a debug build. Release-vs-debug payload equality was not
  measured in H0; `EXP-R1`–`R6` cover repeat-run determinism, not profile
  equality.
- The snapshot proves the legacy payloads did not move. It does not prove they
  are correct; correctness remains with the two-source oracle gate.
- `tools/he1_baseline.py` is not in a CI job, so it has only been run under
  Python 3.8.10 (the CI interpreters run `check_ids.py` and
  `check_definition.py` on 3.12).
