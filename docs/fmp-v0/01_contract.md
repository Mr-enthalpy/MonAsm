# FMP v0 Contract (frozen for v0 scope)

Status: **frozen for the v0 scope** (`ADR-0095`). Fields marked `TBD` or
`draft` are not frozen; they lack a counterexample or source evidence and are
recorded as out of v0 scope. Nothing in this document overrides
`00_directive.md`, and every deviation must be recorded as an ADR.

Conformance keywords: **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used in the
RFC 2119 sense.

## 1. Scope

This contract defines the data that crosses the planner/materializer boundary.
It defines obligations, not an implementation. The materializer:

- MUST validate completeness and legality against a pinned definition;
- MUST emit bytes and fixup records exactly as planned;
- MUST reject anything it cannot execute exactly.

It MUST NOT select instructions, choose among encoding forms, expand one
instruction into several, relax branches, insert padding, reorder sections or
fragments, execute macros or expressions, or consult undeclared environment
state.

## 2. Invariant registry

Canonical declaration of `INV-*`. Each invariant MUST have an executable test
before it is marked `verified`; `partial` names the gap that is still `TBD`.
The map is run by `cargo test --workspace` from `prototype/`; the CI workflow
`.github/workflows/determinism.yml` runs the same command on three hosts.

| ID | Statement | Enforced by | Test | Status |
|---|---|---|---|---|
| INV-01 | Every planned instruction names one definition-bound machine form; no selection happens at materialization time. | `form_id` resolution + `E-FORM-001` | The `N01` family in all three ISAs (`negatives_produce_exactly_the_registered_diagnostics`) plus `positives_reproduce_the_oracle_bytes`; `EXP-0096` shows every family v0 leaves absent is `E-FORM-001`. | verified |
| INV-02 | Every observable encoding of the same semantic operation has a distinct `form_id`; the materializer never selects among them. | exact form lookup (`E-FORM-001`) + operand signature (`E-OPERAND-*`); definition has one byte template per key | `N01` (coarse or absent form), `N02` (operand signature), `N18a`/`N18b` (the value must not switch the `sh` form), `N19` (a modifier cannot carry a byte variation); AC-04 in `06_validation_matrix.md`; `ADR-0094` for the families v0 leaves absent. | verified |
| INV-03 | One planned instruction produces exactly the bytes of that form; expansion is forbidden. | `expected_size` + `E-SIZE-001` | `N05` (`E-SIZE-001`/`E-LAYOUT-003`) and `N13` (`E-BYTE-001`, no re-encode); every positive's `expected.bin` fixes its length; unit `encodes_the_example_plan`. | verified |
| INV-04 | Layout is fixed by fragments; no padding, relaxation, trampolines, or reordering. | fragment containment + `E-LAYOUT-*` | `N09` (`E-LAYOUT-001`), `N11` (`E-LAYOUT-002`) and `N05` (`E-LAYOUT-003`); `N22a`/`N22f` (`E-LAYOUT-004`), `N22b`/`N22c` (`E-LAYOUT-006`) and `N22d`/`N22e` (`E-LAYOUT-007`); `E-LAYOUT-005` stays unreachable because no plan field requests alignment (`04_errors.md` §2). | verified |
| INV-05 | Same plan + definition + materializer version + options yields identical bytes, fixup records, or identical normalized error. | canonicalization + fingerprint + replay tests | `exp_r1_repeated_execution_is_identical`, `exp_r2_cross_process_agrees_with_in_process`, `exp_r3_artifact_digests_match_the_recorded_values`, `exp_r4_serialization_round_trip_is_identical` and `exp_r6_negative_identity_is_stable` in `determinism.rs`; `canonical_form_matches_python`; `fingerprint_ignores_provenance`. | verified |
| INV-06 | No macros, loops, conditionals, scripts, callbacks, or expression evaluation at materialization time. | data-only plan grammar + no evaluator in crates | `N21a`/`N21b` (unknown plan fields), `N15` (no composite or expression-shaped payload), `N23` (its `N23a` fixture rejects an expression-shaped scalar as `E-PLAN-002` at read time), `unknown_definition_field_is_rejected`; the absence of an evaluator is a source-level property reviewed at each slice. | verified |
| INV-07 | Illegal, incomplete, or inconsistent plans are rejected; no silent repair. | strict validation, no fallback paths | `negatives_produce_exactly_the_registered_diagnostics` over the `N01`–`N23` families; `exp_r5_definition_perturbation_is_loud`; `N13` (no re-encode). | verified |
| INV-08 | Every output is traceable to plan, definition, materializer version, and options, via fingerprint. | fingerprint + provenance block | `fingerprint_ignores_provenance` (the provenance block is outside the fingerprint); `exp_r2_cross_process_agrees_with_in_process` and `exp_r3_artifact_digests_match_the_recorded_values` compare the canonical artifact that carries both; `N10` (`E-DEF-001`) and `N13` (`E-BYTE-001`). | verified |

## 3. Root object

```json
{
  "format_version": "fmp/0.1",
  "target_identity":    { "...": "§4" },
  "definition_identity":{ "...": "§5" },
  "output_contract":    { "...": "§11" },
  "sections":           [ "...": "§6" ],
  "symbols":            [ "...": "§9" ],
  "instructions":       [ "...": "§7" ],
  "fixups":             [ "...": "§10" ],
  "provenance":         { "...": "§12" }
}
```

Rules:

- `format_version` MUST be an exact string; unknown versions are rejected
  (`E-PLAN-001`). No "compatible major version" guessing in v0.
