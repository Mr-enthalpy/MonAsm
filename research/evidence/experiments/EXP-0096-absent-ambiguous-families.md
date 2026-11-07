# EXP-0096 -- seven ambiguous families that v0 keeps absent

- Date: 2026-11-08
- Question: for each `EC` row the contract still marks `draft` (`EC-10`,
  `EC-16`, `EC-18`, `EC-23`, `EC-24`, `EC-25`, `EC-26`), does one mnemonic
  really admit more than one legitimate encoding, and which carrier would the
  plan need?
- Toolchain: `llvm-mc` 23.1.2
- Definition: none -- v0 carries no row for any of the seven families
- Source: `research/evidence/experiments/EXP-0096/`
- Decision: `ADR-0094`

## 1. The measurements

Seven probe files, one per family. `measure.py` assembles each to an object
and asserts the `.text` bytes; the recorded `-show-encoding` text keeps the
printer's view. Every table below is the object bytes, not the printer's
candidate encoding.

### `EC-10` -- x86-64 prefix presence (`ec10-x86-prefix.asm`)

| Source | Bytes | Length | Word |
|---|---|---|---|
| `addl (%rax), %ebx` | `03 18` | 2 | plain |
| `lock addl (%rax), %ebx` | `f0 03 18` | 3 | `F0` added, same opcode |
| `movsb %ds:(%rsi), %es:(%rdi)` | `a4` | 1 | plain |
| `rep movsb` | `f3 a4` | 2 | `F3` added, same opcode |
| `movl %fs:0, %eax` | `64 8b 04 25 00 00 00 00` | 8 | `64` added |

### `EC-16` -- AArch64 `mov` alias (`ec16-a64-mov-alias.asm`)

| Source | Bytes | Word | Node |
|---|---|---|---|
| `mov x0, #1` | `20 00 80 d2` | `0xd2800020` | `MOVZ`, `opc = 10`, `hw = 00` |
| `mov x0, #-1` | `00 00 80 92` | `0x92800000` | `MOVN`, `opc = 00` |
| `mov x0, x1` | `e0 03 01 aa` | `0xaa0103e0` | `ORR` (shifted register) |
| `mov x0, #65536` | `20 00 a0 d2` | `0xd2a00020` | `MOVZ`, `hw = 01` |
| `mov w0, #1` | `20 00 80 52` | `0x52800020` | `MOVZ` 32-bit, `sf = 0` |

### `EC-18` -- AArch64 conditional transfer (`ec18-a64-cond-branch.asm`)

| Source | Bytes | Word | Operand set |
|---|---|---|---|
| `b.eq 1b` | `00 00 00 54` | `0x54000000` | condition + `imm19` |
| `cbz x0, 1b` | `00 00 00 b4` | `0xb4000000` | register + `imm19`, no condition |
| `cbnz w0, 1b` | `00 00 00 35` | `0x35000000` | register + `imm19`, no condition |
| `tbz w0, #0, 1b` | `00 00 00 36` | `0x36000000` | register + bit index + `imm14` |
| `tbnz x0, #63, 1b` | `00 00 f8 b7` | `0xb7f80000` | register + bit index + `imm14` |

All five branch to their own address (offset 0), so the differing bytes are
the opcode and field layout alone.

### `EC-23` -- RV64 jump and call (`ec23-rv64-call.asm`)

| Source | Bytes | Length | Instruction |
|---|---|---|---|
| `.option rvc` + `jal ra, 1b` | `ef 00 00 00` | 4 | `jal` |
| `.option rvc` + `jal x0, 1b` | `01 a0` | 2 | `c.j` |
| `.option rvc` + `c.j 1b` | `01 a0` | 2 | `c.j` |
| `.option rvc` + `jalr ra, 0(ra)` | `82 90` | 2 | `c.jalr` |
| `.option norvc` + `jal x0, 1b` | `6f 00 00 00` | 4 | `jal` |
| `.option norvc` + `jalr ra, 0(ra)` | `e7 80 00 00` | 4 | `jalr` |

The same source line produces a two-byte or a four-byte instruction depending
only on whether C is enabled, and RV64 has no `c.jal`, so `jal ra` never
shortens. The recorded printer text shows the compressed shape explicitly as
`[0bAAAAAA01,0b101AAAAA]` next to the four-byte `[0xef,...]`.

### `EC-24` -- RV64 `fence` masks (`ec24-rv64-fence.asm`)

