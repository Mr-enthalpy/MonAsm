# EXP-0010 — the RV64 definition tables are generated from `location`, not typed

- Date: 2026-11-04
- Subject: `definitions/rv64/{0.1.0,0.2.0}.json`, their eight forms, and the
  fixtures that gate them
- Basis: **experiment** for every template, placement, digest and byte string
- Reproduce: `python research/evidence/experiments/EXP-0010/generate_rv64.py`
  then `cargo test --workspace`
- Depends on: `EXP-0009`, `EXP-0011`, `EXP-0012`, ADR-0007, ADR-0008, ADR-0009

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

A second risk appears when a form needs a slot-level legality rule: `c.addi`
rejects two in-range values. `EXP-0012` measured that case; ADR-0009 added
`excluded` so the rule is data, not a predicate. This experiment emits both
documents from the same built forms and shows that adding `c.addi` does not move
`0.1.0`.

## 2. Inputs, and which nodes were read

The eight nodes from ADR-0007 §Decision 2, still pinned by
`tools/check_rv64_source.py`:

| Node | Form | `left_shift` | Document |
|---|---|---|---|
| `inst/I/add.yaml` | `riscv:add/rd-rs1-rs2` | 0 | `0.1.0`, `0.2.0` |
| `inst/I/addi.yaml` | `riscv:addi/rd-rs1-imm12` | 0 | `0.1.0`, `0.2.0` |
| `inst/I/beq.yaml` | `riscv:beq/rs1-rs2-imm12` | 1 | `0.1.0`, `0.2.0` |
| `inst/I/jal.yaml` | `riscv:jal/rd-imm20` | 1 | `0.1.0`, `0.2.0` |
| `inst/I/auipc.yaml` | `riscv:auipc/rd-imm20` | 12 | `0.1.0`, `0.2.0` |
| `inst/I/ld.yaml` | `riscv:ld/rd-base-imm12` | 0 | `0.1.0`, `0.2.0` |
| `inst/I/sd.yaml` | `riscv:sd/rs-base-imm12` | 0 | `0.1.0`, `0.2.0` |
| `inst/C/c.addi.yaml` | `riscv:c.addi/rd-imm6` | 0 | `0.2.0` only |

`inst/C/c.addi.yaml` is read now: its `not: 0` becomes `excluded: [0]`
(ADR-0009), and its `definedBy: Zca` maps to the plan token `rv64c`. It cannot
join `0.1.0`, because the document's `enabled_extensions` is part of its identity;
§3.1 records the version split. `ld`/`sd` were blocked when this experiment was
first written and are read now that ADR-0008 fixed the operand representation;
§3.1 records how their two `encoding:` blocks are selected.

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
5. turns a variable's `not:` into the slot's `excluded` list (ADR-0009), rejecting
   a list that is not strictly increasing or lies outside the slot's domain;
6. accepts a form when some `definedBy` branch is unconditional or guarded by
   `xlen: 64`, and that branch names the extension the spec expects (`I` or
   `Zca`), then maps that name to the plan token (`rv64i` or `rv64c`) and checks
   the token is in the document it is about to enter.

The result:

| `form_id` | template | placements |
|---|---|---|
| `riscv:add/rd-rs1-rs2` | `33000000` | `[7,5]`, `[15,5]`, `[20,5]` |
| `riscv:addi/rd-rs1-imm12` | `13000000` | `[7,5]`, `[15,5]`, `[20,12]` |
| `riscv:beq/rs1-rs2-imm12` | `63000000` | `[15,5]`, `[20,5]`, `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` |
| `riscv:jal/rd-imm20` | `6f000000` | `[7,5]`, `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]` |
| `riscv:auipc/rd-imm20` | `17000000` | `[7,5]`, `[12,20]` |
| `riscv:ld/rd-base-imm12` | `03300000` | `[7,5]`, `[15,5]`, `[20,12]` |
| `riscv:sd/rs-base-imm12` | `23300000` | `[20,5]`, `[15,5]`, `[31,7]`, `[7,5]` |
| `riscv:c.addi/rd-imm6` | `0100` | `[7,5]` (excl 0), `[12,1]`, `[2,5]` (excl 0) |

Templates are little-endian file order, so `33000000` is the word `0x00000033` and
`0100` is the halfword `0x0001`. The document digests are

