# ADR-0127: the execution credential is parsed facts plus the bound definition

- Status: accepted
- Date: 2026-11-13
- Settles: what a parsed-plan identity covers, the byte protocol it uses, which
  definition object may be executed, which parser rules a mutable DTO must be
  re-checked against, and which post-encode failures may exist
- Supersedes: none
- Superseded by: none
- Revises: decision D13, D14 and D16 of `docs/architecture/he1-h1-plan.md`;
  `fmp-model/src/definition.rs` (`Definition`, `Registry`),
  `fmp-model/src/plan.rs` (`legacy_document`, `check_structure`),
  `fmp-model/src/identity.rs` (new), `fmp-validate/src/lib.rs` (arithmetic and
  the `page` rule), `fmp-materialize/src/lib.rs` (fingerprint input, accessors
  and wide-field encoding), the H1a tests listed in §9,
  `.github/workflows/gates.yml` (dependency-direction, identity-vector and
  release-bound steps), `research/he1/H1-report.md` (new),
  `tools/plan_identity.py` (new)
- Keeps in force: `ADR-0123` for the artifact envelope; `ADR-0126` for the
  `payload/0.1` projection; `ADR-0125` for the HE-1 scope; the fixup rows of
  `docs/fmp-v0/03_fixup_model.md` quoted in §7

## Context

H0 reproduced four concentration points and filed them as evidence, not as
properties (`research/he1/H0-report.md` §3). Two of them meet in H1:

- a loaded `Definition` could be re-encoded in memory under its original digest,
  because `digest` was a stored string and `forms` was public
  (`a_loaded_definition_can_be_re_encoded_under_its_original_digest`);
- the only plan identity in the product, `fmp_materialize::fingerprint`, hashes
  the raw document the planner wrote. It cannot see a changed parsed operand
  (`a_parsed_operand_can_change_under_a_stable_fingerprint`) and it does see
  fields the parser drops (`a_legacy_fingerprint_covers_document_fields_the_parser_drops`).

H1a closes the definition side and defines the parsed-plan identity, without
introducing the execution credential itself. `ValidatedPlan`, `bind`, the new
`materialize`, `ExecutionReceipt` and the CLI split are H1b
(`docs/architecture/he1-h1-plan.md` §3.2–§3.4). Until H1b lands, the identity
exists and is tested, but `materialize` still accepts `(&Plan, &Definition)` and
still re-runs its own digest comparison. Nothing in this ADR claims otherwise.

The round rule applies: every field below has a counterexample in §4–§7, and the
H1a tests are the executable part of the argument.

## 1. `Definition` is a closed loaded object

**Decision.** `Definition` has private fields, no public constructor and no
`Clone`. Its only constructors are `definition::read` and `Registry::load_dir`.
`document` is deleted: it was written once and never read, and a second copy of
the facts is a second authority. Access is read-only:
`definition_format()`, `namespace()`, `version()`, `target()`, `forms()`,
`digest()`. `Registry` stores `Vec<Arc<Definition>>`; `find` returns
`Arc<Definition>`; `add` takes ownership.

**Counterexample (H0, now impossible).** Replace every
`forms[i].template` with `vec![0x90; len]`. Before H1a the digest string did not
move and `materialize` emitted the mutated bytes under the old digest. After
H1a the program does not compile; the `compile_fail` doctests in
`fmp-model/src/lib.rs` assert both spellings (`definition.forms = …` and a
`Definition { … }` literal that names **every** field). The second one can only
fail on the private-field access: an incomplete literal also fails with all
fields public, which is why it is not evidence. The positive control reads
`namespace()`, `version()` and `digest()` through the same import path so a
wrong import cannot make the two negative doctests green for the wrong reason.
The fault-injection control is a scratch copy with all six fields `pub`: both
negative doctests then fail, so neither is green for an unrelated reason.

**Replacement evidence.** `a_definition_edit_reloads_to_a_new_digest` edits a
template byte in the **document**, reloads, asserts the digest changed, and
asserts the untouched plan is rejected at
`/definition_identity/digest` with `E-DEF-001`. `a_definition_reloads_to_the_same_digest`
and `a_canonically_equal_definition_loads_to_the_same_digest` pin the other
direction: the digest is a function of the canonical document, not of the
object's address or its spelling. `the_registry_shares_one_immutable_definition`
asserts `Arc::ptr_eq` and a strong count of three, so "shared" cannot quietly
become "copied".

