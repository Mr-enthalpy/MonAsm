# ADR-0021: `cmp`/`cmn` are a separate alias family, generated from the base node with `Rd` pinned to 31

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P14` (the `cmp`/`cmn` alias family), the boundary between the
  alias nodes and the `subs`/`adds` encode nodes they name, and the
  `E-OPERAND-002` counterexample
- Supersedes: none
- Superseded by: none

## Context

`ADR-0018` noted that `cmp` and `cmn` fix `Rd = 31` and drop the destination, so
the `subs`/`adds` rows of the same layout already reach their words; `ADR-0020`
decision 6 then held the family out of `0.11.0` because the operand count
differs. The MRS makes the split explicit: alongside the encode nodes the drop
carries twelve `Instruction.InstructionAlias` nodes — `CMP` and `CMN` over the
six `{imm, shift, ext}` × `{32, 64}` combinations (`EXP-0023` §1).

Five measured facts decide the boundaries.

1. **The word is the base word with `Rd` at 31.** `cmp x1, x2` is `0xeb02003f`,
   and `subs xzr, x1, x2` is the same word; `cmp x1, #5` is `0xf100143f` and
   `subs xzr, x1, #5` is the same; `cmp w1, w2` is `0x6b02003f`, the `subs`
   `w` word (`EXP-0023` §2). `cmn` is the `adds` twin throughout: `cmn x1, x2`
   is `0xab02003f`. Bits 4–0 are `11111` in every measured alias word.
2. **The alias nodes carry no `encoding`.** Each of the twelve has
   `operation_id` (`CMP_SUBS_addsub_shift`, `CMN_ADDS_addsub_ext`, …), a
   `condition` of `Rd == '11111'`, `preferred: true` and
   `_meta.encoded_in`, and no `encoding` key at all (`EXP-0023` §1). The bytes
   therefore come from the base node; the alias node is the independent source
   for *which* base node and *which* operands, not for the bit fields. That is
   the second source `AGENTS.md` asks for on this slice.
3. **The width is the node's, as on the base rows.** `cmp w1, w2` clears bit 31
   against `cmp x1, x2`, and the alias nodes name `<Wd>`/`<Wm>` or `<Xn>`/`<Xm>`
   in `encoded_in`. No plan field and no row chooses between the two
   (`ADR-0019`).
4. **The alias drops the destination, so it is a two-operand shape.**
   `cmp` and `cmn` name `Rn` and `Rm` (or `imm12`) only. Reusing a `subs` row
   and passing `xzr` as `dest` would encode the same word, but it would make the
   plan spell a register the mnemonic does not take, and a wrong `Rd` would be a
   silent synonym or a wrong byte (`INV-07`).
5. **Register 31 is still a plain `reg_number` in every remaining slot.**
   `cmp sp, #5` is `0xf10017ff`, `cmp wsp, #5` is `0x710017ff`,
   `cmp sp, x2` is the extended word `0xeb2263ff` and `cmp wsp, w2, uxtb #0` is
   `0x6b2203ff`; `cmp x1, sp` is rejected (`EXP-0023` §3). The role still says
   whether 31 denotes `sp` or `wzr`.

One spelling difference is recorded rather than copied: `llvm-mc` accepts
`cmp x1, w2, uxtx #3` (and `subs xzr, x1, w2, uxtx #0`) while
`add x0, x1, w2, uxtx #0` is rejected, and the alias word is the same
`0xeb226c3f` as `cmp x1, x2, uxtx #3` (`EXP-0023` §3). The register number is
the same 5-bit field either way; the table keeps `ADR-0016`'s width rule, so a
`w32` `src2` on a `-uxtx` row is `E-OPERAND-001` rather than a second spelling
of the same word.

## Decision

1. **Forty forms are added in `definitions/aarch64/0.12.0.json`**, per mnemonic
   and width (`ADR-0017`, `ADR-0018`, `ADR-0019` applied to the alias):
   - four shifted rows — `lsl0`, `imm6-lsl`, `imm6-lsr`, `imm6-asr` — and two
     immediate rows — `lsl0`, `lsl12` — on each of `x64` and `w32`, from
     `SUBS_64S_addsub_shift`/`SUBS_64S_addsub_imm` for `cmp` and
     `ADDS_64S_addsub_shift`/`ADDS_64S_addsub_imm` for `cmn`, and the `sf = 0`
     twins for the `w32` rows;
   - eight extended rows on `x64` only, one per `option` value, from
     `SUBS_64S_addsub_ext` (`cmp`) and `ADDS_64S_addsub_ext` (`cmn`).

   The names drop the `dest` component the mnemonic cannot carry:
   `aarch64:cmp/x64-x64-lsl0`, `aarch64:cmp/x64-imm12-lsl12`,
   `aarch64:cmp/x64-x64-w32-imm3-uxtb`, `aarch64:cmn/w32-w32-imm6-lsr`, and so
   on. `0.12.0` repeats the ninety-two `0.11.0` forms unchanged and adds these
   forty; `0.1.0` … `0.11.0` stay frozen at their digests.
