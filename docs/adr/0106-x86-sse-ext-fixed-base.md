# ADR-0106: the legacy SSE fixed-base rows gain the extended register window

- Status: accepted
- Date: 2026-11-09
- Settles: `X86-P76` (the eight `xmm8`-`xmm15` fixed-base rows and their byte
  vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-38` of `02_encoding_choices.md` (the reach-is-a-form rule gains
  the register operand); the reading-aid table and `0.70.0` paragraph of
  `07_definition_format.md` §8.1; the x86 table of `06_validation_matrix.md`;
  adds `definitions/x86_64/0.70.0.json`, `EXP-0107` and the
  `X86-P76`/`N01ep`/`N02cy`/`N03zt` fixtures

## Context

`0.20.0` shipped the four fixed-base legacy SSE `movaps` rows (`%rsp`/`%r12` ×
load/store × `disp8`/`disp32`). They carry `ModRM.reg` as a three-bit slot, so
they reach only `xmm0`-`xmm7`; `N14w` pins that window with `E-OPERAND-004`.
The general base rows already gained the `xmm8`-`xmm15` window in `0.11.0`
(`xmm-ext-base-disp8`/`-disp32`), because their template already carries a
`REX` byte for the base's fourth bit.

The fixed `%rsp`/`%r12` rows have no `REX` byte at all. `EXP-0107` measures what
the register's fourth bit costs there: `movaps 8(%rsp), %xmm8` is
`44 0f 28 44 24 08` (six bytes) while `movaps 8(%rsp), %xmm0` is
`0f 28 44 24 08` (five), and `%r12` pays `45` for `REX.R` and the fixed
`REX.B`. The byte appears only when the register is 8-15, so emitting it from
the operand value would make the instruction length a function of an operand —
the exact shape `INV-04` forbids.

## Decision

1. **Eight `-ext` rows, not a widened slot.** `0.70.0` appends
   `x86:movaps/xmm-ext-rsp-disp8/legacy`,
   `x86:movaps/xmm-ext-rsp-disp32/legacy`,
   `x86:movaps/xmm-ext-r12-disp8/legacy`,
   `x86:movaps/xmm-ext-r12-disp32/legacy`,
   `x86:movaps/rsp-disp8-xmm-ext/legacy`,
   `x86:movaps/rsp-disp32-xmm-ext/legacy`,
   `x86:movaps/r12-disp8-xmm-ext/legacy` and
   `x86:movaps/r12-disp32-xmm-ext/legacy`. Each is the measured `EXP-0107`
   template with the register and displacement zeroed (`44…` for `%rsp`,
   `45…` for `%r12`).
2. **The register slot is the existing `-ext` shape.** `x86.xmm`/`xmm` at
   `[2,1]` (`REX.R`) and `[27,3]` (`ModRM.reg`), with `0`-`7` excluded, exactly
   as `xmm-ext-base-disp8` spells it. The displacement moves one byte to
   `[40,8]`/`[40,32]` because the `REX` byte is new.
3. **The low rows are unchanged.** `xmm0`-`xmm7` keeps its five/six/eight/nine
   byte rows and its `E-OPERAND-004` window (`N14w`); a plan that wants
   `xmm8`-`xmm15` names the `-ext` row instead of asking the materializer to
   widen the low one.
4. **The extension requirement stays `[]`.** These are legacy-SSE rows; no
   AVX/AVX-512 extension is involved.
5. **`0.70.0` is additive and immutable.** It repeats the 519 `0.69.0` forms
   byte-for-byte; the generator asserts the reproduction before it writes the
   new version. The digest is
   `sha256:02cbd866ce04b7584456bccf177c1aef7395a6b503240ddd1617be8e73f9eb2e`.

## Consequences

- `X86-P76-sse-ext-fixed-base` is the 60-byte vector of eight instructions, all
  `movaps`, no label and no relocation. The oracle input hash is
  `b465ac746967c9ab8ede119518bf950c28b3abe8a585d2276d248d2ae7411c68` and the
  output hash is
  `d2fef597f7b2174b80f8ad83271369932d03582eaca6c70a5e7f0f825f1a7f63`.
- `N01ep` pins the `0.69.0` boundary, `N02cy` the operand count
  (`expected: 2`, `found: 1`) and `N03zt` the signed-8 end at the new
  displacement placement.
- The corpus grows to 117 positives and 574 negatives; every one of the 527
  forms in `0.70.0` is named by a positive fixture (`check_definition.py`).
- `0.69.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **Widen the existing `xmm0`-`xmm7` slot to four bits and let the materializer
  add `REX`.** Rejected: the byte is present only for values 8-15, so the
  instruction length would depend on the operand (`INV-04`); the existing
  `0.9.0` shared field is the counterexample that could not (`N14f`/`N14g`).
- **Reuse `xmm-ext-base-disp8` and drop the fixed base.** Rejected: `%rsp`
  forces the `SIB` byte and `%r12` forces `REX.B`; they are byte-affecting
  address shapes (`EC-35`), not a base operand's value.
- **Add only the `disp8` rows and let `disp32` follow.** Rejected: `disp8` and
  `disp32` are separate `ModRM.mod` choices (`EC-02`), so each length has to be
  its own row.
- **Move the window to VEX instead.** Rejected: the VEX rows already reach
  `xmm15` at no extra length by clearing `R̄`; the missing window is the legacy
  fixed-base one.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The eight instructions are 6/6/9/9/6/6/9/9 bytes | `llvm-mc` object bytes, `EXP-0107` §2 | high |
| `REX.R` is bit 2 and the displacement shifts to `[40,…]` | placement arithmetic on the measured bytes | high |
| `xmm0`-`xmm7` on the low rows is `E-OPERAND-004` | `N14w` fixture gate | high |
| `0.70.0` repeats `0.69.0` unchanged | generator assertion and digest | high |
| `N01ep` is `E-FORM-001`, `N02cy` `E-OPERAND-002`, `N03zt` `E-RANGE-001` | fixture gate, `EXP-0107` §4 | high |

## Review triggers

- The `xmm-ext` window is proposed for another legacy SSE mnemonic; the opcode
  changes and the row must be measured, not copied from `movaps`.
- An indexed legacy SSE row is proposed with `xmm8`-`xmm15`; the index adds a
  `SIB` scale/index choice and cannot reuse these placements blindly.
- A VEX/EVEX fixed-base row is proposed to gain a new window; those families
  carry their register bits in the prefix and do not pay a new byte.
- The `0x67` address-size prefix meets an `-ext` row; `ADR-0084` owns the
  prefix order and this ADR does not move the field.
