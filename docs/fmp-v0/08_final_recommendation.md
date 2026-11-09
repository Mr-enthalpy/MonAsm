# FMP v0 Final Recommendation

Status: **final for the v0 scope** (Phase 5, 2026-11-08). This document is the
Phase 5 convergence deliverable required by `00_directive.md` §11 ("Phase 5") and
§17. It does not introduce a new machine fact, field, code, or target table. Every
claim below either cites a file and section, names an executable test, or is
labelled `inference` / `unverified` per `AGENTS.md` rule 3.

Naming note: `00_directive.md` §15 lists `05_final_recommendation.md` as an
example filename, but this set already uses `05_open_decisions.md` as the `OD-*`
registry. The Phase 5 deliverable is therefore `08_final_recommendation.md`; the
content required by §17 is unchanged. This is the only naming deviation.

Inputs: `01_contract.md` to `07_definition_format.md`, the ADR set through
`ADR-0094`, `06_validation_matrix.md`, `90_boundary_audit.md`,
`91_reuse_matrix.md`, `EXP-0002`, `EXP-0004`, `EXP-0096`, `EXP-0033`, the
`definitions/` tree, and the `fixtures/` corpus. Phase 5 is a
documentation/convergence pass; no Rust source, definition document, fixture, or
schema file changed to produce this report.

The one-sentence definition this report must defend is `00_directive.md` §18:

> A Frozen Machine Plan is a machine plan bound to a versioned target encoding
> definition in which every observable encoding and layout choice is already
> made; the deterministic materializer only validates and executes that plan and
> has no planning authority that could change a machine fact.

---

## A. Executive Decision

### A.1 Recommended FMP v0 boundary

FMP v0 ships **Level 0** by default: one canonical plan object, validated and
executed against a pinned definition, producing bytes plus normalized fixup
records. **Level 1** (the same plan projected as laid-out sections, an optional
declared symbol table and the same records) is implemented as an opt-in through
`artifact: sections` (`ADR-0096`, `01_contract.md` §11.2). Neither level writes a
container file. The boundary is:

- **In scope.** `format_version = "fmp/0.1"`; `target_identity`;
  `definition_identity` (`namespace` + `version` + `digest`);
  `output_contract` with `artifact = "bytes"` (Level 0) or `"sections"`
  (Level 1); `sections` with fragments; `symbols`; `instructions` naming an
  exact `form_id` with typed operands; `fixups` with field descriptors, targets,
  PC rules, transforms, ranges and pairing. The full field set and its
  counterexamples are `01_contract.md` §3–§12.
- **Out of scope, rejected, not silently accepted.** `emit_fixups: false`, a
  non-default `fixup_record_order`, non-empty `feature_constraints`, and
  `section_relative` fixup targets. The first three are `E-VERSION-001`; the last
  was `inference`/`unverified` with no v0 fixture, and the `47a383b` audit now
  refuses it `E-VERSION-001` as well (`N24j`, `ADR-0123`,
  `03_fixup_model.md` §2.1). A Level 0 plan that asks for a symbol table is also
  `E-VERSION-001` (`N24i`); Level 2 containers are out of `fmp/0.1`.
- **Not frozen, explicitly optional.** Three plan fields stay `draft`:
  `source_ref`, `source_trace`, `symbol.type` (`01_contract.md` §7, §9). They
  never affect output, so they do not carry a v0 counterexample. `symbol_order`
  is now `frozen`: Level 1 makes the emitted table order observable, and
  `X86-P71` pins the declared order against `symbol_id` order (`ADR-0096`). Per
  `AGENTS.md` rule 2 a field without a counterexample is never marked `frozen`.

The contract-set status therefore moves from `draft` to **"frozen for the v0
scope"** in `ADR-0095`, not to "all fields frozen". "Frozen for v0 scope" means
the in-scope surface is decided and tested; it does not claim the deferred fields
or `section_relative` are validated.

### A.2 Recommended route

**Route C**, as already accepted in `ADR-0001`: a self-owned validator plus a
minimal deterministic encoding kernel driven by versioned target definitions.
XirAsm and LLVM remain oracles and knowledge sources only. The Phase 1 audit
(`90_boundary_audit.md`, `91_reuse_matrix.md`) is re-read here and does not
change the decision; §F records the evidence.

### A.3 Principal evidence

| Evidence | Source | What it proves |
|---|---|---|
| Three ISA vertical loops close byte-exactly | `06_validation_matrix.md` §4; `fixtures/` | 128 positive plans reproduce independently derived bytes; x86 85, AArch64 26, RV64 17 |
| Strict rejection is exercised, not asserted | `06_validation_matrix.md` §1; `04_errors.md` §2 | 619 negative plans, each pinned to a code, JSON Pointer and detail-key set |
| Determinism replays on three hosts | `EXP-0033` §6; CI runs on Ubuntu, macOS, Windows | Identical artifacts and diagnostics across hosts and processes |
| Every invariant has an executable test | `01_contract.md` §2 | INV-01 through INV-08 are `verified` |
| Encoding ambiguity has counterexamples | `02_encoding_choices.md`; `EXP-0096` | 44 `EC` rows frozen; the seven absent families are rejected `E-FORM-001` |
| Definitions are versioned and digest-pinned | `07_definition_format.md` §6, §8 | 104 documents: x86 78, AArch64 20, RV64 6; canonical digests recorded |
| Route A/B are evidence-backed rejections | `90_boundary_audit.md` §3; `91_reuse_matrix.md` | x86 paths class D, RV64 narrow class B, AArch64 knowledge only |

