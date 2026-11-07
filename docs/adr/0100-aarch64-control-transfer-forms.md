# ADR-0100: AArch64 unconditional transfers are four forms and one bit

- Status: accepted
- Date: 2026-11-08
- Settles: the AArch64 control-transfer family of the M5 coverage widening in
  `08_final_recommendation.md` §H: the direct branch, the three register
  branches and the `EC-41` carrier decision, with one positive vector per shape
  and four rejections
- Supersedes: none
- Superseded by: none
- Revises: `EC-18` of `02_encoding_choices.md` (the row keeps its `form
  variant` decision; only the absent-sibling list changes); adds `EC-41`; the
  AArch64 slice table of `02_encoding_choices.md`; the AArch64 row of
  `03_fixup_model.md` §6; the reading-aid table of `07_definition_format.md`
  §8.2; the AArch64 table of `06_validation_matrix.md`; adds
  `definitions/aarch64/0.18.0.json` and the `A64-P21`/`A64-P22` fixtures

## Context

`ADR-0094` shipped one direct transfer, `aarch64:bl/imm26`, and `ADR-0012`
shipped `aarch64:b.cond/imm19`. Neither is a general branch: `bl` writes `x30`,
and `b.cond` only transfers when a condition holds. Three shapes are absent, and
each has a concrete cost.

- A direct transfer that does not write a link register is `b`. A plan that has
  already decided not to link cannot express it, and the workaround — naming
  `bl` and accepting the `x30` write — changes the program.
- A transfer through a register is `br`; its call and return siblings are `blr`
  and `ret`. Their operand is a register the plan must supply, not a
  displacement the materializer can compute.
- The `b`/`bl` split is a *decision a plan makes*, not a byte the fixup may
  choose. The two rows share the operand set, the length and every bit but 31,
  and they produce different relocation records. No `EC` row records that
  choice today.

`EXP-0101` measures the facts the decision needs, in five inputs:

- `field.asm` — `b #0`, `b #4`, `b #-4` are `0x14000000`, `0x14000001` and
  `0x17ffffff`: `imm26` is the field, and llvm-mc's `#n` is a *byte*
  displacement, so the field values `0, 1, -1` are spelled `#0`, `#4`, `#-4`.
  The measured extremes are `b #33554428` = `0x147fffff` and
  `b #-33554432` = `0x17800000`.
- `indirect.asm` — six instructions, all one word shape: `br x1` is
  `0xd61f0020`, `br x0` is `0xd61f0000`, `blr x2` is `0xd63f0040`, `ret x30`
  is `0xd65f03c0`, `ret x0` is `0xd65f0000` and `ret x19` is `0xd65f0260`.
  Only `op` at 21–22 (`00`, `01`, `10`) and `Rn` at 5–9 differ.
- `local.asm` — three `b` instructions resolved against labels at 0, 4 and 8,
  producing `0x14000002`, `0x14000000` and `0x17fffffe`: the field values `2`,
  `0` and `-2` come from arithmetic the assembler performs, and match
  `(S + A - P) >> 2` with `P` the instruction address.
- `extern.asm` — `b ext` emits `0x14000000` under `R_AARCH64_JUMP26` at `0x0`,
  and `bl ext` emits `0x94000000` under `R_AARCH64_CALL26` at `0x4`. The two
  relocation kinds are distinct, so the link bit is visible to the consumer of
  the artifact and cannot be a value the fixup chooses.
- `default.asm` — a bare `ret` assembles to `0xd65f03c0`, the same word as
  `ret x30`. The assembler's default operand is a hidden input.

The AArch64 `B` MRS node fixes the shape: bit 31 selects `b` and `bl`
(`op`), `00` at 29–30, `101` at 26–28 and `imm26` at 0–25. `BR`, `BLR` and
`RET` are the same node with `op0 = 110` at 29–31, `101` at 26–28, bit 25 = 1,
`Z = 0` at 24, bit 23 = 0, `op` at 21–22 set to `00`/`01`/`10`, `op2 = 11111`
at 16–20, `0000` at 12–15, `A = 0`/`M = 0` at 10–11, `Rn` at 5–9 and
`Rm = 00000` at 0–4. The node carries no operation text — its only semantic
label is `operation_id: "B_uncond"` — so the table states the field layout and
does not assert what the instruction does (`07_definition_format.md` §2).

## Decision

