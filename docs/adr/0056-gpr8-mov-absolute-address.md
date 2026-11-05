# ADR-0056: the 8-bit `mov` rows take an absolute address in four register windows

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P33` (the absolute `SIB = 25` shape under the 8-bit GPR `mov`
  opcodes, in all four byte-register windows)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0055` §Review triggers (the 8-bit absolute shape it named);
  `EC-02` (the displacement widths, extended to this opcode family);
  `EC-36` (the byte-register relabelling, extended to these rows);
  `EC-38` (the register window, extended to the byte rows)

## Context

`ADR-0053` … `ADR-0055` gave the 64-, 32- and 16-bit `mov` rows a 32-bit
absolute address. The 8-bit rows are the last width, and they are the only
one where the *same* three-bit `ModRM.reg` field names two disjoint register
sets: without a `REX` byte `4`–`7` are `%ah`–`%bh`, with one they are
`%spl`–`%dil`. `EC-36` already freezes that rule for the memory rows; this
slice is where it meets an absolute address.

`EXP-0058` measures the shape. Five facts come out:

1. **There are four windows, not two.** `movb 0x1234, %al` is
   `8a 04 25 34 12 00 00` (seven bytes) and `movb -128, %bl` is
   `8a 1c 25 80 ff ff ff`; `movb 0x1234, %ah` is `8a 24 25 34 12 00 00` and
   `movb %ah, 0x1234` is `88 24 25 34 12 00 00` (seven bytes, the same shape
   with `reg = 100`); `movb 0x1234, %spl` is `40 8a 24 25 34 12 00 00` and
   `movb %dil, -32768` is `40 88 3c 25 00 80 ff ff` (eight bytes, `REX = 40`);
   `movb 0x1234, %r8b` is `44 8a 04 25 34 12 00 00` and
   `movb %r15b, 0x1234` is `44 88 3c 25 34 12 00 00` (eight bytes,
   `REX = 44`, `REX.R = 1`).
2. **The low and high windows share one byte layout.** `8a` (load) or `88`
   (store) at `[0,8]`, `ModRM` at `[8,8]` with `mod = 00`, `r/m = 100` and the
   register in `ModRM.reg` at `[11,3]`, `SIB = 25` at `[16,8]` and the address
   at `[24,32]`. Only the template's `reg` bits differ: `04`/`0c`/`14`/`1c`
   for `%al`–`%bl` and `24`/`2c`/`34`/`3c` for `%ah`–`%bh`.
3. **Each `REX` window is the same shape one byte later.** `40 8a 24 25 …` and
   `44 8a 04 25 …`: the `REX` byte at `[0,8]`, the opcode at `[8,8]`, `ModRM`
   at `[16,8]` with the register at `[19,3]`, `SIB` at `[24,8]` and the
   address at `[32,32]`. `REX = 40` keeps `REX.R = 0`, so the field still
   names `4`–`7`; `REX = 44` sets `REX.R = 1`, so the register is `[19,3]`
   plus `REX.R` at `[2,1]` and the row's values are `8`–`15`.
4. **The address is the same signed 32-bit field as at every other width.**
   `-1` is `ff ff ff ff`, `-128` is `80 ff ff ff` and `0x7fffffff` is
   `ff ff ff 7f`.
5. **`0x80000000` is content that no row accepts.** `movb 0x80000000, %al`
   assembles to `movabsb` (`a0` plus an eight-byte address, nine bytes), and
   `movb %al, 0x80000000` to `a2`. `llvm-mc` does *not* switch for
   `movb %r8b, 0x80000000`, which stays eight bytes with the address
   `00 00 00 80` — the same four bytes, because the value is the two's
   complement of `-2147483648`. The asymmetry is in `llvm-mc`'s `moffs`
   reach, not in the field: whichever form it picks, the address bytes are the
   signed content, so a plan that writes `2147483648` is one past the end
   (`E-RANGE-001`) and never a form switch (`EC-05`, `INV-02`).

All twenty-four measured byte strings round-trip through
`llvm-mc -disassemble` to the same register and address; the measurement is
`llvm-mc` 23.1.2 on 2026-11-06.

## Decision

**`0.29.0` appends eight rows: load and store in each of the four
byte-register windows. The window is a `form_id` component, so the plan names
the length and the register set it wants and no field value chooses either.**

| Direction | Window | `form_id` | Template | Length |
|---|---|---|---|---|
| load | low `%al`–`%bl` | `x86:mov/r8-abs32/legacy` | `8a 04 25 00 00 00 00` | 7 |
| store | low `%al`–`%bl` | `x86:mov/abs32-r8/legacy` | `88 04 25 00 00 00 00` | 7 |
| load | high `%ah`–`%bh` | `x86:mov/r8h-abs32/legacy` | `8a 24 25 00 00 00 00` | 7 |
| store | high `%ah`–`%bh` | `x86:mov/abs32-r8h/legacy` | `88 24 25 00 00 00 00` | 7 |
| load | `REX = 40` `%spl`–`%dil` | `x86:mov/r8-rex-abs32/legacy` | `40 8a 24 25 00 00 00 00` | 8 |
| store | `REX = 40` `%spl`–`%dil` | `x86:mov/abs32-r8-rex/legacy` | `40 88 24 25 00 00 00 00` | 8 |
| load | `REX = 44` `%r8b`–`%r15b` | `x86:mov/r8-ext-abs32/legacy` | `44 8a 04 25 00 00 00 00` | 8 |
| store | `REX = 44` `%r8b`–`%r15b` | `x86:mov/abs32-r8-ext/legacy` | `44 88 04 25 00 00 00 00` | 8 |

