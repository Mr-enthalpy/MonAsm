# AArch64 fixtures

Vectors: `A64-P1` … `A64-P16` in `docs/fmp-v0/06_validation_matrix.md`.

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
| `positive/A64-P11-adds-subs-family` | `aarch64:adds/x64-x64-x64-lsl0`, `adds/x64-imm12-lsl0` at 4095, `adds/x64-imm12-lsl12` at 291, `adds/x64-x64-x64-imm6-lsl`/`-lsr`/`-asr`, and the same six `subs/…` rows (`0.9.0`); twelve instructions, 48 B | `llvm-mc` (no linker: registers and immediates only, no relocations) |
| `positive/A64-P12-w-rows` | `aarch64:add/w32-w32-w32-lsl0`, `add/w32-imm12-lsl0` at 4095, `add/w32-imm12-lsl12` at 291, `add/w32-w32-w32-imm6-lsl`/`-lsr`/`-asr`, and the same six `sub/…`, `adds/…` and `subs/…` rows (`0.10.0`); twenty-four instructions, 96 B, registers 0–30 | `llvm-mc` (no linker: registers and immediates only, no relocations) |
| `positive/A64-P13-ext-family` | the eight `aarch64:sub/x64-x64-*-imm3-*` rows, the eight `adds/…` rows and the eight `subs/…` rows (`0.11.0`), plus `sub sp, x1, w2, uxtb #3`, `adds x0, sp, w1, uxtb` and `subs xzr, x1, w2, uxtb #0`; twenty-seven instructions, 108 B | `llvm-mc` (no linker: registers and immediates only, no relocations) |
| `positive/A64-P14-cmp-cmn-family` | the forty `aarch64:cmp/…`/`cmn/…` rows (`0.12.0`): four shifted and two immediate rows on each width, the eight `option` rows on `x64`, plus seven register-31 rows (`cmp sp, #5`, `cmp wsp, #5`, `cmp sp, x2`, `cmn sp, #5`, `cmn sp, x2`, `cmp x1, xzr`, `cmp w1, wzr`); forty-seven instructions, 188 B | `llvm-mc` (no linker: registers and immediates only, no relocations) |
| `positive/A64-P15-store-imm9-addressing` | `aarch64:str/x64-base-imm9-pre` ×2 (`0.13.0`), `str/x64-base-imm9-post` ×2, `stur/x64-base-imm9` ×2, and `str/x64-base-imm12` ×2 at 0 and 4095; eight instructions, 32 B | `llvm-mc` (no linker: immediates only, no relocations) |
| `positive/A64-P16-loadlit` | `aarch64:ldr/x64-imm19` ×6 (`0.14.0`): two symbol targets and four plain field values, both ends of `imm19` included; six instructions, 24 B | `llvm-mc` (no linker: local instruction labels, no relocations) |
| `negative/N01-absent-scaled-form` | `aarch64:add/x64-imm12-lsl12` against `0.1.0`, which lacks it | `E-FORM-001` |
| `negative/N01b-absent-register-offset-form` | `aarch64:ldr/x64-base-regoff` (`0.4.0` has no such form) | `E-FORM-001` |
| `negative/N01d-absent-movz-lane` | `aarch64:movz/x64-imm16-lsl8` (`0.5.0` has four lanes, not eight) | `E-FORM-001` |
| `negative/N01e-absent-extend-form` | `aarch64:add/x64-x64-w64-uxtw-imm3`, an extend spelling against `0.6.0` | `E-FORM-001` |
| `negative/N01f-absent-sub-ext` | `aarch64:sub/x64-x64-w32-imm3-uxtb` against `0.7.0`, before any document carried the extended `sub` row (the boundary moved to `0.11.0`) | `E-FORM-001` |
| `negative/N01g-absent-flag-form` | `aarch64:subs/x64-x64-x64-lsl0` against `0.8.0` (`S = 1` is a different node; the row lands in `0.9.0`) | `E-FORM-001` |
| `negative/N01h-absent-32bit-form` | `aarch64:sub/w32-w32-w32-lsl0` (`sf = 0` is a different node) | `E-FORM-001` |
| `negative/N01i-absent-cmp-alias` | `aarch64:cmp/x64-x64-lsl0` against `0.11.0`, where the alias family is not yet in the table | `E-FORM-001` |
| `negative/N01j-absent-flag-32bit-form` | `aarch64:adds/w32-w32-w32-lsl0` (`sf = 0` on the `S = 1` node is still a different node) | `E-FORM-001` |
| `negative/N01k-absent-w-form` | `aarch64:add/w32-w32-w32-lsl0` against `0.9.0`, which does not have the `w` rows yet | `E-FORM-001` |
| `negative/N01l-absent-32bit-ext-form` | `aarch64:sub/w32-w32-w32-imm3-uxtb`, one of the four `sf = 0` extended nodes, in no document | `E-FORM-001` |
| `negative/N01m-absent-cmn-alias` | `aarch64:cmn/x64-imm12-lsl0` against `0.11.0`, the `cmn` half of `N01i` | `E-FORM-001` |
| `negative/N01n-absent-store-imm9-form` | `aarch64:str/x64-base-imm9-pre` against `0.12.0`, which does not have the store `imm9` rows yet | `E-FORM-001` |
| `negative/N01o-absent-loadlit-form` | `aarch64:ldr/x64-imm19` against `0.13.0`, which does not have the literal row yet | `E-FORM-001` |
| `negative/N02b-w-source-in-shift-form` | a `w32` operand on the `x`-source `-imm6-lsl` row | `E-OPERAND-001` (kind and target_type) |
| `negative/N02c-x-dest-on-w-row` | an `x64` destination on `aarch64:add/w32-w32-w32-lsl0` | `E-OPERAND-001` (kind and target_type) |
| `negative/N02d-ext-x-source-on-w-keyword` | an `x64` source on `aarch64:sub/x64-x64-w32-imm3-uxtb` | `E-OPERAND-001` (kind and target_type) |
| `negative/N02e-dest-on-cmp-row` | a `dest` operand passed to `aarch64:cmp/x64-x64-lsl0`, whose slots are `src` and `src2` only | `E-OPERAND-002` (`expected: 2`, `found: 3`) |
| `negative/N03-imm12-out-of-range` | imm12 = 4096 | `E-RANGE-001` |
| `negative/N03-imm12-disp-out-of-range` | `disp = 4096` on the load/store `imm12` field | `E-RANGE-001` |
| `negative/N03-imm9-disp-out-of-range` | `disp = −257` on the `ldur` `imm9` field | `E-RANGE-001` |
| `negative/N03-str-imm9-post-disp-out-of-range` | `disp = −257` on `str/x64-base-imm9-post` | `E-RANGE-001` |
| `negative/N03-stur-imm9-disp-out-of-range` | `disp = 256` on `stur/x64-base-imm9` | `E-RANGE-001` |
| `negative/N03-cond-out-of-range` | `cond = 16` in a 4-bit field | `E-RANGE-001` |
| `negative/N03-imm6-out-of-range` | `imm6 = 64`, one past the shift amount's 6-bit field | `E-RANGE-001` |
| `negative/N03-imm3-out-of-range` | `imm3 = 8`, one past the extend amount's 3-bit field | `E-RANGE-001` |
| `negative/N04c-bcond-imm19-out-of-range` | `imm19 = 262144`, one past the signed 19-bit field | `E-RANGE-002` |
| `negative/N04d-loadlit-imm19-out-of-range` | `imm19 = 262144` on the literal row, one past the same signed field | `E-RANGE-002` |
| `negative/N12a-pair-without-lo` | two `hi` members in one `pair_group` | `E-FIXUP-007` |
| `negative/N14-register-wider-than-field` | register 32 in a 5-bit field | `E-OPERAND-004` |
| `negative/N18a-no-form-switch` | `0x1000` stated on `-lsl0` (legal only as a scaled literal) | `E-RANGE-001` |
| `negative/N18b-operand-is-field-content` | `0x123000` stated on `-lsl12` (a pre-scaled literal) | `E-RANGE-001` |
| `negative/N18c-movz-pre-scaled-literal` | `0x12340000` stated on `movz/x64-imm16-lsl16` (a pre-scaled literal) | `E-RANGE-001` |
| `negative/N18d-sub-no-form-switch` | `4096` stated on `sub/x64-imm12-lsl0` (encodable only as `-lsl12`) | `E-RANGE-001` |
| `negative/N18e-adds-no-form-switch` | `4096` stated on `adds/x64-imm12-lsl0` (encodable only as `-lsl12`) | `E-RANGE-001` |
| `negative/N18f-w-adds-no-form-switch` | `4096` stated on `adds/w32-imm12-lsl0` (encodable only as `-lsl12`) | `E-RANGE-001` |
| `negative/N16c-imm3-excluded` | `imm3 = 5`, inside the 3-bit field but not allocated to `add` extended | `E-RANGE-004` |
| `negative/N16d-w-imm6-excluded` | `imm6 = 32` on `add/w32-w32-w32-imm6-lsl`, inside the 6-bit field but not allocated to the 32-bit instruction | `E-RANGE-004` |
| `negative/N16e-ext-imm3-excluded` | `imm3 = 5` on `subs/x64-x64-w32-imm3-sxtb`, inside the 3-bit field but not allocated to the extended layout | `E-RANGE-004` |
| `negative/N19-modifier-is-not-a-carrier` | `{"name": "lsl", "value": 3}` in a `modifiers` entry on `aarch64:add/x64-x64-x64-lsl0` | `E-OPERAND-003` |
| `negative/N20-loadlit-fixup-misaligned` | a `pcrel_begin` literal-load fixup whose symbol is 2 bytes away, so the displacement is not a multiple of 4 | `E-RANGE-003` (`required_align 2`, `value 2`) |

