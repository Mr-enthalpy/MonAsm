# Validation Matrix

Status: **draft**. Fixtures and results are filled in Phases 3–4. This file is
the canonical registry for `N*`, `EXP-R*`, and `AC-*`.

## 1. Negative tests (`N*`)

Every negative test must produce a registry code, not a generic failure. Fixture
naming: `fixtures/<isa>/negative/N0X-<slug>.fmp.json`.

| ID | Input condition | Expected | Code | ISAs | Fixture | Status |
|---|---|---|---|---|---|---|
| N01 | Plan names a form that leaves a byte-affecting decision open (`x86:mov/r64-r64`, `x86:add/rm64-imm`), a form missing a required component (`x86:mov/rm-r64` without `/legacy`), a renamed variant, or names a variant the definition does not contain | Reject, never append a default variant or match a near neighbour | E-FORM-001 | x86, aarch64, rv64 | `x86_64/negative/N01-absent-form.fmp.json`, `aarch64/negative/N01-absent-scaled-form.fmp.json`, `aarch64/negative/N01d-absent-movz-lane.fmp.json`, `aarch64/negative/N01e-absent-extend-form.fmp.json`, `aarch64/negative/N01f-absent-sub-ext.fmp.json`, `rv64/negative/N01c-caddi-against-0.1.0.fmp.json` | x86, aarch64 and rv64 passing |
| N02 | Operand register class does not match the form | Reject | E-OPERAND-001 | x86, aarch64, rv64 | `x86_64/negative/N02-operand-kind-mismatch.fmp.json`, `aarch64/negative/N02b-w-source-in-shift-form.fmp.json` | x86 and aarch64 passing |
| N03 | Immediate exceeds the field's range | Reject | E-RANGE-001 | x86, aarch64, rv64 | `x86_64/negative/N03-imm8-out-of-range.fmp.json`, `aarch64/negative/N03-imm12-out-of-range.fmp.json`, `aarch64/negative/N03-cond-out-of-range.fmp.json`, `aarch64/negative/N03-imm6-out-of-range.fmp.json`, `aarch64/negative/N03-imm3-out-of-range.fmp.json` | x86 and aarch64 passing |
| N04 | Branch displacement exceeds the form's range | Reject, never expand | E-RANGE-002 / E-FIXUP-003 | x86, aarch64, rv64 | `x86_64/negative/N04a-rel8-out-of-range.fmp.json`, `N04b-rel32-absolute-out-of-range.fmp.json`, `aarch64/negative/N04c-bcond-imm19-out-of-range.fmp.json` | x86 and aarch64 passing |
| N05 | `expected_size` disagrees with the encoded length | Reject | E-SIZE-001 / E-LAYOUT-003 | x86, aarch64, rv64 | `x86_64/negative/N05-expected-size-mismatch.fmp.json` | x86 passing |
| N06 | Form requires a disabled target extension | Reject | E-TARGET-003 | rv64 (C), x86 (AVX), aarch64 (optional feature) | none | not applicable to x86 v0 (no extension-gated form); see `04_errors.md` §2.3 |
| N07 | Fixup kind is incompatible with the field | Reject | E-FIXUP-001 | x86, aarch64, rv64 | `x86_64/negative/N07-fixup-partial-field.fmp.json` | x86 passing |
| N08 | Reference names a `symbol_id` absent from `symbols[]`; or `resolve_in_place` is asked to patch a symbol that exists but has no address | Reject the identity error in every mode; reject only the mode that needs an address | E-SYMBOL-001 / E-FIXUP-002 | x86, aarch64, rv64 | `x86_64/negative/N08-undeclared-symbol.fmp.json`, `N08b-resolve-undefined-symbol.fmp.json`, `N08c-absolute-pcrel-without-base.fmp.json` | x86 passing |
| N09 | Two layout fragments overlap | Reject | E-LAYOUT-001 | all (layout is ISA-independent) | `x86_64/negative/N09-overlapping-fragments.fmp.json` | x86 passing |
| N10 | Definition digest does not match | Reject | E-DEF-001 | all | `x86_64/negative/N10-definition-digest-mismatch.fmp.json` | x86 passing |
| N11 | Plan implies implicit alignment or padding | Reject | E-LAYOUT-002 / E-LAYOUT-005 | all | `x86_64/negative/N11-fragment-gap.fmp.json` | x86 passing (`E-LAYOUT-002`; `E-LAYOUT-005` unreachable in v0, `04_errors.md` §2.3) |
| N12 | Associated relocation pair is incomplete or inconsistent: no `hi`, more than one `hi`, no `lo`, a target mismatch, or a `pair_role` with no `pair_group` | Reject | E-FIXUP-007 | aarch64 (`adrp`+`lo12`), rv64 (`auipc`+`lo12`) | `aarch64/negative/N12a-pair-without-lo.fmp.json` | aarch64 passing (two `hi`, no `lo`); not applicable to x86 v0 (single-site `rel32`) |
| N13 | `expected_digest` is present and the emitted bytes hash to a different value | Reject, never re-encode to match | E-BYTE-001 | x86, aarch64, rv64 | `x86_64/negative/N13-expected-digest-mismatch.fmp.json` | x86 passing |
| N14 | Operand value does not fit the slot's encoded field: `r9` in a 3-bit `ModRM` field, or `x32` in a 5-bit AArch64 register field | Reject, never truncate to another register | E-OPERAND-004 | x86, aarch64 | `x86_64/negative/N14-register-wider-than-field.fmp.json`, `aarch64/negative/N14-register-wider-than-field.fmp.json` | x86 and aarch64 passing |
| N15 | Operand payload is a composite memory operand (`{"mem": {"base": …, "disp": …}}`), not one of the four `fmp/0.1` shapes | Reject at read time, never split it into operands | E-OPERAND-003 | all | `rv64/negative/N15-composite-memory-payload.fmp.json` | rv64 passing |
| N16 | Operand value is inside the slot's field range but excluded by the form (`c.addi` zero immediate, `c.addi` zero destination, the extended-register `imm3` values `5`–`7`) | Reject, never encode the HINT or the unallocated word the bytes would mean | E-RANGE-004 | rv64, aarch64 | `rv64/negative/N16a-caddi-imm-zero.fmp.json`, `rv64/negative/N16b-caddi-rd-zero.fmp.json`, `aarch64/negative/N16c-imm3-excluded.fmp.json` | rv64 and aarch64 passing |
| N17 | RV64 pair half is inconsistent: `N17a` a `pcrel_lo12` low half with a non-zero `addend`, `N17b` a `pcrel_hi` fixup with no `pair_role: lo`, `N17c` a `pcrel_hi` low half in a different section than its `hi` | Reject, never fold the addend in, fall back to `pcrel_begin`, or measure across sections | E-FIXUP-009 / E-FIXUP-007 | rv64 | `rv64/negative/N17a-lo12-addend-nonzero.fmp.json`, `rv64/negative/N17b-pcrel-hi-without-lo-role.fmp.json`, `rv64/negative/N17c-lo-in-other-section.fmp.json` | rv64 passing |
| N18 | Operand value is legal as a *literal* for the instruction but not inside the named form's field: `0x1000` on `add/x64-imm12-lsl0`, `0x123000` on `add/x64-imm12-lsl12`, or `0x12340000` on `movz/x64-imm16-lsl16` | Reject, never switch to the other form or pre-scale the operand | E-RANGE-001 | aarch64 | `aarch64/negative/N18a-no-form-switch.fmp.json`, `aarch64/negative/N18b-operand-is-field-content.fmp.json`, `aarch64/negative/N18c-movz-pre-scaled-literal.fmp.json` | aarch64 passing |
| N19 | A byte-affecting variation is stated as an operand `modifiers` entry the slot does not permit (`{"name": "lsl", "value": 3}` on `aarch64:add/x64-x64-x64-lsl0`) | Reject, never emit the word the unshifted form would produce | E-OPERAND-003 | aarch64 | `aarch64/negative/N19-modifier-is-not-a-carrier.fmp.json` | aarch64 passing |