**Limits.** This closes the safe-Rust API, not the process. `fmp-model` is
`#![forbid(unsafe_code)]`, and `Form` remains `Clone`, so a caller can copy a
form out; a copy is not a `Definition` and cannot be passed where one is
required. Interior mutability is absent, so an `Arc<Definition>` cannot be
mutated through a shared reference.

## 2. `ParsedPlanIdentity` covers the parsed plan

**Decision.** `fmp_model::identity::ParsedPlanIdentity::of(&Plan)` returns the
algorithm name and a digest:

- algorithm name: `plan-identity/0.1`;
- hash input: `b"plan-identity/0.1\0" ++ facts`, where `facts` is
  `plan_facts(&Plan)`; the domain separator and the algorithm name are the same
  literal, so changing one without the other is a compile-time-visible edit to
  `PLAN_IDENTITY_ALGORITHM` and `DOMAIN`;
- output: `sha256:<64 lowercase hex>`.

`plan-identity/0.1` covers **every field of `Plan` except `legacy_document` and
`provenance`**, including every `path`. The two exclusions are decisions, not
omissions:

| Excluded | Counterexample if included | Evidence |
|---|---|---|
| `legacy_document` | A planner that writes the same execution facts with a different `source_trace` would get a different identity; the legacy fingerprint already behaves that way, and H1 exists to stop repeating it | `the_legacy_document_is_not_part_of_the_identity` |
| `provenance` | `provenance` carries `materializer_version` and free-form `notes`; a note edit would change the identity of the same execution | `provenance_is_not_part_of_the_identity` |

`path` is included on purpose: a JSON Pointer is deterministic plan data, and
covering one extra deterministic field cannot create ambiguity. Removing it
later would be an identity change and needs a new ADR, not a refactor.

**Structural coverage, not a convention.** Every covered struct is destructured
exhaustively, with no `..`; every enum is matched with every variant and no
`_` arm. Adding a field or a variant therefore **fails the build** until the
identity says what it means. `plan_identity_covers_every_parsed_field` is the
semantic second layer: 73 mutations, one or more per covered field and per enum
payload shape, each asserting that the digest moves. A variant switch alone does
not prove the value *inside* a variant is encoded: `same_variant_values_change_the_identity`
adds eight rows that keep the variant fixed and change only its value (register
number, symbol id, absolute target, symbol target, `Some` payload, vector
element, order, count). Together they prove the encoder uses the field's value;
exhaustive destructuring proves the field cannot be forgotten.

## 3. The byte protocol

The protocol is frozen by this section. A changed tag, field order, enum
variant number or integer width is an algorithm change: it needs a new
`plan-identity/<version>` literal, the same literal followed by `\0` as the new
domain separator, new fixed vectors, and a new ADR. There is no negotiation
byte and no self-describing framing.

### 3.1 Tags

| Tag | Primitive | Payload |
|---|---|---|
| `0x01` | `u8` / `bool` | 1 byte (`bool` is `0`/`1`) |
| `0x02` | `u64` | 8 bytes little-endian |
| `0x03` | `i128` | 16 bytes little-endian, two's complement |
| `0x04` | string | `u64` byte length, then UTF-8 bytes (no NUL, no escaping) |
| `0x05` | `none` | nothing |
| `0x06` | `some` | one encoded value |
| `0x07` | vector | `u64` element count, then each element |
| `0x08` | structure | each field in the order below, no count, no names |
| `0x09` | enum | `u32` variant number little-endian, then the variant payload |

Every unsigned integer is encoded as `0x02` + `u64`, regardless of its Rust
width: `address_width: u32`, `declared_size: u64`, `lsb/width: u32`,
`bits/align_bits: u32`, `transform_shift: u32`, `register: u64`. `addend: i64`
is encoded as `0x03` + `i128`. This is deliberate: the protocol has one unsigned
and one signed width, so a later widening of a Rust field from `u32` to `u64`
does not silently change the byte stream.

