# EXP-0028 — the 64-bit move-wide mnemonics: `movk` and `movn`

- Date: 2026-11-05
- Question: what do `movk` and `movn` change against the existing `movz` rows —
  which fields the mnemonics fix, whether the operand is the raw `imm16` field or
  its complement, and what does the assembler refuse?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The field layout comes from the MRS
  nodes and the accepted words from the assembler; the `movn` complement is read
  off the disassembler's output and the encoded field, not from a prose manual.

## 1. The nodes

`MOVK_64_movewide` and `MOVN_64_movewide` are `MOVZ_64_movewide` with the two
`opc` bits fixed differently. Every other field position, the lane selector
`hw`, the 16-bit field and the destination are unchanged. `start+width` counts
from bit 0 of the 32-bit word:

### `MOVK_64_movewide` → `aarch64:movk/x64-imm16-lsl*`

| Field | start+width | Value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed — 64-bit |
| `opc` | 29+2 | `11` | fixed — `movk` |
| — | 26+3 | `100` | fixed |
| — | 23+3 | `101` | fixed |
| `hw` | 21+2 | `xx` | pinned per row (`00`/`01`/`10`/`11`) |
| `imm16` | 5+16 | `xxxxxxxxxxxxxxxx` | slot `imm`, unsigned |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

`MOVN_64_movewide` is the same table with `opc = 00`. With `hw = 00` and all
slots zeroed the templates are `0xf2800000` (`movk`) and `0x92800000` (`movn`),
against `0xd2800000` for `movz`.

The only difference between the three mnemonics is those two bits. It is an
*encoding* decision, so it is the `form_id`'s and never an operand: the node is
chosen by the mnemonic, which the plan already names in `form_id` (`INV-02`,
`EC-16`, ADR-0026).

## 2. The fields, measured

One instruction per run at offset 0, `llvm-mc -triple=aarch64 -filetype=obj`,
then `llvm-objcopy -O binary --only-section=.text`:

| Source | Word | `opc` | `hw` | Reading |
|---|---|---|---|---|
| `movk x0, #0x1234` | `0xf2824680` | `11` | 0 | lane 0 |
| `movk x0, #0x1234, lsl #16` | `0xf2a24680` | `11` | 1 | only bits 22–21 moved |
| `movk x0, #0x1234, lsl #32` | `0xf2c24680` | `11` | 2 | |
| `movk x0, #0x1234, lsl #48` | `0xf2e24680` | `11` | 3 | |
| `movn x0, #0x1234` | `0x92824680` | `00` | 0 | lane 0, raw field |
| `movn x0, #0x1234, lsl #16` | `0x92a24680` | `00` | 1 | |
| `movn x0, #0x1234, lsl #32` | `0x92c24680` | `00` | 2 | |
| `movn x0, #0x1234, lsl #48` | `0x92e24680` | `00` | 3 | |

The `movk` set is the `movz` set (`0xd2824680` … `0xd2e24680`) with the top
nibble `d` replaced by `f`; the `movn` set is the same with `9`. The low 28 bits
are identical across all twelve measurements, so `imm16 = 0x1234` sits at bits
20–5 in every row and only `opc` and `hw` differ. `0xf2824680` and `0xf2a24680`
differ by `0x00200000`, which is `hw = 01` at bits 22–21; no other bit moved.

**`movn` stores the raw field, not its complement.** `movn x0, #0x1234` is
`0x92824680` — `imm16 = 0x1234` at bits 20–5 — and `llvm-objdump` prints it as
`mov x0, #-0x1235`, because the instruction writes the complement of the lane.
If the plan carried the complement, the same request would need a different
number from the assembler's and the field would no longer be the operand. The
`movz` row stores `imm16` directly (`EXP-0016` §2); `movk` does the same and
`movn` keeps the same meaning (`ADR-0026` decision 4).

**Register 31 is a plain `reg_number`.** There is no `sp`/`zr` distinction in
this node: `Rd` is five bits and 31 is `xzr` as a destination.

