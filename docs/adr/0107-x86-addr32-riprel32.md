# ADR-0107: the `0x67` prefix reaches the `%rip`-relative rows

- Status: accepted
- Date: 2026-11-09
- Settles: `X86-P77` (the six `addr32` `%rip`-relative rows and their byte
  vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-08` of `02_encoding_choices.md` (the prefix now names the
  base-less `%rip` shape); the reading-aid table and `0.71.0` paragraph of
  `07_definition_format.md` §8.1; the x86 table of `06_validation_matrix.md`;
  adds `definitions/x86_64/0.71.0.json`, `EXP-0108` and the
  `X86-P77`/`N01eq`/`N02cz`/`N04j` fixtures

## Context

`0.6.0` shipped the `x86:mov/r64-riprel32/legacy` and
`x86:mov/riprel32-r64/legacy` rows as `48 8b 05 …`/`48 89 05 …`, and `0.69.0`
added the SSE pair (`ADR-0105`). All four use `ModRM.mod = 00`,
`ModRM.rm = 101` and a `disp32` measured from the end of the instruction.

`EC-08` already fixes the address-size prefix as a form fact: `0x67` is
template byte 0, before any `REX`, and it selects 32-bit address registers for
a base and an index. The `%rip` form has no base and no index operand, so the
documented rule does not say what the prefix does there -- and `llvm-mc`
accepts it.

`EXP-0108` measures the shape: `addr32 movl 16(%rip), %eax` is
`67 8b 05 10 00 00 00` (seven bytes), one byte longer than the plain row, with
the displacement still the last four bytes. The prefix renames the reference
from `%rip` to `%eip`, and the value operand keeps its width (`0x66` for
`movw`, `REX.W` for `movq`), so the byte order is `0x67`, `0x66`, `REX`,
opcode.

The plan cannot express the choice as an operand: `address_width` is a
target-identity field that selects the whole table, and flipping it to `32`
would change the meaning of every other instruction in the section. Adding the
prefix from a value would make the instruction length a function of an operand
(`INV-02`, `INV-04`).

## Decision

1. **Six new rows.** `0.71.0` appends
   `x86:mov/r32-addr32-riprel32/legacy`,
   `x86:mov/addr32-riprel32-r32/legacy`,
   `x86:mov/r64-addr32-riprel32/legacy`,
   `x86:mov/addr32-riprel32-r64/legacy`,
   `x86:mov/r16-addr32-riprel32/legacy` and
   `x86:mov/addr32-riprel32-r16/legacy`, one per value width and direction.
   Templates are the measured `EXP-0108` bytes with the displacement zeroed:
   `678b0500000000`, `67890500000000`, `67488b0500000000`,
   `6748890500000000`, `67668b0500000000`, `6766890500000000`.
2. **The target keeps the existing `x86.rel`/`riprel32` slot.** One
   `operand_value` slot with `{signed: true, bits: 32, align_bits: 0}` at
   `[24,32]` for the seven-byte rows and `[32,32]` for the eight-byte ones;
   `pcrel_end` is unchanged, because the prefix moves both the field and the
   end of the instruction by the same byte.
3. **The plan stays `address_width: 64`.** The `67` byte is template content,
   not a target-identity field: a plan that declared a 32-bit address width
   would select a different table, not a prefixed row. `EC-08` is revised to
   say so.
4. **The plain rows are unchanged.** `0.70.0`'s six `%rip`-relative rows keep
   their bytes and their `0.6.0`/`0.69.0` provenance; the prefixed shape is a
   new row, never a widened existing one.
5. **`0.71.0` is additive and immutable.** It repeats the 527 `0.70.0` forms
   byte-for-byte, and the generator asserts the reproduction before it writes
   the new version. The digest is
   `sha256:2858c0f163b1239b37f7be9ba294d8d81748038987a154afac66c2b63b4d2c5b`.

## Consequences

- `X86-P77-addr32-riprel32` is the 66-byte vector of six instructions plus a
  label at offset 62. The displacements are 55/48/40/32/24/16 and every one
  resolves through `pcrel_end` with `resolve_in_place`, so the oracle emits no
  relocation record. The input hash is
  `f1c995b4acd639b2c577fcf34498c53c965acc55ff10c4c48af83efaf1da7962` and the
  output hash is
  `9bda3dc77fa5b3abec9b6ac4e3e4a742c1f0d127fd13dec1c198c045c0fb2987`.
- `N01eq` pins the `0.70.0` boundary, `N02cz` the operand count
  (`expected: 2`, `found: 1`) and `N04j` the signed-32 end on the new field
  placement.
- The corpus grows to 118 positives and 577 negatives; every one of the 533
  forms in `0.71.0` is named by a positive fixture (`check_definition.py`).
- `0.70.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **Flip `address_width` to `32` in the plan.** Rejected: that field selects
  the target table and changes the meaning of every instruction; the prefix is
  one instruction's form fact (`INV-05` would also lose the plan/target
  identity).
- **Let the materializer insert `0x67` when the displacement is a symbol.**
  Rejected: the prefix would then depend on the operand shape, and the
  instruction length would change with it (`INV-02`, `INV-04`).
- **Reuse the plain `r32-riprel32` row and add a `prefix` operand.** Rejected:
  the prefix is not an operand in any other row; a modifiable prefix operand
  would be implicit encoding-form selection.
- **Add the `movb` sibling now.** Rejected: there is no plain `movb`
  `%rip`-relative row to prefix; the slice widens only rows that already
  exist.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The six instructions are 7/7/8/8/8/8 bytes | `llvm-mc` object bytes, `EXP-0108` §2 | high |
| The prefix order is `0x67`, `0x66`, `REX`, opcode | measured bytes, `EXP-0108` §2 | high |
| The target is the last 32 bits (`[24,32]`/`[32,32]`) | placement arithmetic on the measured bytes | high |
| `llvm-mc` `addr32` is the `0x67` prefix | `llvm-mc -show-encoding` output in `EXP-0108` | high |
| `0.71.0` repeats `0.70.0` unchanged | generator assertion and digest | high |
| `N01eq` is `E-FORM-001`, `N02cz` `E-OPERAND-002`, `N04j` `E-RANGE-002` | fixture gate, `EXP-0108` §4 | high |

## Review triggers

- A `%rip`-relative row of another opcode is proposed; the opcode byte changes
  and the row must be measured, not copied from `mov`.
- The prefix meets a base or an index; those rows already exist behind `0x67`
  and their prefix order is pinned by `ADR-0080`-`ADR-0082`.
- A plan is proposed to express the prefix through `address_width`; the field
  is target identity, not a per-instruction option.
- `moffs` (`A0`-`A3`) is proposed; it is a different addressing form with an
  absolute 64-bit address, not a `%rip` variant.
