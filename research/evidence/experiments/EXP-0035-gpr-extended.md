# EXP-0035 — x86-64 `r8`–`r15` in a register-direct transfer

- Date: 2026-11-05
- Question: how does one register field reach sixteen GPRs, and what does a
  3-bit field do to a register number that needs four bits?
- Toolchain: `llvm-mc`/`llvm-objcopy`/`llvm-objdump` 23.1.2
- Definition: `definitions/x86_64/0.6.0.json`
  (`sha256:79952b5dc726d18378651498ee35452645d08a4f7a66a133679bc86efa5839f5`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P10-gpr-extended.oracle.json`
- Source: `research/evidence/experiments/EXP-0035/P10.asm`
- Decision: `ADR-0033`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on the source below:

| Source | Bytes | `REX` | `ModRM` |
|---|---|---|---|
| `movq %r8, %r9` | `4d 89 c1` | `0100 1101` — `W=1 R=1 X=0 B=1` | `11 001 000` |
| `movq %r15, %rax` | `4c 89 f8` | `0100 1100` — `W=1 R=1 X=0 B=0` | `11 111 000` |
| `movq %r15, %r8` | `4d 89 f8` | `0100 1101` — `W=1 R=1 X=0 B=1` | `11 111 000` |
| `movq %rax, %rbx` | `48 89 c3` | `0100 1000` — `W=1 R=0 X=0 B=0` | `11 011 000` |

The low three bits of the register number are the `ModRM` field; the fourth bit
is the prefix bit: `R` (bit 2) for `ModRM.reg`, `B` (bit 0) for `ModRM.r/m`.
`movq %r8, %r9` puts `r9 = 8+1` in `r/m` (bit 3 → `B=1`, low bits → `001`) and
`r8 = 8+0` in `reg` (bit 3 → `R=1`, low bits → `000`), so `REX = 4d` and
`ModRM = c1`. The fourth row is the same form with both high bits zero.

## 2. Why this is one row, not four

A 4-bit slot with placements `[0,1]`, `[16,3]` (r/m) or `[2,1]`, `[19,3]`
(reg) writes exactly one byte string per operand value, because the prefix bit
is a bit of the value, not an independent choice:

- `r8` → `REX.B = 1`; `rax` → `REX.B = 0`. There is no operand value that leaves
  the bit unset while naming `r8`, so a redundant `REX` spelling of
  `mov rax, rbx` is not representable.
- Writing the same forms with 3-bit slots and separate `-ext-*` rows would make
  the register number the *sum* of a form suffix and a field, and would let the
  planner pick a redundant prefix. That is the ambiguity `INV-02` forbids.

The templates do not change: `4889c0`, `488bc0`, `4883c000`, `4881c000000000`,
`488b0500000000`, `48890500000000` already contain the `REX` byte with bits 0
and 2 clear. Only the six slots change.

## 3. The oracle

`P10.asm` holds seven mnemonics and two `.byte` lines:

```text
movq %r8, %r9                4d 89 c1
movq %r15, %rax              4c 89 f8
.byte 0x4c, 0x8b, 0xe0       4c 8b e0   (8B /r, reg = r12, r/m = rax)
.byte 0x4d, 0x8b, 0xf5       4d 8b f5   (8B /r, reg = r14, r/m = r13)
movq %r15, %r8               4d 89 f8
addq $1, %r8                 49 83 c0 01
addq $0x7fffffff, %r15       49 81 c7 ff ff ff 7f
movq L1(%rip), %r10          4c 8b 15 07 00 00 00
movq %r11, L1(%rip)          4c 89 1d 00 00 00 00
```

The two `8B` rows are hand-derived from the same placement rule and emitted as
bytes, because `llvm-mc` always selects the `89` direction for a register-to-
register move (`EC-27`). `llvm-mc -disassemble` on the twenty-four bytes of the
first five instructions prints:

```text
movq  %r8, %r9
movq  %r15, %rax
movq  %rax, %r12
movq  %r13, %r14
movq  %r15, %r8
```

so the `8B` byte strings decode to the intended register pair. The assembled
`.text` is 44 bytes: 40 bytes of instruction plus the 4-byte `L1` payload. Output
SHA-256 `134663b4a66f551f8681364e663208681b903fd590528f9fe023571495ea409d`.

`addq $0x7fffffff, %r15` is used instead of `$-1` on purpose: the assembler
shortens `-1` to the `imm8` row, and the fixture must exercise `rm64-imm32`
without asking the materializer to choose between the two.

## 4. The rejection

`N14c` names `0.5.0` and `dest.reg = 8`. The slot there is three bits, so the
plan is rejected before any byte is written:

```text
E-OPERAND-004  /instructions/0/operands/0/payload/reg
               target_type=rm64 value=8 field_bits=3
```

`N14d` names `0.6.0` and `dest.reg = 16`, one past the widened field:
`E-OPERAND-004` with `field_bits=4`.

The counterexample is `EXP-0004` §3: truncating `4d 89 c1` to three bits per
field gives `48 89 c1`, which `llvm-objdump` decodes as `movq %rax, %rcx` — a
different source and destination. A materializer that masked instead of rejecting
would emit that, and `expected_size` (3 bytes either way) would not see it; only
`expected_digest` would.

## 5. What this does not claim

- `REX.X` is unexercised: it extends a `SIB` index, and no v0 row has one.
- The base+displacement rows keep 3-bit base fields. Widening them needs the
  `SIB` and `mod = 00`/`r/m = 101` rules, because `r12` forces a `SIB` byte and
  `r13` with `mod = 00` is `RIP`-relative (`ADR-0033`).
- The 8-bit and 16-bit rows keep 3-bit fields: a 16-bit extended register needs a
  `REX` byte inserted after `0x66`, and a low byte extended register changes the
  `ah`/`spl` split (`ADR-0029`).
- The SSE/VEX/EVEX rows keep 3-bit fields: their extension bits are inverted
  (`~R`/`~X`/`~B`) or move with the prefix length.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
