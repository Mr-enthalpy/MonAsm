# ADR-0094: seven ambiguous families stay absent in v0

- Status: accepted
- Date: 2026-11-08
- Settles: `G2` (the last seven `EC` rows still `draft`)
- Supersedes: none
- Superseded by: none
- Revises: `EC-10`, `EC-16`, `EC-18`, `EC-23`, `EC-24`, `EC-25` and `EC-26`
  (draft → frozen; the carrier is decided, the family stays absent)

## Context

The carrier table has 40 rows. Thirty-three were frozen one slice at a time,
each by the slice that first needed the answer. Seven were never needed:
`EC-10` (x86 prefix presence), `EC-16` (AArch64 `mov` alias), `EC-18` (AArch64
conditional transfer), `EC-23` (RV64 jump and call), `EC-24` (RV64 `fence`
masks), `EC-25` (RV64 CSR immediate form) and `EC-26` (RV64 `aq`/`rl`). `G2`
asks every row for an observed counterexample and a decided carrier, and a
draft row is a missing decision, not a satisfied one.

`EXP-0096` measures all seven with `llvm-mc` 23.1.2, one probe file per
family, asserting the object bytes rather than the printer's candidate
encoding:

1. **`EC-10`.** `addl (%rax), %ebx` is `03 18` and `lock addl (%rax), %ebx`
   is `f0 03 18`: one byte in front of an unchanged opcode and `ModRM`. `rep
   movsb` is `f3 a4` against `a4`, and `movl %fs:0, %eax` is
   `64 8b 04 25 00 00 00 00`.
2. **`EC-16`.** `mov x0, #1` is `20 00 80 d2` (`MOVZ`, `hw = 00`),
   `mov x0, #-1` is `00 00 80 92` (`MOVN`), `mov x0, x1` is
   `e0 03 01 aa` (`ORR`, shifted register), `mov x0, #65536` is
   `20 00 a0 d2` (`MOVZ`, `hw = 01`) and `mov w0, #1` is `20 00 80 52`
   (`sf = 0`).
3. **`EC-18`.** At offset 0, `b.eq` is `00 00 00 54`, `cbz x0` is
   `00 00 00 b4`, `cbnz w0` is `00 00 00 35`, `tbz w0, #0` is
   `00 00 00 36` and `tbnz x0, #63` is `00 00 f8 b7`: three opcodes, two
   displacement widths and three operand sets.
4. **`EC-23`.** With `.option rvc`, `jal ra` is `ef 00 00 00` (4 B),
   `jal x0` and `c.j` are `01 a0` (2 B, `c.j`) and `jalr ra, 0(ra)` is
   `82 90` (2 B, `c.jalr`). With `.option norvc`, `jal x0` is
   `6f 00 00 00` and `jalr ra, 0(ra)` is `e7 80 00 00`. The same source line
   changes length with the extension, and RV64 has no `c.jal`, so `jal ra`
   never shortens.
5. **`EC-24`.** `fence rw, rw` is `0f 00 30 03`, `fence iorw, iorw` is
   `0f 00 f0 0f` and `fence r, w` is `0f 00 10 02`: the same opcode with
   `imm12 = fm | pred | succ` equal to `0x033`, `0x0FF` and `0x021`.
6. **`EC-25`.** `csrrw x1, 0x300, x2` is `f3 10 01 30` (`funct3 = 001`) and
   `csrrwi x1, 0x300, 2` is `f3 50 01 30` (`funct3 = 101`).
7. **`EC-26`.** `amoadd.w` is `af a0 21 00`; `.aq` sets bit 26
   (`af a0 21 04`), `.rl` sets bit 25 (`af a0 21 02`) and `.aqrl` sets both
   (`af a0 21 06`).

Two of the seven already carried a partial answer in earlier decisions --
`ADR-0026` made `movk`/`movn` the `movz` lane family one `opc` over (the
`mov` alias stays out), and `ADR-0012` shipped the `b.cond` half of `EC-18`
-- but neither ADR froze its row, because neither needed the full carrier
statement.

## Decision

The rule is one sentence: **a decision whose output is a byte, a length or a
fixed semantic bit is a form fact; a decision whose output is a field value is
an operand.** `operand modifier` stays in the closed carrier set, but no `EC`
row now uses it, and neither of these seven does.

1. **`EC-10` is frozen with `form variant`.** A prefix changes the
   instruction's semantics and puts a byte in front of an unchanged opcode, so
   it is template byte 0 of a distinct row -- the answer `ADR-0029` gave
   `0x66` and `ADR-0080` gave `0x67`. A modifier that added `F0`/`F3`/`64`
   would make the materializer grow an instruction (`INV-04`). v0 carries no
   prefix row, so naming one is `E-FORM-001`.
2. **`EC-16` is frozen with `form variant`.** One mnemonic maps to `MOVZ`,
   `MOVN` and `ORR`, and `sf`/`hw` are the node's. v0 ships the
   `movz`/`movk`/`movn` lanes as their own rows (`ADR-0014`, `ADR-0026`) and
   has no `mov` alias; naming one is `E-FORM-001`.