2. **Each alias row is the base row with `Rd` pinned to 31 and the `dest` slot
   removed.** No new slot shape, no new field and no new operand kind: the
   generator reads the same encode node as the corresponding `subs`/`adds` row,
   pins `Rd = 31` where that row had a `dest` slot, and keeps every other
   pinned value and slot placement — `shift`/`imm6`, `sh`, `option`/`imm3`,
   `imm6`, `w32` and the excluded tails all come from the earlier rows'
   decisions (`ADR-0009`, `ADR-0016`, `ADR-0019`, `ADR-0020`).
3. **The alias node is a verification oracle, not a byte source.** For each
   emitted row the generator finds the `Instruction.InstructionAlias` node whose
   `operation_id` is the mnemonic plus the base node's name with the `32S`/`32`/
   `64S`/`64` width component removed (`SUBS_64S_addsub_shift` →
   `CMP_SUBS_addsub_shift`), checks there is exactly one such node per width,
   that its `encoded_in` width matches the row, that `condition` is
   `Rd == '11111'` and that `preferred` is `true`, and refuses to emit when any
   of that disagrees. This catches a row built from the wrong base node or the
   wrong width without the alias contributing bits the base does not have.
4. **The 32-bit extended alias rows stay out.** `CMP`/`CMN` over
   `SUBS_32S_addsub_ext`/`ADDS_32S_addsub_ext` would be eight more rows per
   mnemonic, but the 32-bit extended layout itself is not in the table
   (`ADR-0020` decision 7 and `N01l`), so an alias row would name a base shape
   the plan cannot reach. The table never carries an alias without its base.
5. **`E-OPERAND-002` gets its counterexample.** A `cmp` row takes `src` and
   `src2`/`imm`; a plan that also carries `dest` has one operand too many and is
   `E-OPERAND-002` at `/instructions/0/operands` with `expected: 2`,
   `found: 3` (`N02e`). The alias family is the natural witness because it is
   the first shape in the table whose operand count is not its base row's.
6. **`N01i` becomes a version boundary.** It names
   `aarch64:cmp/x64-x64-lsl0` against `0.11.0`, where the id is absent, so the
   code stays `E-FORM-001` while the message shows that the form exists from
   `0.12.0` on.
7. **No schema change and no Rust change.** `form_id` still selects the row,
   the slots are the base slots minus `dest`, and the rejection codes already
   exist.

## Consequences

- `A64-P14` passes: `A64-P14-cmp-cmn-family` carries the forty new rows plus
  register-31 role rows, and its bytes match `llvm-mc` 23.1.2 (`EXP-0023` §4),
  with no relocations.
- The AArch64 table is 132 forms across twelve documents. The generator reads
  the same twenty-nine encode nodes and adds ten alias nodes for verification
  (the two 32-bit extended aliases stay unread).
- The negative set grows by two: `N02e` (the extra `dest` operand,
  `E-OPERAND-002`) and `N01m` (`cmn` against `0.11.0`), and `N01i` is repointed
  to the new id and version.
- The `cmp`/`cmn` shift and immediate rows reach the words `subs`/`adds` already
  produce; both spellings now exist in the table, and the plan's `form_id`
  chooses which operand list it must carry.
- `EC-33` records the alias family in `02_encoding_choices.md`.

## Alternatives considered

- **Reuse the `subs`/`adds` rows with `xzr` as `dest`.** Rejected: `cmp` does
  not take a destination, so the plan would have to spell a register the
  mnemonic cannot name; a different `Rd` would also be an accepted plan
  producing `adds`/`subs` bytes under the `cmp` intent (`INV-01`, `INV-07`).
- **Add a `dest_fixed` field or a `condition` to the base rows.** Rejected:
  the alias node already states `Rd == '11111'`, and `form_id` is the only
  encoding carrier (`ADR-0004`); a second mechanism would let one word be
  reached two ways.
- **Read the bits from the alias node.** Impossible as stated: the alias nodes
  have no `encoding`, and `encoded_in` maps assembly tokens to field names, not
  bit ranges. The base node is the byte source; the alias node is the check.
- **Include the 32-bit extended alias now.** Deferred, not refused: it needs
  the 32-bit extended base rows first, and those still need their own
  counterexamples for `wsp`-as-source and the 32-bit source pairing.
