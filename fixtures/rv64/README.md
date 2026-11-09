# RV64 fixtures

Vectors: `RV-P1` … `RV-P12` in `docs/fmp-v0/06_validation_matrix.md`. Every
document is pinned, because the extension set and the rows are part of its
identity (`07_definition_format.md` §2):

| Document | Forms | Digest |
|---|---|---|
| `definitions/rv64/0.1.0.json` | seven base-`I` forms | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` |
| `definitions/rv64/0.2.0.json` | the same seven plus `riscv:c.addi/rd-imm6` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |
| `definitions/rv64/0.3.0.json` | plus `riscv:lui/rd-imm20` | `sha256:484eae4ba4c80c1ff4d91bc11a6fd9bd36bdc511a8271815d76c0883869ad2af` |
| `definitions/rv64/0.4.0.json` | plus `riscv:jalr/rd-rs1-imm12` | `sha256:e00dee01004ec9d927ac4e5494e8e6dabfcbb4ff0e123980190c9871624afa76` |
| `definitions/rv64/0.5.0.json` | plus the five B-type mnemonics | `sha256:571ab1ed93f4464d5ec8981df02dd0444005ababdaaf1e175d0ec489bb33a776` |
| `definitions/rv64/0.6.0.json` | plus the nine load/store widths | `sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585` |

`0.1.0`/`0.2.0` are generated from the pinned UDB resolved spec by
`research/evidence/experiments/EXP-0010/generate_rv64.py`; `0.5.0` and `0.6.0`
are generated from their predecessors by `EXP-0105/generate_0500.py` and
`EXP-0116/generate_0600.py`, which assert the source forms are reproduced before
they append.

## Positive

| Fixture | Form | Covers |
|---|---|---|
| `RV-P1-add-register` | `riscv:add/rd-rs1-rs2` | `RV-P1` |
| `RV-P2-addi-imm12` | `riscv:addi/rd-rs1-imm12` | `RV-P2`, both signed endpoints |
| `RV-P4-beq-btype` | `riscv:beq/rs1-rs2-imm12` | `RV-P4`, `RV-P6`, forward and backward |
| `RV-P5-jal-jtype` | `riscv:jal/rd-imm20` | `RV-P5`, `RV-P6`, forward and backward |
| `RV-P7-caddi` | `riscv:c.addi/rd-imm6` | `RV-P7`, four immediates; the 4-byte `addi` sits beside the 2-byte form |
| `RV-P8-auipc-imm20` | `riscv:auipc/rd-imm20` | `RV-P8` field half only |
| `RV-P8-pcrel-pair` | `riscv:auipc/rd-imm20`, `riscv:addi/rd-rs1-imm12`, `riscv:sd/rs-base-imm12` | `RV-P8` pair half: one `hi`, two `lo`, three records, unlinked |
| `RV-P8-pcrel-pair-resolved` | `riscv:auipc/rd-imm20`, `riscv:addi/rd-rs1-imm12` | `RV-P8` pair arithmetic against a linked binary |
| `RV-P3-ld-sd-base-offset` | `riscv:ld/rd-base-imm12`, `riscv:sd/rs-base-imm12` | `RV-P3`, four instructions, signed imm12 endpoints |
| `RV-P12-load-store-widths` | `riscv:lb/lh/lw/lbu/lhu/lwu` (`rd-base-imm12`), `riscv:sb/sh/sw` (`rs-base-imm12`) | `RV-P12`, nine rows at `8(a1)` plus the signed-12 ends (`-2048`, `2047`) |

Oracle: `llvm-mc 23.1.2 -triple=riscv64 -filetype=obj`, then
`llvm-objcopy -O binary --only-section=.text`. The oracle's `.s` inputs live
under `research/evidence/experiments/` and are pinned by `input_sha256` in each
`oracle.json`; `python tools/oracle/rerun.py` re-derives all eighteen RV64
positives.
`-mattr=+c` is passed for `RV-P7` only; the base-`I` fixtures are assembled
without it so `llvm-mc` cannot auto-compress an `addi` on them (`EXP-0012` §2.2).

`RV-P3` splits the address into `base` + `disp` operands rather than one memory
payload (`ADR-0008`, `OD-13`), because the base is a 5-bit register field and the
offset a 12-bit signed field; a fixup covering one does not cover the other.
RV64 does not scale the immediate, so `disp` is the byte displacement and the
slot holds it unchanged. The store's data operand is `src` (not `src2`): there is
one source register in `sd`. `04_errors.md` `E-OPERAND-003` is exercised by `N15`
from the other side — a composite `{"mem": …}` payload is rejected at read time.

`RV-P4`/`RV-P5` use `pcrel_begin` with `value_transform: scale` and
`transform_shift: 1`, because the slot holds field content (`07_definition_format.md`
§8.3). Both fixups are `resolve_in_place`, so `records` is 0; the bytes, not a
relocation record, are what the fixture checks.

`RV-P8-auipc-imm20` has no fixup. `llvm-mc` accepts only the unsigned literal in
`[0, 1048575]`, so the plan states the third vector as the signed field value `-1`
and the oracle line is `auipc a0, 1048575`; both describe the same 20 bits.

`RV-P8-pcrel-pair` is the pair half (`ADR-0010`, `OD-15`). One `auipc a0,
%pcrel_hi(blob)` and two low halves — `addi a0, a0, %pcrel_lo(.L0)` and
`sd a1, %pcrel_lo(.L0)(a0)` — point at the same external symbol, and the three
fixups form `pair_group: P8`: `F0001` is the `hi` with `pcrel_begin` +
`pcrel_hi20`, and `F0002`/`F0003` are `lo` members with `pcrel_hi` +
`pcrel_lo12`. That is the psABI's 1:N shape, and it is the fixture for ADR-0010
decision 3: the S-type low half keeps the same transform and differs only in its
`field_descriptor` (`[31:25]` then `[11:7]`, versus `[31:20]` for the I-type).
All three fixups are `emit_relocation`, so Level 0 zeroes the immediate fields
and the bytes are `17 05 00 00 13 05 05 00 23 30 b5 00`; the second source is
`llvm-readobj -r`, which prints `R_RISCV_PCREL_HI20 blob 0x0`,
`R_RISCV_PCREL_LO12_I .L0 0x4` and `R_RISCV_PCREL_LO12_S .L0 0x8` on the same
object. The label `.L0` sits on the `auipc`, which is exactly the "low half names
a label in the same section" relation `pcrel_hi` expresses.

`RV-P8-pcrel-pair-resolved` measures the arithmetic the first fixture cannot:
both fixups are `resolve_in_place`, the `auipc` sits at 4 and `blob` at 0x1000,
so `P_hi` is not page-aligned. The linked words are `17 15 00 00`
(`0x00001517`) and `13 05 c5 ff` (`0xFFC50513`), i.e. high half
`(0x1000 - 4 + 0x800) >> 12 = 1` and low half `(0x1000 - 4) & 0xFFF = 0xFFC`.
Three plausible alternatives each produce a different word — `lo12_i` 0x000,
`pcrel_begin` on the `lo` 0xFF8, no `+0x800` 0 — so the fixture separates the
rule from its neighbours instead of merely matching a number.

`RV-P7-caddi` pins the compressed-versus-standard choice: the first instruction
is `riscv:c.addi/rd-imm6` (`05 05`, 2 B) and the second is
`riscv:addi/rd-rs1-imm12` on the same immediate (`13 85 15 00`, 4 B). The
standard-form line uses `a1` as the source on purpose: with `-mattr=+c`,
`addi a0, a0, 1` would assemble to `05 05`, measuring the assembler's choice
rather than the named form. The `imm = 0` and `dest = 0` cases are rejected, not
encoded: both are inside the declared ranges and produce reserved HINTs
(`EXP-0012` §2.1, ADR-0009).

## Negative

| Fixture | Code | What it pins |
|---|---|---|
| `N01-absent-form` | `E-FORM-001` | `riscv:sub/...` is not in the table; the materializer does not synthesize it |
| `N01c-caddi-against-0.1.0` | `E-FORM-001` | `riscv:c.addi/rd-imm6` is not in `0.1.0`; the lookup is per version, never repaired to `addi` |
| `N02-operand-kind-mismatch` | `E-OPERAND-001` | an operand's `kind` is not the slot's storage class |
| `N03-imm12-out-of-range` | `E-RANGE-001` | `addi` rejects `2048`, it does not truncate to `-2048` |
| `N01fd-absent-fence-form` | `E-FORM-001` | `riscv:fence/fm-pred-succ-imm12` has no row in any version (`EC-24`); the materializer does not synthesize it |
| `N01fe-load-store-row-on-0.5.0` | `E-FORM-001` | `riscv:lw/rd-base-imm12` is not in `0.5.0`; the lookup is per version and never falls back to `ld` |
| `N03a0-sw-imm12-past-signed-12` | `E-RANGE-001` | `sw` rejects `2048`, the signed 12-bit end, even though the field is scattered over 7+5 bits |
| `N04-branch-out-of-range` | `E-RANGE-002` | `beq` rejects a 12-bit field value of `2048` |
| `N15-composite-memory-payload` | `E-OPERAND-003` | a `{"mem": {base, disp}}` payload is not one of the four `fmp/0.1` shapes, so the reader rejects it before the definition is looked up |
| `N16a-caddi-imm-zero` | `E-RANGE-004` | `c.addi` with `imm = 0` is inside `[-32, 31]` but excluded: the bytes would mean a HINT |
| `N16b-caddi-rd-zero` | `E-RANGE-004` | `c.addi` with `dest = 0` is inside `0..31` but excluded: the bytes would mean `c.nop` |
| `N17a-lo12-addend-nonzero` | `E-FIXUP-009` | a `pcrel_lo12` low half with `addend: 4`: the `hi` already folded the addend into the shared displacement, so a second one would be added twice |
| `N17b-pcrel-hi-without-lo-role` | `E-FIXUP-007` | `pcrel_hi` on a fixup with no `pair_role: lo`: there is no `P` to measure from, and no fallback to `pcrel_begin` |
| `N17c-lo-in-other-section` | `E-FIXUP-007` | a `pcrel_hi` low half in `.text2` whose `hi` is in `.text`: `P_hi` would be an offset into a different origin, so the subtraction would silently mix two sections |

## Not covered

- The 1:N half is proven only at the record level: `RV-P8-pcrel-pair` stops at
  `emit_relocation`, so a group with two low halves is not compared against a
  linked binary. The single-`lo` arithmetic is covered by
  `RV-P8-pcrel-pair-resolved`.

See `../README.md` for naming and oracle rules.