The root is a `0x08` structure. `facts` therefore starts with `0x08`; that byte
is protocol, not framing, and it is visible in the pinned hex of §5.

### 3.2 Struct field order (normative)

`Plan` is the root structure, in this order (the two excluded fields are not
encoded):

```text
Plan           : format_version, target, definition, output,
                 sections, symbols, instructions, fixups
TargetIdentity : isa_family, isa_variant, execution_mode,
                 enabled_extensions, feature_constraints, byte_order,
                 address_width, path
DefinitionIdentity : namespace, version, digest, source_ref, path
OutputContract : artifact, section_order, symbol_order, fixup_record_order,
                 include_symbol_table, emit_fixups, path
Section        : section_id, section_kind, image_backed, base_address,
                 declared_size, fragments, path
Fragment       : offset, size, body, path
Symbol         : symbol_id, name, kind, binding, section_id, offset, path
Instruction    : instruction_id, section_id, offset, form_id, operands,
                 expected_size, expected_digest, path
Operand        : role, kind, target_type, payload, modifiers, path
Modifier       : name, value
Fixup          : fixup_id, section_id, offset, field_descriptor, target,
                 addend, pc_reference_rule, value_transform, transform_shift,
                 range_constraint, resolution_mode, pair_group, pair_role, path
FieldRange     : lsb, width
RangeConstraint: signed, bits, align_bits
```

`enabled_extensions`, `feature_constraints`, `section_order`, `fragments`,
`symbols`, `instructions`, `fixups`, `field_descriptor` and `modifiers` are
vectors. `source_ref`, `symbol_order`, `base_address`, `section_id` (Symbol),
`offset` (Symbol), `expected_digest`, `transform_shift`, `pair_group` and
`pair_role` are options. `symbol_order` is `option<vector<string>>`, so `none`
and `some([])` are different facts.

### 3.3 Enum variants (normative)

| Type | Variant numbers and payloads |
|---|---|
| `Artifact` | `0` Bytes, `1` Sections, `2` Unknown(string) |
| `SectionKind` | `0` Code, `1` Data, `2` Rodata, `3` Bss, `4` Unknown(string) |
| `FragmentBody` | `0` Instruction(string), `1` Data(string), `2` Fill(u8) |
| `SymbolKind` | `0` Defined, `1` Undefined, `2` External, `3` Unknown(string) |
| `Binding` | `0` Local, `1` Global, `2` Weak, `3` Unknown(string) |
| `Payload` | `0` Register(u64), `1` Value(i128), `2` Symbol(string), `3` Empty |
| `ModifierValue` | `0` Int(i128), `1` Text(string), `2` Bool(bool) |
| `FixupTarget` | `0` Symbol(string), `1` Absolute(u64), `2` SectionRelative(string), `3` Unknown(string) |
| `PcRule` | `0` None, `1` PcrelBegin, `2` PcrelEnd, `3` PcrelPage, `4` PcrelHi, `5` Unknown(string) |
| `Transform` | `0` Identity, `1` Scale, `2` Page, `3` Hi20, `4` Lo12I, `5` Lo12S, `6` PcrelHi20, `7` PcrelLo12, `8` Unknown(string) |
| `Mode` | `0` ResolveInPlace, `1` EmitRelocation, `2` Unknown(string) |
| `PairRole` | `0` Hi, `1` Lo, `2` Unknown(string) |

An `Unknown` variant carries its name. Two different unknown names are two
different facts (`an_unknown_variant_is_payload_carrying_and_distinct`); the
variant number is not a wildcard.

## 4. `Plan.legacy_document` is a legacy-only input

**Decision.** `Plan.document` is renamed `legacy_document`. It exists for one
reader: `fmp_materialize::fingerprint()`, which hashes the canonical form of the
raw document so its output stays byte-for-byte unchanged (`ADR-0123`). `bind`,
`ParsedPlanIdentity` and every encoding/layout/fixup decision read parsed
fields. `fingerprint`'s output is still an Artifact field, so `legacy_document`
still influences `payload_digest` **through the legacy fingerprint**; that is
not the new identity reading the raw document.

