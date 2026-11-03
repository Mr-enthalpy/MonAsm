# EXP-0009 — the UDB resolved spec states the RV64 scatter, riscv-opcodes does not

- Date: 2026-11-04
- Subject: which source pins the RV64 encoding facts, and whether it states the
  B-type/J-type/RVC bit scatter
- Basis: **experiment** for every size, hash, quoted line and byte string below
- Reproduce: `python research/evidence/experiments/EXP-0009/rv64_fields.py` and
  `python tools/check_rv64_source.py`
- Decides: `OD-12` (ADR-0007)

## 1. Why this experiment exists

The RV64 slice needs, for each form, the fixed bits and the field positions of
its operands. For `beq`, `jal` and `c.addi` the immediate is not a contiguous
field: the value bits are scattered across the instruction word and scaled. That
scatter is exactly the fact `RV-P4`/`P5`/`P6` exist to pin, so the source
decision turns on whether the candidate states it.

Two candidates were measured:

- `riscv/riscv-opcodes`, the long-standing encoding enumeration, BSD-3-Clause;
- the `resolved_spec` export of `riscv/riscv-unified-db` (UDB), supplied by the
  project owner as `C:\Users\hanni\Downloads\resolved_spec.tar.gz`.

The measurement below is the reason ADR-0007 pins the second and keeps the first
as an independent cross-check.

## 2. The archive that was read

```text
file   C:\Users\hanni\Downloads\resolved_spec.tar.gz
size   2694443
sha256 be184986ce3c0cacdf06d975de92aa8948b1a9a267a1c9d75d60afa285bd828f
```

Extracted into the disposable drop point `research/external/rv64-udb/`:

```powershell
tar -xzf C:\Users\hanni\Downloads\resolved_spec.tar.gz -C research\external\rv64-udb
```

Measured contents:

| Measure | Value |
|---|---|
| Archive entries (`tar -tzf`) | 2506 |
| Extracted files | 2398 |
| Extracted bytes | 34156409 |
| Instruction nodes (`inst/<EXT>/*.yaml`) | 1397 |
| Extension directories under `inst/` | 69 |
| `gen/resolved_spec/_/.stamp` | present, **0 bytes** |
| Licence file in the archive | **absent** |

The archive is a build artifact: every instruction node ends with a
`$source: /home/runner/work/riscv-unified-db/riscv-unified-db/gen/spec/_/...`
path, which shows a GitHub Actions workspace but records no revision. The
`.stamp` file that could have carried one is empty. **The UDB commit this
archive was generated from is therefore `unverified`**, and the pin in ADR-0007
is by archive and file hashes, not by revision.

## 3. Licence: BSD-3-Clause-Clear, declared per file

The archive carries no `LICENSE` file (measured above), so the licence evidence
is the per-file SPDX header. Every instruction node read below begins with:

```text
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
```

The identifier is not an inference from a badge: it is the first two lines of
each of the eight files in §4.

The canonical text was taken from the UDB repository, because the archive omits
it:

```text
url    https://raw.githubusercontent.com/riscv/riscv-unified-db/main/LICENSE-BSD-3-Clause-Clear.txt
size   1700
sha256 e3f4d72ac78db3ee135dc76442e165e75f644ed93dfc4103acce65e9d7af8f4d
```

Its first lines:

> SPDX-License-Identifier: BSD-3-Clause-Clear
>
> Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.

`LICENSES/BSD-3-Clause-Clear.txt` in that repository is a symlink whose content
is `../LICENSE-BSD-3-Clause-Clear.txt`; the 1,700-byte file above is the target.
UDB's `REUSE.toml` assigns `BSD-3-Clause-Clear` to UDB code and `spec/schemas/**`,
which agrees with the per-file headers. This is **source** evidence for the
licence of the eight nodes; it says nothing about parts of UDB not read here.

`definitions/rv64/NOTICE` reproduces the text and names the archive hash;
`tools/check_rv64_source.py` verifies both.

## 4. The eight instruction nodes, and the facts they state

