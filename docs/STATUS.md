# Status

Updated: 2026-11-10
Phase: **7 complete** (M6 coverage round 2, `ADR-0112`; S1 `ADR-0113`, S2 `ADR-0114`, S3 `ADR-0115`, S4 `ADR-0116`, S5 `ADR-0117`, S6 `ADR-0118`, S7 `ADR-0119` and the closure `ADR-0120` landed): Phase 4 is complete (all eight invariants `verified`; `EXP-R3` passes on three CI hosts; `N22` closes INV-04 and `N23a` closes INV-06). Phase 5 froze the contract set for the v0 scope (`ADR-0095`), published `08_final_recommendation.md` (§A–§H plus Q1–Q10) and closed `AC-10` with the Phase 6 roadmap M1–M5. Phase 6 M1 (error-coverage gate) is complete with `N24a`–`N24h`, M2 (oracle rerun harness) is complete with `tools/oracle/rerun.py`, and M3 (Level 1 object writer) is complete with `X86-P71` and `ADR-0096`; M3 also added `N24i` and repointed `N24h`. M4 (planner boundary) is complete: `fmp-plan` is implemented and the `planner_api.rs` parity gate runs ten tests over the 128 positives, the 611 `materialize`-phase negatives, from-scratch authoring, closed keys, enum spellings and determinism. M5 (coverage widening) is **complete**: `A64-P20` names the three unused `imm6-asr` rows, `ADR-0098`/`RV-P9` add the RV64 absolute `lui`+`addi` split with `hi20`, and `ADR-0099`/`RV-P10` add `riscv:jalr/rd-rs1-imm12` with the `auipc` + `jalr` call pair. The seven-item first wave is complete after `ADR-0103`, which adds `fmp-def/0.2` per-form `requires_extensions` and the `X86-P74`/`N06b`/`N06c` vectors. The oracle recovery backlog is closed too: all 29 `input-not-stored` inputs were recovered or rebuilt and `tools/oracle/rerun.py` now reports `122/128` with the six `manual-derivation` skips (it reported `116/121` and five skips when M5 closed). `ADR-0111` closes the phase: seven slices landed under `ADR-0104`-`ADR-0110` and the stale metrics are reconciled. Phase 7 M6 is **complete** under `ADR-0112`: `10_m6_plan.md` fixes seven coverage slices (`ADR-0113`-`ADR-0119`) plus the closure `ADR-0120`, with no contract change and no new artifact level. `S1` landed under `ADR-0113`: the integer ALU register/register family in the `opcode` direction (`x86/0.75.0`, 15 rows, `X86-P81`), with `EC-42` widened to the six direction pairs. The round closes at 82 new rows and 841 forms across 104 documents, with 128 positives and 611 negatives (`ADR-0120`). An audit of `47a383b` then closed under `ADR-0121`-`ADR-0124`: fixup bits must belong to exactly one non-inverted `operand_value` slot and the descriptor order must match that slot's placement order (`ADR-0121`); the numeric domains and the 64 MiB image ceiling are checked before the arithmetic they protect (`E-LIMIT-001`, `ADR-0122`); `target.kind: section_relative` and a symbol offset past `declared_size` are refused (`ADR-0123`); and the document, definition, formatting, workspace and oracle gates now run in `.github/workflows/gates.yml`, with the oracle harness driven by argv instead of a shell (`ADR-0124`). Eight negatives land (`N05b`, `N07g`, `N07h`, `N24j`-`N24l`, `N25a`, `N25b`), so the corpus is 128 positives and 619 negatives (611 `materialize`-phase plus 8 `read`-phase), and `04_errors.md` §2.4 records 39 of 44 active codes.
Owner: Mr-enthalpy

This file is the recovery point. A new session should be able to resume from
this file plus `AGENTS.md` alone.

## Phase board

| Phase | Scope | State |
|---|---|---|
| 0 | Environment, evidence baseline, docs skeleton | **complete** |
| 1 | Encoder boundary audit (XirAsm, LLVM) | **complete** for XirAsm; LLVM internals deferred |
| 2 | FMP v0 contract, schema, error model | **complete for the x86, AArch64 and RV64 slices**; the last RV64 row's psABI pairing is now part of the contract (ADR-0010) |
| 3 | Three-ISA vertical prototype | **complete** (2026-11-08): ninety definition documents frozen (`07_definition_format.md`, `EXP-0004`, `EXP-0008`, `EXP-0010`, `EXP-0012`); `fmp-model`/`fmp-validate`/`fmp-materialize`/`fmp-cli` implemented; x86 has 75 positive and 488 negative fixtures, AArch64 has 24 positive and 61 negative, RV64 has 15 positive and 16 negative, all passing the two-source gate; exit criteria below |
| 4 | Invariants, negative tests, replay | **complete** (2026-11-08): `EXP-R1`–`R6` pass in `prototype/crates/fmp-cli/tests/determinism.rs`; `EXP-R3` also passes on Ubuntu 24.04 (`x86_64`), macOS 26.7.2 (`aarch64`) and Windows Server 2025 with the pinned 1.96.0 toolchain (`EXP-0033` §6, run 42402997326); the invariant-to-test map in `01_contract.md` §2 is filled and every row is `verified` (`N22` closes `E-LAYOUT-004`/`006`/`007`, `N23a` closes the expression-shaped-value gap in INV-06) |
| 5 | Convergence, route evaluation, roadmap | **complete** (2026-11-08): `08_final_recommendation.md` §A–§H and Q1–Q10; `ADR-0095` moves the contract set to `frozen for the v0 scope`; `AC-10` satisfied; Phase 6 order fixed as M1 error-coverage gate → M2 oracle rerun harness → M3 Level 1 object writer → M4 planner boundary → M5 coverage widening |
| 6 | Implementation roadmap (M1–M5) | **complete**: M1 error-coverage gate **complete** (2026-11-08) with `N24a`–`N24h`, CI run `42407621760` green on Ubuntu, macOS and Windows; M2 oracle rerun harness **complete** (`tools/oracle/rerun.py`: 116/121 re-derived after the recovery backlog closed, 5 `manual-derivation`, 0 `input-not-stored`, 0 failed; CI run `42408219370` green); M3 Level 1 object writer **complete** (2026-11-08) with `ADR-0096`, `X86-P71` and `EXP-0100`, plus `N24i` and the repointed `N24h`; CI run `42409630161` green on Ubuntu, macOS and Windows; Level 0 bytes unchanged; M4 planner boundary/API **complete** (2026-11-08): `ADR-0097` and `09_planner_api.md` define `fmp-plan`, a total closed builder over `fmp-model` with no validator and no planner authority; the crate is implemented and `cargo tree -p fmp-plan` shows `fmp-model` as its only workspace dependency; `planner_api.rs` runs ten tests (121 positive and 580 `materialize`-phase negative parity, from-scratch authoring for `X86-P1`/`A64-P2`/`RV-P1`/`X86-P71`, closed key sets, optional-member and enum-spelling round trips, fixed-point re-emission, the six `read`-phase negatives, determinism and typed `Unrepresentable` failures), and a removal of `expected_digest` was observed to fail the gate; CI run `42412752660` green on Ubuntu, macOS and Windows; M5 coverage widening **complete** (2026-11-09): `A64-P20` closes the three unused `imm6-asr` rows and `tools/check_definition.py` now fails when a frozen row has no positive fixture; `ADR-0098` defines `hi20`, adds `definitions/rv64/0.3.0.json` (`riscv:lui/rd-imm20`), the three `RV-P9` vectors and `N01eh`/`N07f`; `ADR-0099` adds `riscv:jalr/rd-rs1-imm12` as `definitions/rv64/0.4.0.json`, the three `RV-P10` vectors including the `pcrel_lo12` call pair, and `N01ei`/`N03x`; `ADR-0100` adds `aarch64:b/imm26`, `br/rn`, `blr/rn` and `ret/rn` as `definitions/aarch64/0.18.0.json`, the `A64-P21`/`A64-P22` vectors, `EC-41` and `N01x`/`N01y`/`N04e`/`N19d`; `ADR-0101` adds the three x86 `sub` immediate rows as `definitions/x86_64/0.66.0.json`, the `X86-P72` vector, the `EC-01`/`EC-04` revision and `N01ej`/`N01ek`/`N02ct`/`N03zs`; `ADR-0102` adds the direct x86 `call rel32` row as `definitions/x86_64/0.67.0.json`, the `X86-P73` vector, the `EC-03` revision and `N01el`/`N01em`/`N02cu`/`N02cv`/`N04g`; `ADR-0103` adds `fmp-def/0.2` per-form `requires_extensions` as `definitions/x86_64/0.68.0.json` (513 forms, 125 gated), the subset rule and the step-6 `E-TARGET-003` gate, the `X86-P74` vector and `N06b`/`N06c`. The seven-item first wave is complete and the 29-record oracle recovery backlog is closed (`116/121`, five `manual-derivation` skips); `ADR-0104` adds the five remaining RV64 B-type mnemonics as `definitions/rv64/0.5.0.json` with `RV-P11`/`N01en`/`N02cw`/`N04h`, and `ADR-0105` adds the six SSE `%rip`-relative rows as `definitions/x86_64/0.69.0.json` with `X86-P75`/`N01eo`/`N02cx`/`N04i`, and `ADR-0106` adds the eight `xmm8`-`xmm15` fixed-base legacy SSE rows as `definitions/x86_64/0.70.0.json` with `X86-P76`/`N01ep`/`N02cy`/`N03zt`; `ADR-0107` adds the six `addr32` `%rip` rows as `0.71.0` with `X86-P77`/`N01eq`/`N02cz`/`N04j`; `ADR-0108` the sixteen legacy/VEX SSE indexed rows as `0.72.0` with `X86-P78`/`N01er`/`N02da`/`N03zu`; `ADR-0109` the twelve indexed byte `mov` rows as `0.73.0` with `X86-P79`/`N01es`/`N02db`/`N03zv`; `ADR-0110` the three `29 /r` register/register `sub` rows as `0.74.0` with `X86-P80`/`N01et`/`N02dc`/`N14cg` and the repointed `N01ej`; `ADR-0111` closes the phase and reconciles the metrics |
| 7 | Coverage round 2 (M6) | **complete** (`ADR-0112`): seven additive coverage slices, one ADR each (`ADR-0113`-`ADR-0119`), plus closure `ADR-0120`; `10_m6_plan.md` fixes the slice order, rows and deferrals. `S1` is **complete** (`ADR-0113`, 2026-11-09): `definitions/x86_64/0.75.0.json` appends 15 ALU register/register rows (579 forms, digest `sha256:5b13b6b9…`), the `X86-P81` 80-byte vector and five negatives land, and `EC-42` now covers all six `opcode`/`opcode+1` pairs. `S2` is **complete** (`ADR-0114`, 2026-11-10): `definitions/x86_64/0.76.0.json` appends 36 ALU immediate rows (615 forms, digest `sha256:7535ae06…`), the `X86-P82` 176-byte vector and four negatives land, and `EC-01`/`EC-04` are widened in place. `S3` is **complete** (`ADR-0115`, 2026-11-10): `definitions/x86_64/0.77.0.json` appends 5 `mov` immediate rows (620 forms, digest `sha256:093d8f3c…`); the plan's sixth row, `REX.W B8+rd id`, is not an encoding (`movabs` takes `io`), so the round total is 82 rows and 841 forms. The `X86-P83` 54-byte vector and three negatives land, with `EC-04` widened in place. `S4` is **complete** (`ADR-0116`, 2026-11-10): `definitions/x86_64/0.78.0.json` appends 12 `sub` memory rows -- `29 /r` (store) and `2B /r` (load) at 64/32/16 bits with `base + disp8`/`disp32` (632 forms, digest `sha256:30cb9f13…`) -- with the `X86-P84` 62-byte vector and three negatives, and `EC-42` widened in place to the memory direction. `S5` is **complete** (`ADR-0117`, 2026-11-10): `definitions/rv64/0.6.0.json` appends the nine other load/store widths -- `lb`/`lh`/`lw`/`lbu`/`lhu`/`lwu` on `ld`'s I-type field and `sb`/`sh`/`sw` on `sd`'s S-type scatter, differing only in `funct3` (24 forms, digest `sha256:0baf3b34…`) -- with the `RV-P12` 44-byte vector and three negatives, and no `EC` change because the width is a mnemonic choice. `S6` is **complete** (`ADR-0118`, 2026-11-10): `definitions/aarch64/0.19.0.json` appends the PC-relative `adr` row -- `ADR_only_pcreladdr`, `op = 0` at bit 31, the same `immlo`/`immhi` split as `adrp` but a signed 21-bit **byte** displacement (181 forms, digest `sha256:f299d978…`) -- with the `A64-P23` 32-byte vector and three negatives, and `EC-43` records the one template bit that separates `adr` from `adrp`. `S7` is **complete** (`ADR-0119`, 2026-11-10): `definitions/aarch64/0.20.0.json` appends four rows -- the `mul` alias at 32/64 bits (`MADD` with `Ra` pinned to 31) and `csel` at 32/64 bits (`cond` as the fourth operand) -- for 185 forms (digest `sha256:05033c9e…`), with the `A64-P24` 32-byte vector and four negatives, and `EC-44` records the accumulator field the alias pins. The closure `ADR-0120` is **complete** (2026-11-10): the round lands 82 rows and 841 forms across 104 documents (x86 632, AArch64 185, RV64 24) with 128 positives and 611 negatives, and the two deviations from the plan (S1 15 not 16, S3 5 not 6) are the measured corrections; no contract change and no new artifact level. The `47a383b` audit (`ADR-0121`-`ADR-0124`) lands eight negatives and two read-phase fixtures, so the living corpus is 128 positives and 619 negatives (611 `materialize`-phase plus 8 `read`-phase) |

## Gates

| Gate | Condition | State |
|---|---|---|
| G0 | `llvm-mc` available and emits bytes for x86-64, AArch64, RV64 | **passed** 2026-11-03 (LLVM 23.1.2) |
| G1 | Three questions answered from source: x86 relaxation disable, RISC-V form addressing, AArch64 library entry point | **passed** 2026-11-03 (all three answered; see `90_boundary_audit.md` §4) |
| G2 | Every `EC-*` row has an observed counterexample and a decided carrier | **passed** 2026-11-10: 44 of 44 rows are frozen. The last seven (`EC-10`, `EC-16`, `EC-18`, `EC-23`, `EC-24`, `EC-25`, `EC-26`) are absent-in-v0 decisions with measured counterexamples in `EXP-0096` and decided carriers in `ADR-0094`; `EC-43` and `EC-44` are the M6 additions (`ADR-0118`, `ADR-0119`) |
| G3 | Each ISA has >= 3 positive and >= 2 negative vectors passing two-source checks | **satisfied for x86, AArch64 and RV64** (2026-11-10: x86: 85 positive, 527 negative; AArch64: 26 positive, 69 negative; RV64: 17 positive, 23 negative; 128 + 619 in total after the `47a383b` audit) |

### Phase 3 exit criteria

Phase 3 closes on the gate set and the directive's three experiment matrices, not
on a slice count:

- **Gate G3** — each ISA carries at least three positive and two negative
  vectors whose bytes and diagnostics match a recorded oracle
  (`06_validation_matrix.md` §5). x86 has 72/477, AArch64 20/57 and RV64 9/12.
- **Directive §6.1** (x86-64) — all nine items are carried by the positive rows
  in `06_validation_matrix.md` §4: register transfer, immediate arithmetic, two
  legal encodings of one operation, displacement widths, prefix rules,
  RIP-relative addressing, short and near branches, external-call fixups, and
  the `legacy`/`vex`/`evex` family choice.
- **Directive §6.2** (AArch64) — all eight items: register arithmetic,
  immediate arithmetic, load/store addressing kinds, conditional branch,
  unconditional branch or call, `adrp`+`:lo12:`, a shifted or scaled immediate
  field, and a target-specific modifier.
- **Directive §6.3** (RV64) — all eight items: integer arithmetic, I-type
  immediate, load/store, conditional branch, `jal`, scattered fields, RVC vs
  standard as separate forms, and the `auipc`+`lo12` pair.
- **Gate G2** — all 44 `EC` rows are frozen and each cites a measured
  counterexample and a decided carrier (`ADR-0094`, plus `EC-42`/`EC-43`/`EC-44`
  from M6). `EXP-0096` records the
  seven families v0 keeps absent with no fixture; the rejection path is
  `E-FORM-001`, already pinned by the `N01` family.
- **Determinism** — `EXP-R1`, `EXP-R2`, `EXP-R4`, `EXP-R5` and `EXP-R6` passed
  on this host at close-out (`EXP-0033`); `EXP-R3` was outside the Phase 3 claim
  then and now passes in Phase 4 on three CI hosts (`EXP-0033` §6).

## Decisions