**Counterexample for deleting it now.** The 128 recorded payloads include
`source_trace` in the fingerprint. Deleting `legacy_document` and re-deriving
the fingerprint from parsed fields would move `payload_root`, which `HE-AC-10`
forbids. The `a_legacy_fingerprint_covers_document_fields_the_parser_drops` test
pins the sensitivity, and `he1_baseline.py --check` confirms the projection did
not move in H1a.

**Counterexample for letting identity read it.** H0 already measured the
consequence: a changed parsed operand can leave the fingerprint stable, and a
`source_trace`-only change moves it. The new identity must not inherit either
behaviour.

## 5. Fixed vectors and the independent recomputation

Three plans are pinned. Each digest is asserted by a Rust unit test
(`the_three_protocol_vectors_are_stable`) and by `tools/plan_identity.py
--check`, which encodes the same three facts from the protocol text in Python.

| Vector | Shape | `sha256` digest |
|---|---|---|
| `minimal` | Empty vectors, no options, `artifact = bytes`, `symbol_order = none` | `sha256:a48faecec39dd1de38f13b4868559f307b575a95a0aa241a01caa325400422c4` |
| `data-fragment` | One image-backed `.text` section with a one-byte `Data("90")` fragment; `section_order = [".text"]` | `sha256:9da5a3318e943bcbd5c9c32366708922b68a5e7e7c67a0b3d48a9c7b1a68eec2` |
| `unknown-variants` | Every `Unknown` variant, all three `ModifierValue` payload shapes, one of each covered element | `sha256:1a07ae98cba50f7ee65b36bbe2bb1684eaa0885f728270b9baa39824a2a4632a` |

`source_ref = Some(...)` is **not** covered by these three vectors: all of them
use `None`. The field is still covered by the Rust mutation table
(`plan_identity_covers_every_parsed_field`, row `definition.source_ref`), so the
encoder is not untested, but the `Some` branch has no fixed cross-language
vector. H1a review corrected the earlier claim rather than changing the three
frozen vectors.

The `minimal` facts are 376 bytes and begin with the root `0x08`:

```text
08040700000000000000666d702f302e310804030000000000000078383604060000000000000078
38362d36340402000000000000003634070000000000000000070000000000000000040600000000
0000006c6974746c650240000000000000000410000000000000002f7461726765745f6964656e74
69747908040e000000000000006d6f6e61736d2e6973612e783836040600000000000000302e3735
2e300447000000000000007368613235363a61616161616161616161616161616161616161616161
61616161616161616161616161616161616161616161616161616161616161616161616161616161
6161050414000000000000002f646566696e6974696f6e5f6964656e746974790809000000000700
0000000000000005040e0000000000000073656374696f6e5f6f6666736574010001000410000000
000000002f6f75747075745f636f6e74726163740700000000000000000700000000000000000700
00000000000000070000000000000000
```

Recompute a vector with:

```text
python tools/plan_identity.py --check
```

The script prints `name`, `digest` and `facts=<hex>` for all three and exits
non-zero if a pinned digest does not match. The `documents` job of
`.github/workflows/gates.yml` runs this command, so the Python reference encoder
is exercised on every hosted run (H1a review).

**What this evidence does and does not prove.** Rust and Python were written
independently from the tables above, in different languages with different
default integer and string layouts. Agreement therefore catches a transcription
error, an implicit length or a language-specific layout assumption. It does not
catch a misreading shared by both implementations; the normative tables in §3
and the exhaustive destructuring/mutation table in §2 are the controls for
that. No shipped byte stream is checked against a third implementation, and this
ADR does not claim one.

## 6. `plan::check_structure` re-checks only what the type system cannot hold

**Decision.** `Plan` stays a public mutable DTO by design (D13): the planner API
and the negative corpus build illegal states by editing fields after
`plan::read`. `plan::check_structure(&Plan) -> Vec<Diagnostic>` re-runs exactly
the parser rules the DTO cannot express:

