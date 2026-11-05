# ADR-0052: The EVEX `vmovaps` memory rows take a 32-bit absolute address

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P29` (the `SIB = 25` absolute-address shape of the EVEX
  `vmovaps` memory rows at `xmm`/`ymm`/`zmm` width)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0051` §Review triggers (the absolute shape it named);
  `ADR-0050` §Review triggers (the no-base shape it took)

## Context

`ADR-0051` took the no-base indexed shape and named the next widening in its
first review trigger: `vmovaps 0x1234, %xmm0` is `SIB = 25`, an address with
neither a base nor an index register. That byte spends *both* `SIB` register
fields on constants, so it is the last combination the byte can express:

- `SIB.index = 100`: "no index" — with an operand, this value is excluded
  (`ADR-0035`, `E-RANGE-004`);
- `SIB.base = 101` at `mod = 00`: "no base, `disp32`" (`ADR-0051`).

Five facts come out of the measurements in `EXP-0054`:

1. **`ModRM = 04` and `SIB = 25` are both constant.** `mod = 00`, `r/m = 100`
   spends the byte on the `SIB` escape; the `SIB` byte then has scale `00`,
   index `100` and base `101`. The whole address is one 32-bit field, so every
   row is eleven bytes: `62 f1 7c 08 28 04 25 34 12 00 00`.
2. **The indexed row is three bits away.** `0x1234(,%rax,4)` is
   `62 f1 7c 08 28 04 85 34 12 00 00`: the same `ModRM` and the same base
   field, with `SIB.index` written by an operand instead of the constant
   `100`. The length, the displacement and the vector slot are identical.
3. **The vector slot does not move.** `ModRM.reg` carries the low three bits
   and `P0` the inverted `R̄`/`R̄'`; `%xmm20` is `24`/`62 e1`, `%xmm21` is
   `2c`/`62 e1`, `%ymm8` is `04`/`62 71`, `%ymm9` is `0c`/`62 71`, `%zmm30` is
   `34`/`62 61` and `%zmm31` is `3c`/`62 61`. The five-bit window the earlier
   slices pinned is unchanged.
4. **The displacement is mandatory and signed at `[56,32]`.** `0x0` is four
   zero bytes (`62 f1 7c 08 28 14 25 00 00 00 00`), `-4096` is
   `00 f0 ff ff`, `-1` is `ff ff ff ff`, `-2147483648` is `00 00 00 80` and
   `2147483647` is `ff ff ff 7f`. `llvm-mc` also accepts `0x80000000` and
   `0x100000000`, wrapping them to `00 00 00 80` and `00 00 00 00`; the field
   is signed 32-bit, so both are `E-RANGE-001` for a plan.
5. **The three neighbours are different bytes, not variants of this one.**
   `0x1234(%rax)` is `… 28 80 34 12 00 00` (ten bytes, no `SIB`),
   `0x1234(%rip)` is `… 28 05 34 12 00 00` (ten bytes, `ModRM.rm = 101`) and
   `0x1234(,%rax,4)` is `… 28 04 85 34 12 00 00` (eleven bytes, indexed).
   The absolute shape is the only one with no register in the address.

The measurements are `llvm-mc` 23.1.2 on 2026-11-06; every measured byte
string round-trips through `llvm-mc -disassemble` to the same address.

## Decision

**`0.25.0` appends six rows: for each of the three widths (`xmm`, `ymm`,
`zmm`) and each direction, one `disp32` row whose `ModRM` is `04` and whose
`SIB` byte is the constant `25`. There is no `base`, `index` or `scale` role;
the only operand besides the vector is the 32-bit absolute address.**

The appended rows:

| Width | Load `form_id` | Store `form_id` | Length |
|---|---|---|---|
| `xmm` | `x86:vmovaps/xmm-abs32/evex` | `x86:vmovaps/abs32-xmm/evex` | 11 bytes |
| `ymm` | `x86:vmovaps/ymm-abs32/evex` | `x86:vmovaps/abs32-ymm/evex` | 11 bytes |
| `zmm` | `x86:vmovaps/zmm-abs32/evex` | `x86:vmovaps/abs32-zmm/evex` | 11 bytes |

Five properties follow:

- **The template is `62 f1 7c <L'L> <28|29> 04 25 00 00 00 00`.** The vector
  slot (`[43,3]` plus the inverted extensions at `[12,1]`/`[15,1]`) and the
  displacement at `[56,32]` are the only fields the row carries; `04` and `25`
  are template bytes.
- **The operand sequence is `dest`/`src`, `disp`.** A plan that supplies a
  base, an index or a scale is `E-OPERAND-002` (`N02af`); a plan that carries
  a register where the address belongs is `E-OPERAND-001` on the operand's
  `kind` (`N02ag`).
