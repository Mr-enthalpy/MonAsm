# EXP-0029 — x86-64 RIP-relative memory operands

- Date: 2026-11-05
- Question: what does `ModRM mod = 00`, `r/m = 101` encode in 64-bit mode, which
  field carries the register, how wide and signed is the displacement, and what
  does `llvm-mc` refuse?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: none. The field layout is read off the measured bytes and
  the ModRM rule already recorded in `ADR-0008`; the rule itself is from the ISA
  manual and was not re-read for this slice.
- Fixture oracle: `EXP-0005` (regenerated with `P6.asm` added)

## 1. The shape

`ModRM` is the byte after the opcode. For `movq 16(%rip), %rax` the measured
ModRM is `0x05`:

| Bits | Value | Meaning |
|---|---|---|
| 7–6 | `00` | `mod = 00` |
| 5–3 | `000` | `reg = 000` — the destination register |
| 2–0 | `101` | `r/m = 101`, which under `mod = 00` is RIP + `disp32` |

The instruction is seven bytes: `REX.W` (`0x48`), opcode `0x8B` (load) or
`0x89` (store), `ModRM`, then four displacement bytes. The displacement is the
last field, so the end of the field is the end of the instruction — the
reference point `pcrel_end` names. `r/m = 101` under `mod = 01` or `mod = 10`
is `%rbp`, which is why the form may not be inferred from the ModRM byte alone.

Two forms, one per opcode direction:

| `form_id` | Bytes | Slots |
|---|---|---|
| `x86:mov/r64-riprel32/legacy` | `48 8B 05 disp32` | `dest` at `[19,3]`; `target` at `[24,32]` |
| `x86:mov/riprel32-r64/legacy` | `48 89 05 disp32` | `src` at `[19,3]`; `target` at `[24,32]` |

The fixed `mod`/`r/m` bits are template, not operands; the plan cannot request a
different ModRM shape through either row.

## 2. The fields, measured

One instruction per run at offset 0, `llvm-mc -show-encoding`; the bytes are the
encoding column:

| Source | Encoding | Reading |
|---|---|---|
| `movq 0(%rip), %rax` | `48 8b 05 00 00 00 00` | `disp32 = 0` |
| `movq 16(%rip), %rax` | `48 8b 05 10 00 00 00` | `disp32 = 16`, `reg = 0` |
| `movq 16(%rip), %rcx` | `48 8b 0d 10 00 00 00` | `reg = 1` puts `rcx` in the destination |
| `movq -8(%rip), %rdx` | `48 8b 15 f8 ff ff ff` | `disp32 = -8`, two's complement |
| `movq %rax, 16(%rip)` | `48 89 05 10 00 00 00` | store direction, same ModRM |
| `movq 0(%rbp), %rax` | `48 8b 45 00` | `mod = 01`, `r/m = 101` is `%rbp` |
| `movq 0(%rsp), %rax` | `48 8b 04 24` | `r/m = 100` needs a SIB byte |
| `movq 2147483647(%rip), %rax` | `48 8b 05 ff ff ff 7f` | top of the signed range |
| `movq -2147483648(%rip), %rax` | `48 8b 05 00 00 00 80` | bottom of the signed range |

The first five rows differ only in the `ModRM.reg` field or in `disp32`; the
`mod`/`r/m` bits stay `00 101`. The `%rbp` and `%rsp` rows are the
counterexamples: the same mnemonic with a base register reaches a different
ModRM shape, and `%rsp` adds a byte that the RIP form does not have.

## 3. What the assembler rejects

| Source | Diagnostic |
|---|---|
| `movq 2147483648(%rip), %rax` | `displacement 2147483648 is not within [-2147483648, 2147483647]` |
| `movq -2147483649(%rip), %rax` | `displacement -2147483649 is not within [-2147483648, 2147483647]` |

Both are one past the two measured endpoints, so the field is a signed 32-bit
displacement and not an unsigned one.

## 4. The vector

Input `P6.asm` (LF, trailing newline; 160 bytes,
`sha256:f61542efebf930f78ddfd4a138125a22bcd257aab5b82209f92ca774d21f982f`):

```text
    movq 16(%rip), %rax
    movq L1(%rip), %rcx
    .space 2
    movq %rdx, L1(%rip)
    .space 9
L1:
    .byte 0xaa, 0xbb, 0xcc, 0xdd
    movq ext(%rip), %rbx
```

