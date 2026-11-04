# EXP-0008 — generating the AArch64 tables from the MRS nodes

- Date: 2026-11-04 (`0.2.0` … `0.14.0` added the same day; `0.15.0` and
  `0.16.0` added 2026-11-05)
- Subject: how `definitions/aarch64/0.1.0.json` … `0.16.0.json` were derived, and
  what they do and do not cover
- Basis: **experiment** for every field range, template and byte quoted below
- Reproduce:
  `python tools/check_mrs.py --archive <pinned .tar.gz>`, then
  `python research/evidence/experiments/EXP-0008/generate_aarch64.py`

The script emits all sixteen documents. `0.1.0` … `0.15.0` are frozen and their
digests are asserted by the script, so a later edit that tries to move one fails
instead of shipping. A form declares the version it starts in (`since`), so a
later document is always a superset and cannot lose an earlier row.

## 1. Input

The generator reads one file from the disposable drop point:

```text
research/external/arm-mrs/Instructions.json
size   115441429
sha256 a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe
```

`tools/check_mrs.py` verifies this hash, the `Features.json` hash and the
BSD-3-Clause licence sentence before the drop may be used (ADR-0006). The file is
not vendored; the shipped artifact is the JSON table plus its digest.

The thirty-five encode nodes are named exactly as the MRS names them. The
generator walks `instructions` recursively, matches the node's `name`, rejects
duplicates and refuses to run if any node is missing. It does not read groups or
descriptions. From `0.12.0` it also indexes the `Instruction.InstructionAlias`
nodes, but only to verify the `cmp`/`cmn` pairing: an alias node has no
`encoding`, so it cannot supply a bit field and is never a byte source
(`ADR-0021` decision 3). Ten alias nodes are read; the two 32-bit extended
aliases stay unread with their base nodes.

## 2. The MRS nodes and their encode fields

`start+width` counts from bit 0 of the 32-bit word. `value` is the MRS
`encoding.values[].value` string; `x` means the bit is an operand, `0`/`1` means
the node fixes it.

### `ADD_64_addsub_shift` → `aarch64:add/x64-x64-x64-lsl0` and the three `-imm6-*` rows

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed |
| `op` | 30+1 | `0` | fixed |
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

The MRS leaves `shift` and `imm6` variable because the same node encodes all
shifted-register forms. `0.1.0` has one row, `LSL #0`, so nothing shifts
implicitly (`INV-02`). `0.6.0` reads the same node three more times, once per
keyword, and leaves `imm6` open as the amount: the keyword is a spelling with no
numeric form (`ror` is rejected, `shift = 11` is unallocated), while the amount is
just the field (`EXP-0017` §1–§2, ADR-0015). `shift = 0` with `imm6 = 0` is the
same word as the `0.1.0` row, so both rows stay.

### `ADD_64_addsub_ext` → the eight `aarch64:add/…-imm3-*` rows

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed |
| `op` | 30+1 | `0` | fixed |
| `S` | 29+1 | `0` | fixed |
| `op1` | 28+1 | `0` | fixed |
| — | 25+3 | `101` | fixed |
| — | 24+1 | `1` | fixed |
| `opt` | 22+2 | `00` | fixed — the shifted node's `shift` slot |
| — | 21+1 | `1` | fixed — the bit that separates this node from the shifted one |
| `Rm` | 16+5 | `xxxxx` | slot `src2`, width depends on the keyword |
| `option` | 13+3 | `xxx` | **pinned** per row: `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7` |
| `imm3` | 10+3 | `xxx` | slot `imm`, unsigned, `0…4` with `5…7` excluded |
| `Rn` | 5+5 | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

The node is one bit apart from `ADD_64_addsub_shift`: `opt` is pinned at `00` and
bit 21 is `1`, where the shifted node leaves `shift` at 22+2 and fixes bit 21 to
`0`. `0.7.0` reads it eight times, once per `option`, because the keyword also
decides the width of the register it consumes: the six `[su]xt[bhw]` keywords
take a `w` source and `uxtx`/`sxtx` take an `x` source (`EXP-0018` §2, ADR-0016).
The amount is `imm3` field content, but only `0…4` are allocated, so the slot has
`bits: 3` plus `excluded: [5, 6, 7]` (ADR-0009). `imm3 = 0` stays legal because
the assembler prints `uxtb #0` back as `uxtb`, the same word.

### `ADD_64_addsub_imm` → `aarch64:add/x64-imm12-lsl0` and `.../x64-imm12-lsl12`

