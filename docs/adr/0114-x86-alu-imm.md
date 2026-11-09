# ADR-0114: the integer ALU immediate family at three widths

- Status: accepted
- Date: 2026-11-10
- Settles: `X86-P82` (the thirty-six ALU immediate rows and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-01` of `02_encoding_choices.md` (widened from the `add`/`sub`
  64-bit pair to every ALU mnemonic at 64/32/16 bits) and `EC-04` (the
  accumulator form extended to `and`/`or`/`xor`/`cmp`); the reading-aid table
  and `0.76.0` paragraph of `07_definition_format.md` §8.1; the x86 table of
  `06_validation_matrix.md`; adds `definitions/x86_64/0.76.0.json`, `EXP-0113`
  and the `X86-P82`/`N01ex`/`N01ey`/`N03zw`/`N03zx` fixtures

## Context

`0.75.0` carries the register/register half of the integer ALU family, but the
immediate half is still a strip. `add` and `sub` have their three 64-bit
immediate rows from `0.1.0`/`0.66.0`; no other mnemonic has an immediate row,
and `add`/`sub` have nothing below 64 bits. A plan that wants
`addl $300, %ecx` or `andq $1, %rbx` has no form to name.

Every ALU mnemonic uses the same two immediate opcodes, distinguished only by
the `ModRM.reg` digit:

| Mnemonic | `/digit` | imm8 | full width |
|---|---|---|---|
| `add` | 0 | `83 /0 ib` | `81 /0 iw`/`id` |
| `or` | 1 | `83 /1 ib` | `81 /1 iw`/`id` |
| `and` | 4 | `83 /4 ib` | `81 /4 iw`/`id` |
| `sub` | 5 | `83 /5 ib` | `81 /5 iw`/`id` |
| `xor` | 6 | `83 /6 ib` | `81 /6 iw`/`id` |
| `cmp` | 7 | `83 /7 ib` | `81 /7 iw`/`id` |

`add`/`sub` also have the accumulator short form (`05`/`2D`); `and`, `or`,
`xor` and `cmp` have theirs (`25`, `0D`, `35`, `3D`). Both members of each pair
are legal for a value that fits; `llvm-mc` picks the shorter one. `EXP-0113`
decodes both members and shows the same instruction text.

## Decision

1. **Thirty-six new rows.** `0.76.0` appends:
   - `add` and `sub` at 32 bits (`83 /r ib`, `81 /r id`) and 16 bits
     (`66 83 /r ib`, `66 81 /r iw`), eight rows;
   - `and`, `or`, `xor` and `cmp` at 64, 32 and 16 bits, the `imm8` row plus
     the full-width row, twenty-four rows;
   - the 64-bit `%rax` short form of those four mnemonics (`25`, `0D`, `35`,
     `3D`), four rows.
2. **`EC-01` is widened, not duplicated.** The `imm8` vs full-width choice is
   one decision at three widths: `rm64-imm8`/`rm64-imm32`,
   `rm32-imm8`/`rm32-imm32` and `rm16-imm8`/`rm16-imm16`. `0.76.0` repeats both
   rows for every mnemonic, so the counterexample now names the whole family.
3. **`EC-04` is widened, not duplicated.** The accumulator form is the same
   decision `add`/`sub` already carry. `0.76.0` adds the four remaining pairs
   (`and/rax-imm32` + `and/rm64-imm32`, and so on), and `EXP-0113` shows
   `48 25 2c 01 00 00` and `48 81 e0 2c 01 00 00` decode to the same
   `andq $300, %rax`.
4. **The naming keeps the operand roles.** `x86:<mnemonic>/rm<width>-imm<width>/legacy`
   puts the destination in `ModRM.r/m` and the immediate after the `ModRM`
   byte. At 64 bits the destination is `REX.B` at `[0,1]` plus `ModRM.r/m` at
   `[16,3]`; the immediate is `[24,8]` or `[24,32]`. At 32 bits the fields are
   `[8,3]`/`[16,8]` and `[8,3]`/`[16,32]`; at 16 bits they are
   `[16,3]`/`[24,8]` and `[16,3]`/`[24,16]` behind the `0x66` byte.
5. **The `%rax` short form has only the immediate slot.** The accumulator is
   implicit in the opcode, exactly as in the existing `add/rax-imm32` and
   `sub/rax-imm32` rows; the plan carries one `imm` operand and the form_id
   names the register.
6. **`0.76.0` is additive and immutable.** It repeats the 579 `0.75.0` forms
   byte-for-byte, and the generator asserts the reproduction before it writes
   the new version. The digest is
   `sha256:7535ae0641806b1785096bd286ac62f90f7f02023fd5d47a92b4d4df6371e39a`.

## Consequences

- `X86-P82-alu-imm` is the 176-byte vector of thirty-six instructions: every
  new row appears once, the `imm8` rows carry `$1` and the full-width rows
  `$300`, and the destination alternates between `%rbx` and `%rcx` so the
  `ModRM.r/m` field is shown to be operand-owned. The input hash is
  `0f6416799ee341eb2b1e387b54ef987f084ef7720c99de737f82da5cd2246726` and the
  output hash is
  `5f6ff0fda2c4c39dc4e689a00055de0a4f86a02e0d5f24ec6e63dbd72c38822d`.
- `N01ex` (`test` absent) and `N01ey` (a `0.76.0` row against `0.75.0`) are
  `E-FORM-001`; `N03zw` (`imm8 = 128`) and `N03zx` (`imm16 = 32768`) are
  `E-RANGE-001`.
- The x86 table grows to 615 forms. The corpus grows to 123 positives and 595
  negatives, and every form in `0.76.0` is named by a positive fixture
  (`check_definition.py`).
- `0.75.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **Add only the missing mnemonics at 64 bits.** Rejected: `addl $1, %eax` is
  a separate row with a different length, and leaving it out keeps the family
  unusable below 64 bits.
- **One row per mnemonic with an immediate-width modifier.** Rejected: the
  `83`/`81` opcode byte and the instruction length are template content, and a
  modifier must not write a template byte.
- **Add the 32/16-bit `%rax` short forms (`05`-family at `0x66`).** Rejected:
  they are a separate prefix/opcode window, and the plan leaves them out of
  this slice; they can be added later with their own vector.
- **Add `test`, `neg` and `not` now.** Rejected: their opcodes and operand
  roles differ (`test` has no destination), so each needs its own decision.
- **Add the memory forms now.** Rejected: `ModRM.mod != 11` adds `SIB` and
  displacement geometry; `S4` is the single memory slice of this round.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `0.75.0` has no immediate row for `and`/`or`/`xor`/`cmp`, and `add`/`sub` only at 64 bits | form-id scan of `definitions/x86_64/0.75.0.json` | high |
| The thirty-six instructions are 176 bytes and the two immediate widths differ | `llvm-mc` object bytes, `EXP-0113` §2 | high |
| `83 /r ib` and `81 /r id` (same value 1) decode to the same instruction at 64/32/16 bits | `llvm-mc -disassemble`, `EXP-0113` `direction.txt` | high |
| The four `%rax` short forms and the ModRM forms decode alike | `llvm-mc -disassemble`, `EXP-0113` `direction.txt` | high |
| `N01ex`/`N01ey` are `E-FORM-001`, `N03zw`/`N03zx` `E-RANGE-001` | fixture gate, `EXP-0113` | high |
| `0.76.0` repeats `0.75.0` unchanged | generator assertion and digest | high |

## Review triggers

- A memory shape (`ModRM.mod != 11`) is proposed; it adds `SIB`/displacement
  decisions and a different length.
- The 32/16-bit `%rax` short forms are proposed; they need the `0x66` byte and
  their own rows.
- `test`, `neg`, `not` or another ALU mnemonic is proposed; the opcode byte
  and the operand roles change and must be measured.
- An 8-bit immediate width is proposed; the byte-register windows change the
  prefix and need their own rows.
