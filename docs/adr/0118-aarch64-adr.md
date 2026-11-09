# ADR-0118: `adr` is one more row, not a reading of `adrp`

- Status: accepted
- Date: 2026-11-10
- Settles: `A64-P23` (the `adr` row and its byte vector)
- Supersedes: none
- Superseded by: none
- Revises: the AArch64 table of `07_definition_format.md` §8.2 and §8.3; adds
  `EC-43` to `02_encoding_choices.md`; adds the `adr` row to
  `03_fixup_model.md` §6; adds the `A64-P23` row and the `N01ff`/`N01fg`/`N04k`
  entries to `06_validation_matrix.md`; marks the `S6` row of `10_m6_plan.md`
  landed; adds `definitions/aarch64/0.19.0.json`, `EXP-0117` and the four
  fixtures

## Context

`0.18.0` can form a PC-relative *page* address (`aarch64:adrp/x64-imm21`) and
can branch (`b`/`bl`/`b.cond`), but it cannot form a PC-relative *byte* address.
A plan that needs the address of a nearby label has no row for it and would have
to name `adrp` plus a `:lo12:` `add`, which is a different two-instruction
sequence.

The pinned Arm MRS drop has two nodes, `ADR_only_pcreladdr` and
`ADRP_only_pcreladdr`, and they differ in exactly one fixed bit: `op` at 31 is
`0` for `adr` and `1` for `adrp`. Every other field has the same range —
`immlo` at 29+2, `immhi` at 5+19, `Rd` at 0+5, and the same fixed `100`/`00`
bits at 26+3 and 24+2. So the template is `00000010` against `adrp`'s
`00000090`, and the two rows have identical slot geometry.

What differs is what the 21 bits mean. `adrp` holds a 4 KiB page delta from the
instruction's page; `adr` holds a byte displacement from the instruction
address. `EXP-0117` measures both: `adr x1, #8` is `41 00 00 10` (imm21 = 8,
a byte count), while `adrp x1, #4096` is `01 00 00 b0` (imm21 = 1, a page
count, so the low bit lands in `immlo` and the word is not a simple `+1`). The
cleanest contrast needs no arithmetic at all: `adr x0, #0` is `00 00 00 10` and
`adrp x0, #0` is `00 00 00 90`.

## Decision

1. **One new row.** `0.19.0` appends `aarch64:adr/x64-imm21`, template
   `00000010`, `dest` at `[0,5]` and `target` at `[5,19]`, `[29,2]`. It reuses
   the `aarch64.rel`/`imm21` target type and the `0.1.0` slot shape unchanged.
2. **The generator reads the sibling node, not a literal.** The row's spec names
   `ADR_only_pcreladdr`; the fixed-bit scan turns `op = 0` into bit 31 and the
   coverage check refuses to emit unless all 32 bits are covered exactly once.
   The `adrp` row's spec still names `ADRP_only_pcreladdr`, so the one-bit
   difference is asserted by reading two nodes, not by copying a template.
3. **No new slot kind and no new transform.** The 21-bit value is one signed
   byte count, so the slot is `{ signed: true, bits: 21, align_bits: 0 }` — the
   same as `adrp`'s — and a symbol target is `pcrel_begin` + `identity`. There
   is no shift, no page rounding and no `pair_group`: the field content *is* the
   displacement.
4. **A new `EC` row is required.** The same field content means bytes on one row
   and pages on the other, and a single row would have to read the number to
   decide, then choose a transform — an implicit encoding-form choice
   (`INV-02`). `EC-43` records that, with the two measured pairs.
5. **`0.19.0` is additive and immutable.** It repeats the one hundred and eighty
   `0.18.0` forms byte-for-byte; the generator asserts the reproduction of every
   earlier digest, `0.18.0` included, before it writes the new document. The
   digest is
   `sha256:f299d978b734a295fe111f6e03999d891d08a84e6d02c36ce83ee9a25c961546`.
6. **The version boundary is loud.** Naming `aarch64:adr/x64-imm21` against
   `0.18.0` is `E-FORM-001` (`N01fg`), never a fallback to `adrp`.
7. **The absent page variant is named.** `aarch64:adr/x64-imm21-page` is not a
   row (`N01ff`); the page row is `aarch64:adrp/x64-imm21`, and it keeps
   `pcrel_page` + `page` (`03_fixup_model.md` §6).
8. **What stays out is named.** `tbz`/`tbnz` (`EC-18`) and the `mov` alias
   (`EC-16`) stay closed, as does the `adrp` + `:lo12:` pair already covered by
   `A64-P6`.

## Consequences

