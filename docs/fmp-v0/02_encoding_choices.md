# Encoding Decisions and Their Carriers

Status: **draft** (registry rows are frozen individually). This is the operational
form of INV-02, under ADR-0004.

## The rule

Given a frozen plan and a pinned definition, exactly one byte sequence may result.
A byte-affecting decision is legal only if it is carried by an explicit plan field.
The carriers are a closed set:

| Carrier | How the plan expresses it |
|---|---|
| `form variant` | the `<variant>` component of `form_id`, e.g. `rm64-imm8` vs `rm64-imm32` |
| `encoding family` | the `<encoding_family>` component of `form_id`, e.g. `legacy` / `vex` / `evex` |
| `operand type` | an operand's `kind` / `target_type`, e.g. `wreg` vs `xreg`, `imm8` vs `imm32` |
| `operand modifier` | an entry in `operands[].modifiers`, e.g. `lock`, `addr_size`, `aq` |
| `fixup field` | a required field of the fixup record, e.g. `pc_reference_rule` |
| `target identity` | a field of `target_identity`, e.g. `execution_mode`, `enabled_extensions` |
| `none` | the variation is unsupported; the definition pins one output and a plan cannot ask for the other |

If no carrier is named, the decision is missing and the definition MUST NOT supply
a default. ADR-0004 removed `encoding_choices` as a carrier: a plan states a
machine form, not a form plus a modifier list that restates it.

Two failure modes to avoid:

- **Under-frozen:** the materializer still has to choose. Detected by asking "could
  two honest implementers of this definition emit different bytes for this plan?"
- **Over-frozen:** the plan carries bit patterns and the definition becomes
  decorative. Detected by asking "would this plan still be valid after a
  legitimate definition bug-fix that does not change observable semantics?"

## Test used to classify a decision

For each candidate:

1. Name the two or more legal outputs and their observable difference.
2. Ask whether the difference is *implied by naming the form* (same `form_id` ⇒
   same bytes). If yes, the carrier is `form variant` or `encoding family`, and
   the two outputs need different `form_id`s.
3. Ask whether the difference is *implied by a typed operand* (e.g. a width-typed
   value or register class). If yes, the carrier is `operand type` or
   `operand modifier`.
4. Ask whether the difference is a range legality issue rather than a choice. If
   yes, it is `E-RANGE-*`, not a carrier.
5. Ask whether the difference belongs to layout or to a fixup field. If yes, it is
   a `fill` fragment or a required fixup field.
6. Otherwise the difference is **not expressible in v0**: the carrier is `none`,
   the definition must pin one output, and the other must be unreachable.

A decision that reaches step 6 is not silently dropped. It is recorded here with
`none` and a negative test proving the unsupported variation cannot be requested.

## Registry

`frozen` means the counterexample is written and the carrier is decided. `draft`
means the carrier is plausible but no observed counterexample exists yet; it must
not be moved to `frozen` on the strength of an argument alone.

