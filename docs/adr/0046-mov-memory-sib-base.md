# ADR-0046: The 8/16-bit memory bases reach `%rsp` and `%r12` through fixed `SIB` rows

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P23` (the `SIB` base of the 8/16-bit `mov` memory rows)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0045` §Review triggers (the `%rsp`/`%r12` window it deferred),
  `ADR-0034` §Decision 1 (the same window at 8 and 16 bits), and `EC-35` /
  `EC-38` (both revised in place, no row added)

## Context

`ADR-0045` extended the 8/16-bit `mov` memory rows to `r8`–`r15` and left
`%rsp`/`%r12` out because both force a `SIB` byte. The four families behave the
same way here, and differently from their general rows:

1. **`%rsp` spends one byte.** `movw %ax, 8(%rax)` is `66 89 40 08`, four
   bytes; `movw %ax, 8(%rsp)` is `66 89 44 24 08`, five. The `ModRM` becomes
   `r/m = 100` and a `SIB` byte follows, so everything after `ModRM` moves one
   byte later. A row that accepted both bases and inserted the `SIB` on seeing
   the value would make the instruction length an operand fact (`INV-04`).
2. **`%r12` spends one more.** Its low three bits are also `100`, so it needs
   the same `SIB` plus `REX.B`: `66 41 89 44 24 08`, six bytes. The 64-bit
   family already splits this three ways (`0.3.0`, `0.7.0`); the 8/16-bit rows
   repeat the split per family rather than invent a new shape.
3. **The displacement moves with the `SIB`.** On the word rows it leaves bit 24
   for 32 (`%rsp`) or 40 (`%r12`); on the byte rows it leaves 16 for 24 or 32.
   The register slot moves with it for the same reason: `ModRM` sits behind
   every template prefix, so the word `%r12` row reads its register at
   `[27,3]`, not `[19,3]`.
4. **The high-byte family has one base only.** `movb %ah, 8(%rsp)` is
   `88 64 24 08` and encodes; `movb %ah, 8(%r12)` is rejected with
   `can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`,
   because the `REX.B` byte that names `%r12` renames `ah` to `spl`. There is
   no row to add, only a base to leave out.
5. **The `40` rows are the cheap case.** `movb %spl, 8(%rsp)` is
   `40 88 64 24 08` and `movb %spl, 8(%r12)` is `41 88 64 24 08`: the `REX`
   byte already exists, so only `REX.B` changes. The row still has to be a form
   — a low-base `40` row and a `%rsp` `40` row differ by the `SIB` — but no
   template grows a new prefix byte.

`EXP-0048` measures all of the above with `llvm-mc` 23.1.2 on 2026-11-06, and
each of the twenty-eight byte strings round-trips through
`llvm-mc -disassemble` to the same source line.

## Decision

**`0.19.0` appends twenty-eight fixed-base rows: for each of the four families
(word, REX-less low byte, high byte, `40`-prefixed byte) and each direction,
`disp8` and `disp32` at `%rsp` and at `%r12`, except the high-byte family,
which gets `%rsp` only. The base is fixed in the template and the row carries
only the register and the displacement. No `EC` row is added: `EC-02`,
`EC-06`, `EC-27`, `EC-28`, `EC-35` and `EC-38` already state the shape, and
`EC-35` and `EC-38` are revised in place so the 8/16-bit families join their
statements.**

The appended rows, one per `(family, direction, width, base)`:

| Family | Load `disp8`/`disp32` (`%rsp`, `%r12`) | Store `disp8`/`disp32` (`%rsp`, `%r12`) | Template |
|---|---|---|---|
| word | `x86:mov/r16-{rsp,r12}-disp{8,32}/legacy` | `x86:mov/{rsp,r12}-disp{8,32}-r16/legacy` | `66 [41] 8b/89 44/84 24 disp` |
| low byte | `x86:mov/r8-{rsp,r12}-disp{8,32}/legacy` | `x86:mov/{rsp,r12}-disp{8,32}-r8/legacy` | `[41] 8a/88 44/84 24 disp` |
| high byte | `x86:mov/r8h-rsp-disp{8,32}/legacy` | `x86:mov/rsp-disp{8,32}-r8h/legacy` | `8a/88 64/a4 24 disp` |
| `40` byte | `x86:mov/r8-{rsp,r12}-disp{8,32}-rex/legacy` | `x86:mov/{rsp,r12}-disp{8,32}-r8-rex/legacy` | `40/41 8a/88 64/a4 24 disp` |

Four properties follow:

- **The base is the form.** `%rsp` costs the `SIB` byte and `%r12` costs
  `SIB` + `REX.B`, so the three-way split of `0.3.0`/`0.7.0` is reproduced
  inside each family and no operand value changes a length.