- **There is no shorter form.** `0` is content `0` in the four-byte field, not
  a dropped displacement, because `SIB.base = 101` at `mod = 00` *is* the
  `disp32` request.
- **The address is signed 32-bit content.** `2147483648` is `E-RANGE-001`
  (`N03l`), the same refusal `N04e` applies to a RIP-relative literal.
- **`abs32` names the address shape, not the byte layout** — the same sense
  `riprel32` already has. It is not `moffs` (`EC-05`): the `A0-A3` form does
  not exist for this mnemonic, so there is no second legal absolute encoding
  to choose between.

## Consequences

- `0.25.0` is a 237-form document.
- Its positive fixture `X86-P29-evex-mem-sib-absolute` has six instructions and
  66 bytes, one per row, all eleven bytes.
- Negatives pin the version boundary against `0.24.0` in both directions
  (`N01bb`, `N01bc`), a supplied `index` operand (`N02af`), a register carried
  as the address (`N02ag`) and past-the-end `disp32` content (`N03l`).
- No schema, loader or materializer change: the row is the `ADR-0051` shape
  with three more constant bits and two fewer slots, and both the
  `E-OPERAND-001`/`E-OPERAND-002` checks and the signed range check already
  exist.
- `02_encoding_choices.md` gains the six surface rows and revises `EC-02`,
  `EC-35`, `EC-37` and `EC-40` in place; `EC-05` stays `draft`, because no
  mnemonic in the table has a `moffs` alternative.
- Still absent: a symbol or relocation in the address (the field is content
  only), the `0x67` address-size prefix, the other EVEX SSE memory mnemonics,
  EVEX masking, and the absolute shape under the GPR and 8/16-bit `mov`
  opcodes.

## Alternatives rejected

- **Fold the shape into the indexed row over an optional `index`.** An
  operand may not be optional (`INV-02`), and the omitted value would have to
  be `4` — the very value the indexed row excludes (`E-RANGE-004`), so the
  materializer would have to reinterpret an exclusion as a meaning.
- **Give the row a `base` operand that must be `5`/`13`.** With `mod = 00`
  those two bases mean "no base"; a slot that accepts only register numbers
  whose encoding means the opposite is not a base operand.
- **Drop the displacement when the address is zero.** `llvm-mc` emits four
  zero bytes for `vmovaps 0x0, %xmm2`; a shorter row would be a second
  encoding of the same address and would move `INV-04`'s length decision into
  the materializer.
- **Accept `2147483648`/`0x100000000` and wrap them.** `llvm-mc` does, but
  the field is signed 32-bit and wrapping is a silent repair (`INV-07`);
  `-2147483648` is the plan's way to say the same bytes.
- **Reuse the RIP-relative row.** `ModRM.rm = 101` with no `SIB` is a
  different ten-byte encoding that reads the field as `RIP + disp32`, not as
  an absolute address.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `62 f1 7c 08 28 04 25 34 12 00 00` and its round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0054` §1 | high |
| `SIB = 25` (index `100`, base `101`) with `ModRM = 04` | the byte strings; `EXP-0054` §2 | high |
| `%xmm20`/`%xmm21`/`%ymm8`/`%ymm9`/`%zmm30`/`%zmm31` in `ModRM.reg` + `P0` | `llvm-mc -show-encoding`, `EXP-0054` §2 | high |
| `disp32` at `[56,32]`, signed, `0` still four bytes | `llvm-mc -show-encoding`, `EXP-0054` §3 | high |
| `0x80000000` and `0x100000000` are wrapped by `llvm-mc` | `llvm-mc` output, `EXP-0054` §4 | high |
| base, RIP and indexed neighbours are 10/10/11 bytes | `llvm-mc -show-encoding`, `EXP-0054` §5 | high |
| `%xmm32` is refused by `llvm-mc` | `llvm-mc` error text, `EXP-0054` §4 | high |

## Review triggers

- A symbol or relocation in the address is requested (`R_X86_64_32`,
  `R_X86_64_32S`): the displacement stops being content.
- The `0x67` address-size prefix is attempted: it re-reads the same fields as a
  32-bit address model.
- A second EVEX SSE mnemonic is attempted (`vmovups`, `vmovdqa`): the same
  shape with a different opcode byte, a coverage slice with no new `EC` fact.
- EVEX masking is attempted: `{k1}` writes the `aaa` field, a bit this shape
  does not carry.
- An absolute address under a GPR or 8/16-bit `mov` opcode is requested:
  `48 8b 04 25 …` is the same `SIB` shape one opcode family over, and `mov
  al, [0x1234]` re-opens `EC-05` because `A0` is a second legal encoding.