### A.4 Open blockers

Only one item blocked overall completion, and Phase 5 closes it:
**AC-10** (`06_validation_matrix.md` §3) required an executable next step. §H now
supplies the module list, order, gates, and risks.

No correctness blocker remains for the v0 scope. The remaining items are recorded
here so they cannot be mistaken for coverage:

1. **Level 1 object output** is implemented as of 2026-11-08 (`01_contract.md`
   §11.2, `ADR-0096`): `artifact: sections` splits the same image into sections
   and optionally emits the declared symbol table. Level 2 containers and
   symbol synthesis remain out of `fmp/0.1`.
2. **`section_relative` fixups** are named by the contract but had no measured
   meaning (`03_fixup_model.md` §2.1). Since the `47a383b` audit they are
   refused `E-VERSION-001` (`ADR-0123`, `N24j`) instead of being resolved from a
   base address, and a later slice re-opens the kind only after measuring it.
3. **Eight reachable error codes had no fixture when this report was written.**
   M1 closed that gap on 2026-11-08 with `N24a`–`N24h`; M3 repointed `N24h` to
   `emit_fixups: false` and added `N24i` for the Level 0 symbol-table gate; the
   `47a383b` audit added `N24j`–`N24l` and `E-LIMIT-001`.
   `04_errors.md` §2.4 now records 39 of the 44 active codes as fixture-covered,
   and the five remaining are the JSON-layer, non-plan, structurally unreachable
   and internal groups listed there.
4. **LLVM internals remain unverified** (`90_boundary_audit.md` §8). LLVM was used
   only as an oracle; no LLVM source path was traced, so no LLVM-internal claim is
   made.

---

## B. Source Audit

### B.1 XirAsm-lib encoding path

The audit is a source-and-experiment audit of revision `3ee8a439f5ba`
(`90_boundary_audit.md` §1). The relevant findings:

- **x86 form selection is inside the library and is policy.** `findMatch`
  (`x86_encoder/match.zig:287-349`) resets caller choices and applies curated
  tie-breaks (`F-03`). The full pipeline
  (`x86_encoder/api.zig:258-367`) selects the template, selects the branch form,
  re-encodes to `.near` on a second pass, and rewrites the fixup from the encoded
  size (`F-04`, `F-05`, `F-07`). That is four independent planning decisions the
  FMP must own.
- **The x86 fixup model cannot express an FMP fixup.** It is
  `{kind, size, toffset, relbase}` over contiguous bytes (`encode.zig:127-140`,
  `api.zig:1550-1583`, `F-05`, `F-06`): no field descriptor, PC rule, transform,
  range, resolution mode, or pair (`91_reuse_matrix.md`).
- **RISC-V has a narrow form-addressable entry point.** `encodeRaw`
  (`riscv_encoder/api.zig:28` → `encode.zig:137-144`) takes a pinned spec and
  rejects over-wide fields (`F-08`, `F-10`), but its spec identity is an index or
  `match`/`mask`, not a version-stable id. The semantic `encode` path resolves
  operands through a switch and aliases and is class D (`F-08`).
- **AArch64 is not a component.** The library exports only `x86`, `riscv`, and
  `spirv` (`xirasm_backend.zig:3-5`, `F-01`). AArch64 exists as a 40.88 MB
  Meta-language include tree (`F-12`).

### B.2 LLVM encoding and fixup path

LLVM 23.1.2 was used only as an external oracle. No LLVM source was read in
Phase 1, so this report makes no claim about how `MCAssembler` or
`MCCodeEmitter` orders relaxation (`90_boundary_audit.md` §8). What is established
is behavioural: `llvm-mc` supplies the independently derived bytes and relocations
for the fixture corpus, and each `*.oracle.json` records tool, version, command and
input/output hashes (`fixtures/README.md`). Route B is evaluated in §F on the
audit evidence we do have, not on an unverified internal model.

### B.3 Policy isolation judgement

`91_reuse_matrix.md` classifies every examined component. The result:

- x86: no path is class A or B for execution; the template matcher is **D as
  code, A as knowledge**.
- RV64: the table and `encodeRaw` are **B**, but the identity is not
  version-stable, so they are viable as an oracle cross-check, not a runtime
  dependency.
- AArch64: **D as runtime, A as knowledge**; the useful output is the Arm MRS
  provenance pointer (`F-13`).

**Conclusion.** A strict adapter cannot isolate the planning policy because the
policy sits in the same functions that write bytes. Route A would require a fork,
not an adapter. This is the audit-level justification for Route C, independent of
any preference.

---

## C. Frozen Contract

Status: **frozen for the v0 scope** (`ADR-0095`). The canonical text remains
`01_contract.md`; this section is a map, not a replacement.

### C.1 Data model