| Source | Word | Field | Meaning |
|---|---|---|---|
| `movk x31, #0` | `0xf280001f` | `Rd = 31` | `xzr` |
| `movn x31, #0xffff` | `0x929fffff` | `Rd = 31`, `imm16 = 0xffff` | `xzr` |
| `movk x8, #0xffff, lsl #48` | `0xf2ffffe8` | `hw = 3`, top `imm16` | both ends at once |
| `movn x8, #0, lsl #48` | `0x92e00008` | `hw = 3`, `imm16 = 0` | `movn` keeps its mnemonic |

The last row is the one measured `movn` word that `llvm-objdump` prints as
`movn` rather than `mov`: with `imm16 = 0` at the top lane the built value is
`0xffff000000000000`, and `mov x8, #-0x1000000000000` assembles to the `movz`
word `0xd2ffffe8`, not to `0x92e00008`, so the alias would not round-trip.

**The `mov` alias is the value-driven selection this slice excludes.**
`mov x0, #0x1234` assembles to `0xd2824680` — a `movz` lane 0 — and
`mov x0, #-1` to `0x92800000` — a `movn` lane 0. The same mnemonic, two nodes
and two lanes, chosen from the literal's value. A single `mov` row would have to
pick the node and lane at materialization time, which is `INV-02`; the alias is
therefore absent and no `mov` row exists in any document (`EC-16`, ADR-0026
decision 5).

## 3. What the assembler rejects

One instruction per run, same command:

| Source | Diagnostic |
|---|---|
| `movk x0, #0x1234, lsl #8` | `expected 'lsl' with optional integer 0, 16, 32 or 48` |
| `movk x0, #0x1234, lsl #4` | `expected 'lsl' with optional integer 0, 16, 32 or 48` |
| `movk x0, #0x10000` | `immediate must be an integer in range [0, 65535]` |
| `movn x0, #-1` | `immediate must be an integer in range [0, 65535]` |

The lane set is exactly `0`, `16`, `32`, `48`; `#8` is not a smaller legal lane
and `#4` is not a byte amount. The immediate is the unsigned field, so a
negative literal is out of range rather than a request for the complement — the
complement is `movn`'s operation, not an operand spelling.

For comparison, the 32-bit halves are different nodes: `movk w0, #0x1234,
lsl #16` is `0x72a24680` and `movn w0, #0x1234, lsl #16` is `0x12a24680`. They
share the layout with `sf = 0` and are absent from every document, exactly as the
`w` arithmetic rows were before `0.10.0` (`EC-11`).

## 4. The vector

Input (LF, trailing newline; 268 bytes,
`sha256:7df95f1854ea40d4bab6bdba56adf1d42d4a252e881eb60cb3240868348b794a`):

```text
movk x0, #0x1234
movk x1, #0x00ff, lsl #16
movk x2, #0xbeef, lsl #32
movk x3, #0x0001, lsl #48
movn x4, #0x1234
movn x5, #0x00ff, lsl #16
movn x6, #0xbeef, lsl #32
movn x7, #0x0001, lsl #48
movk x31, #0
movn x31, #0xffff
movk x8, #0xffff, lsl #48
movn x8, #0, lsl #48
```

The first eight lines visit each new row once in lane order, with distinct
`imm16` values (`0x1234`, `0x00ff`, `0xbeef`, `0x0001`) and destinations 0–7, so
a placement slip or a swapped lane shows up in the word. The last four pin the
extremes: `Rd = 31`, `imm16 = 0`, `imm16 = 0xffff` at the top lane, and `movn` at
the top lane with `imm16 = 0`.

`llvm-readobj -r` prints an empty relocation list and the source names no
symbols, so no linker is involved.

