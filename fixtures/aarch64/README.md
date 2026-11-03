# AArch64 fixtures

Vectors: `A64-P1` … `A64-P8` in `docs/fmp-v0/06_validation_matrix.md`.

## What is here

| Fixture | Form(s) | Oracle |
|---|---|---|
| `positive/A64-P1-add-register` | `aarch64:add/x64-x64-x64-lsl0` ×3 | `llvm-mc` |
| `positive/A64-P2-add-imm12` | `aarch64:add/x64-imm12-lsl0` ×2, imm 0 and 4095 | `llvm-mc` |
| `positive/A64-P2-add-imm12-lsl12` | `aarch64:add/x64-imm12-lsl12` ×4 (`0.2.0`), field content 0, 1, 291, 4095 | `llvm-mc` |
| `positive/A64-P5-bl-local-symbol` | `aarch64:bl/imm26` ×2, +4 and −4 | `llvm-mc` + `ld.lld` |
| `positive/A64-P6-adrp-lo12-pair` | `aarch64:adrp/x64-imm21` + `aarch64:add/x64-imm12-lsl0`, one `pair_group` | `llvm-mc` + `ld.lld`; relocation kinds read with `llvm-readobj` |
| `negative/N01-absent-scaled-form` | `aarch64:add/x64-imm12-lsl12` against `0.1.0`, which lacks it | `E-FORM-001` |
| `negative/N03-imm12-out-of-range` | imm12 = 4096 | `E-RANGE-001` |
| `negative/N12a-pair-without-lo` | two `hi` members in one `pair_group` | `E-FIXUP-007` |
| `negative/N14-register-wider-than-field` | register 32 in a 5-bit field | `E-OPERAND-004` |
| `negative/N18a-no-form-switch` | `0x1000` stated on `-lsl0` (legal only as a scaled literal) | `E-RANGE-001` |
| `negative/N18b-operand-is-field-content` | `0x123000` stated on `-lsl12` (a pre-scaled literal) | `E-RANGE-001` |

`N01` is why the split matters: the scaled form exists, but not in `0.1.0`, so a
plan bound to `0.1.0` still cannot reach it. The two fixtures that use the
scaled form name `0.2.0` and its digest.

Not yet covered: `A64-P3` (load/store), `A64-P4` (conditional branch), `A64-P7`
(scattered field) and `A64-P8` (shift/extend modifier). They have no form in
either document, so `N01` rejects them rather than guessing. A linked `:lo12:`
inside the `-lsl12` form is measured at the record level (`EXP-0013` §5) but is
not an address of the symbol, so no fixture links one.

## Two things a reader of the plans should know

**A scaled field carries its field content, not a byte offset.** `bl`'s `imm26`
and `adrp`'s `imm21` are not byte counts: the ISA divides by 4 and by 4096. A
`{ "value": n }` payload on those slots is written to the field as `n`, because a
definition slot has no scaling transform. A byte offset is expressed with a
fixup instead — `scale` with `transform_shift: 2` for `bl`, `page` for `adrp` —
which is the only path that performs the division. Both fixtures use the fixup
path; `A64-P1`/`P2` use plain values on non-scaled fields.

The same rule covers the scaled immediate: `A64-P2-add-imm12-lsl12` holds
`imm12` content (0…4095) and the form's `sh = 1` does the `<< 12`. Stating
`0x1000` there, or stating it on `-lsl0`, is `E-RANGE-001` (`N18a`/`N18b`), never
a form switch.

**An operand whose bits a fixup owns has an empty payload.** `{"payload": {}}`,
not a `symbol_id`: `01_contract.md` §8.1 only allows `symbol_id` on a `target`
role. In `A64-P6` the `add`'s `imm12` is such a slot, and the symbol is named
once, by the fixup.

## Oracle notes

`llvm-mc` does not resolve AArch64 branches or `adrp`: it emits zero bytes plus a
fixup (`fixup_aarch64_pcrel_call26`, `fixup_aarch64_pcrel_adrp_imm21`,
`fixup_aarch64_add_imm12`). For `A64-P5` and `A64-P6` the oracle is therefore
`llvm-mc` → `ld.lld --image-base=0 -Ttext=0` → `llvm-objcopy`, i.e. the bytes the
LLVM toolchain produces for the same `(S, P)` pair after its own linker resolved
them. The `.oracle.json` files record the exact commands and both hashes.

`adrp`'s `immlo` occupies bits 30:29, so an immediate of 1 is `0x2000_0000`, not
`0x20`; `llvm-objdump` prints `b0000000` for it. The oracle caught that during
generation, which is why `A64-P6` compares the whole word.

See `../README.md` for naming and oracle rules.
