# Error Model

Status: **frozen for the v0 scope** (`ADR-0095`). Error identity is part of the
contract; error prose is not.

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
| E-PLAN-001 | Unknown or unsupported `format_version` | `found`, `supported` | N24a |
| E-PLAN-002 | Value has the wrong type or literal form (a non-integer number, a malformed hex byte string), or lies outside the declared domain for its path (a zero-width `field_descriptor` range, a zero-bit `range_constraint`) | `path_type`, `found_kind` | N23a, N25a, N25b |
| E-PLAN-003 | Unknown field in a strict object | `field`, `object` | N21a, N21b |
| E-PLAN-004 | Document is not parseable, or has duplicate keys | `reason` | unit `rejects_duplicate_keys` |
| E-PLAN-005 | Canonical-form violation that changes bytes (e.g. float, BOM, CRLF-dependent content) | `reason` | unit `rejects_a_byte_order_mark` |
| E-PLAN-006 | Required field absent from a strict object | `field`, `object` | N24b |
| E-TARGET-001 | Unsupported or mismatched `isa_family`, `isa_variant`, or `enabled_extensions` (under `fmp-def/0.2`, an extension the table does not declare) | `found` | N06, N06c |
| E-TARGET-002 | Invalid or missing `execution_mode` for the family | `found`, `required` | N24c |
| E-TARGET-003 | A named form's `requires_extensions` is not a subset of the plan's `enabled_extensions` (`fmp-def/0.2`) | `extension`, `form_id` | N06b |
| E-TARGET-004 | Unsupported `byte_order` or `address_width` | `found` | N24d |
| E-DEF-001 | The definition cannot be loaded (unknown `definition_format`, duplicate form, bad template or placement, a template with more than `u32::MAX` bits, a placement end beyond `u64`), or `definition_identity.digest` does not match the loaded definition | `declared`, `actual`, `reason` | N10 |
| E-DEF-002 | Namespace or version not available in this materializer | `namespace`, `version` | EXP-R5 |
| E-FORM-001 | `form_id` is not present in the pinned definition | `form_id`, `namespace`, `version` | N01 |
| E-OPERAND-001 | Operand kind or register class does not match the form | `expected`, `found` | N02 |
| E-OPERAND-002 | Operand count or role sequence mismatch | `expected`, `found` | N02e |
| E-OPERAND-003 | Operand payload malformed for its kind: a composite memory payload, a `symbol_id` on a non-`target` role, an empty payload with no covering fixup, a modifier the slot does not permit | `kind`, `reason` | N15b, N15c, N19, N19b, N19c |
| E-OPERAND-004 | Operand value is not representable in the slot's field width (register number wider than the encoded field) | `target_type`, `value`, `field_bits` | N14 |
| E-RANGE-001 | Immediate outside the legal encoding range | `min`, `max`, `value`, `target_type` | N03, N18a, N18b |
| E-RANGE-002 | Displacement or branch offset outside the legal range | `min`, `max`, `value`, `bits`, `align_bits` | N04 |
| E-RANGE-003 | Alignment requirement not met | `required_align`, `value` | N20 |
| E-RANGE-004 | Operand value is excluded by the slot's declared domain | `target_type`, `value`, `excluded` | N16a, N16b |
| E-LAYOUT-001 | Fragments overlap | `first`, `second` | N09 |
| E-LAYOUT-002 | Fragment gap, or fragment sum != `declared_size` | `declared`, `covered` | N11 |
| E-LAYOUT-003 | Instruction offset/size does not match its fragment | `instruction_id`, `fragment` | N05 |
| E-LAYOUT-004 | List order violates the contract's declared order | `list`, `index` | N22a, N22f |
| E-LAYOUT-005 | Layout requires the materializer to compute padding or alignment | `section_id`, `offset`, `required_align` | — (unreachable, §2.3) |
| E-LAYOUT-006 | Duplicate `section_id`, or `section_order` is not a permutation of `sections[]` | `section_id`, `problem` | N22b, N22c |
| E-LAYOUT-007 | Duplicate `instruction_id`, or two instructions at the same `(section_id, offset)` | `instruction_id`, `section_id`, `offset` | N22d, N22e |
| E-LIMIT-001 | The sum of `declared_size` over `section_order` exceeds the 64 MiB image ceiling | `limit`, `actual` | N24l |
| E-SYMBOL-001 | A reference names a `symbol_id` that `symbols[]` does not declare | `symbol_id`, `mode` | N08 |
| E-SYMBOL-002 | Duplicate `symbol_id`, or duplicate emitted name with conflicting binding | `symbol_id` | N24e |
| E-SYMBOL-003 | Defined symbol without a resolvable location: `section_id`/`offset` missing, `section_id` names no section, or `offset > declared_size` (equality is the legal one-past-the-end label) | `symbol_id` | N24f, N24k |
| E-FIXUP-001 | Fixup is incompatible with the form, the descriptor, or the instruction's operands: the fixup kind does not fit the form (including a `hi20` transform whose `pc_reference_rule` is not `none`); the descriptor widths do not sum to `range_constraint.bits`; the descriptor covers no `operand_value` slot or more than one, a range is not contained in one placement of its slot, or the ranges are not in the slot's placement order; a target operand and `fixup.target` disagree | `kind`, `form_id`, `field` | N07, N07f, N07g, N07h |
| E-FIXUP-002 | Target has no address in a `resolve_in_place` fixup: an undefined or external symbol; a symbol target whose section has no `base_address`, including a same-section symbol under `pc_reference_rule = none` (only `pcrel_begin`/`pcrel_end`/`pcrel_hi` may use offsets alone); or an `absolute` target under a PC rule whose site section has no `base_address` | `fixup_id`, `target` | N08 |
| E-FIXUP-003 | Computed fixup value outside `range_constraint` | `fixup_id`, `min`, `max`, `value` | N04 |
| E-FIXUP-005 | Field descriptor out of bounds or self-overlapping, or the site is not the first byte of a planned instruction | `fixup_id`, `descriptor` | N07 |
| E-FIXUP-006 | Two writers patch overlapping bits — two fixups, a fixup and a non-zero template bit, or an operand-supplied field (a `reg_number` slot, or any inverted placement) and a fixup | `first`, `second` | N07, N07c |
| E-FIXUP-007 | Pair group incomplete or inconsistent: no `hi`, more than one `hi`, no `lo`, a target mismatch, a `pcrel_hi` member whose `hi` is in another section, or `pair_role` without `pair_group` | `pair_group`, `problem` | N12, N17b, N17c |
| E-FIXUP-008 | Duplicate `fixup_id` | `fixup_id`, `offset` | N24g |
| E-FIXUP-009 | Fixup addend not allowed by its kind: an RV64 `pcrel_lo12` low half with a non-zero `addend` | `fixup_id`, `addend`, `value_transform` | N17a |
| E-SIZE-001 | Encoded length != `expected_size`, or `expected_size` != the named form's size at validation time | `instruction_id`, `expected`, `actual` | N05, N05b |
| E-BYTE-001 | Emitted bytes do not match `expected_digest` | `instruction_id`, `declared`, `actual` | N13 |
| E-VERSION-001 | Materializer cannot honor a declared plan feature (`emit_fixups: false`, a Level 0 symbol-table request, `target.kind: section_relative`) | `feature`, `format_version` | N24h, N24i, N24j |
| E-INTERNAL-001 | Internal invariant violated (bug); never used for user input | `invariant` | — (not user-reachable) |

