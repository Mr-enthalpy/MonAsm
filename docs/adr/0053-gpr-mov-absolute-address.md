# ADR-0053: The 64-bit GPR `mov` rows take a 32-bit absolute address and refuse `moffs`

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P30` (the absolute `SIB = 25` shape under the 64-bit GPR
  `mov` opcodes), and freezes `EC-05`
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0052` §Review triggers (the GPR absolute shape it named);
  `EC-05` (from `draft` to `frozen`)

## Context

`ADR-0052` gave the EVEX `vmovaps` family an absolute address and named the
same shape one opcode family over as its last review trigger. The GPR `mov`
rows already carry a base, a `SIB` shape and a RIP-relative shape; the
absolute address is the fourth way to write `[0x1234]`, and the only one
where the mnemonic has a second legal encoding.

Five facts come out of the measurements in `EXP-0055`:

1. **The address is `ModRM = 04` and `SIB = 25` again.** `movq 0x1234, %rax`
   is `48 8b 04 25 34 12 00 00` and `movq %rax, 0x1234` is
   `48 89 04 25 34 12 00 00` — eight bytes, the same `mod = 00`, `r/m = 100`
   escape and the same constant `SIB` as the EVEX rows, with the four-byte
   field at template bits 32–63.
2. **The register is `ModRM.reg` plus `REX.R`, written raw.** `REX.W` is
   template bit 3 of byte 0, so the low registers keep `48`; the fourth
   register bit is `REX.R` at `[2,1]`, so `%r8` is `4c 8b 04 25 …` and `%r15`
   is `4c 8b 3c 25 …`, while `%rax` writes `04` and `%rdi` writes `3c` in
   `ModRM`. Both directions use the same window: `movq %r8, 0x1234` is
   `4c 89 04 25 …` and `movq %r10, 0x1234` is `4c 89 14 25 …`.
3. **`moffs` is a second legal encoding, and it is longer.** `movabsq
   0x1234, %rax` is `48 a1 34 12 00 00 00 00 00 00` and `movabsq %rax,
   0x1234` is `48 a3 34 12 00 00 00 00 00 00` — ten bytes, an `A0`–`A3`
   opcode with an eight-byte address, against the eight-byte `SIB` form.
4. **`llvm-mc` picks the form from the value.** `movq 0x80000000, %rax`
   assembles to `48 a1 00 00 00 00 80 00 00 00` — the assembler silently
   switches to `moffs` when the address does not fit the signed 32-bit field.
   A plan that carries `2147483648` on the `abs32` row is `E-RANGE-001`, never
   a switch to another row (`INV-02`, `INV-07`).
5. **The other widths are the same shape with different prefixes, and the
   32-bit one is not a single row.** `movl 0x1234, %eax` is
   `8b 04 25 34 12 00 00` (seven bytes), `movw` is `66 8b 04 25 …` and
   `movb` is `8a 04 25 …`; but `movl 0x1234, %r8d` is
   `44 8b 04 25 34 12 00 00` (eight bytes), because the REX byte exists only
   for the high registers. That length decision is a separate slice.

The measurements are `llvm-mc` 23.1.2 on 2026-11-06; every measured
`SIB`-absolute byte string round-trips through `llvm-mc -disassemble` to the
same address.

## Decision

**`0.26.0` appends two rows, one per direction, for the 64-bit GPR `mov`
family with a 32-bit absolute address. The `moffs` encoding is not a row:
`EC-05` is frozen with the `form variant` carrier, so a plan names the
`abs32` form and has no way to ask for `A0`–`A3`.**

| Direction | `form_id` | Template | Length |
|---|---|---|---|
| load | `x86:mov/r64-abs32/legacy` | `48 8b 04 25 00 00 00 00` | 8 bytes |
| store | `x86:mov/abs32-r64/legacy` | `48 89 04 25 00 00 00 00` | 8 bytes |

Five properties follow:

- **`REX.W` and the `SIB` byte are template constants.** `04` and `25` are
  the same bytes the EVEX rows use, `r/m = 100` spends the `SIB` escape and
  `SIB.base = 101` at `mod = 00` is the `disp32` request, so the address is
  mandatory and four bytes wide even when it is `0`.
- **The register slot is four bits, raw.** `[19,3]` carries the low three and
  `[2,1]` the `REX.R` bit, with no `invert`; a `gpr64` value above `15` is
  `E-OPERAND-004` (`N14z`).
- **The operand sequence is `dest`/`src`, `disp`.** A supplied `base` or
  `index` is `E-OPERAND-002` (`N02ah`), and the address carried as `disp8`
  is `E-OPERAND-001` on `target_type` (`N02ai`).