- All numbers are JSON integers. Floats are rejected (`E-PLAN-002`).
- All lists have a specified order (§12); the materializer MUST NOT sort input
  lists implicitly, and MUST reject out-of-order lists (`E-LAYOUT-004`) rather
  than fixing them.
- Every object is closed. An unknown field is rejected at the level that carries
  it (`E-PLAN-003`; the definition loader reports `E-DEF-001`), never ignored or
  carried. There is no `x_*` namespace and no extension object in `fmp/0.1`
  (OD-05, ADR-0031); a new field is a new `format_version` or definition
  `version`. `target_identity.enabled_extensions` is the target's extension set,
  not an extension mechanism: with `fmp-def/0.1` it is equal to the table's set
  (`E-TARGET-001`); with `fmp-def/0.2` the table's set is an upper bound, the
  plan's set MUST be a subset (`E-TARGET-001`), and each named form's
  `requires_extensions` MUST be a subset of the plan's set (`E-TARGET-003`,
  `07_definition_format.md` §2–§3).
- The plan contains no expressions, variables, includes, or references to
  external files (`INV-06`).

### 3.1 Integer and address model (OD-09)

There are no floats and no wrap-around arithmetic. Every number belongs to a
declared domain, and a value outside its domain is rejected, never truncated,
saturated, or wrapped.

| Domain | Fields | Range |
|---|---|---|
| address | `base_address`, `fixups[].target.address` | `0 .. 2^address_width - 1`, and no wider than `u64` |
| offset, size | every `offset`, `declared_size`, fragment `size` | `0 .. 2^64 - 1` |
| addend | `fixups[].addend` | `-2^63 .. 2^63 - 1` |
| operand value | `payload.value` of an immediate or displacement | declared by the form as `{signed, bits, align_bits}` |
| computed fixup value | after `pc_reference_rule` and `value_transform` | `fixups[].range_constraint` |

Rules:

1. Numbers are parsed as exact integers (`E-PLAN-002`). A JSON float, an
   exponent notation that is not an integer, or a value outside the field's
   domain is rejected; it is never coerced.
2. `address_width` bounds address **inputs**. It does not set the width of
   arithmetic. `S + A - P` and every transform are evaluated in exact signed
   integers with at least 128 bits of headroom, never in `address_width` bits
   and never in the host word size.
3. A negative displacement is an `i64` (`-4`), never a reinterpreted
   two's-complement pattern chosen by the implementation.
4. Each value is range-checked once, at the point it becomes an encoded field.
   An operand is checked before encoding (`E-RANGE-001` immediate,
   `E-RANGE-002` displacement). A fixup is checked after its transform
   (`E-FIXUP-003`). Intermediates are not checked; §3.2 shows why.
5. `align_bits` is checked on the value produced by `pc_reference_rule`, before
   `value_transform` (a branch displacement must be a multiple of 4, and the
   `pcrel_page` reference is page-aligned by construction). `signed` and `bits`
   are checked on the post-transform value (the scaled value must fit 26 bits).
   Alignment is `E-RANGE-003`; range is `E-FIXUP-003` for a fixup and
   `E-RANGE-001`/`E-RANGE-002` for an operand. A transform that only masks (for
   example `lo12`) truncates by definition and is therefore never range-checked.
6. A transform MAY declare an input domain in the definition when applying it
   outside that domain is meaningless rather than merely out of range. v0
   declares none: for `pcrel_hi20` the output check already bounds the input,
   as §3.2 shows.

### 3.2 Counterexamples behind the integer model

- **A 64-bit address on a 32-bit word size.** Take `S = 0xFFFF_FFFF_FFFF_F000`
  and `P = 0xFFFF_FFFF_FFFF_F004`. The displacement is `-4`, a legal `rel32`.
  Computed in `u64` it is `18446744073709551612`; computed after narrowing `S`
  to `i64` it is an overflow, because `S > i64::MAX`. Both paths reject or
  corrupt a plan that exact signed arithmetic resolves without difficulty.
- **An immediate that does not fit its field.** `add rax, 2147483648`: `imm32`
  is signed, so the domain is `[-2147483648, 2147483647]`. Truncation emits
  `48 05 00 00 00 80`, which is `add rax, -2147483648` — a different program
  (`EXP-0002` W3). The plan is rejected `E-RANGE-001`.
- **A 33-bit intermediate.** RV64 `pcrel_hi20` computes
  `hi20 = (D + 0x800) >> 12` with `D = S + A - P`; the absolute transform
  `hi20` is the same arithmetic with `D = S + A`. For `D = 0x7FFF_F800`
  (2147481600, inside the signed 32-bit range) the sum is `0x8000_0000`. A
  32-bit implementation wraps that to `-2147483648`; the arithmetic shift then
  gives `hi20 = -524288`, which fits signed 20 bits and emits
  `auipc a0, -524288`. Exact arithmetic gives `hi20 = 524288`, which does not
  fit signed 20 bits and is rejected `E-FIXUP-003`. The wrap converts a required
  rejection into a plausible wrong address, which is the failure mode
  `E-RANGE-002` already records for `rel8` truncation.

