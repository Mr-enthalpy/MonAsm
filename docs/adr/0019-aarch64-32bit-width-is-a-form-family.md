# ADR-0019: an AArch64 32-bit width is a form family, `sf = 0` is the node's, and the 32-bit shift amount stops at 31

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P12` (the `w`-width rows, `EC-11`), and the boundary between the
  shifted and extended 32-bit nodes
- Supersedes: none
- Superseded by: none

## Context

`ADR-0017` and `ADR-0018` closed the mnemonic families on the 64-bit nodes and
recorded the `sf = 0` rows as the next slice. The MRS makes the step small: the
eight `*_32*` nodes are the eight `*_64*` nodes already read with `sf` at 31+1
fixed to `0`. Four are shifted-register nodes and four are immediate nodes:

| 32-bit node | 64-bit twin | `op` (30+1) | `S` (29+1) |
|---|---|---|---|
| `ADD_32_addsub_shift` / `ADD_32_addsub_imm` | `ADD_64_*` | `0` | `0` |
| `SUB_32_addsub_shift` / `SUB_32_addsub_imm` | `SUB_64_*` | `1` | `0` |
| `ADDS_32_addsub_shift` / `ADDS_32S_addsub_imm` | `ADDS_64_*` | `0` | `1` |
| `SUBS_32_addsub_shift` / `SUBS_32S_addsub_imm` | `SUBS_64_*` | `1` | `1` |

Nothing else changes: `shift` (22+2), bit 21, `imm6` (10+6), `sh` (22+1) and
`imm12` (10+12) are in the same places (`EXP-0021` §1). So the width is not a
modifier of a row any more than `op` or `S` was; it is which node the row was
generated from.

Five measured facts decide the boundaries.

1. **The words are the existing words with `sf` cleared.** `add w0, w1, w2` is
   `0x0b020020` against `add`'s `0x8b020020`; `sub` moves `0xcb…` to `0x4b…`,
   `adds` `0xab…` to `0x2b…`, `subs` `0xeb…` to `0x6b…`, and the immediates move
   `0x91…`/`0xd1…`/`0xb1…`/`0xf1…` to `0x11…`/`0x51…`/`0x31…`/`0x71…`
   (`EXP-0021` §2). No operand changes meaning.
2. **The register class is the form's.** Every one of the eight nodes names its
   registers `<Wd>`, `<Wn>`, `<Wm>`, `<Wd|WSP>` or `<Wn|WSP>` in the MRS
   `_meta.encoded_in` map, never an `X` register, and `llvm-mc` rejects
   `add w0, w1, x2` (`EXP-0021` §1–§2). The encoded register is the same 5-bit
   number, so a free width would let an `x` register ride on a `w` row and emit a
   legal-looking word for an illegal plan (`INV-07`), exactly the failure
   `ADR-0016` closed for the extend keyword's source.
3. **Register 31 is allowed in every slot, and its meaning is the node's.** The
   shifted node spells all three fields `<Wd>`/`<Wn>`/`<Wm>` (no `SP` form), and
   `add wzr, w1, w2` is `0x0b02003f`, `add w0, wzr, w1` `0x0b0103e0`,
   `add w0, w1, wzr` `0x0b1f0020`: 31 is the zero register. The immediate
   `ADD_32`/`SUB_32` nodes spell `<Wd|WSP>` and `<Wn|WSP>`, and
   `add w0, wsp, #5` is `0x110017e0` / `add wsp, w1, #5` is `0x1100143f`: 31 is
   the stack pointer in both roles. The immediate `ADDS_32S`/`SUBS_32S` nodes
   spell `<Wd>` and `<Wn|WSP>`, so 31 is `wzr` in `Rd` — the `cmn w1, #5` word
   `0x3100143f` is that instruction, and `cmp w1, #5` is `0x7100143f`
   (`EXP-0021` §2). The bits are the same 31 in all cases; only the node's role
   says what it denotes.
