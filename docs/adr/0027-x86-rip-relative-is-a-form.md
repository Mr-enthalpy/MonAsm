# ADR-0027: A RIP-relative memory operand is a form with no base register

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P6` (RIP-relative reference) and the role of its displacement
- Supersedes: none
- Superseded by: none

## Context

`X86-P6` asks for one RIP-relative reference. `ADR-0008` settled that a memory
operand is one operand per encoded field and that the addressing shape is a
`form_id` variant, and it left `X86-P4`/`P6` out until each ModRM shape was
enumerated and measured. This ADR enumerates the one shape `X86-P6` needs.

The shape is `ModRM mod = 00`, `r/m = 101` in 64-bit mode. It does not name a
base register: the address is `RIP + disp32`, and `disp32` is the only field the
plan can supply. The same `r/m = 101` value is a base register under `mod = 01`
or `mod = 10`, which is why the measurement below uses `%rbp`:

| Source | Bytes | ModRM | Reading |
|---|---|---|---|
| `movq 0(%rip), %rax` | `48 8b 05 00 00 00 00` | `mod=00`, `r/m=101` | RIP + `disp32 = 0` |
| `movq 16(%rip), %rax` | `48 8b 05 10 00 00 00` | `mod=00`, `r/m=101` | RIP + `disp32 = 16` |
| `movq 16(%rip), %rcx` | `48 8b 0d 10 00 00 00` | `mod=00`, `r/m=101`, `reg=001` | the register is `ModRM.reg` |
| `movq -8(%rip), %rdx` | `48 8b 15 f8 ff ff ff` | `mod=00`, `r/m=101` | `disp32` is signed |
| `movq %rax, 16(%rip)` | `48 89 05 10 00 00 00` | `mod=00`, `r/m=101`, opcode `89` | the store direction is another opcode |
| `movq 0(%rbp), %rax` | `48 8b 45 00` | `mod=01`, `r/m=101` | the same `r/m` is `%rbp` here |
| `movq 0(%rsp), %rax` | `48 8b 04 24` | `mod=00`, `r/m=100` | `%rsp` needs a SIB byte |
| `movq 2147483647(%rip), %rax` | `48 8b 05 ff ff ff 7f` | `mod=00` | the top of `disp32` |
| `movq -2147483648(%rip), %rax` | `48 8b 05 00 00 00 80` | `mod=00` | the bottom of `disp32` |

`llvm-mc 23.1.2` rejects `movq 2147483648(%rip), %rax` and
`movq -2147483649(%rip), %rax` with
`displacement ... is not within [-2147483648, 2147483647]`, so the field is the
signed 32-bit `disp32`.

The failure this ADR prevents is not a wrong byte in one fixture. If the form
carried a `base` operand, RIP would need a register number it does not have in
`x86.gpr64`; if the base were omitted instead, "no base means RIP" would be a
default. The other direction is worse: a single `x86:mov/r64-mem` over
`base`/`disp` would have to read the base's value and choose `mod = 00` for a
RIP reference or `mod = 01`/`10` for a GPR, which is the value-driven form
selection `INV-02` forbids and `ADR-0008` measured on
`48 8b 41 08` vs `48 8b 81 00 10 00 00`.

The plan must also state where the displacement is measured from. For this
shape the reference is the byte after the instruction (`pcrel_end`): the
instruction is seven bytes, and the measured `movq L1(%rip), %rcx` with `L1`
at offset `0x20` in a section whose instruction starts at `7` is
`48 8b 0d 12 00 00 00`, because `0x20 - (7 + 7) = 0x12`. ELF's
`R_X86_64_PC32` spells the same value as an addend of `-4` at the field's
offset; our `pcrel_end` with `addend = 0` is the same arithmetic because the
field is the last field of the instruction.

## Decision

1. **`X86-P6` ships as two forms in `definitions/x86_64/0.2.0.json`:**
   `x86:mov/r64-riprel32/legacy` (`REX.W 8B /r`, load) and
   `x86:mov/riprel32-r64/legacy` (`REX.W 89 /r`, store). The opcode direction is
   the form, exactly as `rm-r64`/`r64-rm` are two forms (`ADR-0004`, `EC-27`).
2. **The variability is `disp32` only.** The template fixes `mod = 00` and
   `r/m = 101`; the load stores the destination in `ModRM.reg` at `[19,3]`, the
   store stores the source there, and both put `disp32` at `[24,32]`.
3. **The plan names the displacement with the `target` role, not `disp`.** The
   operand is `kind: x86.rel`, `target_type: riprel32`, signed `32` bits, and
   the slot is field content. The role is the one the contract already uses for
   a PC-relative displacement measured from an instruction boundary:
   `x86:jmp/rel32/legacy` and `aarch64:ldr/x64-imm19` both use `target`. A
   `disp` role would describe an offset from a `base` operand, and this shape
   has no base operand: RIP is not a GPR and no field carries its number. The
   form name says `riprel32`, so the missing base is stated by the form, not
   defaulted by the encoder.
4. **The fixup is `pcrel_end` with `addend = 0`.** The reference is the address
   after the instruction; because `disp32` is the last field, that is also the
   end of the field. The form does not declare the rule (the definition format
   has no per-form `pc_reference_rule` field); the plan states it, and the
   fixture pins the measured value. A plan that states `pcrel_begin` is
   internally consistent but describes a different arithmetic, exactly as it
   would for `jmp/rel32`; the digest records what was stated, not ISA truth.
5. **The `disp32` slot is signed `-2147483648…2147483647`.** A literal outside
   that interval is `E-RANGE-002` on the `target` operand; a fixup whose
   resolved displacement leaves the interval is `E-FIXUP-003`. Neither is
   truncated or re-formed.
6. **`r8`–`r15` stay out.** `ModRM.reg` is three bits and the template's `REX`
   byte is `0x48`; no extension bit is declared. Naming `r9` is
   `E-OPERAND-004`, as it is for the `0.1.0` rows.
7. **This does not admit the rest of x86 memory addressing.** `mod = 01`/`10`
   with a base register (`X86-P4`), SIB shapes, the `0x67` address-size prefix
   (`X86-P5`) and absolute `moffs` forms remain absent. Each still needs its
   own enumerated, measured variants.
8. **Only the 64-bit `REX.W` forms.** The 32-bit (no `REX.W`) and 16-bit
   (`0x66`) directions, and byte/word/dword data widths, are absent; naming one
   is `E-FORM-001`.

## Consequences

- `X86-P6` moves from deferred to passing with one positive fixture that
  exercises a literal displacement, a local `pcrel_end` resolution, the store
  direction, and an external relocation.
- A plan can now name a PC-relative data reference without inventing a base
  register, and the address form is still a `form_id` lookup.
- `EC-34` records the decision: the same `r/m = 101` is RIP under `mod = 00`
  and `%rbp` under `mod = 01`, so the shape cannot be inferred from the operand
  values.
- `EC-02`'s note that the v0 slice has no memory operand is no longer true; it
  is corrected, while disp8 vs disp32 stays unexercised until `X86-P4`.
- Cost: two more rows, one more definition document, and one more
  definition digest to pin. The base+disp forms still need their own ADR.

## Alternatives considered

- **One form with a `base` operand and a RIP sentinel (`{reg: 16}`).** Rejected:
  RIP is not in `x86.gpr64`, the sentinel is a magic value outside the register
  file, and the `r/m` field would then carry a register number in one shape and
  a shape marker in another.
- **One form with an optional base (omitted means RIP).** Rejected: an absent
  operand is a default, and `INV-07` requires illegal or incomplete input to
  fail rather than be completed. It would also make `[rip]` and `[base]`
  indistinguishable without reading values.
- **Model the displacement as `disp` with a `base` operand fixed to a new
  `x86.rip` kind.** Rejected for v0: it adds a register class with one member
  and a base slot that owns no bit, to say what the form name already says.
- **Emit `A0–A3` (`moffs`) instead.** Rejected: a different absolute-addressing
  form with different length and semantics (`EC-05`), not a PC-relative
  reference.
- **Let the encoder pick `pcrel_begin` or `pcrel_end` from the form.** Rejected:
  that is a second decision outside the plan; the rule stays in the fixup, the
  same as every existing PC-relative row.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The nine byte strings in Context | `llvm-mc 23.1.2`, `EXP-0029` §2 | high |
| `disp32` is signed 32-bit | `llvm-mc 23.1.2` diagnostics at both ends, `EXP-0029` §3 | high |
| `mod=00`, `r/m=101` is RIP-relative in 64-bit mode | measured bytes plus the ModRM rule; the rule itself is from the ISA manual, not re-read here (`ADR-0008` §Evidence) | high for the bytes, medium for the prose rule |
| The displacement is measured from the end of the instruction | `EXP-0029` §4: `L1` at `0x20`, instruction at `7`, bytes `12 00 00 00` | high |
| ELF's `-4` is the same value as `pcrel_end` with addend 0 | `EXP-0029` §4: `R_X86_64_PC32 ext 0xFFFFFFFFFFFFFFFC` at field offset `0x27` | high |
| `r8`–`r15` are not encodable by the declared 3-bit field | `07_definition_format.md` §8.1 and `N14`; no new measurement | high (consequence of the field width) |
| Base+disp8/disp32 and SIB shapes are still absent | no rows in any x86 document; `X86-P4` still deferred | high |

## Review triggers

- `X86-P4` or `X86-P5` is attempted: the base+disp and SIB variant list must be
  enumerated and measured, and this ADR's two rows must not be widened to cover
  them.
- A plan needs an `x86.rel` operand whose reference point is not the
  instruction end (for example a `0x67` EIP-relative form).
- The definition format gains a per-form `pc_reference_rule` declaration; the
  limitation in decision 4 would then be removed rather than inherited.
