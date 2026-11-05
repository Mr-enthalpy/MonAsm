# EXP-0032 — x86-64 encoding families: legacy SSE, VEX and EVEX

- Date: 2026-11-05
- Question: does one operation at one operand shape have three legal encodings,
  and what does each prefix family fix?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition source: none. The field names below are conventional labels; the
  values are read off the measured bytes, and no ISA manual text was re-read for
  this slice.
- Fixture oracle: `EXP-0005` (regenerated with `P9.asm` added)

## 1. The shape

All three families encode `movaps`/`vmovaps` as an opcode followed by `ModRM`
(`mod` 7–6, `reg` 5–3, `r/m` 2–0). What changes is the prefix before the
opcode, and with it the byte index of `ModRM`:

| Family | Bytes before `ModRM` | `ModRM` at |
|---|---|---|
| legacy SSE | `0F 28` | byte 2 (bit 16) |
| two-byte VEX | `C5` + one byte | byte 3 (bit 24) |
| EVEX | `62` + three bytes | byte 5 (bit 40) |

The prefix bytes are not operands: no plan field names them, and no register
number writes them. Their variable bits are fixed by the row.

Conventional bit names, with the values this slice measures:

| Byte | Bits | `movaps` value | Meaning |
|---|---|---|---|
| VEX byte 1 | 7 | `1` | `R̄` (inverted `REX.R`) |
| | 6–3 | `1111` | `vvvv`, stored inverted; `1111` means "no third operand" |
| | 2 | `0` | `L` (0 = 128-bit) |
| | 1–0 | `00` | `pp` (no mandatory prefix) |
| EVEX P0 | 7–4 | `1111` | `R̄`, `X̄`, `B̄`, `R̄'` |
| | 3–2 | `00` | reserved |
| | 1–0 | `01` | `mm` = `0F` map |
| EVEX P1 | 7 | `0` | `W` |
| | 6–3 | `1111` | `vvvv`, stored inverted |
| | 2 | `1` | fixed 1 |
| | 1–0 | `00` | `pp` |
| EVEX P2 | 7 | `0` | `z` (no zeroing) |
| | 6–5 | `00` | `L'L` (00 = 128-bit) |
| | 4 | `0` | `b` (no broadcast/rounding) |
| | 3 | `1` | `V'`, inverted |
| | 2–0 | `000` | `aaa` (no mask) |

## 2. The fields, measured

One instruction per run, `llvm-mc -show-encoding`:

| Source | Encoding | Reading |
|---|---|---|
| `movaps %xmm1, %xmm0` | `0f 28 c1` | no prefix; `reg = 000`, `r/m = 001` |
| `vmovaps %xmm3, %xmm2` | `c5 f8 28 d3` | 2-byte VEX; `reg = 010`, `r/m = 011` |
| `vmovaps %zmm1, %zmm0` | `62 f1 7c 48 28 c1` | EVEX.512; `L'L = 10` |
| `movaps %xmm8, %xmm9` | `45 0f 28 c8` | `REX.R`/`REX.B` set by registers 8/9 |

`llvm-mc -disassemble` on byte strings the assembler will not select:

| Bytes | Decodes as |
|---|---|
| `62 f1 7c 08 28 c1` | `vmovaps %xmm1, %xmm0` |
| `62 f1 7c 08 28 e5` | `vmovaps %xmm5, %xmm4` |
| `62 f1 7c 28 28 c1` | `vmovaps %ymm1, %ymm0` |
| `62 f1 7c 48 28 c1` | `vmovaps %zmm1, %zmm0` |
| `62 71 7c 08 28 c1` | `vmovaps %xmm1, %xmm8` |

Four readings from the tables:

1. **Three families, one operation.** `0f 28 c1`, `c5 f8 28 c1` and
   `62 f1 7c 08 28 c1` all decode as a move between `xmm0` and `xmm1`. The
   operation and the operands are identical; the bytes are not.
2. **VEX and EVEX are both legal at the same width.** The assembler emits VEX
   for `vmovaps %xmm1, %xmm0` (`c5 f8 28 c1`), never EVEX, yet the EVEX byte
   string decodes to the same instruction. Without a family component in the
   `form_id`, two honest implementers would emit different bytes for the same
   plan (`INV-02`).
3. **The prefix length moves `ModRM`.** `reg = 1` is bit 19 in `0f 28 c1`, bit
   27 in `c5 f8 28 c1` and bit 43 in `62 f1 7c 08 28 c1`. The family is the
   front of the template, not a byte appended later.
4. **The prefix fixes the extension bits.** `xmm0`–`xmm7` need none, so `R̄`,
   `B̄`, `R̄'` and `V'` are all `1` (inverted zero). `movaps %xmm8, %xmm9` sets
   `REX.R`/`REX.B` (`45`), and `62 71 7c 08 28 c1` sets `R̄ = 0` to reach
   `xmm8`. A row that accepted `xmm8` would have to change its own prefix per
   operand, which is the value-driven shape this slice keeps out
   (`E-OPERAND-004`).