`E-PLAN-002`'s two detail keys describe one fault from two sides: `path_type` is
what the path requires (`integer`, `u64`, `i64`, `address`), and `found_kind` is
what the document supplied (`string`, `float`, `boolean`, `integer -1`). The
pair is enough to reproduce the failure without the free-text message, which is
why the code keeps both.

### 2.1 Counterexamples behind specific codes

A code without a concrete failure is decoration. This list records the observed
failure each code exists to prevent, or says `planned` when no observation
exists yet. `observed` means a built assembler produced the failure or the
rejection; `derived` means it follows from a measured byte sequence.

- `E-RANGE-002` — observed, F-06: XirAsm emits `eb 80` for `jmp short 0x82`,
  silently truncating a target that does not fit. Measured 2026-11-04: llvm-mc
  shortens `jmp .+0x81` to `eb 7f` (2 B) but promotes `jmp .+0x82` to
  `e9 7d 00 00 00` (5 B). A materializer that computes a displacement and then
  truncates it, or re-forms the branch, is rejected here. The AArch64 case is the
  same refusal without a shorter form to promote to: `imm19` holds
  `[-262144, 262143]` field units, so the reachable byte range is
  `-1048576 … +1048572`, and `262144` is `N04c` (`EXP-0014` §3 measured both ends;
  an encoder cannot widen `b.cond` to `b` without changing either the instruction
  or the condition). The literal load reuses the same field and the same refusal
  on a non-branch row: `ldr x0, #1048576` is rejected, `262144` is `N04d`, and
  the field's byte range is the same `-1048576 … +1048572` (`EXP-0025` §2).