## 4. `target_identity`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `isa_family` | yes | `x86` \| `aarch64` \| `riscv` | Selects the definition namespace and operand type system. | A `form_id` from another family could resolve against a coincidentally matching name. | frozen |
| `isa_variant` | yes | e.g. `x86-64`, `aarch64`, `rv64` | Distinguishes variants that share a mnemonic spelling. | `add` exists in x86, AArch64, and RV64 with unrelated encodings. | frozen |
| `execution_mode` | yes | x86: `16`/`32`/`64`; others: `"n/a"` | Changes opcode meaning, not just legality. | The byte `0x48` is `REX.W` in 64-bit mode but `dec eax` in 32-bit mode. | frozen |
| `enabled_extensions` | yes | Sorted list, e.g. `["rv64i","rv64m","rv64c"]` | Determines which forms are legal at all. | A `c.addi` form passes validation when the C extension is disabled. | frozen |
| `feature_constraints` | yes | Sorted list of named constraints; MUST be empty in `fmp/0.1` | Pins optional behavior that affects legality, not just performance. | A plan that says `["sve2"]` and is accepted by a v0 materializer emits SVE1 bytes for a program that requires SVE2. A non-empty entry is `E-VERSION-001` (a feature the format version cannot honour), never ignored. | frozen |
| `byte_order` | yes | `little` \| `big` | Determines byte emission order and field placement. | A big-endian RV64 variant would emit identical words with reversed bytes. | frozen |
| `address_width` | yes | bits, e.g. `64` | Fixes the width of relative and absolute fixups. | A rel32 fixup validated as 64-bit arithmetic overflows silently at 32 bits. | frozen |

`target_identity` MUST NOT contain ABI, object-format, or host-platform fields.
Those belong to `output_contract` (§11) or nowhere.

`enabled_extensions` is the only list that changes legality in v0, and its
comparison depends on the definition format the plan pins. Under `fmp-def/0.1`
the plan's set MUST equal the table's set (`E-TARGET-001`); under `fmp-def/0.2`
the table's set is the set the table can encode, the plan's set MUST be a subset
of it (`E-TARGET-001`), and a named form whose `requires_extensions` is not in
the plan's set is `E-TARGET-003` (`07_definition_format.md` §2–§3). A named
constraint that alters encoding would have to be expressible by a form or an
operand; `feature_constraints` therefore stays empty, and an entry is rejected
rather than compared for equality and then ignored.

## 5. `definition_identity`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `namespace` | yes | e.g. `monasm.isa.x86` | Names the rule-set family. | Two unrelated definitions can share a version string. | frozen |
| `version` | yes | Semver of the rule set | Makes upgrades explicit and reviewable. | Silent rule edits become silent byte changes. | frozen |
| `digest` | yes | `sha256:<hex>` over the canonical rule set | Detects rebuilt-but-unchanged-version definitions. | A regenerated table with one changed immediate range produces different bytes for the same plan, with no mismatch signal. | frozen |
| `source_ref` | no | Free-form provenance of generation (commit, generator version) | Audit convenience only; never changes output. | None: output must not depend on it. | draft |

Rules:

- `namespace + version` MUST map to exactly one `digest` for a given materializer
  build. A mismatch is `E-DEF-001`, a hard rejection (N10).
- The digest MUST cover every rule that can change emitted bytes: field layouts,
  operand constraints, range checks, and fixup transforms. It must not cover
  comments or ordering of unused metadata. A rule that selects among forms is
  not a coverage question: ADR-0004 forbids it from existing.
- A definition change MUST be either byte-identical for the plan or rejected;
  there is no "best effort" compatibility mode (OD-06).

## 6. `sections` and fragments

```json
{
  "section_id": ".text",
  "section_kind": "code",
  "image_backed": true,
  "base_address": 4096,
  "declared_size": 16,
  "fragments": [
    { "offset": 0, "size": 4, "kind": "instruction", "instruction_id": "I0001" },
    { "offset": 4, "size": 4, "kind": "data", "payload_hex": "00000000" }
  ]
}
```

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `section_id` | yes | Stable identifier | Fragment and fixup references use it. | Duplicate ids make fixups ambiguous. | frozen |
| `section_kind` | yes | `code` \| `data` \| `rodata` \| `bss` | Determines whether bytes exist and what validation applies. | A `bss` section emitted as zeros inflates the image. | frozen |
| `image_backed` | yes | Whether the section occupies file bytes | Separates virtual size from emitted bytes. | Missing: a reserved-tail section either emits zeros or truncates, both silently. | frozen |
| `base_address` | no | Absolute address of the section, if bound | Needed only for absolute references and cross-section `resolve_in_place` | A plan that treats a missing base as `0` emits a wrong absolute address; a plan with a cross-section `resolve_in_place` fixup and no base has nothing to compute `P` from. Both are `E-FIXUP-002`, never a default of zero. | frozen |
| `declared_size` | yes | Must equal the sum of fragment sizes | Detects planner/layout disagreement instead of repairing it. | Without it, a gap between fragments forces the materializer to choose padding (INV-04). | frozen |
| `fragments` | yes | Ordered, contiguous list | Layout is data, not a policy. | Overlaps or gaps let the materializer decide what goes where. | frozen |

Fragment rules:

- `kind` ∈ `instruction` | `data` | `fill`. Only `fill` may exist solely to pad;
  it MUST carry `fill_byte`.
- Fragments MUST be sorted by `offset`, contiguous, non-overlapping, and cover
  `[0, declared_size)` exactly (`E-LAYOUT-001`, `E-LAYOUT-002`).
- A section with `image_backed: false` occupies no file bytes, so it MUST have no
  fragments; its `declared_size` is virtual and is not a file layout. A fragment
  there asks for bytes the image will not contain (`E-LAYOUT-002`).
- An `instruction` fragment MUST reference exactly one planned instruction whose
  `offset` and size match the fragment (`E-LAYOUT-003`).
- Alignment MUST be expressed as a `fill` fragment by the planner. The
  materializer never computes alignment.
