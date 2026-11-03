# AArch64 fixtures

Vectors: `A64-P1` … `A64-P8` in `docs/fmp-v0/06_validation_matrix.md`.

Priority for v0:

1. `A64-P1` register arithmetic
2. `A64-P4` conditional branch
3. `A64-P6` `adrp` + `add :lo12:` associated fixup pair (AC-05)
4. `A64-P7` scaled/scattered field

Note: fixed 32-bit instruction width does not remove encoding choices — see
`EC-11` … `EC-18`.

See `../README.md` for naming and oracle rules.
