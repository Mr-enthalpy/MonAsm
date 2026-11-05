# ADR-0048: The EVEX `vmovaps` memory rows reach `%rsp` and `%r12` through fixed `SIB` rows

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P25` (the `SIB` base of the EVEX `vmovaps` memory rows at `xmm`/`ymm`/`zmm` width)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0047` §Review triggers (the EVEX `SIB` base it named)

## Context

`ADR-0036` and `ADR-0043`/`ADR-0042` gave the EVEX memory rows a three-bit
base window and a compressed `disp8*N` content, and `ADR-0036` excluded `4` and
`12` because those values force a `SIB` byte. `ADR-0047` then gave the same two
bases to the legacy and VEX families. The EVEX family differs from both in one
respect that decides the shape:

1. **Only the `SIB` byte costs length.** EVEX already carries the base's fourth
   bit as the inverted `B̄` in `P0`, so `%r12` costs no extra prefix byte:
   `{evex} vmovaps 16(%rax), %xmm0` is `62 f1 7c 08 28 40 01` (7 bytes),
   `{evex} vmovaps 16(%rsp), %xmm0` is `62 f1 7c 08 28 44 24 01` (8) and
   `{evex} vmovaps 16(%r12), %xmm0` is `62 d1 7c 08 28 44 24 01` (8). The
   difference between the two new rows is one `P0` bit, not a length.
2. **The vector slot does not move.** The prefix length is unchanged, so
   `ModRM.reg` stays at bit 40 and the vector slot at `[43,3]` (with its two
   inverted extension bits at `[12,1]`/`[15,1]`). Only the displacement moves,
   by the `SIB` byte: `[48,8]` → `[56,8]`, `[48,32]` → `[56,32]`.
3. **The `disp8*N` content is unchanged.** `N` is the width's unit (`16`/`32`/
   `64`), so `16(%rsp)`/`32(%rsp)`/`64(%rsp)` are content `1` and
   `128(%rsp)`/`64(%rsp)`-at-`ymm`/`128(%rsp)`-at-`zmm` are content `8`/`2`/`2`.
   `8(%rsp)` is not a multiple of `16`, so it promotes to `disp32`
   (`62 f1 7c 08 28 84 24 08 00 00 00`), exactly as the general EVEX row does.
4. **`%rbp`/`%r13` are untouched.** `{evex} vmovaps 16(%r13), %xmm0` is
   `62 d1 7c 08 28 45 01`: no `SIB`, the existing `-base-disp8x16` row.

`EXP-0050` measures all of the above with `llvm-mc` 23.1.2 on 2026-11-06, and
each of the twenty-seven measured byte strings round-trips through
`llvm-mc -disassemble` to the same source line.

## Decision

**`0.21.0` appends twenty-four fixed-base rows: for each of the three widths
(`xmm`/`disp8x16`, `ymm`/`disp8x32`, `zmm`/`disp8x64`), each direction and each
displacement form (`disp8xN`, `disp32`), at `%rsp` and at `%r12`. The base is
fixed in the template (`r/m = 100`, `SIB = 24`, `B̄` in `P0`) and the row
carries only the vector register and the displacement. No `EC` row is added:
`EC-35` and `EC-38` already state the shape and the reach, and both are revised
in place so the EVEX family joins their statements.**

The appended rows, one per `(width, direction, displacement form, base)`:

| Width | Load `form_id` | Store `form_id` | Prefix and tail |
|---|---|---|---|
| `xmm` | `x86:vmovaps/xmm-{rsp,r12}-disp8x16/evex`, `…-disp32/evex` | `x86:vmovaps/{rsp,r12}-disp8x16-xmm/evex`, `…-disp32-xmm/evex` | `62 {f1,d1} 7c 08`, then `28`/`29` `44`/`84` `24` `disp` |
| `ymm` | the same two names with `ymm` in place of `xmm` and `disp8x32` in place of `disp8x16` | the same two names with `ymm` in place of `xmm` and `disp8x32` in place of `disp8x16` | `62 {f1,d1} 7c 28`, same tail |
| `zmm` | the same two names with `zmm` in place of `xmm` and `disp8x64` in place of `disp8x16` | the same two names with `zmm` in place of `xmm` and `disp8x64` in place of `disp8x16` | `62 {f1,d1} 7c 48`, same tail |

Four properties follow:

- **The base is the form.** `%rsp` and `%r12` both spend the `SIB` byte, and
  they differ in the fixed `P0` `B̄` bit, so no operand value changes a length
  and no single row can carry both.