`N01` is why the version split matters: a form exists, but not in an older
document, so a plan bound to `0.1.0` still cannot reach `-lsl12`, a plan bound
to `0.2.0` cannot reach `b.cond`, a plan bound to `0.3.0` cannot reach the
load/store rows, a plan bound to `0.4.0` cannot reach the `movz` lanes, a plan
bound to `0.5.0` cannot reach the shift rows, a plan bound to `0.6.0` cannot
reach the extend rows, a plan bound to `0.7.0` cannot reach the `sub` rows, a
plan bound to `0.8.0` cannot reach the `adds`/`subs` rows (which is what `N01g`
now shows for `subs`), a plan bound to `0.9.0` cannot reach the `w` rows
(`N01k`), a plan bound to `0.10.0` cannot reach the extended
`sub`/`adds`/`subs` rows (`N01f`), a plan bound to `0.11.0` cannot reach the
`cmp`/`cmn` rows (`N01i`, `N01m`), a plan bound to `0.12.0` cannot reach the
store `imm9` rows (`N01n`), and a plan bound to `0.13.0` cannot reach the
literal load (`N01o`). `N01h` and `N01j` are the same shape one
version earlier for the `w`
rows of `0.8.0`/`0.9.0`.
Each fixture names the document it targets and that
document's digest.

