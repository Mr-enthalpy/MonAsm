# Prototype

Rust workspace for the materializer. **Empty by design** until Phase 3
(ADR-0003).

## Why nothing is here yet

The contract (`docs/fmp-v0/01_contract.md`) and the validation matrix decide the
data model. Writing types before that would bake in decisions the contract has
not made, and the first refactor would hide which fields were actually
load-bearing.

## When it starts

Phase 3, one vertical slice at a time:

```text
plan -> parse -> validate -> encode -> collect fixups -> compare oracle -> replay
```

## Constraints for every crate

- `#![forbid(unsafe_code)]`.
- No `HashMap` in any path that affects bytes or diagnostics.
- No dependency on XirAsm, LLVM, or any external assembler.
- The materializer MUST NOT contain code that picks among legal encodings; if a
  choice is missing, return a registry error.
