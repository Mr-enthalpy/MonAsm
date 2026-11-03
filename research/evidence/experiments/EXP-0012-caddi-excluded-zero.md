# EXP-0012 — the two `c.addi` zero cases encode HINTs, so the form needs `excluded`

- Date: 2026-11-04
- Subject: `OD-14`, the `excluded` slot field, `riscv:c.addi/rd-imm6`, and the
  fixtures `RV-P7`, `N16a`, `N16b`, `N01c`
- Basis: **experiment** for every byte string, hash, rejection message and digest
- Reproduce: the commands in §2, then
  `python research/evidence/experiments/EXP-0010/generate_rv64.py` and
  `cargo test --workspace`
- Depends on: `EXP-0009`, `EXP-0010`, ADR-0007; feeds ADR-0009, ADR-0008's
  `OD-13` sibling

## 1. Why this experiment exists

`RV-P7` asks for the compressed-versus-standard case: `c.addi` (2 bytes) versus
`addi` (4 bytes), with the encoder never choosing between them. The UDB node for
`c.addi` states `not: 0` on two variables, `imm` and `xd`. `fmp-def/0.1` models a
slot as an interval plus placements, and `0` is inside `[-32, 31]`, so the
existing check cannot reject it.

Before deciding how to represent that — a boolean, a role rule, or a list —
the experiment had to answer two questions with bytes:

1. What does an assembler actually emit for the two zero cases, and what do those
   bytes mean?
2. Does the exclusion belong to the mnemonic (`c.addi`), to the role (`imm`), or
   to the form?

All measurements below used LLVM 23.1.2 at `C:\Users\hanni\Tools\llvm\bin`.
Inputs are one instruction per line, LF line endings, one trailing newline.

## 2. Measurements

### 2.1 `c.addi` at its boundaries and at zero

| Input | Bytes | `llvm-objdump -d` | Note |
|---|---|---|---|
| `c.addi a0, 1` | `05 05` | `c.addi a0, 0x1` | the form as intended |
| `c.addi a0, -32` | `01 15` | `c.addi a0, -0x20` | signed minimum |
| `c.addi a0, 31` | `7d 05` | `c.addi a0, 0x1f` | signed maximum |
| `c.addi a0, -1` | `7d 15` | `c.addi a0, -0x1` | |
| `c.addi a0, 0` | `01 05` | `c.addi a0, 0x0` | **HINT**, not the addition |
| `c.addi x0, 1` | `05 00` | `c.nop 0x1` | **C.NOP**, not the addition |
| `c.addi x0, 0` | `01 00` | `nop` | canonical `nop` |
| `c.addi a0, 32` | — | `llvm-mc` rejects | *immediate must be an integer in the range [-32, 31]* |

Two facts follow. First, zero is inside the declared range, so `E-RANGE-001`
(which reports `min`/`max`) cannot fire. Second, the bytes are not the operation
the plan would have named: `01 05` is a reserved HINT and `05 00` is `c.nop`, so
materializing them is a silent instruction substitution (`INV-02`, `INV-07`).
`c.addi x0, 0` (`01 00`) is the same encoding the standard `nop` pseudo-
instruction uses.

### 2.2 The standard form does not stay standard under `+c`

| Input | Attributes | Bytes |
|---|---|---|
| `addi a0, a0, 1` | none | `13 05 15 00` (4 B) |
| `addi a0, a0, 1` | `-mattr=+c` | `05 05` (2 B) |
| `addi a0, a1, 1` | `-mattr=+c` | `13 85 15 00` (4 B) |
| `c.addi a0, 1` | `-mattr=+c` | `05 05` (2 B) |

The assembler compresses `addi a0, a0, 1` as soon as `C` is enabled, and leaves
`addi a0, a1, 1` alone because the compressed form has no separate source
register. This is the concrete failure `EC-19`/`RV-P7` names: the instruction
length is a function of the operands unless the plan pins the form. It is also
why the fixture's standard-form vector uses `a1` as the source — `a0, a0, 1`
would measure the assembler's choice, not the form's bytes.

Input SHA-256 for the two-line `addi` probe: `46b3207b1f9f4991…` (the one-line
`addi a0, a0, 1` file, §7 lists the full string).

### 2.3 The 3-bit compressed register class is per form, not per `c.` prefix

Earlier notes used `c.addi a6, 5` as the `x8–x15` example (`EC-20`, F-10). That
is wrong for `c.addi`:

| Input | Bytes | Result |
|---|---|---|
| `c.addi a6, 5` | `15 08` | accepted; `xd` is a 5-bit field |
| `c.mv a6, a1` | `2e 88` | accepted |
| `c.lw a2, 0(a0)` | `10 41` | accepted |
| `c.lw a6, 0(a0)` | — | rejected: *register must be a GPR from x8 to x15* |

So the exclusion is a property of the form's field, not of the mnemonic's first
letter. `c.addi`'s exclusion is `xd != 0`; `c.lw`'s is a 3-bit field that cannot
name `x16` at all. `fmp-def/0.1` expresses the first with `excluded: [0]` and the
second with a narrower register placement, and v0 has no `c.lw` row.

## 3. The decision the measurements support