- `base_address` is optional because a same-section PC-relative fixup resolves
  from offsets alone: `S - P` is translation-invariant. It is required in effect
  when the plan has `target.kind: absolute`, or a cross-section
  `resolve_in_place` fixup. A missing base is never read as `0` (`E-FIXUP-002`).
- The sum of `declared_size` over `output_contract.section_order` MUST NOT exceed
  67,108,864 bytes (64 MiB). The ceiling is a format property, not a host limit:
  it is compared in `u128` before any allocation, and exceeding it is
  `E-LIMIT-001` (`ADR-0122`). Without it the plan would choose the allocation,
  so acceptance would depend on the machine's memory (`INV-05`) and an
  over-sized image would abort the process instead of returning a diagnostic
  (`INV-08`).

## 7. `instructions`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `instruction_id` | yes | Unique within the plan | Fixup and fragment references, diagnostics | Duplicate ids make `N05` diagnostics non-deterministic. | frozen |
| `section_id` | yes | Owning section | Locates bytes and fixup sites | Wrong/section-less instruction has no address. | frozen |
| `offset` | yes | Byte offset within the section | Must match the owning fragment | A mismatch silently shifts every following fragment. | frozen |
| `form_id` | yes | Definition-bound encoding form identifier | This is INV-01's whole mechanism | A mnemonic alone admits several encodings with different sizes. | frozen |
| `operands` | yes | Ordered typed operands (§8) | Determines field values and legality | Untyped operands force the encoder to guess operand kind. | frozen |
| `expected_size` | yes | Bytes this instruction MUST emit; MUST equal the named form's encoded size | Detects definition drift and forces rejection | A definition update changing size corrupts layout silently (`N05`). It is compared with `form.size()` during validation, before any fixup bounds arithmetic uses it (`E-SIZE-001`, `ADR-0122`). | frozen |
| `expected_digest` | no | `sha256:<hex>` over the exact bytes this instruction MUST emit, derived independently of the materializer (OD-01) | Detects a same-length encoder defect that `expected_size` cannot see | A materializer whose `REX.B` comes from the wrong operand bit emits `49 89 d8` (`mov r8, rbx`) where the plan meant `48 89 d8` (`mov rax, rbx`). Both are 3 bytes, both legal, and no other field contradicts the output. `EXP-0002` W2. | frozen |
| `source_trace` | no | Planner-side origin (file, line, node) | Audit only | Must never affect output; if it does, replay breaks (INV-05). | draft |

`encoding_choices` is not part of `fmp/0.1`. ADR-0004 moved every byte-affecting
decision onto `form_id` or a typed operand: the registry in
`02_encoding_choices.md` names the carrier of each `EC-*` row. A plan states a
machine form; it does not state a form plus a list that restates which form it
meant.

`form_id` format (OD-04):

```text
<form_id> := <isa_family> ":" <mnemonic> "/" <variant> [ "/" <encoding_family> ]
```

Examples: `x86:add/rm64-imm32/legacy`, `aarch64:add/x64-imm12-lsl0`,
`riscv:c.addi/rd-imm6`. The `-lsl0` suffix is load-bearing, not decoration: the
MRS node leaves AArch64 `shift`/`imm6`/`sh` variable, and the form name states the
pinned value so the operand list does not have to (`07_definition_format.md`
§8.2, ADR-0004).

Rules:

- `form_id` names an encoding form, not a semantic operation and not a
  library-internal opcode integer (Q2, OD-04). The three rejected alternatives
  are recorded in `05_open_decisions.md`: an opaque definition-assigned id can be
  reassigned without the plan noticing; a `match`/`mask` key cannot separate two
  forms that share the pattern (`slli` rv32 vs rv64, `90_boundary_audit.md`
  F-09); and a mnemonic-level name cannot separate the aliases in `EC-27`.
- The `<variant>` component names the operand signature as the pinned definition
  spells it (`rm64-imm8`, `rel32`, `r64-rm`), not a mnemonic-level summary. This
  is what makes `mov r64, r64` and `mov r64, imm`-style aliases distinguishable
  without a second selector (EC-27, EC-04).
- **The variant encodes every distinction the operands do not.** `rm-r64` and
  `r64-rm` have identical operand types and differ only in direction; they are
  two forms. `rax-imm32` has an implicit register, so its operand list is
  shorter than `rm64-imm32` and the two cannot be separated by operands alone.
  If two forms would be distinguishable only by looking at a value (for example
  "fits in 8 bits"), the variant is wrong: that is a value-driven choice, which
  `INV-02` forbids.
- `<encoding_family>` is REQUIRED for `isa_family: x86` and MUST be `legacy` for
  the one-byte-map family; `vex` and `evex` appear only when a slice needs them.
  It MUST be absent for `aarch64` and `riscv` in `fmp/0.1`, whose variant names
  are already exhaustive (a compressed RISC-V instruction is a different
  mnemonic, not a family).
- Two forms that can produce different bytes MUST have different `form_id`s.
- Two `form_id`s that always produce identical bytes for a given definition are
  a definition bug, not a plan choice.
- Resolution of `form_id` MUST be a pure lookup. "Closest match", appending a
  missing width or direction suffix, or any fallback is forbidden
  (`E-FORM-001`). An id the definition does not contain is a plan error; the
  definition is never extended at materialization time.
- **Stability is loud, not silent.** The name is resolved against the pinned
  `namespace + version + digest`. A definition revision that renames a form
  changes the digest, so the old plan fails `E-DEF-001` before lookup; if the
  digest were wrong and the lookup failed, the result is `E-FORM-001`. There is
  no alias table, no deprecated-name window, and no id that survives a rename
  silently. `N01` confirms both halves: an absent or renamed id is `E-FORM-001`
  (no near-match), and `EXP-R5` confirms the digest gate fires first when the
  revision is honest.

