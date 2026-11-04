# ADR-0018: an AArch64 flag-setting mnemonic is a form family, and `S = 1` is the node's

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P11` (widening), and the boundary between `adds`/`subs` and
  `cmp`/`cmn`
- Supersedes: none
- Superseded by: none

## Context

`ADR-0015` and `ADR-0016` closed the `add` shapes; `ADR-0017` closed `sub` and
established that the mnemonic is the form family. The flag-setting spellings are
the next neighbours, and they are the easiest to mistake for a modifier: `adds`
differs from `add` by one letter and one visible effect.

The MRS makes the boundary exact. `ADDS_64_addsub_shift`, `ADDS_64S_addsub_imm`,
`SUBS_64_addsub_shift` and `SUBS_64S_addsub_imm` are the four nodes already read
with `S` at 29+1 fixed to `1`; every other field, including `op` and the variable
`sh`/`shift`/`imm6`/`imm12`, is unchanged (`EXP-0020` §1). So `S` is not a plan
field any more than `op` was.

Three measured facts decide the boundaries.

1. **The four words are the existing four with bit 29 set.** `adds x0, x1, x2` is
   `0xab020020` against `add`'s `0x8b020020`; `subs x0, x1, x2` is `0xeb020020`
   against `sub`'s `0xcb020020`; the immediates move `0x91…`/`0xd1…` to
   `0xb1…`/`0xf1…` (`EXP-0020` §2). No operand changes meaning.
2. **`cmp` and `cmn` are aliases of a *different* shape, not of these rows.**
   `cmp x1, x2` is `0xeb02003f` = `subs xzr, x1, x2`, `cmn x1, x2` is
   `0xab02003f` = `adds xzr, x1, x2`, and the immediates are `cmp x1, #5`
   `0xf100143f` / `cmn x1, #5` `0xb100143f` (`EXP-0020` §2). Each alias fixes
   `Rd` to 31 and drops the destination operand: a two-operand spelling for a
   three-operand encoding. Naming it is a different form family, not a value of
   this one.
3. **Register 31 is `xzr` here too.** `adds xzr, x1, x2` assembles to the `cmn`
   word, i.e. `Rd = 31` is the zero register. `adds x0, sp, x2` does **not** stay
   in this node: it assembles to `0xab2263e0`, the extended node (`opt = 00`,
   bit 21 = 1, `option = 011`), which `0.9.0` does not carry (`EXP-0020` §2,
   `ADR-0016` decision 6).

`adds x0, x1, #0x1000` assembles to `0xb1400420`, the `sh = 1` word, without a
diagnostic (`EXP-0020` §2): the same value-driven re-encoding `N18a` records for
`add` and `N18d` for `sub`.

## Decision

1. **Twelve forms in `definitions/aarch64/0.9.0.json`**, six `adds` and six
   `subs`, each the same row shape as its `add`/`sub` twin:
   - `aarch64:adds/x64-x64-x64-lsl0` and `aarch64:adds/x64-x64-x64-imm6-lsl` /
     `…-imm6-lsr` / `…-imm6-asr` from `ADDS_64_addsub_shift`;
   - `aarch64:adds/x64-imm12-lsl0` and `…/x64-imm12-lsl12` from
     `ADDS_64S_addsub_imm`;
   - the same six under `aarch64:subs/…` from `SUBS_64_addsub_shift` /
     `SUBS_64S_addsub_imm`.

   `0.9.0` repeats the thirty-two `0.8.0` forms unchanged and adds these twelve;
   `0.1.0` … `0.8.0` stay frozen at their digests. The new digest is
   `sha256:99728cd9bd85b8b0768e700e15dd6263171d6261c385ac15ceeb5df6d2cafcff`.
2. **The mnemonic is the form family and `S` is pinned by the node.** The
   generator reads a different MRS node for each family, and those nodes fix
   `S = 1`; no plan field names the bit and no row pins it by hand. As with
   `op`, there is no `form_id` whose `S` bit the operand list could move.
3. **The field decisions are inherited, not repeated.** `sh` (`-lsl0`/`-lsl12`),
   the shift keyword (`-imm6-lsl`/`-lsr`/`-asr`) and `imm6` as `0…63` field
   content are `ADR-0011` and `ADR-0015` applied to different nodes, with the
   same slot shapes, the same `align_bits = 0`, and the same `lsl #0` overlap
   between `-lsl0` and `-imm6-lsl` with `imm6 = 0`.
4. **`cmp` and `cmn` are out.** Naming `aarch64:cmp/x64-x64` is
   `E-FORM-001` (`N01i`): the alias fixes `Rd = 31` and removes the destination
   operand, so it is a two-operand form family of its own. The `adds`/`subs`
   rows can still write the same *bits* when a plan states register 31 as the
   destination; no ambiguity is introduced, because a plan carries a `form_id`,
   never a source spelling.
5. **The `sf = 0` S nodes are out.** Naming `aarch64:adds/w32-w32-w32-lsl0` is
   `E-FORM-001` (`N01j`). The four 32-bit S nodes fix `sf = 0` and are the
   `w`-width slice, which is still open.
6. **The extended S nodes are out.** `ADDS_64S_addsub_ext` and
   `SUBS_64S_addsub_ext` are the eight `option` rows with bit 21 set and
   `S = 1`; naming one is `E-FORM-001`. Consequently register 31 in these rows is
   `xzr`, and `adds x0, sp, x2` / `subs x0, sp, x2` are unreachable through
   `0.9.0` (`EXP-0020` §2).
7. **A literal outside the named `sh` half is `E-RANGE-001`.** `4096` stated on
   `adds/x64-imm12-lsl0` is rejected (`N18e`), never re-encoded as `-lsl12`;
   `subs` gets the same treatment by construction.
8. **No new error code and no schema change.** `E-FORM-001` and `E-RANGE-001`
   are the only codes this slice uses; both already have fixtures.

## Consequences

- `A64-P11` passes: `A64-P11-adds-subs-family` is twelve instructions (48 B),
  one per new row, with distinct registers in every row and `imm12` at 4095 and
  291<<12; its bytes match `llvm-mc` 23.1.2 (`EXP-0020` §3), with no
  relocations.
- The AArch64 table is 44 forms across nine documents, from eighteen MRS nodes.
  The `adds`/`subs` rows add four node names to the generator and no new slot
  shape.
- `EC-12` and `EC-31` are now carried on both sides of `S`, so their
  counterexamples are measured on four mnemonics; `EC-13`'s shifted-register
  half gains the flag-setting spelling.
- The negative set is 26 fixtures: `N01i`, `N01j` and `N18e` join the
  twenty-three.
- `N01g` stays valid but changes meaning: it names
  `aarch64:subs/x64-x64-x64-lsl0` against `0.8.0`, where the row does not exist
  yet. It is now a version-boundary fixture, not evidence that `subs` is
  absent from the table.

## Alternatives considered

- **One row per mnemonic with an `S` operand.** Rejected: the assembly language
  has no numeric spelling for the flag bit, and a free `S` would let a plan
  state `add`'s mnemonic with `subs`'s bytes — the `INV-07` silent-repair shape
  `ADR-0017` rejected for `op`.
- **Fold `cmp`/`cmn` into these rows as an alias variant.** Rejected: the alias
  drops an operand, so the operand list would have to change shape for the same
  `form_id` — a `form_id` names one operand shape (`01_contract.md` §7).
- **Include the `w`-width and extended S nodes here.** Deferred, not refused:
  each pins a different bit (`sf`; bit 21 plus `option`) and needs its own
  counterexample, so each is its own slice.
