# EXP-0019 — the `sub` nodes: one `op` bit away from `add`, three boundaries

- Date: 2026-11-04
- Question: is `sub` a new encoding form or a modifier of `add`; which nodes carry
  the flag-setting and 32-bit spellings; and does the `sh` half behave as it does
  for `add`?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes and the legal spellings
  come from the MRS nodes and the assembler; what subtraction *computes*, and
  what `subs` does to the flags, is not claimed here.

## 1. The nodes

`start+width` counts from bit 0 of the 32-bit word.

### `SUB_64_addsub_imm` → `aarch64:sub/x64-imm12-lsl0` and `.../x64-imm12-lsl12`

| Field | start+width | MRS value | `-lsl0` use | `-lsl12` use |
|---|---|---|---|---|
| `sf` | 31+1 | `1` | fixed | fixed |
| `op` | 30+1 | `1` | fixed — the only bit that differs from `ADD_64_addsub_imm` | fixed |
| `S` | 29+1 | `0` | fixed | fixed |
| — | 26+3 | `100` | fixed | fixed |
| — | 23+3 | `010` | fixed | fixed |
| `sh` | 22+1 | `x` | **pinned to `0` (no LSL #12)** | **pinned to `1` (LSL #12)** |
| `imm12` | 10+12 | `xxxxxxxxxxxx` | slot `imm`, unsigned | slot `imm`, unsigned |
| `Rn` | 5+5 | `xxxxx` | slot `src` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` | slot `dest` |

### `SUB_64_addsub_shift` → `aarch64:sub/x64-x64-x64-lsl0` and the three `-imm6-*` rows

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed |
| `op` | 30+1 | `1` | fixed — differs from `ADD_64_addsub_shift` here only |
| `S` | 29+1 | `0` | fixed |
| `op1` | 28+1 | `0` | fixed |
| — | 25+3 | `101` | fixed |
| — | 24+1 | `1` | fixed |
| `shift` | 22+2 | `xx` | **pinned** per row: `00` on `-lsl0` and `-imm6-lsl`, `01` on `-imm6-lsr`, `10` on `-imm6-asr` |
| — | 21+1 | `0` | fixed |
| `Rm` | 16+5 | `xxxxx` | slot `src2` |
| `imm6` | 10+6 | `xxxxxx` | **pinned to `000000`** on `-lsl0`; slot `imm`, unsigned, on the three `-imm6-*` rows |
| `Rn` | 5+5 | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

Both nodes are field-for-field the `ADD_64` nodes of `EXP-0008` §2 with `op`
inverted, so the generator reads them with the same slot specs and pins only the
field the `add` rows already pin.

### Read, not used (the boundaries)

- `SUBS_64_addsub_shift`: same layout as `SUB_64_addsub_shift` with `S` fixed to
  `1`. `SUBS_64S_addsub_imm`: same layout as `SUB_64_addsub_imm` with `S` fixed
  to `1`.
- `SUB_32_addsub_imm` / `SUB_32_addsub_shift`: the same two layouts with `sf`
  fixed to `0`; `SUB_32_addsub_shift` also shows the `opt`/bit-21 pair the 32-bit
  extended node uses.
- `SUB_64_addsub_ext`: `op = 1` on the extended layout (`opt = 00`, bit 21 = 1),
  i.e. `ADR-0016`'s eight rows with the other `op`. Still absent (`N01f`).

## 2. The spellings, measured

`llvm-mc -triple=aarch64 -show-encoding`, one line per table row.

### Accepted

| Source | Bytes | Word | Row |
|---|---|---|---|
| `sub x0, x1, x2` | `20 00 02 cb` | `0xcb020020` | `-lsl0` |
| `sub x0, x1, x2, lsl #0` | `20 00 02 cb` | `0xcb020020` | `-lsl0` / `-imm6-lsl` with 0 |
| `sub x0, x1, x2, lsl #3` | `20 0c 02 cb` | `0xcb020c20` | `-imm6-lsl` |
| `sub x0, x1, x2, lsr #7` | `20 1c 42 cb` | `0xcb421c20` | `-imm6-lsr` |
| `sub x0, x1, x2, asr #63` | `20 fc 82 cb` | `0xcb82fc20` | `-imm6-asr` |
| `sub x0, x1, #0` | `20 00 00 d1` | `0xd1000020` | `-lsl0` |
| `sub x0, x1, #4095` | `20 fc 3f d1` | `0xd13ffc20` | `-lsl0` |
| `sub x0, x1, #1, lsl #12` | `20 04 40 d1` | `0xd1400420` | `-lsl12`, `imm12 = 1` |
| `sub x0, x1, #291, lsl #12` | `20 8c 44 d1` | `0xd1448c20` | `-lsl12`, `imm12 = 291` |
| `sub x0, x1, #4095, lsl #12` | `20 fc 7f d1` | `0xd17ffc20` | `-lsl12` |

Every `sub` word is the corresponding `add` word with bit 30 set (`0x8b…` →
`0xcb…`, `0x91…` → `0xd1…`), and bits 15–0 are unchanged, which is the whole
claim: `op` is the only difference at the node level.

### Accepted but re-encoded — the value-driven switch

| Source | Bytes | Word | What the assembler did |
|---|---|---|---|
| `sub x0, x1, #0x1000` | `20 04 40 d1` | `0xd1400420` | chose `sh = 1` and `imm12 = 1`, silently |
| `sub x0, x1, #0x123000` | `20 8c 44 d1` | `0xd1448c20` | chose `sh = 1` and `imm12 = 291`, silently |

Both are the `-lsl12` words. A plan that names `-lsl0` and states either literal
must therefore be rejected rather than re-encoded: the form is the decision, and
picking it from the operand's value is `INV-02` (`N18d`).

### Rejected, or a different node

| Source | Result |
|---|---|
| `sub x0, x1, x2, ror #3` | rejected: `expected 'sxtx' 'uxtx' or 'lsl' with optional integer in range [0, 4]` |
| `sub x0, x1, x2, lsl #64` | rejected, same message |
| `sub x0, x1, x2, lsl #-1` | rejected: `expected integer shift amount` |
| `sub w0, w1, w2` | `0x4b020020` — the `sf = 0` node, a different form family |
| `subs x0, x1, x2` | `0xeb020020` — `S = 1`, bit 29 |
| `subs x0, x1, #1` | `0xf1000420` — `S = 1`, bit 29 |
| `sub x0, x1, w2, uxtb #0` | `0xcb220020` — the extended node, bit 21 |
| `sub x0, x1, x2, uxtx #3` | `0xcb226c20` — the extended node |
| `sub sp, x1, x2` | `0xcb22603f` — the extended node with `option = 011`; `sp` is not reachable through the shifted row, where `31` is `xzr` |

The `ror` rejection is the same fact `EXP-0017` §2 measured for `add`:
`shift = 11` is unallocated in this node, so the keyword set is three wide.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 151 bytes,
`sha256:865dc3980cdc476fb9fef77013e229134876d75728acea5c031443e0534ed89d`):

