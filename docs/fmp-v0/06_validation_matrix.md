# Validation Matrix

Status: **draft**. Fixtures and results are filled in Phases 3–4. This file is
the canonical registry for `N*`, `EXP-R*`, and `AC-*`.

## 1. Negative tests (`N*`)

Every negative test must produce a registry code, not a generic failure. Fixture
naming: `fixtures/<isa>/negative/N0X-<slug>.fmp.json`.

| ID | Input condition | Expected | Code | ISAs | Fixture | Status |
|---|---|---|---|---|---|---|
| N01 | Plan names a form that leaves a byte-affecting decision open (`x86:mov/r64-r64`, `x86:add/rm64-imm`), a form missing a required component (`x86:mov/rm-r64` without `/legacy`), a renamed variant, or names a variant the definition does not contain | Reject, never append a default variant or match a near neighbour | E-FORM-001 | x86, aarch64, rv64 | `x86_64/negative/N01-absent-form.fmp.json`, `x86_64/negative/N01x-absent-riprel-form.fmp.json`, `x86_64/negative/N01y-absent-basedisp-form.fmp.json`, `x86_64/negative/N01ac-absent-r12-base-form.fmp.json`, `x86_64/negative/N01ad-absent-index-scale-form.fmp.json`, `x86_64/negative/N01ae-absent-sse-memory-form.fmp.json`, `x86_64/negative/N01af-absent-base-ext-row-on-0.9.0.fmp.json`, `x86_64/negative/N01ag-absent-xmm-ext-row-on-0.10.0.fmp.json`, `x86_64/negative/N01ah-absent-no-disp-row-on-0.11.0.fmp.json`, `x86_64/negative/N01ai-absent-ymm-row-on-0.13.0.fmp.json`, `x86_64/negative/N01aj-legacy-has-no-ymm-width.fmp.json`, `x86_64/negative/N01ak-absent-ymm-memory-row-on-0.14.0.fmp.json`, `x86_64/negative/N01al-absent-vex256-memory-row.fmp.json`, `x86_64/negative/N01am-absent-vex256-base-ext-row-on-0.15.0.fmp.json`, `x86_64/negative/N01an-absent-mov-memory-r16-row-on-0.16.0.fmp.json`, `x86_64/negative/N01ao-absent-mov-memory-base-ext-row-on-0.17.0.fmp.json`, `x86_64/negative/N01ap-absent-mov-memory-sib-row-on-0.18.0.fmp.json`, `x86_64/negative/N01aq-absent-high-byte-r12-row.fmp.json`, `x86_64/negative/N01ar-absent-sse-mem-sib-row-on-0.19.0.fmp.json`, `x86_64/negative/N01as-absent-no-displacement-sse-mem-sib-row.fmp.json`, `x86_64/negative/N01at-absent-evex-mem-sib-row-on-0.20.0.fmp.json`, `x86_64/negative/N01au-absent-no-displacement-evex-mem-sib-row.fmp.json`, `x86_64/negative/N01av-absent-evex-mem-sib-nodisp-row-on-0.21.0.fmp.json`, `x86_64/negative/N01aw-absent-rbp-no-displacement-evex-row.fmp.json`, `aarch64/negative/N01-absent-scaled-form.fmp.json`, `aarch64/negative/N01d-absent-movz-lane.fmp.json`, `aarch64/negative/N01e-absent-extend-form.fmp.json`, `aarch64/negative/N01f-absent-sub-ext.fmp.json`, `aarch64/negative/N01g-absent-flag-form.fmp.json`, `aarch64/negative/N01h-absent-32bit-form.fmp.json`, `aarch64/negative/N01i-absent-cmp-alias.fmp.json`, `aarch64/negative/N01j-absent-flag-32bit-form.fmp.json`, `aarch64/negative/N01k-absent-w-form.fmp.json`, `aarch64/negative/N01l-absent-32bit-ext-form.fmp.json`, `aarch64/negative/N01m-absent-cmn-alias.fmp.json`, `aarch64/negative/N01n-absent-store-imm9-form.fmp.json`, `aarch64/negative/N01o-absent-loadlit-form.fmp.json`, `aarch64/negative/N01p-regoff-absent-in-previous-version.fmp.json`, `aarch64/negative/N01q-absent-regoff-shift-one.fmp.json`, `aarch64/negative/N01r-w32-regoff-absent-in-previous-version.fmp.json`, `aarch64/negative/N01s-absent-w32-regoff-shift-three.fmp.json`, `aarch64/negative/N01t-absent-movk-lsl8.fmp.json`, `aarch64/negative/N01u-movk-absent-in-previous-version.fmp.json`, `aarch64/negative/N01v-absent-w32-movk-lane.fmp.json`, `aarch64/negative/N01w-absent-mov-alias.fmp.json`, `rv64/negative/N01c-caddi-against-0.1.0.fmp.json` | x86, aarch64 and rv64 passing (`N01x` is the `0.1.0` boundary for the `0.2.0` RIP-relative rows, `N01y` is the `0.2.0` boundary for the `0.3.0` base+disp rows, `N01ac` is the `0.6.0` boundary for the `0.7.0` `%r12` rows, `N01i`/`N01m` are `0.11.0` version boundaries now that `0.12.0` carries the ids, `N01n` is the `0.12.0` boundary for the `0.13.0` store rows, `N01o` is the `0.13.0` boundary for the `0.14.0` literal row, `N01p` is the `0.14.0` boundary for the `0.15.0` register-offset rows, `N01q` names a `-lsl1` row that no version has, `N01r` is the `0.15.0` boundary for the `0.16.0` 32-bit rows, `N01s` names a `-lsl3` row that no version has at that width, `N01t` names a `-lsl8` move-wide lane that no version has, `N01u` is the `0.16.0` boundary for the `0.17.0` `movk` rows, `N01v` names a `w32` move-wide lane that no version has, `N01w` names a `mov` alias row that no version has, `N01ad` is the `0.7.0` boundary for the `0.8.0` index/scale rows, `N01ae` is the `0.8.0` boundary for the `0.9.0` SSE memory rows, `N01af` is the `0.9.0` boundary for the `0.10.0` `-base-ext` rows, `N01ag` is the `0.10.0` boundary for the `0.11.0` register rows, and `N01ah` is the `0.11.0` boundary for the `0.12.0` no-displacement rows, `N01ai` is the `0.13.0` boundary for the `0.14.0` `ymm`/`zmm` rows, `N01aj` names a legacy `ymm` row that no version has, `N01ak` is the `0.14.0` boundary for the `0.15.0` EVEX memory rows, and `N01al` names a VEX.256 memory row that no version has, `N01an` is the `0.16.0` boundary for the `0.17.0` 8/16-bit memory rows, `N01ao` is the `0.17.0` boundary for the `0.18.0` `-base-ext` rows, `N01ap` is the `0.18.0` boundary for the `0.19.0` fixed-base `SIB` rows, and `N01aq` names a high-byte `%r12` row that no encoding has, `N01ar` is the `0.19.0` boundary for the `0.20.0` SSE `SIB` rows, `N01as` names a no-displacement SSE `SIB` shape that no version has, `N01at` is the `0.20.0` boundary for the `0.21.0` EVEX `SIB` rows, and `N01au` names a `mod = 00` EVEX `SIB` shape that no version has, `N01av` is the `0.21.0` boundary for the `0.22.0` no-displacement EVEX rows, and `N01aw` names a `%rbp` no-displacement EVEX row that no encoding has) |
| N02 | Operand register class does not match the form, or the operand count/role sequence does | Reject; never add, drop or reorder an operand | E-OPERAND-001 / E-OPERAND-002 | x86, aarch64, rv64 | `x86_64/negative/N02-operand-kind-mismatch.fmp.json`, `x86_64/negative/N02j-base-on-riprel-form.fmp.json`, `x86_64/negative/N02m-dest-on-store-row.fmp.json`, `x86_64/negative/N02n-zmm-operand-on-ymm-row.fmp.json`, `x86_64/negative/N02o-zmm-operand-on-ymm-memory-row.fmp.json`, `x86_64/negative/N02p-disp8x16-unit-on-disp8x32-row.fmp.json`, `x86_64/negative/N02q-zmm-operand-on-vex256-memory-row.fmp.json`, `x86_64/negative/N02r-gpr32-operand-on-mov-memory-r16-row.fmp.json`, `x86_64/negative/N02s-r8h-operand-on-mov-memory-rex-row.fmp.json`, `x86_64/negative/N02t-r8h-operand-on-mov-memory-base-ext-row.fmp.json`, `x86_64/negative/N02u-gpr16-operand-on-mov-memory-sib-row.fmp.json`, `x86_64/negative/N02v-gpr64-operand-on-sse-mem-sib-row.fmp.json`, `x86_64/negative/N02w-extra-base-operand-on-fixed-base-row.fmp.json`, `x86_64/negative/N02x-gpr64-operand-on-evex-mem-sib-row.fmp.json`, `x86_64/negative/N02y-extra-base-operand-on-fixed-base-row.fmp.json`, `x86_64/negative/N02z-gpr64-operand-on-evex-mem-sib-nodisp-row.fmp.json`, `x86_64/negative/N02aa-extra-disp-operand-on-fixed-base-row.fmp.json`, `aarch64/negative/N02b-w-source-in-shift-form.fmp.json`, `aarch64/negative/N02c-x-dest-on-w-row.fmp.json`, `aarch64/negative/N02d-ext-x-source-on-w-keyword.fmp.json`, `aarch64/negative/N02e-dest-on-cmp-row.fmp.json`, `aarch64/negative/N02f-w-index-on-lsl-row.fmp.json`, `aarch64/negative/N02g-w-index-on-w32-lsl-row.fmp.json`, `aarch64/negative/N02h-x-dest-on-w32-row.fmp.json`, `aarch64/negative/N02i-w-dest-on-movk-row.fmp.json` | x86 and aarch64 passing (`N02j` is a `base` operand added to the two-slot RIP-relative row: count mismatch, `expected: 2`, `found: 3`; `N02e` is the count mismatch: `expected: 2`, `found: 3`; `N02f` is a `w32` index on a `-lsl0` row: two `E-OPERAND-001`, on `kind` and `target_type`; `N02g`/`N02h` are the same two errors at `size = 10`, on the `index` and on the `dest`; `N02i` is a `w32` destination on a 64-bit move-wide row: the same two errors on the `dest`; `N02m` is a `dest` on a store row: the role sequence is `src, base, disp`, so the mismatch is one `E-OPERAND-002`; `N02n` passes a `zmm` operand to a `ymm` row: two `E-OPERAND-001`, on `kind` and `target_type`, because width is part of the kind; `N02o` is the same mismatch on a memory row; `N02p` is a `disp8x16` displacement on a `disp8x32` row: one `E-OPERAND-001` on the `disp`'s `target_type`, because the unit is the row's; `N02q` is the same width mismatch on a VEX.256 memory row, `N02r` is a `gpr32` operand on a `0.17.0` word-memory row: the same two `E-OPERAND-001` on `kind` and `target_type`, and `N02s` is an `x86.gpr8h` operand on the REX row, because a REX prefix re-labels numbers 4–7; `N02t` is the same high-byte operand on a `0.18.0` `41` extension row, where number 4 is `spl` and the row's own set is 0–3, so it adds one `E-RANGE-004` on the `dest`; `N02u` passes a `x86.gpr16` operand to a `0.19.0` byte `SIB` row: two `E-OPERAND-001`, on `kind` and `target_type`, `N02v` passes a `x86.gpr64` operand to a `0.20.0` `xmm` `SIB` row: the same two errors, and `N02w` adds a third `base` operand to a fixed-base row, where the base lives in the template: one `E-OPERAND-002`, `expected: 2`, `found: 3`, `N02x` is the same `gpr64`-on-`xmm` mismatch on a `0.21.0` EVEX `SIB` row, and `N02y` is the same extra-`base` mismatch there, `N02z` is the same `gpr64`-on-`xmm` mismatch on a `0.22.0` no-displacement EVEX row, and `N02aa` supplies a `disp` operand to a row that has no `disp` slot: one `E-OPERAND-002`, `expected: 1`, `found: 2`) |
| N03 | Immediate exceeds the field's range | Reject | E-RANGE-001 | x86, aarch64, rv64 | `x86_64/negative/N03-imm8-out-of-range.fmp.json`, `x86_64/negative/N03-disp8-out-of-range.fmp.json`, `x86_64/negative/N03c-scale-is-field-content.fmp.json`, `x86_64/negative/N03d-evex-disp8-content-out-of-range.fmp.json`, `x86_64/negative/N03e-disp8x32-content-out-of-range.fmp.json`, `x86_64/negative/N03f-disp8-content-out-of-range-vex256.fmp.json`, `x86_64/negative/N03g-disp8-content-out-of-range-mov-memory.fmp.json`, `x86_64/negative/N03h-disp8-content-out-of-range-mov-memory-sib.fmp.json`, `x86_64/negative/N03i-disp8-content-out-of-range-sse-mem-sib.fmp.json`, `x86_64/negative/N03j-disp8x16-content-out-of-range-evex-mem-sib.fmp.json`, `aarch64/negative/N03-imm12-out-of-range.fmp.json`, `aarch64/negative/N03-cond-out-of-range.fmp.json`, `aarch64/negative/N03-imm6-out-of-range.fmp.json`, `aarch64/negative/N03-imm3-out-of-range.fmp.json`, `aarch64/negative/N03-imm12-disp-out-of-range.fmp.json`, `aarch64/negative/N03-imm9-disp-out-of-range.fmp.json`, `aarch64/negative/N03-str-imm9-post-disp-out-of-range.fmp.json`, `aarch64/negative/N03-stur-imm9-disp-out-of-range.fmp.json`, `aarch64/negative/N03-movk-imm16-out-of-range.fmp.json` | x86 and aarch64 passing (`N03-disp8` is `disp8 = 128`, one past the measured `[-128, 127]`, on a `disp8` form: it is not re-formed as `disp32`; `N03c` is the SIB scale's multiplier `8` against the two-bit field content `0…3`; `N03d` is the EVEX `disp8x16` content `128`, one past the signed-8 field; `N03e` is the same content on a `disp8x32` row, which proves the unit is not part of the range; `N03f` is content `128` on a VEX `disp8` row, a plain byte with no unit, and `N03g` is the same content `128` on a `0.17.0` 8-bit `disp8` row, and `N03h` is the same content on a `0.19.0` `SIB` row, and `N03i` the same content on a `0.20.0` SSE `SIB` row, so the `SIB` does not move the field end, and `N03j` is the same content on a `0.21.0` EVEX `SIB` row, where the `disp8x16` field is still a signed byte) |
| N04 | Control-transfer or literal displacement exceeds the form's range | Reject, never expand or re-form | E-RANGE-002 / E-FIXUP-003 | x86, aarch64, rv64 | `x86_64/negative/N04a-rel8-out-of-range.fmp.json`, `N04b-rel32-absolute-out-of-range.fmp.json`, `x86_64/negative/N04e-riprel32-literal-out-of-range.fmp.json`, `aarch64/negative/N04c-bcond-imm19-out-of-range.fmp.json`, `aarch64/negative/N04d-loadlit-imm19-out-of-range.fmp.json` | x86 and aarch64 passing (`N04e` is `disp32 = 2147483648`, one past the measured `[-2147483648, 2147483647]`) |
| N05 | `expected_size` disagrees with the encoded length | Reject | E-SIZE-001 / E-LAYOUT-003 | x86, aarch64, rv64 | `x86_64/negative/N05-expected-size-mismatch.fmp.json` | x86 passing |
| N06 | The plan's target identity does not match the definition it names, including an `enabled_extensions` set that omits what the definition's forms need | Reject | E-TARGET-001 / E-TARGET-003 | rv64 (C), x86 (AVX-512), aarch64 (optional feature) | `x86_64/negative/N06-extension-list-mismatch.fmp.json`, `rv64/negative/N06-extension-list-mismatch.fmp.json` | x86 and rv64 passing (`E-TARGET-001`: `0.5.0` declares `avx`/`avx512f`/`avx512vl` for its EVEX row and a plan that omits them is rejected; `rv64/0.2.0.json` declares `rv64i`/`rv64c` and a plan that names only `rv64i` is rejected); aarch64 has no non-empty set to mismatch in v0; `E-TARGET-003` stays unreachable because no row carries its own requirement (`04_errors.md` §2.3) |
| N07 | Fixup kind is incompatible with the field | Reject | E-FIXUP-001 | x86, aarch64, rv64 | `x86_64/negative/N07-fixup-partial-field.fmp.json`, `x86_64/negative/N07b-riprel-operand-fixup-mismatch.fmp.json` | x86 passing (`N07b`: the operand names `S1`, the fixup targets `S2`) |
| N08 | Reference names a `symbol_id` absent from `symbols[]`; or `resolve_in_place` is asked to patch a symbol that exists but has no address | Reject the identity error in every mode; reject only the mode that needs an address | E-SYMBOL-001 / E-FIXUP-002 | x86, aarch64, rv64 | `x86_64/negative/N08-undeclared-symbol.fmp.json`, `N08b-resolve-undefined-symbol.fmp.json`, `N08c-absolute-pcrel-without-base.fmp.json` | x86 passing |
| N09 | Two layout fragments overlap | Reject | E-LAYOUT-001 | all (layout is ISA-independent) | `x86_64/negative/N09-overlapping-fragments.fmp.json` | x86 passing |
| N10 | Definition digest does not match | Reject | E-DEF-001 | all | `x86_64/negative/N10-definition-digest-mismatch.fmp.json` | x86 passing |
| N11 | Plan implies implicit alignment or padding | Reject | E-LAYOUT-002 / E-LAYOUT-005 | all | `x86_64/negative/N11-fragment-gap.fmp.json` | x86 passing (`E-LAYOUT-002`; `E-LAYOUT-005` unreachable in v0, `04_errors.md` §2.3) |
| N12 | Associated relocation pair is incomplete or inconsistent: no `hi`, more than one `hi`, no `lo`, a target mismatch, or a `pair_role` with no `pair_group` | Reject | E-FIXUP-007 | aarch64 (`adrp`+`lo12`), rv64 (`auipc`+`lo12`) | `aarch64/negative/N12a-pair-without-lo.fmp.json` | aarch64 passing (two `hi`, no `lo`); not applicable to x86 v0 (single-site `rel32`) |
| N13 | `expected_digest` is present and the emitted bytes hash to a different value | Reject, never re-encode to match | E-BYTE-001 | x86, aarch64, rv64 | `x86_64/negative/N13-expected-digest-mismatch.fmp.json` | x86 passing |
| N14 | Operand value does not fit the slot's encoded field: `r9` in a 3-bit `ModRM` field, `x32` in a 5-bit AArch64 register field, `xmm8` in a 3-bit `xmm` field, `r8` against the 3-bit `0.5.0` table, `r8` against a 3-bit SSE memory base, `r16` against the 4-bit `0.6.0` table, or `r16` against the 4-bit `0.10.0` SSE base window, or `xmm16` against the 4-bit `0.11.0` register window, or `r16` against the 4-bit `0.12.0` no-displacement base field, or `xmm16` on a `0.12.0` 4-bit EVEX row, or `xmm32` against a 5-bit `0.13.0` EVEX field, or `xmm16` on a 4-bit `0.13.0` VEX row, or `ymm16` on a 4-bit VEX row, or `zmm32` against a 5-bit EVEX field, or `ymm32` on a 5-bit EVEX memory row, or base `8` on the 3-bit `0.17.0` 8/16-bit memory window, or base `16` on the 4-bit `0.18.0` memory base window, or register `8` on a 3-bit `0.19.0` `SIB` row | Reject, never truncate to another register | E-OPERAND-004 | x86, aarch64 | `x86_64/negative/N14-register-wider-than-field.fmp.json`, `x86_64/negative/N14b-xmm8-wider-than-field.fmp.json`, `x86_64/negative/N14c-extended-register-on-old-table.fmp.json`, `x86_64/negative/N14d-register-16-on-extended-table.fmp.json`, `x86_64/negative/N14e-xmm8-on-sse-memory-row.fmp.json`, `x86_64/negative/N14f-base8-on-vex-row.fmp.json`, `x86_64/negative/N14g-base8-on-evex-row.fmp.json`, `x86_64/negative/N14h-base16-on-base-ext-row.fmp.json`, `x86_64/negative/N14i-xmm16-wider-than-field.fmp.json`, `x86_64/negative/N14j-xmm8-on-3bit-legacy-row.fmp.json`, `x86_64/negative/N14k-xmm8-source-on-2byte-vex-row.fmp.json`, `x86_64/negative/N14l-base16-on-no-disp-row.fmp.json`, `x86_64/negative/N14m-xmm16-on-0.12.0-evex-row.fmp.json`, `x86_64/negative/N14n-xmm32-on-5bit-evex-row.fmp.json`, `x86_64/negative/N14o-xmm16-on-4bit-vex-row.fmp.json`, `x86_64/negative/N14p-ymm16-on-4bit-vex-row.fmp.json`, `x86_64/negative/N14q-zmm32-on-5bit-evex-row.fmp.json`, `x86_64/negative/N14r-ymm32-on-5bit-evex-memory-row.fmp.json`, `x86_64/negative/N14s-ymm16-on-4bit-vex256-memory-row.fmp.json`, `x86_64/negative/N14t-base8-on-3bit-mov-memory-row.fmp.json`, `x86_64/negative/N14u-base16-on-4bit-mov-memory-base-row.fmp.json`, `x86_64/negative/N14v-register8-on-mov-memory-sib-row.fmp.json`, `x86_64/negative/N14w-register8-on-legacy-sse-mem-sib-row.fmp.json`, `x86_64/negative/N14x-register32-on-evex-mem-sib-row.fmp.json`, `x86_64/negative/N14y-register32-on-evex-mem-sib-nodisp-row.fmp.json`, `aarch64/negative/N14-register-wider-than-field.fmp.json` | x86 and aarch64 passing (`N14b` is the `xmm8` field end on the `0.5.0` SSE/EVEX rows; `N14c` is the version boundary: `field_bits = 3` for a GPR on `0.5.0`; `N14d` is the field end: `field_bits = 4` on `0.6.0`; `N14e`/`N14f`/`N14g` are the 3-bit SSE memory slots: `xmm8` on the register field, `r8` on the VEX base and `r8` on the EVEX base, all `field_bits = 3`; `N14h` is the 4-bit `0.10.0` base window: `r16` is `field_bits = 4`; `N14i` is the 4-bit `0.11.0` register window (`xmm16`), `N14j` is `xmm8` on the 3-bit legacy register-direct row, `N14k` is a high source on the two-byte VEX row, `N14l` is `r16` on a `0.12.0` 4-bit no-displacement base, `N14m` is `xmm16` on a `0.12.0` 4-bit EVEX row (the version boundary), `N14n` is `xmm32` at the 5-bit `0.13.0` field end, and `N14o` is `xmm16` on a `0.13.0` 4-bit VEX row (the family boundary), `N14p` is `ymm16` on the same 4-bit VEX window at 256-bit width, and `N14q` is `zmm32` at the 5-bit `0.14.0` EVEX field end, with `N14r` the same field end on a `0.15.0` EVEX memory row, and `N14s` is `ymm16` beyond the four-bit VEX.256 memory slot, `N14t` is base `8` on the three-bit `0.17.0` 8/16-bit memory window, the deferred `-base-ext` case, `N14u` is base `16` on the four-bit `0.18.0` window, `N14v` is register `8` on the three-bit byte slot of a `0.19.0` `SIB` row, and `N14w` is `xmm8` on the three-bit register slot of a `0.20.0` legacy SSE `SIB` row, where the sibling VEX row would accept it, and `N14x` is register `32` at the five-bit EVEX field end of a `0.21.0` `SIB` row, and `N14y` is register `32` at the same field end of a `0.22.0` no-displacement row) |
| N15 | Operand payload is a composite memory operand (`{"mem": {"base": …, "disp": …}}`), not one of the four `fmp/0.1` shapes | Reject at read time, never split it into operands | E-OPERAND-003 | all | `rv64/negative/N15-composite-memory-payload.fmp.json` | rv64 passing |
| N16 | Operand value is inside the slot's field range but excluded by the form (`c.addi` zero immediate, `c.addi` zero destination, the extended-register `imm3` values `5`–`7`, the 32-bit `imm6` values `32`–`63`, `%rsp` as a base on a non-SIB row, `%rsp` as an SSE memory base, `%r12` as a base on a non-SIB row, a low base or `%r12` on an SSE `-base-ext` row, a low `xmm` on an SSE register-extension row, `%rsp` or `%rbp` as a base on a no-displacement row, a low base on a legacy no-displacement high-base row, `%rsp` on a general EVEX no-displacement row, `%rsp` as a SIB index, which is the "no index" encoding, number 4–7 on a REX-less `0.17.0` byte-memory row, `%rsp` as a base on a `0.17.0` memory row, a low base or `%r12` on a `0.18.0` `-base-ext` row, `%r12` on a widened `40` row, a low-byte number on a `0.19.0` `40` `SIB` row) | Reject, never encode the HINT or the unallocated word the bytes would mean | E-RANGE-004 | x86, rv64, aarch64 | `rv64/negative/N16a-caddi-imm-zero.fmp.json`, `rv64/negative/N16b-caddi-rd-zero.fmp.json`, `x86_64/negative/N16f-rsp-on-non-sib-form.fmp.json`, `x86_64/negative/N16h-r12-on-general-base-form.fmp.json`, `x86_64/negative/N16i-index-rsp-excluded.fmp.json`, `x86_64/negative/N16j-base-rsp-excluded.fmp.json`, `x86_64/negative/N16k-low-base-on-base-ext-row.fmp.json`, `x86_64/negative/N16l-r12-on-base-ext-row.fmp.json`, `x86_64/negative/N16m-low-xmm-on-xmm-ext-row.fmp.json`, `x86_64/negative/N16n-low-source-on-vex-src-ext-row.fmp.json`, `x86_64/negative/N16o-rsp-on-no-disp-row.fmp.json`, `x86_64/negative/N16p-rbp-on-no-disp-row.fmp.json`, `x86_64/negative/N16q-low-base-on-no-disp-base-ext-row.fmp.json`, `x86_64/negative/N16r-rbp-on-vex256-no-disp-row.fmp.json`, `x86_64/negative/N16s-r12-on-vex256-base-ext-row.fmp.json`, `x86_64/negative/N16t-high-byte-number-on-rexless-mov-memory-row.fmp.json`, `x86_64/negative/N16u-rsp-on-mov-memory-r16-row.fmp.json`, `x86_64/negative/N16v-low-base-on-mov-memory-base-ext-row.fmp.json`, `x86_64/negative/N16w-r12-on-mov-memory-base-ext-row.fmp.json`, `x86_64/negative/N16x-r12-on-widened-mov-memory-rex-row.fmp.json`, `x86_64/negative/N16y-low-byte-number-on-mov-memory-sib-rex-row.fmp.json`, `x86_64/negative/N16z-rsp-on-general-evex-no-displacement-row.fmp.json`, `aarch64/negative/N16c-imm3-excluded.fmp.json`, `aarch64/negative/N16d-w-imm6-excluded.fmp.json`, `aarch64/negative/N16e-ext-imm3-excluded.fmp.json` | x86, rv64 and aarch64 passing (`N16f`: register 4 fits the base field but would need a SIB byte, so it is rejected rather than widened; `N16h`: register 12 is the `%r12` case of the same rule on the `0.7.0` general rows; `N16i`: index 4 is the `SIB` "no index" encoding, which would silently drop the register; `N16j`: `%rsp` is the same SIB-forcing exclusion on the `0.9.0` SSE memory rows; `N16k` and `N16l` are the `0.10.0` base window: `rax` and `%r12` are outside a `-base-ext` row, which accepts only `8`–`15` minus `12`; `N16m` and `N16n` are the `0.11.0` register windows: a low `xmm` on a legacy extension row and on the VEX source-extension row; `N16o` and `N16p` are the `0.12.0` no-displacement exclusions: `%rsp` forces a `SIB` byte and `%rbp` collides with `r/m = 101`, so both bases must name the `disp8` row with displacement `0`, and `N16q` is a low base on the legacy `REX.B` no-displacement row; `N16r`/`N16s` are the VEX.256 windows: `%rbp` on a no-displacement row and `%r12` on an extended-base row, `N16t` is number 4 on the REX-less `0.17.0` byte-memory row (the high-byte register set, `E-RANGE-004`), `N16u` is `%rsp` as the base of a `0.17.0` word-memory row, which would spend a `SIB` byte, and the `0.18.0` trio `N16v`/`N16w`/`N16x` is the two new windows: a low base on an extension row, `%r12` on an extension row, `%r12` on a widened `40` row, and `N16y` is number `0` on a `0.19.0` `40` `SIB` row, whose register window is 4–7, and `N16z` is `%rsp` as the base of a `0.22.0` general EVEX no-displacement row, which must name the fixed-base row instead) |
| N17 | RV64 pair half is inconsistent: `N17a` a `pcrel_lo12` low half with a non-zero `addend`, `N17b` a `pcrel_hi` fixup with no `pair_role: lo`, `N17c` a `pcrel_hi` low half in a different section than its `hi` | Reject, never fold the addend in, fall back to `pcrel_begin`, or measure across sections | E-FIXUP-009 / E-FIXUP-007 | rv64 | `rv64/negative/N17a-lo12-addend-nonzero.fmp.json`, `rv64/negative/N17b-pcrel-hi-without-lo-role.fmp.json`, `rv64/negative/N17c-lo-in-other-section.fmp.json` | rv64 passing |
| N18 | Operand value is legal as a *literal* for the instruction but not inside the named form's field: `0x1000` on `add/x64-imm12-lsl0`, `0x123000` on `add/x64-imm12-lsl12`, `0x12340000` on `movz/x64-imm16-lsl16`, `0x12340000` on `movk/x64-imm16-lsl16`, `4096` on `sub/x64-imm12-lsl0`, `4096` on `adds/x64-imm12-lsl0`, or `4096` on `adds/w32-imm12-lsl0` | Reject, never switch to the other form or pre-scale the operand | E-RANGE-001 | aarch64 | `aarch64/negative/N18a-no-form-switch.fmp.json`, `aarch64/negative/N18b-operand-is-field-content.fmp.json`, `aarch64/negative/N18c-movz-pre-scaled-literal.fmp.json`, `aarch64/negative/N18d-sub-no-form-switch.fmp.json`, `aarch64/negative/N18e-adds-no-form-switch.fmp.json`, `aarch64/negative/N18f-w-adds-no-form-switch.fmp.json`, `aarch64/negative/N18g-movk-pre-scaled-literal.fmp.json` | aarch64 passing |
| N19 | A byte-affecting variation is stated as an operand `modifiers` entry the slot does not permit (`{"name": "lsl", "value": 3}` on `aarch64:add/x64-x64-x64-lsl0`, `{"name": "lsl", "value": 3}` on the `index` of `aarch64:ldr/x64-base-regoff-lsl0`, or `{"name": "lsl", "value": 2}` on the `index` of `aarch64:ldr/w32-base-regoff-lsl0`) | Reject, never emit the word the unshifted form would produce | E-OPERAND-003 | aarch64 | `aarch64/negative/N19-modifier-is-not-a-carrier.fmp.json`, `aarch64/negative/N19b-regoff-modifier-is-not-a-carrier.fmp.json`, `aarch64/negative/N19c-w32-regoff-modifier-is-not-a-carrier.fmp.json` | aarch64 passing |
| N20 | A fixup's pre-transform displacement is not a multiple of the slot's unit (`align_bits`), e.g. a literal load whose symbol is 2 bytes away | Reject, never round the displacement | E-RANGE-003 | aarch64, rv64, x86 | `aarch64/negative/N20-loadlit-fixup-misaligned.fmp.json` | aarch64 passing (`required_align 2`, `value 2`, at `/fixups/0/value_transform`) |
| N21 | A plan or definition object carries a field the current format does not declare | Reject at read time, never ignore or carry the value | E-PLAN-003 / E-DEF-001 | x86 (plan), all (definition) | `x86_64/negative/N21a-unknown-root-field.fmp.json`, `x86_64/negative/N21b-unknown-instruction-field.fmp.json` | x86 passing (root path `""`, instruction path `/instructions/0`, detail keys `field`/`object`); the definition half is the unit test `unknown_definition_field_is_rejected` (`ADR-0031`) |

