# ADR-0033: A GPR operand is four bits; the form owns the REX extension bit

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P10` (the extended GPR file) and the `R`/`B` half of `EC-06`
- Supersedes: none
- Superseded by: none

## Context

`0.1.0`–`0.5.0` give every x86-64 register slot a 3-bit placement, because the
`ModRM` register fields are three bits. `llvm-mc` 23.1.2 measures what that
excludes, on 2026-11-05:

| Source | Bytes | Reaches |
|---|---|---|
| `movq %r8, %r9` | `4d 89 c1` | `r8`–`r15` |
| `movq %r15, %rax` | `4c 89 f8` | `r8`–`r15` |
| `movq %rax, %r12` | `49 89 c4` | `r8`–`r15` |
| `movq %rax, %rbx` | `48 89 c3` | `rax`–`rdi` |

The fourth byte string is the same instruction as the first three with every
extension bit zero. So the register number is one value of four bits, and the
high bit lives in a prefix bit the form already contains: `REX.B` (bit 0) extends
`ModRM.r/m` and `REX.R` (bit 2) extends `ModRM.reg`. `mov %r8, %r9` is
`REX.WRB = 4d`, `modrm = c1` (`mod = 11`, `reg = 1`, `r/m = 0`).

There were two candidate answers:

- **A** one row per extension-bit combination (`-ext-rm`, `-ext-reg`, `-ext-both`),
  keeping every slot 3 bits wide;
- **B** one row per operand shape, with a 4-bit slot whose first placement is the
  extension bit.

## Decision

**B. A register-direct GPR operand is a 4-bit value; the form fixes where each
bit goes.**

- The slot's placements are ordered most-significant first: `[0,1]` then `[16,3]`
  for `ModRM.r/m` (`REX.B` is bit 0 of the `REX` byte), and `[2,1]` then `[19,3]`
  for `ModRM.reg` (`REX.R` is bit 2). Both are ordinary placements; nothing about
  the value is computed by the materializer.
- There is exactly **one** encoding of `(form, operand values)`. `mov %rax, %rbx`
  through `x86:mov/rm-r64/legacy` is `48 89 c3`; the `REX.R` bit is register
  `rbx`'s bit 3, which is zero. A second spelling with a redundant `REX` bit is
  not reachable, because no operand bit can set it. Option A would have made the
  redundant spelling reachable as a separate `form_id` and would have doubled the
  table for no new information.
- The width is a property of the **table version**, not a new `form_id`. `0.6.0`
  changes the same six `form_id`s from 3-bit to 4-bit register slots:
  `x86:mov/rm-r64/legacy`, `x86:mov/r64-rm/legacy`, `x86:add/rm64-imm8/legacy`,
  `x86:add/rm64-imm32/legacy`, `x86:mov/r64-riprel32/legacy` and
  `x86:mov/riprel32-r64/legacy`. A `0.5.0` plan keeps its 3-bit table because the
  plan pins `definition_identity.version` and `digest`; this is a version
  boundary, not a silent widening.
- An operand that does not fit is rejected, never truncated. On `0.5.0`,
  `reg = 8` is `E-OPERAND-004` with `field_bits = 3`; on `0.6.0`, `reg = 16` is
  `E-OPERAND-004` with `field_bits = 4`. Truncating `mov r9, r8` (`4d 89 c1`) to
  three bits per field yields `48 89 c1`, which disassembles as `movq %rax, %rcx`
  — a different register pair, the failure `EXP-0004` §3 measured.

## Rows deliberately left at three bits

| Family | Why | Next step |
|---|---|---|
| base+displacement rows (`X86-P4`) | `r12`/`r13` change the addressing form: `r/m = 100` forces a SIB byte and `mod = 00` with `r/m = 101` is `RIP`-relative. Widening the base field without the SIB and `mod` rules would emit a different instruction. | its own ADR with the SIB/index slice (`EC-35`) |
| 16-bit rows (`0.4.0`) | the table has no `REX` byte; `r8w` needs a prefix byte inserted between `0x66` and the opcode, so the template grows by one byte | its own ADR |
| 8-bit rows (`0.4.0`) | `r8b`–`r15b` need `REX`, and any `REX` re-labels `ah`–`bh`; the low-byte rows are split by REX presence, so the extension is a family question first (`ADR-0029`) | its own ADR |
| high-byte row | `REX` is illegal with `ah`–`bh`; there is no extension bit to place | never |
| SSE/VEX/EVEX rows (`0.5.0`) | the extension bits are `REX.R` for legacy, but inverted `~R`/`~X`/`~B` in VEX, and `R'`/`X'`/`B'` in EVEX; the bit positions move with the prefix length | its own ADR |

The `REX.X` bit stays unexercised: it extends a SIB index, and no v0 form has an
index operand.

## Consequences

- `0.6.0` is a new document with a new digest; `X86-P10-gpr-extended` is its
  positive fixture (44 bytes: four register-direct transfers, the store and load
  directions, both `add` immediates, both `RIP`-relative directions and a 4-byte
  data fragment), measured against `llvm-mc` 23.1.2 (`EXP-0035`).
- `N14c` pins the version boundary (`reg = 8` on `0.5.0` is `field_bits = 3`) and
  `N14d` the new field end (`reg = 16` on `0.6.0` is `field_bits = 4`). `N14`
  stays as it is: it names `0.1.0`, whose field is still three bits.
- `EC-06` keeps its `frozen` status and now records that `W`, `R` and `B` are
  carried; `X` and the high-byte exclusion remain the halves without a v0 row.
- `07_definition_format.md` §8.1 shows the `0.6.0` placements, because the table
  is keyed by `form_id` and the newest table is the one in force.
