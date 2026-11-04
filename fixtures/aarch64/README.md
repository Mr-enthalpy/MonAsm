# AArch64 fixtures

Vectors: `A64-P1` … `A64-P10` in `docs/fmp-v0/06_validation_matrix.md`.

## What is here

| Fixture | Form(s) | Oracle |
|---|---|---|
| `positive/A64-P1-add-register` | `aarch64:add/x64-x64-x64-lsl0` ×3 | `llvm-mc` |
| `positive/A64-P2-add-imm12` | `aarch64:add/x64-imm12-lsl0` ×2, imm 0 and 4095 | `llvm-mc` |
| `positive/A64-P2-add-imm12-lsl12` | `aarch64:add/x64-imm12-lsl12` ×4 (`0.2.0`), field content 0, 1, 291, 4095 | `llvm-mc` |
| `positive/A64-P3-ldst-addressing` | `aarch64:ldr/x64-base-imm12` ×2 (`0.4.0`), `ldr/x64-base-imm9-pre`, `ldr/x64-base-imm9-post`, `ldur/x64-base-imm9`, `str/x64-base-imm12`; six instructions, 24 B | `llvm-mc` (no linker: immediates only, no relocations) |
| `positive/A64-P4-b-cond` | `aarch64:b.cond/imm19` ×3 (`0.3.0`), `b.eq` +4, `b.ne` −4, `b.gt` −8 | `llvm-mc` (no linker: local labels, no relocations) |
| `positive/A64-P5-bl-local-symbol` | `aarch64:bl/imm26` ×2, +4 and −4 | `llvm-mc` + `ld.lld` |
| `positive/A64-P6-adrp-lo12-pair` | `aarch64:adrp/x64-imm21` + `aarch64:add/x64-imm12-lsl0`, one `pair_group` | `llvm-mc` + `ld.lld`; relocation kinds read with `llvm-readobj` |
| `positive/A64-P7-movz-lane` | `aarch64:movz/x64-imm16-lsl0` ×2, `-lsl16`, `-lsl32`, `-lsl48` (`0.5.0`); five instructions, 20 B | `llvm-mc` (no linker: immediates only, no relocations) |
| `positive/A64-P8-shift-modifier` | `aarch64:add/x64-x64-x64-imm6-lsl`, `-imm6-lsr`, `-imm6-asr` (`0.6.0`); six instructions, 24 B | `llvm-mc` (no linker: registers and immediates only, no relocations) |
| `positive/A64-P9-extend-modifier` | six `aarch64:add/x64-x64-w32-imm3-*` rows and `-x64-imm3-uxtx`/`-imm3-sxtx` (`0.7.0`); eight instructions, 32 B | `llvm-mc` (no linker: registers and immediates only, no relocations) |
| `positive/A64-P10-sub-family` | `aarch64:sub/x64-x64-x64-lsl0`, `sub/x64-imm12-lsl0` at 4095, `sub/x64-imm12-lsl12` at 291, `sub/x64-x64-x64-imm6-lsl`/`-lsr`/`-asr` (`0.8.0`); six instructions, 24 B | `llvm-mc` (no linker: registers and immediates only, no relocations) |
| `negative/N01-absent-scaled-form` | `aarch64:add/x64-imm12-lsl12` against `0.1.0`, which lacks it | `E-FORM-001` |
| `negative/N01b-absent-register-offset-form` | `aarch64:ldr/x64-base-regoff` (`0.4.0` has no such form) | `E-FORM-001` |
| `negative/N01d-absent-movz-lane` | `aarch64:movz/x64-imm16-lsl8` (`0.5.0` has four lanes, not eight) | `E-FORM-001` |
| `negative/N01e-absent-extend-form` | `aarch64:add/x64-x64-w64-uxtw-imm3`, an extend spelling against `0.6.0` | `E-FORM-001` |
| `negative/N01f-absent-sub-ext` | `aarch64:sub/x64-x64-w32-imm3-uxtb` (`0.8.0` has the immediate and shifted `sub` nodes, not the extended one) | `E-FORM-001` |
| `negative/N01g-absent-flag-form` | `aarch64:subs/x64-x64-x64-lsl0` (`S = 1` is a different node) | `E-FORM-001` |
| `negative/N01h-absent-32bit-form` | `aarch64:sub/w32-w32-w32-lsl0` (`sf = 0` is a different node) | `E-FORM-001` |
| `negative/N02b-w-source-in-shift-form` | a `w32` operand on the `x`-source `-imm6-lsl` row | `E-OPERAND-001` (kind and target_type) |
| `negative/N03-imm12-out-of-range` | imm12 = 4096 | `E-RANGE-001` |
| `negative/N03-imm12-disp-out-of-range` | `disp = 4096` on the load/store `imm12` field | `E-RANGE-001` |
| `negative/N03-imm9-disp-out-of-range` | `disp = −257` on the `imm9` field | `E-RANGE-001` |
| `negative/N03-cond-out-of-range` | `cond = 16` in a 4-bit field | `E-RANGE-001` |
| `negative/N03-imm6-out-of-range` | `imm6 = 64`, one past the shift amount's 6-bit field | `E-RANGE-001` |
| `negative/N03-imm3-out-of-range` | `imm3 = 8`, one past the extend amount's 3-bit field | `E-RANGE-001` |
| `negative/N04c-bcond-imm19-out-of-range` | `imm19 = 262144`, one past the signed 19-bit field | `E-RANGE-002` |
| `negative/N12a-pair-without-lo` | two `hi` members in one `pair_group` | `E-FIXUP-007` |
| `negative/N14-register-wider-than-field` | register 32 in a 5-bit field | `E-OPERAND-004` |
| `negative/N18a-no-form-switch` | `0x1000` stated on `-lsl0` (legal only as a scaled literal) | `E-RANGE-001` |
| `negative/N18b-operand-is-field-content` | `0x123000` stated on `-lsl12` (a pre-scaled literal) | `E-RANGE-001` |
| `negative/N18c-movz-pre-scaled-literal` | `0x12340000` stated on `movz/x64-imm16-lsl16` (a pre-scaled literal) | `E-RANGE-001` |
| `negative/N18d-sub-no-form-switch` | `4096` stated on `sub/x64-imm12-lsl0` (encodable only as `-lsl12`) | `E-RANGE-001` |
| `negative/N16c-imm3-excluded` | `imm3 = 5`, inside the 3-bit field but not allocated to `add` extended | `E-RANGE-004` |
| `negative/N19-modifier-is-not-a-carrier` | `{"name": "lsl", "value": 3}` in a `modifiers` entry on `aarch64:add/x64-x64-x64-lsl0` | `E-OPERAND-003` |

