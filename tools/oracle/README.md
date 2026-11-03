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

LLVM 23.1.2 is installed at `C:\Users\hanni\Tools\llvm\bin` and on the user
`PATH` (gate G0 passed). Wrappers are added per fixture in Phase 3.

Canonical invocation for the oracle records:

```bash
# x86-64: Intel operand order is explicit
llvm-mc -triple=x86_64 -x86-asm-syntax=intel -show-encoding

# AArch64
llvm-mc -triple=aarch64 -show-encoding

# RV64
llvm-mc -triple=riscv64 -show-encoding
```
