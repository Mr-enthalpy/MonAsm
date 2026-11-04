# EXP-0008 — generating the AArch64 tables from the MRS nodes

- Date: 2026-11-04 (documents `0.2.0` … `0.4.0` added the same day)
- Subject: how `definitions/aarch64/0.1.0.json`, `0.2.0.json`, `0.3.0.json` and
  `0.4.0.json` were derived, and what they do and do not cover
- Basis: **experiment** for every field range, template and byte quoted below
- Reproduce:
  `python tools/check_mrs.py --archive <pinned .tar.gz>`, then
  `python research/evidence/experiments/EXP-0008/generate_aarch64.py`

The script emits all four documents. `0.1.0`, `0.2.0` and `0.3.0` are frozen and
their digests are asserted by the script, so a later edit that tries to move one
fails instead of shipping. A form declares the version it starts in (`since`), so
a later document is always a superset and cannot lose an earlier row.

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

The ten nodes are named exactly as the MRS names them. The generator walks
`instructions` recursively, matches the node's `name`, rejects duplicates and
refuses to run if any node is missing. It does not read aliases, groups or
descriptions.

## 2. The MRS nodes and their encode fields

`start+width` counts from bit 0 of the 32-bit word. `value` is the MRS
`encoding.values[].value` string; `x` means the bit is an operand, `0`/`1` means
the node fixes it.

### `ADD_64_addsub_shift` → `aarch64:add/x64-x64-x64-lsl0`

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed |
| `op` | 30+1 | `0` | fixed |
| `S` | 29+1 | `0` | fixed |
| `op1` | 28+1 | `0` | fixed |
| — | 25+3 | `101` | fixed |
| — | 24+1 | `1` | fixed |
| `shift` | 22+2 | `xx` | **pinned to `00` (LSL)** |
| — | 21+1 | `0` | fixed |
| `Rm` | 16+5 | `xxxxx` | slot `src2` |
| `imm6` | 10+6 | `xxxxxx` | **pinned to `000000`** |
| `Rn` | 5+5 | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

The MRS leaves `shift` and `imm6` variable because the same node encodes all
shifted-register forms. v0 has one row, `LSL #0`; the name says so and nothing
shifts implicitly (`INV-02`).

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

The five load/store nodes each leave exactly one field variable (`imm12` or
`imm9`), so a row is the node plus the unit its field counts. That is why the
kind cannot be an operand value: choosing between these nodes changes the
opcode bits *and* the offset field width (`EXP-0015` §1–§2, ADR-0013). Only these
five nodes are read; `LDR_64_ldst_regoff`, `LDR_64_loadlit` and the three `imm9`
store nodes are absent from the table, so naming one is `E-FORM-001`.

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

Templates are stored little-endian, the only byte order v0 definitions declare
(`07_definition_format.md` §4.1).

## 4. Oracle

`llvm-mc` 23.1.2 assembles all eleven forms. It does **not** resolve AArch64
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
is an immediate, so there is no relocation in the first place.

The seven positive fixtures are:

| Fixture | Document | Bytes | What it proves |
|---|---|---|---|
| `A64-P1-add-register` | `0.1.0` | `2000028b c500078b 20001f8b` | three register triples, including `Rm = 31` (`xzr`) |
| `A64-P2-add-imm12` | `0.1.0` | `20000091 62fc3f91` | both ends of the unsigned imm12 range |
| `A64-P2-add-imm12-lsl12` | `0.2.0` | `20044091 208c4491 62fc7f91 20004091` | `sh = 1` with field content 1, 291, 4095 and 0 |
| `A64-P3-ldst-addressing` | `0.4.0` | `200040f9 62fc7ff9 a48c40f8 e6845ff8 280150f8 6a0100f9` | `imm12` at 0 and 4095, pre-index +8, post-index −8, `ldur` at −256, store at 0 |
| `A64-P4-b-cond` | `0.3.0` | `20000054 e1ffff54 ccffff54` | three conditions (0, 1, 12) and three displacements (+4, −4, −8) |
| `A64-P5-bl-local-symbol` | `0.1.0` | `01000094 ffffff97` | `bl` +4 and −4, resolved by the linker |
| `A64-P6-adrp-lo12-pair` | `0.1.0` | `…b0000000 91002000` at `0xff8`/`0xffc` | `adrp` split field plus the paired `add` |

These were checked against our materializer, not generated by it
(`AGENTS.md` rule 5). The materializer reproduces all seven byte-for-byte and the
eleven negative fixtures (`N01`, `N01b`, `N03`, `N03-cond`, `N03-imm12-disp`,
`N03-imm9-disp`, `N04c`, `N12a`, `N14`, `N18a`, `N18b`) reject exactly the
registered diagnostic sets. `N18a`/`N18b` are the scaled form's other half: the
first is `0x1000` stated on `-lsl0`, the second `0x123000` on `-lsl12`, and both
must be `E-RANGE-001` instead of a form switch or a pre-scale. `N03-cond` is
`cond = 16` and `N04c` is `imm19 = 262144`: the first would mask to `eq` if it
were truncated, the second is the first value past the signed field, and both
must be rejected rather than repaired. `N03-imm12-disp` and `N03-imm9-disp` are
the load/store ranges (`4096` and `−257`), and `N01b` is the register-offset
kind that has no row: `E-FORM-001`, not a reinterpreted load.

## 5. What this record does not claim

- **Not exhaustive coverage of the nodes.** The table exercises the register and
  immediate fields at range ends, but it does not enumerate all 2^5 × 2^5 × 2^5
  register triples, nor every `bl`, `b.cond` or load/store displacement.
  `EXP-0004` did that for the seven x86 rows; this slice has eleven rows and
  seven positive fixtures, and `EXP-0014` §2 enumerates the sixteen condition
  values but not their products with the 2^19 displacements; `EXP-0015` §2
  measures both ends of `imm12` and `imm9` but not every value in between.
- **Not a statement about the other packagings.** Only the archive pinned by
  ADR-0006 was read (`EXP-0006`, `EXP-0007`).
- **Not an encoding-selection mechanism.** Ten MRS nodes are read because eleven
  forms exist in the table (`ADD_64_addsub_imm` is read twice). The generator is
  disposable research tooling; the materializer never reads MRS data, never looks
  a mnemonic up, and only resolves the exact `form_id` a plan names.
- **`A64-P7` and `A64-P8` are absent.** Naming them is `E-FORM-001`. The scaled
  `add`, `b.cond` and load/store rows are no longer in this list: the first is a
  row in `0.2.0` (ADR-0011), the second a row in `0.3.0` (ADR-0012), and the last
  five are rows in `0.4.0` (ADR-0013), none of them a slot-level scaling rule or
  a value-driven form choice.
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
```

The digests are computed over the canonical form of each whole document
(`01_contract.md` §12, `OD-06`) and printed by `tools/check_definition.py`,
which also checks that the reading-aid table in `07_definition_format.md` §8.2
matches the JSON row by row. `definitions/aarch64/NOTICE` reproduces the upstream
BSD-3-Clause notice and names the archive hash; `0.2.0`, `0.3.0` and `0.4.0` need
no second notice because they are generated from the same drop and ship under the
same terms.

Because `0.3.0` repeats all five earlier rows verbatim, the only difference from
`0.2.0` is the added `b.cond` row; because `0.4.0` repeats all six earlier rows
verbatim, the only difference from `0.3.0` is the five load/store rows. The
generator's frozen-digest assertions are what prove that no earlier row moved
while a new one landed.