N13's counterexample is `EXP-0002` W2: a same-length encoder defect turns
`48 89 d8` (`mov rax, rbx`) into `49 89 d8` (`mov r8, rbx`), both 3 bytes and
both legal. `expected_size` cannot see it; only the digest can. The test must
also confirm the materializer does **not** attempt a repair (W4: a plan whose
immediate is edited must be rejected, not re-encoded around).

N14 is the field-width failure, not the class failure. `r9` is a legal
`x86.gpr64`, so `E-OPERAND-001` does not apply; the v0 `ModRM` field is 3 bits
and the `REX` byte is pinned, so the value simply does not fit. `EXP-0004` §3
measured what truncation would do: `48 89 c8` decodes as `movq %rcx, %rax`, a
move of a different register. The AArch64 fixture is the same shape with a 5-bit
field (`x32` would truncate to `x0`); an RV64 case would have the same shape, but
no such fixture exists yet.

N18 is the A64-P2 pair: the operand is inside the *literal's* legal set but not
inside the named form's field. `llvm-mc` accepts `#0x1000` and silently emits the
`sh=1` form (`EV-26`, `EXP-0013` §2); the materializer must reject it on `-lsl0`
(`N18a`, `E-RANGE-001`), because choosing the form from the value is `INV-02`.
The converse spelling is `N18b`: naming `-lsl12` and passing `0x123000` is also
`E-RANGE-001`, because the operand is `imm12` field content (0…4095) and the
`<< 12` belongs to the form, not to the slot. Together they pin "the slot is the
field" (`07_definition_format.md` §8.3) on both sides.

