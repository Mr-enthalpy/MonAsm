# ADR-0115: `mov` immediate, both shapes at 16/32 bits

- Status: accepted
- Date: 2026-11-10
- Settles: `X86-P83` (the five `mov` immediate rows and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-04` of `02_encoding_choices.md` (widened from the accumulator
  pair to the register-in-opcode pair, including `mov`), the reading-aid table
  and `0.77.0` paragraph of `07_definition_format.md` §8.1, the x86 table of
  `06_validation_matrix.md`, and the `S3` row of `10_m6_plan.md` (six rows
  become five); adds `definitions/x86_64/0.77.0.json`, `EXP-0114` and the
  `X86-P83`/`N01ez`/`N01fa`/`N03zy` fixtures

## Context

`0.76.0` has no `mov` row with an immediate slot. A plan that wants
`movl $300, %ecx` or `movq $300, %r8` has no form to name. The gap was already
recorded as a review trigger in `ADR-0093` and is the `S3` row of `ADR-0112`.

Two encodings exist for a register destination:

| Width | Register in opcode | ModRM | Notes |
|---|---|---|---|
| 16 | `66 B8+rw iw` | `66 C7 /0 iw` | both legal |
| 32 | `B8+rd id` | `C7 /0 id` | both legal |
| 64 | `REX.W B8+rd io` | `REX.W C7 /0 id` | the opcode form is `movabs`, not `id` |

`EXP-0114` measures the difference: `movl $300, %ebx` is `bb 2c 01 00 00`
(5 B) or `c7 c3 2c 01 00 00` (6 B), and `movw $300, %bx` is `66 bb 2c 01`
(4 B) or `66 c7 c3 2c 01` (5 B). Both pairs decode to the same instruction.
`llvm-mc` always picks the `B8+rd` shape for a 16/32-bit register destination,
so the `C7 /0` bytes are hand-derived and confirmed by `llvm-mc -disassemble`.

At 64 bits there is no `id` form of `B8+rd`: `movabsq $300, %rax` is `48 b8`
plus eight immediate bytes, while `movq $300, %rax` is `48 c7 c0 2c 01 00 00`.
`movabs` is explicitly out of scope in `ADR-0112`.

## Decision

1. **Five new rows, not six.** `0.77.0` appends:
   - `B8+rd` at 16 bits (`66 B8+rw iw`) and 32 bits (`B8+rd id`), two rows;
   - `C7 /0` at 16 bits (`66 C7 /0 iw`), 32 bits (`C7 /0 id`) and 64 bits
     (`REX.W C7 /0 id`), three rows.

   The plan's `REX.W B8+rd id` row is not an encoding: the `REX.W` opcode form
   takes `io`, which is `movabs`. The correction is recorded here and in the
   `S3` row of `10_m6_plan.md`; the round total becomes 82 new rows, x86
   564 → 632 and 841 forms.
2. **`EC-04` is widened, not duplicated.** The pair is already a named
   decision: `B8+rd` vs `C7 /0` appears in `EC-04` with `mov eax, 300` as its
   counterexample. The slice adds the measured 16/32-bit instances and the
   64-bit `movabs` exclusion; no new `EC` row, so the count stays 42.
3. **The naming keeps the operand roles.** `x86:mov/r<width>-imm<width>` puts
   the destination in the opcode's low three bits; `x86:mov/rm<width>-imm<width>`
   puts it in `ModRM.r/m`. This follows `mov/rm-r64` vs `mov/r64-rm`, where
   `r64` is the register outside `ModRM.r/m`.
4. **The field layout is the measured template with the fields zeroed.** The
   16-bit row is `[8,3]` + `[16,16]`, the 32-bit row `[0,3]` + `[8,32]`; the
   16-bit `C7` row is `[16,3]` + `[24,16]`, the 32-bit `C7` row `[8,3]` +
   `[16,32]`, and the 64-bit row `[0,1]` (REX.B) + `[16,3]` + `[24,32]`.
5. **The 16/32-bit rows stay three-bit.** `movl $300, %r8d` is
   `41 b8 2c 01 00 00` (6 B) and `movw $300, %r8w` is `66 41 b8 2c 01` (5 B):
   the extra `REX` byte changes the length, which a template cannot express.
   The 64-bit row folds `REX.B` into the `REX.W` byte it already has
   (`49 c7 c0 2c 01 00 00` for `%r8`), so it reaches `%r8`-`%r15`.
6. **`0.77.0` is additive and immutable.** It repeats the 615 `0.76.0` forms
   byte-for-byte, and the generator asserts the reproduction before it writes
   the new version. The digest is
   `sha256:093d8f3c0abefc04b9c9b4ed421412a1f9a1fe54bf430951653fac0955d4c68b`.

## Consequences

- `X86-P83-mov-imm` is the 54-byte vector of ten instructions: the `B8+rd` row
  at 16/32 bits with `$1` and `$300`, the `C7 /0` row at the same widths with
  the same values, and the 64-bit `C7` row at `%rbx` and `%r8`. The destination
  alternates between `%bx`/`%cx` (registers 3 and 1) so the opcode low bits and
  the `ModRM.r/m` field are shown to be operand-owned. The input hash is
  `04364e251bd0b46b5f4e4678a8496e85a34e2e469255921b7af1c86e676a36e2` and the
  output hash is
  `3e98bc659fe8805f36f7a07a598c4bc8143eeb7643072a9fc0a38e303c36ddf0`.
- The fixture's oracle is `manual+disassembly`: instructions 1-6 are the
  assembler's own selection, while instructions 7-10 are the `C7 /0` shapes
  that `llvm-mc` does not select for a register destination. The recorded
  `direction.txt` decodes both shapes to the same instruction text, and the
  fixture gate materializes the plan through the definition.
- `N01ez` (`movabs` absent) and `N01fa` (a `0.77.0` row against `0.76.0`) are
  `E-FORM-001`; `N03zy` (`imm32 = 2147483648`) is `E-RANGE-001`, because the
  value does not sign-extend into the 64-bit destination.
- The x86 table grows to 620 forms. The corpus grows to 124 positives and 598
  negatives, and every form in `0.77.0` is named by a positive fixture
  (`check_definition.py`).
- `0.76.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **Keep the plan's sixth row (`REX.W B8+rd id`).** Rejected: the encoding does
  not exist. `REX.W B8+rd` carries `io`; the six-byte/seven-byte `id` form is
  `C7 /0`, which the slice already has.
- **Add `movabs` (`REX.W B8+rd io`) now.** Rejected: it is a ten-byte
  instruction with an eight-byte immediate and its own range; `ADR-0112` keeps
  it out and the review trigger names it.
- **One row with an encoding selector.** Rejected: the opcode byte and the
  instruction length are template content. A selector is an implicit
  encoding-form choice (`INV-02`), and a modifier must not write a template
  byte.
- **Land only the 16/32-bit `B8+rd` rows.** Rejected: `C7 /0` is a legal
  encoding of the same instruction, and leaving it out would make the
  `EC-04` decision one-sided at those widths.
- **Add the 8-bit `B0`/`C6` windows now.** Rejected: the byte-register windows
  (`%spl`/`%ah` and the `REX` split) are a separate decision.
- **Add the memory `C7 /0` shapes now.** Rejected: `ModRM.mod != 11` adds
  `SIB` and displacement geometry; `S4` is the single memory slice.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `0.76.0` has no `mov` row with an immediate slot | form-id scan of `definitions/x86_64/0.76.0.json` | high |
| The ten instructions are 54 bytes | `llvm-mc` object bytes plus hand-derived `C7` bytes, `EXP-0114` §2 | high |
| `B8+rd` and `C7 /0` decode to the same instruction at 16/32 bits | `llvm-mc -disassemble`, `EXP-0114` `direction.txt` | high |
| `REX.W B8+rd` is `movabs` with an eight-byte immediate | `llvm-mc -show-encoding`, `EXP-0114` `direction.txt` | high |
| The 16/32-bit rows cannot reach `%r8`-`%r15` without a length change | `llvm-mc -show-encoding`, `EXP-0114` `direction.txt` | high |
| `N01ez`/`N01fa` are `E-FORM-001`, `N03zy` `E-RANGE-001` | fixture gate, `EXP-0114` | high |
| `0.77.0` repeats `0.76.0` unchanged | generator assertion and digest | high |

## Review triggers

- `movabs` (`REX.W B8+rd io`) is proposed; it needs an `imm64` slot and its own
  range and vector.
- The 8-bit `B0`/`C6` windows are proposed; the byte-register sets change the
  prefix and need their own rows.
- A memory destination (`ModRM.mod != 11`) is proposed; it adds `SIB`,
  displacement and a different length.
- The 16/32-bit `%r8`-`%r15` windows are proposed; they add a `REX` byte and
  therefore separate templates.
- The `mov` register/memory directions or the segment-register forms are
  proposed; each is a different opcode byte and needs its own decision.