| Node | Size (B) | SHA-256 | Read for |
|---|---|---|---|
| `inst/I/add.yaml` | 5484 | `f0c718f33b5394eaa7f3828bc02fbeb8fed0a5dca0d21e9b30fa16662f8b4812` | `RV-P1` |
| `inst/I/addi.yaml` | 5475 | `f8f3099bbbde3120a7d7c796debe3ab30a42f195849208713139f9f3a525e8a6` | `RV-P2` |
| `inst/I/ld.yaml` | 27033 | `a2afcd44fd54f5de7a9a9226f66f273b92c4e868a3519782a06c0f0fe3cc4c35` | `RV-P3` |
| `inst/I/sd.yaml` | 26947 | `f0b69996f811f7ae206f9219cf6057318eb908d6f04af70e83e403606c71390e` | `RV-P3` |
| `inst/I/beq.yaml` | 7846 | `bb8084dbfb7b4a88f9f42e49f316702f39b435576000d3b4d4299212abb3ee40` | `RV-P4`, `RV-P6` |
| `inst/I/jal.yaml` | 6524 | `3028bcf4bfefca77a50a4bf1bd27353c2d817abac58235af0745b1bfb739ac3e` | `RV-P5`, `RV-P6` |
| `inst/I/auipc.yaml` | 4585 | `e1cfdacb153cdcbc2d89c1f65005279bb2aa8cde2e30856223886105f6979fa8` | `RV-P8` |
| `inst/C/c.addi.yaml` | 8225 | `584daae38d4e830b88be6474f5420d39d858a6c1ca94acd70ce4f5c300348e75` | `RV-P7` |

Quoted verbatim, with `operation()` and `operation_ast` omitted: those are an
executable model, not an encoding fact, and ADR-0007 does not read them.

```yaml
# add
encoding:
  match: "0000000----------000-----0110011"
  variables:
    - name: xs2
      location: 24-20
    - name: xs1
      location: 19-15
    - name: xd
      location: 11-7

# addi
encoding:
  match: "-----------------000-----0010011"
  variables:
    - name: imm
      location: 31-20
      sign_extend: true
    - name: xs1
      location: 19-15
    - name: xd
      location: 11-7

# ld, RV64 block (the file also carries an RV32/Zilsd block)
  RV64:
    match: -----------------011-----0000011
    variables:
      - name: imm
        location: 31-20
        sign_extend: true
      - name: xs1
        location: 19-15
      - name: xd
        location: 11-7

# sd, RV64 block
  RV64:
    match: -----------------011-----0100011
    variables:
      - name: imm
        location: "31-25|11-7"
        sign_extend: true
      - name: xs2
        location: 24-20
      - name: xs1
        location: 19-15

# beq
encoding:
  match: "-----------------000-----1100011"
  variables:
    - name: imm
      location: "31|7|30-25|11-8"
      left_shift: 1
      sign_extend: true
    - name: xs2
      location: 24-20
    - name: xs1
      location: 19-15

# jal
encoding:
  match: "-------------------------1101111"
  variables:
    - name: imm
      location: "31|19-12|20|30-21"
      left_shift: 1
      sign_extend: true
    - name: xd
      location: 11-7

# auipc
encoding:
  match: "-------------------------0010111"
  variables:
    - name: imm
      location: 31-12
      left_shift: 12
      sign_extend: true
    - name: xd
      location: 11-7

# c.addi
encoding:
  match: "000-----------01"
  variables:
    - name: imm
      location: "12|6-2"
      not: 0
      sign_extend: true
    - name: xd
      location: 11-7
      not: 0
```

`ld` and `sd` also carry `RV32` blocks, and there `xd`/`xs2` list a `not:` set of
odd register numbers (the `Zilsd` even-pair rule). The RV64 block has no such
constraint, which is why the slice reads the RV64 block and not the RV32 one.

## 5. What `location` means, and the placements it derives

`location` is a `|`-separated list of instruction bit groups, **most
significant group first**. Each group is `hi-lo` (or a single bit). The value's
bits are assigned from its most significant bit downwards, one group at a time,
and within a group the group's MSB lands on instruction bit `hi`.

So `"31|7|30-25|11-8"` (12 bits) is: value bit 11 → bit 31, bit 10 → bit 7,
bits 9..4 → bits 30..25, bits 3..0 → bits 11..8. That is the B-type scatter, and
it is stated, not inferred.

