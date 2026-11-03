# Error Model

Status: **draft**. Error identity is part of the contract; error prose is not.

## 1. Envelope

```json
{
  "code": "E-RANGE-001",
  "path": "/instructions/12/operands/1/payload/value",
  "details": { "min": -128, "max": 127, "value": 200, "target_type": "imm8" },
  "message": "immediate 200 does not fit imm8"
}
```

Rules:

- `code` is stable. It never changes meaning between versions; a new meaning gets
  a new code.
- `path` is a JSON Pointer into the plan (or `""` for whole-document errors).
- `details` keys are fixed per code and sorted. Values are informational.
- `message` is free text and MUST NOT be used for identity, comparison, or
  hashing (`EXP-R6`).
- Numbers in messages are formatted with `.` decimal and no grouping, independent
  of locale.
- Multiple errors are reported sorted by `(path, code)`. Reporting MUST NOT
  depend on hash iteration order.
- Diagnostic identity = `sha256(code || "\0" || path || "\0" || join(sorted(detail_keys), ","))`.

## 2. Registry

| Code | Trigger | Fixed detail keys | Related test |
|---|---|---|---|
| E-PLAN-001 | Unknown or unsupported `format_version` | `found`, `supported` | — |
| E-PLAN-002 | Non-integer numeric value, or value outside the declared integer domain | `path_type`, `found_kind` | — |
| E-PLAN-003 | Unknown field in a strict object | `field`, `object` | — |
| E-PLAN-004 | Document is not parseable, or has duplicate keys | `reason` | — |
| E-PLAN-005 | Canonical-form violation that changes bytes (e.g. float, BOM, CRLF-dependent content) | `reason` | EXP-R4 |
| E-TARGET-001 | Unsupported `isa_family` or `isa_variant` | `found` | — |
| E-TARGET-002 | Invalid or missing `execution_mode` for the family | `found`, `required` | — |
| E-TARGET-003 | Form requires an extension that is not enabled | `extension`, `form_id` | N06 |
| E-TARGET-004 | Unsupported `byte_order` or `address_width` | `found` | — |
| E-DEF-001 | `definition_identity.digest` does not match the loaded definition | `declared`, `actual` | N10 |
| E-DEF-002 | Namespace or version not available in this materializer | `namespace`, `version` | EXP-R5 |
| E-FORM-001 | `form_id` is not present in the pinned definition | `form_id`, `namespace`, `version` | N01 |
| E-OPERAND-001 | Operand kind or register class does not match the form | `expected`, `found` | N02 |
| E-OPERAND-002 | Operand count or role sequence mismatch | `expected`, `found` | — |
| E-OPERAND-003 | Operand payload malformed for its kind | `kind`, `reason` | — |
| E-RANGE-001 | Immediate outside the legal encoding range | `min`, `max`, `value`, `target_type` | N03 |
| E-RANGE-002 | Displacement or branch offset outside the legal range | `min`, `max`, `value`, `bits`, `align_bits` | N04 |
| E-RANGE-003 | Alignment requirement not met | `required_align`, `value` | — |
| E-LAYOUT-001 | Fragments overlap | `first`, `second` | N09 |
| E-LAYOUT-002 | Fragment gap, or fragment sum != `declared_size` | `declared`, `covered` | N11 |
| E-LAYOUT-003 | Instruction offset/size does not match its fragment | `instruction_id`, `fragment` | N05 |
| E-LAYOUT-004 | List order violates the contract's declared order | `list`, `index` | — |
| E-LAYOUT-005 | Layout requires the materializer to compute padding or alignment | `section_id`, `offset`, `required_align` | N11 |
| E-SYMBOL-001 | Reference cannot be resolved under the declared resolution policy | `symbol_id`, `mode` | N08 |
| E-SYMBOL-002 | Duplicate `symbol_id`, or duplicate emitted name with conflicting binding | `symbol_id` | — |
| E-SYMBOL-003 | Defined symbol without a location | `symbol_id` | — |
| E-FIXUP-001 | Fixup kind is incompatible with the field descriptor or form | `kind`, `form_id`, `field` | N07 |
| E-FIXUP-002 | Unresolved target in a resolve-in-place fixup | `fixup_id`, `target` | N08 |
| E-FIXUP-003 | Computed fixup value outside `range_constraint` | `fixup_id`, `min`, `max`, `value` | N04 |
| E-FIXUP-004 | Relocation kind unsupported by the output contract | `kind`, `artifact` | — |
| E-FIXUP-005 | Field descriptor out of bounds or self-overlapping | `fixup_id`, `descriptor` | — |
| E-FIXUP-006 | Two fixups patch overlapping bits | `first`, `second` | — |
| E-FIXUP-007 | Pair group incomplete, duplicated role, or target mismatch | `pair_group`, `problem` | N12 |
| E-SIZE-001 | Encoded length != `expected_size` | `instruction_id`, `expected`, `actual` | N05 |
| E-BYTE-001 | Emitted bytes do not match `expected_digest` | `instruction_id`, `declared`, `actual` | N13 |
| E-VERSION-001 | Materializer cannot honor a declared plan feature | `feature`, `format_version` | — |
| E-INTERNAL-001 | Internal invariant violated (bug); never used for user input | `invariant` | — |