| Source | Bytes | Word | `imm12` = `fm` / `pred` / `succ` |
|---|---|---|---|
| `fence rw, rw` | `0f 00 30 03` | `0x0330000f` | `0` / `3` / `3` |
| `fence iorw, iorw` | `0f 00 f0 0f` | `0x0ff0000f` | `0` / `15` / `15` |
| `fence r, w` | `0f 00 10 02` | `0x0210000f` | `0` / `2` / `1` |

### `EC-25` -- RV64 CSR immediate form (`ec25-rv64-csr.asm`)

| Source | Bytes | Word | `funct3` |
|---|---|---|---|
| `csrrw x1, 0x300, x2` | `f3 10 01 30` | `0x300110f3` | `001` |
| `csrrwi x1, 0x300, 2` | `f3 50 01 30` | `0x300150f3` | `101` |

### `EC-26` -- RV64 `aq` / `rl` (`ec26-rv64-amo.asm`)

| Source | Bytes | Word | Bits 26-25 |
|---|---|---|---|
| `amoadd.w x1, x2, (x3)` | `af a0 21 00` | `0x0021a0af` | `00` |
| `amoadd.w.aq x1, x2, (x3)` | `af a0 21 04` | `0x0421a0af` | `10` |
| `amoadd.w.rl x1, x2, (x3)` | `af a0 21 02` | `0x0221a0af` | `01` |
| `amoadd.w.aqrl x1, x2, (x3)` | `af a0 21 06` | `0x0621a0af` | `11` |

## 2. What the bytes decide

- **`EC-10`: `form variant`.** A prefix changes the instruction's semantics
  and adds a byte in front of an unchanged opcode, so it is template content
  of a distinct row -- the same answer `ADR-0029` gave `0x66` and `ADR-0080`
  gave `0x67`. A modifier that added `F0` would make the materializer grow an
  instruction (`INV-04`). v0 carries no such row, so naming one is
  `E-FORM-001`.
- **`EC-16`: `form variant`.** One mnemonic maps to `MOVZ`, `MOVN` and `ORR`,
  with `hw` and `sf` fixed per node. v0 already ships the `movz`/`movk`/
  `movn` lanes as their own rows (`ADR-0014`, `ADR-0026`) and has no `mov`
  alias; naming one is `E-FORM-001`.
- **`EC-18`: `form variant`.** `b.cond`, `cbz`/`cbnz` and `tbz`/`tbnz` differ
  in opcode, displacement width and operand list. v0 ships the `b.cond`
  family only (`ADR-0012`); the other two are absent (`E-FORM-001`).
- **`EC-23`: `form variant`.** `jal`, `c.j` and `jalr` are different
  instructions with different lengths and operand sets, and the assembler's
  shortening proves the choice is real. v0 ships the four-byte `jal` only,
  and `form_id` fixes the length, so no plan can be shortened (`INV-02`).
- **`EC-24`: `operand type`.** The mnemonic never changes; the `imm12` field
  carries `fm`/`pred`/`succ` as typed values, so a `fence` row (when one
  exists) takes them as field operands. v0 has no `fence` row
  (`E-FORM-001`).
- **`EC-25`: `form variant`.** `csrrw` and `csrrwi` differ in `funct3` and in
  the kind of operand the `rs1` field holds, so the immediate form cannot be
  a modifier on the register form. v0 has neither (`E-FORM-001`).
- **`EC-26`: `form variant`.** Each suffix fixes one of four bit pairs in the
  same word. A modifier would write bits, which `ADR-0015` already ruled out
  for the AArch64 shift keyword; the suffix is therefore part of `form_id`.
  v0 has no atomic row (`E-FORM-001`).

The carrier rule behind all seven is one sentence: a decision whose output is
a byte, a length or a fixed semantic bit is a form fact, and a decision whose
output is a field value is an operand. `operand modifier` remains in the
closed carrier set, but no `EC` row uses it.

## 3. Why there is no fixture

None of the seven families has a row, so there is no plan to accept and no
bytes for the materializer to produce. The rejection path is `E-FORM-001`
(the named `form_id` is not in the pinned definition), which the `N01` family
already pins in every ISA; adding a seventh copy of "an absent form is
rejected" would test `E-FORM-001`, not the decision. The counterexample `G2`
asks for is the measurement above: one mnemonic, more than one legitimate
encoding, and a plan vocabulary that must name which one.

## Reproduce

```
python research/evidence/experiments/EXP-0096/measure.py
```

The script re-assembles the seven probe files, asserts every byte string and
length in this document, and rewrites the recorded `-show-encoding` and
`-bytes` files.
