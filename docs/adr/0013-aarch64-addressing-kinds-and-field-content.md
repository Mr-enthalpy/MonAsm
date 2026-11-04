# ADR-0013: AArch64 addressing kinds are forms, and the offset is field content

- Status: accepted
- Date: 2026-11-04
- Settles: the AArch64 half of `OD-13` that `ADR-0008` §3 deferred ("a plan
  states the field value or a fixup supplies it"), and `A64-P3`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0008` decided that a memory operand is one operand per encoded field, that
the addressing *kind* is a `form_id` variant, and that a slot holds field
content. Its §3 then stopped at one question: AArch64's unsigned-offset `imm12`
is scaled by the access size, so either the plan states the field value (2 for
16 bytes) or a fixup supplies it. `A64-P3` cannot be planned until that is
answered, and `EC-14` already lists the addressing kinds as a `form variant`
without having a measured counterexample.

The 64-bit load/store family in the pinned MRS drop states the fields. Each
addressing kind is a separate node, and the nodes differ in exactly the bits
that name the kind:

| Node | bit 24 | bits 11–10 | offset field | other |
|---|---|---|---|---|
| `LDR_64_ldst_pos` | `1` | — | `imm12` at `10+12` | `opc = 01` |
| `LDR_64_ldst_immpre` | `0` | `11` | `imm9` at `12+9` | `opc = 01` |
| `LDR_64_ldst_immpost` | `0` | `01` | `imm9` at `12+9` | `opc = 01` |
| `LDUR_64_ldst_unscaled` | `0` | `00` | `imm9` at `12+9` | `opc = 01` |
| `STR_64_ldst_pos` | `1` | — | `imm12` at `10+12` | `opc = 00` |
| `LDR_64_ldst_regoff` | `0` | `10` | `Rm`/`option`/`S` | `bit 21 = 1` |
| `LDR_64_loadlit` | `0` | — | `imm19` at `5+19` | literal, no `Rn` |

Three measurements make the decision (all `llvm-mc` 23.1.2, `EXP-0015`):

1. **The scaled and unscaled forms take different numbers for the same
   address.** `ldr x0, [x1, #16]` is `0xf9400820` with `imm12 = 2`, while
   `ldur x0, [x1, #16]` is `0xf8410020` with `imm9 = 16`. The field is what
   differs; the byte offset is the same.
2. **The mnemonic does not determine the form.** `ldr x0, [x1, #1]` assembles to
   `0xf8401020`, and `llvm-objdump` reads that word back as `ldur x0, [x1,
   #0x1]`; `ldr x0, [x1, #-8]` becomes `ldur x0, [x1, #-0x8]` (`0xf85f8020`).
   The assembler silently switches instruction when the offset does not fit the
   scaled field, which is exactly the choice `INV-02` forbids at materialization
   time.
3. **Each kind has a closed range.** `imm12` accepts `0..4095` field units
   (`#32760` is `0xf97ffc20`); `#32768` is rejected. `imm9` accepts `-256..255`
   bytes; `-256` and `255` are accepted and `256`/`-257` are rejected.

## Decision

1. **Five forms in `definitions/aarch64/0.4.0.json`.** The four kinds that carry
   an immediate are four `form_id`s, plus the store's unsigned-offset row:
   `aarch64:ldr/x64-base-imm12` (`LDR_64_ldst_pos`),
   `aarch64:ldr/x64-base-imm9-pre` (`LDR_64_ldst_immpre`),
   `aarch64:ldr/x64-base-imm9-post` (`LDR_64_ldst_immpost`),
   `aarch64:ldur/x64-base-imm9` (`LDUR_64_ldst_unscaled`) and
   `aarch64:str/x64-base-imm12` (`STR_64_ldst_pos`). The kind is a property of
   the id, never of the operand values (`ADR-0008` §2, `EC-14`).
2. **`disp` is field content, and the unit belongs to the field.** On the two
   `imm12` rows the operand counts 8-byte units for these `x`-width rows (the
   node's `size = 11` is fixed; `#16` → `2`); on the `imm9` rows it counts bytes
   and is signed (`-256..255`). `target_type` names the field (`imm12` /
   `imm9`), `role: disp` selects the range code (`E-RANGE-001`), and
   `align_bits` stays `0` on both because the slot holds the field, not the byte
   offset (`07_definition_format.md` §4, §8.3).
3. **No slot-level scale is added.** `fmp-def/0.1` has no slot transform
   (`07_definition_format.md` §5), and byte semantics already have a home: the
   fixup path (`value_transform: scale`, `transform_shift`), which is how `bl`,
   `b.cond` and RV64's B-type carry a byte displacement. A slot-level divisor
   would be a second way to state the same number, and the two would have to be
   kept consistent by hand.
4. **No fixup onto `disp` in this slice.** An AArch64 `:lo12:` into a scaled
   `imm12` field needs `(A & 0xfff) >> 3` plus an alignment rule, which is a
   fixup-transform decision with its own counterevidence. The fixture states
   `{ "value": … }` only, so the range check is the whole behaviour under test.
   Adding the fixup is a review trigger below, not a silent extension.
5. **The store's other three kinds are absent.** `str`/`stur` with `imm9` are
   the same nodes with `opc = 00`; they are not in the table, so naming
   `aarch64:str/x64-base-imm9-post` is `E-FORM-001`. The store's unsigned-offset
   row ships because it is the one that proves `opc` is carried by the form
   rather than inferred from the mnemonic.
6. **Register offset and literal are absent.** `LDR_64_ldst_regoff` (four
   fields: `Rm`, `option`, `S`, plus `Rn`/`Rt`) and `LDR_64_loadlit` (`imm19`
   plus `Rt`, no base) are different operand sets, not this row with an operand.
   Naming `aarch64:ldr/x64-base-regoff` is `E-FORM-001` (`N01`).
7. **`Rn` and `Rt` are `aarch64.gpr64`/`x64`, 0…31, whatever 31 decodes to.**
   The field is five bits; whether register 31 in `Rn` names `sp` rather than
   `xzr` is a decode fact this slice does not test, and no encoding decision
   follows from it. The plan states the number; the definition states the bits.

## Why not a byte offset

The tempting alternative is `disp` in bytes with the row dividing by the access
size. It reads better — `disp = 16` means 16 bytes on every row — but it needs a
per-slot transform the format does not have, and it would put two byte-displacement
mechanisms in the contract: the slot's divisor and the fixup's `transform_shift`.
The failure it prevents is real and must be answered by evidence instead: a plan
that states the assembler's `#16` as `disp = 16` on an `imm12` row addresses 128
bytes, emits four legal bytes, and passes every size check. What catches it is
`expected_digest` (`OD-01`), which exists for exactly this class of same-length
defect, plus the row's stated unit. The reverse trap — stating field content `2`
on a byte-unit row — is just as silent, so the divisor does not remove the
hazard; it only changes which mistake is likely.

The `align_bits` field would also stop meaning what `07_definition_format.md` §4
says it means. It checks *the value as planned* against a multiple before any
transform; a byte-unit `disp` would need the divisor's remainder checked instead,
which is a third rule for the same bits.

## Consequences

- `A64-P3` passes: `A64-P3-ldst-addressing` is six instructions (both ends of
  `imm12`, pre-index `+8`, post-index `−8`, `ldur` at `−256`, and a store at
  offset 0) whose 24 bytes match `llvm-mc` (`EXP-0015` §3). The two `imm12`
  values and the two `imm9` signs make a defect in either field visible.
- `definitions/aarch64/0.4.0.json` is the third superset; `0.1.0`…`0.3.0` stay
  frozen and unchanged, so a plan bound to `0.3.0` cannot reach the new rows
  (`E-FORM-001`, `N01`).
- `EC-14` gains its measured counterexample: the assembler's `ldr x0,[x1,#1]` →
  `0xf8401020` (`ldur`) is the form switch the plan may not perform. The row
  also gains the unscaled kind in its "legal outputs" list, which the decision
  already covered.
- Two negatives: `N03` gains `disp = 4096` on `imm12` and `disp = -257` on
  `imm9`. `N01` gains the absent register-offset id, so "the addressing kind the
  table does not have" is a fixture, not a footnote.
- No schema, error-code or Rust change: `role: disp`, `aarch64.imm`, an
  `{value}` payload and a per-slot `range` all exist; a new document version
  loads through the same `Registry::load_dir`.
- A plan is more verbose (three operands instead of one memory operand) and the
  unit is per row. Both are costs of `INV-02` and `ADR-0008`, and both are
  visible in the table rather than in the encoder.

## Alternatives considered

- **One form per mnemonic with a `kind` operand (`{value: 0}` = post, `3` = pre)
  or a modifier.** Rejected: that is the sixteen-conditions mistake in different
  clothes. The kind changes the opcode bits *and* the offset field (12 bits vs
  9), so the "operand" would select which other slots exist — a form decision
  expressed as a value.
- **Byte offsets with a slot divisor.** Rejected above: a format feature with a
  second scaling mechanism, and it does not remove the silent-mismatch hazard.
- **Only the unsigned-offset row, deferring pre/post.** Rejected: `EC-14` names
  four kinds and the writeback difference is visible in bytes, so a slice with
  one kind would leave the interesting half unmeasured. One fixture with all
  kinds is cheaper than two slices.
- **Include register offset now.** Rejected: `Rm`/`option`/`S` add a second
  register and a shift kind to the operand list (`EC-13`'s extended-register
  problem), which is its own decision; absence is `E-FORM-001`.
- **Fold `ldur` into the `ldr` row and let the offset value choose.** Rejected by
  measurement 2: that is precisely what the assembler does, and it is `INV-02`.
- **Reuse the RV64 `ld`/`sd` rows' `disp` semantics unchanged.** They are the
  same statement (field content) and that is why they are consistent; the unit
  differs because the field differs, and each row states its unit.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The four kinds are distinct MRS nodes differing in bit 24 and bits 11–10 | MRS `Instructions.json`, the node dumps in `EXP-0015` §1 | high |
| `ldr x0,[x1,#16]` is `imm12 = 2`; `ldur x0,[x1,#16]` is `imm9 = 16` | `EXP-0015` §2, measured | high |
| `imm12` is `0..4095` field units (`#32760` max) and `imm9` is `−256..255` | `EXP-0015` §2, both ends measured | high |
| `ldr x0,[x1,#1]` assembles to `0xf8401020`, decoded as `ldur` | `EXP-0015` §2, measured | high |
| The six-instruction vector is `200040f9 62fc7ff9 a48c40f8 e6845ff8 280150f8 6a0100f9` | `EXP-0015` §3, `llvm-mc` + `llvm-objcopy`, no relocations | high |
| Register 31 in `Rn`/`Rt` is a decode question, not an encoding one | five bits either way; not tested here | **unverified** as a semantic claim, irrelevant to bytes |

## Review triggers

- A slice needs a `:lo12:` (or any address) fixup on `disp`. That needs a scaled
  low-12 transform for AArch64 and its alignment rule; it is a new ADR.
- A slice needs the store's `imm9` kinds, register offset, or literal loads.
  They are new rows and (for the latter two) new operand sets.
- A plan must state byte offsets on memory rows. That is a format feature
  (slot-level transform) and reverses decision 3; it must not be done by
  widening the range.
- A 32-bit or floating-point load appears. `size`/`opc` change and each is a new
  row; the `imm12` unit becomes 4 or 16 bytes, so the unit column is per row.
