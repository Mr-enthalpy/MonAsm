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
| INV-02 | Every byte-affecting choice not implied by `form_id + operands + target` is explicit (`EC-*`). | choice-set exactness check + `E-CHOICE-001` | TBD |
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

## 4. `target_identity`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `isa_family` | yes | `x86` \| `aarch64` \| `riscv` | Selects the definition namespace and operand type system. | A `form_id` from another family could resolve against a coincidentally matching name. | frozen |
| `isa_variant` | yes | e.g. `x86-64`, `aarch64`, `rv64` | Distinguishes variants that share a mnemonic spelling. | `add` exists in x86, AArch64, and RV64 with unrelated encodings. | frozen |
| `execution_mode` | yes | x86: `16`/`32`/`64`; others: `"n/a"` | Changes opcode meaning, not just legality. | The byte `0x48` is `REX.W` in 64-bit mode but `dec eax` in 32-bit mode. | frozen |
| `enabled_extensions` | yes | Sorted list, e.g. `["rv64i","rv64m","rv64c"]` | Determines which forms are legal at all. | A `c.addi` form passes validation when the C extension is disabled. | frozen |
| `feature_constraints` | yes | Sorted list of named constraints (may be empty) | Pins optional behavior that affects legality, not just performance. | A plan legal only under one micro-architectural feature set is accepted elsewhere. | draft |
| `byte_order` | yes | `little` \| `big` | Determines byte emission order and field placement. | A big-endian RV64 variant would emit identical words with reversed bytes. | frozen |
| `address_width` | yes | bits, e.g. `64` | Fixes the width of relative and absolute fixups. | A rel32 fixup validated as 64-bit arithmetic overflows silently at 32 bits. | frozen |

`target_identity` MUST NOT contain ABI, object-format, or host-platform fields.
Those belong to `output_contract` (§11) or nowhere.

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
  operand constraints, range checks, fixup transforms, and defaults that select
  among forms. It must not cover comments or ordering of unused metadata.
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
| `base_address` | no | Absolute address if bound | Needed to resolve absolute references at Level 1. | Unbound absolute fixups cannot be validated against the address width. | draft |
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

## 7. `instructions`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `instruction_id` | yes | Unique within the plan | Fixup and fragment references, diagnostics | Duplicate ids make `N05` diagnostics non-deterministic. | frozen |
| `section_id` | yes | Owning section | Locates bytes and fixup sites | Wrong/section-less instruction has no address. | frozen |
| `offset` | yes | Byte offset within the section | Must match the owning fragment | A mismatch silently shifts every following fragment. | frozen |
| `form_id` | yes | Definition-bound encoding form identifier | This is INV-01's whole mechanism | A mnemonic alone admits several encodings with different sizes. | frozen |
| `operands` | yes | Ordered typed operands (§8) | Determines field values and legality | Untyped operands force the encoder to guess operand kind. | frozen |
| `encoding_choices` | yes | Ordered list of `EC-*` selections; may be empty | INV-02's whole mechanism | Empty when a choice exists means the encoder picks silently. | frozen |
| `expected_size` | yes | Bytes this instruction MUST emit | Detects definition drift and forces rejection | A definition update changing size corrupts layout silently (`N05`). | frozen |
| `expected_digest` | no | Hash of expected bytes (OD-01) | Extra tamper detection | None yet; not used in v0 pending OD-01. | draft |
| `source_trace` | no | Planner-side origin (file, line, node) | Audit only | Must never affect output; if it does, replay breaks (INV-05). | draft |

`form_id` format (draft):

```text
<form_id> := <isa_family> ":" <mnemonic> "/" <variant> [ "/" <encoding_family> ]
```

Examples: `x86:add/r64-imm32/legacy`, `aarch64:add/x64-imm12-scaled`,
`riscv:c.addi/rd-eq-rs1/quadrant1`.

Rules:

- `form_id` names an encoding form, not a semantic operation and not a
  library-internal opcode integer (Q2, OD-04).
