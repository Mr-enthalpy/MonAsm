# RV64 fixtures

Vectors: `RV-P1` … `RV-P8` in `docs/fmp-v0/06_validation_matrix.md`. The table is
`definitions/rv64/0.1.0.json` (digest
`sha256:8cd063a50db57179fc9ea027f1dab4de8820a7001242bc4046dc03fef1489ea2`),
generated from the pinned UDB resolved spec by
`research/evidence/experiments/EXP-0010/generate_rv64.py`.

## Positive

| Fixture | Form | Covers |
|---|---|---|
| `RV-P1-add-register` | `riscv:add/rd-rs1-rs2` | `RV-P1` |
| `RV-P2-addi-imm12` | `riscv:addi/rd-rs1-imm12` | `RV-P2`, both signed endpoints |
| `RV-P4-beq-btype` | `riscv:beq/rs1-rs2-imm12` | `RV-P4`, `RV-P6`, forward and backward |
| `RV-P5-jal-jtype` | `riscv:jal/rd-imm20` | `RV-P5`, `RV-P6`, forward and backward |
| `RV-P8-auipc-imm20` | `riscv:auipc/rd-imm20` | `RV-P8` field half only |

Oracle: `llvm-mc 23.1.2 -triple=riscv64 -filetype=obj`, then
`llvm-objcopy -O binary --only-section=.text`. The oracle's `.s` input is not
shipped, but each `oracle.json` lists its lines and pins them by `input_sha256`.
`c.*` is not exercised, so `-mattr=+c` is not needed.

`RV-P4`/`RV-P5` use `pcrel_begin` with `value_transform: scale` and
`transform_shift: 1`, because the slot holds field content (`07_definition_format.md`
§8.3). Both fixups are `resolve_in_place`, so `records` is 0; the bytes, not a
relocation record, are what the fixture checks.

`RV-P8-auipc-imm20` has no fixup. `llvm-mc` accepts only the unsigned literal in
`[0, 1048575]`, so the plan states the third vector as the signed field value `-1`
and the oracle line is `auipc a0, 1048575`; both describe the same 20 bits. The
`%pcrel_hi`/`%pcrel_lo` pair is **not** covered here (see below).

## Negative

| Fixture | Code | What it pins |
|---|---|---|
| `N01-absent-form` | `E-FORM-001` | `riscv:sub/...` is not in the table; the materializer does not synthesize it |
| `N02-operand-kind-mismatch` | `E-OPERAND-001` | an operand's `kind` is not the slot's storage class |
| `N03-imm12-out-of-range` | `E-RANGE-001` | `addi` rejects `2048`, it does not truncate to `-2048` |
| `N04-branch-out-of-range` | `E-RANGE-002` | `beq` rejects a 12-bit field value of `2048` |

## Not covered

- `RV-P3` (`ld`/`sd`) needs an `riscv.mem.base-offset` payload shape, and
  `fmp/0.1` fixes only `{reg}`, `{value}`, `{symbol_id}` and `{}`
  (`01_contract.md` §8.1).
- `RV-P7` (`c.addi`) needs `imm != 0` and `xd != 0`; `fmp-def/0.1` cannot
  express `not: 0`, and encoding either zero silently emits `c.nop` or a HINT
  (ADR-0007 §Decision 5).
- `RV-P8`'s pair half needs the psABI `R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I`
  relation pinned; the encoding blocks do not state it.

Naming any of those forms is `E-FORM-001`.

See `../README.md` for naming and oracle rules.
