# Planner Boundary API

Status: **accepted for v0** (`ADR-0097`). This document defines the programmatic
form of the boundary that `01_contract.md` §1 already names: the planner writes
an FMP, the materializer validates and executes it. It adds no field, no error
code and no format version. Where this document and `01_contract.md` disagree,
the contract wins.

## 1. What the API is, and is not

The contract is one closed JSON document. The API is a typed writer for that
document, exported so a planner does not have to assemble JSON by hand. It is
deliberately not a second contract:

- The **materializer** still reads, validates and emits through
  `fmp-model/src/plan.rs`, `fmp-validate/src/lib.rs` and
  `fmp-materialize/src/lib.rs`. The API never replaces that path.
- The **builder** has no planning authority. It performs no instruction
  selection, encoding-form selection, instruction expansion, layout, padding,
  relaxation, reordering, fixup derivation, range check, symbol synthesis,
  defaulting or sorting. Every one of those is either a planner fact passed in
  or a rejection by the materializer.
- The builder **does not validate**. It serializes caller-supplied facts. The
  first authority to accept or reject a document is the same reader the CLI
  uses (`fmp_model::plan::read`), followed by the same validator and emitter.
  This is what makes "same codes" true by construction rather than by a second
  rule set.

The glossary term is **plan builder**: the typed authoring surface for an FMP
document, on the planner side of the boundary.

## 2. Crate and dependency direction

`prototype/crates/fmp-plan` is a library crate in the workspace.

| Edge | Allowed | Reason |
|---|---|---|
| `fmp-plan` -> `fmp-model` | yes | The contract types and canonical JSON live in `fmp-model`; the builder must emit exactly that document |
| `fmp-model` -> `fmp-plan` | no | The reader must not depend on an authoring path |
| `fmp-plan` -> `fmp-validate` / `fmp-materialize` | no | The builder must not carry a second validator or an encoder |
| `fmp-validate` / `fmp-materialize` / `fmp-cli` -> `fmp-plan` | no (except as a test dependency) | The materializer must not link the planner-side crate; the API tests may use it |

The library has no encoder, no definition table and no file I/O. It is a pure
function from typed facts to `fmp_model::json::Json`.

## 3. Types

The types mirror `01_contract.md` §3–§12 one-to-one. A required field is a
constructor parameter; an optional field is an `Option`; a closed enum lists
exactly the contract's members.

| Contract object | Builder type | Notes |
|---|---|---|
| root (§3) | `PlanBuilder` | `new` takes the seven required members; `provenance` is the one optional member |
| `target_identity` (§4) | `TargetIdentity` | `address_width` is `u32`; the reader applies the target rules |
| `definition_identity` (§5) | `DefinitionIdentity` | `namespace`, `version`, `digest` are strings; the registry resolves them |
| `output_contract` (§11) | `OutputContract` | `Artifact` is `Bytes | Sections`; `FixupRecordOrder` has one member |
| `sections[]` (§6) | `Section` | `SectionKind` is `Code | Data | Rodata | Bss` |
| fragment (§6) | `Fragment` | `FragmentBody` is `Instruction(String) | Data(Vec<u8>) | Fill(u8)`, written as `instruction_id`, `payload_hex` (lowercase) and `fill_byte` |
| `symbols[]` (§9) | `Symbol` | `SymbolKind` and `Binding` are the contract enums |
| `instructions[]` (§7) | `Instruction` | `form_id` stays a string; see §4 |
| operand (§8) | `Operand` | `Payload` is `Register(u64) | Value(i128) | Symbol(String) | Empty` |
| modifier (§8) | `Modifier` | value is `Int(i128) | Text(String) | Bool(bool)` |
| `fixups[]` (§10) | `Fixup` | see §4 for the target, rule, transform, mode and pair enums |

`PlanBuilder` has one constructor, one optional-member setter and two build
methods, with no partial state:

```rust
pub struct PlanBuilder { /* every required member is set */ }

impl PlanBuilder {
    /// The seven required root members. The format version is the crate's
    /// target (`fmp/0.1`), not a caller argument.
    pub fn new(
        target: TargetIdentity,
        definition: DefinitionIdentity,
        output: OutputContract,
        sections: Vec<Section>,
        symbols: Vec<Symbol>,
        instructions: Vec<Instruction>,
        fixups: Vec<Fixup>,
    ) -> Self;

    pub fn provenance(self, provenance: Provenance) -> Self;

    /// Serialize. No validation, no repair, no defaults.
    pub fn build(self) -> Json;

    /// `fmp_model::canonical::canonical_bytes(&self.build())`: sorted keys,
    /// no insignificant whitespace, integers only. Array order is unchanged;
    /// §12's ordering is what the caller passes and the validator checks.
    pub fn build_canonical(self) -> Vec<u8>;
}
```

A caller that wants a partial document has no API for it. `E-PLAN-006` for a
missing member is therefore **unrepresentable** through the builder; the reader
still reports it for a hand-written document.

## 4. The five discipline rules

1. **Total required fields, no partial state.** Every required field is a
   constructor argument. There is no `Default`, no `new_empty`, no `Option`
   around a required member and no `build` that can fail for an internal reason.
2. **Closed objects.** Each type has exactly one slot per contract field. There
   is no `unknown`, `extra`, `raw`, `x_*`, map-of-fields or catch-all slot, so
   an unknown field is unrepresentable (`E-PLAN-003` stays a document-path
   code).
3. **No defaults.** An absent optional field is omitted from the emitted object;
   it is never filled with `false`, `0`, `identity` or an empty list. A default
   is a decision the planner did not write.
4. **No order changes.** Vectors are emitted in caller order. The builder never
   sorts, deduplicates, groups or renumbers. `E-LAYOUT-004` and `E-LAYOUT-006`
   stay the reader's job.
