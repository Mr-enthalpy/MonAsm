# FMP v0 Contract (draft)

Status: **draft**. Fields marked `TBD` are not frozen; they lack a counterexample
or source evidence. Nothing in this document overrides
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
before it is marked verified; the test column is filled in Phase 4.

| ID | Statement | Enforced by | Test |
|---|---|---|---|
| INV-01 | Every planned instruction names one definition-bound machine form; no selection happens at materialization time. | `form_id` resolution + `E-FORM-001` | TBD |
| INV-02 | Every observable encoding of the same semantic operation has a distinct `form_id`; the materializer never selects among them. | exact form lookup (`E-FORM-001`) + operand signature (`E-OPERAND-*`); definition has one byte template per key | TBD |
| INV-03 | One planned instruction produces exactly the bytes of that form; expansion is forbidden. | `expected_size` + `E-SIZE-001` | TBD |
| INV-04 | Layout is fixed by fragments; no padding, relaxation, trampolines, or reordering. | fragment containment + `E-LAYOUT-*` | TBD |
| INV-05 | Same plan + definition + materializer version + options yields identical bytes, fixup records, or identical normalized error. | canonicalization + fingerprint + replay tests | TBD |
| INV-06 | No macros, loops, conditionals, scripts, callbacks, or expression evaluation at materialization time. | data-only plan grammar + no evaluator in crates | TBD |
| INV-07 | Illegal, incomplete, or inconsistent plans are rejected; no silent repair. | strict validation, no fallback paths | TBD |
| INV-08 | Every output is traceable to plan, definition, materializer version, and options, via fingerprint. | fingerprint + provenance block | TBD |

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
- Unknown fields are rejected in v0 unless they are inside a versioned extension
  object (OD-05).
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
  `hi20 = (D + 0x800) >> 12` with `D = S + A - P`. For `D = 0x7FFF_F800`
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

`enabled_extensions` is the only list that changes legality in v0. A named
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
- An `instruction` fragment MUST reference exactly one planned instruction whose
  `offset` and size match the fragment (`E-LAYOUT-003`).
- Alignment MUST be expressed as a `fill` fragment by the planner. The
  materializer never computes alignment.
- `base_address` is optional because a same-section PC-relative fixup resolves
  from offsets alone: `S - P` is translation-invariant. It is required in effect
  when the plan has `target.kind: absolute`, or a cross-section
  `resolve_in_place` fixup. A missing base is never read as `0` (`E-FIXUP-002`).

## 7. `instructions`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `instruction_id` | yes | Unique within the plan | Fixup and fragment references, diagnostics | Duplicate ids make `N05` diagnostics non-deterministic. | frozen |
| `section_id` | yes | Owning section | Locates bytes and fixup sites | Wrong/section-less instruction has no address. | frozen |
| `offset` | yes | Byte offset within the section | Must match the owning fragment | A mismatch silently shifts every following fragment. | frozen |
| `form_id` | yes | Definition-bound encoding form identifier | This is INV-01's whole mechanism | A mnemonic alone admits several encodings with different sizes. | frozen |
| `operands` | yes | Ordered typed operands (§8) | Determines field values and legality | Untyped operands force the encoder to guess operand kind. | frozen |
| `expected_size` | yes | Bytes this instruction MUST emit | Detects definition drift and forces rejection | A definition update changing size corrupts layout silently (`N05`). | frozen |
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

