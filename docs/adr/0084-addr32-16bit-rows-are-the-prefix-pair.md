# ADR-0084: the `0x67` 16-bit value rows are the prefix pair

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P61` (the `0x67` + `0x66` `movw` rows on the 32-bit indexed
  address shape, both directions at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-02` (the same `[40,8]`/`[40,32]` displacement offsets now carry
  the `0x67 66` pair), `EC-06` (the bare 16-bit row has no `REX` byte; its `REX`
  windows are deferred), `EC-07` (the `0x66` prefix follows `0x67` and selects
  the 16-bit value width), `EC-08` (the 16-bit sibling is one bare pair), `EC-36`
  (the two legacy prefixes are ordered `0x67` then `0x66` before the opcode),
  `EC-37` (the index keeps its three `SIB` bits at 16-bit value width) and
  `EC-38` (the `addr32` 16-bit family starts as one no-`REX` window)

## Context

`0.53.0` … `0.56.0` built the `0x67` address-size rows for the 32-bit and
64-bit value widths. The 16-bit width is the remaining one, and it brings a
second legacy prefix: `0x66`. `EXP-0086` measures the bare pair (no `REX`):

1. **The prefix order is `0x67` then `0x66`.** `movw 8(%eax,%ecx,1), %ax` is
   `67 66 8b 44 08 08`: six bytes, `0x67` at byte 0, `0x66` at byte 1, the
   opcode at byte 2, `ModRM = 44` at byte 3, `SIB = 08` at byte 4 and `disp8`
   at byte 5.
2. **The geometry is the `0.54.0` geometry.** `0x66` takes the byte the `REX`
   prefix occupied on the 32/64-bit rows, so the value register is `[27,3]`,
   the base `[32,3]`, the index `[35,3]`, the scale `[38,2]` and the
   displacement `[40,8]`/`[40,32]`. Because the row has no `REX` byte, every
   register slot is three bits: `%ax`–`%di`, `%eax`–`%edi` and `%ecx`-sized
   indexes.
3. **The address registers are still the 32-bit ones.** `%ebp` is a legal base
   (`67 66 8b 44 0d 08`) and a legal index (`67 66 8b 44 28 08`), `%esp` is a
   legal base (`67 66 8b 44 0c 08`) and not an index, and the x8 scale is
   `67 66 8b 44 c8 08`. A value register past `%di` (`%r8w`) or an address
   register past `%edi` (`%r8d`) needs a `REX` byte and is not this row:
   `movw 8(%r8d,%ecx,1), %ax` is `67 66 41 8b 44 08 08` (seven bytes) and
   `movw 8(%eax,%ecx,1), %r8w` is `67 66 44 8b 44 08 08`.
4. **The `disp32` rows are nine bytes.** `movw 200(%eax,%ecx,1), %ax` is
   `67 66 8b 84 08 c8 00 00 00` with the four displacement bytes at `[40,32]`.

## Decision

1. **`0.57.0` appends four rows: two directions × two displacement widths.**

   | Direction | Displacement | `form_id` | Template | Length |
   |---|---|---|---|---|
   | load | `disp8` | `x86:mov/r16-addr32-base-index-disp8/legacy` | `67 66 8b 44 00 00` | 6 |
   | store | `disp8` | `x86:mov/addr32-base-index-disp8-r16/legacy` | `67 66 89 44 00 00` | 6 |
   | load | `disp32` | `x86:mov/r16-addr32-base-index-disp32/legacy` | `67 66 8b 84 00 00 00 00 00` | 9 |
   | store | `disp32` | `x86:mov/addr32-base-index-disp32-r16/legacy` | `67 66 89 84 00 00 00 00 00` | 9 |

2. **The geometry is the `0.54.0` geometry.** `0x67` is byte 0 and `0x66`
   byte 1, so the opcode is byte 2, `ModRM` byte 3 and `SIB` byte 4: value
   register `[27,3]`, base `[32,3]`, index `[35,3]`, scale `[38,2]` and
   displacement `[40,8]`/`[40,32]`.
3. **No `REX` byte is present.** The value is `x86.gpr16`/`r16` (a three-bit
   field), the base is `x86.gpr32`/`rm32` and the index is
   `x86.gpr32`/`sib_index32` with `4` excluded. A value above `7` is
   `E-OPERAND-004`, a base above `7` is `E-OPERAND-004`, and index `4` is
   `E-RANGE-004`.
4. **No schema, loader or materializer change.** The pair is two template
   prefixes; every slot is the same shape the `0.53.0` bare `addr32` row
   already uses, only one width down.

## Consequences

- `0.57.0` is a 453-form document that byte-reproduces every `0.56.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P61-gpr16-mov-index-addr32-prefix-pair` has eight
  instructions: the four rows plus four corners (`%ebp` as a base, `%ebp` as
  an index, the x8 scale and a `%dx` value). Its `expected.bin` comes from
  `llvm-mc` + `llvm-objcopy`, never from the materializer.
- Negatives pin the version boundary in both directions, a missing index, a
  `REX`-needing value register, a `REX`-needing base, the scale end, the index
  `4` exclusion and the three-bit field end.
- `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-36`, `EC-37` and `EC-38` are revised
  in place; no `EC` row is added or renumbered.

## Alternatives rejected

- **Put `0x66` before `0x67`.** Rejected by measurement: `llvm-mc` emits
  `67 66` for `movw 8(%eax,%ecx,1), %ax`, and a byte swap is a different
  instruction stream (and would move every field one byte).
- **Use `x86.gpr16` for the base and index because the value is 16-bit.**
  Rejected by measurement: `0x67` selects 32-bit address registers, so the
  same bytes name `%eax`-sized registers (`%ebp` is a legal base).
- **Split the bare pair into `REX` windows now.** Rejected for this slice:
  each window inserts a `REX` byte at byte 2 and moves the opcode, `ModRM`,
  `SIB` and displacement one byte later; that is a separate set of rows.
- **Add a symbol in the displacement now.** A relocation changes the field's
  meaning (`03_fixup_model.md`), and no `addr32` fixup row exists.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 66 8b 44 08 08` is the low `movw` load at six bytes | `llvm-mc -show-encoding`, `EXP-0086` §1 | high |
| `0x66` takes byte 1, so the opcode is at byte 2 | `llvm-mc -show-encoding`, `EXP-0086` §2 | high |
| `%ebp` is a legal base and index; `%esp` is a base but not an index | `llvm-mc`, `EXP-0086` §3 | high |
| the `disp32` rows are nine bytes with `disp32` at `[40,32]` | `llvm-mc -show-encoding`, `EXP-0086` §1 | high |
| the eight byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0086` §1 | high |

## Review triggers

- A `0x67 66` row with a `REX` window (`%r8w`, `%r8d`, `%r9d`) is attempted.
- A symbol or relocation in an `addr32` displacement is requested.
- The no-base indexed shape or the `moffs` form is attempted with `0x67`.
- A `0x66` row with a 64-bit address register is proposed.
- An EVEX or VEX row is proposed with an address-size prefix.