N13's counterexample is `EXP-0002` W2: a same-length encoder defect turns
`48 89 d8` (`mov rax, rbx`) into `49 89 d8` (`mov r8, rbx`), both 3 bytes and
both legal. `expected_size` cannot see it; only the digest can. The test must
also confirm the materializer does **not** attempt a repair (W4: a plan whose
immediate is edited must be rejected, not re-encoded around).

N14 is the field-width failure, not the class failure. `r9` is a legal
`x86.gpr64`, so `E-OPERAND-001` does not apply; in `0.1.0`–`0.5.0` the `ModRM`
field is 3 bits and the `REX` byte is pinned, so the value simply does not fit.
`EXP-0004` §3 measured what truncation would do: `48 89 c8` decodes as
`movq %rcx, %rax`, a move of a different register. `0.6.0` widens those slots to
four bits and places the high bit in `REX.R`/`REX.B` (`ADR-0033`), so `N14c`
pins the old boundary (`field_bits = 3`) and `N14d` the new field end
(`field_bits = 4`: `r16` does not exist). The AArch64 fixture is the same shape
with a 5-bit field (`x32` would truncate to `x0`); an RV64 case would have the
same shape, but no such fixture exists yet.

N18 is the A64-P2 pair: the operand is inside the *literal's* legal set but not
inside the named form's field. `llvm-mc` accepts `#0x1000` and silently emits the
`sh=1` form (`EV-26`, `EXP-0013` §2); the materializer must reject it on `-lsl0`
(`N18a`, `E-RANGE-001`), because choosing the form from the value is `INV-02`.
The converse spelling is `N18b`: naming `-lsl12` and passing `0x123000` is also
`E-RANGE-001`, because the operand is `imm12` field content (0…4095) and the
`<< 12` belongs to the form, not to the slot. Together they pin "the slot is the
field" (`07_definition_format.md` §8.3) on both sides.

