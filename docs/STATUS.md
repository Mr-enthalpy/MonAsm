# Status

Updated: 2026-11-04
Phase: **3 in progress (x86, AArch64 and RV64 slices): three definition tables, the materializer and the fixture gate are in place; four AArch64 coverage rows remain, and RV64's memory/compressed/pair rows are blocked on format decisions**
Owner: Mr-enthalpy

This file is the recovery point. A new session should be able to resume from
this file plus `AGENTS.md` alone.

## Phase board

| Phase | Scope | State |
|---|---|---|
| 0 | Environment, evidence baseline, docs skeleton | **complete** |
| 1 | Encoder boundary audit (XirAsm, LLVM) | **complete** for XirAsm; LLVM internals deferred |
| 2 | FMP v0 contract, schema, error model | **complete for the x86, AArch64 and RV64 slices**; the RV64 rows that need a new payload shape or a non-zero constraint are format questions, not contract gaps |
| 3 | Three-ISA vertical prototype | **in progress**: three definition tables frozen (`07_definition_format.md`, `EXP-0004`, `EXP-0008`, `EXP-0010`); `fmp-model`/`fmp-validate`/`fmp-materialize`/`fmp-cli` implemented; x86 has 5 positive and 12 negative fixtures, AArch64 has 4 positive and 4 negative, RV64 has 5 positive and 4 negative, all passing the two-source gate |
| 4 | Invariants, negative tests, replay | not started |
| 5 | Convergence, route evaluation, roadmap | not started |

## Gates

| Gate | Condition | State |
|---|---|---|
| G0 | `llvm-mc` available and emits bytes for x86-64, AArch64, RV64 | **passed** 2026-11-03 (LLVM 23.1.2) |
| G1 | Three questions answered from source: x86 relaxation disable, RISC-V form addressing, AArch64 library entry point | **passed** 2026-11-03 (all three answered; see `90_boundary_audit.md` §4) |
| G2 | Every `EC-*` row has an observed counterexample and a decided carrier | **in progress**: the x86 slice rows are frozen (EC-01/02/03/04/06/07/27/28); 10 rows are still `draft` |
| G3 | Each ISA has >= 3 positive and >= 2 negative vectors passing two-source checks | **satisfied for x86, AArch64 and RV64** (x86: 5 positive, 12 negative; AArch64: 4 positive, 4 negative; RV64: 5 positive, 4 negative) |

## Decisions

| ID | Decision | State |
|---|---|---|
| ADR-0001 | Self-owned encoding core (Route C); XirAsm/LLVM are temporary oracles | accepted |
| ADR-0002 | Docs-first with explicit context anchors | accepted |
| ADR-0003 | Rust prototype, Level 0/1 output | accepted (provisional); OD-03 narrowed v0 to Level 0 |
| ADR-0004 | `form_id` carries every encoding decision; `encoding_choices` removed | accepted 2026-11-04 |
| ADR-0005 | AArch64 knowledge comes from the Arm MRS 2026-06; no XirAsm file is copied, the Arm notice ships with the table | accepted 2026-11-04 |
| ADR-0006 | The AArch64 source is pinned by MRS *packaging*: archive hash + both file hashes + the BSD-3-Clause licence sentence; the release block alone is not a pin | accepted 2026-11-04 |
| ADR-0007 | RV64 knowledge comes from the UDB resolved spec, pinned by archive hash + eight node hashes + the BSD-3-Clause-Clear header; `left_shift` is a fixup transform, and `not: 0` keeps `c.addi` out of v0 | accepted 2026-11-04 |

## Settled decisions (contract level)

