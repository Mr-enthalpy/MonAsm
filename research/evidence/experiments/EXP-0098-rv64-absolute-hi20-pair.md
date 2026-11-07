# EXP-0098 -- the absolute `lui` + `addi` split (`%hi` / `%lo`)

- Date: 2026-11-08
- Question: how is an absolute RV64 address built from `lui` and `addi`, what do
  the object records and the resolved bytes look like, and which
  `pc_reference_rule` does the high half need?
- Toolchain: `llvm-mc`/`llvm-readobj`/`llvm-objcopy` 23.1.2, `ld.lld` 23.1.2
- Definition: `definitions/rv64/0.3.0.json` (the `0.2.0` table plus
  `riscv:lui/rd-imm20`)
- Fixture oracle: `fixtures/rv64/positive/RV-P9-lui-imm20.oracle.json`,
  `RV-P9-lui-pair.oracle.json` and `RV-P9-lui-pair-resolved.oracle.json`
- Source: `research/evidence/experiments/EXP-0098/`
- Decision: `ADR-0098`

## 1. The measurement

`literal.asm` is `lui a0, <imm>` at three field values:

| Source | Bytes | `imm20` |
|---|---|---|
| `lui a0, 0` | `37 05 00 00` | 0 |
| `lui a0, 1` | `37 15 00 00` | 1 |
| `lui a0, 0xfffff` | `37 f5 ff ff` | 1048575 |

`imm` sits at 31-12, `rd` at 11-7 and the opcode is `0110111` (UDB
`inst/I/lui.yaml`). `llvm-mc` rejects both `-1` and `0x100000` ("integer in the
range [0, 1048575]"), so the plan's slot is `signed: false`: the encoded field
is the unsigned 20-bit value, and the sign extension happens when the
instruction executes.

`pair.asm` is the pair against an external symbol:

```text
lui  a0, %hi(blob)
addi a0, a0, %lo(blob)
```

The object bytes are `37 05 00 00 13 05 05 00` (both fields zero) and
`llvm-readobj --relocations` reports:

```text
0x0 R_RISCV_HI20   blob 0x0
0x4 R_RISCV_LO12_I blob 0x0
```

`pair-resolved.asm` puts `.text` at `0x1000` and `L1` at offset `0x234`, so the
symbol address is `0x1234`:

```text
lui  a0, %hi(L1)
addi a0, a0, %lo(L1)
```

The linked image is `37 15 00 00 13 05 45 23`: `lui a0, 1` and
`addi a0, a0, 0x234`. Hand derivation agrees: `(0x1234 + 0x800) >> 12 = 1` and
`0x1234 & 0xFFF = 0x234`.

## 2. What the bytes pin

The high half is `(S + A + 0x800) >> 12` with no `P`; that is why the plan writes
`pc_reference_rule = none`. The same bytes would not be produced by the
neighbouring transforms:

- `pcrel_hi20` with `P = 0x1000` gives `(0x1234 - 0x1000 + 0x800) >> 12 = 0`, a
  different high word; the resolved fixture therefore tells the two rules apart.
- `identity` would write `0x1234` into the 20-bit field (a different high word).
- `lo12_i` masks the same value to `0x234`, which is the low half's field, not
  the high half's.

The low half masks the absolute `S + A` (`lo12_i`), not a displaced value, so a
`hi20` fixup with any PC rule is `E-FIXUP-001`. `N07f` pins that rejection.

The `0.3.0` row is `template 37000000`, `dest` at 7+5, `target` at 12+20,
`range {signed: false, bits: 20}`. `emit_relocation` zeroes the field and emits
the record; `resolve_in_place` needs the section `base_address`, because a
`none` rule cannot cancel the site (`03_fixup_model.md` §4).

## 3. Scope note

The measured operand domain is `[0, 1048575]`, so the v0 slice expresses an
absolute address whose `(S + A + 0x800) >> 12` lies in that interval. An address
in the upper 2 GiB of the 32-bit space would need the field's sign bit, and the
unsigned slot does not carry it; such a plan is `E-FIXUP-003` rather than a
silently truncated high half (`inference`: this follows from the measured
operand domain and the `signed: false` range, not from a vector).

## Reproduce

```text
python research/evidence/experiments/EXP-0098/measure.py
```

The script assembles the three inputs, asserts the byte strings, the two
relocation names and the 568-byte linked image, and writes `bytes.txt`,
`relocations.txt` and `show-encoding.txt`.