Applicability notes: N12 is not applicable to x86-64 in v0 because the selected
x86 slice uses a single-site `rel32`; if an x86 pair case is added, the row must
be revisited.

N01 was written against `encoding_choices`. After ADR-0004 the decision is
carried by `form_id`, so the directive's N01 input ("missing required encoding
choice") is exactly a plan whose form under-specifies the encoding. The test must
also confirm the id is not repaired by appending a width, direction or encoding
family suffix, and that a renamed variant fails instead of matching its
neighbour (`OD-04`).

N08 splits by repair path: a `symbol_id` that names no entry in `symbols[]` is
`E-SYMBOL-001` (the plan is internally inconsistent), while a symbol that exists
but has no address and is asked to resolve in place is `E-FIXUP-002`. A plan that
wants a record instead is legal and emits one (`OD-02`).

### Phase 1 evidence for N03 and N04

The audit produced both the positive restraint and the negative counterexample
from a built reference implementation (`90_boundary_audit.md` F-06, F-10, F-11;
raw commands in `research/evidence/experiments/EXP-0001-xirasm-boundary-probes.md`):

| Behaviour | Reference implementation | What our materializer must do instead |
|---|---|---|
| RISC-V immediate out of field range | rejects (`addi a0,a1,2048`) | same: `E-RANGE-001` |
| RISC-V branch out of range | rejects (`beq ...,0x1008`, `c.j 0x800`) | same: `E-RANGE-002` |
| x86 label branch out of `rel8` | rejects (`does not fit the signed 8-bit displacement`) | same: `E-FIXUP-003` |
| x86 numeric `short` branch out of `rel8` | emits `eb 80` for target `0x82` — **silently truncated** | reject: `E-RANGE-002`. This is the concrete failure N04 exists to prevent. |
| x86 unqualified branch | auto-shortens to `rel8`, promotes to `rel32` when far | never shorten, never promote: `INV-02`, `INV-04` |

## 2. Determinism experiments (`EXP-R*`)

| ID | Experiment | Method | Observable | Status |
|---|---|---|---|---|
| EXP-R1 | Repeated execution | Materialize the same plan 100 times in one process; compare bytes, fixup records, fingerprints | Byte equality | **passing** — 55 positive fixtures × 100 runs, canonical artifact equal (`EXP-0033` §1, re-run in §7) |
| EXP-R2 | Cross-process | Run the CLI in N independent processes; compare hashes of artifacts | Hash equality | **passing** — 3 plans × 4 CLI processes, canonical artifact equal to the in-process result (`EXP-0033` §2) |
| EXP-R3 | Different host environment | Run on a second OS/compiler/host where available; otherwise mark unverified | Hash equality or explicit `unverified` | **unverified** — one Windows host; WSL has no distribution, no second machine was used (`EXP-0033` §6) |
| EXP-R4 | Serialization replay | Serialize → parse → materialize; compare with direct materialization | Byte equality | **passing** — 55 positives × canonical and pretty round trips (`EXP-0033` §3, re-run in §7) |
| EXP-R5 | Definition perturbation | Swap the definition for a modified one; expect E-DEF-001, not silent bytes | Error identity | **passing** — a changed template is `E-DEF-001` at `/definition_identity/digest`, a renamed version is `E-DEF-002`; neither emits bytes (`EXP-0033` §4) |
| EXP-R6 | Negative determinism | Repeat an invalid plan; compare error identity (code+path+detail keys), ignoring `message` | Identity equality | **passing** — 187 negatives × 100 runs (`EXP-0033` §7) |

EXP-R3 must not be claimed unless actually executed. "Not tested on a second
host" is the honest result.

## 3. Acceptance criteria (`AC-*`)