Examples: `x86:add/rm64-imm32/legacy`, `aarch64:add/x64-imm12-scaled`,
`riscv:c.addi/rd-eq-rs1`.

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
fixes its shape, its load-time checks, its digest coverage and the v0 x86 table
(`definitions/x86_64/0.1.0.json`).

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
- The plan MUST carry a hash. Raw expected bytes are forbidden: bytes can be
  emitted and a hash cannot, so a hash cannot silently become the source of
  truth. Variant C (byte template + patch fields) was rejected for exactly this
  reason, and it also loses the operand and form that legality depends on.
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
| `target_type` | yes | Definition-declared constraint name for this operand slot | Binds the operand to the constraint the definition checks | `kind` names a storage class (`riscv.xreg`), not the class the field can hold. `c.addi` encodes 3 register bits; without `creg_x8_x15` a plan could supply `x16`, which the 3-bit field would silently truncate to `x8` (`EC-20`, F-10). Likewise a `lo12` transform masks by definition: a value planned as `imm12` would be silently truncated to its low 12 bits instead of rejected. | frozen |
| `payload` | yes | Kind-specific data | Carries the actual value | — | frozen |
| `modifiers` | yes | Sorted `{name, value}` list | Small observable variations (shift, extend, scale) | An ignored `lock` emits an unlocked read-modify-write (`F0` missing) with different semantics and no error; an unsorted list makes two plans for the same instruction hash differently (`EC-10`, `INV-05`). Unknown names are `E-OPERAND-003`. | frozen |

`target_type` names the **slot constraint**, not the operand's storage class: a
register placed in a `rm64` slot still says `rm64`, because the constraint is
what the definition checks and what the operand must satisfy. The check is exact
equality with the form's declared slot type, followed by the slot's own
legality rule (a `r64` slot rejects a `x86.mem` payload). It is a guard, not a
selector: it can only make a plan fail (`E-OPERAND-001`), never choose bits.
That is why it is allowed to duplicate a definition constraint while
`encoding_choices` was not (ADR-0004).

`modifiers` is likewise a guard. It may carry a variation the form permits
(`lsl`, `lock`, `addr_size`, `aq`), and the definition decides whether the pair
`(name, value)` is legal for that form. The list MUST be sorted by `name`, and
an empty list is the explicit statement "no modifier", never a default.

There is no universal `Memory(base, index, scale, displacement)`. Each ISA keeps
its own addressing kinds, because the addressing semantics differ:

| ISA | Addressing kinds (draft) |
|---|---|
| x86-64 | `x86.mem` with `base`/`index`/`scale`/`disp`/`rip_relative`/`addr_size`/`segment` |
| AArch64 | `aarch64.mem.unsigned-offset` (imm12 scaled), `.pre-index`, `.post-index`, `.register-offset`, `.literal` |
| RV64 | `riscv.mem.base-offset` (base register + 12-bit signed offset) |

Legality of an operand is owned by the definition, not by the schema. A schema
that accepts an operand does not imply the definition accepts it (`N02`, `N03`).

## 9. Symbols

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `symbol_id` | yes | Unique id used by fixups | Stable references | Name-only references break with duplicate local names. | frozen |
| `name` | yes | Emitted name | Symbol table level only | — | frozen |
| `kind` | yes | `defined` \| `undefined` \| `external` | Determines resolution obligations | Treating `external` as `undefined` silently changes relocation policy. | frozen |
| `binding` | yes | `local` \| `global` \| `weak` | Object symbol semantics | Absent, an emitter defaults to `global`, so a weak symbol becomes strong and a later definition can no longer override it. `binding` MUST NOT change Level 0 bytes; two plans differing only here emit identical code (INV-05). | frozen |
| `section_id`, `offset` | defined only | Location | Required for resolution | A defined symbol without a location is unresolvable but looks valid. | frozen |
| `type` | no | `func` \| `object` \| `notype` | Object metadata | None at Level 0/1. | draft |

Symbol identity is separate from symbol reference, fixup site, fixup kind,
relocation representation, and resolution policy. Collapsing them is the
mistake `03_fixup_model.md` is written to prevent.

## 10. Fixups

See `03_fixup_model.md`. Every fixup names a site, a field descriptor (possibly
non-contiguous), a target reference, an explicit addend, a `pc_reference_rule`, a
value transform, a range constraint, and a resolution mode. No field may be
defaulted by the materializer.

