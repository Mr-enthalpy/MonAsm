# MonAsm

A deterministic materializer for a **Frozen Machine Plan (FMP)**.

FMP is the contract between an upstream planner and this repository. The planner
is responsible for instruction selection, operand legalization, encoding-form
selection, layout, and fixup planning. The materializer validates a frozen plan
and executes it: it emits bytes and fixup records, and rejects anything it cannot
execute exactly as written.

The materializer has no planning authority. That is the whole point.

## Status

**Phase 3 in progress on x86-64, AArch64 and RV64.** Gate G0 (oracle toolchain) and
G1 (encoder boundary audit) passed. The audit found that XirAsm's x86 path makes
four independent encoding decisions the caller cannot address, that its RISC-V
path is the only form-addressable entry point, and that AArch64 exists solely as a
40.9 MB interpreted Meta-language tree. Thirteen contract-level decisions are
settled (OD-01, OD-02, OD-03, OD-04, OD-06, OD-07, OD-09, OD-10, OD-11, OD-12,
OD-13, OD-14, OD-15); ADR-0004 makes `form_id` the only encoding selector, ADR-0005
takes AArch64 knowledge from the Arm MRS, ADR-0006 pins the MRS packaging by hash
and licence, ADR-0007 takes RV64 knowledge from the UDB resolved spec, ADR-0008
makes a memory operand one operand per encoded field, ADR-0009 gives a slot a
closed `excluded` list, ADR-0010 makes an RV64 low half name its high half,
ADR-0011 makes AArch64 `add ..., lsl #12` a form rather than a slot scale,
ADR-0012 makes an AArch64 condition a typed operand rather than sixteen forms,
ADR-0013 makes AArch64 addressing kinds forms and the offset field content,
ADR-0014 makes an AArch64 `movz` lane a form with `imm16` as field content,
ADR-0015 makes an AArch64 shift keyword a form with the amount as field content,
ADR-0016 makes an AArch64 extend keyword a form with the amount as field
content and a closed excluded tail, ADR-0017 makes an AArch64 mnemonic a
form family (`sub` repeats the `add` shapes with the node's `op = 1`), and
ADR-0018 makes the flag-setting mnemonic a form family too (`adds`/`subs`
repeat the shapes with the node's `S = 1`), and ADR-0019 makes the 32-bit width
a form family (`add`/`sub`/`adds`/`subs` repeat the shapes on the `sf = 0`
nodes, with every register slot `w32`), and ADR-0020 makes the extended-register
mnemonic a form family too (`sub`/`adds`/`subs` repeat the eight `add` extend
rows with the node's `op`/`S` fixed).
Fourteen definition documents are frozen and oracle-verified; the materializer and
its fixture gate are implemented.

| Area | State |
|---|---|
| Contract (`docs/fmp-v0/01_contract.md`) | draft, fields marked `TBD` where unproven |
| Schema (`schema/fmp-v0.schema.json`) | draft, examples validate |
| Definitions (`definitions/`) | x86-64 `0.1.0` (7 forms), aarch64 `0.1.0` (4 forms), `0.2.0` (5 forms), `0.3.0` (6 forms), `0.4.0` (11 forms), `0.5.0` (15 forms), `0.6.0` (18 forms), `0.7.0` (26 forms), `0.8.0` (32 forms), `0.9.0` (44 forms), `0.10.0` (68 forms) and `0.11.0` (92 forms), rv64 `0.1.0` (7 forms) and `0.2.0` (8 forms) frozen, digests pinned |
| Prototype (`prototype/`) | workspace compiled; all three slices materialize from the plan |
| Oracles (`tools/oracle/`) | planned; `llvm-mc` (± `ld.lld`) drives the experiments |
| Evidence (`research/evidence/`) | index, XirAsm snapshot, EXP-0001…EXP-0022 |

Read `docs/STATUS.md` for the current phase, gate status, and next action.

## Reading order

1. `AGENTS.md` — working constraints and the eight invariants.
2. `docs/fmp-v0/00_directive.md` — immutable research directive (source of truth).
3. `docs/fmp-v0/01_contract.md` — the FMP v0 contract.
4. `docs/STATUS.md` — where the work stands.

## Repository layout

```text
docs/
  STATUS.md                  phase, gates, next action, open decisions
  glossary.md                terms used across the contract set
  fmp-v0/                    contract, encoding choices, fixups, errors, matrix
  adr/                       architecture decision records
schema/                      JSON Schema for FMP v0 (draft)
definitions/{x86_64,aarch64,rv64}/  pinned encoding tables, one target each
fixtures/{x86_64,aarch64,rv64}/ plan + expected bytes + oracle metadata
research/evidence/           source index, pinned revisions, experiment records
research/external/           disposable snapshots (gitignored, pinned by SHA)
prototype/                   Rust workspace (materializer, Phase 3)
tools/oracle/                temporary oracle wrappers (llvm-mc, binutils)
tools/check_ids.py           documentation consistency check
tools/check_definition.py    definition table <-> document consistency check
tools/check_mrs.py           verifies the pinned Arm MRS drop (ADR-0006)
tools/check_rv64_source.py   verifies the pinned UDB drop (ADR-0007)
```

## Invariants at a glance

INV-01 no implicit instruction selection · INV-02 no implicit encoding-form
selection · INV-03 no implicit expansion · INV-04 no implicit layout change ·
INV-05 no hidden environment dependency · INV-06 no metaprogramming ·
INV-07 strict rejection · INV-08 replayable and traceable.

Each invariant has a registry row in `docs/fmp-v0/01_contract.md` and must map to
an executable test before it can be marked verified.

## Checking the docs

```bash
python tools/check_ids.py
```

The check verifies that IDs (`INV-*`, `N*`, `EXP-R*`, `AC-*`, `EC-*`, `OD-*`,
`E-*`) are declared exactly once in their registry document, that references
resolve, and that every declared negative test appears in the validation matrix.

## Dependency posture

XirAsm and LLVM are **temporary**: oracles, knowledge sources, and audit targets
(see `docs/adr/0001-route-c-self-owned-core.md`). The product path must build and
run with both directories deleted.

## License

Apache License 2.0. See `LICENSE`.