Applicability notes: N12 is not applicable to x86-64 in v0 because the selected
x86 slice uses a single-site `rel32`; if an x86 pair case is added, the row must
be revisited.

N01 was written against `encoding_choices`. After ADR-0004 the decision is
carried by `form_id`, so the directive's N01 input ("missing required encoding
choice") is exactly a plan whose form under-specifies the encoding. The test must
also confirm the id is not repaired by appending a width, direction or encoding
family suffix, and that a renamed variant fails instead of matching its
neighbour (`OD-04`).

N08 splits by repair path: a `symbol_id` that names no entry in `symbols[]` is
`E-SYMBOL-001` (the plan is internally inconsistent), while a symbol that exists
but has no address and is asked to resolve in place is `E-FIXUP-002`. A plan that
wants a record instead is legal and emits one (`OD-02`).

### Phase 1 evidence for N03 and N04

The audit produced both the positive restraint and the negative counterexample
from a built reference implementation (`90_boundary_audit.md` F-06, F-10, F-11;
raw commands in `research/evidence/experiments/EXP-0001-xirasm-boundary-probes.md`):

| Behaviour | Reference implementation | What our materializer must do instead |
|---|---|---|
| RISC-V immediate out of field range | rejects (`addi a0,a1,2048`) | same: `E-RANGE-001` |
| RISC-V branch out of range | rejects (`beq ...,0x1008`, `c.j 0x800`) | same: `E-RANGE-002` |
| x86 label branch out of `rel8` | rejects (`does not fit the signed 8-bit displacement`) | same: `E-FIXUP-003` |
| x86 numeric `short` branch out of `rel8` | emits `eb 80` for target `0x82` — **silently truncated** | reject: `E-RANGE-002`. This is the concrete failure N04 exists to prevent. |
| x86 unqualified branch | auto-shortens to `rel8`, promotes to `rel32` when far | never shorten, never promote: `INV-02`, `INV-04` |

## 2. Determinism experiments (`EXP-R*`)

| ID | Experiment | Method | Observable | Status |
|---|---|---|---|---|
| EXP-R1 | Repeated execution | Materialize the same plan 100 times in one process; compare bytes, fixup records, fingerprints | Byte equality | planned |
| EXP-R2 | Cross-process | Run the CLI in N independent processes; compare hashes of artifacts | Hash equality | planned |
| EXP-R3 | Different host environment | Run on a second OS/compiler/host where available; otherwise mark unverified | Hash equality or explicit `unverified` | planned |
| EXP-R4 | Serialization replay | Serialize → parse → materialize; compare with direct materialization | Byte equality | planned |
| EXP-R5 | Definition perturbation | Swap the definition for a modified one; expect E-DEF-001, not silent bytes | Error identity | planned |
| EXP-R6 | Negative determinism | Repeat an invalid plan; compare error identity (code+path+detail keys), ignoring `message` | Identity equality | planned |

EXP-R3 must not be claimed unless actually executed. "Not tested on a second
host" is the honest result.

## 3. Acceptance criteria (`AC-*`)

