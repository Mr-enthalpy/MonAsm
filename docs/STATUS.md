# Status

Updated: 2026-11-04
Phase: **3 in progress (x86, AArch64 and RV64 slices): ten definition documents, the materializer and the fixture gate are in place; every x86, AArch64 and RV64 coverage row is now carried, so widening is coverage work with its own ADR per slice**
Owner: Mr-enthalpy

This file is the recovery point. A new session should be able to resume from
this file plus `AGENTS.md` alone.

## Phase board

| Phase | Scope | State |
|---|---|---|
| 0 | Environment, evidence baseline, docs skeleton | **complete** |
| 1 | Encoder boundary audit (XirAsm, LLVM) | **complete** for XirAsm; LLVM internals deferred |
| 2 | FMP v0 contract, schema, error model | **complete for the x86, AArch64 and RV64 slices**; the last RV64 row's psABI pairing is now part of the contract (ADR-0010) |
| 3 | Three-ISA vertical prototype | **in progress**: ten definition documents frozen (`07_definition_format.md`, `EXP-0004`, `EXP-0008`, `EXP-0010`, `EXP-0012`); `fmp-model`/`fmp-validate`/`fmp-materialize`/`fmp-cli` implemented; x86 has 5 positive and 15 negative fixtures, AArch64 has 10 positive and 20 negative, RV64 has 9 positive and 11 negative, all passing the two-source gate |
| 4 | Invariants, negative tests, replay | not started |
| 5 | Convergence, route evaluation, roadmap | not started |

## Gates

| Gate | Condition | State |
|---|---|---|
| G0 | `llvm-mc` available and emits bytes for x86-64, AArch64, RV64 | **passed** 2026-11-03 (LLVM 23.1.2) |
| G1 | Three questions answered from source: x86 relaxation disable, RISC-V form addressing, AArch64 library entry point | **passed** 2026-11-03 (all three answered; see `90_boundary_audit.md` §4) |
| G2 | Every `EC-*` row has an observed counterexample and a decided carrier | **in progress**: 22 of 32 rows are frozen; the 10 rows still `draft` are EC-05, EC-08, EC-09, EC-10, EC-16, EC-18, EC-23, EC-24, EC-25 and EC-26, and none of them is needed by the three slices as they stand |
| G3 | Each ISA has >= 3 positive and >= 2 negative vectors passing two-source checks | **satisfied for x86, AArch64 and RV64** (x86: 5 positive, 15 negative; AArch64: 10 positive, 20 negative; RV64: 9 positive, 11 negative) |

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
| ADR-0016 | An AArch64 extend keyword is a form and the amount is field content with an excluded tail: `0.7.0` adds eight rows, one per `option` value (`-imm3-uxtb` … `-imm3-sxtx`), with `option` pinned at 15–13, `src2` a `w` register on the six `[su]xt[bhw]` rows and an `x` register on the two `[su]xtx` rows, and `imm3` as an `aarch64.imm`/`imm3` operand at `[10,3]` over `0…4` with `excluded: [5,6,7]`; `imm3 = 8` is `E-RANGE-001` (`N03-imm3`), `5` is `E-RANGE-004` (`N16c`), a `w` operand on a shifted row is `E-OPERAND-001` (`N02b`), and `sub`/`adds`/`subs`/the 32-bit node stay out (`E-FORM-001`, `N01f`) | accepted 2026-11-04 |

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
| OD-13 | A memory operand is field-level: `base`/`disp` are separate operands and the addressing form is a `form_id` variant; a composite `{"mem": …}` payload is `E-OPERAND-003` | ADR-0008; ADR-0013 (AArch64 half); `EXP-0011`; `EXP-0015`; `N15`; `N01b` |
| OD-14 | A slot may exclude a closed list of exact values inside its domain; the rejection is `E-RANGE-004`, the check is a lookup, and an absent key means no exclusion | ADR-0009; `EXP-0012`; `N16a`/`N16b` |
| OD-15 | A `hi`/`lo` pair expresses RISC-V's "the low half names the high half" with `pcrel_hi` (P = the paired `hi`'s site) and `pcrel_lo12` (mask the displaced value), a zero `lo` addend, and a 1:N group | ADR-0010; psABI `riscv-elf.adoc:1578-1605`; `RV-P8-pcrel-pair`, `RV-P8-pcrel-pair-resolved`; `N17a`/`N17b` |

## Open decisions

See `docs/fmp-v0/05_open_decisions.md`. Blocking items currently:

| ID | Question | Blocks |
|---|---|---|
| OD-05 | Unknown fields and extensions | AC-10, Q10 |
| OD-08 | Canonical wire form | AC-07 |