### 7.1 The definition artifact

`form_id` is resolved against a **pinned definition artifact**. The contract fixes
only what the plan names — `definition_identity` = `namespace` + `version` +
`digest` — and delegates the artifact itself to `07_definition_format.md`, which
fixes its shape, its load-time checks, its digest coverage and the shipped v0
tables: `definitions/x86_64/0.1.0.json` … `0.78.0.json`,
`definitions/aarch64/0.1.0.json` … `0.20.0.json`, and
`definitions/rv64/0.1.0.json` … `0.6.0.json`.

- A definition that fails a load-time check is `E-DEF-001`; the process stops
  before any plan is read from it.
- A `namespace`/`version` this materializer does not ship is `E-DEF-002`, checked
  before hashing, so a plan cannot pull in an arbitrary table by digest alone.
- A plan's digest that does not match the loaded definition is `E-DEF-001`
  (`N10`). Formatting never moves the digest; a rule change always does
  (`EXP-0004` §4).

`expected_digest` rules (OD-01, measured in `EXP-0002`):

- It is a **check**, never an input. The materializer MUST encode from
  `form_id + operands`, then compare, then reject (`E-BYTE-001`). It MUST NOT
  derive emitted bytes from the digest.
- `expected_digest` is optional per instruction. When a plan must detect a
  same-length encoder defect it MUST carry the digest; a plan that does not carry
  one relies on `expected_size` alone and cannot detect that class of defect. Raw
  expected bytes are forbidden: bytes can be emitted and a hash cannot, so a hash
  cannot silently become the source of truth. Variant C (byte template + patch
  fields) was rejected for exactly this reason, and it also loses the operand and
  form that legality depends on.
- `expected_size` is checked first; a length fault is `E-SIZE-001` and the
  digest is never consulted.
- When any `expected_digest` is present, `provenance.generated_by` MUST name its
  derivation source. A digest produced by the same encoder the materializer runs
  is recorded as such and buys nothing: only an independently derived digest
  (oracle or hand derivation) detects a same-length encoder defect.

## 8. Typed operands

```json
{ "role": "dest", "kind": "x86.gpr64", "target_type": "rm64", "payload": { "reg": 0 }, "modifiers": [] }
```

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `role` | yes | `dest` \| `src` \| `src2` \| `base` \| `index` \| `disp` \| `imm` \| `target` \| `pred` \| `list` \| `modifier` | Position-dependent encoding | Swapping `src`/`src2` changes a RISC-V R-type field order with no error. | frozen |
| `kind` | yes | Target-namespaced operand kind | Selects the field encoder and legality rules | A `gpr8` value in a `gpr64` field silently truncates. | frozen |
| `target_type` | yes | Definition-declared constraint name for this operand slot | Binds the operand to the constraint the definition checks | `kind` names a storage class (`riscv.xreg`), not the class the field can hold. `c.addi`'s `xd` is a 5-bit field that accepts every register except `x0` (measured: `c.addi a6, 5` → `15 08`), while `c.lw`'s 3-bit `rd'` accepts only `x8`–`x15` (measured: `c.lw a6, 0(a0)` rejected, `c.lw a2, 0(a0)` → `10 41`); without a per-form constraint a plan could supply `x16` to the narrow field and the encoder would truncate it to `x8` (`EC-20`, F-10, `EXP-0012` §2). Likewise a `lo12` transform masks by definition: a value planned as `imm12` would be silently truncated to its low 12 bits instead of rejected. | frozen |
| `payload` | yes | Kind-specific data | Carries the actual value | — | frozen |
| `modifiers` | yes | Sorted `{name, value}` list | Small observable variations (shift, extend, scale) | An ignored `lock` emits an unlocked read-modify-write (`F0` missing) with different semantics and no error; an unsorted list makes two plans for the same instruction hash differently (`EC-10`, `INV-05`). Unknown names are `E-OPERAND-003`. | frozen |

`target_type` names the **slot constraint**, not the operand's storage class: a
register placed in a `rm64` slot still says `rm64`, because the constraint is
what the definition checks and what the operand must satisfy. The check is exact
equality with the form's declared slot type, followed by the slot's own legality
rule (a `r64` slot rejects an operand whose payload is not `{reg}`). It is a
guard, not a selector: it can only make a plan fail (`E-OPERAND-001`), never
choose bits.
That is why it is allowed to duplicate a definition constraint while
`encoding_choices` was not (ADR-0004).

`modifiers` is likewise a guard. It may carry a variation the form permits
(`lsl`, `lock`, `addr_size`, `aq`), and the definition decides whether the pair
`(name, value)` is legal for that form. The list MUST be sorted by `name`, and
an empty list is the explicit statement "no modifier", never a default.

There is no universal `Memory(base, index, scale, displacement)` payload. A memory
operand is **decomposed into one operand per encoded field** — `base`, `disp`,
and `index`/`scale` where an ISA has them — and the addressing *form* is a
`form_id` variant (`ADR-0008`, `OD-13`). The four payload shapes in §8.1 are
unchanged, and a composite object such as `{"mem": {...}}` is `E-OPERAND-003`
(`N15`).