1. **Four forms, one new document.** `definitions/aarch64/0.18.0.json` repeats
   the 176 forms of `0.17.0` unchanged and appends:

   | `form_id` | template | slot |
   |---|---|---|
   | `aarch64:b/imm26` | `00000014` | target: `aarch64.rel`/`imm26` → `[0,26]` |
   | `aarch64:br/rn` | `00001fd6` | src: `aarch64.gpr64`/`x64` → `[5,5]` |
   | `aarch64:blr/rn` | `00003fd6` | src: `aarch64.gpr64`/`x64` → `[5,5]` |
   | `aarch64:ret/rn` | `00005fd6` | src: `aarch64.gpr64`/`x64` → `[5,5]` |

   `0.17.0` stays frozen, so a plan that names one of the four against an older
   document is still `E-FORM-001`. The templates are little-endian byte
   strings: the words are `0x14000000`, `0xd61f0000`, `0xd63f0000` and
   `0xd65f0000`.
2. **The link bit is a form variant, not a modifier.** `b` and `bl` differ only
   in bit 31 and in their relocation kind, which is exactly the shape `EC-41`
   records: same length, same operand, different program. The `b` row is a
   separate `form_id`, so a plan that names `b` gets the jump word and a plan
   that names `bl` gets the call word; a `link` modifier on the `b` target is
   `E-OPERAND-003` at `/instructions/0/operands/0/modifiers` (`N19d`).
3. **`imm26` is the field, and the operand range is the field's.** The slot is
   `aarch64.rel`/`imm26` with `{ signed: true, bits: 26, align_bits: 0 }` at
   `[0,26]`, exactly as `bl`'s. The fixup is `pcrel_begin`, `scale(2)`,
   `range_constraint { signed: true, bits: 26, align_bits: 2 }` (`§8.3`: the
   slot is the field, the fixup is the scaled reference). `N04e` states
   `33554432` and is `E-RANGE-002`, the same boundary `bl` already has. This is
   stricter than llvm-mc 23.1.2, which silently wraps `b #33554432` to
   `0x14800000`; v0 rejects instead of repairing (`INV-07`).
