# EXP-0017 — AArch64 shifted-register shift: three keywords, one 6-bit amount

- Date: 2026-11-04
- Question: which bits carry the shift kind and the shift amount on
  `add x0, x1, x2, lsl #3`, what values does the amount take, and can a modifier
  entry carry it?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and field ranges come from
  the MRS node and the assembler; what each shift *computes* is not claimed here,
  because it changes no bit.

## 1. The node

`start+width` counts from bit 0 of the 32-bit word.

### `ADD_64_addsub_shift` → the three `aarch64:add/x64-x64-x64-imm6-*` rows

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed (64-bit) |
| `op` | 30+1 | `0` | fixed (`add`) |
| `S` | 29+1 | `0` | fixed (no flags) |
| `op1` | 28+1 | `0` | fixed |
| — | 25+3 | `101` | fixed |
| — | 24+1 | `1` | fixed |
| `shift` | 22+2 | `xx` | **pinned** per row: `0`, `1`, `2` |
| — | 21+1 | `0` | fixed (this is what separates the node from `ADD_64_addsub_ext`) |
| `Rm` | 16+5 | `xxxxx` | slot `src2` |
| `imm6` | 10+6 | `xxxxxx` | slot `imm`, unsigned, field content |
| `Rn` | 5+5 | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

### Not in the table

- `ADD_64_addsub_ext`: same mnemonic, `option` at 13+3 and `imm3` at 10+3, bit 21
  = `1`. Measured: `add x0, x1, x2, uxtx #3` → `0x8b226c20` (`option = 3`),
  `add x0, x1, x2, sxtx #3` → `0x8b22ec20` (`option = 7`), and
  `add x0, x1, w2, uxtw #3` → `0x8b224c20` (`option = 2`) — the last one takes a
  `w` source register, which is a second decision (`EC-11`).
- `ADD_32_addsub_shift` / `SUB_64_addsub_shift`: other nodes (`sf = 0`, `op = 1`).
- `shift = 11`: unallocated in this node. `add x0, x1, x2, ror #3` is rejected.

## 2. The spellings, measured

One instruction per run, `llvm-mc -triple=aarch64 -show-encoding`:

| Source | Bytes | Word | `shift` | `imm6` |
|---|---|---|---|---|
| `add x0, x1, x2, lsl #3` | `20 0c 02 8b` | `0x8b020c20` | `00` | 3 |
| `add x0, x1, x2, lsr #7` | `20 1c 42 8b` | `0x8b421c20` | `01` | 7 |
| `add x0, x1, x2, asr #63` | `20 fc 82 8b` | `0x8b82fc20` | `10` | 63 |
| `add x3, x4, x5, lsl #63` | `83 fc 05 8b` | `0x8b05fc83` | `00` | 63 |
| `add x0, x1, x2, lsl #0` | `20 00 02 8b` | `0x8b020020` | `00` | 0 |
| `add x0, x1, x2, lsr #0` | `20 00 42 8b` | `0x8b420020` | `01` | 0 |
| `add x0, x1, x2` | `20 00 02 8b` | `0x8b020020` | `00` | 0 |

Three facts fall out.

**The kind is two bits and there are three keywords.** The first three words have
the same `Rm`, `Rn`, `Rd` and differ only in bits 23–22 and bits 15–10, so the
field split is visible in one row of the table. `ror` is not one of them: the
assembler rejects it, and `shift = 11` is not an `add` instruction.

**The amount is six bits and both ends are legal.** `lsl #0` and `lsl #63` both
assemble, and `lsl #64` does not: the assembler's message for the out-of-range
attempt names the extend spellings and `[0, 4]`, because it tries the
extended-register parse before giving up (`EXP-0017` reads no semantics from that
message; the MRS field is what fixes `0…63`).

**The `lsl #0` spelling is the same instruction as no modifier at all.** The last
two rows of the table are the same bytes, and `llvm-mc -show-encoding` prints the
`lsl #0` line back as `add x0, x1, x2`. So the "no shift stated" row (`-lsl0`) and
the "shift stated as zero" row are one word with two spellings — which is why
`0.6.0` keeps both and documents the overlap (ADR-0015 decision 5).

## 3. The vector

Input (LF, trailing newline, two leading spaces; 153 bytes,
`sha256:3d226fa68fec0ebfba561293b6df5963c4a7a25b8104f063e05927edca5bfee1`):