A plan is one closed JSON object with nine top-level members: eight required and
the optional `provenance` (`01_contract.md` §3). Every object is closed; an
unknown field is `E-PLAN-003` (the definition
loader reports `E-DEF-001`). Numbers are JSON integers only; a float is
`E-PLAN-002` and an expression-shaped scalar is `E-PLAN-002` at read time
(`N23a`). Lists have declared order and are rejected if out of order
(`E-LAYOUT-004`), never sorted.

### C.2 Form identity

`form_id` is `<isa_family>:<mnemonic>/<variant>[/<encoding_family>]`
(`01_contract.md` §7, OD-04). It names an encoding form, not a semantic operation
and not a library opcode integer. The variant encodes every distinction the
operands do not; two forms that can emit different bytes must have different ids.
Resolution is a pure lookup against the pinned `namespace + version + digest`,
with no alias table and no near-match (`E-FORM-001`). A renamed form changes the
digest, so an old plan fails `E-DEF-001` before lookup; a dishonest digest that
still reaches lookup fails `E-FORM-001` (`N01`, `EXP-R5`).

### C.3 Operands

An operand is `{role, kind, target_type, payload, modifiers}`
(`01_contract.md` §8). `target_type` names the slot constraint, not the storage
class; it is a guard that can only fail a plan (`E-OPERAND-001`), never choose
bits. `payload` has exactly four shapes: `{reg}`, `{value}`, `{symbol_id}`, `{}`;
a composite memory object is `E-OPERAND-003` (`N15`). Memory is decomposed into
one operand per encoded field and the addressing shape is a form variant, because
otherwise the encoder would pick `mod`/`SIB` from values (`INV-02`).
`modifiers` is sorted and is a guard, not a selector.

### C.4 Encoding choices

`encoding_choices` is not part of `fmp/0.1` (`ADR-0004`). Every byte-affecting
decision is carried by `form_id` or a typed operand. The 42 `EC` rows in
`02_encoding_choices.md` name the carrier of each decision. The seven families
that would need a plan-side carrier v0 does not ship stay absent and are rejected
`E-FORM-001` (`ADR-0094`, `EXP-0096`).

### C.5 Layout

Layout is fixed by fragments inside sections (`01_contract.md` §6). The
materializer checks containment (`E-LAYOUT-001`), gap and sum equality
(`E-LAYOUT-002`), instruction/fragment agreement (`E-LAYOUT-003`), declared order
(`E-LAYOUT-004`), and uniqueness/ordering rules (`E-LAYOUT-006`, `E-LAYOUT-007`).
It never pads, relaxes, reorders, or inserts a trampoline. `E-LAYOUT-005` names
"the encoder would have to compute padding" and remains intentionally unreachable
because no plan field requests alignment (`04_errors.md` §2.3, `N22`).

### C.6 Symbols and fixups

A fixup carries `field_descriptor`, `target`, `addend`, `pc_reference_rule`,
`value_transform`, `range_constraint`, `resolution_mode`, and optional pairing
(`03_fixup_model.md` §2–§8). Target kinds are `symbol`, `absolute`, and
`section_relative`; only the first two are exercised, and `section_relative` is
refused `E-VERSION-001` (`§2.1`, `ADR-0123`). `resolve_in_place` computes and writes;
`emit_relocation` zeroes and records. One writer per bit is enforced
(`E-FIXUP-006`). The Level 0 record is the uniform cross-ISA shape: one record
shape carries every `emit_relocation` case, which is why `E-FIXUP-004` was retired
(`04_errors.md` §2.2).

### C.7 Version and error model

`format_version` is an exact string (`E-PLAN-001`). Definition identity is
`namespace + version + digest`; an unshipped pair is `E-DEF-002`, a digest
mismatch is `E-DEF-001` (`N10`, `EXP-R5`). Errors have stable identity
`(code, plan_path, sorted detail keys)` and are sorted by `(plan_path, code)`;
prose is not identity (`04_errors.md` §1, `EXP-R6`). The registry has 44 active
codes; the retired and unreachable sets are stated explicitly in `04_errors.md`
§2.2–§2.3 so a later slice cannot mistake absence for coverage.

### C.8 What is not frozen

`source_ref`, `source_trace`, `symbol.type` remain `draft`
(`01_contract.md` §7, §9). `section_relative` is refused `E-VERSION-001` rather
than left `unverified` (`03_fixup_model.md` §2.1, `ADR-0123`). `symbol_order` is frozen because Level 1 emits the
table in that order (`ADR-0096`). Level 1 itself is implemented; Level 2
containers and synthetic symbols remain out of v0 scope. These are recorded as
out of v0 scope, not as frozen facts.

---

## D. Cross-ISA Validation

### D.1 x86-64

- **Surface.** 78 definition documents, `0.1.0` … `0.78.0`; the canonical latest
  table has **632 forms** (measured from
  `definitions/x86_64/0.78.0.json`). Twenty `EC` rows are carried by this
  architecture (`02_encoding_choices.md` §"v0 surface").
