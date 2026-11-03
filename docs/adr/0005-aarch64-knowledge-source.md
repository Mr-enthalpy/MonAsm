# ADR-0005: AArch64 knowledge comes from the Arm MRS, not from XirAsm or LLVM

- Status: accepted
- Date: 2026-11-04
- Settles: OD-07
- Supersedes: none
- Superseded by: none

## Context

`OD-07` asks where AArch64 encoding knowledge comes from. The candidates were
re-deriving from the ISA manual, extracting XirAsm's generated Meta-DSL, or
extracting LLVM TableGen.

`90_boundary_audit.md` F-12 measured that XirAsm has no AArch64 library entry
point: `include/arm/a64.inc` is eight `import(...)` lines and the real content is
a 40.88 MB interpreted Meta program. That program cannot be linked into a
materializer that must satisfy `INV-05` (no hidden state) and `INV-06` (no
metaprogramming).

F-13 found the knowledge source behind it: the **Arm Architecture Machine
Readable Specification, 2026-06**. The generated A64 directory carries Arm's
notice and an MPL-2.0 file. Which files fall under which licence was the open
question.

The two NOTICE files in the snapshot
(`research/external/XirAsm/include/arm/a64/generated/NOTICE` and
`.../generated/latest/NOTICE`) answer that question:

- The source inventory and encoding mappings use the Arm MRS 2026-06, and "the
  upstream data carries the following notice" — a three-clause BSD notice,
  "Copyright 2010-2026 Arm Limited or its affiliates", with the standard
  source/binary retention conditions and disclaimer.
- MPL-2.0 is scoped explicitly, not left to inference: "Operand translation
  rules are adapted from dynasm-rs, under MPL-2.0", and the adapted files are
  enumerated (`tools/arm64/normalize_a64.py`, `normalize_a64_e5.py`,
  `b4_rules.py`, `extension_rules.py`, `e5_rules.py`, and the `rules/*.json`
  ranges).

So the data and the adaptation scripts are different works under different
licences. Only the data is needed for a definition table.

## Decision

1. **The knowledge source is the Arm Architecture Machine Readable
   Specification, 2026-06.** AArch64 encoding facts are taken from the MRS data,
   not from XirAsm's Meta program and not from LLVM TableGen. LLVM remains an
   oracle (`llvm-mc`), never a source of the table.
2. **No XirAsm file is copied into the product.** `definitions/aarch64/*.json`
   is generated from MRS data by a tool we own. `prototype/`, `definitions/` and
   `tools/` must not contain an MPL-2.0 file, and the product build must not read
   `research/external/` or `tools/oracle/`.
3. **Attribution travels with the data.** Every file that redistributes MRS
   data, and every distributed binary that embeds a generated table, reproduces
   Arm's copyright notice, the three conditions and the disclaimer. A short
   `NOTICE` next to `definitions/aarch64/` carries it; if a table is embedded
   with `include_str!`, the same notice ships with the binary's documentation.
   This is condition 1 (source) and condition 2 (binary) of the notice, not a
   courtesy.
4. **The generated table is data, not code.** It contains no scripts, callbacks,
   macros or expressions, consistent with `07_definition_format.md` and
   `INV-06`. The generator is a disposable research tool; the shipped artifact
   is the JSON document plus its digest.
5. **The AArch64 slice is the verification, not a condition of the source
   decision.** `A64-P1` (`add`), `A64-P5` (`bl`) and `A64-P6` (`adrp` +
   `add #:lo12:`) must reproduce `llvm-mc` bytes from the generated table before
   the table is called frozen. Until then the table is an experiment, not a
   product definition.

## Consequences

- `research/external/` stays disposable. Deleting it removes the licence
  evidence and XirAsm, but not any product file or build step.
- The MPL-2.0 obligation is avoided by construction: we do not copy the adapted
  operand-translation scripts, so there is no file-level copyleft in the
  product. If a future slice needs one of those rules, it is re-derived from the
  MRS data and the derivation is recorded; importing the script itself would
  require a new ADR that accepts the MPL-2.0 file and keeps it in a disposable
  zone.
- The repository is Apache-2.0. The Arm BSD-3-Clause data is compatible: it is
  included with its own notice, not relicensed.
- AArch64 `EC-*` rows can now name the MRS node that supplies each fact, so a
  definition row can be traced to its source without a reverse lookup into
  XirAsm's generated program.

## Alternatives considered

- **Extract XirAsm's generated Meta-DSL.** Rejected. The generated `.inc` files
  are a 40.9 MB program, not a table, and their semantics live in an interpreter
  (`F-12`). Copying them would import both the Meta layer and an execution model
  the materializer is forbidden to have.
- **Extract LLVM TableGen.** Rejected as a *source*, retained as an oracle.
  TableGen describes LLVM's instruction-selection world (patterns, predicates,
  multiclasses); flattening it into our `form_id` surface is a translation with
  its own decisions, and the result would inherit LLVM's choices rather than the
  ISA's. `llvm-mc` output is still used to check bytes.
- **Re-derive from the prose ISA manual only.** Rejected as the primary path. It
  is possible but slow and error-prone for 4,000+ instruction nodes; the MRS is
  the same knowledge in machine-readable form under a permissive notice.
- **Copy the MRS data into the repository as-is.** Rejected. The product needs a
  small, versioned form table with our `form_id` names, not the full MRS
  inventory; copying the inventory would make the digest cover data no plan can
  name.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| XirAsm has no AArch64 library entry point; A64 is a Meta program | `90_boundary_audit.md` F-12, read from source | high |
| The A64 data derives from Arm MRS 2026-06 | both `NOTICE` files, read | high |
| The data is under a three-clause BSD notice | `NOTICE` lines 4–27, read | high |
| MPL-2.0 covers the enumerated adaptation scripts, not the `.inc` data | `NOTICE` lines 29–31, read | high |
| Arm's download/website terms match the reproduced notice | not read; the notice is the only upstream text in the snapshot | **unverified** |

The last row is the residual risk. Before a table is published outside this
repository, the MRS archive's own licence file is read and compared with the
notice above. If they differ, this ADR is revisited rather than silently
reinterpreted.

## Review triggers

- The MRS release changes year or the notice changes text.
- A slice needs one of the enumerated MPL-2.0 adaptation scripts.
- A generated table is embedded in a distributed binary whose documentation
  does not carry the notice.
- The AArch64 slice cannot reproduce an oracle byte from the MRS data.
