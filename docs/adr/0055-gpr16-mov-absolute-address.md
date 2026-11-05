# ADR-0055: The 16-bit `mov` rows take an absolute address behind the `66` prefix

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P32` (the absolute `SIB = 25` shape under the 16-bit GPR `mov`
  opcodes, low and extended register windows)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0054` §Review triggers (the 16-bit absolute shape it named);
  `EC-02` (the displacement widths, extended to this opcode family);
  `EC-38` (the register window, extended to the word rows)

## Context

`ADR-0054` gave the 32-bit `mov` rows a 32-bit absolute address and made the
register window a `form_id` component. The 16-bit rows need the same address,
but they already spend one byte on the operand-size prefix `66`, and they
already have a five-bit reach in the encoding: `REX.R` is available even though
`REX.W` is not. `EXP-0057` measures how the two windows sit behind that prefix.

Five facts come out of the measurement:

1. **The low window is eight bytes and still has no `REX` byte.** `movw
   0x1234, %ax` is `66 8b 04 25 34 12 00 00` and `movw %ax, 0x1234` is
   `66 89 04 25 34 12 00 00`. The `66` is template bit 0, the opcode is at
   `[8,8]`, `ModRM = 04` at `[16,8]`, `SIB = 25` at `[24,8]` and the address at
   `[32,32]`. `ModRM.reg` at `[19,3]` carries `%ax`–`%di`, so
   `movw 0x1234, %sp` is `66 8b 24 25 34 12 00 00`.
2. **The extended window is nine bytes and spends `REX = 44` after the
   prefix.** `movw 0x1234, %r8w` is `66 44 8b 04 25 34 12 00 00` — `66` at
   `[0,8]`, `REX` at `[8,8]`, the opcode at `[16,8]`, `ModRM` at `[24,8]`,
   `SIB` at `[32,8]` and the address at `[40,32]`. `REX.W = 0` and
   `REX.R = 1`; both directions agree (`movw %r8w, 0x1234` is
   `66 44 89 04 25 34 12 00 00`, and `movw -1, %r15w` is
   `66 44 8b 3c 25 ff ff ff ff`).
3. **The address is still a signed 32-bit field, not a 16-bit one.** `-32768`
   is `00 80 ff ff` and `0x7fff` is `ff 7f 00 00`; the `66` prefix names the
   operand width and never narrows the address.
4. **`0x80000000` leaves the row.** `movw 0x80000000, %ax` assembles to
   `movabsw` (`66 a1` plus an eight-byte address, ten bytes), so the row keeps
   `disp32` signed content and the content one past the signed end is a
   refusal, never a form switch (`EC-05`).
5. **`%r16w` is outside the field.** `movw 0x1234, %r16w` is
   `66 d5 40 8b 04 25 34 12 00 00` — an APX `d5` prefix between `66` and the
   opcode, ten bytes, a different shape this slice does not carry.

All fourteen measured byte strings round-trip through `llvm-mc -disassemble`
to the same address; the measurement is `llvm-mc` 23.1.2 on 2026-11-06.

## Decision

**`0.28.0` appends four rows: load and store in the low and extended 16-bit
register windows. The window is a `form_id` component, so the plan names the
length it wants and no field value chooses it.**

| Direction | Window | `form_id` | Template | Length |
|---|---|---|---|---|
| load | low | `x86:mov/r16-abs32/legacy` | `66 8b 04 25 00 00 00 00` | 8 bytes |
| load | ext | `x86:mov/r16-ext-abs32/legacy` | `66 44 8b 04 25 00 00 00 00` | 9 bytes |
| store | low | `x86:mov/abs32-r16/legacy` | `66 89 04 25 00 00 00 00` | 8 bytes |
| store | ext | `x86:mov/abs32-r16-ext/legacy` | `66 44 89 04 25 00 00 00 00` | 9 bytes |

Five properties follow:

- **`66` is template bit 0 in all four rows.** The operand width is a byte in
  the template, not a decision the materializer makes from a register kind.
- **The low rows have no `REX` byte.** `ModRM` sits at `[16,8]`, `SIB` at
  `[24,8]` and the address at `[32,32]`. The register slot is the three-bit
  `ModRM.reg` at `[19,3]`, so its value set is `0`–`7` by construction and `8`
  is `E-OPERAND-004`, not a second window.
