# Oracle tools

Temporary. **Disposable zone** (ADR-0001): deleting this directory must not
break the product build.

## Purpose

Wrap independent authorities used to check our bytes:

- `llvm-mc` — primary oracle for x86-64, AArch64, RV64 encoding.
- `llvm-objdump` / `readelf` — relocation record checks.
- GNU `as` / `objdump` — secondary opinion when the first two agree and we want
  a third.

## Rules

- Oracles produce `*.expected.bin` and `*.oracle.json`; the materializer never
  produces expected data.
- Every record pins the exact version and command line.
- Nothing in `prototype/` may reference this directory.
- Scratch output goes to `out/` or `tmp/`, both gitignored.

## State

Empty. Blocked on gate G0 (toolchain installation). See `docs/STATUS.md`.
