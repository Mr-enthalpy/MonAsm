# EXP-0008 — generating the AArch64 table from four MRS nodes

- Date: 2026-11-04
- Subject: how `definitions/aarch64/0.1.0.json` was derived, and what it does and
  does not cover
- Basis: **experiment** for every field range, template and byte quoted below
- Reproduce:
  `python tools/check_mrs.py --archive <pinned .tar.gz>`, then
  `python research/evidence/experiments/EXP-0008/generate_aarch64.py`

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

The four nodes are named exactly as the MRS names them. The generator walks
`instructions` recursively, matches the node's `name`, rejects duplicates and
refuses to run if any node is missing. It does not read aliases, groups or
descriptions.

## 2. The four nodes and their encode fields

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

### `ADD_64_addsub_imm` → `aarch64:add/x64-imm12-lsl0`

| Field | start+width | MRS value | Our use |
|---|---|---|---|
| `sf` | 31+1 | `1` | fixed |
| `op` | 30+1 | `0` | fixed |
| `S` | 29+1 | `0` | fixed |
| — | 26+3 | `100` | fixed |
| — | 23+3 | `010` | fixed |
| `sh` | 22+1 | `x` | **pinned to `0` (no LSL #12)** |
| `imm12` | 10+12 | `xxxxxxxxxxxx` | slot `imm`, unsigned |
| `Rn` | 5+5 | `xxxxx` | slot `src` |
| `Rd` | 0+5 | `xxxxx` | slot `dest` |

The `-lsl12` half of `A64-P2` would need `sh = 1` with the immediate scaled by
4096. A definition slot has no scaling transform (`07_definition_format.md`
§8.3), so that form is deliberately absent rather than approximated.

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

## 3. How the template is built

For each node the generator:

1. classifies every encode field as *fixed* (value string over `{0,1}`) or
   *variable* (value string all `x`); a field mixing the two is a hard error;
2. ORs the fixed values in at their `start` positions;
3. requires every name in `pinned_zero` to be present **and** variable — pinning
   a bit the MRS already fixes would hide a decision rather than state one;
4. derives each slot's placements from the MRS field ranges, so a wrong bit
   position is a mismatch, not a typo;
5. checks that the slot's placement widths sum to its declared `range.bits`;
6. checks that every one of the 32 bits is owned exactly once by a fixed bit, a
   pinned bit, or one slot placement, and that no two owners overlap.

Any failure aborts before the file is written. The output therefore cannot
contain an uncovered bit, a doubly-written bit, or a placement the MRS does not
have.

The generated templates are:

| Form | Template (file order) | Word (disassembler order) |
|---|---|---|
| `aarch64:add/x64-x64-x64-lsl0` | `0000008b` | `0x8b000000` |
| `aarch64:add/x64-imm12-lsl0` | `00000091` | `0x91000000` |
| `aarch64:bl/imm26` | `00000094` | `0x94000000` |
| `aarch64:adrp/x64-imm21` | `00000090` | `0x90000000` |

Templates are stored little-endian, the only byte order v0 definitions declare
(`07_definition_format.md` §4.1).

## 4. Oracle

`llvm-mc` 23.1.2 assembles all four forms. It does **not** resolve AArch64
branches or `adrp`: it emits zeros plus `fixup_aarch64_pcrel_call26`,
`fixup_aarch64_pcrel_adrp_imm21` or `fixup_aarch64_add_imm12`. For the two forms
whose bits a fixup owns, the oracle is therefore the LLVM toolchain's own
resolution:

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

The four fixtures are:

| Fixture | Bytes | What it proves |
|---|---|---|
| `A64-P1-add-register` | `2000028b c500078b 20001f8b` | three register triples, including `Rm = 31` (`xzr`) |
| `A64-P2-add-imm12` | `20000091 62fc3f91` | both ends of the unsigned imm12 range |
| `A64-P5-bl-local-symbol` | `01000094 ffffff97` | `bl` +4 and −4, resolved by the linker |
| `A64-P6-adrp-lo12-pair` | `…b0000000 91002000` at `0xff8`/`0xffc` | `adrp` split field plus the paired `add` |

These were checked against our materializer, not generated by it
(`AGENTS.md` rule 5). The materializer reproduces all four byte-for-byte and the
four negative fixtures reject exactly the registered diagnostic sets.

## 5. What this record does not claim

- **Not exhaustive coverage of the nodes.** The table exercises the register and
  immediate fields at range ends, but it does not enumerate all 2^5 × 2^5 × 2^5
  register triples, nor every `bl` displacement. `EXP-0004` did that for the
  seven x86 rows; this slice has four rows and four fixtures.
- **Not a statement about the other packagings.** Only the archive pinned by
  ADR-0006 was read (`EXP-0006`, `EXP-0007`).
- **Not an encoding-selection mechanism.** Four MRS nodes are read because four
  forms exist in the table. The generator is disposable research tooling; the
  materializer never reads MRS data, never looks a mnemonic up, and only resolves
  the exact `form_id` a plan names.
- **`A64-P3`, `A64-P4`, `A64-P7`, `A64-P8` and `-lsl12` are absent.** Naming them
  is `E-FORM-001`. The missing piece for `-lsl12` is a slot-level scaling
  decision, which is a format change with its own ADR, not a generator tweak.

## 6. Result

```text
definition  definitions/aarch64/0.1.0.json
namespace   monasm.isa.aarch64
version     0.1.0
forms       4
digest      sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e
```

The digest is computed over the canonical form of the whole document
(`01_contract.md` §12, `OD-06`) and printed by `tools/check_definition.py`,
which also checks that the reading-aid table in `07_definition_format.md` §8.2
matches the JSON row by row. `definitions/aarch64/NOTICE` reproduces the upstream
BSD-3-Clause notice and names the archive hash.