| ID | Requirement | Evidence form | Status |
|---|---|---|---|
| AC-01 | Contract complete enough to guide implementation | `01_contract.md` with no `TBD` on fields used by the three slices | **clear for the x86 and AArch64 slices**: OD-02, OD-04, OD-07 and OD-09 settled; the fields those tables use have frozen rows in `01_contract.md`, `03_fixup_model.md` and `07_definition_format.md`. The RV64 surface has no table yet (`OD-12` settles its source, ADR-0007), so AC-01 stays open until `definitions/rv64/` lands |
| AC-02 | Key fields justified | Each frozen field cites a counterexample or source evidence | in progress — every field the x86 slice uses now cites one (OD-02/04/09); the remaining `draft` fields are optional or Level 1 |
| AC-03 | Three-ISA vertical slices | One closed loop per ISA: plan → validate → encode → fixup → oracle compare | planned |
| AC-04 | Encoding ambiguity proven absent | x86 `imm8`/`imm32`, `rel8`/`rel32`, `89`/`8B` and RV64 `c.*` vs standard are distinct `form_id`s; per-`EC` negative test per `02_encoding_choices.md`, "Validation obligation" | planned |
| AC-05 | Fixups validated | x86 `rel32`; AArch64 `adrp`+`:lo12:`; RV64 `auipc`+`lo12` or B-type scatter | planned — the mode decision is settled (OD-02: two modes, one effect each), so the fixtures can be written |
| AC-06 | Strict rejection | All applicable N01–N13 with recorded codes | planned |
| AC-07 | Deterministic replay | EXP-R1, EXP-R2, EXP-R4, EXP-R5 | planned |
| AC-08 | Reuse boundary backed by source evidence | `90_boundary_audit.md` with revision, file, symbol, line range | **done** for XirAsm; LLVM internals deferred (see audit §8) |
| AC-09 | Unresolved problems stated | `05_open_decisions.md` with blocking impact, no "later" hand-waving | in progress |
| AC-10 | Executable next step | Final report §H: modules, order, gates, blockers | planned |

## 4. Positive vectors

Each vector needs **two independent sources**: our materializer, and an oracle
(`llvm-mc` bytes, binutils, or a manual derivation recorded in
`research/evidence/experiments/`). The oracle's exact version must be recorded.

### x86-64 (directive §6.1)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| X86-P1 | Register-to-register transfer | `x86:mov/rm-r64/legacy` (`REX.W 89 /r`) and `x86:mov/r64-rm/legacy` (`REX.W 8B /r`) | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P2 | Arithmetic with immediate | `x86:add/rm64-imm8/legacy` and `x86:add/rm64-imm32/legacy` as separate forms | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P3 | Same operation, different legal encodings | `x86:add/rax-imm32/legacy` vs `x86:add/rm64-imm32/legacy`; `x86:mov/rm-r64` vs `x86:mov/r64-rm` | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P4 | Displacement width | `mov rax, [rbp-8]` (disp8) vs (disp32) | llvm-mc | deferred: needs one `form_id` per ModRM mod shape, measured (`ADR-0008`, `OD-13`) |
| X86-P5 | Prefix rules | 16-bit operand with `0x66`; REX + high-byte rejection | llvm-mc | deferred: no `0x66`/high-byte form in the v0 surface (`OD-10`) |
| X86-P6 | RIP-relative reference | `mov rax, [rip+disp32]` with a fixup | llvm-mc + readelf | deferred: needs a `rip_relative` `form_id`, measured (`ADR-0008`, `OD-13`) |
| X86-P7 | Short vs near branch | `x86:jmp/rel8/legacy` and `x86:jmp/rel32/legacy` as explicit plans | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P8 | External branch fixup | `x86:jmp/rel32/legacy` to an undefined symbol with `emit_relocation`, record emitted. `call rel32` is not in the v0 surface (`OD-10`); its descriptor is identical, so the record shape is exercised without adding a form | llvm-mc + llvm-readobj | x86 passing (`EXP-0005`) |
| X86-P9 | Explicit encoding family | SSE vs VEX vs EVEX for one operation | llvm-mc | deferred (OD-10) |