| Rule | Diagnostic |
|---|---|
| `format_version == "fmp/0.1"` | `E-PLAN-001` at `/format_version`, details `found`/`supported` |
| Each `FragmentBody::Data` payload is even-length lowercase hex | `E-PLAN-002` at `<fragment>/payload_hex`, `path_type = "lowercase hex bytes"`, `found_kind` = the text |
| `FieldRange.lsb <= 127` | `E-PLAN-002` at the field's `/lsb`, `path_type = "u7"`, `found_kind = "integer 128"` |
| `FieldRange.width` in `1..=64` | `E-PLAN-002` at `/width`, `path_type = "u7"` |
| `RangeConstraint.bits` in `1..=64` | `E-PLAN-002` at `/bits`, `path_type = "u7"` |
| `RangeConstraint.align_bits <= 12` | `E-PLAN-002` at `/align_bits`, `path_type = "u4"` |
| `Fixup.transform_shift <= 63` | `E-PLAN-002` at `/transform_shift`, `path_type = "u6"` |

Codes, pointers and detail keys are copied from `plan::read`, so a legal plan
produces no new output and a mutated DTO produces the same diagnostic it would
have produced as JSON.

It deliberately does **not** repeat:

- object shape, field presence, integer domains and enum spellings, which
  `bind_document` has already turned into concrete types;
- `payload_hex` length versus `fragment.size` (`E-LAYOUT-002` in
  `check_fragments`);
- descriptor width sum versus `range_constraint.bits` (`E-FIXUP-001` in
  `check_fixup_descriptor`);
- overlap or ownership (`check_fixup_overlap` / `check_fixup_ownership`).

It never reads `legacy_document`, so a plan edited only in its raw document is
not rejected here for a fact this function does not own.

**Stage placement.** H1b's `bind` calls `check_structure` before the definition
identity comparison and before `check`, so no shift, sum or bit loop sees an
out-of-domain value. H1a does not have `bind`; the tests call
`check_structure`/`check` directly (§9). That is a stage boundary, not a weaker
requirement: the same input must be rejected at `check_structure` once `bind`
exists, and H1b's replay table asserts it.

## 7. Numeric hardening and the `page` precondition (D14, D16)

### 7.1 What `check` does now

| Site | Before | After |
|---|---|---|
| `cover_state` slot end and intersection | `u32` `offset + width` | `u64` endpoints; `u64` intersection |
| `check_fixup_descriptor` field end | `u32` `lsb + width` | `u64` |
| `check_fixup_descriptor` width sum | `u32` sum | `u64` sum |
| descriptor overlap comparison | `u32` sums | `u64` sums |
| `check_fixup_overlap` absolute bit position | `u64` `offset * 8 + lsb` | `u128` `offset as u128 * 8 + lsb` |
| `check_one_writer` / `check_fixup_ownership` bit loops | `lsb .. lsb + width` (`u32::MAX` possible) | `lsb .. min(lsb + width, form.bits())` |
| register field width | `1u64 << field_bits` (panics at 64 in debug) | `1u128.checked_shl(field_bits)` (no panic; a `u64` register fits any field ≥ 64) |
| register field encoding (`fmp-materialize` `write_field`) | `value & mask(width_bits)`, then `masked >> remaining` in `i128` | each placement is extracted directly from the low 128 bits of a `u128`; every higher bit is `value`'s sign bit |
| alignment unit | `1i128 << align_bits` | `1i128.checked_shl(align_bits)`; a non-zero value at an unrepresentable alignment is misaligned |
| signed/unsigned range | `1i128 << (bits - 1)`, `1i128 << bits` | `checked_shl`; an unrepresentable half becomes the open bound instead of a panic |

The exact counterexamples:

- `a_descriptor_width_sum_cannot_overflow` sets two `field_descriptor` entries
  with `width = u32::MAX`. Before the change the `u32` sum wrapped and
  `lsb + width` could wrap; the loop could iterate ~4·10⁹ times. After the
  change `check` returns `E-FIXUP-001`/`E-FIXUP-005` in bounded time.
- `two_huge_fixup_offsets_do_not_overflow` injects `offset = u64::MAX` and
  `u64::MAX - 8` into the **JSON** and re-reads it, so the parser's `u64` domain
  is respected and only `offset * 8` is under test. Before the change the
  multiplication wrapped and could invent or miss an overlap; after the change
  the plan is rejected at `/fixups/0/offset` and `/fixups/1/offset` with no
  `E-INTERNAL-001`.
