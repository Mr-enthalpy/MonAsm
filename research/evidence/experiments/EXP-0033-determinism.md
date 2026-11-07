# EXP-0033 — Deterministic replay: `EXP-R1`, `EXP-R2`, `EXP-R3`, `EXP-R4`, `EXP-R5`, `EXP-R6`

- Date: 2026-11-05
- Questions: does the same plan yield the same artifact across repetitions, across
  processes, across serialization, and across a perturbed definition; and does an
  invalid plan keep one diagnostic identity?
- Toolchain: Rust 1.96.0. The primary host is Windows
  (`x86_64-pc-windows-msvc`); §6 adds Ubuntu, macOS arm64 and a second Windows
  host for `EXP-R3`.
- Test: `prototype/crates/fmp-cli/tests/determinism.rs`
- Command: `cargo test -p fmp-cli --test determinism`
- Corpus: 38 positive and 99 negative fixtures at the time of the run
  (x86 9/30, AArch64 20/57, RV64 9/12).

The unit of comparison is the artifact's canonical JSON — `bytes_hex`, `size`,
`fixups`, `fingerprint` and `materializer_version` — not a formatted printout. A
diagnostic comparison uses `Diagnostic::identity()`: `(code, path,
sorted detail keys)`. Free-text messages are excluded, as `01_contract.md` §12
requires.

## 1. `EXP-R1` — repeated execution

Each positive fixture is materialized 100 times in one process. Run 0's
canonical artifact bytes are the reference; every later run must equal it.

Result: **38 fixtures × 100 runs, all equal.** No counter or time source enters
the artifact; `fixups` are collected from the plan in `fixup_record_order` order,
not from a set.

## 2. `EXP-R2` — independent processes

Three plans are run through the CLI in four separate processes each:

| ISA | Fixture |
|---|---|
| x86 | `X86-P9-sse-vex-evex` |
| AArch64 | `A64-P14-cmp-cmn-family` |
| RV64 | `RV-P8-pcrel-pair` |

The CLI is `prototype/target/debug/fmp.exe materialize <plan> --definitions
definitions`. Each process exits 0, its stdout is parsed, canonicalized and
compared with the in-process artifact.

Result: **12 process runs, all equal to the in-process artifact.** The CLI writes
nothing to stdout on rejection, so this comparison cannot see a partial artifact.

Reference for the x86 case, measured with this build:

```text
fingerprint      sha256:5e6bc559fc0356ef325018ffcc7e0a2a7c0cfb42bf3fd2c79420ccd177880a37
canonical sha256 da97dcaad805b973984a92d2ffb933a82a407b1a4cc9a1aa87bfc8a9c715c660
bytes            13
records          0
```

## 3. `EXP-R4` — serialization replay

Each positive fixture is parsed, written as canonical JSON and re-parsed, then
materialized; the same is done with the pretty form. The canonical artifact must
equal the artifact from the original bytes, and the canonical re-parse must have
the same document digest.

Result: **38 fixtures × 2 serializations, all equal.** This is also the
measurement behind the wire-form decision (`OD-08`): a plan is a JSON document
whose logical value is what the materializer reads, and canonical JSON is the
one serialization used for hashing and replay. Requiring canonical bytes on
input would add a failure mode that changes no byte.

## 4. `EXP-R5` — definition perturbation

Two copies of `definitions/` are written under `prototype/target/`, and one copy
of `definitions/x86_64/0.5.0.json` is edited in each:

1. **Rule change, same version.** The last hex digit of the first form's
   `template` is flipped. The table still loads; the plan
   `X86-P9-sse-vex-evex` still names `monasm.isa.x86/0.5.0`. Result:
   **`E-DEF-001` at `/definition_identity/digest`, one diagnostic, no bytes.**
2. **Version move.** The table's `version` becomes `0.5.0-perturbed`. Result:
   **`E-DEF-002` at `/definition_identity`, one diagnostic.** No near-match is
   offered.

Result: both perturbations are loud, and neither emits an artifact. This is the
same gate `N10` exercises with a hand-edited digest.

## 5. `EXP-R6` — negative determinism

Every negative fixture is executed 100 times, using its declared `phase`: a
read-phase plan is rejected by `plan::read`, a materialize-phase plan by
`fmp_materialize::materialize`. The complete sorted identity list must match run
0.