`N01` is why the version split matters: a form exists, but not in an older
document, so a plan bound to `0.1.0` still cannot reach `-lsl12`, a plan bound
to `0.2.0` cannot reach `b.cond`, a plan bound to `0.3.0` cannot reach the
load/store rows, a plan bound to `0.4.0` cannot reach the `movz` lanes, a plan
bound to `0.5.0` cannot reach the shift rows, a plan bound to `0.6.0` cannot
reach the extend rows, and a plan bound to `0.7.0` cannot reach the `sub` rows.
Each fixture names the document it targets and that
document's digest.

`subs`, the `w`-width rows, the extended `sub` node, the load/store
register-offset and literal kinds, and
the store's `imm9` kinds are absent for the same reason. A linked `:lo12:` inside
the `-lsl12` form is measured at the record level (`EXP-0013` §5) but is not an
address of the symbol, so no fixture links one.

## Two things a reader of the plans should know

**A scaled field carries its field content, not a byte offset.** `bl`'s `imm26`
and `adrp`'s `imm21` are not byte counts: the ISA divides by 4 and by 4096. A
`{ "value": n }` payload on those slots is written to the field as `n`, because a
definition slot has no scaling transform. A byte offset is expressed with a
fixup instead — `scale` with `transform_shift: 2` for `bl`, `page` for `adrp` —
which is the only path that performs the division. Both branch fixtures use the
fixup path. `A64-P1`/`P2` state plain values on fields that are not scaled at
all; `A64-P3` states field content too, even though its `imm12` is scaled in the
ISA, because the multiplier belongs to the field and not to a slot transform.

The same rule covers the scaled immediate: `A64-P2-add-imm12-lsl12` holds
`imm12` content (0…4095) and the form's `sh = 1` does the `<< 12`. Stating
`0x1000` there, or stating it on `-lsl0`, is `E-RANGE-001` (`N18a`/`N18b`), never
a form switch. `A64-P10` repeats both halves on `sub` (`0.8.0`): 291 on
`-imm12-lsl12` is field content, 4095 on `-imm12-lsl0` is the field's top, and
4096 on `-imm12-lsl0` is `E-RANGE-001` (`N18d`).

The load/store rows are the third instance. Their `disp` is the field, so the
unit is per row: the two unsigned-offset rows count 8-byte units for the `x`
width, which is why `A64-P3` states `2` for `#16` and `4095` for `#32760`, while
the `imm9` rows count signed bytes (`8`, `−8`, `−256`). Stating a byte offset on
an `imm12` row would address eight times too far and still emit four legal bytes,
which is the same-length hazard `expected_digest` (`OD-01`) exists for
(`ADR-0013`).

The `movz` rows are the fourth instance, with the multiplier selected by a field
instead of fixed: `imm16` is the field content and `hw` is the exponent, so
`A64-P7-movz-lane` states `4660` on both `-lsl0` and `-lsl16` and the two words
differ only in bits 22–21. Stating the pre-scaled literal (`0x12340000`) on
`-lsl16` is `E-RANGE-001` (`N18c`), and `lsl #8` is not a lane the ISA has, so it
is `E-FORM-001` (`N01d`, `ADR-0014`).

The shift rows are the fifth instance, and the one where a single spelling is two
decisions at once. `imm6` is the field content (`0…63`, no multiplier), and the
keyword selects the row: `lsl #3`, `lsr #7` and `asr #63` differ in bits 23–22 and
nothing else about their operands. The keyword cannot be carried by a `modifiers`
entry — a modifier is a guard in v0 — so the same shift stated as
`{"name": "lsl", "value": 3}` on `-lsl0` is `E-OPERAND-003` (`N19`), and an amount
of `64` is `E-RANGE-001` (`N03-imm6`). `lsl #0` and `-lsl0` are the same word
(`0x8b020020`), so both rows stay (`ADR-0015`, `EXP-0017`).

The extend rows are the sixth instance, and the one where the keyword also decides
the source's width. `A64-P9` uses six `w`-source rows and two `x`-source rows;
`imm3` is the field content (`0…4`), so `8` is `E-RANGE-001` (`N03-imm3`) and `5`
is `E-RANGE-004` (`N16c`), because the values `5`–`7` fit the three-bit field but
are unallocated. Because the encoded register is the same 5-bit number either way,
the class cannot be a plan field: a `w32` operand on an `x`-source row is
`E-OPERAND-001` (`N02b`), which is also what a shifted row says about a `w`
source (`ADR-0016`, `EXP-0018`).

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
