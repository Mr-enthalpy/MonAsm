# EXP-0010 — the RV64 definition table is generated from `location`, not typed

- Date: 2026-11-04
- Subject: `definitions/rv64/0.1.0.json`, its five forms, and the fixtures that
  gate it
- Basis: **experiment** for every template, placement, digest and byte string
- Reproduce: `python research/evidence/experiments/EXP-0010/generate_rv64.py`
  then `cargo test --workspace`
- Depends on: `EXP-0009`, ADR-0007

## 1. What this experiment had to show

`EXP-0009` proved that a UDB `encoding.location` string is a complete description
of an instruction's variable bits and that fourteen `llvm-mc` byte strings follow
from it. That was a probe. The product needs a **table**: `form_id`s, templates,
slot placements, ranges and a digest, in the shape `fmp-def/0.1` fixes.

The risk this experiment addresses is transcription. A hand-typed table can be
wrong in a way that still looks plausible: `beq`'s 12-bit immediate has four
placements, and swapping two of them changes bytes without changing any length or
range check. So the generator derives every placement from the pinned node, and
the fixtures compare the Rust materializer against bytes produced by `llvm-mc`,
not against the generator.

## 2. Inputs, and which nodes were read

The five unblocked nodes from ADR-0007 §Decision 2, still pinned by
`tools/check_rv64_source.py`:

| Node | Form | `left_shift` |
|---|---|---|
| `inst/I/add.yaml` | `riscv:add/rd-rs1-rs2` | 0 |
| `inst/I/addi.yaml` | `riscv:addi/rd-rs1-imm12` | 0 |
| `inst/I/beq.yaml` | `riscv:beq/rs1-rs2-imm12` | 1 |
| `inst/I/jal.yaml` | `riscv:jal/rd-imm20` | 1 |
| `inst/I/auipc.yaml` | `riscv:auipc/rd-imm20` | 12 |

`inst/I/ld.yaml`, `inst/I/sd.yaml` and `inst/C/c.addi.yaml` stay in the pin but
are **not read by this generator**. `ld`/`sd` need a memory payload shape;
`c.addi` needs a non-zero constraint. Both gaps are format gaps, recorded in §7,
and the generator refuses to emit a form whose source states `not:`.

`PyYAML` is not installed in this environment (Python 3.8.10), so the generator
reads the node text with a small line-oriented extractor for exactly the fields
ADR-0007 allows: `encoding.match`, `encoding.variables[].location`,
`sign_extend`, `left_shift`, `not`, and `definedBy.extension.name`. It does not
read `operation()` or `operation_ast`. A future source change that moves a field
outside this shape fails the extractor instead of being silently ignored.

## 3. Derivation

For each form the generator:

1. builds the fixed word from `match` (`1` is a set bit, `0` a clear bit, `-` a
   variable bit, MSB first);
2. splits each operand's `location` on `|` and turns `hi-lo` into
   `{bit_offset: lo, width: hi-lo+1}` in value order;
3. asserts the union of all placements is exactly the set of `-` positions, that
   no bit is claimed twice, and that no placement touches a fixed bit;
4. asserts the source `sign_extend` and `left_shift` against the table's intent,
   so a source drift cannot silently change scaling;
5. refuses a form whose `definedBy.extension.name` is not `I`, which is why the
   document may declare `enabled_extensions: ["rv64i"]`.

The result:

| `form_id` | template | placements |
|---|---|---|
| `riscv:add/rd-rs1-rs2` | `33000000` | `[7,5]`, `[15,5]`, `[20,5]` |
| `riscv:addi/rd-rs1-imm12` | `13000000` | `[7,5]`, `[15,5]`, `[20,12]` |
| `riscv:beq/rs1-rs2-imm12` | `63000000` | `[15,5]`, `[20,5]`, `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` |
| `riscv:jal/rd-imm20` | `6f000000` | `[7,5]`, `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]` |
| `riscv:auipc/rd-imm20` | `17000000` | `[7,5]`, `[12,20]` |

Templates are little-endian file order, so `33000000` is the word `0x00000033`.
The document digest is
`sha256:8cd063a50db57179fc9ea027f1dab4de8820a7001242bc4046dc03fef1489ea2`.

`enabled_extensions` is `["rv64i"]`, not `[]`: every node says `definedBy: I`,
and `01_contract.md` §4 uses `["rv64i","rv64m","rv64c"]` as its example spelling.
One set covers the whole document and is compared exactly with the plan's, so a
plan that names `[]` or `["rv64i","rv64c"]` is `E-TARGET-001`. That is stricter
than "the mnemonic is in the table", and it is the only legality lever the
contract gives the definition.

## 4. Self-check before writing

The generator re-encodes nine vectors from the table it has just built (template
plus placements) and compares them with the bytes recorded in `EXP-0009` §6:

```text
add a0, a1, a2       33 85 c5 00
addi a0, a1, -2048   13 85 05 80
beq a0, a1, 8        63 04 b5 00
beq a0, a1, -8       e3 0c b5 fe
jal ra, 8            ef 00 80 00
jal ra, -8           ef f0 9f ff
auipc a0, 1          17 15 00 00
auipc a0, 1048575    17 f5 ff ff
```

