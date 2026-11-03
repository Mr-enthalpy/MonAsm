# EXP-0002 — expected bytes in the plan (OD-01) and the v0 output level (OD-03)

- Date: 2026-11-04
- Subject: FMP v0 contract decisions OD-01 and OD-03
- Toolchain: LLVM 23.1.2 (`llvm-mc`, `llvm-objcopy`, `llvm-readobj`), Python 3
- Basis: **experiment** for every byte and every size printed below; **inference**
  where a verdict follows from which fields a variant carries
- Reproduce: `python exp0002.py --emit` in this directory

The script assembles the sources in this directory with `llvm-mc`, reads the
bytes back with `llvm-objcopy`, and prints the relocation records with
`llvm-readobj`. Nothing in this record is transcribed: the numbers are whatever
LLVM 23.1.2 produced on the run.

## 1. The measured slice

Four x86-64 instructions, no fixups, so the size comparison answers OD-01 alone.

| Offset | Instruction | Bytes | Length |
|---|---|---|---|
| 0x00 | `mov rax, rbx` | `48 89 d8` | 3 |
| 0x03 | `add rax, 1` | `48 83 c0 01` | 4 |
| 0x07 | `add rax, 300` | `48 05 2c 01 00 00` | 6 |
| 0x0d | `mov rax, [rbp - 8]` | `48 8b 45 f8` | 4 |

Total 17 bytes (`0x11`). The script aborts if these bytes ever differ from the
table, so a toolchain change is loud rather than silent.

`add rax, 1` and `add rax, 300` are the same operation in two different forms
(`imm8`, 4 bytes; accumulator `imm32`, 6 bytes). That is `EC-01`/`EC-04` in the
slice, and it is why the slice can detect a length-changing definition drift.

## 2. OD-01 — what a plan costs in each variant

A plan file differs from an empty plan in two parts: a fixed part
(`target_identity`, `definition_identity`, `output_contract`, `provenance`, one
empty section) and the instructions. "Marginal" below is the difference, so the
fixed part cannot flatter or penalise a variant. Sizes are canonical JSON
(`sort_keys=True`, `separators=(",",":")`, UTF-8) in bytes.

| Variant | Total | Fixed | Marginal | Per instruction |
|---|---|---|---|---|
| A: form + operands + choices | 2539 | 823 | 1716 | 429.0 |
| B: A + `expected_digest` | 2907 | 823 | 2084 | 521.0 |
| C: byte template + patches | 1438 | 823 | 615 | 153.8 |

Measurement note (2026-11-04): these numbers were taken with the then-required
empty `encoding_choices` list in variants A and B. ADR-0004 removed that field,
so current canonical sizes are about 22 B per instruction smaller in both
variants; the 92-byte digest overhead and the direction of the A-vs-B comparison
are unchanged. The raw plan files here are kept as measured and are not rewritten.

Readings:

- `expected_digest` costs exactly **92 bytes per instruction** (368 / 4): 17 for
  the quoted key, 1 for its colon, 73 for `"sha256:"` plus 64 hex digits plus the
  closing quote, 1 for the comma. That is **+21.4 %** over variant A, and it is a
  constant, not a ratio that grows with operand complexity.
- Variant C is **64.2 % smaller** than A. C is cheaper because it deletes the
  fields that make validation possible, not because it encodes the same
  information more compactly. §3 shows what the deletion costs.

C also needs a different schema: `form_id`, `operands`, `encoding_choices` and
`expected_size` are replaced by `template_hex`, so every field the contract uses
for legality (`INV-01`, `INV-02`) disappears.

## 3. OD-01 — what each variant can check

| Check | A | B | C |
|---|---|---|---|
| The form exists in the pinned definition | yes | yes | no form field |
| The operands are legal for that form | yes | yes | no operand field |
| The encoded length equals the declared length | yes | yes | the length *is* the template |
| The encoded bits equal an independent expectation | no | yes | the template *is* the expectation |

## 4. OD-01 — fault matrix

Each row takes one realistic fault and shows the byte string it produces. The
right-hand column is the disassembly of those bytes, produced live by
`llvm-mc -disassemble`: the wrong output is a *legal instruction*, which is what
makes it dangerous.

### W1 — definition drift that changes length

The `imm8` form disappears from the definition; the same plan encodes through
the accumulator form.

```text
intended   48 83 c0 01          4 B    add rax, 1
produced   48 05 01 00 00 00    6 B    add rax, 1
```

Both are correct encodings of the same operation. The plan's layout was built
for 4 bytes.

