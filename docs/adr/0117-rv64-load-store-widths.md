# ADR-0117: the RV64 load/store widths are nine more rows

- Status: accepted
- Date: 2026-11-10
- Settles: `RV-P12` (the nine load/store rows and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: the RV64 table of `06_validation_matrix.md`; adds `07_definition_format.md`
  §8.7; marks the `S5` row of `10_m6_plan.md` landed; adds
  `definitions/rv64/0.6.0.json`, `EXP-0116` and the
  `RV-P12`/`N01fd`/`N01fe`/`N03a0` fixtures

## Context

`0.5.0` has exactly two memory rows, `riscv:ld/rd-base-imm12` and
`riscv:sd/rs-base-imm12`. A plan that needs a byte, halfword or word access
cannot express it at all, so a compiler-backed plan would have to use `ld`/`sd`
and then narrow the register, which is not the instruction it wrote.

The nine missing operations are the same encoding family. In the pinned UDB
drop, `inst/I/{lb,lh,lw,lbu,lhu,lwu}.yaml` all declare
`encoding.match "...FUNCT3...0000011"` with `imm` at 31-20
`sign_extend: true`, `xs1` at 19-15 and `xd` at 11-7; `inst/I/{sb,sh,sw}.yaml`
declare `...FUNCT3...0100011` with `imm` at `"31-25|11-7"`
`sign_extend: true`, `xs2` at 24-20 and `xs1` at 19-15. Only `funct3`
(bits 12-14) changes, so the slot geometry `0.5.0` already carries is the
geometry of all nine rows. `lwu` is additionally restricted to `xlen: 64`.

`EXP-0116` derives the expected bytes from those fields, then assembles the
same eleven lines with `llvm-mc` 23.1.2 and reads them back with
`llvm-objdump -d`. The two reads agree, and the disassembly names the mnemonic
each row claims.

## Decision

1. **Nine new rows.** `0.6.0` appends `riscv:lb/rd-base-imm12`,
   `riscv:lh/rd-base-imm12`, `riscv:lw/rd-base-imm12`,
   `riscv:lbu/rd-base-imm12`, `riscv:lhu/rd-base-imm12`,
   `riscv:lwu/rd-base-imm12`, `riscv:sb/rs-base-imm12`,
   `riscv:sh/rs-base-imm12` and `riscv:sw/rs-base-imm12`. `ld`/`sd` are
   unchanged.
2. **The geometry is the sibling's, not a copy by hand.** Each load row takes
   `ld`'s `dest`/`base`/`disp` slots and each store row takes `sd`'s
   `src`/`base`/`disp` slots. The generator asserts the two source geometries
   (placements and roles) before it copies them, and changes only `form_id`
   and `template`.
3. **The template is derived twice.** The generator computes
   `funct3 << 12 | opcode` from the node's `match` and compares it with a
   hand-written little-endian template; the fixture then compares the table
   with the assembler's bytes.
4. **No `EC` row is added.** The width is selected by the mnemonic, so it is a
   form variant, not a field whose value the materializer could choose
   (`INV-01`, `INV-02`). The `imm12` field itself is already pinned by `sd`
   (`07_definition_format.md` §8.4), and this slice does not change it.
5. **`0.6.0` is additive and immutable.** It repeats the fifteen `0.5.0` forms
   byte-for-byte; the generator asserts the reproduction before it writes the
   new version. The digest is
   `sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585`.
6. **The version boundary is loud.** Naming `lw` against `0.5.0` is
   `E-FORM-001` (`N01fe`), never a fallback to `ld`.
7. **What stays out is named.** `fence` (`EC-24`), `ecall`/`ebreak`, the
   atomics (`EC-26`) and the compressed load/store family (`EC-19`, `EC-23`)
   remain `E-FORM-001`. `N01fd` records the `fence` absence.

## Consequences

- `RV-P12-load-store-widths` is the 44-byte vector of eleven instructions: the
  nine rows at `8(a1)` plus `lb a0, -2048(a1)` and `sw a2, 2047(a1)`, the two
  ends of the signed 12-bit field. The input hash is
  `301eb7d4ecf93528940a184510427a51cb97f62b8cd7a09bfc9cc77cb7172b6d` and the
  output hash is
  `4cac900aeda50e5169475d4077e1819e8daa0c1e2353d36e530fbc46685fbfd0`.
  Every instruction is selectable from a mnemonic, so the oracle is `assembler`
  and `tools/oracle/rerun.py` re-derives the whole image.
- `N01fd` (absent `fence`) and `N01fe` (the `0.5.0` boundary) are
  `E-FORM-001`; `N03a0` (`disp = 2048` on `sw`) is `E-RANGE-001`, which also
  shows the range is the 12-bit content and not the 7-bit or 5-bit placement.
- The RV64 tables grow to 24 forms. The corpus grows to 126 positives and 604
  negatives, and every form in `0.6.0` is named by a positive fixture
  (`check_definition.py`).
- `0.5.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **One parameterised row with a width operand.** Rejected: the width is
  `funct3`, template content; a width selector would be an implicit
  instruction/encoding-form choice (`INV-01`, `INV-02`).
- **Derive the rows from `ld`/`sd` using a mnemonic suffix map.** Rejected:
  the source is the per-mnemonic node, and the generator reads each node; a
  suffix map would invent structure the spec does not state.
- **Add `fence` in the same slice.** Rejected: `EC-24` names it as a field
  choice (`fm`/`pred`/`succ`), so it needs its own operand class and its own
  decision.
- **Add the compressed `c.lw`/`c.sw` rows.** Rejected: `EC-19`/`EC-20` govern
  the compressed family, which is a separate slice with its own register-class
  exclusions.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `0.5.0` has only `ld`/`sd` as memory rows | form-id scan of `definitions/rv64/0.5.0.json` | high |
| The nine nodes differ from `ld`/`sd` only in `funct3` | UDB node `encoding.match`, asserted by the generator | high |
| The eleven instructions are 44 bytes | `llvm-mc` object bytes, `EXP-0116` `measure.py` | high |
| The field derivation and the assembler agree | `measure.py` compares the derived words with the assembled image | high |
| The disassembly names the same mnemonics | `llvm-objdump -d`, `EXP-0116` `direction.txt` | high |
| `N01fd`/`N01fe` are `E-FORM-001`, `N03a0` `E-RANGE-001` | fixture gate, `EXP-0116` | high |
| `0.6.0` repeats `0.5.0` unchanged | generator assertion and digest | high |

## Review triggers

- `fence` is proposed; it is `EC-24` and needs a mask operand class.
- The compressed load/store rows are proposed; they are `EC-19`/`EC-20` and
  need the `x8`–`x15` register-class exclusions.
- Atomics are proposed; they are `EC-26` and need the `aq`/`rl` form variants.
- A scaled displacement is proposed; RV64 does not scale the load/store
  immediate, so that would be a different architecture fact, not a transform.
- `ld`/`sd` change; they are outside this slice and their slots are the
  geometry the nine rows reuse.