| ID | ISA | Legal outputs | Observable difference | Carrier | Counterexample if the carrier is removed | Status |
|---|---|---|---|---|---|---|
| EC-01 | x86-64 | `add r/m64, imm` as sign-extended imm8 (`83 /0 ib`) vs imm32 (`81 /0 id`) | 4 vs 7 bytes with `REX.W` | `form variant` (`rm64-imm8` / `rm64-imm32`) | `add rax, 1` is legal both ways (`48 83 c0 01`, `48 81 c0 01 00 00 00`); an encoder that picks by value violates INV-02 and shifts every later offset. | frozen |
| EC-02 | x86-64 | Memory displacement as none (`mod=00`), disp8 (`mod=01`) or disp32 (`mod=10`) | 0 vs 1 vs 4 displacement bytes | `form variant` (`mem-disp0` / `mem-disp8` / `mem-disp32`) | `mov rax, [rbp-8]` → `48 8b 45 f8` (disp8); `[rbp-200]` → disp32. The no-displacement shape is a third legal encoding, not a zero value: `movaps (%rax), %xmm0` is `0f 28 00` (3 B), `0f 28 40 00` (4 B, `mod = 01`, `disp8 = 0`) decodes as the same instruction, and `llvm-mc -disassemble` reads both identically. All three widths are now forms: `0.2.0` took the RIP shape (`EC-34`), `0.3.0` took base+disp8/disp32 (`EC-35`, `ADR-0028`), and `0.12.0` takes the no-displacement SSE rows (`ADR-0039`, `EXP-0041`); the EVEX `disp8` field is compressed (`EC-39`, `ADR-0036`); `0.22.0` takes the EVEX no-displacement shape at `%rsp`/`%r12` (`ADR-0049`, `X86-P26`, `EXP-0051`); and `0.23.0` takes all three shapes with a `SIB` index and scale, where the same `mod` field decides whether the displacement slot exists (`ADR-0050`, `X86-P27`, `EXP-0052`); `0.24.0` adds the fourth combination — no base at all (`SIB.base = 101`), where `mod = 00` *is* the `disp32` request, so `vmovaps (,%rax,4), %xmm1` is `62 f1 7c 08 28 0c 85 00 00 00 00` and stays eleven bytes at offset zero (`ADR-0051`, `X86-P28`, `EXP-0053`). `0.25.0` closes the byte: the absolute address is `SIB = 25`, where `index = 100` and `base = 101` are both constants, so `vmovaps 0x1234, %xmm0` is `62 f1 7c 08 28 04 25 34 12 00 00` — eleven bytes, with `0` as content `0` rather than a dropped slot (`ADR-0052`, `X86-P29`, `EXP-0054`). `0.26.0` moves the byte into the 64-bit GPR `mov` family: `movq 0x1234, %rax` is `48 8b 04 25 34 12 00 00`, again with the address as four bytes of content rather than a dropped slot (`ADR-0053`, `X86-P30`, `EXP-0055`). `0.27.0` carries it into the 32-bit rows in both register windows: `movl 0x1234, %eax` is `8b 04 25 34 12 00 00` (seven bytes) and `movl 0x1234, %r8d` is `44 8b 04 25 34 12 00 00` (eight), so the same `disp32` slot sits at `[24,32]` or `[32,32]` depending on the row (`ADR-0054`, `X86-P31`, `EXP-0056`). `0.28.0` adds the 16-bit rows, where the `66` prefix precedes the same `04`/`25` bytes: `movw 0x1234, %ax` is `66 8b 04 25 34 12 00 00` (eight bytes) and `movw 0x1234, %r8w` is `66 44 8b 04 25 34 12 00 00` (nine), so the address sits at `[32,32]` or `[40,32]` and the operand width never narrows it — `-32768` is still `00 80 ff ff` (`ADR-0055`, `X86-P32`, `EXP-0057`). `0.29.0` closes the width axis at eight bits, where the field sits at `[24,32]` when the row has no `REX` byte and at `[32,32]` when it has one: `movb -128, %bl` is `8a 1c 25 80 ff ff ff` and `movb %dil, -32768` is `40 88 3c 25 00 80 ff ff` (`ADR-0056`, `X86-P33`, `EXP-0058`). `0.31.0` finally brings the third shape to that same byte `mov` family: `movb (%rax), %al` is `8a 00` (two bytes) and `movb (%r8), %r15b` is `45 8a 3f` (three), each one byte shorter than the `disp8` row beside it, while `%rbp` and `%r13` stay on their `disp8 = 0` rows (`8a 45 00`) because `r/m = 101` means RIP-relative at `mod = 00`, and `%rsp`/`%r12` stay on their `SIB` rows because the two-byte shape carries no `SIB` byte (`ADR-0058`, `X86-P35`, `EXP-0060`). `0.37.0` takes the axis to the 32-bit base rows: `movl 8(%rax), %eax` is `8b 40 08` (`mod = 01`, one displacement byte) and `movl 128(%rax), %eax` is `8b 80 80 00 00 00` (`mod = 10`, four), so the range end is a form boundary and `128` on a `disp8` row is `E-RANGE-001` (`ADR-0064`, `N03r`, `EXP-0066`). `0.38.0` completes that axis: `movl 200(%rax), %eax` is `8b 80 c8 00 00 00` (`mod = 10`, four displacement bytes) and the signed 32-bit span is the range (`8b 80 ff ff ff 7f`, `8b 80 00 00 00 80`), so `128` belongs to the `disp32` row and a `disp8` operand on it is `E-OPERAND-001` (`ADR-0065`, `N03s`, `EXP-0067`). `0.39.0` carries the byte onto the `SIB` bases: `movl 8(%rsp), %eax` is `8b 44 24 08` and `movl 128(%rsp), %eax` is `8b 84 24 80 00 00 00`, so the same range end separates two forms there too (`ADR-0066`, `N03t`, `EXP-0068`). `0.40.0` completes the axis on the `SIB` bases: `movl 200(%rsp), %eax` is `8b 84 24 c8 00 00 00`, and `2147483648` leaves the row for a different form (`ADR-0067`, `N03u`, `EXP-0069`). `0.43.0` puts the `disp8` shape behind the 16-bit `REX.R` register window and shows how `mod = 01` changes the base rule: `movw 8(%rax), %r8w` is `66 44 8b 40 08` (five bytes, displacement at `[32,8]`) and `movw 8(%rsp), %r8w` is `66 44 8b 44 24 08` (six, displacement at `[40,8]`); because `r/m = 101` is a base with a displacement, `%rbp`/`%r13` are legal there (`66 44 8b 45 08`), while `128` still belongs to a different `disp32` row (`E-RANGE-001`, `N03v`) (`ADR-0070`, `EXP-0072`). `0.44.0` puts the `disp32` shape behind the same register window: `movw 200(%rax), %r8w` is `66 44 8b 80 c8 00 00 00` (eight bytes, displacement at `[32,32]`) and the `SIB` rows are `66 44 8b 84 24 c8 00 00 00` (nine, `[40,32]`); `2147483648` is still `E-RANGE-001`, never a silent wrap (`N03w`) (`ADR-0071`, `EXP-0073`). `0.45.0` puts the `SIB` shape on the same width: `movw 8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08` (six bytes, the `SIB` byte before the displacement at `[40,8]`) and `movw 200(%rax,%rcx,1), %r8w` is `66 44 8b 84 08 c8 00 00 00` (nine, `[40,32]`), so the `SIB` byte inserts itself between `ModRM` and the displacement (`ADR-0072`, `EXP-0074`). `0.46.0` takes the `REX` byte out of that shape: `movw 8(%rax,%rcx,1), %ax` is `66 8b 44 08 08` (five bytes, `SIB` at byte 3 and the displacement at `[32,8]`) and `movw 200(%rax,%rcx,1), %ax` is `66 8b 84 08 c8 00 00 00` (eight, `[32,32]`), so every field moves one byte earlier with the missing prefix (`ADR-0073`, `EXP-0075`). `0.47.0` adds the `REX` byte back but only for the base or the index: `movw 8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08` (six bytes, `REX.B`, `SIB = 08`, displacement at `[40,8]`) and `movw 200(%r8,%rcx,1), %ax` is `66 41 8b 84 08 c8 00 00 00` (nine, `[40,32]`), so the prefix byte again inserts itself between the opcode and the displacement (`ADR-0074`, `EXP-0076`). `0.48.0` keeps that `REX` byte for the row where both memory operands are extended, so the displacement stays at `[40,8]`/`[40,32]`: `movw 8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08` and `movw 200(%r8,%r9,1), %ax` is `66 43 8b 84 08 c8 00 00 00` (`ADR-0075`, `EXP-0077`). `0.49.0` drops the prefix from the indexed shape entirely for the 32-bit family: `movl 8(%rax,%rcx,1), %eax` is `8b 44 08 08` (four) and `movl 200(%rax,%rcx,1), %eax` is `8b 84 08 c8 00 00 00` (seven), with `ModRM` at byte 1 and the displacement at `[24,8]`/`[24,32]` (`ADR-0076`, `EXP-0078`). `0.50.0` puts a `REX` byte in front of those rows, so `ModRM` moves to byte 2 and the displacement to `[32,8]`/`[32,32]`: `movl 8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08` (five) and `movl 200(%rax,%rcx,1), %r8d` is `44 8b 84 08 c8 00 00 00` (eight) (`ADR-0077`, `EXP-0079`). `0.51.0` extends both memory operands at once on the same rows, and the displacement stays at `[32,8]`/`[32,32]`: `movl 8(%r8,%r9,1), %eax` is `43 8b 44 08 08` (five) and `movl 200(%r8,%r9,1), %eax` is `43 8b 84 08 c8 00 00 00` (eight) (`ADR-0078`, `EXP-0080`). `0.52.0` keeps the same offsets with all three extension bits: `movl 8(%r8,%r9,1), %r8d` is `47 8b 44 08 08` (five) and `movl 200(%r8,%r9,1), %r8d` is `47 8b 84 08 c8 00 00 00` (eight) (`ADR-0079`, `EXP-0081`). `0.53.0` adds the `0x67` rows at the same offsets: `movl 8(%eax,%ecx,1), %eax` is `67 8b 44 08 08` (five) and `movl 200(%eax,%ecx,1), %eax` is `67 8b 84 08 c8 00 00 00` (eight) (`ADR-0080`, `EXP-0082`). `0.54.0` puts one `REX` byte after `0x67`, so the `disp8`/`disp32` fields move to `[40,8]`/`[40,32]`: `movl 8(%eax,%ecx,1), %r8d` is `67 44 8b 44 08 08` (six) and `movl 200(%eax,%ecx,1), %r8d` is `67 44 8b 84 08 c8 00 00 00` (nine) (`ADR-0081`, `EXP-0083`). `0.55.0` keeps those offsets with two fixed bits: `movl 8(%r8d,%r9d,1), %eax` is `67 43 8b 44 08 08` (six) and `movl 200(%r8d,%r9d,1), %r8d` is `67 47 8b 84 08 c8 00 00 00` (nine) (`ADR-0082`, `EXP-0084`). `0.56.0` keeps those offsets at 64-bit value width: `movq 8(%eax,%ecx,1), %rax` is `67 48 8b 44 08 08` (six) and `movq 200(%eax,%ecx,1), %rax` is `67 48 8b 84 08 c8 00 00 00` (nine) (`ADR-0083`, `EXP-0085`). `0.57.0` keeps those offsets with the `0x67 66` pair: `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08` (six) and `movw 200(%eax,%ecx,1), %ax` is `67 66 8b 84 08 c8 00 00 00` (nine) (`ADR-0084`, `EXP-0086`). `0.58.0` moves those offsets one byte when a `REX` byte is present: `movw 8(%eax,%ecx,1), %r8w` is `67 66 44 8b 44 08 08` (seven) and `movw 200(%eax,%ecx,1), %r8w` is `67 66 44 8b 84 08 c8 00 00 00` (ten, `disp32` at `[48,32]`) (`ADR-0085`, `EXP-0087`). | frozen |
| EC-03 | x86-64 | Relative branch rel8 (`EB`) vs rel32 (`E9`) | 2 vs 5 bytes | `form variant` (`rel8` / `rel32`) | llvm-mc 23.1.2: `jmp .+0x81` → `eb 7f` (2 B) but `jmp .+0x82` → `e9 7d 00 00 00` (5 B). One byte of target distance changes the instruction length; that is relaxation, not encoding (INV-04). | frozen |
| EC-04 | x86-64 | Accumulator form (`05 id`, `B8+rd`) vs ModRM form (`81 /0 id`, `C7 /0 id`) | Different opcode byte; the accumulator form is one byte shorter because it has no ModRM | `form variant` (`rax-imm32` / `rm64-imm32`) | `add rax, 300` → `48 05 2c 01 00 00` (6 B) or `48 81 c0 2c 01 00 00` (7 B); `mov eax, 300` → `b8 2c 01 00 00` (5 B) or `c7 c0 2c 01 00 00` (6 B). Both tools pick the accumulator and neither exposes the other. | frozen |
| EC-05 | x86-64 | `moffs` absolute form (`A0`–`A3`) vs `ModRM` with `disp32` (`SIB = 25`) | Different opcode and length; ten vs eight bytes for the same source instruction | `form variant` (`moffs` / `mem-abs32` as `form_id` components) | `llvm-mc` 23.1.2: `movabsq 0x1234, %rax` is `48 a1 34 12 00 00 00 00 00 00` (10 B) while `movq 0x1234, %rax` is `48 8b 04 25 34 12 00 00` (8 B) — the same load at two lengths, so a row that carried both would hand the choice to the materializer (`INV-02`). `llvm-mc` makes that choice by itself for `0x80000000`, assembling `movq 0x80000000, %rax` to the ten-byte `48 a1 00 00 00 00 80 00 00 00`, which a plan may not do: the value is `E-RANGE-001` on the `abs32` row (`N03m`) and the `moffs` row is absent (`N01bf`). `0.26.0` freezes the row set with only the `SIB` shape (`ADR-0053`, `EXP-0055`) | frozen |
| EC-06 | x86-64 | REX presence and W/R/X/B bits; high-byte registers (`AH`) are illegal with any REX | Legality and one prefix byte | `operand type` (register class → REX bits) + definition rule | A plan naming `AH` with a 64-bit operand cannot be encoded; the encoder must reject, not silently switch registers. The high-byte half now ships in `0.4.0`: `x86.gpr8h` is its own kind, a REX template cannot carry it, and a REX-less `x86.gpr8` slot excludes 4–7 (`E-DEF-001`) (`ADR-0029`, `EXP-0031`). The `W`/`R`/`B` half ships in `0.6.0`: the six register-direct 64-bit rows take a 4-bit register slot whose top bit is placed in `REX.R`/`REX.B`, so `mov %r8, %r9` is `4d 89 c1` while `mov %rax, %rbx` stays `48 89 c3` (`ADR-0033`, `EXP-0035`). `REX.X` waited for an index operand until `0.8.0`, and the 8/16-bit and high-byte rows keep their narrower fields. The SSE `xmm` register reaches `REX.R`/`REX.B` in `0.11.0`: three legacy `40 0F 28 /r` windows carry the fourth bit, while EVEX and VEX use the inverted `R̄`/`B̄` (the EVEX register-direct source is `ModRM.rm`, so it uses `B̄` at bit 13) (`ADR-0038`, `EXP-0040`). `0.13.0` gives the EVEX `xmm` slot a fifth bit: bit 4 is the inverted `R̄'` for `ModRM.reg` and, in register form, the inverted `X̄` for `ModRM.rm`, so `vmovaps %xmm31, %xmm30` is `62 01 7c 08 28 f7` while `%xmm15, %xmm30` is `62 41 7c 08 28 f7`; legacy and VEX have no second extension bit, so their slots stay at three and four bits (`ADR-0040`, `EXP-0042`). The SSE base reaches `REX.B` in `0.10.0` through a `-base-ext` window, because the legacy row must grow a `REX` byte and the two-byte VEX a third byte (`ADR-0037`, `EXP-0039`). The `B` bit also reaches a memory base in `0.7.0`: the base+disp rows take a 4-bit base, `REX.B` is its top bit, and `%r12` gets its own fixed-base rows because it shares `%rsp`'s low three bits (`ADR-0034`, `EXP-0036`). `REX.X` reaches a `SIB` index in `0.8.0` (`movq 8(%r8,%r9,2), %r10` is `4f 8b 54 48 08`), so all four bits have a row (`ADR-0035`, `EXP-0037`). `0.30.0` puts `REX.R` and `REX.B` in one byte at byte width, where the register and the base both need an extension: `movb 8(%rax), %r8b` is `44 8a 40 08` (four bytes, `REX.R = 1`) and `movb 8(%r8), %r8b` is `45 8a 40 08` (the same length, `REX.B = 1` as well) — one `REX` byte, two slot bits at `[2,1]` and `[0,1]`, and no row that reads the operand to choose which bit to set (`ADR-0057`, `EXP-0059`). `0.32.0` fixes `REX.B` in the template for the `%r12` `SIB` rows, one row per base, so no operand decides it (`ADR-0059`, `EXP-0061`). `0.42.0` extends `REX.R` to the 16-bit `mod = 00` `mov` rows, where the `0x66` prefix puts the `REX` byte at byte 1: `movw (%rax), %r8w` is `66 44 8b 00`, with `R` at `[10,1]` and the register at `[27,3]`, and `movw (%r8), %r8w` is `66 45 8b 00`, one byte carrying `R` and `B`; the low register window is excluded from the `-ext` rows so the fixed bit can never be cleared (`ADR-0069`, `EXP-0071`). `0.43.0` keeps that register window on the `disp8` rows, where the `REX` byte stays at byte 1: `movw 8(%rax), %r8w` is `66 44 8b 40 08` with `R` at `[10,1]` and the register at `[27,3]`, and `movw 8(%r8), %r8w` is `66 45 8b 40 08`, one byte carrying `R` and `B`; the low window is again excluded from the `-ext` rows (`ADR-0070`, `EXP-0072`). `0.44.0` keeps the window on the `disp32` rows, where the displacement moves to `[32,32]` (`[40,32]` behind `SIB`) and `%rbp`/`%r13` are legal bases at `mod = 10` (`66 44 8b 85 c8 00 00 00`) (`ADR-0071`, `EXP-0073`). `0.45.0` reaches `REX.X` on the 16-bit rows, because the `SIB` index's fourth bit is the same byte's bit 1: `movw 8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08`, where `REX = 47` carries `R`, `X` and `B` at `[10,1]`, `[9,1]` and `[8,1]` and the row stays six bytes (`ADR-0072`, `EXP-0074`). `0.50.0` gives the 32-bit indexed rows one extension bit per row: `movl 8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08` (`REX.R` only), `movl 8(%r8,%rcx,1), %eax` is `41 8b 44 08 08` (`REX.B` only), and `movl 8(%rax,%r9,1), %eax` is `42 8b 44 08 08` (`REX.X` only) (`ADR-0077`, `EXP-0079`). `0.51.0` puts both memory extension bits in the same `REX` byte: `movl 8(%r8,%r9,1), %eax` is `43 8b 44 08 08` (`REX.BX`, `REX = 43`), and the register still has no bit in this row (`movl 8(%r8,%r9,1), %r8d` is `47 8b 44 08 08`, the deferred `REX.RBX` row) (`ADR-0078`, `EXP-0080`). `0.52.0` sets `R`, `B` and `X` in the same byte: `movl 8(%r8,%r9,1), %r8d` is `47 8b 44 08 08` (`REX = 47`), and all three register slots become four bits (`ADR-0079`, `EXP-0081`). `0.54.0` puts one `REX` byte after the `0x67` byte, so the byte order is `0x67`, `REX`, opcode: `REX.R` is `67 44 8b 44 08 08`, `REX.B` is `67 41 8b 44 08 08` and `REX.X` is `67 42 8b 44 08 08` (`ADR-0081`, `EXP-0083`). `0.55.0` fixes two bits of the same byte at once: `67 43` is `REX.BX`, `67 45` is `REX.RB`, `67 46` is `REX.RX` and `67 47` is `REX.RBX`, so `movl 8(%r8d,%r9d,1), %r8d` is `67 47 8b 44 08 08` (`ADR-0082`, `EXP-0084`). `0.56.0` fixes `REX.W` in the template while `R`/`X`/`B` stay operand fields: `67 48` is the low-register row, `67 4c` sets `R`, `67 49` sets `B`, `67 4a` sets `X` and `67 4f` sets all three (`ADR-0083`, `EXP-0085`). `0.57.0` puts no `REX` byte on the 16-bit pair, so `0x66` sits at byte 1 and every register slot is three bits: `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08`; the 16-bit `REX` windows (a `REX` byte at byte 2, then opcode and `SIB` one byte later) were deferred in `0.57.0` (`ADR-0084`, `EXP-0086`). `0.58.0` puts that `REX` byte at byte 2: `R` at `[18,1]`, `B` at `[16,1]` and `X` at `[17,1]`, so `movw 8(%eax,%ecx,1), %r8w` is `67 66 44 8b 44 08 08`, `movw 8(%r8d,%ecx,1), %ax` is `67 66 41 8b 44 08 08` and `movw 8(%eax,%r9d,1), %ax` is `67 66 42 8b 44 08 08`; the two-bit windows stay deferred (`ADR-0085`, `EXP-0087`). | frozen |
| EC-07 | x86-64 | Operand-size prefix `0x66` vs a distinct 16/32/64-bit form | One prefix byte, different semantics | `form variant` (`r16-*`) | `add ax, bx` requires `66`; omitting it changes the operand width. `0.57.0` puts `0x66` after `0x67` and before the opcode on the indexed `addr32` `mov`: `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08` while the 32-bit sibling is `67 8b 44 08 08`, so the extra byte is the form, not an operand value (`ADR-0084`, `EXP-0086`). `0x66` stays at byte 1 when a `REX` byte follows it: `movw 8(%eax,%ecx,1), %r8w` is `67 66 44 8b 44 08 08`, so the prefix order is `0x67`, `0x66`, `REX` (`ADR-0085`, `EXP-0087`). | frozen |
| EC-08 | x86-64 | Address-size prefix `0x67` in 64-bit mode: the prefix selects 32-bit address registers (`%eax`–`%edi`) for the base and the index while the value operand keeps its own width | One prefix byte, and a base/index field that names a different register set | `form variant` (`-addr32-` rows; `67` is template byte 0, before any `REX`) | `llvm-mc` 23.1.2: `movl 8(%eax,%ecx,1), %eax` is `67 8b 44 08 08` (five bytes), while `movl 8(%rax,%rcx,1), %eax` is `8b 44 08 08` (four); the same `SIB = 08` names `%ecx`/`%eax` in the first and `%rcx`/`%rax` in the second. A single row accepting both would pick the prefix and the length from an operand kind (`INV-02`, `INV-04`), and `%rsp` remains rejected as an index while `%ebp` is legal (`67 8b 44 28 08`). `0.53.0` adds the four `REX`-less rows (`ADR-0080`, `EXP-0082`) and `0.54.0` adds the three single-`REX` windows (`67 44`, `67 41`, `67 42`; `ADR-0081`, `EXP-0083`), fixing the prefix order at `0x67` then `REX`. `0.55.0` adds the four two-bit windows (`67 43`, `67 45`, `67 46`, `67 47`; `ADR-0082`, `EXP-0084`), so every fixed-bit combination behind `0x67` that keeps the 32-bit width is a row. `0.56.0` adds the `REX.W` sibling as one wide row per shape (`67 48`, widening to `67 49`/`67 4a`/`67 4c`/`67 4f` from the operands; `ADR-0083`, `EXP-0085`), because `REX.W` already forces the prefix byte. `0.57.0` adds the 16-bit sibling as one bare pair (`67 66 8b`/`67 66 89`): `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08` and a `%r8w` value or `%r8d` address needs a `REX` byte at byte 2, a window `0.58.0` adds (`ADR-0084`, `EXP-0086`). `0.58.0` adds the three single-`REX` windows (`REX.R` value `%r8w`, `REX.B` base `%r8d`, `REX.X` index `%r9d`) while the address registers stay 32-bit: `67 66 41 8b 44 08 08` names `%r8d` as the base, and the two-bit windows stay deferred (`ADR-0085`, `EXP-0087`). | frozen |
| EC-09 | x86-64 | Legacy SSE vs VEX vs EVEX for the same operation, and the vector width within a family | Prefix family, `L`/`L'L` width, 3–6 byte encodings, register reach | `form variant` (`/legacy` / `/vex` / `/evex` with a width component) | `llvm-mc` 23.1.2: `movaps %xmm1,%xmm0` is `0f 28 c1`, `vmovaps %xmm3,%xmm2` is `c5 f8 28 d3`, and `62 f1 7c 08 28 e5` decodes as `vmovaps %xmm5,%xmm4`. Same operation, same operands, three lengths; VEX and EVEX are both legal at `xmm` width, and `llvm-mc` always picks VEX for the mnemonic, so an unfamilied row would let two implementers emit different bytes (`INV-02`). A plan that names a family the table lacks is `E-FORM-001` (`N01aa`, `N01ab`), a `zmm` operand on the `xmm` row is `E-OPERAND-001` (`N02l`), and the extension set the EVEX row needs is checked by `E-TARGET-001` (`N06`) (`ADR-0030`, `EXP-0032`). The memory rows repeat the family split at one more operand shape: the same load/store pair exists in all three families, and only the EVEX row has the compressed `disp8` (`EC-38`, `EC-39`, `ADR-0036`, `EXP-0038`). The register reach repeats the split: `movaps %xmm1,%xmm8` is `44 0f 28 c1` while `movaps %xmm1,%xmm0` is `0f 28 c1`, and `vmovaps %xmm8,%xmm0` is `c5 78 29 c0` although the also-legal `c4 c1 78 28 c0` is five bytes, so even within VEX the reach selects a different opcode and length (`ADR-0038`, `EXP-0040`). Width is the same prefix-choice decision with one more dimension: `vmovaps %ymm1,%ymm0` is `c5 fc 28 c1` and `vmovaps %xmm1,%xmm0` is `c5 f8 28 c1`, differing only in `L`, while `62 f1 7c 28 28 c1` (256-bit) and `62 f1 7c 48 28 c1` (512-bit) differ only in `L'L`; the mnemonic and every operand agree, so a row without a width would let two implementers emit different bytes (`INV-02`). The width is a `form_id` component and the template pins the field (`ADR-0041`, `EXP-0043`); a plan that mixes widths is `E-OPERAND-001` (`N02n`) and one that names a width the family cannot express is `E-FORM-001` (`N01aj`). | frozen |
| EC-10 | x86-64 | `LOCK` / `REP` / segment prefix presence | One or more prefix bytes | `operand modifier` (`lock` / `rep` / `segment`) | `lock add [rax], ebx` vs plain `add` differ only by `F0`, with different semantics. | draft |
| EC-11 | AArch64 | 32-bit (`w`) vs 64-bit (`x`) variant | Different `sf` bit, different semantics | `form variant` (`w32-…` / `x64-…`) + `operand type` guard (`aarch64.gpr32`/`w32` vs `aarch64.gpr64`/`x64`) | `add w0,w1,w2` is `0x0b020020` and `add x0,x1,x2` is `0x8b020020`: bit 31 alone, and the operand values are identical, so no operand field could carry the choice. The width is which MRS node the row came from (`ADD_32_addsub_shift` vs `ADD_64_addsub_shift`, `sf` at 31+1), and the register class is a second, independent guard: the nodes spell `<Wd>`/`<Wn>`/`<Wm>` and `llvm-mc` rejects `add w0, w1, x2`; an `x64` operand on a `w` row is `E-OPERAND-001` (`N02c`, `EXP-0021` §2). | frozen |
| EC-12 | AArch64 | `add/sub` immediate: imm12 vs imm12 shifted by 12 | Different `sh` bit and range | `form variant` (`imm12` / `imm12-scaled`) | `add x0,x1,#1` and `add x0,x1,#1,lsl #12` are both legal spellings of different values. The `sub` rows in `0.8.0` carry the same pair: `sub x0, x1, #4096` is encodable only as `-lsl12` (`imm12 = 1`), `llvm-mc` picks that form without a diagnostic, and naming `-lsl0` is `E-RANGE-001` (`N18d`, `EXP-0019` §2). | frozen |
| EC-13 | AArch64 | Shifted-register vs extended-register form | Different `shift`/`option` fields | `form variant` (`shifted-reg` / `extended-reg`) | `add x0,x1,x2,lsl #3` vs `add x0,x1,w2,uxtw #3` share a mnemonic but not an encoding. The flag-setting spelling repeats it: `adds x0,x1,x2,lsl #3` is `0xab020c20` while `adds x0,x1,w2,uxtw #3` is `0xab224c20`, so the same split lands on the `S = 1` nodes (`EXP-0020` §2, ADR-0018). | frozen |
| EC-14 | AArch64 | Load/store addressing: unsigned-offset vs pre-index vs post-index vs unscaled vs register-offset | Different addressing bits (bit 24, bits 11–10) and writeback semantics | `form variant` (`unsigned-offset` / `pre-index` / `post-index` / `unscaled` / `register-offset`) | llvm-mc 23.1.2: `ldr x0,[x1,#16]` is `0xf9400820` (`imm12 = 2`, unsigned-offset) while `ldur x0,[x1,#16]` is `0xf8410020` (`imm9 = 16`, unscaled). Worse, `ldr x0,[x1,#1]` emits `0xf8401020`, which `llvm-objdump` reads back as `ldur`: the mnemonic does not name the form, so the assembler silently switches instruction on the offset's value (INV-02). The store half is the same: `str x0,[x1,#8]!` is `0xf8008c20` (pre-index, `opc = 00`) and `str x0,[x1,#1]` emits `0xf8001020`, read back as `stur` (`EXP-0024` §2). The register-offset kind is the same split once more: `ldr x0,[x1,x2]` is `0xf8626820` (bit 21 = 1, bits 11–10 = `10`), a word none of the four offset spellings produces, and `lsl #0` versus `lsl #3` moves only bit 12 (`EXP-0026` §1). The 32-bit node repeats it at `size = 10`: `ldr w0,[x1,x2]` is `0xb8626820` and `lsl #2` is `0xb8627820` (`EXP-0027` §1–§2). | frozen |
| EC-15 | AArch64 | Literal load vs `adrp` + `lo12` sequence | Instruction count (INV-03 boundary) | `form variant` (one instruction vs two planned instructions) | A "load from label" request is a plan decision: one literal load or two instructions. llvm-mc 23.1.2: `ldr x0, #-4` is one 4-byte word (`0x58ffffe0`), while the same address takes `adrp` + `add :lo12:` — two planned instructions with a pair-grouped fixup. Its reach is `−1048576 … +1048572` bytes and the reference is the instruction address (`pcrel_begin`, `EXP-0025` §2). Both halves now have rows (`aarch64:ldr/x64-imm19` in `0.14.0`, `aarch64:adrp/x64-imm21` since `0.1.0`), so the choice is the plan's and neither is inferred from the distance. | frozen |
| EC-16 | AArch64 | `mov` alias family: `movz` / `movn` / `orr` immediate / register | Different opcodes | `form variant` (`movz` / `movn` / `orr-imm` / `reg`) | `mov x0,#1` can be `movz` or `orr`; both are legitimate and differ in bytes. | draft |
| EC-17 | AArch64 | `adr` (±1 MB) vs `adrp` (page) for a symbol address | Different instruction and fixup kind | `form variant` + `fixup field` (`kind`) | Choosing `adrp` when the target is in range changes both bytes and relocation semantics. | frozen |
| EC-18 | AArch64 | `b.cond` vs `cbz/cbnz` vs `tbz/tbnz` for a conditional transfer | Different forms and operand sets | `form variant` | A planner that says only "branch if zero" has not chosen a form. The `b.cond` half now ships as `aarch64:b.cond/imm19`; `cbz`/`tbnz` are absent, so naming one is `E-FORM-001`. | draft |
| EC-19 | RV64 | Compressed (`c.*`, 2 bytes) vs standard (4 bytes) | 2 vs 4 bytes | `form variant` (the `c.` mnemonic is a different form; `riscv:c.addi/rd-imm6` in `0.2.0`) | With `-mattr=+c`, `addi a0, a0, 1` assembles to `05 05`; the same immediate with `a1` stays `13 85 15 00`, and `c.addi a0, 1` is `05 05` only because it was named. An encoder that picks by register/operand shape violates INV-02. | frozen |
| EC-20 | RV64 | Compressed register class `x8–x15` (3-bit field) vs full 5-bit register | Legality | `operand type` + definition rule | `c.lw a6, 0(a0)` is rejected ("register must be a GPR from x8 to x15"); `c.lw a2, 0(a0)` is `10 41`. `c.addi a6, 5` is legal (`15 08`): its `xd` is a 5-bit field, so the rule is per form, not per mnemonic prefix. | frozen |
| EC-21 | RV64 | Absolute vs PC-relative symbol materialization: `lui`+`addi` vs `auipc`+`addi` | Instruction pair and relocation kind | `form variant` + `fixup field` (`kind`) | Choosing PC-relative changes both instructions and the fixup pair. | frozen |
| EC-22 | RV64 | B-type/J-type immediate scatter is fixed by form, but the PC base is not | Fixup value | `fixup field` (`pc_reference_rule`) | Same form, different `P`, different bytes: a contract bug. | frozen |
| EC-23 | RV64 | `jal` vs `jalr` for a call; `c.j` vs `jal` for a jump | Different instruction, range, link behavior | `form variant` | A "call" that becomes `jalr` needs a base register the plan never provided. | draft |
| EC-24 | RV64 | `fence` `fm`/`pred`/`succ` field values | Bits 31–28, 27–24, 23–20 | `operand type` (`fence_mask`) | `fence rw,rw` vs `fence iorw,iorw` differ in fields, not in mnemonic. | draft |
| EC-25 | RV64 | CSR operation immediate (`csrrwi`) vs register (`csrrw`) | Different funct3 | `form variant` | `csrrwi` cannot carry a register operand; a generic "CSR op" leaves the choice open. | draft |
| EC-26 | RV64 | Atomic `aq`/`rl` bits | Bits 26–25 | `operand modifier` (`aq` / `rl`) | `amoadd.w` vs `amoadd.w.aqrl` differ in ordering semantics and bytes. | draft |
| EC-27 | x86-64 | `89 /r` (`MOV r/m64, r64`) vs `8B /r` (`MOV r64, r/m64`) | Different opcode bytes, same length, same semantics | `form variant` (`rm-r64` / `r64-rm`) | `mov rax, rbx` is both `48 89 d8` and `48 8b c3`; both disassemble to `movq %rbx, %rax` and both are 3 bytes. `expected_size` cannot detect a wrong choice, and no operand distinguishes them; only `expected_digest` can (OD-01). The SSE pair repeats the split: `0F 28` is the load and `0F 29` the store, and the `form_id` component is the only carrier (`ADR-0036`). | frozen |
| EC-28 | x86-64 | Minimal prefix set vs a redundant prefix (`89 d8` vs `40 89 d8`; likewise a redundant `66`, segment or `REX` prefix) | One byte per redundant prefix, identical semantics | `none` — definition rule: emit the minimal prefix set | `40 89 d8` decodes as `movl %ebx, %eax`, exactly like `89 d8`. Two honest implementers could differ by one byte with no observable semantic difference, so the definition must pin minimality and no plan field may request the redundant byte. | frozen |
| EC-29 | AArch64 | `b.cond` condition: sixteen values in the 4-bit `cond` field | Bits 0–3; no length, opcode or relocation change | `operand type` (`aarch64.cond` / `cond4`) | `b.eq .+4` is `0x54000020` and `b.ne .+4` is `0x54000021`: one nibble apart, both 4 bytes, so a wrong condition is a valid word that branches on the wrong flags. Masking `cond = 16` to four bits yields `0x0`, which is `eq` (`ADR-0012`, `EXP-0014`). | frozen |
| EC-30 | AArch64 | `MOVZ` lane: `hw` selects which 16-bit lane of the 64-bit destination the `imm16` content lands in | Bits 22–21; the value the instruction builds is `imm16 << 16·hw` | `form variant` (`-lsl0` … `-lsl48`) | `llvm-mc` 23.1.2: `movz x0, #0x1234` is `0xd2824680` and `movz x0, #0x1234, lsl #16` is `0xd2a24680`. Both put the same `imm16 = 0x1234` at bits 20–5 and differ only in bits 22–21, so neither the operand value nor `expected_size` can tell them apart; two honest implementers of one `movz` row would emit different words (`ADR-0014`, `EXP-0016`). `movk` and `movn` reuse the same lane field with `opc` fixed by the node: `movk x0, #0x1234` is `0xf2824680` and `movn x0, #0x1234` is `0x92824680`, both with `imm16 = 0x1234` (`ADR-0026`, `EXP-0028` §2). | frozen |
| EC-31 | AArch64 | Shift on a register operand: `lsl` / `lsr` / `asr` with an amount `0…63` (`shift` at 23–22, `imm6` at 15–10) | Bits 23–22 and 15–10; the operand value is combined with a shifted register | `form variant` for the keyword (`-imm6-lsl` … `-imm6-asr`), `operand type` for the amount (`aarch64.imm` / `imm6`) | `llvm-mc` 23.1.2: `add x0, x1, x2, lsl #3` is `0x8b020c20` and `add x0, x1, x2, lsr #7` is `0x8b421c20`; every register field is identical, and a plan that stated only the registers could not distinguish the two words. The amount is a second reading of the same instruction: `lsl #0` and `lsl #63` differ only in `imm6`. The keyword has no numeric spelling (`ror` is rejected, `shift = 11` is unallocated), and a `modifiers` entry cannot carry it — the `-lsl0` row with `{"name": "lsl", "value": 3}` is `E-OPERAND-003` (`N19`), because the materializer would otherwise emit the unshifted word and report success (`ADR-0015`, `EXP-0017`). | frozen |
| EC-32 | AArch64 | Extend keyword and amount on an extended-register source: `uxtb`/`uxth`/`uxtw`/`sxtb`/`sxth`/`sxtw` (a `w` source) or `uxtx`/`sxtx` (an `x` source), each with `imm3` in `0…4` (`option` at 15–13, `imm3` at 12–10, bit 21 = 1) | Bits 15–13 and 12–10, plus the register class the keyword implies | `form variant` for the keyword (`-imm3-uxtb` … `-imm3-sxtx`), `operand type` for the amount (`aarch64.imm` / `imm3`) | `llvm-mc` 23.1.2: `add x0, x1, w2, uxtb #0` is `0x8b220020` and `add x0, x1, w2, uxth #4` is `0x8b223020`; all three register fields are identical and only bits 15–13 and 12–10 differ, so a plan stating only the registers could not tell the rows apart. The register class is the second counterexample: `option = 3` (`uxtx`) consumes an `x` register, and the assembler rejects `uxtw` on an `x` source and `uxtx` on a `w` one, so a single row with a free `option` and a free register class would emit a legal word for an illegal plan. The amount is not a signed 3-bit range: values `5`, `6`, `7` fit the field but are unallocated, which is why `imm3` is a `0…4` domain plus a closed `excluded` list rather than a wider range (`ADR-0016`, `EXP-0018`). | frozen |
| EC-33 | AArch64 | `cmp`/`cmn` alias vs the `subs`/`adds` row with `Rd = 31` | One fixed `Rd` field and a shorter operand list | `form variant` (`cmp/…` / `cmn/…` as two-operand rows) | `cmp x1, x2` is `0xeb02003f`, the same word as `subs xzr, x1, x2`, while `subs x0, x1, x2` is `0xeb020020`. A single `subs` row with a free `Rd` would emit `cmp`'s word or a `subs` word depending on an operand value, and would make the plan spell a destination register the mnemonic cannot name; the alias is its own two-operand form with `Rd` pinned (`ADR-0021`, `EXP-0023` §2). | frozen |
| EC-34 | x86-64 | RIP-relative vs base+disp addressing: `mod = 00`, `r/m = 101` is RIP + `disp32`; the same `r/m` under `mod = 01`/`10` is a base register | 7 bytes with `disp32` and no base vs 4/7 bytes with a base; the base's identity selects the shape | `form variant` (`riprel32` / `mem-disp8` / `mem-disp32`) | `llvm-mc` 23.1.2: `movq 16(%rip), %rax` is `48 8b 05 10 00 00 00` and contains no base register, while `movq 0(%rbp), %rax` is `48 8b 45 00` because `mod = 00`, `r/m = 101` would mean RIP. A single `mov/r64-mem` over `base`/`disp` would have to read the base's value to choose `mod`, and RIP has no GPR number for that operand; the form is the only carrier (`ADR-0027`, `EXP-0029`). | frozen |
| EC-35 | x86-64 | SIB byte presence: `%rsp` as a base forces `r/m = 100` and a SIB byte whose `base` is also `100`, while any other base of the same width uses `r/m = base` and no SIB | One extra byte and one different ModRM `r/m`; the base's identity selects the shape | `form variant` (`-base-disp8`/`-base-disp32` vs `-rsp-disp8`/`-rsp-disp32`, base fixed in the latter) | `llvm-mc` 23.1.2: `movq 8(%rsp), %rsi` is `48 8b 74 24 08` (ModRM `74`, SIB `24`) and `movq 8(%rbp), %rcx` is `48 8b 4d 08` (ModRM `4d`, no SIB). The same register number 4 is legal in both; if one row accepted it and inserted the SIB byte from the operand value, the instruction length would change with an operand (`INV-04`). The `%rsp` rows therefore fix the base and exclude 4 from the general rows (`E-RANGE-004`, `N16f`) (`ADR-0028`, `EXP-0030`). `%r12` is the same case one register number higher: its low three bits are also `100`, so `0.7.0` gives it four fixed-base rows whose template carries `REX.B` (`49` instead of `48`), and the general rows exclude both `4` and `12` (`ADR-0034`, `N16h`, `EXP-0036`). `0.8.0` turns the SIB byte into operand-owned fields: `r/m = 100` announces it, `SIB.base`/`SIB.index`/`SIB.scale` are one operand each, and only the index excludes a value (`4`, the "no index" encoding), because a SIB base of `100` is `%rsp`/`%r12` rather than "no base" (`ADR-0035`, `N16i`, `EXP-0037`). `0.9.0` applies the same exclusion to the SSE memory rows in all three families (`EC-38`, `N16j`, `ADR-0036`). `0.19.0` closes the same gap inside the 8/16-bit `mov` families: each of the four families (word, REX-less low byte, high byte, `40`-prefixed byte) gains a `%rsp` row and, except the high-byte one, a `%r12` row, so `66 89 44 24 08` and `66 41 89 44 24 08` are forms rather than an inserted `SIB`, and `ModRM` plus the displacement move one byte later with it (`[19,3]`/`[32,8]` → `[27,3]`/`[40,8]` on the word pair), while `movb %ah, 8(%r12)` stays unencodable because the `REX.B` byte renames the register (`ADR-0046`, `N16y`, `N01aq`, `EXP-0048`). `0.20.0` extends the same fix to the SSE memory rows: `movaps 8(%rsp), %xmm0` is `0f 28 44 24 08` and `movaps 8(%r12), %xmm0` is `41 0f 28 44 24 08`, while `vmovaps 8(%r12), %xmm0` spends `c4 c1 78` because the two-byte VEX cannot carry `B = 1` at all, so sixteen fixed-base rows carry the base and its prefix (`ADR-0047`, `X86-P24`, `EXP-0049`). `0.21.0` adds the EVEX half: `{evex} vmovaps 16(%rsp), %xmm0` is `62 f1 7c 08 28 44 24 01` and `%r12` differs only in `P0` (`62 d1 7c 08 28 44 24 01`), because `B̄` is already in the four-byte prefix, so both bases spend the same one `SIB` byte and no prefix byte (`ADR-0048`, `X86-P25`, `EXP-0050`). `0.22.0` adds the `mod = 00` half, where the same `SIB` byte is the only place the base appears: `{evex} vmovaps (%rsp), %xmm0` is `62 f1 7c 08 28 04 24` and `(%r12)` is `62 d1 7c 08 28 04 24`, seven bytes with no displacement, and `%rbp`/`%r13` cannot use the shape at all because `mod = 00` with `r/m = 101` is RIP-relative (`ADR-0049`, `X86-P26`, `EXP-0051`). `0.23.0` makes the byte operand-owned: `r/m = 100` announces it, base `[48,3]`/`B̄`, index `[51,3]`/`X̄` and scale `[54,2]` are one operand each, and on the `mod = 00` rows `SIB.base = 101` means "no base, `disp32`", so `%rbp`/`%r13` are excluded there and keep the `disp8*N = 0` row (`E-RANGE-004`, `N16ab`) while `%rsp`/`%r12` become ordinary bases (`ADR-0050`, `EXP-0052`). `0.24.0` takes the third meaning of the byte: with `SIB.base = 101` at `mod = 00` the base slot disappears and the displacement returns, so `vmovaps (,%rax,4), %xmm1` is `62 f1 7c 08 28 0c 85 00 00 00 00` — `SIB` bits 48–50 are the constant `101`, the `disp32` slot is mandatory, and the row has no `base` role at all, so supplying one is `E-OPERAND-002` (`N02ad`) (`ADR-0051`, `EXP-0053`). `0.25.0` spends both register fields at once: `SIB = 25` (`index = 100`, `base = 101`) is the absolute row, whose only address operand is the `disp32`, so `vmovaps 0x1234, %xmm0` is `62 f1 7c 08 28 04 25 34 12 00 00` and a plan that supplies a register is `E-OPERAND-002` (`N02af`) (`ADR-0052`, `EXP-0054`). `0.26.0` repeats the shape one opcode family over: the 64-bit `mov` rows write `SIB = 25` in the template, so `movq 0x1234, %rax` is `48 8b 04 25 34 12 00 00` and supplying a base is still `E-OPERAND-002` (`N02ah`) (`ADR-0053`, `EXP-0055`). `0.32.0` gives the byte `mov` family the same `mod = 00` pair: `SIB = 24` sits in the template, `REX.B` picks `%rsp` or `%r12`, and the base is a row name rather than an operand, so `movb (%rsp), %al` is `8a 04 24` and `movb (%r12), %al` is `41 8a 04 24` (`ADR-0059`, `N02ay`, `EXP-0061`). `0.33.0` carries the same split into the 64-bit family's `mod = 00` shape: its two plain-base rows exclude `4`, `5`, `12` and `13` (`ADR-0060`, `N16ao`, `N16aq`), and `0.34.0` gives the two `SIB` bases their own rows, so `movq (%rsp), %rax` is `48 8b 04 24` and `movq (%r12), %rax` is `49 8b 04 24` (`ADR-0061`, `N02bb`, `EXP-0063`). `0.36.0` repeats the pair at 32-bit width: `movl (%rsp), %eax` is `8b 04 24` and `movl (%r12), %eax` is `41 8b 04 24`, the same `SIB = 24` with `REX.B` as the only difference, so each base, direction and register window is its own fixed-base row (`ADR-0063`, `N02be`, `EXP-0065`). `0.39.0` gives those rows a `disp8` variant: `movl 8(%rsp), %eax` is `8b 44 24 08` and `movl 8(%r12), %eax` is `41 8b 44 24 08`, the same `SIB = 24` plus one displacement byte, so the base stays a form property and the register window still splits (`ADR-0066`, `N16bf`, `EXP-0068`). `0.40.0` adds the `disp32` variant: `movl 200(%rsp), %eax` is `8b 84 24 c8 00 00 00` and `movl 200(%r12), %eax` is `41 8b 84 24 c8 00 00 00`, again the same `SIB = 24` with `REX.B` as the only difference (`ADR-0067`, `N16bg`, `EXP-0069`). `0.41.0` brings the same two bases to the 16-bit family at `mod = 00`: `movw (%rsp), %ax` is `66 8b 04 24` and `movw (%r12), %ax` is `66 41 8b 04 24`, again the same `SIB = 24` with `REX.B` as the only difference, so the base stays a form property there too (`ADR-0068`, `N16bh`, `N16bi`, `EXP-0070`). | frozen |
| EC-36 | x86-64 | Prefix byte rules: `0x66` selects the 16-bit operand size, and a REX prefix re-labels byte registers 4–7 from `ah`/`ch`/`dh`/`bh` to `spl`/`bpl`/`sil`/`dil` | One prefix byte; for 4–7 the same bytes name a different register set | `form variant` (`-r16-`/`-rm16-` carry `66`; `-rm8h-` vs `-rm8-` vs `-rm8-r8-rex-`) and `operand type` (`x86.gpr16`, `x86.gpr8h`, `x86.gpr8`) | `llvm-mc` 23.1.2: `movw %bx, %ax` is `66 89 d8` while `movl %ebx, %eax` is `89 d8` — the same opcode and ModRM, one prefix byte apart, and no operand value distinguishes them. `movb %ah, %ch` is `88 e5` and `movb %spl, %bpl` is `40 88 e5`: the same two bytes plus a REX, different registers. A single `mov/r8-r8` row over numbers 0–7 would have to read the number to choose the prefix and the register set, and would emit `ah` for a plan that said `spl` (`INV-02`, `INV-05`); `movb %ah, %spl` is rejected by `llvm-mc` with `can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`. The rows are disjoint by `excluded`: `0–3` in the REX-less low-byte row, `4–7` in the high-byte row, `4–7` in the REX row (`E-RANGE-004`, `N16g`), and a REX row carrying `x86.gpr8h` is `E-DEF-001` (`ADR-0029`, `EXP-0031`). `0.29.0` carries the same relabelling into the absolute-address rows: `8a 24 25 …` is `%ah` while `40 8a 24 25 …` is `%spl` — the same opcode, `ModRM` and `SIB`, one `REX` byte apart — so the byte width has four windows and four rows rather than two, and naming `%ah` on the `REX = 40` row is a different `form_id` on both `kind` and `target_type` (`E-OPERAND-001`, `N02as`; `ADR-0056`, `EXP-0058`). `0.57.0` orders the two legacy prefixes `0x67` then `0x66` before the opcode: `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08`, and omitting either byte changes the address width or the value width (`ADR-0084`, `EXP-0086`). `0.58.0` keeps the pair in front of `REX`: `movw 8(%eax,%ecx,1), %r8w` is `67 66 44 8b 44 08 08`, so the order is `0x67`, `0x66`, `REX`, opcode (`ADR-0085`, `EXP-0087`). | frozen |
| EC-37 | x86-64 | SIB index and scale: an index register and a scale factor need a `SIB` byte (`r/m = 100`), and `SIB.index = 100` with `REX.X = 0` means "no index" | One byte with three operand-owned fields, and the index's fourth bit in `REX.X` | `form variant` (`-base-index-disp8`/`-disp32`) + `operand` (`sib_index`, plus the scale as two bits of field content) + `excluded` | `llvm-mc` 23.1.2: `movq 8(%rax,%rcx,1), %rdx` is `48 8b 54 08 08` and `movq 8(%rax,%rcx,8), %rdx` is `48 8b 54 c8 08` — same `ModRM`, different `SIB` top bits, so the scale is content and not a form; `movq 8(%rax,%r12,4), %rdx` is `4a 8b 54 a0 08` (`REX.X = 1` with `SIB.index = 100`), while `48 8b 54 20 08` with `REX.X = 0` decodes as `movq 8(%rax,%riz), %rdx`, so index `4` must be rejected (`E-RANGE-004`, `N16i`) and `%rsp` is not an index at all (`llvm-mc`: `invalid base+index expression`). Carrying the multiplier instead of the field content would need the materializer to compute `1 << content` (an implicit encoding step, `INV-02`) and cannot express ×16: the field content `8` is `E-RANGE-001` (`N03c`). The shape is a form because `r/m = 100` changes the instruction length and the `SIB` byte's presence (`ADR-0035`, `EXP-0037`). `0.23.0` repeats it inside the EVEX `vmovaps` family: `ModRM` `04`/`44`/`84` announces the same `SIB` byte one byte later (bits 48–55), the index's fourth bit is the inverted `X̄` at `[14,1]` instead of `REX.X`, and the two-bit scale at `[54,2]` is unchanged; `{evex} vmovaps (%rsp,%rax,1), %xmm0` is `62 f1 7c 08 28 04 04` and `(%rsp,%r12,1)` is `62 b1 7c 08 28 04 24`, so index `4` is again `E-RANGE-004` (`N16aa`) and `%r12` is legal through `X̄ = 0` (`ADR-0050`, `EXP-0052`). `0.24.0` keeps both fields where the base disappears: `(,%rax,4)` is `62 f1 7c 08 28 0c 85 00 00 00 00` and `-4096(,%r12,8), %xmm3` is `62 b1 7c 08 28 1c e5 00 f0 ff ff`, so only `SIB` bits 48–50 and the `disp32` slot moved (`ADR-0051`, `EXP-0053`). `0.25.0` takes the `100` index value as a shape instead of an exclusion: the absolute row writes it into the template, so `vmovaps 0x1234, %xmm0` is `62 f1 7c 08 28 04 25 34 12 00 00` while the indexed row beside it is `62 f1 7c 08 28 04 85 34 12 00 00` — three bits and the operand list differ (`ADR-0052`, `EXP-0054`). `0.26.0` makes those three bits template constants in the GPR `mov` rows too: `movq 0x1234, %rax` is `48 8b 04 25 34 12 00 00` while the indexed row is `48 8b 04 85 34 12 00 00`, so the absolute row has no `index` role to fill (`ADR-0053`, `EXP-0055`). `0.45.0` repeats the whole shape at 16-bit width: the `SIB` byte is the same three fields one byte after `ModRM`, the index's fourth bit is `REX.X` at `[9,1]`, the two-bit scale is at `[38,2]`, and the base is the full `REX.B`/`SIB.base` window; `movw 8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08`, `movw 8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08` and `movw 8(%rdi,%r12,4), %r15w` is `66 46 89 7c a7 08`, so index `4` is again `E-RANGE-004` (`N16bv`) and `%r12` is legal through `REX.X = 1` (`ADR-0072`, `EXP-0074`). `0.46.0` drops the `REX` byte, so the index has only its three `SIB` bits: `movw 8(%rax,%rcx,1), %ax` is `66 8b 44 08 08` at five bytes and `movw 8(%rdi,%rsi,4), %di` is `66 8b 7c b7 08`, index `4` is again `E-RANGE-004` (`N16bx`), and `%r12` is not reachable from the row at all, because its low three bits are `100` and there is no `REX.X` (`ADR-0073`, `EXP-0075`). `0.47.0` keeps the register low and gives the base or the index its fourth bit: `movw 8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08` (`REX.B`) and `movw 8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08` (`REX.X`), both six bytes. The index is either the low three bits (base window) or `REX.X` plus three bits (index window, so `%r12` is legal again), and index `4` stays `E-RANGE-004` (`ADR-0074`, `EXP-0076`). `0.48.0` gives both memory operands their fourth bit at once: `movw 8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08` (`REX = 43`), `movw 8(%r12,%r12,1), %ax` is `66 43 8b 44 24 08` (`SIB.base = 100` and `SIB.index = 100` are both meaningful with `REX.B`/`REX.X` set), and `%rbp` is a legal index (`66 41 8b 44 2d 08` for `8(%r13,%rbp,1), %ax`) while `%rsp` is not (`ADR-0075`, `EXP-0077`). `0.49.0` carries the same shape into the 32-bit family, where `r/m = 100` still announces the `SIB` byte one byte earlier: `movl 8(%rax,%rcx,1), %eax` is `8b 44 08 08` (`SIB = 08`), `movl 8(%rdi,%rsi,4), %edi` is `8b 7c b7 08` (`SIB = b7`, scale `2`), and index `4` is still the "no index" value, so `%rsp` is rejected and `4` is `E-RANGE-004` (`N16cc`) (`ADR-0076`, `EXP-0078`). `0.50.0` carries the index's fourth bit into `REX.X` on the prefix-carrying 32-bit rows: `movl 8(%rax,%r9,1), %eax` is `42 8b 44 08 08`, with `SIB.index` at `[27,3]` and `REX.X` at `[1,1]` (`ADR-0077`, `EXP-0079`). `0.51.0` sets `REX.B` and `REX.X` together, so `movl 8(%r8,%r9,1), %eax` is `43 8b 44 08 08` with `SIB.index` at `[27,3]` and `REX.X` at `[1,1]`; `%r12` as an index is `43 8b 44 20 08` (`ADR-0078`, `EXP-0080`). `0.52.0` keeps the index slot at `[1,1]`/`[27,3]` with `REX.X` set: `movl 8(%r8,%r9,1), %r8d` is `47 8b 44 08 08` and `%r12` as an index is `47 8b 44 20 08` (`ADR-0079`, `EXP-0081`). `0.53.0` carries the same `SIB` byte on the `0x67` rows, where the base and index are 32-bit address registers: `movl 8(%eax,%ecx,1), %eax` is `67 8b 44 08 08` and `%ebp` is a legal index (`67 8b 44 28 08`), while `%esp` stays rejected (`ADR-0080`, `EXP-0082`). `0.54.0` sets `REX.X` at `[9,1]` on the extended index row: `movl 8(%eax,%r9d,1), %eax` is `67 42 8b 44 08 08` and `%r12d` as an index is `67 42 8b 44 20 08`, while `%ebp` remains a legal low index (`ADR-0081`, `EXP-0083`). `0.55.0` composes `REX.X` with `REX.B` or `REX.R` in the same byte: `movl 8(%r8d,%r9d,1), %eax` is `67 43 8b 44 08 08` (`REX.BX`) and `movl 8(%eax,%r9d,1), %r8d` is `67 46 8b 44 08 08` (`REX.RX`), with `%r12d` still legal as an index (`67 42 8b 44 20 08`) and `%esp` still rejected (`ADR-0082`, `EXP-0084`). `0.56.0` keeps `REX.X` at `[9,1]` on the 32-bit address shape at 64-bit value width: `movq 8(%eax,%r12d,1), %rax` is `67 4a 8b 44 20 08` and `%ebp` remains a legal base (`67 48 8b 44 0d 08`) (`ADR-0083`, `EXP-0085`). `0.57.0` carries the same `SIB` byte at 16-bit value width behind `0x67 66`, where the index has only its three `SIB` bits at `[35,3]`: `%ebp` is a legal index (`67 66 8b 44 28 08`) and `%esp` stays rejected (`ADR-0084`, `EXP-0086`). `0.58.0` carries that `SIB` byte one byte later when `REX` exists: the index is `[43,3]` and the scale `[46,2]`, with `REX.X` fixed at `[17,1]` on the extended window, so `movw 8(%eax,%r9d,1), %ax` is `67 66 42 8b 44 08 08` and `%esp` stays rejected (`ADR-0085`, `EXP-0087`). | frozen |
| EC-38 | x86-64 | Memory base reach is a window per encoding family: the legacy row has no `REX` byte, two-byte VEX has no `B`, and reaching `r8`–`r15` changes the instruction length, while EVEX already carries an inverted `B̄` in its four-byte prefix; the 8/16-bit `mov` rows split three ways, because the word and low-byte rows pay a `REX` byte, the `40`-prefixed byte rows already carry one, and the high-byte rows can never extend | One prefix byte (or none) and a base's fourth bit | `form variant` (`-base-ext` rows) + `operand value` (the disjoint windows: the low rows exclude `8`–`15`, the extension rows exclude `0`–`7` and `12`) | `llvm-mc` 23.1.2: `movaps 8(%r8), %xmm0` is `41 0f 28 40 08` while `movaps 8(%rax), %xmm0` is `0f 28 40 08`; `vmovaps 8(%r8), %xmm0` is `c4 c1 78 28 40 08` while the same base 0 is `c5 f8 28 40 08`; `{evex} vmovaps 16(%r8), %xmm0` stays seven bytes (`62 d1 7c 08 28 40 01`) because `B̄` is already in the prefix. One row that accepted both reaches and inserted the longer prefix on seeing a high value would change the instruction length from an operand (`INV-04`), so the reach is the form; 0.9.0's shared 3-bit field is the counterexample that could not (`N14f`, `N14g`), and `0.10.0` splits it into two disjoint windows (`N01af`, `N16k`, `N16l`) (`ADR-0036`, `ADR-0037`, `EXP-0039`). The 8/16-bit `mov` memory rows repeat the split inside one mnemonic: `movw %ax, 8(%rax)` is `66 89 40 08` (four bytes) while `movw %ax, 8(%r8)` is `66 41 89 40 08` (five), yet `movb %spl, 8(%rax)` and `movb %spl, 8(%r8)` are both four bytes (`40 88 60 08` / `41 88 60 08`), so only the rows without a `REX` byte gain a form; `movb %ah, 8(%r8)` has no encoding at all because the `REX` byte that carries `REX.B` renames `ah` to `spl`. The byte axis splits the register set between the two windows — numbers 0–3 on the new `41` rows, 4–7 on the widened `40` rows — so one `(register, base)` pair names exactly one row (`ADR-0045`, `EXP-0047`). `0.19.0` then closes the `SIB` half of the same axis: `%rsp` and `%r12` reach the 8/16-bit rows through twenty-eight fixed-base rows, because the `SIB` byte is part of the template and the two bases stay disjoint from the general rows (`66 89 40 08` vs `66 89 44 24 08` vs `66 41 89 44 24 08`); the high-byte family gets the `%rsp` row only, since `movb %ah, 8(%r12)` would need the `REX` byte that renames `ah` (`ADR-0046`, `N01aq`, `EXP-0048`). `0.20.0` adds the `SIB` pair to the SSE families too: the legacy rows pay the `41` `REX.B` byte (`0f 28 44 24 08` vs `41 0f 28 44 24 08`), the VEX rows pay the three-byte prefix (`c5 f8 28 44 24 08` vs `c4 c1 78 28 44 24 08`), and each family keeps the register window it already had — `xmm0`–`xmm7` on legacy, `xmm0`–`xmm15` on VEX, where clearing `R̄` (`c5 78` / `c4 41 78`) changes no length (`ADR-0047`, `EXP-0049`). `0.21.0` gives the EVEX memory rows the same `SIB` pair, and there the two bases cost the same byte: `62 f1 7c 08 28 44 24 01` for `%rsp` and `62 d1 7c 08 28 44 24 01` for `%r12`, with the whole `xmm0`–`xmm31` window reachable at no extra length, since `B̄`, `R̄` and `R̄'` are already prefix bits (`ADR-0048`, `EXP-0050`). `0.22.0` repeats it with no displacement: `62 f1 7c 08 28 04 24` for `%rsp` and `62 d1 7c 08 28 04 24` for `%r12`, where the two bases still differ only in `P0` and the whole `xmm0`–`xmm31` window stays reachable at the same seven bytes (`ADR-0049`, `EXP-0051`). The 32-bit GPR register window is the same axis one operand class over: `movl 0x1234, %eax` is `8b 04 25 34 12 00 00` (seven bytes) while `movl 0x1234, %r8d` pays `REX = 44` and is eight (`44 8b 04 25 34 12 00 00`), so the low rows hold only the three-bit `ModRM.reg` window at `[11,3]` (`0`–`7`) and the `-ext` rows hold `[19,3]` plus `REX.R` at `[2,1]` with `0`–`7` excluded (`E-RANGE-004`, `N16ad`); `0.27.0` makes both halves rows so the length difference is a `form_id` component (`ADR-0054`, `EXP-0056`). The 16-bit rows repeat the same split one width down: `movw 0x1234, %ax` is `66 8b 04 25 34 12 00 00` (eight bytes, no `REX` byte) while `movw 0x1234, %r8w` pays `REX = 44` after the prefix and is nine (`66 44 8b 04 25 34 12 00 00`), so `0.28.0` makes the word window a `form_id` component too (`ADR-0055`, `EXP-0057`). The byte rows split four ways on the same axis: `movb 0x1234, %al` is `8a 04 25 34 12 00 00` and `movb 0x1234, %ah` is `8a 24 25 34 12 00 00` (seven bytes each, no `REX` byte), while `movb 0x1234, %spl` pays `REX = 40` (`40 8a 24 25 …`) and `movb 0x1234, %r8b` pays `REX = 44` (`44 8a 04 25 …`), both eight bytes; `0.29.0` appends the four windows × load/store, so the length is the prefix and the register set is the `form_id` (`ADR-0056`, `EXP-0058`). `0.30.0` carries the fourth window into the memory rows: `%r8b`-`%r15b` need a `REX` byte at every base window, so `movb 8(%rax), %r8b` is `44 8a 40 08` and `movb 8(%r12), %r10b` is `45 8a 54 24 08` where `movb 8(%rax), %ah` is `8a 60 08` and `movb 8(%rax), %spl` is `40 8a 60 08`; the high-byte kind therefore cannot reach any of the extended rows (`E-DEF-001` at definition load, `E-OPERAND-001` in a plan, `N02at`) and the register slot excludes `0`-`7` (`E-RANGE-004`, `N16ag`; `ADR-0057`, `EXP-0059`). `0.35.0` gives the 32-bit `mov` family its first base rows and repeats the split on both fields: `movl (%rax), %eax` is `8b 00` (two bytes, no `REX`), `movl (%rax), %r8d` pays `44` (three bytes, `REX.R` fixed) and `movl (%r8), %eax` pays `41` (three bytes, `REX.B` fixed), so `movl (%r9), %r15d` is `45 8b 39`; the low row's 3-bit `r/m` reaches only bases `0`-`7`, the `REX.R` row carries the base's fourth bit as a slot and reaches all twelve, the `REX.B` row holds only `8`-`15`, and the three plain-base rows exclude `%rsp`/`%r12` (they need the `SIB` byte, which `0.36.0` gives them as eight fixed-base rows: `8b 04 24`/`41 8b 04 24`, with `%r12` always paying the fixed `REX.B` byte and the `-ext` windows four bytes each) and `%rbp`/`%r13` (`r/m = 101` at `mod = 00` is RIP-relative: `movl (%rbp), %eax` is `8b 45 00`) (`ADR-0062`, `ADR-0063`, `EXP-0064`, `EXP-0065`, `N16as`/`N16at`/`N16au`/`N16av`, `N16aw`). `0.37.0` adds the `mod = 01` windows: `movl 8(%rax), %eax` keeps the 3-bit register and base (`8b 40 08`), `movl 8(%rax), %r8d` carries `REX.R` (`44 8b 40 08`), and `movl 8(%r8), %eax` carries `REX.B` (`41 8b 40 08`) with a `8`-`15` base window that excludes the low bases, because a low value would clear the fixed `REX.B` bit and emit `40 8b 40 08` — a different instruction (`ADR-0064`, `N16az`/`N16ba`, `EXP-0066`). `0.38.0` adds the `mod = 10` windows: the same three reach splits (`8b 80 c8 00 00 00`, `44 8b 80 c8 00 00 00`, `41 8b 80 c8 00 00 00`), the displacement at `[24,32]` behind a `REX` byte, and the `REX.B` row again excluding the low bases for the same fixed-bit reason (`ADR-0065`, `N16bd`/`N16be`, `EXP-0067`). `0.41.0` gives the 16-bit `mov` family its `mod = 00` windows: `movw (%rax), %ax` is `66 8b 00` (three bytes) while `movw (%r8), %ax` is `66 41 8b 00` (four), so the plain-base rows split on the base window and exclude `%rsp`/`%rbp` (`N16bh`/`N16bk`) while the `-ext` rows hold `8`–`15` and exclude `0`–`7` (a low value would clear the fixed `REX.B`) plus `%r12`/`%r13`, which `mod = 00` cannot hold (`N16bj`/`N16bi`/`N16bl`); the two `SIB` bases are the four fixed rows above (`ADR-0068`, `EXP-0070`). `0.43.0` repeats the split on the `disp8` rows and shows that the base window itself depends on `mod`: at `mod = 01` `r/m = 101` is a legal `%rbp`/`%r13` base, so the low-base row excludes `%rsp` only (`N16bq`) and the `-ext`-base row excludes `0`–`7` (a low value would clear the fixed `REX.B`, `N16br`) plus `%r12`; the register window is the same `%r8w`–`%r15w` split as the `mod = 00` rows (`ADR-0070`, `EXP-0072`). `0.44.0` repeats the split on the `disp32` rows with the `mod = 10` base window: the plain row excludes `%rsp` only (`N16bt`) and the `-ext` row excludes `0`–`7` and `%r12` (`N16bu`) (`ADR-0071`, `EXP-0073`). `0.45.0` puts the base window back into one row where the `SIB` byte is present: `REX.B` is a slot beside the fixed `REX.R`, so `movw 8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08` and `movw 8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08`, both six bytes; `%rsp`/`%r12` are legal bases because `r/m = 100` announces the `SIB` byte, and `%rbp`/`%r13` because `SIB.base = 101` is a base with a displacement (`ADR-0072`, `EXP-0074`). `0.46.0` shows the other half of that row: without the `REX` byte the base, index and register windows are three bits each, so `movw 8(%rax,%rcx,1), %ax` is `66 8b 44 08 08` and register `8` / base `8` are `E-OPERAND-004` (`N14bb`/`N14bc`), while `%rsp`/`%rbp` stay legal bases because `SIB.base = 100`/`101` is a base with a displacement (`66 8b 44 0c 08` / `66 8b 44 0d 08`) (`ADR-0073`, `EXP-0075`). `0.47.0` splits the window again: with a `REX` byte present only for the base or the index, the register stays at three bits (`%ax`–`%di`), so `movw 8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08` and `movw 8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08`, while base `8` on the `-index-ext` row (`N14be`), index `3` on the `-index-ext` row (`N16by`) and base `3` on the `-base-ext` row (`N16bz`) are loudly rejected (`E-OPERAND-004`/`E-RANGE-004`), never silently cleared (`ADR-0074`, `EXP-0076`). `0.48.0` adds the third member of the split, where both memory operands are extended: `movw 8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08` (`REX = 43`), the register is still three bits so register `8` is `E-OPERAND-004` (`N14bf`), and both operand slots exclude the low window so base `3`/index `3` are `E-RANGE-004` (`N16ca`/`N16cb`) (`ADR-0075`, `EXP-0077`). `0.49.0` gives the 32-bit family its own `REX`-less member: all three registers are three bits, so register `8` and base `8` stay `E-OPERAND-004` (`N14bg`/`N14bh`) and belong to the pending `REX.R`/`REX.B` rows, while index `4` is `E-RANGE-004` (`N16cc`); `%rsp`/`%rbp` are legal bases (`8b 44 0c 08` / `8b 44 35 08`) (`ADR-0076`, `EXP-0078`). `0.50.0` adds the three single-bit members to the 32-bit family: `44 8b 44 08 08` (`R`), `41 8b 44 08 08` (`B`) and `42 8b 44 08 08` (`X`), each excluding `0`–`7` on the extended slot (`E-RANGE-004`, `N16cd`/`N16ce`/`N16cf`), while the non-extended operands stay three bits (`E-OPERAND-004`, `N14bi`/`N14bj`) (`ADR-0077`, `EXP-0079`). `0.51.0` adds the `BX` member to the 32-bit split: `43 8b 44 08 08` fixes `REX.B` and `REX.X` at once, excluding `0`–`7` on both memory slots (`E-RANGE-004`, `N16cg`/`N16ch`), while the register stays three bits (`E-OPERAND-004`, `N14bk`) (`ADR-0078`, `EXP-0080`). `0.52.0` completes the 32-bit split with the all-extended member: `47 8b 44 08 08` fixes `REX.R`, `REX.B` and `REX.X` at once, excluding `0`–`7` on all three register slots (`E-RANGE-004`, `N16ci`/`N16cj`/`N16ck`) (`ADR-0079`, `EXP-0081`). The `0x67` row is another no-`REX` window: base and index are three bits (`0`–`7`), so an `%r8d` address register is a deferred `addr32` `REX` form rather than an operand value (`ADR-0080`, `EXP-0082`). `0.54.0` splits the `addr32` row into the three single-bit windows: the extended operand is `[10,1]`+`[27,3]` (`REX.R`), `[8,1]`+`[32,3]` (`REX.B`) or `[9,1]`+`[35,3]` (`REX.X`) and excludes `0`–`7` (`E-RANGE-004`), while the operands it keeps low stay three bits (`E-OPERAND-004`) (`ADR-0081`, `EXP-0083`). `0.55.0` adds the four two-bit windows: the two extended operands each carry their `REX` bit and exclude `0`–`7` (`E-RANGE-004`), and the third operand stays a three-bit field (`E-OPERAND-004`), so the `addr32` family has eight windows in all (the bare row, three single-bit rows and four two-bit rows) (`ADR-0082`, `EXP-0084`). `0.56.0` shows the other half of the rule: when the template already carries `REX` (here `REX.W`), the row keeps four-bit register slots and `67 48` widens to `67 4f` from the operand values without a new row (`ADR-0083`, `EXP-0085`). `0.57.0` adds the 16-bit value pair as one no-`REX` window: the value, base and index are three bits each, so `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08`, a value or base above `7` is `E-OPERAND-004` and index `4` is `E-RANGE-004`; the `REX` windows of the 16-bit pair were deferred in `0.57.0` (`ADR-0084`, `EXP-0086`). `0.58.0` reaches `%r8w`–`%r15w` and `%r8d`–`%r15d` one bit at a time: `%r15w` with `%ebp` is `67 66 44 8b 7c 0d 08`, `%r15d` as a base is `67 66 41 8b 54 2f 08` and `%r15d` as an index is `67 66 42 8b 54 38 08`; the two-bit windows stay deferred (`ADR-0085`, `EXP-0087`). | frozen |
| EC-39 | x86-64 | EVEX `disp8*N`: the byte is a compressed field, `disp8 = byte_offset / N`, and `N` is fixed per form (`16` for `xmm`, `32` for `ymm`, `64` for `zmm`), while `disp32` carries bytes | One byte vs four, and the same byte means a different offset | `form variant` (`-disp8x16` / `-disp8x32` / `-disp8x64` / `-disp32`) + `operand type` (`disp8x16` / `disp8x32` / `disp8x64` / `disp32`, whose value is the field content) | `llvm-mc` 23.1.2 with `{evex}`: `vmovaps 16(%rax), %xmm0` is `62 f1 7c 08 28 40 01` (content `1`), `-16` is `… 48 ff` (content `-1`), `2032` is `… 50 7f` (content `127`), while `8(%rax)` is `62 f1 7c 08 28 98 08 00 00 00` (a `disp32` byte `8`, because `8` is not a multiple of `16`) and `2048` is also a `disp32`. Carrying the byte offset would need a division at materialization time (`INV-02`) and would truncate `8` to content `0` (`ADR-0036`, `EXP-0038`). `0.15.0` shows the unit is not a constant: the same content `1` under `P2 = 08`/`28`/`48` is `16`/`32`/`64` bytes (`{evex} vmovaps 32(%rax), %ymm0` is `62 f1 7c 28 28 40 01`, `vmovaps 64(%rax), %zmm0` is `62 f1 7c 48 28 40 01`), so the extremes are `-4096 … 4064` at `ymm` and `-8192 … 8128` at `zmm` while `4096` and `8192` promote to `disp32`. A shared `disp8` slot would have to recover `N` by reading the width byte it is about to write, and would then judge `4064` out of range; the unit therefore lives in the row's `target_type`, never in a division (`ADR-0042`, `EXP-0044`, `N02p`, `N03e`). | frozen |
| EC-40 | x86-64 | Extension-bit polarity: legacy `REX.R`/`REX.B`/`REX.X` are written raw, while VEX and EVEX `R̄`/`B̄`/`X̄` carry the complement | One prefix bit, and the same operand value flips it | `placement invert` (a placement with `"invert": true`) | `llvm-mc` 23.1.2: `{evex} vmovaps 16(%r8), %xmm0` is `62 d1 7c 08 28 40 01` (`B̄ = 0` for base `8`) while `16(%rax)` is `62 f1 7c 08 28 40 01` (`B̄ = 1`); writing the base's fourth bit raw leaves `P0 = f1` and encodes `(%rax)`. The three-byte VEX repeats it: `c4 c1 78 28 40 08` decodes as `8(%r8)` and `c4 e1 78 28 40 08` as `8(%rax)`. Legacy is the opposite: `41 0f 28 40 08` is `8(%r8)` and `40 0f 28 40 08` is `8(%rax)`, the redundant `REX` included. The polarity is a property of the form's placement, never a choice the materializer makes (`ADR-0037`, `EXP-0039`). `0.13.0` adds a second inverted bit: `R̄'` at template bit 12 carries `ModRM.reg` bit 4, and `X̄` at bit 14 carries `ModRM.rm` bit 4 in register form. Writing either raw on `vmovaps %xmm31, %xmm30` (`62 01 7c 08 28 f7`) produces `62 f1 7c 08 28 f7`, which `llvm-mc -disassemble` reads as `%xmm7, %xmm6`; dropping the `R̄'` placement instead leaves `62 11 7c 08 28 f7` = `%xmm31, %xmm14` (`ADR-0040`, `EXP-0042`). `0.23.0` gives `X̄` a second job: in the `SIB` memory rows it carries the index's fourth bit, so `(%rsp,%rax,1)` is `62 f1 7c 08 28 04 04` and `(%rsp,%r12,1)` is `62 b1 7c 08 28 04 24` (`f1` → `b1`), the complement of the index value exactly as `B̄` complements the base (`ADR-0050`, `EXP-0052`). `0.24.0` keeps `X̄` while `B̄` stops being an operand: `(,%r13,4), %ymm9` is `62 31 7c 28 28 0c ad 00 00 00 00` and `-4096(,%r12,8), %xmm3` is `62 b1 7c 08 28 1c e5 00 f0 ff ff`, so the same index value flips the same bit with no base present (`ADR-0051`, `EXP-0053`). `0.25.0` removes all three address bits from the operand list: the absolute row's `SIB = 25` is template, and only the vector slot still rides `R̄`/`R̄'`, so `%xmm21` is `62 e1 7c 08 29 2c 25 …` (`ADR-0052`, `EXP-0054`). | frozen |

