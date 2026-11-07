# Prototype

Rust workspace for the materializer, and (from M4) the planner-side plan builder.
It is no longer empty: the three vertical slices and the fixture gate are
implemented.

## Crates

| Crate | Role |
|---|---|
| `fmp-model` | Plan and definition model, strict binding (`plan.rs`, `bind.rs`, `definition.rs`), diagnostics and codes, canonical JSON and digests |
| `fmp-validate` | Static checks for steps 2–7 of `01_contract.md` §13: target, output gate, layout, symbols, instructions, operands and fixups |
| `fmp-materialize` | Digest check, `fmp_validate::check`, emission and fingerprint (`materialize`) |
| `fmp-cli` | The `fmp materialize <plan.json> --definitions <dir>` binary and the fixture/determinism tests |
| `fmp-plan` | Planner-side plan builder (`ADR-0097`, `docs/fmp-v0/09_planner_api.md`): a total, closed writer that depends only on `fmp-model` and has no validator |

The materializer path is:

```text
bytes -> fmp_model::plan::read -> fmp_materialize::materialize -> Artifact (bytes / sections + records)
```

`fmp-plan` sits on the other side of the boundary and writes the bytes that path
reads. It must never be linked by `fmp-validate`, `fmp-materialize` or the `fmp`
binary outside a test target.

## Tests

- `fmp-cli/tests/fixtures.rs` — every positive reproduces the oracle bytes (and,
  at Level 1, the recorded section/symbol envelope); every negative reproduces
  exactly the registered diagnostic set.
- `fmp-cli/tests/determinism.rs` — `EXP-R1`–`EXP-R6` replay and identity.
- `fmp-cli/tests/planner_api.rs` — M4 parity gate: 101 positive and 540
  `materialize`-phase negative fixtures rebuilt through `fmp-plan`, plus
  from-scratch, closed-key, optional-member, enum-spelling, structural-exclusion,
  fixed-point and determinism cases.

## Constraints for every crate

- `#![forbid(unsafe_code)]`.
- No `HashMap` in any path that affects bytes or diagnostics.
- No dependency on XirAsm, LLVM, or any external assembler.
- The materializer MUST NOT contain code that picks among legal encodings; if a
  choice is missing, return a registry error.
- The plan builder MUST NOT validate, default, reorder, lay out, encode or
  resolve; it serializes caller facts and the shipped reader/validator remain the
  only authority (`ADR-0097`).
