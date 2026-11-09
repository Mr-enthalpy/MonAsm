# EXP-0105 -- the RV64 B-type mnemonic family

- Date: 2026-11-09
- Question: do the five remaining conditional-branch mnemonics share `beq`'s
  field geometry, scatter and fixup rule, so that only `funct3` changes?
- Toolchain: `llvm-mc`/`llvm-objcopy`/`llvm-objdump` 23.1.2
- Definition: `definitions/rv64/0.4.0.json`; the generated `0.5.0` is the
  product of this experiment
- Fixture oracle: `fixtures/rv64/positive/RV-P11-btype-family.oracle.json`
- Source: `research/evidence/experiments/EXP-0105/RV-P11-btype-family.s`
- Decision: `ADR-0104`

## 1. The source nodes

The pinned UDB resolved drop carries one node per mnemonic
(`research/external/rv64-udb/gen/resolved_spec/_/inst/I/`). The five nodes agree
with `beq.yaml` on everything except the three `funct3` bits:

| Node | `encoding.match` | `location` | `left_shift` | `definedBy` |
|---|---|---|---|---|
| `bne.yaml` | `-----------------001-----1100011` | `31\|7\|30-25\|11-8` | 1 | `I` |
| `blt.yaml` | `-----------------100-----1100011` | `31\|7\|30-25\|11-8` | 1 | `I` |
| `bge.yaml` | `-----------------101-----1100011` | `31\|7\|30-25\|11-8` | 1 | `I` |
| `bltu.yaml` | `-----------------110-----1100011` | `31\|7\|30-25\|11-8` | 1 | `I` |
| `bgeu.yaml` | `-----------------111-----1100011` | `31\|7\|30-25\|11-8` | 1 | `I` |

`funct3` occupies bits 12-14, which are the high nibble of template byte 1, so
the five templates are `63 10 00 00`, `63 40 00 00`, `63 50 00 00`,
`63 60 00 00` and `63 70 00 00` (little-endian files). The source check is in
`generate_0500.py`, which refuses to write the table unless each node carries
the match/target/`left_shift`/extension identities above.

## 2. The measurement

`RV-P11-btype-family.s` is the five mnemonics with two labels: the first three
branch forward to a label eight bytes ahead, the last two branch back to a label
four bytes behind. `llvm-mc` + `llvm-objcopy` produce 20 bytes:

| Source | Bytes |
|---|---|
| `bne a0, a1, L1` | `63 14 b5 00` |
| `blt a0, a1, L2` | `63 44 b5 00` |
| `bge a0, a1, L3` | `63 54 b5 00` |
| `bltu a0, a1, L1` | `e3 6e b5 fe` |
| `bgeu a0, a1, L2` | `e3 7e b5 fe` |

The last two carry the negative field `-4`: `imm[12]` is set and the scatter is
the same four placements. This is the sign half `RV-P4` already covers for
`beq`; here it proves the new mnemonics share it.

## 3. The fixture

The plan is the same 20 bytes through five `scale` fixups with
`transform_shift: 1`, `pcrel_begin`, `resolve_in_place` and
`range_constraint` signed 12 / `align_bits 1`. The oracle input hash is
`32ea6fb614ee855a4180a646ed6d06139cee9bc2c6bdbad98aa5c126aa12a505`; the output
hash is
`1ff019414f397e09250a81f5650c0c2d5f5b35fe128cabc600c5263085dfb581`, size 20,
0 relocation records.

`0.5.0` has 15 forms and digest
`sha256:571ab1ed93f4464d5ec8981df02dd0444005ababdaaf1e175d0ec489bb33a776`.
It repeats the ten `0.4.0` forms unchanged.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01en` | names `riscv:bne/rs1-rs2-imm12` against `0.4.0` | `E-FORM-001` |
| `N02cw` | passes `riscv.imm`/`xreg` as the first source | `E-OPERAND-001` (kind) |
| `N04h` | `bltu` target value `2048` | `E-RANGE-002` (`max 2047`) |

`N04h` is the field boundary: the value is one past the signed 12-bit field
content, and the answer is a rejection, not a wrap to `0`.

## 5. What the slice defers

- `c.j`/`c.jalr` and the compressed branch family (`EC-23`).
- `beqz`/`bnez` and the other pseudoinstructions the source nodes list; they
  are separate mnemonics, not this template.
- The B-type/J-type associated-reference pairing; `RV-P8`/`RV-P10` own that
  axis.
