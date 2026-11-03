# RV64 fixtures

Vectors: `RV-P1` … `RV-P8` in `docs/fmp-v0/06_validation_matrix.md`. **No fixture
exists yet**: the source is pinned (ADR-0007) but `definitions/rv64/0.1.0.json`
has not been generated, so every `riscv:` form name is `E-FORM-001`.

Source and oracle: the UDB resolved-spec nodes named in
`tools/check_rv64_source.py` are the encoding source; `llvm-mc 23.1.2` with
`-triple=riscv64` is the oracle, and `c.*` needs `-mattr=+c`. The byte strings
in `research/evidence/experiments/EXP-0009-udb-resolved-spec.md` §6 are the
first fourteen vectors and can be reused as fixture expectations.

Priority for v0:

1. `RV-P4` B-type scattered immediate (`beq`)
2. `RV-P5` J-type scattered immediate (`jal`)
3. `RV-P1`/`P2`/`P3` `add`, `addi`, `ld`/`sd`
4. `RV-P8` `auipc` + `addi` pair with `%pcrel_hi` / `%pcrel_lo` semantics (AC-05)

`RV-P7` (`c.addi` vs `addi`, AC-04) is **blocked by a format decision**, not by
the source: `c.addi` requires `imm != 0` and `xd != 0`, and `fmp-def/0.1` cannot
express `not: 0` (ADR-0007 §Decision 5). Encoding those inputs would silently
produce `c.nop` or a HINT, which is a different instruction (`INV-02`,
`INV-07`). The row returns when the constraint has a field and an error code.

See `../README.md` for naming and oracle rules.
