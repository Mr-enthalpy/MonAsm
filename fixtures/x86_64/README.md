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
| X86-P6 | `X86-P6-rip-relative` | `EXP-0005` + `EXP-0029`, record count from `llvm-readobj` |

`X86-P6` ships in `definitions/x86_64/0.2.0.json` as two forms with
`mod = 00`, `r/m = 101` and `disp32` as the last field (`ADR-0027`). `X86-P4`
(displacement width) and `X86-P5` (prefix rules) are **deferred, not omitted**:
both need a base+disp or prefixed memory-operand form, which the nine-form
surface (`OD-10`) does not contain. `X86-P4` also needs a SIB decision for
`%rsp`/`%r12`. `X86-P9` is deferred with the extension families (`OD-10`).

## Negative fixtures present

| Vector | Fixture | Code |
|---|---|---|
| N01 | `negative/N01-absent-form`, `negative/N01x-absent-riprel-form` | `E-FORM-001` |
| N02 | `negative/N02-operand-kind-mismatch`, `negative/N02j-base-on-riprel-form` | `E-OPERAND-001`, `E-OPERAND-002` |
| N03 | `negative/N03-imm8-out-of-range` | `E-RANGE-001` |
| N04 | `negative/N04a-rel8-out-of-range`, `N04b-rel32-absolute-out-of-range`, `N04e-riprel32-literal-out-of-range` | `E-RANGE-002`, `E-FIXUP-003` |
| N05 | `negative/N05-expected-size-mismatch` | `E-SIZE-001` |
| N07 | `negative/N07-fixup-partial-field`, `negative/N07b-riprel-operand-fixup-mismatch` | `E-FIXUP-001` |
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