4. **The 32-bit shift amount stops at 31 even though the field is six bits.**
   `add w0, w1, w2, lsl #31` is `0x0b027c20`, while `lsl #32` and `lsl #63` are
   rejected by `llvm-mc`; the word that `imm6 = 32` would produce
   (`0x0b028020`) is read back by `llvm-mc -disassemble` as *invalid instruction
   encoding*, while `imm6 = 31` decodes as `add w0, w1, w2, lsl #31`
   (`EXP-0021` §2). The field is `xxxxxx` in the MRS, so the legal set is the
   field domain minus a closed tail — the same shape as the `imm3` tail
   `ADR-0009`/`ADR-0016` already carry.
5. **The immediate rows keep the value-driven switch the 64-bit rows have.**
   `add w0, w1, #4096` assembles to `0x11400420`, the `sh = 1` word, without a
   diagnostic; `adds` and `subs` do the same (`0x31400420`, `0x71400420`)
   (`EXP-0021` §2). Naming `-lsl0` and stating 4096 must stay `E-RANGE-001`, as
   `N18a`/`N18d`/`N18e` record for `add`/`sub`/`adds`.

The one assembly spelling that does **not** stay in the shifted node is `wsp` as
a source: `add w0, wsp, w1` assembles to `0x0b2143e0`, which is the
extended-register node (bit 21 = 1, `option = 010`), not
`ADD_32_addsub_shift` (`EXP-0021` §2). The row is still reachable as
`add w0, wzr, w1` = `0x0b0103e0`, because that slot's 31 is the zero register;
what is out of reach is the *spelling*, not the encoding.

## Decision

1. **Twenty-four forms in `definitions/aarch64/0.10.0.json`**, six shapes for
   each of the four mnemonics, each the same row shape as its 64-bit twin:
   - `aarch64:add/w32-w32-w32-lsl0` and
     `aarch64:add/w32-w32-w32-imm6-lsl` / `…-imm6-lsr` / `…-imm6-asr` from
     `ADD_32_addsub_shift`;
   - `aarch64:add/w32-imm12-lsl0` and `…/w32-imm12-lsl12` from
     `ADD_32_addsub_imm`;
   - the same six under `aarch64:sub/…` from `SUB_32_addsub_shift` /
     `SUB_32_addsub_imm`, under `aarch64:adds/…` from `ADDS_32_addsub_shift` /
     `ADDS_32S_addsub_imm`, and under `aarch64:subs/…` from
     `SUBS_32_addsub_shift` / `SUBS_32S_addsub_imm`.

   `0.10.0` repeats the forty-four `0.9.0` forms unchanged and adds these
   twenty-four; `0.1.0` … `0.9.0` stay frozen at their digests. The new digest is
   the one `EXP-0021` §5 records.
2. **The width is the form family and `sf` is pinned by the node.** The
   generator reads a different MRS node for each family, and those nodes fix
   `sf = 0`; no plan field names the bit and no row pins it by hand. As with
   `op` and `S`, there is no `form_id` whose `sf` bit the operand list could
   move.
3. **The register class is the form's, not a plan field.** Every register slot
   on these rows is `aarch64.gpr32` / `w32`, so a plan that states
   `aarch64.gpr64` / `x64` is `E-OPERAND-001` on `kind` and on `target_type`
   (`N02c`). This is `ADR-0016`'s rule applied to the destination and first
   source as well as to `src2`.
4. **Register 31 stays legal in every register slot, with the node's meaning.**
   The slots are `reg_number` over the 5-bit field, `0…31`, and no `sp` operand
   kind is added: which of `wzr`/`wsp` 31 denotes is a property of the row's
   role, exactly as `ADR-0013` decision 7 states for the load/store rows. A plan
   cannot ask for "SP rather than ZR", because the number is all the encoding
   carries; splitting it into two kinds would duplicate ISA knowledge into the
   plan and make the same word reachable two ways.
5. **The 32-bit shift amount is `imm6` field content over `0…31`.** The slot
   declares `range.bits = 6` and `excluded: [32, 33, …, 63]`, so a value inside
   the field that the 32-bit form does not allocate is `E-RANGE-004` (`N16d`),
   never a truncated or re-encoded shift. The exclusion is exactly the top
   bit of `imm6`; the 64-bit rows keep `0…63` because their node uses the whole
   field.
