# Status

Updated: 2026-11-04
Phase: **2 in progress (OD-01 and OD-03 settled)**
Owner: Mr-enthalpy

This file is the recovery point. A new session should be able to resume from
this file plus `AGENTS.md` alone.

## Phase board

| Phase | Scope | State |
|---|---|---|
| 0 | Environment, evidence baseline, docs skeleton | **complete** |
| 1 | Encoder boundary audit (XirAsm, LLVM) | **complete** for XirAsm; LLVM internals deferred |
| 2 | FMP v0 contract, schema, error model | **in progress**; OD-01 and OD-03 settled |
| 3 | Three-ISA vertical prototype | not started |
| 4 | Invariants, negative tests, replay | not started |
| 5 | Convergence, route evaluation, roadmap | not started |

## Gates

| Gate | Condition | State |
|---|---|---|
| G0 | `llvm-mc` available and emits bytes for x86-64, AArch64, RV64 | **passed** 2026-11-03 (LLVM 23.1.2) |
| G1 | Three questions answered from source: x86 relaxation disable, RISC-V form addressing, AArch64 library entry point | **passed** 2026-11-03 (all three answered; see `90_boundary_audit.md` §4) |
| G2 | Every `encoding_choice` in `EC-*` has a counterexample | not started |
| G3 | Each ISA has >= 3 positive and >= 2 negative vectors passing two-source checks | not started |

## Decisions

| ID | Decision | State |
|---|---|---|
| ADR-0001 | Self-owned encoding core (Route C); XirAsm/LLVM are temporary oracles | accepted |
| ADR-0002 | Docs-first with explicit context anchors | accepted |
| ADR-0003 | Rust prototype, Level 0/1 output | accepted (provisional); OD-03 narrowed v0 to Level 0 |

## Settled decisions (contract level, no ADR needed)

| ID | Decision | Evidence |
|---|---|---|
| OD-01 | Plan carries an optional per-instruction `expected_digest`; a hash, never raw bytes; a check, never an input | `EXP-0002` §2–§5 |
| OD-03 | v0 emits Level 0; Level 1 optional and deferred; Level 2 out of scope | `EXP-0002` §6 |

## Open decisions

See `docs/fmp-v0/05_open_decisions.md`. Blocking items currently:

| ID | Question | Blocks |
|---|---|---|
| OD-02 | When are fixups applied vs. recorded? | AC-05 |
| OD-04 | How is `form_id` made stable? | AC-08, Q2 |
| OD-05 | Unknown fields and extensions | AC-10, Q10 |
| OD-06 | Definition digest coverage | N10, EXP-R5 |
| OD-07 | AArch64 encoding knowledge source | AC-03, AC-05 |
| OD-08 | Canonical wire form | AC-07 |
| OD-09 | Integer and address model | AC-02 |
| OD-10 | v0 minimal feature surface (which `EC-*`) | AC-09, AC-10 |

OD-04 and OD-07 have evidence but are not accepted. OD-06 is now load-bearing:
`EXP-0002` W1 shows that a definition drift the digest does not cover is caught
only by the weaker size check.

## Next action

Phase 2, in order:

1. Settle **OD-10**: the minimal `EC-*` set for one x86 slice
   (`mov r64,r64`, `add r64,imm8`, `add r64,imm32`, `jmp rel8`, `jmp rel32`).
2. Freeze those `EC-*` rows and remove every `TBD` the x86 slice touches
   (`AC-01`), including `form_id` names (OD-04) and the operand `payload`
   conventions for fixup-filled fields (OD-02).
3. Add the `E-*` counterexamples from `90_boundary_audit.md` §5 to the registry
   and re-run `python tools/check_ids.py`.
4. Only then start Phase 3 (`ADR-0003`).

Phase 2 output so far: `EXP-0002` (OD-01, OD-03), plus the `pcrel_end` fix in
`03_fixup_model.md` §4 and the observed relocation semantics in §6.1.

Phase 1 output to read first: `docs/fmp-v0/90_boundary_audit.md` (findings
F-01…F-15, gate answers in §4) and `docs/fmp-v0/91_reuse_matrix.md`.
Raw experiment records: `research/evidence/experiments/EXP-0001-*.md`,
`research/evidence/experiments/EXP-0002/README.md`.

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