W1 presumes the definition digest did not change: either the drift is one the
digest does not cover — which is what `OD-06` has to prevent — or this row is
testing the second line of defence. If `E-DEF-001` fires first, the fault is
caught before encoding and the row is moot. W2 has no such caveat, which is why
it carries the decision.

- A: **caught** — `expected_size` is 4, the encoding is 6, `E-SIZE-001`.
- B: **caught** — same, and the digest also fails.
- C: **n/a** — the definition is never consulted, so the drift cannot change
  the bytes. C is immune for the same reason it cannot notice a stale template.

### W2 — encoder defect that does not change the length

The `REX.B` bit is taken from the wrong operand.

```text
intended   48 89 d8    3 B    mov rax, rbx
produced   49 89 d8    3 B    mov r8, rbx
```

Same length, both legal, **different program**. No field in variant A contradicts
the output: `expected_size` is 3 and stays 3, and the plan's `src` operand
`{"reg": 3}` says which register the *planner* chose, not which bit of the REX
prefix the encoder must clear. A materializer that never looks at its own output
cannot notice.

- A: **missed** — nothing in the plan contradicts the output.
- B: **caught** — `E-BYTE-001`, the digest was computed over `48 89 d8`.
- C: **n/a** — there is no encoder, and a wrong template is equally undetectable.

This is the counterexample that justifies carrying an expected digest at all.

### W3 — operand outside the field's range

The planner writes `+2147483648`, which does not fit a sign-extended `imm32`.

```text
intended   rejected before encoding
produced   48 05 00 00 00 80    6 B    add rax, -2147483648
```

The 32-bit pattern is a perfectly legal `imm32`; it just means a different
number. This is the same class of failure as the x86 numeric-`short` truncation
found in `EXP-0001` §2.2.

- A: **caught** — the operand is `2147483648` and the form's range is
  `[-2147483648, 2147483647]`; `E-RANGE-001`.
- B: **caught** — same check.
- C: **missed** — there is no operand to check. Whatever 32 bits the planner
  wrote are the program.

### W4 — plan tampering

The immediate changes from 300 to 301, and nothing else changes.

```text
declared   48 05 2c 01 00 00    6 B    add rax, 300
produced   48 05 2d 01 00 00    6 B    add rax, 301
```

- A: **missed** — the plan is self-consistent; only the meaning changed.
- B: **caught** — `E-BYTE-001`.
- C: **n/a** — the template is the answer, so a template edit is not detectable
  by construction.

Note the limit: B is a checksum, not a signature. An actor who can rewrite the
plan can rewrite the digest too. B buys accidental-divergence detection, not
adversarial integrity.

### W5 — unknown form

- A, B: **caught** — `E-FORM-001`.
- C: **n/a** — there is no form to look up.

### Summary

| Fault | A | B | C |
|---|---|---|---|
| W1 length-changing definition drift | caught | caught | n/a |
| W2 same-length encoder defect | **missed** | caught | n/a |
| W3 operand out of range | caught | caught | **missed** |
| W4 plan tampering | **missed** | caught | n/a |
| W5 unknown form | caught | caught | n/a |

Only B catches W2 and W4, and it also catches everything A and C catch. C misses
W3 outright and cannot express W1, W2, W4 or W5 at all.

## 5. OD-01 — verdict

**B, with `expected_digest` and never raw expected bytes.**

- A is rejected because W2 and W4 pass it: a plan that validates completely can
  still produce a different program.
- C is rejected because it deletes the operands (W3) and the form (W5). It is
  also the variant the directive forbids: bytes become the decision instead of
  the result.
- B is accepted because it is a *hash*, not the bytes. A digest is not
  emittable, so it cannot become the source of truth by accident. The materializer
  encodes from `form_id + operands + choices`, then compares, then rejects.

