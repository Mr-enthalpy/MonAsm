# ADR-0049: The EVEX `vmovaps` no-displacement rows take `%rsp` and `%r12` as `SIB` bases

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P26` (the `mod = 00` `SIB` base of the EVEX `vmovaps` memory rows at `xmm`/`ymm`/`zmm` width)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0048` §Review triggers (the `mod = 00` `SIB` base it named)

## Context

`ADR-0048` gave the EVEX `vmovaps` memory rows `%rsp` and `%r12` at `mod = 01`
and `mod = 10`, where the displacement is present. It left `mod = 00` out, and
its first review trigger names the shape: `(%rsp)` drops the displacement byte
entirely. The choice is not a variant of `ADR-0048`; it changes which byte a
`ModRM` pattern spends:

1. **`mod = 00` with `r/m = 100` moves the base into the `SIB`.** The `ModRM`
   byte spends `r/m = 100` on the `SIB` escape, so `%rsp` and `%r12` are named
   by the `SIB` byte (`24`: scale `00`, index `100`, base `100`) and the
   displacement slot disappears. The instruction is seven bytes:
   `62 f1 7c 08 28 04 24` for `(%rsp)` and `62 d1 7c 08 28 04 24` for
   `(%r12)`.
2. **The two rows differ in one `P0` bit, not in length.** `%r12` is the same
   seven bytes with the inverted `B̄` cleared (`f1` → `d1`), exactly as on the
   `disp8*N` rows `ADR-0048` added.
3. **`%rbp` and `%r13` cannot use this shape.** `mod = 00` with `r/m = 101`
   means RIP-relative, so `(%rbp)` keeps a zero displacement and no `SIB`
   (`62 f1 7c 08 28 45 00`, seven bytes) and stays on the `-base` row at
   `mod = 01`.
4. **Zero has exactly one encoding.** `llvm-mc` canonicalizes
   `0(%rsp)` to `(%rsp)`, so the no-displacement row is the only spelling of a
   zero offset; no `disp8*N` row can carry it.

`EXP-0051` measures all of the above with `llvm-mc` 23.1.2 on 2026-11-06, and
each of the sixteen measured byte strings round-trips through
`llvm-mc -disassemble` to the same source line.

## Decision

**`0.22.0` appends twelve fixed-base rows: for each of the three widths
(`xmm`, `ymm`, `zmm`), each direction and each base (`%rsp`, `%r12`), at
`mod = 00` with no displacement slot. The base is fixed in the template
(`r/m = 100`, `SIB = 24`, `B̄` in `P0`) and the row carries only the vector
register. No `EC` row is added: `EC-02`, `EC-35` and `EC-38` already state the
`ModRM`/`SIB` shape and the reach, and all three are revised in place so the
no-displacement EVEX family joins their statements.**

The appended rows, one per `(width, direction, base)`:

| Width | Load `form_id` | Store `form_id` | Template |
|---|---|---|---|
| `xmm` | `x86:vmovaps/xmm-{rsp,r12}/evex` | `x86:vmovaps/{rsp,r12}-xmm/evex` | `62 {f1,d1} 7c 08`, then `28`/`29` `04` `24` |
| `ymm` | the same two names with `ymm` in place of `xmm` | the same two names with `ymm` in place of `xmm` | `62 {f1,d1} 7c 28`, same tail |
| `zmm` | the same two names with `zmm` in place of `xmm` | the same two names with `zmm` in place of `xmm` | `62 {f1,d1} 7c 48`, same tail |

Four properties follow:

- **The base is the form.** `%rsp` and `%r12` both fix the `SIB` byte and
  differ in the fixed `P0` `B̄` bit, so no operand value changes a length and no
  single row can carry both.
- **The vector slot does not move.** The prefix length is unchanged, so
  `dest`/`src` sit at `[43,3]` with `[12,1]`/`[15,1]` inverted, exactly as on
  the `-base` and `-base-disp*` rows.
- **There is no `disp` slot.** The row has one slot, so a plan that supplies a
  displacement is one operand too many (`INV-07`), never a silently ignored
  offset.
