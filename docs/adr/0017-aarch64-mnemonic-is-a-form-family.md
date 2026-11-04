# ADR-0017: an AArch64 mnemonic is a form family, and `sub` repeats the `add` shape with `op = 1`

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P10` (widening), the `sub` half of `EC-12`, and the boundary between
  `sub` and `subs`
- Supersedes: none (narrows `ADR-0016` decision 7 to the *extended* `sub` node)
- Superseded by: none

## Context

`ADR-0011`, `ADR-0015` and `ADR-0016` closed the two `add` nodes the v0 table
reads: `ADD_64_addsub_imm` (`sh`), `ADD_64_addsub_shift` (`shift` + `imm6`) and
`ADD_64_addsub_ext` (`option`, which also fixes the source width). Each of those
decisions was about a field the MRS leaves variable.

`sub` is a different question. The three `SUB_*` nodes are the `ADD_*` nodes with
one bit changed: `op` at 30+1 is `1` instead of `0`, and every other field — the
fixed bits, the variable `sh`/`shift`/`imm6`/`imm12`, and the register fields —
is identical (`EXP-0019` §1). So the mnemonic does not leave a field open; it
selects a different node whose fixed bits differ in exactly that one position.
The assembly language agrees: `sub x0, x1, x2` and `sub x0, x1, #1` are the
`sub` spellings of the same two shapes `add` already has (`EXP-0019` §2).

Three measured facts decide the boundaries.

1. **`S` is a third node, not a field of these.** `SUBS_64_addsub_shift` and
   `SUBS_64S_addsub_imm` fix `S` at 29+1 to `1`; `subs x0, x1, x2` is
   `0xeb020020` and `subs x0, x1, #1` is `0xf1000420`, one bit above the `sub`
   words (`EXP-0019` §2). The flag-setting spelling is therefore a different
   instruction with a different observable effect, not a modifier of `sub`.
2. **`sf = 0` is a third pair of nodes.** `SUB_32_addsub_shift` and
   `SUB_32_addsub_imm` fix `sf` at 31+1 to `0`; `sub w0, w1, w2` is
   `0x4b020020`. That is `EC-11`'s decision applied to `sub`, and like `add`'s
   `w` rows it is absent rather than derived from an operand's width.
3. **A literal that needs `sh = 1` is still not a form choice.** `llvm-mc`
   assembles `sub x0, x1, #0x1000` to `0xd1400420`, the `sh = 1` word, with no
   diagnostic (`EXP-0019` §2) — the same value-driven re-encoding `N18a` records
   for `add` (`EXP-0013` §2). Naming `-lsl0` and stating `4096` must be
   `E-RANGE-001`, because the operand is `imm12` field content.

`ror` is rejected by the assembler for `sub` as for `add` (`EXP-0019` §2):
`shift = 11` is unallocated in this node, so there is no fourth keyword row.

## Decision

1. **Six forms in `definitions/aarch64/0.8.0.json`**, each the `add` row's shape
   with the `sub` node:
   - `aarch64:sub/x64-x64-x64-lsl0` and `aarch64:sub/x64-x64-x64-imm6-lsl` /
     `…-imm6-lsr` / `…-imm6-asr` from `SUB_64_addsub_shift`;
   - `aarch64:sub/x64-imm12-lsl0` and `…/x64-imm12-lsl12` from
     `SUB_64_addsub_imm`.

   `0.8.0` repeats the twenty-six `0.7.0` forms unchanged and adds these six;
   `0.1.0` … `0.7.0` stay frozen at their digests, so naming a `sub` id against
   `0.7.0` is still `E-FORM-001`. The new digest is
   `sha256:9f82b566af004aaa9f0471151497d65acb45c3a7b46e4240345d21f4e330bc35`.
2. **The mnemonic is the form family, and `op` is pinned by the node.** The
   generator reads a different MRS node for each family, and that node fixes
   `op = 1`; no plan field names the bit and no row pins it by hand. A plan that
   wants subtraction names `sub`; there is no `form_id` whose `op` bit the
   operand list could move.
