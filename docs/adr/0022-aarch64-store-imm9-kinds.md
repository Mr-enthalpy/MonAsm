# ADR-0022: the store half of the addressing kinds is the same decision

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P15` (the store `imm9` kinds `ADR-0013` decision 5 held out),
  and the store-side half of the `EC-14` counterexample
- Supersedes: none
- Superseded by: none

## Context

`ADR-0013` decided that an AArch64 addressing kind is a `form_id` and that the
offset is field content, and shipped five rows: `ldr` unsigned-offset,
pre-index, post-index, `ldur`, and the store's unsigned-offset row. Decision 5
then held the store's `imm9` kinds out — `STR_64_ldst_immpre`,
`STR_64_ldst_immpost` and `STUR_64_ldst_unscaled` — because the load half was
enough to measure the rule.

That leaves the store family asymmetric in a way the table can see: a store with
`[x1, #8]!`, `[x1], #-256` or `stur x0, [x1, #-1]` has no row at all, so it is
`E-FORM-001`, while the same three kinds exist for loads. `EC-14` names five
kinds and its counterexample is a load; the store side is unmeasured.

Four measurements decide the slice (all `llvm-mc` 23.1.2, `EXP-0024`):

1. **The three nodes are the load rows' layouts with `opc = 00`.** Fields are
   identical to `LDR_64_ldst_immpre`/`immpost`/`LDUR_64_ldst_unscaled` except
   `opc`, which the node fixes at `00`, and `Rt`, which is the stored register.
   Bits 11–10 still name the kind (`11` pre, `01` post, `00` unscaled), bit 24
   is `0`, and `imm9` is at bits 12–20.
2. **The kind is still not the mnemonic.** `str x0, [x1, #1]` assembles to
   `0xf8001020`, which `llvm-objdump` reads back as `stur x0, [x1, #0x1]`; `str
   x0, [x1, #-8]` becomes `0xf81f8020`, also `stur`. The store assembler makes
   the same value-driven switch the load one does (`INV-02`).
3. **`imm9` is the same field with the same range.** `#8`, `#-256` and `#255`
   are accepted on the pre/post rows and `#-257`/`#256` are rejected with
   `index must be an integer in range [-256, 255]`; `stur` reports the same
   bound. The value is the field content in signed bytes, as in `ADR-0013`
   decision 2.
4. **The `imm12` row does not move.** `str x0, [x1]` is still `0xf9000020` and
   `str x0, [x1, #32760]` is still `0xf93ffc20`, so adding the three rows leaves
   the offset kind's bits and unit alone.

## Decision

1. **Three forms are added in `definitions/aarch64/0.13.0.json`**:
   `aarch64:str/x64-base-imm9-pre` (`STR_64_ldst_immpre`),
   `aarch64:str/x64-base-imm9-post` (`STR_64_ldst_immpost`) and
   `aarch64:stur/x64-base-imm9` (`STUR_64_ldst_unscaled`). `0.13.0` repeats the
   132 `0.12.0` forms unchanged and adds these three; `0.1.0` … `0.12.0` stay
   frozen at their digests, so a plan bound to `0.12.0` cannot reach the new
   rows (`E-FORM-001`, `N01n`).
2. **`stur` ships with the two writeback rows.** The load side already has
   `ldur` for the unscaled kind; leaving `stur` out would make the unscaled kind
   reachable for loads only, and would leave the assembler's own `str x0, [x1,
   #1]` → `stur` word without a row. The three rows together are the store half
   of the four kinds `EC-14` names, so after this slice every 64-bit
   load/store addressing kind in the MRS drop except register offset and
   literal has a row.
3. **`disp` keeps `ADR-0013` decision 2's rule.** `target_type` names the field
   (`imm9`), the slot is `aarch64.imm` with `signed: true`, `bits: 9`,
   `align_bits: 0`, and the range check is `E-RANGE-001`. No slot-level scale
   and no new transform: the byte/field distinction stays in the form's name and
   in the row's stated unit, not in the encoder.
4. **The stored register is `src`, not `dest`.** `aarch64:str/x64-base-imm12`
   already fixed that for stores, so the new rows reuse the operand list
   `src`, `base`, `disp` in that order. A `dest` on a store row makes five
   operands where the row declares three, which is `E-OPERAND-002` by the count
   rule `N02e` pins (that fixture's own counts are `expected: 2`, `found: 3`).
5. **Two range negatives and one version boundary.** `N03-str-imm9-post-disp-out-of-range`
   (`disp = -257`) and `N03-stur-imm9-disp-out-of-range` (`disp = 256`) pin the
   two ends on two of the three new rows; `N01n-absent-store-imm9-form` names
   `aarch64:str/x64-base-imm9-pre` against `0.12.0` and stays `E-FORM-001`.
6. **No schema change and no Rust change.** `role: disp`, `aarch64.imm`, a
   `{value}` payload, a signed per-slot range and a new document version all
   already load.

## Consequences

- `A64-P15` passes: `A64-P15-store-imm9-addressing` is eight instructions over
  five forms (pre `+8`/`−256`, post `+8`/`255`, `stur` `+16`/`−1`, and the
  `imm12` row at `0`/`4095`) whose 32 bytes match `llvm-mc` 23.1.2 with no
  relocations (`EXP-0024` §3).
- The AArch64 table is 135 forms across thirteen documents, from thirty-two
  encode nodes plus the ten alias verification nodes.
- The negative set grows by three; the AArch64 fixtures become sixteen positive
  and thirty-eight negative.
- `EC-14`'s evidence now quotes the store twin (`str x0, [x1, #1]` →
  `0xf8001020` = `stur`), so the "the mnemonic does not name the form" claim is
  measured on both halves of the family.
- A store with a negative offset or a writeback is now plannable; before this
  slice it had no row at all.

## Alternatives considered

- **Fold the store `imm9` kinds into `str/x64-base-imm12` with a kind
  operand.** Rejected: the kind clears bit 24 *and* replaces the 12-bit `imm12`
  with a 9-bit `imm9` plus two kind bits, so the "operand" would select which
  other slots exist — a form decision expressed as a value (`INV-02`).
- **Add pre/post and skip `stur`.** Rejected above: it would leave the unscaled
  kind unreachable for stores and the assembler's own `str → stur` switch
  unrepresented, so a plan stating the word the assembler produces would have no
  legal row.
- **Add the three rows to `0.12.0` under the same digest.** Rejected: a document
  that names a version carries the forms of that version, and a digest change
  under a fixed version is the drift `OD-06` exists to catch. The new rows get
  their own version.
- **Let the store's `disp` be a byte offset and scale by `size`.** Rejected for
  the reason in `ADR-0013` ("Why not a byte offset"): `fmp-def/0.1` has no slot
  transform, and a slot divisor would be a second scaling mechanism next to the
  fixup's `transform_shift`.
- **Include register offset in the same slice.** Deferred, not refused:
  `Rm`/`option`/`S` add a second register, a shift kind and the `S` scale bit,
  which is its own decision with its own counterexamples. It stays absent
  (`E-FORM-001`, `N01b`).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The three store kinds are `opc = 00` twins of the load nodes, differing only in bits 11–10 | MRS `Instructions.json`, node dumps in `EXP-0024` §1 | high |
| `str x0,[x1,#8]!` is `0xf8008c20` and `str x0,[x1],#255` is `0xf80ff4e6` | `EXP-0024` §2, measured | high |
| `imm9` is `−256..255` bytes on all three store kinds | `EXP-0024` §2, both ends and both rejects measured | high |
| `str x0,[x1,#1]` assembles to `0xf8001020`, decoded as `stur` | `EXP-0024` §2, measured | high |
| The eight-instruction vector is `208c00f8 620c10f8 a48400f8 e6f40ff8 280101f8 6af11ff8 ac0100f9 eefd3ff9` | `EXP-0024` §3, `llvm-mc` + `llvm-objcopy`, no relocations | high |
| Register 31 in `Rn`/`Rt` is a decode question, not an encoding one | five bits either way; not tested here | **unverified** as a semantic claim, irrelevant to bytes |
| A store `dest` operand is `E-OPERAND-002` | the slot list has no `dest`; the count rule is `N02e`'s, this slice adds no fixture for it | high (mechanism), not measured in this slice |

## Review triggers

- A slice needs a store `:lo12:` or any fixup on `disp`. That is a
  scaled low-12 transform and its alignment rule, i.e. a new ADR (the same
  trigger `ADR-0013` left open on the load side).
- Register offset or literal loads/stores land. They are new operand sets
  (`Rm`/`option`/`S`; `imm19` with no base) and both need their own ADR.
- A 32-bit, `b`/`h`, or floating-point store appears. `size`, `opc` and the
  register class change, so each is a new row and the `imm12` unit becomes 4,
  2 or 16 bytes.
- A plan needs one row to cover two kinds. That reverses decision 1 and would
  have to state how the value picks the bits without violating `INV-02`.
