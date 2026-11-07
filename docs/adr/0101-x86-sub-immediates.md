# ADR-0101: x86 `sub` takes the three `add` immediate shapes with `/5` fixed

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P72` (the three `sub` immediate rows: `REX.W 83 /5 ib`,
  `REX.W 81 /5 id` and `REX.W 2D id`)
- Supersedes: none
- Superseded by: none
- Revises: `EC-01` (the sign-extended `imm8` vs `imm32` pair is not specific to
  `add`) and `EC-04` (the accumulator form applies to `sub` too); the x86-64
  slice table of `02_encoding_choices.md`; the x86 table of
  `06_validation_matrix.md`; adds `definitions/x86_64/0.66.0.json` and the
  `X86-P72` fixture

## Context

The table has carried exactly three `add` immediate rows since `0.1.0`:
`x86:add/rm64-imm8/legacy` (`REX.W 83 /0 ib`), `x86:add/rm64-imm32/legacy`
(`REX.W 81 /0 id`) and `x86:add/rax-imm32/legacy` (`REX.W 05 id`). No `0.1.0`
…`0.65.0` document has a form whose `form_id` contains `sub`: the 509-form
canonical `0.65.0` table returns zero matches, and every earlier document is a
subset of it, so a plan that names a `sub` row is `E-FORM-001` today.

`sub` is the same instruction family with `ModRM.reg = /5` instead of `/0` and
the accumulator opcode `2D` instead of `05`. `EXP-0102` measures the whole
surface with `llvm-mc`/`llvm-objcopy` 23.1.2 on 2026-11-08:

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

Three facts decide the rows:

1. **`/5` is the only change in the `ModRM` byte.** `48 83 e8 01` differs from
   `48 83 c0 01` (`add`) in `ModRM.reg` alone; the `REX.W` byte, the opcode and
   the immediate are identical. The field is not an operand and no plan field
   may carry it.
2. **`subq $300, %rax` has two legal encodings.** `48 2d 2c 01 00 00` (6 B) and
   `48 81 e8 2c 01 00 00` (7 B) perform the same operation. `llvm-mc` picks the
   accumulator, so the choice is a form the plan must name, exactly as `EC-04`
   states for `add`; the value cannot pick it (`INV-02`).
3. **The register forms are a different pair and stay absent.**
   `subq %rbx, %rax` is `48 29 d8` and `subq %rax, %rbx` is `48 29 c3`: both use
   opcode `29` (`SUB r/m64, r64`) with the two registers swapped in `ModRM`,
   and `llvm-mc` never selects `2B` for a register-register `sub`. The `add`
   register halves are equally absent from the table, so adding one direction
   of `sub` here would be a different slice with its own evidence.

## Decision

1. **`0.66.0` appends exactly three rows**, in the order the `add` family
   states them:

   | `form_id` | Template | Slots |
   |---|---|---|
   | `x86:sub/rm64-imm8/legacy` | `4883e800` | `dest` `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; `imm` `x86.imm`/`imm8` → `[24,8]` |
   | `x86:sub/rm64-imm32/legacy` | `4881e800000000` | `dest` `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; `imm` `x86.imm`/`imm32` → `[24,32]` |
   | `x86:sub/rax-imm32/legacy` | `482d00000000` | `imm` `x86.imm`/`imm32` → `[16,32]` |

   The `dest` slot is four bits because `0.6.0` widened it (`ADR-0033`):
   `REX.B` at `[0,1]` extends `ModRM.r/m` at `[16,3]`. `subq $1, %r8` is
   `49 83 e8 01` — the `REX` byte is `49`, not `48` — which is the fixture's
   evidence that the destination reaches `%r8`–`%r15` through one row.
2. **`/5` and `2D` are template content, not plan fields.** The form is named
   by the plan, so the mnemonic and the `ModRM.reg` opcode extension are
   implied by `form_id` (`INV-02`). There is no `op` operand and no `add`
   reuse: `sub $1, %rax` is not `add $-1, %rax`, because that would be an
   implicit rewrite and the negation of `-2147483648` is not representable
   (`INV-03`).
3. **The immediate remains field content with its signed range.** `imm8` is
   `{signed: true, bits: 8, align_bits: 0}` and `imm32` likewise at 32 bits, so
   `128` on the `imm8` row is `E-RANGE-001` (`N03zs`), not an `imm32`
   promotion. A plan that wants `128` names `rm64-imm32`.
4. **The accumulator row has no destination operand.** `x86:sub/rax-imm32` is
   fixed to `%rax` by its template, the same shape as `x86:add/rax-imm32`
   (`EC-04`). A plan that supplies a `dest` on it has an extra operand and is
   `E-OPERAND-002`.
5. **The register forms stay absent.** Naming `x86:sub/rm64-r64/legacy` is
   `E-FORM-001` (`N01ej`); the id appears in no definition document, because
   `29`/`2B` need their own direction decision and fixture.
   Naming a `0.66.0` row against `0.65.0` is also `E-FORM-001` (`N01ek`), which
   pins the version boundary.
6. **No schema, loader or materializer change.** Every slot kind, placement,
   range and operand role used here already exists; only the definition table
   grows. `0.65.0` is unchanged; `0.66.0` has 512 forms with digest
   `sha256:63b3b3a153aa0b5508f2055496efa1c56ac74e56b03d56f56f5c522b6d2e1904`.

## Consequences

- `X86-P72-sub-immediates` is ten instructions and 55 bytes: the three rows
  once each at the signed ends, plus `subq $1, %r8` for the `REX.B` bit and
  `subq $300, %rax` for the accumulator choice. Its `expected.bin` comes from
  `llvm-mc` + `llvm-objcopy`, never from the materializer; the oracle's
  `input_sha256` is
  `31d8186bc3e847039e4629493cacaa6605f3d2dc0883296dabee39b98397c90c`
  (`probe.asm`) and its `output_sha256` is
  `60352c7055d173fe2af1141aa18f3d53b05d6c5ebc36e5fda70aa69c55f3b722`
  (the 55-byte `.text`).
- Four negatives pin the shape: the register sibling (`N01ej`,
  `E-FORM-001`), the version boundary (`N01ek`, `E-FORM-001`), `128` on the
  signed 8-bit immediate (`N03zs`, `E-RANGE-001`) and a `x86.gpr32`/`r32`
  destination on the `rm64-imm32` row (`N02ct`, `E-OPERAND-001` twice — the
  kind and the target type).
- `EC-01` and `EC-04` are revised in place: the two rows and the accumulator
  choice are properties of the mnemonic family, not of `add`. No `EC` row is
  added or renumbered.
- The x86 slice table gains the three rows, the x86 fixture README gains
  `X86-P72`, and `07_definition_format.md` §8.1 gains the three rows, the
  header range `0.1.0` … `0.66.0` and the new digest.

## Alternatives rejected

- **One `sub` row with an `op` or `negate` operand.** Rejected: the difference
  is the `ModRM.reg` opcode extension and the opcode byte, both form facts.
  A plan field that selected them would be implicit instruction selection
  (`INV-01`, `INV-02`), and the same field would have to serve `add`, `and`,
  `or` and every other `/r` group.
- **Select `imm8` whenever the value fits, `imm32` otherwise.** Rejected:
  `subq $1, %rax` is legal both ways (`48 83 e8 01` and `48 81 e8 01 00 00 00`);
  choosing by value is the `EC-01` relaxation, shifts every later offset and
  makes `expected_size` unstable (`INV-04`).
- **Reuse `x86:add/*` with a negated immediate.** Rejected: `INV-03` forbids
  expansion, the flags are not guaranteed by the contract, and the negation of
  `-2147483648` overflows the 32-bit immediate.
- **Always use the accumulator opcode when the destination is `%rax`.**
  Rejected: `EC-04`. `48 81 e8 …` is legal for `%rax` too, so the choice must
  be the plan's; `llvm-mc` picking `48 2d …` is evidence of the ambiguity, not
  permission to copy it.
- **Add the register-register rows in the same version.** Rejected: `29`/`2B`
  are two directions with their own encoding choice, and the `add` register
  rows are absent for the same reason. Mixing them in would make one version
  carry two unrelated decisions and leave `check_form_coverage` with a form
  no byte fixture explains.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| the three rows are `83 /5 ib`, `81 /5 id` and `2D id` | `llvm-mc -show-encoding` and object bytes, `EXP-0102` §1 | high |
| `subq $1, %r8` is `49 83 e8 01`, so the destination slot's `REX.B` is `[0,1]` | object bytes plus the `0.66.0` slot placement, `EXP-0102` §1 | high |
| `subq $300, %rax` is `48 2d 2c 01 00 00` and `48 81 e8 2c 01 00 00` is the same operation | `llvm-mc -show-encoding`, `EXP-0102` §1 | high |
| `subq %rbx, %rax` / `subq %rax, %rbx` are `48 29 d8` / `48 29 c3` and `llvm-mc` never picks `2B` | `register.asm` object bytes, `EXP-0102` §2 | high |
| `0.65.0` has no `sub` form | `definitions/x86_64/0.65.0.json`, form-id scan | high |
| `128` on the signed 8-bit immediate is rejected, not promoted | `N03zs` run through the CLI, `EXP-0102` §4 | high |
| the `r32` destination misses the kind and the target type | `N02ct` run through the CLI, `EXP-0102` §4 | high |

## Review triggers

- A register-register `sub` row (`29`/`2B`) is proposed; it needs its own
  direction decision and its own fixture.
- A `sub` row at another width (`8`/`16`/`32`) or with a memory destination is
  proposed; the x86 slice has no such `add` rows either, so it is a new family.
- A symbol in the `sub` immediate is proposed; the relocation class
  (`R_X86_64_32S`) and the field width need their own measurement.
- A plan asks for `sbb`, `dec`/`neg` or another instruction that reuses `83 /5`
  with a different reading.
