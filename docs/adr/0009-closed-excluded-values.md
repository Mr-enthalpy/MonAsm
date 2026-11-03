# ADR-0009: A slot may exclude values, but only a closed list of them

- Status: accepted
- Date: 2026-11-04
- Settles: `OD-14` (how a form rejects a value inside its field's range)
- Supersedes: none
- Superseded by: none

## Context

`RV-P7` (`c.addi`) has been blocked since ADR-0007 for one reason: its UDB node
states `not: 0` on two variables, and `fmp-def/0.1` models each slot's domain as
an interval (`range: {signed, bits, align_bits}`). `0` is inside `[-32, 31]`, so
no existing check can reject it.

The source is not being pedantic. Measured with `llvm-mc 23.1.2` on 2026-11-04
(`EXP-0012` §2):

| Input | Bytes | What `llvm-objdump` calls it |
|---|---|---|
| `c.addi a0, 1` | `05 05` | `c.addi a0, 0x1` |
| `c.addi a0, -32` | `01 15` | `c.addi a0, -0x20` |
| `c.addi a0, 0` | `01 05` | `c.addi a0, 0x0` |
| `c.addi x0, 1` | `05 00` | `c.nop 0x1` |
| `c.addi x0, 0` | `01 00` | `nop` |

The assembler accepts both zero cases and emits a 2-byte encoding, so a plan that
asked for "add 0 to `a0`" would be materialized as a reserved HINT rather than as
the addition it names. That is the failure `INV-07` forbids: the input is legal
syntax, illegal semantics, and the only correct answer is a rejection. `c.addi
a0, 32` is already rejected by the assembler as out of range (`[-32, 31]`), and
that path is `E-RANGE-001`, which does not apply here.

Three candidate carriers were considered.

1. **A boolean predicate (`non_zero: true`).** Covers these two slots exactly and
   nothing else. Rejected: `INV-06` forbids expression evaluation, and a named
   predicate per constraint is the same door opened one hinge at a time. The UDB
   source already uses a list for the general case — the `RV32` block of
   `ld.yaml` excludes every odd register for Zilsd — so the boolean would have to
   be replaced by a list the first time a second constraint appears.
2. **Reject at the plan level, by role.** For example "an `imm` operand of 0 in a
   C form". Rejected: legality is a property of the form, not of a role or a
   mnemonic prefix. `addi a0, a0, 0` is a perfectly legal standard instruction
   (`13 05 05 00`), so a role-level rule would either be too broad or need
   mnemonic knowledge the format does not have.
3. **A closed list of excluded values on the slot.** The slot says which exact
   values its field may not carry; everything else in `range` is legal. This is
   data, not a predicate, and the generator derives it from the source's `not:`.

## Decision

1. **A slot may declare `excluded`**: an array of integers, strictly increasing,
   each inside the slot's representable domain (`range` for `operand_value`, the
   placements' bit width for `reg_number`). It applies to both `from` modes. An
   absent key means "no value is excluded"; the generator is the only writer, and
   it already refuses a node whose `not:` it cannot express, so absence is a
   statement rather than a default.
2. **The excluded set is subtracted from the interval, not merged into it.** A
   value in `excluded` is rejected even though `range` accepts it, with
   `E-RANGE-004` and detail keys `target_type`, `value`, `excluded`. The plan
   path is the payload leaf (`/payload/value` or `/payload/reg`), so the
   diagnostic names the operand that carried the value.
3. **No predicates, ranges, or expressions in `excluded`.** Exact integers only,
   sorted by the generator. A constraint that is not a finite list stays out of
   `fmp-def/0.1`.
4. **`c.addi` is admitted in a new table version, `rv64/0.2.0.json`**, because
   the document's `enabled_extensions` is compared exactly with the plan's and
   `c.addi` requires `rv64c` (its UDB node says `definedBy: Zca`, and `ext/C.yaml`
   lists `Zca` in `C`'s requirements, so the plan token is `rv64c`). `0.1.0`
   stays base-`I` and keeps its digest; a plan that wants the compressed form pins
   `0.2.0` and declares `["rv64i","rv64c"]`. Naming `riscv:c.addi/rd-imm6`
   against `0.1.0` remains `E-FORM-001`, pinned by a fixture.
5. **The generator turns `not:` into `excluded` and refuses anything else.** A
   source `not:` entry that is not a plain integer, or a form whose `not:` is on
   a variable the slot model cannot express, fails the generator instead of
   being dropped.

## Consequences

- `RV-P7` unblocks with three new negative fixtures: `imm = 0` and `rd = 0`
  (`N16a`, `N16b`), both `E-RANGE-004` and both rejected rather than encoded as
  `c.nop`/HINT, plus `N01c`, which pins that naming the form against `0.1.0` is
  `E-FORM-001` rather than a fallback to `addi`.
- `E-RANGE-004` becomes a registered code with an observed counterexample
  (`c.addi a0, 0` → `01 05`), not a speculative branch.
- The RV64 slice grows a second definition version. That is deliberate: the
  target feature set is part of the definition's identity (`07_definition_format.md`
  §2), so widening it moves the digest, and moving an already-published digest
  would make an old plan mean something new.
- The format gains one optional slot key. Tables that need no exclusion do not
  change, and their digests do not move.
- A form can now be non-convex. The load-time checks keep the set a sorted list
  of exact values, so "legal" stays decidable by inspection and there is no
  order-dependent behaviour (`INV-05`).

## Alternatives considered

- **Widen `range` with a `min`/`max` hole.** Rejected: an interval with a hole is
  two intervals, and the plan's range check would have to know which one applies;
  the two-interval shape is not simpler than a list.
- **Model the HINT encodings as separate forms** (`riscv:c.addi.hint/...`).
  Rejected: a form is an encoding decision, and the encoding is identical. The
  plan would have to name a form whose operands contradict its name, and the
  materializer would still need a value check to know which form applies.
- **Leave `RV-P7` out of v0.** Rejected: the exclusion is now measurable, small,
  and the directive's RV64 slice explicitly asks for RVC versus standard forms.
- **Copy the UDB `not:` lists verbatim, including the Zilsd odd-register list,
  into every block.** Rejected: the generator reads the `RV64` block only
  (`EXP-0010` §3.1), so a 32-bit pairing rule must not appear in a 64-bit table.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `c.addi`'s source states `not: 0` on `imm` and `xd` | `inst/C/c.addi.yaml`, read; `EXP-0012` §2 | high |
| Zero-valued `c.addi` encodes as a HINT, not the addition | `llvm-objdump` on `01 05` / `05 00` / `01 00`, `EXP-0012` §2 | high |
| `imm` range is `[-32, 31]` | `llvm-mc` rejects `c.addi a0, 32`; `range.bits: 6, signed: true` | high |
| `excluded` cannot be expressed by any existing error path | `E-RANGE-001` reports `min`/`max` that contain 0 | high |
| The list shape generalises to Zilsd's odd-register rule | `ld.yaml` `RV32` block, read; not exercised in v0 | medium (source read, no fixture) |

## Review triggers

- A form needs an exclusion that is not a finite list (a modulo rule, a pairing
  rule between two operands). That is a new decision, not an `excluded` entry.
- The `RV64` Zilsd block is admitted: its 16-value list is the first large
  `excluded` set, and the load-time "inside the field" check must be re-read for
  a 32-bit table.
- A later format version adds slot-level transforms; `excluded` is checked
  against the pre-transform value, and that ordering would need restating.