Two rules make a fixup unambiguous (OD-02):

- `resolution_mode` is exactly `resolve_in_place` or `emit_relocation`. The
  first writes the checked value and emits no record; the second zeroes the
  covered bits and emits one record. "Resolve and also record" is not a mode.
- One writer per bit. A fixup-covered field is not also set by an operand
  (`E-FIXUP-006`). A fixup whose target disagrees with a `target` operand on the
  same instruction is `E-FIXUP-001`.

## 11. `output_contract`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `artifact` | yes | `bytes` \| `sections` (Level 0/1) | Selects the output shape | Object-file output would require ordering policy (OD-03). | frozen |
| `section_order` | yes | Explicit list of `section_id` | Emission order is observable in the image | Implicit map order differs between runs (INV-05). | frozen |
| `symbol_order` | no | Explicit list of `symbol_id` | Only for Level 1 tables | Hash order changes table bytes across processes. | draft |
| `fixup_record_order` | yes | `(section_id, offset, fixup_id)` | Record order is part of the output contract | Any other order makes byte comparison environment-dependent. | frozen |
| `include_symbol_table` | yes | Boolean | Selects whether Level 1 emits `symbols[]` | One emitter writes `.symtab` and another omits it; both artifacts are "correct" and differ. It MUST be `false` at Level 0 and MUST NOT change instruction bytes. | frozen |
| `emit_fixups` | yes | Boolean, MUST be `true` in `fmp/0.1` | Prevents "resolved by magic" behavior | A plan with external references could emit bytes with no records. `false` is rejected (`E-VERSION-001`), not honoured. | frozen |

Output level (OD-03, measured in `EXP-0002` §6): v0 emits **Level 0** — bytes
plus normalized fixup records. Level 1 (`artifact: sections` with
`include_symbol_table: true`) is optional and deferred. No AC-05 shape needs a
symbol table or a relocation table to be expressed: the Level 0 fixup record
already carries the site, the bit range, the target, the addend, the PC rule, the
transform, the range and the pair relation. Level 1 would add serialization, and
for RV64 it would add a synthesized local symbol per `hi` site, because
`R_RISCV_PCREL_LO12_I` names the `auipc`, not the target. `artifact: sections`
stays legal in the schema so a later slice can opt in without a format bump.

## 12. Canonicalization, ordering, fingerprint

- Canonical JSON: keys sorted by Unicode code point, no insignificant
  whitespace, UTF-8 without BOM, LF newlines, integers only, no duplicate keys,
  `null` omitted when the field is optional and absent.
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

1. Parse and schema check (`E-PLAN-*`).
2. Target identity check (`E-TARGET-*`).
3. Definition digest check (`E-DEF-*`).
4. Section/fragment consistency (`E-LAYOUT-*`, `N09`, `N11`).
5. Symbol table consistency (`E-SYMBOL-*`, `N08`).
6. Static instruction checks: form lookup, operand legality, ranges
   (`E-FORM-*`, `E-OPERAND-*`, `E-RANGE-*`).
7. Fixup compatibility (`E-FIXUP-*`): descriptor bounds, one writer per bit,
   pairing, and mode/target compatibility.
8. Emission: encode, compare `expected_size`, compare `expected_digest`, then
   apply each fixup exactly once — `resolve_in_place` computes and writes,
   `emit_relocation` zeroes and records (`E-SIZE-*`, `E-BYTE-*`, `E-FIXUP-*`).

Steps 1–7 are pure static checks and MUST NOT emit bytes. Emission runs only if
steps 1–7 produce no errors. Errors are reported sorted by `(plan_path, code)`;
no partial artifact is returned.

## 14. Open items

Fields marked `draft` above are tracked in `05_open_decisions.md`, with the
blocking acceptance criterion for each. The integer/address model is OD-09 and
is now settled in §3.1; the canonical wire form (OD-08) still affects §12 and
must be settled before the first fixture is frozen.
