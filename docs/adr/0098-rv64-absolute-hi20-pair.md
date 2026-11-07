# ADR-0098: `hi20` is the absolute high half, and RV64 `lui` carries it

- Status: accepted
- Date: 2026-11-08
- Settles: the RV64 absolute-address family of the M5 coverage widening in
  `08_final_recommendation.md` §H: one positive pair-plus-field vector, one
  absent-sibling rejection and one rule-mismatch rejection
- Supersedes: none
- Superseded by: none
- Revises: `03_fixup_model.md` §6 and its ISA table; the `E-FIXUP-001` row of
  `04_errors.md`; the reading-aid table in `07_definition_format.md` §8; the
  RV64 table of `06_validation_matrix.md`; adds `definitions/rv64/0.3.0.json`
  and the `RV-P9` fixtures

## Context

`03_fixup_model.md` §6 named `hi20` in the schema's `value_transform` enum but
defined no semantics for it, and `fmp-validate` rejected the name with
`E-VERSION-001` (`feature: value_transform:hi20`). That was the right default
while no vector needed it: inventing an arithmetic at materialization time is a
decision, not a validation.

M5 needs the missing half of the RV64 address model. `auipc` (`pcrel_hi20`) and
`lui` (`hi20`) are the two ways RV64 constructs a 32-bit upper part, and v0 had
only the PC-relative one (`RV-P8`). `lui a0, %hi(blob)` + `addi a0, a0,
%lo(blob)` is the standard absolute build, and without `hi20` a plan that means
"the address of `blob`" has no expressible form: `pcrel_hi20` forces a `P` the
address does not have, and `identity` cannot name the upper 20 bits.

`EXP-0098` measures the three facts the decision needs:

- the `lui` field is `imm` at 31-12 with `rd` at 11-7 and `opcode = 0110111`
  (UDB `inst/I/lui.yaml`), and `llvm-mc` accepts the literal only in
  `[0, 1048575]` -- `-1` and `0x100000` are both rejected;
- the unresolved pair emits `R_RISCV_HI20` at `0x0` and `R_RISCV_LO12_I` at
  `0x4`, with both fields zero, which is exactly what `emit_relocation` writes;
- with `.text` at `0x1000` and `L1` at `0x1234`, the linked words are
  `lui a0, 1` and `addi a0, a0, 0x234`, matching `(S + A + 0x800) >> 12` and
  `S + A & 0xFFF`.

## Decision

1. **`hi20` is `v = (D + 0x800) >> 12`, with `D = S + A`.** It shares the
   arithmetic of `pcrel_hi20` and differs only in the reference point. Because
   `D` must not carry a `P`, a `hi20` fixup whose `pc_reference_rule` is not
   `none` is `E-FIXUP-001` (`N07f`). The low half is `lo12_i` on the same
   absolute value, so a PC rule on the high half would shift the reconstructed
   address by a page multiple while every field still fits its range.
2. **`lui` is one form: `riscv:lui/rd-imm20`.** `definitions/rv64/0.3.0.json`
   appends it to the `0.2.0` table: `template 37000000`, `dest` at 7+5,
   `target` at 12+20. The slot is `signed: false`, `bits: 20`, because the
   measured assembler domain is the unsigned field; the instruction's own sign
   extension is not a plan decision. Literal payloads and a covering fixup use
   the same form, as `auipc` already does.
3. **The pair is data, never an expansion.** The plan carries both instructions
   and both fixups, each with its own `value_transform`; `pair_group`/`pair_role`
   records the relation, and the materializer neither synthesizes the second
   instruction nor infers the low half from the high half (`INV-03`, `INV-02`,
   OD-02). `emit_relocation` and `resolve_in_place` keep their one-effect-each
   behaviour; `resolve_in_place` needs the target section's `base_address`
   because a `none` rule cannot cancel the site.
4. **The absent sibling is `c.lui`.** `N01eh` names `riscv:c.lui/rd-imm6`
   against `0.3.0` and gets `E-FORM-001`. The compressed form is a separate
   decision with its own operand exclusions and is not part of this vertical
   slice; naming it must fail loudly rather than fall back to `lui`.
5. **`lo12_s` stays reserved.** This ADR retires one reserved transform, not the
   reservation rule. `lo12_s` keeps its `E-VERSION-001` semantics and its
   rationale (`ADR-0010`), so `E-VERSION-001` remains reachable from a
   well-formed plan and the reachability counts in `04_errors.md` §2.4 do not
   move.

## Consequences

- `hi20` moves from "named but rejected" to a defined transform with a positive
  vector, a rule-mismatch negative and a concrete counterexample in
  `03_fixup_model.md` §6. The `value_transform:hi20` branch of
  `E-VERSION-001` no longer has a producer; the code keeps its other producers
  (`lo12_s`, unknown enum members, `emit_fixups: false`, Level 0 symbol tables).
- `0.3.0` is immutable once committed; its digest is
  `sha256:484eae4ba4c80c1ff4d91bc11a6fd9bd36bdc511a8271815d76c0883869ad2af`, and
  the corpus grows to 105 positives and 542 `materialize`-phase negatives.
- The absolute and PC-relative upper halves now have parallel, separately
  measured shapes. A later `%pcrel_hi`-style alias or an automatic pair
  expansion would need a new ADR that supersedes this one.
- The v0 slice expresses an absolute address whose high half fits the unsigned
  20-bit field; an address that would need the field's sign bit is
  `E-FIXUP-003`, not a truncated high half (`EXP-0098` §3, labelled
  `inference` because it follows from the measured domain rather than from a
  vector).

## Alternatives rejected

- **Treat `hi20` as `pcrel_hi20`.** Rejected: the two rules differ by `P`. The
  resolved fixture is the counterexample -- `pcrel_hi20` would write `0` where
  the absolute rule writes `1` -- and the low half masks `S + A`, so the
  reconstructed address would be wrong, not merely rounded.
- **One `absolute` transform that picks hi or lo from the descriptor width.**
  Rejected: the transform would select an encoding form from a width, which is
  `INV-02`/OD-02 ("one writer per bit") inverted. The high and low halves stay
  separate transforms.
- **Express the pair as an operand keyword such as `%hi`/`%lo` in
  `payload.value`.** Rejected: the keyword is a decision, and decisions live in
  `form_id`/fixups, not in a string the materializer would have to parse
  (`INV-06`).
- **Add `c.lui` in the same slice.** Rejected: it has different operand
  exclusions and a 16-bit encoding, so it is a separate form with its own
  counterexamples. Contract before coverage; `N01eh` keeps the absence loud.
- **Define `hi20` as a synonym for `pcrel_hi20` and let the plan choose
  `none`.** Rejected: a synonym hides the reference point in a field the
  transform no longer names, and the counterexample above shows the two are not
  the same function.
