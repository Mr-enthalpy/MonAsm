# ADR-0096: the Level 1 artifact is sections, declared symbols and the Level 0 records

- Status: accepted
- Date: 2026-11-08
- Settles: `08_final_recommendation.md` §H M3 (Level 1 object writer)
- Supersedes: none
- Superseded by: none
- Revises: `01_contract.md` §11 and new §11.2, the `symbol_order` row of
  `01_contract.md` §11, `OD-03` in `05_open_decisions.md`, and the
  `symbol_order.x-status` value in `schema/fmp-v0.schema.json`

## Context

`ADR-0095` decision 4 left Level 1 (`artifact: sections`,
`include_symbol_table: true`) legal in the schema but rejected at runtime as
`E-VERSION-001`, because `OD-03` deferred it. `01_contract.md` §11.1 defines the
Level 0 envelope, but no section defines the Level 1 envelope. M3 cannot encode
an output shape that the contract does not state, and `AGENTS.md` rule 1 forbids
writing code first.

Two facts measured before this ADR:

- `fmp-validate` rejects `artifact: sections` and `include_symbol_table: true`
  in `check_output`, and rejects `emit_fixups: false` and a non-default
  `fixup_record_order` there too. The JSON Schema marks `emit_fixups` as
  `const: true`, but the Rust reader does not enforce `const`; a plan with
  `emit_fixups: false` reached `E-VERSION-001` at
  `/output_contract/emit_fixups` (experiment 2026-11-08, `fmp materialize` on a
  copy of `X86-P1`). `E-VERSION-001` therefore stays reachable after Level 1
  lands.
- `fmp-validate` already checks that `section_order` is a permutation of
  `sections[]` (`E-LAYOUT-006`), that `symbol_order`, when present, is a
  permutation of `symbols[]` and in the same order as the `symbols` array
  (`E-LAYOUT-004`), and that without `symbol_order` the `symbols` array is
  sorted by `symbol_id` (`E-LAYOUT-004`). Emission can therefore trust both
  orders instead of inventing a repair.

## Decision

1. **Level 1 is a JSON description artifact, not a container file.** `level: 1`
   carries laid-out section images, the symbol table when the plan asks for it,
   and the same `fixups` records Level 0 carries. No ELF, COFF, Mach-O or other
   container is written; container policy is Level 2 and stays out of `fmp/0.1`.
2. **`sections[]` contains exactly one entry per id in
   `output_contract.section_order`, in that order.** The entry fields are:

   | Field | Required | Meaning |
   |---|---|---|
   | `section_id` | yes | The plan's `section_id`, echoed |
   | `section_kind` | yes | `code` \| `data` \| `rodata` \| `bss` |
   | `image_backed` | yes | The plan's flag, echoed |
   | `base_address` | only when the plan declares it | The plan's `base_address`, echoed; never defaulted to `0` |
   | `size` | yes | The plan's `declared_size`; for an image-backed section this equals `len(bytes_hex) / 2` |
   | `bytes_hex` | yes | Lowercase hex of the emitted section bytes; `""` when `image_backed` is `false` |

   A non-image-backed section is still listed, with `size` equal to its virtual
   `declared_size` and no bytes. Omitting it would make `section_order` name an
   entry the artifact does not contain, and would lose the only place the
   artifact states the virtual size.
3. **`symbols[]` is present if and only if `include_symbol_table` is `true`.**
   Its entries are the plan's symbols, in `symbol_order` when present and by
   ascending `symbol_id` otherwise. An entry carries `symbol_id`, `name`,
   `kind` (`defined` \| `undefined` \| `external`) and `binding` (`local` \|
   `global` \| `weak`), plus `section_id` and `offset` for a `defined` symbol.
   The validator already rejects a defined symbol without a location and an
   undefined/external symbol with one (`E-SYMBOL-003`), so the emitted record is
   total without a default. M3 does **not** synthesize symbols: in particular,
   the RV64 `pcrel_lo12` local label remains a Level 1 writer task beyond this
   ADR, and the fixup records already carry the pair relation.
4. **`fixups[]` is unchanged.** It is the Level 0 record list from
   `03_fixup_model.md` §8 in `fixup_record_order`. There is no second
   `relocations[]` array: a relocation is exactly the `emit_relocation` subset,
   and a second projection could disagree with the first.
5. **Level 0 is byte-for-byte unchanged.** With `artifact: bytes` the envelope
   keeps the fields, order and values of §11.1. A Level 1 section image is the
   same bytes the Level 0 image concatenates, so the Level 1 payload can be
   checked against the existing oracle bytes without a second encoder.
6. **The output gates become:**
   - `artifact: sections` is accepted; an unknown `artifact` value remains
     `E-VERSION-001` at `/output_contract/artifact`;
   - `include_symbol_table: true` is accepted only with `artifact: sections`;
     with `artifact: bytes` it remains `E-VERSION-001` at
     `/output_contract/include_symbol_table`;
   - `emit_fixups: false`, a non-default `fixup_record_order` and a non-empty
     `feature_constraints` remain `E-VERSION-001`, unchanged.
7. **`symbol_order` is frozen.** Its counterexample is a plan whose emitted
   symbol table must follow declaration order: symbols `ext` then `S1` in the
   source, while `symbol_id` order is `S1` then `ext`. Without the field the
   contract forces `S1, ext`; an emitter that instead walks a map would produce
   a different table for the same symbol set on a different process. With the
   field, §12 pins the table to the plan's order and the validator refuses a
   list that is not the declared permutation (`E-LAYOUT-004`).
8. **`N24h` moves its trigger.** The fixture now sets `emit_fixups: false`
   instead of `artifact: sections`, so `E-VERSION-001` keeps an end-to-end
   negative and the Level 1 acceptance does not orphan the code.

## Consequences

- A consumer can split the Level 0 image by `section_id` and `size`, and can
  read the declared symbol table without re-reading the plan.
- Level 1 adds no encoder and no layout pass: both levels are projections of the
  same validated plan, which is the check M3's exit gate asks for.
- A plan that requests neither a section split nor a symbol table can stay at
  Level 0; nothing forces the larger envelope.
- RV64 consumers that need a synthetic `pcrel_lo12` local still need a later
  writer. That gap is named here rather than hidden behind `include_symbol_table`.

## Alternatives rejected

- **Emit an ELF/COFF object.** Rejected by `OD-03` and `ADR-0003`: container
  policy (section flags, string tables, alignment, relocation type numbers) is
  Level 2 and would add choices the plan does not state.
- **A separate `relocations[]` array.** Rejected: it duplicates the
  `emit_relocation` subset of `fixups[]`, and two projections of one decision
  can disagree. `EXP-0002` §6 already showed the Level 1 relocation record is a
  projection, not an enrichment.
- **List only image-backed sections.** Rejected: the virtual size of a `bss`
  section would disappear from the artifact, and `section_order` would name an
  absent section.
- **Default `base_address` to `0` when the plan omits it.** Rejected:
  `01_contract.md` §5 already makes a missing base `E-FIXUP-002` rather than a
  zero, and a default would change an absolute reference silently.
- **Leave `symbol_order` `draft`.** Rejected: M3 now emits a symbol table, so
  its order is observable output and needs a counterexample and a frozen status.
- **Retire `E-VERSION-001`.** Rejected: `emit_fixups: false` and non-empty
  `feature_constraints` are still accepted by the reader and still rejected by
  the version gate; deleting the code would remove a live rejection.
