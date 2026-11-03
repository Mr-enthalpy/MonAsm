# ADR-0011: AArch64 `add` with `LSL #12` is a form, not a slot transform

- Status: accepted
- Date: 2026-11-04
- Settles: `EC-12`'s `sh = 1` half, the remainder of `A64-P2`
- Supersedes: none
- Superseded by: none

## Context

`A64-P2` asks for immediate arithmetic, and `02_encoding_choices.md` calls the
two legal encodings of `ADD (immediate)` one decision (`EC-12`): a 12-bit
immediate scaled by `LSL #0` or by `LSL #12`, selected by the `sh` bit at
position 22. The unscaled half is `aarch64:add/x64-imm12-lsl0` in `0.1.0`. The
scaled half is absent, and `OD-07` recorded why: a definition slot has no
scaling transform (`07_definition_format.md` §8.3), so the table could not say
"multiply the operand by 4096".

Two facts decide the shape.

1. **The architecture puts the scale in the instruction, not in the operand.**
   The Arm A64 ISA page for `ADD (immediate)` (revision `2026-03_rel`,
   2026-03-26) states that `<imm>` is an unsigned immediate in 0…4095 encoded
   in `imm12`, that `sh` selects `LSL #0` or `LSL #12`, and that the decoded
   value is `imm12` with twelve zeros appended at the chosen shift. The Arm MRS
   node `ADD_64_addsub_imm` states the same layout — `sh` at `22+1`, `imm12` at
   `10+12`, both `x` — and nothing about meaning, because the package omits
   descriptive content (`research/external/arm-mrs/README.md`).
2. **The literal is not the field.** `llvm-mc` accepts `add x0, x1, #0x1000`
   and emits `0x91400420`: `sh = 1`, `imm12 = 1`. With an explicit
   `lsl #12` spelling the operand is field content again and must be in
   0…4095. `EXP-0013` §2 measured both, including the rejections (`0x1ffc`,
   `0x1001`, `0x1000000`), and `0xfff, lsl #12` encoding the same word as
   `0xfff000`.

Fact 2 is the boundary. An encoder that turns `0x1000` into a different `sh`
has selected an encoding form from an operand value, which is `INV-02`. A
materializer executing a frozen plan must not do it, so the plan has to name the
form.

## Decision

1. **A second form, in a second document.** `aarch64:add/x64-imm12-lsl12` is
   added by `definitions/aarch64/0.2.0.json`. The new document repeats the four
   `0.1.0` forms unchanged and adds this one; `0.1.0` stays frozen at
   `sha256:96f87aa2…`, so a plan that names the scaled id against `0.1.0` is
   still `E-FORM-001` (`N01`). The new digest is `sha256:169e4bf6…`.
2. **The form fixes `sh = 1` in its template.** The generator pins the MRS field
   explicitly (it now takes a field→value map, not a list of fields to zero),
   and the template is `00004091`: the `-lsl0` word with bit 22 set. `sh` is not
   an operand and not a fixup field, so no plan can disagree with the name.
3. **The slot still holds `imm12` field content.** `imm` is
   `aarch64.imm`/`imm12` with `{ "signed": false, "bits": 12, "align_bits": 0 }`
   and placement `[10,12]`, identical to the `-lsl0` row. `{ "value": n }` means
   the field is `n`; the scaled literal `n << 12` is a property of the form,
   exactly as `bl`'s `imm26` counts instructions rather than bytes (§8.3).
4. **No slot-level scale is introduced.** Not in `fmp-def/0.1`, not in the
   validator, not in the materializer. The same number would then mean two
   different things on the two `add` rows, and a second carrier would exist for
   a decision `form_id` already names (`INV-02`, ADR-0004).
5. **The two failure directions are both `E-RANGE-001`.** `N18a` states
   `0x1000` on `-lsl0`: the value is legal for the instruction but not for the
   named field, and a materializer rejects it instead of switching forms.
   `N18b` states `0x123000` on `-lsl12`: the operand is field content, so a
   pre-scaled value is out of range too. Neither code is new; the failure is the
   same one `N03` pins.
6. **The fixup path does not change.** A `:lo12:` low half in either form is
   `value_transform: lo12_i` with `pair_role: lo` in the same `pair_group`; the
   record kind and the 12-bit value the linker fills in do not change, so filling
   the field does not pick the shift — the `form_id` does. `EXP-0013` §5
   measured it, and also measured that the scaled instruction then adds that field
   at bit 12, so `adrp` plus a scaled `:lo12:` is not an `S + A` address sequence.
   No v0 plan uses that combination.
7. **`sub` is not included.** It has the same `sh` field and would take the same
   decision, but it is a different `EC` site and a different instruction; it
   gets its own `form_id` when a slice asks for it, never a shared row.

## Consequences