- `a_wide_register_field_does_not_overflow_the_width_check` builds definitions
  whose `reg_number` slot sums to 64 and to 128 bits. `reg_number` slots may not
  declare `range`, so the loader bounds each placement to 64 but not their sum;
  `width_bits == 64` is the first value that makes `1u64 << 64` overflow in
  debug. Both definitions load and `check` accepts register `0` without a panic
  or a spurious `E-OPERAND-004`. The fix is the `u128` comparison, not a
  load-time bound: a wide field is a legal definition fact, only the comparison
  was unsafe. This test uses register `0` and stops at `check`; it is not
  encoding evidence.
- `a_wide_register_field_encodes_the_same_bytes_in_every_build`
  (`fmp-materialize/tests/he1_wide_register.rs`) closes the other half. It
  builds 64-, 127-, 128- and 192-bit fields with **non-zero** registers and
  asserts the exact bytes from `materialize` after `check_structure` and
  `check` are empty. Before the fix the 127-bit case panicked in debug
  (`(1i128 << 127) - 1`) and the 192-bit case succeeded in release while also
  writing the value into the *first* 64-bit placement (`>> 128` wrapped). The
  test runs in debug and release, locally and in CI (§10); a zero register
  would have hidden the release defect because the wrong chunk is also zero.

**Entry boundary.** Two `width = u32::MAX` entries are **structurally** illegal
under D13. Once `bind` exists they must be rejected by `check_structure` with
`E-PLAN-002` and must never reach `check`. H1a's direct `check` call proves the
second line of defence only; it is not the intended entry point for that input.

**Legal outputs unchanged.** Every 128 positive payload is byte-identical
(`payload_root` in §9) and the 619 negative triples are unchanged. The
arithmetic changes only paths that previously overflowed or looped.

### 7.2 `page` requires `pcrel_page`

`03_fixup_model.md` gives `page` the value
`v = (page(S + A) - page(P)) >> 12`, with `page(x) = x & !0xFFF`, and names
`pcrel_page` as "page base of `P`" (`ADR-0127` context: `A64-P6`). Without a PC
rule there is no `P`, so the kind is not resolvable.

**Decision.** `Check_fixup_kind` rejects `Transform::Page` unless
`pc_reference_rule == PcrelPage`:

- code `E-FIXUP-001`;
- pointer `<fixup>/pc_reference_rule`;
- details `kind = "value_transform:page"`, `form_id = ""`,
  `field = "page requires pc_reference_rule pcrel_page"`.

The rule is phrased as "what the transform needs", not as an AArch64 branch, so
another target that uses `page` gets the same precondition.