- **The address is signed 32-bit content.** `2147483648` is `E-RANGE-001`
  (`N03m`), the refusal the EVEX rows already apply.
- **`moffs` is not reachable.** Naming `x86:mov/r64-moffs64/legacy` is
  `E-FORM-001` (`N01bf`); the table never hands the choice to the
  materializer, even though `llvm-mc` makes it for `0x80000000`.

## Consequences

- `0.26.0` is a 239-form document.
- Its positive fixture `X86-P30-gpr-mov-abs32` has six instructions and 48
  bytes: both directions at `%rax` and `%r15`, plus the signed ends.
- Negatives pin the version boundary in both directions (`N01bd`, `N01be`),
  the absent `moffs` row (`N01bf`), a supplied `base` (`N02ah`), a `disp8`
  address (`N02ai`), the past-the-end content (`N03m`) and the register field
  end (`N14z`).
- `EC-05` moves from `draft` to `frozen`: its carrier is the `form_id`
  (`-abs32` present, `moffs` absent) and its counterexample is the
  ten-byte `movabsq` beside the eight-byte `movq`, plus the value-driven
  switch `llvm-mc` performs for `0x80000000`.
- No schema, loader or materializer change: the row is a template with a
  register slot and a signed displacement slot, both already supported.
- `02_encoding_choices.md` gains the two surface rows, revises `EC-05` and
  revises `EC-35`/`EC-37` where they describe the address shape.
- Still absent: the 32-bit `-ext` shape (`44 8b 04 25 …` versus
  `8b 04 25 …`), the 16- and 8-bit absolute rows (prefix and byte-set slices),
  the `0x67` address-size prefix, a symbol in the address, and the absolute
  address under the SSE and EVEX opcodes at other mnemonic bytes.

## Alternatives rejected

- **Add a `moffs` row beside the `SIB` row.** Two rows would encode the same
  source instruction at two lengths and the plan would have to pick, which is
  the choice `INV-02` forbids; the plan names a length-bearing row or nothing.
- **Let the materializer switch to `moffs` when the value does not fit.**
  That is what `llvm-mc` does for `0x80000000`, and it makes a field value
  change the form and the length (`INV-04`, `INV-07`).
- **Widen `disp32` to unsigned so `0x80000000` fits.** The field is signed
  bytes; the same address written as `-2147483648` produces `00 00 00 80`,
  so the unsigned reading would be a second spelling of one field content.
- **Reuse the RIP-relative or base rows with an omitted register.** An
  operand may not be optional, and `ModRM.rm = 101` means `RIP + disp32`,
  not an absolute address.
- **Add the 32-bit rows in the same slice.** They need a second form for
  `r8d`–`r15d`, because the REX byte only exists for those registers; that is
  a length decision, not a field decision, and it gets its own ADR.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `48 8b 04 25 34 12 00 00` and `48 89 04 25 34 12 00 00` | `llvm-mc -show-encoding`, `EXP-0055` §1 | high |
| `SIB = 25` with `ModRM = 04` at bits 16–23, `disp32` at 32–63 | the byte strings; `EXP-0055` §2 | high |
| `REX.R` at `[2,1]`, raw, for `%r8`/`%r15`/`%r9`/`%r10` | `llvm-mc -show-encoding`, `EXP-0055` §2 | high |
| `movabsq` is `48 a1`/`48 a3` with an eight-byte address | `llvm-mc -show-encoding`, `EXP-0055` §3 | high |
| `llvm-mc` switches to `moffs` for `0x80000000` | `llvm-mc` output, `EXP-0055` §3 | high |
| 32-bit high registers need `44 8b …` | `llvm-mc` output, `EXP-0055` §4 | high |
| `%r16` needs the APX `d5` prefix, outside the 4-bit field | `llvm-mc` output, `EXP-0055` §4 | high |

## Review triggers

- The 32-bit absolute rows are attempted: the `r8d`–`r15d` case needs a
  `-ext` form because the `REX` byte appears only for those registers.
- The 16- or 8-bit absolute rows are attempted: `66 8b` and the three
  `movb` register sets decide the row shape, and `movb %ah, 0x1234` is
  `88 24 25 …` with no `REX` byte.
- A symbol or relocation in the address is requested (`R_X86_64_32`,
  `R_X86_64_32S`): the field stops being content.
- `movabs`/`moffs` is requested for a width the table does not carry: it
  re-opens `EC-05` as a new row rather than a second spelling.
- The `0x67` prefix is attempted: the same fields read as a 32-bit address.
- The absolute address under the other x86 opcode families is attempted
  (`add`, `cmp`, the SSE and EVEX families at other mnemonics).
