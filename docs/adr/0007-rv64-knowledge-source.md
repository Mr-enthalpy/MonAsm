# ADR-0007: RV64 knowledge comes from the UDB resolved spec, pinned by archive hash

- Status: accepted
- Date: 2026-11-04
- Settles: `OD-12` (where RV64 encoding knowledge comes from)
- Supersedes: none
- Superseded by: none

## Context

`OD-12` asks where the RV64 encoding facts come from. The directive's §6.3
requires eight things of the slice: integer arithmetic, I-type immediates,
load/store, conditional branches, `jal`, scattered bit fields, RVC versus
standard forms, and an `auipc` + `lo12` associated reference. Six of those need
field positions; three of them (`beq`, `jal`, `c.addi`) have immediates whose
value bits are **not contiguous** in the instruction word.

The first candidate was `riscv/riscv-opcodes`: small, stable, machine-readable,
BSD-3-Clause. `EXP-0009` §7 measured it and found the gap that decides this ADR.
`arg_lut.csv` gives ranges — `"bimm12hi", 31, 25`, `"bimm12lo", 11, 7`,
`"jimm20", 31, 12`, `"c_nzimm6hi", 12, 12`, `"c_nzimm6lo", 6, 2` — and the
extension line names the fields:

```text
beq     bimm12hi rs1 rs2 bimm12lo 14..12=0 6..2=0x18 1..0=3
```

Nothing in the repository says which immediate bits go in which part of those
fields. The 7-bit field at 31..25 holds `imm[12]|imm[10:5]`, the 5-bit field at
11..7 holds `imm[4:1]|imm[11]`; treating the immediate as one 12-bit value across
the two ranges produces different bytes. That scatter is precisely what
`RV-P4`/`P5`/`P6` exist to pin, so riscv-opcodes cannot be the source for them.

The project owner then supplied the `resolved_spec` export of `riscv/riscv-unified-db`
(UDB). `EXP-0009` measured it:

- archive `resolved_spec.tar.gz`, `2694443` B,
  `sha256:be184986ce3c0cacdf06d975de92aa8948b1a9a267a1c9d75d60afa285bd828f`,
  2,398 files, 1,397 instruction nodes;
- `inst/I/beq.yaml` states
  `location: "31|7|30-25|11-8"` with `left_shift: 1` and `sign_extend: true`;
- `inst/I/jal.yaml` states `location: "31|19-12|20|30-21"`;
- `inst/I/auipc.yaml` states `location: 31-12` with `left_shift: 12`;
- `inst/C/c.addi.yaml` states `location: "12|6-2"` and `not: 0` on both `imm`
  and `xd`;
- every node declares `SPDX-License-Identifier: BSD-3-Clause-Clear` and
  "Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries."

`location` is the scatter, stated as a `|`-separated list of instruction bit
groups in value order. `EXP-0009` §5 turns it into `{bit_offset, width}`
placements mechanically, and §6 reproduces fourteen `llvm-mc` byte strings from
those placements with no hand-written scatter.

Two properties of the source limit what it can be trusted for, and both are
handled below rather than ignored:

1. UDB's `README.adoc` says the data "is also a work in progress and may be
   incorrect", and that instruction encodings are validated **against
   riscv-opcodes**. UDB is downstream of the upstream enumeration.
2. The archive records no revision: `.stamp` is empty and the `$source` map
   names only a CI workspace path. Packagings, not commits, are what can be
   hashed here.

## Decision

1. **The RV64 knowledge source is the UDB `resolved_spec` archive**, pinned by
   `sha256:be184986ce3c0cacdf06d975de92aa8948b1a9a267a1c9d75d60afa285bd828f`
   (`2694443` B). `definitions/rv64/` may only be generated from a drop that
   satisfies every clause below; anything else is rejected, not repaired
   (`INV-07`).
2. **Read scope is the named instruction nodes, one extension at a time.** v0
   reads `inst/I/{add,addi,ld,sd,beq,jal,auipc}.yaml` and `inst/C/c.addi.yaml`,
   all ratified. No node from an unratified extension may enter a v0 table, and
   the extensions a plan enables are still checked by the materializer, not by
   the table's presence in the directory.