```text
  add x0, x1, x2, lsl #3
  add x0, x1, x2, lsr #7
  add x0, x1, x2, asr #63
  add x3, x4, x5, lsl #63
  add x0, x1, x2, lsl #0
  add x0, x1, x2, lsr #0
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is a register or an
immediate, so no linker is involved. `.text` is 24 bytes.

| Offset | Bytes | Word | `llvm-objdump` | Plan |
|---|---|---|---|---|
| 0 | `20 0c 02 8b` | `0x8b020c20` | `add x0, x1, x2, lsl #3` | `-imm6-lsl`, `imm6 = 3` |
| 4 | `20 1c 42 8b` | `0x8b421c20` | `add x0, x1, x2, lsr #7` | `-imm6-lsr`, `imm6 = 7` |
| 8 | `20 fc 82 8b` | `0x8b82fc20` | `add x0, x1, x2, asr #63` | `-imm6-asr`, `imm6 = 63` |
| 12 | `83 fc 05 8b` | `0x8b05fc83` | `add x3, x4, x5, lsl #63` | `-imm6-lsl`, `imm6 = 63` |
| 16 | `20 00 02 8b` | `0x8b020020` | `add x0, x1, x2` | `-imm6-lsl`, `imm6 = 0` |
| 20 | `20 00 42 8b` | `0x8b420020` | `add x0, x1, x2, lsr #0` | `-imm6-lsr`, `imm6 = 0` |

Output: 24 bytes,
`sha256:b20a9e68f624be216c293d3e8ab9d518d9e3c6dd59f89681c22704a8ec20a82d`,
`bytes_hex` `200c028b201c428b20fc828b83fc058b2000028b2000428b`.

The vector pins each decision independently:

- all three `shift` values, with the first three rows sharing `Rd`/`Rn`/`Rm` so a
  kind slip moves bits nothing else moves;
- `imm6` at both ends (`0` and `63`), with `63` used twice: as `asr #63` and as
  `lsl #63` on a different register triple, so a `shift`/`imm6` mix-up is visible
  twice;
- the `0` end on a kind other than LSL (`lsr #0`), so a range that started at `1`
  would fail rather than pass by accident;
- the `lsl #0` overlap with `-lsl0`, measured rather than argued.

## 4. What this fixes, and what it does not

Fixes:

- the three templates (`0x8b000000`, `0x8b004000`, `0x8b008000` base words) and
  one slot placement (`imm6` at `[10,6]`), derived from the MRS fields by the
  generator;
- the rule: the keyword is the `form_id`, the amount is field content in `0…63`
  with `align_bits = 0`, and no modifier carries a number into bits;
- the negative evidence: amount `64` is `E-RANGE-001` (`N03-imm6`), a modifier
  that states `lsl #3` on `-lsl0` is `E-OPERAND-003` (`N19`), and the extend
  family has no row (`N01e`, `E-FORM-001`).

Does not fix:

- **the extend family.** `option`/`imm3` on the same mnemonic, with a `w` source
  for some options; its own node and its own decision.
- **`sub` and the 32-bit rows.** Other nodes.
- **a symbol in `imm6`.** None of the three rows has a fixup.
- **what the shift computes.** AArch64's shift-by-0 reading and the operand-width
  rules are semantics, and this slice fixes bytes only.

## 5. Result

The rows ship in `definitions/aarch64/0.6.0.json`, which repeats the fifteen
earlier forms and adds three:

```text
definition  definitions/aarch64/0.6.0.json
namespace   monasm.isa.aarch64
version     0.6.0
forms       18
digest      sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 24 bytes above with no fixup records, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P8-shift-modifier` | six instructions, three forms | 24 bytes, `sha256:b20a9e68…` |
| `N03-imm6-out-of-range` | `imm6 = 64` on `-imm6-lsl` | `E-RANGE-001`, `min 0`, `max 63` |
| `N19-modifier-is-not-a-carrier` | `{"name": "lsl", "value": 3}` on `-lsl0` | `E-OPERAND-003`, `reason: modifier \`lsl\` is not permitted` |
| `N01e-absent-extend-form` | `aarch64:add/x64-x64-w64-uxtw-imm3` | `E-FORM-001` |