**Counterexample.** Before H1a, `A64-P6-adrp-lo12-pair` with
`fixups[0].pc_reference_rule = none` passed `check` and fell into the
`internal(...)` arm in `emit` (`fmp-materialize/src/lib.rs`, "value_transform
`page` needs a pc_reference_rule"). `a_page_transform_without_a_page_pc_rule_is_rejected`
asserts the static rejection and the absence of `E-INTERNAL-001`.

## 8. Every `internal(...)` branch has a static precondition

`materialize` is still the H0 shape in H1a, so this table decides what H1b may
keep as `Internal`; it does not by itself change the return type. The column
"Precondition" names the validator rule that makes the branch unreachable for a
plan that passed `check`. All line numbers are from the H1a tree.

| Site | Message | Static precondition | Disposition |
|---|---|---|---|
| `:384` | section_order names an unvalidated section | `check_layout`: `section_order` is a permutation of `sections[]` (`E-LAYOUT-006`) | not plan-triggerable; keep `Internal` |
| `:393` | validated image size does not fit the host | `check_layout`: total declared image ≤ 64 MiB (`E-LIMIT-001`); 64 MiB < `usize::MAX` on every supported host | host-domain guard; H1b does not classify it as `Internal` |
| `:401` | image reservation failed | request is bounded by `E-LIMIT-001`; failure depends on host memory, not on the plan | H1b maps it to `MaterializationFailure::HostFailure` (`HostFault`) |
| `:425` | fragment names an unvalidated instruction | `check_fragments`: an instruction fragment names an existing instruction in the same section at the same offset and size (`E-LAYOUT-003`) | not plan-triggerable; keep `Internal` |
| `:470` | symbol_order names an unvalidated symbol | `check_layout`: when present, `symbol_order` equals `symbols[]` exactly (`E-LAYOUT-004`) | not plan-triggerable; keep `Internal` |
| `:500` | an unvalidated artifact value reached emission | `check_output`: `Artifact::Unknown` is `E-VERSION-001` (`artifact:<name>`) | not plan-triggerable; keep `Internal` |
| `:566` | validated form disappeared | `check_instructions`: a named form exists in the bound definition (`E-FORM-001`) | not plan-triggerable; keep `Internal` |
| `:675` | validated pcrel_hi pair disappeared | `check_fixup_pairs`: a pair group has exactly one `hi` and at least one `lo` (`E-FIXUP-007`) | not plan-triggerable; keep `Internal` |
| `:729` | value_transform `page` needs a pc_reference_rule | **new in H1a:** `check_fixup_kind` requires `page ⇒ pcrel_page` (`E-FIXUP-001`, §7.2) | closed; remains a defensive arm |
| `:748` | validated transform disappeared | `check_fixup_kind`: `lo12_s` and `unknown` transforms are `E-VERSION-001` | not plan-triggerable; keep `Internal` |
| `:777` | validated resolution_mode disappeared | `check_fixup_kind`: `Mode::Unknown` is `E-VERSION-001` (`resolution_mode:<name>`) | not plan-triggerable; keep `Internal` |
| `:803` | validated target kind disappeared | `check_fixup_target`: `section_relative` is `E-VERSION-001` (`target.kind:section_relative`) | not plan-triggerable; keep `Internal` |
| `:809` | validated symbol disappeared | `check_fixup_target`: a named symbol exists (`E-SYMBOL-001`) | not plan-triggerable; keep `Internal` |
| `:812` | validated symbol has no location | `check_fixup_target`: `resolve_in_place` requires a `defined` symbol with an offset (`E-FIXUP-002`) | not plan-triggerable; keep `Internal` |
| `:839` | validated target kind disappeared | `check_fixup_kind`/`check_fixup_target`: `target.kind:unknown` is `E-VERSION-001` | not plan-triggerable; keep `Internal` |

The audit found exactly one plan-triggerable branch, `:729`; §7.2 closes it.
The two host-domain branches (`:393`, `:401`) are not "the plan broke an
invariant" and must not share the `Internal` channel in H1b. The other twelve
are genuinely unreachable after `check`, and H1b's `Internal` variant is for
them alone.

## 9. Post-encode failures are measured, not assumed

`fmp_validate::check` is steps 2–7 of `docs/fmp-v0/01_contract.md`;
`fmp_materialize::materialize` re-runs it and then encodes.
`he1_stage_boundaries.rs` asserts both columns for each recorded negative:

| Fixture | Code | `check` | `materialize` | Value-level snapshot H1b adds |
|---|---|---|---|---|
| `N13-expected-digest-mismatch` | `E-BYTE-001` | empty | `E-BYTE-001` | `declared`, `actual` |
| `N20-loadlit-fixup-misaligned` | `E-RANGE-003` | empty | `E-RANGE-003` | `required_align`, `value` |
| `N04b-rel32-absolute-out-of-range` | `E-FIXUP-003` | empty | `E-FIXUP-003` | `min`, `max`, `value` |
| `N04f-absolute-address-in-imm8-field` | `E-FIXUP-003` | empty | `E-FIXUP-003` | `min`, `max`, `value` |
| `N05-expected-size-mismatch` | `E-SIZE-001` | `E-SIZE-001` | `E-SIZE-001` | none — static rejection |
| `N05b-huge-expected-size` | `E-SIZE-001` + `E-LAYOUT-003` | rejected | rejected | none — static rejection |

The measured set is **four fixtures, three codes**. The withdrawn H0 statement
"only `E-SIZE-001`/`E-BYTE-001` fail after encoding" counted a code, not a
fixture, and included a static rejection. H1b adds the value-level assertions to
these four when `MaterializationFailure::PostEncodeAssertion` exists; the other
615 negatives keep the code + Pointer + detail-key-set gate
(`fixtures.rs::negatives_produce_exactly_the_registered_diagnostics`). This ADR
does not claim byte-identical diagnostic arrays for the whole corpus.

## 10. Dependency direction is executable

The validator may depend on the model; the materializer may depend on both; the
validator must never depend on the materializer, or `check` could reach the
encoder and "verified" would silently mean "emitted". `.github/workflows/gates.yml`
now runs, in the `workspace` job:

```text
cargo tree -p fmp-validate --edges normal
```

and fails if the graph contains `fmp-materialize`. `--edges normal` deliberately
excludes dev-dependencies, so a test-only edge is allowed; the shipped graph is
what the check owns. Local run in H1a:

```text
fmp-validate v0.0.0
└── fmp-model v0.0.0
    └── sha2 v0.10.9
        └── cfg-if v1.0.4
        └── cpufeatures v0.2.17
        └── digest v0.10.7
            └── block-buffer v0.10.4
            └── crypto-common v0.1.7
```

No `fmp-materialize` edge exists. The step is a review guard, not a substitute
for reading the manifest: it catches the direction, not a new crate's purpose.

## 11. What H1a does not decide

- It does not add `ValidatedPlan`, `bind`, `BindIdentity`, the new
  `materialize`, `Materialization`, `ExecutionReceipt`,
  `MaterializationFailure`, `HostFault` or the CLI failure split. Those are H1b
  (`docs/architecture/he1-h1-plan.md` §3.2–§3.4).
- It does not turn `ParsedPlanIdentity` into the execution credential. Until
  `bind` compares `(namespace, version, digest)` against the bound
  `Arc<Definition>`, the old `materialize` still compares only the digest. The
  identity is frozen now so H1b can bind it, not because it is already enforced.
- It does not change `definitions/**`, `fixtures/**`, `docs/fmp-v0/**`, the 128
  payloads or `definitions_root`.
- It adds no error code. The new rejections use `E-PLAN-001`, `E-PLAN-002` and
  `E-FIXUP-001`, all already registered.
- It adds no hand-maintained third count. The legacy corpus counts stay in
  `STATUS.md`; the test counts in `research/he1/H1-report.md` are generated from
  one run.

## 12. Evidence

All commands were run from `C:\Users\hanni\Projects\MonAsm` unless the row says
`prototype/`.

| Command | Result |
|---|---|
| `cargo fmt --all -- --check` (`prototype/`) | exit 0 |
| `cargo test --workspace` (`prototype/`) | 89 passed, 0 failed: `fmp-model` 33 unit + 5 structure + 3 doctests, `fmp-validate` 4 bounds, `fmp-materialize` 9 unit + 4 stage + 1 wide, `fmp-plan` 5, `fmp-cli` 6 determinism + 2 fixtures + 7 characterization + 10 planner parity |
| `cargo test --release -p fmp-validate --test he1_validation_bounds` (`prototype/`) | 4 passed, 0 failed |
| `cargo test --release -p fmp-materialize --test he1_wide_register` (`prototype/`) | 1 passed, 0 failed |
| `python tools/check_ids.py` | `OK (0 warning(s))` |
| `python tools/check_definition.py` | `OK`; 104 documents, newest x86 `0.78.0` (632 forms) |
| `python tools/plan_identity.py --check` | three pinned digests match (§5) |
| `python tools/he1_baseline.py --check research/he1/compatibility-results.json` | `OK: payload projection identical`; `payload_root sha256:3f6d177d…ffefad9`; `definitions_root sha256:575b7c5f…35690e` |
| `cargo tree -p fmp-validate --edges normal` (`prototype/`) | no `fmp-materialize` edge (§10) |

`research/he1/H1-report.md` records the same run with the test names, the three
vector recomputations and the run identity (`base_commit` `0948620…`, code
commit `d2cd7dd…`, `prototype/` tree `e31c88ae…`, CI run/job IDs). It is
evidence, not a build input.