## v0 surface (OD-10)

v0 ships only the forms its slices use. The definition table is the feature
surface: a variant that is absent cannot be selected, repaired or approximated,
and naming it is `E-FORM-001`. There is no feature flag and no partially
implemented form.

The x86-64 slice is four hundred and thirteen forms covering fifteen frozen `EC` rows:

| `form_id` | Bytes | Operand signature | Covers |
|---|---|---|---|
| `x86:mov/rm-r64/legacy` | `REX.W 89 /r` | dest `rm64`, src `r64` | EC-27 |
| `x86:mov/r64-rm/legacy` | `REX.W 8B /r` | dest `r64`, src `rm64` | EC-27 |
| `x86:add/rm64-imm8/legacy` | `REX.W 83 /0 ib` | dest `rm64`, imm `imm8` | EC-01 |
| `x86:add/rm64-imm32/legacy` | `REX.W 81 /0 id` | dest `rm64`, imm `imm32` | EC-01, EC-04 |
| `x86:add/rax-imm32/legacy` | `REX.W 05 id` | imm `imm32`, register fixed to `rax` | EC-04 |
| `x86:jmp/rel8/legacy` | `EB cb` | `rel8` target | EC-03 |
| `x86:jmp/rel32/legacy` | `E9 cd` | `rel32` target | EC-03 |
| `x86:mov/r64-riprel32/legacy` | `REX.W 8B /r`, `mod=00`, `r/m=101` | dest `r64`, target `riprel32` (`pcrel_end`) | EC-34, X86-P6 |
| `x86:mov/riprel32-r64/legacy` | `REX.W 89 /r`, `mod=00`, `r/m=101` | src `r64`, target `riprel32` (`pcrel_end`) | EC-34, X86-P6 |
| `x86:mov/r64-base-disp8/legacy` | `REX.W 8B /r`, `mod=01`, `r/m=base` | dest `r64`, base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-35, X86-P4 |
| `x86:mov/r64-base-disp32/legacy` | `REX.W 8B /r`, `mod=10`, `r/m=base` | dest `r64`, base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-35, X86-P4 |
| `x86:mov/base-disp8-r64/legacy` | `REX.W 89 /r`, `mod=01`, `r/m=base` | src `r64`, base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-35, X86-P4 |
| `x86:mov/base-disp32-r64/legacy` | `REX.W 89 /r`, `mod=10`, `r/m=base` | src `r64`, base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-35, X86-P4 |
| `x86:mov/r64-rsp-disp8/legacy` | `REX.W 8B /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `r64`, disp `disp8`, base fixed to `rsp` | EC-02, EC-35, X86-P4 |
| `x86:mov/r64-rsp-disp32/legacy` | `REX.W 8B /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `r64`, disp `disp32`, base fixed to `rsp` | EC-02, EC-35, X86-P4 |
| `x86:mov/rsp-disp8-r64/legacy` | `REX.W 89 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `r64`, disp `disp8`, base fixed to `rsp` | EC-02, EC-35, X86-P4 |
| `x86:mov/rsp-disp32-r64/legacy` | `REX.W 89 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `r64`, disp `disp32`, base fixed to `rsp` | EC-02, EC-35, X86-P4 |
| `x86:mov/r64-r12-disp8/legacy` | `REX.W 8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r64`, disp `disp8`, base fixed to `r12` | EC-35, X86-P11 |
| `x86:mov/r64-r12-disp32/legacy` | `REX.W 8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r64`, disp `disp32`, base fixed to `r12` | EC-35, X86-P11 |
| `x86:mov/r12-disp8-r64/legacy` | `REX.W 89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r64`, disp `disp8`, base fixed to `r12` | EC-35, X86-P11 |
| `x86:mov/r12-disp32-r64/legacy` | `REX.W 89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r64`, disp `disp32`, base fixed to `r12` | EC-35, X86-P11 |
| `x86:mov/r64-base-index-disp8/legacy` | `REX.W 8B /r`, `mod=01`, `r/m=100`, `SIB` | dest `r64`, base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8` | EC-37, X86-P12 |
| `x86:mov/r64-base-index-disp32/legacy` | `REX.W 8B /r`, `mod=10`, `r/m=100`, `SIB` | dest `r64`, base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-37, X86-P12 |
| `x86:mov/base-index-disp8-r64/legacy` | `REX.W 89 /r`, `mod=01`, `r/m=100`, `SIB` | src `r64`, base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8` | EC-37, X86-P12 |
| `x86:mov/base-index-disp32-r64/legacy` | `REX.W 89 /r`, `mod=10`, `r/m=100`, `SIB` | src `r64`, base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-37, X86-P12 |
| `x86:mov/rm16-r16/legacy` | `66 89 /r` | dest `rm16`, src `r16` | EC-36, X86-P5 |
| `x86:mov/r16-rm16/legacy` | `66 8B /r` | dest `r16`, src `rm16` | EC-36, X86-P5 |
| `x86:mov/rm8h-r8h/legacy` | `88 /r` | dest `rm8h`, src `r8h` (numbers 4–7: `ah`/`ch`/`dh`/`bh`) | EC-36, X86-P5 |
| `x86:mov/rm8-r8/legacy` | `88 /r` | dest `rm8`, src `r8` (numbers 0–3: `al`/`cl`/`dl`/`bl`) | EC-36, X86-P5 |
| `x86:mov/rm8-r8-rex/legacy` | `REX 88 /r` | dest `rm8`, src `r8` (numbers 4–7: `spl`/`bpl`/`sil`/`dil`) | EC-36, X86-P5 |
| `x86:movaps/xmm-xmm/legacy` | `0F 28 /r` | dest `xmm`, src `xmm` | EC-09, X86-P9 |
| `x86:vmovaps/xmm-xmm/vex` | `C5 F8 28 /r`, `R̄` inverted | dest `xmm` (0–15), src `xmm` (0–7) | EC-09, X86-P15 |
| `x86:vmovaps/xmm-xmm/evex` | `62 F1 7C 08 28 /r`, `R̄`/`R̄'`/`B̄`/`X̄` inverted | dest `xmm` (0–31), src `xmm` (0–31) | EC-06, EC-09, EC-40, X86-P15, X86-P17 |
| `x86:movaps/xmm-base-disp8/legacy` | `0F 28 /r`, `mod=01`, `r/m=base` | dest `xmm` (0–7), base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-09, EC-35, EC-38, X86-P13 |
| `x86:movaps/xmm-base-disp32/legacy` | `0F 28 /r`, `mod=10`, `r/m=base` | dest `xmm` (0–7), base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-09, EC-35, EC-38, X86-P13 |
| `x86:movaps/base-disp8-xmm/legacy` | `0F 29 /r`, `mod=01`, `r/m=base` | src `xmm` (0–7), base `rm64` (not `%rsp`), disp `disp8` | EC-09, EC-27, EC-35, EC-38, X86-P13 |
| `x86:movaps/base-disp32-xmm/legacy` | `0F 29 /r`, `mod=10`, `r/m=base` | src `xmm` (0–7), base `rm64` (not `%rsp`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, X86-P13 |
| `x86:vmovaps/xmm-base-disp8/vex` | `C5 F8 28 /r`, `mod=01`, `r/m=base`, `R̄` inverted | dest `xmm` (0–15), base `rm64` (not `%rsp`), disp `disp8` | EC-09, EC-35, EC-38, X86-P15 |
| `x86:vmovaps/xmm-base-disp32/vex` | `C5 F8 28 /r`, `mod=10`, `r/m=base`, `R̄` inverted | dest `xmm` (0–15), base `rm64` (not `%rsp`), disp `disp32` | EC-09, EC-35, EC-38, X86-P15 |
| `x86:vmovaps/base-disp8-xmm/vex` | `C5 F8 29 /r`, `mod=01`, `r/m=base`, `R̄` inverted | src `xmm` (0–15), base `rm64` (not `%rsp`), disp `disp8` | EC-09, EC-27, EC-35, EC-38, X86-P15 |
| `x86:vmovaps/base-disp32-xmm/vex` | `C5 F8 29 /r`, `mod=10`, `r/m=base`, `R̄` inverted | src `xmm` (0–15), base `rm64` (not `%rsp`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, X86-P15 |
| `x86:vmovaps/xmm-base-disp8x16/evex` | `62 F1 7C 08 28 /r`, `mod=01`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `xmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp8x16` (field content, unit 16) | EC-09, EC-35, EC-38, EC-39, EC-40, X86-P15, X86-P17 |
| `x86:vmovaps/xmm-base-disp32/evex` | `62 F1 7C 08 28 /r`, `mod=10`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `xmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp32` | EC-09, EC-35, EC-38, EC-39, EC-40, X86-P15, X86-P17 |
| `x86:vmovaps/base-disp8x16-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=01`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `xmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp8x16` (field content, unit 16) | EC-09, EC-27, EC-35, EC-38, EC-39, EC-40, X86-P15, X86-P17 |
| `x86:vmovaps/base-disp32-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=10`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `xmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, EC-39, EC-40, X86-P15, X86-P17 |
| `x86:movaps/xmm-base-ext-disp8/legacy` | `REX.B 0F 28 /r`, `mod=01`, `r/m=base`, base 8–15 | dest `xmm` (0–7), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P14 |
| `x86:movaps/xmm-base-ext-disp32/legacy` | `REX.B 0F 28 /r`, `mod=10`, `r/m=base`, base 8–15 | dest `xmm` (0–7), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P14 |
| `x86:movaps/base-ext-disp8-xmm/legacy` | `REX.B 0F 29 /r`, `mod=01`, `r/m=base`, base 8–15 | src `xmm` (0–7), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-06, EC-09, EC-27, EC-35, EC-38, X86-P14 |
| `x86:movaps/base-ext-disp32-xmm/legacy` | `REX.B 0F 29 /r`, `mod=10`, `r/m=base`, base 8–15 | src `xmm` (0–7), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-06, EC-09, EC-27, EC-35, EC-38, X86-P14 |
| `x86:vmovaps/xmm-base-ext-disp8/vex` | `C4 C1 78 28 /r`, `mod=01`, `r/m=base`, `R̄`/`B̄` inverted | dest `xmm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-09, EC-35, EC-38, EC-40, X86-P15 |
| `x86:vmovaps/xmm-base-ext-disp32/vex` | `C4 C1 78 28 /r`, `mod=10`, `r/m=base`, `R̄`/`B̄` inverted | dest `xmm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-09, EC-35, EC-38, EC-40, X86-P15 |
| `x86:vmovaps/base-ext-disp8-xmm/vex` | `C4 C1 78 29 /r`, `mod=01`, `r/m=base`, `R̄`/`B̄` inverted | src `xmm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-09, EC-27, EC-35, EC-38, EC-40, X86-P15 |
| `x86:vmovaps/base-ext-disp32-xmm/vex` | `C4 C1 78 29 /r`, `mod=10`, `r/m=base`, `R̄`/`B̄` inverted | src `xmm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, EC-40, X86-P15 |
| `x86:movaps/xmm-ext-xmm/legacy` | `REX.R 0F 28 /r` | dest `xmm` (8–15), src `xmm` (0–7) | EC-06, EC-09, X86-P15 |
| `x86:movaps/xmm-xmm-ext/legacy` | `REX.B 0F 28 /r` | dest `xmm` (0–7), src `xmm` (8–15) | EC-06, EC-09, X86-P15 |
| `x86:movaps/xmm-ext-xmm-ext/legacy` | `REX.R`/`REX.B 0F 28 /r` | dest `xmm` (8–15), src `xmm` (8–15) | EC-06, EC-09, X86-P15 |
| `x86:vmovaps/xmm-xmm-src-ext/vex` | `C5 78 29 /r`, `R̄` inverted | dest `xmm` (0–7), src `xmm` (8–15) | EC-09, EC-40, X86-P15 |
| `x86:vmovaps/xmm-xmm-both-ext/vex` | `C4 41 78 28 /r`, `R̄`/`B̄` inverted | dest `xmm` (8–15), src `xmm` (8–15) | EC-09, EC-40, X86-P15 |
| `x86:movaps/xmm-ext-base-disp8/legacy` | `REX.R 0F 28 /r`, `mod=01`, `r/m=base` | dest `xmm` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp8` | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P15 |
| `x86:movaps/xmm-ext-base-disp32/legacy` | `REX.R 0F 28 /r`, `mod=10`, `r/m=base` | dest `xmm` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp32` | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P15 |
| `x86:movaps/base-disp8-xmm-ext/legacy` | `REX.R 0F 29 /r`, `mod=01`, `r/m=base` | src `xmm` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp8` | EC-06, EC-09, EC-27, EC-35, EC-38, X86-P15 |
| `x86:movaps/base-disp32-xmm-ext/legacy` | `REX.R 0F 29 /r`, `mod=10`, `r/m=base` | src `xmm` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp32` | EC-06, EC-09, EC-27, EC-35, EC-38, X86-P15 |
| `x86:movaps/xmm-base/legacy` | `0F 28 /r`, `mod=00`, `r/m=base` | dest `xmm` (0–7), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-09, EC-34, EC-35, X86-P16 |
| `x86:movaps/base-xmm/legacy` | `0F 29 /r`, `mod=00`, `r/m=base` | src `xmm` (0–7), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-09, EC-27, EC-34, EC-35, X86-P16 |
| `x86:movaps/xmm-ext-base/legacy` | `REX.R 0F 28 /r`, `mod=00`, `r/m=base` | dest `xmm` (8–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-09, EC-34, EC-35, X86-P16 |
| `x86:movaps/base-xmm-ext/legacy` | `REX.R 0F 29 /r`, `mod=00`, `r/m=base` | src `xmm` (8–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-09, EC-27, EC-34, EC-35, X86-P16 |
| `x86:movaps/xmm-base-ext/legacy` | `REX.B 0F 28 /r`, `mod=00`, `r/m=base` | dest `xmm` (0–7), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-06, EC-09, EC-34, EC-35, X86-P16 |
| `x86:movaps/base-ext-xmm/legacy` | `REX.B 0F 29 /r`, `mod=00`, `r/m=base` | src `xmm` (0–7), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-06, EC-09, EC-27, EC-34, EC-35, X86-P16 |
| `x86:vmovaps/xmm-base/vex` | `C5 F8 28 /r`, `mod=00`, `r/m=base` | dest `xmm` (0–15), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-09, EC-34, EC-35, X86-P16 |
| `x86:vmovaps/base-xmm/vex` | `C5 F8 29 /r`, `mod=00`, `r/m=base` | src `xmm` (0–15), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-09, EC-27, EC-34, EC-35, X86-P16 |
| `x86:vmovaps/xmm-base-ext/vex` | `C4 C1 78 28 /r`, `mod=00`, `r/m=base`, `R̄`/`B̄` inverted | dest `xmm` (0–15), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-09, EC-35, EC-40, X86-P16 |
| `x86:vmovaps/base-ext-xmm/vex` | `C4 C1 78 29 /r`, `mod=00`, `r/m=base`, `R̄`/`B̄` inverted | src `xmm` (0–15), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-09, EC-27, EC-35, EC-40, X86-P16 |
| `x86:vmovaps/xmm-base/evex` | `62 F1 7C 08 28 /r`, `mod=00`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `xmm` (0–31), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-09, EC-34, EC-35, EC-40, X86-P16, X86-P17 |
| `x86:vmovaps/base-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=00`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `xmm` (0–31), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-09, EC-27, EC-34, EC-35, EC-40, X86-P16, X86-P17 |
| `x86:vmovaps/ymm-ymm/vex` | `C5 FC 28 /r`, `L = 1`, `R̄` inverted | dest `ymm` (0–15), src `ymm` (0–7) | EC-09, EC-40, X86-P18 |
| `x86:vmovaps/ymm-ymm-src-ext/vex` | `C5 7C 29 /r`, `L = 1`, `R̄` inverted | dest `ymm` (0–7), src `ymm` (8–15) | EC-09, EC-40, X86-P18 |
| `x86:vmovaps/ymm-ymm-both-ext/vex` | `C4 41 7C 28 /r`, `L = 1`, `R̄`/`B̄` inverted | dest `ymm` (8–15), src `ymm` (8–15) | EC-09, EC-40, X86-P18 |
| `x86:vmovaps/ymm-ymm/evex` | `62 F1 7C 28 28 /r`, `L'L = 10`, `R̄`/`R̄'`/`B̄`/`X̄` inverted | dest `ymm` (0–31), src `ymm` (0–31) | EC-06, EC-09, EC-40, X86-P18 |
| `x86:vmovaps/zmm-zmm/evex` | `62 F1 7C 48 28 /r`, `L'L = 11`, `R̄`/`R̄'`/`B̄`/`X̄` inverted | dest `zmm` (0–31), src `zmm` (0–31) | EC-06, EC-09, EC-40, X86-P18 |
| `x86:vmovaps/ymm-base-disp8x32/evex` | `62 F1 7C 28 28 /r`, `mod=01`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `ymm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp8x32` (field content, unit 32) | EC-09, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/ymm-base-disp32/evex` | `62 F1 7C 28 28 /r`, `mod=10`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `ymm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp32` | EC-09, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/base-disp8x32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=01`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `ymm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp8x32` (field content, unit 32) | EC-09, EC-27, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/base-disp32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=10`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `ymm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/ymm-base/evex` | `62 F1 7C 28 28 /r`, `mod=00`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `ymm` (0–31), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-09, EC-34, EC-35, EC-40, X86-P19 |
| `x86:vmovaps/base-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=00`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `ymm` (0–31), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-09, EC-27, EC-34, EC-35, EC-40, X86-P19 |
| `x86:vmovaps/zmm-base-disp8x64/evex` | `62 F1 7C 48 28 /r`, `mod=01`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `zmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp8x64` (field content, unit 64) | EC-09, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/zmm-base-disp32/evex` | `62 F1 7C 48 28 /r`, `mod=10`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `zmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp32` | EC-09, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/base-disp8x64-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=01`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `zmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp8x64` (field content, unit 64) | EC-09, EC-27, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/base-disp32-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=10`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `zmm` (0–31), base `rm64` (4 bits, not `%rsp`/`%r12`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, EC-39, EC-40, X86-P19 |
| `x86:vmovaps/zmm-base/evex` | `62 F1 7C 48 28 /r`, `mod=00`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | dest `zmm` (0–31), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-09, EC-34, EC-35, EC-40, X86-P19 |
| `x86:vmovaps/base-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=00`, `r/m=base`, `R̄`/`R̄'`/`B̄` inverted | src `zmm` (0–31), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-09, EC-27, EC-34, EC-35, EC-40, X86-P19 |
| `x86:vmovaps/ymm-base-disp8/vex` | `C5 FC 28 /r`, `mod=01`, `r/m=base`, `L = 1`, `R̄` inverted | dest `ymm` (0–15), base `rm64` (0–7, not `%rsp`), disp `disp8` | EC-09, EC-35, EC-38, X86-P20 |
| `x86:vmovaps/ymm-base-disp32/vex` | `C5 FC 28 /r`, `mod=10`, `r/m=base`, `L = 1`, `R̄` inverted | dest `ymm` (0–15), base `rm64` (0–7, not `%rsp`), disp `disp32` | EC-09, EC-35, EC-38, X86-P20 |
| `x86:vmovaps/base-disp8-ymm/vex` | `C5 FC 29 /r`, `mod=01`, `r/m=base`, `L = 1`, `R̄` inverted | src `ymm` (0–15), base `rm64` (0–7, not `%rsp`), disp `disp8` | EC-09, EC-27, EC-35, EC-38, X86-P20 |
| `x86:vmovaps/base-disp32-ymm/vex` | `C5 FC 29 /r`, `mod=10`, `r/m=base`, `L = 1`, `R̄` inverted | src `ymm` (0–15), base `rm64` (0–7, not `%rsp`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, X86-P20 |
| `x86:vmovaps/ymm-base-ext-disp8/vex` | `C4 C1 7C 28 /r`, `mod=01`, `r/m=base`, `L = 1`, `R̄`/`B̄` inverted | dest `ymm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-09, EC-35, EC-38, EC-40, X86-P20 |
| `x86:vmovaps/ymm-base-ext-disp32/vex` | `C4 C1 7C 28 /r`, `mod=10`, `r/m=base`, `L = 1`, `R̄`/`B̄` inverted | dest `ymm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-09, EC-35, EC-38, EC-40, X86-P20 |
| `x86:vmovaps/base-ext-disp8-ymm/vex` | `C4 C1 7C 29 /r`, `mod=01`, `r/m=base`, `L = 1`, `R̄`/`B̄` inverted | src `ymm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-09, EC-27, EC-35, EC-38, EC-40, X86-P20 |
| `x86:vmovaps/base-ext-disp32-ymm/vex` | `C4 C1 7C 29 /r`, `mod=10`, `r/m=base`, `L = 1`, `R̄`/`B̄` inverted | src `ymm` (0–15), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-09, EC-27, EC-35, EC-38, EC-40, X86-P20 |
| `x86:vmovaps/ymm-base/vex` | `C5 FC 28 /r`, `mod=00`, `r/m=base`, `L = 1`, `R̄` inverted | dest `ymm` (0–15), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-09, EC-34, EC-35, X86-P20 |
| `x86:vmovaps/base-ymm/vex` | `C5 FC 29 /r`, `mod=00`, `r/m=base`, `L = 1`, `R̄` inverted | src `ymm` (0–15), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-09, EC-27, EC-34, EC-35, X86-P20 |
| `x86:vmovaps/ymm-base-ext/vex` | `C4 C1 7C 28 /r`, `mod=00`, `r/m=base`, `L = 1`, `R̄`/`B̄` inverted | dest `ymm` (0–15), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-09, EC-35, EC-40, X86-P20 |
| `x86:vmovaps/base-ext-ymm/vex` | `C4 C1 7C 29 /r`, `mod=00`, `r/m=base`, `L = 1`, `R̄`/`B̄` inverted | src `ymm` (0–15), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-09, EC-27, EC-35, EC-40, X86-P20 |
| `x86:mov/r16-base-disp8/legacy` | `66 8B /r`, `mod=01`, `r/m=base` | dest `r16`, base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/r16-base-disp32/legacy` | `66 8B /r`, `mod=10`, `r/m=base` | dest `r16`, base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/base-disp8-r16/legacy` | `66 89 /r`, `mod=01`, `r/m=base` | src `r16`, base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/base-disp32-r16/legacy` | `66 89 /r`, `mod=10`, `r/m=base` | src `r16`, base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/r8-base-disp8/legacy` | `8A /r`, `mod=01`, `r/m=base` | dest `r8` (0–3), base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8-base-disp32/legacy` | `8A /r`, `mod=10`, `r/m=base` | dest `r8` (0–3), base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp8-r8/legacy` | `88 /r`, `mod=01`, `r/m=base` | src `r8` (0–3), base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp32-r8/legacy` | `88 /r`, `mod=10`, `r/m=base` | src `r8` (0–3), base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8h-base-disp8/legacy` | `8A /r`, `mod=01`, `r/m=base` | dest `r8h` (4–7: `ah`/`ch`/`dh`/`bh`), base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8h-base-disp32/legacy` | `8A /r`, `mod=10`, `r/m=base` | dest `r8h` (4–7), base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp8-r8h/legacy` | `88 /r`, `mod=01`, `r/m=base` | src `r8h` (4–7), base `rm64` (not `%rsp`), disp `disp8` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp32-r8h/legacy` | `88 /r`, `mod=10`, `r/m=base` | src `r8h` (4–7), base `rm64` (not `%rsp`), disp `disp32` | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8-base-disp8-rex/legacy` | `40 8A /r`, `mod=01`, `r/m=base`, `REX.B` | dest `r8` (4–7: `spl`/`bpl`/`sil`/`dil`), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp8` | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 |
| `x86:mov/r8-base-disp32-rex/legacy` | `40 8A /r`, `mod=10`, `r/m=base`, `REX.B` | dest `r8` (4–7), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp32` | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 |
| `x86:mov/base-disp8-r8-rex/legacy` | `40 88 /r`, `mod=01`, `r/m=base`, `REX.B` | src `r8` (4–7: `spl`/`bpl`/`sil`/`dil`), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp8` | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 |
| `x86:mov/base-disp32-r8-rex/legacy` | `40 88 /r`, `mod=10`, `r/m=base`, `REX.B` | src `r8` (4–7), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp32` | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 |
| `x86:mov/r16-base-ext-disp8/legacy` | `66 41 8B /r`, `mod=01`, `r/m=base`, `REX.B` | dest `r16`, base `rm64` (8–15, not `%r12`), disp `disp8` | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r16-base-ext-disp32/legacy` | `66 41 8B /r`, `mod=10`, `r/m=base`, `REX.B` | dest `r16`, base `rm64` (8–15, not `%r12`), disp `disp32` | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp8-r16/legacy` | `66 41 89 /r`, `mod=01`, `r/m=base`, `REX.B` | src `r16`, base `rm64` (8–15, not `%r12`), disp `disp8` | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp32-r16/legacy` | `66 41 89 /r`, `mod=10`, `r/m=base`, `REX.B` | src `r16`, base `rm64` (8–15, not `%r12`), disp `disp32` | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r8-base-ext-disp8/legacy` | `41 8A /r`, `mod=01`, `r/m=base`, `REX.B` | dest `r8` (0–3), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r8-base-ext-disp32/legacy` | `41 8A /r`, `mod=10`, `r/m=base`, `REX.B` | dest `r8` (0–3), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp8-r8/legacy` | `41 88 /r`, `mod=01`, `r/m=base`, `REX.B` | src `r8` (0–3), base `rm64` (8–15, not `%r12`), disp `disp8` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp32-r8/legacy` | `41 88 /r`, `mod=10`, `r/m=base`, `REX.B` | src `r8` (0–3), base `rm64` (8–15, not `%r12`), disp `disp32` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r16-rsp-disp8/legacy` | `66 8B /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `r16`, disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r16-r12-disp8/legacy` | `66 41 8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r16`, disp `disp8`, base fixed to `r12` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r16-rsp-disp32/legacy` | `66 8B /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `r16`, disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r16-r12-disp32/legacy` | `66 41 8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r16`, disp `disp32`, base fixed to `r12` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r16/legacy` | `66 89 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `r16`, disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp8-r16/legacy` | `66 41 89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r16`, disp `disp8`, base fixed to `r12` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r16/legacy` | `66 89 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `r16`, disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp32-r16/legacy` | `66 41 89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r16`, disp `disp32`, base fixed to `r12` | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp8/legacy` | `8A /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `r8` (0–3), disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp8/legacy` | `41 8A /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r8` (0–3), disp `disp8`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp32/legacy` | `8A /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `r8` (0–3), disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp32/legacy` | `41 8A /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r8` (0–3), disp `disp32`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r8/legacy` | `88 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `r8` (0–3), disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp8-r8/legacy` | `41 88 /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r8` (0–3), disp `disp8`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r8/legacy` | `88 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `r8` (0–3), disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp32-r8/legacy` | `41 88 /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r8` (0–3), disp `disp32`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8h-rsp-disp8/legacy` | `8A /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `r8h` (4–7: `ah`/`ch`/`dh`/`bh`), disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8h-rsp-disp32/legacy` | `8A /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `r8h` (4–7), disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r8h/legacy` | `88 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `r8h` (4–7: `ah`/`ch`/`dh`/`bh`), disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r8h/legacy` | `88 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `r8h` (4–7), disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp8-rex/legacy` | `40 8A /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `r8` (4–7: `spl`/`bpl`/`sil`/`dil`), disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp8-rex/legacy` | `41 8A /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r8` (4–7), disp `disp8`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp32-rex/legacy` | `40 8A /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `r8` (4–7), disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp32-rex/legacy` | `41 8A /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `r8` (4–7), disp `disp32`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r8-rex/legacy` | `40 88 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `r8` (4–7: `spl`/`bpl`/`sil`/`dil`), disp `disp8`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp8-r8-rex/legacy` | `41 88 /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r8` (4–7), disp `disp8`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r8-rex/legacy` | `40 88 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `r8` (4–7), disp `disp32`, base fixed to `rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp32-r8-rex/legacy` | `41 88 /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | src `r8` (4–7), disp `disp32`, base fixed to `r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:movaps/xmm-rsp-disp8/legacy` | `0F 28 /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `xmm` (0–7), disp `disp8`, base fixed to `rsp` | EC-02, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/xmm-rsp-disp32/legacy` | `0F 28 /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `xmm` (0–7), disp `disp32`, base fixed to `rsp` | EC-02, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/xmm-r12-disp8/legacy` | `41 0F 28 /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `xmm` (0–7), disp `disp8`, base fixed to `r12` | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/xmm-r12-disp32/legacy` | `41 0F 28 /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | dest `xmm` (0–7), disp `disp32`, base fixed to `r12` | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/rsp-disp8-xmm/legacy` | `0F 29 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `xmm` (0–7), disp `disp8`, base fixed to `rsp` | EC-02, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:movaps/rsp-disp32-xmm/legacy` | `0F 29 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `xmm` (0–7), disp `disp32`, base fixed to `rsp` | EC-02, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:movaps/r12-disp8-xmm/legacy` | `41 0F 29 /r`, `mod=01`, `r/m=100`, `SIB=24`, `REX.B=1` | src `xmm` (0–7), disp `disp8`, base fixed to `r12` | EC-02, EC-06, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:movaps/r12-disp32-xmm/legacy` | `41 0F 29 /r`, `mod=10`, `r/m=100`, `SIB=24`, `REX.B=1` | src `xmm` (0–7), disp `disp32`, base fixed to `r12` | EC-02, EC-06, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-rsp-disp8/vex` | `C5 F8 28 /r`, `mod=01`, `r/m=100`, `SIB=24`, `R̄` inverted | dest `xmm` (0–15), disp `disp8`, base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-rsp-disp32/vex` | `C5 F8 28 /r`, `mod=10`, `r/m=100`, `SIB=24`, `R̄` inverted | dest `xmm` (0–15), disp `disp32`, base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-r12-disp8/vex` | `C4 C1 78 28 /r`, `mod=01`, `r/m=100`, `SIB=24`, `R̄` inverted | dest `xmm` (0–15), disp `disp8`, base fixed to `r12` | EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-r12-disp32/vex` | `C4 C1 78 28 /r`, `mod=10`, `r/m=100`, `SIB=24`, `R̄` inverted | dest `xmm` (0–15), disp `disp32`, base fixed to `r12` | EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/rsp-disp8-xmm/vex` | `C5 F8 29 /r`, `mod=01`, `r/m=100`, `SIB=24`, `R̄` inverted | src `xmm` (0–15), disp `disp8`, base fixed to `rsp` | EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/rsp-disp32-xmm/vex` | `C5 F8 29 /r`, `mod=10`, `r/m=100`, `SIB=24`, `R̄` inverted | src `xmm` (0–15), disp `disp32`, base fixed to `rsp` | EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/r12-disp8-xmm/vex` | `C4 C1 78 29 /r`, `mod=01`, `r/m=100`, `SIB=24`, `R̄` inverted | src `xmm` (0–15), disp `disp8`, base fixed to `r12` | EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/r12-disp32-xmm/vex` | `C4 C1 78 29 /r`, `mod=10`, `r/m=100`, `SIB=24`, `R̄` inverted | src `xmm` (0–15), disp `disp32`, base fixed to `r12` | EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-rsp-disp8x16/evex` | `62 F1 7C 08 28 /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `xmm` (0–31), disp `disp8x16` (field content, unit 16), base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-rsp-disp32/evex` | `62 F1 7C 08 28 /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `xmm` (0–31), disp `disp32`, base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-r12-disp8x16/evex` | `62 D1 7C 08 28 /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `xmm` (0–31), disp `disp8x16` (field content, unit 16), base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-r12-disp32/evex` | `62 D1 7C 08 28 /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `xmm` (0–31), disp `disp32`, base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp8x16-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `xmm` (0–31), disp `disp8x16` (field content, unit 16), base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp32-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `xmm` (0–31), disp `disp32`, base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp8x16-xmm/evex` | `62 D1 7C 08 29 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `xmm` (0–31), disp `disp8x16` (field content, unit 16), base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp32-xmm/evex` | `62 D1 7C 08 29 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `xmm` (0–31), disp `disp32`, base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-rsp-disp8x32/evex` | `62 F1 7C 28 28 /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `ymm` (0–31), disp `disp8x32` (field content, unit 32), base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-rsp-disp32/evex` | `62 F1 7C 28 28 /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `ymm` (0–31), disp `disp32`, base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-r12-disp8x32/evex` | `62 D1 7C 28 28 /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `ymm` (0–31), disp `disp8x32` (field content, unit 32), base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-r12-disp32/evex` | `62 D1 7C 28 28 /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `ymm` (0–31), disp `disp32`, base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp8x32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `ymm` (0–31), disp `disp8x32` (field content, unit 32), base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `ymm` (0–31), disp `disp32`, base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp8x32-ymm/evex` | `62 D1 7C 28 29 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `ymm` (0–31), disp `disp8x32` (field content, unit 32), base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp32-ymm/evex` | `62 D1 7C 28 29 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `ymm` (0–31), disp `disp32`, base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-rsp-disp8x64/evex` | `62 F1 7C 48 28 /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `zmm` (0–31), disp `disp8x64` (field content, unit 64), base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-rsp-disp32/evex` | `62 F1 7C 48 28 /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `zmm` (0–31), disp `disp32`, base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-r12-disp8x64/evex` | `62 D1 7C 48 28 /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `zmm` (0–31), disp `disp8x64` (field content, unit 64), base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-r12-disp32/evex` | `62 D1 7C 48 28 /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `zmm` (0–31), disp `disp32`, base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp8x64-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `zmm` (0–31), disp `disp8x64` (field content, unit 64), base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp32-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `zmm` (0–31), disp `disp32`, base fixed to `rsp` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp8x64-zmm/evex` | `62 D1 7C 48 29 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `zmm` (0–31), disp `disp8x64` (field content, unit 64), base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp32-zmm/evex` | `62 D1 7C 48 29 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `zmm` (0–31), disp `disp32`, base fixed to `r12` | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-rsp/evex` | `62 F1 7C 08 28 /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `xmm` (0–31), base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/xmm-r12/evex` | `62 D1 7C 08 28 /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `xmm` (0–31), base fixed to `r12` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/rsp-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `xmm` (0–31), base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/r12-xmm/evex` | `62 D1 7C 08 29 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `xmm` (0–31), base fixed to `r12` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/ymm-rsp/evex` | `62 F1 7C 28 28 /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `ymm` (0–31), base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/ymm-r12/evex` | `62 D1 7C 28 28 /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `ymm` (0–31), base fixed to `r12` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/rsp-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `ymm` (0–31), base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/r12-ymm/evex` | `62 D1 7C 28 29 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `ymm` (0–31), base fixed to `r12` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/zmm-rsp/evex` | `62 F1 7C 48 28 /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `zmm` (0–31), base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/zmm-r12/evex` | `62 D1 7C 48 28 /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `zmm` (0–31), base fixed to `r12` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/rsp-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `zmm` (0–31), base fixed to `rsp` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/r12-zmm/evex` | `62 D1 7C 48 29 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `zmm` (0–31), base fixed to `r12` | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/xmm-base-index/evex` | `62 F1 7C 08 28 /r`, `mod=00`, `r/m=100`, `SIB` | dest `xmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/xmm-base-index-disp8x16/evex` | `62 F1 7C 08 28 /r`, `mod=01`, `r/m=100`, `SIB` | dest `xmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8x16` (field content, unit 16) | EC-02, EC-09, EC-35, EC-37, EC-39, EC-40, X86-P27 |
| `x86:vmovaps/xmm-base-index-disp32/evex` | `62 F1 7C 08 28 /r`, `mod=10`, `r/m=100`, `SIB` | dest `xmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/base-index-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=00`, `r/m=100`, `SIB` | src `xmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/base-index-disp8x16-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=01`, `r/m=100`, `SIB` | src `xmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8x16` (field content, unit 16) | EC-02, EC-09, EC-35, EC-37, EC-39, EC-40, X86-P27 |
| `x86:vmovaps/base-index-disp32-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=10`, `r/m=100`, `SIB` | src `xmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/ymm-base-index/evex` | `62 F1 7C 28 28 /r`, `mod=00`, `r/m=100`, `SIB` | dest `ymm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/ymm-base-index-disp8x32/evex` | `62 F1 7C 28 28 /r`, `mod=01`, `r/m=100`, `SIB` | dest `ymm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8x32` (field content, unit 32) | EC-02, EC-09, EC-35, EC-37, EC-39, EC-40, X86-P27 |
| `x86:vmovaps/ymm-base-index-disp32/evex` | `62 F1 7C 28 28 /r`, `mod=10`, `r/m=100`, `SIB` | dest `ymm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/base-index-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=00`, `r/m=100`, `SIB` | src `ymm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/base-index-disp8x32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=01`, `r/m=100`, `SIB` | src `ymm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8x32` (field content, unit 32) | EC-02, EC-09, EC-35, EC-37, EC-39, EC-40, X86-P27 |
| `x86:vmovaps/base-index-disp32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=10`, `r/m=100`, `SIB` | src `ymm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/zmm-base-index/evex` | `62 F1 7C 48 28 /r`, `mod=00`, `r/m=100`, `SIB` | dest `zmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/zmm-base-index-disp8x64/evex` | `62 F1 7C 48 28 /r`, `mod=01`, `r/m=100`, `SIB` | dest `zmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8x64` (field content, unit 64) | EC-02, EC-09, EC-35, EC-37, EC-39, EC-40, X86-P27 |
| `x86:vmovaps/zmm-base-index-disp32/evex` | `62 F1 7C 48 28 /r`, `mod=10`, `r/m=100`, `SIB` | dest `zmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/base-index-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=00`, `r/m=100`, `SIB` | src `zmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/base-index-disp8x64-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=01`, `r/m=100`, `SIB` | src `zmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp8x64` (field content, unit 64) | EC-02, EC-09, EC-35, EC-37, EC-39, EC-40, X86-P27 |
| `x86:vmovaps/base-index-disp32-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=10`, `r/m=100`, `SIB` | src `zmm` (0–31), base `rm64`, index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P27 |
| `x86:vmovaps/xmm-index-disp32/evex` | `62 F1 7C 08 28 /r`, `mod=00`, `r/m=100`, `SIB=05` | dest `xmm` (0–31), index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P28 |
| `x86:vmovaps/index-disp32-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=00`, `r/m=100`, `SIB=05` | src `xmm` (0–31), index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P28 |
| `x86:vmovaps/ymm-index-disp32/evex` | `62 F1 7C 28 28 /r`, `mod=00`, `r/m=100`, `SIB=05` | dest `ymm` (0–31), index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P28 |
| `x86:vmovaps/index-disp32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=00`, `r/m=100`, `SIB=05` | src `ymm` (0–31), index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P28 |
| `x86:vmovaps/zmm-index-disp32/evex` | `62 F1 7C 48 28 /r`, `mod=00`, `r/m=100`, `SIB=05` | dest `zmm` (0–31), index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P28 |
| `x86:vmovaps/index-disp32-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=00`, `r/m=100`, `SIB=05` | src `zmm` (0–31), index `sib_index` (not `%rsp`), scale `scale2` (field content), disp `disp32` | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P28 |
| `x86:vmovaps/xmm-abs32/evex` | `62 F1 7C 08 28 /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `xmm` (0–31), disp `disp32` (absolute address) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P29 |
| `x86:vmovaps/abs32-xmm/evex` | `62 F1 7C 08 29 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `xmm` (0–31), disp `disp32` (absolute address) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P29 |
| `x86:vmovaps/ymm-abs32/evex` | `62 F1 7C 28 28 /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `ymm` (0–31), disp `disp32` (absolute address) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P29 |
| `x86:vmovaps/abs32-ymm/evex` | `62 F1 7C 28 29 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `ymm` (0–31), disp `disp32` (absolute address) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P29 |
| `x86:vmovaps/zmm-abs32/evex` | `62 F1 7C 48 28 /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `zmm` (0–31), disp `disp32` (absolute address) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P29 |
| `x86:vmovaps/abs32-zmm/evex` | `62 F1 7C 48 29 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `zmm` (0–31), disp `disp32` (absolute address) | EC-02, EC-09, EC-35, EC-37, EC-40, X86-P29 |
| `x86:mov/r64-abs32/legacy` | `REX.W 8B /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r64`, disp `disp32` (absolute address) | EC-02, EC-05, EC-35, EC-37, X86-P30 |
| `x86:mov/abs32-r64/legacy` | `REX.W 89 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r64`, disp `disp32` (absolute address) | EC-02, EC-05, EC-35, EC-37, X86-P30 |
| `x86:mov/r32-abs32/legacy` | `8B /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r32` (0–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-35, EC-37, EC-38, X86-P31 |
| `x86:mov/r32-ext-abs32/legacy` | `REX.R 8B /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r32` (8–15), disp `disp32` (absolute address) | EC-02, EC-05, EC-06, EC-35, EC-37, EC-38, X86-P31 |
| `x86:mov/abs32-r32/legacy` | `89 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r32` (0–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-35, EC-37, EC-38, X86-P31 |
| `x86:mov/abs32-r32-ext/legacy` | `REX.R 89 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r32` (8–15), disp `disp32` (absolute address) | EC-02, EC-05, EC-06, EC-35, EC-37, EC-38, X86-P31 |
| `x86:mov/r16-abs32/legacy` | `66 8B /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r16` (0–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P32 |
| `x86:mov/r16-ext-abs32/legacy` | `66 REX.R 8B /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r16` (8–15), disp `disp32` (absolute address) | EC-02, EC-05, EC-06, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P32 |
| `x86:mov/abs32-r16/legacy` | `66 89 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r16` (0–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P32 |
| `x86:mov/abs32-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r16` (8–15), disp `disp32` (absolute address) | EC-02, EC-05, EC-06, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P32 |
| `x86:mov/r8-abs32/legacy` | `8A /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r8` (0–3), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/abs32-r8/legacy` | `88 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r8` (0–3), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/r8h-abs32/legacy` | `8A /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r8h` (4–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/abs32-r8h/legacy` | `88 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r8h` (4–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/r8-rex-abs32/legacy` | `REX 8A /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r8` (4–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/abs32-r8-rex/legacy` | `REX 88 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r8` (4–7), disp `disp32` (absolute address) | EC-02, EC-05, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/r8-ext-abs32/legacy` | `REX.R 8A /r`, `mod=00`, `r/m=100`, `SIB=25` | dest `r8` (8–15), disp `disp32` (absolute address) | EC-02, EC-05, EC-06, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/abs32-r8-ext/legacy` | `REX.R 88 /r`, `mod=00`, `r/m=100`, `SIB=25` | src `r8` (8–15), disp `disp32` (absolute address) | EC-02, EC-05, EC-06, EC-27, EC-35, EC-36, EC-37, EC-38, X86-P33 |
| `x86:mov/r8-ext-base-disp8/legacy` | `REX.R 8A /r`, `mod=01`, `r/m=base` | dest `r8` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp8` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r8-ext-base-disp32/legacy` | `REX.R 8A /r`, `mod=10`, `r/m=base` | dest `r8` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp32` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r8-ext-rsp-disp8/legacy` | `REX.R 8A /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `r8` (8–15), disp `disp8`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r8-ext-rsp-disp32/legacy` | `REX.R 8A /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `r8` (8–15), disp `disp32`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r8-ext-r12-disp8/legacy` | `REX.R+REX.B 8A /r`, `mod=01`, `r/m=100`, `SIB=24` | dest `r8` (8–15), disp `disp8`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r8-ext-r12-disp32/legacy` | `REX.R+REX.B 8A /r`, `mod=10`, `r/m=100`, `SIB=24` | dest `r8` (8–15), disp `disp32`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/base-disp8-r8-ext/legacy` | `REX.R 88 /r`, `mod=01`, `r/m=base` | src `r8` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp8` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/base-disp32-r8-ext/legacy` | `REX.R 88 /r`, `mod=10`, `r/m=base` | src `r8` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`), disp `disp32` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/rsp-disp8-r8-ext/legacy` | `REX.R 88 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `r8` (8–15), disp `disp8`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/rsp-disp32-r8-ext/legacy` | `REX.R 88 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `r8` (8–15), disp `disp32`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r12-disp8-r8-ext/legacy` | `REX.R+REX.B 88 /r`, `mod=01`, `r/m=100`, `SIB=24` | src `r8` (8–15), disp `disp8`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r12-disp32-r8-ext/legacy` | `REX.R+REX.B 88 /r`, `mod=10`, `r/m=100`, `SIB=24` | src `r8` (8–15), disp `disp32`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-37, EC-38, X86-P34 |
| `x86:mov/r8-base/legacy` | `8A /r`, `mod=00`, `r/m=base` | dest `r8` (0–3), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/base-r8/legacy` | `88 /r`, `mod=00`, `r/m=base` | src `r8` (0–3), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/r8h-base/legacy` | `8A /r`, `mod=00`, `r/m=base` | dest `r8h` (4–7: `ah`/`ch`/`dh`/`bh`), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/base-r8h/legacy` | `88 /r`, `mod=00`, `r/m=base` | src `r8h` (4–7: `ah`/`ch`/`dh`/`bh`), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/r8-base-rex/legacy` | `40 8A /r`, `mod=00`, `r/m=base` | dest `r8` (4–7: `spl`/`bpl`/`sil`/`dil`), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/base-r8-rex/legacy` | `40 88 /r`, `mod=00`, `r/m=base` | src `r8` (4–7: `spl`/`bpl`/`sil`/`dil`), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/r8-ext-base/legacy` | `REX.R 8A /r`, `mod=00`, `r/m=base` | dest `r8` (8–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/base-r8-ext/legacy` | `REX.R 88 /r`, `mod=00`, `r/m=base` | src `r8` (8–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-36, X86-P35 |
| `x86:mov/r8-rsp/legacy` | `8A /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r8` (0–3), base fixed `%rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/rsp-r8/legacy` | `88 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r8` (0–3), base fixed `%rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r8-r12/legacy` | `41 8A /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r8` (0–3), base fixed `%r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r12-r8/legacy` | `41 88 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r8` (0–3), base fixed `%r12` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r8h-rsp/legacy` | `8A /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r8h` (4–7), base fixed `%rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/rsp-r8h/legacy` | `88 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r8h` (4–7), base fixed `%rsp` | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r8-rsp-rex/legacy` | `40 8A /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r8` (4–7), base fixed `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/rsp-r8-rex/legacy` | `40 88 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r8` (4–7), base fixed `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r8-r12-rex/legacy` | `41 8A /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r8` (4–7), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r12-r8-rex/legacy` | `41 88 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r8` (4–7), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r8-ext-rsp/legacy` | `REX.R 8A /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r8` (8–15), base fixed `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/rsp-r8-ext/legacy` | `REX.R 88 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r8` (8–15), base fixed `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r8-ext-r12/legacy` | `REX.R 8A /r`, `REX.B=1`, `mod=00`, `r/m=100`, `SIB=24` | dest `r8` (8–15), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r12-r8-ext/legacy` | `REX.R 88 /r`, `REX.B=1`, `mod=00`, `r/m=100`, `SIB=24` | src `r8` (8–15), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, X86-P36 |
| `x86:mov/r64-base/legacy` | `REX.W 8B /r`, `mod=00`, `r/m=base` | dest `r64` (0–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-34, EC-35, X86-P37 |
| `x86:mov/base-r64/legacy` | `REX.W 89 /r`, `mod=00`, `r/m=base` | src `r64` (0–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-34, EC-35, X86-P37 |
| `x86:mov/r64-rsp/legacy` | `REX.W 8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r64` (0–15), base fixed `%rsp` | EC-02, EC-06, EC-35, X86-P38 |
| `x86:mov/rsp-r64/legacy` | `REX.W 89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r64` (0–15), base fixed `%rsp` | EC-02, EC-06, EC-35, X86-P38 |
| `x86:mov/r64-r12/legacy` | `REX.W 8B /r`, `REX.B=1`, `mod=00`, `r/m=100`, `SIB=24` | dest `r64` (0–15), base fixed `%r12` | EC-02, EC-06, EC-35, X86-P38 |
| `x86:mov/r12-r64/legacy` | `REX.W 89 /r`, `REX.B=1`, `mod=00`, `r/m=100`, `SIB=24` | src `r64` (0–15), base fixed `%r12` | EC-02, EC-06, EC-35, X86-P38 |
| `x86:mov/r32-base/legacy` | `8B /r`, `mod=00`, `r/m=base` | dest `r32` (0–7), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P39 |
| `x86:mov/base-r32/legacy` | `89 /r`, `mod=00`, `r/m=base` | src `r32` (0–7), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P39 |
| `x86:mov/r32-ext-base/legacy` | `REX.R 8B /r`, `mod=00`, `r/m=base` | dest `r32` (8–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P39 |
| `x86:mov/base-r32-ext/legacy` | `REX.R 89 /r`, `mod=00`, `r/m=base` | src `r32` (8–15), base `rm64` (0–15, not `%rsp`/`%rbp`/`%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P39 |
| `x86:mov/r32-base-ext/legacy` | `REX.B 8B /r`, `mod=00`, `r/m=base` | dest `r32` (0–7), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P39 |
| `x86:mov/base-ext-r32/legacy` | `REX.B 89 /r`, `mod=00`, `r/m=base` | src `r32` (0–7), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P39 |
| `x86:mov/r32-rsp/legacy` | `8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r32` (0–7), base fixed `%rsp` | EC-02, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/rsp-r32/legacy` | `89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r32` (0–7), base fixed `%rsp` | EC-02, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/r32-r12/legacy` | `REX.B 8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r32` (0–7), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/r12-r32/legacy` | `REX.B 89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r32` (0–7), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/r32-ext-rsp/legacy` | `REX.R 8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r32` (8–15), base fixed `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/rsp-r32-ext/legacy` | `REX.R 89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r32` (8–15), base fixed `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/r32-ext-r12/legacy` | `REX.R 8B /r`, `REX.B=1`, `mod=00`, `r/m=100`, `SIB=24` | dest `r32` (8–15), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/r12-r32-ext/legacy` | `REX.R 89 /r`, `REX.B=1`, `mod=00`, `r/m=100`, `SIB=24` | src `r32` (8–15), base fixed `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, EC-38, X86-P40 |
| `x86:mov/r32-base-disp8/legacy` | `8B /r`, `mod=01`, `r/m=base`, `disp8` | dest `r32` (0–7), base `rm64` (0–7, not `%rsp`) | EC-02, EC-27, EC-28, EC-34, EC-38, X86-P41 |
| `x86:mov/base-disp8-r32/legacy` | `89 /r`, `mod=01`, `r/m=base`, `disp8` | src `r32` (0–7), base `rm64` (0–7, not `%rsp`) | EC-02, EC-27, EC-28, EC-34, EC-38, X86-P41 |
| `x86:mov/r32-ext-base-disp8/legacy` | `REX.R 8B /r`, `mod=01`, `r/m=base`, `disp8` | dest `r32` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P41 |
| `x86:mov/base-disp8-r32-ext/legacy` | `REX.R 89 /r`, `mod=01`, `r/m=base`, `disp8` | src `r32` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P41 |
| `x86:mov/r32-base-ext-disp8/legacy` | `REX.B 8B /r`, `mod=01`, `r/m=base`, `disp8` | dest `r32` (0–7), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P41 |
| `x86:mov/base-ext-disp8-r32/legacy` | `REX.B 89 /r`, `mod=01`, `r/m=base`, `disp8` | src `r32` (0–7), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P41 |
| `x86:mov/r32-base-disp32/legacy` | `8B /r`, `mod=10`, `r/m=base`, `disp32` | dest `r32` (0–7), base `rm64` (0–7, not `%rsp`) | EC-02, EC-27, EC-28, EC-34, EC-38, X86-P42 |
| `x86:mov/base-disp32-r32/legacy` | `89 /r`, `mod=10`, `r/m=base`, `disp32` | src `r32` (0–7), base `rm64` (0–7, not `%rsp`) | EC-02, EC-27, EC-28, EC-34, EC-38, X86-P42 |
| `x86:mov/r32-ext-base-disp32/legacy` | `REX.R 8B /r`, `mod=10`, `r/m=base`, `disp32` | dest `r32` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P42 |
| `x86:mov/base-disp32-r32-ext/legacy` | `REX.R 89 /r`, `mod=10`, `r/m=base`, `disp32` | src `r32` (8–15), base `rm64` (0–15, not `%rsp`/`%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P42 |
| `x86:mov/r32-base-ext-disp32/legacy` | `REX.B 8B /r`, `mod=10`, `r/m=base`, `disp32` | dest `r32` (0–7), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P42 |
| `x86:mov/base-ext-disp32-r32/legacy` | `REX.B 89 /r`, `mod=10`, `r/m=base`, `disp32` | src `r32` (0–7), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-28, EC-34, EC-38, X86-P42 |
| `x86:mov/r32-rsp-disp8/legacy` | `8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | dest `r32` (0–7), disp `disp8`, base fixed to `%rsp` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/rsp-disp8-r32/legacy` | `89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | src `r32` (0–7), disp `disp8`, base fixed to `%rsp` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/r32-ext-rsp-disp8/legacy` | `REX.R 8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | dest `r32` (8–15), disp `disp8`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/rsp-disp8-r32-ext/legacy` | `REX.R 89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | src `r32` (8–15), disp `disp8`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/r32-r12-disp8/legacy` | `REX.B 8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | dest `r32` (0–7), disp `disp8`, base fixed to `%r12` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/r12-disp8-r32/legacy` | `REX.B 89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | src `r32` (0–7), disp `disp8`, base fixed to `%r12` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/r32-ext-r12-disp8/legacy` | `REX.RB 8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | dest `r32` (8–15), disp `disp8`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/r12-disp8-r32-ext/legacy` | `REX.RB 89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | src `r32` (8–15), disp `disp8`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P43 |
| `x86:mov/r32-rsp-disp32/legacy` | `8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | dest `r32` (0–7), disp `disp32`, base fixed to `%rsp` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/rsp-disp32-r32/legacy` | `89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | src `r32` (0–7), disp `disp32`, base fixed to `%rsp` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/r32-ext-rsp-disp32/legacy` | `REX.R 8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | dest `r32` (8–15), disp `disp32`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/rsp-disp32-r32-ext/legacy` | `REX.R 89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | src `r32` (8–15), disp `disp32`, base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/r32-r12-disp32/legacy` | `REX.B 8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | dest `r32` (0–7), disp `disp32`, base fixed to `%r12` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/r12-disp32-r32/legacy` | `REX.B 89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | src `r32` (0–7), disp `disp32`, base fixed to `%r12` | EC-02, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/r32-ext-r12-disp32/legacy` | `REX.RB 8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | dest `r32` (8–15), disp `disp32`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/r12-disp32-r32-ext/legacy` | `REX.RB 89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | src `r32` (8–15), disp `disp32`, base fixed to `%r12` | EC-02, EC-06, EC-27, EC-28, EC-34, EC-35, X86-P44 |
| `x86:mov/r16-base/legacy` | `66 8B /r`, `mod=00`, `r/m=base` | dest `r16` (0–7), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-38, X86-P45 |
| `x86:mov/base-r16/legacy` | `66 89 /r`, `mod=00`, `r/m=base` | src `r16` (0–7), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-27, EC-38, X86-P45 |
| `x86:mov/r16-base-ext/legacy` | `66 REX.B 8B /r`, `mod=00`, `r/m=base` | dest `r16` (0–7), base `rm64` (8–15) | EC-02, EC-27, EC-38, X86-P45 |
| `x86:mov/base-ext-r16/legacy` | `66 REX.B 89 /r`, `mod=00`, `r/m=base` | src `r16` (0–7), base `rm64` (8–15) | EC-02, EC-27, EC-38, X86-P45 |
| `x86:mov/r16-rsp/legacy` | `66 8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r16` (0–7), base fixed to `%rsp` | EC-02, EC-27, EC-35, X86-P45 |
| `x86:mov/rsp-r16/legacy` | `66 89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r16` (0–7), base fixed to `%rsp` | EC-02, EC-27, EC-35, X86-P45 |
| `x86:mov/r16-r12/legacy` | `66 REX.B 8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r16` (0–7), base fixed to `%r12` | EC-02, EC-27, EC-35, X86-P45 |
| `x86:mov/r12-r16/legacy` | `66 REX.B 89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r16` (0–7), base fixed to `%r12` | EC-02, EC-27, EC-35, X86-P45 |
| `x86:mov/r16-ext-base/legacy` | `66 REX.R 8B /r`, `mod=00`, `r/m=base` | dest `r16` (8–15), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-06, EC-27, EC-38, X86-P46 |
| `x86:mov/base-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=00`, `r/m=base` | src `r16` (8–15), base `rm64` (0–7, not `%rsp`/`%rbp`) | EC-02, EC-06, EC-27, EC-38, X86-P46 |
| `x86:mov/r16-ext-base-ext/legacy` | `66 REX.RB 8B /r`, `mod=00`, `r/m=base` | dest `r16` (8–15), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-38, X86-P46 |
| `x86:mov/base-ext-r16-ext/legacy` | `66 REX.RB 89 /r`, `mod=00`, `r/m=base` | src `r16` (8–15), base `rm64` (8–15, not `%r12`/`%r13`) | EC-02, EC-06, EC-27, EC-38, X86-P46 |
| `x86:mov/r16-ext-rsp/legacy` | `66 REX.R 8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r16` (8–15), base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-35, X86-P46 |
| `x86:mov/rsp-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r16` (8–15), base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-35, X86-P46 |
| `x86:mov/r16-ext-r12/legacy` | `66 REX.RB 8B /r`, `mod=00`, `r/m=100`, `SIB=24` | dest `r16` (8–15), base fixed to `%r12` | EC-02, EC-06, EC-27, EC-35, X86-P46 |
| `x86:mov/r12-r16-ext/legacy` | `66 REX.RB 89 /r`, `mod=00`, `r/m=100`, `SIB=24` | src `r16` (8–15), base fixed to `%r12` | EC-02, EC-06, EC-27, EC-35, X86-P46 |
| `x86:mov/r16-ext-base-disp8/legacy` | `66 REX.R 8B /r`, `mod=01`, `r/m=base`, `disp8` | dest `r16` (8–15), base `rm64` (0–7, not `%rsp`) | EC-02, EC-06, EC-27, EC-38, X86-P47 |
| `x86:mov/base-disp8-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=01`, `r/m=base`, `disp8` | src `r16` (8–15), base `rm64` (0–7, not `%rsp`) | EC-02, EC-06, EC-27, EC-38, X86-P47 |
| `x86:mov/r16-ext-base-ext-disp8/legacy` | `66 REX.RB 8B /r`, `mod=01`, `r/m=base`, `disp8` | dest `r16` (8–15), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-38, X86-P47 |
| `x86:mov/base-ext-disp8-r16-ext/legacy` | `66 REX.RB 89 /r`, `mod=01`, `r/m=base`, `disp8` | src `r16` (8–15), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-38, X86-P47 |
| `x86:mov/r16-ext-rsp-disp8/legacy` | `66 REX.R 8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | dest `r16` (8–15), base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-35, X86-P47 |
| `x86:mov/rsp-disp8-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | src `r16` (8–15), base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-35, X86-P47 |
| `x86:mov/r16-ext-r12-disp8/legacy` | `66 REX.RB 8B /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | dest `r16` (8–15), base fixed to `%r12` | EC-02, EC-06, EC-27, EC-35, X86-P47 |
| `x86:mov/r12-disp8-r16-ext/legacy` | `66 REX.RB 89 /r`, `mod=01`, `r/m=100`, `SIB=24`, `disp8` | src `r16` (8–15), base fixed to `%r12` | EC-02, EC-06, EC-27, EC-35, X86-P47 |
| `x86:mov/r16-ext-base-disp32/legacy` | `66 REX.R 8B /r`, `mod=10`, `r/m=base`, `disp32` | dest `r16` (8–15), base `rm64` (0–7, not `%rsp`) | EC-02, EC-06, EC-27, EC-38, X86-P48 |
| `x86:mov/base-disp32-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=10`, `r/m=base`, `disp32` | src `r16` (8–15), base `rm64` (0–7, not `%rsp`) | EC-02, EC-06, EC-27, EC-38, X86-P48 |
| `x86:mov/r16-ext-base-ext-disp32/legacy` | `66 REX.RB 8B /r`, `mod=10`, `r/m=base`, `disp32` | dest `r16` (8–15), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-38, X86-P48 |
| `x86:mov/base-ext-disp32-r16-ext/legacy` | `66 REX.RB 89 /r`, `mod=10`, `r/m=base`, `disp32` | src `r16` (8–15), base `rm64` (8–15, not `%r12`) | EC-02, EC-06, EC-27, EC-38, X86-P48 |
| `x86:mov/r16-ext-rsp-disp32/legacy` | `66 REX.R 8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | dest `r16` (8–15), base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-35, X86-P48 |
| `x86:mov/rsp-disp32-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | src `r16` (8–15), base fixed to `%rsp` | EC-02, EC-06, EC-27, EC-35, X86-P48 |
| `x86:mov/r16-ext-r12-disp32/legacy` | `66 REX.RB 8B /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | dest `r16` (8–15), base fixed to `%r12` | EC-02, EC-06, EC-27, EC-35, X86-P48 |
| `x86:mov/r12-disp32-r16-ext/legacy` | `66 REX.RB 89 /r`, `mod=10`, `r/m=100`, `SIB=24`, `disp32` | src `r16` (8–15), base fixed to `%r12` | EC-02, EC-06, EC-27, EC-35, X86-P48 |
| `x86:mov/r16-ext-base-index-disp8/legacy` | `66 REX.R 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r16` (8–15), base `rm64` (0–15), index `sib_index` (0–15 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P49 |
| `x86:mov/base-index-disp8-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r16` (8–15), base `rm64` (0–15), index `sib_index` (0–15 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P49 |
| `x86:mov/r16-ext-base-index-disp32/legacy` | `66 REX.R 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r16` (8–15), base `rm64` (0–15), index `sib_index` (0–15 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P49 |
| `x86:mov/base-index-disp32-r16-ext/legacy` | `66 REX.R 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r16` (8–15), base `rm64` (0–15), index `sib_index` (0–15 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P49 |
| `x86:mov/r16-base-index-disp8/legacy` | `66 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r16` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-36, EC-37, EC-38, X86-P50 |
| `x86:mov/base-index-disp8-r16/legacy` | `66 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r16` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-36, EC-37, EC-38, X86-P50 |
| `x86:mov/r16-base-index-disp32/legacy` | `66 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r16` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-36, EC-37, EC-38, X86-P50 |
| `x86:mov/base-index-disp32-r16/legacy` | `66 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r16` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-36, EC-37, EC-38, X86-P50 |
| `x86:mov/r16-base-ext-index-disp8/legacy` | `66 REX.B 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r16` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/base-ext-index-disp8-r16/legacy` | `66 REX.B 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r16` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/r16-base-ext-index-disp32/legacy` | `66 REX.B 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r16` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/base-ext-index-disp32-r16/legacy` | `66 REX.B 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r16` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/r16-base-index-ext-disp8/legacy` | `66 REX.X 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r16` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/base-index-ext-disp8-r16/legacy` | `66 REX.X 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r16` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/r16-base-index-ext-disp32/legacy` | `66 REX.X 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r16` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/base-index-ext-disp32-r16/legacy` | `66 REX.X 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r16` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P51 |
| `x86:mov/r16-base-ext-index-ext-disp8/legacy` | `66 REX.BX 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r16` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P52 |
| `x86:mov/base-ext-index-ext-disp8-r16/legacy` | `66 REX.BX 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r16` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P52 |
| `x86:mov/r16-base-ext-index-ext-disp32/legacy` | `66 REX.BX 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r16` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P52 |
| `x86:mov/base-ext-index-ext-disp32-r16/legacy` | `66 REX.BX 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r16` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P52 |
| `x86:mov/r32-base-index-disp8/legacy` | `8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r32` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-37, EC-38, X86-P53 |
| `x86:mov/base-index-disp8-r32/legacy` | `89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r32` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-37, EC-38, X86-P53 |
| `x86:mov/r32-base-index-disp32/legacy` | `8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r32` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-37, EC-38, X86-P53 |
| `x86:mov/base-index-disp32-r32/legacy` | `89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r32` (0–7), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-27, EC-37, EC-38, X86-P53 |
| `x86:mov/r32-ext-base-index-disp8/legacy` | `REX.R 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r32` (8–15), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/base-index-disp8-r32-ext/legacy` | `REX.R 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r32` (8–15), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/r32-ext-base-index-disp32/legacy` | `REX.R 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r32` (8–15), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/base-index-disp32-r32-ext/legacy` | `REX.R 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r32` (8–15), base `rm64` (0–7), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/r32-base-ext-index-disp8/legacy` | `REX.B 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r32` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/base-ext-index-disp8-r32/legacy` | `REX.B 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r32` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/r32-base-ext-index-disp32/legacy` | `REX.B 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r32` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/base-ext-index-disp32-r32/legacy` | `REX.B 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r32` (0–7), base `rm64` (8–15), index `sib_index` (0–7 except 4), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/r32-base-index-ext-disp8/legacy` | `REX.X 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r32` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/base-index-ext-disp8-r32/legacy` | `REX.X 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r32` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/r32-base-index-ext-disp32/legacy` | `REX.X 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r32` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/base-index-ext-disp32-r32/legacy` | `REX.X 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r32` (0–7), base `rm64` (0–7), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P54 |
| `x86:mov/r32-base-ext-index-ext-disp8/legacy` | `REX.BX 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r32` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P55 |
| `x86:mov/base-ext-index-ext-disp8-r32/legacy` | `REX.BX 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r32` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P55 |
| `x86:mov/r32-base-ext-index-ext-disp32/legacy` | `REX.BX 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r32` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P55 |
| `x86:mov/base-ext-index-ext-disp32-r32/legacy` | `REX.BX 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r32` (0–7), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P55 |
| `x86:mov/r32-ext-base-ext-index-ext-disp8/legacy` | `REX.RBX 8B /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | dest `r32` (8–15), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P56 |
| `x86:mov/base-ext-index-ext-disp8-r32-ext/legacy` | `REX.RBX 89 /r`, `mod=01`, `r/m=100`, `SIB`, `disp8` | src `r32` (8–15), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P56 |
| `x86:mov/r32-ext-base-ext-index-ext-disp32/legacy` | `REX.RBX 8B /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | dest `r32` (8–15), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P56 |
| `x86:mov/base-ext-index-ext-disp32-r32-ext/legacy` | `REX.RBX 89 /r`, `mod=10`, `r/m=100`, `SIB`, `disp32` | src `r32` (8–15), base `rm64` (8–15), index `sib_index` (8–15), scale `scale2` (2 bits) | EC-02, EC-06, EC-27, EC-37, EC-38, X86-P56 |

The variant names the operand signature as the ISA opcode table spells it, which
is what makes the two `mov` forms and the two `add` immediate forms distinct
without an extra choice field. A plan that names `x86:mov/r64-r64` or
`x86:add/rm64-imm` is rejected: those ids are not in the v0 definition.

The AArch64 slice is one hundred and seventy-six forms across seventeen documents,
covering eleven frozen `EC` rows:

| `form_id` | Encoding | Operand signature | Table | Covers |
|---|---|---|---|---|
| `aarch64:add/x64-x64-x64-lsl0` | `ADD (shifted register)`, `sf=1`, `shift=LSL`, `imm6=0` | dest `x64`, src `x64`, src2 `x64` | all | EC-11, EC-13 |
| `aarch64:add/x64-imm12-lsl0` | `ADD (immediate)`, `sf=1`, `sh=0` | dest `x64`, src `x64`, imm `imm12` | all | EC-11, EC-12 (`sh=0` half) |
| `aarch64:add/x64-imm12-lsl12` | `ADD (immediate)`, `sf=1`, `sh=1` | dest `x64`, src `x64`, imm `imm12` (field content) | `0.2.0`+ | EC-11, EC-12 (`sh=1` half) |
| `aarch64:bl/imm26` | `BL imm26` | `imm26` target | all | A64-P5 |
| `aarch64:adrp/x64-imm21` | `ADRP immlo:immhi` | dest `x64`, `imm21` target | all | EC-15, EC-17 |
| `aarch64:b.cond/imm19` | `B.cond`, `o0=0` | cond `cond4`, `imm19` target | `0.3.0`+ | EC-29, A64-P4 |
| `aarch64:ldr/x64-base-imm12` | `LDR (immediate)`, `size=11`, bit 24 = 1 | dest `x64`, base `x64`, disp `imm12` (8-byte units) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:ldr/x64-base-imm9-pre` | `LDR (immediate)`, bits 11–10 = `11` | dest `x64`, base `x64`, disp `imm9` (signed bytes) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:ldr/x64-base-imm9-post` | `LDR (immediate)`, bits 11–10 = `01` | dest `x64`, base `x64`, disp `imm9` (signed bytes) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:ldur/x64-base-imm9` | `LDUR`, bits 11–10 = `00` | dest `x64`, base `x64`, disp `imm9` (signed bytes) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:str/x64-base-imm12` | `STR (immediate)`, `size=11`, bit 24 = 1 | src `x64`, base `x64`, disp `imm12` (8-byte units) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:str/x64-base-imm9-pre` | `STR (immediate)`, bits 11–10 = `11`, `opc=00` | src `x64`, base `x64`, disp `imm9` (signed bytes) | `0.13.0`+ | EC-14, A64-P15 |
| `aarch64:str/x64-base-imm9-post` | `STR (immediate)`, bits 11–10 = `01`, `opc=00` | src `x64`, base `x64`, disp `imm9` (signed bytes) | `0.13.0`+ | EC-14, A64-P15 |
| `aarch64:stur/x64-base-imm9` | `STUR`, bits 11–10 = `00`, `opc=00` | src `x64`, base `x64`, disp `imm9` (signed bytes) | `0.13.0`+ | EC-14, A64-P15 |
| `aarch64:ldr/x64-imm19` | `LDR (literal)`, `opc=01`, `VR=0`, no `Rn` | dest `x64`, `imm19` target (field content, ×4) | `0.14.0`+ | EC-15, A64-P16 |
| `aarch64:ldr/x64-base-regoff-lsl0` | `LDR (register)`, `option=011`, `S=0` | dest `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/x64-base-regoff-lsl3` | `LDR (register)`, `option=011`, `S=1` | dest `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/x64-base-regoff-uxtw0` | `LDR (register)`, `option=010`, `S=0` | dest `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/x64-base-regoff-uxtw3` | `LDR (register)`, `option=010`, `S=1` | dest `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/x64-base-regoff-sxtw0` | `LDR (register)`, `option=110`, `S=0` | dest `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/x64-base-regoff-sxtw3` | `LDR (register)`, `option=110`, `S=1` | dest `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/x64-base-regoff-sxtx0` | `LDR (register)`, `option=111`, `S=0` | dest `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/x64-base-regoff-sxtx3` | `LDR (register)`, `option=111`, `S=1` | dest `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-lsl0` | `STR (register)`, `opc=00`, `option=011`, `S=0` | src `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-lsl3` | `STR (register)`, `option=011`, `S=1` | src `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-uxtw0` | `STR (register)`, `option=010`, `S=0` | src `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-uxtw3` | `STR (register)`, `option=010`, `S=1` | src `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-sxtw0` | `STR (register)`, `option=110`, `S=0` | src `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-sxtw3` | `STR (register)`, `option=110`, `S=1` | src `x64`, base `x64`, index `w32` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-sxtx0` | `STR (register)`, `option=111`, `S=0` | src `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:str/x64-base-regoff-sxtx3` | `STR (register)`, `option=111`, `S=1` | src `x64`, base `x64`, index `x64` | `0.15.0`+ | EC-14, A64-P17 |
| `aarch64:ldr/w32-base-regoff-lsl0` | `LDR (register)`, `size=10`, `option=011`, `S=0` | dest `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:ldr/w32-base-regoff-lsl2` | `LDR (register)`, `size=10`, `option=011`, `S=1` | dest `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:ldr/w32-base-regoff-uxtw0` | `LDR (register)`, `size=10`, `option=010`, `S=0` | dest `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:ldr/w32-base-regoff-uxtw2` | `LDR (register)`, `size=10`, `option=010`, `S=1` | dest `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:ldr/w32-base-regoff-sxtw0` | `LDR (register)`, `size=10`, `option=110`, `S=0` | dest `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:ldr/w32-base-regoff-sxtw2` | `LDR (register)`, `size=10`, `option=110`, `S=1` | dest `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:ldr/w32-base-regoff-sxtx0` | `LDR (register)`, `size=10`, `option=111`, `S=0` | dest `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:ldr/w32-base-regoff-sxtx2` | `LDR (register)`, `size=10`, `option=111`, `S=1` | dest `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-lsl0` | `STR (register)`, `size=10`, `opc=00`, `option=011`, `S=0` | src `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-lsl2` | `STR (register)`, `size=10`, `opc=00`, `option=011`, `S=1` | src `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-uxtw0` | `STR (register)`, `size=10`, `opc=00`, `option=010`, `S=0` | src `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-uxtw2` | `STR (register)`, `size=10`, `opc=00`, `option=010`, `S=1` | src `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-sxtw0` | `STR (register)`, `size=10`, `opc=00`, `option=110`, `S=0` | src `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-sxtw2` | `STR (register)`, `size=10`, `opc=00`, `option=110`, `S=1` | src `w32`, base `x64`, index `w32` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-sxtx0` | `STR (register)`, `size=10`, `opc=00`, `option=111`, `S=0` | src `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:str/w32-base-regoff-sxtx2` | `STR (register)`, `size=10`, `opc=00`, `option=111`, `S=1` | src `w32`, base `x64`, index `x64` | `0.16.0`+ | EC-14, A64-P18 |
| `aarch64:movz/x64-imm16-lsl0` | `MOVZ`, `sf=1`, `opc=10`, `hw=00` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:movz/x64-imm16-lsl16` | `MOVZ`, `hw=01` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:movz/x64-imm16-lsl32` | `MOVZ`, `hw=10` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:movz/x64-imm16-lsl48` | `MOVZ`, `hw=11` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:movk/x64-imm16-lsl0` | `MOVK`, `sf=1`, `opc=11`, `hw=00` | dest `x64`, imm `imm16` (field content) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:movk/x64-imm16-lsl16` | `MOVK`, `hw=01` | dest `x64`, imm `imm16` (field content) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:movk/x64-imm16-lsl32` | `MOVK`, `hw=10` | dest `x64`, imm `imm16` (field content) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:movk/x64-imm16-lsl48` | `MOVK`, `hw=11` | dest `x64`, imm `imm16` (field content) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:movn/x64-imm16-lsl0` | `MOVN`, `sf=1`, `opc=00`, `hw=00` | dest `x64`, imm `imm16` (field content, not complemented) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:movn/x64-imm16-lsl16` | `MOVN`, `hw=01` | dest `x64`, imm `imm16` (field content, not complemented) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:movn/x64-imm16-lsl32` | `MOVN`, `hw=10` | dest `x64`, imm `imm16` (field content, not complemented) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:movn/x64-imm16-lsl48` | `MOVN`, `hw=11` | dest `x64`, imm `imm16` (field content, not complemented) | `0.17.0`+ | EC-30, EC-16, A64-P19 |
| `aarch64:add/x64-x64-x64-imm6-lsl` | `ADD (shifted register)`, `sf=1`, `shift=LSL` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` (amount) | `0.6.0`+ | EC-31, A64-P8 |
| `aarch64:add/x64-x64-x64-imm6-lsr` | `ADD (shifted register)`, `shift=LSR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` (amount) | `0.6.0`+ | EC-31, A64-P8 |
| `aarch64:add/x64-x64-x64-imm6-asr` | `ADD (shifted register)`, `shift=ASR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` (amount) | `0.6.0`+ | EC-31, A64-P8 |
| `aarch64:add/x64-x64-w32-imm3-uxtb` | `ADD (extended register)`, `sf=1`, bit 21 = 1, `option=000` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:add/x64-x64-w32-imm3-uxth` | `ADD (extended register)`, `option=001` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:add/x64-x64-w32-imm3-uxtw` | `ADD (extended register)`, `option=010` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:add/x64-x64-x64-imm3-uxtx` | `ADD (extended register)`, `option=011` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:add/x64-x64-w32-imm3-sxtb` | `ADD (extended register)`, `option=100` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:add/x64-x64-w32-imm3-sxth` | `ADD (extended register)`, `option=101` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:add/x64-x64-w32-imm3-sxtw` | `ADD (extended register)`, `option=110` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:add/x64-x64-x64-imm3-sxtx` | `ADD (extended register)`, `option=111` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.7.0`+ | EC-13, EC-32, A64-P9 |
| `aarch64:sub/x64-x64-x64-lsl0` | `SUB (shifted register)`, `op=1`, `shift=LSL`, `imm6=0` | dest `x64`, src `x64`, src2 `x64` | `0.8.0`+ | A64-P10 |
| `aarch64:sub/x64-imm12-lsl0` | `SUB (immediate)`, `op=1`, `sh=0` | dest `x64`, src `x64`, imm `imm12` | `0.8.0`+ | EC-12 (`sub` half), A64-P10 |
| `aarch64:sub/x64-imm12-lsl12` | `SUB (immediate)`, `sh=1` | dest `x64`, src `x64`, imm `imm12` (field content) | `0.8.0`+ | EC-12 (`sub` half), A64-P10 |
| `aarch64:sub/x64-x64-x64-imm6-lsl` | `SUB (shifted register)`, `shift=LSL` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.8.0`+ | EC-31, A64-P10 |
| `aarch64:sub/x64-x64-x64-imm6-lsr` | `SUB (shifted register)`, `shift=LSR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.8.0`+ | EC-31, A64-P10 |
| `aarch64:sub/x64-x64-x64-imm6-asr` | `SUB (shifted register)`, `shift=ASR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.8.0`+ | EC-31, A64-P10 |
| `aarch64:adds/x64-x64-x64-lsl0` | `ADDS (shifted register)`, `op=0`, `S=1`, `shift=LSL`, `imm6=0` | dest `x64`, src `x64`, src2 `x64` | `0.9.0`+ | EC-13, A64-P11 |
| `aarch64:adds/x64-imm12-lsl0` | `ADDS (immediate)`, `S=1`, `sh=0` | dest `x64`, src `x64`, imm `imm12` | `0.9.0`+ | EC-12, A64-P11 |
| `aarch64:adds/x64-imm12-lsl12` | `ADDS (immediate)`, `sh=1` | dest `x64`, src `x64`, imm `imm12` (field content) | `0.9.0`+ | EC-12, A64-P11 |
| `aarch64:adds/x64-x64-x64-imm6-lsl` | `ADDS (shifted register)`, `shift=LSL` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.9.0`+ | EC-31, A64-P11 |
| `aarch64:adds/x64-x64-x64-imm6-lsr` | `ADDS (shifted register)`, `shift=LSR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.9.0`+ | EC-31, A64-P11 |
| `aarch64:adds/x64-x64-x64-imm6-asr` | `ADDS (shifted register)`, `shift=ASR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.9.0`+ | EC-31, A64-P11 |
| `aarch64:subs/x64-x64-x64-lsl0` | `SUBS (shifted register)`, `op=1`, `S=1`, `shift=LSL`, `imm6=0` | dest `x64`, src `x64`, src2 `x64` | `0.9.0`+ | EC-13, A64-P11 |
| `aarch64:subs/x64-imm12-lsl0` | `SUBS (immediate)`, `S=1`, `sh=0` | dest `x64`, src `x64`, imm `imm12` | `0.9.0`+ | EC-12, A64-P11 |
| `aarch64:subs/x64-imm12-lsl12` | `SUBS (immediate)`, `sh=1` | dest `x64`, src `x64`, imm `imm12` (field content) | `0.9.0`+ | EC-12, A64-P11 |
| `aarch64:subs/x64-x64-x64-imm6-lsl` | `SUBS (shifted register)`, `shift=LSL` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.9.0`+ | EC-31, A64-P11 |
| `aarch64:subs/x64-x64-x64-imm6-lsr` | `SUBS (shifted register)`, `shift=LSR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.9.0`+ | EC-31, A64-P11 |
| `aarch64:subs/x64-x64-x64-imm6-asr` | `SUBS (shifted register)`, `shift=ASR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` | `0.9.0`+ | EC-31, A64-P11 |
| `aarch64:add/w32-w32-w32-lsl0` | `ADD (shifted register)`, `sf=0`, `shift=LSL`, `imm6=0` | dest `w32`, src `w32`, src2 `w32` | `0.10.0`+ | EC-11, EC-13, A64-P12 |
| `aarch64:add/w32-imm12-lsl0` | `ADD (immediate)`, `sf=0`, `sh=0` | dest `w32`, src `w32`, imm `imm12` | `0.10.0`+ | EC-11, EC-12 (`sh=0` half), A64-P12 |
| `aarch64:add/w32-imm12-lsl12` | `ADD (immediate)`, `sf=0`, `sh=1` | dest `w32`, src `w32`, imm `imm12` (field content) | `0.10.0`+ | EC-11, EC-12 (`sh=1` half), A64-P12 |
| `aarch64:add/w32-w32-w32-imm6-lsl` | `ADD (shifted register)`, `sf=0`, `shift=LSL` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:add/w32-w32-w32-imm6-lsr` | `ADD (shifted register)`, `sf=0`, `shift=LSR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:add/w32-w32-w32-imm6-asr` | `ADD (shifted register)`, `sf=0`, `shift=ASR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:sub/w32-w32-w32-lsl0` | `SUB (shifted register)`, `sf=0`, `op=1`, `shift=LSL`, `imm6=0` | dest `w32`, src `w32`, src2 `w32` | `0.10.0`+ | EC-11, EC-13, A64-P12 |
| `aarch64:sub/w32-imm12-lsl0` | `SUB (immediate)`, `sf=0`, `op=1`, `sh=0` | dest `w32`, src `w32`, imm `imm12` | `0.10.0`+ | EC-11, EC-12 (`sh=0` half), A64-P12 |
| `aarch64:sub/w32-imm12-lsl12` | `SUB (immediate)`, `sf=0`, `op=1`, `sh=1` | dest `w32`, src `w32`, imm `imm12` (field content) | `0.10.0`+ | EC-11, EC-12 (`sh=1` half), A64-P12 |
| `aarch64:sub/w32-w32-w32-imm6-lsl` | `SUB (shifted register)`, `sf=0`, `op=1`, `shift=LSL` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:sub/w32-w32-w32-imm6-lsr` | `SUB (shifted register)`, `sf=0`, `op=1`, `shift=LSR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:sub/w32-w32-w32-imm6-asr` | `SUB (shifted register)`, `sf=0`, `op=1`, `shift=ASR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:adds/w32-w32-w32-lsl0` | `ADDS (shifted register)`, `sf=0`, `S=1`, `shift=LSL`, `imm6=0` | dest `w32`, src `w32`, src2 `w32` | `0.10.0`+ | EC-11, EC-13, A64-P12 |
| `aarch64:adds/w32-imm12-lsl0` | `ADDS (immediate)`, `sf=0`, `S=1`, `sh=0` | dest `w32`, src `w32`, imm `imm12` | `0.10.0`+ | EC-11, EC-12 (`sh=0` half), A64-P12 |
| `aarch64:adds/w32-imm12-lsl12` | `ADDS (immediate)`, `sf=0`, `S=1`, `sh=1` | dest `w32`, src `w32`, imm `imm12` (field content) | `0.10.0`+ | EC-11, EC-12 (`sh=1` half), A64-P12 |
| `aarch64:adds/w32-w32-w32-imm6-lsl` | `ADDS (shifted register)`, `sf=0`, `S=1`, `shift=LSL` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:adds/w32-w32-w32-imm6-lsr` | `ADDS (shifted register)`, `sf=0`, `S=1`, `shift=LSR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:adds/w32-w32-w32-imm6-asr` | `ADDS (shifted register)`, `sf=0`, `S=1`, `shift=ASR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:subs/w32-w32-w32-lsl0` | `SUBS (shifted register)`, `sf=0`, `op=1`, `S=1`, `shift=LSL`, `imm6=0` | dest `w32`, src `w32`, src2 `w32` | `0.10.0`+ | EC-11, EC-13, A64-P12 |
| `aarch64:subs/w32-imm12-lsl0` | `SUBS (immediate)`, `sf=0`, `op=1`, `S=1`, `sh=0` | dest `w32`, src `w32`, imm `imm12` | `0.10.0`+ | EC-11, EC-12 (`sh=0` half), A64-P12 |
| `aarch64:subs/w32-imm12-lsl12` | `SUBS (immediate)`, `sf=0`, `op=1`, `S=1`, `sh=1` | dest `w32`, src `w32`, imm `imm12` (field content) | `0.10.0`+ | EC-11, EC-12 (`sh=1` half), A64-P12 |
| `aarch64:subs/w32-w32-w32-imm6-lsl` | `SUBS (shifted register)`, `sf=0`, `op=1`, `S=1`, `shift=LSL` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:subs/w32-w32-w32-imm6-lsr` | `SUBS (shifted register)`, `sf=0`, `op=1`, `S=1`, `shift=LSR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:subs/w32-w32-w32-imm6-asr` | `SUBS (shifted register)`, `sf=0`, `op=1`, `S=1`, `shift=ASR` | dest `w32`, src `w32`, src2 `w32`, imm `imm6` (`0…31`) | `0.10.0`+ | EC-11, EC-31, A64-P12 |
| `aarch64:sub/x64-x64-w32-imm3-uxtb` | `SUB (extended register)`, `op=1`, bit 21 = 1, `option=000` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:sub/x64-x64-w32-imm3-uxth` | `SUB (extended register)`, `option=001` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:sub/x64-x64-w32-imm3-uxtw` | `SUB (extended register)`, `option=010` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:sub/x64-x64-x64-imm3-uxtx` | `SUB (extended register)`, `option=011` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:sub/x64-x64-w32-imm3-sxtb` | `SUB (extended register)`, `option=100` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:sub/x64-x64-w32-imm3-sxth` | `SUB (extended register)`, `option=101` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:sub/x64-x64-w32-imm3-sxtw` | `SUB (extended register)`, `option=110` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:sub/x64-x64-x64-imm3-sxtx` | `SUB (extended register)`, `option=111` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-w32-imm3-uxtb` | `ADDS (extended register)`, `S=1`, bit 21 = 1, `option=000` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-w32-imm3-uxth` | `ADDS (extended register)`, `option=001` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-w32-imm3-uxtw` | `ADDS (extended register)`, `option=010` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-x64-imm3-uxtx` | `ADDS (extended register)`, `option=011` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-w32-imm3-sxtb` | `ADDS (extended register)`, `option=100` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-w32-imm3-sxth` | `ADDS (extended register)`, `option=101` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-w32-imm3-sxtw` | `ADDS (extended register)`, `option=110` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:adds/x64-x64-x64-imm3-sxtx` | `ADDS (extended register)`, `option=111` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-w32-imm3-uxtb` | `SUBS (extended register)`, `op=1`, `S=1`, bit 21 = 1, `option=000` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-w32-imm3-uxth` | `SUBS (extended register)`, `option=001` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-w32-imm3-uxtw` | `SUBS (extended register)`, `option=010` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-x64-imm3-uxtx` | `SUBS (extended register)`, `option=011` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-w32-imm3-sxtb` | `SUBS (extended register)`, `option=100` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-w32-imm3-sxth` | `SUBS (extended register)`, `option=101` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-w32-imm3-sxtw` | `SUBS (extended register)`, `option=110` | dest `x64`, src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:subs/x64-x64-x64-imm3-sxtx` | `SUBS (extended register)`, `option=111` | dest `x64`, src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.11.0`+ | EC-13, EC-32, A64-P13 |
| `aarch64:cmp/x64-x64-lsl0` | `SUBS (shifted register)`, `Rd=31`, `shift=LSL`, `imm6=0` | src `x64`, src2 `x64` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-imm6-lsl` | `SUBS (shifted register)`, `Rd=31`, `shift=LSL` | src `x64`, src2 `x64`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-imm6-lsr` | `SUBS (shifted register)`, `Rd=31`, `shift=LSR` | src `x64`, src2 `x64`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-imm6-asr` | `SUBS (shifted register)`, `Rd=31`, `shift=ASR` | src `x64`, src2 `x64`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-imm12-lsl0` | `SUBS (immediate)`, `Rd=31`, `sh=0` | src `x64`, imm `imm12` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-imm12-lsl12` | `SUBS (immediate)`, `Rd=31`, `sh=1` | src `x64`, imm `imm12` (field content) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/w32-w32-lsl0` | `SUBS (shifted register)`, `Rd=31`, `shift=LSL`, `imm6=0` | src `w32`, src2 `w32` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/w32-w32-imm6-lsl` | `SUBS (shifted register)`, `Rd=31`, `shift=LSL` | src `w32`, src2 `w32`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/w32-w32-imm6-lsr` | `SUBS (shifted register)`, `Rd=31`, `shift=LSR` | src `w32`, src2 `w32`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/w32-w32-imm6-asr` | `SUBS (shifted register)`, `Rd=31`, `shift=ASR` | src `w32`, src2 `w32`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/w32-imm12-lsl0` | `SUBS (immediate)`, `Rd=31`, `sh=0` | src `w32`, imm `imm12` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/w32-imm12-lsl12` | `SUBS (immediate)`, `Rd=31`, `sh=1` | src `w32`, imm `imm12` (field content) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-w32-imm3-uxtb` | `SUBS (extended register)`, `Rd=31`, `option=000` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-w32-imm3-uxth` | `SUBS (extended register)`, `Rd=31`, `option=001` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-w32-imm3-uxtw` | `SUBS (extended register)`, `Rd=31`, `option=010` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-x64-imm3-uxtx` | `SUBS (extended register)`, `Rd=31`, `option=011` | src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-w32-imm3-sxtb` | `SUBS (extended register)`, `Rd=31`, `option=100` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-w32-imm3-sxth` | `SUBS (extended register)`, `Rd=31`, `option=101` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-w32-imm3-sxtw` | `SUBS (extended register)`, `Rd=31`, `option=110` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmp/x64-x64-x64-imm3-sxtx` | `SUBS (extended register)`, `Rd=31`, `option=111` | src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-lsl0` | `ADDS (shifted register)`, `Rd=31`, `shift=LSL`, `imm6=0` | src `x64`, src2 `x64` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-imm6-lsl` | `ADDS (shifted register)`, `Rd=31`, `shift=LSL` | src `x64`, src2 `x64`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-imm6-lsr` | `ADDS (shifted register)`, `Rd=31`, `shift=LSR` | src `x64`, src2 `x64`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-imm6-asr` | `ADDS (shifted register)`, `Rd=31`, `shift=ASR` | src `x64`, src2 `x64`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-imm12-lsl0` | `ADDS (immediate)`, `Rd=31`, `sh=0` | src `x64`, imm `imm12` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-imm12-lsl12` | `ADDS (immediate)`, `Rd=31`, `sh=1` | src `x64`, imm `imm12` (field content) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/w32-w32-lsl0` | `ADDS (shifted register)`, `Rd=31`, `shift=LSL`, `imm6=0` | src `w32`, src2 `w32` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/w32-w32-imm6-lsl` | `ADDS (shifted register)`, `Rd=31`, `shift=LSL` | src `w32`, src2 `w32`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/w32-w32-imm6-lsr` | `ADDS (shifted register)`, `Rd=31`, `shift=LSR` | src `w32`, src2 `w32`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/w32-w32-imm6-asr` | `ADDS (shifted register)`, `Rd=31`, `shift=ASR` | src `w32`, src2 `w32`, imm `imm6` (amount) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/w32-imm12-lsl0` | `ADDS (immediate)`, `Rd=31`, `sh=0` | src `w32`, imm `imm12` | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/w32-imm12-lsl12` | `ADDS (immediate)`, `Rd=31`, `sh=1` | src `w32`, imm `imm12` (field content) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-w32-imm3-uxtb` | `ADDS (extended register)`, `Rd=31`, `option=000` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-w32-imm3-uxth` | `ADDS (extended register)`, `Rd=31`, `option=001` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-w32-imm3-uxtw` | `ADDS (extended register)`, `Rd=31`, `option=010` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-x64-imm3-uxtx` | `ADDS (extended register)`, `Rd=31`, `option=011` | src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-w32-imm3-sxtb` | `ADDS (extended register)`, `Rd=31`, `option=100` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-w32-imm3-sxth` | `ADDS (extended register)`, `Rd=31`, `option=101` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-w32-imm3-sxtw` | `ADDS (extended register)`, `Rd=31`, `option=110` | src `x64`, src2 `w32`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |
| `aarch64:cmn/x64-x64-x64-imm3-sxtx` | `ADDS (extended register)`, `Rd=31`, `option=111` | src `x64`, src2 `x64`, imm `imm3` (0–4) | `0.12.0`+ | EC-33, A64-P14 |

The `-lsl0`/`-lsl12` suffix is part of the id because the MRS node leaves
`shift`, `imm6` and `sh` variable; the table pins them and the name says so
(`07_definition_format.md` §8.2). Both halves of `EC-12` are therefore carried
by a form variant, not by a value-dependent bit. `-lsl12` is in `0.2.0` and later
only, so naming it against `0.1.0` is `E-FORM-001` (`N01`). The
`-lsl0` … `-lsl48` suffix on the twelve move-wide rows is the same device for the
2-bit `hw` lane selector, `-imm6-lsl` … `-imm6-asr` is the same device again
for the 2-bit `shift` selector, with the amount as the last operand, and
`-imm3-uxtb` … `-imm3-sxtx` is the same device for the 3-bit `option` selector
of the extended-register node.

The six `sub` rows use the first two devices again with one difference: the
mnemonic is not a field at all. `SUB_64_addsub_imm` and `SUB_64_addsub_shift` are
the `ADD_64` nodes with `op` at 30+1 fixed to `1`, so `sub` is a different node
rather than a value of an operand, and the `form_id`'s mnemonic component is what
carries it (`A64-P10`, ADR-0017). `sh`, the shift keyword and `imm6` are treated
exactly as the `add` rows treat them, including the `lsl #0` overlap, and a
literal outside the named `sh` half is `E-RANGE-001` (`N18d`).

The twelve `adds`/`subs` rows are the same two devices on the `S = 1` nodes, and
they settle the same question `sub` answered: the flag-setting part of the
mnemonic is not a field either. `ADDS_64_addsub_shift`, `ADDS_64S_addsub_imm`,
`SUBS_64_addsub_shift` and `SUBS_64S_addsub_imm` are the four nodes already read
with `S` at 29+1 fixed to `1`, so the bit belongs to the node and the `form_id`'s
mnemonic component is again what carries it (`A64-P11`, ADR-0018). `sh`, the shift
keyword and `imm6` are inherited unchanged, `0x1000` on `adds/x64-imm12-lsl0` is
`E-RANGE-001` (`N18e`), and `cmp`/`cmn` are a separate two-operand shape that
fixes `Rd = 31` and drops the destination (`ADR-0021`, `N01i`).

The twenty-four `w` rows are the same devices on the `sf = 0` nodes.
`ADD_32_addsub_shift`/`ADD_32_addsub_imm`, `SUB_32_*`, `ADDS_32_addsub_shift`/
`ADDS_32S_addsub_imm` and `SUBS_32_*` are the eight nodes already read with `sf`
at 31+1 fixed to `0`, so the width belongs to the node and the operand-signature
component of the `form_id` (`w32-…` vs `x64-…`) is what carries it (`A64-P12`,
ADR-0019). Every register slot is `aarch64.gpr32`/`w32`; an `x64` operand is
`E-OPERAND-001` (`N02c`). Register 31 stays legal in every slot and denotes what
the node's role says — `wzr` on the shifted rows and on `ADDS_32S`/`SUBS_32S`
`Rd`, `wsp` on `ADD_32`/`SUB_32` `Rd`/`Rn` and on `ADDS_32S`/`SUBS_32S` `Rn` —
because the encoding stores one 5-bit number and the role is the node's
(`EXP-0021` §2). The 32-bit `imm6` allocates only `0…31`: the slot states
`bits: 6` plus `excluded: [32 … 63]`, so `imm6 = 32` is `E-RANGE-004` (`N16d`)
rather than a truncated shift, and `4096` on `-lsl0` is still `E-RANGE-001`
(`N18f`).

`b.cond` is the opposite case and shows where the line is: the condition is a
4-bit *operand* (`EC-29`), so one row covers all sixteen conditions, while the
`b.cond`-vs-`cbz`-vs-`tbz` choice of instruction is a form variant (`EC-18`).

`movz` is the third shape, between those two. The lane is an *encoding* field
(`hw` at bits 22–21), not a condition and not a choice of instruction, and the
assembly language gives it four spellings (`lsl #0/#16/#32/#48`) but no operand:
`llvm-mc` rejects `lsl #8` and rejects a pre-scaled literal such as `#0x10000`
(`EXP-0016` §2). So `0.5.0` carries one row per lane, `imm16` stays field content
in `0…65535`, and the `mov` alias — which *does* pick the lane from the literal's
value — stays out as `EC-16` (`EC-30`, ADR-0014).

`movk` and `movn` are that same shape one `opc` over: the same layout as `movz`
with the
mnemonic's `opc` fixed by the node (`11`/`00`), so `0.17.0` adds the same four
lanes for each and no plan field names the operation. `movn`'s operand is the raw
`imm16` field, not its complement: `movn x0, #0x1234` is `0x92824680`, the `movz`
word with `opc` changed, and the complement is the instruction's operation. The
`mov` alias is still out: the same literal chooses `movz` or `movn` and the lane
(`mov x0, #0x1234` → `0xd2824680`, `mov x0, #-1` → `0x92800000`), which is the
value-driven selection `INV-02` forbids (`ADR-0026`, `EXP-0028` §2). The `sf = 0`
move-wide lanes stay out with their `w` node, as the `w` arithmetic rows did
before `0.10.0`.

The shift on a register operand is the fourth shape and the one a plan would most
naturally try to carry as a modifier. It is two decisions in one spelling:
`add x0, x1, x2, lsl #3` names a *kind* (`lsl`/`lsr`/`asr`, three keywords and no
numeric spelling — `ror` is rejected and `shift = 11` is unallocated) and an
*amount* (`imm6`, `0…63`). `0.6.0` carries the kind as the form
(`-imm6-lsl` … `-imm6-asr`) and the amount as an `imm6` operand, because a
`modifiers` entry is a guard that never writes a bit: the `-lsl0` row with
`{"name": "lsl", "value": 3}` is `E-OPERAND-003` (`N19`), and silently accepting it
would emit the unshifted word and report success (`EC-31`, ADR-0015).

The extended-register node is the fifth shape and the one a plan would most
naturally try to carry as an `option` operand. It is one bit apart from the
shifted node (bit 21 = 1, `opt` pinned at `00`), and its keyword does two jobs:
it writes the 3-bit `option` field *and* fixes the width of the register it
consumes — the six `[su]xt[bhw]` keywords take a `w` source, `uxtx`/`sxtx` take
an `x` source, and the assembler rejects the cross pairings (`EXP-0018` §2).
Because the encoding records the width as the same 5-bit register number, a free
`option` operand would let a `w` register ride on `-imm3-uxtx` and emit a legal
word for an illegal plan (`INV-07`). `0.7.0` therefore carries one row per
keyword, and the amount is `imm3` field content: the field is three bits, but
only `0…4` are allocated, so the slot states `bits: 3` plus `excluded: [5, 6, 7]`
(`ADR-0009`). `imm3 = 8` is `E-RANGE-001` (`N03-imm3`), `imm3 = 5` is
`E-RANGE-004` (`N16c`), and a `w` operand on `-imm3-uxtx` or on a shifted `x64`
row is `E-OPERAND-001` (`N02b`).

`0.11.0` closes the mnemonic family on this layout. `SUB_64_addsub_ext`,
`ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext` are `ADD_64_addsub_ext` with
`op` at 30+1 and/or `S` at 29+1 fixed, so the eight extended rows repeat for
each of `sub`, `adds` and `subs` (`ADR-0020`). The keyword still fixes the
`src2` width and the `imm3` tail is unchanged: an `x` source on a `-uxtb` row is
`E-OPERAND-001` (`N02d`) and `imm3 = 5` on a `subs` row is `E-RANGE-004`
(`N16e`). Register 31 is not pinned: it stays a plain `reg_number`, and the
node's role decides whether it denotes `sp` or `xzr` (`ADR-0020` decision 5).
The `sf = 0` nodes are in `0.10.0` on the shifted and immediate layouts only;
the extended ones are absent from every document, so
`aarch64:sub/w32-w32-w32-imm3-uxtb` and its `add`/`adds`/`subs` twins are
`E-FORM-001` (`N01l`), and the `cmp`/`cmn` aliases are still out of `0.11.0`
(`N01i`). `N01f`, `N01g`, `N01h`, `N01j` and `N01k` name a row against a version
that predates it, so they now mark version boundaries rather than absence from
the table.

`0.12.0` adds the `cmp`/`cmn` alias family as its own two-operand shape
(`ADR-0021`, `EC-33`). Each row is the `subs`/`adds` row of the same layout and
width with `Rd` pinned to 31 and the destination dropped: four shifted rows and
two immediate rows per mnemonic on `x64` and `w32`, plus the eight `option` rows
on `x64`, for forty rows. The alias MRS nodes carry no `encoding`; their
`operation_id` names the base node, their `condition` is `Rd == '11111'` and
`preferred` is true, so the bytes stay the base node's and the node is the
independent check. The shift and immediate rules transfer per width — including
the `w32` `imm6` tail `32…63` — and the extend keyword still fixes `src2`'s width.
Register 31 stays a plain `reg_number`: `cmp sp, #5` is `0xf10017ff` and
`cmp wsp, w2, uxtb #0` is `0x6b2203ff`. A plan that names a `cmp`/`cmn` row and
still passes `dest` has one operand too many and is `E-OPERAND-002` (`N02e`). The
32-bit extended alias rows stay out because their base rows do (`N01l`).

`0.13.0` completes the store half (`ADR-0022`). `STR_64_ldst_immpre`,
`STR_64_ldst_immpost` and `STUR_64_ldst_unscaled` are the load rows' layouts with
`opc` at `00` and `Rt` as the stored register, so three rows join the family and
no new slot shape appears: `src`, `base`, `disp` in that order. The `imm9` unit,
sign and range transfer unchanged (`-256 … 255`, `E-RANGE-001`), the kind is
still the `form_id`, and the store mnemonic still does not name it —
`str x0,[x1,#1]` assembles to `0xf8001020`, which reads back as `stur`
(`EXP-0024`). `N01n` names the pre-index store id against `0.12.0`, so the new
rows are a version boundary rather than an absence.

`0.14.0` adds the literal load, and it is the first row in this family whose
operand list differs rather than only its bits (`ADR-0023`). `LDR_64_loadlit`
has no `Rn`: the row is `dest` + `target`, with `imm19` at 5+19 and `Rt` at
0+5, and the fixed pattern is `0x58000000`. `imm19` is field content in 4-byte
units, so `{ "value": 1 }` is a load from `PC + 4` and a byte displacement is
the `pcrel_begin` + `scale(2)` fixup with `align_bits: 2`; the field's signed
range is `−262144 … 262143`, i.e. `−1048576 … +1048572` bytes (`EXP-0025`). Only
`opc = 01` (`LDR Xt`) is a row: `00` (`LDR Wt`), `10` (`LDRSW`) and `11`
(`PRFM`) change the destination class or the operation, and `VR = 1` is the
SIMD/FP family. There is no store literal to add — no `STR_*_loadlit` node
exists and the assembler rejects the spelling — so `aarch64:str/x64-imm19` is
`E-FORM-001` in every document.

The eight offset rows carry `EC-14` and are the AArch64 half of `ADR-0008`:
the address is `base` + `disp`, never one memory payload, and the addressing
kind is the `form_id`. `disp` is field content, so the unit belongs to the row:
the two unsigned-offset rows count 8-byte units (`#16` is `disp = 2`) and the
six `imm9` rows count signed bytes (`-256 … 255`), with `align_bits = 0` on
both because the slot holds the field, not the byte offset (`ADR-0013`,
`ADR-0022`). The literal row is the ninth member of the family and the only one
without a `base`. The register-offset kind is the tenth: `Rm`/`option`/`S`
replace `disp`, and bit 21 = 1 with bits 11–10 = `10` is what makes it a
different kind rather than a different displacement.

The sixteen register-offset rows put the second register in an `index` slot and
turn the two remaining variable fields into form bits (`ADR-0024`). `option`
(13+3) is the index's width and extension in one value: `011` `lsl` and `111`
`sxtx` consume an `x` register, `010` `uxtw` and `110` `sxtw` consume a `w`, and
the assembler rejects the cross pairings, so the slot's `kind` follows the row.
`S` (12+1) is the scale: `0` is the unscaled index and `1` multiplies it by the
access size, which is 8 on these `size = 11` rows, so `lsl #0` versus `lsl #3` is
a `form_id` choice and never an operand value (`INV-02`). Both fields are
byte-affecting and neither is a payload, which is why the coarse
`aarch64:ldr/x64-base-regoff` is still not a form in any document (`N01b`, and
`N01p` binds it against `0.14.0`). There is no register-offset `ldur`, and no
writeback spelling: the assembler rejects both (`EXP-0026` §2).

The sixteen 32-bit rows are the same decision at `size = 10` (`ADR-0025`). The
templates' top bits change, `option` keeps the same keyword/width pairing, and
`S = 1` now means `#2`, so the suffixes are `-lsl2` … `-sxtx2` and `-lsl3` names
no row (`N01s`). Only `Rt` changes class: `dest`/`src` are `w32` while `base` and
the `x` index rows stay `x64`, which is why an `x64` destination is
`E-OPERAND-001` (`N02h`). A modifier carrying `lsl #2` is still `E-OPERAND-003`
(`N19c`): the scale is the `S` bit, and a modifier never writes one.

`EC-10` is out of v0. `EC-05` is frozen by `0.26.0`: the `SIB`-absolute row
carries the address, the `moffs` row is absent, and a value past the signed
field is `E-RANGE-001` rather than a switch to `A0`–`A3` (`ADR-0053`,
`N01bf`, `N03m`). `EC-09` is frozen by `0.5.0`: the three
`movaps` rows carry the family in the `form_id` (`/legacy`, `/vex`, `/evex`), so
`vex`/`evex` appear only in that table and a family the table lacks is still
`E-FORM-001` (`ADR-0030`).

`EC-37` is frozen by `0.8.0`: the `SIB` byte's three fields are one operand each
(`base`, `index`, and a two-bit scale carried as field content), the shape is the
`-base-index-` component of the `form_id`, and `index = 4` — the "no index"
encoding — is the one excluded value (`ADR-0035`, `N16i`, `N03c`, `EXP-0037`).
The scale's multiplier is never an operand value: `0…3` are the bits, and `8`
(the multiplier) is `E-RANGE-001` rather than a silently truncated `0`.

`EC-38` stays `frozen` in `0.10.0`, with the window as its carrier: reaching
`r8`–`r15` changes the instruction length in the legacy and VEX families, so the
`-base-ext` rows are forms, and no row may choose a prefix from an operand value
(`ADR-0037`, `EXP-0039`). `EC-40` is frozen by the same slice:
`placement.invert` is the only way a definition writes a complemented chunk, so
EVEX and VEX `B̄` are data rather than a rule in the materializer. The `xmm`
slot stays three bits, and `xmm8` on an SSE memory row is still
`E-OPERAND-004` (`N14e`).

`0.15.0` carries that same slot shape into memory, where `EC-39` finally has to
name three units instead of one (`ADR-0042`). Twelve rows repeat the six
`0.13.0` `xmm` memory shapes at `ymm` and `zmm`: the compressed load and store
(`-disp8x32`, `-disp8x64`), the four-byte displacement (`-disp32`) and the
no-displacement pair, each with a load and a store. Only `P2` changes between
the two widths (`28` vs `48`), every other byte and every placement is the
`0.13.0` one, and the base windows are unchanged: `%rsp`/`%r12` are excluded on
the displacement rows because `mod=01`/`10` still needs a SIB byte for them, and
`%rbp`/`%r13` join the exclusions on the no-displacement rows because `mod=00`
spends `r/m=101` on the RIP-relative escape (`EC-02`, `EC-35`). What is new is
that `N` is 32 and 64, and it is a property of the row: the plan's displacement
is the field content, `−128 … 127`, so `4064(%rax)` is content `127` at `ymm`
and `−4096` is `−128`, while `4096` and `28` are `disp32` rows because neither
is a multiple of 32. A single `disp8` slot with the unit derived at
materialization would have to read `P2` to find the divisor and would reject
`4064` as out of range; the unit lives in `target_type`, and naming `disp8x16`
on a `disp8x32` row is `E-OPERAND-001` (`N02p`, `N03e`, `EXP-0044`). VEX.256
memory stays out of `0.15.0` because it adds no contract fact — `vmovaps
32(%rax), %ymm0` is `c5 fc 28 40 20`, a plain unscaled `disp8` byte — so naming
`x86:vmovaps/ymm-base-disp8/vex` is `E-FORM-001` there (`N01al`).

`0.16.0` adds that coverage without adding a fact (`ADR-0043`). Twelve VEX.256
rows mirror the twelve VEX memory rows of `0.11.0`/`0.12.0` at `L = 1`: the
low-base window (`C5 FC`, three-bit base, `%rsp` excluded) and the high-base
window (`C4 C1 7C`, `B̄` at bit 13 inverted, `r8`–`r15` minus `%r12`), each with
the `disp8` pair, the `disp32` pair and the `mod = 00` pair. The vector slot is
the same four bits (`R̄` at 15 inverted plus `ModRM.reg` at 27 or 35), now
`x86.ymm`/`ymm`; `ymm8` with a low base is `c5 7c 28 00` and with base `r8` is
`c4 41 7c 28 00`. VEX has no compression, so the displacement payload is the
plain signed byte and needs no `disp8xN` name (`EC-02`, `EC-35`). A `zmm`
operand is `E-OPERAND-001` (`N02q`), `ymm16` is `E-OPERAND-004` (`N14s`),
`%rbp`/`%r12` are `E-RANGE-004` (`N16r`, `N16s`), and content `128` is
`E-RANGE-001` (`N03f`, `EXP-0045`).

`0.17.0` takes the same prefix and register-set facts into `mov` memory at 8 and
16 bits (`ADR-0044`). Four word rows (`66 8B /r` load, `66 89 /r` store) carry
a `r16` in `ModRM.reg` and a `disp8` or `disp32`; twelve byte rows split by
register set: `8A`/`88` for numbers 0–3, the same opcodes for `r8h` numbers 4–7
(`ah`–`bh`), and `40 8A`/`40 88` for numbers 4–7 behind a REX byte
(`spl`–`dil`). The `66` byte is part of the row template and precedes any REX
byte, so the displacement fields sit at 24 on the word and `40`-byte rows and
at 16 on the REX-less byte rows; no operand value chooses a width (`EC-36`).
The byte sets stay disjoint (`EC-28`), and every base remains the three-bit
window 0–7 minus `%rsp`, because a `SIB` byte or a `REX.B` would change the
length of a row whose template is fixed (`EC-02`, `EC-38`). `x86.gpr32` on a
word row is `E-OPERAND-001` (`N02r`), `x86.gpr8h` on a `-rex` row is
`E-OPERAND-001` (`N02s`), number 4 on the REX-less low row is `E-RANGE-004`
(`N16t`), `%rsp` is `E-RANGE-004` (`N16u`), content `128` on a `disp8` slot is
`E-RANGE-001` (`N03g`), base `8` is `E-OPERAND-004` (`N14t`), and the rows are
absent from `0.16.0` (`N01an`).

`0.18.0` reaches `r8`–`r15` on those rows (`ADR-0045`). The families diverge:
the word rows put `REX.B` at bit 8 (the `66` byte stays template byte 0) and
the REX-less low-byte rows at bit 0, so eight `-base-ext` rows appear and each
is one byte longer than its short counterpart; the four `40`-prefixed byte
rows already carry the `REX` byte, so they widen from three to four base bits
in place and their low-base bytes do not move. The byte axis is a partition:
the new rows carry numbers 0–3 and exclude 4–7, while the widened `40` rows
carry 4–7 — `movb %al, 8(%r8)` is `41 88 40 08` and `movb %spl, 8(%r8)` is
`41 88 60 08`, each on exactly one row. The high-byte rows stay at three bits
because `movb %ah, 8(%r8)` has no encoding: the `REX` byte renames `ah`.
Extension rows exclude `0`–`7` and `%r12`; the widened rows exclude `%rsp` and
`%r12`, since both force a `SIB` byte (`EC-35`). Base `0` on an extension row is
`E-RANGE-004` (`N16v`), `%r12` on either window is `E-RANGE-004` (`N16w`,
`N16x`), base `16` is `E-OPERAND-004` (`N14u`), `x86.gpr8h` on a `41` row is
`E-OPERAND-001` (`N02t`), and the rows are absent from `0.17.0` (`N01ao`,
`EXP-0047`).

`0.19.0` adds the two bases those rows deferred (`ADR-0046`). `%rsp` sets
`r/m = 100` and spends a `SIB` byte (`24`), and `%r12` spends the same byte plus
`REX.B`, so one row per `(family, direction, width, base)` appears with the base
fixed in the template — twenty-eight rows in all, the shape `0.3.0`/`0.7.0`
gave `movq`. The prefixes are template bytes, so `ModRM` and the displacement
move with them: the word `%rsp` rows keep `[19,3]`/`[32,…]`, the word `%r12`
rows read `[27,3]`/`[40,…]`, the REX-less byte `%rsp` rows `[11,3]`/`[24,…]`,
and every row whose template carries a `REX` byte `[19,3]`/`[32,…]`. The
register windows do not move: the low-byte rows still carry 0–3, the `40` rows
4–7, and the high-byte rows 4–7 with `%rsp` only, because `movb %ah, 8(%r12)`
has no encoding. Naming a row against `0.18.0` is `E-FORM-001` (`N01ap`), a
word operand on a byte row is two `E-OPERAND-001` (`N02u`), content `128` on a
`disp8` slot is `E-RANGE-001` (`N03h`), register `8` is `E-OPERAND-004`
(`N14v`), number `0` on a `40` row is `E-RANGE-004` (`N16y`), and the absent
high-byte `%r12` row is `E-FORM-001` (`N01aq`, `EXP-0048`).

The RV64 slice is eight forms across two documents, generated from the pinned UDB
nodes (ADR-0007, ADR-0009). Seven base-`I` forms are in `0.1.0`; `c.addi` joins
them in `0.2.0`, because it needs `rv64c` and the document's extension set is part
of its identity:

| `form_id` | Encoding | Operand signature | Table | Covers |
|---|---|---|---|---|
| `riscv:add/rd-rs1-rs2` | `ADD` R-type, `funct7=0`, `funct3=0` | dest `xreg`, src `xreg`, src2 `xreg` | `0.1.0` | `RV-P1` |
| `riscv:addi/rd-rs1-imm12` | `ADDI`, `funct3=0` | dest `xreg`, src `xreg`, imm `imm12` | `0.1.0` | `RV-P2` |
| `riscv:beq/rs1-rs2-imm12` | `BEQ` B-type, `funct3=0` | src `xreg`, src2 `xreg`, `imm12` target | `0.1.0` | `RV-P4`, `EC-22` |
| `riscv:jal/rd-imm20` | `JAL` J-type | dest `xreg`, `imm20` target | `0.1.0` | `RV-P5`, `EC-22` |
| `riscv:auipc/rd-imm20` | `AUIPC` U-type | dest `xreg`, `imm20` target | `0.1.0` | `RV-P8` (field half), `EC-21` (instruction half) |
| `riscv:ld/rd-base-imm12` | `LOAD` I-type, `funct3=011` | dest `xreg`, base `xreg`, disp `imm12` | `0.1.0` | `RV-P3` |
| `riscv:sd/rs-base-imm12` | `STORE` S-type, `funct3=011` | src `xreg`, base `xreg`, disp `imm12` | `0.1.0` | `RV-P3` |
| `riscv:c.addi/rd-imm6` | `C.ADDI` CI-format, 16-bit | dest `xreg` (`excl 0`), imm `imm6` (`excl 0`) | `0.2.0` | `RV-P7`, `EC-19`, `OD-14` |

The two memory forms decompose the address into `base` + `disp` rather than one
payload operand, and the addressing form is the `form_id` (ADR-0008, `OD-13`).
That is the same carrier `EC-02` names for x86's no-displacement/disp8/disp32
split, and it is what keeps an encoder from choosing `mod` from the
displacement's value.

`EC-19` is carried by `riscv:c.addi/rd-imm6`: `0.2.0` names the compressed form,
`0.1.0` does not, and a plan that asks for it against `0.1.0` is `E-FORM-001`
(`N01c`). Its `not: 0` is the `excluded` field of ADR-0009/`OD-14`; naming either
zero is `E-RANGE-004` (`N16a`, `N16b`), never a silent `c.nop`/HINT.

`EC-21` is now carried on its PC-relative side. The `auipc` form fixes the
instruction, `pcrel_hi20`/`pcrel_lo12` carry the transform, ADR-0010 pins the
psABI relation as `pc_reference_rule: pcrel_hi` plus a 1:N `pair_group`, and two
fixtures claim it — `RV-P8-pcrel-pair` on the record side and
`RV-P8-pcrel-pair-resolved` against a linked binary. What EC-21 still does not
decide is the *absolute* alternative `lui`+`addi`: no v0 form carries `lui`, so
the choice is embodied by which form the plan names and cannot yet be measured
against both sides. `EC-20` stays without a carrier because v0 has no 3-bit
compressed register field (`c.lw`-style CL/CS forms are not in either table); its
example is `c.lw`.

## Evidence

### Phase 1 (2026-11-03)

`docs/fmp-v0/90_boundary_audit.md` supplies observed counterexamples. "Observed"
means a built assembler produced both variants or refused to, and llvm-mc 23.1.2
agreed where it could express the case.

- `EC-01` — F-07: `add rax, 1` → `48 83 c0 01` in both XirAsm and llvm-mc; there
  is no way to request the `81 /0 id` form.
- `EC-02` — F-07: `mov rax, [rbp-8]` → `48 8b 45 f8` (disp8); `[rbp-200]` →
  disp32. Chosen implicitly in both tools.
- `EC-03` — F-04, F-06: XirAsm `jmp 0x10` → `eb 0e`, `jmp 0x1000` →
  `e9 fb 0f 00 00`. The same mnemonic changes size with the target value.
- `EC-04` — F-07: `add rax, 300` → `48 05 2c 01 00 00` (accumulator) in both
  tools; `81 /0 id` is equally legal and unreachable.
- `EC-16` — EXP-0001 §5: AArch64 `mov x13, #1` assembled to `movz` bytes
  (`2d 00 80 d2`) inside the macro layer.
- `EC-19` — F-11, `EXP-0012` §2: `addi a0, a0, 1` stays 4 bytes without `+c`; with
  `-mattr=+c` llvm-mc assembles the same line to `05 05`, and `c.addi a4, 5` is
  2 bytes only when written explicitly. The plan-side `form_id` is the carrier.
- `EC-20` — F-10, `EXP-0012` §2: `c.lw a6, 0(a0)` is rejected; `c.lw a2, 0(a0)`
  is `10 41`. The earlier example (`c.addi a6, 5`) was wrong: measured, `c.addi`
  accepts it as `15 08`, because its `xd` is a 5-bit field. The `x8..x15` rule is
  per form, not per `c.` prefix.

### Measured 2026-11-04 (llvm-mc 23.1.2)

Full run, method and caveats: `research/evidence/experiments/EXP-0003/`. Rerun
with `python exp0003.py`; the README table is regenerated by `--emit`.

Commands: `llvm-mc -triple=x86_64 -x86-asm-syntax=intel -show-encoding` for
assembly, `-disassemble` with a byte list for decoding, `-filetype=obj` plus
`llvm-objdump -d` for branch layout.

| Observation | Result |
|---|---|
| `mov rax, rbx` | `48 89 d8` |
| `mov eax, ebx` | `89 d8` |
| `48 8b c3` disassembles | `movq %rbx, %rax` |
| `48 89 d8` disassembles | `movq %rbx, %rax` |
| `0x40 0x89 0xd8` disassembles | `movl %ebx, %eax` |
| `add rax, 1` | `48 83 c0 01` |
| `add rax, 300` | `48 05 2c 01 00 00` |
| `48 81 c0 2c 01 00 00` disassembles | `addq $300, %rax` |
| `mov eax, 300` | `b8 2c 01 00 00` |
| `c7 c0 2c 01 00 00` disassembles | `movl $300, %eax` |
| `jmp .+0x81` | `eb 7f` (2 B) |
| `jmp .+0x82` | `e9 7d 00 00 00` (5 B) |
| `jmp .+0x1000` | `e9 fb 0f 00 00` |

Two oracle cautions found while collecting these:

- llvm-mc does not use a bare integer branch operand as an absolute target:
  `jmp 0x12`, `jmp 0x7f`, `jmp 0x80`, `jmp 0x1000` and `jmp 5` all emit
  `e9 00 00 00 00` under `-filetype=obj`. Only a label or a `.+N` expression
  reaches the encoder.
- `llvm-mc -disassemble` prints the branch *displacement*, not the resolved
  target (`eb 0e` prints as `jmp 14`). Branch target arithmetic therefore cannot
  be validated with the disassembler; the fixture must compare bytes and compute
  the target from the plan.

## Not choices

These are computed by the definition and MUST NOT be stored or requested:

- opcode bits, funct fields, and ModRM/RM field placement implied by the form;
- `REX.W` for a 64-bit x86 form;
- register number encoding from an operand's `target_type`;
- immediate bit placement implied by the form (including B-type/J-type scatter);
- the value of a fixup-covered field, which that fixup writes alone (OD-02);
- byte order, which comes from `target_identity.byte_order`;
- alignment and padding, which are `fill` fragments, not instruction properties.

If a proposed field merely restates one of these, it is over-freezing: it
duplicates rule knowledge into the plan and will drift.

## Validation obligation

The materializer performs exact checks; none of them compares a "choice set".

Plan side, in contract §13 order:

1. `form_id` resolves to exactly one definition row (`E-FORM-001`). No default,
   no variant inferred from operand values, no appending of a width suffix.
2. Operand signature matches the form's declared signature: count, role sequence,
   `kind`, `target_type` (`E-OPERAND-001`/`002`/`003`).
3. Operand values fit the form's declared ranges (`E-RANGE-001`/`002`/`003`).
4. Encoded length equals `expected_size` (`E-SIZE-001`).
5. If present, the hash of the emitted bytes equals `expected_digest`
   (`E-BYTE-001`).
6. Fixup fields are all present; nothing is defaulted. Each fixup has exactly one
   writer and one effect: `resolve_in_place` writes, `emit_relocation` zeroes
   and records (`E-FIXUP-*`, OD-02).

Definition side:

- The form table is keyed by `(form_id, operand signature, target_identity)` and
  maps to exactly one byte template. Ambiguity is unrepresentable, so there is no
  runtime branch that could choose.
- A wildcard or fallback row that can match more than one form is a definition
  defect (`E-DEF-001` at load time), not a plan error.

Test obligation per `EC` row:

- carrier is `none`: a test must show the variation cannot be requested — the
  plan cannot produce those bytes, and if a plan claims them via
  `expected_digest` the result is `E-BYTE-001`.
- carrier is a plan field: a test must show that removing or falsifying the
  carrier is rejected, not repaired.
- carrier is `form variant`: the negative test is `N01` (a coarse or absent form
  is `E-FORM-001`).

## Open work

The v0 `EC` set is decided (OD-10). What remains is per-row evidence:

- `EC-08`, `EC-10`, `EC-16`, `EC-18`, `EC-23`, `EC-24`,
  `EC-25`, `EC-26` are `draft` and need an observed counterexample before they can
  be frozen. None of them is required by the x86 slice. `EC-08`, `EC-10` and
  `EC-26` name `operand modifier` as the carrier for `addr_size`, `lock`/`rep` and
  `aq`/`rl`; ADR-0015 shows that in v0 a modifier is a guard that never writes a
  bit, so each of those rows still needs a decision about which of the two
  readings it is.
- The AArch64 rows now have a table (ADR-0005, ADR-0006, ADR-0011, ADR-0012):
  EC-11, EC-13, EC-15 and EC-17 are exercised by `definitions/aarch64/0.1.0.json`;
  EC-12 in both halves, `sh=0` in `0.1.0` and `sh=1` in `0.2.0`; EC-29 in `0.3.0`,
  which carries the condition as an operand rather than as sixteen forms; EC-14 in
  `0.4.0`, one row per addressing kind; EC-30 in `0.5.0`, one row per `movz` lane;
  EC-31 in `0.6.0`, one row per shift keyword with the amount as an `imm6`
  operand, and EC-32 in `0.7.0`, one row per extend keyword with the amount as an
  `imm3` operand whose domain is `0…4` minus a closed `excluded` tail.
  EC-16 (the `mov` alias family) stays `draft` and is not in the v0
  surface as a family: its `movz` and `movn` components now have rows
  (`0.5.0` and `0.17.0`), but `mov` itself picks the operation and lane from the
  literal's value, so no `mov` row exists. EC-18 stays `draft`; EC-30 decides the
  lane *inside* a move-wide row and does not decide which
  lowering a `mov` request becomes. EC-13 is now carried in both halves:
  shifted-register by `0.1.0` and `0.6.0`, extended-register by `0.7.0`. `0.8.0`
  adds the `sub` halves of EC-12 and EC-31 (ADR-0017), and `0.9.0` repeats them on
  the `S = 1` nodes for `adds`/`subs` (ADR-0018); `0.10.0` adds the twenty-four
  `w` rows (ADR-0019), `0.11.0` the extended-register `sub`/`adds`/`subs` rows
  (ADR-0020), and `0.12.0` the forty `cmp`/`cmn` aliases (ADR-0021). `0.13.0`
  completes the store `imm9` kinds (ADR-0022), `0.14.0` adds the literal load
  (ADR-0023), and `0.15.0` adds the sixteen register-offset rows (ADR-0024), so
  every load/store addressing kind the MRS drop carries now has a row. `0.16.0`
  repeats them at `size = 10` for the `w` width (ADR-0025), which changes the
  `S = 1` amount to `#2` and the destination class to `w32`; `0.17.0` adds the
  eight 64-bit `movk`/`movn` lanes (ADR-0026); the `b`/`h` widths, the
  signed/extended loads, the `mov` alias and the 32-bit move-wide lanes still
  have no row.
- The RV64 source is settled (ADR-0007: the UDB resolved spec, pinned by archive
  hash in `EXP-0009`), and both documents are generated: `definitions/rv64/0.1.0.json`
  and `0.2.0.json` (ADR-0009). `RV-P7` (`c.addi`) needed a format decision before
  it could land: the source forbids `imm = 0` and `xd = 0`, and `fmp-def/0.1`
  cannot express `not: 0` (§4 of `07_definition_format.md`); ADR-0009 added the
  closed `excluded` list instead of widening the schema.
