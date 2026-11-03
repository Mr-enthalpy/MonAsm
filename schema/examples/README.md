# Schema examples

These are **illustrative** documents that show the shape of an FMP. They are not
fixtures: they claim no byte correctness and are not used by any test.

| File | Shows |
|---|---|
| `x86-mov-r64-r64.example.json` | Minimal plan: one section, one instruction, no symbols, no fixups; carries the real x86-64 `0.1.0` definition digest |
| `aarch64-adrp-add.example.json` | Associated fixup pair (`adrp` + `:lo12:`) |
| `rv64-caddi.example.json` | Explicit compressed form with an encoding choice |

Rules for examples:

- Keep them schema-valid.
- Never copy them into `fixtures/`; fixtures need oracle bytes and metadata.
- If the schema changes, examples are updated in the same commit.
- The AArch64 and RV64 examples carry an all-zero digest because no definition
  exists for those targets yet (`OD-07`); they illustrate shape only and would be
  rejected `E-DEF-002` by the materializer. The x86 example names the pinned
  digest from `docs/fmp-v0/07_definition_format.md` §8.