The reason is that the fields are not interchangeable. `ld a0, 8(a1)`
(`03 b5 85 00`) is a 5-bit `xs1`, a 12-bit sign-extended `imm` and a 5-bit `xd`,
so a single `{base, disp}` operand would own two ranges, two bit positions and
two answers to "which field does a fixup cover". On x86 the addressing form is a
function of the operand values, which is exactly why it may not be left to the
encoder: `movq 8(%rcx), %rax` is `48 8b 41 08` (ModRM mod=01) while
`movq 4096(%rcx), %rax` is `48 8b 81 00 10 00 00` (mod=10), and
`movq (%rbp), %rax` is `48 8b 45 00`, because mod=00 with `r/m = 101` means
RIP-relative. An encoder that picked mod from the displacement or the base
register would be selecting an encoding form (`INV-02`), so two forms are two
`form_id`s.

| ISA | v0 memory carrier |
|---|---|
| x86-64 | absent: each ModRM mod / SIB shape needs its own `form_id`, measured before `X86-P4`–`P6` can land |
| AArch64 | absent: the four `A64-P3` addressing kinds (unsigned-offset, pre/post-index, register-offset, literal) are form variants, not payloads |
| RV64 | `ld`/`sd` decompose into `dest`/`src`, `base`, `disp`; one form per mnemonic (`07_definition_format.md` §8.4) |

Legality of an operand is owned by the definition, not by the schema. A schema
that accepts an operand does not imply the definition accepts it (`N02`, `N03`).

### 8.1 Payload shapes in `fmp/0.1`

`payload` is a JSON object. `fmp/0.1` fixes four shapes, and a payload that is
none of them is `E-OPERAND-003` (`N15` pins the composite-memory case):

| Shape | Meaning | Legal when |
|---|---|---|
| `{ "reg": <u64> }` | Register number in the target's own numbering | the slot's `from` is `reg_number` |
| `{ "value": <integer> }` | The numeric value the operand encodes | the slot's `from` is `operand_value` and no fixup covers those bits |
| `{ "symbol_id": "<id>" }` | A symbolic target, carried as a guard only | a `target` role whose bits a fixup covers; it MUST equal `fixup.target.symbol_id` (`E-FIXUP-001`) |
| `{}` | No value: the fixup named for these bits is the only writer | the slot's bits are covered by a fixup (`E-OPERAND-003` otherwise) |

Exactly one key is allowed. `{ "reg": 0, "value": 0 }` states two values for one
field; it is not resolved by precedence, it is `E-OPERAND-003`.

The split is what keeps `E-FIXUP-006` decidable rather than a policy:

- An operand that carries `value` for a field a fixup covers gives one patch two
  writers. The plan cannot say which it meant, and "the fixup wins" would be a
  silent repair.
- An operand that carries `{}` for a field no fixup covers leaves the field at
  the template's base value. That is a default, not a decision (`INV-07`).

Counterexample: `{ "reg": 9 }` in a slot whose `from` is `operand_value` would
otherwise be read as the immediate `9`, because the payload key names the
register file and the slot names the field. Rejecting the mismatch is why the
shape is checked against the slot and not against the operand alone.

## 9. Symbols

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `symbol_id` | yes | Unique id used by fixups | Stable references | Name-only references break with duplicate local names. | frozen |
| `name` | yes | Emitted name | Symbol table level only | — | frozen |
| `kind` | yes | `defined` \| `undefined` \| `external` | Determines resolution obligations | Treating `external` as `undefined` silently changes relocation policy. | frozen |
| `binding` | yes | `local` \| `global` \| `weak` | Object symbol semantics | Absent, an emitter defaults to `global`, so a weak symbol becomes strong and a later definition can no longer override it. `binding` MUST NOT change Level 0 bytes; two plans differing only here emit identical code (INV-05). | frozen |
| `section_id`, `offset` | defined only | Location | Required for resolution | A defined symbol without a location is unresolvable but looks valid. `offset` MUST be `<=` the named section's `declared_size`: equality is the one-past-the-end label, and a larger offset names a byte that the section does not contain (`E-SYMBOL-003`, `ADR-0123`). Without the bound, `offset: 4096` in a 5-byte section resolves to an address outside it, and with `section_relative` refused there is no other field that could have meant "inside this section". | frozen |
| `type` | no | `func` \| `object` \| `notype` | Object metadata | None at Level 0/1. | draft |

Symbol identity is separate from symbol reference, fixup site, fixup kind,
relocation representation, and resolution policy. Collapsing them is the
mistake `03_fixup_model.md` is written to prevent.

## 10. Fixups

See `03_fixup_model.md`. Every fixup names a site, a field descriptor (possibly
non-contiguous), a target reference, an explicit addend, a `pc_reference_rule`, a
value transform, a range constraint, and a resolution mode. No field may be
defaulted by the materializer.

These rules make a fixup unambiguous (`OD-02`, `ADR-0121`):

- `resolution_mode` is exactly `resolve_in_place` or `emit_relocation`. The
  first writes the checked value and emits no record; the second zeroes the
  covered bits and emits one record. "Resolve and also record" is not a mode.
- One writer per bit. A fixup-covered field is not also set by an operand
  (`E-FIXUP-006`). A fixup whose target disagrees with a `target` operand on the
  same instruction is `E-FIXUP-001`.
- The bits a fixup covers MUST belong to exactly one slot, and that slot MUST be
  `from: operand_value`. A covered bit that belongs to a `reg_number` slot, or to
  an inverted placement, is a second writer (`E-FIXUP-006`); covering zero slots
  or more than one is `E-FIXUP-001`.
- Each `field_descriptor` range MUST be contained in one placement of that slot,
  and the ranges MUST appear in the slot's placement order, which is the value
  order. A range across a boundary, or the right ranges in another order, is
  `E-FIXUP-001` (`03_fixup_model.md` §3).