5. **No computation.** `form_id`, operand `kind` and `target_type` are strings;
   the builder does not enumerate a definition version. It does not compute an
   offset, size, addend, range or pair, does not encode a `form_id`, does not
   resolve a symbol and does not decode or synthesize bytes. `Data(Vec<u8>)` is
   the one convenience: it is serialized as lowercase hex, which is a wire
   spelling, not a machine fact.

Two consequences follow directly:

- A changed definition version changes the strings a planner writes, not the
  API. Hard-coding forms would freeze one definition version into the builder
  and turn a catalog update into a library release.
- The builder cannot be used to "try" a form or a layout. It only writes what
  it is given; the answer to "does this work" comes from the validator.

## 5. Re-emission helper

`PlanBuilder::from_model(&fmp_model::Plan) -> Result<PlanBuilder, Unrepresentable>`
builds a document from an already-bound plan. It exists for tools that rewrite a
plan and for the parity tests in §7; it is not a parser and not a validation
shortcut.

It is lossless over the **frozen v0 surface**. It drops the three `draft`
fields (`source_ref`, `source_trace`, `symbol.type`) because the v0 builder does
not expose them and `fmp_model::Plan` does not retain the latter two. It drops
the schema-only `symbol.size` for the reason in §6. Canonical key order is
independent of field order, so the only fingerprint difference is a dropped
draft field; a parity test that compares bytes, records or envelopes never
depends on the fingerprint of the source document. No fixture in the corpus
carries a draft field (checked by scanning every `*.fmp.json` for `source_ref`,
`source_trace` and `"type":`), so for the corpus the re-emitted document is also
fingerprint-identical.

`Err(Unrepresentable)` is returned, never a panic, when the bound plan holds a
value the closed builder cannot express: an unknown enum member (the reader
retains `Unknown(String)` so the *validator* can report `E-VERSION-001`), a
`section_relative` fixup target, or a non-default `fixup_record_order` (the
other order strings are `E-VERSION-001` at `/output_contract/fixup_record_order`,
so they are outside the frozen surface). The error names the path and the value.
Corpus plans contain none of these, which is why the parity gate is 540/540
rather than "540 minus exceptions". The two fields the reader accepts but does
not retain (`source_trace`, `symbol.type`) and the schema-only `symbol.size` are
dropped without error, because `Plan` does not carry them.

## 6. Surface exclusions

The builder is the **frozen v0** authoring surface, not the whole schema.

| Excluded | Status | Why |
|---|---|---|
| `source_ref` | `draft` | No counterexample; out of v0 scope (`ADR-0095`) |
| `source_trace` | `draft` | Audit only; must never affect output |
| `symbol.type` | `draft` | Object metadata with no Level 0/1 effect |
| `section_relative` fixup target | `unverified` | No fixture and no established semantics (`03_fixup_model.md` §2.1) |
| Unknown `artifact`, enum members | rejected | Closed enums; an unknown member is `E-VERSION-001` on the document path |
| `symbol.size` | not in the contract | The schema's `symbol` object allows `size`, the contract §9 table does not define it, and `fmp-model` accepts but does not bind it. The builder follows the contract and does not expose it; §8 records the defect |

A plan that needs an excluded field still has the document path. The field
remains legal where the contract says so; excluding it here does not make the
document invalid and does not retire a code.

## 7. The gate

The M4 exit gate is `08_final_recommendation.md` §H: *API tests reject illegal
plans at the same codes*. The tests are integration tests in
`prototype/crates/fmp-cli/tests/planner_api.rs`, because that crate already
loads the registry and the fixture tree. `fmp-plan` stays free of the encoder.

| Test | Corpus | Assertion |
|---|---|---|
| Positive parity | all 101 positives | `from_model` -> `build_canonical` -> `read` -> `materialize` gives the same bytes, the same record count and, where recorded, the same Level 1 section/symbol envelope |
| Negative parity | all 540 `materialize`-phase negatives | the same code, JSON Pointer and detail-key set as the fixture's `expected-error.json` |
| From scratch | at least one positive per ISA, plus `X86-P71` | the document built only from constructors materializes to the oracle bytes; this proves the API is usable without `from_model` |
| Closed sets | one maximal document | each emitted object's key set equals the contract's closed set; no unknown key and no missing required key |
| Structural exclusion | the six `read`-phase negatives | they are unrepresentable by type (`N15` composite payload, `N21a`/`N21b` unknown field, `N23a` expression-shaped value, `N24a` unsupported version, `N24b` missing nested field); the existing fixture gate still rejects them on the document path |
| Determinism | two builds of one document | identical canonical bytes; the builder has no state, map order or environment input |

The negative parity test is the load-bearing one. It does not re-implement a
rule: it rebuilds the same plan through the builder and lets the unchanged
reader and validator reject it. A builder field that the validator reads but
the builder drops or renames fails the test, which is the drift guard the
document path cannot provide on its own.

`from_model` is a convenience for that test, not the claim. The from-scratch
test keeps the claim honest: the API can author a plan with no bound model in
hand.

## 8. Non-goals and recorded defects

- No planner IR, no instruction selection, no decode, no re-encode, no
  relaxation, no container writer, no schema code generation, no FFI and no
  second validator. Each would move a decision across the boundary or create a
  second source of truth.
- No dependency on the three ISA tables. A definition version is data; the
  builder writes `form_id` strings.
- The `symbol.size` mismatch in §6 is a documentation defect, not an M4 change.
  It is recorded here so a later ADR can either add the field to `01_contract.md`
  §9 as `draft` or remove it from `schema/fmp-v0.schema.json` and
  `fmp-model`'s accepted field set. Until then, `fmp-model` accepts and ignores
  it, which is the one place the closed-object rule is weaker than the contract
  states.