The extended `sf = 0` nodes (`add w0, wsp, w1` is the extended node)
and the load/store
register-offset kind are absent for the same reason. A linked
`:lo12:` inside
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
4096 on `-imm12-lsl0` is `E-RANGE-001` (`N18d`). `A64-P11` repeats it once more
on the `S = 1` rows: `adds` and `subs` take 4095 and 291<<12 as field content,
and 4096 on `adds/x64-imm12-lsl0` is `E-RANGE-001` (`N18e`).

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

The mnemonic rows are the seventh instance, and the one where a letter, not a
bit, is the decision. `A64-P10`/`A64-P11` show that `sub`, `adds` and `subs` are
not values of an operand: each is a different MRS node, with `op` or `S` fixed by
the node, so the `form_id`'s mnemonic component carries it and no plan field can
move the bit. The `0.9.0` rows repeat the `add`/`sub` shapes one bit over
(`0x8b…`→`0xab…`, `0xcb…`→`0xeb…`, `0x91…`→`0xb1…`, `0xd1…`→`0xf1…`); `cmp` and
`cmn` are a two-operand alias family of their own, carried by `0.12.0` and
described as the tenth instance below.

The width rows are the eighth instance, and the one where no operand at all can
carry the decision. `A64-P12` repeats all six shapes on the eight `sf = 0` nodes,
so every word is its `x64` twin with bit 31 cleared (`0x8b…`→`0x0b…`,
`0xcb…`→`0x4b…`, `0xab…`→`0x2b…`, `0xeb…`→`0x6b…`, and `0x91…`/`0xd1…`/`0xb1…`/
`0xf1…`→`0x11…`/`0x51…`/`0x31…`/`0x71…`). The width is the node, so the `form_id`
says `w32-…` or `x64-…`, and the register class is a second guard: the nodes
spell `<Wd>`/`<Wn>`/`<Wm>` and `llvm-mc` rejects `add w0, w1, x2`, so an `x64`
operand on a `w` row is `E-OPERAND-001` (`N02c`). Register 31 stays legal in every
slot and means what the role says — `wzr` on the shifted rows and on
`ADDS_32S`/`SUBS_32S` `Rd`, `wsp` on `ADD_32`/`SUB_32` `Rd`/`Rn` and on
`ADDS_32S`/`SUBS_32S` `Rn` — so the vector uses registers 0–30 and those role
meanings live in `EXP-0021` §2. The 32-bit shift amount stops at 31: `lsl #32` is
rejected and the `imm6 = 32` word does not decode, so the slot is `bits: 6` with
`excluded: [32 … 63]` and `32` is `E-RANGE-004` (`N16d`), while `4096` on
`-imm12-lsl0` is still `E-RANGE-001` (`N18f`, `ADR-0019`).

