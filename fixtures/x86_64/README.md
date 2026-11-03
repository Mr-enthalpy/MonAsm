# x86-64 fixtures

Vectors: `X86-P1` … `X86-P9` in `docs/fmp-v0/06_validation_matrix.md`.

## Positive vectors present

| ID | Fixture | Oracle |
|---|---|---|
| X86-P1 | `X86-P1-mov-r64-both-directions` | `EXP-0005` (`manual+disassembly` for the `8B /r` half) |
| X86-P2 | `X86-P2-add-imm8-and-imm32` | `EXP-0005` |
| X86-P3 | `X86-P3-two-legal-encodings` | `EXP-0005` (`81 /0` measured on `%rbx`; decode-verified on `%rax`) |
| X86-P7 | `X86-P7-short-and-near-branch` | `EXP-0005` |
| X86-P8 | `X86-P8-local-and-external-branch` | `EXP-0005`, record count from `llvm-readobj` |

`X86-P4` (displacement width), `X86-P5` (prefix rules) and `X86-P6`
(RIP-relative) are **deferred, not omitted**: all three need a memory-operand
form, which the seven-form v0 surface (`OD-10`) does not contain. The schema's
payload shapes (`01_contract.md` §8.1) would have to grow a `{mem: …}` shape
first. `X86-P9` is deferred with the extension families (`OD-10`).

## Negative fixtures present

| Vector | Fixture | Code |
|---|---|---|
| N01 | `negative/N01-absent-form` | `E-FORM-001` |
| N02 | `negative/N02-operand-kind-mismatch` | `E-OPERAND-001` |
| N03 | `negative/N03-imm8-out-of-range` | `E-RANGE-001` |
| N04 | `negative/N04a-rel8-out-of-range`, `N04b-rel32-absolute-out-of-range` | `E-RANGE-002`, `E-FIXUP-003` |
| N05 | `negative/N05-expected-size-mismatch` | `E-SIZE-001` |
| N07 | `negative/N07-fixup-partial-field` | `E-FIXUP-001` |
| N08 | `negative/N08-undeclared-symbol`, `N08b-resolve-undefined-symbol`, `N08c-absolute-pcrel-without-base` | `E-SYMBOL-001`, `E-FIXUP-002` |
| N09 | `negative/N09-overlapping-fragments` | `E-LAYOUT-001` |
| N10 | `negative/N10-definition-digest-mismatch` | `E-DEF-001` |
| N11 | `negative/N11-fragment-gap` | `E-LAYOUT-002` |
| N13 | `negative/N13-expected-digest-mismatch` | `E-BYTE-001` |
| N14 | `negative/N14-register-wider-than-field` | `E-OPERAND-004` |

`N06` (extension-gated form) and `N12` (relocation pair) have no x86 case in
v0: the slice has no extension-gated form and only single-site `rel32` fixups.
Both are recorded as not applicable in `06_validation_matrix.md`, not silently
skipped.

See `../README.md` for naming and oracle rules.