3. **The field decisions are inherited, not repeated.** `sh` (`-lsl0`/`-lsl12`),
   the shift keyword (`-imm6-lsl`/`-lsr`/`-asr`) and `imm6` as `0…63` field
   content are `ADR-0011` and `ADR-0015` applied to a different node, with the
   same slot shapes and the same `align_bits = 0`. `lsl #0` is expressible both
   as `-lsl0` and as `-imm6-lsl` with `imm6 = 0`, the same overlap `ADR-0015`
   decision 5 kept for `add`.
4. **`subs`, the `sf = 0` nodes and `SUB_64_addsub_ext` are out.** Naming
   `aarch64:subs/x64-x64-x64-lsl0` is `E-FORM-001` (`N01g`), naming
   `aarch64:sub/w32-w32-w32-lsl0` is `E-FORM-001` (`N01h`), and naming
   `aarch64:sub/x64-x64-w32-imm3-uxtb` stays `E-FORM-001` (`N01f`). The three
   are separate slices because each fixes a different bit (`S`, `sf`, and
   bit 21 + `option`) and each deserves its own counterexample.
5. **A literal outside the named `sh` half is `E-RANGE-001`.** `4096` stated on
   `-lsl0` is rejected (`N18d`), never re-encoded as `-lsl12`, and a pre-scaled
   literal on `-lsl12` is rejected by the same `imm12` range. This is `N18a`/
   `N18b`'s rule one mnemonic over; the operand is the field, the `<< 12`
   belongs to the form.
6. **Register 31 means `xzr` in these rows.** The shifted and immediate nodes
   read `31` as the zero register; `sub sp, x1, x2` is *not* one of them — the
   assembler encodes it through the extended node
   (`0xcb22603f`, `option = 011`, bit 21 = 1), which this table does not carry,
   so a plan cannot reach `sp` here. `A64-P1` already measures `Rm = 31` as
   `xzr` for the shifted `add` row.
7. **No new error code and no schema change.** `E-FORM-001` and `E-RANGE-001`
   are the only codes this slice uses; both already have fixtures.

## Consequences

- `A64-P10` passes: `A64-P10-sub-family` is six instructions (24 B), one per new
  row, with distinct registers in every row and `imm12` at 4095 and 291<<12; its
  bytes match `llvm-mc` 23.1.2 (`EXP-0019` §3), with no relocations.
- The AArch64 table is 32 forms across eight documents, from fourteen MRS nodes.
  The `sub` rows add two node names to the generator and no new slot shape.
- `EC-12`'s `sub` half is now carried by a row pair rather than only described,
  so the row's counterexample (a literal that only fits the other half) is
  measured on both mnemonics.
- The negative set is 23 fixtures: `N01g`, `N01h` and `N18d` join the twenty.
- `ADR-0016` decision 7 read "`sub`, `adds`/`subs` and the 32-bit node are out".
  That sentence is now scoped to the *extended* node: `SUB_64_addsub_ext` is
  still absent (`N01f`), while the immediate and shifted `sub` nodes land here.
  Nothing in `ADR-0016`'s decision changes, because its subject was the
  `option`/`imm3` treatment.

## Alternatives considered

- **One row per mnemonic with an `op` operand.** Rejected: the assembly language
  has no numeric spelling for the mnemonic, and a free `op` bit would let a plan
  state `add`'s registers with `sub`'s bytes — the `INV-07` silent-repair shape
  `ADR-0016` rejected for `option`.
- **Fold `sub` into the `add` rows by allowing a negative immediate.** Rejected:
  that is a different instruction (`op = 1`) chosen from the operand's sign,
  which is exactly the value-driven form selection `INV-02` forbids.
- **Include the `subs` and `sf = 0` nodes in the same version.** Deferred, not
  refused: each pins a different bit and needs its own counterexample, so each
  is its own slice.
- **Include `SUB_64_addsub_ext` here.** Deferred for the same reason; the eight
  `option` rows are `ADR-0016`'s shape and `N01f` keeps them out of `0.8.0`.
