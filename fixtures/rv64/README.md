# RV64 fixtures

Vectors: `RV-P1` … `RV-P8` in `docs/fmp-v0/06_validation_matrix.md`.

Priority for v0:

1. `RV-P7` `c.addi` vs `addi` as two explicit plans (AC-04)
2. `RV-P4` B-type scattered immediate
3. `RV-P5` J-type scattered immediate
4. `RV-P8` `auipc` + `addi` pair with `%pcrel_hi` / `%pcrel_lo` semantics (AC-05)

See `../README.md` for naming and oracle rules.