ADR-0009 chooses a **closed `excluded` list on the slot**: exact integers,
strictly increasing, inside the slot's representable domain; absent means none.
The check is a lookup, not a predicate, so `INV-06` holds and "legal" stays
decidable by inspection. The generator turns the node's `not:` into that list and
refuses a `not:` it cannot express; a scalar `not: 0` and the `RV32` `ld` block's
16-element odd-register list are the same construct.

The alternative — a `non_zero: true` boolean — was rejected because the second
constraint would force a list anyway, and a predicate would be the first
expression in a format that promises none. A plan-level rule by role was
rejected because `addi a0, a0, 0` (`13 05 05 00`) is legal and must not be
rejected.

## 4. The table and its digest

`inst/C/c.addi.yaml` is 8,225 B, SHA-256
`584daae38d4e830b88be6474f5420d39d858a6c1ca94acd70ce4f5c300348e75`. Its
`encoding.match` is `000-----------01`; `imm` is `location: "12|6-2"` with
`not: 0` and `sign_extend: true`; `xd` is `11-7` with `not: 0`. The generator
derives the template `0100` and the placements `[12,1]`, `[2,5]` for `imm` and
`[7,5]` for `xd`, then encodes four vectors from the table alone:

```text
c.addi a0, 1      05 05
c.addi a0, -32    01 15
c.addi a0, 31     7d 05
c.addi a0, -1     7d 15
```

Because `definedBy.extension.name` is `Zca` and `ext/C.yaml` places `Zca` in C's
`requirements.allOf`, the form needs `rv64c` enabled. The document's extension set
is compared exactly with the plan's, so `c.addi` cannot be added to `0.1.0`
without changing what that version means. `0.2.0` is the new document:

| Document | Forms | `enabled_extensions` | Digest |
|---|---|---|---|
| `definitions/rv64/0.1.0.json` | 7 | `["rv64i"]` | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` (unchanged) |
| `definitions/rv64/0.2.0.json` | 8 | `["rv64i","rv64c"]` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |

The generator writes both files in one run, and `0.1.0` is byte-identical before
and after (`git diff` is empty for it). Base forms are shared by construction,
not copied: the same built form object is placed in both documents.

## 5. Fixtures

`RV-P7-caddi` is 12 B: `c.addi a0, 1` (`05 05`), `addi a0, a1, 1`
(`13 85 15 00`), `c.addi a0, -32` (`01 15`), `c.addi a0, 31` (`7d 05`), and
`c.addi a0, -1` (`7d 15`). The oracle input is 71 B, SHA-256
`3be4bf6e4825ecb83c31d67fb6ce8ad531e960c1f7a7da9d1977cd22dc1c63c6`; the
extracted `.text` is SHA-256
`213f5727fed78ca94f4082078d87e223b0263a96e94dc793f07645d3e6423563`.

`N16a-caddi-imm-zero` sets `imm = 0`; `N16b-caddi-rd-zero` sets `dest = 0`. Both
pin `0.2.0` and declare `["rv64i","rv64c"]`, and both must produce exactly one
diagnostic: `E-RANGE-004`, at `/instructions/0/operands/1/payload/value` and
`/instructions/0/operands/0/payload/reg` respectively, with keys `target_type`,
`value`, `excluded`. `N01c-caddi-against-0.1.0` names the same form against
`0.1.0` and pins `E-FORM-001` at `/instructions/0/form_id`: the table lookup is
per version, and the missing form is not repaired to `addi`.

The generator also asserts that each built form's plan-level extension is in the
document it is placed in (`rv64i` for `I`, `rv64c` for `Zca`), so a future form
cannot silently widen a table without a version bump.

## 6. What this settles, and what it does not

Settled (`ADR-0009`, `OD-14`):

- A slot may exclude a closed list of exact values; the check is
  `E-RANGE-004` and is subtracted from `range`.
- `c.addi` is `riscv:c.addi/rd-imm6` in `rv64/0.2.0`, and `RV-P7` passes through
  the Rust materializer against `llvm-mc` bytes.
- `0.1.0` is unchanged and still rejects the form (`N01c`).

Not settled:

- **The Zilsd odd-register list is not exercised.** The `RV32` block of
  `ld.yaml` uses the same `not:` construct with 16 values, but v0 is RV64 and the
  generator reads the `RV64` block only. Its load-time behaviour is read, not
  measured end to end.
- **A non-list legality rule.** A modulo rule or a pairing rule between two
  operands is not expressible as `excluded` and remains a future decision.
- **`c.lw`/`c.sw` register-class forms.** They need the narrower register
  placement, not `excluded`, and are not in v0.

## 7. Reproduction

```powershell
$env:PYTHONIOENCODING="utf-8"
# §2.1
llvm-mc -triple=riscv64 -mattr=+c -show-encoding caddi.s
llvm-mc -triple=riscv64 -mattr=+c -filetype=obj caddi.s -o caddi.o
llvm-objcopy -O binary --only-section=.text caddi.o caddi.bin
llvm-objdump -d --triple=riscv64 caddi.o
# §2.2-2.3: same commands, one input line each
# the table and the fixtures
python research\evidence\experiments\EXP-0010\generate_rv64.py
cd prototype; cargo test --workspace
```

Input SHA-256 values recorded above are for the exact files used; the fixture's
`.s` is not shipped, matching the other RV64 fixtures (`fixtures/rv64/README.md`).
