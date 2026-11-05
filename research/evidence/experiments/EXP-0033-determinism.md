# EXP-0033 — Deterministic replay: `EXP-R1`, `EXP-R2`, `EXP-R4`, `EXP-R5`, `EXP-R6`

- Date: 2026-11-05
- Questions: does the same plan yield the same artifact across repetitions, across
  processes, across serialization, and across a perturbed definition; and does an
  invalid plan keep one diagnostic identity?
- Toolchain: Rust 1.96.0 (`stable-x86_64-pc-windows-msvc`), one Windows host.
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

## 6. Not run — `EXP-R3`

`EXP-R3` asks for a second OS, compiler build or host CPU. Only one Windows host
is available: WSL has no distribution installed and no second machine was used.
**Cross-platform determinism is `unverified`.** This record does not turn a
same-host result into a cross-host claim.

## 7. Re-run after `X86-P10` … `X86-P24`

The same suite was re-run on 2026-11-05 after `0.6.0` and the `r8`–`r15`
fixtures landed, again after `0.7.0` and `X86-P11`, a third time after
`0.8.0` and `X86-P12`, a fourth time after `0.9.0` and `X86-P13`, a fifth
time after `0.10.0` and `X86-P14`, a sixth time after `0.11.0` and
`X86-P15`, a seventh time after `0.12.0` and `X86-P16`, an eighth time
after `0.13.0` and `X86-P17`, a ninth time after `0.14.0` and `X86-P18`, a
tenth time after `0.15.0` and `X86-P19`, an eleventh time after `0.16.0`
`X86-P20`, a twelfth time after `0.17.0` and `X86-P21`, a thirteenth time
after `0.18.0` and `X86-P22`, a fourteenth time on 2026-11-06 after
`0.19.0` and `X86-P23`, and a fifteenth time on 2026-11-06 after `0.20.0` and
`X86-P24`.
The corpus is now
**53 positive and 175 negative** fixtures (x86 24/106, AArch64 20/57, RV64 9/12).
Result: all five tests still pass, with the same method (`EXP-R1` 53 × 100,
`EXP-R2` 12 processes, `EXP-R4` 53 × 2, `EXP-R5` unchanged, `EXP-R6` 175 × 100). The counts in §1–§5 are the original
run's; this section records the current corpus instead of rewriting them.