### 2.1 Counterexamples behind specific codes

A code without a concrete failure is decoration. This list records the observed
failure each code exists to prevent, or says `planned` when no observation
exists yet. `observed` means a built assembler produced the failure or the
rejection; `derived` means it follows from a measured byte sequence.

- `E-RANGE-002` — observed, F-06: XirAsm emits `eb 80` for `jmp short 0x82`,
  silently truncating a target that does not fit. Measured 2026-11-04: llvm-mc
  shortens `jmp .+0x81` to `eb 7f` (2 B) but promotes `jmp .+0x82` to
  `e9 7d 00 00 00` (5 B). A materializer that computes a displacement and then
  truncates it, or re-forms the branch, is rejected here.
- `E-FIXUP-003` — observed, F-06 (label path): XirAsm rejects an out-of-range
  label with "does not fit the signed 8-bit displacement". The same condition on
  a planned fixup is this code.
- `E-RANGE-001` — observed, F-10: XirAsm rejects `addi a0, a1, 2048` and
  `addi a0, a1, -2049`. The RV64 slice reproduces the boundary.
- `E-OPERAND-001` — observed, F-10: `c.addi a6, 5` (x16) is rejected because the
  compressed register class is `x8..x15`. A register-class violation is a
  legality rule, never a widening opportunity.
- `E-SIZE-001` — observed, `EXP-0002` W1: a definition drift that changes the
  encoded length is caught by `expected_size` alone.
- `E-BYTE-001` — observed, `EXP-0002` W2: a same-length encoder defect emits
  `49 89 d8` where the plan meant `48 89 d8`. Both are 3 bytes and both are
  legal; only the digest distinguishes them. In `EXP-0002`'s generator the digest
  is hashed from the oracle's bytes, not from the materializer's output.
- `E-FORM-001` — derived, ADR-0004: the v0 x86 slice has no coarse form such as
  `x86:mov/r64-r64`. A plan naming one must be rejected, not resolved to a
  default variant. The test is N01; it runs in Phase 3.
- `E-DEF-001` — `planned` (EXP-R5). No observation yet; it must not be cited as
  evidenced.

### 2.2 Retired codes

A mechanism that is removed takes its codes with it. Retired codes are never
reused for a different condition.

| Code | Retired | Reason | Replacement |
|---|---|---|---|
| E-CHOICE-001 | 2026-11-04 | `encoding_choices` removed by ADR-0004; a missing decision is a missing or under-specified form | E-FORM-001 |
| E-CHOICE-002 | 2026-11-04 | the same | E-FORM-001 / E-OPERAND-002 |
| E-CHOICE-003 | 2026-11-04 | the same; a value outside the form's set is a form or range error | E-FORM-001 / E-RANGE-001 |

## 3. Rules

- Every rejection MUST name a code from this registry. A generic failure is a
  defect in the error model.
- "assembler failed", "invalid input", or a stack trace are not acceptable
  outcomes for a negative test (`AC-06`).
- No code may be reused for a different condition.
- A code that is no longer produced is retired, never repurposed.
- Warnings are out of scope for v0: an ambiguous plan is an error.

## 4. Determinism

- Static checks (contract §13 steps 1–7) produce the complete error set before
  any byte is emitted.
- Emission errors are appended only when static checks are clean, so a plan never
  produces a partial artifact plus errors.
- Error ordering and identity MUST be reproducible across processes (`EXP-R2`,
  `EXP-R6`).
- Any error whose details include a pointer, timestamp, host name, or address is
  a bug (`E-INTERNAL-001` at review time).