| Offset | Bytes | Word | `llvm-objdump` |
|---|---|---|---|
| 0 | `80 46 82 f2` | `0xf2824680` | `movk x0, #0x1234` |
| 4 | `e1 1f a0 f2` | `0xf2a01fe1` | `movk x1, #0xff, lsl #16` |
| 8 | `e2 dd d7 f2` | `0xf2d7dde2` | `movk x2, #0xbeef, lsl #32` |
| 12 | `23 00 e0 f2` | `0xf2e00023` | `movk x3, #0x1, lsl #48` |
| 16 | `84 46 82 92` | `0x92824684` | `mov x4, #-0x1235` |
| 20 | `e5 1f a0 92` | `0x92a01fe5` | `mov x5, #-0xff0001` |
| 24 | `e6 dd d7 92` | `0x92d7dde6` | `mov x6, #-0xbeef00000001` |
| 28 | `27 00 e0 92` | `0x92e00027` | `mov x7, #-0x1000000000001` |
| 32 | `1f 00 80 f2` | `0xf280001f` | `movk xzr, #0x0` |
| 36 | `ff ff 9f 92` | `0x929fffff` | `mov xzr, #-0x10000` |
| 40 | `e8 ff ff f2` | `0xf2ffffe8` | `movk x8, #0xffff, lsl #48` |
| 44 | `08 00 e0 92` | `0x92e00008` | `movn x8, #0x0, lsl #48` |

Output: 48 bytes,
`sha256:ec16d04e59c5133b303bedf0d70a5558967c5575d9985e87eb56e8405bad65a7`,
`bytes_hex`
`804682f2e11fa0f2e2ddd7f22300e0f284468292e51fa092e6ddd7922700e0921f0080f2ffff9f92e8fffff20800e092`.

## 5. What this fixes, and what it does not

Fixes:

- the two templates and the five field placements, derived from the MRS nodes by
  the generator;
- `opc` as the only difference between `movz`, `movk` and `movn`, fixed by the
  node, so no plan field names the operation (`EC-16`);
- `hw` as the lane selector, pinned per row, with the accepted set
  `#0`/`#16`/`#32`/`#48` measured in both directions (`EC-30`);
- `imm16` as the unsigned field `0…65535`, stored raw on `movn` rather than as
  its complement;
- the operand list: `dest` `x64` and `imm` `imm16`, unchanged from `movz`;
- the negative evidence: a `-lsl8` lane, a `w32` lane and the `mov` alias have
  no row (`E-FORM-001`), `0.16.0` has no `movk` row (`E-FORM-001`), a `w32`
  destination is `E-OPERAND-001`, and `65536` or a pre-scaled literal is
  `E-RANGE-001`.

Does not fix:

- **the `sf = 0` move-wide lanes.** `MOVK_32_movewide`/`MOVN_32_movewide` are
  different nodes with their own `sf` pin; no row is added.
- **the `mov` alias.** It chooses the operation and the lane from the literal's
  value; `EC-16` stays `draft` as a family.
- **`movz`/`movk`/`movn` with a shifted register or symbol operand.** The nodes
  take an immediate field only.
- **any semantic claim about the built value.** This record measures encoded
  words and the disassembler's rendering; it does not model the instruction's
  result.

## 6. Result

The rows ship in `definitions/aarch64/0.17.0.json`, which repeats the 168
`0.16.0` forms and adds eight:

```text
definition  definitions/aarch64/0.17.0.json
namespace   monasm.isa.aarch64
version     0.17.0
forms       176
digest      sha256:de2c53e1871f5c24f6af73082dcc402729786d2e6e2495f84e3ed553adb4e4ed
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 48 bytes above and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P19-movwide` | twelve instructions, eight new rows plus four boundary rows | 48 bytes, `sha256:ec16d04e…` |
| `N01t-absent-movk-lsl8` | `-lsl8` against `0.17.0` | `E-FORM-001` |
| `N01u-movk-absent-in-previous-version` | `-lsl16` against `0.16.0` | `E-FORM-001` |
| `N01v-absent-w32-movk-lane` | `w32` lane against `0.17.0` | `E-FORM-001` |
| `N01w-absent-mov-alias` | `mov` alias against `0.17.0` | `E-FORM-001` |
| `N02i-w-dest-on-movk-row` | `w32` destination on a 64-bit row | `E-OPERAND-001` on `kind` and `target_type` |
| `N03-movk-imm16-out-of-range` | `imm16 = 65536` on `-lsl0` | `E-RANGE-001` |
| `N18g-movk-pre-scaled-literal` | `0x12340000` on `-lsl16` | `E-RANGE-001` |

`N18g` is the move-wide twin of `N18c`: the same rule that `movz` cannot carry a
pre-scaled literal applies to `movk`, because the row already names the lane.