| ID | Decision | Evidence |
|---|---|---|
| OD-01 | Plan carries an optional per-instruction `expected_digest`; a hash, never raw bytes; a check, never an input | `EXP-0002` §2–§5 |
| OD-02 | Exactly two fixup modes, one effect each: `resolve_in_place` writes, `emit_relocation` zeroes and records; records are RELA-shaped; the mode never depends on symbol liveness | `EXP-0002` §6; `03_fixup_model.md` §5, §8 |
| OD-03 | v0 emits Level 0; Level 1 optional and deferred; Level 2 out of scope | `EXP-0002` §6 |
| OD-04 | `form_id` is a structured name resolved by exact lookup; a rename is loud (`E-FORM-001`, or `E-DEF-001` first); no opaque id, no `match`/`mask` | `01_contract.md` §7; F-09 |
| OD-06 | The definition digest covers the whole data-only definition in canonical form; a rule change moves it, formatting does not, and a comment is unrepresentable | `EXP-0004` §4; `07_definition_format.md` §6 |
| OD-07 | AArch64 facts come from the Arm MRS 2026-06 OPENSOURCE packaging; our own table is generated from the data, no MPL-2.0 script is copied, and the Arm BSD-3-Clause notice ships with `definitions/aarch64/` | ADR-0005, ADR-0006; `EXP-0007`; `90_boundary_audit.md` F-12, F-13; `definitions/aarch64/NOTICE` |
| OD-09 | Exact integers with declared domains, no wrap, one range check per value after the transform | `01_contract.md` §3.1–§3.2 |
| OD-10 | v0 ships only the forms the slices use; the definition table is the feature surface and absence is `E-FORM-001` | `02_encoding_choices.md`, "v0 surface"; ADR-0004 |
| OD-11 | A byte-affecting decision is carried by `form_id`, a typed operand, a fixup field or a target field — never by a separate choice list | ADR-0004; `02_encoding_choices.md` |
| OD-12 | RV64 facts come from the UDB resolved spec (`sha256:be184986…`), pinned per node; riscv-opcodes is the upstream cross-check and `llvm-mc` the oracle | ADR-0007; `EXP-0009`; `EXP-0010`; `definitions/rv64/NOTICE` |

## Open decisions

See `docs/fmp-v0/05_open_decisions.md`. Blocking items currently:

| ID | Question | Blocks |
|---|---|---|
| OD-05 | Unknown fields and extensions | AC-10, Q10 |
| OD-08 | Canonical wire form | AC-07 |

OD-05 and OD-08 do not block the x86 slice. OD-07 is settled by ADR-0005 and
pinned by ADR-0006, and the AArch64 table it authorised now exists: four MRS
nodes generated the four forms in `definitions/aarch64/0.1.0.json`, matched
against `llvm-mc` by four fixtures (`EXP-0008`). What remains is coverage, not a
decision: `A64-P3`/`P4`/`P7`/`P8` and the `-lsl12` half of `A64-P2` have no
table row yet. OD-12 is settled by ADR-0007: the RV64 source is the UDB resolved
spec, pinned by archive and node hashes, `EXP-0009` verified the B/J/RVC scatter
against `llvm-mc`, and `EXP-0010` generated
`definitions/rv64/0.1.0.json` (five forms) from five of those nodes. RV64's
`ld`/`sd` row needs a memory payload shape, its `c.addi` row needs a non-zero
constraint, and its `auipc`+`lo12` pair needs the psABI relation; each is a new
format decision, not a missing source. OD-06 was load-bearing because `EXP-0002`
W1 shows that a definition drift the digest does not cover is caught only by the
weaker size check; it is now settled, and `EXP-0004` §4 measures both halves.

## Next action

1. Decide the next format question, one ADR each, before widening any table:
   - the memory payload shape (`riscv.mem.base-offset`, `x86.mem`). It unblocks
     `RV-P3` and `X86-P4`/`P5`/`P6`; `01_contract.md` §8.1 fixes only `{reg}`,
     `{value}`, `{symbol_id}` and `{}` today;
   - a closed non-zero constraint for `fmp-def/0.1`. It unblocks `RV-P7`
     (`c.addi`), whose source states `not: 0` on `imm` and `xd`;
   - the psABI `R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I` pairing. It unblocks
     `RV-P8`'s pair half; the `auipc` form already exists.
   Each lands with a counterexample, an error code where rejection is the answer,
   and a fixture that shows the exclusion today (`E-FORM-001` or the new code).
