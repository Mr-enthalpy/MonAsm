# ADR-0003: Rust prototype, Level 0/1 output

- Status: accepted (provisional)
- Date: 2026-11-03
- Supersedes: none
- Superseded by: none

## Context

The prototype must encode three ISAs, compare bytes against an oracle, and repeat
identically across processes. It also has to be pleasant to audit: a reviewer
should be able to see that no choice is made inside the encoder.

Candidate languages:

- **Rust** — installed (1.96.0), strong typing for bit-field and register-class
  invariants, deterministic collections available, good FFI story for calling
  oracles, cheap cross-compilation.
- **Zig** — required to link `xirasm-lib` directly, but pins us to an unstable
  0.17 toolchain and to the library we have decided not to depend on.
- **Python** — fastest to write, but weak typing for the exact classes of bug
  this project cares about (width, sign, range, bit placement).

Output level: the directive (§5.3) prefers Level 0 or Level 1 for v0; Level 2
object files add ordering and padding policy that must itself be frozen.

## Decision

1. The prototype is a Rust workspace: `fmp-model`, `fmp-validate`,
   `fmp-materialize`, `fmp-cli`.
2. Materializer crates use `#![forbid(unsafe_code)]` and deterministic data
   structures: no `HashMap` in any path that affects output or diagnostics;
   ordered maps and explicit sorting only.
3. v0 targets **Level 0** (bytes plus normalized fixup records) and **Level 1**
   (laid-out section images, symbol table, relocation records) where a slice
   needs symbols to be meaningful. Level 2 is out of scope for v0.
4. Toolchain pinning and a reproducible build profile are deferred to Phase 3,
   when the first vector exists; the pin must be recorded in
   `research/evidence/source_index.md` and in `EXP-R3`.

## Consequences

- No dependency on Zig or XirAsm in the product path. The audit still builds
  XirAsm separately under `research/external/`.
- Rust forces us to model operand kinds explicitly, which matches the contract's
  refusal to have one universal operand type.
- Level 0/1 keeps the object-format policy question out of v0, at the cost of
  deferring ELF/COFF/Mach-O ordering questions to a later ADR.

## Alternatives considered

- Zig prototype: rejected for v0 because the toolchain is unstable and it
  invites accidental coupling to `xirasm-lib`.
- Python prototype: rejected for the core; acceptable for `tools/oracle/`
  scripts and `tools/check_ids.py`.

## Review triggers

Revisit after Phase 1, or if a slice cannot be expressed at Level 1 without
object-format ordering decisions.