- `E-FIXUP-003` — observed, F-06 (label path): XirAsm rejects an out-of-range
  label with "does not fit the signed 8-bit displacement". The same condition on
  a planned fixup is this code.
- `E-RANGE-001` — observed, F-10: XirAsm rejects `addi a0, a1, 2048` and
  `addi a0, a1, -2049`. The RV64 slice reproduces the boundary. The AArch64
  counterexample is a value that another form *could* encode: `add x0, x1,
  #0x1000` is legal as `-lsl12` but is out of `imm12` for `-lsl0`, and `llvm-mc`
  accepts it by switching forms (`EV-26`, `EXP-0013` §2). A materializer rejects
  it instead (`N18a`); the converse, `0x123000` on `-lsl12`, is `N18b`. The code
  is the same because the failure is the same: the value is not in the named
  form's field. The `b.cond` case is the same shape one level down: `cond = 16`
  is a plausible number for "one past the last condition" but the field is four
  bits, and masking it yields `0x0`, which is `eq` — an accepted branch on the
  wrong condition (`N03`, `EXP-0014` §2). The range check is what turns that into
  a rejection instead of a silently different program. The load/store `disp`
  ranges are the same shape one field over: `imm12` holds `0…4095` field units
  and `imm9` holds `−256…255` signed bytes, so the assembler's `#32760` is `4095`
  while `#32768` has no encoding, and `4096` or `−257` is `N03` (`EXP-0015` §2).
  The store rows are the same field on the other half of the family, so `−257`
  on `str/x64-base-imm9-post` and `256` on `stur/x64-base-imm9` are `N03` too
  (`EXP-0024` §2).
  Widening `imm9` to `imm12` would be a different addressing kind, which is a
  different `form_id`; the materializer may not do it to make the value fit.
- `E-OPERAND-001` — observed, F-10: `c.addi a6, 5` (x16) is rejected because the
  compressed register class is `x8..x15`. A register-class violation is a
  legality rule, never a widening opportunity.
- `E-OPERAND-002` — observed, `EXP-0023` §4: `aarch64:cmp/x64-x64-lsl0` has two
  slots (`src`, `src2`), because the alias fixes `Rd = 31` and drops the
  destination, and a plan that passes `dest` as well carries three operands.
  Rejecting the count is the only honest outcome: ignoring the extra operand
  would accept a plan that states a register the mnemonic cannot name, and
  honouring it would make `Rd` depend on an operand value instead of the form
  (`INV-01`, `INV-07`). The test is `N02e`, which reports `expected: 2`,
  `found: 3` at `/instructions/0/operands`.
- `E-OPERAND-004` — observed, `EXP-0004` §3: the v0 x86 `ModRM` field is 3 bits
  and the `REX` byte is pinned to `0x48`, so `r9` is not encodable. Truncating 9
  (`0b1001`) to 3 bits yields `0b001`, and `48 89 c8` decodes as
  `movq %rcx, %rax` — measured, not argued. `r9` fits `x86.gpr64` and therefore
  passes `E-OPERAND-001`; the failure is that the form's field is too narrow,
  which is a different diagnostic from "the form does not accept this class".
- `E-OPERAND-003` — derived, ADR-0015: a `modifiers` entry is a guard and never
  writes a bit. `{ "name": "lsl", "value": 3 }` on the `src2` of
  `aarch64:add/x64-x64-x64-lsl0` would have to move `shift`/`imm6` to be honoured,
  and the same entry on the `index` of `aarch64:ldr/x64-base-regoff-lsl0` would
  have to set `S`. These are refused (`N19`, `N19b`, `N19c`); accepting and
  ignoring them
  would emit the unshifted word and report success.
- `E-SIZE-001` — observed, `EXP-0002` W1: a definition drift that changes the
  encoded length is caught by `expected_size` alone.