This is a transcription check, not the two-source gate: the bytes it compares
against were produced by `llvm-mc` in `EXP-0009`, but the encoder here shares the
placement derivation with the table. §5 is the independent check.

## 5. The fixture gate

Five positive fixtures reproduce `llvm-mc 23.1.2 -triple=riscv64` bytes through
the Rust materializer:

| Fixture | Bytes | What it adds |
|---|---|---|
| `RV-P1-add-register` | `33 85 c5 00 b3 07 18 01 33 05 b0 00` | three register triples, including `x0` as a source |
| `RV-P2-addi-imm12` | `13 85 15 00 13 85 f5 ff 13 85 f5 7f 13 85 05 80` | both signed endpoints, `-2048` and `2047` |
| `RV-P4-beq-btype` | `63 04 b5 00 13 85 15 00 e3 0c b5 fe` | B-type scatter, forward and backward, through `scale(1)` fixups |
| `RV-P5-jal-jtype` | `ef 00 80 00 13 85 15 00 ef f0 9f ff` | J-type scatter, forward and backward |
| `RV-P8-auipc-imm20` | `17 15 00 00 17 f5 ff 7f 17 f5 ff ff` | field values `1`, `0x7FFFF`, `0xFFFFF` |

The branches state a **byte** displacement in the plan (a symbol plus a `scale`
fixup with `transform_shift: 1`) and the materializer stores `displacement >> 1`
in the field. That is ADR-0007 §Decision 4 exercised end to end, and it is why
`beq a0, a1, -8` comes out `e3 0c b5 fe` rather than the bytes a naive 12-bit
write would produce. Both fixups are `resolve_in_place`, so no relocation record
is emitted (`records: 0`).

`auipc a0, -1` cannot be written as a literal: `llvm-mc` requires
`[0, 1048575]` and rejects `-1`. The oracle line is `auipc a0, 1048575`, which is
the same 20-bit field, and the plan states `-1` because the slot is signed. The
oracle record says so; nothing is inferred from the assembler's spelling.

Four negative fixtures pin rejection:

| Fixture | Diagnostic |
|---|---|
| `N01-absent-form` | `E-FORM-001` at `/instructions/0/form_id` |
| `N02-operand-kind-mismatch` | `E-OPERAND-001` at `/instructions/0/operands/0/kind` |
| `N03-imm12-out-of-range` | `E-RANGE-001` at `/instructions/0/operands/2/payload/value` |
| `N04-branch-out-of-range` | `E-RANGE-002` at `/instructions/0/operands/2/payload/value` |

`N03` is the counterexample for the signed range: `addi a0, a1, 2048` must not
become `addi a0, a1, -2048` by truncation. `N04` is the same failure for the
scattered branch field, where a silent mask would keep the layout intact and only
change the target.

## 6. What the table does not do

- It does not select. Every row is one `form_id` with one template. `addi` never
  becomes `c.addi`, `jal` never becomes `jalr`, and no row is chosen from an
  operand value.
- It does not scale. The `beq`/`jal`/`auipc` slots hold field content
  (`align_bits: 0`); scaling is a fixup field (`transform_shift` 1 or 12).
- It does not lay out. No padding, relaxation or trampoline is in the document.
- It does not cover the three blocked rows in §7.

## 7. Open, and why each is a format question

- **`RV-P3` (`ld`/`sd`).** The nodes are pinned and their RV64 encoding blocks
  are simple (`imm` `[31,20]`, `xs1` `[19,15]`, `xd` `[11,7]`; `sd`: `imm`
  `[31,25]`,`[11,7]`). But `fmp/0.1` fixes the payload shapes to `{reg}`,
  `{value}`, `{symbol_id}` and `{}`, and a load/store needs a base register and an
  offset in one operand (`riscv.mem.base-offset`). Admitting it needs a contract
  change and an ADR, the same blocker as x86's P4–P6.
- **`RV-P7` (`c.addi`).** A 16-bit form whose source states `not: 0` on `imm` and
  `xd`. The generator models 16-bit words and would derive the placements
  (`[7,5]`, `[12,1]`, `[2,5]`), but `fmp-def/0.1` has no non-zero constraint, and
  `llvm-mc` accepts both zero cases as `c.nop`/HINT. Admitting the form without
  the constraint would be a silent instruction substitution (`INV-02`, `INV-07`).
- **`RV-P8`'s pair half.** The `auipc` field is in the table; the
  `R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I` relation is not in the UDB encoding
  block. `pcrel_hi20` and `lo12_i` exist as fixup transforms, but which addend
  each half carries, and which of the two halves owns which site, must come from
  a pinned psABI text before a fixture can claim the pair.

## 8. Reproduction

```powershell
$env:PYTHONIOENCODING="utf-8"
python research\evidence\experiments\EXP-0010\generate_rv64.py
python tools\check_rv64_source.py
python tools\check_definition.py
cd prototype; cargo test --workspace
```

The generator prints the five forms, the nine self-check vectors, the digest and
the `07_definition_format.md` §8.4 rows. It refuses to write if the rendered JSON
does not parse back to the document it built, or if a placement does not cover
exactly the bits `match` calls variable.
