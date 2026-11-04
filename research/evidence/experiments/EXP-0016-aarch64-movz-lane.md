# EXP-0016 — AArch64 `movz`: four lanes, one 16-bit field, and no value-driven form choice

- Date: 2026-11-04
- Question: which bits select the 16-bit lane of `MOVZ`, does the assembler accept a
  pre-scaled literal, and is the lane an operand of the assembly language?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the field ranges come
  from the MRS node and the assembler; the *meaning* of the four lanes is stated
  by the assembly syntax (`lsl #0/#16/#32/#48`), not by a narrative source.

## 1. The node

`start+width` counts from bit 0 of the 32-bit word.

### `MOVZ_64_movewide` → the four `aarch64:movz/x64-imm16-lsl*` rows

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed (64-bit; the `w` variant is another node) |
| `opc` | 29+2 | `10` | fixed (`movz`; `movn` is `00`, `movk` is `11`) |
| — | 26+3 | `100` | fixed |
| — | 23+3 | `101` | fixed |
| `hw` | 21+2 | `xx` | pinned per row: `0`, `1`, `2`, `3` |
| `imm16` | 5+16 | `xxxxxxxxxxxxxxxx` | slot `imm`, unsigned, field content |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

`MOVK_64_movewide` and `MOVN_64_movewide` have the same layout with `opc = 11` and
`opc = 00`. They are not in the table: `opc` is the form, so each is a row of its
own when a slice asks for it (ADR-0011 decision 7, ADR-0014 decision 5).

### Not in the table

- `MOVZ_32_movewide`: `sf = 0`, and the destination is a `w` register. Measured:
  `movz w0, #0x1234` → `0x52824680`. Naming it is `E-FORM-001`.
- `mov`/`movz` alias lowering: measured, `mov x0, #0x1234` and `mov x0, #0x12340000`
  encode `0xd2824680` and `0xd2a24680` — the same two words as the `movz`
  spellings above, with the lane chosen from the literal's value. The alias family
  is `EC-16`, still `draft`; this slice ships the `movz` instruction, not the alias
  (ADR-0014 decision 5).

## 2. The lanes, measured

One instruction per run, `llvm-mc -triple=aarch64 -show-encoding`:

| Source | Bytes | Word | `hw` | Decoded value |
|---|---|---|---|---|
| `movz x0, #0x1234` | `80 46 82 d2` | `0xd2824680` | `00` | `0x1234` |
| `movz x0, #0x1234, lsl #16` | `80 46 a2 d2` | `0xd2a24680` | `01` | `0x00000000_12340000` |
| `movz x2, #1, lsl #32` | `22 00 c0 d2` | `0xd2c00022` | `10` | `0x00000001_00000000` |
| `movz x5, #0xffff, lsl #48` | `e5 ff ff d2` | `0xd2ffffe5` | `11` | `0xffff0000_00000000` |
| `movz x0, #0` | `00 00 80 d2` | `0xd2800000` | `00` | `0` |
| `movz w0, #0x1234` | `80 46 82 52` | `0x52824680` | `00` | `0x1234` in a `w` register |

Three facts fall out.

**The lane is two bits and the field is sixteen.** The first four words share
`opc`, the two literal runs and `Rd`; they differ in bits 22–21 only. The same
`imm16` content (`0x1234`) appears on the first two rows, so a plan that states
only the immediate cannot distinguish them — that is the `EC-30` counterexample.

**The pre-scaled literal is rejected, not folded.** `movz x0, #0x10000` fails with
"immediate must be an integer in range [0, 65535]". The assembler does *not* turn
it into `hw = 1, imm16 = 1` the way it turns `add x0, x1, #0x1000` into `sh = 1`
(`EV-26`). So `movz` has no value-driven form choice to imitate; the lane is
spelled, and the immediate is the field.

**Only four lane spellings exist.** `movz x0, #0x1234, lsl #8` fails with
"expected 'lsl' with optional integer 0, 16, 32 or 48". The four rows are the four
spellings, and `lsl #8` is not an instruction at all.