- `target.kind: section_relative` is refused (`E-VERSION-001`, `ADR-0123`). The
  schema names the kind, but `fmp/0.1` has no measured meaning for "a section's
  address", so the plan must name a `symbol` or an `absolute` address instead.

## 11. `output_contract`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `artifact` | yes | `bytes` \| `sections` (Level 0/1) | Selects the output shape | Object-file output would require ordering policy (OD-03). | frozen |
| `section_order` | yes | Explicit list of `section_id` | Emission order is observable in the image | Implicit map order differs between runs (INV-05). | frozen |
| `symbol_order` | no | Explicit list of `symbol_id` | Pins the Level 1 `symbols[]` order | A plan whose symbols are declared `ext` then `S1` cannot request that table order; the emitter falls back to `symbol_id` order (`S1`, `ext`) or, worse, to map order, so two processes emit different tables for the same symbol set (INV-05). | frozen |
| `fixup_record_order` | yes | `(section_id, offset, fixup_id)` | Record order is part of the output contract | Any other order makes byte comparison environment-dependent. | frozen |
| `include_symbol_table` | yes | Boolean | Selects whether Level 1 emits `symbols[]` | One emitter writes `.symtab` and another omits it; both artifacts are "correct" and differ. It MUST be `false` at Level 0; `true` at Level 0 is `E-VERSION-001`. It MUST NOT change instruction bytes. | frozen |
| `emit_fixups` | yes | Boolean, MUST be `true` in `fmp/0.1` | Prevents "resolved by magic" behavior | A plan with external references could emit bytes with no records. `false` is rejected (`E-VERSION-001`), not honoured. | frozen |

Output level (OD-03, measured in `EXP-0002` §6): Level 0 is mandatory and Level 1
is implemented as of 2026-11-08 (`ADR-0096`). Level 2 (container files) stays out
of `fmp/0.1`. No AC-05 shape needs a symbol table or a relocation table to be
expressed: the Level 0 fixup record already carries the site, the bit range, the
target, the addend, the PC rule, the transform, the range and the pair relation.
Level 1 therefore adds serialization, not encoding information. It does not
synthesize symbols in `fmp/0.1`; for RV64 the `auipc`-naming local label that
`R_RISCV_PCREL_LO12_I` would need remains a later writer task, while the Level 0
record keeps the pair relation explicit. `artifact: sections` and
`include_symbol_table: true` are accepted at Level 1; `include_symbol_table: true`
with `artifact: bytes` remains `E-VERSION-001`.

### 11.1 The Level 0 artifact

With `artifact: bytes`, `include_symbol_table: false` and `emit_fixups: true`, the
materializer produces one document:

```json
{
  "format_version": "fmp/0.1",
  "level": 0,
  "bytes_hex": "4889d8",
  "size": 3,
  "fixups": [],
  "fingerprint": "sha256:…",
  "materializer_version": "0.0.0"
}
```

| Field | Meaning |
|---|---|
| `format_version` | The plan's `format_version`, echoed after the gate |
| `level` | `0`; the only level this build emits |
| `bytes_hex` | Lowercase hex, no separator, `size` bytes; sections concatenated in `section_order`, fragments by `offset` |
| `size` | `len(bytes_hex) / 2`, stated so a consumer need not count |
| `fixups` | The `03_fixup_model.md` §8 records, in `fixup_record_order` |
| `fingerprint` | §12's fingerprint over the plan, the definition identity, and nothing else |
| `materializer_version` | Audit only; never part of `bytes_hex` or the fingerprint |

The envelope is deterministic: no timestamps, hostnames, absolute paths or tool
versions other than the build's own constant. `E-BYTE-001` is checked before the
envelope is assembled, so an artifact is either complete and correct or absent.

### 11.2 The Level 1 artifact

With `artifact: sections` and `emit_fixups: true`, the materializer produces one
document (`ADR-0096`):

```json
{
  "format_version": "fmp/0.1",
  "level": 1,
  "sections": [
    {
      "section_id": ".text",
      "section_kind": "code",
      "image_backed": true,
      "size": 3,
      "bytes_hex": "4889d8"
    }
  ],
  "symbols": [
    {
      "symbol_id": "S1",
      "name": "start",
      "kind": "defined",
      "binding": "global",
      "section_id": ".text",
      "offset": 0
    }
  ],
  "fixups": [],
  "fingerprint": "sha256:…",
  "materializer_version": "0.0.0"
}
```

`sections[]` has exactly one entry per `section_order` id, in that order. A
non-image-backed section (for example `bss`) is listed with its virtual
`declared_size` and `"bytes_hex": ""`, so the list never names an absent section
and the virtual size is not lost.

| Field | Required | Meaning |
|---|---|---|
| `format_version` | yes | The plan's `format_version`, echoed after the gate |
| `level` | yes | `1` |
| `sections` | yes | One entry per `section_order` id, in that order |
| `symbols` | iff `include_symbol_table` | The plan's symbols, in `symbol_order` or by `symbol_id` |
| `fixups` | yes | The §8 records, in `fixup_record_order`; identical to Level 0 |
| `fingerprint` | yes | §12's fingerprint over the plan, the definition identity, and nothing else |
| `materializer_version` | yes | Audit only; never part of the bytes or the fingerprint |