- **The full register file is reachable.** The EVEX slots are five bits, so
  `%xmm20`, `%ymm21` and `%zmm30` encode on these rows at no length cost.

## Consequences

- `0.22.0` is a 207-form document with digest
  `sha256:61c7cd1c940a7b22838a2c3418ba54031a20c6b227203fb9b4a57875f1c36b58`.
- Its positive fixture `X86-P26-evex-mem-sib-nodisp` has twelve instructions
  and 84 bytes, one per row: the `xmm` four run `xmm0`–`xmm3`, the `ymm` four
  `ymm8`–`ymm11`, the `zmm` four `zmm16`–`zmm19`.
- Negatives pin the version boundary against `0.21.0`, the absent `%rbp` shape,
  an operand-class mismatch, the extra `disp` operand a no-displacement row
  refuses, the five-bit register field end, and `%rsp` on the general
  `xmm-base` row.
- `07_definition_format.md` §8.1 gains the twelve rows, the `0.22.0` digest row
  and narrative; `02_encoding_choices.md` gains the surface rows and revises
  `EC-02`, `EC-35` and `EC-38` in place.
- No schema, loader or materializer change: the rows use the fixed-base shape
  `0.3.0` introduced, the `SIB` byte is part of the template, and dropping the
  displacement slot is the absence of a slot.
- Still absent on this axis: an index or scale under these opcodes, `%rbp`/
  `%r13` at `mod = 00` (they cannot encode that way), the other EVEX SSE memory
  mnemonics, and EVEX masking.

## Alternatives rejected

- **Reuse the `-base` row with a `SIB` modifier.** A modifier may not write bits
  (`ADR-0015`), and the length would become a plan choice (`INV-04`).
- **One row for both bases with the `B̄` bit as an operand.** `B̄` is the fixed
  template byte that distinguishes `%rsp` from `%r12`; making it a slot would
  turn a base decision into an operand value while the base is fixed.
- **A zero-content `disp8*N` row instead.** `0(%rsp)` is not a `disp8` shape;
  `llvm-mc` emits seven bytes with no displacement, so a displacement row would
  produce a different, longer byte string for the same source.
- **Extend this slice to `%rbp`/`%r13`.** They have no `mod = 00` encoding at
  all (`r/m = 101` is RIP-relative), so there is no row to add.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `62 f1 7c 08 28 04 24`, `62 d1 7c 08 28 04 24`, `62 f1 7c 08 29 14 24` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0051` §1 | high |
| `dest`/`src` stay at `[43,3]` + `[12,1]`/`[15,1]`; there is no `disp` slot | the byte strings above; `EXP-0051` §2 | high |
| `%r12` differs from `%rsp` only in `P0` (`f1` → `d1`), at equal length | `llvm-mc -show-encoding`, `EXP-0051` §2 | high |
| `0(%rsp)` canonicalizes to `(%rsp)`, seven bytes | `llvm-mc -show-encoding`, `EXP-0051` §3 | high |
| `%rbp`/`%r13` keep a zero displacement and no `SIB` (`62 … 45 00`) | `llvm-mc -show-encoding`, `EXP-0051` §4 | high |
| `%xmm20`/`%ymm21`/`%zmm30` encode on these rows at no length cost | `llvm-mc -show-encoding`, `EXP-0051` §4 | high |
| `%xmm32` is `error: invalid register name` | `llvm-mc` error text, `EXP-0051` §5 | high |

## Review triggers

- An index or scale is attempted: `(%rsp,%rax,1)` is
  `62 f1 7c 08 28 04 04`, a different `SIB` byte (`index = 000`).
- A second EVEX SSE mnemonic is attempted (`vmovups`, `vmovdqa`): the same
  shape with a different opcode byte, a coverage slice with no new `EC` fact.
- EVEX masking is attempted: `{k1}` writes the `aaa` field, a bit this shape
  does not carry.
- A `%rbp`/`%r13` no-displacement row is requested: no such encoding exists at
  `mod = 00`, so the request has to settle for the `disp8 = 0` form.
