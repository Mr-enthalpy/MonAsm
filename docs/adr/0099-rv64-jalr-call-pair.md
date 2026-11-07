# ADR-0099: RV64 `jalr` is a form, and its low half is the call pair

- Status: accepted
- Date: 2026-11-08
- Settles: the RV64 control-transfer family of the M5 coverage widening in
  `08_final_recommendation.md` §H: one field vector, one call-pair record
  vector, one resolved pair and two rejections
- Supersedes: none
- Superseded by: none
- Revises: `EC-23` of `02_encoding_choices.md` (the decision stays `form
  variant`; only the "v0 ships `jal` only" clause changes); the `RV64
  jal/c.j/jalr aliases` row of `08_final_recommendation.md` §G.2; the
  `pcrel_hi` row of `03_fixup_model.md` §4 and two rows of its §6 ISA table; the
  reading-aid table in `07_definition_format.md` §8; the RV64 table of
  `06_validation_matrix.md`; adds `definitions/rv64/0.4.0.json` and the `RV-P10`
  fixtures

## Context

`EC-23` froze "`jal` vs `jalr`" as a `form variant`, and `ADR-0094` shipped the
four-byte `jal` only. The absent half has a concrete cost: `jal` carries a
21-bit PC-relative displacement and no base register, while a call through a
register is `jalr`, whose immediate is added to `X[rs1]`. A plan that needs the
second cannot express it at all, and `EC-23`'s own evidence says why the
distinction is real -- with C enabled `jalr ra, 0(ra)` is the two-byte `c.jalr`
(`EXP-0096`), so the length is a function of the form, not of the materializer.

`EXP-0099` measures the four facts the decision needs:

- the field is `imm` at 31-20 (signed), `xs1` at 19-15, `funct3 = 000`, `xd` at
  11-7, `opcode = 1100111` (UDB `inst/I/jalr.yaml`), and the measured domain is
  `[-2048, 2047]`;
- the unresolved `auipc` + `jalr` pair emits `R_RISCV_PCREL_HI20` at `0x0` and
  `R_RISCV_PCREL_LO12_I` at `0x4`, and the low record names the `auipc` label,
  not the target -- the same associated pair `RV-P8` already carries;
- with `.text` at `0x1000` and `L1` at `0x1900` the linked words are
  `auipc ra, 1` and `jalr ra, 0x900(ra)`, matching `(S + A - P_hi + 0x800) >>
  12` and `(S + A - P_hi) & 0xFFF`;
- that `0x900` has bit 11 set, and `llvm-objdump -d` reads the word back as
  `jalr -0x700(ra) <L1>` -- the hardware sign-extends the field, and
  `0x1000 + 0x1000 - 0x700 = 0x1900` is the target.

## Decision

1. **`jalr` is one form: `riscv:jalr/rd-rs1-imm12`.**
   `definitions/rv64/0.4.0.json` appends it to the `0.3.0` table: `template
   67000000`, `dest` at 7+5, `src` at 15+5, `imm` at 20+12 with `range
   {signed: true, bits: 12}`. The instruction length is the form's, so the
   4-byte and 2-byte encodings of one source line stay two forms.
2. **The low half reuses `pcrel_lo12`; no transform is added.** In the call
   idiom `X[rs1]` holds `P_hi + hi20 * 4096`, so the correct immediate is
   `S + A - P_hi - hi20 * 4096`. That value is congruent to `S + A - P_hi`
   modulo 4096, so the 12-bit pattern `pcrel_lo12` writes is the same one. The
   fixup is `pc_reference_rule = pcrel_hi`, `pair_role = lo`, `addend = 0`, and
   its `range_constraint` is `signed: false` because the transform masks: the
   sign bit the hardware sees is the field's, not an out-of-range value
   (`N03x` shows where `E-RANGE-001` does apply, on the operand).
3. **`rs1` is an operand, never a fixup field.** The plan supplies the register
   the call goes through; the materializer has no business inferring one
   (`INV-05`: no hidden input, here no hidden register). Consequently a plan
   that pairs `jalr` with `pcrel_begin` is not rejected. It is a different
   program -- `pcrel_begin` measures from the `jalr`'s own address, which is not
   what the instruction adds -- but rejecting it would require the validator to
   model each form's run-time dataflow, and the definition format says what a
   form's fields *are*, not what the instruction *means*.
4. **The absent sibling is `c.jalr`.** `N01ei` names `riscv:c.jalr/rs1` against
   `0.4.0` and gets `E-FORM-001`. The compressed encoding is a separate form
   with a different length; naming it must fail loudly rather than fall back to
   `jalr`.
5. **The alias family stays absent.** `call`, `ret`, `jr` and `j` are
   pseudo-instructions, not forms; v0 has none of them, and `EC-23` continues to
   decide only *which* of `jal`/`jalr` a plan names. Adding a mnemonic that the
   materializer expands would be `INV-03`.

## Consequences

- `EC-23` keeps its `form variant` decision and its `frozen` status; the
  evidence text now says v0 ships `jal` and `jalr` as two forms instead of `jal`
  only, and names `N01ei` for the compressed sibling.
- `0.4.0` is immutable once committed; its digest is
  `sha256:e00dee01004ec9d927ac4e5494e8e6dabfcbb4ff0e123980190c9871624afa76`, and
  the corpus grows to 108 positives and 544 `materialize`-phase negatives.
- The absolute split (`RV-P9`) and the call pair now both have a measured
  low half. A later `ret`/`call` alias, or an automatic `jal` → `jalr` choice
  when the target is out of `jal`'s range, would need a new ADR that supersedes
  this one; the second is `INV-02` and `INV-04` in one step.
- `08_final_recommendation.md` §D.3 is a Phase-5 snapshot and is left as written;
  its statement that the *pseudo-alias family* is absent remains true.

## Alternatives rejected

- **Pair `jalr` with `pcrel_begin`.** Rejected: `P` would be the `jalr`'s
  address, but the instruction adds to a register the plan controls. The
  resolved fixture is the counterexample -- the measured `pcrel_hi` value is
  `0x900`, and `pcrel_begin` with `identity` over `signed: false, bits: 12`
  writes `0x1900 - 0x1004 = 0x8FC`, which fits the field, so the jump lands at
  `0x2000 + 0x8FC = 0x28FC` instead of `0x1900`. That plan passes every check v0
  has, which is why the idiom is documented rather than legislated.
- **Add an `absolute_jalr` form or a `jalr`-specific transform.** Rejected: the
  arithmetic is `pcrel_lo12`'s, and a second name for one function invites the
  two definitions to disagree. Contract before coverage, no new field without a
  counterexample.
- **Mark the low half `signed: true`.** Rejected: the measured `0x900` is
  correct and would be rejected. The mask is the definition, and `EXP-0099` §3
  is the counterexample.
- **Ship `c.jalr` alongside.** Rejected: CJ-format has no immediate field and a
  2-byte length; it is a separate form with its own operand set. `N01ei` keeps
  the absence loud.
- **Let the materializer choose `jalr` when `jal`'s range is exceeded.**
  Rejected: a relaxation decision at materialization time, `INV-02` and
  `INV-04`. The plan names the form and owns the range check.