2. Extend the AArch64 coverage, one vertical slice at a time:
   - add the `-lsl12` half of `A64-P2`. This needs a decision about slot-level
     scaling, because a definition slot has no transform and `sh = 1` multiplies
     the immediate by 4096. It is a format change with its own ADR, not a
     generator tweak (`07_definition_format.md` §8.3);
   - then `A64-P4` (`b.eq`, imm19), `A64-P3` (load/store), `A64-P7` and `A64-P8`,
     each with its own MRS node, fixture and oracle record.
3. Close the remaining contract debt:
   - `OD-05` (unknown fields/extensions) and `OD-08` (canonical wire form);
   - the Level 1 artifact envelope, which is deferred by `OD-03` and is not
     needed by the Level 0 gate.
4. Keep `python tools/check_ids.py`, `python tools/check_definition.py` and
   `python tools/check_rv64_source.py` green after every change, and keep
   `cargo test --workspace` green: it is the fixture gate, not a smoke test.

Phase 3 output so far: the Rust workspace under `prototype/` (`fmp-model` for the
strict JSON reader and the plan/definition binders, `fmp-validate` for contract
§13 steps 2–7, `fmp-materialize` for encoding and the two fixup modes,
`fmp-cli` with exit codes 0/1/2); the frozen table
`definitions/x86_64/0.1.0.json` (seven forms, digest `sha256:c6bfa9…`);
`EXP-0004` (223 decoded byte strings across all seven rows, plus the `OD-06`
digest measurement); `EXP-0005` (5 positive fixtures against LLVM 23.1.2, with
the two decode-only caveats); and 12 negative fixtures whose complete diagnostic
sets — code, JSON Pointer, detail keys — are compared for exact equality.
`E-OPERAND-004`/`N14` (an operand wider than its field) is one of them.

The AArch64 slice adds `definitions/aarch64/0.1.0.json` (four forms: two `add`,
`bl`, `adrp`; digest `sha256:96f87aa…`) with the Arm BSD-3-Clause notice beside
it, `EXP-0008` (four MRS nodes, the all-32-bits-covered check, and the
`immlo`-at-30:29 correction the oracle caught), and 4 positive + 4 negative
fixtures. A64-P5/P6 use `llvm-mc` → `ld.lld` → `llvm-objcopy` because `llvm-mc`
leaves AArch64 branch and `adrp` fields as relocations. The fixture gate now
scans every `fixtures/<isa>/<kind>/` directory, so a new table's vectors are
gated the moment they land.

The RV64 slice adds `definitions/rv64/0.1.0.json` (five forms: `add`, `addi`,
`beq`, `jal`, `auipc`; digest `sha256:8cd063a5…`) with the BSD-3-Clause-Clear
notice beside it. ADR-0007 fixes the source as the UDB resolved spec
(`sha256:be184986…`); `EXP-0009` measures eight instruction nodes and reproduces
fourteen `llvm-mc` byte strings from their `location` fields; `EXP-0010`
generates the table from five of those nodes, asserts full-bit coverage, and
re-encodes nine probe vectors from the table it built. `tools/check_rv64_source.py`
gates the drop, the SPDX headers and `definitions/rv64/NOTICE`. The five positive
fixtures exercise `add`, both `addi` endpoints, the B-type scatter forward and
backward, the J-type scatter forward and backward, and the `auipc` field; the
four negatives pin `E-FORM-001`, `E-OPERAND-001`, `E-RANGE-001` and
`E-RANGE-002`. `ld`/`sd`, `c.addi` and the `auipc`+`lo12` pair stay out, each for
a recorded format reason rather than a missing source.

The materializer is deliberately not a bridge to LLVM: it reads only the plan
and the pinned definition, writes bytes and RELA-shaped records, and has no
fallback when a form, field or symbol is missing.

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
