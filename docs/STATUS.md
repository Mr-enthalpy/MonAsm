# Status

Updated: 2026-11-03
Phase: **0 complete (G0 passed); Phase 1 next**
Owner: Mr-enthalpy

This file is the recovery point. A new session should be able to resume from
this file plus `AGENTS.md` alone.

## Phase board

| Phase | Scope | State |
|---|---|---|
| 0 | Environment, evidence baseline, docs skeleton | **complete** |
| 1 | Encoder boundary audit (XirAsm, LLVM) | **next** |
| 2 | FMP v0 contract, schema, error model | not started |
| 3 | Three-ISA vertical prototype | not started |
| 4 | Invariants, negative tests, replay | not started |
| 5 | Convergence, route evaluation, roadmap | not started |

## Gates

| Gate | Condition | State |
|---|---|---|
| G0 | `llvm-mc` available and emits bytes for x86-64, AArch64, RV64 | **passed** 2026-11-03 (LLVM 23.1.2) |
| G1 | Three questions answered from source: x86 relaxation disable, RISC-V form addressing, AArch64 library entry point | not started |
| G2 | Every `encoding_choice` in `EC-*` has a counterexample | not started |
| G3 | Each ISA has >= 3 positive and >= 2 negative vectors passing two-source checks | not started |

## Decisions

| ID | Decision | State |
|---|---|---|
| ADR-0001 | Self-owned encoding core (Route C); XirAsm/LLVM are temporary oracles | accepted |
| ADR-0002 | Docs-first with explicit context anchors | accepted |
| ADR-0003 | Rust prototype, Level 0/1 output | accepted (provisional) |

## Open decisions

See `docs/fmp-v0/05_open_decisions.md`. Blocking items currently:

| ID | Question | Blocks |
|---|---|---|
| OD-01 | Does the plan carry expected bytes (A/B/C)? | AC-04, AC-07 |
| OD-02 | When are fixups applied vs. recorded? | AC-05 |
| OD-03 | Output level 0, 1, or 2 for v0? | AC-03 |
| OD-07 | AArch64 encoding knowledge source | AC-03, AC-05 |

## Next action

1. Run the XirAsm build/test spike against pinned commit `3ee8a439f5ba`
   with `C:\Users\hanni\Tools\zig\zig.exe`.
2. Start Phase 1 with the x86 relaxation path (`size.zig`, `EncodeContext`) and
   the RISC-V mnemonic-to-form resolution (`tables.zig`).
3. Capture the first oracle bytes for `X86-P1`, `A64-P1`, and `RV-P1` under
   `research/evidence/experiments/`.

## Known environment facts (verified 2026-11-03)

| Item | Value |
|---|---|
| Host | Windows, `C:\Users\hanni\Projects\MonAsm` |
| Git remote | `git@github.com:Mr-enthalpy/MonAsm.git` (SSH, authenticated) |
| Zig | 0.17.0 at `C:\Users\hanni\Tools\zig` |
| LLVM | 23.1.2 at `C:\Users\hanni\Tools\llvm` (`llvm-mc` verified on x86-64, AArch64, RV64) |
| GNU binutils | not installed (llvm-objdump/llvm-readobj cover v0 needs) |
| Rust | 1.96.0 (`stable-x86_64-pc-windows-msvc`) |
| Visual Studio | 2022 present |
| Python | 3.8 |
| WSL | executable present, no distribution installed |

## Immutable source text

`docs/fmp-v0/00_directive.md` is a verbatim copy of the research directive. It is
never edited. Integrity checksum (SHA-256) is recorded in
`research/evidence/source_index.md`.
