# x86-64 fixtures

Vectors: `X86-P1` … `X86-P18` in `docs/fmp-v0/06_validation_matrix.md`.

## Positive vectors present

| ID | Fixture | Oracle |
|---|---|---|
| X86-P1 | `X86-P1-mov-r64-both-directions` | `EXP-0005` (`manual+disassembly` for the `8B /r` half) |
| X86-P2 | `X86-P2-add-imm8-and-imm32` | `EXP-0005` |
| X86-P3 | `X86-P3-two-legal-encodings` | `EXP-0005` (`81 /0` measured on `%rbx`; decode-verified on `%rax`) |
| X86-P7 | `X86-P7-short-and-near-branch` | `EXP-0005` |
| X86-P8 | `X86-P8-local-and-external-branch` | `EXP-0005`, record count from `llvm-readobj` |
| X86-P6 | `X86-P6-rip-relative` | `EXP-0005` + `EXP-0029`, record count from `llvm-readobj` |
| X86-P4 | `X86-P4-base-disp` | `EXP-0005` + `EXP-0030` (`manual+disassembly` for the small-value `disp32`) |
| X86-P5 | `X86-P5-prefixes` | `EXP-0005` + `EXP-0031` (`manual+disassembly` for the 16-bit `8B` half) |
| X86-P9 | `X86-P9-sse-vex-evex` | `EXP-0005` + `EXP-0032` (`manual+disassembly` for the EVEX.128 row) |
| X86-P10 | `X86-P10-gpr-extended` | `EXP-0035` |
| X86-P11 | `X86-P11-base-extended` | `EXP-0036` |
| X86-P12 | `X86-P12-base-index-scale` | `EXP-0037` |
| X86-P13 | `X86-P13-sse-memory` | `EXP-0038` (`{evex}` forces the EVEX family) |
| X86-P14 | `X86-P14-sse-base-ext` | `EXP-0039` (`{evex}` forces the EVEX family) |
| X86-P15 | `X86-P15-sse-xmm-ext` | `EXP-0040` (`{evex}` forces the EVEX family) |
| X86-P16 | `X86-P16-sse-no-disp` | `EXP-0041` (`{evex}` forces the EVEX family) |
| X86-P17 | `X86-P17-sse-xmm16-31` | `EXP-0042` (the operand selects EVEX; no `{evex}` needed) |
| X86-P18 | `X86-P18-sse-ymm-zmm` | `EXP-0043` (`{evex}` forces the EVEX.256 row; `ymm`/`zmm` otherwise select the family) |

`X86-P6` ships in `definitions/x86_64/0.2.0.json` as two forms with
`mod = 00`, `r/m = 101` and `disp32` as the last field (`ADR-0027`). `X86-P4`
ships in `0.3.0` as eight forms, load/store × `disp8`/`disp32` ×
base-in-`r/m`/`%rsp`-fixed (`ADR-0028`). `X86-P5` ships in `0.4.0` as five
forms: two 16-bit directions whose template starts with `0x66`, the high-byte
row, and the low-byte pair split by a REX prefix (`ADR-0029`).
`X86-P9` ships in `0.5.0` as three `movaps` rows at `xmm` width, one per
encoding family: `/legacy` (`0f 28 /r`), two-byte `/vex` (`c5 f8 28 /r`) and
EVEX.128 `/evex` (`62 f1 7c 08 28 /r`), with the prefix as template and the
`ModRM` slots moving with it (`ADR-0030`). `X86-P10` ships in `0.6.0` as the
six 64-bit register-direct rows widened to a 4-bit `x86.gpr64` (`ADR-0033`),
`X86-P11` in `0.7.0` as the twelve base+disp rows at a 4-bit base plus four
fixed-base `%r12` rows (`ADR-0034`), `X86-P12` in `0.8.0` as four
`base + index*scale + disp` rows (`ADR-0035`), `X86-P13` in `0.9.0` as
twelve SSE memory rows across the three families, with the EVEX `disp8` as
compressed field content (`ADR-0036`), and `X86-P14` in `0.10.0` as the SSE
base window: the four EVEX rows widen in place and eight `-base-ext` rows carry
the legacy `REX` and three-byte-VEX reach, with `placement.invert` writing the
inverted `B̄` (`ADR-0037`). `X86-P15` ships in `0.11.0` as the register window:
the VEX and EVEX memory `xmm` slots and the EVEX register-direct pair widen in
place, three legacy `REX.R`/`REX.B` register rows and two VEX register rows join
(`C5 78 29` for a high source, `C4 41 78 28` for both high), and four legacy
memory rows carry a 4-bit `xmm` with a 4-bit base (`ADR-0038`). `X86-P16` ships
in `0.12.0` as the no-displacement shape: six legacy, four VEX and two EVEX rows
with `mod = 00` and no `disp` slot, because `0f 28 00` (three bytes) and
`0f 28 40 00` (four bytes, `disp8 = 0`) decode as the same instruction; `%rsp`/
`%r12` (a `SIB` byte) and `%rbp`/`%r13` (`r/m = 101` is RIP) stay outside and
name the `disp8` row with displacement `0` (`ADR-0039`). `X86-P17` ships in
`0.13.0` as the fifth EVEX register bit: the same seven EVEX rows get a 5-bit
`xmm` slot in place, with the inverted `R̄'` at bit 12 for `ModRM.reg` and the
inverted `X̄` at bit 14 for a register-direct `ModRM.rm`, so `vmovaps %xmm31,
%xmm30` is `62 01 7c 08 28 f7` with no new row and no length change (`ADR-0040`).
`X86-P18` ships in `0.14.0` as the other two widths: five register-direct rows —
three VEX.256 windows (`C5 FC 28`, `C5 7C 29` for a high source, `C4 41 7C 28` for
both high), one EVEX.256 row (`62 F1 7C 28 28`) and one EVEX.512 row
(`62 F1 7C 48 28`) — with `x86.ymm` and `x86.zmm` as distinct kinds (`ADR-0041`).