4. **`Rn` is an operand, and register 31 is `xzr`.** The three register forms
   carry one `src` slot of kind `aarch64.gpr64`/`x64` at `[5,5]`. There is no
   `excluded` list: the field is five bits and all 32 values encode, so `br xzr`
   is `0xd61f03e0` and `ret xzr` is `0xd65f03e0` — both measured. The slot is
   `Xn`, not `XdSP`, so the assembler's `blr sp` rejection has no v0 spelling
   to reject; a plan that states `{ "reg": 31 }` means `xzr`, as the existing
   `add`/`cmp` rows already document (`02_encoding_choices.md` §"Register 31 is
   not pinned").
5. **`ret` names its register; the default is absent.** There is no
   `aarch64:ret` row and no implicit `x30`. A plan that omits the operand and
   hopes for the assembler's default is `E-FORM-001` (`N01y`), because
   synthesizing `x30` would be a hidden input (`INV-05`) and would make one
   `form_id` mean two programs. `ret x30` is `aarch64:ret/rn` with
   `{ "reg": 30 }`, and it encodes the same word the assembler produces.
6. **The conditional siblings stay absent.** `cbz`, `cbnz`, `tbz` and `tbnz`
   carry a register plus a scaled displacement (and, for the bit tests, a bit
   index), so they are different forms with different operand sets, not rows of
   this family. `N01x` names `aarch64:cbz/x64-imm19` against `0.18.0` and gets
   `E-FORM-001`; `EC-18` keeps deciding the conditional transfer and now says
   which half ships.
7. **`+4` alignment is a fixup constraint here, not a slot rule.** The operand
   range has `align_bits: 0` like every other `imm26` slot; the *fixup* states
   `align_bits: 2`, as `03_fixup_model.md` §6 requires, so a plan can name a
   byte target without lying about the field's width.

## Consequences

- The AArch64 slice grows from 176 to 180 forms across eighteen documents, and
  the corpus to 111 positives and 548 `materialize`-phase negatives (554
  total). The oracle is `77/111`.
- `0.18.0` is immutable once committed; its digest is
  `sha256:c32e3674bf50140276d29fd01891bab20a86b849fa1503d2c9d02ae6aa503824`,
  and it is the first document to carry more than one direct-branch shape.
- `A64-P21` (field and local-symbol halves) and `A64-P22` (six register
  encodings) become passing; `N04e`, `N01x`, `N01y` and `N19d` are the
  negative boundary. `A64-P5` keeps covering `bl` with its own vector.
- `EC-41` is `frozen`: the counterexample is the two relocation kinds, which
  differ even though the operand and the length do not.
- `03_fixup_model.md` §6 gains a row saying the register branches have no
  displacement field: the register is an operand, the PC is not involved, and
  no fixup may be attached. `ret` is in that row so that a future `ret`-with-a
  displacement idea meets the absence of a field first.
- `08_final_recommendation.md` §D.3 and its roadmap rows are Phase-5 snapshots
  and are left as written; the `cbz`/`tbnz` clause in §G.2 stays true.

## Alternatives rejected

- **One `branch` form with a `link` modifier.** Rejected: `N19d` is the
  counterexample. A modifier is a property of an operand, and the materializer
  would have to turn it into bit 31 and a relocation kind — two effects from a
  field the definition does not carry. `EC-41` decides the carrier is the
  `form_id` instead.
- **`aarch64:ret` with an implicit `x30`.** Rejected: `N01y` is
  `E-FORM-001`, and the assembler's bare-`ret` default is a hidden input
  (`INV-05`). It would also make `ret x19` and `ret` two spellings of one row
  with different operand counts.
- **`br` as a modifier of `ret`.** Rejected: the three words differ in `op`
  at 21–22, which is a fixed field of the instruction shape; a plan that says
  "return" and a plan that says "branch" must not resolve to the same row.
- **Ship `cbz`/`cbnz` in this slice.** Rejected: a different operand set
  (`Rt` + `imm19`, or `Rt` + bit index + `imm14`), a different field, and a
  condition decision that `EC-18` owns. Contract before coverage; `N01x` keeps
  the absence loud.
- **Relax the operand range to the byte displacement.** Rejected: the plan
  states the field everywhere else (`ADR-0011` §8.3, `ADR-0023`), and a
  `#33554432` target is not a field value. Letting it wrap is what llvm-mc
  does; v0 rejects (`INV-07`).
- **Encode `sp` for `Rn = 31`.** Rejected: the MRS node's operand is `Xn`, and
  the assembler rejects `blr sp`. The field's 31 is `xzr`; there is no SP
  operand kind to attach, and inventing one for a value the ISA does not
  encode would be a silent repair.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `B` has `imm26` at 0–25 and bit 31 as the link bit; `BL` is the same node with `op = 1` | `research/external/arm-mrs/Instructions.json`: the `B_only_branch_imm`, `BR_64_branch_reg`, `BLR_64_branch_reg` and `RET_64R_branch_reg` records' `encoding.values`, read field by field | high |
| `br`/`blr`/`ret` share the layout and differ only in `op` at 21–22 and `Rn` at 5–9 | MRS `BR`/`BLR`/`RET` encoding values; `EXP-0101` §2 measured six words | high |
| `b ext` is `R_AARCH64_JUMP26` and `bl ext` is `R_AARCH64_CALL26` | `EXP-0101` §4, `llvm-readobj --relocations`: offsets `0x0` and `0x4` | high |
| `b`'s field domain is `-33554432 … 33554431` and `33554432` wraps in llvm-mc | `EXP-0101` §1: `#33554428` and `#-33554432` encode, `#33554432` gives `0x14800000` | high |
| `br xzr`/`ret xzr` encode, `blr sp`/`ret w0` do not | `EXP-0101` §2, llvm-mc 23.1.2 rejections | high |
| A bare `ret` is `ret x30` (`0xd65f03c0`) | `EXP-0101` §5 measured | high |
| `0.17.0` did not move; `0.18.0` is a superset with 180 forms | `check_definition.py`: 180 forms, digest `sha256:c32e3674…` | high |
| The four vectors reproduce the measured bytes through the CLI | `A64-P21-b-imm26`, `A64-P21-b-local-symbol`, `A64-P22-register-branch`: bytes equal `.expected.bin` | high |

## Review triggers

- A slice needs an indirect branch through a register the plan cannot name as
  `x64` (for example the `sp` reading, or an authenticated branch such as
  `braa`/`blraa`). That is a new operand kind or a new form, not a wider slot.
- A slice needs `cbz`/`cbnz`/`tbz`/`tbnz`. `EC-18` decides the sibling set;
  this ADR only settles which half ships.
- A proposal to give `ret` a default operand. That reverses decision 5 and
  needs a new ADR that supersedes this one, plus an answer for `ret x19`.
- A plan that wants `b` and `bl` from one `form_id`. That is `EC-41`'s
  counterexample and `INV-02`; the answer is two rows.