`fmp-def/0.1` spells the same fact as `{bit_offset, width}` placements whose
`bit_offset` is the group's `lo` and whose order is value order (§4.1 of
`07_definition_format.md`). The probe derives them mechanically:

| Node | Variable | Placements |
|---|---|---|
| `add` | `xd`, `xs1`, `xs2` | `[7,5]`, `[15,5]`, `[20,5]` |
| `addi` | `xd`, `xs1`, `imm` | `[7,5]`, `[15,5]`, `[20,12]` |
| `ld` | `xd`, `xs1`, `imm` | `[7,5]`, `[15,5]`, `[20,12]` |
| `sd` | `xs2`, `xs1`, `imm` | `[20,5]`, `[15,5]`, `[25,7]`, `[7,5]` |
| `beq` | `xs1`, `xs2`, `imm` | `[15,5]`, `[20,5]`, `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` |
| `jal` | `xd`, `imm` | `[7,5]`, `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]` |
| `auipc` | `xd`, `imm` | `[7,5]`, `[12,20]` |
| `c.addi` | `xd`, `imm` | `[7,5]`, `[12,1]`, `[2,5]` |

`left_shift` is a property of decoding, not of the field: `beq`/`jal` store
`offset >> 1`, `auipc` stores `offset >> 12`. A definition slot has no scaling
transform (`07_definition_format.md` §8.3), so the slot holds **field content**
and a byte offset is expressed with a fixup whose `transform_shift` equals
`left_shift`. The probe prints both numbers for every branch vector so the
relation is visible in the record, not assumed.

## 6. The oracle check