| Field | start+width | MRS value | `-lsl0` use | `-lsl12` use |
|---|---|---|---|---|
| `sf` | 31+1 | `1` | fixed | fixed |
| `op` | 30+1 | `0` | fixed | fixed |
| `S` | 29+1 | `0` | fixed | fixed |
| — | 26+3 | `100` | fixed | fixed |
| — | 23+3 | `010` | fixed | fixed |
| `sh` | 22+1 | `x` | **pinned to `0` (no LSL #12)** | **pinned to `1` (LSL #12)** |
| `imm12` | 10+12 | `xxxxxxxxxxxx` | slot `imm`, unsigned | slot `imm`, unsigned |
| `Rn` | 5+5 | `xxxxx` | slot `src` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` | slot `dest` |

The node is read twice. Both forms put `imm12` field content in the slot and
differ only in the pinned `sh`, which is why the second one is a second row and
not a scaled slot: the operand is `[0, 4095]` in both, and the instruction
applies the `<< 12` (`07_definition_format.md` §8.3, ADR-0011). The scaled form
is emitted into `0.2.0` only, so `0.1.0` stays byte-identical.

### `SUB_64_addsub_shift` / `SUB_64_addsub_imm` → the six `aarch64:sub/…` rows

These are field-for-field the two `ADD_64` nodes above with `op` at 30+1 fixed to
`1` instead of `0`; nothing else in either layout changes (`EXP-0019` §1). The
generator therefore reads them with the same slot specs and pins only the field
the `add` rows already pin:

| Node | `op` (30+1) | Pinned per row | Slots | Rows |
|---|---|---|---|---|
| `SUB_64_addsub_shift` | `1` | `shift` (22+2): `00`/`01`/`10`; `imm6` `000000` on `-lsl0` | `dest`/`src`/`src2`, plus `imm` (`imm6`) on the three `-imm6-*` rows | `-lsl0`, `-imm6-lsl`, `-imm6-lsr`, `-imm6-asr` |
| `SUB_64_addsub_imm` | `1` | `sh` (22+1): `0`/`1` | `dest`/`src`/`imm` (`imm12`) | `-lsl0`, `-lsl12` |

`0.8.0` reads each node once per row, so the mnemonic is the form family: the
node fixes `op`, no plan field names it, and no row pins it by hand
(ADR-0017). `ror` is unallocated here as it is on the shifted `add` node, so the
keyword set is still three wide, and `lsl #0` on `-imm6-lsl` is the same word as
`-lsl0`, exactly as for `add` (`EXP-0019` §2). The `S = 1` nodes
(`SUBS_64_addsub_shift`, `SUBS_64S_addsub_imm`) and `SUB_64_addsub_ext` are not
read in the `sub` section: each fixes a different bit, so each is its own slice
and naming one is `E-FORM-001` (`N01f`, `N01g`). The `sf = 0` pair
(`SUB_32_addsub_shift`, `SUB_32_addsub_imm`) is read later, in its own section
(`N01h` is that row against `0.8.0`).

### `ADDS_64_addsub_shift` / `ADDS_64S_addsub_imm` / `SUBS_64_addsub_shift` / `SUBS_64S_addsub_imm` → the twelve `aarch64:adds/…` and `aarch64:subs/…` rows

These four are the four nodes above with `S` at 29+1 fixed to `1`; `op` keeps its
value (`0` for the `ADDS_64` pair, `1` for the `SUBS_64` pair), and
`64S`/`64` in the MRS name is the node's own spelling for the flag-setting 64-bit
form, not a fact the generator infers from (`EXP-0020` §1):

| Node | `op` (30+1) | `S` (29+1) | Pinned per row | Slots | Rows |
|---|---|---|---|---|---|
| `ADDS_64_addsub_shift` | `0` | `1` | `shift` (22+2): `00`/`01`/`10`; `imm6` `000000` on `-lsl0` | `dest`/`src`/`src2`, plus `imm` (`imm6`) on the three `-imm6-*` rows | `-lsl0`, `-imm6-lsl`, `-imm6-lsr`, `-imm6-asr` |
| `ADDS_64S_addsub_imm` | `0` | `1` | `sh` (22+1): `0`/`1` | `dest`/`src`/`imm` (`imm12`) | `-lsl0`, `-lsl12` |
| `SUBS_64_addsub_shift` | `1` | `1` | as `ADDS_64_addsub_shift` | as `ADDS_64_addsub_shift` | the same four |
| `SUBS_64S_addsub_imm` | `1` | `1` | as `ADDS_64S_addsub_imm` | as `ADDS_64S_addsub_imm` | the same two |

`0.9.0` reads each node once per row, so the flag-setting mnemonic is the form
family too: the node fixes `S`, no plan field names it, and no row pins it by
hand (ADR-0018). The two extended S nodes (`ADDS_64S_addsub_ext`,
`SUBS_64S_addsub_ext`) are not read: bit 21 plus `option` makes them a different
slice, so naming one is `E-FORM-001` (`N01f`, `N01g`). The `sf = 0` S pairs are
read later, in their own section (`N01j` is that row against `0.9.0`).
`cmp`/`cmn` are assembler aliases that fix `Rd = 31` and
drop the destination, so they are a two-operand family with no node of their own
(`N01i`, `EXP-0020` §2).

### `ADD_32_addsub_shift` / `ADD_32_addsub_imm` / `SUB_32_*` / `ADDS_32_addsub_shift` / `ADDS_32S_addsub_imm` / `SUBS_*` → the twenty-four `w` rows

These eight are the eight nodes above with `sf` at 31+1 fixed to `0`; `op` and
`S` keep the values their 64-bit twins have, and every other field — `shift`
(22+2), bit 21, `imm6` (10+6), `sh` (22+1), `imm12` (10+12) — is in the same
place (`EXP-0021` §1):

| Node | `sf` (31+1) | `op` (30+1) | `S` (29+1) | Pinned per row | Slots | Rows |
|---|---|---|---|---|---|---|
| `ADD_32_addsub_shift` | `0` | `0` | `0` | `shift`: `00`/`01`/`10`; `imm6` `000000` on `-lsl0` | `dest`/`src`/`src2` (`w32`), plus `imm` (`imm6`, `excluded` 32–63) on the three `-imm6-*` rows | four |
| `ADD_32_addsub_imm` | `0` | `0` | `0` | `sh`: `0`/`1` | `dest`/`src` (`w32`), `imm` (`imm12`) | two |
| `SUB_32_addsub_shift` | `0` | `1` | `0` | as `ADD_32_addsub_shift` | as `ADD_32_addsub_shift` | four |
| `SUB_32_addsub_imm` | `0` | `1` | `0` | as `ADD_32_addsub_imm` | as `ADD_32_addsub_imm` | two |
| `ADDS_32_addsub_shift` | `0` | `0` | `1` | as `ADD_32_addsub_shift` | as `ADD_32_addsub_shift` | four |
| `ADDS_32S_addsub_imm` | `0` | `0` | `1` | as `ADD_32_addsub_imm` | as `ADD_32_addsub_imm` | two |
| `SUBS_32_addsub_shift` | `0` | `1` | `1` | as `ADD_32_addsub_shift` | as `ADD_32_addsub_shift` | four |
| `SUBS_32S_addsub_imm` | `0` | `1` | `1` | as `ADD_32_addsub_imm` | as `ADD_32_addsub_imm` | two |

`0.10.0` reads each node once per row, so the width is the form family: the node
fixes `sf`, no plan field names it, and the `form_id`'s operand signature
(`w32-…` vs `x64-…`) says which family the row belongs to (ADR-0019). Every
register slot is `aarch64.gpr32`/`w32`; the MRS spells the shifted nodes
`<Wd>`/`<Wn>`/`<Wm>` and the immediate nodes `<Wd|WSP>`/`<Wn|WSP>` or `<Wd>`/
`<Wn|WSP>`, so register 31 stays a plain `reg_number` whose meaning is the
node's role (`EXP-0021` §1–§2). The `imm6` slot is the one field-level
difference: the field is six bits, but the 32-bit instruction allocates only
`0…31`, so the slot declares `bits: 6` with `excluded: [32 … 63]` (ADR-0019).
The four `*_32*_addsub_ext` nodes are not read: bit 21 plus `option` again, so
`add w0, wsp, w1` (`0x0b2143e0`) is `E-FORM-001`, not a shifted row.

### `SUB_64_addsub_ext` / `ADDS_64S_addsub_ext` / `SUBS_64S_addsub_ext` → the twenty-four extended rows

These three are `ADD_64_addsub_ext` with `op` at 30+1 and/or `S` at 29+1 fixed;
`opt` (22+2) is `00`, bit 21 is `1`, and `Rm` (16+5), `option` (13+3), `imm3`
(10+3), `Rn` (5+5) and `Rd` (0+5) are in the same place (`EXP-0022` §1):

| Node | `sf` (31+1) | `op` (30+1) | `S` (29+1) | Pinned per row | Slots | Rows |
|---|---|---|---|---|---|---|
| `SUB_64_addsub_ext` | `1` | `1` | `0` | `option` `000`…`111` | `dest`/`src` (`x64`), `src2` (`w32` on `[su]xt[bhw]`, `x64` on `uxtx`/`sxtx`), `imm` (`imm3`, `excluded` 5–7) | eight |
| `ADDS_64S_addsub_ext` | `1` | `0` | `1` | as `SUB_64_addsub_ext` | as `SUB_64_addsub_ext` | eight |
| `SUBS_64S_addsub_ext` | `1` | `1` | `1` | as `SUB_64_addsub_ext` | as `SUB_64_addsub_ext` | eight |

`0.11.0` reads each node once per `option` value, so the mnemonic is the form
family: the node fixes `op`/`S`, no plan field names either bit, and the
`form_id`'s mnemonic component says which node the row came from (ADR-0020).
The keyword keeps choosing `src2`'s width — the six `[su]xt[bhw]` rows take a
`w32` register, the two `[su]xtx` rows an `x64` one — and `imm3` keeps the
`0…4` allocation with `5…7` excluded (`EXP-0022` §2). Register 31 stays a plain
`reg_number`: the MRS grammar spells `Rd` `XdSP_option` on `SUB` and
`XdOrXZR__6` on both S nodes, and `Rn` `XnSP_option` on all three, so the role
decides whether 31 is `sp` or `xzr` and the slot never does (`EXP-0022` §1–§2).
The four `*_32*_addsub_ext` nodes are still not read (`N01l`).

### The ten `CMP`/`CMN` alias nodes → the forty `cmp`/`cmn` rows (verification only)

`CMP` and `CMN` appear in the `Instruction.InstructionAlias` list, twelve nodes
over the six `{imm, shift, ext}` × `{32, 64}` combinations. None of them has an
`encoding` key, so they contribute no field range. Each carries:

| Key | Value | What the generator checks |
|---|---|---|
| `operation_id` | `CMP_SUBS_addsub_shift`, `CMN_ADDS_addsub_ext`, … | exactly two nodes per `(name, operation_id)`, one per width; the row's base node is the id with `32S?`/`64S?` removed |
| `condition` | `Rd == '11111'` | the AST is that binary comparison; anything else refuses to emit |
| `preferred` | `true` | the alias is the printed spelling |
| `_meta.encoded_in` | `<Xn>`/`<Wn>` keys | the width, read from the key prefix, matches the row's base node |

The bytes stay the base node's: `0.12.0` builds `aarch64:cmp/x64-x64-lsl0` from
`SUBS_64S_addsub_shift` with `Rd` at 0+5 pinned to `11111` and the `dest` slot
removed, exactly as the `subs` row had it, and the alias node only confirms which
base node and width that row must name (`ADR-0021` decision 2–3, `EXP-0023`
§1–§2). Register 31 stays a plain `reg_number` in `Rn`/`Rm`, so `cmp sp, #5` and
`cmp x1, xzr` are the same slot shape with different role meanings (`EXP-0023`
§3). The 32-bit extended aliases (`CMP_SUBS_addsub_ext`/`CMN_ADDS_addsub_ext` at
`sf = 0`) stay unread because their base rows are not in the table (`N01l`).

### `BL_only_branch_imm` → `aarch64:bl/imm26`

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `op` | 31+1 | `1` | fixed |
| — | 29+2 | `00` | fixed |
| — | 26+3 | `101` | fixed |
| `imm26` | 0+26 | `xxxxxxxxxxxxxxxxxxxxxxxxxx` | slot `target`, signed |

### `ADRP_only_pcreladdr` → `aarch64:adrp/x64-imm21`

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `op` | 31+1 | `1` | fixed |
| `immlo` | 29+2 | `xx` | slot `target`, bits 1:0 |
| — | 26+3 | `100` | fixed |
| — | 24+2 | `00` | fixed |
| `immhi` | 5+19 | `xxxxxxxxxxxxxxxxxxx` | slot `target`, bits 20:2 |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

`immlo` is at **30:29**, not next to `immhi`. The table records the two
placements in value order — `[5,19]` then `[29,2]` — and the first fixture
attempt, which used a hand-derived `0x90000020` for `imm21 = 1`, was wrong:
the oracle emits `b0000000`. That is the kind of error the two-source rule
exists to catch, and it is why the fixture compares whole words, not the
immediate field alone.

### `B_only_condbranch` → `aarch64:b.cond/imm19`

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `op0` | 29+3 | `010` | fixed |
| — | 26+3 | `101` | fixed |
| — | 24+2 | `00` | fixed |
| `imm19` | 5+19 | `xxxxxxxxxxxxxxxxxxx` | slot `target`, signed |
| `o0` | 4+1 | `0` | fixed |
| `cond` | 0+4 | `xxxx` | slot `imm`, unsigned, `0..15` |

This node has **two** variable fields, and they take opposite treatments:
`imm19` is field content of a `target` slot, exactly like `bl`'s `imm26`, while
`cond` is a 4-bit *operand* (`aarch64.cond` / `cond4`). Sixteen rows that differ
only in the low nibble would be one instruction spelled sixteen times, so the
condition is a slot and the form has no `excluded` list: all sixteen values are
architecture-defined, `AL` and `NV` included (`EXP-0014` §2, ADR-0012). The row
is emitted into `0.3.0` only.

### `LDR_64_ldst_pos` → `aarch64:ldr/x64-base-imm12`

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `size` | 30+2 | `11` | fixed (8-byte access) |
| — | 28+2 | `11` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `1` | fixed — the unsigned-offset kind |
| `opc` | 22+2 | `01` | fixed (load) |
| `imm12` | 10+12 | `xxxxxxxxxxxx` | slot `disp`, unsigned, 8-byte units |
| `Rn` | 5+5 | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | slot `dest` |

### `LDR_64_ldst_immpre`, `LDR_64_ldst_immpost`, `LDUR_64_ldst_unscaled` → the three `imm9` rows

The three nodes share one layout and differ only in bits 11–10, which is the
addressing kind:

| Field | start+width | pre | post | unscaled | Our use |
|---|---|---|---|---|---|
| `size` | 30+2 | `11` | `11` | `11` | fixed |
| — | 28+2 | `11` | `11` | `11` | fixed |
| — | 27+1 | `1` | `1` | `1` | fixed |
| `VR` | 26+1 | `0` | `0` | `0` | fixed |
| — | 25+1 | `0` | `0` | `0` | fixed |
| — | 24+1 | `0` | `0` | `0` | fixed |
| `opc` | 22+2 | `01` | `01` | `01` | fixed (load) |
| — | 21+1 | `0` | `0` | `0` | fixed |
| `imm9` | 12+9 | `xxxxxxxxx` | `xxxxxxxxx` | `xxxxxxxxx` | slot `disp`, signed, bytes |
| — | 10+2 | `11` | `01` | `00` | fixed — the kind |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `dest` |

### `STR_64_ldst_pos` → `aarch64:str/x64-base-imm12`

Same layout as `LDR_64_ldst_pos` with `opc = 00` and `Rt` as the slot `src`,
because the register is read rather than written. This row exists to show that
`opc` comes from the form and not from the mnemonic (ADR-0013 decision 5).

### `STR_64_ldst_immpre`, `STR_64_ldst_immpost`, `STUR_64_ldst_unscaled` → the three store `imm9` rows

`0.13.0` adds the store half of the same three kinds. The field lists are the
`LDR_64_ldst_*`/`LDUR_64_ldst_unscaled` ones with `opc` at `00` and `Rt` as the
slot `src`:

| Field | start+width | pre | post | unscaled | Our use |
|---|---|---|---|---|---|
| `size` | 30+2 | `11` | `11` | `11` | fixed |
| — | 28+2 | `11` | `11` | `11` | fixed |
| — | 27+1 | `1` | `1` | `1` | fixed |
| `VR` | 26+1 | `0` | `0` | `0` | fixed |
| — | 25+1 | `0` | `0` | `0` | fixed |
| — | 24+1 | `0` | `0` | `0` | fixed |
| `opc` | 22+2 | `00` | `00` | `00` | fixed (store) |
| — | 21+1 | `0` | `0` | `0` | fixed |
| `imm9` | 12+9 | `xxxxxxxxx` | `xxxxxxxxx` | `xxxxxxxxx` | slot `disp`, signed, bytes |
| — | 10+2 | `11` | `01` | `00` | fixed — the kind |
| `Rn` | 5+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | `xxxxx` | `xxxxx` | slot `src` (stored register) |

The eight load/store nodes each leave exactly one field variable (`imm12` or
`imm9`), so a row is the node plus the unit its field counts. That is why the
kind cannot be an operand value: choosing between these nodes changes the
opcode bits *and* the offset field width (`EXP-0015` §1–§2, `EXP-0024` §1,
ADR-0013, ADR-0022).

### `LDR_64_loadlit` → `aarch64:ldr/x64-imm19`

`0.14.0` adds the one load with no base register. The node fixes the pattern and
leaves two fields:

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `opc` | 30+2 | `01` | fixed (`LDR Xt`) |
| — | 28+2 | `01` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed (no SIMD/FP) |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `0` | fixed |
| `imm19` | 5+19 | `xxxxxxxxxxxxxxxxxxx` | slot `target`, signed, 4-byte units |
| `Rt` | 0+5 | `xxxxx` | slot `dest` |
| `Rn` | — | absent | no `base` slot exists |

The fixed bits are `0x58000000`, and there are no kind bits to pin: bits 11–10
and bit 21 are not fields in this node. `Rt` and `imm19` are the only variable
parts, so the row has two slots and no base. The other `opc` values (`00`
`LDR Wt`, `10` `LDRSW`, `11` `PRFM`) and the `VR = 1` family stay out, as does
every store literal: the drop has no `STR_*_loadlit` node (`EXP-0025` §1–§2,
ADR-0023).

### `LDR_64_ldst_regoff` / `STR_64_ldst_regoff` → the sixteen register-offset rows

`0.15.0` adds the last addressing kind the drop carries. Both nodes have the same
layout and differ only in `opc`; each is read eight times, once per `option`/`S`
pair:

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `size` | 30+2 | `11` | fixed (64-bit) |
| — | 28+2 | `11` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed (no SIMD/FP) |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `0` | fixed |
| `opc` | 22+2 | `01` / `00` | fixed — `LDR Xt` / `STR Xt` |
| — | 21+1 | `1` | fixed — register-offset kind bit |
| `Rm` | 16+5 | `xxxxx` | slot `index` (`x64` on `lsl`/`sxtx`, `w32` on `uxtw`/`sxtw`) |
| `option` | 13+3 | `xxx` | **pinned** per row: `011` LSL, `010` UXTW, `110` SXTW, `111` SXTX |
| `S` | 12+1 | `x` | **pinned** per row: `0` unscaled, `1` scaled by 8 |
| — | 11+2 | `10` | fixed — register-offset kind bits |
| `Rn` | 5+5 | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | slot `dest` / `src` |

`option` and `S` are the two byte-affecting decisions, so each of the eight
combinations is a row (`INV-02`, ADR-0024). `Rm` is a plain `reg_number`: the
field is the 5-bit number and the slot's role tells `sp` from `xzr`/`wzr`.
`option` also fixes the index width, which is why the `uxtw`/`sxtw` rows declare
`aarch64.gpr32`/`w32` and the others `aarch64.gpr64`/`x64` (`EXP-0026` §2). The
coarse `aarch64:ldr/x64-base-regoff` never becomes a form, so `N01b` stays an
`E-FORM-001` (`N01p` binds a concrete row to `0.14.0` for the same boundary).

### `LDR_32_ldst_regoff` / `STR_32_ldst_regoff` → the sixteen 32-bit register-offset rows

`0.16.0` adds the 32-bit half of the same kind. The nodes are the 64-bit pair with
`size = 10`, so only the templates' top bits and the `S = 1` amount change; each
is read eight times, once per `option`/`S` pair:

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `size` | 30+2 | `10` | fixed (32-bit) |
| — | 28+2 | `11` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed (no SIMD/FP) |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `0` | fixed |
| `opc` | 22+2 | `01` / `00` | fixed — `LDR Wt` / `STR Wt` |
| — | 21+1 | `1` | fixed — register-offset kind bit |
| `Rm` | 16+5 | `xxxxx` | slot `index` (`x64` on `lsl`/`sxtx`, `w32` on `uxtw`/`sxtw`) |
| `option` | 13+3 | `xxx` | **pinned** per row: `011` LSL, `010` UXTW, `110` SXTW, `111` SXTX |
| `S` | 12+1 | `x` | **pinned** per row: `0` unscaled, `1` scaled by 4 |
| — | 11+2 | `10` | fixed — register-offset kind bits |
| `Rn` | 5+5 | `xxxxx` | slot `base` |
| `Rt` | 0+5 | `xxxxx` | slot `dest` / `src` (`w32`) |

`option` fixes the index width exactly as at 64 bits, so the `uxtw`/`sxtw` rows
again take `aarch64.gpr32`/`w32` and the others `aarch64.gpr64`/`x64`. The one
new slot fact is that `Rt` is `aarch64.gpr32`/`w32` on both mnemonics: the
access is 4 bytes, so the loaded or stored register is `w`. `EXP-0027` §2
measures the eight-row ladder at `#0`/`#2` and §3 the rejections; the scale is
the only decision `ADR-0024` did not already make.

### `MOVZ_64_movewide` → the four `aarch64:movz/x64-imm16-lsl*` rows

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed |
| `opc` | 29+2 | `10` | fixed (`movz`) |
| — | 26+3 | `100` | fixed |
| — | 23+3 | `101` | fixed |
| `hw` | 21+2 | `xx` | **pinned** per row: `0`, `1`, `2`, `3` |
| `imm16` | 5+16 | `xxxxxxxxxxxxxxxx` | slot `imm`, unsigned |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

This is the second node the table reads four times, and the first where the pinned
field is multi-bit: `hw` is the 16-bit lane selector, the four values are exactly
the four `lsl #0/#16/#32/#48` spellings, and `imm16` stays field content
(`EXP-0016` §1–§2, ADR-0014). `MOVK_64_movewide` (`opc = 11`), `MOVN_64_movewide`
(`opc = 00`) and `MOVZ_32_movewide` (`sf = 0`) have the same layout and are absent,
so naming one is `E-FORM-001`.

## 3. How the template is built

For each node the generator:

1. classifies every encode field as *fixed* (value string over `{0,1}`) or
   *variable* (value string all `x`); a field mixing the two is a hard error;
2. ORs the fixed values in at their `start` positions;
3. requires every name in `pinned` to be present **and** variable, and the
   pinned value to fit the field — pinning a bit the MRS already fixes would
   hide a decision rather than state one; the value is an integer, so `sh = 1`
   and `sh = 0` are the same kind of statement;
4. derives each slot's placements from the MRS field ranges, so a wrong bit
   position is a mismatch, not a typo;
5. checks that the slot's placement widths sum to its declared `range.bits`;
6. checks that every one of the 32 bits is owned exactly once by a fixed bit, a
   pinned bit, or one slot placement, and that no two owners overlap.
7. selects the forms for each document version (`since` gate: a form is present in
   every document at or after its `since`, and absent `since` means all of them),
   renders them, and re-parses the text to confirm the renderer and the builder
   describe the same document before anything is written.

Any failure aborts before the file is written. The output therefore cannot
contain an uncovered bit, a doubly-written bit, or a placement the MRS does not
have.

The generated templates are:

| Form | Template (file order) | Word (disassembler order) |
|---|---|---|
| `aarch64:add/x64-x64-x64-lsl0` | `0000008b` | `0x8b000000` |
| `aarch64:add/x64-imm12-lsl0` | `00000091` | `0x91000000` |
| `aarch64:add/x64-imm12-lsl12` | `00004091` | `0x91400000` |
| `aarch64:bl/imm26` | `00000094` | `0x94000000` |
| `aarch64:adrp/x64-imm21` | `00000090` | `0x90000000` |
| `aarch64:b.cond/imm19` | `00000054` | `0x54000000` |
| `aarch64:ldr/x64-base-imm12` | `000040f9` | `0xf9400000` |
| `aarch64:ldr/x64-base-imm9-pre` | `000c40f8` | `0xf8400c00` |
| `aarch64:ldr/x64-base-imm9-post` | `000440f8` | `0xf8400400` |
| `aarch64:ldur/x64-base-imm9` | `000040f8` | `0xf8400000` |
| `aarch64:str/x64-base-imm12` | `000000f9` | `0xf9000000` |
| `aarch64:str/x64-base-imm9-pre` | `000c00f8` | `0xf8000c00` |
| `aarch64:str/x64-base-imm9-post` | `000400f8` | `0xf8000400` |
| `aarch64:stur/x64-base-imm9` | `000000f8` | `0xf8000000` |
| `aarch64:ldr/x64-imm19` | `00000058` | `0x58000000` |
| `aarch64:ldr/x64-base-regoff-lsl0` | `006860f8` | `0xf8606800` |
| `aarch64:ldr/x64-base-regoff-lsl3` | `007860f8` | `0xf8607800` |
| `aarch64:ldr/x64-base-regoff-uxtw0` | `004860f8` | `0xf8604800` |
| `aarch64:ldr/x64-base-regoff-uxtw3` | `005860f8` | `0xf8605800` |
| `aarch64:ldr/x64-base-regoff-sxtw0` | `00c860f8` | `0xf860c800` |
| `aarch64:ldr/x64-base-regoff-sxtw3` | `00d860f8` | `0xf860d800` |
| `aarch64:ldr/x64-base-regoff-sxtx0` | `00e860f8` | `0xf860e800` |
| `aarch64:ldr/x64-base-regoff-sxtx3` | `00f860f8` | `0xf860f800` |
| `aarch64:str/x64-base-regoff-lsl0` | `006820f8` | `0xf8206800` |
| `aarch64:str/x64-base-regoff-lsl3` | `007820f8` | `0xf8207800` |
| `aarch64:str/x64-base-regoff-uxtw0` | `004820f8` | `0xf8204800` |
| `aarch64:str/x64-base-regoff-uxtw3` | `005820f8` | `0xf8205800` |
| `aarch64:str/x64-base-regoff-sxtw0` | `00c820f8` | `0xf820c800` |
| `aarch64:str/x64-base-regoff-sxtw3` | `00d820f8` | `0xf820d800` |
| `aarch64:str/x64-base-regoff-sxtx0` | `00e820f8` | `0xf820e800` |
| `aarch64:str/x64-base-regoff-sxtx3` | `00f820f8` | `0xf820f800` |
| `aarch64:ldr/w32-base-regoff-lsl0` | `006860b8` | `0xb8606800` |
| `aarch64:ldr/w32-base-regoff-lsl2` | `007860b8` | `0xb8607800` |
| `aarch64:ldr/w32-base-regoff-uxtw0` | `004860b8` | `0xb8604800` |
| `aarch64:ldr/w32-base-regoff-uxtw2` | `005860b8` | `0xb8605800` |
| `aarch64:ldr/w32-base-regoff-sxtw0` | `00c860b8` | `0xb860c800` |
| `aarch64:ldr/w32-base-regoff-sxtw2` | `00d860b8` | `0xb860d800` |
| `aarch64:ldr/w32-base-regoff-sxtx0` | `00e860b8` | `0xb860e800` |
| `aarch64:ldr/w32-base-regoff-sxtx2` | `00f860b8` | `0xb860f800` |
| `aarch64:str/w32-base-regoff-lsl0` | `006820b8` | `0xb8206800` |
| `aarch64:str/w32-base-regoff-lsl2` | `007820b8` | `0xb8207800` |
| `aarch64:str/w32-base-regoff-uxtw0` | `004820b8` | `0xb8204800` |
| `aarch64:str/w32-base-regoff-uxtw2` | `005820b8` | `0xb8205800` |
| `aarch64:str/w32-base-regoff-sxtw0` | `00c820b8` | `0xb820c800` |
| `aarch64:str/w32-base-regoff-sxtw2` | `00d820b8` | `0xb820d800` |
| `aarch64:str/w32-base-regoff-sxtx0` | `00e820b8` | `0xb820e800` |
| `aarch64:str/w32-base-regoff-sxtx2` | `00f820b8` | `0xb820f800` |
| `aarch64:movz/x64-imm16-lsl0` | `000080d2` | `0xd2800000` |
| `aarch64:movz/x64-imm16-lsl16` | `0000a0d2` | `0xd2a00000` |
| `aarch64:movz/x64-imm16-lsl32` | `0000c0d2` | `0xd2c00000` |
| `aarch64:movz/x64-imm16-lsl48` | `0000e0d2` | `0xd2e00000` |
| `aarch64:add/x64-x64-x64-imm6-lsl` | `0000008b` | `0x8b000000` |
| `aarch64:add/x64-x64-x64-imm6-lsr` | `0000408b` | `0x8b400000` |
| `aarch64:add/x64-x64-x64-imm6-asr` | `0000808b` | `0x8b800000` |
| `aarch64:add/x64-x64-w32-imm3-uxtb` | `0000208b` | `0x8b200000` |
| `aarch64:add/x64-x64-w32-imm3-uxth` | `0020208b` | `0x8b202000` |
| `aarch64:add/x64-x64-w32-imm3-uxtw` | `0040208b` | `0x8b204000` |
| `aarch64:add/x64-x64-x64-imm3-uxtx` | `0060208b` | `0x8b206000` |
| `aarch64:add/x64-x64-w32-imm3-sxtb` | `0080208b` | `0x8b208000` |
| `aarch64:add/x64-x64-w32-imm3-sxth` | `00a0208b` | `0x8b20a000` |
| `aarch64:add/x64-x64-w32-imm3-sxtw` | `00c0208b` | `0x8b20c000` |
| `aarch64:add/x64-x64-x64-imm3-sxtx` | `00e0208b` | `0x8b20e000` |
| `aarch64:sub/x64-x64-x64-lsl0` | `000000cb` | `0xcb000000` |
| `aarch64:sub/x64-imm12-lsl0` | `000000d1` | `0xd1000000` |
| `aarch64:sub/x64-imm12-lsl12` | `000040d1` | `0xd1400000` |
| `aarch64:sub/x64-x64-x64-imm6-lsl` | `000000cb` | `0xcb000000` |
| `aarch64:sub/x64-x64-x64-imm6-lsr` | `000040cb` | `0xcb400000` |
| `aarch64:sub/x64-x64-x64-imm6-asr` | `000080cb` | `0xcb800000` |
| `aarch64:adds/x64-x64-x64-lsl0` | `000000ab` | `0xab000000` |
| `aarch64:adds/x64-imm12-lsl0` | `000000b1` | `0xb1000000` |
| `aarch64:adds/x64-imm12-lsl12` | `000040b1` | `0xb1400000` |
| `aarch64:adds/x64-x64-x64-imm6-lsl` | `000000ab` | `0xab000000` |
| `aarch64:adds/x64-x64-x64-imm6-lsr` | `000040ab` | `0xab400000` |
| `aarch64:adds/x64-x64-x64-imm6-asr` | `000080ab` | `0xab800000` |
| `aarch64:subs/x64-x64-x64-lsl0` | `000000eb` | `0xeb000000` |
| `aarch64:subs/x64-imm12-lsl0` | `000000f1` | `0xf1000000` |
| `aarch64:subs/x64-imm12-lsl12` | `000040f1` | `0xf1400000` |
| `aarch64:subs/x64-x64-x64-imm6-lsl` | `000000eb` | `0xeb000000` |
| `aarch64:subs/x64-x64-x64-imm6-lsr` | `000040eb` | `0xeb400000` |
| `aarch64:subs/x64-x64-x64-imm6-asr` | `000080eb` | `0xeb800000` |
| `aarch64:add/w32-w32-w32-lsl0` | `0000000b` | `0x0b000000` |
| `aarch64:add/w32-w32-w32-imm6-lsl` | `0000000b` | `0x0b000000` |
| `aarch64:add/w32-w32-w32-imm6-lsr` | `0000400b` | `0x0b400000` |
| `aarch64:add/w32-w32-w32-imm6-asr` | `0000800b` | `0x0b800000` |
| `aarch64:add/w32-imm12-lsl0` | `00000011` | `0x11000000` |
| `aarch64:add/w32-imm12-lsl12` | `00004011` | `0x11400000` |
| `aarch64:sub/w32-w32-w32-lsl0` | `0000004b` | `0x4b000000` |
| `aarch64:sub/w32-w32-w32-imm6-lsl` | `0000004b` | `0x4b000000` |
| `aarch64:sub/w32-w32-w32-imm6-lsr` | `0000404b` | `0x4b400000` |
| `aarch64:sub/w32-w32-w32-imm6-asr` | `0000804b` | `0x4b800000` |
| `aarch64:sub/w32-imm12-lsl0` | `00000051` | `0x51000000` |
| `aarch64:sub/w32-imm12-lsl12` | `00004051` | `0x51400000` |
| `aarch64:adds/w32-w32-w32-lsl0` | `0000002b` | `0x2b000000` |
| `aarch64:adds/w32-w32-w32-imm6-lsl` | `0000002b` | `0x2b000000` |
| `aarch64:adds/w32-w32-w32-imm6-lsr` | `0000402b` | `0x2b400000` |
| `aarch64:adds/w32-w32-w32-imm6-asr` | `0000802b` | `0x2b800000` |
| `aarch64:adds/w32-imm12-lsl0` | `00000031` | `0x31000000` |
| `aarch64:adds/w32-imm12-lsl12` | `00004031` | `0x31400000` |
| `aarch64:subs/w32-w32-w32-lsl0` | `0000006b` | `0x6b000000` |
| `aarch64:subs/w32-w32-w32-imm6-lsl` | `0000006b` | `0x6b000000` |
| `aarch64:subs/w32-w32-w32-imm6-lsr` | `0000406b` | `0x6b400000` |
| `aarch64:subs/w32-w32-w32-imm6-asr` | `0000806b` | `0x6b800000` |
| `aarch64:subs/w32-imm12-lsl0` | `00000071` | `0x71000000` |
| `aarch64:subs/w32-imm12-lsl12` | `00004071` | `0x71400000` |
| `aarch64:sub/x64-x64-w32-imm3-uxtb` | `000020cb` | `0xcb200000` |
| `aarch64:sub/x64-x64-w32-imm3-uxth` | `002020cb` | `0xcb202000` |
| `aarch64:sub/x64-x64-w32-imm3-uxtw` | `004020cb` | `0xcb204000` |
| `aarch64:sub/x64-x64-x64-imm3-uxtx` | `006020cb` | `0xcb206000` |
| `aarch64:sub/x64-x64-w32-imm3-sxtb` | `008020cb` | `0xcb208000` |
| `aarch64:sub/x64-x64-w32-imm3-sxth` | `00a020cb` | `0xcb20a000` |
| `aarch64:sub/x64-x64-w32-imm3-sxtw` | `00c020cb` | `0xcb20c000` |
| `aarch64:sub/x64-x64-x64-imm3-sxtx` | `00e020cb` | `0xcb20e000` |
| `aarch64:adds/x64-x64-w32-imm3-uxtb` | `000020ab` | `0xab200000` |
| `aarch64:adds/x64-x64-w32-imm3-uxth` | `002020ab` | `0xab202000` |
| `aarch64:adds/x64-x64-w32-imm3-uxtw` | `004020ab` | `0xab204000` |
| `aarch64:adds/x64-x64-x64-imm3-uxtx` | `006020ab` | `0xab206000` |
| `aarch64:adds/x64-x64-w32-imm3-sxtb` | `008020ab` | `0xab208000` |
| `aarch64:adds/x64-x64-w32-imm3-sxth` | `00a020ab` | `0xab20a000` |
| `aarch64:adds/x64-x64-w32-imm3-sxtw` | `00c020ab` | `0xab20c000` |
| `aarch64:adds/x64-x64-x64-imm3-sxtx` | `00e020ab` | `0xab20e000` |
| `aarch64:subs/x64-x64-w32-imm3-uxtb` | `000020eb` | `0xeb200000` |
| `aarch64:subs/x64-x64-w32-imm3-uxth` | `002020eb` | `0xeb202000` |
| `aarch64:subs/x64-x64-w32-imm3-uxtw` | `004020eb` | `0xeb204000` |
| `aarch64:subs/x64-x64-x64-imm3-uxtx` | `006020eb` | `0xeb206000` |
| `aarch64:subs/x64-x64-w32-imm3-sxtb` | `008020eb` | `0xeb208000` |
| `aarch64:subs/x64-x64-w32-imm3-sxth` | `00a020eb` | `0xeb20a000` |
| `aarch64:subs/x64-x64-w32-imm3-sxtw` | `00c020eb` | `0xeb20c000` |
| `aarch64:subs/x64-x64-x64-imm3-sxtx` | `00e020eb` | `0xeb20e000` |
| `aarch64:cmp/x64-x64-lsl0` | `1f0000eb` | `0xeb00001f` |
| `aarch64:cmp/x64-x64-imm6-lsl` | `1f0000eb` | `0xeb00001f` |
| `aarch64:cmp/x64-x64-imm6-lsr` | `1f0040eb` | `0xeb40001f` |
| `aarch64:cmp/x64-x64-imm6-asr` | `1f0080eb` | `0xeb80001f` |
| `aarch64:cmp/x64-imm12-lsl0` | `1f0000f1` | `0xf100001f` |
| `aarch64:cmp/x64-imm12-lsl12` | `1f0040f1` | `0xf140001f` |
| `aarch64:cmp/w32-w32-lsl0` | `1f00006b` | `0x6b00001f` |
| `aarch64:cmp/w32-w32-imm6-lsl` | `1f00006b` | `0x6b00001f` |
| `aarch64:cmp/w32-w32-imm6-lsr` | `1f00406b` | `0x6b40001f` |
| `aarch64:cmp/w32-w32-imm6-asr` | `1f00806b` | `0x6b80001f` |
| `aarch64:cmp/w32-imm12-lsl0` | `1f000071` | `0x7100001f` |
| `aarch64:cmp/w32-imm12-lsl12` | `1f004071` | `0x7140001f` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtb` | `1f0020eb` | `0xeb20001f` |
| `aarch64:cmp/x64-x64-w32-imm3-uxth` | `1f2020eb` | `0xeb20201f` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtw` | `1f4020eb` | `0xeb20401f` |
| `aarch64:cmp/x64-x64-x64-imm3-uxtx` | `1f6020eb` | `0xeb20601f` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtb` | `1f8020eb` | `0xeb20801f` |
| `aarch64:cmp/x64-x64-w32-imm3-sxth` | `1fa020eb` | `0xeb20a01f` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtw` | `1fc020eb` | `0xeb20c01f` |
| `aarch64:cmp/x64-x64-x64-imm3-sxtx` | `1fe020eb` | `0xeb20e01f` |
| `aarch64:cmn/x64-x64-lsl0` | `1f0000ab` | `0xab00001f` |
| `aarch64:cmn/x64-x64-imm6-lsl` | `1f0000ab` | `0xab00001f` |
| `aarch64:cmn/x64-x64-imm6-lsr` | `1f0040ab` | `0xab40001f` |
| `aarch64:cmn/x64-x64-imm6-asr` | `1f0080ab` | `0xab80001f` |
| `aarch64:cmn/x64-imm12-lsl0` | `1f0000b1` | `0xb100001f` |
| `aarch64:cmn/x64-imm12-lsl12` | `1f0040b1` | `0xb140001f` |
| `aarch64:cmn/w32-w32-lsl0` | `1f00002b` | `0x2b00001f` |
| `aarch64:cmn/w32-w32-imm6-lsl` | `1f00002b` | `0x2b00001f` |
| `aarch64:cmn/w32-w32-imm6-lsr` | `1f00402b` | `0x2b40001f` |
| `aarch64:cmn/w32-w32-imm6-asr` | `1f00802b` | `0x2b80001f` |
| `aarch64:cmn/w32-imm12-lsl0` | `1f000031` | `0x3100001f` |
| `aarch64:cmn/w32-imm12-lsl12` | `1f004031` | `0x3140001f` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtb` | `1f0020ab` | `0xab20001f` |
| `aarch64:cmn/x64-x64-w32-imm3-uxth` | `1f2020ab` | `0xab20201f` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtw` | `1f4020ab` | `0xab20401f` |
| `aarch64:cmn/x64-x64-x64-imm3-uxtx` | `1f6020ab` | `0xab20601f` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtb` | `1f8020ab` | `0xab20801f` |
| `aarch64:cmn/x64-x64-w32-imm3-sxth` | `1fa020ab` | `0xab20a01f` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtw` | `1fc020ab` | `0xab20c01f` |
| `aarch64:cmn/x64-x64-x64-imm3-sxtx` | `1fe020ab` | `0xab20e01f` |

Templates are stored little-endian, the only byte order v0 definitions declare
(`07_definition_format.md` §4.1).

## 4. Oracle

`llvm-mc` 23.1.2 assembles all one hundred and sixty-eight forms. It does **not** resolve AArch64
branches or `adrp` when the target is a symbol: it emits zeros plus
`fixup_aarch64_pcrel_call26`, `fixup_aarch64_pcrel_adrp_imm21` or
`fixup_aarch64_add_imm12`. For the forms whose bits a fixup owns, the oracle is
therefore the LLVM toolchain's own resolution:

```text
llvm-mc -triple=aarch64 -filetype=obj <input>.s -o out.o
ld.lld --image-base=0 -Ttext=0 -o out.elf out.o
llvm-objcopy -O binary --only-section=.text out.elf out.bin
```

`ld.lld` also applies target relaxations by default. It will rewrite
`adrp`+`add` into `adr` when the target is in range, so the `A64-P6` input keeps
the pair at `0xff8` and the symbol at `0x1008`: the page delta is `0x1000`, out
of `adr` range, and the emitted words are `b0000000 91002000`. The exact commands
and hashes are in each fixture's `.oracle.json`.

`b.cond` is the exception that needed no linker: its three targets are local
labels in the same section, and `llvm-mc` resolved them itself —
`llvm-readobj -r` on the object prints an empty relocation list. The bytes are
therefore the assembler's own, and the fixture records that as oracle metadata
(`EXP-0014` §3). `A64-P3` is the same case for a different reason: every operand
is an immediate, so there is no relocation in the first place. `A64-P8` and
`A64-P9` are the same case again: registers and immediates only (`EXP-0017` §3,
`EXP-0018` §3), and so is `A64-P10` (`EXP-0019` §3), `A64-P11` (`EXP-0020` §3),
`A64-P12` (`EXP-0021` §3), `A64-P13` (`EXP-0022` §3) and `A64-P14` (`EXP-0023`
§3).

The nineteen positive fixtures are:

| Fixture | Document | Bytes | What it proves |
|---|---|---|---|
| `A64-P1-add-register` | `0.1.0` | `2000028b c500078b 20001f8b` | three register triples, including `Rm = 31` (`xzr`) |
| `A64-P2-add-imm12` | `0.1.0` | `20000091 62fc3f91` | both ends of the unsigned imm12 range |
| `A64-P2-add-imm12-lsl12` | `0.2.0` | `20044091 208c4491 62fc7f91 20004091` | `sh = 1` with field content 1, 291, 4095 and 0 |
| `A64-P3-ldst-addressing` | `0.4.0` | `200040f9 62fc7ff9 a48c40f8 e6845ff8 280150f8 6a0100f9` | `imm12` at 0 and 4095, pre-index +8, post-index −8, `ldur` at −256, store at 0 |
| `A64-P4-b-cond` | `0.3.0` | `20000054 e1ffff54 ccffff54` | three conditions (0, 1, 12) and three displacements (+4, −4, −8) |
| `A64-P5-bl-local-symbol` | `0.1.0` | `01000094 ffffff97` | `bl` +4 and −4, resolved by the linker |
| `A64-P6-adrp-lo12-pair` | `0.1.0` | `…b0000000 91002000` at `0xff8`/`0xffc` | `adrp` split field plus the paired `add` |
| `A64-P7-movz-lane` | `0.5.0` | `804682d2 8046a2d2 2200c0d2 e5ffffd2 000080d2` | all four `hw` values, with `imm16 = 0x1234` on the first two so only the lane differs |
| `A64-P8-shift-modifier` | `0.6.0` | `200c028b 201c428b 20fc828b 83fc058b 2000028b 2000428b` | all three `shift` values, `imm6` at 0 and 63, and the `lsl #0` overlap with `-lsl0` |
| `A64-P9-extend-modifier` | `0.7.0` | `8300258b e630288b 494d2b8b ac912e8b 0fa2318b 72d2348b d562378b 38f33a8b` | all eight `option` values, six `w` sources and two `x` sources, `imm3` at 0 and 4, and distinct `Rd`/`Rn`/`Rm` in every row |
| `A64-P10-sub-family` | `0.8.0` | `830005cb e6fc3fd1 498d44d1 ac0d0ecb 0f1e51cb 72fe94cb` | one instruction per `sub` row: `-lsl0`, `imm12` at 4095 and 291<<12, and all three shift keywords with `imm6` at 3, 7 and 63 |
| `A64-P11-adds-subs-family` | `0.9.0` | `200002ab 83fc3fb1 c58c44b1 070d09ab 6a1d4cab cdfd8fab 300212eb 93fe3ff1 d58e44f1 170f19eb 7a1f5ceb dd0700f1` | one instruction per `adds`/`subs` row: both mnemonics, `imm12` at 4095 and 291<<12, all three shift keywords with `imm6` at 3, 7 and 63, and distinct registers in every row |
| `A64-P12-w-rows` | `0.10.0` | `2000020b 83fc3f11 c58c4411 070d090b 6a1d4c0b cd7d8f0b 3002124b 93fe3f51 d58e4451 170f194b 7a1f5c4b dd070051 2000022b 83fc3f31 c58c4431 070d092b 6a1d4c2b cd7d8f2b 3002126b 93fe3f71 d58e4471 170f196b 7a1f5c6b dd070071` | one instruction per `w` row across all four mnemonics: `imm12` at 4095 and 291<<12, all three shift keywords with `imm6` at 3, 7 and 31 (the top allocated amount), and distinct registers 0–30 in every row |
| `A64-P13-ext-family` | `0.11.0` | `200022cb 833025cb e64c28cb 49652bcb ac912ecb 0faa31cb 72ce34cb d5e237cb 38073aab 9b333dab 1e4021ab 626824ab c58c27ab 28a12aab 8bd12dab eee530ab 510a33eb b42e36eb 175339eb 7a633ceb dd8720eb 41a823eb a4cc26eb 07f129eb 3f0c22cb e00321ab 3f0022eb` | one instruction per extended `sub`/`adds`/`subs` row: all eight `option` values on each mnemonic, `imm3` at 0–4, distinct registers 0–30, plus three register-31 rows (`sub` `Rd` = `sp`, `Rn` = `sp`, `subs` `Rd` = `xzr`) |
| `A64-P14-cmp-cmn-family` | `0.12.0` | `3f0002eb 7f1404eb bf1c46eb ff2488eb 3f1500f1 5f8d44f1 7f010c6b bf3d0e6b ff45506b 3f4e926b 7f160071 9f8e4471 bf0236eb ff2638eb 3f4b3aeb 7f6f3ceb bf933eeb 1fa021eb 5fc423eb 9fe825eb df0007ab 1f1509ab 5f1d4bab 9f258dab df1500b1 ff8d44b1 1f02112b 5f3e132b 9f46552b df4e972b 1f170031 3f8f4431 5f033bab 9f273dab df4b20ab 3f6c22ab 7f9024ab bfa026ab dfc427ab 1fe929ab ff1700f1 ff170071 ff6322eb ff1700b1 ff6322ab 3f001feb 3f001f6b` | one instruction per `cmp`/`cmn` form: four shifted and two immediate rows on each width, all eight `option` values on `x64`, `imm3` at 0–4 and `imm6` at 5, 7, 9, 15, 17 and 19, plus seven register-31 rows (`sp`/`wsp` in `Rn`, `xzr`/`wzr` in `Rm`) |
| `A64-P15-store-imm9-addressing` | `0.13.0` | `208c00f8 620c10f8 a48400f8 e6f40ff8 280101f8 6af11ff8 ac0100f9 eefd3ff9` | the store `imm9` kinds at both ends: pre-index `+8`/`−256`, post-index `+8`/`255`, `stur` `+16`/`−1`, and the `imm12` row at `0`/`4095` unchanged |
| `A64-P16-loadlit` | `0.14.0` | `40000058 e1ffff58 e2ff7f58 03008058 84ffff58 25000058` | one form, six values: two symbol targets (`+2`/`−4` field units), plain `−1`/`1`, and both field ends (`262143`/`−262144`) |
| `A64-P17-regoff` | `0.15.0` | `206862f8 417863f8 624864f8 835865f8 a4c866f8 c5d867f8 e6e868f8 07f969f8 206822f8 417823f8 624824f8 835825f8 a4c826f8 c5d827f8 e6e828f8 07f929f8 e06b62f8 20787ff8 e07b22f8 20487ff8` | one instruction per register-offset row: all eight `option`/`S` pairs on `ldr` and `str`, then four register-31 rows (`sp` in `Rn`, `xzr`/`wzr` in `Rm`) |
| `A64-P18-w32regoff` | `0.16.0` | `206862b8 417863b8 624864b8 835865b8 a4c866b8 c5d867b8 e6e868b8 07f969b8 206822b8 417823b8 624824b8 835825b8 a4c826b8 c5d827b8 e6e828b8 07f929b8 e06b62b8 20787fb8 e07b22b8 20487fb8` | one instruction per 32-bit register-offset row: all eight `option`/`S` pairs on `ldr` and `str` at `#0`/`#2`, then the same four register-31 rows, with a `w32` destination/source and `x64` base and index |

These were checked against our materializer, not generated by it
(`AGENTS.md` rule 5). The materializer reproduces all nineteen byte-for-byte and the
fifty negative fixtures (`N01`, `N01b`, `N01d`, `N01e`, `N01f`, `N01g`,
`N01h`, `N01i`, `N01j`, `N01k`, `N01l`, `N01m`, `N01n`, `N01o`, `N01p`, `N01q`,
`N01r`, `N01s`,
`N02b`, `N02c`, `N02d`, `N02e`, `N02f`, `N02g`, `N02h`, `N03`, `N03-cond`, `N03-imm12-disp`,
`N03-imm3`, `N03-imm6`,
`N03-imm9-disp`, `N03-str-imm9-post-disp`, `N03-stur-imm9-disp`, `N04c`, `N04d`,
`N12a`, `N14`, `N16c`, `N16d`, `N16e`, `N18a`, `N18b`, `N18c`, `N18d`, `N18e`,
`N18f`, `N19`, `N19b`, `N20`) reject
exactly the registered diagnostic sets.
`N18a`/`N18b` are the
scaled form's other half: the first is `0x1000` stated on `-lsl0`, the second
`0x123000` on `-lsl12`, and both must be `E-RANGE-001` instead of a form switch or
a pre-scale. `N18c` is the same rule one instruction over: `0x12340000` on
`movz/x64-imm16-lsl16` is the lane's pre-scaled literal, not `imm16` content.
`N03-cond` is `cond = 16` and `N04c` is `imm19 = 262144`: the first would mask to
`eq` if it were truncated, the second is the first value past the signed field, and
both must be rejected rather than repaired. `N04d` is the same `262144` on the
literal row's `imm19`, and `N20` is the same row's fixup with a 2-byte symbol
offset: the field value is in range there, so the alignment check is a second
diagnostic rather than a range failure (`EXP-0025` §2–§3). `N03-imm12-disp` and
`N03-imm9-disp`
are the load/store ranges (`4096` and `−257`), `N01b` is the coarse
register-offset id
and `N01d` the `lsl #8` lane: `E-FORM-001`, not a reinterpreted load or a zeroed
shift. The shift rows add three more: `N03-imm6` is an amount of `64` (the first
value past the 6-bit field), `N19` is the same shift stated as a `modifiers`
entry on `-lsl0` (`E-OPERAND-003`, because a modifier never writes a bit and
accepting it would emit the unshifted word), and `N01e` is an extend spelling
against `0.6.0`, which predates the rows (`EXP-0017` §1–§2, ADR-0015). The extend
rows add four: `N03-imm3` is an amount of `8` (the first value past the 3-bit
field), `N16c` is `5` (inside the field, unallocated, so the closed `excluded`
list rejects it rather than emitting the word), `N02b` is a `w32` operand on an
`x`-source row (the class is the form's, `E-OPERAND-001`), and `N01f` is the
extended `sub` row against `0.7.0`, before any document carried it — a version
boundary now that `0.11.0` does (`EXP-0018` §2,
ADR-0016, narrowed by ADR-0017). The `sub` rows add three: `N01g` is
`aarch64:subs/x64-x64-x64-lsl0` (`S = 1` is a different node), `N01h` is
`aarch64:sub/w32-w32-w32-lsl0` (`sf = 0` is a different pair of nodes), and
`N18d` is `4096` on `sub/x64-imm12-lsl0`, which only fits `-lsl12` and must be
`E-RANGE-001` rather than a form switch (`EXP-0019` §2, ADR-0017). The
`adds`/`subs` rows add three: `N01i` is `aarch64:cmp/x64-x64-lsl0` against
`0.11.0` (the alias fixes `Rd = 31` and drops the destination, so it is a
two-operand family of its own; the row exists from `0.12.0`, which makes this a
version boundary),
`N01j` is `aarch64:adds/w32-w32-w32-lsl0` (`sf = 0` on the `S = 1` node is a
different node), and `N18e` is `4096` on `adds/x64-imm12-lsl0`, the same
value-driven switch one bit over (`EXP-0020` §2, ADR-0018). The `w` rows add
four: `N01k` is `aarch64:add/w32-w32-w32-lsl0` against `0.9.0` (the row exists
only from `0.10.0`), `N02c` is an `x64` destination on a `w` row
(`E-OPERAND-001` on `kind` and `target_type` — the class is the form's), `N16d`
is `imm6 = 32` (inside the six-bit field but outside the 32-bit instruction's
`0…31`, so the closed `excluded` list rejects it), and `N18f` is `4096` on
`adds/w32-imm12-lsl0`, the same form switch one width over (`EXP-0021` §2,
ADR-0019). The extended `sub`/`adds`/`subs` rows add three: `N01l` is
`aarch64:sub/w32-w32-w32-imm3-uxtb`, one of the four `sf = 0` extended nodes
that no document carries, `N02d` is an `x64` source on a `-uxtb` row
(`E-OPERAND-001` on `kind` and `target_type`), and `N16e` is `imm3 = 5` on a
`subs` row — inside the field, unallocated, so the closed `excluded` list
rejects it exactly as `N16c` does on `add` (`EXP-0022` §2, ADR-0020). The
`cmp`/`cmn` rows add two: `N02e` is a `dest` operand on
`aarch64:cmp/x64-x64-lsl0` (the alias row has two slots, so the plan has one
operand too many and gets `E-OPERAND-002` with `expected: 2`, `found: 3` — the
first shape in the table whose operand count differs from its base row), and
`N01m` is `aarch64:cmn/x64-imm12-lsl0` against `0.11.0`, another version
boundary (`EXP-0023` §4–§5, ADR-0021). The store `imm9` rows add three:
`N03-str-imm9-post-disp` is `−257` on the post-index row and
`N03-stur-imm9-disp` is `256` on the unscaled row (the two ends of the field on
two of the three new rows), and `N01n` is `aarch64:str/x64-base-imm9-pre`
against `0.12.0`, the version boundary (`EXP-0024` §2–§5, ADR-0022). The
register-offset rows add four: `N01p` is `aarch64:ldr/x64-base-regoff-lsl0`
against `0.14.0` (the version boundary), `N01q` is the `-lsl1` spelling that
names no row, `N02f` is a `w32` index on a `-lsl0` row (`E-OPERAND-001` on
`kind` and `target_type`), and `N19b` states `lsl #3` as a modifier on the
`index` (`E-OPERAND-003`; a modifier never writes the `S` bit) (`EXP-0026`
§2–§4, ADR-0024). The 32-bit register-offset rows add five: `N01r` is
`aarch64:ldr/w32-base-regoff-lsl0` against `0.15.0` (the version boundary),
`N01s` is the `-lsl3` spelling that names no row at this width, `N02g` is a
`w32` index on a `-lsl0` row and `N02h` an `x64` destination on it
(`E-OPERAND-001` on `kind` and `target_type` for both), and `N19c` states
`lsl #2` as a modifier on the `index` (`E-OPERAND-003`, the 32-bit twin of
`N19b`) (`EXP-0027` §2–§4, ADR-0025).

## 5. What this record does not claim

- **Not exhaustive coverage of the nodes.** The table exercises the register and
  immediate fields at range ends, but it does not enumerate all 2^5 × 2^5 × 2^5
  register triples, nor every `bl`, `b.cond`, load/store, `movz`, shift, extend,
  `sub`, `adds`, `subs`, `w`, extended `sub`/`adds`/`subs`, `cmp`/`cmn`, store
  `imm9`, literal load or register-offset value.
  `EXP-0004` did that for the seven x86 rows; this slice has one hundred and
  sixty-eight rows and nineteen positive fixtures, and `EXP-0014` §2 enumerates the sixteen condition
  values but not their products with the 2^19 displacements; `EXP-0015` §2
  measures both ends of `imm12` and `imm9` but not every value in between,
  `EXP-0016` §2 measures all four `hw` values but two `imm16` values,
  `EXP-0017` §2 measures both ends of `imm6` on two of the three keywords,
  `EXP-0018` §2 measures `imm3` at 0 and 4 but not 1, 2 or 3 on every row,
  `EXP-0019` §3 measures one value per `sub` row, `EXP-0020` §3 measures one
  value per `adds`/`subs` row, `EXP-0021` §3 measures one value per `w` row,
  `EXP-0022` §3 measures one value per extended `sub`/`adds`/`subs` row,
  `EXP-0023` §4 measures one value per `cmp`/`cmn` row plus seven register-31
  rows, `EXP-0024` §3 measures both ends of `imm9` on two of the three store
  rows, `EXP-0025` §2 measures both ends of `imm19`, three values inside it
  and five rejections on the literal row, and `EXP-0026` §2–§3 measures the
  `option`/`S` ladder, five register-31 rows and fourteen rejections, with §4
  reproducing all sixteen register-offset rows; `EXP-0027` §2–§3 measures the
  same ladder at `size = 10` with four more register-31 rows and eleven
  rejections, and §4 reproduces the sixteen 32-bit rows.
- **Not a statement about the other packagings.** Only the archive pinned by
  ADR-0006 was read (`EXP-0006`, `EXP-0007`).
- **Not an encoding-selection mechanism.** Forty-six MRS nodes are read because
  one hundred and sixty-eight forms exist in the table (thirty-six encode nodes,
  most of them read more than once, plus ten `CMP`/`CMN` alias nodes read only for
  verification; `ADD_64_addsub_shift` is read four times,
  `ADD_64_addsub_ext` eight times, `ADD_64_addsub_imm` twice,
  `MOVZ_64_movewide` four times, `SUB_64_addsub_shift` four times,
  `SUB_64_addsub_imm` twice, `ADDS_64_addsub_shift` and `SUBS_64_addsub_shift`
  four times each, `ADDS_64S_addsub_imm` and `SUBS_64S_addsub_imm` twice each,
  `ADD_32_addsub_shift` four times, `ADD_32_addsub_imm` twice,
  `SUB_32_addsub_shift` four times, `SUB_32_addsub_imm` twice,
  `ADDS_32_addsub_shift` four times, `ADDS_32S_addsub_imm` twice,
  `SUBS_32_addsub_shift` four times, `SUBS_32S_addsub_imm` twice,
  `SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext` eight
  times each, `LDR_64_loadlit` once, the eight offset load/store nodes once
  each, and `LDR_64_ldst_regoff`/`STR_64_ldst_regoff` eight times each, and
  `LDR_32_ldst_regoff`/`STR_32_ldst_regoff` eight times each). The
  generator is
  disposable research tooling; the materializer never reads MRS data, never looks
  a mnemonic up, and only resolves the exact `form_id` a plan names.
- **The extended `sf = 0` nodes are absent.** They are other nodes with their own
  `sf` pin, so naming one is `E-FORM-001` (`N01l`). The
  scaled `add`, `b.cond`, load/store, `movz`, shift, extend, `sub`,
  `adds`/`subs`, `w`, extended `sub`/`adds`/`subs`, `cmp`/`cmn`, store `imm9`,
  literal load and register-offset rows are
  rows in `0.2.0` (ADR-0011), `0.3.0` (ADR-0012), `0.4.0` (ADR-0013),
  `0.5.0` (ADR-0014), `0.6.0` (ADR-0015), `0.7.0` (ADR-0016),
  `0.8.0` (ADR-0017), `0.9.0` (ADR-0018), `0.10.0` (ADR-0019),
  `0.11.0` (ADR-0020), `0.12.0` (ADR-0021), `0.13.0` (ADR-0022),
  `0.14.0` (ADR-0023), `0.15.0` (ADR-0024) and `0.16.0` (ADR-0025)
  respectively, none of them a
  slot-level scaling rule or a value-driven form choice; the ten `cmp`/`cmn`
  alias nodes are verification sources for those rows rather than byte sources,
  and the two 32-bit extended aliases stay unread because their base rows do.
  `N01f`, `N01g`,
  `N01h`, `N01j`, `N01k`, `N01i`, `N01m`, `N01n`, `N01o`, `N01p`, `N01q`,
  `N01r` and `N01s` name
  a row against a
  version that predates it, so they stay version boundaries rather than absences.
- **The scaled `:lo12:` link path is unmeasured.** No fixture pairs `adrp` with
  `add ..., lsl #12`; only the `-lsl0` pair is linked (`A64-P6`).

## 6. Result

```text
definition  definitions/aarch64/0.1.0.json
namespace   monasm.isa.aarch64
version     0.1.0
forms       4
digest      sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e

definition  definitions/aarch64/0.2.0.json
namespace   monasm.isa.aarch64
version     0.2.0
forms       5
digest      sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed

definition  definitions/aarch64/0.3.0.json
namespace   monasm.isa.aarch64
version     0.3.0
forms       6
digest      sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb

definition  definitions/aarch64/0.4.0.json
namespace   monasm.isa.aarch64
version     0.4.0
forms       11
digest      sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78

definition  definitions/aarch64/0.5.0.json
namespace   monasm.isa.aarch64
version     0.5.0
forms       15
digest      sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e

definition  definitions/aarch64/0.6.0.json
namespace   monasm.isa.aarch64
version     0.6.0
forms       18
digest      sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964

definition  definitions/aarch64/0.7.0.json
namespace   monasm.isa.aarch64
version     0.7.0
forms       26
digest      sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053

definition  definitions/aarch64/0.8.0.json
namespace   monasm.isa.aarch64
version     0.8.0
forms       32
digest      sha256:9f82b566af004aaa9f0471151497d65acb45c3a7b46e4240345d21f4e330bc35

definition  definitions/aarch64/0.9.0.json
namespace   monasm.isa.aarch64
version     0.9.0
forms       44
digest      sha256:99728cd9bd85b8b0768e700e15dd6263171d6261c385ac15ceeb5df6d2cafcff

definition  definitions/aarch64/0.10.0.json
namespace   monasm.isa.aarch64
version     0.10.0
forms       68
digest      sha256:e958d69b4ba93222e7621a1f5c3ebd056ce929e2974a961a03abb7b66f0b247b

definition  definitions/aarch64/0.11.0.json
namespace   monasm.isa.aarch64
version     0.11.0
forms       92
digest      sha256:c5a9aec943f9b195c400380b8416bf63cba944da3fdf0203f90de5baff295002

definition  definitions/aarch64/0.12.0.json
namespace   monasm.isa.aarch64
version     0.12.0
forms       132
digest      sha256:8a428926568b99f0674785cc674bc066adc452216131706d458b9e3390da03b6

definition  definitions/aarch64/0.13.0.json
namespace   monasm.isa.aarch64
version     0.13.0
forms       135
digest      sha256:d3876dd37a8441057b586312b3bee410e39594c64806b2c5c59960c06f9c7a5f

definition  definitions/aarch64/0.14.0.json
namespace   monasm.isa.aarch64
version     0.14.0
forms       136
digest      sha256:a90ceac19824fbb00731e040346daa191973652e58522fab72336e24f769a5ba

definition  definitions/aarch64/0.15.0.json
namespace   monasm.isa.aarch64
version     0.15.0
forms       152
digest      sha256:422ebb83b897b18e010da37539796b0b97cfc9018a47209fc4a6ddc5b14af5d3

definition  definitions/aarch64/0.16.0.json
namespace   monasm.isa.aarch64
version     0.16.0
forms       168
digest      sha256:1e83c6cad91594e8315500f39d0bcffa235edc90c5f47c012555c077a8dbc457
```

The digests are computed over the canonical form of each whole document
(`01_contract.md` §12, `OD-06`) and printed by `tools/check_definition.py`,
which also checks that the reading-aid table in `07_definition_format.md` §8.2
matches the JSON row by row. `definitions/aarch64/NOTICE` reproduces the upstream
BSD-3-Clause notice and names the archive hash; `0.2.0` … `0.16.0` need
no second notice because they are generated from the same drop and ship under the
same terms.

Because `0.3.0` repeats all five earlier rows verbatim, the only difference from
`0.2.0` is the added `b.cond` row; because `0.4.0` repeats all six earlier rows
verbatim, the only difference from `0.3.0` is the five load/store rows; because
`0.5.0` repeats all eleven earlier rows verbatim, the only difference from `0.4.0`
is the four `movz` rows; because `0.6.0` repeats all fifteen earlier rows
verbatim, the only difference from `0.5.0` is the three shift rows; because
`0.7.0` repeats all eighteen earlier rows verbatim, the only difference from
`0.6.0` is the eight extend rows; because `0.8.0` repeats all twenty-six
earlier rows verbatim, the only difference from `0.7.0` is the six `sub` rows;
because `0.9.0` repeats all thirty-two earlier rows verbatim, the only difference
from `0.8.0` is the twelve `adds`/`subs` rows; because `0.10.0` repeats all
forty-four earlier rows verbatim, the only difference from `0.9.0` is the
twenty-four `w` rows; because `0.11.0` repeats all sixty-eight earlier rows
verbatim, the only difference from `0.10.0` is the twenty-four extended
`sub`/`adds`/`subs` rows; because `0.12.0` repeats all ninety-two earlier
rows verbatim, the only difference from `0.11.0` is the forty `cmp`/`cmn` rows;
and because `0.13.0` repeats all one hundred and thirty-two earlier rows
verbatim, the only difference from `0.12.0` is the three store `imm9` rows;
because `0.14.0` repeats all one hundred and thirty-five earlier rows verbatim,
the only difference from `0.13.0` is the literal load row; because `0.15.0`
repeats all one hundred and thirty-six earlier rows verbatim, the only difference
from `0.14.0` is the sixteen register-offset rows; and because `0.16.0` repeats
all one hundred and fifty-two earlier rows verbatim, the only difference from
`0.15.0` is the sixteen 32-bit register-offset rows. The
generator's frozen-digest assertions are what prove
that no earlier row moved while a new one landed.