## 3. The vector

Input `P9.asm` (LF, trailing newline; 41 bytes,
`sha256:20511b368d774490def64d52e7b81c2cfa7f8199e3386691b6cb85842f2cf327`):

```text
movaps %xmm1, %xmm0
vmovaps %xmm3, %xmm2
```

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | `0f 28 c1` | legacy SSE: `reg = %xmm0`, `r/m = %xmm1` |
| 3 | `c5 f8 28 d3` | two-byte VEX: `reg = %xmm2`, `r/m = %xmm3` |
| 7 | `62 f1 7c 08 28 e5` | EVEX.128: `reg = %xmm4`, `r/m = %xmm5` |

The third instruction is the EVEX.128 twin of the second: `llvm-mc` always emits
`c5 f8 28 e5` for `vmovaps %xmm5, %xmm4`, so the `62 …` bytes are verified by
`llvm-mc -disassemble` (`vmovaps %xmm5, %xmm4`). The oracle record says
`manual+disassembly` and carries that line.

Output: 13 bytes,
`sha256:2afcdc1f68f1d0b6c1bd58495a20f8d94d61bac3c294bd58beb4184e6ed13714`,
`bytes_hex` `0f28c1c5f828d362f17c0828e5`.

No relocations: every operand is a register, so the record has `records = 0`.

## 4. What this fixes, and what it does not

Fixes:

- the family as the `/legacy`, `/vex` or `/evex` component of the `form_id`,
  with no operand, modifier or second selector;
- the template carrying the prefix, and the `ModRM` placements that follow from
  its length (`[19,3]`/`[16,3]`, `[27,3]`/`[24,3]`, `[43,3]`/`[40,3]`);
- `x86.xmm` as a single kind across the three families, because the register
  set does not change with the family;
- the extension set: `0.5.0` declares `avx`, `avx512f` and `avx512vl`, and a
  plan naming the table must declare the same sorted list (`E-TARGET-001`);
- the negative evidence: an unfamilied id is `E-FORM-001` (`N01aa`), the VEX
  row against `0.4.0` is `E-FORM-001` (`N01ab`), a `zmm` operand is
  `E-OPERAND-001` on both `kind` and `target_type` (`N02l`), a plan without the
  extensions is `E-TARGET-001` (`N06`), and `xmm8` is `E-OPERAND-004` (`N14b`).

Does not fix:

- **the store direction (`0F 29`).** The direction pair is `X86-P1`'s question
  at 64 bits; this slice pins one direction per family.
- **memory operands.** A memory source brings back `mod`/SIB, and EVEX also
  changes displacement compression (`disp8*N`), which is not modelled.
- **`ymm`/`zmm`.** They change `L`/`L'L` and, above register 15, need `R'`/`V'`
  as operand-owned bits.
- **masking.** `aaa` and `{z}` are operands or separate forms, not modifiers.
- **the three-byte `C4` VEX form.** It carries a different `mmmmm` and `X`/`B`,
  so the same `/vex` suffix would not pin the template.
- **`movapd`/`movdqa`.** Their mandatory `0x66` moves into VEX/EVEX `pp`, so
  the prefix is a family-internal field, not the `0x66` of `EC-36`.

## 5. Result

The rows ship in `definitions/x86_64/0.5.0.json`, which repeats the twenty-two
`0.4.0` forms and adds three:

```text
definition  definitions/x86_64/0.5.0.json
namespace   monasm.isa.x86
version     0.5.0
forms       25
extensions  avx, avx512f, avx512vl
digest      sha256:24256f0c427447ee8db5506d7b395e3682dbb3b0317f0effa1ed3c4f75cc0aeb
```

`07_definition_format.md` §8 records the digest and the rows; `EXP-0005` §2
records the regenerated fixture.

Our materializer emits the 13 bytes above and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `X86-P9-sse-vex-evex` | two assembled families plus the decode-verified EVEX row | 13 bytes, `sha256:2afcdc1f…`, no record |
| `N01aa-absent-unfamilied-vmovaps-form` | `x86:vmovaps/xmm-xmm` with no suffix | `E-FORM-001` |
| `N01ab-vex-form-absent-in-0.4.0` | the VEX row against `0.4.0` | `E-FORM-001` |
| `N02l-zmm-operand-on-xmm-evex-form` | `x86.zmm`/`zmm` on the EVEX `xmm` row | `E-OPERAND-001` on `kind` and `target_type` |
| `N06-extension-list-mismatch` | the `0.5.0` legacy row with `enabled_extensions: []` | `E-TARGET-001` |
| `N14b-xmm8-wider-than-field` | `reg = 8` in a 3-bit `xmm` field | `E-OPERAND-004` |