- `A64-P2` becomes passing: `A64-P2-add-imm12-lsl12` is a four-instruction
  vector (field content 1, 291, 4095, 0 at `sh = 1`), and its bytes match
  `llvm-mc` 23.1.2 (`EXP-0013` §3). The negatives are `N18` (`N18a` and `N18b`),
  in addition to `N01`, which keeps pinning the absent-form path against `0.1.0`.
- The AArch64 set is now five positive and six negative fixtures, and
  `fixtures/aarch64/README.md` records which document each one targets. Nothing
  about the x86 or RV64 documents moves.
- `EC-12` is carried in both halves by form variants; no `EC` id is added,
  because the row already registered the choice. `07_definition_format.md` §8.2
  lists the new row with a `0.2.0`-only marker and the digest table gains one
  line.
- No schema, error-code or Rust change is needed: `fmp-def/0.1` already
  expresses the form, and the fixture gate picked the new document up through
  `Registry::load_dir`. That is the test that the decision is a table entry
  rather than a format extension.
- The scaled `:lo12:` + `adrp` sequence is measured but is not an address
  sequence: `EXP-0013` §5 shows the same relocation and field value, then the
  instruction's shift turning `0x123450` into a pair that sums to `0x573000`.
  No fixture uses it; `A64-P6` links only the `-lsl0` low half. A slice that
  wants a scaled symbol reference must say what the addend means first.

## Alternatives considered

- **Add a slot-level scale (for example `scale_bits: 12`) so one form serves
  both halves.** Rejected: the same `{ "value": n }` would mean different
  numbers on two rows, which is the ambiguity `form_id` exists to remove; it
  would also add a field to the schema, a check to `check_definition.py` and a
  transform to the materializer for a decision that is already carried.
- **One form with a plan-supplied `sh` bit.** Rejected: `sh` is a fixed field of
  an instruction shape, not an operand of the assembly language, and exposing it
  would let a plan name bytes the instruction does not have.
- **One form for `add` immediate, with the materializer choosing `sh` from the
  value.** Rejected: that is `llvm-mc`'s behaviour (`EV-26`) and is exactly
  `INV-02`. It also changes the meaning of the operand list between plans that
  differ only in a constant.
- **Extend `-lsl0` with an optional `lsl` modifier operand.** Rejected: the
  operand list would vary while the `form_id` stayed fixed, so one id would map
  to two templates; `02_encoding_choices.md`'s carrier test would fail on it,
  and `N01`'s exact lookup would stop being exact.
- **Store the already-scaled literal (`n << 12`) in `imm12` and fix `sh = 1`.**
  Rejected: the field is 12 bits, so `0xfff000` does not fit; `N18b` is that
  alternative's failure mode.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `sh` is bit 22 and `imm12` is bits 10–21 | Arm MRS `ADD_64_addsub_imm` encoding values, read; the A64 ISA page's field map | high |
| `<imm>` is 0…4095 in `imm12`; `sh` selects `LSL #0`/`#12`; decode appends twelve zeros | Arm A64 ISA, `ADD (immediate)`, revision `2026-03_rel`, read at the public mirror; restated in `EXP-0013` §1, no passage copied | high |
| The `sh = 1` word is the `sh = 0` word with bit 22 set | `EXP-0013` §3: `0x913ffc20` vs `0x917ffc20`, `0x91000020` vs `0x91400020` | high |
| `llvm-mc` selects `sh` from a plain literal, and rejects `0x1ffc`/`0x1001`/`0x1000000` without rounding | `EXP-0013` §2, measured | high |
| `0.1.0` did not move; `0.2.0` is a superset of the same four forms | generator run 2026-11-04: frozen digest asserted, `0.2.0` digest `sha256:169e4bf6…`, five forms | high |
| A linked `:lo12:` inside `-lsl12` keeps the same record and field value but is not an `S + A` address | `EXP-0013` §5: `#:lo12:ext, lsl #12` emits `ADD_ABS_LO12_NC`, `ld.lld` writes `0x450`, word `91514000`, and `0x123000 + 0x450000 = 0x573000 ≠ 0x123450` | high for the record and arithmetic; no fixture |

## Review triggers

- A slice needs a scaled *symbol* reference. The record and the arithmetic are
  measured (`EXP-0013` §5); what is missing is a decision on what the addend
  means, since `adrp` plus a scaled `:lo12:` does not compute `S + A`. That is a
  new ADR, not a wider field.
- `sub` immediate, `movz`/`movk` or any other instruction with an `sh`-like bit.
  Each is a new `form_id` and a new row, not a parameter on this one.
- A proposal to let a slot scale its operand. That reverses §8.3 and needs a new
  ADR superseding it, plus a `fmp-def/0.1` schema change.
- A plan that must accept both the shifted and the unshifted literal for one
  instruction. That is two forms, selected by the plan; accepting both under one
  id would reintroduce `INV-02`.
