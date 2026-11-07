# EXP-0102 -- the x86 `sub` immediate rows

- Date: 2026-11-08
- Question: which immediate encodings does `sub` take at the 64-bit register
  width, and what do the absent register forms look like?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.66.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P72-sub-immediates.oracle.json`
- Sources: `research/evidence/experiments/EXP-0102/probe.asm`,
  `research/evidence/experiments/EXP-0102/register.asm`
- Decision: `ADR-0101`

## 1. The measurement

`llvm-mc -show-encoding` and the object bytes agree on all ten instructions;
`measure.py` asserts the 55-byte `.text` and writes `bytes.txt` and
`show-encoding.txt`.

| Source | Bytes | Length | Row |
|---|---|---|---|
| `subq $1, %rax` | `48 83 e8 01` | 4 | `rm64-imm8` |
| `subq $127, %rcx` | `48 83 e9 7f` | 4 | `rm64-imm8` |
| `subq $-128, %rax` | `48 83 e8 80` | 4 | `rm64-imm8` |
| `subq $1, %r8` | `49 83 e8 01` | 4 | `rm64-imm8`, `REX.B` |
| `subq $300, %rbx` | `48 81 eb 2c 01 00 00` | 7 | `rm64-imm32` |
| `subq $2147483647, %r15` | `49 81 ef ff ff ff 7f` | 7 | `rm64-imm32`, `REX.B` |
| `subq $-2147483648, %rdx` | `48 81 ea 00 00 00 80` | 7 | `rm64-imm32` |
| `subq $300, %rax` | `48 2d 2c 01 00 00` | 6 | `rax-imm32` |
| `subq $2147483647, %rax` | `48 2d ff ff ff 7f` | 6 | `rax-imm32` |
| `subq $-2147483648, %rax` | `48 2d 00 00 00 80` | 6 | `rax-imm32` |

The `add` rows of `0.1.0` differ only in `ModRM.reg` and in the accumulator
opcode: `48 83 c0 01` is `addq $1, %rax`, `48 83 e8 01` is `subq $1, %rax`, and
`48 05 …`/`48 2d …` are the two accumulator forms. The `REX.W` byte, the opcode
and the immediate placement are identical.

`subq $1, %r8` is the row's `REX.B` evidence: `49` is `48 | 0x01`, so the
destination slot's `[0,1]` chunk is set and `ModRM.r/m` still carries the low
three bits. `subq $2147483647, %r15` repeats the same bit on the `imm32` row.

## 2. The register forms are a different pair

`register.asm` measures the shapes this slice does not take:

| Source | Bytes | Opcode |
|---|---|---|
| `subq %rbx, %rax` | `48 29 d8` | `29 /r` |
| `subq %rax, %rbx` | `48 29 c3` | `29 /r` |
| `subq $1, %rax` | `48 83 e8 01` | the shipped `imm8` row |

Both register-register spellings use `29` and differ only in `ModRM`; `llvm-mc`
never selects `2B` (`SUB r64, r/m64`) for a register-register `sub`. The `add`
register halves are equally absent from the table, so the register form is a
separate direction decision with its own evidence, not part of this slice.

## 3. The fixture

`X86-P72-sub-immediates` is the ten-instruction, 55-byte vector above.
`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from the
materializer; the oracle's `input_sha256` is
`31d8186bc3e847039e4629493cacaa6605f3d2dc0883296dabee39b98397c90c`
(`probe.asm`) and its `output_sha256` is
`60352c7055d173fe2af1141aa18f3d53b05d6c5ebc36e5fda70aa69c55f3b722`
(the 55-byte `.text`).

`0.66.0` has 512 forms and the canonical digest
`sha256:63b3b3a153aa0b5508f2055496efa1c56ac74e56b03d56f56f5c522b6d2e1904`.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01ej` | names `x86:sub/rm64-r64/legacy`, which no version has | `E-FORM-001` |
| `N01ek` | names the `imm8` row against `0.65.0` | `E-FORM-001` |
| `N03zs` | imm `128` on the signed 8-bit row | `E-RANGE-001` (`max 127`) |
| `N02ct` | passes `x86.gpr32`/`r32` as the destination of `rm64-imm32` | `E-OPERAND-001` twice (`kind`, `target_type`) |

`N03zs` is the promotion boundary: `128` fits `imm32`, but the plan named the
`imm8` row, so the answer is a rejection and never a silent widening.

## 5. What the slice defers

- The register-register `sub` pair (`29`/`2B`), with its direction decision.
- `sub` at the 8-, 16- and 32-bit widths and with a memory destination.
- A symbol in the `sub` immediate (`R_X86_64_32S`); the field class needs its
  own measurement, as `EXP-0095` did for `add`.
- `sbb`, `neg`, `dec` and the other instructions that reuse the `/r` group.