**The alias is the opposite case.** `mov x0, #0x1234` and `mov x0, #0x12340000`
both assemble, to `0xd2824680` and `0xd2a24680` — the same two words the explicit
`movz` lines produce. So the alias *does* pick the lane from the literal's value,
which is exactly the `INV-02` behaviour `movz` refuses. That decision is `EC-16`
and stays `draft`; it is why the alias is not a row in this table (ADR-0014
decision 5).

`llvm-objdump` reads the top lane back as `mov x5, #-0x1000000000000`: the same
bytes are a negative 64-bit value. That is why the plan states `imm16 = 65535` and
the row states the lane, instead of the plan stating a 64-bit literal that has two
readings.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 121 bytes,
`sha256:69d7474bc7c646eb26e5cbef3af53b214edb13a3b1c838276f81cfbd43a645d7`):

```text
  movz x0, #0x1234
  movz x0, #0x1234, lsl #16
  movz x2, #1, lsl #32
  movz x5, #0xffff, lsl #48
  movz x0, #0, lsl #0
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is an immediate, so no
linker is involved. `.text` is 20 bytes.

| Offset | Bytes | Word | `llvm-objdump` | Plan `imm16` |
|---|---|---|---|---|
| 0 | `80 46 82 d2` | `0xd2824680` | `mov x0, #0x1234` | `4660` (`-lsl0`) |
| 4 | `80 46 a2 d2` | `0xd2a24680` | `mov x0, #0x12340000` | `4660` (`-lsl16`) |
| 8 | `22 00 c0 d2` | `0xd2c00022` | `mov x2, #0x100000000` | `1` (`-lsl32`) |
| 12 | `e5 ff ff d2` | `0xd2ffffe5` | `mov x5, #-0x1000000000000` | `65535` (`-lsl48`) |
| 16 | `00 00 80 d2` | `0xd2800000` | `mov x0, #0x0` | `0` (`-lsl0`) |

Output: 20 bytes,
`sha256:a0a4818ad64c188d184d3d01947ad0370f50bf8625aa9d5643b9969c050d617b`,
`bytes_hex` `804682d28046a2d22200c0d2e5ffffd2000080d2`.

The vector pins each decision independently:

- all four `hw` values, with the *same* `imm16` on the first two rows, so a lane
  slip in the template moves bytes the others do not;
- `imm16` at both ends (`0` and `65535`), and `Rd` at two different registers
  (`x0`, `x2`, `x5`);
- the field itself: `0x1234` sits at bits 20–5 in both of the first two rows, so
  the only difference is the lane.

## 4. What this fixes, and what it does not

Fixes:

- the four templates and the single slot placement (`imm16` at `[5,16]`,
  `Rd` at `[0,5]`), derived from the MRS fields by the generator;
- the rule: the lane is the `form_id`, `imm16` is field content in `0…65535`
  with `align_bits = 0`, and no slot-level scale exists;
- the negative evidence: a pre-scaled literal is `E-RANGE-001` (`N18c`) and a lane
  the ISA does not have is `E-FORM-001` (`N01d`).

Does not fix:

- **`movk`, `movn` and the `w` variant.** Same shapes with different `opc`/`sf`;
  each is a row that does not exist yet (`E-FORM-001`).
- **the `mov` alias family** (`EC-16`). Which lowering a `mov` request becomes is a
  planner decision this slice does not carry.
- **a symbol in `imm16`.** None of the four rows has a fixup; a `:abs_g0:`-style
  relocation would need its own transform decision.

## 5. Result

The rows ship in `definitions/aarch64/0.5.0.json`, which repeats the eleven earlier
forms and adds four:

```text
definition  definitions/aarch64/0.5.0.json
namespace   monasm.isa.aarch64
version     0.5.0
forms       15
digest      sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 20 bytes above with no fixup records, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P7-movz-lane` | five instructions, four forms | 20 bytes, `sha256:a0a4818a…` |
| `N18c-movz-pre-scaled-literal` | `imm16 = 305397760` on `movz/x64-imm16-lsl16` | `E-RANGE-001`, `min 0`, `max 65535` |
| `N01d-absent-movz-lane` | `aarch64:movz/x64-imm16-lsl8` | `E-FORM-001` |