The layout is deliberate: `L1` sits at offset `0x20`, so the two local
displacements are non-zero and differ from each other, and the literal
displacement is a third value. The four data bytes make `L1` a real location
rather than a label on an instruction boundary.

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | `48 8b 05 10 00 00 00` | literal `disp32 = 16` |
| 7 | `48 8b 0d 12 00 00 00` | `L1` at `0x20`, instruction ends at `0x0e`, disp `0x12` |
| 14 | `00 00` | fill |
| 16 | `48 89 15 09 00 00 00` | store to `L1`, instruction ends at `0x17`, disp `0x09` |
| 23 | nine `00` bytes | fill |
| 32 | `aa bb cc dd` | `L1` |
| 36 | `48 8b 1d 00 00 00 00` | `ext`, relocation, disp field zeroed |

Output: 43 bytes,
`sha256:1e70735cff06ee7a57c34709753ea715ac9098f5c4d8bcb650804eb8c04709bf`,
`bytes_hex`
`488b0510000000488b0d12000000000048891509000000000000000000000000aabbccdd488b1d00000000`.

`llvm-readobj --relocations` on the object file reports

```text
0x27 R_X86_64_PC32 ext 0xFFFFFFFFFFFFFFFC
```

`0x27` is the `disp32` field of the instruction at `0x24` (`0x24 + 3`), and
`-4` is the field-relative spelling of the same value our `pcrel_end` with
`addend = 0` computes (`03_fixup_model.md` §6.1). The fixture's oracle record
therefore has `records = 1`.

## 5. What this fixes, and what it does not

Fixes:

- the two templates and the two field placements: `dest`/`src` in
  `ModRM.reg` at `[19,3]`, `disp32` at `[24,32]`;
- the role of the displacement: `target`, `x86.rel`/`riprel32`, signed 32 bits,
  because the form has no base register and the reference is PC-relative
  (`ADR-0027`);
- the reference point: `pcrel_end`, measured on the two local labels;
- the negative evidence: the same form against `0.1.0` is `E-FORM-001`, an
  extra `base` operand is `E-OPERAND-002`, `disp32 = 2147483648` is
  `E-RANGE-002`, and an operand symbol that disagrees with the fixup target is
  `E-FIXUP-001`.

Does not fix:

- **base + disp8/disp32 (`X86-P4`).** `mod = 01`/`10`, the `%rbp` special case
  and the SIB exclusion for `%rsp`/`%r12` are still absent. They need their own
  enumerated variant list and their own ADR.
- **the `0x67` address-size prefix (`X86-P5`).** EIP-relative addressing is a
  different reference width and a different form.
- **absolute `moffs` and SIB-based addressing.** `EC-05` is still `draft`.
- **`r8`–`r15`.** `ModRM.reg` is three bits and the template's `REX` byte is
  `0x48`; no `REX.R`/`REX.B` slot exists, so a plan naming `r9` is
  `E-OPERAND-004`.
- **byte/word/dword data widths.** Only `REX.W` qword moves are in the slice.

## 6. Result

The rows ship in `definitions/x86_64/0.2.0.json`, which repeats the seven
`0.1.0` forms and adds two:

```text
definition  definitions/x86_64/0.2.0.json
namespace   monasm.isa.x86
version     0.2.0
forms       9
digest      sha256:d9c088cacb9d20dcf8b801cbdb978996ed31d2e70b631897a905d179207991ac
```

`EXP-0004` §4 and `07_definition_format.md` §8 record the digest; `EXP-0005`
§2 records the regenerated fixture.

Our materializer emits the 43 bytes above and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `X86-P6-rip-relative` | four instructions: literal, local load, local store, external load | 43 bytes, `sha256:1e70735c…`, one record |
| `N01x-absent-riprel-form` | the load form against `0.1.0` | `E-FORM-001` |
| `N02j-base-on-riprel-form` | `dest`/`base`/`target` on the two-slot form | `E-OPERAND-002` (`expected: 2`, `found: 3`) |
| `N04e-riprel32-literal-out-of-range` | `disp32 = 2147483648` | `E-RANGE-002` |
| `N07b-riprel-operand-fixup-mismatch` | operand names `S1`, fixup targets `S2` | `E-FIXUP-001` |