| Document | Forms | `enabled_extensions` | Digest |
|---|---|---|---|
| `0.1.0` | the seven base forms | `["rv64i"]` | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` |
| `0.2.0` | the same seven plus `c.addi` | `["rv64i","rv64c"]` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |

### 3.1 Two nodes, two xlen blocks

`ld.yaml` and `sd.yaml` carry one `encoding:` block per xlen. Both RV32 blocks
state `not:` lists on the destination/source register (the Zilsd pair rule: even
registers only); the RV64 blocks do not. The generator selects the block **by
header** (`RV64:`) rather than taking the first one, and fails if the named block
is absent. This is not cosmetic: taking the first block would derive the RV32
placements and import a 32-bit legality rule into a 64-bit table, and the
`not:` check would then reject the form for the wrong reason.

`definedBy` gets the same treatment. `ld`/`sd` state an `anyOf` over (`xlen: 64`,
`I`) and (`xlen: 32`, `Zilsd`); `add` states a bare `extension: {name: I}`. The
extractor returns `[(xlen, name)]`, with `xlen` `None` for the unconditional
branch, so the assertion can say *which* branch admitted the node instead of
matching the first `name:` it sees.

`enabled_extensions` is `["rv64i"]` for `0.1.0`, not `[]`: every node in it says
`definedBy: I`, and `01_contract.md` §4 uses `["rv64i","rv64m","rv64c"]` as its
example spelling. One set covers the whole document and is compared exactly with
the plan's, so a plan that names `[]` or `["rv64i","rv64c"]` against `0.1.0` is
`E-TARGET-001`. That is stricter than "the mnemonic is in the table", and it is
the only legality lever the contract gives the definition.

`c.addi` is `definedBy.extension.name: Zca`, not `C`. `ext/C.yaml` states that
`Zca` is the non-FP subset of `C` and puts `extension: Zca` in C's
`requirements.allOf`, so the plan-level token is `rv64c`; the mapping
`{"I": "rv64i", "Zca": "rv64c"}` is asserted per node, not guessed. Widening
`0.1.0`'s set would change what its version means, so the form goes to `0.2.0`,
whose set is `["rv64i","rv64c"]`. The generator refuses to emit a form whose plan
token is missing from its document's set, so a future addition cannot widen a
table quietly.

## 4. Self-check before writing

The generator re-encodes sixteen vectors from the tables it has just built
(template plus placements) and compares them with the bytes recorded in
`EXP-0009` §6, `EXP-0011` §3 and `EXP-0012` §2:

```text
add a0, a1, a2       33 85 c5 00
addi a0, a1, -2048   13 85 05 80
beq a0, a1, 8        63 04 b5 00
beq a0, a1, -8       e3 0c b5 fe
jal ra, 8            ef 00 80 00
jal ra, -8           ef f0 9f ff
auipc a0, 1          17 15 00 00
auipc a0, 1048575    17 f5 ff ff
ld a0, 8(a1)         03 b5 85 00
ld a0, -2048(a1)     03 b5 05 80
sd a2, 8(a1)         23 b4 c5 00
sd a2, 2047(a1)      a3 bf c5 7e
c.addi a0, 1         05 05
c.addi a0, -32       01 15
c.addi a0, 31        7d 05
c.addi a0, -1        7d 15
```

The `c.addi` zero cases are deliberately absent: they are rejected values, not
vectors, and `N16a`/`N16b` pin them.

This is a transcription check, not the two-source gate: the bytes it compares
against were produced by `llvm-mc` in `EXP-0009`, but the encoder here shares the
placement derivation with the table. §5 is the independent check.

## 5. The fixture gate

Seven positive fixtures reproduce `llvm-mc 23.1.2 -triple=riscv64` bytes through
the Rust materializer:

| Fixture | Bytes | What it adds |
|---|---|---|
| `RV-P1-add-register` | `33 85 c5 00 b3 07 18 01 33 05 b0 00` | three register triples, including `x0` as a source |
| `RV-P2-addi-imm12` | `13 85 15 00 13 85 f5 ff 13 85 f5 7f 13 85 05 80` | both signed endpoints, `-2048` and `2047` |
| `RV-P4-beq-btype` | `63 04 b5 00 13 85 15 00 e3 0c b5 fe` | B-type scatter, forward and backward, through `scale(1)` fixups |
| `RV-P5-jal-jtype` | `ef 00 80 00 13 85 15 00 ef f0 9f ff` | J-type scatter, forward and backward |
| `RV-P7-caddi` | `05 05 13 85 15 00 01 15 7d 05 7d 15` | 2-byte `c.addi` beside 4-byte `addi`, four immediates |
| `RV-P8-auipc-imm20` | `17 15 00 00 17 f5 ff 7f 17 f5 ff ff` | field values `1`, `0x7FFFF`, `0xFFFFF` |
| `RV-P3-ld-sd-base-offset` | `03 b5 85 00 23 b4 c5 00 03 b5 05 80 a3 bf c5 7e` | `ld`/`sd`, contiguous and split immediate, both signed imm12 endpoints |

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

`RV-P7-caddi` is the compressed-versus-standard check: `c.addi a0, 1` is
`05 05` (2 B) and `addi a0, a1, 1` is `13 85 15 00` (4 B). The standard line uses
`a1` as the source because under `-mattr=+c` `addi a0, a0, 1` compresses to
`05 05`; the fixture must not measure the assembler's choice (`EXP-0012` §2.2).
The other three vectors are the signed endpoints of the 6-bit immediate.

Eight negative fixtures pin rejection:

| Fixture | Diagnostic |
|---|---|
| `N01-absent-form` | `E-FORM-001` at `/instructions/0/form_id` |
| `N01c-caddi-against-0.1.0` | `E-FORM-001` at `/instructions/0/form_id`; the same form exists only in `0.2.0` |
| `N02-operand-kind-mismatch` | `E-OPERAND-001` at `/instructions/0/operands/0/kind` |
| `N03-imm12-out-of-range` | `E-RANGE-001` at `/instructions/0/operands/2/payload/value` |
| `N04-branch-out-of-range` | `E-RANGE-002` at `/instructions/0/operands/2/payload/value` |
| `N15-composite-memory-payload` | `E-OPERAND-003` at `/instructions/0/operands/1/payload`, at **read** time (`"phase": "read"`) |
| `N16a-caddi-imm-zero` | `E-RANGE-004` at `/instructions/0/operands/1/payload/value` |
| `N16b-caddi-rd-zero` | `E-RANGE-004` at `/instructions/0/operands/0/payload/reg` |

`N03` is the counterexample for the signed range: `addi a0, a1, 2048` must not
become `addi a0, a1, -2048` by truncation. `N04` is the same failure for the
scattered branch field, where a silent mask would keep the layout intact and only
change the target. `N16a`/`N16b` are the case `range` cannot catch: both zeroes
are inside their declared domains and still encode HINTs. `N01c` shows that the
version split is not a fallback: naming the `0.2.0` form against `0.1.0` does not
become `addi`.

## 6. What the table does not do

- It does not select. Every row is one `form_id` with one template. `addi` never
  becomes `c.addi`, `jal` never becomes `jalr`, and no row is chosen from an
  operand value.
- It does not scale. The `beq`/`jal`/`auipc` slots hold field content
  (`align_bits: 0`); scaling is a fixup field (`transform_shift` 1 or 12).
- It does not lay out. No padding, relaxation or trampoline is in the document.
- It does not cover the blocked row in §7.

## 7. Open, and why it is a format question

- **`RV-P8`'s pair half.** The `auipc` field is in the table; the
  `R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I` relation is not in the UDB encoding
  block. `pcrel_hi20` and `lo12_i` exist as fixup transforms, but which addend
  each half carries, and which of the two halves owns which site, must come from
  a pinned psABI text before a fixture can claim the pair.

`RV-P7` is closed: `c.addi` is generated into `0.2.0`, and the `not: 0` on both
variables became `excluded: [0]` (§3, ADR-0009). `EC-20`'s 3-bit compressed
register class (`c.lw`-style) is still without a v0 form; it needs a narrower
register placement, not `excluded`, and is not a `RV-P7` blocker.

## 8. Reproduction

```powershell
$env:PYTHONIOENCODING="utf-8"
python research\evidence\experiments\EXP-0010\generate_rv64.py
python tools\check_rv64_source.py
python tools\check_definition.py
cd prototype; cargo test --workspace
```

The generator prints the eight forms, the sixteen self-check vectors, both
digests and the `07_definition_format.md` §8.4/§8.5 rows. It refuses to write if
the rendered JSON does not parse back to the document it built, if a placement
does not cover exactly the bits `match` calls variable, or if a form's plan token
is not in its document's extension set.