- `E-BYTE-001` — observed, `EXP-0002` W2: a same-length encoder defect emits
  `49 89 d8` where the plan meant `48 89 d8`. Both are 3 bytes and both are
  legal; only the digest distinguishes them. In `EXP-0002`'s generator the digest
  is hashed from the oracle's bytes, not from the materializer's output.
- `E-FORM-001` — derived, ADR-0004: the v0 x86 slice has no coarse form such as
  `x86:mov/r64-r64`. A plan naming one must be rejected, not resolved to a
  default variant. The test is N01; it runs in Phase 3.
- `E-DEF-001` — partly measured, `EXP-0004` §4: a one-bit change to an immediate
  range moves the definition digest, and a formatting-only change does not. The
  end-to-end case (a plan whose `definition_identity.digest` does not match the
  loaded definition) is `N10` and runs in Phase 3; until then the plan-side half
  must not be cited as evidenced.
- `E-RANGE-003` — derived, OD-09: an AArch64 `b` targets `.text+2`. The
  displacement is not a multiple of 4, and `imm26 = D >> 2` would silently drop
  the low two bits, branching 2 bytes before the requested address. Reject
  rather than round. `N20` is the first fixture: a `pcrel_begin` literal-load
  fixup whose target is 2 bytes away is refused at `/fixups/0/value_transform`
  with `required_align 2` and `value 2`, after the field itself was checked and
  found in range (`EXP-0025` §3).
- `E-RANGE-004` — observed, `EXP-0012` §2: `c.addi a0, 0` is accepted by
  `llvm-mc 23.1.2` and encodes `01 05`, which `llvm-objdump` prints as
  `c.addi a0, 0x0`; `c.addi x0, 1` encodes `05 00` and prints as `c.nop 0x1`.
  Both values are inside the declared field range (`imm` is `[-32, 31]`, `rd` is
  `0..31`), so `E-RANGE-001` cannot fire, and both encodings are reserved HINTs
  rather than the addition the plan names. The slot's `excluded: [0]` rejects
  them; the check is a lookup, not a predicate (ADR-0009, `OD-14`). The test is
  N16 (`N16a` and `N16b`).
- `E-FIXUP-002` — derived, OD-02 (`03_fixup_model.md` §5.1): a plan names an
  external `call` target and `resolve_in_place`. There is no `S` to compute, so
  the only honest outcomes are "refuse" (this code) or "emit zero", and zero
  turns the call into a branch to itself. Level 1 would write the record instead;
  that is `emit_relocation`, a different mode the plan must name. The same code
  covers the missing-origin cases: a cross-section reference whose section has no
  `base_address`, and an `absolute` target under `pcrel_begin`/`pcrel_end`/
  `pcrel_page` whose *site* section has none. Reading either missing base as zero
  would silently place the section at address 0 (`03_fixup_model.md` §4).
- `E-SYMBOL-001` — derived, N08: the plan references `symbol_id: "S9"` with no
  entry in `symbols[]`. This is not a resolution policy question, because no
  policy can supply an identity the plan never defined.
- `E-FIXUP-006` — derived, OD-02 (`03_fixup_model.md` §3): an `add` fixup covers
  `imm12` and the same instruction's `lo12` operand also carries `value: 5`. Two
  writers, one field; whichever wins, the plan contained a number that was
  discarded without a diagnostic. The measured counterexample is a descriptor
  over a `reg_number` slot: on `x86:mov/rm-r64/legacy` the encoder writes `ModRM`
  bits 0-2 and 19-21 from the two operands, and a fixup over those bits wrote them
  again after the operands, so one of the plan's two statements was silently
  dropped (`N07`, before `ADR-0121`). The same rule covers an inverted placement,
  because inversion is the operand path's polarity, not a value the fixup owns.
- `E-VERSION-001` — derived, OD-02 (`03_fixup_model.md` §10): a plan writes
  `value_transform: "got_pcrel"`. `fmp/0.1` has no such member, so the plan
  declares a feature the format version cannot honour; treating it as a plain
  PC-relative record would silently drop the GOT indirection.
- `E-PLAN-006` — derived, contract §13 step 1: an instruction that omits
  `expected_size`. Without this code the absence has to be read as "no
  constraint", and the size check then passes vacuously — a defaulted field in
  the one place `INV-03` depends on it. The strict-object check therefore reports
  a missing field instead of letting the field's consumer see `None`. The same
  code covers the one conditional requirement in `fmp/0.1`: contract §7 says a
  plan that carries any `expected_digest` MUST name its derivation source in
  `provenance.generated_by`. A digest whose provenance is unknown is
  indistinguishable from one the encoder under test produced, which is the case
  `E-BYTE-001` exists to catch, so the field is reported as required rather than
  read as "no source".
