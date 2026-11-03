# x86-64 fixtures

Vectors: `X86-P1` … `X86-P9` in `docs/fmp-v0/06_validation_matrix.md`.

Priority for v0:

1. `X86-P1` `mov r64, r64`
2. `X86-P3` and `X86-P7` explicit `imm8`/`imm32` and `rel8`/`rel32` pairs
3. `X86-P6` RIP-relative fixup
4. `X86-P8` external call fixup

See `../README.md` for naming and oracle rules.