- **Fixtures.** 85 positive plans and 527 negative plans. The positive set covers
  the `mov`/`add`/`and`/`or`/`xor`/`cmp`/`sub` integer families in both
  directions and at 64/32/16 bits (register/register, immediate, and for `sub`
  the memory directions), `imm8`/`imm32`, `rel8`/`rel32`, register
  extension through `REX`, base/index/scale, absolute and RIP-relative
  addressing, SSE/VEX/EVEX register and memory shapes, the byte-register
  high/low split, and the Level 1 section/symbol envelope (`X86-P71`).
- **Key counterexamples.** `mov r64, r64`/`mov r64, rm64` are two forms
  (`89`/`8B`), and a plan naming a coarse form is `E-FORM-001` (`N01`). The two
  legal encodings of `add` (`01`/`81`) are separate forms. `REX` byte
  reconstruction is pinned by `X86-P10` to `X86-P56`. The same-length defect
  `48 89 d8` → `49 89 d8` is caught only by `expected_digest`
  (`EXP-0002` W2, `E-BYTE-001`).
- **Fixup.** `X86-P8` and `X86-P6` cover `rel32` records and `R_X86_64_PC32`
  (§D.4).

### D.2 AArch64

- **Surface.** 20 definition documents, `0.1.0` … `0.20.0`; **185 forms**
  (measured from `definitions/aarch64/0.20.0.json`, distinct across all
  versions). Sixteen `EC` rows are carried by this architecture.
- **Fixtures.** 26 positive and 69 negative plans. The positive set covers
  `add`/`sub`/`adds`/`subs` across immediate, shifted-register and
  extended-register variants; `cmp`/`cmn`; `movz`/`movn`/`movk`; `ldr`/`str`/
  `ldur`/`stur` across unsigned-offset, pre/post-index, register-offset and
  literal forms; `b.cond`, `bl`, `br`/`blr`/`ret`, `adrp` and the
  `adrp`+`:lo12:` pair; `adr`; and `mul`/`csel`. The
  `cbz`/`cbnz`/`tbz`/`tbnz` families and the `mov` alias are exercised as absent
  families, not as positives.
- **Key counterexamples.** `add` immediate variants `-lsl0`/`-lsl12` are separate
  forms (`N18a`/`N18b` show a value must not switch the `sh` form). `adrp` and
  `add :lo12:` share an encoding whose page low bits are split, so the plan names
  each form and the fixup names each field. The `mov` alias is absent and rejected
  (`ADR-0094`).
- **Fixup.** `A64-P6-adrp-lo12-pair` exercises a two-record pair with
  `pc_reference_rule = pcrel_page` / `page` (21-bit hi) and `none` / `lo12_i`
  (12-bit lo), `resolution_mode = resolve_in_place`, and `pair_group`.

### D.3 RV64

- **Surface.** Six definition documents, `0.1.0` … `0.6.0`; the latest table
  has **24 forms** (measured from `definitions/rv64/0.6.0.json`), including
  `lui` (`hi20`), `jalr`, the six B-type mnemonics, `c.addi` and the nine
  further load/store widths. The compressed slice is `rv64c`; base is `rv64i`.
- **Fixtures.** 17 positive and 23 negative plans. Positives cover `add`, `addi`,
  `ld`/`sd`, `lb`/`lh`/`lw`/`lbu`/`lhu`/`lwu`/`sb`/`sh`/`sw`,
  `beq`/`bne`/`blt`/`bge`/`bltu`/`bgeu`, `jal`, `auipc`, `lui`,
  `jalr`, `c.addi`, and the `pcrel_hi`/`lo12` pair. The `jal`/`c.j`/`jalr`
  pseudo-alias family is exercised as absent (negative), not as a positive.