3. **The facts taken are encoding facts only**: `encoding.match` (fixed bits),
   `encoding.variables[].location` (field positions), `sign_extend`,
   `left_shift`, and `not`. `operation()` and `operation_ast` are **not** read:
   they are an executable model, and a materializer that evaluated them would
   violate `INV-06`. The YAML is not copied into the product; `definitions/rv64/`
   holds derived JSON.
4. **`left_shift` is a fixup transform, never a slot transform.** UDB's
   `left_shift` describes decoding: the field holds `value >> left_shift`. A
   definition slot writes the field content it is given (`07_definition_format.md`
   §8.3), so a byte offset is expressed with a `scale` fixup whose
   `transform_shift` equals `left_shift` — 1 for `beq`/`jal`, 12 for `auipc`.
   A plan that writes a byte offset straight into the field emits a wrong
   program; it is not scaled on the plan's behalf (`INV-04`).
5. **`not: 0` is not expressible in `fmp-def/0.1`, so forms that need it stay
   out of v0.** `c.addi` requires `xd != 0` and `imm != 0`; encoding either zero
   silently produces a HINT or `c.nop`, which is a different instruction
   (`llvm-mc` does exactly that, `EXP-0009` §6). Admitting `c.addi` therefore
   needs a closed non-zero constraint in the definition format, an error code,
   a counterexample and its own ADR. Until then `RV-P7` is planned but has no
   row, and naming `riscv:c.addi/...` is `E-FORM-001`.
6. **Attribution travels with the data.** `definitions/rv64/NOTICE` reproduces
   the BSD-3-Clause-Clear text, names the archive hash and the SPDX identifier,
   and lists the nodes read. The text is pinned by
   `sha256:e3f4d72ac78db3ee135dc76442e165e75f644ed93dfc4103acce65e9d7af8f4d`
   (1,700 B, UDB `LICENSE-BSD-3-Clause-Clear.txt`), because the archive itself
   carries no licence file. This is condition 1 (source) and condition 2
   (binary) of that notice, not a courtesy.
7. **The pin is by bytes, and `check_rv64_source.py` is the gate.** It verifies
   the archive hash when named, each pinned node's size and SHA-256, each node's
   SPDX header, and the `NOTICE` body against the pinned licence text.
   `riscv-opcodes` is kept as the independent upstream cross-check; `llvm-mc` is
   the oracle. Neither is a build input.
8. **A different archive is a new decision.** If any pinned byte changes — a new
   UDB export, a different UDB commit, a re-serialisation — the gate fails and a
   new ADR must re-read the headers and state whether `definitions/rv64/` is
   regenerated. An archive that leaves all eight nodes byte-identical changes
   none of the facts the table rests on, so it needs no new ADR.
9. **The table is frozen only after the oracle check.** Every form in
   `definitions/rv64/0.1.0.json` must reproduce `llvm-mc 23.1.2` bytes from the
   generated table before it is called frozen, exactly as the AArch64 slice did
   (`EXP-0008`).

> Status note 2026-11-04: item 5's condition was met by ADR-0009. The slot-level
> `excluded` list, `E-RANGE-004` and `EXP-0012` admit `c.addi` as
> `riscv:c.addi/rd-imm6` in `definitions/rv64/0.2.0.json`, which declares
> `["rv64i","rv64c"]`; `0.1.0` keeps its seven forms and its digest. Every pinned
> byte and every fact above still holds, so this ADR is not superseded.

## Consequences

- The scatter is data. `beq`, `jal` and the RVC forms can be generated from
  `location` without a hand-written bit table, and the oracle check is a real
  second source rather than a re-run of the same numbers (`EXP-0009` §5–§6).
- `riscv-opcodes` remains useful for exactly what it does state: fixed bits and
  register ranges. It is recorded in `source_index.md` with its own hashes so a
  later slice can cross-check UDB without re-cloning.