Oracle note for X86-P7, measured 2026-11-04: llvm-mc does not accept a bare
numeric branch target (`jmp 0x12`, `0x7f`, `0x80`, `0x1000`, `5` all emit
`e9 00 00 00 00` under `-filetype=obj`). Use a label or a `.+N` expression:
`jmp .+0x81` → `eb 7f`, `jmp .+0x82` → `e9 7d 00 00 00`. The disassembler prints
the displacement, not the resolved target, so the vector is compared as bytes and
the target is computed from the plan.

Definition anchor for X86-P1–P8, measured 2026-11-04: the seven forms live in
`definitions/x86_64/0.1.0.json` (digest
`sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad`), and
`EXP-0004` decodes 223 plan-derived byte strings with `llvm-mc` to confirm every
row's field placement.

X86-P1, P2, P3, P7 and P8 have fixtures under `fixtures/x86_64/positive/` and a
recorded oracle in `EXP-0005`; the fixture gate compares their bytes with the
oracle's, never with the materializer's own expectation.

X86-P4, P5 and P6 are **deferred, not omitted**. P4 and P6 need memory
addressing, and `ADR-0008` settled the representation: it is one operand per
encoded field (`base`, `disp`, `index`, `scale`), never a `{mem: …}` payload,
because the encoding form changes with the operand values. `movq 8(%rcx), %rax`
is `48 8b 41 08` (mod=01), `movq 4096(%rcx), %rax` is
`48 8b 81 00 10 00 00` (mod=10), and `movq (%rbp), %rax` is `48 8b 45 00`
(mod=01, because mod=00 with `r/m = 101` is RIP-relative). An encoder that
picked mod from the displacement would select an encoding form (`INV-02`), so
the slice needs one `form_id` per ModRM mod / SIB shape, enumerated and measured
before it lands. P5 is a different gap: the `0x66` prefix and the high-byte
register rule are absent from the v0 surface (`OD-10`). The rows return when
that definition slice lands.


### AArch64 (directive §6.2)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| A64-P1 | Register arithmetic | `add x0, x1, x2` (`shifted-register`, pinned `LSL #0`) | llvm-mc | **passing** — `aarch64/positive/A64-P1-add-register` |
| A64-P2 | Immediate arithmetic | `add x0, x1, #imm12` and the `LSL #12` variant as two forms | llvm-mc | **passing** — `add/x64-imm12-lsl0` (imm 0 and 4095) in `A64-P2-add-imm12`; `add/x64-imm12-lsl12` (field content 1, 291, 4095, 0) in `A64-P2-add-imm12-lsl12`; `N18a`/`N18b` reject the form-switching spellings |
| A64-P3 | Load/store addressing | unsigned-offset vs pre/post-index vs unscaled as distinct forms | llvm-mc | **passing** — `A64-P3-ldst-addressing` (six instructions, five forms: `imm12` at 0 and 4095, pre-index +8, post-index −8, `ldur` at −256, store at 0) through `aarch64:ldr/x64-base-imm12`, `ldr/x64-base-imm9-pre`, `ldr/x64-base-imm9-post`, `ldur/x64-base-imm9` and `str/x64-base-imm12`; `N03` rejects `disp = 4096` on `imm12` and `disp = −257` on `imm9`; `N01b` rejects the absent register-offset id |
| A64-P4 | Conditional branch | `b.eq` imm19 | llvm-mc | **passing** — `A64-P4-b-cond` (`b.eq` +4, `b.ne` −4, `b.gt` −8) through `aarch64:b.cond/imm19` with the condition as a `cond4` operand; `N03` rejects `cond = 16` and `N04c` rejects an out-of-range `imm19` |
| A64-P5 | Unconditional branch/call | `bl` imm26 | llvm-mc + ld.lld | **passing** — `A64-P5-bl-local-symbol` (+4 and −4) |
| A64-P6 | PC-relative pair | `adrp` + `add #:lo12:` with `pair_group` | llvm-mc + ld.lld + llvm-readobj | **passing** — `A64-P6-adrp-lo12-pair` |
| A64-P7 | Scattered/scaled field | `movz` lane selection as four forms, `imm16` scaled by `16·hw` | llvm-mc | **passing** — `A64-P7-movz-lane` (five instructions, four forms: `hw` 0, 1, 2 and 3, with the same `imm16 = 4660` on the first two and 65535/0 at the ends) through `aarch64:movz/x64-imm16-lsl0` … `-lsl48`; `N18c` rejects a pre-scaled literal on `-lsl16` and `N01d` rejects the absent `lsl #8` lane |
| A64-P8 | Target-specific modifier | shift modifier on a register operand: the keyword is the form, `imm6` is the amount (`0…63`) | llvm-mc | **passing** — `A64-P8-shift-modifier` (six instructions, three forms: `lsl #3`, `lsr #7`, `asr #63`, `lsl #63`, `lsl #0`, `lsr #0`) through `aarch64:add/x64-x64-x64-imm6-lsl` … `-imm6-asr`; `N03-imm6` rejects an amount of 64, `N19` rejects the same shift stated as a `modifiers` entry, and `N01e` rejects the absent extend family |
| A64-P9 | Target-specific modifier | extend modifier on a register operand: the keyword is the form and fixes the source width, `imm3` is the amount (`0…4`, `5…7` excluded) | llvm-mc | **passing** — `A64-P9-extend-modifier` (eight instructions, one per `option`: six `w`-source keywords and two `x`-source keywords, with `imm3` at 0 and 4 on both classes and all three registers distinct in every row) through `aarch64:add/x64-x64-w32-imm3-uxtb` … `-imm3-sxtx`; `N03-imm3` rejects an amount of 8, `N16c` rejects 5 as excluded, `N02b` rejects a `w` operand on a shifted row, and `N01f` rejects the absent `sub`-extended id |