- `E-LAYOUT-006` — derived, contract §12: a plan with two sections whose
  `section_id` is both `.text`. A fixup naming `.text` then has two candidate
  sites and the materializer must pick one, which is a choice it has no authority
  to make. The same code covers `section_order` naming a subset of `sections[]`:
  the unnamed section's bytes would vanish from the image with no diagnostic.
- `E-LAYOUT-007` — derived, contract §7 against §12. Two instructions both named
  `I0001`, at offsets 0 and 4: the fragment whose `instruction_id` is `I0001`
  resolves to the first, so the second is fully validated and then never emitted.
  Two instructions at the same `(section_id, offset)` are the same fault from the
  other side — one fragment names one of them, and which one wins is list order,
  the implicit tie-break §3 forbids. `instruction_id` is therefore required to be
  unique, and `(section_id, offset)` to be unique, before emission is ordered.
- `E-FIXUP-007` — derived, `03_fixup_model.md` §7 (ADR-0010): a fixup that names
  `pcrel_hi` but has no `pair_role: lo`. Its `P` has no source, and the tempting
  fallback is `pcrel_begin`, which measures from the `addi` itself: with the
  `auipc` at 0 and the `addi` at 4 the reference comes out 4 bytes too high and
  still looks like a valid address. N17's `N17b` pins that shape. The
  complementary shape is a group with two `hi` members (`N12a`): the same target
  has two candidate reference points and nothing says which one a `lo` meant.
  A third shape is a `lo` in a different section from its `hi` (`N17c`): `S` and
  `P_hi` would then be offsets into two unrelated origins, and their difference is
  arithmetic on two coordinate systems — a small, plausible, wrong number rather
  than a wrap. The group is therefore confined to one section.
- `E-FIXUP-008` — derived, `03_fixup_model.md` §8: two fixups both named `F0001`
  at different sites. `fixup_record_order` still sorts them, but the emitted
  records are addressed by `fixup_id`; a consumer applying records by id applies
  one twice or drops one, and the plan says nothing about which. `pair_group`
  does not help, because it groups a `hi` and a `lo` that are deliberately
  different fixups.
- `E-FIXUP-009` — source, psABI `riscv-elf.adoc:1184`/`:1186` (ADR-0010): a
  `pcrel_lo12` low half carrying `addend: 4`. The `hi` already folded its addend
  into the shared displacement: with the `auipc` at 0 and a symbol at `0x1000`,
  `hi20 = (0x1000 + 4 + 0x800) >> 12 = 1` and the low half needs
  `(0x1004 - 0) & 0xFFF = 4`. A second addend on the low half yields 8, which is
  the address of a byte past the symbol — a plausible, wrong reference, and the
  plan would have stated the same addend twice with no way to tell which one the
  author meant.

- `E-LIMIT-001` — measured, `ADR-0122`: a plan with a single `fill` fragment of
  2^63 bytes panicked in `raw_vec` (`capacity overflow`) on `47a383b`, because
  `emit` passed `declared_size` straight to `resize`. Without a stated ceiling the
  plan chooses the allocation, so whether a plan is accepted depends on the host's
  memory rather than on the plan (`INV-05`), and the failure mode is a process
  death with no diagnostic (`INV-08`). A smaller over-sized plan is worse: it is
  accepted on a large host and refused on a small one. `N24l` is the fixture: a
  non-image-backed `.bss` of 67,108,865 bytes, one byte over the ceiling, so no
  fragment can explain the total away.

### 2.2 Retired codes

A mechanism that is removed takes its codes with it. Retired codes are never
reused for a different condition.

| Code | Retired | Reason | Replacement |
|---|---|---|---|
| E-CHOICE-001 | 2026-11-04 | `encoding_choices` removed by ADR-0004; a missing decision is a missing or under-specified form | E-FORM-001 |
| E-CHOICE-002 | 2026-11-04 | the same | E-FORM-001 / E-OPERAND-002 |
| E-CHOICE-003 | 2026-11-04 | the same; a value outside the form's set is a form or range error | E-FORM-001 / E-RANGE-001 |
| E-FIXUP-004 | 2026-11-04 | `fmp/0.1` emits one record shape for every `emit_relocation` fixup and every fixup shape has one, so the trigger ("output contract cannot carry the record") is unreachable. A request for a relocation kind the format does not define is a declared-feature failure | E-VERSION-001 / E-FIXUP-001 |

