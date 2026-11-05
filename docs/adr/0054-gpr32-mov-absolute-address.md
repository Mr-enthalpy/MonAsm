# ADR-0054: The 32-bit `mov` rows take an absolute address in two register windows

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P31` (the absolute `SIB = 25` shape under the 32-bit GPR `mov`
  opcodes, low and extended register windows)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0053` §Review triggers (the 32-bit `-ext` shape it named);
  `EC-38` (the register-window split, revised in place)

## Context

`ADR-0053` gave the 64-bit GPR `mov` family a 32-bit absolute address and made
the `REX` byte a template constant, because `REX.W` is always present. The
32-bit family cannot do that: `REX` is not required for `%eax`–`%edi`, but it
*is* required for `%r8d`–`%r15d`, so the same source instruction has two legal
lengths depending on the register. That is the window split `EC-38` records,
and until both halves are rows the split is only half reachable.

`EXP-0056` measures four facts:

1. **The low window is seven bytes with no `REX` byte.** `movl 0x1234, %eax` is
   `8b 04 25 34 12 00 00` and `movl %eax, 0x1234` is
   `89 04 25 34 12 00 00` — opcode, `ModRM = 04`, `SIB = 25`, four bytes of
   address. `ModRM.reg` at `[11,3]` carries `%eax`–`%edi`, so
   `movl -2147483648, %edi` is `8b 3c 25 00 00 00 80` and
   `movl 0x1234, %esp` is `8b 24 25 34 12 00 00`.
2. **The extended window is eight bytes and sets `REX.R` alone.** The same
   load at `%r8d` is `44 8b 04 25 34 12 00 00`: one `REX` byte with
   `REX.R = 1` and `REX.W = 0`, then the same opcode, `ModRM`, `SIB` and
   address. `%r12d`–`%r15d` write `24`–`3c` in `ModRM`:
   `44 8b 24 25 …`, `44 8b 2c 25 …`, `44 8b 34 25 …`,
   `44 8b 3c 25 …`. Both directions agree: `movl %r8d, 0x1234` is
   `44 89 04 25 34 12 00 00` and `movl %r10d, 0x0` is
   `44 89 14 25 00 00 00 00`.
3. **The address is the same four bytes at both lengths.** `0` is four zero
   bytes, `-1` is `ff ff ff ff`, `0x7fffffff` is `ff ff ff 7f` and
   `-2147483648` is `00 00 00 80`, identically in the low and extended
   windows; the length difference is the `REX` byte, never the field.
4. **The ext window's value set is closed.** `%eax` cannot appear in the
   extended row (its `REX.R = 1` template would encode `%r8d`), so the
   extended register slot excludes `0`–`7` and `movl 0x1234, %eax` on that row
   is `E-RANGE-004`. `%r16d` is outside the four-bit field in either window
   (`llvm-mc` reaches for the APX `d5` prefix), so it is `E-OPERAND-004`, and
   in the low window the three-bit field already stops at `%edi`.

All fourteen measured byte strings round-trip through `llvm-mc -disassemble`
to the same address; the measurement is `llvm-mc` 23.1.2 on 2026-11-06.

## Decision

**`0.27.0` appends four rows: load and store in the low window and in the
extended window. The window is a `form_id` component, so a plan names the
length it wants and no field value chooses it.**

| Direction | Window | `form_id` | Template | Length |
|---|---|---|---|---|
| load | low | `x86:mov/r32-abs32/legacy` | `8b 04 25 00 00 00 00` | 7 bytes |
| load | ext | `x86:mov/r32-ext-abs32/legacy` | `44 8b 04 25 00 00 00 00` | 8 bytes |
| store | low | `x86:mov/abs32-r32/legacy` | `89 04 25 00 00 00 00` | 7 bytes |
| store | ext | `x86:mov/abs32-r32-ext/legacy` | `44 89 04 25 00 00 00 00` | 8 bytes |

Five properties follow:

- **The low rows have no `REX` byte at all.** `ModRM` sits at `[8,8]`, `SIB` at
  `[16,8]` and the address at `[24,32]`. The register slot is exactly the
  three-bit `ModRM.reg` field, so its value set is `0`–`7` by construction and
  `8` is `E-OPERAND-004` rather than a second window.
- **The ext rows spend one byte on `REX = 44`.** `REX.W = 0`, `REX.R = 1`,
  `REX.X = 0`, `REX.B = 0`; `ModRM` moves to `[16,8]`, `SIB` to `[24,8]` and
  the address to `[32,32]`. The register is four bits wide — `[19,3]` plus
  `REX.R` at `[2,1]` — with `excluded: [0,1,2,3,4,5,6,7]`, so the template's
  `REX.R = 1` cannot be contradicted by an operand.