| ID | Requirement | Evidence form | Status |
|---|---|---|---|
| AC-01 | Contract complete enough to guide implementation | `01_contract.md` with no `TBD` on fields used by the three slices | **clear for all three slices** (2026-11-05): OD-02, OD-04, OD-07, OD-09 and OD-12 are settled, `definitions/rv64/0.1.0.json`/`0.2.0.json` landed, and no field the three slices use is `TBD`; `symbol_order` and the Level 1 envelope stay `draft` because `OD-03` defers them and no slice needs them |
| AC-02 | Key fields justified | Each frozen field cites a counterexample or source evidence | **clear for the fields the three slices use**: OD-02/04/09/13/14/15 cite measured counterexamples and the remaining `draft` fields (`symbol_order`, Level 1) are optional |
| AC-03 | Three-ISA vertical slices | One closed loop per ISA: plan → validate → encode → fixup → oracle compare | **satisfied** (2026-11-06): x86 26 positive + 118 negative, AArch64 20 + 57, RV64 9 + 12, and `cargo test -p fmp-cli --test fixtures` compares every positive's bytes/record count with the oracle and every negative's complete diagnostic set |
| AC-04 | Encoding ambiguity proven absent | x86 `imm8`/`imm32`, `rel8`/`rel32`, `89`/`8B`, the `88`/`40 88`/`88h` register sets, the `legacy`/`vex`/`evex` families at register and memory shapes, the `L`/`L'L` widths (`xmm`/`ymm`/`zmm`), the `-base-index-` shape with its two-bit scale, the two SSE base windows, the three SSE register windows, the three memory displacement widths (none, `disp8`, `disp32`), the inverted extension bits (including the second EVEX host bit for `xmm16`–`xmm31`), and the EVEX `disp8x16`/`disp8x32`/`disp8x64` content, plus RV64 `c.*` vs standard, are distinct `form_id`s and field types; per-`EC` negative test per `02_encoding_choices.md`, "Validation obligation" | **satisfied for the frozen rows** (2026-11-05): each of the 31 frozen `EC` rows names a carrier that the fixtures reject when falsified (form variants through `N01`, operand classes through `N02`, excluded values through `N16`, the scale's and the EVEX `disp8*N` units through `N03`); the nine `draft` rows are outside the v0 surface and are listed in `02_encoding_choices.md`, "Open work" |
| AC-05 | Fixups validated | x86 `rel32`; AArch64 `adrp`+`:lo12:`; RV64 `auipc`+`lo12` or B-type scatter | **satisfied** (2026-11-05): `X86-P8-local-and-external-branch` (`rel32` record), `X86-P6-rip-relative` (`R_X86_64_PC32`), `A64-P6-adrp-lo12-pair` (`adrp`+`lo12`), `RV-P8-pcrel-pair` (three records) and `RV-P8-pcrel-pair-resolved` (linked arithmetic) |
| AC-06 | Strict rejection | All applicable N01–N13 with recorded codes | **satisfied for N01–N20 as applicable** (2026-11-05): every row has at least one fixture whose code, JSON Pointer and detail keys are compared exactly; N12 is not applicable to x86 v0 (single-site `rel32`), and N06 is exercised on x86 and rv64 |
| AC-07 | Deterministic replay | EXP-R1, EXP-R2, EXP-R4, EXP-R5 | **satisfied for one host** (2026-11-05): `EXP-R1`/`R2`/`R4`/`R5` pass, and `R6` covers negative identity (`EXP-0033`); `EXP-R3` stays `unverified`, so cross-platform replay is not claimed |
| AC-08 | Reuse boundary backed by source evidence | `90_boundary_audit.md` with revision, file, symbol, line range | **done** for XirAsm; LLVM internals deferred (see audit §8) |
| AC-09 | Unresolved problems stated | `05_open_decisions.md` with blocking impact, no "later" hand-waving | **satisfied** (2026-11-05): every `OD-*` row is accepted, including OD-05 (ADR-0031) and OD-08 (ADR-0032); the only deferred item is the Level 1 envelope, which OD-03 records as out of scope |
| AC-10 | Executable next step | Final report §H: modules, order, gates, blockers | planned |

## 4. Positive vectors

Each vector needs **two independent sources**: our materializer, and an oracle
(`llvm-mc` bytes, binutils, or a manual derivation recorded in
`research/evidence/experiments/`). The oracle's exact version must be recorded.

### x86-64 (directive §6.1)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| X86-P1 | Register-to-register transfer | `x86:mov/rm-r64/legacy` (`REX.W 89 /r`) and `x86:mov/r64-rm/legacy` (`REX.W 8B /r`) | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P2 | Arithmetic with immediate | `x86:add/rm64-imm8/legacy` and `x86:add/rm64-imm32/legacy` as separate forms | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P3 | Same operation, different legal encodings | `x86:add/rax-imm32/legacy` vs `x86:add/rm64-imm32/legacy`; `x86:mov/rm-r64` vs `x86:mov/r64-rm` | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P4 | Displacement width | `mov rax, [rbp-8]` (disp8) vs (disp32): `x86:mov/r64-base-disp8/legacy` / `-disp32`, the store pair, and the `%rsp` SIB pair | llvm-mc + llvm-objdump | x86 passing (`EXP-0030`; `X86-P4-base-disp`) |
| X86-P5 | Prefix rules | 16-bit operand with `0x66`; REX + high-byte rejection: `x86:mov/rm16-r16/legacy`, `x86:mov/r16-rm16/legacy`, `x86:mov/rm8h-r8h/legacy`, `x86:mov/rm8-r8/legacy` and `x86:mov/rm8-r8-rex/legacy` | llvm-mc | x86 passing (`EXP-0031`; `X86-P5-prefixes`) |
| X86-P6 | RIP-relative reference | `mov rax, [rip+disp32]`: `x86:mov/r64-riprel32/legacy` and the store direction, with a `pcrel_end` fixup | llvm-mc + llvm-readobj | x86 passing (`EXP-0029`; `X86-P6-rip-relative`) |
| X86-P7 | Short vs near branch | `x86:jmp/rel8/legacy` and `x86:jmp/rel32/legacy` as explicit plans | llvm-mc | x86 passing (`EXP-0005`) |
| X86-P8 | External branch fixup | `x86:jmp/rel32/legacy` to an undefined symbol with `emit_relocation`, record emitted. `call rel32` is not in the v0 surface (`OD-10`); its descriptor is identical, so the record shape is exercised without adding a form | llvm-mc + llvm-readobj | x86 passing (`EXP-0005`) |
| X86-P9 | Explicit encoding family | SSE vs VEX vs EVEX for one operation: `x86:movaps/xmm-xmm/legacy`, `x86:vmovaps/xmm-xmm/vex` and `x86:vmovaps/xmm-xmm/evex` | llvm-mc | x86 passing (`EXP-0032`; `X86-P9-sse-vex-evex`) |
| X86-P10 | The extended GPR file | `r8`–`r15` in a register-direct transfer: the six 64-bit rows of `0.6.0` carry a 4-bit register slot whose high bit is `REX.R`/`REX.B`, so `mov %r8,%r9` is `4d 89 c1` and `mov %rax,%rbx` keeps `48 89 c3` | llvm-mc + `llvm-mc -disassemble` | x86 passing (`EXP-0035`; `X86-P10-gpr-extended`) |
| X86-P11 | The extended memory base | `r8`–`r15` as a base: `0.7.0` widens the base+disp rows to four bits, excludes the two SIB-forcing values (`4`, `12`), and gives `%r12` four fixed-base rows that differ from the `%rsp` rows only in `REX.B` (`49` vs `48`) | llvm-mc | x86 passing (`EXP-0036`; `X86-P11-base-extended`) |
| X86-P12 | The SIB index and scale | `base + index*scale + disp`: `0.8.0` adds four rows whose `SIB` byte carries a 4-bit index (bit 3 in `REX.X`, `4` = "no index" excluded), a 4-bit base (all sixteen legal, `%rsp`/`%r12` included) and a two-bit scale operand `0…3` (×1…×8), so `movq 8(%r8,%r9,2), %r10` is `4f 8b 54 48 08` and `movq 8(%rax,%r12,4), %rdx` is `4a 8b 54 a0 08` | llvm-mc + `llvm-mc -disassemble` | x86 passing (`EXP-0037`; `X86-P12-base-index-scale`) |
| X86-P13 | SSE memory operands | `movaps`/`vmovaps` with a base and a displacement: `0.9.0` adds twelve rows across `legacy`/`vex`/`evex`, load/store × `disp8`/`disp32`; the base is 3 bits in all three families (`%rsp` excluded), and the EVEX `disp8` operand is the compressed content (`disp8x16`, unit 16) | llvm-mc (with `{evex}`) | x86 passing (`EXP-0038`; `X86-P13-sse-memory`) |
| X86-P14 | SSE base at `r8`–`r15` | `movaps`/`vmovaps` with a high base: `0.10.0` widens the four EVEX rows in place (the base's fourth bit at the inverted `B̄`) and adds eight `-base-ext` rows (legacy `REX.B`, three-byte VEX `C4 C1 78`); the low and extension windows are disjoint, `%r12` stays excluded, and the `xmm` slot stays 3 bits | llvm-mc (with `{evex}`) + `llvm-mc -disassemble` | x86 passing (`EXP-0039`; `X86-P14-sse-base-ext`) |
| X86-P15 | SSE register at `xmm8`–`xmm15` | `movaps`/`vmovaps` with a high register: `0.11.0` widens the VEX and EVEX memory `xmm` slots and the EVEX register-direct pair in place (`R̄` at bit 15, `B̄` at bit 13 for the EVEX source), adds three legacy `40 0F 28 /r` register windows (`REX.R`/`REX.B`), two VEX register windows (`C5 78 29` for a high source, `C4 41 78 28` for both high) and four `REX.R` legacy memory rows with a 4-bit base; a low `xmm` on an extension row is `E-RANGE-004` | llvm-mc (with `{evex}`) + `llvm-mc -disassemble` | x86 passing (`EXP-0040`; `X86-P15-sse-xmm-ext`) |
| X86-P16 | SSE memory with no displacement | `movaps (%rax), %xmm0` is `0f 28 00`, three bytes: `0.12.0` adds twelve `mod = 00` rows (six legacy, four VEX, two EVEX) with no `disp` slot. No displacement and `disp8 = 0` are different encodings (`0f 28 00` vs `0f 28 40 00`), so the width is a form; `%rsp`/`%r12` force a `SIB` byte and `%rbp`/`%r13` collide with `r/m = 101`, so those bases stay on the `disp8` row with displacement `0` (`E-RANGE-004`) | llvm-mc (with `{evex}`) + `llvm-mc -disassemble` | x86 passing (`EXP-0041`; `X86-P16-sse-no-disp`) |
| X86-P17 | The EVEX vector register reaches `xmm16`–`xmm31` | `vmovaps %xmm31, %xmm30` is `62 01 7c 08 28 f7`, six bytes: `0.13.0` widens the `xmm` slot of the seven EVEX rows in place from four bits to five, so bit 4 is the inverted `R̄'` for `ModRM.reg` and the inverted `X̄` for a register-direct `ModRM.rm`. No row is added and no length changes; legacy and VEX have no second extension bit, so the same operand stays `E-OPERAND-004` there (`N14o`), and `xmm32` is outside the five-bit field (`N14n`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` | x86 passing (`EXP-0042`; `X86-P17-sse-xmm16-31`) |
| X86-P18 | Vector width as a form fact, `ymm` and `zmm` | `vmovaps %ymm1, %ymm0` is `c5 fc 28 c1` while `vmovaps %xmm1, %xmm0` is `c5 f8 28 c1`, differing only in `L`; `62 f1 7c 28 28 c1` and `62 f1 7c 48 28 c1` differ only in `L'L`. `0.14.0` adds five register-direct rows — three VEX.256 windows (low/low with `R̄`, opcode 29 for a high source, three-byte `C4` for both high), one EVEX.256 and one EVEX.512 — and two kinds, `x86.ymm`/`ymm` and `x86.zmm`/`zmm`. Width is never selected by an operand value (`INV-02`); a width mismatch is `E-OPERAND-001` (`N02n`), legacy has no `ymm` row (`N01aj`), `ymm16` is outside the VEX field (`N14p`) and `zmm32` outside the EVEX field (`N14q`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` | x86 passing (`EXP-0043`; `X86-P18-sse-ymm-zmm`) |
| X86-P19 | The EVEX compressed-displacement unit at `ymm`/`zmm` width | `{evex} vmovaps 32(%rax), %ymm0` is `62 f1 7c 28 28 40 01` and `vmovaps 64(%rax), %zmm0` is `62 f1 7c 48 28 40 01`: content `1` is `32` bytes at `N = 32` and `64` at `N = 64`, while the `0.9.0` `xmm` row reads the same byte as `16`. `0.15.0` adds twelve memory rows — six per width — and revises `EC-39` so the unit is the row's `target_type` (`disp8x32`/`disp8x64`), never a division at materialization time. Reach and base windows are unchanged; a `disp8x16` displacement on a `disp8x32` row is `E-OPERAND-001` (`N02p`), content `128` is `E-RANGE-001` (`N03e`), `ymm32` is `E-OPERAND-004` (`N14r`), and VEX.256 memory has no row in `0.15.0` (`N01al`; `X86-P20` adds it in `0.16.0`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` | x86 passing (`EXP-0044`; `X86-P19-sse-ymm-zmm-memory`) |
| X86-P20 | VEX.256 memory coverage | `vmovaps 32(%rax), %ymm0` is `c5 fc 28 40 20` and `vmovaps 32(%r8), %ymm0` is `c4 c1 7c 28 40 20`: the displacement is a plain signed byte, not a compressed unit, and only `L` changes from the 128-bit row. `0.16.0` adds twelve rows — the two base windows × load/store × `disp8`/`disp32`/none — with no new `EC` fact. The vector slot is still four bits (`R̄` + `ModRM.reg`), a `zmm` operand is `E-OPERAND-001` (`N02q`), `ymm16` is `E-OPERAND-004` (`N14s`), `%rbp`/`%r12` are `E-RANGE-004` (`N16r`/`N16s`), content `128` is `E-RANGE-001` (`N03f`), and `0.15.0` rejects both windows (`N01al`/`N01am`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` | x86 passing (`EXP-0045`; `X86-P20-vex-ymm-memory`) |

| X86-P21 | The 8-bit and 16-bit memory rows | `movw %ax, 8(%rax)` is `66 89 40 08` and `movb %ah, 8(%rax)` is `88 60 08`, while `movb %spl, 8(%rax)` is `40 88 60 08`: the `66` prefix and the three byte register sets carry over from `0.4.0`, with `ModRM` and the displacement moving with the prefix. `0.17.0` adds sixteen rows — four word and twelve byte (low, high, REX) × load/store × `disp8`/`disp32` — with no new `EC` fact. Every base is the three-bit window 0–7 minus `%rsp`; `gpr32` on a word row is `E-OPERAND-001` (`N02r`), `gpr8h` on the REX row is `E-OPERAND-001` (`N02s`), number 4 on the REX-less low row is `E-RANGE-004` (`N16t`), `%rsp` is `E-RANGE-004` (`N16u`), content `128` is `E-RANGE-001` (`N03g`), base `8` is `E-OPERAND-004` (`N14t`), and `0.16.0` rejects every row (`N01an`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` + llvm-objcopy | x86 passing (`EXP-0046`; `X86-P21-mov-mem-8-16`) |
| X86-P22 | The extended base of the 8/16-bit memory rows | `movw %ax, 8(%r8)` is `66 41 89 40 08` (five bytes, one more than `66 89 40 08`) and `movb %al, 8(%r8)` is `41 88 40 08`, while `movb %spl, 8(%r8)` is `41 88 60 08`: `0.18.0` adds eight `-base-ext` rows (word and REX-less low-byte, load/store × `disp8`/`disp32`) and widens the four `40`-prefixed byte rows in place. `REX.B` is bit 8 on the word rows (the `66` byte stays first) and bit 0 on the byte rows; the byte axis is a partition, numbers 0–3 on the new rows and 4–7 on the widened ones. Extension rows exclude `0`–`7` and `%r12`; the widened rows exclude `%rsp` and `%r12`. Base `0` on an extension row is `E-RANGE-004` (`N16v`), `%r12` is the same code on either window (`N16w`/`N16x`), base `16` is `E-OPERAND-004` (`N14u`), `gpr8h` on a `41` row is `E-OPERAND-001` (`N02t`), and `0.17.0` rejects the rows (`N01ao`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` + llvm-objcopy | x86 passing (`EXP-0047`; `X86-P22-mov-mem-base-ext`) |
| X86-P23 | The `SIB` base of the 8/16-bit memory rows | `movw %ax, 8(%rsp)` is `66 89 44 24 08` and `movw %ax, 8(%r12)` is `66 41 89 44 24 08`: `%rsp` spends a `SIB` byte (`r/m = 100`, `SIB = 24`) and `%r12` spends `REX.B` on top, so `0.19.0` appends twenty-eight fixed-base rows — word, REX-less low byte, high byte and `40`-prefixed byte, load/store × `disp8`/`disp32`, at both bases except the high-byte family, which has no `%r12` encoding. The base leaves the operand list and enters the template; `ModRM.reg`/`disp` move one byte later with it (`[27,3]`/`[40,8]` on the word `%r12` rows). Naming a row against `0.18.0` is `E-FORM-001` (`N01ap`), the high-byte `%r12` row is the same code (`N01aq`), a word operand is two `E-OPERAND-001` (`N02u`), content `128` is `E-RANGE-001` (`N03h`), register `8` is `E-OPERAND-004` (`N14v`), and number `0` on a `40` row is `E-RANGE-004` (`N16y`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` + llvm-objcopy | x86 passing (`EXP-0048`; `X86-P23-mov-mem-sib`) |
| X86-P24 | The `SIB` base of the SSE `movaps`/`vmovaps` memory rows | `movaps 8(%rsp), %xmm0` is `0f 28 44 24 08` and `movaps 8(%r12), %xmm0` is `41 0f 28 44 24 08`, while `vmovaps 8(%r12), %xmm0` is `c4 c1 78 28 44 24 08`: the legacy rows spend `REX.B` and the VEX rows the three-byte prefix, since the two-byte form cannot carry `B = 1`. `0.20.0` appends sixteen fixed-base rows — two families × load/store × `disp8`/`disp32` × `%rsp`/`%r12` — with the base in the template and the register window inherited: legacy stops at `xmm7` (`E-OPERAND-004`, `N14w`), VEX keeps `xmm0`–`xmm15` by clearing `R̄`. Naming a row against `0.19.0` is `E-FORM-001` (`N01ar`), the absent no-displacement shape is the same code (`N01as`), a `gpr64` operand is two `E-OPERAND-001` (`N02v`), a third `base` operand is `E-OPERAND-002` (`N02w`), and content `128` is `E-RANGE-001` (`N03i`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` + llvm-objcopy | x86 passing (`EXP-0049`; `X86-P24-sse-mem-sib`) |
| X86-P25 | The `SIB` base of the EVEX `vmovaps` memory rows | `{evex} vmovaps 16(%rsp), %xmm0` is `62 f1 7c 08 28 44 24 01` and `{evex} vmovaps 16(%r12), %xmm0` is `62 d1 7c 08 28 44 24 01`: the base costs one `SIB` byte and no prefix byte, because `B̄` is already in `P0`, so the two bases are the same length and differ only in that byte. `0.21.0` appends twenty-four fixed-base rows — three widths × load/store × `disp8*N`/`disp32` × `%rsp`/`%r12` — with the vector slot staying at `[43,3]` and only the displacement moving to `[56,8]`/`[56,32]`; the five-bit field already reaches `xmm31`. Naming a row against `0.20.0` is `E-FORM-001` (`N01at`), the absent `mod = 00` shape is the same code (`N01au`), a `gpr64` operand is two `E-OPERAND-001` (`N02x`), a third `base` operand is `E-OPERAND-002` (`N02y`), content `128` on `disp8x16` is `E-RANGE-001` (`N03j`), and register `32` is `E-OPERAND-004` (`N14x`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` + llvm-objcopy | x86 passing (`EXP-0050`; `X86-P25-evex-mem-sib`) |
| X86-P26 | The `mod = 00` `SIB` base of the EVEX `vmovaps` memory rows | `{evex} vmovaps (%rsp), %xmm0` is `62 f1 7c 08 28 04 24` and `{evex} vmovaps (%r12), %xmm0` is `62 d1 7c 08 28 04 24`: `mod = 00` with `r/m = 100` puts the base in the `SIB` byte (`24`) and drops the displacement slot entirely, so the row is seven bytes and `%r12` still costs only the `P0` bit. `0.22.0` appends twelve fixed-base rows — three widths × load/store × `%rsp`/`%r12` — with the vector slot staying at `[43,3]`; `%rbp`/`%r13` stay out because `mod = 00` with `r/m = 101` is RIP-relative. Naming a row against `0.21.0` is `E-FORM-001` (`N01av`), the absent `%rbp` shape is the same code (`N01aw`), a `gpr64` operand is two `E-OPERAND-001` (`N02z`), an extra `disp` operand is `E-OPERAND-002` (`N02aa`), register `32` is `E-OPERAND-004` (`N14y`), and `%rsp` on the general `xmm-base` row is `E-RANGE-004` (`N16z`) | llvm-mc 23.1.2 + `llvm-mc -disassemble` + llvm-objcopy | x86 passing (`EXP-0051`; `X86-P26-evex-mem-sib-nodisp`) |

Oracle note for X86-P7, measured 2026-11-04: llvm-mc does not accept a bare
numeric branch target (`jmp 0x12`, `0x7f`, `0x80`, `0x1000`, `5` all emit
`e9 00 00 00 00` under `-filetype=obj`). Use a label or a `.+N` expression:
`jmp .+0x81` → `eb 7f`, `jmp .+0x82` → `e9 7d 00 00 00`. The disassembler prints
the displacement, not the resolved target, so the vector is compared as bytes and
the target is computed from the plan.

Definition anchor for X86-P1–P9, measured 2026-11-04 and 2026-11-05: the seven
`0.1.0` forms live in `definitions/x86_64/0.1.0.json` (digest
`sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad`), and
`EXP-0004` decodes 223 plan-derived byte strings with `llvm-mc` to confirm every
row's field placement. `definitions/x86_64/0.2.0.json` repeats those seven and
adds the two RIP-relative rows (nine forms, digest
`sha256:d9c088cacb9d20dcf8b801cbdb978996ed31d2e70b631897a905d179207991ac`);
`EXP-0029` measures their fields and the fixture below.
`definitions/x86_64/0.3.0.json` repeats those nine and adds the eight
base+displacement rows (seventeen forms, digest
`sha256:02500bf74d5c3db7816a30aca6c9c4d8fc7c5097306bc742f51284636c487c10`);
`EXP-0030` measures their fields and the fixture below.
`definitions/x86_64/0.4.0.json` repeats those seventeen and adds the five
prefix rows (twenty-two forms, digest
`sha256:ee2141cbb17f338c5b4a9de0302076bb2416838c09f7c44e2ca097cb142a2682`);
`EXP-0031` measures their bytes and the fixture below.
`definitions/x86_64/0.5.0.json` repeats those twenty-two and adds the three
encoding-family rows (twenty-five forms, digest
`sha256:24256f0c427447ee8db5506d7b395e3682dbb3b0317f0effa1ed3c4f75cc0aeb`);
`EXP-0032` measures the three families and the fixture below, and `0.5.0` is the
first x86 table whose `enabled_extensions` is not empty
(`avx`, `avx512f`, `avx512vl`).
`definitions/x86_64/0.9.0.json` repeats the `0.8.0` table and adds the twelve
SSE memory rows (forty-five forms, digest
`sha256:cc538253ba2d8a111ee16a8d5a8db1aa6efaaed75270889eed20f0f2f5ed6eb8`);
`EXP-0038` measures the fourteen-instruction fixture below.
`definitions/x86_64/0.10.0.json` widens the SSE base: the four EVEX rows take
`[13,1]` inverted + `[40,3]` and eight `-base-ext` rows join (fifty-three forms,
digest `sha256:0c10ff1c373eea2fe6098e67da3047081b34a5779d9ec492c47069ac73613442`);
`EXP-0039` measures the fourteen-instruction fixture below.
`definitions/x86_64/0.11.0.json` widens `x86.xmm`: the VEX and EVEX rows widen
in place, three legacy register windows and two VEX register windows join, and
four legacy memory rows carry a 4-bit `xmm` and base (sixty-two forms, digest
`sha256:d9669be62267ecd90d69dc9f936bcb947948b8c1ec7c7ba0670eb63f32de0570`);
`EXP-0040` measures the twenty-three-instruction fixture below.
`definitions/x86_64/0.12.0.json` adds the no-displacement shape: twelve
`mod = 00` rows across the three families, six of them legacy because the
`REX` byte is the only carrier of a high base or a high register there
(seventy-four forms, digest
`sha256:a74ae09e3f9d2596f2e99edde80d6a487e8596efc05d87e59d6409f82ebf35ae`);
`EXP-0041` measures the sixteen-instruction fixture below.
`definitions/x86_64/0.18.0.json` repeats `0.17.0` and adds the eight
`-base-ext` rows while widening the four `40` byte rows in place (127 forms,
digest `sha256:e1281b0c11d7e2bed9bd1ec7fa5404dadca2c82959376cbe3edfd9ff56b9e33d`);
`EXP-0047` measures the eighteen-instruction fixture below.
`definitions/x86_64/0.19.0.json` repeats `0.18.0` and adds the twenty-eight
fixed-base `SIB` rows (155 forms, digest
`sha256:dddc678fe0abc6fa03c2e61c8fcafef2570b496775a11a25e1ab29e01bfe5130`);
`EXP-0048` measures the twenty-eight-instruction fixture below.
`definitions/x86_64/0.20.0.json` repeats `0.19.0` and adds the sixteen SSE
fixed-base `SIB` rows (171 forms, digest
`sha256:b8bd1ed3ed38d71f6b19cc1854c9252df13850127c4e9433981a3a45f49d0f99`);
`EXP-0049` measures the sixteen-instruction fixture below.
`definitions/x86_64/0.21.0.json` repeats `0.20.0` and adds the twenty-four EVEX
fixed-base `SIB` rows (195 forms, digest
`sha256:30af3fec5c2f50e3ab30fb30d32e6b2e71f4520dbdb2660c6c9de1767b7b1160`);
`EXP-0050` measures the twenty-four-instruction fixture below.
`definitions/x86_64/0.22.0.json` repeats `0.21.0` and adds the twelve EVEX
no-displacement fixed-base `SIB` rows (207 forms, digest
`sha256:61c7cd1c940a7b22838a2c3418ba54031a20c6b227203fb9b4a57875f1c36b58`);
`EXP-0051` measures the twelve-instruction fixture below.

X86-P1 … X86-P26 have fixtures under `fixtures/x86_64/positive/` and a
recorded oracle (`EXP-0005`, `EXP-0035`…`EXP-0051`); the
fixture gate compares their bytes with the oracle's, never with the
materializer's own expectation.

`ADR-0008` settled the memory representation: one operand per encoded field
(`base`, `disp`, `index`, `scale`), never a `{mem: …}` payload, because the
encoding form changes with the operand values. That decision plus `ADR-0027`
and `ADR-0028` closed P4 and P6: `movq 8(%rcx), %rax` is `48 8b 41 08`
(mod=01), `movq 4096(%rcx), %rax` is `48 8b 81 00 10 00 00` (mod=10),
`movq (%rbp), %rax` is `48 8b 45 00` (mod=01, because mod=00 with `r/m = 101`
is RIP-relative), and `%rsp` is a fixed-base SIB form. P5 is a different
question and is closed by `ADR-0029`: `0x66` selects the 16-bit width as
template byte 0, and the 8-bit rows are split by prefix because `88 e5` is
`ah`/`ch` while `40 88 e5` is `spl`/`bpl` (`EC-36`, `EXP-0031`). P9 is a
different question again and is closed by `ADR-0030`: `movaps` at `xmm` width is
`0f 28 c1` with no prefix, `c5 f8 28 d3` in two-byte VEX and
`62 f1 7c 08 28 e5` in EVEX.128, so the family is the `/legacy`, `/vex` or
`/evex` component of the `form_id` and never an operand (`EC-09`, `EXP-0032`).
All nine directive §6.1 rows P1–P9 now pass; `OD-10`'s VEX/EVEX deferral is
lifted, and `EC-05`/`EC-10` and the rest of the extension surface stay out.
P10 is widening rather than a directive row: `ADR-0033` makes a `x86.gpr64` slot
four bits and places the high bit in `REX.R`/`REX.B`, so the six 64-bit
register-direct rows reach `r8`–`r15` (`48 89 c3` for `mov rax, rbx`,
`4d 89 c1` for `mov r8, r9`) from `0.6.0`, while `N14c`/`N14d` pin the two ends
of the field (`EC-06`, `EXP-0035`).
P11 continues the same widening for a memory base: `ADR-0034` gives `0.7.0`'s
base+disp rows a 4-bit base and a 4-bit `ModRM.reg` operand, excludes both
SIB-forcing values (`4`, `12`), and adds four fixed-base `%r12` rows that differ
from the `%rsp` rows only in `REX.B` (`49` vs `48`), so
`movq 8(%r12), %rax` is `49 8b 44 24 08` while `movq 8(%rsp), %rax` is
`48 8b 44 24 08` (`N16h`, `N01ac`, `EXP-0036`).
P12 is the third widening step, and the one that reaches `REX.X`: `ADR-0035`
gives `0.8.0` four rows whose template fixes `r/m = 100` and with it the `SIB`
byte, so `base + index*scale + disp` is a form and never a value-driven reshape
of another row. The `SIB` fields are operands — `base` is four bits and excludes
nothing (`%rsp`/`%r12` are ordinary bases once the byte exists), `index` is four
bits and excludes `4` (the "no index" encoding, `N16i`), and the scale is the
two-bit field content `0…3` carried as an operand, so `movq 8(%rax,%rcx,8), %rdx`
is `48 8b 54 c8 08` and `movq 8(%r8,%r9,2), %r10` is `4f 8b 54 48 08`
(`N03c`, `N01ad`, `EXP-0037`).
P13 is the SSE memory shape rather than another widening step: `ADR-0036` adds
twelve rows for `movaps`/`vmovaps` load and store across `legacy`, `vex` and
`evex` and both displacement widths. The base is three bits in all three
families — the legacy templates have no `REX`, `C5` has no `B`, and EVEX's
`B̄` is inverted — so `r8` is rejected rather than written raw (`N14f`,
`N14g`), and `%rsp` stays excluded (`N16j`). The EVEX `disp8` is the compressed
field: the plan carries the content (`disp8x16`, unit 16), and a byte offset
that is not a multiple of 16 names the `disp32` row (`EC-38`, `EC-39`,
`N03d`, `EXP-0038`).
P14 takes the widening P13 deferred. `ADR-0037` gives `0.10.0` a base window
per family: the four EVEX rows widen in place (`[13,1]` inverted + `[40,3]`),
because `62 f1 7c 08` and `62 d1 7c 08` are the same length, and the legacy and
VEX families get eight `-base-ext` rows, because reaching the high base adds a
`REX` byte (`41 0f 28 40 08` versus `0f 28 40 08`) or a third VEX byte
(`c4 c1 78 28 40 08` versus `c5 f8 28 40 08`). The windows exclude each other's
numbers, so exactly one row encodes a given base (`N16k`, `N16l`), the fourth
bit is a `placement.invert` chunk rather than a raw write (`EC-40`), and
`%r12` still forces a `SIB` byte (`E-RANGE-004`, `N16l`). `xmm8` stays outside
the register field (`N14e`), and `N01af`/`N14h` pin the version boundary and
the field end (`EXP-0039`).

P15 is the register counterpart of P14. `ADR-0038` widens `x86.xmm` to four
bits in `0.11.0`; EVEX and the VEX/EVEX memory rows widen in place, because
their prefixes already carry the inverted `R̄`/`B̄`. In a register-direct EVEX
instruction the destination is `ModRM.reg` (`R̄`, bit 15) and the source is
`ModRM.rm` (`B̄`, bit 13), so the two operands use different bits. The legacy
family needs three `40 0F 28 /r` windows (`44`/`41`/`45` for dest-high,
src-high and both), and the VEX family needs two more: `C5 78 29 /r` for a high
source with a low destination, and `C4 41 78 28 /r` for both high. `llvm-mc`
encodes both `c5 78 29 c0` and `c4 c1 78 28 c0` for `vmovaps %xmm8, %xmm0`, so
the table pins the four-byte opcode-29 form rather than letting the width decide
(`EC-06`, `EC-09`, `EXP-0040`). `N14i`/`N14j`/`N14k` pin the field ends and
`N16m`/`N16n` the disjoint windows.

P16 adds the shape `0.9.0` left out: a memory operand with no displacement at
all. `ADR-0039` gives `0.12.0` twelve `mod = 00` rows. `llvm-mc` measures
`0f 28 00` for `movaps (%rax), %xmm0`, and `llvm-mc -disassemble` also accepts
`0f 28 40 00`, which is the same instruction with `mod = 01` and `disp8 = 0`;
because a plan that named only the operands would let the materializer pick the
shorter encoding, the width is a form and the counterexample is the pair
(`EC-02`). The legacy family needs three windows for the same reason P15 did —
low/low, `REX.R` for a high register, `REX.B` for a high base — and the
`REX.R` window carries `REX.B` for free, so one row spans base `0`–`15`. VEX
keeps the two-byte prefix for a low base and moves to `C4 C1 78` for a high one;
EVEX stays six bytes and varies `P0`. Two base values are outside the shape:
`%rsp`/`%r12` force a `SIB` byte (`N16o`) and `%rbp`/`%r13` collide with
`r/m = 101`, which is RIP-relative under `mod = 00`, so `llvm-mc` emits
`0f 28 45 00` and the plan must name the `disp8` row with `0` (`N16p`).
`N16q` pins a low base on the legacy high-base row, `N14l` the 4-bit base end,
and `N01ah` the `0.11.0` boundary (`EXP-0041`).

P17 completes the register reach that P15 started. `ADR-0040` gives the seven
EVEX rows a fifth `xmm` bit in place, so `xmm16`–`xmm31` become reachable
without a new row and without a longer instruction. `llvm-mc` measures
`62 01 7c 08 28 f7` for `vmovaps %xmm31, %xmm30`; clearing `X̄` gives
`62 41 7c 08 28 f7`, which `llvm-mc -disassemble` reads as `%xmm15, %xmm30`,
and writing the two register bits raw gives `62 f1 7c 08 28 f7` = `%xmm7, %xmm6`
(`EC-06`, `EC-40`). The memory rows carry `X̄` at its template value because
they have no `SIB` field, so the same bit never has to be reinterpreted. `N14m`
pins the `0.12.0`/`0.13.0` boundary (`field_bits = 4`), `N14n` the five-bit field
end (`xmm32`), and `N14o` the family boundary (`xmm16` on a VEX row,
`field_bits = 4`) (`EXP-0042`).

P18 turns the remaining width axis into a form fact. The mnemonic is the same
for every width, so the only thing that changes is one prefix field: VEX `L`
(`c5 fc 28 c1` vs `c5 f8 28 c1`) or EVEX `L'L` (`62 f1 7c 28 28 c1` vs
`62 f1 7c 48 28 c1`). `ADR-0041` adds five register-direct rows rather than a
width operand: three VEX.256 windows that repeat P15's `xmm` windows (a high
destination stays in `R̄`, a high source moves to opcode 29, both-high needs the
three-byte `C4`), one EVEX.256 row and one EVEX.512 row that keep P17's five
register bits. `x86.ymm` and `x86.zmm` are distinct kinds, so a `zmm` operand on
a `ymm` row is `E-OPERAND-001` (`N02n`); legacy has no width field (`N01aj`),
`ymm16` is outside the VEX field (`N14p`), and `zmm32` is the EVEX field end
(`N14q`). Memory forms at these widths stay out because their compressed
displacement unit would revise `EC-39` (`EXP-0043`).

P19 finishes the width axis on memory and turns the compressed unit into a form
fact. The same eight-bit field means `16`, `32` or `64` bytes depending on `P2`,
so `ADR-0042` adds twelve rows — the six `0.13.0` `xmm` memory shapes at each
width — and revises `EC-39` so `N` is the slot's `target_type`
(`disp8x32`/`disp8x64`) instead of a constant. Only `P2` differs between the
two widths, so the five-bit vector slot and the four-bit base window are
P17's and P14's. The displacement payload stays the field content: `4064` is
content `127` at `ymm`, `−4096` is `−128`, and values the unit cannot divide
(`28`, `4096`, `60`, `8192`) are `disp32` rows rather than truncations
(`N02p`, `N03e`, `N14r`, `EXP-0044`). VEX.256 memory needs no new fact, so
`0.15.0` leaves it out (`N01al`) and `0.16.0` adds it as coverage (`ADR-0043`,
`X86-P20`): twelve rows at `L = 1`, the two base windows from `0.11.0`/`0.12.0`
unchanged, and a plain signed `disp8` because VEX has no compression. A `zmm`
operand is `E-OPERAND-001` (`N02q`), `ymm16` is `E-OPERAND-004` (`N14s`),
`%rbp`/`%r12` are `E-RANGE-004` (`N16r`/`N16s`), and content `128` is
`E-RANGE-001` (`N03f`, `EXP-0045`).

P21 carries the prefix and byte-register facts into memory at 8 and 16 bits
(`ADR-0044`). `0.17.0` adds sixteen rows: four word rows (`66 89`/`66 8b`) and
twelve byte rows in the three sets `0.4.0` already separated. The `66` byte
precedes any REX byte, so the word rows put `ModRM` at bit 16 and the
displacement at 24; the REX-less byte rows put them at 8 and 16; and the
`spl`–`dil` rows use a template `40` byte and move them back to 16 and 24. No
row adds an `EC` fact — `EC-02`, `EC-27`, `EC-28`, `EC-36` and `EC-38` already
state every field. The base window is the three-bit one from `0.3.0`, so `%rsp`
is `E-RANGE-004` (`N16u`) and `r8`–`r15` wait for the deferred `-base-ext` rows
(`N14t`). The byte sets stay disjoint: number 4 on the REX-less low row is
`E-RANGE-004` (`N16t`) and `x86.gpr8h` on the `-rex` row is `E-OPERAND-001`
(`N02s`). `EXP-0046` measures the twenty-six-instruction fixture
`X86-P21-mov-mem-8-16` (122 bytes), and every byte string round-trips through
`llvm-mc -disassemble`.

P22 carries the base window into those rows (`ADR-0045`). The families do not
behave alike, and that is the whole decision: the word and REX-less low-byte
rows have no `REX` byte in their template, so a high base adds one and the row
must be a separate form — eight `-base-ext` rows, one byte longer, with `REX.B`
at bit 8 after the `66` byte on the word rows and at bit 0 on the byte rows.
The four `40`-prefixed byte rows already carry the byte for `spl`–`dil`, so
their base widens from three bits to four in place and low bases keep their
bytes. The byte register set is the other half of the partition: the new rows
carry numbers 0–3 and exclude 4–7, the widened rows carry 4–7, and the
high-byte set has no encoding with a high base because the `REX` byte renames
`ah` (`N02t`). Every extension row excludes `0`–`7` and `%r12` so one
`(register, base)` pair names one row; `%rsp`/`%r12` stay out of both windows.
`EXP-0047` measures the eighteen-instruction fixture
`X86-P22-mov-mem-base-ext` (100 bytes), and all thirty-one probe strings
round-trip through `llvm-mc -disassemble`.

P23 adds the two bases P22 deferred (`ADR-0046`). `%rsp` spends a `SIB` byte and
`%r12` spends `REX.B` on top, so the length decision stays with the form: the
base is fixed in the template and the row carries only the register and the
displacement, the shape `0.3.0`/`0.7.0` gave `movq`. Twenty-eight rows cover
the four families at both widths, and the high-byte family gets `%rsp` only,
because `movb %ah, 8(%r12)` has no encoding — the `REX.B` byte that names
`%r12` renames `ah` to `spl`. The prefixes are template bytes, so `ModRM` and
the displacement move one byte later than on the `-base-disp*` rows, and the
byte register windows stay where `0.4.0` put them. `EXP-0048` measures the
twenty-eight-instruction fixture `X86-P23-mov-mem-sib` (178 bytes), and all
twenty-eight probe strings round-trip through `llvm-mc -disassemble`.

P24 repeats the `SIB` decision inside the SSE families (`ADR-0047`). The shape
is P23's: the base enters the template, `%rsp` spends the `SIB` byte `24` and
`%r12` spends `REX.B` in the legacy family, while VEX cannot carry `B = 1` in
the two-byte prefix and pays `c4 78` instead. Sixteen rows cover both families
at load/store × `disp8`/`disp32` × both bases. The register windows are
inherited rather than widened: the legacy field stays three bits, so `xmm8` is
`E-OPERAND-004`, and the VEX slot keeps `R̄`, so `vmovaps 8(%r12), %xmm9` is
`c4 41 78 28 4c 24 08` at the same length. `EXP-0049` measures the
sixteen-instruction fixture `X86-P24-sse-mem-sib` (120 bytes), and all twenty
probe strings round-trip through `llvm-mc -disassemble`.

`0.21.0` reaches the same two bases in the EVEX family (`ADR-0048`). There the base
costs no prefix byte at all: the fourth bit is already the inverted `B̄` in `P0`,
so `62 f1` and `62 d1` are the same length and differ only in that byte. The
twenty-four rows cover the three widths at their own `disp8*N` unit (`16`/`32`/`64`),
load/store and `disp8*N`/`disp32`, at `%rsp` and `%r12`; the prefix does not
grow, so the vector slot stays at `[43,3]` and only the displacement moves, from
bit 48 to 56. A displacement that is not a multiple of `N` promotes to `disp32`
rather than truncating, and the five-bit slot reaches `xmm31` with no length
change. `EXP-0050` measures the twenty-four-instruction fixture
`X86-P25-evex-mem-sib` (228 bytes), and all twenty-seven probe strings
round-trip through `llvm-mc -disassemble`.

`0.22.0` closes the `mod = 00` half of the same axis (`ADR-0049`). With
`r/m = 100` the base moves into the `SIB` byte (`24`) and `mod = 00` drops the
displacement slot, so `(%rsp)` is `62 f1 7c 08 28 04 24` and `(%r12)` is
`62 d1 7c 08 28 04 24` -- seven bytes, the two bases still differing only in
`P0`. The row has one slot, so a plan that supplies a `disp` operand is
`E-OPERAND-002` rather than a silently ignored offset, and `llvm-mc`
canonicalizes `0(%rsp)` to `(%rsp)`, so the shape is the only encoding of a
zero offset. `%rbp`/`%r13` cannot use it: `mod = 00` with `r/m = 101` is
RIP-relative, so `(%rbp)` keeps a zero displacement byte on the `-base` row.
`EXP-0051` measures the twelve-instruction fixture
`X86-P26-evex-mem-sib-nodisp` (84 bytes), and all sixteen probe strings
round-trip through `llvm-mc -disassemble`.

### AArch64 (directive §6.2)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| A64-P1 | Register arithmetic | `add x0, x1, x2` (`shifted-register`, pinned `LSL #0`) | llvm-mc | **passing** — `aarch64/positive/A64-P1-add-register` |
| A64-P2 | Immediate arithmetic | `add x0, x1, #imm12` and the `LSL #12` variant as two forms | llvm-mc | **passing** — `add/x64-imm12-lsl0` (imm 0 and 4095) in `A64-P2-add-imm12`; `add/x64-imm12-lsl12` (field content 1, 291, 4095, 0) in `A64-P2-add-imm12-lsl12`; `N18a`/`N18b` reject the form-switching spellings |
| A64-P3 | Load/store addressing | unsigned-offset vs pre/post-index vs unscaled as distinct forms | llvm-mc | **passing** — `A64-P3-ldst-addressing` (six instructions, five forms: `imm12` at 0 and 4095, pre-index +8, post-index −8, `ldur` at −256, store at 0) through `aarch64:ldr/x64-base-imm12`, `ldr/x64-base-imm9-pre`, `ldr/x64-base-imm9-post`, `ldur/x64-base-imm9` and `str/x64-base-imm12`; `N03` rejects `disp = 4096` on `imm12` and `disp = −257` on `imm9`; `N01b` rejects the absent register-offset id |
| A64-P4 | Conditional branch | `b.eq` imm19 | llvm-mc | **passing** — `A64-P4-b-cond` (`b.eq` +4, `b.ne` −4, `b.gt` −8) through `aarch64:b.cond/imm19` with the condition as a `cond4` operand; `N03` rejects `cond = 16` and `N04c` rejects an out-of-range `imm19` |
| A64-P5 | Unconditional branch/call | `bl` imm26 | llvm-mc + ld.lld | **passing** — `A64-P5-bl-local-symbol` (+4 and −4) |
| A64-P6 | PC-relative pair | `adrp` + `add #:lo12:` with `pair_group` | llvm-mc + ld.lld + llvm-readobj | **passing** — `A64-P6-adrp-lo12-pair` |
| A64-P7 | Scattered/scaled field | `movz` lane selection as four forms, `imm16` scaled by `16·hw` | llvm-mc | **passing** — `A64-P7-movz-lane` (five instructions, four forms: `hw` 0, 1, 2 and 3, with the same `imm16 = 4660` on the first two and 65535/0 at the ends) through `aarch64:movz/x64-imm16-lsl0` … `-lsl48`; `N18c` rejects a pre-scaled literal on `-lsl16` and `N01d` rejects the absent `lsl #8` lane |
| A64-P8 | Target-specific modifier | shift modifier on a register operand: the keyword is the form, `imm6` is the amount (`0…63`) | llvm-mc | **passing** — `A64-P8-shift-modifier` (six instructions, three forms: `lsl #3`, `lsr #7`, `asr #63`, `lsl #63`, `lsl #0`, `lsr #0`) through `aarch64:add/x64-x64-x64-imm6-lsl` … `-imm6-asr`; `N03-imm6` rejects an amount of 64, `N19` rejects the same shift stated as a `modifiers` entry, and `N01e` rejects the absent extend family |
| A64-P9 | Target-specific modifier | extend modifier on a register operand: the keyword is the form and fixes the source width, `imm3` is the amount (`0…4`, `5…7` excluded) | llvm-mc | **passing** — `A64-P9-extend-modifier` (eight instructions, one per `option`: six `w`-source keywords and two `x`-source keywords, with `imm3` at 0 and 4 on both classes and all three registers distinct in every row) through `aarch64:add/x64-x64-w32-imm3-uxtb` … `-imm3-sxtx`; `N03-imm3` rejects an amount of 8, `N16c` rejects 5 as excluded, `N02b` rejects a `w` operand on a shifted row, and `N01f` rejects that id against `0.7.0` |
| A64-P10 | Widening: a second arithmetic mnemonic | `sub` reuses the `add` shapes with `op = 1`: the unshifted register row, both `sh` halves of the immediate row, and the three shift keywords | llvm-mc | **passing** — `A64-P10-sub-family` (six instructions, one per new row: `-lsl0`, `-imm12-lsl0` at 4095, `-imm12-lsl12` at 291, and `-imm6-lsl/lsr/asr` at 3/7/63, with distinct registers in every row) through `aarch64:sub/x64-x64-x64-lsl0` … `-imm6-asr`; `N01g` rejects the absent `subs` form, `N01h` the absent `w` form, and `N18d` a literal that only fits the other `sh` half |
| A64-P11 | Widening: the flag-setting mnemonic | `adds`/`subs` reuse the `add`/`sub` shapes with `S = 1`: the unshifted register row, both `sh` halves of the immediate row, and the three shift keywords, per mnemonic | llvm-mc | **passing** — `A64-P11-adds-subs-family` (twelve instructions, one per new row: six `adds` and six `subs`, with `imm12` at 4095 and 291<<12, all three shift keywords at `imm6` 3/7/63, and distinct registers in every row) through `aarch64:adds/x64-x64-x64-lsl0` … `subs/x64-x64-x64-imm6-asr`; `N01i` rejects the absent `cmp` alias, `N01j` the absent `w` form, and `N18e` a literal that only fits the other `sh` half |
| A64-P12 | Widening: the 32-bit register class | every `add`/`sub`/`adds`/`subs` shape repeated on the `sf = 0` node, with `w32` registers and `imm6` over `0…31` | llvm-mc | **passing** — `A64-P12-w-rows` (twenty-four instructions, one per new row: six per mnemonic, with `imm12` at 4095 and 291<<12, all three shift keywords at `imm6` 3/7/31, and distinct registers 0–30 in every row) through `aarch64:add/w32-w32-w32-lsl0` … `subs/w32-w32-w32-imm6-asr`; `N01k` rejects the `w` form against `0.9.0`, `N02c` an `x64` destination on a `w` row, `N16d` `imm6 = 32`, and `N18f` a literal that only fits the other `sh` half |
| A64-P13 | Widening: the extended-register mnemonic family | `sub`/`adds`/`subs` repeat the eight `add` extended rows with the mnemonic node fixed; the keyword still picks the `src2` width and `imm3` stays `0…4` | llvm-mc | **passing** — `A64-P13-ext-family` (twenty-seven instructions: all eight `option` values on each of `sub`/`adds`/`subs`, `imm3` cycling 0–4, and three register-31 rows — `sub sp, …`, `adds x0, sp, …`, `subs xzr, …`) through `aarch64:sub/x64-x64-w32-imm3-uxtb` … `subs/x64-x64-x64-imm3-sxtx`; `N01l` rejects the absent 32-bit extended id, `N02d` an `x64` source on a `-uxtb` row, and `N16e` `imm3 = 5` on a `subs` row |
| A64-P14 | Widening: the `cmp`/`cmn` alias family | each alias row is its `subs`/`adds` base row with `Rd` pinned to 31 and the destination dropped: four shifted and two immediate rows per width, plus the eight `option` rows on `x64` | llvm-mc | **passing** — `A64-P14-cmp-cmn-family` (forty-seven instructions: forty alias rows, one per new form, and seven register-31 rows — `cmp sp, #5`, `cmp wsp, #5`, `cmp sp, x2`, `cmn sp, #5`, `cmn sp, x2`, `cmp x1, xzr`, `cmp w1, wzr`) through `aarch64:cmp/x64-x64-lsl0` … `cmn/x64-x64-x64-imm3-sxtx`; `N02e` rejects a `dest` operand on a `cmp` row (`E-OPERAND-002`, `expected: 2`, `found: 3`), and `N01i`/`N01m` reject the ids against `0.11.0` |
| A64-P15 | Widening: the store half of the addressing kinds | `str` pre-index and post-index plus `stur`, each the load row's layout with `opc = 00` and the stored register as `src`; `imm9` keeps its signed-byte range | llvm-mc | **passing** — `A64-P15-store-imm9-addressing` (eight instructions, five forms: pre-index `+8`/`−256`, post-index `+8`/`255`, `stur` `+16`/`−1`, and the `imm12` row at `0`/`4095`) through `aarch64:str/x64-base-imm9-pre`, `-imm9-post` and `stur/x64-base-imm9`; `N03` rejects `disp = −257` on the post row and `256` on `stur`, and `N01n` rejects the pre-index id against `0.12.0` |
| A64-P16 | Widening: the literal load, the one load without a base register | `ldr x0, <label>`: `imm19` at 5+19, `Rt` at 0+5, fixed pattern `0x58000000`; the target is a `pcrel_begin` fixup with `scale(2)` and `align_bits 2` | llvm-mc | **passing** — `A64-P16-loadlit` (six instructions over one form: two symbol targets at `+2` and `−4` field units, plain `−1`/`1`, and both field ends `262143`/`−262144`) through `aarch64:ldr/x64-imm19`; `N04d` rejects `imm19 = 262144` (`E-RANGE-002`), `N20` rejects a 2-byte symbol offset (`E-RANGE-003`), and `N01o` rejects the id against `0.13.0` |
| A64-P17 | Widening: the register-offset kind, the last load/store addressing kind | `ldr`/`str x0, [x1, x2, <keyword>]`: `Rm` at 16+5 as `index`, `option` at 13+3 and `S` at 12+1 pinned per row, `Rn` at 5+5 and `Rt` at 0+5; `option` also fixes the index width (`w` for `uxtw`/`sxtw`, `x` for `lsl`/`sxtx`) | llvm-mc | **passing** — `A64-P17-regoff` (twenty instructions: all sixteen new rows, once each, plus four register-31 rows — `sp` in `Rn`, `xzr`/`wzr` in `Rm`) through `aarch64:ldr/x64-base-regoff-lsl0` … `str/x64-base-regoff-sxtx3`; `N01p` rejects the id against `0.14.0`, `N01q` rejects a `-lsl1` row, `N02f` rejects a `w32` index on a `-lsl0` row, and `N19b` rejects `lsl #3` as a modifier |
| A64-P18 | Widening: the 32-bit register offset | `ldr`/`str w0, [x1, x2, <keyword>]`: the same nodes as A64-P17 with `size = 10`, so `S = 1` scales by the 4-byte access (`#2`) and only `Rt` changes class (`w32`); `Rn`/`Rm` stay `x64` | llvm-mc | **passing** — `A64-P18-w32regoff` (twenty instructions: all sixteen new rows, once each, plus four register-31 rows — `sp` in `Rn`, `xzr`/`wzr` in `Rm`) through `aarch64:ldr/w32-base-regoff-lsl0` … `str/w32-base-regoff-sxtx2`; `N01r` rejects the id against `0.15.0`, `N01s` rejects a `-lsl3` row, `N02g` rejects a `w32` index on a `-lsl0` row, `N02h` rejects an `x64` destination, and `N19c` rejects `lsl #2` as a modifier |
| A64-P19 | Widening: the 64-bit move-wide mnemonics | `movk`/`movn x0, #imm16, <lane>`: `MOVK_64_movewide`/`MOVN_64_movewide` fix `opc = 11`/`00` and `sf = 1`, `hw` at 22–21 is pinned per row, `imm16` at 5+16 is field content, `Rd` at 0+5 is the destination | llvm-mc | **passing** — `A64-P19-movwide` (twelve instructions: the eight new rows once each in lane order plus four boundary rows — `x31` as destination, `#0`, `#0xffff` at `lsl #48`, `#0` on `movn` at `lsl #48`) through `aarch64:movk/x64-imm16-lsl0` … `movn/x64-imm16-lsl48`; `N01t` rejects a `-lsl8` lane, `N01u` rejects the id against `0.16.0`, `N01v` rejects a `w32` lane, `N01w` rejects the `mov` alias, `N02i` rejects a `w32` destination, `N03-movk-imm16` rejects `imm16 = 65536`, and `N18g` rejects a pre-scaled literal |

Definition anchor for A64-P1/P2/P3/P4/P5/P6/P7/P8/P9/P10/P11/P12/P13/P14/P15/P16/P17/P18/P19,
measured 2026-11-04 (A64-P18 and A64-P19 measured 2026-11-05): the four base
forms live in `definitions/aarch64/0.1.0.json` (digest
`sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e`),
generated from the Arm MRS 2026-06 drop by `EXP-0008`. `0.2.0` adds the fifth,
`aarch64:add/x64-imm12-lsl12` (digest
`sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed`), a
superset of the same four plus a second reading of `ADD_64_addsub_imm` with
`sh = 1`; `0.1.0` is unchanged, which is why `N01` still rejects that id
when a plan names it against `0.1.0`. The `-lsl0`/`-lsl12` suffix names the pinned
`sh`, and neither form rescales the operand (ADR-0011). `0.3.0` adds the sixth,
`aarch64:b.cond/imm19` (digest
`sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb`),
whose `B_only_condbranch` node leaves both the 4-bit condition and the 19-bit
displacement variable; the condition is an operand (`EC-29`, ADR-0012), not
sixteen forms. `0.4.0` adds the five load/store rows (digest
`sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78`), one per
MRS addressing-kind node, with `disp` as field content in 8-byte units (`imm12`)
or signed bytes (`imm9`) (`EC-14`, ADR-0013); `0.5.0` adds the four `movz` rows
(digest `sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e`),
one per `hw` value, with `imm16` as field content (`EC-30`, ADR-0014); `0.6.0`
adds the three shift rows (digest
`sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964`), one
per keyword, with the amount as an `imm6` operand (`EC-31`, ADR-0015); `0.7.0`
adds the eight extend rows (digest
`sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053`), one
per `option` value, with the keyword fixing the source width and the amount as an
`imm3` operand over `0…4` minus the excluded `5…7` (`EC-32`, ADR-0016); `0.8.0`
adds the six `sub` rows (digest
`sha256:9f82b566af004aaa9f0471151497d65acb45c3a7b46e4240345d21f4e330bc35`), the
immediate and shifted nodes with `op = 1`, the same `sh`/`shift`/`imm6`
treatment as the `add` rows and the same slot shapes (`EC-12` `sub` half,
`EC-31`, ADR-0017); and `0.9.0` adds the twelve `adds`/`subs` rows (digest
`sha256:99728cd9bd85b8b0768e700e15dd6263171d6261c385ac15ceeb5df6d2cafcff`),
the same two shapes again with `S = 1`, with the same treatment and slot shapes
(`EC-12`, `EC-13`, `EC-31`, ADR-0018); and `0.10.0` adds the twenty-four `w` rows
(digest
`sha256:e958d69b4ba93222e7621a1f5c3ebd056ce929e2974a961a03abb7b66f0b247b`),
the same six shapes on each of the eight `sf = 0` nodes with `w32` registers and
the 32-bit `imm6` tail (`EC-11`, `EC-31`, ADR-0019); and `0.11.0` adds the
twenty-four extended `sub`/`adds`/`subs` rows (digest
`sha256:c5a9aec943f9b195c400380b8416bf63cba944da3fdf0203f90de5baff295002`), the
eight `add` extended rows repeated with `op` and/or `S` fixed by the node
(`EC-13`, `EC-32`, ADR-0020); `0.12.0` adds the forty `cmp`/`cmn` rows (digest
`sha256:8a428926568b99f0674785cc674bc066adc452216131706d458b9e3390da03b6`), the
`subs`/`adds` rows again with `Rd` pinned to 31 and the destination dropped, the
alias node serving as the pairing check (`EC-33`, ADR-0021); `0.13.0` adds the
three store `imm9` rows (digest
`sha256:d3876dd37a8441057b586312b3bee410e39594c64806b2c5c59960c06f9c7a5f`), the
load rows' layouts with `opc = 00` and `Rt` as the stored register
(`EC-14`, ADR-0022); `0.14.0` adds the literal load (digest
`sha256:a90ceac19824fbb00731e040346daa191973652e58522fab72336e24f769a5ba`),
`LDR_64_loadlit` with no `Rn`, a `dest` and a `target` slot, and `imm19` as
field content in 4-byte units (`EC-15`, ADR-0023); `0.15.0` adds the sixteen
register-offset rows (digest
`sha256:422ebb83b897b18e010da37539796b0b97cfc9018a47209fc4a6ddc5b14af5d3`), eight
`option`/`S` pairs per mnemonic with `Rm` as an `index` slot whose width follows
`option` (`EC-14`, ADR-0024); `0.16.0` adds the sixteen 32-bit register-offset rows
(digest `sha256:1e83c6cad91594e8315500f39d0bcffa235edc90c5f47c012555c077a8dbc457`),
the same eight pairs with `size = 10`, `S` as `#2` and a `w32` destination/source
(`EC-14`, ADR-0025); `0.17.0` adds the eight 64-bit `movk`/`movn` rows (digest
`sha256:de2c53e1871f5c24f6af73082dcc402729786d2e6e2495f84e3ed553adb4e4ed`), the
four `hw` lanes on each of the two `opc`-fixed nodes with `imm16` as field
content (`EC-30`, `EC-16`, ADR-0026); `0.1.0`…`0.16.0` are unchanged.
`llvm-mc` does not resolve AArch64 branch or `adrp` immediates when
they name a symbol, so A64-P5/P6 take their bytes after
`ld.lld --image-base=0 -Ttext=0` has resolved the same `(S, P)` pair; the
relocation kinds were read with `llvm-readobj -r` before linking (see
`fixtures/aarch64/README.md`). A64-P3 and A64-P4 need no linker: A64-P3's operands
are all immediates and A64-P4's three targets are local labels in one section, so
`llvm-mc` resolves both itself and emits no relocations. A64-P7, A64-P8, A64-P9,
A64-P10, A64-P11, A64-P12, A64-P13, A64-P14, A64-P15, A64-P16, A64-P17, A64-P18 and
A64-P19
need no linker either: their operands are registers or immediates, and A64-P16's
two symbol targets are local instruction labels that `llvm-mc` resolves itself
(`EXP-0025` §3). The
fifty-seven negative fixtures (`N01` ×22, `N02` ×8, `N03` ×9, `N04c`, `N04d`,
`N12a`, `N14`, `N16` ×3, `N18` ×7, `N19` ×3, `N20`) exercise these tables with
exact diagnostic sets.

N18's `movz` case is the same "literal versus field" shape as `add`'s. `hw`
selects the lane, so `imm16` is field content in `0…65535` on every one of the
four rows; `0x12340000` on `-lsl16` is a pre-scaled literal and is
`E-RANGE-001` (`N18c`), not a switch to `-lsl32`. `llvm-mc` is the boundary here:
it rejects `movz x0, #0x12340000` outright ("immediate must be an integer in range
[0, 65535]") and accepts only `lsl #0/#16/#32/#48`, so the four rows are exactly
the four spellings (`EXP-0016` §2, ADR-0014). `N01d` is the other half: an
`lsl #8` lane has no row, so it is `E-FORM-001`, not a zero shift.

A64-P19 extends the same lane rule to the other two move-wide mnemonics. The
`opc` field is the mnemonic and the node fixes it, so `movk`/`movn` add four lanes
each and no plan field names the operation (`EC-16`, ADR-0026). `movn`'s operand
is the raw `imm16` field, not its complement: `movn x0, #0x1234` is `0x92824680`,
which is the `movz` word with the `opc` bits changed, and `llvm-objdump` reads it
back as `mov x0, #-0x1235` because the complement is the instruction's operation
(`EXP-0028` §2–§3). `imm16 = 65536` is `E-RANGE-001` (`N03-movk-imm16`), a
pre-scaled literal is the same error (`N18g`), a `w32` destination is
`E-OPERAND-001` (`N02i`, because the rows are the `sf = 1` node), and the `mov`
alias stays out because the literal's value chooses both the operation and the
lane (`mov x0, #0x1234` → `0xd2824680`, `mov x0, #-1` → `0x92800000`), which is
`E-FORM-001` (`N01w`) and `INV-02`. `N01t`/`N01v` name the two lanes no version
has (`-lsl8`, `w32`), and `N01u` is the `0.16.0` boundary for the `0.17.0` rows.

N03 and N04 gain their AArch64 cases from `b.cond`, and both are the "in range
but wrong field" shape. `cond = 16` is a legal number for a 4-bit-typed value but
not for a 4-bit field; masking it would give `0x0`, which is `eq` — a branch on
the opposite condition from the one a planner who wrote 16 presumably meant
(`EXP-0014` §2 measures the sixteen values). `imm19 = 262144` is the first value
past the signed 19-bit field, which is why the reachable displacement ends at
`+1048572` rather than `+1 MiB` (`EXP-0014` §3). The fixture states the
displacement as a field value instead of a fixup so the range check is the only
thing under test; the positive vector exercises the fixup path.

N03's load/store cases are the same shape one field over. `imm12` is `0…4095`
field units (the access size is the multiplier) and `imm9` is `−256…255` signed
bytes, so `4096` and `−257` have no encoding; there is no second form to fall
back to, because the kind is already the `form_id` (`EXP-0015` §2, ADR-0013).
The store rows repeat the same field on the other half of the family, so `−257`
on `str/x64-base-imm9-post` and `256` on `stur/x64-base-imm9` are the same
rejection (`EXP-0024` §2, ADR-0022).
`N01b` is the other half: `aarch64:ldr/x64-base-regoff` names an addressing kind
the table does not contain, so it is `E-FORM-001`, not a plan the materializer
silently reinterprets as an unsigned-offset load.

A64-P8 is the modifier case, and it splits into two different readings of one
spelling. `add x0, x1, x2, lsl #3` names a kind (`shift` at 23–22, three keywords
and no numeric spelling — `ror` is rejected and `11` is unallocated) and an amount
(`imm6` at 15–10, `0…63`). The keyword is a form and the amount is field content
(`EC-31`, ADR-0015), which is why `N03-imm6` is `E-RANGE-001` for `64` — there is
no second row to switch to, and no scale to apply. `N19` is the modifier-shaped
failure: the same shift stated as `{"name": "lsl", "value": 3}` on the `-lsl0` row
is `E-OPERAND-003`, because a modifier is a guard and never writes a bit; accepting
it silently would emit the unshifted word and report success. `N01e` is the scope
boundary: the extend family (`add x0, x1, w2, uxtw #3`, `0x8b224c20`) is a
different node with a `w` source operand, so it is `E-FORM-001` — absent from the
table, which is not the same claim as illegal (`EXP-0017` §1–§2).

A64-P10 is the widening case, and its boundary is the mnemonic rather than a
field. `sub` is not a value of anything: `SUB_64_addsub_shift` and
`SUB_64_addsub_imm` are the `ADD_64` nodes with `op` at bit 30 fixed to `1`, so
the six rows repeat the `add` shapes and differ only in that node (`ADR-0017`).
The three `E-FORM-001` fixtures are the three neighbours `0.8.0` does not
carry — `subs` (`S = 1`, bit 29: `0xeb020020`), `sub w0, w1, w2` (`sf = 0`:
`0x4b020020`, carried later by `0.10.0`, so `N01h` is a version-boundary
fixture) and `sub … uxtb` (bit 21 plus `option`, `N01f`) — and `N18d` is the
value-driven half: `llvm-mc` assembles `sub x0, x1, #0x1000` to the `-lsl12` word
`0xd1400420` without a diagnostic (`EXP-0019` §2), so the materializer has to
reject it on `-lsl0` instead. `sub sp, …` is the extended node as well
(`0xcb22603f`), which is why register 31 in these rows is `xzr`, not `sp`.

A64-P11 is the same widening one bit over, and it fixes where the alias line is.
`adds`/`subs` are the four nodes already read with `S` at bit 29 fixed to `1`
(`EXP-0020` §1), so the twelve rows repeat the `add`/`sub` shapes and differ only
in that node, exactly as `sub` differed in `op` (`ADR-0018`). `N01i` is the alias
boundary: `cmp x1, x2` is `subs xzr, x1, x2` (`0xeb02003f`) and `cmn x1, x2` is
`adds xzr, x1, x2` (`0xab02003f`), so each fixes `Rd = 31` and drops the
destination — a two-operand form family of its own, not a value of these rows;
`0.12.0` carries that family, so `N01i` (and `N01m`) now mark a version boundary
rather than an absence.
`N01j` is the width boundary (`adds w0, w1, w2` → `0x2b020020`), and `N18e` is
the value half: `llvm-mc` assembles `adds x0, x1, #0x1000` to
`0xb1400420` (`-lsl12`) without a diagnostic (`EXP-0020` §2), so the materializer
has to reject it on `-lsl0` instead. `adds x0, sp, x2` (`0xab2263e0`) and
`subs x0, sp, x2` (`0xeb2263e0`) are the extended S nodes, which `0.9.0` does not
carry, so register 31 in these rows is `xzr` as well.

A64-P12 is the width half of the same widening, and its boundary is both a
mnemonic bit and a register class. The eight `*_32*` nodes are the eight
`*_64*` nodes already read with `sf` at bit 31 fixed to `0` (`EXP-0021` §1), so
the twenty-four rows repeat the six shapes on each mnemonic and differ only in
that node (`ADR-0019`). `N01k` is the version boundary: the `w` row against
`0.9.0`, where it does not exist yet — `N01h` and `N01j` are the same shape
against `0.8.0`/`0.9.0`. `N02c` is the class boundary: the MRS spells every
shifted-node register `<Wd>`/`<Wn>`/`<Wm>` and `llvm-mc` rejects
`add w0, w1, x2`, so an `x64` operand on a `w` row is `E-OPERAND-001` on `kind`
and on `target_type` rather than a second reading of the same 5-bit number.
`N16d` is the field boundary: `imm6` is six bits but the 32-bit form allocates
only `0…31` (`lsl #32` is rejected, the `imm6 = 32` word does not decode), so
the slot carries `excluded: [32 … 63]` and `32` is `E-RANGE-004`. `N18f` is the
value half, unchanged from the 64-bit rows: `llvm-mc` assembles
`adds w0, w1, #4096` to `0x31400420` (`-lsl12`) without a diagnostic, so the
materializer has to reject it on `-lsl0` instead. Register 31 stays legal in
every slot and means what the node's role says — `wzr` on the shifted rows and
on `ADDS_32S`/`SUBS_32S` `Rd` (`0x3100143f` is `cmn w1, #5`), `wsp` on
`ADD_32`/`SUB_32` `Rd`/`Rn` and on `ADDS_32S`/`SUBS_32S` `Rn` — because the
encoding stores one number, so the vector uses registers 0–30 and the role
meanings are recorded in `EXP-0021` §2 instead.

A64-P13 is the mnemonic half of the extended layout. `SUB_64_addsub_ext`,
`ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext` are `ADD_64_addsub_ext` with
`op` at bit 30 and/or `S` at bit 29 fixed (`EXP-0022` §1), so the twenty-four
rows repeat the eight `add` extended rows three times and differ only in that
node (`ADR-0020`). The keyword keeps doing both jobs — `uxtb` … `sxtw` take a
`w` source, `uxtx`/`sxtx` an `x` one — so `N02d` is `E-OPERAND-001` on a new
row exactly as `N02b` was on the `add` rows, and `imm3 = 5` on a `subs` row is
`E-RANGE-004` (`N16e`), the same tail `N16c` pins for `add`. `N01l` is the
width boundary: the four `sf = 0` extended nodes are in no document, so
`sub w0, w1, w2, uxtb` has no row, unlike the shifted and immediate `w` rows
that `0.10.0` carries. Register 31 is not a form input here: `sub` spells `Rd`
`XdSP_option`, so `sub sp, x1, w2, uxtb #3` is `0xcb220c3f`, while both S nodes
spell it `XdOrXZR__6` and reject `adds sp, …`/`subs sp, …`, so
`subs xzr, x1, w2, uxtb #0` is the `cmp x1, w2, uxtb` word `0xeb22003f`; all
three spell `Rn` `XnSP_option`. Because the encoding stores one 5-bit number,
the plan states 31 and the node's role supplies the meaning, as on the `w`
rows (`EXP-0022` §2).

A64-P14 is the alias half of that layout. The twelve `CMP`/`CMN`
`Instruction.InstructionAlias` nodes name ten base nodes the table already reads
and carry no `encoding` at all (`EXP-0023` §1), so `0.12.0` builds each of the
forty rows from the base node with `Rd` pinned to 31 and the `dest` slot removed,
and uses the alias node only to check that the row names the right base node and
width (`ADR-0021` decisions 2–3). The bytes are therefore the `subs`/`adds`
words: `cmp x1, x2` is `0xeb02003f` and `cmn x1, #5` is `0xb100143f`
(`EXP-0023` §2). Two spellings are measured and not modelled: `cmp wsp, w2, lsl #3`
assembles to the **32-bit extended** word `0x6b224fff` (bit 21 = 1), which the
table does not carry — the same silent node switch `EXP-0022` measured on `sub` —
and `cmp x1, w2, uxtx #3` is accepted although `add x0, x1, w2, uxtx #0` is
rejected; the register number is the same 5-bit field, so the width rule stays
`ADR-0016`'s and the spelling difference adds no row (`EXP-0023` §3).
`N02e` is the operand-count boundary: a `dest` on `aarch64:cmp/x64-x64-lsl0` makes
three operands where the row has two, so it is `E-OPERAND-002` with `expected: 2`,
`found: 3` — the first shape in the table whose count differs from its base row.
`N01m` is the `cmn` half of the version boundary and the two 32-bit extended
aliases stay out with their base rows (`N01l`, `ADR-0021` decision 4).

A64-P15 is the store half of the same layout, and it needed nothing new. The
three nodes `STR_64_ldst_immpre`, `STR_64_ldst_immpost` and
`STUR_64_ldst_unscaled` are the load rows' field lists with `opc` at `00` and
`Rt` as the stored register (`EXP-0024` §1), so the rows reuse `src`/`base`/`disp`
and the `imm9` slot exactly as `0.4.0` defined them (`ADR-0022`). The store
mnemonic is as unreliable as the load one: `str x0, [x1, #1]` assembles to
`0xf8001020`, which reads back as `stur` (`EXP-0024` §2), so the kind has to stay
in the `form_id` rather than follow the offset's value (`INV-02`, `EC-14`). The
vector puts both ends of `imm9` on both writeback rows and both signs on `stur`,
and repeats the `imm12` row at `0` and `4095` so a change to the store half that
moved the offset row would show up in the same 32 bytes. `N03` pins the two
range ends on the new rows and `N01n` is the version boundary: the id exists from
`0.13.0` on, and a plan bound to `0.12.0` is `E-FORM-001`.

A64-P16 is the first row in the family whose operand list changes. `LDR_64_loadlit`
has no `Rn` at all — the fixed pattern is `0x58000000` and the only variable
fields are `imm19` at 5+19 and `Rt` at 0+5 (`EXP-0025` §1) — so the row declares
`dest` and `target` and nothing else; a third operand is `E-OPERAND-002` by the
count rule `N02e` pins. `imm19` is field content in 4-byte units, so the six-value
vector states `2`, `-1`, `262143`, `-262144`, `-4` and `1`, and the two symbol
targets go through `pcrel_begin` + `scale(2)` fixups whose `+2` and `−4` results
are what `llvm-mc` emitted for labels 8 bytes ahead and 16 bytes behind
(`EXP-0025` §3). Two diagnostics are new to this row: `N04d` is an `imm19` value
one past the field (`262144`, `E-RANGE-002`), and `N20` is a symbol offset that is
not a multiple of 4 (`2`, `E-RANGE-003` at `/fixups/0/value_transform`). The
assembler reports both as one message; the split is `OD-09`'s and is our own
(`ADR-0023` decision 6).

A64-P17 completes the load/store addressing kinds. The register-offset nodes have
three variable fields where the offset rows had one: `Rm` at 16+5, `option` at
13+3 and `S` at 12+1 (`EXP-0026` §1). `option` and `S` are pinned, so a plan
cannot choose them: `option` fixes the index's width (`w` for `uxtw`/`sxtw`, `x`
for `lsl`/`sxtx`) as well as its extension, and `S` is the only scale carrier, so
`lsl #0` and `lsl #3` are two rows rather than one row with an amount operand.
The vector states all sixteen combinations once and then puts 31 in `Rn` or `Rm`,
so `sp`/`xzr`/`wzr` are pinned by the same words. `N02f` is the slot-width
mismatch, `N19b` the modifier-shaped attempt to state `S` as an operand, `N01q`
the `-lsl1` spelling that has no row, and `N01p` the version boundary: `0.14.0`
predates the rows (`ADR-0024`).

A64-P18 is the same three-variable-field shape at `size = 10`, and the point is
what does *not* change: `Rm`, `option` and `S` keep their positions and meanings,
so the sixteen rows differ from A64-P17 only in the template's top bits and in
what `S = 1` names — `#2`, because the access is 4 bytes (`EXP-0027` §1–§2). The
one slot that changes class is `Rt`, which is `w` on both mnemonics while `Rn` and
`Rm` stay `x`; the vector therefore mixes a `w32` destination with an `x64` base
and index in every row and still pins 31 in each role. `N02g` is the `w32` index
mismatch, `N02h` the `x64` destination mismatch, `N19c` the modifier-shaped
attempt to state `S` as an operand, `N01s` the `-lsl3` spelling that has no row at
this width, and `N01r` the version boundary: `0.15.0` predates the rows
(`ADR-0025`).

### RV64 (directive §6.3)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| RV-P1 | Standard integer arithmetic | `add` (R-type) | llvm-mc | **passing** — `rv64/positive/RV-P1-add-register` |
| RV-P2 | I-type immediate | `addi` imm12 | llvm-mc | **passing** — `RV-P2-addi-imm12` (both signed endpoints) |
| RV-P3 | Load/store | `ld`/`sd` base+offset, decomposed into `base` + `disp` | llvm-mc | **passing** — `rv64/positive/RV-P3-ld-sd-base-offset` (four instructions, signed imm12 endpoints) |
| RV-P4 | Conditional branch | `beq` B-type scatter | llvm-mc | **passing** — `RV-P4-beq-btype` (+8 and −8) |
| RV-P5 | Control transfer | `jal` J-type scatter | llvm-mc | **passing** — `RV-P5-jal-jtype` (+8 and −8) |
| RV-P6 | Scattered fields | B-type and J-type bit placement verified byte-for-byte | llvm-mc | **passing** with `RV-P4`/`RV-P5`; `beq` uses four placements, `jal` four |
| RV-P7 | Compressed vs standard | `c.addi` (2 bytes) vs `addi` (4 bytes), never chosen by the encoder | llvm-mc | **passing** — `RV-P7-caddi` (four immediates), with `N16a`/`N16b` rejecting the zero cases |
| RV-P8 | Associated reference | `auipc`+`addi` pair with `hi20`/`lo12` | llvm-mc + llvm-readobj + ld.lld | **passing** — `RV-P8-auipc-imm20` covers the form's field; `RV-P8-pcrel-pair` the 1:N group (three records); `RV-P8-pcrel-pair-resolved` the arithmetic against a linked binary |

The source is pinned (`OD-12`, ADR-0007): the UDB resolved-spec nodes named in
`check_rv64_source.py`, with `EXP-0009` deriving the B/J/RVC placements and
matching fourteen `llvm-mc` byte strings. `EXP-0010` generated
`definitions/rv64/0.1.0.json` (seven base-`I` forms, digest
`sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083`)
and `0.2.0` (the same seven plus `c.addi`, digest
`sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10`)
from eight of those nodes and re-encoded the probe vectors from each table it
built; the positive fixtures above are the independent gate, and the
negative fixtures (`N01`, `N01c`, `N02`, `N03`, `N04`, `N15`, `N16a`/`N16b`,
`N17a`/`N17b`/`N17c`) pin the rejection paths.

`RV-P3` is carried by two forms (`riscv:ld/rd-base-imm12`, `riscv:sd/rs-base-imm12`)
built from the `RV64` encoding block of `I/ld.yaml` (sha256:a2afcd44…) and
`I/sd.yaml` (sha256:f0b69996…). The address is three operands, not one memory
payload (`ADR-0008`, `OD-13`): `dest`/`src`, `base` and `disp`. `sd` scatters its
12-bit immediate over `[31:25]` and `[11:7]`, so the decomposition is also the
reason the scatter is field-derived. `N15` pins the rejected alternative: a
`{"mem": …}` payload is `E-OPERAND-003` at read time.

`RV-P7` is carried by `riscv:c.addi/rd-imm6` in `0.2.0`, built from
`inst/C/c.addi.yaml` (sha256 pinned by `check_rv64_source.py`). The node states
`not: 0` on `imm` and `xd`; `ADR-0009`/`OD-14` turn that into `excluded: [0]` on
both slots, and `EXP-0012` §2 measured the alternative — `c.addi a0, 0` encodes
`01 05` (`c.addi a0, 0x0`) and `c.addi x0, 1` encodes `05 00` (`c.nop 0x1`), both
reserved HINTs. `N16a`/`N16b` pin `E-RANGE-004`; `N01c` pins that naming the form
against `0.1.0` is `E-FORM-001`, not a silent fallback to `addi`.

`RV-P8`'s pair half was blocked on the format, not the source. The psABI states
the `R_RISCV_PCREL_HI20`/`LO12_I` relation and the encoding blocks do not; ADR-0010
turns the four normative statements (`riscv-elf.adoc:1578-1605`, `:1184`, `:1186`)
into `pc_reference_rule: pcrel_hi`, `value_transform: pcrel_lo12`, `E-FIXUP-009`
and a 1:N group. Two fixtures carry it. `RV-P8-pcrel-pair` is the unlinked gate:
one `auipc`, one `addi` and one `sd`, all `emit_relocation`, so the group is one
`hi` and two `lo`, and the oracle is the object file's three records. The S-type
member also measures ADR-0010 decision 3 — `llvm-mc` emits `R_RISCV_PCREL_LO12_S`
for the same `pcrel_lo12` value. `RV-P8-pcrel-pair-resolved` is the arithmetic
gate: `auipc` at 4, `blob` at 0x1000, both fixups `resolve_in_place`, and the
linked words `0x00001517` / `0xFFC50513` equal `(0x1000 - 4 + 0x800) >> 12 = 1`
and `(0x1000 - 4) & 0xFFF = 0xFFC`. The three alternatives give three different
words (`lo12_i` → 0x000, `pcrel_begin` on the `lo` → 0xFF8, no `+0x800` → 0), so
the fixture distinguishes the rule rather than merely agreeing with it. `N17a`
pins the rejected low-half addend, `N17b` the rejected `pcrel_hi` without a `lo`
role, and `N17c` the rejected `lo` in another section: `S` and `P_hi` would then
be offsets into unrelated origins, so the mask would hide a coordinate-system
error instead of reporting it.

## 5. Gate G3

G3 passes when each ISA has at least three positive vectors with matching oracle
bytes and two negative vectors with registry codes, all reproducible from a clean
checkout with the recorded toolchain versions.