### 2.3 Codes with no `fmp/0.1` trigger

One user-input code is declared and implemented but no plan can reach it yet.
It stays in the registry because the condition it names is real in the model, and
a silent omission would make a later slice look like it had always been covered.

- `E-LAYOUT-005` — no plan field requests alignment: fragments carry no alignment
  attribute, and a `fill` fragment is the only padding. A plan that wants padding
  and omits the fragment produces a gap, which is `E-LAYOUT-002`. The code
  becomes reachable if a fragment ever gains `align_to`.
- `E-INTERNAL-001` — not a user-input code. It is raised only when the
  materializer's own invariant is violated (a bug), so no plan can trigger it by
  construction; §4 uses it as the review marker for an error that leaks a pointer,
  timestamp, host name, or address.

`E-TARGET-003` left this list when `fmp-def/0.2` added per-form
`requires_extensions` (`ADR-0103`). A `0.2` form states its own requirement, so
a plan that names a VEX row without `avx` is now reachable and `N06b` exercises
it. `fmp-def/0.1` tables still have no per-form trigger: their one set is
compared for equality and a mismatch is `E-TARGET-001` (`N06`).

### 2.4 Coverage gate before widening (M1)

The registry is the declared surface; a code is *covered* only when a test
asserts its exact code, JSON Pointer and detail-key set (`fixtures/README.md`).
M1 closed the reachable gap on 2026-11-08: 43 codes are active, 38 are covered by
a fixture, and the five that are not cannot be reached by a well-formed plan or
do not belong to the plan layer. M3 did not add a code; it repointed `N24h` from
the now-accepted Level 1 `artifact` to `emit_fixups: false` and added `N24i` for
a Level 0 symbol-table request, so `E-VERSION-001` keeps two end-to-end
negatives and the counts are unchanged. `fmp-def/0.2` (`ADR-0103`) makes
`E-TARGET-003` reachable through `N06b`.

The audit of `47a383b` added one code, `E-LIMIT-001` (`ADR-0122`), reachable
through `N24l`, so the counts are now 44 active and 39 covered; the five
uncovered codes are unchanged.

| Group | Codes | Evidence |
|---|---|---|
| Fixture-covered | 39 active codes | `fixtures/`; `N24a`–`N24i` are the M1 additions plus the M3 split; `N06b` adds `E-TARGET-003`; `N24j`–`N24l` add `E-VERSION-001` (`section_relative`), `E-SYMBOL-003` (offset bound) and `E-LIMIT-001` |
| JSON layer, unit only | `E-PLAN-004`, `E-PLAN-005` | `rejects_duplicate_keys`, `rejects_a_byte_order_mark`; no plan-layer fixture can reach them |
| Non-plan conditions | `E-DEF-002` | `exp_r5_definition_perturbation_is_loud` |
| Structurally unreachable | `E-LAYOUT-005` | §2.3; revisit only if the format gains the trigger |
| Not user-input | `E-INTERNAL-001` | §2.3; the bug marker |

The `N24` family holds the twelve coverage fixtures: `N24a` (`E-PLAN-001`),
`N24b` (`E-PLAN-006`), `N24c` (`E-TARGET-002`), `N24d` (`E-TARGET-004`), `N24e`
(`E-SYMBOL-002`), `N24f` (`E-SYMBOL-003`), `N24g` (`E-FIXUP-008`), `N24h`
(`E-VERSION-001` for `emit_fixups: false`), `N24i` (`E-VERSION-001` for
`include_symbol_table: true` at Level 0), `N24j` (`E-VERSION-001` for
`target.kind: section_relative`), `N24k` (`E-SYMBOL-003` for an offset past the
section) and `N24l` (`E-LIMIT-001`). Each one is an otherwise valid plan
with exactly the named fault, so the fixture asserts a single diagnostic rather
than a cascade.

`E-PLAN-002` is covered three times: `N23a` (expression-shaped scalar),
`N25a`/`N25b` (zero descriptor width and zero range bits, both `read` phase) and
the JSON unit tests `rejects_floats_and_exponents` /
`rejects_a_negative_zero_fraction`.

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
