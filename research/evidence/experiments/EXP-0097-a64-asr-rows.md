# EXP-0097 -- the three `imm6-asr` rows that no fixture named

- Date: 2026-11-08
- Question: `definitions/aarch64/0.17.0.json` carries 176 forms, and three of
  them were never named by a fixture: `aarch64:sub/w32-w32-w32-imm6-asr`,
  `aarch64:subs/x64-x64-x64-imm6-asr` and `aarch64:subs/w32-w32-w32-imm6-asr`.
  Do those rows encode what the table says, and where is the 32-bit shift
  ceiling?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/aarch64/0.17.0.json`
- Fixture oracle: `fixtures/aarch64/positive/A64-P20-asr-rows.oracle.json`
- Source: `research/evidence/experiments/EXP-0097/`
- Decision: none; the carrier (`form variant`) is already frozen by `EC-01`
  and the rows already exist. This experiment only retires the evidence gap.

## 1. The measurement

`asr-rows.asm` is five instructions: the three uncovered rows at `#3`, then the
two boundary values.

| Source | Bytes | Row | `imm6` |
|---|---|---|---|
| `sub w0, w1, w2, asr #3` | `20 0c 82 4b` | `sub/w32-w32-w32-imm6-asr` | 3 |
| `subs x0, x1, x2, asr #3` | `20 0c 82 eb` | `subs/x64-x64-x64-imm6-asr` | 3 |
| `subs w0, w1, w2, asr #3` | `20 0c 82 6b` | `subs/w32-w32-w32-imm6-asr` | 3 |
| `subs x3, x4, x5, asr #63` | `83 fc 85 eb` | `subs/x64-x64-x64-imm6-asr` | 63 |
| `sub w6, w7, w8, asr #31` | `e6 7c 88 4b` | `sub/w32-w32-w32-imm6-asr` | 31 |

The first two instructions differ only in byte 3 (`4b` vs `eb`): bit 29 (`S`)
and bits 30-31 (`opc = 11` for `subs`) are pinned by the `form_id`. The second
and third differ in byte 3 (`eb` vs `6b`) and byte 0 bit 7 is not free: `sf`
sits in bit 31 of the little-endian word, so the 64-bit row is `eb` and the
32-bit row `6b` with the same `Rd`/`Rn`/`Rm`/`imm6`.

The boundary rows show the field is 6 bits on both widths, and that the 32-bit
row still admits 31: `e6 7c 88 4b` has `imm6 = 31`. The `w32` rows exclude
32-63 (`excluded` in the table), so 31 is the highest legal value and 32 is
`E-RANGE-004`; `N16d` pins that rejection on the `add/w32-w32-w32-imm6-lsl`
sibling. `asr #0` is not rejected here: it is the same bytes as `lsl #0`, but a
plan that names the `-asr` variant has already made the decision, so accepting
it does not add an implicit choice.

## 2. Why this is evidence, not coverage

The three rows were already frozen in `0.17.0`; no definition, schema, error
code or Rust change is involved. A coverage check over the latest table now
asserts that every form is named by at least one positive fixture
(`tools/check_definition.py`), so the gap cannot return unnoticed.

## Reproduce

```
python research/evidence/experiments/EXP-0097/measure.py
```

The script assembles `asr-rows.asm`, asserts the five byte strings above and
the 20-byte total, and writes `bytes.txt` and `show-encoding.txt`.
