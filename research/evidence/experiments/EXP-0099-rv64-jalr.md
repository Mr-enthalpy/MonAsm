# EXP-0099 -- RV64 `jalr`: the field, the `auipc` pair, and the base register

- Date: 2026-11-08
- Question: what does RV64 `jalr` encode, how does the `auipc` + `jalr` call pair
  resolve, and what does the low half's 12-bit field mean when its sign bit is
  set?
- Toolchain: `llvm-mc`/`llvm-readobj`/`llvm-objcopy`/`llvm-objdump` 23.1.2,
  `ld.lld` 23.1.2
- Definition: `definitions/rv64/0.4.0.json` (the `0.3.0` table plus
  `riscv:jalr/rd-rs1-imm12`)
- Fixture oracle: `fixtures/rv64/positive/RV-P10-jalr-imm12.oracle.json`,
  `RV-P10-call-pair.oracle.json` and `RV-P10-call-pair-resolved.oracle.json`
- Source: `research/evidence/experiments/EXP-0099/`
- Decision: `ADR-0099`

## 1. The field

`field.asm` is three `jalr rd, imm(rs1)` lines under `.option norvc`:

| Source | Bytes | `imm` | `rd` | `rs1` |
|---|---|---|---|---|
| `jalr a0, 0(a1)` | `67 85 05 00` | 0 | 10 | 11 |
| `jalr x0, 2047(a1)` | `67 80 f5 7f` | 2047 | 0 | 11 |
| `jalr x0, -2048(a1)` | `67 80 05 80` | -2048 | 0 | 11 |

`imm` sits at 31-20 (sign-extended), `xs1` at 19-15, `funct3 = 000`, `xd` at
11-7 and the opcode is `1100111` (UDB `inst/I/jalr.yaml`). The measured immediate
domain is `[-2048, 2047]`; `2048` is `E-RANGE-001` (`N03x`).

`.option norvc` is load-bearing. `EXP-0096` measured that the same first line
with C enabled is `82 90`, the two-byte `c.jalr`. That is a different form with a
different length, so the plan names the 4-byte `riscv:jalr/rd-rs1-imm12` and the
2-byte `c.jalr` is absent (`E-FORM-001`, `N01ei`).

## 2. The call pair

`call.asm` is the standard call idiom against an external symbol:

```text
.L0:
  auipc ra, %pcrel_hi(blob)
  jalr ra, %pcrel_lo(.L0)(ra)
```

The object bytes are `97 00 00 00 e7 80 00 00` (both fields zero) and
`llvm-readobj --relocations` reports:

```text
0x0 R_RISCV_PCREL_HI20   blob 0x0
0x4 R_RISCV_PCREL_LO12_I .L0  0x0
```

The low record names `.L0`, the `auipc` label, not `blob`. That is the same
relation `RV-P8` carries, and the plan stores it as `pair_group` plus
`pair_role`, never inferred from the symbol.

`call-resolved.asm` puts `.text` at `0x1000` and `L1` at `0x1900`:

```text
.L0:
  auipc ra, %pcrel_hi(L1)
  jalr ra, %pcrel_lo(.L0)(ra)
  .space 0x8f8
L1:
  .word 0
```

The linked words are `97 10 00 00 e7 80 00 90`: `auipc ra, 1` and `jalr ra,
0x900(ra)`. Hand derivation agrees: `(0x1900 - 0x1000 + 0x800) >> 12 = 1` and
`(0x1900 - 0x1000) & 0xFFF = 0x900`.

## 3. Why the low half is `signed: false`

The `jalr` immediate is added to `X[rs1]`, not to `pc`. In the call idiom
`X[rs1]` holds `P_hi + hi20 * 4096`, so the correct immediate is
`S + A - P_hi - hi20 * 4096`, a value in `[-2048, 2047]`. The plan writes
`(S + A - P_hi) & 0xFFF`, which is the same 12-bit pattern because the two
values are congruent modulo 4096.

When the remainder is negative the mask sets bit 11. `llvm-objdump -d` reads the
linked word back as:

```text
1004:  jalr  -0x700(ra) <L1>
```

and `0x1000 + 0x1000 - 0x700 = 0x1900`, the target. So `0x900` in the field is
correct and in range. A `signed: true` low half would reject it as
`E-FIXUP-003`, which is why the descriptor says `signed: false`: `pcrel_lo12`
masks and never range-checks (`03_fixup_model.md` §6).

## 4. What the materializer does not check

`rs1` is a register operand, not a fixup field. The plan must supply it, and the
materializer cannot know whether the register holds `P_hi` at run time. A plan
that pairs `jalr` with `pcrel_begin` is therefore not rejected, and it is not
the same program: `pcrel_begin` measures from the `jalr`'s own address
(`0x1004`), which is not what the instruction adds. In the resolved layout that
plan would write `0x1900 - 0x1004 = 0x8FC` into the field, and the jump would
land at `0x2000 + 0x8FC = 0x28FC` instead of `0x1900`. Modeling the register's
run time value would require the materializer to interpret the instruction
stream, which v0 does not do: the definition says which fields a form has, not
what the instruction means.

## Reproduce

```text
python research/evidence/experiments/EXP-0099/measure.py
```

The script assembles the four inputs, asserts the byte strings, the two
relocation names, the 2308-byte linked image, the `-0x700(ra)` disassembly and
the `c.jalr` bytes, and writes `bytes.txt`, `relocations.txt`,
`show-encoding.txt` and `disassembly.txt`.