- **The ext rows insert `REX = 44` between the prefix and the opcode.** `66`
  stays at `[0,8]`, `REX` at `[8,8]`, and everything after it moves one byte
  later; the register is four bits wide — `[27,3]` plus `REX.R` at `[10,1]` —
  with `excluded: [0,1,2,3,4,5,6,7]`, so the template's `REX.R = 1` cannot be
  contradicted by an operand.
- **`ModRM = 04` and `SIB = 25` are template constants in all four rows.** The
  address is mandatory and four bytes wide even when it is `0`, exactly as at
  32- and 64-bit width.
- **The address is signed 32-bit content.** `2147483648` is `E-RANGE-001`, and
  a supplied `base` or a `disp8` address is `E-OPERAND-002` /
  `E-OPERAND-001`, the refusals the narrower rows already apply.

## Consequences

- `0.28.0` is a 247-form document, byte-reproducing every `0.27.0` row.
- Its positive fixture `X86-P32-gpr16-mov-abs32` has six instructions and 51
  bytes: both directions at a low and an extended register, plus the signed
  ends. The `66` prefix is one byte in every row and the window is the other
  difference.
- Negatives pin the version boundary in both directions (`N01bi`, `N01bj`),
  a supplied `base` (`N02am`), a `disp8` address (`N02an`), a 32-bit register
  on a 16-bit row (`N02ao`), the past-the-end content (`N03o`), the register
  field end (`N14ab`) and the excluded low window on the ext row (`N16ae`).
- `EC-02` is revised in place: its displacement-width sentence now reaches this
  family. `EC-38` is revised in place: the word rows join the register-window
  split with a `REX` byte that costs nine bytes rather than eight.
- No schema, loader or materializer change: the rows are templates with a
  register slot and a signed displacement slot, both already supported.
- Still absent: the 8-bit absolute rows (the three `movb` register sets), the
  `0x67` address-size prefix, a symbol in the address, `moffs` for this width,
  the APX `d5` register window, and the absolute address under the other x86
  opcode families.

## Alternatives rejected

- **Add only the `-ext` rows.** The low window would stay unnameable, so
  `movw 0x1234, %ax` could not be planned at all and the eight-byte length
  would have no row to choose.
- **Make one row with a four-bit register slot and an optional `REX` byte.**
  The byte's presence would depend on the operand value, so the row's length
  would stop being a template fact (`INV-04`).
- **Treat the address as 16-bit content because the operand is 16 bits.** The
  measurement contradicts it: `-32768` is `00 80 ff ff`, a sign-extended
  32-bit field.
- **Reuse the 32-bit rows with a 16-bit register kind.** That is
  `E-OPERAND-001` on `kind` and `target_type` (`N02ao`), and `66` would have
  to be inserted from the operand width.
- **Let `%r16w` fall through to the `d5` prefix.** The prefix is a different
  template, not a wider field, and reaching for it would make the length
  depend on the register number.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 8b 04 25 34 12 00 00` and `66 89 04 25 34 12 00 00` | `llvm-mc -show-encoding`, `EXP-0057` §1 | high |
| `66 44 8b 04 25 …` and `66 44 89 04 25 …` for `%r8w` | `llvm-mc -show-encoding`, `EXP-0057` §1 | high |
| `66` at `[0,8]`, `REX.R` at `[10,1]`, `ModRM.reg` at `[27,3]` | the byte strings; `EXP-0057` §2 | high |
| the address is signed 32-bit content (`-32768` → `00 80 ff ff`) | `llvm-mc -show-encoding`, `EXP-0057` §2 | high |
| `0x80000000` switches to `movabsw` | `llvm-mc -show-encoding`, `EXP-0057` §2 | high |
| `%r16w` needs the APX `d5` prefix | `llvm-mc` output, `EXP-0057` §4 | high |

## Review triggers

- The 8-bit absolute rows are attempted: the three `movb` register sets decide
  the row shape, and `movb %ah, 0x1234` is `88 24 25 …` with no `REX` byte.
- A symbol or relocation in the address is requested (`R_X86_64_32`,
  `R_X86_64_32S`): the field stops being content.
- `moffs` is requested for this width: it re-opens `EC-05` as a new row at
  `66 a1`/`66 a3`, ten bytes.
- The `0x67` prefix is attempted: the same fields read as a 32-bit address.
- The 16-bit `-ext` shape is combined with an extended base: `REX.B` and
  `REX.R` share one byte, and the combination changes the fixture surface.
- The absolute address under the other x86 opcode families is attempted.
