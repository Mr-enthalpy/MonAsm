# RV64 fixtures

Vectors: `RV-P1` … `RV-P8` in `docs/fmp-v0/06_validation_matrix.md`. Two
documents are pinned, because the extension set is part of a document's identity
(`07_definition_format.md` §2):

| Document | Forms | Digest |
|---|---|---|
| `definitions/rv64/0.1.0.json` | seven base-`I` forms | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` |
| `definitions/rv64/0.2.0.json` | the same seven plus `riscv:c.addi/rd-imm6` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |

Both are generated from the pinned UDB resolved spec by
`research/evidence/experiments/EXP-0010/generate_rv64.py`.

## Positive

| Fixture | Form | Covers |
|---|---|---|
| `RV-P1-add-register` | `riscv:add/rd-rs1-rs2` | `RV-P1` |
| `RV-P2-addi-imm12` | `riscv:addi/rd-rs1-imm12` | `RV-P2`, both signed endpoints |
| `RV-P4-beq-btype` | `riscv:beq/rs1-rs2-imm12` | `RV-P4`, `RV-P6`, forward and backward |
| `RV-P5-jal-jtype` | `riscv:jal/rd-imm20` | `RV-P5`, `RV-P6`, forward and backward |
| `RV-P7-caddi` | `riscv:c.addi/rd-imm6` | `RV-P7`, four immediates; the 4-byte `addi` sits beside the 2-byte form |
| `RV-P8-auipc-imm20` | `riscv:auipc/rd-imm20` | `RV-P8` field half only |
| `RV-P3-ld-sd-base-offset` | `riscv:ld/rd-base-imm12`, `riscv:sd/rs-base-imm12` | `RV-P3`, four instructions, signed imm12 endpoints |

Oracle: `llvm-mc 23.1.2 -triple=riscv64 -filetype=obj`, then
`llvm-objcopy -O binary --only-section=.text`. The oracle's `.s` input is not
shipped, but each `oracle.json` lists its lines and pins them by `input_sha256`.
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
and the oracle line is `auipc a0, 1048575`; both describe the same 20 bits. The
`%pcrel_hi`/`%pcrel_lo` pair is **not** covered here (see below).

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
| `N04-branch-out-of-range` | `E-RANGE-002` | `beq` rejects a 12-bit field value of `2048` |
| `N15-composite-memory-payload` | `E-OPERAND-003` | a `{"mem": {base, disp}}` payload is not one of the four `fmp/0.1` shapes, so the reader rejects it before the definition is looked up |
| `N16a-caddi-imm-zero` | `E-RANGE-004` | `c.addi` with `imm = 0` is inside `[-32, 31]` but excluded: the bytes would mean a HINT |
| `N16b-caddi-rd-zero` | `E-RANGE-004` | `c.addi` with `dest = 0` is inside `0..31` but excluded: the bytes would mean `c.nop` |

## Not covered

- `RV-P8`'s pair half needs the psABI `R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I`
  relation pinned; the encoding blocks do not state it.

Naming that pair is `E-FORM-001` until it is pinned.

See `../README.md` for naming and oracle rules.
