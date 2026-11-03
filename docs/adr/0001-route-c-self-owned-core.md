# ADR-0001: Self-owned encoding core; external assemblers are temporary oracles

- Status: accepted
- Date: 2026-11-03
- Supersedes: none
- Superseded by: none

## Context

The research directive (`docs/fmp-v0/00_directive.md` §2, §13) asks for an
evidence-based comparison of three routes, with XirAsm-lib as a leading reuse
candidate. The project owner has stated the long-term intent: build an
independent implementation, tolerate short-term dependence on external
assemblers, but do not maintain that dependence.

A first read of XirAsm (commit `3ee8a439f5ba`) shows the reuse path is narrower
than the directive assumed:

- `deps/xirasm-lib` ships exactly three backends: x86, RISC-V, SPIR-V
  (`src/xirasm_backend.zig:3-5`). There is **no AArch64 encoder**.
- The library explicitly excludes symbol tables, labels, pseudo directives,
  layout, and object formats (`deps/xirasm-lib/README.md:12-19`), which is
  precisely the FMP fixup and layout surface.
- The RISC-V entry point is mnemonic-driven
  (`EncodeRequest{mnemonic, xlen, operands}`), with mnemonic-to-spec resolution
  happening inside the library tables — an implicit selection point the FMP is
  designed to eliminate.
- AArch64 encoding exists as generated XirAsm meta-DSL source
  (`include/arm/a64/generated/latest/source-bodies.inc`, ~6.9 MB) executed by the
  frontend's Meta VM, not as a callable API.

These are preliminary findings; Phase 1 must confirm runtime behavior. They are
sufficient to settle the *direction*, which is a separate question from the
audit.

## Decision

1. The product path is **Route C**: a self-owned validator plus a minimal
   deterministic encoding kernel driven by versioned target definitions.
2. XirAsm and LLVM are used only as (a) oracles for byte comparison, (b) sources
   of public encoding knowledge, (c) audit targets whose implicit decisions we
   must explicitly forbid.
3. No component of the materializer runtime may import, link, shell out to, or
   otherwise require XirAsm or LLVM.
4. `tools/oracle/` and `research/external/` are disposable zones: deleting them
   must not break the product build. Reproducibility is preserved by pinning
   revisions in `research/evidence/source_index.md`.

## Consequences

Positive:

- The decision boundary stays auditable: any implicit choice would have to be
  written by us, in our code, and can therefore be tested for.
- No coupling to Zig 0.17 churn or LLVM internal data structures.
- AArch64 no longer blocks the architecture: we are not waiting for a library
  that does not exist.

Negative:

- We own the encoding tables. Coverage is expensive and must be scoped to the
  vertical slices in the directive (§6).
- Correctness risk shifts onto our own oracle discipline: every positive vector
  needs an independent reference (rule 5 in `AGENTS.md`).
- Phase 1's reuse matrix will document knowledge we deliberately do not link,
  which is effort spent on material that will not ship.

Neutral:

- The directive's Route A/B analysis is still produced, but as a *risk and
  knowledge* comparison, not as an adoption decision.

## Alternatives considered

- **Route A (XirAsm-lib center).** Rejected as the product path: missing
  AArch64, mnemonic-driven selection, no fixup/layout surface, and Zig 0.17
  toolchain coupling. Retained as an oracle for x86 and RISC-V.
- **Route B (LLVM MC center).** Rejected as the product path: the relaxation,
  layout, and assembler policy surface is exactly what must be excluded, and
  isolating it costs more than owning a narrow kernel. Retained as the primary
  oracle and as a knowledge source for field mappings.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| xirasm-lib has no AArch64 backend | file listing + `xirasm_backend.zig` | high |
| lib excludes symbols/layout/object formats | `deps/xirasm-lib/README.md:12-19` | high |
| RISC-V API is mnemonic-driven | `riscv_encoder/api.zig:16-57`, `types.zig` | high |
| x86 relaxation is hint-controllable | `x86_encoder/api.zig:78,153,331` | medium — behavior unverified |
| AArch64 encoding runs in the Meta VM | generated `.inc` sizes + frontend modules | medium — runtime unverified |

## Review triggers

Revisit if Phase 1 finds a callable, form-addressable, AArch64-capable encoding
entry point in XirAsm, or if owning the kernel proves infeasible within the v0
slice budget.