- Two forms that can produce different bytes MUST have different `form_id`s.
- Two `form_id`s that always produce identical bytes for a given definition are
  a definition bug, not a plan choice.
- Resolution of `form_id` MUST be a pure lookup. "Closest match" or fallback is
  forbidden (`E-FORM-001`).

## 8. Typed operands

```json
{ "role": "dest", "kind": "x86.gpr64", "target_type": "r64", "payload": { "reg": 0 }, "modifiers": [] }
```

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `role` | yes | `dest` \| `src` \| `src2` \| `base` \| `index` \| `disp` \| `imm` \| `target` \| `pred` \| `list` \| `modifier` | Position-dependent encoding | Swapping `src`/`src2` changes a RISC-V R-type field order with no error. | frozen |
| `kind` | yes | Target-namespaced operand kind | Selects the field encoder and legality rules | A `gpr8` value in a `gpr64` field silently truncates. | frozen |
| `target_type` | yes | Definition-declared type name | Binds the operand to a constraint | Without it, range/class checks have nothing to check against. | draft |
| `payload` | yes | Kind-specific data | Carries the actual value | — | frozen |
| `modifiers` | yes | Sorted `{name, value}` list | Small observable variations (shift, extend, scale) | `lsl #12` vs no shift differ by one bit and by meaning. | draft |

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
| `binding` | yes | `local` \| `global` \| `weak` | Object symbol semantics | — | draft |
| `section_id`, `offset` | defined only | Location | Required for resolution | A defined symbol without a location is unresolvable but looks valid. | frozen |
| `type` | no | `func` \| `object` \| `notype` | Object metadata | None at Level 0/1. | draft |

Symbol identity is separate from symbol reference, fixup site, fixup kind,
relocation representation, and resolution policy. Collapsing them is the
mistake `03_fixup_model.md` is written to prevent.

## 10. Fixups

See `03_fixup_model.md`. The contract requires that every fixup names a site, a
field descriptor (possibly non-contiguous), a target reference, an explicit
addend, a `pc_reference_rule`, a value transform, a range constraint, and a
resolution mode. No field may be defaulted by the materializer.

## 11. `output_contract`

| Field | Required | Meaning | Why it must be frozen | Counterexample if absent | Status |
|---|---|---|---|---|---|
| `artifact` | yes | `bytes` \| `sections` (Level 0/1) | Selects the output shape | Object-file output would require ordering policy (OD-03). | frozen |
| `section_order` | yes | Explicit list of `section_id` | Emission order is observable in the image | Implicit map order differs between runs (INV-05). | frozen |
| `symbol_order` | no | Explicit list of `symbol_id` | Only for Level 1 tables | Hash order changes table bytes across processes. | draft |
| `fixup_record_order` | yes | `(section_id, offset, fixup_id)` | Record order is part of the output contract | Any other order makes byte comparison environment-dependent. | frozen |
| `include_symbol_table` | yes | Boolean | Level 1 only | Ambiguous whether Level 1 output includes symbols. | draft |
| `emit_fixups` | yes | Boolean, MUST be true for unresolved targets | Prevents "resolved by magic" behavior | A plan with external references could emit bytes with no records. | frozen |

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
6. Static instruction checks: form lookup, operand legality, ranges, choice-set
   exactness (`E-FORM-*`, `E-OPERAND-*`, `E-RANGE-*`, `E-CHOICE-*`).
7. Fixup compatibility (`E-FIXUP-*`).
8. Emission: encode, compare `expected_size`, apply/record fixups
   (`E-SIZE-*`, `E-FIXUP-*`).

Steps 1–7 are pure static checks and MUST NOT emit bytes. Emission runs only if
steps 1–7 produce no errors. Errors are reported sorted by `(plan_path, code)`;
no partial artifact is returned.

## 14. Open items

Fields marked `draft` above are tracked in `05_open_decisions.md`, with the
blocking acceptance criterion for each. In particular, the canonical wire form is
OD-08 and the integer/address model is OD-09; both affect §12 and must be settled
before the first fixture is frozen.