```text
  sub x3, x4, x5
  sub x6, x7, #4095
  sub x9, x10, #291, lsl #12
  sub x12, x13, x14, lsl #3
  sub x15, x16, x17, lsr #7
  sub x18, x19, x20, asr #63
```

`llvm-mc -triple=aarch64 -filetype=obj` emits **no relocations**
(`llvm-readobj -r` prints an empty list): every operand is a register or an
immediate, so no linker is involved. `.text` is 24 bytes.

| Offset | Bytes | Word | Row | Fields |
|---|---|---|---|---|
| 0 | `83 00 05 cb` | `0xcb050083` | `-lsl0` | `Rd` 3, `Rn` 4, `Rm` 5 |
| 4 | `e6 fc 3f d1` | `0xd13ffce6` | `-imm12-lsl0` | `Rd` 6, `Rn` 7, `imm12` 4095 |
| 8 | `49 8d 44 d1` | `0xd1448d49` | `-imm12-lsl12` | `Rd` 9, `Rn` 10, `imm12` 291 |
| 12 | `ac 0d 0e cb` | `0xcb0e0dac` | `-imm6-lsl` | `Rd` 12, `Rn` 13, `Rm` 14, `imm6` 3 |
| 16 | `0f 1e 51 cb` | `0xcb511e0f` | `-imm6-lsr` | `Rd` 15, `Rn` 16, `Rm` 17, `imm6` 7 |
| 20 | `72 fe 94 cb` | `0xcb94fe72` | `-imm6-asr` | `Rd` 18, `Rn` 19, `Rm` 20, `imm6` 63 |

Output: 24 bytes,
`sha256:a83770708689f5cc0fea5fd016f3189fbd6d56e673b318142b6a89ba8fba8953`,
`bytes_hex` `830005cbe6fc3fd1498d44d1ac0d0ecb0f1e51cb72fe94cb`.

The vector pins each decision independently:

- one instruction per row, so a wrong `op` bit in any row cannot hide behind a
  neighbouring row's bytes;
- `imm12` at 4095 (all twelve bits set) and at 291 on `-lsl12`, so the field and
  the pinned `sh` are both visible;
- all three shift keywords, with `imm6` at 3, 7 and 63, so bits 23–22 and 15–10
  move independently;
- every row uses distinct registers, so a register-field slip cannot hide.

## 4. What this fixes, and what it does not

Fixes:

- the six templates (`0xcb000000` / `0xcb400000` / `0xcb800000` for the shifted
  rows, `0xd1000000` / `0xd1400000` for the immediate rows) and their slots,
  derived from the MRS fields by the generator;
- the rule: the mnemonic is the form family and `op` is the node's, not a plan
  field; the `sh`/`shift`/`imm6` treatment is inherited from `ADR-0011` and
  `ADR-0015`;
- the negative evidence: `subs` (`N01g`), the `sf = 0` node (`N01h`) and the
  extended node (`N01f`) are `E-FORM-001`, and a literal outside the named `sh`
  half is `E-RANGE-001` (`N18d`).

Does not fix:

- **`subs`/`adds` and the flag-setting aliases** (`cmp`, `cmn`, `neg`, `negs`).
- **The `sf = 0` node**, i.e. every `w` row of every family.
- **`SUB_64_addsub_ext`**, the eight extended rows with `op = 1`.
- **`sp` as an operand.** In the shifted and immediate nodes register 31 means
  `xzr`; `sub sp, …` is the extended node, which is absent, so no plan can reach
  it through `0.8.0`.
- **What subtraction computes.** Semantics, not bytes.

## 5. Result

The rows ship in `definitions/aarch64/0.8.0.json`, which repeats the
twenty-six earlier forms and adds six:

```text
definition  definitions/aarch64/0.8.0.json
namespace   monasm.isa.aarch64
version     0.8.0
forms       32
digest      sha256:9f82b566af004aaa9f0471151497d65acb45c3a7b46e4240345d21f4e330bc35
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 24 bytes above with no fixup records, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P10-sub-family` | six instructions, six forms | 24 bytes, `sha256:a8377070…` |
| `N01g-absent-flag-form` | `aarch64:subs/x64-x64-x64-lsl0` | `E-FORM-001` |
| `N01h-absent-32bit-form` | `aarch64:sub/w32-w32-w32-lsl0` | `E-FORM-001` |
| `N18d-sub-no-form-switch` | `imm12 = 4096` on `-imm12-lsl0` | `E-RANGE-001` |