Definition anchor for A64-P1/P2/P3/P4/P5/P6/P7/P8/P9, measured 2026-11-04: the four base
forms live in `definitions/aarch64/0.1.0.json` (digest
`sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e`),
generated from the Arm MRS 2026-06 drop by `EXP-0008`. `0.2.0` adds the fifth,
`aarch64:add/x64-imm12-lsl12` (digest
`sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed`), a
superset of the same four plus a second reading of `ADD_64_addsub_imm` with
`sh = 1`; `0.1.0` is unchanged, which is why `N01` still rejects that id
when a plan names it against `0.1.0`. The `-lsl0`/`-lsl12` suffix names the pinned
`sh`, and neither form rescales the operand (ADR-0011). `0.3.0` adds the sixth,
`aarch64:b.cond/imm19` (digest
`sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb`),
whose `B_only_condbranch` node leaves both the 4-bit condition and the 19-bit
displacement variable; the condition is an operand (`EC-29`, ADR-0012), not
sixteen forms. `0.4.0` adds the five load/store rows (digest
`sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78`), one per
MRS addressing-kind node, with `disp` as field content in 8-byte units (`imm12`)
or signed bytes (`imm9`) (`EC-14`, ADR-0013); `0.5.0` adds the four `movz` rows
(digest `sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e`),
one per `hw` value, with `imm16` as field content (`EC-30`, ADR-0014); `0.6.0`
adds the three shift rows (digest
`sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964`), one
per keyword, with the amount as an `imm6` operand (`EC-31`, ADR-0015); `0.7.0`
adds the eight extend rows (digest
`sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053`), one
per `option` value, with the keyword fixing the source width and the amount as an
`imm3` operand over `0…4` minus the excluded `5…7` (`EC-32`, ADR-0016);
`0.1.0`…`0.6.0` are unchanged.
`llvm-mc` does not resolve AArch64 branch or `adrp` immediates when
they name a symbol, so A64-P5/P6 take their bytes after
`ld.lld --image-base=0 -Ttext=0` has resolved the same `(S, P)` pair; the
relocation kinds were read with `llvm-readobj -r` before linking (see
`fixtures/aarch64/README.md`). A64-P3 and A64-P4 need no linker: A64-P3's operands
are all immediates and A64-P4's three targets are local labels in one section, so
`llvm-mc` resolves both itself and emits no relocations. A64-P7, A64-P8 and A64-P9
need no linker either: their operands are registers or immediates only. The twenty
negative fixtures (`N01` ×5, `N02`, `N03` ×6, `N04c`, `N12a`, `N14`, `N16`, `N18`
×3, `N19`) exercise these tables with exact diagnostic sets.