6. **The field decisions are inherited, not repeated.** `sh` (`-lsl0`/`-lsl12`),
   the shift keyword (`-imm6-lsl`/`-lsr`/`-asr`) and `imm6`/`imm12` as field
   content are `ADR-0011` and `ADR-0015` applied to different nodes, with the
   same slot shapes, the same `align_bits = 0`, and the same `lsl #0` overlap
   between `-lsl0` and `-imm6-lsl` with `imm6 = 0`.
7. **A literal outside the named `sh` half is `E-RANGE-001`** on the `w` rows
   too: `4096` stated on `add/w32-imm12-lsl0` is rejected (`N18f`), never
   re-encoded as `-lsl12`; `sub`/`adds`/`subs` get the same treatment by
   construction.
8. **The extended 32-bit node and the aliases are out.** `ADD_32_addsub_ext`
   (`SUB_32_addsub_ext`, `ADDS_32S_addsub_ext`, `SUBS_32S_addsub_ext`) is the
   bit-21-plus-`option` layout with `sf = 0` and is a different slice; naming one
   stays `E-FORM-001`. `cmp`/`cmn` remain the two-operand family `ADR-0018` left
   out. So `add w0, wsp, w1` and `add w0, w1, w2, uxtw #3` are unreachable
   through `0.10.0` even though the assembler will emit both.
9. **No new error code, no schema change, no Rust change.** `aarch64.gpr32` /
   `w32` entered with the extend rows (`ADR-0016`) and `excluded` with
   `ADR-0009`; `E-OPERAND-001`, `E-RANGE-001` and `E-RANGE-004` already have
   fixtures.

## Consequences

- `A64-P12` passes: `A64-P12-w-rows` is twenty-four instructions (96 B), one per
  new row, with distinct registers in every row, `imm12` at 4095 and 291<<12,
  and `imm6` at 3, 7 and 31; its bytes match `llvm-mc` 23.1.2 (`EXP-0021` §3),
  with no relocations.
- The AArch64 table is 68 forms across ten documents, from twenty-six MRS nodes.
  The new rows add eight node names to the generator and no new slot shape.
- `EC-11` is now carried on both sides of the width in every shape, not only by
  `add`/`sub`; `EC-12` and `EC-31` gain their `w` halves. `EC-32` is untouched:
  the extend keyword's rows are still 64-bit.
- The negative set is 30 fixtures: `N01k`, `N02c`, `N16d` and `N18f` join the
  twenty-six.
- `N01h` and `N01j` stay valid but have narrowed meaning: they name a `w` row
  against `0.8.0`/`0.9.0`, where the row does not exist yet. They are now
  version-boundary fixtures, not evidence that the `w` rows are absent from the
  table.

## Alternatives considered

- **A free width operand (`sf`) on every row.** Rejected: the assembly language
  has no spelling for the bit, and a free `sf` would let a plan state `add`'s
  mnemonic with `add w0,w1,w2`'s bytes — the `INV-07` silent-repair shape
  `ADR-0017` rejected for `op` and `ADR-0018` for `S`.
- **One row with a `w32`/`x64` operand type and no separate `form_id`.** Rejected:
  the MRS node fixes `sf`, so the operand type could not select the bit without
  the materializer choosing; the `form_id` is the carrier and the type is a
  second, independent guard.
- **A five-bit `imm6` placement with bit 15 pinned to 0.** Not wrong, but it
  needs a partial-field mask in the generator, a concept no other row uses, and
  it moves a bit out of the slot. `excluded` already means "inside the field,
  outside the legal set" (`ADR-0009`), and it is what the `imm3` tail uses; the
  counterexample is a lookup either way.
- **An `sp` operand kind to separate `wzr` from `wsp`.** Rejected: both are the
  number 31 in the same 5-bit field, the role is the node's, and a third kind
  would be a plan-side restatement of the instruction, not a machine fact the
  encoding stores.
- **Include the extended 32-bit rows here.** Deferred, not refused: they pin
  bit 21 plus `option` and need the source-width counterexample again on the
  `sf = 0` side, so they are their own slice.
