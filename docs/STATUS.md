# Status

Updated: 2026-11-04
Phase: **3 in progress (x86 slice): the definition table is frozen and verified; the materializer is the next artifact**
Owner: Mr-enthalpy

This file is the recovery point. A new session should be able to resume from
this file plus `AGENTS.md` alone.

## Phase board

| Phase | Scope | State |
|---|---|---|
| 0 | Environment, evidence baseline, docs skeleton | **complete** |
| 1 | Encoder boundary audit (XirAsm, LLVM) | **complete** for XirAsm; LLVM internals deferred |
| 2 | FMP v0 contract, schema, error model | **complete for the x86 slice**; AArch64/RV64 surfaces block on OD-07 |
| 3 | Three-ISA vertical prototype | **in progress** on x86: definition table frozen (`07_definition_format.md`, `EXP-0004`); encoder/validator not written |
| 4 | Invariants, negative tests, replay | not started |
| 5 | Convergence, route evaluation, roadmap | not started |

## Gates

| Gate | Condition | State |
|---|---|---|
| G0 | `llvm-mc` available and emits bytes for x86-64, AArch64, RV64 | **passed** 2026-11-03 (LLVM 23.1.2) |
| G1 | Three questions answered from source: x86 relaxation disable, RISC-V form addressing, AArch64 library entry point | **passed** 2026-11-03 (all three answered; see `90_boundary_audit.md` §4) |
| G2 | Every `EC-*` row has an observed counterexample and a decided carrier | **in progress**: the x86 slice rows are frozen (EC-01/02/03/04/06/07/27/28); 10 rows are still `draft` |
| G3 | Each ISA has >= 3 positive and >= 2 negative vectors passing two-source checks | not started |

## Decisions

| ID | Decision | State |
|---|---|---|
| ADR-0001 | Self-owned encoding core (Route C); XirAsm/LLVM are temporary oracles | accepted |
| ADR-0002 | Docs-first with explicit context anchors | accepted |
| ADR-0003 | Rust prototype, Level 0/1 output | accepted (provisional); OD-03 narrowed v0 to Level 0 |
| ADR-0004 | `form_id` carries every encoding decision; `encoding_choices` removed | accepted 2026-11-04 |

## Settled decisions (contract level)

| ID | Decision | Evidence |
|---|---|---|
| OD-01 | Plan carries an optional per-instruction `expected_digest`; a hash, never raw bytes; a check, never an input | `EXP-0002` §2–§5 |
| OD-02 | Exactly two fixup modes, one effect each: `resolve_in_place` writes, `emit_relocation` zeroes and records; records are RELA-shaped; the mode never depends on symbol liveness | `EXP-0002` §6; `03_fixup_model.md` §5, §8 |
| OD-03 | v0 emits Level 0; Level 1 optional and deferred; Level 2 out of scope | `EXP-0002` §6 |
| OD-04 | `form_id` is a structured name resolved by exact lookup; a rename is loud (`E-FORM-001`, or `E-DEF-001` first); no opaque id, no `match`/`mask` | `01_contract.md` §7; F-09 |
| OD-06 | The definition digest covers the whole data-only definition in canonical form; a rule change moves it, formatting does not, and a comment is unrepresentable | `EXP-0004` §4; `07_definition_format.md` §6 |
| OD-09 | Exact integers with declared domains, no wrap, one range check per value after the transform | `01_contract.md` §3.1–§3.2 |
| OD-10 | v0 ships only the forms the slices use; the definition table is the feature surface and absence is `E-FORM-001` | `02_encoding_choices.md`, "v0 surface"; ADR-0004 |
| OD-11 | A byte-affecting decision is carried by `form_id`, a typed operand, a fixup field or a target field — never by a separate choice list | ADR-0004; `02_encoding_choices.md` |

## Open decisions

See `docs/fmp-v0/05_open_decisions.md`. Blocking items currently:

| ID | Question | Blocks |
|---|---|---|
| OD-05 | Unknown fields and extensions | AC-10, Q10 |
| OD-07 | AArch64 encoding knowledge source | AC-03, AC-05 |
| OD-08 | Canonical wire form | AC-07 |

OD-07 has evidence but is not accepted. OD-06 was load-bearing because `EXP-0002`
W1 shows that a definition drift the digest does not cover is caught only by the
weaker size check; it is now settled, and `EXP-0004` §4 measures both halves.

## Next action

1. Write the x86 materializer in `prototype/`: plan model and parser (`fmp-model`),
   static checks (`fmp-validate`), definition loading + encoding + fixup execution
   (`fmp-materialize`), and the `fmp` CLI.
2. Order inside that work: definition load with the digest check, exact-integer
   fixup engine (OD-02 modes, OD-09 arithmetic), then the `N01`, `N02`, `N03`,
   `N04`, `N05`, `N07`, `N08`, `N10`, `N13`, `N14` fixtures and the `X86-P1`–`P8`
   positive fixtures with their oracle records.
3. Keep `python tools/check_ids.py` and `python tools/check_definition.py` green
   after every change.
4. Unblock OD-07 (licence review) before starting AArch64. OD-05 and OD-08 are the
   remaining contract decisions; neither blocks the x86 slice.

Phase 3 output so far: `07_definition_format.md` (the definition artifact and its
load-time checks), `definitions/x86_64/0.1.0.json` (the seven v0 forms, digest
`sha256:c6bfa9…`), `EXP-0004` (223 decoded byte strings across all seven rows,
plus the `OD-06` digest measurement), `E-OPERAND-004`/`N14` (an operand wider than
its field is rejected, not truncated), and `tools/check_definition.py`, which
fails if the document and the JSON table disagree.

Phase 2 output: `EXP-0002` (OD-01, OD-03), `EXP-0003` (the alias pairs behind
OD-11/ADR-0004), the `pcrel_end` fix in `03_fixup_model.md` §4, the observed
relocation semantics in §6.1, ADR-0004 (OD-10, OD-11), the rewritten
`02_encoding_choices.md` with per-row carriers, the counterexample/retirement
sections in `04_errors.md`, and the OD-02/OD-04/OD-09 freeze: two fixup modes
with one effect each, a structured `form_id` with loud failure, and the exact
integer/address model in `01_contract.md` §3.1. The schema lost
`reject_if_unresolved`, `overwrite_bytes` and the one-value `bit_order` enum, and
`E-FIXUP-004` is retired.

`EXP-0002`'s plan-size numbers were measured with the then-required empty
`encoding_choices` list. ADR-0004 removes that field, so absolute sizes drop by
about 22 B per instruction; the A-vs-B comparison is unaffected in direction.

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
