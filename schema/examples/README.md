# Schema examples

These are **illustrative** documents that show the shape of an FMP. They are not
fixtures: they claim no byte correctness and are not used by any test.

| File | Shows |
|---|---|
| `x86-mov-r64-r64.example.json` | Minimal plan: one section, one instruction, one symbol, no fixups |
| `aarch64-adrp-add.example.json` | Associated fixup pair (`adrp` + `:lo12:`) |
| `rv64-caddi.example.json` | Explicit compressed form with an encoding choice |

Rules for examples:

- Keep them schema-valid.
- Never copy them into `fixtures/`; fixtures need oracle bytes and metadata.
- If the schema changes, examples are updated in the same commit.