| ID | Decision | State |
|---|---|---|
| ADR-0001 | Self-owned encoding core (Route C); XirAsm/LLVM are temporary oracles | accepted |
| ADR-0002 | Docs-first with explicit context anchors | accepted |
| ADR-0003 | Rust prototype, Level 0/1 output | accepted (provisional); OD-03 narrowed v0 to Level 0 |
| ADR-0004 | `form_id` carries every encoding decision; `encoding_choices` removed | accepted 2026-11-04 |
| ADR-0005 | AArch64 knowledge comes from the Arm MRS 2026-06; no XirAsm file is copied, the Arm notice ships with the table | accepted 2026-11-04 |
| ADR-0006 | The AArch64 source is pinned by MRS *packaging*: archive hash + both file hashes + the BSD-3-Clause licence sentence; the release block alone is not a pin | accepted 2026-11-04 |
| ADR-0007 | RV64 knowledge comes from the UDB resolved spec, pinned by archive hash + eight node hashes + the BSD-3-Clause-Clear header; `left_shift` is a fixup transform, and its `not: 0` rule was the reason `c.addi` stayed out of v0 until ADR-0009 gave the slot an `excluded` list | accepted 2026-11-04 |
| ADR-0008 | A memory operand is one operand per encoded field (`base`/`disp`/`index`/`scale`); the addressing form is a `form_id` variant, never a payload shape or a value-driven choice | accepted 2026-11-04 |
| ADR-0009 | A slot may declare `excluded`: a closed, strictly increasing list of exact integers inside its domain; absent means none, a hit is `E-RANGE-004`, and the check is a lookup, never a predicate | accepted 2026-11-04 |
| ADR-0010 | An RV64 low half names its high half: `pc_reference_rule: pcrel_hi` puts `P` at the paired `hi`'s site, `value_transform: pcrel_lo12` masks the displaced value, a `lo` addend must be 0 (`E-FIXUP-009`), and a group is one `hi` with at least one `lo` | accepted 2026-11-04 |
| ADR-0011 | AArch64 `add` with `LSL #12` is a second `form_id` (`-lsl12`) in `0.2.0`: the form pins `sh = 1`, the slot stays `imm12` field content, no slot-level scale is added, and a literal that only fits the other form is `E-RANGE-001` (`N18a`/`N18b`) | accepted 2026-11-04 |
| ADR-0012 | An AArch64 condition is an operand, not sixteen forms: `aarch64:b.cond/imm19` in `0.3.0` carries `cond` as `aarch64.cond`/`cond4` at bits 0–3 (range `0..15`, no `excluded` — all sixteen are defined), and the `imm19` target is field content with a `pcrel_begin` + `scale(2)` fixup; `cond = 16` is `E-RANGE-001` (`N03`), a displacement past `imm19` is `E-RANGE-002` (`N04c`) | accepted 2026-11-04 |
| ADR-0013 | AArch64 addressing kinds are forms, and `disp` is field content: `0.4.0` adds five load/store rows (`ldr` imm12/imm9-pre/imm9-post, `ldur` imm9, `str` imm12), `imm12` counts 8-byte units for these `x` rows, `imm9` counts signed bytes, `align_bits` stays 0, and the register-offset, literal and store-`imm9` kinds stay absent (`E-FORM-001`) | accepted 2026-11-04 |
| ADR-0014 | The AArch64 `movz` lane is a form: `0.5.0` adds four rows (`-lsl0` … `-lsl48`), each pinning its `hw` value, with `imm16` as field content in `0…65535`; no slot scale and no `lsl` modifier, a pre-scaled literal is `E-RANGE-001` (`N18c`), an `lsl #8` lane is `E-FORM-001` (`N01d`), and `movk`/`movn`/`w`/the `mov` alias stay out | accepted 2026-11-04 |
| ADR-0015 | An AArch64 shift keyword is a form and the amount is field content: `0.6.0` adds three rows (`-imm6-lsl`/`-imm6-lsr`/`-imm6-asr`), each pinning `shift` (22+2), with `imm6` as an `aarch64.imm`/`imm6` operand over `0…63` at `[10,6]` and `align_bits 0`; a modifier never writes a bit, so the same shift stated as `{"name":"lsl","value":3}` on `-lsl0` is `E-OPERAND-003` (`N19`), an amount of 64 is `E-RANGE-001` (`N03-imm6`), `imm6 = 0` on `-imm6-lsl` is the same word as `-lsl0` and both stay, and the extend family/`sub`/the `w` rows stay out (`E-FORM-001`, `N01e`) | accepted 2026-11-04 |
| ADR-0016 | An AArch64 extend keyword is a form and the amount is field content with an excluded tail: `0.7.0` adds eight rows, one per `option` value (`-imm3-uxtb` … `-imm3-sxtx`), with `option` pinned at 15–13, `src2` a `w` register on the six `[su]xt[bhw]` rows and an `x` register on the two `[su]xtx` rows, and `imm3` as an `aarch64.imm`/`imm3` operand at `[10,3]` over `0…4` with `excluded: [5,6,7]`; `imm3 = 8` is `E-RANGE-001` (`N03-imm3`), `5` is `E-RANGE-004` (`N16c`), a `w` operand on a shifted row is `E-OPERAND-001` (`N02b`), and the extended `sub` node/`adds`/`subs`/the 32-bit node stay out (`E-FORM-001`, `N01f`, `N01g`, `N01h`; the decision-7 scope is narrowed by ADR-0017) | accepted 2026-11-04 |
| ADR-0017 | An AArch64 mnemonic is a form family: `0.8.0` adds six `sub` rows (`-lsl0`, `-imm12-lsl0`/`-lsl12`, `-imm6-lsl`/`-lsr`/`-asr`) from `SUB_64_addsub_shift`/`SUB_64_addsub_imm`, which are the `ADD_64` nodes with `op` at 30+1 fixed to `1` by the node itself, so no plan field names the mnemonic bit; the `sh`/`shift`/`imm6` treatment and slot shapes are inherited from ADR-0011/ADR-0015, register 31 in these rows is `xzr` (not `sp`), `subs` and the `sf = 0` node are `E-FORM-001` (`N01g`/`N01h`), and a literal outside the named `sh` half is `E-RANGE-001` (`N18d`) | accepted 2026-11-04 |
| ADR-0018 | An AArch64 flag-setting mnemonic is a form family and `S = 1` is the node's: `0.9.0` adds twelve rows, six `adds` and six `subs` (`-lsl0`, `-imm12-lsl0`/`-lsl12`, `-imm6-lsl`/`-lsr`/`-asr` each) from `ADDS_64_addsub_shift`/`ADDS_64S_addsub_imm`/`SUBS_64_addsub_shift`/`SUBS_64S_addsub_imm`, the four nodes already read with `S` at 29+1 fixed to `1`, so no plan field names the bit; every word is its `add`/`sub` twin with bit 29 set, the `sh`/`shift`/`imm6` treatment and slot shapes are inherited, register 31 is `xzr` (the extended S nodes are absent), `cmp`/`cmn` are a two-operand alias family and out (`N01i`), the `sf = 0` S nodes are out (`N01j`), and a literal outside the named `sh` half is `E-RANGE-001` (`N18e`) | accepted 2026-11-04 |
| ADR-0019 | The AArch64 32-bit width is a form family and `sf = 0` is the node's: `0.10.0` adds twenty-four rows, the six `add`/`sub`/`adds`/`subs` shapes each repeated on the eight `*_32*` nodes, so `w32-…` vs `x64-…` in the `form_id` is the width and no plan field names the bit; every register slot is `aarch64.gpr32`/`w32` (an `x64` operand is `E-OPERAND-001`, `N02c`), register 31 stays a plain `reg_number` whose meaning is the node's role (no `sp` operand kind), the 32-bit `imm6` declares `bits: 6` with `excluded: [32…63]` (`imm6 = 32` is `E-RANGE-004`, `N16d`), `4096` on `-lsl0` stays `E-RANGE-001` (`N18f`), and the extended 32-bit nodes plus `cmp`/`cmn` stay out (`E-FORM-001`, `N01k`) | accepted 2026-11-04 |
| ADR-0020 | The AArch64 extended-register mnemonic family repeats the `add` shapes on the `op = 1`/`S = 1` nodes: `0.11.0` adds twenty-four rows, the eight `option` rows each on `SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext`, so the mnemonic is the form family and no plan field names `op` or `S`; the keyword still fixes `src2`'s width (six `[su]xt[bhw]` take `w32`, `uxtx`/`sxtx` take `x64`, `N02d`), `imm3` keeps `excluded: [5, 6, 7]` (`N16e`), register 31 stays a plain `reg_number` whose meaning is the node's role (`sp` only in `sub`'s `Rd`), and the 32-bit extended nodes plus `cmp`/`cmn` stay out (`E-FORM-001`, `N01l`) | accepted 2026-11-04 |
| ADR-0021 | `cmp`/`cmn` are a separate two-operand alias family: `0.12.0` adds forty rows, each the `subs`/`adds` row of the same layout and width with `Rd` pinned to 31 and the `dest` slot removed, built from the base node because the MRS alias nodes carry no `encoding`; the alias node is the pairing check (`operation_id`, `condition` `Rd == '11111'`, `preferred`, width), so it never supplies a bit field; the 32-bit extended aliases stay out with their base rows (`N01l`), a `dest` on a `cmp`/`cmn` row is `E-OPERAND-002` (`N02e`), and `N01i`/`N01m` become version boundaries against `0.11.0` | accepted 2026-11-04 |
| ADR-0022 | The store half of the addressing kinds is the same decision: `0.13.0` adds three rows (`str/x64-base-imm9-pre`, `str/x64-base-imm9-post`, `stur/x64-base-imm9`), each the load row's layout with `opc = 00` and `Rt` as the stored register, so the kind stays a `form_id`, `disp` keeps ADR-0013's field-content rule (`imm9`, signed bytes, `-256…255`, `align_bits 0`), the slot list stays `src`/`base`/`disp`, `N03` pins the two range ends and `N01n` the `0.12.0` version boundary, and no schema or Rust change is needed | accepted 2026-11-04 |
| ADR-0023 | The literal load carries its displacement in `imm19` and has no base register: `0.14.0` adds one row, `aarch64:ldr/x64-imm19`, from `LDR_64_loadlit` (`opc = 01`, pattern `0x58000000`), with `dest` at `[0,5]` and `target` at `[5,19]` and no `base`; the slot is the field (`align_bits 0`), a byte displacement is a `pcrel_begin` + `scale(2)` fixup with `range.bits 19`/`align_bits 2` and the byte range `−1048576…+1048572`, `imm19 = 262144` is `E-RANGE-002` (`N04d`), a 2-byte symbol offset is `E-RANGE-003` (`N20`, our own split of the assembler's one message), `N01o` is the `0.13.0` boundary, the `w`/`LDRSW`/`PRFM`/SIMD literals and register offset stay out, and no store literal exists | accepted 2026-11-04 |
| ADR-0024 | Register offset is a form family and `option`/`S` are form bits: `0.15.0` adds sixteen rows, `ldr`/`str` × `{lsl,uxtw,sxtw,sxtx}{0,3}`, from `LDR_64_ldst_regoff`/`STR_64_ldst_regoff`, which differ only in `opc`; `Rm` is an `index` slot at `[16,5]`, `option` (13+3) fixes both the keyword and the index width (`lsl`/`sxtx` take `x64`, `uxtw`/`sxtw` take `w32`), and `S` (12+1) is the only scale carrier (`#0` or `#3` on these `size = 11` rows), so neither is an operand; `lsl #0` is the same word as the bare spelling, `-lsl1`/`-lsl4` have no row (`N01q`), a `w32` index on a `-lsl0` row is `E-OPERAND-001` (`N02f`), a modifier stating `lsl #3` is `E-OPERAND-003` (`N19b`), `N01p` is the `0.14.0` boundary, the coarse `aarch64:ldr/x64-base-regoff` stays absent (`N01b`), the `w`/byte/halfword and `prfm` register offsets stay out, and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0025 | The 32-bit register offset is the same `option` family at `size = 10`: `0.16.0` adds sixteen rows, `ldr`/`str` × `{lsl,uxtw,sxtw,sxtx}{0,2}`, from `LDR_32_ldst_regoff`/`STR_32_ldst_regoff`, which are the 64-bit pair with `size = 10` and the same `opc` split; `option` keeps its keyword/width pairing (`lsl`/`sxtx` take `x64`, `uxtw`/`sxtw` take `w32`), `S` is still the only scale carrier but means `#2` on a 4-byte access, and only `Rt` changes class (`w32`), so `dest`/`src` are `aarch64.gpr32`/`w32` while `base` and the `x` index rows stay `x64`; `-lsl3` has no row at this width (`N01s`), a `w32` index on `-lsl0` or an `x64` destination is `E-OPERAND-001` (`N02g`/`N02h`), a modifier stating `lsl #2` is `E-OPERAND-003` (`N19c`), `N01r` is the `0.15.0` boundary, the `b`/`h` widths, the signed/extended loads and `prfm` stay out, and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0026 | `movk`/`movn` are the `movz` lane family one `opc` over: `0.17.0` adds eight rows, four `hw` lanes on each of `MOVK_64_movewide` (`opc = 11`) and `MOVN_64_movewide` (`opc = 00`), so the mnemonic is the node and no plan field names the operation (`EC-16`); `sf = 1`, `hw` at 21+2 and `Rd` at 0+5 are unchanged, `imm16` stays unsigned field content in `0…65535`, and `movn` stores the raw field rather than its complement; `-lsl8` has no row (`N01t`), the `w` lanes and the `mov` alias stay out (`N01v`/`N01w`), a `w32` destination is `E-OPERAND-001` (`N02i`), `imm16 = 65536` or a pre-scaled literal is `E-RANGE-001` (`N03-movk-imm16`, `N18g`), and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0027 | A RIP-relative memory operand is a form with no base register: `0.2.0` adds two rows, `x86:mov/r64-riprel32/legacy` (`REX.W 8B /r`, `mod = 00`, `r/m = 101`) and `x86:mov/riprel32-r64/legacy` (`REX.W 89 /r`), so the opcode direction is still the form (`EC-27`) and the addressing shape is the form rather than an operand value (`EC-34`); `ModRM.reg` is the destination or source at `[19,3]`, `disp32` is the last field at `[24,32]`, and the displacement is a `target` operand (`x86.rel`/`riprel32`, signed 32) with a `pcrel_end` fixup and `addend 0`, because RIP is not in `x86.gpr64` and no slot carries its number; `disp32 = 2147483648` is `E-RANGE-002` (`N04e`), an extra `base` is `E-OPERAND-002` (`N02j`), `N01x` is the `0.1.0` boundary, and an operand/fixup target mismatch is `E-FIXUP-001` (`N07b`); base+disp8/disp32 (`X86-P4`), SIB, the `0x67` prefix (`X86-P5`) and `moffs` stay out, and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0028 | Base+displacement is eight rows across four shapes: `0.3.0` adds load/store × `disp8`/`disp32` × base-in-`r/m`/`%rsp`-fixed, so `mod` and the SIB byte are template rather than operand-driven; the general rows carry `base` at `[16,3]` with `excluded: [4]` (`%rsp` would force a SIB byte, `E-RANGE-004`), the `%rsp` rows fix `r/m = 100`, `SIB = 24` and the base, `disp8`/`disp32` are signed field content, `disp8 = 128` is `E-RANGE-001` (`N03-disp8-out-of-range`), `%rsp` on a general row is `E-RANGE-004` (`N16f`), `N01y` is the `0.2.0` boundary, and index/scale, `mod = 00`, `r8`–`r15`, `0x67` and `moffs` stay out | accepted 2026-11-05 |
| ADR-0029 | The operand-size prefix and the high-byte registers are form facts: `0.4.0` adds five rows — two 16-bit directions with `0x66` as template byte 0, the high-byte row (`x86.gpr8h`, numbers 4–7 = `ah`/`ch`/`dh`/`bh`), and the low-byte pair split by REX (REX-less 0–3, REX 4–7 = `spl`/`bpl`/`sil`/`dil`) — so the prefix is never chosen from an operand value; the exclusion lists keep the three 8-bit rows disjoint (`88 e5` is `ah`/`ch`, `40 88 e5` is `spl`/`bpl`), and the loader rejects a `gpr8h` slot in a REX template or a REX-less `gpr8` slot that does not exclude 4–7 (`E-DEF-001`); `N01z` is the `0.3.0` boundary, `N02k` is a `gpr8h` operand on the REX row (`E-OPERAND-001` ×2), `N16g` is number 4 in the REX-less row (`E-RANGE-004`), and `8A`, memory operands at these widths, `0x67` and `r8`–`r15` stay out | accepted 2026-11-05 |
| ADR-0030 | The x86 encoding family is a form fact: `0.5.0` adds three rows at `xmm` width — `x86:movaps/xmm-xmm/legacy` (`0f28c0`, 3 bytes), `x86:vmovaps/xmm-xmm/vex` (`c5f828c0`, 4 bytes) and `x86:vmovaps/xmm-xmm/evex` (`62f17c0828c0`, 6 bytes) — so `/legacy`, `/vex` or `/evex` in the `form_id` is the family, the prefix is template, and the slots move with the prefix length (`[19,3]`/`[16,3]`, `[27,3]`/`[24,3]`, `[43,3]`/`[40,3]`); `x86.xmm` is one kind, registers 0–7 only, and the VEX/EVEX extension bits are template constants; `0.5.0` declares `avx`/`avx512f`/`avx512vl` for its EVEX.128 row, so a plan must declare the same set (`E-TARGET-001`, `N06`), while `E-TARGET-003` stays unreachable; `N01aa` is the unfamilied id, `N01ab` the `0.4.0` boundary, `N02l` a `zmm` operand on the `xmm` row (`E-OPERAND-001` ×2) and `N14b` is `xmm8` (`E-OPERAND-004`); memory operands, masking, `ymm`/`zmm`, the three-byte `C4` VEX form and `movapd`/`movdqa` stay out | accepted 2026-11-05 |
| ADR-0031 | Every plan and definition object is closed: an unknown field is `E-PLAN-003` (plan) or `E-DEF-001` (definition), there is no `x_*` namespace and no extension object in `fmp/0.1`; `enabled_extensions` is an equality-checked target set (`E-TARGET-001`) | accepted 2026-11-05 |
| ADR-0032 | Canonical JSON is the v0 wire form: the reader accepts any valid JSON spelling of the same value, and binary transport is deferred to a later `format_version` | accepted 2026-11-05 |
| ADR-0033 | A `x86.gpr64` operand is four bits: the low three are the `ModRM` field and bit 3 is a placement into the form's existing `REX` byte (`REX.B` = `[0,1]` for `r/m`, `REX.R` = `[2,1]` for `reg`); one row per operand shape, not per extension combination; `0.6.0` widens the six register-direct rows, base+disp, 8/16-bit, high-byte and SSE/VEX/EVEX rows stay narrow, and `REX.X` is unexercised | accepted 2026-11-05 |
| ADR-0034 | A memory base is four bits and the SIB byte is a form fact: `0.7.0` widens the twelve base+disp rows (`REX.R`/`REX.B`), the general rows exclude the SIB-forcing values `4` and `12` (`E-RANGE-004`), and `%r12` gets four fixed-base rows that differ from `%rsp` only in `REX.B`; index/scale and `REX.X` are a separate shape | accepted 2026-11-05 |
| ADR-0035 | The SIB index and scale are operands and `REX.X` extends the index: `0.8.0` adds four `base + index*scale + disp` rows whose template fixes `r/m = 100` and the `SIB` byte; `base` is four bits with no exclusion (`%rsp`/`%r12` are ordinary bases), `index` is four bits excluding `4` (`SIB.index = 100` with `REX.X = 0` means "no index", `E-RANGE-004`), and the scale is the two-bit field content `0…3` carried as `role: imm`/`kind: x86.scale`/`target_type: scale2`, never the multiplier (`E-RANGE-001`); `mod = 00` and a base-only `SIB` row stay out | accepted 2026-11-05 |
| ADR-0036 | The SSE memory operand is one family and EVEX `disp8` is compressed: `0.9.0` adds twelve `movaps`/`vmovaps` rows (load/store × `disp8`/`disp32` × `legacy`/`vex`/`evex`); the base and the `xmm` register stay three bits in all three families because the legacy templates have no `REX`, two-byte `C5` has no `B`, and EVEX's `B̄`/`R̄` are inverted (so `r8`/`xmm8` are `E-OPERAND-004`, `%rsp` is `E-RANGE-004`); the EVEX `disp8` operand is the compressed field content (`target_type: disp8x16`, unit 16, `-128…127`), while `disp32` carries the byte offset (`EC-38`, `EC-39`) | accepted 2026-11-05 |
| ADR-0037 | The SSE base reaches `r8`–`r15` through a per-family window: `0.10.0` widens the four EVEX rows in place (base `[13,1]` inverted + `[40,3]`, `excluded: [4, 12]`, because `62 f1 …` and `62 d1 …` are the same length) and adds eight `-base-ext` rows for legacy (`40 0F 28/29 /r`, `REX.B` at `[0,1]`) and three-byte VEX (`C4 C1 78 28/29 /r`, inverted `B̄` at `[13,1]`), because reaching the high base adds a byte; the two windows exclude each other's values, so exactly one row encodes a base; `placement.invert` (default false) writes its chunk complemented, which is `EC-40`, and the `xmm` slot stays three bits (`xmm8` is `E-OPERAND-004`); `%r12` stays `E-RANGE-004` in both windows | accepted 2026-11-05 |
| ADR-0038 | The SSE register reaches `xmm8`–`xmm15` through per-family windows: `0.11.0` widens `x86.xmm` to four bits, keeps the EVEX register-direct pair and the VEX/EVEX memory rows in place (`R̄` at bit 15 for `ModRM.reg`, `B̄` at bit 13 for the EVEX source and every EVEX/VEX base), and adds three legacy `40 0F 28 /r` register windows (`REX.R`/`REX.B`, the all-low corner staying with the 3-byte row), two VEX register windows (`C5 78 29 /r` for a high source with a low destination, `C4 41 78 28 /r` for both high) and four `REX.R` legacy memory rows whose `REX` byte also carries a 4-bit base; `llvm-mc` encodes `vmovaps %xmm8, %xmm0` as both `c5 78 29 c0` (four bytes) and `c4 c1 78 28 c0` (five), so the table pins the opcode-29 form (`EC-09`); per-slot `excluded` keeps every window disjoint and `xmm16` is `E-OPERAND-004` | accepted 2026-11-05 |
| ADR-0039 | A no-displacement SSE memory operand is a third width, not a zero value: `0.12.0` adds twelve `mod = 00` rows (six legacy, four VEX, two EVEX) with no `disp` slot, because `0f 28 00` (three bytes) and `0f 28 40 00` (four bytes, `mod = 01`, `disp8 = 0`) decode as the same `movaps (%rax), %xmm0` and `llvm-mc` canonicalizes `movaps 0(%rax), %xmm0` to the short form, so an encoder that chose would make `INV-02`'s decision; the legacy family needs three windows (`REX.R` for a high register, `REX.B` for a high base, the `REX.R` row carrying both bits), VEX keeps `C5` for a low base and needs `C4 C1 78` for a high one, and EVEX stays six bytes; `%rsp`/`%r12` force a `SIB` byte and `%rbp`/`%r13` collide with `r/m = 101` under `mod = 00`, so both are `E-RANGE-004` on the new rows and must name the `disp8` row with displacement `0`; `EC-02` gains its third width in place and no new `EC` row is needed | accepted 2026-11-05 |
| ADR-0040 | The EVEX vector register is five bits: `0.13.0` widens the `xmm` slot of the seven EVEX rows in place (`ModRM.reg` bit 4 = inverted `R̄'` at `[12,1]`, bit 3 = inverted `R̄` at `[15,1]`; register-direct `ModRM.rm` bit 4 = inverted `X̄` at `[14,1]`, bit 3 = inverted `B̄` at `[13,1]`), so `xmm16`–`xmm31` become reachable with no new row and no length change: `vmovaps %xmm31, %xmm30` is `62 01 7c 08 28 f7`, six bytes. Writing the two register bits raw gives `62 f1 …` = `%xmm7, %xmm6`, dropping `R̄'` gives `62 11 …` = `%xmm31, %xmm14`, and leaving `X̄` set gives `62 41 …` = `%xmm15, %xmm30`; memory rows have no `SIB` field, so `X̄` stays at its template value there. Legacy and VEX have no second extension bit, so their `xmm` slots stay at three/four bits (`xmm16` is `E-OPERAND-004`, `N14o`), `xmm32` is outside the five-bit field (`N14n`), and `EC-06`/`EC-40` are revised in place rather than adding a row | accepted 2026-11-05 |
| ADR-0041 | Vector width is a form fact: `0.14.0` adds the five register-direct `ymm`/`zmm` rows — `x86:vmovaps/ymm-ymm/vex` (`c5fc28c0`, `L = 1`, dest `[15,1]` inverted `R̄` + `[27,3]`, src `[24,3]`), `x86:vmovaps/ymm-ymm-src-ext/vex` (`c57c29c0`, opcode 29 puts a high source in `ModRM.reg`, `excluded: [0…7]`), `x86:vmovaps/ymm-ymm-both-ext/vex` (`c4417c28c0`, three-byte `C4`, both slots `excluded: [0…7]`), `x86:vmovaps/ymm-ymm/evex` (`62f17c2828c0`, `L'L = 10`) and `x86:vmovaps/zmm-zmm/evex` (`62f17c4828c0`, `L'L = 11`) — plus the kinds `x86.ymm`/`ymm` and `x86.zmm`/`zmm`. The mnemonic never changes, only the prefix field, so a width operand or modifier would make the materializer select a form (`INV-02`); the EVEX rows keep the `0.13.0` five register bits. A width mismatch is `E-OPERAND-001` (`N02n`), legacy has no `ymm` row (`N01aj`), `ymm16` is outside the VEX field (`N14p`) and `zmm32` the EVEX field end (`N14q`); `EC-09` is revised in place (family + width are one prefix-choice decision) and the frozen count stays 31 of 40. Memory forms at these widths would revise `EC-39` and stay out | accepted 2026-11-05 |
| ADR-0042 | The EVEX compressed-displacement unit is a form fact: `0.15.0` adds twelve memory rows — the six `0.13.0` `xmm` memory shapes at `ymm` (`62 f1 7c 28 …`) and `zmm` (`62 f1 7c 48 …`) — and revises `EC-39` in place so `N` is the row's `target_type` (`disp8x16`/`disp8x32`/`disp8x64`), never a division. One field content means three displacements: `0x01` decodes as `16`, `32` and `64` bytes under `P2 = 08`/`28`/`48`, so the plan's displacement stays the field content (`−128 … 127`), and the byte offsets it reaches are `−4096 … 4064` at `N = 32` and `−8192 … 8128` at `N = 64` while `4096`/`8192` and values the unit cannot divide (`28`, `60`) are `disp32` rows. Only `P2` differs between the widths; the five-bit vector slot and the four-bit base window with its `[4, 12]`/`[4, 5, 12, 13]` exclusions carry over unchanged, `disp8x16` on a `disp8x32` row is `E-OPERAND-001` (`N02p`), content `128` is `E-RANGE-001` (`N03e`), `ymm32` is `E-OPERAND-004` (`N14r`), `N01ak` is the `0.14.0` boundary, and VEX.256 memory needs no new fact (`c5 fc 28 40 20` is a plain `disp8`) so it stays absent at `0.15.0` (`N01al`; `ADR-0043` adds the rows as coverage); no schema or Rust change | accepted 2026-11-05 |
| ADR-0043 | VEX.256 memory is coverage, not a new fact: `0.16.0` adds twelve rows mirroring the VEX memory rows of `0.11.0`/`0.12.0` at `L = 1` — the low-base two-byte window (`c5 fc …`, three-bit base, `%rsp` excluded) and the high-base three-byte window (`c4 c1 7c …`, `B̄` at bit 13 inverted, `r8`–`r15` minus `%r12`) — each with the `disp8` pair, the `disp32` pair and the `mod = 00` pair. The vector slot stays four bits (`R̄` + `ModRM.reg`), now `x86.ymm`/`ymm`; VEX has no compression, so `32(%rax)` is the plain byte `20` and needs no `disp8xN` name (`EC-02`, `EC-35`). No `EC` row is added or revised; a `zmm` operand is `E-OPERAND-001` (`N02q`), `ymm16` is `E-OPERAND-004` (`N14s`), `%rbp`/`%r12` are `E-RANGE-004` (`N16r`/`N16s`), content `128` is `E-RANGE-001` (`N03f`), and `N01al`/`N01am` are the `0.15.0` boundaries; no schema or Rust change | accepted 2026-11-05 |
| ADR-0044 | The 8- and 16-bit `mov` memory rows reuse the prefix and register-set facts: `0.17.0` adds sixteen rows — four word rows (`66 8b`/`66 89`, `x86.gpr16` at `[19,3]`, base `[16,3]`, displacement `[24,8]`/`[24,32]`) and twelve byte rows in the three `0.4.0` sets (REX-less low `88`/`8a` numbers 0–3 at `ModRM` bit 8, high `88`/`8a` numbers 4–7, and `40 88`/`40 8a` numbers 4–7 with `ModRM` back at bit 16) — and adds or revises no `EC` row, because `EC-02`, `EC-27`, `EC-28`, `EC-36` and `EC-38` already state every field. The `0x66` byte is template byte 0 ahead of any REX byte, so no operand selects a width; the byte sets stay disjoint (`x86.gpr8h` on a `-rex` row is `E-OPERAND-001`, `N02s`; number 4 on the REX-less low row is `E-RANGE-004`, `N16t`); every base is the three-bit window 0–7 minus `%rsp` (`E-RANGE-004`, `N16u`), so `r8`–`r15` wait for `-base-ext` rows (`E-OPERAND-004`, `N14t`); a `gpr32` operand is `E-OPERAND-001` (`N02r`), content `128` on `disp8` is `E-RANGE-001` (`N03g`), and `N01an` is the `0.16.0` boundary; no schema or Rust change | accepted 2026-11-05 |
| ADR-0045 | The 8/16-bit memory bases reach `r8`–`r15`: `0.18.0` adds eight `-base-ext` rows (word load/store × `disp8`/`disp32`, then REX-less low-byte load/store × `disp8`/`disp32`) and widens the four `40`-prefixed byte rows from three to four base bits in place. The word rows put `REX.B` at `[8,1]` because the `66` byte stays template byte 0 and the byte rows at `[0,1]`; the word and low-byte rows have no `REX` byte, so reaching a high base adds one and the length must be the form's (`INV-04`), while the `40` rows already carry it and widen for free. The byte axis is a partition: the new rows carry numbers 0–3 and exclude 4–7, the widened rows carry 4–7, and the high-byte set has no encoding with a high base because the `REX` byte renames `ah`–`bh` to `spl`–`dil`. Extension rows exclude `0`–`7` and `%r12`, the widened rows `%rsp` and `%r12`, so one `(register, base)` pair names one row; a low base on an extension row, `%r12` on either window, base `16` and a `gpr8h` operand are `E-RANGE-004`/`E-OPERAND-004`/`E-OPERAND-001` (`N16v`/`N16w`/`N16x`/`N14u`/`N02t`), and `N01ao` is the `0.17.0` boundary. The definition gates learn to skip a leading `0x66` before looking for the `REX` byte, pinned by a new loader unit test; no `EC` row is added, `EC-38` is revised in place, and there is no schema change | accepted 2026-11-05 |
| ADR-0046 | The 8/16-bit memory bases reach `%rsp` and `%r12` through fixed-base `SIB` rows: `0.19.0` appends twenty-eight rows — word, REX-less low byte, high byte and `40`-prefixed byte, each load/store × `disp8`/`disp32`, at `%rsp` and `%r12` except the high-byte family, which gets `%rsp` only because `movb %ah, 8(%r12)` has no encoding (the `REX.B` byte that names `%r12` renames `ah` to `spl`). `%rsp` sets `r/m = 100` and spends a `SIB` byte (`24`), `%r12` spends `REX.B` on top, so the base leaves the operand list and enters the template: the row carries only the register and the displacement, the shape `0.3.0`/`0.7.0` gave `movq`, and no operand value changes a length (`INV-04`). The prefixes are template bytes, so `ModRM.reg`/`disp` move one byte later than on the `-base-disp*` rows (`[19,3]`/`[32,…]` on the word `%rsp` rows, `[27,3]`/`[40,…]` on the word `%r12` rows, `[11,3]`/`[24,…]` on the REX-less byte `%rsp` rows, and `[19,3]`/`[32,…]` on every row whose template carries a `REX` byte); the register windows stay 0–3 for the low rows, 4–7 for the `40` rows and 4–7 for the high-byte rows. Naming a row against `0.18.0` and the absent high-byte `%r12` row are `E-FORM-001` (`N01ap`/`N01aq`), a `gpr16` on a byte row is `E-OPERAND-001` (`N02u`), content `128` is `E-RANGE-001` (`N03h`), register `8` is `E-OPERAND-004` (`N14v`), and number `0` on a `40` row is `E-RANGE-004` (`N16y`); no `EC` row is added, `EC-35` and `EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0047 | The SSE `movaps`/`vmovaps` memory rows reach `%rsp` and `%r12` through fixed-base `SIB` rows: `0.20.0` appends sixteen rows — legacy and VEX, load/store × `disp8`/`disp32` × both bases — with the base in the template and the row carrying only the register and the displacement. `%rsp` sets `r/m = 100` and spends the `SIB` byte `24`; legacy `%r12` adds `REX.B` (`41`), and VEX `%r12` forces the three-byte prefix (`c4 c1 78`) because the two-byte form cannot carry `B = 1`, so no operand value changes a length (`INV-04`). The prefixes are template bytes, so `ModRM.reg`/`disp` move one byte later: `[19,3]`/`[32,…]` on legacy `%rsp`, `[27,3]`/`[40,…]` on legacy `%r12` and VEX `%rsp`, `[35,3]`/`[48,…]` on VEX `%r12`. The register windows are inherited rather than widened: the legacy field stays three bits (`xmm8` is `E-OPERAND-004`, `N14w`) and the VEX slot keeps its inverted `R` bit, so it already reaches `xmm8`–`xmm15` at no length cost. Naming a row against `0.19.0` and the absent `mod = 00` shape are `E-FORM-001` (`N01ar`/`N01as`), a `gpr64` operand is `E-OPERAND-001` (`N02v`), a third `base` operand is `E-OPERAND-002` (`N02w`), and content `128` is `E-RANGE-001` (`N03i`); no `EC` row is added, `EC-35` and `EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0048 | The EVEX `vmovaps` memory rows reach `%rsp` and `%r12` through fixed-base `SIB` rows: `0.21.0` appends twenty-four rows — three widths (`xmm`/`ymm`/`zmm`) × load/store × `disp8*N`/`disp32` × both bases — with the base in the template and the row carrying only the register and the displacement. `%rsp` sets `r/m = 100` and spends the `SIB` byte `24`; `%r12` spends the same byte and no prefix byte, because its fourth bit is already the inverted `B̄` in `P0` (`62 f1 ...` vs `62 d1 ...`), so the two bases are the same length and no operand value changes a length (`INV-04`). The prefix does not grow, so the vector slot stays `[43,3]` with its inverted `R̄`/`R̄'` bits and only the displacement moves, from `[48,…]` to `[56,…]`; the five-bit slot already reaches `xmm31` at no length cost. `disp8*N` content is still the same `disp / N` (`16`/`32`/`64` are content `1`), and `8(%rsp)` promotes to `disp32` rather than truncating. Naming a row against `0.20.0` and the absent `mod = 00` shape are `E-FORM-001` (`N01at`/`N01au`), a `gpr64` operand is two `E-OPERAND-001` (`N02x`), a third `base` operand is `E-OPERAND-002` (`N02y`), content `128` is `E-RANGE-001` (`N03j`), and register `32` is `E-OPERAND-004` (`N14x`); no `EC` row is added, `EC-35` and `EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0049 | The EVEX `vmovaps` no-displacement rows take `%rsp` and `%r12` as `SIB` bases: `0.22.0` appends twelve rows — three widths × load/store × both bases — at `mod = 00`, where `r/m = 100` moves the base into the `SIB` byte and leaves no displacement slot, so each row is seven bytes and carries only the vector register. `%rsp` is `62 f1 7c 08 28 04 24`, `%r12` is `62 d1 7c 08 28 04 24`; the two bases still differ only in the inverted `B̄` in `P0`, so a base never changes the length (`INV-04`). The prefix does not grow, so the vector slot stays `[43,3]` with its inverted `R̄`/`R̄'` bits; there is no `disp` slot, so a displacement operand is `E-OPERAND-002` rather than a silently ignored offset, and `llvm-mc` canonicalizes `0(%rsp)` to `(%rsp)`, so the shape is the only encoding of a zero offset. `%rbp`/`%r13` cannot use it (`mod = 00`, `r/m = 101` is RIP-relative) and keep `62 … 45 00` on the `-base` row. Naming a row against `0.21.0` and the absent `%rbp` shape are `E-FORM-001` (`N01av`/`N01aw`), a `gpr64` operand is two `E-OPERAND-001` (`N02z`), an extra `disp` operand is `E-OPERAND-002` (`N02aa`), register `32` is `E-OPERAND-004` (`N14y`), and `%rsp` on the general `xmm-base` row is `E-RANGE-004` (`N16z`); no `EC` row is added, `EC-02`/`EC-35`/`EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0050 | The EVEX `vmovaps` memory rows take a `SIB` index and a scale: `0.23.0` appends eighteen rows — three widths × load/store × none/`disp8*N`/`disp32` — with the base as an operand again and the `SIB` byte operand-owned. `r/m = 100` announces the byte, so `ModRM` is `04`/`44`/`84`; it sits at bits 48–55 with base `[48,3]` plus the inverted `B̄` at `[13,1]`, index `[51,3]` plus the inverted `X̄` at `[14,1]`, and scale `[54,2]`, while the prefix stays four bytes and the vector slot stays `[43,3]`. `(%rsp,%rax,1)` is `62 f1 7c 08 28 04 04` and `(%rsp,%r12,1)` is `62 b1 7c 08 28 04 24`, so `X̄` is the index's fourth bit, exactly as `EC-40` uses it. The index excludes `4` (the "no index" encoding, `E-RANGE-004`, `N16aa`) while `12` is legal; the scale is field content `0…3` over `1 << content`, never the multiplier. On the `mod = 00` rows `SIB.base = 101` means "no base, `disp32`", so `%rbp`/`%r13` are excluded there only (`N16ab`) and keep the `disp8*N = 0` row, `62 f1 7c 08 28 44 05 00`; `llvm-mc` also canonicalizes `0(%rax,%rcx,1)` to the seven-byte no-displacement row. Naming a row against `0.22.0` is `E-FORM-001` (`N01ax`/`N01ay`), the scale as `x86.imm` is `E-OPERAND-001` (`N02ab`), an extra `disp` operand is `E-OPERAND-002` (`N02ac`); no `EC` row is added, `EC-02`/`EC-35`/`EC-37`/`EC-40` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0051 | The EVEX `vmovaps` memory rows accept an index with no base: `0.24.0` appends six rows — three widths × load/store, `disp32` only — and the `base` role disappears. `mod = 00` with `SIB.base = 101` means "no base, `disp32`", so the template is `62 f1 7c <L'L> <28|29> 04 05 00 00 00 00` and every row is eleven bytes, the displacement slot present even at offset zero. `SIB` bits 48–50 are the constant `101`; the index is still `[51,3]` plus the inverted `X̄` at `[14,1]` and excludes `4`, the scale is still `[54,2]` field content, and `disp32` is signed content at `[56,32]`. `(,%rax,4)` is `62 f1 7c 08 28 0c 85 00 00 00 00` and `-4096(,%r12,8), %xmm3` is `62 b1 7c 08 28 1c e5 00 f0 ff ff`. The operand sequence is `dest`/`src`, `index`, `imm`, `disp`, so a supplied base is `E-OPERAND-002` (`N02ad`), the scale as `x86.imm` is `E-OPERAND-001` (`N02ae`), `disp32` content `2147483648` is `E-RANGE-001` (`N03k`, where `llvm-mc` silently wraps) and index `4` is `E-RANGE-004` (`N16ac`); naming a row against `0.23.0` is `E-FORM-001` (`N01az`/`N01ba`). The absolute `SIB = 25` shape is deferred, no `EC` row is added, `EC-02`/`EC-35`/`EC-37`/`EC-40` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0052 | The EVEX `vmovaps` memory rows take a 32-bit absolute address: `0.25.0` appends six rows — three widths × load/store, `disp32` only — whose `ModRM` is `04` and whose `SIB` byte is the constant `25` (scale `00`, index `100` "no index", base `101` "no base, `disp32`"), so there is no `base`, `index` or `scale` role and the template is `62 f1 7c <L'L> <28\|29> 04 25 00 00 00 00`, eleven bytes in every row. The vector slot stays `[43,3]` with its inverted `R̄`/`R̄'`, the address is signed content at `[56,32]` and is mandatory: `0x0` and `0x7fff` still spend four bytes, and `0x1234, %xmm0` is `62 f1 7c 08 28 04 25 34 12 00 00`. The neighbours stay distinct forms — `0x1234(%rax)` ten bytes with no `SIB`, `0x1234(%rip)` ten bytes with `r/m = 101`, `0x1234(,%rax,4)` the `0.24.0` row three `SIB` bits away — and `abs32` names the address shape, not `moffs` (`EC-05` stays `draft`). The operand sequence is `dest`/`src`, `disp`, so a supplied `index` is `E-OPERAND-002` (`N02af`), `disp8` as the address is `E-OPERAND-001` (`N02ag`), and `disp32` content `2147483648` is `E-RANGE-001` (`N03l`, where `llvm-mc` silently wraps); naming a row against `0.24.0` is `E-FORM-001` (`N01bb`/`N01bc`). No `EC` row is added, `EC-02`/`EC-35`/`EC-37`/`EC-40` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0053 | The 64-bit GPR `mov` rows take a 32-bit absolute address: `0.26.0` appends two rows — load and store, `disp32` only — whose `ModRM` is `04` and whose `SIB` byte is the constant `25`, so the template is `48 <8B\|89> 04 25 00 00 00 00` and each row is eight bytes. `REX.W` is template bit 3; the register is four bits written raw (`[19,3]` plus `REX.R` at `[2,1]`), so `%r15` is `4c 8b 3c 25 34 12 00 00` while `%rax` keeps `48`, and the address is signed content at `[32,32]`. A supplied `base` is `E-OPERAND-002` (`N02ah`), `disp8` as the address is `E-OPERAND-001` (`N02ai`), content `2147483648` is `E-RANGE-001` (`N03m`), register `16` is `E-OPERAND-004` (`N14z`), and naming a row against `0.25.0` is `E-FORM-001` (`N01bd`/`N01be`). `moffs` (`A0`–`A3`) is the second legal encoding at ten bytes and has no row, so naming `moffs64` is `E-FORM-001` (`N01bf`) and `EC-05` is frozen with the `form variant` carrier, where `llvm-mc` itself switches form for `0x80000000`. `EC-02`/`EC-35`/`EC-37` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0054 | The 32-bit GPR `mov` rows take a 32-bit absolute address in two register windows: `0.27.0` appends four rows — load and store, each low and `-ext` — whose `ModRM` is `04` and whose `SIB` byte is the constant `25`. The low rows have no `REX` byte, so the register is the three-bit `ModRM.reg` at `[11,3]` and each row is seven bytes (`8b 04 25 …` / `89 04 25 …`); the `-ext` rows spend one byte on `REX = 44` (`REX.W = 0`, `REX.R = 1`) and put the register at `[19,3]` plus `REX.R` at `[2,1]` with `0`–`7` excluded, so each row is eight bytes (`44 8b 04 25 …` / `44 89 04 25 …`). The address is signed content at `[24,32]` or `[32,32]`. A supplied `base` is `E-OPERAND-002` (`N02aj`), `disp8` as the address is `E-OPERAND-001` (`N02ak`), a `gpr64`/`r64` operand on an `r32` row is `E-OPERAND-001` twice (`N02al`), content `2147483648` is `E-RANGE-001` (`N03n`), register `16` is `E-OPERAND-004` (`N14aa`), register `0` on the `-ext` row is `E-RANGE-004` (`N16ad`), and naming a row against `0.26.0` is `E-FORM-001` (`N01bg`/`N01bh`). `EC-02`/`EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0055 | The 16-bit GPR `mov` rows take a 32-bit absolute address behind the `66` prefix: `0.28.0` appends four rows — load and store, each low and `-ext` — whose `ModRM` is `04` and whose `SIB` byte is the constant `25`. All four start with `66`, so the low rows have no `REX` byte, the register is the three-bit `ModRM.reg` at `[19,3]` and each row is eight bytes (`66 8b 04 25 …` / `66 89 04 25 …`); the `-ext` rows insert `REX = 44` (`REX.W = 0`, `REX.R = 1`) at `[8,8]` and put the register at `[27,3]` plus `REX.R` at `[10,1]` with `0`–`7` excluded, so each row is nine bytes (`66 44 8b 04 25 …` / `66 44 89 04 25 …`). The address stays signed 32-bit content at `[32,32]` or `[40,32]` — `-32768` is `00 80 ff ff` — and `0x80000000` leaves the row for `movabsw`. A supplied `base` is `E-OPERAND-002` (`N02am`), `disp8` as the address is `E-OPERAND-001` (`N02an`), a `gpr32`/`r32` operand on an `r16` row is `E-OPERAND-001` twice (`N02ao`), content `2147483648` is `E-RANGE-001` (`N03o`), register `16` is `E-OPERAND-004` (`N14ab`), register `0` on the `-ext` row is `E-RANGE-004` (`N16ae`), and naming a row against `0.27.0` is `E-FORM-001` (`N01bi`/`N01bj`). `EC-02`/`EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0056 | The 8-bit GPR `mov` rows take a 32-bit absolute address in four byte-register windows: `0.29.0` appends eight rows — load and store in each of `%al`–`%bl`, `%ah`–`%bh`, `%spl`–`%dil` and `%r8b`–`%r15b` — whose `ModRM` is `04`/`24` and whose `SIB` byte is the constant `25`. The low and high rows have no `REX` byte, put the register at `[11,3]` and are seven bytes (`8a 04 25 …` / `8a 24 25 …`); the `REX = 40` and `REX = 44` rows put the register at `[19,3]` (plus `REX.R` at `[2,1]` for the extended window) and are eight. The address stays signed 32-bit content at `[24,32]` or `[32,32]`; `0x80000000` sends the low rows to `movabsb`. A supplied `base` is `E-OPERAND-002` (`N02ap`), `disp8` as the address is `E-OPERAND-001` (`N02aq`), a `gpr16`/`r16` operand is `E-OPERAND-001` twice (`N02ar`), a `gpr8h`/`r8h` operand on the low row is `E-OPERAND-001` twice plus `E-RANGE-004` (`N02as`), content `2147483648` is `E-RANGE-001` (`N03p`), register `16` is `E-OPERAND-004` (`N14ac`), register `0` on the `REX = 40` row is `E-RANGE-004` (`N16af`), and naming a row against `0.28.0` is `E-FORM-001` (`N01bk`/`N01bl`). `EC-02`, `EC-36` and `EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0057 | The extended byte register reaches the byte `mov` memory rows: `0.30.0` appends twelve rows — load and store in the three base windows the family already has (a plain base, `%rsp` behind `ModRM.r/m = 100` with `SIB = 24`, and `%r12` as the same `SIB` byte with `REX.B = 1`), each at disp8 and disp32. Every row carries `REX.R = 1` at `[2,1]`, so the register slot is four bits (`REX.R` plus `[19,3]`) and excludes `0`–`7`; the plain-base slot is four bits (`REX.B` at `[0,1]` plus `[16,3]`) and excludes `4` and `12`. One prefix byte carries both extension bits, so `movb 8(%rax), %r8b` is `44 8a 40 08` and `movb 8(%r8), %r8b` is `45 8a 40 08`, four bytes each, while the `SIB` rows are five (`44 8a 44 24 08` for `%rsp`, `45 8a 44 24 08` for `%r12`) and their `disp32` halves are eight. `%rbp`/`%r13` need no row because `mod = 01` is the family's floor (`44 8a 7d 08` is `movb 8(%rbp), %r15b`), and the high-byte kind cannot join: `movb 8(%r8), %ah` is rejected while `movb 8(%rax), %ah` is `8a 60 08`. A `gpr8h`/`r8h` operand is `E-OPERAND-001` twice (`N02at`), `disp8` on a `disp32` row is `E-OPERAND-001` (`N02au`), a `base` operand on a `SIB` row is `E-OPERAND-002` (`N02av`), content `2147483648` is `E-RANGE-001` (`N03q`), register `16` is `E-OPERAND-004` (`N14ad`), register `0` on an extended row is `E-RANGE-004` (`N16ag`), `%rsp` or `%r12` as the base of a plain-base row is `E-RANGE-004` (`N16ah`/`N16ai`), and naming a row against `0.29.0` is `E-FORM-001` (`N01bm`/`N01bn`). `EC-06` and `EC-38` are revised in place, and there is no schema or Rust change | accepted 2026-11-06 |
| ADR-0058 | The byte `mov` rows take the no-displacement memory shape: `0.31.0` appends eight rows — load and store in each of the four byte-register windows at `mod = 00` — so `movb (%rax), %al` is `8a 00` and `movb %cl, (%rcx)` is `88 09` (two bytes, opcode at `[0,8]`, `ModRM` at `[8,8]`, register `[11,3]`, base `[8,3]`), while `movb (%rsi), %dil` is `40 8a 3e` and `movb %r15b, (%r9)` is `45 88 39` (three bytes, register `[19,3]` with `REX.R` at `[2,1]` and base `[16,3]` with `REX.B` at `[0,1]`). The base slot excludes four values, not two: `%rbp`/`%r13`, because `r/m = 101` at `mod = 00` is RIP-relative `disp32` (`llvm-mc` writes `movb (%rbp), %al` as `8a 45 00`, `mod = 01`), and `%rsp`/`%r12`, because they need the `SIB` byte (`8a 04 24`, `41 8a 04 24`) a later slice carries. There is no `disp` slot, so a `disp` operand is `E-OPERAND-002` (`N02ax`); `%rbp`/`%r13`/`%rsp`/`%r12` as base are `E-RANGE-004` (`N16aj`/`N16ak`/`N16al`/`N16am`), base `8` on a three-bit row is `E-OPERAND-004` (`N14ae`), a `gpr8h`/`r8h` operand on the low row is `E-OPERAND-001` twice (`N02aw`), and naming a row against `0.30.0` is `E-FORM-001` (`N01bo`/`N01bp`). `EC-02` is revised in place: the byte `mov` family now carries all three displacement shapes. No new `EC` row, and no schema or Rust change | accepted 2026-11-06 |
| ADR-0059 | The byte `mov` rows take the `%rsp`/`%r12` `SIB` bases at `mod = 00`: `0.32.0` appends fourteen rows (both directions × seven base/register combinations) with `SIB = 24` and the base fixed in the template, so `movb (%rsp), %al` is `8a 04 24` and `movb (%r12), %al` is `41 8a 04 24` — the same three bytes after a `REX` byte whose `B` bit alone picks the base — while the high-byte window has no `%r12` half because `REX.B` renames `%ah` to `%spl`. A `base` or `disp` operand is `E-OPERAND-002` (`N02ay`/`N02az`), the absent high-byte `%r12` row is `E-FORM-001` (`N01bs`), register `16`/`8` on a three-bit row is `E-OPERAND-004` (`N14af`/`N14ag`), register `0` on the `REX = 40` row is `E-RANGE-004` (`N16an`), and naming a row against `0.31.0` is `E-FORM-001` (`N01bq`/`N01br`). `EC-35` and `EC-06` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0060 | The 64-bit `mov` rows take the no-displacement memory shape: `0.33.0` appends two rows (both directions) with `REX.W` in the template, so `movq (%rax), %rax` is `48 8b 00` and `movq %rax, (%rax)` is `48 89 00` — three bytes, one row for every register and base (`REX.R` at `[2,1]`, `REX.B` at `[0,1]`). The base slot excludes `%rbp`/`%r13` because `r/m = 101` at `mod = 00` is the RIP-relative `disp32` row, and `%rsp`/`%r12` because they need the `SIB` byte (`48 8b 04 24`, `49 8b 04 24`). `llvm-mc` normalises an explicit zero displacement on a plain base to the short form (`0(%rax)` assembles to `48 8b 00`), so the plan names the row. A `disp` operand is `E-OPERAND-002` (`N02ba`), register `16` is `E-OPERAND-004` (`N14ah`), the four bases are `E-RANGE-004` (`N16ao`–`N16ar`), and naming a row against `0.32.0` is `E-FORM-001` (`N01bt`/`N01bu`). `EC-35` is revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0061 | The 64-bit `mov` rows take the `%rsp`/`%r12` `SIB` bases at `mod = 00`: `0.34.0` appends four rows (one per base and direction) with the base, `SIB = 24` and `REX.B` fixed in the template, so `movq (%rsp), %rax` is `48 8b 04 24` and `movq (%r12), %rax` is `49 8b 04 24` — four bytes, `ModRM = 04`. Only `REX.R` at `[2,1]` is a slot, so one row per base and direction covers all sixteen registers (`movq (%rsp), %r8` is `4c 8b 04 24`). The base is not an operand: a `base` or `disp` operand is `E-OPERAND-002` (`N02bb`/`N02bc`), register `16` is `E-OPERAND-004` (`N14ai`), and naming a row against `0.33.0` is `E-FORM-001` (`N01bv`/`N01bw`). `EC-35` is revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0062 | The 32-bit `mov` family takes its first base rows: `0.35.0` appends six rows (three reach windows per direction) for the `mod = 00` plain-base shape, so `movl (%rax), %eax` is `8b 00` and `movl %eax, (%rax)` is `89 00` — two bytes, no displacement. The legacy row has no `REX` byte, so a high register or base changes the length and the reach is the form: `movl (%rax), %r8d` is `44 8b 00` (`REX.R`), `movl (%r8), %eax` is `41 8b 00` (`REX.B`), and `movl (%r9), %r15d` is `45 8b 39`. The windows are disjoint; every row excludes `%rsp`/`%r12` (`SIB`) and `%rbp`/`%r13` (RIP-relative). A `disp` operand is `E-OPERAND-002` (`N02bd`), the field ends are `E-OPERAND-004` (`N14aj`/`N14ak`), the exclusions are `E-RANGE-004` (`N16as`–`N16av`), and naming a row against `0.34.0` is `E-FORM-001` (`N01bx`/`N01by`). `EC-38` is revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0063 | The 32-bit `mov` family takes the `%rsp`/`%r12` `SIB` bases: `0.36.0` appends eight rows (one per base, direction and register window) for the `mod = 00` `SIB` shape, so `movl (%rsp), %eax` is `8b 04 24` and `movl (%r12), %eax` is `41 8b 04 24` — `ModRM = 04` plus `SIB = 24`, the base and its `REX.B` in the template. The two bases share the low three bits `100`, so each needs its own row and a base operand is `E-OPERAND-002`. The register window still splits: `%rsp` is three bytes in the low window and four in the `REX.R` window (`44 8b 04 24`), while every `%r12` row is four (`41`/`45`). `%rbp`/`%r13` stay RIP-relative. A `base`/`disp` operand is `E-OPERAND-002` (`N02be`/`N02bf`), the field ends are `E-OPERAND-004` (`N14al`/`N14am`), the `-ext` floor is `E-RANGE-004` (`N16aw`), and naming a row against `0.35.0` is `E-FORM-001` (`N01bz`/`N01ca`). `EC-35` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0064 | The 32-bit `mov` family takes the `disp8` base shape: `0.37.0` appends six rows (three reach windows per direction) with `mod = 01` and a signed 8-bit `disp` slot, so `movl 8(%rax), %eax` is `8b 40 08` and `movl %eax, 8(%rax)` is `89 40 08` — three bytes, base in `ModRM.r/m`, displacement at `[16,8]`, range `-128…127`. The reach is still three rows: `44 8b 40 08` (`REX.R`), `41 8b 40 08` (`REX.B`), `45 8b 79 08` (both), with the displacement at `[24,8]`. `%rbp`/`%r13` are ordinary bases at `mod = 01` (`8b 45 08`), so only `%rsp`/`%r12` stay excluded (`N16ax`/`N16ay`), and the `REX.B` row excludes the low bases, which would clear its fixed bit (`N16ba`). A missing `disp` is `E-OPERAND-002` (`N02bg`), `128` is `E-RANGE-001` (`N03r`), the field ends are `E-OPERAND-004` (`N14an`/`N14ao`), and naming a row against `0.36.0` is `E-FORM-001` (`N01cb`/`N01cc`). `EC-02` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0065 | The 32-bit `mov` family takes the `disp32` base shape: `0.38.0` appends six rows (three reach windows per direction) with `mod = 10` and a signed 32-bit `disp` slot, so `movl 200(%rax), %eax` is `8b 80 c8 00 00 00` and `movl %eax, 200(%rax)` is `89 80 c8 00 00 00` — six bytes, base in `ModRM.r/m`, displacement at `[16,32]`, range `-2147483648…2147483647`. The reach is still three rows: `44 8b 80 c8 00 00 00` (`REX.R`), `41 8b 80 c8 00 00 00` (`REX.B`), `45 8b b9 c8 00 00 00` (both), with the displacement at `[24,32]`. `%rbp`/`%r13` are ordinary bases (`8b 85 c8 00 00 00`), so only `%rsp`/`%r12` stay excluded (`N16bb`/`N16bc`), and the `REX.B` row excludes the low bases, which would clear its fixed bit (`N16be`). A missing `disp` is `E-OPERAND-002` (`N02bh`), `2147483648` is `E-RANGE-001` (`N03s`), the field ends are `E-OPERAND-004` (`N14ap`/`N14aq`), and naming a row against `0.37.0` is `E-FORM-001` (`N01cd`/`N01ce`). `EC-02` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0066 | The 32-bit `mov` family takes the `SIB` `disp8` shape: `0.39.0` appends eight rows (two bases × two directions × two register windows) with `mod = 01`, `SIB = 24` fixed in the template and a signed 8-bit `disp` slot, so `movl 8(%rsp), %eax` is `8b 44 24 08` and `movl %eax, 8(%rsp)` is `89 44 24 08` — four bytes, displacement at `[24,8]`, range `-128…127`. `%r12` is the same three bytes behind `REX.B` (`41 8b 44 24 08`), so the base stays a form property; the register window still splits (`44 8b 44 24 08`, `41 8b 44 24 08`, `45 8b 44 24 08`), with the displacement at `[32,8]`. A missing `disp` is `E-OPERAND-002` (`N02bi`), `128` is `E-RANGE-001` (`N03t`), the field ends are `E-OPERAND-004` (`N14ar`/`N14as`), the `REX.R` floor is `E-RANGE-004` (`N16bf`), and naming a row against `0.38.0` is `E-FORM-001` (`N01cf`/`N01cg`). `EC-02` and `EC-35` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0067 | The 32-bit `mov` family takes the `SIB` `disp32` shape: `0.40.0` appends eight rows (two bases × two directions × two register windows) with `mod = 10`, `SIB = 24` fixed in the template and a signed 32-bit `disp` slot, so `movl 200(%rsp), %eax` is `8b 84 24 c8 00 00 00` and `movl %eax, 200(%rsp)` is `89 84 24 c8 00 00 00` — seven bytes, displacement at `[24,32]`, range `-2147483648…2147483647`. `%r12` is the same three bytes behind `REX.B` (`41 8b 84 24 c8 00 00 00`), so the base stays a form property; the register window still splits (`44 8b 84 24 c8 00 00 00`, `41 8b 84 24 c8 00 00 00`, `45 8b 84 24 c8 00 00 00`), with the displacement at `[32,32]`. A missing `disp` is `E-OPERAND-002` (`N02bj`), `2147483648` is `E-RANGE-001` (`N03u`), the field ends are `E-OPERAND-004` (`N14at`/`N14au`), the `REX.R` floor is `E-RANGE-004` (`N16bg`), and naming a row against `0.39.0` is `E-FORM-001` (`N01ch`/`N01ci`). `EC-02` and `EC-35` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0068 | The 16-bit `mov` family takes its base rows: `0.41.0` appends eight `mod = 00` rows — four over a plain base (two directions × two base windows) and four over the fixed `%rsp`/`%r12` `SIB` bases — with no displacement slot, so `movw (%rax), %ax` is `66 8b 00` (three bytes, base slot `[16,3]`) and `movw %ax, (%rax)` is `66 89 00`. A `REX.B` base costs a byte (`66 41 8b 00`) and moves the register field to `[27,3]` and the base to `[24,3]`; `%rsp`/`%r12` are `66 8b 04 24` and `66 41 8b 04 24`, the same `SIB = 24` with `REX.B` the only difference. At `mod = 00` `r/m = 101` is `rip`-relative, so `%rbp`/`%r13` are not plain bases (`movw (%rbp), %ax` is `66 8b 45 00`, a `mod = 01` row). A supplied `disp` is `E-OPERAND-002` (`N02bk`), `%rsp`/`%r12` on a plain row and a low base on the `-ext` row are `E-RANGE-004` (`N16bh`–`N16bj`), `%rbp`/`%r13` are `E-RANGE-004` (`N16bk`/`N16bl`), and naming a row against `0.40.0` is `E-FORM-001` (`N01cj`/`N01ck`). `EC-35` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0069 | The 16-bit `mod = 00` rows take the `REX.R` register window: `0.42.0` appends eight rows that widen the register slot to `%r8w`–`%r15w` — the same four base shapes (plain low, plain `-ext`, `%rsp`, `%r12`), both directions — so `movw (%rax), %r8w` is `66 44 8b 00` (four bytes, `REX = 44`, `R` at `[10,1]` and the register at `[27,3]`) and `movw (%r8), %r8w` is `66 45 8b 00`, one byte carrying both `R` and `B`. The low register window is excluded from the `-ext` rows (`E-RANGE-004`, `N16bm`), `16` is past the four-bit field (`E-OPERAND-004`, `N14av`), a supplied `disp` is `E-OPERAND-002` (`N02bl`), `%rsp`/`%rbp` on the new base rows are `E-RANGE-004` (`N16bn`/`N16bo`), and naming a row against `0.41.0` is `E-FORM-001` (`N01cl`/`N01cm`). `EC-06` is revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0070 | The 16-bit `disp8` rows take the `REX.R` register window: `0.43.0` appends eight rows that widen the register slot to `%r8w`–`%r15w` on the four base shapes, both directions, so `movw 8(%rax), %r8w` is `66 44 8b 40 08` (five bytes, `REX = 44`, `R` at `[10,1]`, register at `[27,3]`, displacement at `[32,8]`) and `movw 8(%r8), %r8w` is `66 45 8b 40 08`, one byte carrying both `R` and `B`. The `SIB` rows add the `SIB` byte and put the displacement at `[40,8]`: `66 44 8b 44 24 08` and `66 45 8b 44 24 08`. At `mod = 01` `%rbp`/`%r13` are legal bases (`66 44 8b 45 08`), so the plain row excludes `%rsp` only (`N16bq`) and the `-ext` row excludes `0`–`7` and `%r12` (`N16br`). A missing `disp` is `E-OPERAND-002` (`N02bm`), `128` is `E-RANGE-001` (`N03v`), a low register on an `-ext` row is `E-RANGE-004` (`N16bp`), `16` is `E-OPERAND-004` (`N14aw`), and naming a row against `0.42.0` is `E-FORM-001` (`N01cn`/`N01co`). `EC-02`, `EC-06` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0071 | The 16-bit `disp32` rows take the `REX.R` register window: `0.44.0` appends eight rows that widen the register slot to `%r8w`–`%r15w` on the four base shapes, both directions, so `movw 200(%rax), %r8w` is `66 44 8b 80 c8 00 00 00` (eight bytes, `REX = 44`, `R` at `[10,1]`, register at `[27,3]`, displacement at `[32,32]`) and `movw 200(%r8), %r8w` is `66 45 8b 80 c8 00 00 00`, one byte carrying both `R` and `B`. The `SIB` rows add the `SIB` byte and put the displacement at `[40,32]`: `66 44 8b 84 24 c8 00 00 00` and `66 45 8b 84 24 c8 00 00 00`. At `mod = 10` `%rbp`/`%r13` are legal bases (`66 44 8b 85 c8 00 00 00`), so the plain row excludes `%rsp` only (`N16bt`) and the `-ext` row excludes `0`–`7` and `%r12` (`N16bu`). A missing `disp` is `E-OPERAND-002` (`N02bn`), `2147483648` is `E-RANGE-001` (`N03w`), a low register on an `-ext` row is `E-RANGE-004` (`N16bs`), `16` is `E-OPERAND-004` (`N14ax`), and naming a row against `0.43.0` is `E-FORM-001` (`N01cp`/`N01cq`). `EC-02`, `EC-06` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0072 | The 16-bit `mov` memory rows take a `SIB` index and scale: `0.45.0` appends four rows that put `REX.B`/`REX.X` beside the fixed `REX.R` on the same byte, so `movw 8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08` (six bytes, `SIB` at byte 4, `disp8` at `[40,8]`) and `movw 8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08`, with `R`, `X` and `B` in one `REX` byte. The base is one four-bit slot (`REX.B` + `SIB.base`, all sixteen values), the index is one four-bit slot (`REX.X` + `SIB.index`, `4` excluded), and the scale is two bits of field content (`0…3`; `4` is `E-RANGE-001`). The `disp32` rows put four bytes at `[40,32]` (`66 44 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bo`), a low register on an `-ext` row is `E-RANGE-004` (`N16bw`), index `4` is `E-RANGE-004` (`N16bv`), `16`/base `16` are `E-OPERAND-004` (`N14ay`/`N14az`), and naming a row against `0.44.0` is `E-FORM-001` (`N01cr`/`N01cs`). `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0073 | The 16-bit `mov` index/scale rows take the `REX`-less low-register window: `0.46.0` appends four rows without a `REX` byte, so `movw 8(%rax,%rcx,1), %ax` is `66 8b 44 08 08` (five bytes, `ModRM` at byte 2, `SIB` at byte 3, `disp8` at `[32,8]`) and `movw 8(%rdi,%rsi,4), %di` is `66 8b 7c b7 08`. The register, base and index fields are three bits each (`[19,3]`, `[24,3]`, `[27,3]`), the scale is two bits of content at `[30,2]`, and the index excludes `4`; `%rsp`/`%rbp` stay legal bases (`66 8b 44 0c 08` / `66 8b 44 0d 08`) because `r/m = 100` announces the `SIB` byte. The `disp32` rows put four bytes at `[32,32]` (`66 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bp`), scale `4` is `E-RANGE-001` (`N03y`), index `4` is `E-RANGE-004` (`N16bx`), register `16` and register/base `8` are `E-OPERAND-004` (`N14ba`/`N14bb`/`N14bc`), and naming a row against `0.45.0` is `E-FORM-001` (`N01ct`/`N01cu`). `EC-02`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0074 | The low-register 16-bit `mov` indexed rows take the `REX.B` and `REX.X` windows: `0.47.0` appends eight rows (two windows × two directions × two displacement widths) that keep the register at `[27,3]` and give the base or the index a fourth bit, so `movw 8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08` (six bytes, `REX.B = 1`, `disp8` at `[40,8]`) and `movw 8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08` (`REX.X = 1`). The base and index stay three bits at `[32,3]`/`[35,3]`, the scale at `[38,2]`; the extended operand's slot lists the `REX` bit as its most significant placement and excludes the low window, so base `3` and index `3` are `E-RANGE-004` (`N16bz`/`N16by`). Register `8`–`15` and the other operand past `7` are `E-OPERAND-004` (`N14bd`/`N14be`). `%r12`/`%rsp`/`%rbp`/`%r13` are legal bases, and `%r12` is legal as an index through `REX.X`. The `disp32` rows put four bytes at `[40,32]` (`66 41 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bq`), scale `4` is `E-RANGE-001` (`N03z`), and naming a row against `0.46.0` is `E-FORM-001` (`N01cv`/`N01cw`). `EC-02`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0075 | The low-register 16-bit `mov` indexed rows take the `REX.BX` window: `0.48.0` appends four rows (two directions × two displacement widths) where the base and the index are both in `%r8`–`%r15` while the register stays at `[27,3]`, so `movw 8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08` (six bytes, `REX = 43`, `disp8` at `[40,8]`) and `movw 8(%r15,%r15,8), %di` is `66 43 8b 7c ff 08`. Both memory slots list their `REX` bit as the most significant placement (`[8,1]`+`[32,3]`, `[9,1]`+`[35,3]`) and exclude `0`–`7`, so a low base or index is `E-RANGE-004` (`N16ca`/`N16cb`) and register `8` is `E-OPERAND-004` (`N14bf`). `%r12` is legal as base and as index (`66 43 8b 44 24 08`), `%rsp`/`%rbp` remain legal bases, and `%rbp` is a legal index (`66 41 8b 44 2d 08`). The `disp32` rows put four bytes at `[40,32]` (`66 43 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02br`), scale `4` is `E-RANGE-001` (`N03za`), and naming a row against `0.47.0` is `E-FORM-001` (`N01cx`/`N01cy`). `EC-02`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0076 | The 32-bit `mov` family takes the `REX`-less indexed rows: `0.49.0` appends four rows (two directions × two displacement widths) with no prefix byte, so `movl 8(%rax,%rcx,1), %eax` is `8b 44 08 08` (four bytes, `ModRM` at byte 1, `SIB = 08`, `disp8` at `[24,8]`) and `movl 8(%rdi,%rsi,4), %edi` is `8b 7c b7 08`. The register, base and index are three bits (`[11,3]`/`[16,3]`/`[19,3]`) and the scale is `[22,2]`, so register `8` and base `8` are `E-OPERAND-004` (`N14bg`/`N14bh`) and belong to the pending `REX.R`/`REX.B` rows. The index excludes `4`, the "no index" encoding (`E-RANGE-004`, `N16cc`); `%rsp`/`%rbp` stay legal bases (`8b 44 0c 08` / `8b 44 35 08`), and `%r12` as a base is `41 8b 44 0c 08`. The `disp32` rows put four bytes at `[24,32]` (`8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bs`), scale `4` is `E-RANGE-001` (`N03zb`), and naming a row against `0.48.0` is `E-FORM-001` (`N01cz`/`N01da`). `EC-02`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0077 | The 32-bit indexed `mov` rows take the single `REX` windows: `0.50.0` appends twelve rows (three extension bits × two directions × two displacement widths), each fixing exactly one bit. `movl 8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08` (`REX.R`), `movl 8(%r8,%rcx,1), %eax` is `41 8b 44 08 08` (`REX.B`) and `movl 8(%rax,%r9,1), %eax` is `42 8b 44 08 08` (`REX.X`). The prefix pushes `ModRM` to byte 2, so the register is `[19,3]`, the base `[24,3]`, the index `[27,3]`, the scale `[30,2]` and the displacement `[32,8]`/`[32,32]`. Each extended slot lists its fixed bit as the most significant placement (`[2,1]`/`[0,1]`/`[1,1]`) and excludes `0`–`7`, so a low value is `E-RANGE-004` (`N16cd`/`N16ce`/`N16cf`); the operands the row keeps low stay three-bit, so register `8` on the `B` row and base `8` on the `X` row are `E-OPERAND-004` (`N14bi`/`N14bj`). `%r12` is legal in both memory windows, `%rsp` is a legal base on the `R` row, and `%rsp` as an index stays rejected. The `disp32` rows put four bytes at `[32,32]` (`44 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bt`), scale `4` is `E-RANGE-001` (`N03zc`), and naming a row against `0.49.0` is `E-FORM-001` (`N01db`/`N01dc`). The `REX.BX` window is deferred. `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0078 | The 32-bit indexed `mov` rows take the `REX.BX` window: `0.51.0` appends four rows (two directions × two displacement widths) where both memory operands are extended while the register stays low, so `movl 8(%r8,%r9,1), %eax` is `43 8b 44 08 08` (five bytes, `REX = 43`, `ModRM` at byte 2, `SIB = 08`, `disp8` at `[32,8]`) and `movl 8(%r15,%r15,8), %edi` is `43 8b 7c ff 08`. Both memory slots list their `REX` bit as the most significant placement (`[0,1]`+`[24,3]`, `[1,1]`+`[27,3]`) and exclude `0`–`7`, so a low base or index is `E-RANGE-004` (`N16cg`/`N16ch`); the register is still three bits, so `8` is `E-OPERAND-004` (`N14bk`) and belongs to the deferred `REX.RBX` row (`47 8b 44 08 08`). `%r12` is legal as base and as index (`43 8b 44 24 08`), and `%rsp` as an index stays rejected. The `disp32` rows put four bytes at `[32,32]` (`43 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bu`), scale `4` is `E-RANGE-001` (`N03zd`), and naming a row against `0.50.0` is `E-FORM-001` (`N01dd`/`N01de`). `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0079 | The 32-bit indexed `mov` rows take the `REX.RBX` window: `0.52.0` appends four rows (two directions × two displacement widths) where the register, the base and the index are all extended, so `movl 8(%r8,%r9,1), %r8d` is `47 8b 44 08 08` (five bytes, `REX = 47`, `ModRM` at byte 2, `SIB = 08`, `disp8` at `[32,8]`) and `movl 8(%r15,%r15,8), %r15d` is `47 8b 7c ff 08`. All three register slots list their `REX` bit as the most significant placement (`[2,1]`+`[19,3]`, `[0,1]`+`[24,3]`, `[1,1]`+`[27,3]`) and exclude `0`–`7`, so a low value on any of them is `E-RANGE-004` (`N16ci`/`N16cj`/`N16ck`). `%r12` is legal on all three operands (`8(%r12,%r12,1), %r8d` is `47 8b 44 24 08`, `%r12d, 8(%r12,%r12,1)` is `47 89 64 24 08`), and `%rsp` as an index stays rejected. The `disp32` rows put four bytes at `[32,32]` (`47 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bv`), scale `4` is `E-RANGE-001` (`N03ze`), and naming a row against `0.51.0` is `E-FORM-001` (`N01df`/`N01dg`). `EC-02`, `EC-06`, `EC-37` and `EC-38` are revised in place; no new `EC` row, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0080 | `0x67` is a form fact, and `EC-08` is frozen with `form variant` as the carrier: `0.53.0` appends four `REX`-less address-size rows (two directions × two displacement widths) where `67` is template byte 0, so `movl 8(%eax,%ecx,1), %eax` is `67 8b 44 08 08` (five bytes, opcode at byte 1, `ModRM` at byte 2, `SIB = 08`, `disp8` at `[32,8]`) and `movl 8(%edi,%esi,4), %edi` is `67 8b 7c b7 08`. The base and index are 32-bit address registers (`x86.gpr32`/`rm32` at `[24,3]`, `x86.gpr32`/`sib_index32` at `[27,3]`, index `4` excluded), the value register is `x86.gpr32`/`r32` at `[19,3]`, the scale is `[30,2]` and the displacement is `[32,8]`/`[32,32]`. A value past the three-bit field is `E-OPERAND-004` (`N14bl`/`N14bm`), a 64-bit base is `E-OPERAND-001` (`N02bx`), index `4` is `E-RANGE-004` (`N16cl`), a missing index is `E-OPERAND-002` (`N02bw`), scale `4` is `E-RANGE-001` (`N03zf`), and naming a row against `0.52.0` is `E-FORM-001` (`N01dh`/`N01di`). `%ebp` is a legal index (`67 8b 44 28 08`) while `%rsp` stays rejected, and `0x67` precedes any `REX` byte (`67 47 8b 44 08 08`, deferred). `EC-02`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0081 | The `0x67` rows take the three single-`REX` windows: `0.54.0` appends twelve rows (three bits × two directions × two displacement widths) where `0x67` stays byte 0 and `REX` becomes byte 1, so `movl 8(%eax,%ecx,1), %r8d` is `67 44 8b 44 08 08` (six bytes, opcode at byte 2, `ModRM = 44` at byte 3, `SIB = 08` at byte 4, `disp8` at `[40,8]`) and `movl 200(%eax,%ecx,1), %r8d` is `67 44 8b 84 08 c8 00 00 00` (nine). `REX.R` extends the value register (`[10,1]`+`[27,3]`), `REX.B` the base (`[8,1]`+`[32,3]`) and `REX.X` the index (`[9,1]`+`[35,3]`), each excluding `0`–`7` (`E-RANGE-004`, `N16cm`/`N16cn`/`N16co`); the scale is `[38,2]` and the displacement `[40,8]`/`[40,32]`. The operands a row keeps low stay three-bit fields (`E-OPERAND-004`, `N14bn`/`N14bo`), `%r12d` is legal as base and index (`67 41 8b 44 0c 08`, `67 42 8b 44 20 08`), `%esp` as an index stays rejected, and `%ebp` is a legal base (`67 44 8b 44 0d 08`). A missing index is `E-OPERAND-002` (`N02by`), scale `4` is `E-RANGE-001` (`N03zg`), and naming a row against `0.53.0` is `E-FORM-001` (`N01dj`/`N01dk`). The two-bit windows are added by `ADR-0082`. `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0082 | The `0x67` rows take the four two-fixed-bit `REX` windows: `0.55.0` appends sixteen rows (four bit combinations × two directions × two displacement widths) where `0x67` stays byte 0 and `REX` byte 1, so `movl 8(%r8d,%r9d,1), %eax` is `67 43 8b 44 08 08` (six bytes, `REX.BX`, opcode at byte 2, `ModRM = 44` at byte 3, `SIB = 08` at byte 4, `disp8` at `[40,8]`) and `movl 8(%r8d,%r9d,1), %r8d` is `67 47 8b 44 08 08` (`REX.RBX`); the `disp32` siblings are nine bytes. `67 45` is `REX.RB` and `67 46` is `REX.RX`. The geometry is the `0.54.0` geometry (register `[27,3]`, base `[32,3]`, index `[35,3]`, scale `[38,2]`, displacement `[40,8]`/`[40,32]`); each fixed bit stays at `[10,1]` (`R`), `[8,1]` (`B`) or `[9,1]` (`X`), its slot excludes `0`–`7` (`E-RANGE-004`, `N16cp`/`N16cq`/`N16cr`), and the operands a row keeps low stay three bits (`E-OPERAND-004`, `N14bp`/`N14bq`). `%r12d` on all three operands is `67 47 8b 64 24 08`, `%r13d` is `67 47 8b 6c 2d 08`, the x8 scale with `%r15d` is `67 47 8b 7c c8 08`, and `%esp` as an index stays rejected. A missing index is `E-OPERAND-002` (`N02bz`), scale `4` is `E-RANGE-001` (`N03zh`), and naming a row against `0.54.0` is `E-FORM-001` (`N01dl`/`N01dm`). The `0x67` `REX.W` siblings stay deferred. `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0083 | The `0x67` `REX.W` rows are one wide row per shape: `0.56.0` appends four rows (two directions × two displacement widths) with `REX.W` fixed in the template, so `movq 8(%eax,%ecx,1), %rax` is `67 48 8b 44 08 08` (six bytes; `0x67` at byte 0, `REX = 48` at byte 1, opcode at byte 2, `ModRM = 44` at byte 3, `SIB = 08` at byte 4, `disp8` at `[40,8]`) and `movq 200(%eax,%ecx,1), %rax` is `67 48 8b 84 08 c8 00 00 00` (nine, `disp32` at `[40,32]`). `R`/`X`/`B` stay operand fields in the byte `REX.W` already forces: `movq 8(%r8d,%r9d,1), %r8` is `67 4f 8b 44 08 08` (`REX.RBX`), `67 49` is `REX.B`, `67 4a` is `REX.X` and `67 4c` is `REX.R`, all six bytes. The value is `x86.gpr64`/`r64` at `[10,1]`+`[27,3]`, while the base and index are `x86.gpr32`/`rm32` and `x86.gpr32`/`sib_index32` (index `4` excluded) because `0x67` selects 32-bit address registers: `%r12d` works as base and index, `%ebp` as a base, and a 64-bit base is `E-OPERAND-001` (`N02cb`). `%r12`/`%r13` on all three operands are `67 4f 8b 64 24 08`/`67 4f 8b 6c 2d 08`, the x8 scale is `67 48 8b 44 c8 08`, and the `%r15`/`%r15d`/`%ebp` store is `67 4d 89 7c 2f 08`. A missing index is `E-OPERAND-002` (`N02ca`), scale `4` is `E-RANGE-001` (`N03zi`), index `4` is `E-RANGE-004` (`N16cs`), and a five-bit register is `E-OPERAND-004` (`N14br`/`N14bs`). The `0x67` `REX.W` siblings are no longer deferred. `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0084 | The `0x67` 16-bit value rows are the prefix pair: `0.57.0` appends four rows (two directions × two displacement widths) where `0x67` is byte 0 and `0x66` byte 1, so `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08` (six bytes; opcode at byte 2, `ModRM = 44` at byte 3, `SIB = 08` at byte 4, `disp8` at `[40,8]`) and `movw 200(%eax,%ecx,1), %ax` is `67 66 8b 84 08 c8 00 00 00` (nine, `disp32` at `[40,32]`). The bare pair has no `REX` byte, so the value is `x86.gpr16`/`r16` at `[27,3]`, the base is `x86.gpr32`/`rm32` at `[32,3]` and the index is `x86.gpr32`/`sib_index32` at `[35,3]` (index `4` excluded). `%ebp` is a legal base and index (`67 66 8b 44 0d 08`/`67 66 8b 44 28 08`), `%esp` is a base but not an index, and the x8 scale is `67 66 8b 44 c8 08`. A value or base above `7` is `E-OPERAND-004` (`N14bt`/`N14bu`), index `4` is `E-RANGE-004` (`N16ct`), scale `4` is `E-RANGE-001` (`N03zj`), a missing index is `E-OPERAND-002` (`N02cc`), a 64-bit base is `E-OPERAND-001` (`N02cd`), and naming a row against `0.56.0` is `E-FORM-001` (`N01dp`/`N01dq`). The `0x67 66` `REX` windows stay deferred because they insert a byte at position 2. `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-36`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0085 | The `0x67 66` rows take the three single-`REX` windows: `0.58.0` appends twelve rows (three windows × two directions × two displacement widths) with the `REX` byte at position 2, so `movw 8(%eax,%ecx,1), %r8w` is `67 66 44 8b 44 08 08` (seven bytes; `0x67` at byte 0, `0x66` at byte 1, `REX = 44` at byte 2, opcode at byte 3, `ModRM = 44` at byte 4, `SIB = 08` at byte 5, `disp8` at `[48,8]`) and `movw 200(%eax,%ecx,1), %r8w` is `67 66 44 8b 84 08 c8 00 00 00` (ten, `disp32` at `[48,32]`). One fixed bit opens one window: `R` at `[18,1]` widens the value (`%r8w`–`%r15w`, `67 66 44 …`), `B` at `[16,1]` the base (`%r8d`–`%r15d`, `67 66 41 8b 44 08 08`) and `X` at `[17,1]` the index (`67 66 42 8b 44 08 08`). The widened slot excludes `0`–`7` (`E-RANGE-004`, `N16cu`/`N16cv`/`N16cw`), a value past its four-bit field is `E-OPERAND-004` (`N14bv`), the index still excludes `4`, the scale `4` is `E-RANGE-001` (`N03zk`), a missing index is `E-OPERAND-002` (`N02ce`), and naming a row against `0.57.0` is `E-FORM-001` (`N01dr`/`N01ds`). The two- and three-bit windows stay deferred. `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-36`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-07 |
| ADR-0086 | The `0x67 66` rows take the four two-fixed-bit `REX` windows: `0.59.0` appends sixteen rows (four bit combinations × two directions × two displacement widths) with `REX` at position 2, so `movw 8(%r8d,%ecx,1), %r8w` is `67 66 45 8b 44 08 08` (`REX.RB`, seven bytes; `0x67` at byte 0, `0x66` at byte 1, `REX = 45` at byte 2, opcode at byte 3, `ModRM = 44` at byte 4, `SIB = 08` at byte 5, `disp8` at `[48,8]`) and `movw 200(%r8d,%ecx,1), %r8w` is `67 66 45 8b 84 08 c8 00 00 00` (ten, `disp32` at `[48,32]`). `67 66 46` is `REX.RX`, `67 66 43` is `REX.BX` and `67 66 47` is `REX.RBX`; the geometry is the `0.58.0` geometry (value `[35,3]`, base `[40,3]`, index `[43,3]`, scale `[46,2]`, displacement `[48,8]`/`[48,32]`), each fixed bit stays at `[18,1]` (`R`), `[16,1]` (`B`) or `[17,1]` (`X`), and its slot excludes `0`–`7` (`E-RANGE-004`, `N16cx`/`N16cy`/`N16cz`). The address registers stay 32-bit, so index `4` with `REX.X = 1` names `%r12d` (`67 66 47 8b 64 24 08`), while `%esp` as an index stays rejected. A value past its four-bit field is `E-OPERAND-004` (`N14bw`), scale `4` is `E-RANGE-001` (`N03zl`), a missing index is `E-OPERAND-002` (`N02cf`), and naming a row against `0.58.0` is `E-FORM-001` (`N01dt`/`N01du`). The `REX.W` siblings stay deferred. `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-36`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-08 |
| ADR-0087 | The `0x67 66` rows take the no-base indexed shape: `0.60.0` appends eight rows (four `REX` windows × two directions, `disp32` only) where `mod = 00` and `SIB.base = 101` free the base slot, so `movw 8(,%ecx,1), %ax` is `67 66 8b 04 0d 08 00 00 00` (nine bytes; `0x67` at byte 0, `0x66` at byte 1, opcode at byte 2, `ModRM = 04` at byte 3, `SIB = 0d` at byte 4, `disp32` at `[40,32]`) and `movw 8(,%r9d,1), %r8w` is `67 66 46 8b 04 0d 08 00 00 00` (ten, `REX = 46` at byte 2 and every later field eight bits higher: value `[35,3]`, index `[43,3]`, scale `[46,2]`, displacement `[48,32]`). There is no `base` role and no `REX.B` bit; the displacement is four bytes at every value, including zero (`67 66 8b 04 0d 00 00 00 00`). `SIB.base = 101` carries the no-base meaning, so index `4` with `REX.X = 1` names `%r12d` (`67 66 42 8b 04 25 08 00 00 00`) while the bare row rejects `4` (`E-RANGE-004`, `N16da`) and the `RX` row rejects `0` (`N16db`); a missing index and a supplied base are both `E-OPERAND-002` (`N02cg`/`N02ch`), scale `4` is `E-RANGE-001` (`N03zm`), a value past its four-bit field is `E-OPERAND-004` (`N14bx`), and naming a row against `0.59.0` is `E-FORM-001` (`N01dv`/`N01dw`). The `REX.W` siblings stay deferred: `llvm-mc` never emits the redundant `0x66` before `REX.W` (`data16` emits a standalone byte), so there is no asm→obj oracle. `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-08 |
| ADR-0088 | The no-base indexed shape reaches the 32-bit value width: `0.61.0` appends eight rows (four `REX` windows × two directions, `disp32` only) where the absent `0x66` removes one geometry, so `movl 8(,%ecx,1), %eax` is `67 8b 04 0d 08 00 00 00` (eight bytes; `0x67` at byte 0, opcode at byte 1, `ModRM = 04` at byte 2, `SIB = 0d` at byte 3, value `[19,3]`, index `[27,3]`, scale `[30,2]`, `disp32` at `[32,32]`) and `movl 8(,%r9d,1), %r8d` is `67 46 8b 04 0d 08 00 00 00` (nine, `REX = 46` at byte 1 with `R` at `[10,1]` and `X` at `[9,1]`, so every later field is eight bits higher: `[27,3]`/`[35,3]`/`[38,2]`/`[40,32]`). There is no `base` role and no `REX.B` bit; the displacement is four bytes at every value, including zero (`67 8b 04 0d 00 00 00 00`). `SIB.base = 101` carries the no-base meaning, so index `4` with `REX.X = 1` names `%r12d` (`67 42 8b 04 25 08 00 00 00`) while the bare row rejects `4` (`E-RANGE-004`, `N16dc`) and the `RX` row rejects `0` (`N16dd`); a missing index and a supplied base are both `E-OPERAND-002` (`N02ci`/`N02cj`), scale `4` is `E-RANGE-001` (`N03zn`), a value past its four-bit field is `E-OPERAND-004` (`N14by`), and naming a row against `0.60.0` is `E-FORM-001` (`N01dx`/`N01dy`). The `REX.W` `movq` shape (`67 48`/`67 4c`/`67 4a`/`67 4e`) stays deferred: `REX.W` is mandatory there and `R`/`X` are free bits inside it. `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-08 |
| ADR-0089 | The no-base indexed shape reaches the 64-bit value width: `0.62.0` appends two rows, one per direction, because `REX.W` is mandatory and the `REX` byte therefore always exists. `movq 8(,%ecx,1), %rax` is `67 48 8b 04 0d 08 00 00 00` (nine bytes; `0x67` at byte 0, `REX` at byte 1, opcode at byte 2, `ModRM = 04` at byte 3, `SIB = 0d` at byte 4) with the value at `[10,1]`+`[27,3]`, the index at `[9,1]`+`[35,3]`, the scale at `[38,2]` and `disp32` at `[40,32]`. `R` and `X` are free bits of that one byte, so `0x48`/`0x4c`/`0x4a`/`0x4e` are the same form and one row per direction covers all sixteen value registers and indexes. There is no `base` role and no `REX.B` bit; the displacement is four bytes at every value, including zero (`67 48 8b 04 0d 00 00 00 00`). `SIB.base = 101` carries the no-base meaning, so `%r12d` is legal through `REX.X = 1` (`67 4a 8b 04 25 08 00 00 00`) while index `4` with `REX.X = 0` is `E-RANGE-004` (`N16de`); a missing index and a supplied base are both `E-OPERAND-002` (`N02ck`/`N02cl`), scale `4` is `E-RANGE-001` (`N03zo`), a value or index past its four-bit field is `E-OPERAND-004` (`N14bz`/`N14ca`), and naming a row against `0.61.0` is `E-FORM-001` (`N01dz`/`N01ea`). `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-08 |
| ADR-0090 | The absolute `SIB = 25` shape gains the `0x67` prefix at the 32-bit value width: `0.63.0` appends four rows (bare and `REX.R` x two directions). `addr32 movl 4660, %eax` is `67 8b 04 25 34 12 00 00` (eight bytes; `0x67` at byte 0, opcode at byte 1, `ModRM = 04` at byte 2, `SIB = 25` at byte 3, `disp32` at `[32,32]`) with the value at `[19,3]`; the `REX` row puts `REX` at byte 1, the value at `[10,1]`+`[27,3]` (excluding `0`-`7`) and the displacement at `[40,32]`. `SIB = 25` is `scale = 00`/`index = 100`/`base = 101`, so the address carries no register: there is no `base`, `index` or `scale` slot and no `REX.B`/`REX.X` bit, and a supplied base is `E-OPERAND-002` (`N02cm`). The displacement is four bytes at every value, including zero (`67 8b 04 25 00 00 00 00`), and `2147483648` is `E-RANGE-001` (`N03zp`); the bare three-bit value field rejects `8` (`N14cc`), the extended four-bit one rejects `16` (`N14cb`), value `0` on the `-ext` row is `E-RANGE-004` (`N16df`), and naming a row against `0.62.0` is `E-FORM-001` (`N01eb`/`N01ec`). `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-08 |
| ADR-0091 | The absolute `SIB = 25` shape behind `0x67` reaches the 64-bit value width: `0.64.0` appends two rows, one per direction, because `REX.W` is mandatory and `R` is a free bit of the same byte. `addr32 movq 4660, %rax` is `67 48 8b 04 25 34 12 00 00` (nine bytes; `0x67` at byte 0, `REX.W` at byte 1, opcode at byte 2, `ModRM = 04` at byte 3, `SIB = 25` at byte 4, `disp32` at `[40,32]`) with the value at `[10,1]`+`[27,3]` covering `0`-`15`; there is no bare geometry and no exclusion. `SIB = 25` is `scale = 00`/`index = 100`/`base = 101`, so the address carries no register: no `base`, `index` or `scale` slot and no `REX.B`/`REX.X` bit. The displacement is four bytes at every value, including zero (`67 48 8b 04 25 00 00 00 00`), and `2147483648` is `E-RANGE-001` (`N03zq`); a supplied base and a missing displacement are `E-OPERAND-002` (`N02cn`/`N02co`), a 32-bit operand is `E-OPERAND-001` twice (`N02cp`), value `16` is `E-OPERAND-004` (`N14cd`), and naming a row against `0.63.0` is `E-FORM-001` (`N01ed`/`N01ee`). `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-08 |
| ADR-0092 | The absolute `SIB = 25` shape gains the `0x67 66` prefix pair at the 16-bit value width: `0.65.0` appends four rows (bare and `REX.R` x two directions). `addr32 movw 4660, %ax` is `67 66 8b 04 25 34 12 00 00` (nine bytes; `0x67` at byte 0, `0x66` at byte 1, opcode at byte 2, `ModRM = 04` at byte 3, `SIB = 25` at byte 4, `disp32` at `[40,32]`) with the value at `[27,3]`; the `REX` row puts `REX` at byte 2, the value at `[18,1]`+`[35,3]` (excluding `0`-`7`) and the displacement at `[48,32]`. `SIB = 25` is `scale = 00`/`index = 100`/`base = 101`, so the address carries no register: no `base`, `index` or `scale` slot and no `REX.B`/`REX.X` bit. The displacement is four bytes at every value, including zero (`67 66 8b 04 25 00 00 00 00`), and `2147483648` is `E-RANGE-001` (`N03zr`); a supplied base and a missing displacement are `E-OPERAND-002` (`N02cq`/`N02cr`), a 32-bit operand is `E-OPERAND-001` twice (`N02cs`), the bare three-bit field rejects `8` (`N14cf`), the extended four-bit one rejects `16` (`N14ce`), value `0` on the `-ext` row is `E-RANGE-004` (`N16dg`), and naming a row against `0.64.0` is `E-FORM-001` (`N01ef`/`N01eg`). `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and `EC-38` are revised in place; no `EC` row is added or renumbered, and no schema or Rust change | accepted 2026-11-08 |
| ADR-0093 | An absolute 32-bit content field can carry a symbol: the operand keeps `payload: {}` and one fixup over exactly the slot's bits carries `pc_reference_rule = none`, `value_transform = identity`, the addend and `range_constraint {signed: true, bits: 32, align_bits: 0}`. Nine measured windows: the eight `disp32` slots of the absolute `mov` rows are 7/7/8/8/9/7/7/11 bytes at `[24,32]`, `[24,32]`, `[32,32]`, `[32,32]`, `[40,32]`, `[24,32]`, `[24,32]`, `[56,32]`, and `addq $ext, %rax` puts the same symbol in the `imm32` slot at `[24,32]`. `emit_relocation` writes zero and emits one `R_X86_64_32S`-style record (nine records at `0x3`/`0xA`/`0x12`/`0x1A`/`0x23`/`0x2A`/`0x31`/`0x3C`/`0x43`) and cannot range-check the value; `resolve_in_place` writes `S + A` and needs the target's section `base_address`, because a `none` rule cannot cancel the site, so the unbound plan is `E-FIXUP-002` (`N08d`). With `.text` at `0x1000` and `L1` at offset 30 the five resolved displacements are `0x101e`/`0x1022`/`0x101e`/`0x1020`/`0x101e`. `payload: {symbol_id}` on `disp` and `payload: {}` with no covering fixup are `E-OPERAND-003` (`N15b`/`N15c`), a value plus a covering fixup is `E-FIXUP-006` (`N07c`), a partial window is two `E-FIXUP-001` (`N07d`), the 64-bit `[32,32]` window on a 7-byte row is `E-FIXUP-005` plus `E-FIXUP-001` (`N07e`), and `0x1000` in the 8-bit `add` immediate is `E-FIXUP-003` (`N04f`). `0.65.0` stays canonical (509 forms, digest `sha256:9f5bc421…`); `EC-02`, `EC-05`, `EC-34` and `EC-39` are revised in place, and no definition, schema or Rust change is needed | accepted 2026-11-08 |
| ADR-0094 | Seven ambiguous families stay absent in v0: `EC-10` (x86 prefix presence), `EC-16` (AArch64 `mov` alias), `EC-18` (AArch64 conditional transfer), `EC-23` (RV64 jump and call), `EC-24` (RV64 `fence` masks), `EC-25` (RV64 CSR immediate) and `EC-26` (RV64 `aq`/`rl`) are frozen with a decided carrier but no row. `EXP-0096` measures the two or more legitimate encodings in each family: `lock addl (%rax), %ebx` is `f0 03 18` against `03 18`; `mov x0, #1` is `20 00 80 d2` (`MOVZ`) against `00 00 80 92` (`MOVN`) for `#-1`; `jal x0` is `01 a0` (`c.j`) under `.option rvc` against `6f 00 00 00` under `.option norvc`; `fence rw, rw` is `0f 00 30 03` against `0f 00 f0 0f` for `iorw, iorw`; `csrrw` is `f3 10 01 30` (`funct3 = 001`) against `f3 50 01 30` (`funct3 = 101`) for `csrrwi`; `.aq` sets bit 26 and `.rl` bit 25. A decision whose output is a byte, a length or a fixed semantic bit is a `form variant`; `EC-24` is `operand type` because its output is the `imm12` field value. No definition, schema, Rust or fixture change: `0.65.0` stays canonical (509 forms, `sha256:9f5bc421…`) and the corpus stays 100 positive / 530 negative. The rejection path for all seven is `E-FORM-001`, already pinned by `N01` | accepted 2026-11-08 |
| ADR-0095 | The contract set is `frozen for the v0 scope`: every in-scope field is frozen with a counterexample, all `EC` and `OD` rows are settled, and the remaining `draft` fields are explicitly optional | `01_contract.md`; `04_errors.md` §2.4; `EXP-R3` |
| ADR-0096 | Level 1 is a JSON description artifact: `artifact: sections` emits `sections[]` in `section_order`, an optional `symbols[]` in `symbol_order`, and the unchanged Level 0 `fixups[]`; no container and no synthesized symbols; Level 0 bytes stay identical | `X86-P71`; `EXP-0100`; `01_contract.md` §11.2 |
| ADR-0097 | The planner boundary is `fmp-plan`: a total, closed plan builder that depends only on `fmp-model`, has no validator and no planner authority, exposes the frozen v0 surface (`source_ref`, `source_trace`, `symbol.type`, `section_relative` and `symbol.size` excluded), and proves "same codes" by re-reading its own bytes through the shipped reader and validator; implemented in `prototype/crates/fmp-plan` with the ten-test `planner_api.rs` parity gate | `09_planner_api.md`; `ADR-0031`; `ADR-0095`; `ADR-0096`; `planner_api.rs` |
| ADR-0098 | `hi20` is the absolute high half: `v = (D + 0x800) >> 12` with `D = S + A`, so `pc_reference_rule` MUST be `none` (`E-FIXUP-001`, `N07f`) and the matching low half is `lo12_i` on the same absolute value; `definitions/rv64/0.3.0.json` appends `riscv:lui/rd-imm20` (`37000000`, `dest` 7+5, `target` 12+20, `signed: false`), measured at `0`, `1` and `0xfffff` and against the linked pair (`L1` at `0x1234` gives `lui a0, 1` + `addi a0, a0, 0x234`); the absent sibling `c.lui` stays `E-FORM-001` (`N01eh`), `lo12_s` stays reserved, and no transform selects an encoding form | `EXP-0098`; `RV-P9`; `03_fixup_model.md` §6; `07_definition_format.md` §8 |
| ADR-0099 | RV64 `jalr` is a form, not a relaxation: `definitions/rv64/0.4.0.json` appends `riscv:jalr/rd-rs1-imm12` (`67000000`, `dest` 7+5, `src` 15+5, `imm` 20+12 `signed: true`), and the `auipc` + `jalr` call pair reuses `pcrel_hi20`/`pcrel_lo12` with `pair_role` `hi`/`lo` -- no new transform, because the mask and the instruction's sign extension agree; the low half stays `signed: false` and a masked value with bit 11 set is legal (`L1` at `0x1900` gives `auipc ra, 1` + `jalr ra, 0x900`, read back as `jalr -0x700(ra) <L1>`); `rs1` is an operand the plan supplies, so the materializer never infers a base register, and `c.jalr` stays `E-FORM-001` (`N01ei`) while `2048` stays `E-RANGE-001` (`N03x`) | `EXP-0099`; `RV-P10`; `EC-23`; `03_fixup_model.md` §4, §6; `07_definition_format.md` §8 |
| ADR-0100 | AArch64 unconditional transfers are four forms and one bit: `definitions/aarch64/0.18.0.json` appends `aarch64:b/imm26` (`00000014`), `br/rn` (`00001fd6`), `blr/rn` (`00003fd6`) and `ret/rn` (`00005fd6`), with `imm26` at 0+25 as field content and `Rn` at 5+5 as a `src` operand (register 31 is `xzr`); the `b`/`bl` split is the `form_id` (`EC-41`) because the link bit changes the relocation (`R_AARCH64_JUMP26` vs `R_AARCH64_CALL26`) and a `link` modifier is `E-OPERAND-003` (`N19d`); `ret` carries no implicit `x30` (`N01y`), `cbz` stays `E-FORM-001` (`N01x`) and `imm26 = 33554432` is `E-RANGE-002` (`N04e`) although llvm-mc wraps it | `EXP-0101`; `A64-P21`; `A64-P22`; `EC-41`; `03_fixup_model.md` §6; `07_definition_format.md` §8 |
| ADR-0101 | x86 `sub` takes the three `add` immediate shapes with `ModRM.reg` fixed to `/5`: `definitions/x86_64/0.66.0.json` appends `x86:sub/rm64-imm8/legacy` (`4883e800`), `sub/rm64-imm32/legacy` (`4881e800000000`) and `sub/rax-imm32/legacy` (`482d00000000`), with the four-bit destination at `[0,1]`+`[16,3]` and the immediate at `[24,8]`/`[24,32]`/`[16,32]`; `/5` and `2D` are template content, not plan fields, so `sub rax, 300` is `48 2d 2c 01 00 00` (6 B) or `48 81 e8 2c 01 00 00` (7 B) and the row must be named (`EC-04`); the register pair (`29`/`2B`) stays absent (`N01ej`), a `0.66.0` row against `0.65.0` is `E-FORM-001` (`N01ek`), `128` on the signed 8-bit immediate is `E-RANGE-001` (`N03zs`) and a `r32` destination on `imm32` is `E-OPERAND-001` twice (`N02ct`); 512 forms, digest `sha256:63b3b3a153aa0b5508f2055496efa1c56ac74e56b03d56f56f5c522b6d2e1904` | `EXP-0102`; `X86-P72`; `EC-01`; `EC-04`; `07_definition_format.md` §8.1 |
| ADR-0102 | The direct x86 `call rel32` row is a form, not a link modifier: `definitions/x86_64/0.67.0.json` appends `x86:call/rel32/legacy` (`e800000000`) with the `x86.rel`/`rel32` target at `[8,32]` and `pcrel_end`; `callq L1` is `e8 05 00 00 00` (displacement from the end of the instruction), `callq ext` is `e8 00 00 00 00` with one `R_X86_64_PLT32 ext -4` record, and `call .+130` is the literal field `e8 7d 00 00 00`; `E8` is template content, so there is no `link`/`opcode` field and no rel8 row (`EC-03`); the indirect `FF /2` family (`ff d0`/`ff 10`/`ff 50 08`) stays absent (`N01el`), a `0.67.0` row against `0.66.0` is `E-FORM-001` (`N01em`), a register target is `E-OPERAND-001` twice (`N02cu`), a missing target is `E-OPERAND-002` (`N02cv`) and `2147483648` on the signed displacement is `E-RANGE-002` (`N04g`); 513 forms, digest `sha256:367d76ebf89ee9c1cf51f561b4798eeb0a2000ae3688ee9a52a4c4a9eaea5c9e` | `EXP-0103`; `X86-P73`; `EC-03`; `07_definition_format.md` §8.1 |
| ADR-0103 | `fmp-def/0.2` makes `requires_extensions` required on every form and treats `enabled_extensions` as an upper bound: the plan's set must be a subset (`E-TARGET-001`) and a named form whose requirement is not covered is `E-TARGET-003` at step 6 (`ADR-0103`); `definitions/x86_64/0.68.0.json` repeats the 513 forms of `0.67.0` unchanged and adds 388 `[]`, 38 `["avx"]`, 29 `["avx","avx512f"]` and 58 `["avx","avx512f","avx512vl"]` rows; the split is the operand width (`EXP-0104`: VEX `L`, EVEX `L'L`), and `llvm-mc` has no `-mattr` gate, so the name mapping is an inference; `X86-P20`'s 24 VEX instructions re-pinned with `["avx"]` are `X86-P74`, `N06b` is `E-TARGET-003` on `avx`, `N06c` is `E-TARGET-001` with `found = sse4.2`; `0.1` equality and `N06` are unchanged; digest `sha256:4c9ff304b305ceb831fd99e22bf0a7c422cce4104d08de604a6509f58e1501d2` | `EXP-0104`; `X86-P74`; `N06b`; `N06c`; `07_definition_format.md` §2/§3/§8.1; `04_errors.md` §2.3/§2.4 |
| ADR-0104 | The RV64 B-type family is five more rows on `beq`'s geometry: `definitions/rv64/0.5.0.json` appends `riscv:bne/rs1-rs2-imm12`, `blt`, `bge`, `bltu` and `bgeu` (`63100000`/`63400000`/`63500000`/`63600000`/`63700000`), each with the four-placement signed-12 target, `src`/`src2` and the `scale(1)` fixup; the five pinned UDB nodes differ from `beq.yaml` only in `funct3` (001/100/101/110/111); `RV-P11` is 20 bytes with three forward (`+8`) and two backward (`−4`) branches; `N01en` is the `0.4.0` boundary, `N02cw` the operand class and `N04h` the signed-12 end; 15 forms, digest `sha256:571ab1ed93f4464d5ec8981df02dd0444005ababdaaf1e175d0ec489bb33a776` | `EXP-0105`; `RV-P11`; `N01en`; `N02cw`; `N04h`; `07_definition_format.md` §8.6 |
| ADR-0105 | SSE `%rip`-relative rows are six forms: `definitions/x86_64/0.69.0.json` appends `movaps`/`vmovaps` xmm load and store at the legacy, VEX and EVEX encodings with one `x86.rel`/`riprel32` target at `[24,32]`/`[32,32]`/`[48,32]` and `pcrel_end`; the six templates are the measured `16(%rip)` encodings with the displacement zeroed (`EXP-0106`), and `X86-P75` is a 70-byte vector whose one symbol at offset 66 gives six different displacements; `N01eo` is the deliberately absent `ymm` sibling, `N02cx` a missing target and `N04i` the signed-32 end; 519 forms, digest `sha256:94dee360550537cbefed798bcc4e7d790b9a879391e0b6a47ecf24a819a6b596`; `EC-34` now names the SSE rows too | `EXP-0106`; `X86-P75`; `N01eo`; `N02cx`; `N04i`; `07_definition_format.md` §8.1 |
| ADR-0106 | The legacy SSE fixed-base rows gain the extended-register window as eight `-ext` rows: `definitions/x86_64/0.70.0.json` appends `movaps` xmm load/store × `disp8`/`disp32` × `%rsp`/`%r12` with `REX.R` at `[2,1]`, `ModRM.reg` at `[27,3]`, displacement at `[40,8]`/`[40,32]` and `xmm0`-`xmm7` excluded, because emitting the `REX` byte from the register value would change the instruction length (`INV-04`); the templates are the measured `EXP-0107` bytes (`44`/`45` first byte); `X86-P76` is a 60-byte vector of eight rows; `N01ep` is the `0.69.0` boundary, `N02cy` a missing disp and `N03zt` the signed-8 end; 527 forms, digest `sha256:02cbd866ce04b7584456bccf177c1aef7395a6b503240ddd1617be8e73f9eb2e`; `EC-38` now names the register window too | `EXP-0107`; `X86-P76`; `N01ep`; `N02cy`; `N03zt`; `07_definition_format.md` §8.1 |
| ADR-0107 | The `0x67` prefix reaches the `%rip`-relative rows as six forms: `definitions/x86_64/0.71.0.json` appends `mov` load/store at `r16`/`r32`/`r64` with the target at `[24,32]` (r32) or `[32,32]` (r64/r16); `addr32 movl 16(%rip), %eax` is `67 8b 05 10 00 00 00` (7 B), `movq` is `67 48 8b 05 …` (8 B) and `movw` is `67 66 8b 05 …` (8 B), so the prefix order is `0x67` then `0x66`/`REX`; the plan keeps `address_width: 64` because the prefix is a form fact under `EC-08`, not a target-identity field; `X86-P77` resolves one symbol at offset 62 through six `pcrel_end` fixups; `N01eq` is the `0.70.0` boundary, `N02cz` a missing target and `N04j` the signed-32 end; 533 forms, digest `sha256:2858c0f163b1239b37f7be9ba294d8d81748038987a154afac66c2b63b4d2c5b`; `EC-08` now names the `%rip` rows too | `EXP-0108`; `X86-P77`; `N01eq`; `N02cz`; `N04j`; `07_definition_format.md` §8.1 |
| ADR-0108 | The legacy and VEX SSE families gain the general indexed shape: `definitions/x86_64/0.72.0.json` appends sixteen `movaps`/`vmovaps` rows over the low base/index window, crossing {load, store} × {`disp8`, `disp32`} × {`xmm0`-`xmm7`, `xmm8`-`xmm15`}; the index sits at `[27,3]` (legacy low) or `[35,3]` behind the `REX`/VEX byte, the scale at `[30,2]`/`[38,2]`, and the high `xmm` window is a separate row because `REX.R` (`44`) or `R̄` (`c5 78`) is template content, not inserted from an operand (`INV-04`); `X86-P78` is a 116-byte vector of sixteen rows; `N01er` is the `0.71.0` boundary, `N02da` a missing base (`expected: 5`, `found: 4`) and `N03zu` the signed-8 end; 549 forms, digest `sha256:15fbacc2e014b9c135762f53a8b55b8c7d5dc21e9ff665ee5a0259437d70bf11`; `EC-37` now names the SSE indexed rows | `EXP-0109`; `X86-P78`; `N01er`; `N02da`; `N03zu`; `07_definition_format.md` §8.1 |
| ADR-0109 | The indexed byte `mov` lands in the three no-new-prefix windows: `definitions/x86_64/0.73.0.json` appends twelve rows over `r8` (`%al`-`%dl`, no `REX`), `r8h` (`%ah`-`%dh`) and `r8-rex` (`%spl`-`%dil`, `40` prefix), crossing {load, store} × {`disp8`, `disp32`}; the value slot is `[11,3]`/`[19,3]` with the window's exclusion, base `[16,3]`/`[24,3]`, index `[19,3]`/`[27,3]`, scale `[22,2]`/`[30,2]`, displacement `[24,…]`/`[32,…]`; the high `%r8b`-`%r15b` window needs `REX.R` and stays deferred; `X86-P79` is a 70-byte vector; `N01es` is the `0.72.0` boundary, `N02db` a missing base (`expected: 5`, `found: 4`) and `N03zv` the signed-8 end; 561 forms, digest `sha256:dfe7c9385b5a6a8636d8a54252ba72e3630aee3573b7e71062c4d7f8777d4237`; `EC-36` now names the indexed byte rows | `EXP-0110`; `X86-P79`; `N01es`; `N02db`; `N03zv`; `07_definition_format.md` §8.1 |
| ADR-0110 | The `29 /r` register/register `sub` lands at three widths: `definitions/x86_64/0.74.0.json` appends `x86:sub/rm64-r64/legacy` (`4829c8`), `x86:sub/rm32-r32/legacy` (`29c8`) and `x86:sub/rm16-r16/legacy` (`6629c8`); the destination is `REX.B` + `ModRM.r/m` on the 64-bit row (`ModRM.r/m` at 32/16 bits), the source is `REX.R` + `ModRM.reg`, and both fields are three bits, so `%r8`-`%r15` stays deferred; the memory-destination direction `2B /r` stays absent (`N01ej`, repointed from the old `29`/`2B` claim); `X86-P80` is a 16-byte vector; `N01et` is the `0.73.0` boundary, `N02dc` a missing source (`expected: 2`, `found: 1`) and `N14cg` register `8` past the three-bit field; 564 forms, digest `sha256:27f337115cffe89c8d7028863e7748783247344ba4d8e622fa9c4345efdead58`; `EC-42` records the direction choice | `EXP-0111`; `X86-P80`; `N01et`; `N01ej`; `N02dc`; `N14cg`; `07_definition_format.md` §8.1 |
| ADR-0111 | Phase 6 M5 closes: the seven coverage slices landed one ADR each (`ADR-0104`-`ADR-0110`), so the definition set ends at x86-64 `0.74.0` (564 forms), `rv64/0.5.0` (15 forms) and `aarch64/0.18.0` (180 forms) -- 759 forms, every one named by a positive fixture. The corpus is 121 positives and 586 negatives (580 `materialize`-phase plus 6 `read`-phase), and `tools/oracle/rerun.py` re-derives `116/121` byte-identically with the five `manual-derivation` skips and no failures. The accepted non-goals stay closed: `moffs`, APX `d5`, EVEX masking/broadcast, AArch64 `EC-16`/`EC-18`, RV64 `c.j`/`c.jalr` and FP/SIMD beyond SSE, plus the slice residue (zero-displacement indexed shapes, high base/index windows, the S7 memory shapes and `2B` r/r). This ADR also reconciles the stale counts in this file, `08_final_recommendation.md` and `02_encoding_choices.md` | `08_final_recommendation.md` §D/§F/§H; `06_validation_matrix.md`; `07_definition_format.md` §8.1 |
| ADR-0112 | Phase 7 M6 is coverage round 2, seven additive slices plus a closure: `S1` x86 ALU register/register at three widths (`x86/0.75.0`, 16 rows, `X86-P81`), `S2` x86 ALU immediate (`0.76.0`, 36 rows, `X86-P82`), `S3` x86 `mov` immediate (`0.77.0`, 6 rows, `X86-P83`), `S4` x86 `sub` memory directions (`0.78.0`, 12 rows, `X86-P84`), `S5` RV64 load/store widths (`rv64/0.6.0`, 9 rows, `RV-P12`), `S6` AArch64 `adr` (`aarch64/0.19.0`, 1 row, `A64-P23`) and `S7` AArch64 `mul`+`csel` (`0.20.0`, 4 rows, `A64-P24`), with closure `ADR-0120`. `10_m6_plan.md` fixes the order, the deferrals and the gate set; `fmp/0.1` is unchanged, the standing non-goals stay closed, and the new `EC` rows (plus the `EC-42` direction revision) are declared by each slice's ADR before its rows land. The planned total is 84 new rows and 7 new positives (843 forms, x86 634 / AArch64 185 / RV64 24); the closure records the measured counts | `10_m6_plan.md`; `06_validation_matrix.md`; `02_encoding_choices.md`; `07_definition_format.md` §8.1 |
| ADR-0113 | S1 lands the integer ALU register/register family in the `opcode` direction: `definitions/x86_64/0.75.0.json` appends 15 rows (not the plan's 16: `sub` already had all three widths, `add` had none), namely `add` at 64/32/16 bits and `and`/`or`/`xor`/`cmp` at the same three widths, each with the destination in `REX.B`+`ModRM.r/m` and the source in `REX.R`+`ModRM.reg`; `EC-42` is widened in place to the six `opcode`/`opcode+1` pairs (`01`/`03`, `09`/`0B`, `21`/`23`, `29`/`2B`, `31`/`33`, `39`/`3B`), and the `opcode+1` sibling stays absent. The 64-bit rows reach `%r8`-`%r15` through the REX bits; the 32/16-bit rows stay three-bit. `X86-P81` is the 80-byte vector of 30 instructions (both operand orders); `N01eu` (`adc`), `N01ev` (the sibling direction) and `N01ew` (the `0.74.0` boundary) are `E-FORM-001`, `N02dd` is `E-OPERAND-002` and `N14ch` is `E-OPERAND-004`; 579 forms, digest `sha256:5b13b6b96a4061f354e7d0a371175936cb66c71dbfa80a7eabbf74bfe7eef40d` | `EXP-0112`; `X86-P81`; `N01eu`; `N01ev`; `N01ew`; `N02dd`; `N14ch`; `02_encoding_choices.md`; `07_definition_format.md` §8.1 |
| ADR-0114 | S2 lands the integer ALU immediate family: `definitions/x86_64/0.76.0.json` appends 36 rows -- `add`/`sub` at 32/16 bits (`83 /r ib`, `81 /r id`/`iw`, 8 rows), `and`/`or`/`xor`/`cmp` at 64/32/16 bits in both immediate widths (24 rows), and the four 64-bit `%rax` short forms `25`/`0D`/`35`/`3D` (4 rows) -- for 615 forms, digest `sha256:7535ae0641806b1785096bd286ac62f90f7f02023fd5d47a92b4d4df6371e39a`. `EC-01` is widened in place to `imm8` vs full-width at all three widths for every mnemonic, and `EC-04` is widened to the accumulator form of the four new mnemonics; no new `EC` row. The `imm8` rows sign-extend; the full-width rows carry `imm16` at 16 bits and `imm32` at 32/64 bits. The 64-bit ModRM rows reach `%r8`-`%r15` through `REX.B`; the 32/16-bit rows stay three-bit; the `%rax` form carries only the immediate slot. `X86-P82` is the 176-byte vector of 36 instructions; `N01ex` (`test`) and `N01ey` (the `0.75.0` boundary) are `E-FORM-001`, `N03zw` (`imm8 = 128`) and `N03zx` (`imm16 = 32768`) are `E-RANGE-001` | `EXP-0113`; `X86-P82`; `N01ex`; `N01ey`; `N03zw`; `N03zx`; `02_encoding_choices.md`; `07_definition_format.md` §8.1 |
| ADR-0115 | S3 lands the `mov` immediate family: `definitions/x86_64/0.77.0.json` appends 5 rows -- `B8+rd` at 16/32 bits (destination in the opcode's low three bits) and `C7 /0` at 16/32/64 bits (destination in `ModRM.r/m`) -- for 620 forms, digest `sha256:093d8f3c0abefc04b9c9b4ed421412a1f9a1fe54bf430951653fac0955d4c68b`. The slice is five rows and not the plan's six: `REX.W B8+rd` takes a 64-bit immediate (`io`) and is `movabs`, which stays out; the round total becomes 82 rows and 841 forms. `EC-04` is widened in place to the register-in-opcode pair, so the count stays 42. The 16/32-bit rows stay three-bit (`%r8d`/`%r8w` add a `REX` byte); the 64-bit row reaches `%r8`-`%r15` through `REX.B` in the `REX.W` byte. `X86-P83` is the 54-byte vector of 10 instructions, with a `manual+disassembly` oracle for the `C7 /0` 16/32-bit shapes that `llvm-mc` never selects; `N01ez` (`movabs`) and `N01fa` (the `0.76.0` boundary) are `E-FORM-001`, `N03zy` (`imm32 = 2147483648`) is `E-RANGE-001` | `EXP-0114`; `X86-P83`; `N01ez`; `N01fa`; `N03zy`; `02_encoding_choices.md`; `07_definition_format.md` §8.1 |
| ADR-0116 | S4 lands the `sub` memory directions: `definitions/x86_64/0.78.0.json` appends 12 rows -- `29 /r` (store: memory in `ModRM.r/m`, register in `ModRM.reg`) and `2B /r` (load: memory source in `ModRM.r/m`, register in `ModRM.reg`) at 64/32/16 bits, each with `base + disp8` and `base + disp32` -- for 632 forms, digest `sha256:30cb9f13047ff742d8f53a20f93218a601302bd52814ad26364347cb85576a21`. `EC-42` is widened in place from the register/register pair to the memory direction, so the count stays 42. The 64-bit rows fold `REX.B` into the `REX.W` byte and exclude `%rsp`/`%r12`; the 32/16-bit base stays three-bit. `X86-P84` is the 62-byte vector of 12 instructions with an `assembler` oracle; `N01fb` (absent indexed sibling) and `N01fc` (the `0.77.0` boundary) are `E-FORM-001`, `N03zz` (`disp8 = 128`) is `E-RANGE-001` | `EXP-0115`; `X86-P84`; `N01fb`; `N01fc`; `N03zz`; `02_encoding_choices.md`; `07_definition_format.md` §8.1 |
| ADR-0117 | S5 lands the RV64 load/store widths: `definitions/rv64/0.6.0.json` appends 9 rows -- `lb`/`lh`/`lw`/`lbu`/`lhu`/`lwu` (`0000011`) and `sb`/`sh`/`sw` (`0100011`) -- for 24 forms, digest `sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585`. Each row reuses `ld`/`sd`'s slots and changes only `funct3` (bits 12-14): the loads keep the contiguous `imm` at 31-20, the stores the S-type scatter 31-25|11-7; the generator asserts each UDB node's `match`, scatter, `sign_extend` and base-`I` extension. No `EC` row is added, because the width is chosen by the mnemonic (a form variant), not by a field value. `RV-P12` is the 44-byte vector of 11 instructions with an `assembler` oracle; `N01fd` (absent `fence`) and `N01fe` (the `0.5.0` boundary) are `E-FORM-001`, `N03a0` (`disp = 2048` on `sw`) is `E-RANGE-001` | `EXP-0116`; `RV-P12`; `N01fd`; `N01fe`; `N03a0`; `07_definition_format.md` §8.7 |
| ADR-0118 | S6 lands the AArch64 PC-relative byte address: `definitions/aarch64/0.19.0.json` appends `aarch64:adr/x64-imm21` (`00000010`) for 181 forms, digest `sha256:f299d978b734a295fe111f6e03999d891d08a84e6d02c36ce83ee9a25c961546`. `ADR_only_pcreladdr` is `ADRP_only_pcreladdr` with `op = 0` at bit 31, and `immlo` (29+2) / `immhi` (5+19) is the same split, but the 21 bits are a signed byte displacement from the instruction address rather than a 4 KiB page delta. The slot stays `{ signed: true, bits: 21, align_bits: 0 }` and a symbol is `pcrel_begin` + `identity` (no shift, no pair), against `adrp`'s `pcrel_page` + `page`; `EC-43` is added because one row cannot mean both. `A64-P23` is the 32-byte vector of 8 instructions (five literals including both signed ends, three symbol sites giving 0/-24/-8) with an `assembler` oracle; `N01ff` (absent page variant) and `N01fg` (the `0.18.0` boundary) are `E-FORM-001`, and `N04k` (`imm21 = 1048576`) is `E-RANGE-002`. Measured limit: the materializer does not compare `value_transform` with the mnemonic, so `adr` + `page` is accepted once the target has an address (`EXP-0117/probe_transform.py`) | `EXP-0117`; `A64-P23`; `N01ff`; `N01fg`; `N04k`; `EC-43`; `03_fixup_model.md` §6; `07_definition_format.md` §8.2 |
| ADR-0119 | S7 lands the AArch64 multiply alias and the conditional select: `definitions/aarch64/0.20.0.json` appends four rows -- `aarch64:mul/w32-w32-w32` and `mul/x64-x64-x64` (`007c001b`/`007c009b`) and `aarch64:csel/w32-w32-w32-cond4` and `csel/x64-x64-x64-cond4` (`0000801a`/`0000809a`) -- for 185 forms, digest `sha256:05033c9e1c5ca430d2922312cf7139c9bc4e8cc7c34364e24a455efa9a1df6cd`. `MUL` is an Arm MRS *alias* node (`operation_id` `MUL_MADD`, `condition` `Ra == '11111'`, `preferred: true`, no `encoding`) over `MADD_32A_dp_3src`/`MADD_64A_dp_3src`, so the rows pin `Ra` at 10+5, keep `Rd`/`Rn`/`Rm` at 0/5/16 and name three operands; the four-operand `madd` shape has no row. `CSEL_*_condsel` fixes `op`/`S` at 30-29 and `o2` at 10 and exposes `cond` at 12+4 as the frozen `aarch64.cond`/`cond4` (all sixteen values legal). `EC-44` is added for the `mul`/`madd` split. `A64-P24` is the 32-byte vector of eight instructions (three `mul` rows including `wzr` in `Rm`, five `csel` rows over `eq`/`ne`/`al`/`nv`/`gt`) with an `assembler` oracle; `N01fh` (the `madd` shape named `mul`) and `N01fi` (the `0.19.0` boundary) are `E-FORM-001`, `N02dd` (two operands) is `E-OPERAND-002`, and `N03a1` (`cond = 16`) is `E-RANGE-001`, which corrects the plan's `E-OPERAND-004` claim | `EXP-0118`; `A64-P24`; `N01fh`; `N01fi`; `N02dd`; `N03a1`; `EC-44`; `07_definition_format.md` §8.2 |
| ADR-0120 | Phase 7 M6 closes after the seven slices: the definition set is x86-64 `0.78.0` (632 forms, digest `sha256:30cb9f13…`), `rv64/0.6.0` (24 forms, digest `sha256:0baf3b34…`) and `aarch64/0.20.0` (185 forms, digest `sha256:05033c9e…`) -- 841 forms across 104 documents, every one named by a positive fixture. The corpus at the M6 close was 128 positives and 611 negatives (605 `materialize`-phase plus 6 `read`-phase); `tools/oracle/rerun.py` re-derives `122/128` with six `manual-derivation` skips (`X86-P1`, `X86-P4`, `X86-P5`, `X86-P9`, `X86-P10`, `X86-P83`) and no failures. The round lands 82 rows and not the planned 84, and 841 forms and not 843: `S1` is fifteen rows because `sub` already had all three register/register widths (`ADR-0113`) and `S3` is five because `REX.W B8+rd` is `movabs` (`ADR-0115`). `EC-43`/`EC-44` are the additions and `EC-42` was revised twice, so the registry is 44 rows, all frozen (gate G2). The non-goals stay closed (`moffs`, APX `d5`, EVEX masking/broadcast, AArch64 `EC-16`/`EC-18`, RV64 `c.j`/`c.jalr`, FP/SIMD beyond SSE) together with the round's residue, and no contract change or new artifact level shipped. CI for this commit is `unverified` | `STATUS.md`; `08_final_recommendation.md` §A.3/§D/§F.3/§H; `09_planner_api.md` §5/§7; `tools/oracle/README.md`; `10_m6_plan.md` |
| ADR-0121 | A fixup's covered bits belong to exactly one slot, and that slot is `from: operand_value`: a `reg_number` bit or an inverted placement is the operand path writing the same bits (`E-FIXUP-006`, `first = operand`), while zero slots, two slots, a range across a placement boundary or the right ranges in the wrong order are `E-FIXUP-001`. The descriptor order is the value order, so it must match the slot's placement order. `N07` gains the `E-FIXUP-006` diagnostic beside its existing `E-FIXUP-001`: the measured `x86:mov/rm-r64/legacy` descriptor rewrote `ModRM` after both operands; `N07g` (RV64 `beq`, had emitted `63 00 b5 00`) and `N07h` (AArch64 `b.cond`, had emitted `00 00 00 54`) pin the accepted-and-wrong encodings | `03_fixup_model.md` §3; `01_contract.md` §10; `04_errors.md` §2.1; `N07`; `N07g`; `N07h` |
| ADR-0122 | Numeric domains and the image resource are checked before the arithmetic they protect: `field_descriptor.width` and `range_constraint.bits` are at least 1 (`E-PLAN-002`, read phase), the loader's template and placement arithmetic is checked (`E-DEF-001`), `expected_size` equals `form.size()` (`E-SIZE-001`) and the descriptor bound is `form.size() * 8` (`E-FIXUP-005`), and the `u128` sum of `declared_size` over `section_order` is at most 67,108,864 bytes (`E-LIMIT-001`). The three measured panics were a subtract overflow at `constraint.bits - 1` in `fmp-materialize`, a multiply overflow in `fmp-validate`, and `capacity overflow` in `raw_vec` on a 2^63 `fill` | `04_errors.md` §2.1/§2.4; `01_contract.md` §6/§7/§13; `N05b`; `N24l`; `N25a`; `N25b` |
| ADR-0123 | The v0 surface is closed: `target.kind: section_relative` is refused `E-VERSION-001` at `/fixups/<i>/target/kind` with `feature = target.kind:section_relative`, and a defined symbol's `offset` must be `<= declared_size` (`E-SYMBOL-003`; equality is the one-past-the-end label). `fmp-plan` keeps both as `Unrepresentable`, and `planner_api.rs` cross-checks the refusal pointer through `rebuild_negative` instead of skipping the plans | `01_contract.md` §9/§10; `03_fixup_model.md` §2.1/§10; `N24j`; `N24k`; `09_planner_api.md` §7 |
| ADR-0124 | The contract gates run in CI (`.github/workflows/gates.yml`): `check_ids.py`, `check_definition.py`, the whitespace check over the range the event names on a full checkout, `cargo fmt --all -- --check` with `rustfmt` installed for the pinned toolchain, `cargo test --workspace`, and `rerun.py --allow-skip-reason manual-derivation` against `llvm-mc 23.1.2` installed from the digest-checked `llvmorg-23.1.2` release asset, with a version mismatch treated as a failure. `rerun.py` runs each `&&` stage as argv with `shell=False`, resolves the executable through `PATH`, allows only `llvm-mc`/`llvm-objcopy`/`llvm-readobj`/`ld.lld`, and refuses a token containing a shell metacharacter; an unnamed skip fails. `check_mrs.py`/`check_rv64_source.py` stay local because they read the gitignored `research/external/` | `.github/workflows/gates.yml`; `tools/oracle/README.md`; `04_errors.md` §2.4 |

## Settled decisions (contract level)

| ID | Decision | Evidence |
|---|---|---|
| OD-01 | Plan carries an optional per-instruction `expected_digest`; a hash, never raw bytes; a check, never an input | `EXP-0002` §2–§5 |
| OD-02 | Exactly two fixup modes, one effect each: `resolve_in_place` writes, `emit_relocation` zeroes and records; records are RELA-shaped; the mode never depends on symbol liveness | `EXP-0002` §6; `03_fixup_model.md` §5, §8 |
| OD-03 | v0 emits Level 0 by default; Level 1 (`artifact: sections` + symbol table) is implemented in `ADR-0096`; Level 2 is out of scope | `EXP-0002` §6; `01_contract.md` §11.2 |
| OD-04 | `form_id` is a structured name resolved by exact lookup; a rename is loud (`E-FORM-001`, or `E-DEF-001` first); no opaque id, no `match`/`mask` | `01_contract.md` §7; F-09 |
| OD-06 | The definition digest covers the whole data-only definition in canonical form; a rule change moves it, formatting does not, and a comment is unrepresentable | `EXP-0004` §4; `07_definition_format.md` §6 |
| OD-07 | AArch64 facts come from the Arm MRS 2026-06 OPENSOURCE packaging; our own table is generated from the data, no MPL-2.0 script is copied, and the Arm BSD-3-Clause notice ships with `definitions/aarch64/` | ADR-0005, ADR-0006; `EXP-0007`; `90_boundary_audit.md` F-12, F-13; `definitions/aarch64/NOTICE` |
| OD-09 | Exact integers with declared domains, no wrap, one range check per value after the transform | `01_contract.md` §3.1–§3.2 |
| OD-10 | v0 ships only the forms the slices use; the definition table is the feature surface and absence is `E-FORM-001` | `02_encoding_choices.md`, "v0 surface"; ADR-0004 |
| OD-11 | A byte-affecting decision is carried by `form_id`, a typed operand, a fixup field or a target field — never by a separate choice list | ADR-0004; `02_encoding_choices.md` |
| OD-12 | RV64 facts come from the UDB resolved spec (`sha256:be184986…`), pinned per node; riscv-opcodes is the upstream cross-check and `llvm-mc` the oracle | ADR-0007; `EXP-0009`; `EXP-0010`; `definitions/rv64/NOTICE` |
| OD-13 | A memory operand is field-level: `base`/`disp` are separate operands and the addressing form is a `form_id` variant; a composite `{"mem": …}` payload is `E-OPERAND-003` | ADR-0008; ADR-0013 (AArch64 half); ADR-0027 (x86 RIP half); ADR-0028 (x86 base+disp half); `EXP-0011`; `EXP-0015`; `EXP-0029`; `EXP-0030`; `N15`; `N01b`; `X86-P6`; `X86-P4` |
| OD-14 | A slot may exclude a closed list of exact values inside its domain; the rejection is `E-RANGE-004`, the check is a lookup, and an absent key means no exclusion | ADR-0009; `EXP-0012`; `N16a`/`N16b` |
| OD-15 | A `hi`/`lo` pair expresses RISC-V's "the low half names the high half" with `pcrel_hi` (P = the paired `hi`'s site) and `pcrel_lo12` (mask the displaced value), a zero `lo` addend, and a 1:N group | ADR-0010; psABI `riscv-elf.adoc:1578-1605`; `RV-P8-pcrel-pair`, `RV-P8-pcrel-pair-resolved`; `N17a`/`N17b` |

## Open decisions

See `docs/fmp-v0/05_open_decisions.md`. **No item blocks the slices:** every
`OD-*` row is accepted as of 2026-11-05, with `OD-05` (unknown fields) settled by
ADR-0031 and `OD-08` (canonical wire form) by ADR-0032. The Level 1 artifact
envelope is implemented by `ADR-0096` (amending `OD-03`). OD-07 is settled by ADR-0005 and
pinned by ADR-0006, and the AArch64 tables it authorised now exist: five MRS
nodes generated the forms in `definitions/aarch64/0.1.0.json`, the same nodes
generated `0.2.0.json` with one extra row for the `sh = 1` half of `A64-P2`
(ADR-0011), and `0.3.0.json` adds the `b.cond` row whose condition is an operand
(ADR-0012). `0.4.0.json` adds five load/store rows from five more nodes, one per
addressing kind (`A64-P3`, ADR-0013), `0.5.0.json` adds four `movz` rows from
one node, one per `hw` lane (`A64-P7`, ADR-0014), `0.6.0.json` adds three
shift rows from `ADD_64_addsub_shift`, one per keyword (`A64-P8`, ADR-0015),
`0.7.0.json` adds eight extend rows from `ADD_64_addsub_ext`, one per `option`
value (`A64-P9`, ADR-0016), `0.8.0.json` adds six `sub` rows from
`SUB_64_addsub_shift`/`SUB_64_addsub_imm`, whose nodes fix `op = 1` so the
mnemonic is the form family (`A64-P10`, ADR-0017), and `0.9.0.json` adds twelve
`adds`/`subs` rows from the four `S = 1` nodes, whose `S` bit is fixed by the node
in the same way (`A64-P11`, ADR-0018), `0.10.0.json` adds twenty-four `w`
rows, the same six shapes on the eight `sf = 0` nodes, whose width is fixed by
the node in the same way (`A64-P12`, ADR-0019), `0.11.0.json` adds
twenty-four extended `sub`/`adds`/`subs` rows from the three `op = 1`/`S = 1`
extended nodes (`A64-P13`, ADR-0020), and `0.12.0.json` adds forty `cmp`/`cmn`
alias rows, each the base row with `Rd` pinned to 31 and the destination dropped
(`A64-P14`, ADR-0021), and `0.13.0.json` adds the three store `imm9` rows, the
load rows' layouts with `opc = 00` and the stored register as `src` (`A64-P15`,
ADR-0022), and `0.14.0.json` adds the literal load row, `LDR_64_loadlit` with
`dest` and `target` and no base register (`A64-P16`, ADR-0023), `0.15.0.json`
adds the sixteen register-offset rows, one per `option`/`S` pair on each of the
two register-offset nodes (`A64-P17`, ADR-0024), and `0.16.0.json` adds the
sixteen 32-bit register-offset rows, the same pairs at `size = 10` with `#2` as
the scaled amount and `w32` as the destination/source class (`A64-P18`,
ADR-0025), and `0.17.0.json` adds the eight 64-bit `movk`/`movn` lanes, the four
`hw` values on each of the two `opc`-fixed nodes with `imm16` as field content
(`A64-P19`, ADR-0026).
Twenty positive fixtures match `llvm-mc` (`EXP-0008`, `EXP-0013`, `EXP-0014`, `EXP-0015`,
`EXP-0016`, `EXP-0017`, `EXP-0018`, `EXP-0019`, `EXP-0020`, `EXP-0021`,
`EXP-0022`, `EXP-0023`, `EXP-0024`, `EXP-0025`, `EXP-0026`, `EXP-0027`,
`EXP-0028`). Every directive §6.2 item now has a passing
row; what remains is widening, not a decision.
OD-12 is settled by ADR-0007: the RV64 source is the UDB resolved
spec, pinned by archive and node hashes, `EXP-0009` verified the B/J/RVC scatter
against `llvm-mc`, and `EXP-0010` generated `definitions/rv64/0.1.0.json` (seven
forms) and `0.2.0.json` (eight) from eight of those nodes. OD-13 is
settled by ADR-0008: `EXP-0011` measured that a memory operand spans fields with
different ranges (RV64 `xs1`/`imm`/`xd`), that the x86 encoding form changes with
the displacement value (`48 8b 41 08` vs `48 8b 81 00 10 00 00`), and that the
AArch64 `imm12` is already a scaled field value (`ldr x0, [x1, #16]` →
`imm12 = 2`). `ld`/`sd` are therefore three operands, and `N15` pins the rejected
composite payload. The AArch64 half is pinned by ADR-0013: `disp` is field
content, so the offset kinds are five rows in `aarch64/0.4.0.json`, the store
trio joins them in `0.13.0.json`, the literal in `0.14.0.json` and register
offset in `0.15.0.json` and `0.16.0.json`, so every addressing kind the drop
carries now has a row at both the `x` and `w` widths that have one;
`N01b` still rejects the coarse register-offset id (`ADR-0024`/`ADR-0025`). The
x86 half is pinned by ADR-0027 and ADR-0028: `disp32` with no base is a
`target` operand with a `pcrel_end` fixup, and base+disp8/disp32 is a `base`
operand plus a `disp` operand whose width is the form's, with `%rsp` either a
fixed-base form or `E-RANGE-004` (`X86-P6`, `X86-P4`, `EXP-0029`, `EXP-0030`).
OD-14 is settled by
ADR-0009: `EXP-0012` §2 measured that
`c.addi a0, 0` (`01 05`) and `c.addi x0, 1` (`05 00`) are reserved HINTs despite
being inside the declared range, so the slot excludes `0` and
`riscv:c.addi/rd-imm6` lands in `rv64/0.2.0.json` (`RV-P7`, `N16a`/`N16b`). The
same mechanism keeps the x86 8-bit rows disjoint: `ADR-0029` uses `excluded`
to split numbers 0–3/4–7 between the REX-less, high-byte and REX rows, and
`N16g` pins register 4 in the REX-less row (`E-RANGE-004`). OD-15
is settled by ADR-0010: the ELF psABI (`v2.0-rc0`, `EV-22`) states that the low
half resolves against the high half's site, that its addend must be 0, and that
one high part may serve several low parts, so `pcrel_hi`/`pcrel_lo12` and a 1:N
`pair_group` are now `fmp/0.1` (`RV-P8-pcrel-pair`,
`RV-P8-pcrel-pair-resolved`, `N17a`/`N17b`). OD-06 was
load-bearing because `EXP-0002` W1 shows that a definition drift the digest does
not cover is caught only by the weaker size check; it is now settled, and
`EXP-0004` §4 measures both halves.

## Next action

Phases 3, 4 and 5 are complete, and Phase 6 **M1, M2, M3 and M4 are
complete**. M1 added `N24a`–`N24i`, so `04_errors.md` §2.4 records 38 of the 43
active codes as fixture-covered. M2 added `tools/oracle/rerun.py`: it resolves
each assembler input by `input_sha256` and re-runs the recorded command, so
`122/128` positives reproduce byte-identically; the `6` remaining skips are
`manual-derivation`, and no record is `input-not-stored` any more: the 20
AArch64 and 9 RV64 inputs were recovered from the experiment listings or rebuilt
from the recorded spellings, and 20 of them now reproduce the recorded
`input_sha256` exactly (`tools/oracle/README.md` §"State"). M3 added the Level 1
writer (`ADR-0096`): `artifact: sections` emits `sections[]` in `section_order`,
an optional `symbols[]` in `symbol_order`, and the unchanged Level 0 records;
`X86-P71` and `EXP-0100` validate the envelope and the Level 0 image is still the
oracle's 43 bytes. M4 is **complete**: `prototype/crates/fmp-plan` is the total
closed builder (only workspace dependency `fmp-model`; no materializer crate
links it outside the `fmp-cli` test target), and `planner_api.rs` runs ten
tests — 128 positive and 605 `materialize`-phase negative parity at the M4
close, from-scratch
authoring for `X86-P1`/`A64-P2`/`RV-P1`/`X86-P71`, closed key sets,
optional-member and enum-spelling round trips, fixed-point re-emission,
structural exclusion of the eight `read`-phase negatives (including the audit's
`N25a`/`N25b`), determinism and typed
`Unrepresentable` failures.

M5 coverage widening is **complete** (`08_final_recommendation.md` §H). Seven
first-wave items have landed: `A64-P20` names the three unused `imm6-asr` rows
(and `tools/check_definition.py` now rejects a frozen row no positive fixture
names), `ADR-0098`/`RV-P9` define `hi20` and add `riscv:lui/rd-imm20` as
`definitions/rv64/0.3.0.json` with a positive field vector, an
`emit_relocation` pair and a resolved pair, plus `N01eh` (`c.lui` absent,
`E-FORM-001`) and `N07f` (`hi20` with a PC rule, `E-FIXUP-001`),
`ADR-0099`/`RV-P10` add `riscv:jalr/rd-rs1-imm12` as
`definitions/rv64/0.4.0.json` with the `auipc` + `jalr` call pair (the low half
is the existing `pcrel_lo12`), plus `N01ei` (`c.jalr` absent, `E-FORM-001`) and
`N03x` (`imm12 = 2048`, `E-RANGE-001`), `ADR-0100`/`A64-P21`/`A64-P22` add
`aarch64:b/imm26` and the three register branches as
`definitions/aarch64/0.18.0.json` (180 forms), plus `N04e` (`imm26 = 33554432`,
`E-RANGE-002`), `N19d` (a `link` modifier, `E-OPERAND-003`), `N01x` (`cbz`
absent) and `N01y` (a no-operand `ret`), `ADR-0101`/`X86-P72` add the three
`sub` immediate rows as `definitions/x86_64/0.66.0.json` (512 forms), plus
`N01ej` (the register pair is absent), `N01ek` (the version boundary),
`N02ct` (a `r32` destination) and `N03zs` (`128` on the signed 8-bit
immediate), `ADR-0102`/`X86-P73` add the direct x86 `call rel32` row as
`definitions/x86_64/0.67.0.json` (513 forms), plus `N01el` (the indirect
`FF /2` family is absent), `N01em` (the version boundary), `N02cu` (a register
target), `N02cv` (a missing target) and `N04g` (`2147483648`), and
`ADR-0103`/`X86-P74` add `fmp-def/0.2` per-form `requires_extensions` as
`definitions/x86_64/0.68.0.json` (513 forms, 125 gated), the subset rule and the
step-6 `E-TARGET-003` gate, plus `N06b` (a VEX row with `[]`) and `N06c` (an
extension the table does not declare). The seven-item first wave is complete,
and the oracle recovery backlog that followed it is closed: the 29
`input-not-stored` positive records (20 AArch64, 9 RV64) now resolve by
`input_sha256`, so `tools/oracle/rerun.py` reports `116/121` with only the five
`manual-derivation` skips. The scope decision (`ADR-0111` is reserved for it)
widens the coverage in seven slices, one ADR each: `ADR-0104`/`RV-P11` adds the
five remaining RV64 B-type mnemonics as `definitions/rv64/0.5.0.json` (15 forms),
with `N01en`/`N02cw`/`N04h`; `ADR-0105`/`X86-P75` adds the six SSE
`%rip`-relative rows as `definitions/x86_64/0.69.0.json` (519 forms), with
`N01eo`/`N02cx`/`N04i`, and `ADR-0106`/`X86-P76` adds the eight `xmm8`-`xmm15`
fixed-base legacy SSE rows as `definitions/x86_64/0.70.0.json` (527 forms), with
`N01ep`/`N02cy`/`N03zt`, and `ADR-0107`/`X86-P77` adds the six `0x67`
`%rip`-relative rows as `definitions/x86_64/0.71.0.json` (533 forms), with
`N01eq`/`N02cz`/`N04j`, and `ADR-0108`/`X86-P78` adds the sixteen legacy/VEX
SSE indexed rows as `definitions/x86_64/0.72.0.json` (549 forms), with
`N01er`/`N02da`/`N03zu`, and `ADR-0109`/`X86-P79` adds the twelve indexed
byte `mov` rows as `definitions/x86_64/0.73.0.json` (561 forms), with
`N01es`/`N02db`/`N03zv`, and `ADR-0110`/`X86-P80` adds the three `29 /r`
register/register `sub` rows as `definitions/x86_64/0.74.0.json` (564 forms),
with `N01et`/`N02dc`/`N14cg` and the repointed `N01ej`. `ADR-0111` closes the
phase. The final surface is x86-64 `0.74.0` (564 forms), `rv64/0.5.0` (15 forms)
and `aarch64/0.18.0` (180 forms): 759 forms in all, with every form named by a
positive fixture. At the M5 close the corpus was 121 positives and 586 negatives
(580 `materialize`-phase plus 6 `read`-phase); `tools/oracle/rerun.py` re-derived
`116/121` positives byte-identically, with the five `manual-derivation` skips and
no failures. The accepted non-goals stay closed: `moffs`, APX `d5`, EVEX
masking/broadcast, AArch64 `EC-16`/`EC-18`, RV64 `c.j`/`c.jalr` and FP/SIMD
beyond SSE, plus the slice residue (zero-displacement indexed shapes, the 32/16-bit high-base
window and the index windows, the S7 memory shapes and `2B` r/r).

Phase 7 M6 is **complete** (`ADR-0120`). `ADR-0112` fixed the scope and
`10_m6_plan.md` fixes the seven slices: `S1` x86 ALU register/register
(`ADR-0113`, `x86/0.75.0`, `X86-P81`), `S2` x86 ALU immediate (`ADR-0114`,
`x86/0.76.0`, `X86-P82`), `S3` x86 `mov` immediate (`ADR-0115`, `x86/0.77.0`,
`X86-P83`), `S4` x86 `sub` memory directions (`ADR-0116`, `x86/0.78.0`,
`X86-P84`), `S5` RV64 load/store widths (`ADR-0117`, `rv64/0.6.0`, `RV-P12`),
`S6` AArch64 `adr` (`ADR-0118`, `aarch64/0.19.0`, `A64-P23`) and `S7` AArch64
`mul`+`csel` (`ADR-0119`, `aarch64/0.20.0`, `A64-P24`), with `ADR-0120` as the
closure.

`S1` is **complete** (`ADR-0113`). `definitions/x86_64/0.75.0.json` appends 15
integer ALU register/register rows in the `opcode` direction -- `add` at
64/32/16 bits and `and`/`or`/`xor`/`cmp` at the same three widths -- for 579
forms, with digest
`sha256:5b13b6b96a4061f354e7d0a371175936cb66c71dbfa80a7eabbf74bfe7eef40d`.
The 64-bit rows reach `%r8`-`%r15` through `REX.B`/`REX.R`; the 32/16-bit rows
stay three-bit. `EC-42` is revised in place to the six `opcode`/`opcode+1`
pairs, and the register-destination sibling of every pair stays absent.
`X86-P81-alu-rr` is the 80-byte vector of 30 instructions (both operand orders
for each of the fifteen rows), and `N01eu`/`N01ev`/`N01ew`/`N02dd`/`N14ch` cover
the absent mnemonic, the absent sibling, the `0.74.0` boundary, a missing source
and register `8` on a 32-bit row.

`S2` is **complete** (`ADR-0114`). `definitions/x86_64/0.76.0.json` appends 36
integer ALU immediate rows -- `add`/`sub` at 32/16 bits, `and`/`or`/`xor`/`cmp`
at 64/32/16 bits with `imm8` plus the full-width immediate, and the four 64-bit
`%rax` short forms -- for 615 forms, with digest
`sha256:7535ae0641806b1785096bd286ac62f90f7f02023fd5d47a92b4d4df6371e39a`.
`EC-01` now covers `imm8` vs full-width at 64/32/16 bits for every mnemonic and
`EC-04` covers the accumulator form of the four new mnemonics; no new `EC` row
is needed, so the count stays 42. `X86-P82-alu-imm` is the 176-byte vector of 36
instructions (`imm8` rows at `$1`, full-width rows at `$300`, destination
`%rbx`/`%rcx`), and `N01ex` (`test`), `N01ey` (the `0.75.0` boundary),
`N03zw` (`imm8 = 128`) and `N03zx` (`imm16 = 32768`) cover the rejected cases.
The corpus is now 123 positives and 595 negatives.

`S3` is **complete** (`ADR-0115`). `definitions/x86_64/0.77.0.json` appends 5
`mov` immediate rows -- `B8+rd` at 16/32 bits and `C7 /0` at 16/32/64 bits --
for 620 forms, with digest
`sha256:093d8f3c0abefc04b9c9b4ed421412a1f9a1fe54bf430951653fac0955d4c68b`.
The slice is five rows and not the plan's six: `REX.W B8+rd` takes a 64-bit
immediate and is `movabs`, which stays out. `EC-04` is widened in place to the
register-in-opcode pair (`B8+rd` vs `C7 /0`), so the count stays 42.
`X86-P83-mov-imm` is the 54-byte vector of 10 instructions; its oracle is
`manual+disassembly` because `llvm-mc` always picks `B8+rd` for a 16/32-bit
register destination, and instructions 7-10 are the hand-derived `C7 /0`
shapes confirmed by `llvm-mc -disassemble`. `N01ez` (`movabs`), `N01fa` (the
`0.76.0` boundary) and `N03zy` (`imm32 = 2147483648`) cover the rejected cases.
The corpus is now 124 positives and 598 negatives.

`S4` is **complete** (`ADR-0116`). `definitions/x86_64/0.78.0.json` appends 12
`sub` memory rows -- the `29 /r` store direction and the `2B /r` load direction
at 64/32/16 bits, each with `base + disp8` and `base + disp32` -- for 632
forms, with digest
`sha256:30cb9f13047ff742d8f53a20f93218a601302bd52814ad26364347cb85576a21`.
`29` keeps the memory destination in `ModRM.r/m` and `2B` keeps the memory
source there, with the register in `ModRM.reg` in both, so the same operands
differ only in the opcode byte; `EC-42` is widened in place to the memory
direction and the count stays 42. `X86-P84-sub-mem` is the 62-byte vector of 12
instructions, measured entirely by `llvm-mc`, so the oracle is `assembler` and
the rerun harness re-derives it. `N01fb` (the absent indexed sibling) and
`N01fc` (the `0.77.0` boundary) are `E-FORM-001`, `N03zz` (`disp8 = 128`) is
`E-RANGE-001`. `%rsp`/`%r12` (SIB) and the zero-displacement shape stay out;
the 32/16-bit base stays three-bit. The corpus is now 125 positives and 601
negatives.

`S5` is **complete** (`ADR-0117`). `definitions/rv64/0.6.0.json` appends 9
load/store width rows -- `lb`/`lh`/`lw`/`lbu`/`lhu`/`lwu` on the I-type field
and `sb`/`sh`/`sw` on the S-type scatter, differing from `ld`/`sd` only in
`funct3` -- for 24 forms, with digest
`sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585`.
`RV-P12-load-store-widths` is the 44-byte vector of 11 instructions: the nine
rows at `8(a1)` plus `lb a0, -2048(a1)` and `sw a2, 2047(a1)`, the signed
12-bit ends. `EXP-0116` derives the bytes from the UDB fields and then compares
them with `llvm-mc`, and `llvm-objdump -d` reads the mnemonics back. No `EC` row
is added, because the width is a mnemonic choice rather than a field value;
`fence` (`EC-24`), the atomics and the compressed family stay out. `N01fd`
(absent `fence`) and `N01fe` (the `0.5.0` boundary) are `E-FORM-001`; `N03a0`
(`disp = 2048` on `sw`) is `E-RANGE-001`. The corpus is now 126 positives and
604 negatives.

`S6` is **complete** (`ADR-0118`). `definitions/aarch64/0.19.0.json` appends the
PC-relative `adr` row -- `ADR_only_pcreladdr`, `op = 0` at bit 31, the same
`immlo`/`immhi` split as `adrp` but a signed 21-bit **byte** displacement -- for
181 forms, with digest
`sha256:f299d978b734a295fe111f6e03999d891d08a84e6d02c36ce83ee9a25c961546`.
`A64-P23-adr-imm21` is the 32-byte vector of eight instructions: five literals
including both signed ends (`1048575`, `-1048576`) and three symbol sites giving
`0`, `-24` and `-8`, so the reference point is the instruction and not its end.
`EXP-0117` derives every word from the MRS node, compares it with `llvm-mc`, and
measures the `adr`/`adrp` contrast behind `EC-43` (`adr x0, #0` is `10000000`,
`adrp x0, #0` is `90000000`). It also records the one limit: the materializer
does not couple `value_transform` to the mnemonic, so `adr` with `pcrel_page` +
`page` is `E-FIXUP-002` without a section `base_address` and is accepted with
one. `N01ff` (the absent page variant) and `N01fg` (the `0.18.0` boundary) are
`E-FORM-001`; `N04k` (`imm21 = 1048576`) is `E-RANGE-002`. `S7` (`ADR-0119`)
adds the AArch64 multiply alias and the conditional select as
`definitions/aarch64/0.20.0.json` -- 185 forms, digest
`sha256:05033c9e1c5ca430d2922312cf7139c9bc4e8cc7c34364e24a455efa9a1df6cd`.
`MUL` is the MRS alias `MUL_MADD` over the `MADD` nodes with `Ra` (bits 14-10)
pinned to 31, so `A64-P24-mul-csel` is a 32-byte vector of eight instructions:
three `mul` rows (both widths plus `wzr` in `Rm`) and five `csel` rows over both
widths and `eq`/`ne`/`al`/`nv`/`gt`. `EXP-0118` derives every word from the MRS
node, compares it with `llvm-mc` and re-reads it with `llvm-objdump`, and
measures the two contrasts behind `EC-44`: `mul`/`madd` differ only in bits
14-10 (`9b027c20` vs `9b020c20`) and `csel`/`csinc` only in bit 10 (`9a820020`
vs `9a820420`). `N01fh` (the four-operand `madd` shape named `mul`) and `N01fi`
(the `0.19.0` boundary) are `E-FORM-001`; `N02dd` (two operands) is
`E-OPERAND-002`; `N03a1` (`cond = 16`) is `E-RANGE-001`, which corrects the
plan's `E-OPERAND-004` claim and is noted as such in `10_m6_plan.md` §3. The
corpus is now 128 positives and 611 negatives. The closure `ADR-0120` records
the round: 82 new rows (not the plan's 84) and 841 forms (not 843) across 104
documents, with 128 positives and 611 negatives (605 `materialize`-phase plus
6 `read`-phase). The two differences are the two measured slice corrections --
`S1` is fifteen rows because `sub` already had all three register/register
widths, and `S3` is five because `REX.W B8+rd` is `movabs` -- and no other
count moved. `tools/oracle/rerun.py` re-derives `122/128` records with six
`manual-derivation` skips and no failures; the six are `X86-P1`, `X86-P4`,
`X86-P5`, `X86-P9`, `X86-P10` and `X86-P83`. Phase 7 is complete, the standing
non-goals and the round's residue stay closed, and any further widening needs a
new scope ADR.

The `47a383b` audit is **complete** (`ADR-0121`-`ADR-0124`). It closed the
fixup-ownership hole (`ADR-0121`: `N07` repointed, `N07g`/`N07h` added), bounded
the numeric and resource surface (`ADR-0122`: `N05b`, `N24l`, `N25a`, `N25b`),
closed the v0 surface (`ADR-0123`: `N24j`, `N24k`) and put the gates and the
shell-free oracle rerun in `.github/workflows/gates.yml` (`ADR-0124`). The
living corpus is 128 positives and 619 negatives (611 `materialize`-phase plus 8
`read`-phase), and `04_errors.md` §2.4 records 39 of the 44 active codes. The
first hosted run of those gates (`42677800026`) failed in all three jobs on
setup, not on the contract: the minimal 1.96.0 toolchain had no `cargo-fmt`, the
shallow checkout had no `HEAD^` for the whitespace step, and `apt.llvm.org`
served `llvm-mc 23.1.6` where the records pin `23.1.2`. `ADR-0124` now records
those measured causes: the workflow installs `rustfmt` explicitly, diffs the
whitespace range the event names on a full checkout, and installs the
digest-checked `llvmorg-23.1.2` release asset. The repaired run `42681104791`
(commit `23ad206`) is **green in all three jobs**: `workspace tests`
(formatting plus the suite), `oracle rerun` (`toolchain: llvm-mc 23.1.2`,
`122/128 re-derived, 6 skipped, 0 failed`) and `document and definition gates`
(`whitespace range: 8057508…daf1..HEAD`). The gate set is measured end to end on
a hosted runner, so the next action is a new scope ADR before any further
widening.

**HE-1 is the new scope** (`ADR-0125`, 2026-11-10): the target is a horizontal
extension base — target packages, an immutable definition bundle, a
target-agnostic core and package-level conformance — not more coverage. H0 is
**complete**: the baseline is recorded in
`research/he1/compatibility-results.json` (`payload_root`
`sha256:3f6d177d212642fcf6c2e0efbb717fcf8e936698c5f158f359c6965ecffefad9`;
104 definitions, 128 positives, 619 negatives, `122/128` oracle re-derivations
with the six `manual-derivation` skips), and the seven characterization tests in
`prototype/crates/fmp-cli/tests/he1_identity_characterization.rs` pin four
measured concentration points, one legacy-fingerprint constraint and two
controls. `ADR-0126` splits the artifact identity into a compared payload
projection and an uncompared build receipt, and adds the `baseline` job so the
128 payloads are re-checked on a Linux runner; `tools/test_he1_baseline.py`
(75 tests) turns the eight manual comparator experiments into a CI gate, a fault
now exits 2 rather than sharing exit 1 with a real diff, a document nested too
deeply for Python's JSON reader (`RecursionError`, not a `ValueError`) is now a
fault rather than a traceback with exit 1 on every read path — snapshot, anchor,
fresh plan and materializer stdout — a JSON boolean (`false`/`true`) is not an
integer where `level`, `size` or a count is required, and a structurally
invalid snapshot is refused before the 128 materializations instead of failing
inside the comparator. Structural validation is now complete: projections, both
roots, every entry's envelope, digest types and recomputed roots are checked,
each entry's content is re-hashed into its declared payload and envelope digests,
and derived counts (`definitions.count`, `by_isa` sums, oracle sums, artifacts vs
positives) must agree; a failing toolchain subprocess is recorded as
`unavailable` instead of raising. An entry whose `envelope` was deleted is a
fault even when the comparison would skip it, and a fresh artifact that loses a
required member (`materializer_version`, `level`, `fingerprint`, …) is rejected
before projection. Recording is explicit (`--record`),
and `research/he1/baseline-anchor.json` pins `payload_root` **and**
`definitions_root` independently, so re-recording the snapshot cannot silently
reset either the artifacts or the definition files; a mismatch is a diff
(exit 1), a malformed anchor is a fault (exit 2), and moving either root needs a
compatibility ADR. The definitions root covers the sorted definition path,
raw-file digest and canonical digest, so a whitespace-only edit followed by
`--record` still fails the anchor. The envelope root is deliberately not anchored
because it contains `materializer_version`.
One probe found a real gap rather than a clean result: a 20 000-deep JSON plan
ends the `fmp` process with `0xC00000FD` (stack overflow), which H4 owes a
bounded rejection test. Next: H1b, the binding half of identity closure
(`ADR-0127`); H1a has landed (below). The accepted implementation plan is
`docs/architecture/he1-h1-plan.md`; its sixteen decisions (D1–D16) are recorded,
with D3/D4/D5/D7 revised after the first review, D11/D12 added after the second
(identity layering, and keeping `Plan.document` as a legacy-only input), D4
revised again after the third (allocation failure is
`MaterializationFailure::HostFailure`, not `Internal` or a plan rejection,
because `emit` calls `try_reserve_exact` and §8.3 requires the split), and D13
added after the fourth and expanded after the fifth: `bind` re-runs
`plan::check_structure` on the public mutable `Plan` before producing
`ValidatedPlan`, covering not only X86-P71 odd-length and non-hex `payload_hex`
but all five parser numeric bounds (`lsb` 0–127, `width` 1–64, `bits` 1–64,
`align_bits` 0–12, `transform_shift` 0–63), with `align_bits=128`,
`transform_shift=128`, illegal-width and `u32::MAX` width-sum regression tests in
H1a; the validator's descriptor arithmetic moves to `u64`/`checked_add` as a
second line of defence. The third round also records that
`BindIdentity` is not a full-artifact replay key (a `source_trace`-only change
keeps it equal while `payload_digest` moves) and moves the
definition-mutability test conversion into H1a; the fourth round routes
`MaterializationFailure::Internal` to exit 2 through a distinct internal-fault
channel, so an implementation bug is not reported as a rejected plan. The sixth
round adds **D14**: `offset` is a full `u64`, so `check_fixup_overlap`'s
`offset * 8` must use `u128`/checked arithmetic and the per-bit loops in
`check_one_writer`/`check_fixup_ownership` must be clipped to `form.bits()`;
H1a tests both from a legally parsed JSON plan in debug and release, and requires
bounded completion rather than only "no panic". The same round splits the stage
tests by API (H1a calls `check_structure`/`check` directly; H1b replays the cases
through `bind`) and records that the old fingerprint test is **not** flipped: the
legacy `fingerprint` stays stable, and `ParsedPlanIdentity`/`ExecutionReceipt`
carry the new facts. The seventh round adds **D15** and **D16**: `bind` compares
the full `(namespace, version, digest)` triple against the bound
`Arc<Definition>` (the old `materialize` compared only the digest, and
`Registry::find`'s namespace/version constraint is not on `bind`'s input), with
H1b tests for namespace-only, version-only, digest-compatibility and the legacy
facade; and `page` now requires `pcrel_page`, because `Page` + `PcRule::None`
passed `check_fixup_kind` and fell into `internal(...)` in `emit` — H1a adds the
static `E-FIXUP-001` rule, H1b replays it through `bind`, and H1a fills a 15-row
table in `ADR-0127` naming the static precondition of every `internal(...)`
branch. The round also withdraws the hardcoded "three post-encode failures"
value-snapshot set: the two `E-SIZE-001` negatives are rejected by `validate`
before `emit`, so H1a measures the actual stage and the set is decided there. A
new risk is registered: `reg_number` slots may not declare `range`, so their
total width can reach 64..127 and `1u64 << field_bits` in the validator
overflows in debug; H1a reproduces it and either bounds `width_bits` at load or
compares in `u128`, and "private fields" is explicitly not a discharge. The
eighth round corrects three local points without changing the direction. First,
the H1b width counterexample was contradictory: `bind` runs `check_structure`
first, so the two `u32::MAX` widths must be rejected there with `E-PLAN-002`
and never reach `check`; H1a's direct `check` call stays as the second-line
proof, and §4.2's replay row now gives the expected stage per entry point
instead of reusing one expectation for both. Second, `artifact_entry()` still
read the fresh plan and the materializer stdout with bare `json.loads`, so a
deeply nested document on those paths exited 1; both now use `parse_json()` and
two tests pin it (67 comparator tests total). Third, the `materialize`
signature `compile_fail` test moves from `fmp-validate` to `fmp-materialize`,
with a positive control sharing each import path, because `fmp-validate` cannot
import `fmp-materialize` and the doctest would have stayed green for the wrong
reason. The plan's two stale "current facts" (only `E-SIZE-001`/`E-BYTE-001`
fail after encoding; no host failure inside `materialize`) moved to a §1.3
withdrawn-conclusions table. The ninth round closes two loose ends. First,
`isinstance(value, int)` accepted JSON booleans because `bool` subclasses
`int`: `level: false`, `size: true` and boolean counts passed both validators,
and `True == 1` let a derived-count comparison agree, so a corrupt snapshot
could be reported as a baseline difference instead of a fault. `is_json_integer`
now requires `type(value) is int` and every JSON integer check in
`validate_fresh_artifact()`/`validate_snapshot()` uses it; seven tests cover the
bool cases and a corrupted snapshot exits 2 without calling `snapshot()`
(75 comparator tests total). Second, H1 §5 no longer promises that the fields,
semantics and rejection rules stay unchanged: it now says the document format is
unchanged and existing legal payloads stay byte-identical, while inputs
previously accepted by mistake, never explicitly rejected, or ended in an
internal fault may be tightened, with every new rejection, diagnostic change and
stage migration recorded in the compatibility table and §4.3. The tenth round
binds execution to the hashed file: `resolve_binary("./fmp")` normalised to
`Path("fmp")`, so POSIX `subprocess` searched `PATH` while `sha256_file()` opened
the local file — a same-named PATH program could run while the implementation
receipt recorded a different digest. `resolve_binary()` now returns
`path.resolve()` for explicit and discovered binaries, and a real-subprocess test
with a local `fmp` and a PATH shadow pins the executed program and the recorded
digest to the same file (POSIX-only; CI passes a path with a separator and never
took the bare-name branch). Two
limits
stay open for H1 acceptance rather than being claimed as passed: `FMP_BUILD_ID`
is `None`, and debug/release payload equality is unmeasured.

**H1a is landed** (2026-11-13, branch `he1/h1a-identity-core`, `ADR-0127`;
review amendment 2026-11-14): `Definition` is a closed loaded object (private
fields, no `document`, no `Clone`), `Registry` stores `Vec<Arc<Definition>>` and
`find` returns `Arc<Definition>`, and the new
`fmp_model::identity::ParsedPlanIdentity` defines `plan-identity/0.1` over every
parsed `Plan` field except `legacy_document` and `provenance`, with exhaustive
destructuring and a per-field mutation table so a new field fails the build
until the identity covers it. `Plan.document` is renamed `legacy_document` and
has exactly one reader, the legacy `fingerprint`. `plan::check_structure`
re-checks the parser rules the mutable DTO cannot carry (`format_version`,
`payload_hex`, and the five numeric bounds), and the validator's descriptor
arithmetic and per-bit loops are hardened (`u128`/`u64`/`checked_*`, clipped to
`form.bits()`); the `page ⇒ pcrel_page` precondition is now static
(`E-FIXUP-001`), the register-width overflow is reproduced and fixed by
comparing in `u128`, and `write_field` now extracts each placement from the low
128 bits, so 64/127/128/192-bit register fields encode the expected bytes with a
non-zero register in debug and release (the reviewed tree panicked at 127 in
debug and filled the first placement at 192 in release).
`ADR-0127` carries the 15-row `internal(...)` precondition table plus the
measured post-encode set (four fixtures, three codes; the two `E-SIZE-001`
negatives are static). Three fixed identity vectors are pinned in `ADR-0127`
and recomputed independently by `tools/plan_identity.py --check`, which the
`documents` CI job now runs; the `workspace` job runs the release bound and
wide-field tests, and still fails if `cargo tree -p fmp-validate --edges normal`
reaches `fmp-materialize`. The second `compile_fail` doctest names every
`Definition` field, so it fails only on private access; making all six fields
`pub` in a scratch copy turns both negative doctests red. Neither frozen root
moved: `payload_root` and `definitions_root` are unchanged, and `definitions/`,
`fixtures/`, `docs/fmp-v0/` and the 128 payloads are untouched.
H1a evidence and test names are in `research/he1/H1-report.md`. H1b
(`ValidatedPlan`, `bind`, the new `materialize`, `ExecutionReceipt`,
`MaterializationFailure` and the CLI failure split) is next and **not started**;
the current `materialize` is still the two-argument H0 entry point.
The phase board above
stays the v0 record; HE-1 phases
are reported in `research/he1/`.

### Widening backlog

1. Decide the next format question, one ADR each, before widening any table.
   The AArch64 `-lsl12` half of `A64-P2` is closed without a format change:
   `OD-07`/ADR-0011 pinned `sh = 1` in a second `form_id` and kept the slot as
   `imm12` field content, so `A64-P2` now passes with `N18a`/`N18b` pinning the
   two spellings that must be rejected. Each remaining decision lands with a
   counterexample, an error code where rejection is the answer, and a fixture
   that shows the rejection (`E-FORM-001` or the new code).
   The RV64 pair question is closed: `OD-15`/ADR-0010 added `pcrel_hi` and
   `pcrel_lo12`, and `RV-P8-pcrel-pair` plus `RV-P8-pcrel-pair-resolved` now
   carry the record and arithmetic halves.
   The memory-operand question is closed: `OD-13`/ADR-0008 chose one operand per
   field, `RV-P3` now passes, `A64-P3` is closed by `0.4.0`/ADR-0013, and
   `X86-P6` is closed by `0.2.0`/ADR-0027, the one shape with no base register
   (`mod = 00`, `r/m = 101`, `disp32`), `X86-P4` by `0.3.0`/ADR-0028, which
   enumerated the eight base+disp rows and the `%rsp` SIB pair, and `X86-P5` by
   `0.4.0`/ADR-0029, which made the `0x66` width and the high-byte register set
   form facts. The non-zero question is
   closed too: `OD-14`/ADR-0009 added `excluded`, and `RV-P7` now passes
   (`EXP-0012`).
2. Extend the AArch64 coverage, one vertical slice at a time. All eight directive
   §6.2 items now pass, and every load/store addressing kind the MRS drop carries
   is now a row; the next slices are widening, and each needs its own ADR
   (ADR-0011 decision 7's rule):
   - register offset, the last absent load/store kind, is closed by `A64-P17`:
     ADR-0024 added the sixteen `option`/`S` rows, and `N01b` still rejects the
     coarse id. Its 32-bit half is closed by `A64-P18`: ADR-0025 repeated the
     sixteen rows at `size = 10`, where `S = 1` is `#2` and only `Rt` is `w32`.
   `A64-P4` is closed by `0.3.0`: ADR-0012 made the condition an operand
   (`aarch64.cond`/`cond4`) instead of sixteen forms, and `N03`/`N04c` pin the
   two rejections. `A64-P3` is closed by `0.4.0`: ADR-0013 made each addressing
   kind a form and `disp` field content, `A64-P3-ldst-addressing` matches
   `llvm-mc`, and `N03` ×2 plus `N01b` pin the rejections. `A64-P7` is closed by
   `0.5.0`: ADR-0014 made the `movz` lane a form with `imm16` as field content,
   `A64-P7-movz-lane` matches `llvm-mc`, and `N18c`/`N01d` pin the pre-scaled
   literal and the absent lane. `A64-P8` is closed by `0.6.0`: ADR-0015 made the
   shift keyword a form and `imm6` field content, `A64-P8-shift-modifier` matches
   `llvm-mc`, and `N03-imm6`/`N19`/`N01e` pin the amount, the modifier carrier and
   the absent extend family. `A64-P9` is closed by `0.7.0`: ADR-0016 made the
   extend keyword a form (it also fixes the source width) and `imm3` field content
   with an excluded tail, `A64-P9-extend-modifier` matches `llvm-mc`, and
   `N03-imm3`/`N16c`/`N02b`/`N01f` pin the two ends of the domain, the source class
   and the absent `sub` node. `A64-P10` is closed by `0.8.0`: ADR-0017 made the
   mnemonic the form family, so `sub` repeats the `add` shapes with `op = 1`,
   `A64-P10-sub-family` matches `llvm-mc`, and `N01g`/`N01h`/`N18d` pin the absent
   `subs`, the absent `w` form and the literal that only fits the other `sh` half.
   `A64-P11` is closed by `0.9.0`: ADR-0018 made the flag-setting mnemonic the
   form family too, so `adds`/`subs` repeat the shapes with `S = 1`,
   `A64-P11-adds-subs-family` matches `llvm-mc`, and `N01i`/`N01j`/`N18e` pin the
   absent `cmp` alias, the absent `w` form and the same literal. `A64-P12` is
   closed by `0.10.0`: ADR-0019 made the width the form family too, so the `w`
   rows repeat the six shapes on the eight `sf = 0` nodes with `w32` registers,
   `A64-P12-w-rows` matches `llvm-mc`, and `N01k`/`N02c`/`N16d`/`N18f` pin the
   version boundary, the `x64` operand, `imm6 = 32` and the same literal.
   `A64-P13` is closed by `0.11.0`: ADR-0020 repeated the eight extended rows on
   the `op = 1`/`S = 1` nodes, `A64-P13-ext-family` matches `llvm-mc`, and
   `N01l`/`N02d`/`N16e` pin the absent 32-bit extended node, the wrong `src2`
   class and `imm3 = 5`. `A64-P14` is closed by `0.12.0`: ADR-0021 made
   `cmp`/`cmn` a two-operand alias family whose bytes are the base node's and
   whose alias node is only the pairing check, `A64-P14-cmp-cmn-family` matches
   `llvm-mc`, and `N02e`/`N01i`/`N01m` pin the extra `dest` and the two version
   boundaries. `A64-P15` is closed by `0.13.0`: ADR-0022 added the store
   `imm9` trio as the load rows' layouts with `opc = 00`,
   `A64-P15-store-imm9-addressing` matches `llvm-mc`, and `N03` ×2 plus `N01n`
   pin the two range ends and the version boundary. `A64-P16` is closed by
   `0.14.0`: ADR-0023 added the literal row with `dest`/`target` and no base,
   `A64-P16-loadlit` matches `llvm-mc`, and `N04d`/`N20`/`N01o` pin the field
   end, the alignment split and the version boundary. `A64-P17` is closed by
   `0.15.0`: ADR-0024 added the sixteen register-offset rows with `option` and
   `S` pinned and `Rm` as an `index` slot, `A64-P17-regoff` matches `llvm-mc`,
   and `N01p`/`N01q`/`N02f`/`N19b` pin the version boundary, the absent `-lsl1`
   row, the `w32` index mismatch and the modifier carrier. `A64-P18` is closed by
   `0.16.0`: ADR-0025 repeated the rows at `size = 10`, `A64-P18-w32regoff`
   matches `llvm-mc`, and `N01r`/`N01s`/`N02g`/`N02h`/`N19c` pin the version
   boundary, the absent `-lsl3` row, the `w32` index and `x64` destination
   mismatches and the same modifier rule. `A64-P19` is closed by `0.17.0`:
   ADR-0026 added the four `movk` and four `movn` lanes with `opc` fixed by the
   node, `A64-P19-movwide` matches `llvm-mc`, and
   `N01t`/`N01u`/`N01v`/`N01w`/`N02i`/`N03-movk-imm16`/`N18g` pin the absent
   `-lsl8` lane, the `0.16.0` boundary, the `w32` lane, the `mov` alias, the
   `w32` destination, the field end and the pre-scaled literal. A `:lo12:` inside the
   `-lsl12` form is measured at the record level but is not a symbol address
   (`EXP-0013` §5); a slice that wants one must decide what its addend means
   first.
3. Extend the x86 coverage the same way. `X86-P6` is closed by `0.2.0`:
   ADR-0027 added the two RIP-relative rows with `disp32` as a `target`
   operand, `X86-P6-rip-relative` matches `llvm-mc` (43 bytes, one
   `R_X86_64_PC32` record), and
   `N01x`/`N02j`/`N04e`/`N07b` pin the version boundary, the extra `base`, the
   field end and the operand/fixup mismatch. `X86-P4` is closed by `0.3.0`:
   ADR-0028 added the eight base+displacement rows plus the `%rsp` SIB pair,
   `X86-P4-base-disp` matches `llvm-mc` (51 bytes, no record), and
   `N01y`/`N03-disp8-out-of-range`/`N16f` pin the version boundary, the `disp8`
   field end and the `%rsp` exclusion. `X86-P5` is closed by `0.4.0`: ADR-0029
   added the two 16-bit directions, the high-byte row and the low-byte pair,
   `X86-P5-prefixes` matches `llvm-mc` (20 bytes, no record), and
   `N01z`/`N02k`/`N16g` pin the version boundary, the high-byte operand on a REX
   row and the number-4 exclusion. `X86-P9` is closed by `0.5.0`: ADR-0030 added
   one `movaps` shape in three families (`/legacy`, `/vex`, `/evex`) with the
   prefix as template and the `ModRM` placements following it,
   `X86-P9-sse-vex-evex` matches `llvm-mc` (13 bytes, no record), and
   `N01aa`/`N01ab`/`N02l`/`N06`/`N14c`/`N14d` pin the absent family, the `0.5.0`
   boundary, the `zmm` operand, the extension-list mismatch and the two ends of
   the register field. `X86-P10` widens the six 64-bit register-direct rows in
   `0.6.0` (`ADR-0033`): a `x86.gpr64` slot is four bits, its high bit is a
   placement into `REX.R`/`REX.B`, `X86-P10-gpr-extended` matches `llvm-mc`
   (44 bytes, no record), and `N14c`/`N14d` pin the 3-bit `0.5.0` boundary and
   the 4-bit field end. `X86-P11` continues the same widening into memory: `0.7.0`
   (`ADR-0034`) gives the base+disp rows a 4-bit base and a 4-bit `ModRM.reg`
   operand, excludes both SIB-forcing values (`4`, `12`), and adds four
   fixed-base `%r12` rows that differ from the `%rsp` rows only in `REX.B`;
   `X86-P11-base-extended` matches `llvm-mc` (93 bytes, no record), and
   `N16h`/`N01ac` pin the `%r12` exclusion and the `0.6.0` boundary. `X86-P12`
   closes the third widening step and the last unused `REX` bit: `0.8.0`
   (`ADR-0035`) adds four `base + index*scale + disp` rows whose `SIB` byte is
   template, with a 4-bit `base` that excludes nothing, a 4-bit `index` that
   excludes `4` (the "no index" encoding) and a two-bit scale operand carried as
   field content; `X86-P12-base-index-scale` matches `llvm-mc` (71 bytes, no
   record), and `N16i`/`N03c`/`N01ad` pin the index exclusion, the multiplier
   `8` against the two-bit field and the `0.7.0` boundary. `X86-P13` takes the
   SSE family's memory shape rather than another widening step: `0.9.0`
   (`ADR-0036`) adds twelve `movaps`/`vmovaps` rows across
   `legacy`/`vex`/`evex` and both displacement widths, keeps the base and the
   `xmm` register at three bits in all three families (legacy has no `REX`,
   `C5` has no `B`, EVEX inverts `B̄`/`R̄`), and carries the EVEX `disp8` as the
   compressed field content (`disp8x16`, unit 16) instead of a byte offset;
   `X86-P13-sse-memory` matches `llvm-mc` (96 bytes, no record), and
   `N01ae`/`N14e`/`N14f`/`N14g`/`N16j`/`N03d`/`N02m` pin the version boundary,
   the two 3-bit register fields, the EVEX inverted-bit deferral, the `%rsp`
   exclusion, the field end and the store-row role sequence. `X86-P14` takes
   the widening P13 deferred: `0.10.0` (`ADR-0037`) widens the four EVEX rows
   in place (base `[13,1]` inverted + `[40,3]`, `%r12` excluded with `%rsp`) and
   adds eight `-base-ext` rows for the families whose reach costs a byte
   (legacy `40 0F 28/29 /r` with `REX.B`, three-byte VEX `C4 C1 78 28/29 /r`
   with inverted `B̄`), the two windows excluding each other's values;
   `X86-P14-sse-base-ext` matches `llvm-mc` (104 bytes, no record), and
   `N01af`/`N14h`/`N16k`/`N16l` pin the `0.9.0` boundary, the 4-bit field end
   and the two out-of-window values. `X86-P15` is the register counterpart:
   `0.11.0` (`ADR-0038`) widens `x86.xmm` to four bits, keeps the EVEX
   register-direct pair and the VEX/EVEX memory rows in place (`R̄` at bit 15
   for `ModRM.reg`, `B̄` at bit 13 for the EVEX source and every EVEX/VEX
   base), and adds three legacy register windows (`REX.R`/`REX.B`), two VEX
   register windows (`C5 78 29` for a high source with a low destination,
   `C4 41 78 28` for both high) and four legacy memory rows whose `REX.R` byte
   also carries a 4-bit base; `X86-P15-sse-xmm-ext` matches `llvm-mc` (128
   bytes, no record), the two legal VEX spellings of `vmovaps %xmm8, %xmm0`
   (`c5 78 29 c0`, four bytes; `c4 c1 78 28 c0`, five) are the `EC-09`
   counterexample, and `N01ag`/`N14i`/`N14j`/`N14k`/`N16m`/`N16n` pin the
   boundary, the field ends and the two out-of-window values. `X86-P16` adds the
   shape P14 and P15 left out: `0.12.0` (`ADR-0039`) gives the three families
   twelve `mod = 00` rows with no `disp` slot, so `movaps (%rax), %xmm0` is
   `0f 28 00`, three bytes. No displacement and `disp8 = 0` are one instruction
   at two lengths (`0f 28 00` versus `0f 28 40 00`), so the width stays a form;
   `%rsp`/`%r12` force a `SIB` byte and `%rbp`/`%r13` collide with
   `r/m = 101`, so those bases remain on the `disp8` row with displacement `0`;
   `X86-P16-sse-no-disp` matches `llvm-mc` (72 bytes, no record), and
   `N01ah`/`N14l`/`N16o`/`N16p`/`N16q` pin the boundary, the 4-bit base end,
   `%rsp`, `%rbp` and a low base on the legacy high-base row. `X86-P17`
   completes the register reach: `0.13.0` (`ADR-0040`) widens the `xmm` slot of
   the seven EVEX rows from four bits to five in place, so bit 4 is the
   inverted `R̄'` for `ModRM.reg` and the inverted `X̄` for a register-direct
   `ModRM.rm`; `vmovaps %xmm31, %xmm30` is `62 01 7c 08 28 f7`, six bytes, and
   no row is added and no length changes; `X86-P17-sse-xmm16-31` matches
   `llvm-mc` (112 bytes, no record), and
   `N14m`/`N14n`/`N14o` pin the version boundary, the 5-bit field end (`xmm32`)
   and the VEX family boundary. `X86-P18` turns width into a form fact:
   `0.14.0` (`ADR-0041`) adds five register-direct `ymm`/`zmm` rows and the
   kinds `x86.ymm`/`ymm` and `x86.zmm`/`zmm`. The mnemonic is unchanged, so the
   width is one prefix field — VEX `L` (`c5 fc 28 c1` versus `c5 f8 28 c1`) or
   EVEX `L'L` (`62 f1 7c 28 28 c1` versus `62 f1 7c 48 28 c1`) — and the three
   VEX.256 windows repeat P15's `xmm` windows (high destination in `R̄`, high
   source through opcode 29, both-high through three-byte `C4`). `X86-P18-sse-ymm-zmm`
   matches `llvm-mc` (84 bytes, no record), and `N01ai`/`N01aj`/`N02n`/`N14p`/`N14q`
   pin the version boundary, the absent legacy width, a width mismatch, the VEX
   field end and the EVEX field end. `X86-P19` turns the compressed
   displacement unit into a form fact: `0.15.0` (`ADR-0042`) adds twelve memory
   rows — the six `0.13.0` `xmm` memory shapes at `ymm` and `zmm`, differing
   only in `P2` — and revises `EC-39` so `N` is the row's `target_type`
   (`disp8x32`/`disp8x64`). Content `1` is `32` bytes at `ymm` and `64` at
   `zmm`, so `4064`/`−4096` are the `disp8x32` ends and `8128`/`−8192` the
   `disp8x64` ends, while `28`, `4096`, `60` and `8192` are `disp32` rows;
   `X86-P19-sse-ymm-zmm-memory` matches `llvm-mc` (192 bytes, no record), and
   `N01ak`/`N01al`/`N02o`/`N02p`/`N03e`/`N14r` pin the `0.14.0` boundary, the
   absent VEX.256 memory row, the width and unit mismatches, the content field
   end and the five-bit vector field end. `X86-P20` closes the VEX width axis
   without adding a fact: `0.16.0` (`ADR-0043`) adds twelve VEX.256 memory rows
   mirroring the `0.11.0`/`0.12.0` VEX rows at `L = 1` — the low-base two-byte
   window (`c5 fc …`) and the high-base three-byte window (`c4 c1 7c …`), each
   with the `disp8`, `disp32` and `mod = 00` pairs. The displacement is a plain
   signed byte, not a compressed unit, and the four-bit vector slot and both
   base windows carry over unchanged; `X86-P20-vex-ymm-memory` matches `llvm-mc`
   (144 bytes, no record), and `N01am`/`N02q`/`N03f`/`N14s`/`N16r`/`N16s` pin
   the version boundary, the width mismatch, the content field end, the vector
   field end and the two base exclusions. `X86-P21` carries the prefix and
   byte-register facts into a memory operand: `0.17.0` (`ADR-0044`) adds
   sixteen rows — four word (`66 8b`/`66 89`) and twelve byte (REX-less low,
   high, and `40`-prefixed) rows, each with `disp8` and `disp32` — because the
   `0x66` byte and the three disjoint byte sets are already form facts
   (`EC-36`) and the width is never an operand. Every base stays the three-bit
   window 0–7 minus `%rsp`; `X86-P21-mov-mem-8-16` matches `llvm-mc` (122 bytes,
   no record), and
   `N01an`/`N02r`/`N02s`/`N03g`/`N14t`/`N16t`/`N16u` pin the version boundary,
   the two operand-class mismatches, the content field end, the deferred
   `-base-ext` case, the high-byte number and the `%rsp` exclusion. Every
   directive §6.1 row is carried; the remaining widening is the EVEX `SIB` base,
   the SSE RIP-relative row, `mod = 00` for the GPR rows, the `0x67` prefix,
   index/scale under the 8/16-bit `mov` opcodes, the four-bit
   `r8b`–`r15b`/`r8w`–`r15w` registers, the legacy `REX.R` SSE window with a
   fixed base, and EVEX masking. `X86-P22` takes the first of those: `0.18.0`
   (`ADR-0045`) adds eight `-base-ext` rows and widens
   the four `40`-prefixed byte rows in place, because the word and low-byte rows
   have no `REX` byte, so a high base adds one and the length is the form's
   (`INV-04`), while the `40` rows already carry it. `REX.B` is bit 8 after the
   `66` byte on the word rows and bit 0 on the byte rows; the byte registers
   split 0–3 on the new rows and 4–7 on the widened ones, so one
   `(register, base)` pair names one row, and the high-byte set has no encoding
   with a high base. `X86-P22-mov-mem-base-ext` matches `llvm-mc` (100 bytes, no
   record), and `N01ao`/`N02t`/`N14u`/`N16v`/`N16w`/`N16x` pin the version
   boundary, the high-byte refusal, the four-bit field end and the two disjoint
   windows. `X86-P23` then adds the two bases that slice left out: `0.19.0`
   (`ADR-0046`) appends twenty-eight fixed-base `SIB` rows, because `%rsp` spends
   a `SIB` byte and `%r12` spends `REX.B` on top, so the base is a template fact
   and the row carries only the register and the displacement; the high-byte
   family gets `%rsp` only, since `movb %ah, 8(%r12)` has no encoding.
   `X86-P23-mov-mem-sib` matches `llvm-mc` (178 bytes, no record), and
   `N01ap`/`N01aq`/`N02u`/`N03h`/`N14v`/`N16y` pin the version boundary, the
   absent high-byte row, the width mismatch, the content field end, the
   three-bit register field and the `40` register window. `X86-P24` repeats the
   `SIB` decision inside the SSE families: `0.20.0` (`ADR-0047`) appends sixteen
   fixed-base rows — legacy `movaps` and VEX `vmovaps`, load/store ×
   `disp8`/`disp32` × `%rsp`/`%r12` — with the base in the template and each
   family's register window inherited, so the legacy field stays three bits
   while the VEX `R̄` already reaches `xmm8`–`xmm15`; `%r12` costs `REX.B` in
   the legacy family and the three-byte prefix in the VEX one.
   `X86-P24-sse-mem-sib` matches `llvm-mc` (120 bytes, no record), and
   `N01ar`/`N01as`/`N02v`/`N02w`/`N03i`/`N14w` pin the version boundary, the
   absent `mod = 00` shape, the operand class, the extra `base` operand, the
   content field end and the legacy three-bit register field.
   `X86-P25` then repeats the same `SIB` decision in the EVEX family:
   `0.21.0` (`ADR-0048`) appends twenty-four fixed-base rows —
   `xmm`/`ymm`/`zmm` × load/store × `disp8*N`/`disp32` ×
   `%rsp`/`%r12`. There the base costs no prefix byte: the fourth bit is
   already the inverted `B̄` in `P0`, so `62 f1 …` and
   `62 d1 …` are the same length; the prefix does not grow, so the
   vector slot stays at `[43,3]` and only the displacement moves, from bit
   48 to 56. A displacement that is not a multiple of `N` promotes to
   `disp32` rather than truncating, and the five-bit slot already reaches
   `xmm31` at no length cost. `X86-P25-evex-mem-sib` matches `llvm-mc`
   (228 bytes, no record), and `N01at`/`N01au`/`N02x`/`N02y`/`N03j`/`N14x`
   pin the version boundary, the absent `mod = 00` shape, the operand
   class, the extra `base` operand, the content field end and the
   five-bit register field. `X86-P26` closes the `mod = 00` half of that
   axis: `0.22.0` (`ADR-0049`) appends twelve fixed-base rows —
   `xmm`/`ymm`/`zmm` × load/store × `%rsp`/`%r12`. `r/m = 100` moves the
   base into the `SIB` byte and `mod = 00` drops the displacement slot, so
   `(%rsp)` is `62 f1 7c 08 28 04 24` and `(%r12)` is
   `62 d1 7c 08 28 04 24`: seven bytes, still differing only in `P0`.
   `%rbp`/`%r13` cannot use the shape (`mod = 00`, `r/m = 101` is
   RIP-relative) and keep `62 … 45 00` on the `-base` row, and `llvm-mc`
   canonicalizes `0(%rsp)` to `(%rsp)`, so the row is the only encoding of
   a zero offset. `X86-P26-evex-mem-sib-nodisp` matches `llvm-mc`
   (84 bytes, no record), and `N01av`/`N01aw`/`N02z`/`N02aa`/`N14y`/`N16z`
   pin the version boundary, the absent `%rbp` shape, the operand class,
   the extra `disp` operand, the five-bit register field and `%rsp` on the
   general row. `X86-P27` opens that byte to an index and a scale: `0.23.0`
   (`ADR-0050`) appends eighteen rows — three widths × load/store ×
   none/`disp8*N`/`disp32` — with the base an operand again. `r/m = 100`
   announces the `SIB` byte, so `ModRM` is `04`/`44`/`84`; base is `[48,3]`
   plus the inverted `B̄`, index `[51,3]` plus the inverted `X̄`, and scale
   `[54,2]`. `(%rsp,%rax,1)` is `62 f1 7c 08 28 04 04` and
   `(%rsp,%r12,1)` is `62 b1 7c 08 28 04 24`, so `X̄` is the index's fourth
   bit; index `4` is the "no index" encoding, and on the `mod = 00` rows
   `SIB.base = 101` means "no base, `disp32`", so `%rbp`/`%r13` are excluded
   there and keep the `disp8*N = 0` row. `X86-P27-evex-mem-sib-index` matches
   `llvm-mc` (156 bytes, no record), and
   `N01ax`/`N01ay`/`N02ab`/`N02ac`/`N16aa`/`N16ab` pin the version boundary
   in both directions, the scale carried as `x86.imm`, the extra `disp`
   operand, the index exclusion and the no-base base exclusion.
   `X86-P28` takes the last `SIB` base choice: `0.24.0` (`ADR-0051`) appends six
   rows — three widths × load/store, `disp32` only — with no `base` role at all.
   `mod = 00` with `SIB.base = 101` means "no base, `disp32`", so `ModRM` stays
   `04`, the template carries `05` and four displacement bytes, and every row is
   eleven bytes; `(,%rax,4)` is `62 f1 7c 08 28 0c 85 00 00 00 00` and
   `-4096(,%r12,8), %xmm3` is `62 b1 7c 08 28 1c e5 00 f0 ff ff`. `X86-P28-evex-mem-sib-nobase-index`
   matches `llvm-mc` (66 bytes, no record), and
   `N01az`/`N01ba`/`N02ad`/`N02ae`/`N03k`/`N16ac` pin the version boundary in
   both directions, the supplied base, the scale carrier, the `disp32` end and
   the index exclusion.
   `X86-P29` takes the last `SIB` combination: `0.25.0` (`ADR-0052`) appends six
   rows — three widths × load/store, `disp32` only — with neither a `base` nor an
   `index` role. `SIB = 25` spends both register fields on constants (index
   `100`, base `101`), so `ModRM` stays `04`, the address is four bytes and every
   row is eleven bytes: `0x1234, %xmm0` is
   `62 f1 7c 08 28 04 25 34 12 00 00`, and `0` and `0x7fff` still spend the full
   field. `X86-P29-evex-mem-sib-absolute` matches `llvm-mc` (66 bytes, no
   record), and `N01bb`/`N01bc`/`N02af`/`N02ag`/`N03l` pin the version boundary
   in both directions, the supplied `index`, the `disp8` address and the
   `disp32` end.
   `X86-P30` carries the same shape into the 64-bit GPR `mov` family: `0.26.0`
   (`ADR-0053`) appends two rows — load and store — with `ModRM = 04`, the
   constant `SIB = 25` and a four-byte address at `[32,32]`, so each row is
   eight bytes; `0x1234, %rax` is `48 8b 04 25 34 12 00 00` and `%r15, 0x1234`
   is `4c 89 3c 25 34 12 00 00`. `moffs` (`A0`–`A3`) stays absent, freezing
   `EC-05`. `X86-P30-gpr-mov-abs32` matches `llvm-mc` (48 bytes, no record), and
   `N01bd`/`N01be`/`N01bf`/`N02ah`/`N02ai`/`N03m`/`N14z` pin the version
   boundary in both directions, the absent `moffs` row, the supplied `base`, the
   `disp8` address, the `disp32` end and the register field end.
   `X86-P31` takes the same address into the 32-bit GPR `mov` rows, which are
   not one row: `movl 0x1234, %eax` is `8b 04 25 34 12 00 00` (seven bytes, no
   `REX` byte) while `movl 0x1234, %r8d` is `44 8b 04 25 34 12 00 00` (eight
   bytes, `REX = 44`). `0.27.0` (`ADR-0054`) appends four rows — load and store,
   each low and `-ext` — with `ModRM = 04`, `SIB = 25` and the address at
   `[24,32]` or `[32,32]`; the low register is the three-bit `ModRM.reg` at
   `[11,3]`, the `-ext` register is `[19,3]` plus `REX.R` at `[2,1]` with
   `0`–`7` excluded. `X86-P31-gpr32-mov-abs32` matches `llvm-mc` (45 bytes, four
   seven-byte and two eight-byte instructions, no record), and
   `N01bg`/`N01bh`/`N02aj`/`N02ak`/`N02al`/`N03n`/`N14aa`/`N16ad` pin both
   version boundaries, the supplied `base`, the `disp8` address, the 64-bit
   operand on an `r32` row, the `disp32` end, the register field end and the
   excluded low window.
   `X86-P32` takes the shape one width down, behind the operand-size prefix:
   `movw 0x1234, %ax` is `66 8b 04 25 34 12 00 00` (eight bytes, no `REX`
   byte) while `movw 0x1234, %r8w` is `66 44 8b 04 25 34 12 00 00` (nine
   bytes, `REX = 44`). `0.28.0` (`ADR-0055`) appends four rows with
   `ModRM = 04`, `SIB = 25` and the address at `[32,32]` or `[40,32]`; the
   low register is `[19,3]`, the `-ext` register is `[27,3]` plus `REX.R` at
   `[10,1]` with `0`–`7` excluded. The address does not narrow with the
   operand: `-32768` is `00 80 ff ff`, and `0x80000000` switches `llvm-mc`
   to `movabsw`. `X86-P32-gpr16-mov-abs32` matches `llvm-mc` (51 bytes, four
   eight-byte and two nine-byte instructions, no record), and
   `N01bi`/`N01bj`/`N02am`/`N02an`/`N02ao`/`N03o`/`N14ab`/`N16ae` pin both
   version boundaries, the supplied `base`, the `disp8` address, the 32-bit
   operand on an `r16` row, the `disp32` end, the register field end and the
   excluded low window.
   `X86-P33` closes the axis at eight bits, where the same three-bit field
   names two register sets: `movb 0x1234, %al` is `8a 04 25 34 12 00 00` and
   `movb 0x1234, %ah` is `8a 24 25 34 12 00 00` (seven bytes each, no `REX`
   byte), while `movb 0x1234, %spl` is `40 8a 24 25 34 12 00 00` and
   `movb 0x1234, %r8b` is `44 8a 04 25 34 12 00 00` (eight bytes). `0.29.0`
   (`ADR-0056`) appends eight rows with `ModRM` `04`/`24`, `SIB = 25` and the
   address at `[24,32]` or `[32,32]`; the plain register is `[11,3]`, the two
   `REX` windows are `[19,3]`, and the extended one adds `REX.R` at `[2,1]`.
   The address does not narrow with the operand: `-128` is `80 ff ff ff` and
   `0x80000000` switches `llvm-mc` to `movabsb` for the low rows.
   `X86-P33-gpr8-mov-abs32` matches `llvm-mc` (60 bytes, four seven-byte and
   four eight-byte instructions, no record), and
   `N01bk`/`N01bl`/`N02ap`/`N02aq`/`N02ar`/`N02as`/`N03p`/`N14ac`/`N16af`
   pin both version boundaries, the supplied `base`, the `disp8` address, the
   16-bit operand on an `r8` row, the high-byte kind on the low-byte row, the
   `disp32` end, the register field end and the excluded low window.
   `X86-P34` carries that window into the memory rows, where the register
   and the base can both need an extension and one `REX` byte holds both
   bits: `movb 8(%rax), %r8b` is `44 8a 40 08` and `movb 8(%r8), %r8b` is
   `45 8a 40 08` (four bytes each, `REX.R` at `[2,1]`, `REX.B` at `[0,1]`,
   the register at `[19,3]` and the base at `[16,3]`), while
   `movb 8(%rsp), %r8b` is `44 8a 44 24 08` (five bytes, `SIB = 24`, the
   displacement at `[32,8]`) and `movb 8(%r12), %r8b` is `45 8a 44 24 08`
   (the same `SIB` byte with `REX.B = 1`). `%rbp` and `%r13` need no row
   because `mod = 01` is the family's floor (`movb 8(%rbp), %r15b` is
   `44 8a 7d 08`), and the high-byte kind cannot join (`movb 8(%rax), %ah`
   is `8a 60 08`, `movb 8(%r8), %ah` is rejected). `0.30.0` (`ADR-0057`)
   appends twelve rows: both directions × three base windows ×
   disp8/disp32. `X86-P34-gpr8-ext-mem` matches `llvm-mc` (74 bytes, six
   four- and five-byte instructions beside six seven- and eight-byte
   ones, no record), and
   `N01bm`/`N01bn`/`N02at`/`N02au`/`N02av`/`N03q`/`N14ad`/`N16ag`/
   `N16ah`/`N16ai` pin both version boundaries, the high-byte kind on an
   extended row, the `disp8` displacement on a `disp32` row, the extra
   `base` on a `SIB` row, the `disp32` end, the register field end, the
   excluded low window and the two `SIB`-forcing bases.
   `X86-P35` takes the third displacement shape (`ADR-0058`):
   `movb (%rax), %al` is `8a 00` and `movb %cl, (%rcx)` is `88 09` (two
   bytes, opcode at `[0,8]`, `ModRM` at `[8,8]`, register `[11,3]`, base
   `[8,3]`), while `movb (%rsi), %dil` is `40 8a 3e` and
   `movb %r15b, (%r9)` is `45 88 39` (three bytes, register `[19,3]`
   plus `REX.R` at `[2,1]`, base `[16,3]` plus `REX.B` at `[0,1]`).
   `%rbp` and `%r13` cannot inhabit it — `r/m = 101` at `mod = 00`
   is RIP-relative `disp32`, so `llvm-mc` writes `movb (%rbp), %al` as
   `8a 45 00` — and `%rsp`/`%r12` need the `SIB` byte
   (`8a 04 24`, `41 8a 04 24`) left to the next slice. `0.31.0` appends
   eight rows: both directions × four register windows.
   `X86-P35-gpr8-mov-mem-nodisp` matches `llvm-mc` (20 bytes, four
   two-byte and four three-byte instructions, no record), and
   `N01bo`/`N01bp`/`N02aw`/`N02ax`/`N14ae`/`N16aj`/`N16ak`/`N16al`/
   `N16am` pin both version boundaries, the high-byte kind on the low
   row, the refused `disp` operand, the three-bit base end, the two
   RIP-relative collisions and the two `SIB`-forcing bases.
   `X86-P36` closes that deferral (`ADR-0059`): `movb (%rsp), %al` is
   `8a 04 24` and `movb (%r12), %al` is `41 8a 04 24`, the same three
   bytes after a `REX` byte whose `B` bit alone picks the base, with
   `SIB = 24` at `[16,8]` (or `[24,8]` behind the prefix) and the
   register at `[11,3]` (or `[19,3]`). The high-byte window has only the
   `%rsp` half, because `REX.B` renames `%ah` to `%spl`. `0.32.0` appends
   fourteen rows (both directions × seven base/register combinations)
   with the base fixed in the template, so a `base` or `disp` operand is
   `E-OPERAND-002`. `X86-P36-gpr8-mov-mem-sib-nodisp` matches `llvm-mc`
   (52 bytes, four three-byte and ten four-byte instructions, no
   record), and `N01bq`/`N01br`/`N01bs`/`N02ay`/`N02az`/`N14af`/
   `N14ag`/`N16an` pin both version boundaries, the unencodable
   high-byte `%r12` row, the extra `base` and `disp` operands, the
   three-bit field end and the `REX = 40` exclusion.
   `X86-P37` gives the 64-bit family the same shape (`ADR-0060`):
   `movq (%rax), %rax` is `48 8b 00` — three bytes with `REX.W` in the
   template, both register fields four bits wide, and one row for every
   register and base, so `movq (%r9), %r15` is `4d 8b 39`. The base slot
   excludes `%rbp`/`%r13` (RIP-relative at `r/m = 101`) and
   `%rsp`/`%r12` (`SIB` byte), and `llvm-mc` normalises an explicit zero
   displacement on a plain base to the short form, so the plan names the
   row. `0.33.0` appends two rows, both directions; a `disp` operand is
   `E-OPERAND-002`, register `16` is `E-OPERAND-004`, the four bases are
   `E-RANGE-004`. `X86-P37-gpr64-mov-mem-nodisp` matches `llvm-mc`
   (18 bytes, six three-byte instructions, no record), and
   `N01bt`/`N01bu`/`N02ba`/`N14ah`/`N16ao`–`N16ar` pin both version
   boundaries, the refused `disp` operand, the four-bit field end and the
   four excluded bases.
   `X86-P38` takes the two `SIB` bases onto that shape (`ADR-0061`):
   `movq (%rsp), %rax` is `48 8b 04 24` and `movq (%r12), %rax` is
   `49 8b 04 24` — four bytes, `ModRM = 04` and `SIB = 24` — with the base
   and its `REX.B` in the template, so only `REX.R` is a slot and one row
   per base and direction covers all sixteen registers (`movq (%rsp), %r8`
   is `4c 8b 04 24`). `0.34.0` appends four rows; a `base` or `disp`
   operand is `E-OPERAND-002`, register `16` is `E-OPERAND-004`.
   `X86-P38-gpr64-mov-mem-sib-nodisp` matches `llvm-mc` (32 bytes, eight
   four-byte instructions, no record), and
   `N01bv`/`N01bw`/`N02bb`/`N02bc`/`N14ai` pin both version boundaries,
   the two refused operands and the four-bit field end.
   `X86-P39` gives the 32-bit family its first base rows (`ADR-0062`):
   `movl (%rax), %eax` is `8b 00` and `movl %eax, (%rax)` is `89 00` —
   two bytes, `mod = 00`, no displacement. The legacy row has no `REX`
   byte, so a high register or base changes the length and the reach is
   the form: `movl (%rax), %r8d` is `44 8b 00` (`REX.R`),
   `movl (%r8), %eax` is `41 8b 00` (`REX.B`), and `movl (%r9), %r15d`
   is `45 8b 39`; the three windows are disjoint, and every row excludes
   `%rsp`/`%r12` (`SIB`) and `%rbp`/`%r13` (RIP-relative). `0.35.0`
   appends six rows; a `disp` operand is `E-OPERAND-002`, the field ends
   are `E-OPERAND-004`, the exclusions are `E-RANGE-004`.
   `X86-P39-gpr32-mov-mem-nodisp` matches `llvm-mc` (32 bytes, twelve
   instructions, no record), and
   `N01bx`/`N01by`/`N02bd`/`N14aj`/`N14ak`/`N16as`–`N16av` pin both
   version boundaries, the refused operand, both field ends and the
   excluded bases and windows.
   `X86-P40` takes the `%rsp`/`%r12` `SIB` bases onto that family
   (`ADR-0063`): `movl (%rsp), %eax` is `8b 04 24` and
   `movl (%r12), %eax` is `41 8b 04 24` — `ModRM = 04` plus `SIB = 24`,
   the base and its `REX.B` in the template. The two bases share the low
   three bits `100`, so each needs its own row; the register window still
   splits, so `%rsp` is three bytes in the low window and four in the
   `REX.R` window (`44 8b 04 24`), while every `%r12` row is four
   (`41`/`45`). `0.36.0` appends eight rows; a `base`/`disp` operand is
   `E-OPERAND-002`, the field ends are `E-OPERAND-004`, the `-ext` floor
   is `E-RANGE-004`. `X86-P40-gpr32-mov-mem-sib-nodisp` matches `llvm-mc`
   (60 bytes, sixteen instructions, no record), and
   `N01bz`/`N01ca`/`N02be`/`N02bf`/`N14al`/`N14am`/`N16aw` pin the two
   version boundaries, the two refused operands, both field ends and the
   register-window floor.
   `X86-P41` gives the family the plain-base `disp8` shape (`ADR-0064`):
   `movl 8(%rax), %eax` is `8b 40 08` and `movl %eax, 8(%rax)` is
   `89 40 08` — three bytes, `mod = 01`, the base in `ModRM.r/m` and a
   signed byte at `[16,8]` (`-128…127`). The reach is still three rows:
   `44 8b 40 08` (`REX.R`), `41 8b 40 08` (`REX.B`) and `45 8b 79 08`
   (both), with the displacement at `[24,8]`. At `mod = 01`
   `%rbp`/`%r13` are ordinary bases (`8b 45 08`), so only `%rsp`/`%r12`
   stay excluded; the `REX.B` row also keeps the low bases out. `0.37.0`
   appends six rows; a missing `disp` is `E-OPERAND-002`, `128` is
   `E-RANGE-001`, the field ends are `E-OPERAND-004`, the windows are
   `E-RANGE-004`. `X86-P41-gpr32-mov-mem-disp8` matches `llvm-mc`
   (44 bytes, twelve instructions, no record), and
   `N01cb`/`N01cc`/`N02bg`/`N03r`/`N14an`/`N14ao`/`N16ax`/`N16ay`/`N16az`/`N16ba`
   pin both version boundaries, the missing displacement, the range end,
   both field ends and the four window edges.
   `X86-P42` completes the displacement axis for that family (`ADR-0065`):
   `movl 200(%rax), %eax` is `8b 80 c8 00 00 00` and
   `movl %eax, 200(%rax)` is `89 80 c8 00 00 00` — six bytes,
   `mod = 10`, the base in `ModRM.r/m` and a signed 32-bit displacement at
   `[16,32]` (`-2147483648…2147483647`). The reach is again three rows:
   `44 8b 80 c8 00 00 00` (`REX.R`), `41 8b 80 c8 00 00 00` (`REX.B`) and
   `45 8b b9 c8 00 00 00` (both), with the displacement at `[24,32]`.
   `%rbp`/`%r13` are ordinary bases (`8b 85 c8 00 00 00`), so only
   `%rsp`/`%r12` stay excluded; the `REX.B` row also keeps the low bases
   out. `0.38.0` appends six rows; a missing `disp` is
   `E-OPERAND-002`, `2147483648` is `E-RANGE-001`, the field ends are
   `E-OPERAND-004`, the windows are `E-RANGE-004`.
   `X86-P42-gpr32-mov-mem-disp32` matches `llvm-mc` (80 bytes, twelve
   instructions, no record), and
   `N01cd`/`N01ce`/`N02bh`/`N03s`/`N14ap`/`N14aq`/`N16bb`/`N16bc`/`N16bd`/`N16be`
   pin both version boundaries, the missing displacement, the range end,
   both field ends and the four window edges.
   `X86-P43` combines the `SIB` bases with the `disp8` shape
   (`ADR-0066`): `movl 8(%rsp), %eax` is `8b 44 24 08` and
   `movl %eax, 8(%rsp)` is `89 44 24 08` — four bytes, `mod = 01`,
   `SIB = 24` and a signed byte at `[24,8]` (`-128…127`). `%r12` is the
   same three bytes behind `REX.B` (`41 8b 44 24 08`), so the base stays
   a form property; the register window still splits
   (`44 8b 44 24 08`, `41 8b 44 24 08`, `45 8b 44 24 08`) with the
   displacement at `[32,8]`. `0.39.0` appends eight rows; a missing `disp`
   is `E-OPERAND-002`, `128` is `E-RANGE-001`, the field ends are
   `E-OPERAND-004`, the `REX.R` floor is `E-RANGE-004`.
   `X86-P43-gpr32-mov-mem-sib-disp8` matches `llvm-mc` (76 bytes, sixteen
   instructions, no record), and
   `N01cf`/`N01cg`/`N02bi`/`N03t`/`N14ar`/`N14as`/`N16bf` pin both version
   boundaries, the missing displacement, the range end, both field ends
   and the `REX.R` floor.
   `X86-P44` completes the displacement axis for the `SIB` bases
   (`ADR-0067`): `movl 200(%rsp), %eax` is `8b 84 24 c8 00 00 00` and
   `movl %eax, 200(%rsp)` is `89 84 24 c8 00 00 00` — seven bytes,
   `mod = 10`, `SIB = 24` and a signed 32-bit displacement at `[24,32]`
   (`-2147483648…2147483647`). `%r12` is the same three bytes behind
   `REX.B` (`41 8b 84 24 c8 00 00 00`), so the base stays a form property;
   the register window still splits (`44 8b 84 24 c8 00 00 00`,
   `41 8b 84 24 c8 00 00 00`, `45 8b 84 24 c8 00 00 00`) with the
   displacement at `[32,32]`. `0.40.0` appends eight rows; a missing `disp`
   is `E-OPERAND-002`, `2147483648` is `E-RANGE-001`, the field ends are
   `E-OPERAND-004`, the `REX.R` floor is `E-RANGE-004`.
   `X86-P44-gpr32-mov-mem-sib-disp32` matches `llvm-mc` (124 bytes, sixteen
   instructions, no record), and
   `N01ch`/`N01ci`/`N02bj`/`N03u`/`N14at`/`N14au`/`N16bg` pin both version
   boundaries, the missing displacement, the range end, both field ends
   and the `REX.R` floor.
   `X86-P45` gives the 16-bit `mov` family its `mod = 00` rows
   (`ADR-0068`): `movw (%rax), %ax` is `66 8b 00` (three bytes, base slot
   `[16,3]`, no displacement) and `movw %ax, (%rax)` is `66 89 00`. A
   `REX.B` base costs a byte (`66 41 8b 00`) and moves the register field
   to `[27,3]` and the base to `[24,3]`; `%rsp`/`%r12` are `66 8b 04 24`
   and `66 41 8b 04 24`. `0.41.0` appends eight rows; a supplied `disp` is
   `E-OPERAND-002`, `%rsp`/`%r12` on a plain row and a low base on the
   `-ext` row are `E-RANGE-004`, and `%rbp`/`%r13` are `E-RANGE-004`.
   `X86-P45-gpr16-mov-mem-nodisp` matches `llvm-mc` (46 bytes, twelve
   instructions, no record), and
   `N01cj`/`N01ck`/`N02bk`/`N16bh`/`N16bi`/`N16bj`/`N16bk`/`N16bl` pin both
   version boundaries, the supplied displacement, the `%rsp`/`%r12` bases,
   the low-base floor and the `%rbp`/`%r13` exclusion.
   `X86-P46` takes the `REX.R` register window on those rows (`ADR-0069`):
   `movw (%rax), %r8w` is `66 44 8b 00` (four bytes, `REX = 44`, register at
   `[10,1]` + `[27,3]`) and `movw (%r8), %r8w` is `66 45 8b 00`, one byte
   carrying both `R` and `B`. `0.42.0` appends eight rows; a low register is
   `E-RANGE-004`, `16` is `E-OPERAND-004`, a supplied `disp` is
   `E-OPERAND-002`, and `%rsp`/`%rbp` on the new base rows are
   `E-RANGE-004`. `X86-P46-gpr16-mov-mem-nodisp-rex-r` matches `llvm-mc`
   (62 bytes, fourteen instructions, no record), and
   `N01cl`/`N01cm`/`N02bl`/`N14av`/`N16bm`/`N16bn`/`N16bo` pin both version
   boundaries, the supplied displacement, the register-window end and floor,
   and the two base exclusions.
   `X86-P47` carries that register window onto the `disp8` rows
   (`ADR-0070`): `movw 8(%rax), %r8w` is `66 44 8b 40 08` (five bytes,
   displacement at `[32,8]`) and `movw 8(%r8), %r8w` is `66 45 8b 40 08`, one
   byte carrying both extension bits; the `SIB` rows move the displacement to
   `[40,8]` (`66 44 8b 44 24 08`, `66 45 8b 44 24 08`). At `mod = 01`
   `%rbp`/`%r13` are legal bases (`66 44 8b 45 08`), so the plain row excludes
   `%rsp` only and the `-ext` row excludes `0`–`7` and `%r12`. `0.43.0`
   appends eight rows; a missing `disp` is `E-OPERAND-002`, `128` is
   `E-RANGE-001`, a low register is `E-RANGE-004`, `16` is
   `E-OPERAND-004`, and the two base cases are `E-RANGE-004`.
   `X86-P47-gpr16-mov-mem-disp8-rex-r` matches `llvm-mc` (76 bytes, fourteen
   instructions, no record), and
   `N01cn`/`N01co`/`N02bm`/`N03v`/`N14aw`/`N16bp`/`N16bq`/`N16br` pin both
   version boundaries, the missing displacement, its range end, the
   register-window end and floor, and the two base exclusions.
   `X86-P48` carries that window onto the `disp32` rows (`ADR-0071`):
   `movw 200(%rax), %r8w` is `66 44 8b 80 c8 00 00 00` (eight bytes,
   displacement at `[32,32]`) and `movw 200(%r8), %r8w` is
   `66 45 8b 80 c8 00 00 00`, one byte carrying both extension bits; the `SIB`
   rows move the displacement to `[40,32]` (`66 44 8b 84 24 c8 00 00 00`,
   `66 45 8b 84 24 c8 00 00 00`). At `mod = 10` `%rbp`/`%r13` are legal bases
   (`66 44 8b 85 c8 00 00 00`), so the plain row excludes `%rsp` only and the
   `-ext` row excludes `0`–`7` and `%r12`. `0.44.0` appends eight rows; a missing
   `disp` is `E-OPERAND-002`, `2147483648` is `E-RANGE-001`, a low register is
   `E-RANGE-004`, `16` is `E-OPERAND-004`, and the two base cases are
   `E-RANGE-004`. `X86-P48-gpr16-mov-mem-disp32-rex-r` matches `llvm-mc`
   (118 bytes, fourteen instructions, no record), and
   `N01cp`/`N01cq`/`N02bn`/`N03w`/`N14ax`/`N16bs`/`N16bt`/`N16bu` pin both
   version boundaries, the missing displacement, its range end, the
   register-window end and floor, and the two base exclusions.
   `X86-P49` adds the `SIB` index and scale to those rows (`ADR-0072`):
   `movw 8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08` (six bytes, `REX = 44`,
   `SIB = 08`, `disp8` at `[40,8]`) and `movw 8(%r15,%r13,8), %r15w` is
   `66 47 8b 7c ef 08`, with `R`, `X` and `B` in one byte. The base is one
   four-bit slot (`REX.B` + `SIB.base`), the index one four-bit slot (`REX.X`
   + `SIB.index`, `4` excluded), and the scale two bits of content (`4` is
   `E-RANGE-001`). The `disp32` rows put four bytes at `[40,32]`
   (`66 44 8b 84 08 c8 00 00 00`). `0.45.0` appends four rows; a missing index
   is `E-OPERAND-002`, scale `4` is `E-RANGE-001`, a low register and index
   `4` are `E-RANGE-004`, and `16`/base `16` are `E-OPERAND-004`.
   `X86-P49-gpr16-mov-index-rex-rx` matches `llvm-mc` (90 bytes, twelve
   instructions, no record), and
   `N01cr`/`N01cs`/`N02bo`/`N03x`/`N14ay`/`N14az`/`N16bv`/`N16bw` pin both
   version boundaries, the missing index, the scale end, the register and
   base ends, the low-register floor and the index exclusion.
   `X86-P50` takes the `REX` byte out of that shape (`ADR-0073`):
   `movw 8(%rax,%rcx,1), %ax` is `66 8b 44 08 08` (five bytes, `ModRM = 44`,
   `SIB = 08`, `disp8` at `[32,8]`) and `movw 8(%rdi,%rsi,4), %di` is
   `66 8b 7c b7 08`; `%rsp`/`%rbp` are legal bases (`66 8b 44 0c 08` /
   `66 8b 44 0d 08`), while register `8` and base `8` are `E-OPERAND-004`.
   The `disp32` rows put four bytes at `[32,32]`
   (`66 8b 84 08 c8 00 00 00`). `0.46.0` appends four rows; a missing index is
   `E-OPERAND-002`, scale `4` is `E-RANGE-001`, index `4` is `E-RANGE-004`,
   and register/base `8` and register `16` are `E-OPERAND-004`.
   `X86-P50-gpr16-mov-index-low` matches `llvm-mc` (78 bytes, twelve
   instructions, no record), and
   `N01ct`/`N01cu`/`N02bp`/`N03y`/`N14ba`/`N14bb`/`N14bc`/`N16bx` pin both
   version boundaries, the missing index, the scale end, the register and
   base field ends and the index exclusion.
   `X86-P51` keeps the register low and gives the base or the index its fourth
   bit (`ADR-0074`): `movw 8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08` (six
   bytes, `REX.B = 1`, `SIB = 08`, `disp8` at `[40,8]`) and
   `movw 8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08` (`REX.X = 1`). The
   register stays at `[27,3]`, the base and index at `[32,3]`/`[35,3]`, and
   the extended operand's slot excludes the low window. `0.47.0` appends
   eight rows; a missing index is `E-OPERAND-002`, scale `4` is
   `E-RANGE-001`, register `8`/the other operand `8` are `E-OPERAND-004`,
   and a low base or index on an `-ext` row is `E-RANGE-004`.
   `X86-P51-gpr16-mov-index-ext-window` matches `llvm-mc` (90 bytes, twelve
   instructions, no record), and
   `N01cv`/`N01cw`/`N02bq`/`N03z`/`N14bd`/`N14be`/`N16by`/`N16bz` pin both
   version boundaries, the missing index, the scale end, the register floor,
   the non-extended operand's field end and both window floors.
   `X86-P52` extends both memory operands at once (`ADR-0075`):
   `movw 8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08` (six bytes, `REX = 43`,
   `SIB = 08`, `disp8` at `[40,8]`) and `movw 8(%r15,%r15,8), %di` is
   `66 43 8b 7c ff 08`. The register stays at `[27,3]`; base and index are
   four-bit slots (`[8,1]`+`[32,3]`, `[9,1]`+`[35,3]`) that exclude `0`–`7`,
   so `%r12` is legal on both (`66 43 8b 44 24 08`). `0.48.0` appends four
   rows; a missing index is `E-OPERAND-002`, scale `4` is `E-RANGE-001`,
   register `8` is `E-OPERAND-004`, and a low base or index is
   `E-RANGE-004`.
   `X86-P52-gpr16-mov-index-rex-bx-window` matches `llvm-mc` (90 bytes, twelve
   instructions, no record), and
   `N01cx`/`N01cy`/`N02br`/`N03za`/`N14bf`/`N16ca`/`N16cb` pin both version
   boundaries, the missing index, the scale end, the register floor and both
   window floors.
   `X86-P53` carries the index/scale shape into the 32-bit family, where there
   is no prefix byte at all (`ADR-0076`): `movl 8(%rax,%rcx,1), %eax` is
   `8b 44 08 08` (four bytes, `ModRM` at byte 1, `SIB = 08`, `disp8` at
   `[24,8]`) and `movl 8(%rdi,%rsi,4), %edi` is `8b 7c b7 08`. The register,
   base and index are three bits (`[11,3]`/`[16,3]`/`[19,3]`) and the scale is
   `[22,2]`; register `8` and base `8` are `E-OPERAND-004`, index `4` is
   `E-RANGE-004`, and `%rsp`/`%rbp` stay legal bases. `0.49.0` appends four
   rows.
   `X86-P53-gpr32-mov-index-low` matches `llvm-mc` (63 bytes, twelve
   instructions, no record), and
   `N01cz`/`N01da`/`N02bs`/`N03zb`/`N14bg`/`N14bh`/`N16cc` pin both version
   boundaries, the missing index, the scale end, both three-bit field ends and
   the index exclusion.
   `X86-P54` gives those 32-bit indexed rows their single `REX` windows
   (`ADR-0077`): `movl 8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08` (`REX.R`,
   five bytes), `movl 8(%r8,%rcx,1), %eax` is `41 8b 44 08 08` (`REX.B`) and
   `movl 8(%rax,%r9,1), %eax` is `42 8b 44 08 08` (`REX.X`). The prefix pushes
   `ModRM` to byte 2, so the register is `[19,3]`, the base `[24,3]`, the index
   `[27,3]`, the scale `[30,2]` and the displacement `[32,8]`/`[32,32]`. Each
   extended slot lists its fixed bit as the most significant placement and
   excludes `0`–`7` (`E-RANGE-004`); the operands the row keeps low stay
   three-bit (`E-OPERAND-004`). `0.50.0` appends twelve rows.
   `X86-P54-gpr32-mov-index-rex-windows` matches `llvm-mc` (93 bytes, fifteen
   instructions, no record), and
   `N01db`/`N01dc`/`N02bt`/`N03zc`/`N14bi`/`N14bj`/`N16cd`/`N16ce`/`N16cf` pin
   both version boundaries, the missing index, the scale end, the low operands
   on the `B`/`X` rows and the three window floors.
   `X86-P55` completes the window split on those rows with `REX.BX`
   (`ADR-0078`): `movl 8(%r8,%r9,1), %eax` is `43 8b 44 08 08` (five bytes,
   `REX = 43`, `ModRM` at byte 2, `SIB = 08`, `disp8` at `[32,8]`) and
   `movl 8(%r15,%r15,8), %edi` is `43 8b 7c ff 08`. Both memory slots list
   their `REX` bit as the most significant placement and exclude `0`–`7`
   (`E-RANGE-004`), while the register stays three bits and `8` is
   `E-OPERAND-004`. `%r12` is legal on both memory operands
   (`43 8b 44 24 08`). `0.51.0` appends four rows.
   `X86-P55-gpr32-mov-index-rex-bx-window` matches `llvm-mc` (56 bytes, ten
   instructions, no record), and
   `N01dd`/`N01de`/`N02bu`/`N03zd`/`N14bk`/`N16cg`/`N16ch` pin both version
   boundaries, the missing index, the scale end, the register field end and
   both memory window floors.
   `X86-P56` closes the split on those rows with `REX.RBX` (`ADR-0079`):
   `movl 8(%r8,%r9,1), %r8d` is `47 8b 44 08 08` (five bytes, `REX = 47`,
   `ModRM` at byte 2, `SIB = 08`, `disp8` at `[32,8]`) and
   `movl 8(%r15,%r15,8), %r15d` is `47 8b 7c ff 08`. All three register slots
   list their `REX` bit as the most significant placement and exclude `0`–`7`
   (`E-RANGE-004`), and `%r12` is legal on all three operands. `0.52.0`
   appends four rows. `X86-P56-gpr32-mov-index-rex-rbx-window` matches
   `llvm-mc` (56 bytes, ten instructions, no record), and
   `N01df`/`N01dg`/`N02bv`/`N03ze`/`N16ci`/`N16cj`/`N16ck` pin both version
   boundaries, the missing index, the scale end and the three register slots'
   floors.
   `X86-P57` puts the `0x67` address-size prefix in front of those rows with
   `EC-08` frozen as a form (`ADR-0080`): `67` is template byte 0, so the
   opcode moves to byte 1 and `ModRM` stays at byte 2.
   `movl 8(%eax,%ecx,1), %eax` is `67 8b 44 08 08` (five bytes,
   `SIB = 08`, `disp8` at `[32,8]`) and `movl 8(%edi,%esi,4), %edi` is
   `67 8b 7c b7 08`. The base and index are 32-bit address registers
   (`x86.gpr32`/`rm32` at `[24,3]`, `x86.gpr32`/`sib_index32` at `[27,3]`,
   index `4` excluded), while the value register stays `x86.gpr32`/`r32` at
   `[19,3]`. `0.53.0` appends four rows.
   `X86-P57-gpr32-mov-index-addr32-window` matches `llvm-mc` (56 bytes, ten
   instructions, no record), and
   `N01dh`/`N01di`/`N02bw`/`N02bx`/`N03zf`/`N14bl`/`N14bm`/`N16cl` pin both
   version boundaries, the missing index, the 64-bit base, the scale end, the
   two three-bit field ends and the index `4` exclusion.
   `X86-P58` adds the three single-`REX` windows behind `0x67` (`ADR-0081`):
   `0x67` stays byte 0 and `REX` becomes byte 1, so the opcode moves to byte 2,
   `ModRM = 44` to byte 3 and `SIB = 08` to byte 4.
   `movl 8(%eax,%ecx,1), %r8d` is `67 44 8b 44 08 08` (six bytes, `REX.R`),
   `movl 8(%r8d,%ecx,1), %eax` is `67 41 8b 44 08 08` (`REX.B`) and
   `movl 8(%eax,%r9d,1), %eax` is `67 42 8b 44 08 08` (`REX.X`). Each extended
   slot is four bits and excludes `0`–`7`, while the operands a row keeps low
   stay three bits; the scale is `[38,2]` and the displacement
   `[40,8]`/`[40,32]`. `%r12d` is legal as base and index
   (`67 41 8b 44 0c 08`, `67 42 8b 44 20 08`), `%esp` as an index stays
   rejected, and `%ebp` is a legal base (`67 44 8b 44 0d 08`). `0.54.0`
   appends twelve rows.
   `X86-P58-gpr32-mov-index-addr32-rex-windows` matches `llvm-mc` (114 bytes,
   sixteen instructions, no record), and
   `N01dj`/`N01dk`/`N02by`/`N03zg`/`N16cm`/`N16cn`/`N16co`/`N14bn`/`N14bo` pin
   both version boundaries, the missing index, the scale end, the three
   extended windows' floors and the two three-bit field ends.
   `X86-P59` adds the four two-fixed-bit windows behind `0x67` (`ADR-0082`).
   The geometry is unchanged: `0x67` byte 0, `REX` byte 1, opcode byte 2,
   `ModRM` byte 3 and `SIB` byte 4, with the register at `[27,3]`, the base at
   `[32,3]`, the index at `[35,3]`, the scale at `[38,2]` and the displacement
   at `[40,8]`/`[40,32]`. `movl 8(%r8d,%r9d,1), %eax` is `67 43 8b 44 08 08`
   (`REX.BX`), `movl 8(%r8d,%ecx,1), %r8d` is `67 45 8b 44 08 08` (`REX.RB`),
   `movl 8(%eax,%r9d,1), %r8d` is `67 46 8b 44 08 08` (`REX.RX`) and
   `movl 8(%r8d,%r9d,1), %r8d` is `67 47 8b 44 08 08` (`REX.RBX`). Each
   extended slot excludes `0`–`7` while a low slot stays three bits; `%r12d`
   on all three operands is `67 47 8b 64 24 08`, `%r13d` is
   `67 47 8b 6c 2d 08`, the x8 scale with `%r15d` is `67 47 8b 7c c8 08`, and
   `%esp` as an index stays rejected. `0.55.0` appends sixteen rows.
   `X86-P59-gpr32-mov-index-addr32-rex-two-bit-windows` matches `llvm-mc`
   (144 bytes, twenty instructions, no record), and
   `N01dl`/`N01dm`/`N02bz`/`N03zh`/`N16cp`/`N16cq`/`N16cr`/`N14bp`/`N14bq` pin
   both version boundaries, the missing index, the scale end, the three
   extended windows' floors and the two three-bit field ends.
   `X86-P60` adds the `0x67` `REX.W` `movq` rows (`ADR-0083`). `REX.W` is
   template content while `R`/`X`/`B` come from the operands, so one wide row
   per direction and displacement width suffices: `movq 8(%eax,%ecx,1), %rax`
   is `67 48 8b 44 08 08` and `67 48` widens to `67 4f` (`REX.RBX`), `67 49`
   (`REX.B`), `67 4a` (`REX.X`) or `67 4c` (`REX.R`) without a new row. The
   geometry is unchanged (`0x67` byte 0, `REX` byte 1, opcode byte 2, `ModRM`
   byte 3, `SIB` byte 4; value `[10,1]`+`[27,3]`, base `[8,1]`+`[32,3]`, index
   `[9,1]`+`[35,3]`, scale `[38,2]`, displacement `[40,8]`/`[40,32]`), and the
   address registers stay 32-bit under `0x67` (`%r12d` works as base and index,
   `%ebp` as a base, a 64-bit base is rejected). `0.56.0` appends four rows.
   `X86-P60-gpr64-mov-index-addr32-rex-w` matches `llvm-mc` (78 bytes, twelve
   instructions, no record), and
   `N01dn`/`N01do`/`N02ca`/`N02cb`/`N03zi`/`N16cs`/`N14br`/`N14bs` pin both
   version boundaries, the missing index, the 64-bit base, the scale end, the
   `%esp` index slot and the two four-bit field ends.
   `X86-P61` adds the `0x67 66` 16-bit value pair (`ADR-0084`). `0x67` stays
   byte 0 and `0x66` takes byte 1, so the opcode is byte 2, `ModRM` byte 3 and
   `SIB` byte 4, with the value at `[27,3]`, the base at `[32,3]`, the index at
   `[35,3]`, the scale at `[38,2]` and the displacement at
   `[40,8]`/`[40,32]`. The bare pair has no `REX` byte, so the value, base and
   index are three bits each: `movw 8(%eax,%ecx,1), %ax` is
   `67 66 8b 44 08 08`, `%ebp` works as a base and as an index
   (`67 66 8b 44 0d 08`/`67 66 8b 44 28 08`), the x8 scale is
   `67 66 8b 44 c8 08`, and `%esp` is a base but not an index. `0.57.0`
   appends four rows. `X86-P61-gpr16-mov-index-addr32-prefix-pair` matches
   `llvm-mc` (54 bytes, eight instructions, no record), and
   `N01dp`/`N01dq`/`N02cc`/`N02cd`/`N03zj`/`N16ct`/`N14bt`/`N14bu` pin both
   version boundaries, the missing index, the 64-bit base, the scale end, the
   `%esp` index slot and the two three-bit field ends.
   `X86-P62` adds the three single-`REX` windows on the `0x67 66` pair
   (`ADR-0085`). The `REX` byte sits at position 2, so `0x67` stays byte 0,
   `0x66` byte 1, the opcode moves to byte 3, `ModRM` to byte 4 and `SIB` to
   byte 5; the slots move to `[35,3]`/`[40,3]`/`[43,3]`/`[46,2]` with the
   displacement at `[48,8]`/`[48,32]`. One fixed bit opens one window: `R` at
   `[18,1]` widens the value (`movw 8(%eax,%ecx,1), %r8w` is
   `67 66 44 8b 44 08 08`), `B` at `[16,1]` the base
   (`67 66 41 8b 44 08 08`) and `X` at `[17,1]` the index
   (`67 66 42 8b 44 08 08`), while the address registers stay 32-bit.
   `0.58.0` appends twelve rows. `X86-P62-gpr16-mov-index-addr32-rex-windows`
   matches `llvm-mc` (130 bytes, sixteen instructions, no record), and
   `N01dr`/`N01ds`/`N02ce`/`N16cu`/`N16cv`/`N16cw`/`N03zk`/`N14bv` pin both
   version boundaries, the missing index, the three window floors, the scale
   end and the four-bit field end.
   `X86-P63` adds the four two-`REX`-bit windows on the `0x67 66` pair
   (`ADR-0086`). The `REX` byte keeps position 2, so the geometry is the
   `0.58.0` geometry (`[35,3]`/`[40,3]`/`[43,3]`/`[46,2]`, displacement
   `[48,8]`/`[48,32]`). `RB` (`0x45`) widens the value and the base
   (`movw 8(%r8d,%ecx,1), %r8w` is `67 66 45 8b 44 08 08`), `RX` (`0x46`)
   the value and the index, `BX` (`0x43`) the base and the index and `RBX`
   (`0x47`) all three; the address registers stay 32-bit. `0.59.0` appends
   sixteen rows. `X86-P63-gpr16-mov-index-addr32-rex-two-bit-windows` matches
   `llvm-mc` (164 bytes, twenty instructions, no record), and
   `N01dt`/`N01du`/`N02cf`/`N16cx`/`N16cy`/`N16cz`/`N03zl`/`N14bw` pin both
   version boundaries, the missing index, the three extended-window floors,
   the scale end and the four-bit field end.
   `X86-P64` adds the no-base indexed shape on the `0x67 66` pair
   (`ADR-0087`). `mod = 00` with `SIB.base = 101` means no base and forces
   a `disp32`, so `movw 8(,%ecx,1), %ax` is `67 66 8b 04 0d 08 00 00 00`
   and the row has no `base` role. There is no `REX.B` bit: `R` at
   `[18,1]` and `X` at `[17,1]` insert the `REX` byte at position 2 and
   move every later field eight bits (`movw 8(,%r9d,1), %r8w` is
   `67 66 46 8b 04 0d 08 00 00 00`). `0.60.0` appends eight rows.
   `X86-P64-gpr16-mov-index-addr32-no-base` matches `llvm-mc` (125 bytes,
   thirteen instructions, no record), and
   `N01dv`/`N01dw`/`N02cg`/`N02ch`/`N03zm`/`N14bx`/`N16da`/`N16db` pin
   both version boundaries, the missing index, the supplied base, the
   scale end, the four-bit field end and both index windows.
   `X86-P65` extends that shape to the 32-bit value width (`ADR-0088`):
   the `0x66` disappears, so `movl 8(,%ecx,1), %eax` is
   `67 8b 04 0d 08 00 00 00` (eight bytes) and the `REX` byte sits at
   byte 1 (`movl 8(,%r9d,1), %r8d` is `67 46 8b 04 0d 08 00 00 00`).
   `0.61.0` appends eight rows.
   `X86-P65-gpr32-mov-index-addr32-no-base` matches `llvm-mc` (112 bytes,
   thirteen instructions, no record), and
   `N01dx`/`N01dy`/`N02ci`/`N02cj`/`N03zn`/`N14by`/`N16dc`/`N16dd` pin
   both version boundaries, the missing index, the supplied base, the
   scale end, the four-bit field end and both index windows.
   `X86-P66` reaches the 64-bit value width (`ADR-0089`), where `REX.W` is
   mandatory: `movq 8(,%ecx,1), %rax` is `67 48 8b 04 0d 08 00 00 00`
   (nine bytes) and `R`/`X` are free bits of the `REX` byte, so one row
   per direction covers all sixteen registers and indexes. `0.62.0`
   appends two rows.
   `X86-P66-gpr64-mov-index-addr32-no-base` matches `llvm-mc` (117 bytes,
   thirteen instructions, no record), and
   `N01dz`/`N01ea`/`N02ck`/`N02cl`/`N03zo`/`N14bz`/`N14ca`/`N16de` pin
   both version boundaries, the missing index, the supplied base, the
   scale end, both four-bit field ends and the index constant.
   `X86-P67` takes the absolute `SIB = 25` shape behind `0x67`
   (`ADR-0090`): `addr32 movl 4660, %eax` is
   `67 8b 04 25 34 12 00 00` (eight bytes) with no address register at
   all, because `SIB = 25` is the `scale = 00`/`index = 100`/`base = 101`
   constant. The `REX.R` rows are nine bytes (`67 44 8b 04 25 …`), so
   `0.63.0` appends four rows.
   `X86-P67-gpr32-mov-addr32-abs32` matches `llvm-mc` (84 bytes, ten
   instructions, no record), and
   `N01eb`/`N01ec`/`N02cm`/`N03zp`/`N14cb`/`N14cc`/`N16df` pin both
   version boundaries, the supplied base, the signed displacement end,
   both value-field ends and the extended window floor.
   `X86-P68` reaches the 64-bit width of the same shape (`ADR-0091`),
   where `REX.W` is mandatory: `addr32 movq 4660, %rax` is
   `67 48 8b 04 25 34 12 00 00` (nine bytes), and `R`/`ModRM.reg` cover
   all sixteen values in one row per direction, so `0.64.0` appends two
   rows.
   `X86-P68-gpr64-mov-addr32-abs32` matches `llvm-mc` (90 bytes, ten
   instructions, no record), and
   `N01ed`/`N01ee`/`N02cn`/`N02co`/`N02cp`/`N03zq`/`N14cd` pin both
   version boundaries, the supplied base, the missing displacement, a
   32-bit operand, the signed displacement end and the four-bit value
   end.
   `X86-P69` takes the `0x67 66` absolute shape (`ADR-0092`):
   `addr32 movw 4660, %ax` is `67 66 8b 04 25 34 12 00 00` (nine
   bytes) and the `REX.R` rows are ten (`67 66 44 8b 04 25 …`), so
   `0.65.0` appends four rows.
   `X86-P69-gpr16-mov-addr32-abs32` matches `llvm-mc` (94 bytes, ten
   instructions, no record), and
   `N01ef`/`N01eg`/`N02cq`/`N02cr`/`N02cs`/`N03zr`/`N14ce`/`N14cf`/`N16dg`
   pin both version boundaries, the supplied base, the missing
   displacement, a 32-bit operand, the signed displacement end, both
   value-field ends and the extended window floor.
   `X86-P70` puts a symbol in an absolute 32-bit content field instead of a
   literal (`ADR-0093`): the operand keeps `payload: {}` and one fixup
   carries `pc_reference_rule = none`, `identity`, the addend and a signed
   32-bit range, so `movl ext, %eax` is `8b 04 25 00 00 00 00` with the
   reference in an `R_X86_64_32S`-style record and no length change. The
   slice needs no definition change; `0.65.0` stays canonical.
   `X86-P70-abs32-symbol` matches `llvm-mc` (71 bytes, nine instructions,
   nine records at `0x3`/`0xA`/`0x12`/`0x1A`/`0x23`/`0x2A`/`0x31`/`0x3C`/
   `0x43`), and `X86-P70-abs32-symbol-resolved` matches `ld.lld` (37
   bytes, five instructions, no record: `.text` at `0x1000`, `L1` at
   offset 30, values `0x101e`/`0x1022`/`0x101e`/`0x1020`/`0x101e`).
   `N15b`/`N15c`/`N07c`/`N07d`/`N07e`/`N08d`/`N04f` pin the symbol
   payload on a non-`target` role, the empty payload with no fixup, the
   double writer, both wrong windows, `resolve_in_place` without a bound
   section and an absolute address past an 8-bit field.
4. Contract debt is closed: `OD-05` (unknown fields/extensions) by ADR-0031,
   pinned by `N21a`/`N21b` and the definition unit test, and `OD-08` (canonical
   wire form) by ADR-0032, pinned by `EXP-R4`. The Level 1 artifact envelope
   stays deferred by `OD-03` and is not needed by the Level 0 gate.
5. Keep `python tools/check_ids.py`, `python tools/check_definition.py` and
   `python tools/check_rv64_source.py` green after every change, and keep
   `cargo test --workspace` green: it is the fixture gate, not a smoke test.

Phase 3 output so far: the Rust workspace under `prototype/` (`fmp-model` for the
strict JSON reader and the plan/definition binders, `fmp-validate` for contract
§13 steps 2–7, `fmp-materialize` for encoding and the two fixup modes,
`fmp-cli` with exit codes 0/1/2); the frozen tables
`definitions/x86_64/0.1.0.json` (seven forms, digest `sha256:c6bfa9…`),
`0.2.0.json` (nine forms, digest `sha256:d9c088ca…`, the two RIP-relative
rows), `0.3.0.json` (seventeen forms, digest `sha256:02500bf7…`, the eight
base+displacement rows), `0.4.0.json` (twenty-two forms, digest
`sha256:ee2141cb…`, the five prefix rows), `0.5.0.json` (twenty-five forms,
digest `sha256:24256f0c…`, the three encoding-family rows), `0.6.0.json`
(twenty-five forms, digest `sha256:79952b5d…`, the six 64-bit register-direct
rows widened from 3-bit to 4-bit register fields), `0.7.0.json` (twenty-nine
forms, digest `sha256:8c40c948…`, the twelve base+disp rows widened to a 4-bit
base and the four fixed-base `%r12` rows), `0.8.0.json` (thirty-three forms,
digest `sha256:e55f694a…`, the four `SIB` index/scale rows), `0.9.0.json`
(forty-five forms, digest `sha256:cc538253…`, the twelve SSE memory rows),
`0.10.0.json` (fifty-three forms, digest `sha256:0c10ff1c…`, the four widened
EVEX base slots and the eight `-base-ext` rows), `0.11.0.json` (sixty-two
forms, digest `sha256:d9669be6…`, the three legacy register windows, two VEX
register windows and four legacy memory rows, with the VEX/EVEX `xmm` slots
widened in place) and `0.12.0.json` (seventy-four forms, digest
`sha256:a74ae09e…`, the twelve no-displacement rows) and `0.13.0.json`
(seventy-four forms, digest `sha256:79eabc2d…`, the seven EVEX `xmm` slots
widened to five bits in place) and `0.14.0.json` (seventy-nine forms, digest
`sha256:3126af72…`, the five register-direct `ymm`/`zmm` rows) and
`0.15.0.json` (ninety-one forms, digest `sha256:305e9604…`, the twelve EVEX
memory rows at `ymm`/`zmm` with `EC-39`'s unit as a form fact) and
`0.16.0.json` (one hundred and three forms, digest `sha256:64ea1acf…`, the
twelve VEX.256 memory rows with no new `EC` fact) and `0.17.0.json` (one hundred
and nineteen forms, digest `sha256:eb837025…`, the sixteen 8/16-bit `mov`
memory rows, again with no new `EC` fact) and `0.18.0.json` (one hundred and
twenty-seven forms, digest `sha256:e1281b0c…`, the eight `-base-ext` rows and
the four widened `40` byte rows, again with no new `EC` fact) and `0.19.0.json`
(one hundred and fifty-five forms, digest `sha256:dddc678f…`, the twenty-eight
fixed-base `SIB` rows, again with no new `EC` fact) and `0.20.0.json` (one
hundred and seventy-one forms, digest `sha256:b8bd1ed3…`, the sixteen SSE
fixed-base `SIB` rows, again with no new `EC` fact) and `0.21.0.json` (one
hundred and ninety-five forms, digest `sha256:30af3fec…`, the twenty-four
EVEX fixed-base `SIB` rows, again with no new `EC` fact) and `0.22.0.json` (two
hundred and seven forms, digest `sha256:61c7cd1c…`, the twelve EVEX
no-displacement fixed-base `SIB` rows, again with no new `EC` fact) and
`0.23.0.json` (two hundred and twenty-five forms, digest `sha256:507e55c8…`, the
eighteen EVEX `SIB` index/scale rows, again with no new `EC` fact) and
`0.24.0.json` (two hundred and thirty-one forms, digest `sha256:2521f2dc…`, the
six no-base EVEX `SIB` index rows, again with no new `EC` fact) and
`0.25.0.json` (two hundred and thirty-seven forms, digest `sha256:b72c0b08…`,
the six absolute `SIB` rows, again with no new `EC` fact) and
`0.26.0.json` (two hundred and thirty-nine forms, digest `sha256:e253e050…`, the
two 64-bit GPR `mov` absolute rows, which freeze `EC-05`) and
`0.27.0.json` (two hundred and forty-three forms, digest `sha256:c51a0a6b…`, the
four 32-bit GPR `mov` absolute rows, the two register windows, again with no new
`EC` fact) and
`0.28.0.json` (two hundred and forty-seven forms, digest `sha256:1c1e6623…`, the
four 16-bit GPR `mov` absolute rows behind the `66` prefix, again with no new
`EC` fact) and
`0.29.0.json` (two hundred and fifty-five forms, digest `sha256:cf78fac0…`, the
eight 8-bit GPR `mov` absolute rows in four register windows, again with no
new `EC` fact) and
`0.30.0.json` (two hundred and sixty-seven forms, digest `sha256:5dae4541…`, the
twelve extended-byte-register memory rows, again with no new `EC` fact)
and
`0.31.0.json` (two hundred and seventy-five forms, digest `sha256:cc01b72c…`, the
eight no-displacement byte `mov` rows, which revise `EC-02` in place) and
`0.32.0.json` (two hundred and eighty-nine forms, digest `sha256:bad81d66…`, the
fourteen `%rsp`/`%r12` `SIB` rows at `mod = 00`, which revise `EC-35` and
`EC-06` in place) and
`0.33.0.json` (two hundred and ninety-one forms, digest `sha256:b6659c62…`, the
two 64-bit no-displacement `mov` rows, which revise `EC-35` in place) and
`0.34.0.json` (two hundred and ninety-five forms, digest `sha256:03368b63…`, the
four 64-bit `%rsp`/`%r12` `SIB` rows, which revise `EC-35` in place) and
`0.35.0.json` (three hundred and one forms, digest `sha256:d4fd01ad…`, the
six 32-bit no-displacement `mov` rows in three reach windows, which revise
`EC-38` in place) and
`0.36.0.json` (three hundred and nine forms, digest `sha256:c4a61297…`, the
eight 32-bit `%rsp`/`%r12` `SIB` rows, which revise `EC-35` and `EC-38` in
place) and
`0.37.0.json` (three hundred and fifteen forms, digest `sha256:1a29805f…`,
the six 32-bit plain-base `disp8` `mov` rows, which revise `EC-02` and
`EC-38` in place) and
`0.38.0.json` (three hundred and twenty-one forms, digest `sha256:47355a15…`,
the six 32-bit plain-base `disp32` `mov` rows, which revise `EC-02` and
`EC-38` in place) and
`0.39.0.json` (three hundred and twenty-nine forms, digest `sha256:08e2fb7a…`,
the eight 32-bit `%rsp`/`%r12` `SIB` `disp8` `mov` rows, which revise `EC-02`
and `EC-35` in place) and
`0.40.0.json` (three hundred and thirty-seven forms, digest `sha256:ddeb4734…`,
the eight 32-bit `%rsp`/`%r12` `SIB` `disp32` `mov` rows, which revise `EC-02`
and `EC-35` in place) and
`0.41.0.json` (three hundred and forty-five forms, digest `sha256:a2c5fa28…`,
the eight 16-bit `mod = 00` `mov` rows, which revise `EC-35` and `EC-38` in
place) and
`0.42.0.json` (three hundred and fifty-three forms, digest `sha256:b45380cd…`,
the eight `REX.R` register-window rows, which revise `EC-06` in place) and
`0.43.0.json` (three hundred and sixty-one forms, digest `sha256:da40c854…`,
the eight `disp8` rows with the same register window, which revise `EC-02`,
`EC-06` and `EC-38` in place) and
`0.44.0.json` (three hundred and sixty-nine forms, digest `sha256:4361f534…`,
the eight `disp32` rows with the same register window, which revise `EC-02`,
`EC-06` and `EC-38` in place) and
`0.45.0.json` (three hundred and seventy-three forms, digest
`sha256:9adaf50a…`, the four indexed rows with `REX.B`/`REX.X` beside the
fixed `REX.R`, which revise `EC-02`, `EC-06`, `EC-37` and `EC-38` in place) and
`0.46.0.json` (three hundred and seventy-seven forms, digest
`sha256:44a396f3…`, the four `REX`-less indexed rows whose three-bit fields
revise `EC-02`, `EC-37` and `EC-38` in place) and
`0.47.0.json` (three hundred and eighty-five forms, digest
`sha256:08946463…`, the eight rows that give the base or the index a fourth
bit while the register stays low, revising `EC-02`, `EC-37` and `EC-38` in
place) and
`0.48.0.json` (three hundred and eighty-nine forms, digest `sha256:552b8273…`,
the four rows where both memory operands gain their fourth bit while the
register stays low, revising `EC-02`, `EC-37` and `EC-38` in place) and
`0.49.0.json` (three hundred and ninety-three forms, digest `sha256:5a7ec114…`,
the four `REX`-less 32-bit indexed rows whose three-bit register, base and index
fields revise `EC-02`, `EC-37` and `EC-38` in place) and
`0.50.0.json` (four hundred and five forms, digest `sha256:6f38e272…`, the
twelve single-`REX`-bit rows on the same 32-bit indexed shape, whose
`[2,1]`/`[0,1]`/`[1,1]` placements revise `EC-02`, `EC-06`, `EC-37` and
`EC-38` in place) and
`0.51.0.json` (four hundred and nine forms, digest `sha256:e73395df…`, the four
`REX.BX` rows whose two fixed memory bits revise `EC-02`, `EC-06`, `EC-37` and
`EC-38` in place) and
`0.52.0.json` (four hundred and thirteen forms, digest `sha256:4587b149…`, the
four `REX.RBX` rows whose three fixed register bits revise `EC-02`, `EC-06`,
`EC-37` and `EC-38` in place) and
`0.53.0.json` (four hundred and seventeen forms, digest `sha256:9c4c913f…`, the
four `0x67` address-size rows whose 32-bit base/index slots revise `EC-02`,
`EC-08`, `EC-37` and `EC-38` in place) and
`0.54.0.json` (four hundred and twenty-nine forms, digest `sha256:4513f6a9…`,
the twelve single-`REX` `0x67` rows whose fixed-bit and displacement placements
revise `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` in place) and
`0.55.0.json` (four hundred and forty-five forms, digest `sha256:e4fe0118…`,
the sixteen two-fixed-bit `0x67` rows whose second fixed bit revises the same
five `EC` rows in place) and
`0.56.0.json` (four hundred and forty-nine forms, digest `sha256:d039c972…`,
the four `0x67` `REX.W` `movq` rows whose template-fixed `W` and 32-bit address
slots revise the same five `EC` rows in place) and
`0.57.0.json` (four hundred and fifty-three forms, digest `sha256:4b41ac75…`,
the four `0x67 66` 16-bit value rows whose prefix pair revises `EC-02`,
`EC-06`, `EC-07`, `EC-08`, `EC-36`, `EC-37` and `EC-38` in place) and
`0.58.0.json` (four hundred and sixty-five forms, digest `sha256:8e7fc7e7…`,
the twelve `0x67 66` single-`REX` window rows whose fixed bit and shifted
displacement placements revise the same seven `EC` rows in place) and
`0.59.0.json` (four hundred and eighty-one forms, digest `sha256:bf7e54f5…`,
the sixteen `0x67 66` two-`REX`-bit window rows whose second fixed bit revises
the same seven `EC` rows in place) and
`0.60.0.json` (four hundred and eighty-nine forms, digest `sha256:f951de4c…`,
the eight `0x67 66` no-base indexed rows whose missing base and mandatory
`disp32` revise `EC-02`, `EC-06`, `EC-08`, `EC-37` and `EC-38` in place and
`0.61.0.json` (four hundred and ninety-seven forms, digest `sha256:e5a57fc7…`,
the eight `0x67` no-base indexed 32-bit rows whose absent `0x66` and
shifted fields revise `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and
`EC-38` in place and
`0.62.0.json` (four hundred and ninety-nine forms, digest `sha256:bbcd8062…`,
the two `0x67` no-base indexed 64-bit rows whose mandatory `REX.W` and
free `R`/`X` bits revise `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and
`EC-38` in place and
`0.63.0.json` (five hundred and three forms, digest `sha256:72c7e8f2…`,
the four `0x67` absolute `SIB = 25` rows whose constant `SIB`, shifted
`REX.R` geometry and absent address roles revise `EC-02`, `EC-06`,
`EC-07`, `EC-08`, `EC-37` and `EC-38` in place and
`0.64.0.json` (five hundred and five forms, digest `sha256:fc98a834…`,
the two `0x67` absolute `SIB = 25` 64-bit rows whose mandatory `REX.W`
and free `R` bit revise `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37` and
`EC-38` in place and
`0.65.0.json` (five hundred and nine forms, digest `sha256:9f5bc421…`,
the four `0x67 66` absolute `SIB = 25` rows whose `REX` byte at position
2 and shifted geometry revise `EC-02`, `EC-06`, `EC-07`, `EC-08`,
`EC-37` and `EC-38` in place);
`EXP-0004` (223 decoded byte strings across the seven `0.1.0` rows, plus the
`OD-06` digest measurement); `EXP-0005` (9 positive fixtures against LLVM
23.1.2, with the decode-verified caveat on five instructions); `EXP-0029` (the
RIP-relative fields,
the signed `disp32` ends and the record offset); `EXP-0030` (the base+disp
fields, the `%rsp` SIB byte and the signed `disp8`/`disp32` ends); `EXP-0031`
(the `0x66` width, the 8-bit register sets and the prefix order); `EXP-0032`
(the three encoding families, the moving `ModRM` placement and the extension
set); `EXP-0035` (the `r8`–`r15` placements, the `REX.R`/`REX.B` split and the
version boundary); `EXP-0036` (the `r8`–`r15` bases, the `%r12`/`%rsp` SIB pair
and the `E-RANGE-004` exclusion); `EXP-0037` (the `SIB` scale contents, the
`REX.X`-extended index, the `%riz` "no index" measurement and the multiplier
rejection); `EXP-0038` (the three SSE memory families, the family-dependent
base reach and the EVEX `disp8` content); `EXP-0039` (the `r8`–`r15` SSE base
windows, the `REX`/third-VEX-byte length change and the inverted `B̄`);
`EXP-0040` (the `xmm8`–`xmm15` register windows, the `REX.R`/`REX.B` and
`R̄`/`B̄` placements and the two legal VEX spellings of a high source);
`EXP-0041` (the no-displacement shape, the `disp8 = 0` twin, the `SIB` and
`r/m = 101` base exclusions and the per-family register reach); `EXP-0042` (the
five-bit EVEX register, the `R̄'`/`X̄` placements, the three falsified encodings
and the unchanged length); `EXP-0043` (the `L`/`L'L` width field, the
register-independent widening, the three VEX.256 windows and the EVEX.256/512
pair); `EXP-0044` (the `disp8*N` unit at `ymm`/`zmm`, the three widths of one
field content, the compressed extremes and `disp32` promotions, and VEX.256
memory's plain unscaled byte); `EXP-0045` (the twelve VEX.256 memory shapes, the
unchanged two base windows and four-bit vector slot, and the round-trip proof
that the VEX displacement is a plain signed byte); `EXP-0046` (the word and
byte memory rows, the `0x66`-before-`REX` order, the three disjoint byte sets
and the deferred `-base-ext`/`%rsp`/`mod = 00`/four-bit windows); `EXP-0047`
(the extended bases, the `66`-then-`REX` bit positions, the four-family split
and the register partition); `EXP-0048` (the `SIB` bases, the moving `ModRM`
and displacement, the high-byte `%r12` refusal and the unchanged register
windows); `EXP-0049` (the SSE `SIB` bases, the moving `ModRM` and displacement,
the inherited register windows and the VEX `R̄` window);
`EXP-0050` (the EVEX `SIB` bases, the unchanged vector slot, the
`disp8*N` content and the five-bit window); `EXP-0051` (the `mod = 00` `SIB`
bases, the missing displacement slot, the one-encoding zero offset and the
`%rbp`/`%r13` refusal); `EXP-0052` (the `SIB` index and scale, the `X̄` fourth
bit, the index `4` exclusion and the no-base `%rbp`/`%r13` rows); `EXP-0053` (the
no-base `SIB` shape, the constant base `101`, the mandatory `disp32` and the
deferred absolute `SIB = 25` address); `EXP-0054` (the absolute `SIB = 25`
address, both register fields as constants, the mandatory four-byte field and
the three register-based neighbours); `EXP-0055` (the same shape under the
64-bit GPR `mov` opcodes, the raw four-bit register window, the ten-byte
`moffs` second encoding and the version boundary); `EXP-0056` (the same shape
at 32-bit width, the seven-byte low window beside the eight-byte `REX`
window, the excluded low window and the version boundary); `EXP-0057` (the same shape
at 16-bit width behind the `66` prefix, the eight-byte low window beside the
nine-byte `REX` window, the 32-bit address that does not narrow, the
`movabsw` second encoding and the version boundary); `EXP-0058` (the same
shape at 8-bit width in four register windows, the seven-byte low and
high rows beside the eight-byte `REX` rows, the `REX = 40` relabelling of
`%spl`–`%dil`, the address that does not narrow, the `movabsb` second
encoding and the version boundary); `EXP-0059` (the extended byte
register, `REX.R` and `REX.B` in one prefix byte, the three base windows,
the `SIB` byte `24` shared by `%rsp` and `%r12`, the high-byte refusal,
the deferred `moffs` shape and the version boundary); `EXP-0060` (the
`mod = 00` shape at two and three bytes, the two `REX`-less and two
prefixed windows, the `r/m = 101` RIP-relative collision that keeps
`%rbp`/`%r13` on their zero-displacement rows, the `SIB` byte that keeps
`%rsp`/`%r12` out, and the version boundary); `EXP-0061` (the
`SIB = 24` rows at three and four bytes, `%rsp`/`%r12` differing only in
`REX.B`, the high-byte `%r12` refusal, the fixed base and the version
boundary); `EXP-0062` (the three-byte 64-bit rows, one row for all
sixteen registers and bases, the four excluded bases, the assembler's
normalisation of an explicit zero displacement, and the version boundary);
`EXP-0063` (the four-byte `SIB = 24` rows, `%rsp`/`%r12` differing only in
`REX.B`, the `REX.R` slot, the fixed base and the version boundary);
`EXP-0064` (the two-byte 32-bit rows, the three reach windows and their
disjoint exclusions, the `0x41`/`0x44`/`0x45` bytes, the RIP-relative and
`SIB` bases, and the version boundary);
`EXP-0065` (the three- and four-byte 32-bit `SIB` rows, the `SIB = 24`
template, `%rsp`/`%r12` differing only in `REX.B`, the register-window
split, the fixed base and the version boundary);
`EXP-0066` (the three-byte 32-bit `disp8` rows, the signed byte range, the
three reach windows, `%rbp`/`%r13` becoming legal at `mod = 01`, the
low-base exclusion on the `REX.B` row, and the version boundary);
`EXP-0067` (the six-byte 32-bit `disp32` rows, the signed 32-bit range, the
three reach windows, `%rbp`/`%r13` remaining legal at `mod = 10`, the
low-base exclusion on the `REX.B` row, and the version boundary);
`EXP-0068` (the four- and five-byte 32-bit `SIB` `disp8` rows, the signed
byte range, the three reach windows, the fixed base, the `REX.R` floor and
the version boundary);
`EXP-0069` (the seven- and eight-byte 32-bit `SIB` `disp32` rows, the signed
32-bit range, the three reach windows, the fixed base, the `REX.R` floor and
the version boundary);
`EXP-0070` (the three- to five-byte 16-bit `mod = 00` rows, the plain and
`REX.B` base windows, the `%rsp`/`%r12` fixed bases, the `%rbp`/`%r13`
exclusion and the version boundary);
`EXP-0071` (the four- and five-byte `REX.R` register window, the shared `REX`
byte, the `SIB` bases, the low-register floor, the field end and the version
boundary);
`EXP-0072` (the five- and six-byte 16-bit `disp8` rows with the `REX.R`
window, the displacement at `[32,8]`/`[40,8]`, the legal `%rbp`/`%r13` bases at
`mod = 01`, the signed byte ends and the version boundary);
`EXP-0073` (the eight- and nine-byte 16-bit `disp32` rows with the `REX.R`
window, the displacement at `[32,32]`/`[40,32]`, the legal `%rbp`/`%r13` bases
at `mod = 10`, the signed 32-bit ends and the version boundary);
`EXP-0074` (the six- and nine-byte 16-bit indexed rows, one `REX` byte carrying
`R`/`X`/`B`, the full base and index windows, the two-bit scale, the
displacement at `[40,8]`/`[40,32]`, the `%rsp` index rejection and the version
boundary);
`EXP-0075` (the five- and eight-byte `REX`-less indexed rows, `ModRM`/`SIB` one
byte earlier, the three-bit register/base/index fields, the legal
`%rsp`/`%rbp` bases, the displacement at `[32,8]`/`[32,32]`, the `%rsp` index
rejection and the version boundary);
`EXP-0076` (the six- and nine-byte indexed rows with `REX.B` or `REX.X`, the
register at `[27,3]` and `ModRM`/`SIB` back at bytes 3/4, the legal
`%r12`/`%rsp`/`%rbp` bases, `%r12` as an index, the displacement at
`[40,8]`/`[40,32]`, the `%rsp` index rejection and the version boundary);
`EXP-0077` (the six- and nine-byte rows with `REX = 43`, the register at
`[27,3]`, both memory slots at `8`–`15`, the legal `%rsp`/`%rbp` bases,
`%r12` on both operands, the displacement at `[40,8]`/`[40,32]`, the `%rsp`
index rejection and the version boundary);
`EXP-0078` (the four- and seven-byte `REX`-less 32-bit rows, `ModRM`/`SIB` at
bytes 1/2, the register, base and index at `[11,3]`/`[16,3]`/`[19,3]`, the
legal `%rsp`/`%rbp` bases, the displacement at `[24,8]`/`[24,32]`, the index
`4` exclusion, the pending `REX` windows and the version boundary);
`EXP-0079` (the five- and eight-byte single-bit rows, `REX` at byte 0,
`ModRM`/`SIB` at bytes 2/3, the register, base and index at
`[19,3]`/`[24,3]`/`[27,3]`, the scale at `[30,2]`, the displacement at
`[32,8]`/`[32,32]`, `%r12` on both memory windows, the three window floors,
the low operands on the `B`/`X` rows and the version boundary);
`EXP-0080` (the five- and eight-byte `REX.BX` rows, `REX = 43` at byte 0,
`ModRM`/`SIB` at bytes 2/3, the register at `[19,3]`, base and index as
four-bit slots, the scale at `[30,2]`, the displacement at `[32,8]`/`[32,32]`,
`%r12` on both memory operands, `%r15`/`%r15` at x8, the two memory window
floors, the deferred `REX.RBX` row and the version boundary);
`EXP-0081` (the five- and eight-byte `REX.RBX` rows, `REX = 47` at byte 0,
`ModRM`/`SIB` at bytes 2/3, all three register slots as four-bit fields, the
scale at `[30,2]`, the displacement at `[32,8]`/`[32,32]`, `%r12` on all three
operands, `%r15`/`%r15` with `%r15d` at x8, the three register floors and the
version boundary);
`EXP-0082` (the five- and eight-byte `0x67` rows, `67` at byte 0, opcode at
byte 1, `ModRM`/`SIB` at bytes 2/3, the value register at `[19,3]`, the 32-bit
base and index at `[24,3]`/`[27,3]`, the scale at `[30,2]`, the displacement at
`[32,8]`/`[32,32]`, `%esp` and `%ebp` as bases, `%ebp` as an index, the x4/x8/x2
scales, a negative displacement, the 64-bit siblings, the deferred
`0x67`+`REX` windows and the version boundary);
`EXP-0083` (the six- and nine-byte single-`REX` `0x67` rows, `67` at byte 0,
`REX.R`/`REX.B`/`REX.X` at byte 1, opcode at byte 2, `ModRM`/`SIB` at bytes 3/4,
the register at `[27,3]` with `[10,1]`, the base at `[32,3]` with `[8,1]`, the
index at `[35,3]` with `[9,1]`, the scale at `[38,2]`, the displacement at
`[40,8]`/`[40,32]`, `%r12d` on both memory operands, `%ebp` as a base, the x8
scale, the 64-bit siblings, the deferred two-bit `addr32` windows and the
version boundary);
`EXP-0084` (the six- and nine-byte two-bit `0x67` rows, `REX.BX`/`REX.RB`/
`REX.RX`/`REX.RBX` at byte 1, opcode at byte 2, `ModRM`/`SIB` at bytes 3/4,
the same slot offsets, `%r12d`/`%r13d` on all three operands, the x8 scale,
the 64-bit siblings, the `REX.WBX` sibling, `%esp` as a base and index, the
bare row and the version boundary);
`EXP-0085` (the six- and nine-byte `0x67` `REX.W` rows, `REX = 48` at byte 1
with `R`/`X`/`B` from the operands, opcode at byte 2, `ModRM`/`SIB` at bytes
3/4, the value at `[10,1]`+`[27,3]` with the base/index at `[8,1]`+`[32,3]`/
`[9,1]`+`[35,3]`, the scale at `[38,2]`, the displacement at `[40,8]`/`[40,32]`,
`%r12`/`%r13` on all three operands, `%ebp` as a base, `%r12d` as base and
index, the x8 scale, the 64-bit and 32-bit siblings, `%esp` as a base and
index, the rejected 32-bit value register and the version boundary);
`EXP-0086` (the six- and nine-byte `0x67 66` rows, the prefix order `0x67` then
`0x66`, `0x66` at byte 1, opcode at byte 2, `ModRM`/`SIB` at bytes 3/4, the
same slot offsets, `%ebp` as base and index, the x8 scale, the 64-bit and
32-bit siblings, `%esp` as a base and index, the rejected 32-bit value
register, the deferred `REX` windows and the version boundary);
`EXP-0087` (the seven- and ten-byte `0x67 66` single-`REX` rows, `REX` at
byte 2 with `R` at `[18,1]`, `B` at `[16,1]` and `X` at `[17,1]`, opcode at
byte 3, `ModRM`/`SIB` at bytes 4/5, the value/base/index at `[35,3]`/`[40,3]`/
`[43,3]`, the scale at `[46,2]`, the displacement at `[48,8]`/`[48,32]`, the
four window floors, the two-bit `%r12w`/`%r12d` sibling, the 64-bit and 32-bit
siblings, `%esp` as a base and index, the rejected 32-bit value register and
the version boundary);
`EXP-0088` (the seven- and ten-byte `0x67 66` two-`REX`-bit rows, `REX = 45`/
`46`/`43`/`47` at byte 2, opcode at byte 3, `ModRM`/`SIB` at bytes 4/5, the
value/base/index at `[35,3]`/`[40,3]`/`[43,3]`, the scale at `[46,2]`, the
displacement at `[48,8]`/`[48,32]`, the three window floors, `%r12d` as a base
and as an index, the x8 scale, the single-`REX` and 64-bit siblings, `%esp` as
a base and index, the rejected 32-bit value register and the version boundary);
`EXP-0089` (the nine- and ten-byte `0x67 66` no-base indexed rows,
`SIB.base = 101` at `mod = 00`, the mandatory four-byte displacement, the
`[40,32]`/`[48,32]` geometry split, the four `REX` windows, index `4` under
`REX.X` as `%r12d`, the x4 and x8 scales, the base+index, 32-bit, 64-bit and
absolute neighbours, `%esp` as an index and a 32-bit value register, and the
`REX.W` finding that `data16` emits a standalone `0x66` before `0x67`);
`EXP-0090` (the eight- and nine-byte `0x67` no-base indexed `movl` rows,
`SIB.base = 101` at `mod = 00`, the mandatory four-byte displacement, the
`[32,32]`/`[40,32]` geometry split, the four `REX` windows, index `4` under
`REX.X` as `%r12d`, the x4 and x8 scales, the base+index, `movw`, 64-bit and
absolute neighbours, `%esp` as an index and a 16-bit value register, and the
deferred `REX.W` `movq` sibling);
`EXP-0091` (the nine-byte `0x67` no-base indexed `movq` rows, `REX.W` at
byte 1, `SIB.base = 101` at `mod = 00`, the mandatory four-byte
displacement, one geometry with `R`/`X` as free bits (`48`/`4c`/`4a`/`4e`),
index `4` under `REX.X` as `%r12d`, the x4 and x8 scales, the base+index,
`movw` and `movl` siblings, the 64-bit-addressing and absolute neighbours,
`%esp` as an index and a 32-bit value register);
`EXP-0092` (the eight- and nine-byte `0x67` absolute `SIB = 25` rows, the
constant `SIB` byte, the `[32,32]`/`[40,32]` geometry split behind
`REX.R`, the mandatory four-byte displacement and its signed ends,
`%r15d` as the value, the absolute row without `0x67`, the 64-bit and
16-bit siblings, the indexed and base+index neighbours, the two `moffs`
forms, the `0x67` RIP-relative row and two rejected spellings);
`EXP-0093` (the nine-byte `0x67` absolute `SIB = 25` rows at the 64-bit
width, the mandatory `REX.W` byte and its free `R` bit, the constant
`SIB`, the four-byte displacement and its signed ends, `%r8` and `%r15`
as values, the absolute row without `0x67`, the 32-bit and 16-bit
siblings, the no-base indexed and base+index neighbours, both `moffs`
forms with the `0x67` offset-width disagreement, the `0x67` RIP-relative
row and two rejected spellings);
`EXP-0094` (the nine- and ten-byte `0x67 66` absolute `SIB = 25` rows at
the 16-bit width, the `REX` byte at position 2 and its operand-owned `R`
bit, the constant `SIB`, the four-byte displacement and its signed ends,
`%r8w` and `%r15w` as values, the absolute row without `0x67`, the
32-bit and 64-bit siblings, the no-base indexed and base+index
neighbours, both `moffs` forms with the offset-width disagreement, the
`0x67 66` RIP-relative row and two rejected spellings);
and
523
negative fixtures whose
complete diagnostic sets — code, JSON Pointer, detail keys — are compared for
exact equality. `E-OPERAND-004`/`N14` (an operand wider than its field) is one
of them.

The AArch64 slice adds `definitions/aarch64/0.1.0.json` (four forms: two `add`,
`bl`, `adrp`; digest `sha256:96f87aa…`) with the Arm BSD-3-Clause notice beside
it, `EXP-0008` (five MRS nodes, the all-32-bits-covered check, and the
`immlo`-at-30:29 correction the oracle caught), and 20 positive + 57 negative
fixtures. `0.2.0` adds the fifth form, `aarch64:add/x64-imm12-lsl12` (digest
`sha256:169e4bf6…`), which pins `sh = 1` and leaves the operand as `imm12`
field content (ADR-0011, `EXP-0013`); `N18a`/`N18b` record the two literals that
must be rejected rather than form-switched. `0.3.0` adds the sixth,
`aarch64:b.cond/imm19` (digest `sha256:71af93c0…`), where the condition is a
four-bit operand rather than sixteen near-identical rows (ADR-0012, `EXP-0014`);
`N03-cond` and `N04c` pin `cond = 16` and an `imm19` overflow. `0.4.0` adds five
load/store rows (digest `sha256:14d6c2b6…`), one per addressing kind, with `disp`
as field content in 8-byte units (`imm12`) or signed bytes (`imm9`) (ADR-0013,
`EXP-0015`); `A64-P3-ldst-addressing` is 24 bytes over five forms, and
`N03-imm12-disp`/`N03-imm9-disp`/`N01b` pin the two range rejections and the
absent register-offset kind. `0.5.0` adds four `movz` rows (digest
`sha256:9cec1688…`), one per `hw` lane, with `imm16` as field content (ADR-0014,
`EXP-0016`); `A64-P7-movz-lane` is 20 bytes over all four, and `N18c`/`N01d` pin
the pre-scaled literal and the absent `lsl #8` lane. `0.6.0` adds three shift
rows (digest `sha256:1151944e…`), one per keyword, with the amount as an `imm6`
operand in `0…63` (ADR-0015, `EXP-0017`); `A64-P8-shift-modifier` is 24 bytes
over all three, and `N03-imm6`/`N19`/`N01e` pin the range, the modifier carrier
and the absent extend family. `0.7.0` adds eight extend rows (digest
`sha256:1bb92035…`), one per `option` value, with the keyword fixing the source
width and the amount as an `imm3` operand over `0…4` minus `5…7` (ADR-0016,
`EXP-0018`); `A64-P9-extend-modifier` is 32 bytes over all eight, and
`N03-imm3`/`N16c`/`N02b`/`N01f` pin the field end, the excluded tail, the source
class and the absent `sub` node. `0.8.0` adds six `sub` rows (digest
`sha256:9f82b566…`) from the `op = 1` twin of the two `add` nodes, with the
mnemonic as the form family and register 31 reading `xzr` (ADR-0017, `EXP-0019`);
`A64-P10-sub-family` is 24 bytes over six forms, and `N01g`/`N01h`/`N18d` pin the
absent `subs`, the absent `w` form and the literal that only fits the other `sh`
half. `0.9.0` adds twelve `adds`/`subs` rows (digest `sha256:99728cd9…`) from the
four `S = 1` nodes, one bit over the `add`/`sub` shapes, with the flag-setting
mnemonic as the form family (ADR-0018, `EXP-0020`); `A64-P11-adds-subs-family` is
48 bytes over twelve forms, and `N01i`/`N01j`/`N18e` pin the absent `cmp` alias,
the absent `w` form and the literal that only fits the other `sh` half. `0.10.0`
adds twenty-four `w` rows (digest `sha256:e958d69b…`), the same six shapes on the
eight `sf = 0` nodes with every register slot `aarch64.gpr32`/`w32` and the
32-bit `imm6` tail excluded (ADR-0019, `EXP-0021`); `A64-P12-w-rows` is 96 bytes
over twenty-four forms, and `N01k`/`N02c`/`N16d`/`N18f` pin the version boundary,
the `x64` operand, `imm6 = 32` and the same literal. `0.11.0` adds twenty-four
extended `sub`/`adds`/`subs` rows (digest `sha256:c5a9aec9…`), the eight
`option` rows repeated on the three `op = 1`/`S = 1` extended nodes, with the
keyword still fixing `src2`'s width and `imm3` still excluded over `5…7`
(ADR-0020, `EXP-0022`); `A64-P13-ext-family` is 108 bytes over twenty-seven
instructions, and `N01l`/`N02d`/`N16e` pin the absent 32-bit extended node, the
wrong `src2` class and `imm3 = 5`. `0.12.0` adds forty `cmp`/`cmn` alias rows
(digest `sha256:8a428926…`), each the `subs`/`adds` base row with `Rd` pinned to
31 and the `dest` slot removed, with the MRS alias node used only as the pairing
check because it carries no `encoding` (ADR-0021, `EXP-0023`);
`A64-P14-cmp-cmn-family` is 188 bytes over forty-seven instructions, and
`N02e`/`N01i`/`N01m` pin the extra `dest` operand and the two version boundaries.
`0.13.0` adds the three store `imm9` rows (digest `sha256:d3876dd3…`), the load
rows' layouts with `opc = 00` and `Rt` as `src`, so the kind stays the `form_id`
and `disp` keeps its signed-byte range (ADR-0022, `EXP-0024`);
`A64-P15-store-imm9-addressing` is 32 bytes over five forms, and `N03` ×2 plus
`N01n` pin the two range ends and the `0.12.0` boundary. `0.14.0` adds the
literal load (digest `sha256:a90ceac1…`), `LDR_64_loadlit` with `opc = 01` and
`dest`/`target` as its only slots: `imm19` is field content in 4-byte units, so a
byte displacement is a `pcrel_begin` + `scale(2)` fixup (ADR-0023, `EXP-0025`);
`A64-P16-loadlit` is 24 bytes over one form, `N04d` rejects `imm19 = 262144`,
`N20` rejects a 2-byte symbol offset as `E-RANGE-003`, and `N01o` is the `0.13.0`
boundary. `0.15.0` adds the sixteen register-offset rows (digest
`sha256:422ebb83…`), `option` and `S` pinned per row and `Rm` as an `index` slot
whose width follows `option`, so the scale is never an operand (ADR-0024,
`EXP-0026`); `A64-P17-regoff` is 80 bytes over the sixteen rows plus four
register-31 rows, `N01p` is the `0.14.0` boundary, `N01q` rejects a `-lsl1` row,
`N02f` rejects a `w32` index on a `-lsl0` row, and `N19b` rejects `lsl #3` as a
modifier. `0.16.0` adds the sixteen 32-bit register-offset rows (digest
`sha256:1e83c6ca…`), the same eight pairs at `size = 10` with `option` intact,
`S = 1` as `#2` and only `Rt` changed to `w32` (ADR-0025, `EXP-0027`);
`A64-P18-w32regoff` is 80 bytes over the sixteen rows plus the four register-31
rows, `N01r` is the `0.15.0` boundary, `N01s` rejects a `-lsl3` row, `N02g`
rejects a `w32` index on `-lsl0`, `N02h` rejects an `x64` destination, and
`N19c` rejects `lsl #2` as a modifier. `0.17.0` adds the eight 64-bit
`movk`/`movn` rows (digest `sha256:de2c53e1…`), the four `hw` lanes on each of
`MOVK_64_movewide`/`MOVN_64_movewide` with `opc` fixed by the node and `imm16`
stored raw (ADR-0026, `EXP-0028`); `A64-P19-movwide` is 48 bytes over the eight
rows plus four boundary rows, `N01t` rejects a `-lsl8` lane, `N01u` is the
`0.16.0` boundary, `N01v` rejects a `w32` lane, `N01w` rejects the `mov` alias,
`N02i` rejects a `w32` destination, and `N03-movk-imm16`/`N18g` reject the field
end and a pre-scaled literal.
A64-P5/P6 use `llvm-mc` →
`ld.lld` → `llvm-objcopy`
because `llvm-mc` leaves AArch64 branch and `adrp` fields as relocations; A64-P3,
A64-P4, A64-P7, A64-P8, A64-P9, A64-P10, A64-P11, A64-P12, A64-P13, A64-P14,
A64-P15, A64-P16, A64-P17, A64-P18 and A64-P19
need no
linker
because their
operands are immediates or local labels in one section and `llvm-mc` resolves
them, emitting no relocations.
The generator now gates each form on a `since` version, so an older document
cannot lose a form and a newer one cannot gain one by accident. The fixture gate
scans every `fixtures/<isa>/<kind>/` directory, so a new table's vectors are gated
the moment they land.

The RV64 slice adds two documents. `definitions/rv64/0.1.0.json` holds seven
base-`I` forms (`add`, `addi`, `beq`, `jal`, `auipc`, `ld`, `sd`; digest
`sha256:6afb2bf4…`); `definitions/rv64/0.2.0.json` adds `riscv:c.addi/rd-imm6`
and declares `["rv64i","rv64c"]` (eight forms; digest `sha256:8329a38f…`). Both
carry the BSD-3-Clause-Clear notice. ADR-0007 fixes the source as the UDB
resolved spec (`sha256:be184986…`); `EXP-0009` measures eight instruction nodes
and reproduces fourteen `llvm-mc` byte strings from their `location` fields;
`EXP-0010` generates both documents from the same eight nodes, asserts full-bit
coverage, selects the `RV64` encoding block of `ld`/`sd` so the `RV32` Zilsd
`not:` list cannot leak, turns each `not:` into the slot's `excluded` list
(ADR-0009), and re-encodes sixteen probe vectors from the tables it built.
`tools/check_rv64_source.py` gates the drop, the SPDX headers and
`definitions/rv64/NOTICE`.

The nine positive fixtures exercise `add`, both `addi` endpoints, the B-type
scatter forward and backward, the J-type scatter forward and backward, the
`auipc` field, `ld`/`sd` at both signed imm12 endpoints, and `c.addi` (four
immediates, with the 4-byte `addi` on the same immediate beside it), plus the
`pcrel_hi`/`pcrel_lo12` pair. The twelve negatives pin `E-FORM-001` (including
`N01c`, the same form named against `0.1.0`), `E-OPERAND-001`, `E-RANGE-001`,
`E-RANGE-002`, `E-RANGE-004` (`N16a`/`N16b`, the excluded zeroes),
`E-FIXUP-009`/`E-FIXUP-007` (`N17a`/`N17b`/`N17c`, the pair half),
`E-TARGET-001` (`N06`, a plan that declares `rv64i` against a table that also
declares `rv64c`), and (read time) `E-OPERAND-003`. `RV-P8-pcrel-pair` is the first pair fixture whose oracle is the
object file's relocation records rather than linked bytes: one `auipc`, one `addi`
and one `sd`, all `emit_relocation`, so one `hi` and two `lo` members produce
three records, and the bytes are three templates with zero immediates while
`llvm-readobj -r` supplies the records (`HI20`, `LO12_I`, `LO12_S`). Its companion
`RV-P8-pcrel-pair-resolved` is the arithmetic gate: `auipc` at 4, symbol at
0x1000, both fixups `resolve_in_place`, and the linked words `0x00001517` /
`0xFFC50513` equal `(0x1000 - 4 + 0x800) >> 12 = 1` and
`(0x1000 - 4) & 0xFFF = 0xFFC`; `lo12_i` would write 0x000, `pcrel_begin` on the
low half 0xFF8, and dropping `+0x800` 0, so the fixture separates the decision
from its neighbours. See ADR-0010.

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
| CI hosts | GitHub Actions `ubuntu-24.04` 20261101.360 (`x86_64`), `macos-26-arm64` 20261102.0473 (`aarch64`) and `windows-2025-vs2026` 20261103.298, all with Rust 1.96.0 |

## Immutable source text

`docs/fmp-v0/00_directive.md` is a verbatim copy of the research directive. It is
never edited. Integrity checksum (SHA-256) is recorded in
`research/evidence/source_index.md`.