`llvm-mc 23.1.2`, `-triple=riscv64`; `c.addi` additionally needs `-mattr=+c`
(without it the assembler reports "instruction requires the following: 'C'
(Compressed Instructions) or 'Zca'", measured here):

```text
add a0, a1, a2      -> 33 85 c5 00
addi a0, a1, 1      -> 13 85 15 00
addi a0, a1, -1     -> 13 85 f5 ff
addi a0, a1, 2047   -> 13 85 f5 7f
addi a0, a1, -2048  -> 13 85 05 80
ld a0, 8(a1)        -> 03 b5 85 00
ld a0, -8(a1)       -> 03 b5 85 ff
sd a0, 8(a1)        -> 23 b4 a5 00
beq a0, a1, 8       -> 63 04 b5 00
beq a0, a1, -8      -> e3 0c b5 fe
jal ra, 8           -> ef 00 80 00
jal ra, -8          -> ef f0 9f ff
auipc a0, 1         -> 17 15 00 00
c.addi a0, 1        -> 05 05   (-mattr=+c)
```

`rv64_fields.py` encodes all fourteen from the §4 fields and compares. Result:

```text
OK: 14 positive vectors and 2 negative cases agree with llvm-mc 23.1.2
```

Two negative cases exercise the `not: 0` constraint the source states:
`c.addi a0, 0` and `c.addi x0, 1` are rejected. They are not an oracle check —
`llvm-mc` accepts both and silently emits HINTs (`c.addi a0, 0` → `01 05`,
`c.addi x0, 1` → `05 00`, printed as `c.nop 1`) — they show what the source
forbids and what our slot model cannot yet say (ADR-0007 §Decision 5).

The derived placements were produced before the oracle comparison and then used
unchanged; the agreement is two independent sources (UDB `location` versus
`llvm-mc` bytes), not a table checked against itself.

## 7. Why riscv-opcodes is the cross-check and not the source

Measured on the clone at commit `f24ac23ec9fa947011781a09cd6fd25a7c36dc45`
(2026-10-14):

| File | Size (B) | SHA-256 |
|---|---|---|
| `LICENSE` | 1504 | `ea19b7489bc6e36af15e895abe86ce0941a09fbbca34e4a47cb217621fae1ed2` |
| `arg_lut.csv` | 2119 | `400ae2948def97759ae839d9e76a8cc6827d54ea1b8e84107382b34d60fc6bb5` |
| `extensions/rv_i` | 4491 | `ed0938fb66af33acd028664e0c284568b0d3881f2a818499000bfb3e78eb3b56` |
| `extensions/rv64_i` | 969 | `308518bd771c513362132eb869228cb79cdce91cc42a6523f415a049e9a0a319` |
| `extensions/rv_c` | 1527 | `323d749038899892ef2dc6d55cec0cd45901439d070e7083855a7c874e0ed94a` |

The relevant lines:

```text
beq     bimm12hi rs1 rs2 bimm12lo 14..12=0 6..2=0x18 1..0=3
jal     rd jimm20                          6..2=0x1b 1..0=3
c.addi  rd_rs1_n0 c_nzimm6lo c_nzimm6hi    1..0=1 15..13=0

"bimm12hi", 31, 25
"bimm12lo", 11, 7
"jimm20", 31, 12
"c_nzimm6lo", 6, 2
"c_nzimm6hi", 12, 12
```

`arg_lut.csv` gives **ranges**, not the value-bit split: `bimm12hi` is "bits
31..25", `bimm12lo` is "bits 11..7", and nothing in the repository says that the
7-bit field at 31..25 holds `imm[12]|imm[10:5]` or that the 5-bit field at 11..7
holds `imm[4:1]|imm[11]`. Encoding a contiguous 12-bit value into those two
ranges produces different bytes (for `beq a0,a1,8`, `imm=8` would set bit 3 of
the high range instead of bit 11:8 of the low one). The same gap exists for
`jimm20` (`31..12` holds `imm[20|10:1|11|19:12]`) and `c_nzimm6hi/lo` (the high
field is one bit, `imm[5]`).

So riscv-opcodes cannot supply the fact that `RV-P4`/`P5`/`P6` are about. It is
still useful: UDB's README states "Instruction encodings are validated to match
riscv-opcodes", and the two sources agree on the fixed bits and register fields
measured above. ADR-0007 keeps it as a cross-check and records how to re-read it;
it is not a build input.

## 8. UDB's own status caveat

UDB's `README.adoc` says, in a warning block:

> This project is under rapid development. Expect schemas and APIs to change.
>
> The data in the `spec` directory is also a work in progress and may be
> incorrect.
>
> That said, the following data has been validated against third-party sources:
> * Instruction encodings are validated to match riscv-opcodes

That is a reason to check every form against `llvm-mc` before the table is
called frozen (the two-source rule), not a reason to reject the source: the
scatter is stated explicitly, the fixed bits agree with riscv-opcodes, and the
oracle agrees byte for byte on all fourteen vectors.

## 9. What this settles, and what it does not

Settled by measurement:

- The archive is identified by `sha256:be184986…`; `check_rv64_source.py` gates
  the eight nodes above by size and hash and by their SPDX header.
- The B/J/RVC scatter and the `left_shift` scaling are stated by the source and
  reproduce `llvm-mc` bytes exactly (`RV-P4`/`P5`/`P7` on this evidence only; no
  table or fixture exists yet).
- riscv-opcodes does not state the scatter, so it cannot be the source for those
  rows.

Not settled:

- **The UDB revision.** The archive records no commit; `.stamp` is empty and the
  `$source` map names only the CI workspace. `unverified`.
- **Relocation pairing.** `auipc` + `lo12` (`RV-P8`) needs the psABI's
  `R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I` relation, which is not in the
  resolved spec's encoding blocks. That needs its own pinned psABI evidence
  before `RV-P8`.
- **Non-zero constraints.** `not: 0` on `c.addi`'s `imm` and `xd` has no
  representation in `fmp-def/0.1`. `c.addi` stays out of the v0 surface until a
  format decision adds a closed non-zero constraint and an error code.
- **Whether UDB is right for every future row.** Only eight nodes were read; a
  later slice re-reads the source and extends the pin, or lands a new ADR.

## 10. Reproduction

```powershell
tar -tzf C:\Users\hanni\Downloads\resolved_spec.tar.gz | Measure-Object
tar -xzf C:\Users\hanni\Downloads\resolved_spec.tar.gz -C research\external\rv64-udb
$env:PYTHONIOENCODING="utf-8"
python research\evidence\experiments\EXP-0009\rv64_fields.py
python tools\check_rv64_source.py --archive C:\Users\hanni\Downloads\resolved_spec.tar.gz
```

`research/external/rv64-udb/` is gitignored and deletable; the pin lives in
`source_index.md`, ADR-0007 and `tools/check_rv64_source.py`.
