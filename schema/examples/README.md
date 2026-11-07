# Schema examples

These files are **illustrative** documents that show the shape of an FMP. They
are not fixtures: they are not used by any test and make no byte-correctness
claim. Their names and digests are real, so a reader can compare them with the
shipped definitions, but a materializer run is not part of the example contract.

| File | Shows |
|---|---|
| `x86-mov-r64-r64.example.json` | Minimal Level 0 plan: one section, one instruction, no symbols, no fixups; carries the real x86-64 `0.1.0` digest from `07_definition_format.md` §8.1 |
| `aarch64-adrp-add.example.json` | Associated fixup pair (`adrp` + `:lo12:`) in a **Level 1** envelope (`artifact: sections`, `include_symbol_table: true`); uses the real `0.17.0` digest and the `A64-P6` shape |
| `rv64-caddi.example.json` | Explicit compressed form (`riscv:c.addi/rd-imm6`) in a Level 0 plan; uses the real `0.2.0` digest and the `RV-P7` shape |

Rules for examples:

- Keep them schema-valid.
- Never copy them into `fixtures/`; fixtures need oracle bytes and metadata.
- If the schema changes, examples are updated in the same commit.
- Use real form ids, operand kinds and definition digests. A placeholder digest
  teaches the wrong thing and hides a real lookup failure.
- `fmp/0.1` accepts **Level 0** and **Level 1**. The AArch64 example is Level 1
  (`artifact: sections` + the declared symbol table, `ADR-0096`); it shows the
  section/symbol envelope, while the materializer tests it through fixtures, not
  through this illustrative file.
- The RV64 example is Level 0 and is the only compressed-form example. It shows
  that the `c.*` mnemonic is named by `form_id`, never selected from the
  uncompressed spelling.