- **Key counterexamples.** `c.addi`'s `xd` is a 5-bit field that accepts every
  register except `x0`, while `c.lw`'s `rd'` accepts only `x8`–`x15`; a shared
  `kind` would truncate, so `target_type` carries the per-form constraint
  (`EC-20`, `EXP-0012` §2). `slli` rv32/rv64 cannot be separated by `match`/`mask`
  (`F-09`), which is why `form_id` is the identity, not a table index.
- **Fixup.** `RV-P8-pcrel-pair` exercises `pcrel_hi` + `pcrel_lo12` with a 1:N
  `pair_group`, because one `auipc` may serve several lows.

### D.4 Key counterexamples and differences

| Distinction | x86-64 | AArch64 | RV64 |
|---|---|---|---|
| Form selection | `form_id` variant; coarse id rejected | `form_id` variant; `-lsl0`/`-lsl12` split | `form_id` with per-form register constraint |
| Memory carrier | one form per `mod`/`SIB` shape | one form per addressing kind | decomposed `base`/`disp` operands |
| Field placement | contiguous mostly; `REX` bits split | split page bits (`adrp`) | scatter (`B`/`J` immediates) |
| Fixup pair | not needed at v0 | `hi`/`lo` pair, 1:1 | `hi`/`lo` pair, 1:N |
| Zero/absent register | high-byte rules | `xzr`/`sp` encoding classes | `x0` exclusions per form |

The common structure is `form_id` + typed operands + field-descriptor fixups; the
target-specific parts are operand kinds, register numbering, field placement, and
pairing. This is the answer to Q7: the fixup *envelope* unifies, the *semantics*
stay target-specific.

---

## E. Determinism Proof Obligations

Each invariant has an executable test and a recorded result (`01_contract.md`
§2). The table reproduces the map; no row is "verified by argument".

| Invariant | Method | Result | Unverified remainder |
|---|---|---|---|
| INV-01 | `form_id` lookup, `E-FORM-001`, `N01` in three ISAs; `EXP-0096` for absent families | verified | none for v0 scope |
| INV-02 | exact lookup + operand signature; `N01`/`N02`/`N18`/`N19`; `ADR-0094` | verified | none; absent families are explicit rejections |
| INV-03 | `expected_size` + `E-SIZE-001`; `N05`, `N13`; positive lengths | verified | none |
| INV-04 | fragment checks and `N22` ordering/uniqueness | verified | `E-LAYOUT-005` intentionally unreachable |
| INV-05 | `EXP-R1`/`R2`/`R3`/`R4`/`R6`; canonical JSON and fingerprint tests | verified | none; `EXP-R3` passes on three hosts |
| INV-06 | data-only grammar; `N21a`/`N21b`, `N15`, `N23`; no evaluator in crates | verified | absence of evaluator is a source property reviewed per slice |
| INV-07 | full negative corpus; `EXP-R5`; `N13` | verified | none |
| INV-08 | fingerprint + provenance; `EXP-R2`/`R3`, `fingerprint_ignores_provenance`, `N10`, `N13` | verified | `section_relative` unexercised |

`EXP-0033` §6 records the three-host `EXP-R3` run: Ubuntu 24.04 `x86_64`, macOS
26.7.2 `aarch64`, Windows Server 2025, all on the pinned Rust 1.96.0 toolchain,
with identical artifact digests. CI runs `42402997326`, `42403439382`,
`42403938259`, `42404376743` are green on all three hosts.

The negative side is not a gesture: 619 negative plans are compared by exact code,
JSON Pointer, and detail-key set (`fixtures/README.md`; `fixtures.rs` requires
equality, not containment). That is the executable form of "does not secretly
plan": a plan that asks the materializer to choose gets a rejection, not a
plausible byte string.

---

## F. Route Evaluation

### F.1 Route A — XirAsm-lib centre

- **Reuse cost.** x86 is class D across every byte-producing path; adopting it
  means forking `findMatch`, the size calculator, branch relaxation, and the fixup
  model. RV64 `encodeRaw` is class B but keyed by a non-versioned spec identity.
  AArch64 has no backend at all.
- **Policy isolation.** None of the four x86 decisions is addressable behind an
  adapter, because the same function both selects and encodes (`F-03`–`F-07`).
- **Risk.** A fork would re-introduce the exact implicit decisions the FMP exists
  to forbid, and the fork would have to track an external project's churn.
- **Verdict.** Rejected. Evidence: `90_boundary_audit.md` §3, `91_reuse_matrix.md`,
  `ADR-0001`.

### F.2 Route B — LLVM MC / TableGen centre

- **Coverage.** LLVM's encoding knowledge is the broadest available, and it is
  already our oracle.
- **Coupling.** Reusing MC components would import `MCAssembler` relaxation and
  assembler policy, which are precisely the layout choices INV-04 forbids. The
  internal boundary between relaxation and emission is **unverified** here
  (`90_boundary_audit.md` §8), so a "thin adapter" claim cannot be substantiated.
- **Build cost.** A stable subset would still need a self-owned definition format
  to pin identity and digest; that is most of Route C's work with an additional
  external dependency.
- **Verdict.** Rejected as a runtime route. Retained as oracle and knowledge
  source. Note that the rejection does **not** rest on "LLVM is too big"; it rests
  on the unverified policy boundary and the forbidden relaxation authority.

### F.3 Route C — self-owned minimal kernel + external knowledge

- **Decision boundary.** Every byte-affecting choice is `form_id` or a typed
  operand; the kernel only looks up, checks, and writes (`01_contract.md` §7).
- **Cost.** Reimplementation is real but bounded: 632 + 185 + 24 forms, 44 `EC`
  rows, one fixup model. The audit already names where to get the knowledge
  (RV64 spec table, Arm MRS).
- **Verifiability.** Two independent sources per positive vector (`AGENTS.md`
  rule 5): our materializer plus `llvm-mc` (or a recorded manual derivation)
  compared byte-for-byte.
- **Risk.** ISA widening can silently import implicit decisions. Mitigation: one
  vertical slice at a time, a new ADR per family, and a rejection fixture for
  every excluded family (`ADR-0094` is the template).
- **Verdict.** Recommended and confirmed. Evidence: `ADR-0001`,
  `90_boundary_audit.md` §5–§6, `91_reuse_matrix.md` §"What the classes mean".

### F.4 Recommendation reason

Route C is the only route where the materializer's authority is structurally
limited: it has no selector, no relaxation pass, and no expression evaluator to
misuse. Routes A and B both place a planning decision inside code we would have to
trust; Route C places it in the plan, where a test can reject it.

---

## G. FMP v0 Final Scope

### G.1 v0 must support

| Area | Frozen content | Evidence |
|---|---|---|
| Plan envelope | `fmp/0.1`, closed objects, integer-only, canonical JSON | `01_contract.md` §3, §12 |
| Target identity | family, variant, execution mode, extension set, endianness, address width | `01_contract.md` §4; `N06` |
| Definition identity | namespace, version, digest; mismatch rejected | `01_contract.md` §5; `N10` |
| Instructions | exact `form_id`, typed operands, `expected_size`, optional `expected_digest` | `01_contract.md` §7–§8 |
| Layout | sections, fragments, offsets, declared size; no padding/relax/reorder | `01_contract.md` §6; `N09`, `N11`, `N22` |
| Symbols | id, name, kind, binding, section/offset | `01_contract.md` §9 |
| Fixups | descriptor, target, addend, PC rule, transform, range, mode, pair | `03_fixup_model.md`; `AC-05` |
| Output | Level 0 bytes + normalized fixup records + fingerprint; opt-in Level 1 sections + declared symbols with the same records | `01_contract.md` §11.1–§11.2 |
| Errors | 44 active codes, stable identity, sorted reporting | `04_errors.md` §1–§2 |
| Determinism | replay across repetition, process, serialization, host, definition drift | `EXP-0033` |

### G.2 v0 explicitly does not support

| Feature | Disposition | Evidence |
|---|---|---|
| Level 1 object output (`artifact: sections`) | supported (`ADR-0096`): section split in `section_order`; no container | `X86-P71`; `01_contract.md` §11.2 |
| Symbol table (`include_symbol_table: true`) | supported at Level 1 only, in `symbol_order` or `symbol_id` order; no synthesized symbols | `X86-P71`; `N24i`; `01_contract.md` §11.2 |
| `emit_fixups: false` | rejected | `E-VERSION-001` |
| Non-default `fixup_record_order` | rejected | `E-VERSION-001` |
| Non-empty `feature_constraints` | rejected | `E-VERSION-001` |
| `section_relative` fixup target | rejected `E-VERSION-001`; no measured meaning in v0 | `03_fixup_model.md` §2.1; `N24j`; `ADR-0123` |
| `lock`/`rep`/segment prefixes | absent; multiple encodings | `ADR-0094`, `EC-10` |
| AArch64 `mov` alias | absent | `ADR-0094`, `EC-16` |
| AArch64 `cbz`/`cbnz`/`tbz`/`tbnz` | absent | `ADR-0094`, `EC-18` |
| RV64 `call`/`ret`/`jr`/`j` aliases, and `c.j`/`c.jalr` | absent; `jal` and `jalr` ship as separate forms (`ADR-0099`) | `ADR-0094`, `ADR-0099`, `EC-23` |
| RV64 `fence` masks | absent | `ADR-0094`, `EC-24` |
| RV64 CSR immediate form | absent | `ADR-0094`, `EC-25` |
| RV64 `aq`/`rl` | absent | `ADR-0094`, `EC-26` |
| Floating point / vector beyond the x86 SSE/VEX/EVEX slices | absent | `02_encoding_choices.md` |
| Alignment/padding requests | structurally absent | `E-LAYOUT-005` unreachable |
| Macros, includes, expressions | forbidden by grammar | `INV-06`, `N23a` |

### G.3 Extension points (must not break old plans)

1. **New `form_id`** in a new definition `version`; the old version keeps its
   digest, so an old plan still resolves.
2. **New definition `version`** with a new digest; a plan pins both, so no silent
   adoption.
3. **New `format_version`** for a new envelope; `fmp/0.1` never grows an `x_*`
   field (`OD-05`, `ADR-0031`).
4. **Level 1 opt-in** through `artifact: sections`, implemented in `ADR-0096`;
   it adds serialization, never changes Level 0 bytes.
5. **New error code** must be declared in `04_errors.md` with a trigger, detail
   keys, and a negative test; retired codes stay documented as retired.

---

## H. Implementation Roadmap

### H.1 Module order

The order is fixed: close the evidence gate before adding surface.

| Step | Module | Scope | Exit gate |
|---|---|---|---|
| M1 | Error-coverage gate | Add end-to-end fixtures for the eight reachable uncovered codes; keep the two JSON-layer-only codes as unit tests | **closed 2026-11-08**: `N24a`–`N24h` land, `04_errors.md` §2.4 has no "reachable, no fixture" group, and `cargo test -p fmp-cli --test fixtures` is green |
| M2 | Oracle rerun harness | One command that re-derives every `*.expected.bin` from `llvm-mc` (or records a manual derivation) and diffs | **closed 2026-11-08; the recovery backlog closed 2026-11-09**: `tools/oracle/rerun.py` resolves each input by `input_sha256`, re-runs the recorded command and compares bytes. The 29 `input-not-stored` records (20 AArch64 + 9 RV64) were recovered by content and experiment listings and re-pinned by `input_sha256`, so the harness now re-derives `122/128` positive records with `6` `manual-derivation` skips, `0` `input-not-stored` and `0` failed; `--strict` still fails on those six intended skips (`tools/oracle/README.md`) |
| M3 | Level 1 object writer | `artifact: sections` + `include_symbol_table`; sections, symbols and relocation records from the plan, no relaxation and no container format (Level 2) | **closed 2026-11-08**: `X86-P71` and `EXP-0100` validate the §11.2 envelope; Level 0 bytes are unchanged (`.text` is the same 43-byte oracle image); `N24h`/`N24i` keep `E-VERSION-001` reachable |
| M4 | Planner boundary/API | Export the plan builder as a library boundary, with the same closed-object discipline | **closed 2026-11-08**: `ADR-0097` and `09_planner_api.md` define `fmp-plan`, a total closed builder over `fmp-model` with no validator and no planner authority. `prototype/crates/fmp-plan` is implemented and `cargo tree -p fmp-plan` shows `fmp-model` as its only workspace dependency; `fmp-validate`, `fmp-materialize` and the `fmp` binary have no path to it outside the `fmp-cli` test target. The gate is `planner_api.rs` (ten tests): 128 positive and 605 `materialize`-phase negative parity at the M4 close, from-scratch authoring for `X86-P1`/`A64-P2`/`RV-P1`/`X86-P71`, closed key sets, optional-member and enum-spelling round trips, fixed-point re-emission, structural exclusion of the then-six `read`-phase negatives, determinism and typed `Unrepresentable` failures. A mutation check (removing `expected_digest`) fails the gate |
| M5 | Coverage widening | One ISA family per ADR, each with a rejection fixture for its absent variant | **closed 2026-11-09**: seven slices under `ADR-0104`-`ADR-0110`, plus the scope reconciliation `ADR-0111`. `ADR-0104` adds the RV64 B-type mnemonics (`definitions/rv64/0.5.0.json`, 15 forms); `ADR-0105`/`ADR-0106` add the SSE `%rip` rows and the `xmm8`-`xmm15` fixed-base rows (`0.69.0`, `0.70.0`); `ADR-0107` adds the `addr32` `%rip` rows (`0.71.0`); `ADR-0108` the legacy/VEX SSE indexed rows (`0.72.0`); `ADR-0109` the indexed byte `mov` (`0.73.0`); `ADR-0110` the `29 /r` register/register `sub` (`0.74.0`). Every slice has a positive fixture with an independent oracle and an `E-FORM-001` fixture for the row or sibling it leaves out; the x86 table ends at 564 forms and the corpus is 121 positives and 586 negatives |
| M6 | Coverage round 2 | Seven additive integer-surface slices, one ADR each, plus a closure; no contract change | **closed 2026-11-10**: seven slices under `ADR-0113`-`ADR-0119`, plus the closure `ADR-0120`. `ADR-0113` adds the x86 ALU register/register rows (`0.75.0`), `ADR-0114` the ALU immediate rows (`0.76.0`), `ADR-0115` the `mov` immediate rows (`0.77.0`), `ADR-0116` the `sub` memory directions (`0.78.0`), `ADR-0117` the RV64 load/store widths (`rv64/0.6.0`), `ADR-0118` AArch64 `adr` (`aarch64/0.19.0`) and `ADR-0119` `mul`/`csel` (`0.20.0`). The round lands 82 rows and 841 forms (x86 632, AArch64 185, RV64 24) across 104 documents, with 128 positives and 611 negatives at the M6 close; the two differences from the plan (`S1` 15 not 16, `S3` 5 not 6) are measured corrections recorded in their ADRs |

### H.2 Test gates

Every step must keep all of these green:

- `python tools/check_ids.py`
- `python tools/check_definition.py` (when `definitions/` changes)
- `python tools/check_rv64_source.py`
- `cargo test --workspace` from `prototype/`
- `cargo fmt --all -- --check` from `prototype/`
- CI on Ubuntu, macOS, and Windows with the pinned toolchain

M1's own gate is stronger: a code is "covered" only when a fixture asserts the
exact code, path, and detail keys, matching the existing negative-fixture shape.

### H.3 Main risks and responses

| Risk | Response |
|---|---|
| Widening adds an implicit decision | One family per ADR; a rejection fixture for every absent variant |
| Level 1 re-introduces layout policy | Derive all offsets from the plan; no relaxation pass; byte-diff Level 0 against Level 1 payload |
| Oracle drift | Pin tool version and command in `*.oracle.json`; M2 re-derives and diffs |
| Definition churn breaks old plans | Immutable versioned files plus digest; never edit a released table |
| Error registry drifts from code | M1 gate; `check_definition.py` plus fixture coverage |

### H.4 Blockers

None for v0 close-out. The only true unknown that would change the route is the
LLVM relaxation boundary; it does not need to be resolved while LLVM stays an
oracle. If a future step proposes linking MC, that step must first produce the
source evidence `90_boundary_audit.md` §8 currently lacks.

---

## Appendix — Research Questions

### Q1. What is the minimal sufficient frozen information?

The field set is `01_contract.md` §3–§12. The load-bearing fields, each with a
counterexample: `form_id` (a mnemonic admits several sizes), `target_type` (a
shared slot type truncates `c.addi`'s `xd`), `payload` shape (two writers for one
field), `expected_size` (definition drift changes length), `expected_digest`
(same-length defect), `section_order`/`fixup_record_order` (hash order changes
bytes), and `pc_reference_rule`/`value_transform` (the same addend means different
things). Optional fields are optional because they cannot change output.

### Q2. How is `form_id` identity defined and kept stable?

By the definition artifact, not by an internal number. The plan pins namespace,
version, and digest; the id is `<family>:<mnemonic>/<variant>[/<family>]`. A rename
moves the digest, so the plan fails before lookup; a wrong digest that still
reaches lookup fails `E-FORM-001`. There is no alias table. `N01` and `EXP-R5`
confirm both halves.

### Q3. When does the materializer still choose?

It never chooses a byte-affecting value. The residual "choices" are checks, not
selectors: `target_type` guards legality, `modifiers` guard a permitted variation,
and the fixup mode selects between "write computed value" and "write zero and
record", both already named by the plan. A plan that leaves any of these open is
rejected.

### Q4. Where is the line between encoding rules and plan data?

Definitions own the rule (template, slots, placements, ranges, per-form
constraints). The plan owns the decision (which form, which operands, which target,
which fixup). If a value is needed to pick a form, the form is wrong, because that
is a value-driven choice (`INV-02`). `07_definition_format.md` §5 lists what the
definition deliberately does not carry.

### Q5. Can XirAsm-lib be the materialization core?

No. x86 is class D end to end; AArch64 has no backend; RV64 `encodeRaw` is a
narrow B whose identity is not version-stable. The library is usable as an oracle
and as a knowledge source, never as a runtime dependency (`91_reuse_matrix.md`,
`ADR-0001`).

### Q6. In what form should LLVM participate?

As an oracle and knowledge source only. Not as extracted encoding tables (that
would make LLVM's internal model our contract), and not as MC components (that
imports relaxation policy). The rejection is evidence-based: the relaxation
boundary is unverified, and the decision authority cannot be isolated.

### Q7. Can fixups be expressed uniformly?

The envelope yes: descriptor, target, addend, PC rule, transform, range, mode,
pair. The semantics no: register numbering, field placement, page-bit splitting,
and 1:N pairing differ by ISA. The Level 0 record shape is uniform precisely
because it carries the target-specific pieces as data.

### Q8. How is "does not secretly plan" proven?

By executable evidence, not a diagram: `form_id` exact lookup, no fallback paths,
619 negative plans compared by exact diagnostic, replay tests across three hosts,
and a definition-drift test that is loud. A plan that asks for a decision gets a
rejection; a byte that would require a choice cannot be produced.

### Q9. What is the minimal effective v0 boundary?

Level 0 is the default: bytes plus normalized fixup records, three ISAs, one
vertical slice each, strict rejection, deterministic replay. Level 1 is an opt-in
projection of the same validated plan (`ADR-0096`), not a second encoder.
Everything else is deferred and listed in §G.2. The boundary is minimal because
each excluded feature would add layout or selection authority without adding a
contract question.

### Q10. How do future extensions avoid breaking old plans?

Immutable versioned definitions, digest pinning, exact `format_version`, closed
objects, and no silent alias. A new decision is a new definition version or a new
format version; an old plan remains valid only against the artifact it names. New
error codes are additive and documented; retired codes stay documented as retired.

---

## Documentation defects corrected in Phase 5

These were stale statements, not contract changes; they are listed so the record
shows what moved.

| File | Defect | Correction |
|---|---|---|
| `02_encoding_choices.md` | x86 slice said "four hundred and thirteen forms" | `509` forms, measured from `definitions/x86_64/0.65.0.json` |
| `01_contract.md` §7.1 | said the v0 tables were only the three `0.1.0` files | now points at the actual latest tables |
| `01_contract.md` §7 | "The plan MUST carry a hash" contradicted `expected_digest` being optional | rewritten to state the digest is required when a same-length defect must be detectable |
| `04_errors.md` §2 | `E-PLAN-003`, `E-TARGET-001`, `E-PLAN-004`, `E-PLAN-005` "Related test" cells were stale | pointed at the actual fixtures/unit tests; §2.4 added for the M1 list |
| `schema/examples/rv64-caddi.example.json` | nonexistent form/slot names and an all-zero digest | real `riscv:c.addi/rd-imm6`, `riscv.xreg`/`xreg`, `riscv.imm`/`imm6`, `0.2.0` and its digest |
| `schema/examples/aarch64-adrp-add.example.json` | nonexistent form/slot names, retired kinds, all-zero digest | real `aarch64:adrp/x64-imm21` and `aarch64:add/x64-imm12-lsl0`, `0.17.0` and its digest, explicit Level 1 wording |
| `schema/examples/x86-mov-r64-r64.example.json` | stale note | corrected to the current contract wording |
| `schema/examples/README.md` | cited stale `OD-07`/`encoding_choices` | points at the current contract sections |
| `README.md` | oracle "planned"; "examples validate" | states the oracle as implemented and the examples as illustrative |
| `06_validation_matrix.md` | AC-10 `planned` | AC-10 `satisfied` by §H |
| `01_contract.md` §11 | `symbol_order` and the Level 1 envelope were `draft`/undefined | `symbol_order` frozen with a counterexample; §11.2 defines the Level 1 artifact (`ADR-0096`) |
| `04_errors.md` §2.4 | `N24h` still named the accepted `artifact: sections` | `N24h` repointed to `emit_fixups: false`; `N24i` added for the Level 0 symbol-table gate |
