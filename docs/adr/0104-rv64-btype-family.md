# ADR-0104: the RV64 B-type mnemonic family is five more rows

- Status: accepted
- Date: 2026-11-09
- Settles: `RV-P11` (the five remaining B-type mnemonics and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: the RV64 table of `06_validation_matrix.md`; the reading-aid table
  `07_definition_format.md` §8.6; `docs/STATUS.md` (ADR table and widening
  backlog); adds `definitions/rv64/0.5.0.json`, `EXP-0105` and the
  `RV-P11`/`N01en`/`N02cw`/`N04h` fixtures

## Context

`0.4.0` has one B-type row, `riscv:beq/rs1-rs2-imm12`. `EC-22` froze the
B-type field as a fixed scatter with a `scale(1)` fixup, and `RV-P4` exercises
it. The other five conditional-branch mnemonics are absent, so a plan that
needs "branch if not equal" or an unsigned comparison cannot express it at all.

`EXP-0105` reads the five pinned UDB nodes and measures them with
`llvm-mc`/`llvm-objcopy` 23.1.2. All five agree with `beq.yaml` on
`location: "31|7|30-25|11-8"`, `left_shift: 1`, `definedBy: I` and
`opcode = 1100011`; they differ only in `funct3`. The measured bytes for
`bne`/`blt`/`bge`/`bltu`/`bgeu` at `a0, a1, 8` are `63 14 b5 00`,
`63 44 b5 00`, `63 54 b5 00`, `63 64 b5 00` and `63 74 b5 00`, and the two
backward branches in `RV-P11` carry the negative field `-4`.

## Decision

1. **Five forms, not one parameterised branch.** `0.5.0` appends
   `riscv:bne/rs1-rs2-imm12`, `riscv:blt/...`, `riscv:bge/...`,
   `riscv:bltu/...` and `riscv:bgeu/...`, with templates
   `63100000`/`63400000`/`63500000`/`63600000`/`63700000`. The slots are
   `beq`'s four-placement 12-bit target plus `src`/`src2`; only the three
   `funct3` template bits change. A mnemonic is a form family because the
   materializer must not choose it (`INV-01`), and `funct3` is a byte-affecting
   field.
2. **The fixup rule is unchanged.** `pcrel_begin`, `value_transform: scale`,
   `transform_shift: 1`, `range_constraint {signed: true, bits: 12,
   align_bits: 1}`, `resolve_in_place`. `EXP-0105` §2 shows the forward and
   backward signs in one 20-byte vector, and `N04h` shows the range end.
3. **`0.5.0` is additive and immutable.** It repeats the ten `0.4.0` forms
   byte-for-byte; the generator asserts the reproduction before it writes the
   new version. The digest is
   `sha256:571ab1ed93f4464d5ec8981df02dd0444005ababdaaf1e175d0ec489bb33a776`.
4. **The version boundary is loud.** Naming `bne` against `0.4.0` is
   `E-FORM-001` (`N01en`), not a fallback to `beq`.
5. **The compressed family stays absent.** `c.j`/`c.jalr` remain `EC-23`
   non-goals; `beqz`/`bnez` are pseudoinstructions the source nodes name, and
   v0 does not expand aliases (`INV-03`).

## Consequences

- `RV-P11-btype-family` is the 20-byte vector; the oracle input hash is
  `32ea6fb614ee855a4180a646ed6d06139cee9bc2c6bdbad98aa5c126aa12a505` and the
  output hash is
  `1ff019414f397e09250a81f5650c0c2d5f5b35fe128cabc600c5263085dfb581` with 0
  relocation records.
- `N02cw` pins the operand class (an `imm` where the slot needs `xreg` gives
  `E-OPERAND-001`), and `N04h` pins the signed 12-bit content end (`2048` is
  `E-RANGE-002`).
- The corpus grows to 115 positives and 568 negatives; every one of the 15
  forms in `0.5.0` is named by a positive fixture (`check_definition.py`).
- `0.4.0` remains readable and unchanged, so a plan pinned to it keeps its
  old byte behaviour and cannot see the new rows.

## Alternatives rejected

- **One `riscv:branch/rs1-rs2-imm12` row with a condition operand.** Rejected:
  the condition is `funct3`, a byte-affecting encoding decision. A condition
  operand would make the materializer choose the bits, which is `INV-01`.
- **Widen `beq` in place and alias the other mnemonics.** Rejected: a form_id
  names one encoding; `beq` and `bne` are different bytes and must be
  different rows, and aliasing needs an expansion table (`INV-03`).
- **Add `c.j`/`c.jalr` in the same slice.** Rejected: `EC-23` keeps the
  compressed family absent, and a 2-byte form would change the length axis
  without a measurement of its own.
- **Reuse `beq`'s fixup with `pc_reference_rule: pcrel_end`.** Rejected: RV64
  branches measure from their own address; `RV-P4`/`EXP-0105` measure
  `pcrel_begin`, and `pcrel_end` would move every target by one instruction.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The five nodes share `beq`'s scatter and `left_shift` | five pinned UDB YAMLs, `EXP-0105` §1 | high |
| `funct3` is 001/100/101/110/111 | `encoding.match` of the five nodes | high |
| The five templates encode the measured bytes | object bytes, `EXP-0105` §2 | high |
| `0.5.0` repeats `0.4.0` unchanged | generator assertion and digest | high |
| `N01en` is `E-FORM-001`, `N02cw` is `E-OPERAND-001`, `N04h` is `E-RANGE-002` | fixture gate, `EXP-0105` §4 | high |

## Review triggers

- A compressed branch lands; it needs its own length/field ADR and cannot
  share these rows.
- A pseudoinstruction (`beqz`, `bnez`, …) is proposed as a form; v0 rejects
  expansion, so that is a new decision, not a template tweak.
- The UDB drop changes one node's `location` or `left_shift`; the generator's
  source checks fail and the table must be regenerated from a new pin.