## Negative fixtures present

| Vector | Fixture | Code |
|---|---|---|
| N01 | `negative/N01-absent-form`, `negative/N01x-absent-riprel-form`, `negative/N01y-absent-basedisp-form`, `negative/N01z-absent-16bit-form`, `negative/N01aa-absent-unfamilied-vmovaps-form`, `negative/N01ab-vex-form-absent-in-0.4.0`, `negative/N01ac-absent-r12-base-form`, `negative/N01ad-absent-index-scale-form`, `negative/N01ae-absent-sse-memory-form`, `negative/N01af-absent-base-ext-row-on-0.9.0`, `negative/N01ag-absent-xmm-ext-row-on-0.10.0`, `negative/N01ah-absent-no-disp-row-on-0.11.0`, `negative/N01ai-absent-ymm-row-on-0.13.0`, `negative/N01aj-legacy-has-no-ymm-width` | `E-FORM-001` |
| N02 | `negative/N02-operand-kind-mismatch`, `negative/N02j-base-on-riprel-form`, `negative/N02k-high-byte-operand-on-rex-form`, `negative/N02l-zmm-operand-on-xmm-evex-form`, `negative/N02m-dest-on-store-row`, `negative/N02n-zmm-operand-on-ymm-row` | `E-OPERAND-001`, `E-OPERAND-002` |
| N03 | `negative/N03-imm8-out-of-range`, `negative/N03-disp8-out-of-range`, `negative/N03c-scale-is-field-content`, `negative/N03d-evex-disp8-content-out-of-range` | `E-RANGE-001` |
| N04 | `negative/N04a-rel8-out-of-range`, `N04b-rel32-absolute-out-of-range`, `N04e-riprel32-literal-out-of-range` | `E-RANGE-002`, `E-FIXUP-003` |
| N05 | `negative/N05-expected-size-mismatch` | `E-SIZE-001` |
| N06 | `negative/N06-extension-list-mismatch` | `E-TARGET-001` |
| N07 | `negative/N07-fixup-partial-field`, `negative/N07b-riprel-operand-fixup-mismatch` | `E-FIXUP-001` |
| N08 | `negative/N08-undeclared-symbol`, `N08b-resolve-undefined-symbol`, `N08c-absolute-pcrel-without-base` | `E-SYMBOL-001`, `E-FIXUP-002` |
| N09 | `negative/N09-overlapping-fragments` | `E-LAYOUT-001` |
| N10 | `negative/N10-definition-digest-mismatch` | `E-DEF-001` |
| N11 | `negative/N11-fragment-gap` | `E-LAYOUT-002` |
| N13 | `negative/N13-expected-digest-mismatch` | `E-BYTE-001` |
| N14 | `negative/N14-register-wider-than-field`, `negative/N14b-xmm8-wider-than-field`, `negative/N14c-extended-register-on-old-table`, `negative/N14d-register-16-on-extended-table`, `negative/N14e-xmm8-on-sse-memory-row`, `negative/N14f-base8-on-vex-row`, `negative/N14g-base8-on-evex-row`, `negative/N14h-base16-on-base-ext-row`, `negative/N14i-xmm16-wider-than-field`, `negative/N14j-xmm8-on-3bit-legacy-row`, `negative/N14k-xmm8-source-on-2byte-vex-row`, `negative/N14l-base16-on-no-disp-row`, `negative/N14m-xmm16-on-0.12.0-evex-row`, `negative/N14n-xmm32-on-5bit-evex-row`, `negative/N14o-xmm16-on-4bit-vex-row`, `negative/N14p-ymm16-on-4bit-vex-row`, `negative/N14q-zmm32-on-5bit-evex-row` | `E-OPERAND-004` |
| N16 | `negative/N16f-rsp-on-non-sib-form`, `negative/N16g-low-byte-number-four-without-rex`, `negative/N16h-r12-on-general-base-form`, `negative/N16i-index-rsp-excluded`, `negative/N16j-base-rsp-excluded`, `negative/N16k-low-base-on-base-ext-row`, `negative/N16l-r12-on-base-ext-row`, `negative/N16m-low-xmm-on-xmm-ext-row`, `negative/N16n-low-source-on-vex-src-ext-row`, `negative/N16o-rsp-on-no-disp-row`, `negative/N16p-rbp-on-no-disp-row`, `negative/N16q-low-base-on-no-disp-base-ext-row` | `E-RANGE-004` |

`N06` (extension-list mismatch) now has an x86 case: `0.5.0` declares
`avx`/`avx512f`/`avx512vl` for its EVEX.128 row, and a plan that omits them is
`E-TARGET-001`. `N12` (relocation pair) still has no x86 case in v0: the slice
has only single-site `rel32` fixups. It is recorded as not applicable in
`06_validation_matrix.md`, not silently skipped.

See `../README.md` for naming and oracle rules.
