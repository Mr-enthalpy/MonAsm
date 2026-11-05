# ADR-0043: VEX.256 memory is coverage, not a new fact

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P20` (VEX.256 memory forms)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0042` §Consequences and `ADR-0041` §Consequences (the VEX.256
  memory rows they deferred)

## Context

`0.11.0` and `0.12.0` give the VEX family twelve memory rows at `xmm` width:
six with a low base (two-byte `C5 F8`) and six with a high base (three-byte `C4
C1 78`), each window carrying a `disp8` load/store pair, a `disp32` load/store
pair, and a no-displacement load/store pair. `ADR-0042` measured VEX.256 memory
while deciding the EVEX compressed unit and left the rows out on the ground that
they need no new contract fact: `vmovaps 32(%rax), %ymm0` is `c5 fc 28 40 20`,
a plain signed byte with no multiplication (`EXP-0044` §5). That is correct, but
it leaves a coverage gap: the width axis is complete for register-direct forms
and for EVEX memory, while VEX.256 memory cannot be named at all.

`EXP-0045` measures the full set on 2026-11-05 with `llvm-mc` 23.1.2; §1 of that
experiment records every line. The four facts that fix the shape are:

1. **The width is the `L` bit and nothing else.** The low-base twin of
   `c5 f8 28 40 00` is `c5 fc 28 40 00`; the high-base twin of `c4 c1 78 28 40
   00` is `c4 c1 7c 28 40 00`. No placement moves and no byte is added.
2. **VEX has no compressed displacement.** The displacement byte is the plain
   signed offset: `127` and `-128` are `7f` and `80`, and `128`/`-129` are
   `disp32` rows. There is no `disp8xN` slot and no `EC-39` involvement
   (`EC-02`, `EC-35`).
3. **The two base windows are the `0.11.0` windows.** The two-byte form has no
   `B̄`, so its base is the three low `ModRM.rm` bits with `%rsp` excluded
   (`[4]` on the displacement rows, `[4, 5]` on the no-displacement rows). The
   three-byte form carries `B̄` at bit 13 inverted and reaches `r8`–`r15`, with
   `%r12` excluded (`[0…7, 12]` on the displacement rows) and `%r12`/`%r13`
   excluded on the no-displacement rows (`[12, 13]`).
4. **The vector slot is the same four bits.** `R̄` at bit 15 inverted plus
   `ModRM.reg` at 27 (two-byte) or 35 (three-byte) reaches `ymm0`–`ymm15`;
   `ymm8` with a low base is `c5 7c 28 00`, and `ymm8` with base `r8` is
   `c4 41 7c 28 00`, carrying `R̄` and `B̄` together.

## Decision

**`0.16.0` adds twelve VEX.256 memory rows, mirroring the twelve VEX memory
rows of `0.11.0`/`0.12.0` at `L = 1`. It adds no `EC` row and revises none:
the unit, the base windows, the exclusions and the displacement carriers are
the facts those rows already state.**

The rows, in the order they are appended:

1. `x86:vmovaps/ymm-base-disp8/vex` (`c5fc284000`), dest `ymm`, `disp8` at
   `[32, 8]`, base `[24, 3]` excluding `4`.
2. `x86:vmovaps/ymm-base-disp32/vex` (`c5fc288000000000`), dest `ymm`,
   `disp32` at `[32, 32]`.
3. `x86:vmovaps/base-disp8-ymm/vex` (`c5fc294000`), src `ymm`, opcode `29`.
4. `x86:vmovaps/base-disp32-ymm/vex` (`c5fc298000000000`), src `ymm`.
5. `x86:vmovaps/ymm-base-ext-disp8/vex` (`c4c17c284000`), dest `ymm`, `B̄` at
   `13` inverted, base `[32, 3]` excluding `0…7` and `12`, `disp8` at `[40, 8]`.
6. `x86:vmovaps/ymm-base-ext-disp32/vex` (`c4c17c288000000000`), dest `ymm`.
7. `x86:vmovaps/base-ext-disp8-ymm/vex` (`c4c17c294000`), src `ymm`.
8. `x86:vmovaps/base-ext-disp32-ymm/vex` (`c4c17c298000000000`), src `ymm`.
9. `x86:vmovaps/ymm-base/vex` (`c5fc2800`), `mod=00`, base excluding `4, 5`.
10. `x86:vmovaps/base-ymm/vex` (`c5fc2900`), `mod=00`, opcode `29`.
11. `x86:vmovaps/ymm-base-ext/vex` (`c4c17c2800`), `mod=00`, base excluding
    `12, 13`.
12. `x86:vmovaps/base-ext-ymm/vex` (`c4c17c2900`), `mod=00`, opcode `29`.

The rows use the existing kinds `x86.ymm`/`ymm` and `x86.gpr64`/`rm64`; a `zmm`
operand on one of them is `E-OPERAND-001`, and `ymm16` is `E-OPERAND-004`,
because the VEX memory slot has four bits.

## Consequences

- `0.16.0` is a 103-form document with digest
  `sha256:64ea1acf467afb2f858a5cb2967839445a5ffecac164a5f1b61931cb8fb3b99e`.
- Its positive fixture `X86-P20-vex-ymm-memory` is twenty-four instructions and
  144 bytes: all twelve rows, the `disp8` ends at both windows, `disp32` at
  `128`/`-129`, `ymm8` with a low base, and base `r8` with `ymm8` so `B̄` and
  `R̄` carry in one instruction.
- `N01al` remains the `0.15.0` boundary for `x86:vmovaps/ymm-base-disp8/vex`;
  `N01am` is the same boundary for the three-byte
  `x86:vmovaps/ymm-base-ext-disp8/vex`. `N02q` (a `zmm` operand), `N14s`
  (`ymm16`), `N16r` (`%rbp` on a no-displacement row), `N16s` (`%r12` on an
  extended-base row) and `N03f` (content `128`) pin the new rows' other limits.
- No schema or Rust change. `target_type` and `kind` are opaque strings; the
  rows only add data.
- VEX.256 memory was the last item on the VEX width axis. The remaining x86
  widening is outside it: the 8/16-bit memory rows, a `SIB` base under the SSE
  opcodes, the SSE RIP-relative row, `mod = 00` for the GPR rows, the `0x67`
  prefix, and EVEX masking.

## Alternatives rejected

- **Leave the rows out because they add no contract fact.** Correct about the
  contract, wrong about coverage: a caller cannot express `vmovaps 32(%rax),
  %ymm0` at all, and the only alternative spelling reaches the register-direct
  row or no row. The absence is an `E-FORM-001` with no legal equivalent.
- **One memory row with a width operand.** Width is already the `L` bit the row
  pins (`ADR-0041`), and an operand that writes no bit is a choice at
  materialization time (`INV-02`). The 128-bit and 256-bit bytes differ only in
  that bit, but the plan must still name which one it wants.
- **One base row that accepts both base windows.** The two-byte VEX prefix has
  no `B̄` and the three-byte form adds a byte, so `r8` changes the instruction
  length; `EC-38` requires that change to be a form, not a prefix chosen from an
  operand value.
- **Reuse `disp8x32`.** VEX has no compression: content `1` is one byte, not 32
  (`EXP-0045` §2). Naming a compressed slot on a VEX row would make the
  materializer multiply a field the ISA does not multiply.