OD-05 and OD-08 do not block the x86 slice. OD-07 is settled by ADR-0005 and
pinned by ADR-0006, and the AArch64 tables it authorised now exist: five MRS
nodes generated the forms in `definitions/aarch64/0.1.0.json`, the same nodes
generated `0.2.0.json` with one extra row for the `sh = 1` half of `A64-P2`
(ADR-0011), and `0.3.0.json` adds the `b.cond` row whose condition is an operand
(ADR-0012). `0.4.0.json` adds five load/store rows from five more nodes, one per
addressing kind (`A64-P3`, ADR-0013), `0.5.0.json` adds four `movz` rows from
one node, one per `hw` lane (`A64-P7`, ADR-0014), `0.6.0.json` adds three
shift rows from `ADD_64_addsub_shift`, one per keyword (`A64-P8`, ADR-0015), and
`0.7.0.json` adds eight extend rows from `ADD_64_addsub_ext`, one per `option`
value (`A64-P9`, ADR-0016).
Ten fixtures match `llvm-mc` (`EXP-0008`, `EXP-0013`, `EXP-0014`, `EXP-0015`,
`EXP-0016`, `EXP-0017`, `EXP-0018`). Every directive §6.2 item now has a passing
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
content, so the four addressing kinds are five rows in `aarch64/0.4.0.json` and
`N01b` rejects the register-offset kind (`EXP-0015`). OD-14 is settled by
ADR-0009: `EXP-0012` §2 measured that
`c.addi a0, 0` (`01 05`) and `c.addi x0, 1` (`05 00`) are reserved HINTs despite
being inside the declared range, so the slot excludes `0` and
`riscv:c.addi/rd-imm6` lands in `rv64/0.2.0.json` (`RV-P7`, `N16a`/`N16b`). OD-15
is settled by ADR-0010: the ELF psABI (`v2.0-rc0`, `EV-22`) states that the low
half resolves against the high half's site, that its addend must be 0, and that
one high part may serve several low parts, so `pcrel_hi`/`pcrel_lo12` and a 1:N
`pair_group` are now `fmp/0.1` (`RV-P8-pcrel-pair`,
`RV-P8-pcrel-pair-resolved`, `N17a`/`N17b`). OD-06 was
load-bearing because `EXP-0002` W1 shows that a definition drift the digest does
not cover is caught only by the weaker size check; it is now settled, and
`EXP-0004` §4 measures both halves.

## Next action

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
   `X86-P4`/`P6` carry a precondition (enumerate and measure one `form_id` per
   addressing variant) rather than an open question. The non-zero question is
   closed too: `OD-14`/ADR-0009 added `excluded`, and `RV-P7` now passes
   (`EXP-0012`).
2. Extend the AArch64 coverage, one vertical slice at a time. All eight directive
   §6.2 items now pass; the next slices are widening, and each needs its own ADR
   (ADR-0011 decision 7's rule):
   - `sub` (`SUB_64_addsub_shift` / `SUB_64_addsub_imm`) and the `w`-width rows
     (`sf = 0`, `EC-11`);
   - the load/store kinds still absent: register-offset, literal, and the store's
     `imm9` pre/post pair (ADR-0013 kept them out).
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
   and the absent `sub` node. A `:lo12:` inside the
   `-lsl12` form is measured at the record level but is not a symbol address
   (`EXP-0013` §5); a slice that wants one must decide what its addend means
   first.
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
it, `EXP-0008` (five MRS nodes, the all-32-bits-covered check, and the
`immlo`-at-30:29 correction the oracle caught), and 10 positive + 20 negative
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
class and the absent `sub` node. A64-P5/P6 use `llvm-mc` →
`ld.lld` → `llvm-objcopy`
because `llvm-mc` leaves AArch64 branch and `adrp` fields as relocations; A64-P3,
A64-P4, A64-P7, A64-P8 and A64-P9 need no linker because their operands are
immediates or local labels in one section and `llvm-mc` resolves them, emitting no
relocations.
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
`pcrel_hi`/`pcrel_lo12` pair. The eleven negatives pin `E-FORM-001` (including
`N01c`, the same form named against `0.1.0`), `E-OPERAND-001`, `E-RANGE-001`,
`E-RANGE-002`, `E-RANGE-004` (`N16a`/`N16b`, the excluded zeroes),
`E-FIXUP-009`/`E-FIXUP-007` (`N17a`/`N17b`/`N17c`, the pair half), and (read time)
`E-OPERAND-003`. `RV-P8-pcrel-pair` is the first pair fixture whose oracle is the
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

## Immutable source text

`docs/fmp-v0/00_directive.md` is a verbatim copy of the research directive. It is
never edited. Integrity checksum (SHA-256) is recorded in
`research/evidence/source_index.md`.