- The RV64 table's provenance is per-node: archive hash, node hash, UDB node
  name, and the definition digest. `INV-08` replay does not depend on UDB still
  being downloadable, because the digest covers the table.
- `research/external/rv64-udb/` stays gitignored and deletable. Deleting it
  removes the ability to re-run the source gate, not any product file.
- The unknown UDB revision is an accepted, recorded risk: the pin is the bytes,
  not the commit, and the licence basis is the SPDX header on those bytes.
- Cost: a user without the archive cannot regenerate the table. Accepted — the
  shipped table plus its digest is what a plan is bound to, and the table does
  not need regeneration to be validated.
- `RV-P7` is blocked on a format decision, not on the source. That is a smaller
  and more honest blocker than encoding a form whose zero cases are illegal.

## Alternatives considered

- **`riscv-opcodes` as the source.** Rejected after measuring that it states
  field ranges but not the B/J/RVC value-bit scatter (`EXP-0009` §7). It is
  retained as an independent cross-check, and it remains the upstream that UDB
  itself validates against.
- **Read UDB's `operation()` / IDL as the encoding source.** Rejected: that is a
  semantics program, and evaluating it would put an interpreter in the
  materializer (`INV-06`). Only the `encoding` block is read.
- **Re-derive everything from the ISA manual prose.** Rejected as the primary
  path for the same reason as ADR-0005: the manual is authoritative but not
  machine-readable, and the scatter figures are exactly what a machine-readable
  source should carry. The manual remains the place to go when a source is
  ambiguous, and `llvm-mc` remains the byte oracle.
- **Check out UDB at a git commit instead of pinning the export.** Rejected for
  v0: producing `resolved_spec` needs UDB's Ruby/mise toolchain, which is
  build-time machinery this project must not depend on. The owner supplied the
  export; its bytes are what we can pin. The revision stays `unverified` and is
  recorded as such.
- **Treat `c.addi` zero cases as legal because the ISA calls them HINTs.**
  Rejected: `c.addi a0, 0` and `c.addi x0, 1` are not the instruction the plan
  named, and accepting them would make the materializer choose a different
  instruction from the plan's operands (`INV-02`, `INV-07`).
- **Copy the UDB YAML into `definitions/`.** Rejected: the product needs a small
  form table with our `form_id` names, and a copied database would make the
  digest cover data no plan can name and drag IDL text into the artifact.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The archive is `2,694,443` B and hashes to `be184986…` | `EXP-0009` §2, measured | high |
| The eight nodes state the scatter in `location` | `EXP-0009` §4, read verbatim | high |
| Fourteen vectors encoded from `location` match `llvm-mc` byte for byte | `EXP-0009` §5–§6, experiment | high |
| Each node declares `BSD-3-Clause-Clear` and the Qualcomm copyright line | `EXP-0009` §3, read | high |
| The licence text is 1,700 B and hashes to `e3f4d72a…` | `EXP-0009` §3, fetched and hashed | high |
| riscv-opcodes states field ranges but not the value-bit scatter | `EXP-0009` §7, read | high |
| UDB instruction encodings are validated against riscv-opcodes | UDB `README.adoc`, read | high |
| Which UDB commit produced the archive | no revision recorded; `.stamp` empty | **unverified** |
| The `auipc` + `lo12` relocation pairing | not in the encoding blocks; psABI evidence not yet read | **unverified** |
| Derived JSON redistributed with the notice satisfies condition 2 for an embedded binary | not tested; the JSON ships with `NOTICE` beside it | **unverified** |

## Review triggers

- A new `resolved_spec` archive is supplied, or `check_rv64_source.py` fails on
  one the user believes is correct.
- A slice needs a node outside `I`/`Zca`, or an unratified extension.
- The `not: 0` format decision lands, unblocking `RV-P7`.
- `RV-P8` needs the psABI relocation pairing pinned.
- A table is embedded in a distributed binary.
- UDB changes the SPDX header wording or the licence file.