Result: **99 fixtures × 100 runs, all identities equal.** Multi-diagnostic
fixtures (`N02f`, `N02g`, `N02h`, `N02l`, `N14`, `N14b`) keep both entries and
their order, because diagnostics are sorted by `(path, code)`.

## 6. `EXP-R3` — second host (GitHub Actions)

Run [`42402997326`](https://github.com/Mr-enthalpy/MonAsm/actions/runs/42402997326)
triggered 2026-11-07 18:47 UTC (2026-11-08 local), by
`.github/workflows/determinism.yml`. The workflow installs the same pinned
`rustc`/`cargo` 1.96.0 (`ac68faa20 2026-05-25`) as the primary host and runs
`cargo test --workspace` from `prototype/` on three hosts:

| Host | Image | Target | Result |
|---|---|---|---|
| Ubuntu 24.04.5 LTS | `ubuntu-24.04` 20261101.360 | `x86_64-unknown-linux-gnu` | all tests pass |
| macOS 26.7.2 (25G332) | `macos-26-arm64` 20261102.0473 | `aarch64-apple-darwin` | all tests pass |
| Windows Server 2025 (10.0.26100) | `windows-2025-vs2026` 20261103.298 | `x86_64-pc-windows-msvc` | all tests pass |

Every host passed 6 determinism tests, 2 fixture tests (100 positives, 530
negatives), 5 `fmp-materialize` unit tests and 16 `fmp-model` unit tests. The
new `exp_r3_artifact_digests_match_the_recorded_values` compares the canonical
artifact digest of one plan per ISA against the value recorded on the primary
host:

| ISA | Fixture | Canonical artifact digest |
|---|---|---|
| x86-64 | `X86-P9-sse-vex-evex` | `sha256:da97dcaad805b973984a92d2ffb933a82a407b1a4cc9a1aa87bfc8a9c715c660` |
| AArch64 | `A64-P14-cmp-cmn-family` | `sha256:638e769fb8fe17ab3ed6d2259d1eab3f503ca9b25ca2133745076e7f64bf5a65` |
| RV64 | `RV-P8-pcrel-pair` | `sha256:19bae975204dbe62ff46cf11a2fd70114356ff9656687c8fefc1aa459d032f7c` |

The same values passed on the primary Windows host and on all three CI hosts.
`positives_reproduce_the_oracle_bytes` also compared all 100 positives to the
recorded `expected.bin` bytes on each host, so byte equality is anchored to the
oracle rather than to any one run; the arm64 macOS host additionally covers a
second CPU architecture. **`EXP-R3` is `passing` for the four hosts above.**
It is not claimed for an untested host.

The run log warns that the `ubuntu-latest` label migrates to Ubuntu 26 after
2026-10-19; this run used the `ubuntu-24.04` image named above, and the workflow
pins the toolchain rather than the image. A later image is a new observation.

## 7. Re-run after `X86-P10` … `X86-P48`

The same suite was re-run on 2026-11-05 after `0.6.0` and the `r8`–`r15`
fixtures landed, again after `0.7.0` and `X86-P11`, a third time after
`0.8.0` and `X86-P12`, a fourth time after `0.9.0` and `X86-P13`, a fifth
time after `0.10.0` and `X86-P14`, a sixth time after `0.11.0` and
`X86-P15`, a seventh time after `0.12.0` and `X86-P16`, an eighth time
after `0.13.0` and `X86-P17`, a ninth time after `0.14.0` and `X86-P18`, a
tenth time after `0.15.0` and `X86-P19`, an eleventh time after `0.16.0`
`X86-P20`, a twelfth time after `0.17.0` and `X86-P21`, a thirteenth time
after `0.18.0` and `X86-P22`, a fourteenth time on 2026-11-06 after
`0.19.0` and `X86-P23`, a fifteenth time on 2026-11-06 after `0.20.0` and
`X86-P24`, a sixteenth time on 2026-11-06 after `0.21.0` and `X86-P25`, a
seventeenth time on 2026-11-06 after `0.22.0` and `X86-P26`, an eighteenth
time on 2026-11-06 after `0.23.0` and `X86-P27`, a nineteenth time on
2026-11-06 after `0.24.0` and `X86-P28`, a twentieth time on 2026-11-06
after `0.25.0` and `X86-P29`, and a twenty-first time on 2026-11-06 after
`0.26.0` and `X86-P30`, and a twenty-second time on 2026-11-06 after
`0.27.0` and `X86-P31`, and a twenty-third time on 2026-11-06 after
`0.28.0` and `X86-P32`, a twenty-fourth time on 2026-11-06 after
`0.29.0` and `X86-P33`, a twenty-fifth time on 2026-11-06 after
`0.30.0` and `X86-P34`, and a twenty-sixth time on 2026-11-06 after
`0.31.0` and `X86-P35`, and a twenty-seventh time on 2026-11-07 after
`0.32.0` and `X86-P36`, and a twenty-eighth time on 2026-11-07 after
`0.33.0` and `X86-P37`, and a twenty-ninth time on 2026-11-07 after
`0.34.0` and `X86-P38`, and a thirtieth time on 2026-11-07 after
`0.35.0` and `X86-P39`, a thirty-first time on 2026-11-07 after
`0.36.0` and `X86-P40`, and a thirty-second time on 2026-11-07 after
`0.37.0` and `X86-P41`, and a thirty-third time on 2026-11-07 after
`0.38.0` and `X86-P42`, and a thirty-fourth time on 2026-11-07 after
`0.39.0` and `X86-P43`, and a thirty-fifth time on 2026-11-07 after
`0.40.0` and `X86-P44`, and a thirty-sixth time on 2026-11-07 after
`0.41.0` and `X86-P45`, and a thirty-seventh time on 2026-11-07 after
`0.42.0` and `X86-P46`, and a thirty-eighth time on 2026-11-07 after
`0.43.0` and `X86-P47`, and a thirty-ninth time on 2026-11-07 after
`0.44.0` and `X86-P48`, and a fortieth time on 2026-11-07 after
`0.45.0` and `X86-P49`, and a forty-first time on 2026-11-07 after
`0.46.0` and `X86-P50`, and a forty-second time on 2026-11-07 after
`0.47.0` and `X86-P51`, and a forty-third time on 2026-11-07 after
`0.48.0` and `X86-P52`, and a forty-fourth time on 2026-11-07 after
`0.49.0` and `X86-P53`, and a forty-fifth time on 2026-11-07 after
`0.50.0` and `X86-P54`, and a forty-sixth time on 2026-11-07 after
`0.51.0` and `X86-P55`, a forty-seventh time on 2026-11-07 after
`0.52.0` and `X86-P56`, a forty-eighth time on 2026-11-07 after
`0.53.0` and `X86-P57`, and a forty-ninth time on 2026-11-07 after
`0.54.0` and `X86-P58`, a fiftieth time on 2026-11-07 after `0.55.0` and
`X86-P59`, and a fifty-first time on 2026-11-07 after `0.56.0` and
`X86-P60`, and a fifty-second time on 2026-11-07 after `0.57.0` and
`X86-P61`, and a fifty-third time on 2026-11-08 after `0.58.0` and `X86-P62`,
and a fifty-fourth time on 2026-11-08 after `0.59.0` and `X86-P63`, and a
fifty-fifth time on 2026-11-08 after `0.60.0` and `X86-P64`, a
fifty-sixth time on 2026-11-08 after `0.61.0` and `X86-P65`, a
fifty-seventh time on 2026-11-08 after `0.62.0` and `X86-P66`, a
fifty-eighth time on 2026-11-08 after `0.63.0` and `X86-P67`, a
fifty-ninth time on 2026-11-08 after `0.64.0` and `X86-P68`, and a
sixtieth time on 2026-11-08 after `0.65.0` and `X86-P69`, and a
sixty-first time on 2026-11-08 after `X86-P70` (no definition change), and a
sixty-second time on 2026-11-08 after the six `N22` layout fixtures (no
definition change).
The corpus is now
**100 positive and 536 negative** fixtures (x86 71/467, AArch64 20/57, RV64 9/12).
Result: all five same-host tests still pass, with the same method (`EXP-R1`
100 × 100, `EXP-R2` 12 processes, `EXP-R4` 100 × 2, `EXP-R5` unchanged,
`EXP-R6` 536 × 100). The counts in §1–§5 are the original run's; this section
records the current corpus instead of rewriting them. `EXP-R3` is the cross-host
half and is recorded in §6, not in this same-host re-run.