The extended mnemonic rows are the ninth instance, and the one where the earlier
two families meet: `A64-P13` repeats the eight `add` extend rows on
`SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext`, so each
word is its `add` twin with bit 30 and/or bit 29 set
(`0x8b…`→`0xcb…`/`0xab…`/`0xeb…`) and bits 28–0 unchanged (`EXP-0022` §2). The
keyword still decides the source width and `imm3` still stops at 4 (`N02d`,
`N16e`), and register 31 means what the node's grammar says: `sp` in `sub`'s
`Rd`, `xzr` in the two S nodes' `Rd`, and `sp` in `Rn` throughout — so the vector
carries three rows for it rather than a slot kind (`ADR-0020`). The 32-bit
extended nodes stay absent (`N01l`).

The alias rows are the tenth instance, and the one where the decision is a
shorter operand list rather than a different word. `A64-P14` covers the forty
`0.12.0` rows: each is its `subs`/`adds` base row with `Rd` pinned to 31 and the
destination dropped, so the slots are `src` and `src2`/`imm` only (`ADR-0021`,
`EXP-0023` §2). The MRS alias nodes carry no `encoding` at all — the bytes are the
base node's, and the alias's `operation_id`, `condition` (`Rd == '11111'`) and
width are the pairing check (§1). Register 31 stays a plain `reg_number` and its
meaning is the node's role: `cmp sp, #5` is `0xf10017ff` and `cmp x1, xzr` is
`0xeb1f003f` (§3). Two spellings are left out rather than modelled: `cmp wsp, w2,
lsl #3` assembles to the **32-bit extended** word `0x6b224fff` (bit 21 = 1), which
the table does not carry, and `cmp x1, w2, uxtx #3` is a spelling-only
permissiveness of the alias path, so the width rule is still `ADR-0016`'s. A plan
that passes `dest` to a `cmp`/`cmn` row carries one operand too many and is
`E-OPERAND-002` (`N02e`).

The store rows are the eleventh instance, and the one where the load half was
already the answer. `A64-P15` covers the three `0.13.0` rows: each is the load
row's field list with `opc` at `00` and `Rt` as the stored register, so the slots
are `src`, `base`, `disp` and `disp` keeps the signed-byte `imm9` range
(`ADR-0022`, `EXP-0024` §1). The vector puts both ends on both writeback kinds
(`+8`/`−256` pre, `+8`/`255` post) and both signs on `stur` (`+16`/`−1`), so
`−257` on the post row and `256` on the unscaled row are `E-RANGE-001`
(`N03-str-imm9-post-disp`, `N03-stur-imm9-disp`). The `imm12` row is in the same
vector at `0` and `4095` to show that the new rows did not move it. The store
mnemonic does not name the kind either: `str x0, [x1, #1]` is `0xf8001020` and
`str x0, [x1, #-8]` is `0xf81f8020`, both read back as `stur` (§2).

The literal row is the twelfth instance, and the one where the field is still the
field but the operand list is not the load family's. `A64-P16` covers
`aarch64:ldr/x64-imm19` (`0.14.0`): `LDR_64_loadlit` has no `Rn`, so the slots
are `dest` and `target` and a third operand is `E-OPERAND-002` by the count rule
`N02e` pins (`ADR-0023`, `EXP-0025` §1). `imm19` is field content in 4-byte
units, so the four plain values state `1` and `−1` plus both ends of the signed
field (`262143`, `−262144`); a byte displacement is a fixup instead —
`pcrel_begin` + `scale(2)`, the reference being the instruction address, which a
label 20 bytes ahead proves (`imm19 = 5`, not 6) — so the two symbol targets land
at `+2` and `−4` field units. Stating `262144` is `E-RANGE-002` (`N04d`), and a
symbol 2 bytes away is `E-RANGE-003` at `/fixups/0/value_transform` (`N20`): the
field value is in range there, so alignment is a second check rather than a range
failure. `llvm-mc` reports both with one message; the split is `OD-09`'s and is
our own (§2–§3).

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

The literal load is the exception among the PC-relative rows: `llvm-mc` resolves
its local instruction labels itself and `llvm-readobj -r` prints no relocations
for `A64-P16`, so that vector needs no linker (`EXP-0025` §3).

See `../README.md` for naming and oracle rules.
