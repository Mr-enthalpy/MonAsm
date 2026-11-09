# EXP-0111 -- the `29 /r` register/register `sub`

- Date: 2026-11-09
- Question: the `sub` table has only the immediate rows (`83 /5`, `81 /5`,
  `2D`). What does the register/register `29 /r` shape cost at the three value
  widths, where do the two register fields sit, and how does it differ from the
  other direction `2B /r`?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.73.0.json`; the generated `0.74.0` is the
  product of this experiment
- Fixture oracle: `fixtures/x86_64/positive/X86-P80-sub-rr.oracle.json`
- Sources: `research/evidence/experiments/EXP-0111/probe.s`,
  `research/evidence/experiments/EXP-0111/X86-P80-sub-rr.s`
- Decision: `ADR-0110`

## 1. What is already pinned

`EC-01` fixes the legacy opcode/`ModRM` split; `EC-06`/`EC-07` fix the
`REX.W`/`0x66` prefixes for 64/16-bit rows; `EC-42` records that `29 /r` and
`2B /r` are different directions, not different spellings of one row. The
`sub` table (`0.66.0`, `X86-P72`) covers only the immediate forms, so both
register directions are absent.

`29 /r` is `SUB r/m, r`: the destination is the `ModRM.r/m` operand and the
source is `ModRM.reg`. `2B /r` is `SUB r, r/m`: the register is the
destination. At register/register both encodings are legal, so the assembler's
choice (`29`) is a decision the plan must carry as a row.

## 2. The measurement

`probe.s` is the six instructions, both operand directions at each width:

| Source | Bytes | Length |
|---|---|---|
| `subq %rcx, %rax` | `48 29 c8` | 3 |
| `subq %rax, %rcx` | `48 29 c1` | 3 |
| `subl %ecx, %eax` | `29 c8` | 2 |
| `subl %eax, %ecx` | `29 c1` | 2 |
| `subw %cx, %ax` | `66 29 c8` | 3 |
| `subw %ax, %cx` | `66 29 c1` | 3 |

`ModRM = c8` is `11 001 000`: `reg = 1` (`%rcx`, the source) and `r/m = 0`
(`%rax`, the destination). The reversed instruction is `c1`
(`reg = 0`, `r/m = 1`), so both register fields move independently. The 64-bit
row pays `REX.W = 48` (with `REX.R`/`REX.B` clear in the low window) and the
16-bit row pays `0x66`; the 32-bit row has no prefix.

The other direction is a different opcode: `subq (%rax), %rcx` is `48 2b 08`
(`2B /r`, `reg = 1` = `%rcx` destination). It is not part of this slice.

## 3. The fixture

`X86-P80-sub-rr.s` is the same six instructions. Sizes are 3/3/2/2/3/3 for
16 bytes; there is no label and no relocation.

The input hash is
`7a4aa6fd42e25efb54043a8f22bc58e44aed4138e278a741313618ad014d813c`;
the output hash is
`6a77edb61cdf1b27a46c014a1f31cf59ab5204e26eb720460e5e9886fcef6ccf`,
size 16, 0 relocation records.

`0.74.0` has 564 forms and digest
`sha256:27f337115cffe89c8d7028863e7748783247344ba4d8e622fa9c4345efdead58`.
It repeats the 561 `0.73.0` forms unchanged.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01et` | names `x86:sub/rm64-r64/legacy` against `0.73.0` | `E-FORM-001` |
| `N01ej` | names the absent `2B /r` direction `x86:sub/r64-rm64/legacy` against `0.74.0` | `E-FORM-001` |
| `N02dc` | drops the source from `x86:sub/rm32-r32/legacy` | `E-OPERAND-002` (`expected: 2`, `found: 1`) |
| `N14cg` | destination register `8` on `x86:sub/rm32-r32/legacy` | `E-OPERAND-004` (`field_bits: 3`) |

`N01ej` previously pinned the absence of the whole register pair; with `29 /r`
present it now pins the one direction this slice deliberately leaves out.

## 5. What the slice defers

- The memory-destination direction `2B /r` (`subq (%rax), %rcx` `48 2b 08`),
  including its register/register spelling.
- The high register window `%r8`-`%r15`: `REX.R`/`REX.B` change the prefix, so
  those rows are a separate template.
- Indexed and displacement memory shapes (`29 /r` with `ModRM.mod != 11`).
- The other ALU mnemonics (`add`, `and`, `or`, `xor`, `cmp`): each opcode byte
  must be measured separately.