- `A64-P23-adr-imm21` is a 32-byte vector of eight instructions: five literal
  displacement fields (`0`, `8`, `−8`, `1048575`, `−1048576`, the last two
  being the signed 21-bit ends) and three symbol sites giving `0`, `−24` and
  `−8`. The input hash is
  is `532e93eecb57465e734b6705e924d04d51c0d24a5e763e4bb7ca5ef2f9cbf5f9` and
  the output hash is
  `7a179c052ac4ca977991a96f362210b61e3377d6e3035381e411a8c1a049a01c`. The
  targets are local labels in one section, so `llvm-mc` resolves them,
  `llvm-readobj -r` is empty and the oracle needs no linker.
- The range is `−1048576 … 1048575` bytes, one signed 21-bit field. `llvm-mc`
  rejects `adr x0, #1048576` (`expected label or encodable integer pc offset`)
  and the materializer rejects the same plan as `E-RANGE-002` with
  `max 1048575` (`N04k`), so the field end is checked by two independent paths
  rather than by the assembler alone.
- `0.19.0` has 181 forms; the corpus grows to 127 positives and 607 negatives,
  and every form in `0.19.0` is named by a positive fixture
  (`check_definition.py`).
- `0.18.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new row and keeps its old byte behaviour.
- The record is the guard, not the mnemonic. Nothing in `fmp/0.1` ties
  `identity` to `adr`, so `adr` with `pcrel_page` + `page` is accepted;
  `EXP-0117/probe_transform.py` measures it (rejected as `E-FIXUP-002` without a
  section `base_address`, accepted with one, emitting bytes). That is the same
  limit `b`/`bl` has, and it is recorded rather than papered over.

## Alternatives rejected

- **One row with a `page`/`byte` modifier.** Rejected: the modifier would select
  a template bit and a value meaning at once, which is an implicit encoding-form
  choice (`INV-02`) and would also let a plan keep the wrong transform.
- **Teach the materializer that `adr` implies `identity`.** Rejected: the
  format has no per-mnemonic transform table, and adding one would make the
  mnemonic an implicit input to validation (`INV-01`). The contract's answer is
  that the plan states both facts; `EXP-0117/probe_transform.py` records the
  consequence instead of hiding it.
- **Express `adr` as `scale(2)` over a word count.** Rejected: the assembler
  and the MRS node both put bytes in the field, and `align_bits: 0` is what lets
  the field hold a byte offset. A `scale` fixup with `transform_shift: 0` would
  be the same arithmetic under a misleading name.
- **Route `adr` through the `adrp` row with a page-aligned target.** Rejected:
  that is a different instruction (`op = 1`) and a different meaning; the bytes
  are `+0x80000000` apart and the target would be rounded to a page.
- **Add `adr` as an alias chosen by the immediate's value.** Rejected: a value
  would then pick the mnemonic, which is `EC-16`'s rejected device and the
  reason `mov` has no row.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `ADR_only_pcreladdr` is `ADRP_only_pcreladdr` with `op = 0` | MRS node field scan, `EXP-0117` `measure.py` asserts the ranges | high |
| The eight instructions are 32 bytes and the split is `immlo` 29+2 / `immhi` 5+19 | `measure.py` derives each word from the node, then compares with `llvm-mc` | high |
| The reference point is the instruction, not its end | three symbol sites give `0`, `−24`, `−8`; `llvm-objdump -d` prints `P + v` | high |
| The field is bytes, `adrp`'s is pages | `adr x1, #8` = `41 00 00 10` vs `adrp x1, #4096` = `01 00 00 b0`; `adr x0, #0` vs `adrp x0, #0` differ in bit 31 only | high |
| The range ends are `±1 MiB` with `max 1048575` | measured literals plus `llvm-mc` rejecting `1048576`; `N04k` is `E-RANGE-002` | high |
| `0.19.0` repeats `0.18.0` unchanged | generator assertion on the frozen digest | high |
| `N01ff`/`N01fg` are `E-FORM-001`, `N04k` is `E-RANGE-002` | fixture gate, `EXP-0117` | high |
| The transform is not coupled to the mnemonic | `EXP-0117/probe_transform.py` materializes `adr` with `page` | high |

## Review triggers

- `adrp` + `:lo12:` needs a byte-address alternative; that is a new slice, not a
  rereading of this row.
- `tbz`/`tbnz` (`EC-18`) or the `mov` alias (`EC-16`) are proposed; they are
  separate rows with their own operand classes.
- A plan is found that relies on `adr` + `page`; the fix would be a contract
  rule, which needs its own ADR, not a change here.
- The `w`-register or `adr`-with-shift forms are proposed; the MRS node has no
  such field, so each would be a different node.