N18's `movz` case is the same "literal versus field" shape as `add`'s. `hw`
selects the lane, so `imm16` is field content in `0…65535` on every one of the
four rows; `0x12340000` on `-lsl16` is a pre-scaled literal and is
`E-RANGE-001` (`N18c`), not a switch to `-lsl32`. `llvm-mc` is the boundary here:
it rejects `movz x0, #0x12340000` outright ("immediate must be an integer in range
[0, 65535]") and accepts only `lsl #0/#16/#32/#48`, so the four rows are exactly
the four spellings (`EXP-0016` §2, ADR-0014). `N01d` is the other half: an
`lsl #8` lane has no row, so it is `E-FORM-001`, not a zero shift.

N03 and N04 gain their AArch64 cases from `b.cond`, and both are the "in range
but wrong field" shape. `cond = 16` is a legal number for a 4-bit-typed value but
not for a 4-bit field; masking it would give `0x0`, which is `eq` — a branch on
the opposite condition from the one a planner who wrote 16 presumably meant
(`EXP-0014` §2 measures the sixteen values). `imm19 = 262144` is the first value
past the signed 19-bit field, which is why the reachable displacement ends at
`+1048572` rather than `+1 MiB` (`EXP-0014` §3). The fixture states the
displacement as a field value instead of a fixup so the range check is the only
thing under test; the positive vector exercises the fixup path.

N03's load/store cases are the same shape one field over. `imm12` is `0…4095`
field units (the access size is the multiplier) and `imm9` is `−256…255` signed
bytes, so `4096` and `−257` have no encoding; there is no second form to fall
back to, because the kind is already the `form_id` (`EXP-0015` §2, ADR-0013).
`N01b` is the other half: `aarch64:ldr/x64-base-regoff` names an addressing kind
the table does not contain, so it is `E-FORM-001`, not a plan the materializer
silently reinterprets as an unsigned-offset load.

A64-P8 is the modifier case, and it splits into two different readings of one
spelling. `add x0, x1, x2, lsl #3` names a kind (`shift` at 23–22, three keywords
and no numeric spelling — `ror` is rejected and `11` is unallocated) and an amount
(`imm6` at 15–10, `0…63`). The keyword is a form and the amount is field content
(`EC-31`, ADR-0015), which is why `N03-imm6` is `E-RANGE-001` for `64` — there is
no second row to switch to, and no scale to apply. `N19` is the modifier-shaped
failure: the same shift stated as `{"name": "lsl", "value": 3}` on the `-lsl0` row
is `E-OPERAND-003`, because a modifier is a guard and never writes a bit; accepting
it silently would emit the unshifted word and report success. `N01e` is the scope
boundary: the extend family (`add x0, x1, w2, uxtw #3`, `0x8b224c20`) is a
different node with a `w` source operand, so it is `E-FORM-001` — absent from the
table, which is not the same claim as illegal (`EXP-0017` §1–§2).

### RV64 (directive §6.3)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| RV-P1 | Standard integer arithmetic | `add` (R-type) | llvm-mc | **passing** — `rv64/positive/RV-P1-add-register` |
| RV-P2 | I-type immediate | `addi` imm12 | llvm-mc | **passing** — `RV-P2-addi-imm12` (both signed endpoints) |
| RV-P3 | Load/store | `ld`/`sd` base+offset, decomposed into `base` + `disp` | llvm-mc | **passing** — `rv64/positive/RV-P3-ld-sd-base-offset` (four instructions, signed imm12 endpoints) |
| RV-P4 | Conditional branch | `beq` B-type scatter | llvm-mc | **passing** — `RV-P4-beq-btype` (+8 and −8) |
| RV-P5 | Control transfer | `jal` J-type scatter | llvm-mc | **passing** — `RV-P5-jal-jtype` (+8 and −8) |
| RV-P6 | Scattered fields | B-type and J-type bit placement verified byte-for-byte | llvm-mc | **passing** with `RV-P4`/`RV-P5`; `beq` uses four placements, `jal` four |
| RV-P7 | Compressed vs standard | `c.addi` (2 bytes) vs `addi` (4 bytes), never chosen by the encoder | llvm-mc | **passing** — `RV-P7-caddi` (four immediates), with `N16a`/`N16b` rejecting the zero cases |
| RV-P8 | Associated reference | `auipc`+`addi` pair with `hi20`/`lo12` | llvm-mc + llvm-readobj + ld.lld | **passing** — `RV-P8-auipc-imm20` covers the form's field; `RV-P8-pcrel-pair` the 1:N group (three records); `RV-P8-pcrel-pair-resolved` the arithmetic against a linked binary |

The source is pinned (`OD-12`, ADR-0007): the UDB resolved-spec nodes named in
`check_rv64_source.py`, with `EXP-0009` deriving the B/J/RVC placements and
matching fourteen `llvm-mc` byte strings. `EXP-0010` generated
`definitions/rv64/0.1.0.json` (seven base-`I` forms, digest
`sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083`)
and `0.2.0` (the same seven plus `c.addi`, digest
`sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10`)
from eight of those nodes and re-encoded the probe vectors from each table it
built; the positive fixtures above are the independent gate, and the
negative fixtures (`N01`, `N01c`, `N02`, `N03`, `N04`, `N15`, `N16a`/`N16b`,
`N17a`/`N17b`/`N17c`) pin the rejection paths.

`RV-P3` is carried by two forms (`riscv:ld/rd-base-imm12`, `riscv:sd/rs-base-imm12`)
built from the `RV64` encoding block of `I/ld.yaml` (sha256:a2afcd44…) and
`I/sd.yaml` (sha256:f0b69996…). The address is three operands, not one memory
payload (`ADR-0008`, `OD-13`): `dest`/`src`, `base` and `disp`. `sd` scatters its
12-bit immediate over `[31:25]` and `[11:7]`, so the decomposition is also the
reason the scatter is field-derived. `N15` pins the rejected alternative: a
`{"mem": …}` payload is `E-OPERAND-003` at read time.

`RV-P7` is carried by `riscv:c.addi/rd-imm6` in `0.2.0`, built from
`inst/C/c.addi.yaml` (sha256 pinned by `check_rv64_source.py`). The node states
`not: 0` on `imm` and `xd`; `ADR-0009`/`OD-14` turn that into `excluded: [0]` on
both slots, and `EXP-0012` §2 measured the alternative — `c.addi a0, 0` encodes
`01 05` (`c.addi a0, 0x0`) and `c.addi x0, 1` encodes `05 00` (`c.nop 0x1`), both
reserved HINTs. `N16a`/`N16b` pin `E-RANGE-004`; `N01c` pins that naming the form
against `0.1.0` is `E-FORM-001`, not a silent fallback to `addi`.

`RV-P8`'s pair half was blocked on the format, not the source. The psABI states
the `R_RISCV_PCREL_HI20`/`LO12_I` relation and the encoding blocks do not; ADR-0010
turns the four normative statements (`riscv-elf.adoc:1578-1605`, `:1184`, `:1186`)
into `pc_reference_rule: pcrel_hi`, `value_transform: pcrel_lo12`, `E-FIXUP-009`
and a 1:N group. Two fixtures carry it. `RV-P8-pcrel-pair` is the unlinked gate:
one `auipc`, one `addi` and one `sd`, all `emit_relocation`, so the group is one
`hi` and two `lo`, and the oracle is the object file's three records. The S-type
member also measures ADR-0010 decision 3 — `llvm-mc` emits `R_RISCV_PCREL_LO12_S`
for the same `pcrel_lo12` value. `RV-P8-pcrel-pair-resolved` is the arithmetic
gate: `auipc` at 4, `blob` at 0x1000, both fixups `resolve_in_place`, and the
linked words `0x00001517` / `0xFFC50513` equal `(0x1000 - 4 + 0x800) >> 12 = 1`
and `(0x1000 - 4) & 0xFFF = 0xFFC`. The three alternatives give three different
words (`lo12_i` → 0x000, `pcrel_begin` on the `lo` → 0xFF8, no `+0x800` → 0), so
the fixture distinguishes the rule rather than merely agreeing with it. `N17a`
pins the rejected low-half addend, `N17b` the rejected `pcrel_hi` without a `lo`
role, and `N17c` the rejected `lo` in another section: `S` and `P_hi` would then
be offsets into unrelated origins, so the mask would hide a coordinate-system
error instead of reporting it.

## 5. Gate G3

G3 passes when each ISA has at least three positive vectors with matching oracle
bytes and two negative vectors with registry codes, all reproducible from a clean
checkout with the recorded toolchain versions.