Section entry fields:

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `section_id` | yes | The plan's id, echoed | Two sections are concatenated into one byte string; the consumer cannot tell where the second starts. |
| `section_kind` | yes | `code` \| `data` \| `rodata` \| `bss` | A consumer must infer from the plan, and cannot distinguish a data section from code. |
| `image_backed` | yes | Whether the section has file bytes | A `bss` section would be read as zero-filled bytes and inflate the image (INV-04). |
| `base_address` | only when the plan declares it | The plan's `base_address`, echoed; never defaulted | An absolute reference cannot be interpreted without the plan at hand, and a default of `0` would silently change it. |
| `size` | yes | The plan's `declared_size` | A `bss` section has no bytes; without `size` its virtual extent disappears. For an image-backed section, `size` also lets a consumer verify `len(bytes_hex) / 2`. |
| `bytes_hex` | yes | Lowercase hex, no separator; `""` when `image_backed` is `false` | The section image itself would be missing. |

Symbol entry fields:

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `symbol_id` | yes | The plan's id, echoed | A record cannot be matched to a fixup target, which names `symbol_id`. |
| `name` | yes | The emitted name | The table carries no name a consumer can use. |
| `kind` | yes | `defined` \| `undefined` \| `external` | An external symbol would be mistaken for an unresolved local and get a definition it must not have. |
| `binding` | yes | `local` \| `global` \| `weak` | An emitter defaults to `global`, so a weak symbol silently becomes strong. |
| `section_id`, `offset` | `defined` only | The location, echoed | A defined symbol without a location is unresolvable but looks complete; `E-SYMBOL-003` already rejects that plan. |

`symbols[]` is absent, not empty, when `include_symbol_table` is `false`. The
order is `symbol_order` when present, otherwise ascending `symbol_id`; both are
already validated against the plan (`E-LAYOUT-004`), so the emitter never sorts,
repairs or synthesizes a symbol. In particular, `fmp/0.1` does not synthesize the
RV64 `pcrel_lo12` local label.

The Level 1 payload carries no container: no ELF header, section flags, string
table or relocation-type numbers. Those are Level 2 and stay out of `fmp/0.1`.
The Level 0 image is the concatenation of the `bytes_hex` values of the
image-backed sections in `section_order`, so the existing `*.expected.bin`
oracle still checks a Level 1 plan's code bytes.

## 12. Canonicalization, ordering, fingerprint

- Canonical JSON: keys sorted by Unicode code point, no insignificant
  whitespace, UTF-8 without BOM, LF newlines, integers only, no duplicate keys,
  `null` omitted when the field is optional and absent.
- Canonical JSON is the v0 wire form for fingerprints, definition digests and
  replay records (OD-08, ADR-0032). The reader accepts any valid JSON spelling of
  the same *value*; canonicalization is applied after parsing, because a
  whitespace difference cannot change an emitted byte. Duplicate keys are
  rejected (`E-PLAN-004`) rather than resolved; a BOM is `E-PLAN-005`. A binary
  transport, if ever added, is a new `format_version`, not a second spelling.
- `sections` are serialized in `output_contract.section_order` order;
  `fragments` by `offset`; `instructions` by `(section_id, offset)`;
  `fixups` by `fixup_record_order`; `symbols` by `symbol_order` if present,
  otherwise by `symbol_id`.
- Fingerprint:

```text
sha256("fmp/0.1\0" || canonical_plan_bytes || "\0" ||
       definition.namespace || "/" || definition.version || "\0" ||
       definition.digest)
```

- Diagnostic identity: `(code, plan_path, sorted detail keys)` is stable and
  hashable. Free-text messages are excluded from identity (`EXP-R6`).
- `provenance` records the materializer version and build profile. It is
  excluded from the plan fingerprint but included in the replay record.

## 13. Validation order

1. Parse and schema check (`E-PLAN-*`), including the numeric domains: a
   descriptor width or `range_constraint.bits` below 1 is `E-PLAN-002` here, not
   later (`ADR-0122`).
2. Target identity check (`E-TARGET-001`, `E-TARGET-002`, `E-TARGET-004`).
3. Definition digest check (`E-DEF-*`), including the loader's own arithmetic
   limits: a template wider than `u32::MAX` bits or a placement end beyond `u64`
   is `E-DEF-001`.
4. Section/fragment consistency (`E-LAYOUT-*`, `N09`, `N11`), including the
   `E-LIMIT-001` total over `section_order` (64 MiB).
5. Symbol table consistency (`E-SYMBOL-*`, `N08`), including
   `offset <= declared_size` (`ADR-0123`).
6. Static instruction checks: form lookup, the `fmp-def/0.2` per-form extension
   gate, operand legality, ranges, and `expected_size == form.size()`
   (`E-SIZE-001`) before any fixup bound uses the size (`E-FORM-*`,
   `E-OPERAND-*`, `E-RANGE-*`, and `E-TARGET-003` for a named form whose
   requirement the plan does not enable).
7. Fixup compatibility (`E-FIXUP-*`): descriptor bounds against `form.size() * 8`,
   field ownership (exactly one `operand_value` slot, in that slot's placement
   order), one writer per bit, pairing, and mode/target compatibility.
8. Emission: encode, compare `expected_size`, compare `expected_digest`, then
   apply each fixup exactly once — `resolve_in_place` computes and writes,
   `emit_relocation` zeroes and records (`E-SIZE-*`, `E-BYTE-*`, `E-FIXUP-*`).

Steps 1–7 are pure static checks and MUST NOT emit bytes. Emission runs only if
steps 1–7 produce no errors. Errors are reported sorted by `(plan_path, code)`;
no partial artifact is returned.

## 14. Open items

Fields marked `draft` above are tracked in `05_open_decisions.md`, with the
blocking acceptance criterion for each. The integer/address model is OD-09 and
is now settled in §3.1. The unknown-field rule (OD-05) is settled by ADR-0031 and
the canonical wire form (OD-08) by ADR-0032, so §12 no longer carries an open
decision.