Six properties follow:

- **`ModRM = 04` or `24` and `SIB = 25` are template constants in all eight
  rows.** `r/m = 100` plus `SIB.base = 101` with `SIB.index = 100` is the
  absolute request, and the address is mandatory and four bytes wide even when
  it is `0`.
- **The low and high rows have no `REX` byte and are seven bytes.** The
  register is the three-bit `ModRM.reg` at `[11,3]`; the low rows exclude
  `4`–`7` and the high rows exclude `0`–`3`, so the two windows are disjoint
  and one register number names exactly one row.
- **The high rows keep `x86.gpr8h`.** `EC-36` forbids a `REX` byte naming
  `%ah`–`%bh` (`E-DEF-001`), so the relabelled window cannot reuse the kind.
- **The `REX = 40` rows are eight bytes and hold only `4`–`7`.** The `REX`
  byte is what turns those numbers into `%spl`–`%dil`, so the slot excludes
  `0`–`3`: `%al` on that row would be `E-RANGE-004`, because the template
  would encode `%spl` at the same byte.
- **The `REX = 44` rows are four bits wide.** The slot is `[19,3]` plus
  `REX.R` at `[2,1]` with `excluded: [0,1,2,3,4,5,6,7]`, so `%r8b`–`%r15b`
  are reachable and `0` is `E-RANGE-004`. This is the only 8-bit row that
  reaches `8`–`15`, and it reaches them at a fixed length.
- **The address is signed 32-bit content.** `2147483648` is `E-RANGE-001`, and
  a supplied `base` or a `disp8` address is `E-OPERAND-002` /
  `E-OPERAND-001`, the refusals the wider rows already apply.

## Consequences

- `0.29.0` is a 255-form document, byte-reproducing every `0.28.0` row.
- Its positive fixture `X86-P33-gpr8-mov-abs32` has eight instructions and 60
  bytes: one per row, so both directions appear in every window. Four are
  seven bytes and four are eight, and the `REX = 40`/`REX = 44` pair shows the
  relabelled `%spl`/`%dil` beside the extended `%r8b`/`%r15b`.
- Negatives pin the version boundary in both directions (`N01bk`, `N01bl`),
  a supplied `base` (`N02ap`), a `disp8` address (`N02aq`), a 16-bit register
  on a byte row (`N02ar`), a high-byte kind on a low-byte row (`N02as`), the
  past-the-end content (`N03p`), the four-bit field end (`N14ac`) and the
  excluded low window on the `REX = 40` row (`N16af`).
- `EC-02`, `EC-36` and `EC-38` are revised in place; no new `EC` row appears.
- No schema, loader or materializer change: the rows are templates with a
  register slot and a signed displacement slot, both already supported.
- Still absent: the `REX.B` combination at byte width (an extended base with
  the `REX = 44` row), the `0x67` address-size prefix, a symbol in the
  address, `moffs` for the byte width, and the APX `d5` register window.

## Alternatives rejected

- **Two rows with a shared three-bit field and the prefix chosen from the
  register kind.** The length would follow the operand (`INV-04`), and
  `%ah`/`%spl` share a number, so the plan could not say which it meant.
- **Fold the `REX = 40` window into the low rows.** `%al` would then have two
  lengths, and a plan naming the seven-byte row could be answered with eight
  bytes.
- **Let `%r8b`–`%r15b` share the `REX = 40` rows.** `REX.R` is a template bit
  there; using it for an operand would let the register number change the
  template (`INV-02`).
- **Treat the address as 8-bit content because the operand is 8 bits.** The
  measurement contradicts it: the field is four bytes at every width.
- **Accept `2147483648` because `llvm-mc` kept the short form for `%r8b`.**
  The bytes are the same four bytes as `-2147483648`, so the value is content
  one past the signed end; accepting it would make the assembler's `moffs`
  reach a rule of ours (`INV-02`, `INV-07`).

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8a 04 25 …` / `88 24 25 …` / `40 8a 24 25 …` / `44 8a 04 25 …` | `llvm-mc -show-encoding`, `EXP-0058` §1 | high |
| `ModRM.reg` at `[11,3]` (no `REX`) and `[19,3]` (with `REX`) | the byte strings; `EXP-0058` §2 | high |
| `REX = 40` relabels `4`–`7` to `%spl`–`%dil` | `llvm-mc -show-encoding` and `-disassemble`, `EXP-0058` §3 | high |
| the address is signed 32-bit content at every width | `llvm-mc -show-encoding`, `EXP-0058` §2 | high |
| `0x80000000` leaves the low rows for `movabsb`, but not the `REX = 44` row | `llvm-mc -show-encoding`, `EXP-0058` §2 | high |
| `%r16b` needs the APX `d5` prefix | `llvm-mc` output, `EXP-0058` §4 | high |

## Review triggers

- The `REX.B` combination at byte width is attempted: an extended base and
  `%r8b`–`%r15b` share one `REX` byte (`45 8a 04 25 …`), and `%ah` can never
  join it.
- A symbol or relocation in the address is requested (`R_X86_64_32`,
  `R_X86_64_32S`): the field stops being content.
- `moffs` is requested for the byte width: `a0`/`a2`, nine bytes.
- The `0x67` prefix is attempted: the same fields read as a 32-bit address.
- The absolute address under the other x86 opcode families is attempted.