The condition that makes B meaningful: a digest computed by the same encoder the
materializer runs is tautological. When `expected_digest` is present, the plan
MUST record where it came from, and only an independently derived digest (an
oracle, or a hand derivation) buys the W2 detection. This is the same rule the
validation matrix already applies to positive vectors ("two independent
sources"), moved from the test suite into the plan.

Cost: 92 bytes per instruction where the digest is present. It is optional, so a
plan may carry it on the instructions it cares about. v0 fixtures SHOULD carry it
everywhere, because the fixture *is* the oracle record.

## 6. OD-03 — can an AC-05 case be expressed at Level 0?

Level 0 is "bytes plus normalized fixup records". Level 1 adds laid-out section
images, a symbol table and relocation records. Level 2 is a complete object file
and is out of scope for v0 (`ADR-0003`).

The question is whether the structure a Level 1 artifact adds carries information
that the Level 0 record cannot.

### 6.1 The Level 0 record for an external `call`

`call ext` assembles to `e8 00 00 00 00` with one relocation. The plan expresses
the same patch as one record (canonical JSON, 363 bytes; wrapped here for
reading):

```json
{"addend":0,"bit_order":"value_msb_first","field_descriptor":[{"lsb":0,"width":32}],
 "fixup_id":"F0001","offset":1,"overwrite_bytes":false,
 "pc_reference_rule":"pcrel_end",
 "range_constraint":{"align_bits":0,"bits":32,"signed":true},
 "resolution_mode":"emit_relocation","section_id":".text",
 "target":{"kind":"symbol","symbol_id":"S0001"},"value_transform":"identity"}
```

Measurement note (2026-11-04): this record was written against the draft schema,
which still required `overwrite_bytes: false` and
`bit_order: "value_msb_first"`. Both were removed by the OD-02 schema pass: the
first was pinned to `false`, and the second was a one-value enum with a schema
`default`, so neither carried information. The record is kept as measured, so the
current shape is 54 bytes smaller. The rest of the record is unchanged.

LLVM's own record for the same instruction:

```text
0x1  R_X86_64_PLT32  ext  -4
```

`llvm-readobj` prints four fields: offset, type, symbol, addend. The Level 0
record carries all four (offset `1`; `resolution_mode` plus the field descriptor
stand in for the type; `target.symbol_id` names the symbol through the plan's
`symbols[]`; `addend` `0` with `pcrel_end` reproduces LLVM's `-4`, because ELF
puts `P` at the displacement field while the plan puts it after the instruction).
It also carries three things the LLVM record does not: the exact bit range, the
range constraint, and the value transform. A fourth, the pair relation, appears
only on the two pair shapes in §6.2.

So the Level 1 relocation record is a *projection* of the Level 0 record, not an
enrichment. A symbol **table** is what Level 1 adds — and that only restates
`symbols[]`, which the plan already has.

### 6.2 All three AC-05 shapes, as LLVM records them

| Shape | LLVM records |
|---|---|
| x86-64 `call rel32` | `0x1 R_X86_64_PLT32 ext -4` |
| AArch64 `adrp` + `add :lo12:` | `0x0 R_AARCH64_ADR_PREL_PG_HI21 ext 0`<br>`0x4 R_AARCH64_ADD_ABS_LO12_NC ext 0` |
| RV64 `auipc` + `addi` | `0x0 R_RISCV_PCREL_HI20 ext 0`<br>`0x4 R_RISCV_PCREL_LO12_I .L0 0` |

The third row settles a claim that `03_fixup_model.md` previously stated as
knowledge. The low-half relocation does **not** name `ext`; it names `.L0`, a
local symbol defined at the `auipc`. `llvm-readobj --symbols` confirms `.L0` is
in the symbol table, local, type `None`, at `.text+0`. A model that stores only
"symbol + addend" cannot express this, because there is no symbol for the
program to name — the address is the *site* of the paired instruction.

Consequences:

1. `pair_group`/`pair_role` are not convenience fields. They are the only way to
   express the RISC-V relation, and Level 0 has them while a naive relocation
   list does not.
2. AArch64 and RISC-V differ: AArch64's low half names the target symbol,
   RISC-V's names the high instruction. The pair model covers both because it
   stores the relation, not the spelling.
3. A Level 1 emitter for RISC-V would have to **synthesize** a local symbol per
   `hi` site to fill `R_RISCV_PCREL_LO12_I`. That is extra work and extra state,
   not extra information.

### 6.3 Verdict

**Level 0 is sufficient for every AC-05 case; Level 1 is optional and deferred.**

- No AC-05 shape needs a symbol table or a relocation table to be *expressed*.
  All three are expressible as Level 0 records: §6.1 shows the x86 shape field
  by field, §6.2 shows the two pair shapes.
- Level 1 would add serialization, not information, and for RV64 it would add a
  synthesized symbol requirement (§6.2 point 3).
- This confirms `ADR-0003` rather than changing it: v0 ships Level 0; Level 1 is
  produced only if an artifact must be consumed by a linker without the plan.
  No v0 slice has that requirement.

## 7. What is measured and what is inferred

- **Measured (experiment):** every byte in §1; every size in §2; every produced
  byte string and its disassembly in §4; every relocation record in §6.
- **Inferred:** the verdict columns in §3 and §4. They follow from *which fields
  a variant carries* and from the rule that no other field constrains the emitted
  bits. No materializer exists yet, so no verdict here is an execution trace.
- **Not tested:** whether a real encoder makes the W2 mistake. The fault is
  constructed, not observed. `EXP-0001` F-06 observed a real silent truncation in
  another encoder, which is why W3 is treated as a live risk rather than a
  hypothetical one.