3. **`EC-18` is frozen with `form variant`.** `b.cond`, `cbz`/`cbnz` and
   `tbz`/`tbnz` differ in opcode, displacement width and operand list, so the
   plan must name the family. v0 ships `b.cond` only (`ADR-0012`); the other
   two are absent (`E-FORM-001`).
4. **`EC-23` is frozen with `form variant`.** `jal`, `c.j` and `jalr` are
   different instructions with different lengths and operand sets. v0 ships
   the four-byte `jal` and fixes its length in `form_id`, so no plan can be
   shortened at materialization time (`INV-02`, `INV-04`).
5. **`EC-24` is frozen with `operand type`.** The mnemonic never changes; the
   `imm12` field carries the masks, so a future `fence` row takes `fm`,
   `pred` and `succ` as typed field operands. v0 has no `fence` row
   (`E-FORM-001`).
6. **`EC-25` is frozen with `form variant`.** `csrrw` and `csrrwi` differ in
   `funct3` and in the kind of value the `rs1` field holds, so the immediate
   form cannot be a modifier on the register form. v0 has neither
   (`E-FORM-001`).
7. **`EC-26` is frozen with `form variant`.** Each suffix fixes one of four
   bit pairs in the same word. A modifier would write bits, which `ADR-0015`
   already ruled out for the AArch64 shift keyword, so the suffix is part of
   `form_id`. v0 has no atomic row (`E-FORM-001`).

No family is implemented by this ADR. `G2` asks for an observed
counterexample and a decided carrier, not for coverage; each of these
families would need its own slice, its own ADR and its own `EXP` when it is
taken up.

## Consequences

- All 40 `EC` rows are now `frozen`, so `G2` is satisfied. The `02` document's
  per-row `Status` cell changes in place for the seven rows; no row is added,
  renumbered or removed.
- No definition, schema, loader, materializer or fixture changes. The
  canonical document stays `0.65.0` (509 forms, digest
  `sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a`),
  and the fixture corpus stays 100 positive / 530 negative.
- `E-FORM-001` is the rejection path for all seven. The `N01` family already
  pins it in every ISA, so no fixture is added: a seventh copy would test the
  error code, not the decision (`EXP-0096` §3).
- The carrier sentence above is now the single place the "byte vs field"
  split is stated; the seven rows cite it instead of restating it.
- `EC-16`'s absent `mov` alias and `EC-18`'s absent `cbz`/`tbz` families are
  now frozen as scope decisions, not omissions. A later slice can add them,
  but it must add rows, a version and an ADR.

## Alternatives rejected

- **Leave the seven `draft` and mark `G2` "not applicable".** Rejected: the
  ambiguity is real and measurable in every case, and a draft row states no
  carrier. `G2` is the gate that prevents exactly this.
- **Freeze `EC-10`/`EC-26` as `operand modifier`, following the draft
  column's suggestion.** Rejected: a modifier is a validated plan property,
  not a byte carrier; using it here would make the materializer add `F0` or
  set bits 26-25, which is the implicit encoding `INV-02` forbids and which
  `ADR-0080` already refused for `EC-08`.
- **Implement the seven families so the freeze has a fixture.** Rejected:
  contract before coverage. Each family needs a slice, a row set and an
  `EXP`; none of that is a precondition for deciding who carries the choice.
- **Add one `E-FORM-001` fixture per family.** Rejected: the code is already
  pinned by `N01`; the observation `G2` wants is the assembler producing more
  than one legitimate encoding, which is what `EXP-0096` records.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| a prefix adds one byte in front of an unchanged opcode | object bytes, `EXP-0096` §1 | high |
| one `mov` mnemonic maps to `MOVZ`/`MOVN`/`ORR` with different `sf`/`hw` | object bytes, `EXP-0096` §1 | high |
| the three conditional families differ in opcode, width and operands | object bytes at offset 0, `EXP-0096` §1 | high |
| `jal`/`c.j`/`jalr` have 4/2/2-byte encodings and C toggles the length | object bytes with `.option rvc`/`norvc`, `EXP-0096` §1 | high |
| `fence` `imm12` is `fm`/`pred`/`succ` | object bytes, `EXP-0096` §1 | high |
| `csrrw`/`csrrwi` differ in `funct3` (`001` vs `101`) | object bytes, `EXP-0096` §1 | high |
| `aq`/`rl` are bits 26 and 25 of the atomic word | object bytes, `EXP-0096` §1 | high |
| v0 carries no row for any of the seven families | `0.65.0` forms list | high |

## Review triggers

- Any of the seven is proposed as coverage; that needs its own slice, a
  definition version and an ADR.
- A prefix, a suffix or a fixed semantic bit is proposed as an
  `operand modifier`; the byte-vs-field rule above is the precedent against
  it.
- A new `EC` row is added; the carrier set and this rule must be applied to
  it before it is marked `frozen`.