- **The field offsets follow the prefix count.** `ModRM.reg`/`disp` sit at
  `[19,3]`/`[32,…]` on the `%rsp` word rows, `[27,3]`/`[40,…]` on the `%r12`
  word rows, `[11,3]`/`[24,…]` on the REX-less `%rsp` byte rows, and
  `[19,3]`/`[32,…]` on every row whose template carries a `REX` byte.
- **The register windows do not change.** The new low-byte rows still carry
  `0`–`3` and exclude `4`–`7`, the `40` rows `4`–`7` and exclude `0`–`3`, and
  the high-byte rows `4`–`7` and exclude `0`–`3`. The base axis and the
  register axis stay independent.
- **The high-byte family has no `%r12` row.** `x86:mov/r8h-r12-disp8/legacy`
  is `E-FORM-001`; the encoding does not exist, so there is nothing to defer.

## Consequences

- `0.19.0` is a 155-form document with digest
  `sha256:dddc678fe0abc6fa03c2e61c8fcafef2570b496775a11a25e1ab29e01bfe5130`.
- Its positive fixture `X86-P23-mov-mem-sib` has twenty-eight instructions and
  178 bytes, one per row.
- Negatives pin the version boundary against `0.18.0`, the absent high-byte
  `%r12` row, an operand-width mismatch, the `disp8` content end, the
  three-bit register field and the `40` register window.
- `07_definition_format.md` §8.1 gains the twenty-eight rows, the `0.19.0`
  digest row and narrative; `02_encoding_choices.md` gains the surface rows and
  revises `EC-35` and `EC-38` in place.
- No schema, loader or materializer change: the new rows use the fixed-base
  shape `0.3.0` introduced and the `SIB` byte is part of the template.

## Alternatives rejected

- **One row per family with a four-bit base and a mandatory `SIB`.** `%rax`,
  `%rcx` and the rest would start paying a `SIB` byte they do not spend
  (`EC-35`), so every existing 8/16-bit memory byte would change.
- **A `sib` modifier or a `base` operand that selects the shape.** A modifier
  may not write bits (`ADR-0015`) and the length would become a plan choice,
  which is exactly the `INV-04` line `ADR-0028` drew.
- **Make `SIB.index`/`SIB.scale` operand fields, as `0.8.0` did for `movq`.**
  That is a different capability (`8(%rsp,%rax,4)`), needs its own operand
  types, and a base-only row is the `index = 100`, `scale = 00` special case.
  Adding both axes at once would make the counterexample ambiguous.
- **Give the high-byte family a `%r12` row.** `llvm-mc` rejects the encoding;
  a row that accepted it would name `spl`–`dil` instead of `ah`–`bh`.
- **Include `mod = 00` in the same slice.** `(%rsp)`/`(%r12)` shorten the
  displacement to zero bytes and re-open the `%rbp`/`%r13` collision; it is a
  separate decision (`ADR-0028` deferred it at 64 bits too).
- **Reach `r8b`–`r15b`/`r8w`–`r15w` here.** `REX.R` is a register decision;
  adding it to the same rows would move the register slot again while the base
  slot is also moving.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `66 89 44 24 08`, `66 41 89 44 24 08`, `8a 44 24 08`, `41 8a 5c 24 08` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0048` §1 | high |
| `8a 64 24 08`, `40 8a 64 24 08`, `41 8a 6c 24 08` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0048` §1 | high |
| `ModRM.reg`/`disp` sit at `19/32`, `27/40`, `11/24`, `19/32` by template prefix count | the byte strings above; `EXP-0048` §2 | high |
| `movb %ah, 8(%r12)` is rejected with the REX/high-byte message | `llvm-mc` error text, `EXP-0048` §3 | high |
| `movw %ax, 8(%esp)` spends a `0x67` prefix instead | `llvm-mc -show-encoding`, `EXP-0048` §4 | high |
| `disp8` ends are `127`/`-128` and `128`/`-129` are `disp32` | `llvm-mc -show-encoding`, `EXP-0048` §1 | high |

## Review triggers

- `mod = 00` is attempted for a GPR memory row: `66 41 89 04 24` is
  `movw %ax, (%r12)` and `%rbp`/`%r13` need the `disp8` zero form.
- An index or scale is attempted under these opcodes: `8(%rsp,%rax,4)` needs
  `SIB.index`/`SIB.scale` operands and a fourth base window.
- `r8b`–`r15b` or `r8w`–`r15w` is attempted: `REX.R` moves the register slot
  to four bits on rows that also carry a `SIB`.
- The `0x67` address-size prefix is attempted: `67 66 89 44 24 08` is a
  different base width, not a different base register.
- The SSE `SIB` base is attempted: the `movaps`/`vmovaps` memory rows still
  exclude `%rsp`/`%r12` (`EC-38`).