- **`ModRM = 04` and `SIB = 25` are template constants in all four rows.**
  `r/m = 100` spends the `SIB` escape, `SIB.index = 100` is "no index" and
  `SIB.base = 101` at `mod = 00` requests `disp32`, so the address is mandatory
  and four bytes wide even when it is `0`.
- **The operand sequence is `dest`/`src`, `disp`.** A supplied `base` is
  `E-OPERAND-002` (`N02aj`), the address carried as `disp8` is
  `E-OPERAND-001` on `target_type` (`N02ak`), and a `gpr64`/`r64` operand on an
  `r32` row is `E-OPERAND-001` on both `kind` and `target_type` (`N02al`).
- **The address is signed 32-bit content.** `2147483648` is `E-RANGE-001`
  (`N03n`), the refusal the 64-bit rows already apply.

## Consequences

- `0.27.0` is a 243-form document, byte-reproducing every `0.26.0` row.
- Its positive fixture `X86-P31-gpr32-mov-abs32` has six instructions and 45
  bytes: both directions at a low and an extended register, plus the signed
  ends. It is the first fixture whose instructions are not all one length.
- Negatives pin the version boundary in both directions (`N01bg`, `N01bh`),
  a supplied `base` (`N02aj`), a `disp8` address (`N02ak`), a 64-bit register
  on a 32-bit row (`N02al`), the past-the-end content (`N03n`), the register
  field end (`N14aa`) and the excluded low window on the ext row (`N16ad`).
- `EC-38` is revised in place: its window split now has both halves as rows,
  and the length difference is observable in one fixture.
- No schema, loader or materializer change: the rows are templates with a
  register slot and a signed displacement slot, both already supported.
- `02_encoding_choices.md` gains the four surface rows and revises `EC-38`
  where it describes the window split.
- Still absent: the 16- and 8-bit absolute rows (`66 8b`, the three `movb`
  register sets), the `0x67` address-size prefix, a symbol in the address,
  `moffs` for this width, and the absolute address under the other x86 opcode
  families.

## Alternatives rejected

- **Add only the `-ext` rows.** The low window would stay unnameable, so
  `movl 0x1234, %eax` could not be planned at all and the seven-byte length
  would have no row to choose.
- **Add only the low rows and let `%r8d` fall through to a wider row.** The
  materializer would have to add a `REX` byte from the register value, which is
  exactly the implicit length change `INV-04` forbids.
- **One row with a four-bit register slot and an optional `REX` byte.** The
  byte's presence would depend on the operand, so the row's length would stop
  being a template fact.
- **Reuse the 64-bit rows with a 32-bit register kind.** The template carries
  `REX.W`, which selects 64-bit semantics, and `x86.gpr32` on an `r64` row is
  already `E-OPERAND-001` (`N02r`).
- **Encode the ext window with `invert` on `REX.R`.** The template's `44`
  already means `REX.R = 1`; inverting would let `%eax` alias `%r8d` and make
  two register names share one byte string.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8b 04 25 34 12 00 00` and `89 04 25 34 12 00 00` | `llvm-mc -show-encoding`, `EXP-0056` §1 | high |
| `44 8b 04 25 …` and `44 89 04 25 …` for `%r8d` | `llvm-mc -show-encoding`, `EXP-0056` §1 | high |
| `ModRM.reg` at `[11,3]` in the low rows, `[19,3]` in the ext rows | the byte strings; `EXP-0056` §2 | high |
| the address is the same four bytes in both windows | `llvm-mc -show-encoding`, `EXP-0056` §2 | high |
| `%eax` on the ext row is `E-RANGE-004`, not a second encoding | the template's `REX.R = 1`; `EXP-0056` §3 | high |
| `%r16d` needs the APX `d5` prefix, outside the field | `llvm-mc` output, `EXP-0056` §4 | high |

## Review triggers

- The 16- or 8-bit absolute rows are attempted: `66 8b` and the three `movb`
  register sets decide the row shape, and `movb %ah, 0x1234` is `88 24 25 …`
  with no `REX` byte.
- A symbol or relocation in the address is requested (`R_X86_64_32`,
  `R_X86_64_32S`): the field stops being content.
- `moffs` is requested for this width: it re-opens `EC-05` as a new row, at
  `a1`/`a3` with an eight-byte address.
- The `0x67` prefix is attempted: the same fields read as a 32-bit address.
- The absolute address under the other x86 opcode families is attempted
  (`add`, `cmp`, the SSE and EVEX families at other mnemonics).