- **The vector slot stays where it is.** `dest`/`src` sit at `[43,3]` with
  `[12,1]`/`[15,1]` inverted on all twenty-four rows, because the prefix does
  not grow; the displacement moves to `[56,…]`.
- **The width is the row's.** The `disp8xN` unit and the `L'L` byte are form
  facts (`EC-09`, `EC-39`), so `16`/`32`/`64` are the same content `1` on the
  three widths.
- **The full register file is already reachable.** The EVEX slots are five
  bits, so `%xmm20`, `%ymm21` and `%zmm30` encode on these rows at no length
  cost; the fixture uses `zmm16`–`zmm23` to pin it.

## Consequences

- `0.21.0` is a 195-form document with digest
  `sha256:30af3fec5c2f50e3ab30fb30d32e6b2e71f4520dbdb2660c6c9de1767b7b1160`.
- Its positive fixture `X86-P25-evex-mem-sib` has twenty-four instructions and
  228 bytes, one per row: the `xmm` eight run `xmm0`–`xmm7`, the `ymm` eight
  `ymm8`–`ymm15`, the `zmm` eight `zmm16`–`zmm23`.
- Negatives pin the version boundary against `0.20.0`, the absent
  `mod = 00` `SIB` shape, an operand-class mismatch, the extra `base` operand a
  fixed-base row refuses, the `disp8x16` content end and the five-bit register
  field end.
- `07_definition_format.md` §8.1 gains the twenty-four rows, the `0.21.0`
  digest row and narrative; `02_encoding_choices.md` gains the surface rows and
  revises `EC-35` and `EC-38` in place.
- No schema, loader or materializer change: the rows use the fixed-base shape
  `0.3.0` introduced and the `SIB` byte is part of the template.
- Still absent on this axis: `mod = 00` with a `SIB` base, an index or scale
  under these opcodes, the other EVEX SSE memory mnemonics, and EVEX masking.

## Alternatives rejected

- **One row per width with a four-bit base and a mandatory `SIB`.** A general
  base would start spending a `SIB` byte it does not need (`EC-35`), so every
  existing EVEX memory byte would change.
- **A `sib` modifier or a `base` operand that selects the shape.** A modifier
  may not write bits (`ADR-0015`) and the length would become a plan choice
  (`INV-04`).
- **One row for both bases with the `B̄` bit as an operand.** `B̄` is the
  fixed template byte that distinguishes `%rsp` from `%r12`; making it a slot
  would turn a base decision into an operand value while the base is fixed.
- **Fold `mod = 00` in.** `(%rsp)` drops the displacement byte entirely
  (`62 f1 7c 08 28 04 24`), which is the no-displacement decision, not this one.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `62 f1 7c 08 28 44 24 01`, `62 d1 7c 08 28 44 24 01`, `62 f1 7c 08 29 64 24 01` and their round trip | `llvm-mc -show-encoding` / `-disassemble`, `EXP-0050` §1 | high |
| `dest`/`src` stay at `43` and `disp` moves `48 → 56` | the byte strings above; `EXP-0050` §2 | high |
| `%r12` differs from `%rsp` only in `P0` (`f1` → `d1`), at equal length | `llvm-mc -show-encoding`, `EXP-0050` §2 | high |
| `disp8*N` content is unchanged by the `SIB`; `8(%rsp)` promotes to `disp32` | `llvm-mc -show-encoding`, `EXP-0050` §§1, 3 | high |
| `%xmm20`/`%ymm21`/`%zmm30` encode on these rows at no length cost | `llvm-mc -show-encoding`, `EXP-0050` §4 | high |
| `%r13` stays on the existing `-base-disp8x16` row | `llvm-mc -show-encoding`, `EXP-0050` §4 | high |
| `%xmm32` is `error: invalid register name` | `llvm-mc` error text, `EXP-0050` §5 | high |

## Review triggers

- `mod = 00` with a `SIB` base is attempted: `62 f1 7c 08 28 04 24` is the
  zero-displacement shape, and `%rbp`/`%r13` need the `disp8` zero form.
- An index or scale is attempted: `16(%rsp,%rax,1)` is
  `62 f1 7c 08 28 44 04 01`, a different `SIB` byte (`index = 000`).
- A second EVEX SSE mnemonic is attempted (`vmovups`, `vmovdqa`): the same
  shape with a different opcode byte, a coverage slice with no new `EC` fact.
- EVEX masking is attempted: `{k1}` writes the `aaa` field, a bit this shape
  does not carry.
