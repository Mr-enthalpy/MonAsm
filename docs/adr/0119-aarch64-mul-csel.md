# ADR-0119: `mul` is `madd` with the accumulator pinned, `csel` is its own row

- Status: accepted
- Date: 2026-11-10
- Settles: `A64-P24` (the `mul` and `csel` rows and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: the AArch64 table of `07_definition_format.md` §8.2 and §8.3 and the
  document digest list in §8; adds
  `EC-44` to `02_encoding_choices.md`; adds the `A64-P24` row and the
  `N01fh`/`N01fi`/`N02dd`/`N03a1` entries to `06_validation_matrix.md`; marks
  the `S7` row of `10_m6_plan.md` landed and corrects its `cond = 16` claim;
  adds `definitions/aarch64/0.20.0.json`, `EXP-0118`, the `A64-P24` vector and
  the four negatives

## Context

`0.19.0` can add, subtract, compare, load, store and branch, but it cannot
multiply and it cannot select on a condition. A plan that needs either has no
row for it: `mul` would have to be spelled as a four-operand `madd` with a
`xzr`/`wzr` accumulator, and `csel` would have to be spelled as a branch pair.

The pinned Arm MRS drop has no `MUL` *encoding*. It has a `MUL` alias node
(`_type` `Instruction.InstructionAlias`, `operation_id` `MUL_MADD`,
`condition` `Ra == '11111'`, `preferred: true`, no `encoding`) over the two
`MADD` base nodes, `MADD_32A_dp_3src` and `MADD_64A_dp_3src`. Both base nodes fix
`op54` at 29+2, `op1` at 28+1, `101` at 25+3, `1` at 24+1, `op31` at 21+3 and
`o0` at 15+1, and leave `Rd` at 0+5, `Rn` at 5+5, `Rm` at 16+5 and `Ra` at
10+5; the width is the node's `sf` at 31. So `mul` is the base encoding with
one five-bit field pinned, not a second opcode.

`CSEL_32_condsel` and `CSEL_64_condsel` are ordinary instruction nodes. They fix
`op` at 30, `S` at 29, `op1` at 28, `101` at 25+3, `0100` at 21+4, bit 11 to 0
and `o2` at 10 to 0, and leave `Rd` at 0+5, `Rn` at 5+5, `Rm` at 16+5 and
`cond` at 12+4. That is the same four-bit condition slot `B_only_condbranch`
already exposes as `aarch64.cond`/`cond4`.

`EXP-0118` measures both families and their two contrasts. `mul x0, x1, x2` is
`9b027c20` and `madd x0, x1, x2, x3` is `9b020c20`: the words differ only in
bits 14-10 (`Ra`, 31 vs 3). `csel x0, x1, x2, eq` is `9a820020` and
`csinc x0, x1, x2, eq` is `9a820420`: they differ only in bit 10 (`o2`).

## Decision

1. **Four new rows.** `0.20.0` appends `aarch64:mul/w32-w32-w32` and
   `aarch64:mul/x64-x64-x64` (templates `007c001b` and `007c009b`, `Ra` pinned
   to 31), plus `aarch64:csel/w32-w32-w32-cond4` and
   `aarch64:csel/x64-x64-x64-cond4` (templates `0000801a` and `0000809a`).
2. **The generator reads the alias node and the base node.** The row's spec names
   the base node and the alias mnemonic; `verify_alias` derives the alias
   `operation_id` as `<alias mnemonic>_<base operation_id>` (here `MUL_MADD`,
   which is the same rule that yields `CMP_SUBS_addsub_shift`), selects the
   width by the alias node's `_meta.encoded_in`, and asserts the alias carries
   no `encoding`, is `preferred`, and pins
   `alias_condition_field` (default `Rd`, `Ra` for this family) to `'11111'`.
   The bytes still come from the base node's field scan, so a wrong pin is a
   mismatch, not a copied template.
3. **`mul` has three operands and no accumulator.** The plan names `dest`,
   `src` and `src2`; `Ra = 31` is the row's decision. The shape matches the
   `cmp`/`cmn` precedent (`ADR-0021`), where the alias also drops the register
   the base node encodes. A four-operand `mul` is not a row (`E-FORM-001`,
   `N01fh`), because accepting it would make the alias and `madd` the same row.
4. **`wzr` is legal in `mul`'s `Rm`.** The `mul` rows read plain register
   numbers and exclude nothing, so `mul w0, w1, wzr` is `207c1f1b`; pinning
   `Ra` does not make 31 a reserved operand value elsewhere. `A64-P24` measures
   that row.
5. **`csel` carries the condition as an operand.** Its slot is
   `aarch64.cond`/`cond4`, unsigned 4 bits, with no `excluded` list: all sixteen
   values are conditions the ISA defines, `al` (14) and `nv` (15) included.
   `A64-P24` measures `eq`, `ne`, `al` and `nv`; `cond = 16` is
   `E-RANGE-001` (`N03a1`), the same shape `N03-cond-out-of-range` has on
   `b.cond`.
6. **A new `EC` row is required.** `mul` and `madd` are the same word except
   `Ra`, and the accumulator is not an operand the mnemonic names. A single
   `madd` row with a free `Ra` would emit `mul`'s word or a `madd` word
   depending on an operand value, and would make the plan spell a register the
   mnemonic cannot name — the same device `EC-33` rejects for `cmp`/`cmn`.
   `EC-44` records it with the measured pair.
7. **`0.20.0` is additive and immutable.** It repeats the one hundred and
   eighty-one forms of `0.19.0` byte-for-byte; the generator asserts the
   reproduction of every earlier digest, `0.19.0` included, before it writes
   the new document. The digest is
   `sha256:05033c9e1c5ca430d2922312cf7139c9bc4e8cc7c34364e24a455efa9a1df6cd`.
8. **The version boundary is loud.** Naming a `0.20.0` row against `0.19.0`
   is `E-FORM-001` (`N01fi`), never a fallback to a base row.
9. **The planning document's error code is corrected.** `10_m6_plan.md` §3 S7
   said `cond = 16` is `E-OPERAND-004`; measured, it is `E-RANGE-001` at
   `/instructions/0/operands/3/payload/value` with `min 0`, `max 15`,
   `target_type cond4` (`N03a1`). The plan is amended here rather than left to
   disagree with the gate.
10. **What stays out is named.** `madd`/`msub` with a non-zero `Ra`, the
    `cset`/`cinc` family, `tbz`/`tbnz` (`EC-18`) and the `mov` alias (`EC-16`)
    have no row; each is a separate decision.

## Consequences

- `A64-P24-mul-csel` is a 32-byte vector of eight instructions: three `mul`
  rows (32-bit, 64-bit, and `wzr` in `Rm`) and five `csel` rows over both widths
  and the conditions `eq`, `ne`, `al`, `nv`, `gt`. The input hash is
  `b9e200fc9cdc9751c06fbc0b4239b9373b18cba098d3a89f4e20bc3ac2051410` and the
  output hash is
  `bdae66527cf6d5832b1a157cf74263f04f8f5fd6c89ba8505a222d6477930d44`.
  Measured words: `627c041b`, `c57c079b`, `207c1f1b`, `28018a1a`, `8b118d9a`,
  `20e0829a`, `83f0851a`, `1fc0809a`. The vector has no symbol and no fixup, so
  `llvm-readobj -r` is empty and no linker is involved.
- `0.20.0` has 185 forms across twenty documents; the corpus grows to 128
  positives and 611 negatives, and every form in `0.20.0` is named by a positive
  fixture (`check_definition.py`).
- `0.19.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.
- The four new negatives are `E-FORM-001` (`N01fh` the `madd` shape named
  `mul`, `N01fi` the version boundary), `E-OPERAND-002` (`N02dd`, two operands
  on a three-operand row) and `E-RANGE-001` (`N03a1`, `cond = 16`).
- `cond` is not a modifier. A plan that states `eq` as a `modifiers` entry
  instead of the fourth operand is the same `E-OPERAND-002` operand-count
  failure `N02dd` measures, not a silent conversion.
- The row is the guard, not the mnemonic. Nothing in `fmp/0.1` ties
  `007c001b`'s pinned `Ra` to the name `mul`, so a plan that names the row and
  means `madd` emits `mul` bytes; that is a wrong plan, which is the same limit
  `adr` has (`ADR-0118`).

## Alternatives rejected

- **One `madd` row with a free `Ra`.** Rejected: `mul` and `madd` would then be
  the same row, and whether the plan writes 31 would pick the mnemonic, which is
  `EC-33`'s rejected device and the reason `cmp` is its own family.
- **A `mul` modifier that fixes the accumulator.** Rejected: a modifier
  describes an operand and must not write a template bit; `N19d` already
  rejects a `link` modifier on a branch target for the same reason, and `Ra` is
  not an operand of the alias.
- **Give `mul` four operands and require `xzr`.** Rejected: the mnemonic cannot
  name a fourth register, so the plan would spell a decision the assembly does
  not carry, and `madd` with a non-zero accumulator would need a second row
  anyway.
- **Reuse `B_only_condbranch`'s condition spelling as a keyword-suffix row per
  condition.** Rejected: `b.cond` keeps `cond` as an operand at 0+4, and the
  sixteen-value `cond4` slot is already frozen; sixteen `csel` rows per width
  would store in the name what the field already carries (`INV-02` is not at
  issue, but the operand is the shorter and already-tested form).
- **Express `csel` as `csinc` with a condition that inverts the predicate.**
  Rejected: `o2` at bit 10 is 0 for `csel` and 1 for `csinc`, so the substitution
  changes the word the plan means and adds an implicit predicate rewrite
  (`EXP-0118` measures the one-bit contrast).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `MUL` is an alias node with `operation_id` `MUL_MADD`, condition `Ra == '11111'`, `preferred: true`, no `encoding` | `EXP-0008/generate_aarch64.py` `verify_alias` asserts each part before the document is written; `EXP-0118/measure.py` reads the base nodes | high |
| `MADD_*_dp_3src` fixes `op54`/`op1`/`op31`/`o0` and leaves `Rd`/`Rn`/`Rm`/`Ra` | MRS field scan, `EXP-0118` `measure.py` asserts the ranges | high |
| The eight instructions are 32 bytes and match the field derivation | `measure.py` derives each word from the node, then compares with `llvm-mc` 23.1.2 and `llvm-objdump -d` | high |
| `mul` and `madd` differ only in `Ra` (bits 14-10) | measured `9b027c20` vs `9b020c20`, xor `0x7000` | high |
| `csel` and `csinc` differ only in `o2` (bit 10) | measured `9a820020` vs `9a820420`, xor `0x0400` | high |
| All sixteen condition values are legal on `csel` | node has no `excluded` list; measured `eq`/`ne`/`al`/`nv`; `cond = 16` is `E-RANGE-001` | high (the `al`/`nv` readings are assembled words, not an ISA statement) |
| `0.20.0` repeats `0.19.0` unchanged | generator assertion on the frozen digest | high |
| `N01fh`/`N01fi` are `E-FORM-001`, `N02dd` is `E-OPERAND-002`, `N03a1` is `E-RANGE-001` | CLI probe and the fixture gate | high |

## Review triggers

- `madd`/`msub` with a non-zero accumulator is proposed; that is a new row with
  four operands, and the `EC-44` split stays.
- `cset`/`cinc`/`csinv`/`csneg` are proposed; they are aliases over
  `CSINC`/`CSINV`/`CSNEG`, each with its own pinned field and condition
  inversion.
- `tbz`/`tbnz` (`EC-18`) or the `mov` alias (`EC-16`) are reopened; both stay
  closed by their own ADRs.
- A plan is found that relies on `csel`'s `o2 = 1` (the `csinc` word) named as
  `csel`; the answer is a new row, not a modifier here.
- The 32-bit and 64-bit `mul` rows disagree on a register-31 case; the rows have
  no exclusion, so the measured `wzr` row is the reference.
