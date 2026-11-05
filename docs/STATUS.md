# Status

Updated: 2026-11-05
Phase: **3 in progress (x86, AArch64 and RV64 slices): twenty-six definition documents, the materializer and the fixture gate are in place; every AArch64 and RV64 coverage row and all nine v0 x86 rows are carried, so widening is coverage work with its own ADR per slice**
Owner: Mr-enthalpy

This file is the recovery point. A new session should be able to resume from
this file plus `AGENTS.md` alone.

## Phase board

| Phase | Scope | State |
|---|---|---|
| 0 | Environment, evidence baseline, docs skeleton | **complete** |
| 1 | Encoder boundary audit (XirAsm, LLVM) | **complete** for XirAsm; LLVM internals deferred |
| 2 | FMP v0 contract, schema, error model | **complete for the x86, AArch64 and RV64 slices**; the last RV64 row's psABI pairing is now part of the contract (ADR-0010) |
| 3 | Three-ISA vertical prototype | **in progress**: twenty-six definition documents frozen (`07_definition_format.md`, `EXP-0004`, `EXP-0008`, `EXP-0010`, `EXP-0012`); `fmp-model`/`fmp-validate`/`fmp-materialize`/`fmp-cli` implemented; x86 has 11 positive and 36 negative fixtures, AArch64 has 20 positive and 57 negative, RV64 has 9 positive and 12 negative, all passing the two-source gate |
| 4 | Invariants, negative tests, replay | **in progress**: `EXP-R1`/`R2`/`R4`/`R5`/`R6` pass in `prototype/crates/fmp-cli/tests/determinism.rs` (`EXP-0033`); `EXP-R3` is `unverified` because only one host exists |
| 5 | Convergence, route evaluation, roadmap | not started |

## Gates

| Gate | Condition | State |
|---|---|---|
| G0 | `llvm-mc` available and emits bytes for x86-64, AArch64, RV64 | **passed** 2026-11-03 (LLVM 23.1.2) |
| G1 | Three questions answered from source: x86 relaxation disable, RISC-V form addressing, AArch64 library entry point | **passed** 2026-11-03 (all three answered; see `90_boundary_audit.md` §4) |
| G2 | Every `EC-*` row has an observed counterexample and a decided carrier | **in progress**: 27 of 36 rows are frozen; the 9 rows still `draft` are EC-05, EC-08, EC-10, EC-16, EC-18, EC-23, EC-24, EC-25 and EC-26, and none of them is needed by the three slices as they stand |
| G3 | Each ISA has >= 3 positive and >= 2 negative vectors passing two-source checks | **satisfied for x86, AArch64 and RV64** (x86: 11 positive, 36 negative; AArch64: 20 positive, 57 negative; RV64: 9 positive, 12 negative) |

## Decisions

| ID | Decision | State |
|---|---|---|
| ADR-0001 | Self-owned encoding core (Route C); XirAsm/LLVM are temporary oracles | accepted |
| ADR-0002 | Docs-first with explicit context anchors | accepted |
| ADR-0003 | Rust prototype, Level 0/1 output | accepted (provisional); OD-03 narrowed v0 to Level 0 |
| ADR-0004 | `form_id` carries every encoding decision; `encoding_choices` removed | accepted 2026-11-04 |
| ADR-0005 | AArch64 knowledge comes from the Arm MRS 2026-06; no XirAsm file is copied, the Arm notice ships with the table | accepted 2026-11-04 |
| ADR-0006 | The AArch64 source is pinned by MRS *packaging*: archive hash + both file hashes + the BSD-3-Clause licence sentence; the release block alone is not a pin | accepted 2026-11-04 |
| ADR-0007 | RV64 knowledge comes from the UDB resolved spec, pinned by archive hash + eight node hashes + the BSD-3-Clause-Clear header; `left_shift` is a fixup transform, and its `not: 0` rule was the reason `c.addi` stayed out of v0 until ADR-0009 gave the slot an `excluded` list | accepted 2026-11-04 |
| ADR-0008 | A memory operand is one operand per encoded field (`base`/`disp`/`index`/`scale`); the addressing form is a `form_id` variant, never a payload shape or a value-driven choice | accepted 2026-11-04 |
| ADR-0009 | A slot may declare `excluded`: a closed, strictly increasing list of exact integers inside its domain; absent means none, a hit is `E-RANGE-004`, and the check is a lookup, never a predicate | accepted 2026-11-04 |
| ADR-0010 | An RV64 low half names its high half: `pc_reference_rule: pcrel_hi` puts `P` at the paired `hi`'s site, `value_transform: pcrel_lo12` masks the displaced value, a `lo` addend must be 0 (`E-FIXUP-009`), and a group is one `hi` with at least one `lo` | accepted 2026-11-04 |
| ADR-0011 | AArch64 `add` with `LSL #12` is a second `form_id` (`-lsl12`) in `0.2.0`: the form pins `sh = 1`, the slot stays `imm12` field content, no slot-level scale is added, and a literal that only fits the other form is `E-RANGE-001` (`N18a`/`N18b`) | accepted 2026-11-04 |
| ADR-0012 | An AArch64 condition is an operand, not sixteen forms: `aarch64:b.cond/imm19` in `0.3.0` carries `cond` as `aarch64.cond`/`cond4` at bits 0–3 (range `0..15`, no `excluded` — all sixteen are defined), and the `imm19` target is field content with a `pcrel_begin` + `scale(2)` fixup; `cond = 16` is `E-RANGE-001` (`N03`), a displacement past `imm19` is `E-RANGE-002` (`N04c`) | accepted 2026-11-04 |
| ADR-0013 | AArch64 addressing kinds are forms, and `disp` is field content: `0.4.0` adds five load/store rows (`ldr` imm12/imm9-pre/imm9-post, `ldur` imm9, `str` imm12), `imm12` counts 8-byte units for these `x` rows, `imm9` counts signed bytes, `align_bits` stays 0, and the register-offset, literal and store-`imm9` kinds stay absent (`E-FORM-001`) | accepted 2026-11-04 |
| ADR-0014 | The AArch64 `movz` lane is a form: `0.5.0` adds four rows (`-lsl0` … `-lsl48`), each pinning its `hw` value, with `imm16` as field content in `0…65535`; no slot scale and no `lsl` modifier, a pre-scaled literal is `E-RANGE-001` (`N18c`), an `lsl #8` lane is `E-FORM-001` (`N01d`), and `movk`/`movn`/`w`/the `mov` alias stay out | accepted 2026-11-04 |
| ADR-0015 | An AArch64 shift keyword is a form and the amount is field content: `0.6.0` adds three rows (`-imm6-lsl`/`-imm6-lsr`/`-imm6-asr`), each pinning `shift` (22+2), with `imm6` as an `aarch64.imm`/`imm6` operand over `0…63` at `[10,6]` and `align_bits 0`; a modifier never writes a bit, so the same shift stated as `{"name":"lsl","value":3}` on `-lsl0` is `E-OPERAND-003` (`N19`), an amount of 64 is `E-RANGE-001` (`N03-imm6`), `imm6 = 0` on `-imm6-lsl` is the same word as `-lsl0` and both stay, and the extend family/`sub`/the `w` rows stay out (`E-FORM-001`, `N01e`) | accepted 2026-11-04 |
| ADR-0016 | An AArch64 extend keyword is a form and the amount is field content with an excluded tail: `0.7.0` adds eight rows, one per `option` value (`-imm3-uxtb` … `-imm3-sxtx`), with `option` pinned at 15–13, `src2` a `w` register on the six `[su]xt[bhw]` rows and an `x` register on the two `[su]xtx` rows, and `imm3` as an `aarch64.imm`/`imm3` operand at `[10,3]` over `0…4` with `excluded: [5,6,7]`; `imm3 = 8` is `E-RANGE-001` (`N03-imm3`), `5` is `E-RANGE-004` (`N16c`), a `w` operand on a shifted row is `E-OPERAND-001` (`N02b`), and the extended `sub` node/`adds`/`subs`/the 32-bit node stay out (`E-FORM-001`, `N01f`, `N01g`, `N01h`; the decision-7 scope is narrowed by ADR-0017) | accepted 2026-11-04 |
| ADR-0017 | An AArch64 mnemonic is a form family: `0.8.0` adds six `sub` rows (`-lsl0`, `-imm12-lsl0`/`-lsl12`, `-imm6-lsl`/`-lsr`/`-asr`) from `SUB_64_addsub_shift`/`SUB_64_addsub_imm`, which are the `ADD_64` nodes with `op` at 30+1 fixed to `1` by the node itself, so no plan field names the mnemonic bit; the `sh`/`shift`/`imm6` treatment and slot shapes are inherited from ADR-0011/ADR-0015, register 31 in these rows is `xzr` (not `sp`), `subs` and the `sf = 0` node are `E-FORM-001` (`N01g`/`N01h`), and a literal outside the named `sh` half is `E-RANGE-001` (`N18d`) | accepted 2026-11-04 |
| ADR-0018 | An AArch64 flag-setting mnemonic is a form family and `S = 1` is the node's: `0.9.0` adds twelve rows, six `adds` and six `subs` (`-lsl0`, `-imm12-lsl0`/`-lsl12`, `-imm6-lsl`/`-lsr`/`-asr` each) from `ADDS_64_addsub_shift`/`ADDS_64S_addsub_imm`/`SUBS_64_addsub_shift`/`SUBS_64S_addsub_imm`, the four nodes already read with `S` at 29+1 fixed to `1`, so no plan field names the bit; every word is its `add`/`sub` twin with bit 29 set, the `sh`/`shift`/`imm6` treatment and slot shapes are inherited, register 31 is `xzr` (the extended S nodes are absent), `cmp`/`cmn` are a two-operand alias family and out (`N01i`), the `sf = 0` S nodes are out (`N01j`), and a literal outside the named `sh` half is `E-RANGE-001` (`N18e`) | accepted 2026-11-04 |
| ADR-0019 | The AArch64 32-bit width is a form family and `sf = 0` is the node's: `0.10.0` adds twenty-four rows, the six `add`/`sub`/`adds`/`subs` shapes each repeated on the eight `*_32*` nodes, so `w32-…` vs `x64-…` in the `form_id` is the width and no plan field names the bit; every register slot is `aarch64.gpr32`/`w32` (an `x64` operand is `E-OPERAND-001`, `N02c`), register 31 stays a plain `reg_number` whose meaning is the node's role (no `sp` operand kind), the 32-bit `imm6` declares `bits: 6` with `excluded: [32…63]` (`imm6 = 32` is `E-RANGE-004`, `N16d`), `4096` on `-lsl0` stays `E-RANGE-001` (`N18f`), and the extended 32-bit nodes plus `cmp`/`cmn` stay out (`E-FORM-001`, `N01k`) | accepted 2026-11-04 |
| ADR-0020 | The AArch64 extended-register mnemonic family repeats the `add` shapes on the `op = 1`/`S = 1` nodes: `0.11.0` adds twenty-four rows, the eight `option` rows each on `SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext`, so the mnemonic is the form family and no plan field names `op` or `S`; the keyword still fixes `src2`'s width (six `[su]xt[bhw]` take `w32`, `uxtx`/`sxtx` take `x64`, `N02d`), `imm3` keeps `excluded: [5, 6, 7]` (`N16e`), register 31 stays a plain `reg_number` whose meaning is the node's role (`sp` only in `sub`'s `Rd`), and the 32-bit extended nodes plus `cmp`/`cmn` stay out (`E-FORM-001`, `N01l`) | accepted 2026-11-04 |
| ADR-0021 | `cmp`/`cmn` are a separate two-operand alias family: `0.12.0` adds forty rows, each the `subs`/`adds` row of the same layout and width with `Rd` pinned to 31 and the `dest` slot removed, built from the base node because the MRS alias nodes carry no `encoding`; the alias node is the pairing check (`operation_id`, `condition` `Rd == '11111'`, `preferred`, width), so it never supplies a bit field; the 32-bit extended aliases stay out with their base rows (`N01l`), a `dest` on a `cmp`/`cmn` row is `E-OPERAND-002` (`N02e`), and `N01i`/`N01m` become version boundaries against `0.11.0` | accepted 2026-11-04 |
| ADR-0022 | The store half of the addressing kinds is the same decision: `0.13.0` adds three rows (`str/x64-base-imm9-pre`, `str/x64-base-imm9-post`, `stur/x64-base-imm9`), each the load row's layout with `opc = 00` and `Rt` as the stored register, so the kind stays a `form_id`, `disp` keeps ADR-0013's field-content rule (`imm9`, signed bytes, `-256…255`, `align_bits 0`), the slot list stays `src`/`base`/`disp`, `N03` pins the two range ends and `N01n` the `0.12.0` version boundary, and no schema or Rust change is needed | accepted 2026-11-04 |
| ADR-0023 | The literal load carries its displacement in `imm19` and has no base register: `0.14.0` adds one row, `aarch64:ldr/x64-imm19`, from `LDR_64_loadlit` (`opc = 01`, pattern `0x58000000`), with `dest` at `[0,5]` and `target` at `[5,19]` and no `base`; the slot is the field (`align_bits 0`), a byte displacement is a `pcrel_begin` + `scale(2)` fixup with `range.bits 19`/`align_bits 2` and the byte range `−1048576…+1048572`, `imm19 = 262144` is `E-RANGE-002` (`N04d`), a 2-byte symbol offset is `E-RANGE-003` (`N20`, our own split of the assembler's one message), `N01o` is the `0.13.0` boundary, the `w`/`LDRSW`/`PRFM`/SIMD literals and register offset stay out, and no store literal exists | accepted 2026-11-04 |
| ADR-0024 | Register offset is a form family and `option`/`S` are form bits: `0.15.0` adds sixteen rows, `ldr`/`str` × `{lsl,uxtw,sxtw,sxtx}{0,3}`, from `LDR_64_ldst_regoff`/`STR_64_ldst_regoff`, which differ only in `opc`; `Rm` is an `index` slot at `[16,5]`, `option` (13+3) fixes both the keyword and the index width (`lsl`/`sxtx` take `x64`, `uxtw`/`sxtw` take `w32`), and `S` (12+1) is the only scale carrier (`#0` or `#3` on these `size = 11` rows), so neither is an operand; `lsl #0` is the same word as the bare spelling, `-lsl1`/`-lsl4` have no row (`N01q`), a `w32` index on a `-lsl0` row is `E-OPERAND-001` (`N02f`), a modifier stating `lsl #3` is `E-OPERAND-003` (`N19b`), `N01p` is the `0.14.0` boundary, the coarse `aarch64:ldr/x64-base-regoff` stays absent (`N01b`), the `w`/byte/halfword and `prfm` register offsets stay out, and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0025 | The 32-bit register offset is the same `option` family at `size = 10`: `0.16.0` adds sixteen rows, `ldr`/`str` × `{lsl,uxtw,sxtw,sxtx}{0,2}`, from `LDR_32_ldst_regoff`/`STR_32_ldst_regoff`, which are the 64-bit pair with `size = 10` and the same `opc` split; `option` keeps its keyword/width pairing (`lsl`/`sxtx` take `x64`, `uxtw`/`sxtw` take `w32`), `S` is still the only scale carrier but means `#2` on a 4-byte access, and only `Rt` changes class (`w32`), so `dest`/`src` are `aarch64.gpr32`/`w32` while `base` and the `x` index rows stay `x64`; `-lsl3` has no row at this width (`N01s`), a `w32` index on `-lsl0` or an `x64` destination is `E-OPERAND-001` (`N02g`/`N02h`), a modifier stating `lsl #2` is `E-OPERAND-003` (`N19c`), `N01r` is the `0.15.0` boundary, the `b`/`h` widths, the signed/extended loads and `prfm` stay out, and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0026 | `movk`/`movn` are the `movz` lane family one `opc` over: `0.17.0` adds eight rows, four `hw` lanes on each of `MOVK_64_movewide` (`opc = 11`) and `MOVN_64_movewide` (`opc = 00`), so the mnemonic is the node and no plan field names the operation (`EC-16`); `sf = 1`, `hw` at 21+2 and `Rd` at 0+5 are unchanged, `imm16` stays unsigned field content in `0…65535`, and `movn` stores the raw field rather than its complement; `-lsl8` has no row (`N01t`), the `w` lanes and the `mov` alias stay out (`N01v`/`N01w`), a `w32` destination is `E-OPERAND-001` (`N02i`), `imm16 = 65536` or a pre-scaled literal is `E-RANGE-001` (`N03-movk-imm16`, `N18g`), and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0027 | A RIP-relative memory operand is a form with no base register: `0.2.0` adds two rows, `x86:mov/r64-riprel32/legacy` (`REX.W 8B /r`, `mod = 00`, `r/m = 101`) and `x86:mov/riprel32-r64/legacy` (`REX.W 89 /r`), so the opcode direction is still the form (`EC-27`) and the addressing shape is the form rather than an operand value (`EC-34`); `ModRM.reg` is the destination or source at `[19,3]`, `disp32` is the last field at `[24,32]`, and the displacement is a `target` operand (`x86.rel`/`riprel32`, signed 32) with a `pcrel_end` fixup and `addend 0`, because RIP is not in `x86.gpr64` and no slot carries its number; `disp32 = 2147483648` is `E-RANGE-002` (`N04e`), an extra `base` is `E-OPERAND-002` (`N02j`), `N01x` is the `0.1.0` boundary, and an operand/fixup target mismatch is `E-FIXUP-001` (`N07b`); base+disp8/disp32 (`X86-P4`), SIB, the `0x67` prefix (`X86-P5`) and `moffs` stay out, and no schema or Rust change is needed | accepted 2026-11-05 |
| ADR-0028 | Base+displacement is eight rows across four shapes: `0.3.0` adds load/store × `disp8`/`disp32` × base-in-`r/m`/`%rsp`-fixed, so `mod` and the SIB byte are template rather than operand-driven; the general rows carry `base` at `[16,3]` with `excluded: [4]` (`%rsp` would force a SIB byte, `E-RANGE-004`), the `%rsp` rows fix `r/m = 100`, `SIB = 24` and the base, `disp8`/`disp32` are signed field content, `disp8 = 128` is `E-RANGE-001` (`N03-disp8-out-of-range`), `%rsp` on a general row is `E-RANGE-004` (`N16f`), `N01y` is the `0.2.0` boundary, and index/scale, `mod = 00`, `r8`–`r15`, `0x67` and `moffs` stay out | accepted 2026-11-05 |
| ADR-0029 | The operand-size prefix and the high-byte registers are form facts: `0.4.0` adds five rows — two 16-bit directions with `0x66` as template byte 0, the high-byte row (`x86.gpr8h`, numbers 4–7 = `ah`/`ch`/`dh`/`bh`), and the low-byte pair split by REX (REX-less 0–3, REX 4–7 = `spl`/`bpl`/`sil`/`dil`) — so the prefix is never chosen from an operand value; the exclusion lists keep the three 8-bit rows disjoint (`88 e5` is `ah`/`ch`, `40 88 e5` is `spl`/`bpl`), and the loader rejects a `gpr8h` slot in a REX template or a REX-less `gpr8` slot that does not exclude 4–7 (`E-DEF-001`); `N01z` is the `0.3.0` boundary, `N02k` is a `gpr8h` operand on the REX row (`E-OPERAND-001` ×2), `N16g` is number 4 in the REX-less row (`E-RANGE-004`), and `8A`, memory operands at these widths, `0x67` and `r8`–`r15` stay out | accepted 2026-11-05 |
| ADR-0030 | The x86 encoding family is a form fact: `0.5.0` adds three rows at `xmm` width — `x86:movaps/xmm-xmm/legacy` (`0f28c0`, 3 bytes), `x86:vmovaps/xmm-xmm/vex` (`c5f828c0`, 4 bytes) and `x86:vmovaps/xmm-xmm/evex` (`62f17c0828c0`, 6 bytes) — so `/legacy`, `/vex` or `/evex` in the `form_id` is the family, the prefix is template, and the slots move with the prefix length (`[19,3]`/`[16,3]`, `[27,3]`/`[24,3]`, `[43,3]`/`[40,3]`); `x86.xmm` is one kind, registers 0–7 only, and the VEX/EVEX extension bits are template constants; `0.5.0` declares `avx`/`avx512f`/`avx512vl` for its EVEX.128 row, so a plan must declare the same set (`E-TARGET-001`, `N06`), while `E-TARGET-003` stays unreachable; `N01aa` is the unfamilied id, `N01ab` the `0.4.0` boundary, `N02l` a `zmm` operand on the `xmm` row (`E-OPERAND-001` ×2) and `N14b` is `xmm8` (`E-OPERAND-004`); memory operands, masking, `ymm`/`zmm`, the three-byte `C4` VEX form and `movapd`/`movdqa` stay out | accepted 2026-11-05 |
| ADR-0031 | Every plan and definition object is closed: an unknown field is `E-PLAN-003` (plan) or `E-DEF-001` (definition), there is no `x_*` namespace and no extension object in `fmp/0.1`; `enabled_extensions` is an equality-checked target set (`E-TARGET-001`) | accepted 2026-11-05 |
| ADR-0032 | Canonical JSON is the v0 wire form: the reader accepts any valid JSON spelling of the same value, and binary transport is deferred to a later `format_version` | accepted 2026-11-05 |
| ADR-0033 | A `x86.gpr64` operand is four bits: the low three are the `ModRM` field and bit 3 is a placement into the form's existing `REX` byte (`REX.B` = `[0,1]` for `r/m`, `REX.R` = `[2,1]` for `reg`); one row per operand shape, not per extension combination; `0.6.0` widens the six register-direct rows, base+disp, 8/16-bit, high-byte and SSE/VEX/EVEX rows stay narrow, and `REX.X` is unexercised | accepted 2026-11-05 |
| ADR-0034 | A memory base is four bits and the SIB byte is a form fact: `0.7.0` widens the twelve base+disp rows (`REX.R`/`REX.B`), the general rows exclude the SIB-forcing values `4` and `12` (`E-RANGE-004`), and `%r12` gets four fixed-base rows that differ from `%rsp` only in `REX.B`; index/scale and `REX.X` are a separate shape | accepted 2026-11-05 |

## Settled decisions (contract level)

| ID | Decision | Evidence |
|---|---|---|
| OD-01 | Plan carries an optional per-instruction `expected_digest`; a hash, never raw bytes; a check, never an input | `EXP-0002` §2–§5 |
| OD-02 | Exactly two fixup modes, one effect each: `resolve_in_place` writes, `emit_relocation` zeroes and records; records are RELA-shaped; the mode never depends on symbol liveness | `EXP-0002` §6; `03_fixup_model.md` §5, §8 |
| OD-03 | v0 emits Level 0; Level 1 optional and deferred; Level 2 out of scope | `EXP-0002` §6 |
| OD-04 | `form_id` is a structured name resolved by exact lookup; a rename is loud (`E-FORM-001`, or `E-DEF-001` first); no opaque id, no `match`/`mask` | `01_contract.md` §7; F-09 |
| OD-06 | The definition digest covers the whole data-only definition in canonical form; a rule change moves it, formatting does not, and a comment is unrepresentable | `EXP-0004` §4; `07_definition_format.md` §6 |
| OD-07 | AArch64 facts come from the Arm MRS 2026-06 OPENSOURCE packaging; our own table is generated from the data, no MPL-2.0 script is copied, and the Arm BSD-3-Clause notice ships with `definitions/aarch64/` | ADR-0005, ADR-0006; `EXP-0007`; `90_boundary_audit.md` F-12, F-13; `definitions/aarch64/NOTICE` |
| OD-09 | Exact integers with declared domains, no wrap, one range check per value after the transform | `01_contract.md` §3.1–§3.2 |
| OD-10 | v0 ships only the forms the slices use; the definition table is the feature surface and absence is `E-FORM-001` | `02_encoding_choices.md`, "v0 surface"; ADR-0004 |
| OD-11 | A byte-affecting decision is carried by `form_id`, a typed operand, a fixup field or a target field — never by a separate choice list | ADR-0004; `02_encoding_choices.md` |
| OD-12 | RV64 facts come from the UDB resolved spec (`sha256:be184986…`), pinned per node; riscv-opcodes is the upstream cross-check and `llvm-mc` the oracle | ADR-0007; `EXP-0009`; `EXP-0010`; `definitions/rv64/NOTICE` |
| OD-13 | A memory operand is field-level: `base`/`disp` are separate operands and the addressing form is a `form_id` variant; a composite `{"mem": …}` payload is `E-OPERAND-003` | ADR-0008; ADR-0013 (AArch64 half); ADR-0027 (x86 RIP half); ADR-0028 (x86 base+disp half); `EXP-0011`; `EXP-0015`; `EXP-0029`; `EXP-0030`; `N15`; `N01b`; `X86-P6`; `X86-P4` |
| OD-14 | A slot may exclude a closed list of exact values inside its domain; the rejection is `E-RANGE-004`, the check is a lookup, and an absent key means no exclusion | ADR-0009; `EXP-0012`; `N16a`/`N16b` |
| OD-15 | A `hi`/`lo` pair expresses RISC-V's "the low half names the high half" with `pcrel_hi` (P = the paired `hi`'s site) and `pcrel_lo12` (mask the displaced value), a zero `lo` addend, and a 1:N group | ADR-0010; psABI `riscv-elf.adoc:1578-1605`; `RV-P8-pcrel-pair`, `RV-P8-pcrel-pair-resolved`; `N17a`/`N17b` |

## Open decisions

See `docs/fmp-v0/05_open_decisions.md`. **No item blocks the slices:** every
`OD-*` row is accepted as of 2026-11-05, with `OD-05` (unknown fields) settled by
ADR-0031 and `OD-08` (canonical wire form) by ADR-0032. The Level 1 artifact
envelope stays deferred by `OD-03`. OD-07 is settled by ADR-0005 and
pinned by ADR-0006, and the AArch64 tables it authorised now exist: five MRS
nodes generated the forms in `definitions/aarch64/0.1.0.json`, the same nodes
generated `0.2.0.json` with one extra row for the `sh = 1` half of `A64-P2`
(ADR-0011), and `0.3.0.json` adds the `b.cond` row whose condition is an operand
(ADR-0012). `0.4.0.json` adds five load/store rows from five more nodes, one per
addressing kind (`A64-P3`, ADR-0013), `0.5.0.json` adds four `movz` rows from
one node, one per `hw` lane (`A64-P7`, ADR-0014), `0.6.0.json` adds three
shift rows from `ADD_64_addsub_shift`, one per keyword (`A64-P8`, ADR-0015),
`0.7.0.json` adds eight extend rows from `ADD_64_addsub_ext`, one per `option`
value (`A64-P9`, ADR-0016), `0.8.0.json` adds six `sub` rows from
`SUB_64_addsub_shift`/`SUB_64_addsub_imm`, whose nodes fix `op = 1` so the
mnemonic is the form family (`A64-P10`, ADR-0017), and `0.9.0.json` adds twelve
`adds`/`subs` rows from the four `S = 1` nodes, whose `S` bit is fixed by the node
in the same way (`A64-P11`, ADR-0018), `0.10.0.json` adds twenty-four `w`
rows, the same six shapes on the eight `sf = 0` nodes, whose width is fixed by
the node in the same way (`A64-P12`, ADR-0019), `0.11.0.json` adds
twenty-four extended `sub`/`adds`/`subs` rows from the three `op = 1`/`S = 1`
extended nodes (`A64-P13`, ADR-0020), and `0.12.0.json` adds forty `cmp`/`cmn`
alias rows, each the base row with `Rd` pinned to 31 and the destination dropped
(`A64-P14`, ADR-0021), and `0.13.0.json` adds the three store `imm9` rows, the
load rows' layouts with `opc = 00` and the stored register as `src` (`A64-P15`,
ADR-0022), and `0.14.0.json` adds the literal load row, `LDR_64_loadlit` with
`dest` and `target` and no base register (`A64-P16`, ADR-0023), `0.15.0.json`
adds the sixteen register-offset rows, one per `option`/`S` pair on each of the
two register-offset nodes (`A64-P17`, ADR-0024), and `0.16.0.json` adds the
sixteen 32-bit register-offset rows, the same pairs at `size = 10` with `#2` as
the scaled amount and `w32` as the destination/source class (`A64-P18`,
ADR-0025), and `0.17.0.json` adds the eight 64-bit `movk`/`movn` lanes, the four
`hw` values on each of the two `opc`-fixed nodes with `imm16` as field content
(`A64-P19`, ADR-0026).
Twenty positive fixtures match `llvm-mc` (`EXP-0008`, `EXP-0013`, `EXP-0014`, `EXP-0015`,
`EXP-0016`, `EXP-0017`, `EXP-0018`, `EXP-0019`, `EXP-0020`, `EXP-0021`,
`EXP-0022`, `EXP-0023`, `EXP-0024`, `EXP-0025`, `EXP-0026`, `EXP-0027`,
`EXP-0028`). Every directive §6.2 item now has a passing
row; what remains is widening, not a decision.
OD-12 is settled by ADR-0007: the RV64 source is the UDB resolved
spec, pinned by archive and node hashes, `EXP-0009` verified the B/J/RVC scatter
against `llvm-mc`, and `EXP-0010` generated `definitions/rv64/0.1.0.json` (seven
forms) and `0.2.0.json` (eight) from eight of those nodes. OD-13 is
settled by ADR-0008: `EXP-0011` measured that a memory operand spans fields with
different ranges (RV64 `xs1`/`imm`/`xd`), that the x86 encoding form changes with
the displacement value (`48 8b 41 08` vs `48 8b 81 00 10 00 00`), and that the
AArch64 `imm12` is already a scaled field value (`ldr x0, [x1, #16]` →
`imm12 = 2`). `ld`/`sd` are therefore three operands, and `N15` pins the rejected
composite payload. The AArch64 half is pinned by ADR-0013: `disp` is field
content, so the offset kinds are five rows in `aarch64/0.4.0.json`, the store
trio joins them in `0.13.0.json`, the literal in `0.14.0.json` and register
offset in `0.15.0.json` and `0.16.0.json`, so every addressing kind the drop
carries now has a row at both the `x` and `w` widths that have one;
`N01b` still rejects the coarse register-offset id (`ADR-0024`/`ADR-0025`). The
x86 half is pinned by ADR-0027 and ADR-0028: `disp32` with no base is a
`target` operand with a `pcrel_end` fixup, and base+disp8/disp32 is a `base`
operand plus a `disp` operand whose width is the form's, with `%rsp` either a
fixed-base form or `E-RANGE-004` (`X86-P6`, `X86-P4`, `EXP-0029`, `EXP-0030`).
OD-14 is settled by
ADR-0009: `EXP-0012` §2 measured that
`c.addi a0, 0` (`01 05`) and `c.addi x0, 1` (`05 00`) are reserved HINTs despite
being inside the declared range, so the slot excludes `0` and
`riscv:c.addi/rd-imm6` lands in `rv64/0.2.0.json` (`RV-P7`, `N16a`/`N16b`). The
same mechanism keeps the x86 8-bit rows disjoint: `ADR-0029` uses `excluded`
to split numbers 0–3/4–7 between the REX-less, high-byte and REX rows, and
`N16g` pins register 4 in the REX-less row (`E-RANGE-004`). OD-15
is settled by ADR-0010: the ELF psABI (`v2.0-rc0`, `EV-22`) states that the low
half resolves against the high half's site, that its addend must be 0, and that
one high part may serve several low parts, so `pcrel_hi`/`pcrel_lo12` and a 1:N
`pair_group` are now `fmp/0.1` (`RV-P8-pcrel-pair`,
`RV-P8-pcrel-pair-resolved`, `N17a`/`N17b`). OD-06 was
load-bearing because `EXP-0002` W1 shows that a definition drift the digest does
not cover is caught only by the weaker size check; it is now settled, and
`EXP-0004` §4 measures both halves.

## Next action

1. Decide the next format question, one ADR each, before widening any table.
   The AArch64 `-lsl12` half of `A64-P2` is closed without a format change:
   `OD-07`/ADR-0011 pinned `sh = 1` in a second `form_id` and kept the slot as
   `imm12` field content, so `A64-P2` now passes with `N18a`/`N18b` pinning the
   two spellings that must be rejected. Each remaining decision lands with a
   counterexample, an error code where rejection is the answer, and a fixture
   that shows the rejection (`E-FORM-001` or the new code).
   The RV64 pair question is closed: `OD-15`/ADR-0010 added `pcrel_hi` and
   `pcrel_lo12`, and `RV-P8-pcrel-pair` plus `RV-P8-pcrel-pair-resolved` now
   carry the record and arithmetic halves.
   The memory-operand question is closed: `OD-13`/ADR-0008 chose one operand per
   field, `RV-P3` now passes, `A64-P3` is closed by `0.4.0`/ADR-0013, and
   `X86-P6` is closed by `0.2.0`/ADR-0027, the one shape with no base register
   (`mod = 00`, `r/m = 101`, `disp32`), `X86-P4` by `0.3.0`/ADR-0028, which
   enumerated the eight base+disp rows and the `%rsp` SIB pair, and `X86-P5` by
   `0.4.0`/ADR-0029, which made the `0x66` width and the high-byte register set
   form facts. The non-zero question is
   closed too: `OD-14`/ADR-0009 added `excluded`, and `RV-P7` now passes
   (`EXP-0012`).
2. Extend the AArch64 coverage, one vertical slice at a time. All eight directive
   §6.2 items now pass, and every load/store addressing kind the MRS drop carries
   is now a row; the next slices are widening, and each needs its own ADR
   (ADR-0011 decision 7's rule):
   - register offset, the last absent load/store kind, is closed by `A64-P17`:
     ADR-0024 added the sixteen `option`/`S` rows, and `N01b` still rejects the
     coarse id. Its 32-bit half is closed by `A64-P18`: ADR-0025 repeated the
     sixteen rows at `size = 10`, where `S = 1` is `#2` and only `Rt` is `w32`.
   `A64-P4` is closed by `0.3.0`: ADR-0012 made the condition an operand
   (`aarch64.cond`/`cond4`) instead of sixteen forms, and `N03`/`N04c` pin the
   two rejections. `A64-P3` is closed by `0.4.0`: ADR-0013 made each addressing
   kind a form and `disp` field content, `A64-P3-ldst-addressing` matches
   `llvm-mc`, and `N03` ×2 plus `N01b` pin the rejections. `A64-P7` is closed by
   `0.5.0`: ADR-0014 made the `movz` lane a form with `imm16` as field content,
   `A64-P7-movz-lane` matches `llvm-mc`, and `N18c`/`N01d` pin the pre-scaled
   literal and the absent lane. `A64-P8` is closed by `0.6.0`: ADR-0015 made the
   shift keyword a form and `imm6` field content, `A64-P8-shift-modifier` matches
   `llvm-mc`, and `N03-imm6`/`N19`/`N01e` pin the amount, the modifier carrier and
   the absent extend family. `A64-P9` is closed by `0.7.0`: ADR-0016 made the
   extend keyword a form (it also fixes the source width) and `imm3` field content
   with an excluded tail, `A64-P9-extend-modifier` matches `llvm-mc`, and
   `N03-imm3`/`N16c`/`N02b`/`N01f` pin the two ends of the domain, the source class
   and the absent `sub` node. `A64-P10` is closed by `0.8.0`: ADR-0017 made the
   mnemonic the form family, so `sub` repeats the `add` shapes with `op = 1`,
   `A64-P10-sub-family` matches `llvm-mc`, and `N01g`/`N01h`/`N18d` pin the absent
   `subs`, the absent `w` form and the literal that only fits the other `sh` half.
   `A64-P11` is closed by `0.9.0`: ADR-0018 made the flag-setting mnemonic the
   form family too, so `adds`/`subs` repeat the shapes with `S = 1`,
   `A64-P11-adds-subs-family` matches `llvm-mc`, and `N01i`/`N01j`/`N18e` pin the
   absent `cmp` alias, the absent `w` form and the same literal. `A64-P12` is
   closed by `0.10.0`: ADR-0019 made the width the form family too, so the `w`
   rows repeat the six shapes on the eight `sf = 0` nodes with `w32` registers,
   `A64-P12-w-rows` matches `llvm-mc`, and `N01k`/`N02c`/`N16d`/`N18f` pin the
   version boundary, the `x64` operand, `imm6 = 32` and the same literal.
   `A64-P13` is closed by `0.11.0`: ADR-0020 repeated the eight extended rows on
   the `op = 1`/`S = 1` nodes, `A64-P13-ext-family` matches `llvm-mc`, and
   `N01l`/`N02d`/`N16e` pin the absent 32-bit extended node, the wrong `src2`
   class and `imm3 = 5`. `A64-P14` is closed by `0.12.0`: ADR-0021 made
   `cmp`/`cmn` a two-operand alias family whose bytes are the base node's and
   whose alias node is only the pairing check, `A64-P14-cmp-cmn-family` matches
   `llvm-mc`, and `N02e`/`N01i`/`N01m` pin the extra `dest` and the two version
   boundaries. `A64-P15` is closed by `0.13.0`: ADR-0022 added the store
   `imm9` trio as the load rows' layouts with `opc = 00`,
   `A64-P15-store-imm9-addressing` matches `llvm-mc`, and `N03` ×2 plus `N01n`
   pin the two range ends and the version boundary. `A64-P16` is closed by
   `0.14.0`: ADR-0023 added the literal row with `dest`/`target` and no base,
   `A64-P16-loadlit` matches `llvm-mc`, and `N04d`/`N20`/`N01o` pin the field
   end, the alignment split and the version boundary. `A64-P17` is closed by
   `0.15.0`: ADR-0024 added the sixteen register-offset rows with `option` and
   `S` pinned and `Rm` as an `index` slot, `A64-P17-regoff` matches `llvm-mc`,
   and `N01p`/`N01q`/`N02f`/`N19b` pin the version boundary, the absent `-lsl1`
   row, the `w32` index mismatch and the modifier carrier. `A64-P18` is closed by
   `0.16.0`: ADR-0025 repeated the rows at `size = 10`, `A64-P18-w32regoff`
   matches `llvm-mc`, and `N01r`/`N01s`/`N02g`/`N02h`/`N19c` pin the version
   boundary, the absent `-lsl3` row, the `w32` index and `x64` destination
   mismatches and the same modifier rule. `A64-P19` is closed by `0.17.0`:
   ADR-0026 added the four `movk` and four `movn` lanes with `opc` fixed by the
   node, `A64-P19-movwide` matches `llvm-mc`, and
   `N01t`/`N01u`/`N01v`/`N01w`/`N02i`/`N03-movk-imm16`/`N18g` pin the absent
   `-lsl8` lane, the `0.16.0` boundary, the `w32` lane, the `mov` alias, the
   `w32` destination, the field end and the pre-scaled literal. A `:lo12:` inside the
   `-lsl12` form is measured at the record level but is not a symbol address
   (`EXP-0013` §5); a slice that wants one must decide what its addend means
   first.
3. Extend the x86 coverage the same way. `X86-P6` is closed by `0.2.0`:
   ADR-0027 added the two RIP-relative rows with `disp32` as a `target`
   operand, `X86-P6-rip-relative` matches `llvm-mc` (43 bytes, one
   `R_X86_64_PC32` record), and
   `N01x`/`N02j`/`N04e`/`N07b` pin the version boundary, the extra `base`, the
   field end and the operand/fixup mismatch. `X86-P4` is closed by `0.3.0`:
   ADR-0028 added the eight base+displacement rows plus the `%rsp` SIB pair,
   `X86-P4-base-disp` matches `llvm-mc` (51 bytes, no record), and
   `N01y`/`N03-disp8-out-of-range`/`N16f` pin the version boundary, the `disp8`
   field end and the `%rsp` exclusion. `X86-P5` is closed by `0.4.0`: ADR-0029
   added the two 16-bit directions, the high-byte row and the low-byte pair,
   `X86-P5-prefixes` matches `llvm-mc` (20 bytes, no record), and
   `N01z`/`N02k`/`N16g` pin the version boundary, the high-byte operand on a REX
   row and the number-4 exclusion. `X86-P9` is closed by `0.5.0`: ADR-0030 added
   one `movaps` shape in three families (`/legacy`, `/vex`, `/evex`) with the
   prefix as template and the `ModRM` placements following it,
   `X86-P9-sse-vex-evex` matches `llvm-mc` (13 bytes, no record), and
   `N01aa`/`N01ab`/`N02l`/`N06`/`N14c`/`N14d` pin the absent family, the `0.5.0`
   boundary, the `zmm` operand, the extension-list mismatch and the two ends of
   the register field. `X86-P10` widens the six 64-bit register-direct rows in
   `0.6.0` (`ADR-0033`): a `x86.gpr64` slot is four bits, its high bit is a
   placement into `REX.R`/`REX.B`, `X86-P10-gpr-extended` matches `llvm-mc`
   (44 bytes, no record), and `N14c`/`N14d` pin the 3-bit `0.5.0` boundary and
   the 4-bit field end. `X86-P11` continues the same widening into memory: `0.7.0`
   (`ADR-0034`) gives the base+disp rows a 4-bit base and a 4-bit `ModRM.reg`
   operand, excludes both SIB-forcing values (`4`, `12`), and adds four
   fixed-base `%r12` rows that differ from the `%rsp` rows only in `REX.B`;
   `X86-P11-base-extended` matches `llvm-mc` (93 bytes, no record), and
   `N16h`/`N01ac` pin the `%r12` exclusion and the `0.6.0` boundary. Every
   directive §6.1 row is carried; the remaining widening is index and scale
   (`REX.X`), the 8/16-bit rows and the SSE families.
4. Contract debt is closed: `OD-05` (unknown fields/extensions) by ADR-0031,
   pinned by `N21a`/`N21b` and the definition unit test, and `OD-08` (canonical
   wire form) by ADR-0032, pinned by `EXP-R4`. The Level 1 artifact envelope
   stays deferred by `OD-03` and is not needed by the Level 0 gate.
5. Keep `python tools/check_ids.py`, `python tools/check_definition.py` and
   `python tools/check_rv64_source.py` green after every change, and keep
   `cargo test --workspace` green: it is the fixture gate, not a smoke test.

Phase 3 output so far: the Rust workspace under `prototype/` (`fmp-model` for the
strict JSON reader and the plan/definition binders, `fmp-validate` for contract
§13 steps 2–7, `fmp-materialize` for encoding and the two fixup modes,
`fmp-cli` with exit codes 0/1/2); the frozen tables
`definitions/x86_64/0.1.0.json` (seven forms, digest `sha256:c6bfa9…`),
`0.2.0.json` (nine forms, digest `sha256:d9c088ca…`, the two RIP-relative
rows), `0.3.0.json` (seventeen forms, digest `sha256:02500bf7…`, the eight
base+displacement rows), `0.4.0.json` (twenty-two forms, digest
`sha256:ee2141cb…`, the five prefix rows), `0.5.0.json` (twenty-five forms,
digest `sha256:24256f0c…`, the three encoding-family rows), `0.6.0.json`
(twenty-five forms, digest `sha256:79952b5d…`, the six 64-bit register-direct
rows widened from 3-bit to 4-bit register fields) and `0.7.0.json` (twenty-nine
forms, digest `sha256:8c40c948…`, the twelve base+disp rows widened to a 4-bit
base and the four fixed-base `%r12` rows);
`EXP-0004` (223 decoded byte strings across the seven `0.1.0` rows, plus the
`OD-06` digest measurement); `EXP-0005` (9 positive fixtures against LLVM
23.1.2, with the decode-verified caveat on five instructions); `EXP-0029` (the
RIP-relative fields,
the signed `disp32` ends and the record offset); `EXP-0030` (the base+disp
fields, the `%rsp` SIB byte and the signed `disp8`/`disp32` ends); `EXP-0031`
(the `0x66` width, the 8-bit register sets and the prefix order); `EXP-0032`
(the three encoding families, the moving `ModRM` placement and the extension
set); `EXP-0035` (the `r8`–`r15` placements, the `REX.R`/`REX.B` split and the
version boundary); `EXP-0036` (the `r8`–`r15` bases, the `%r12`/`%rsp` SIB pair
and the `E-RANGE-004` exclusion); and 36 negative fixtures whose
complete diagnostic sets — code, JSON Pointer, detail keys — are compared for
exact equality. `E-OPERAND-004`/`N14` (an operand wider than its field) is one
of them.

The AArch64 slice adds `definitions/aarch64/0.1.0.json` (four forms: two `add`,
`bl`, `adrp`; digest `sha256:96f87aa…`) with the Arm BSD-3-Clause notice beside
it, `EXP-0008` (five MRS nodes, the all-32-bits-covered check, and the
`immlo`-at-30:29 correction the oracle caught), and 20 positive + 57 negative
fixtures. `0.2.0` adds the fifth form, `aarch64:add/x64-imm12-lsl12` (digest
`sha256:169e4bf6…`), which pins `sh = 1` and leaves the operand as `imm12`
field content (ADR-0011, `EXP-0013`); `N18a`/`N18b` record the two literals that
must be rejected rather than form-switched. `0.3.0` adds the sixth,
`aarch64:b.cond/imm19` (digest `sha256:71af93c0…`), where the condition is a
four-bit operand rather than sixteen near-identical rows (ADR-0012, `EXP-0014`);
`N03-cond` and `N04c` pin `cond = 16` and an `imm19` overflow. `0.4.0` adds five
load/store rows (digest `sha256:14d6c2b6…`), one per addressing kind, with `disp`
as field content in 8-byte units (`imm12`) or signed bytes (`imm9`) (ADR-0013,
`EXP-0015`); `A64-P3-ldst-addressing` is 24 bytes over five forms, and
`N03-imm12-disp`/`N03-imm9-disp`/`N01b` pin the two range rejections and the
absent register-offset kind. `0.5.0` adds four `movz` rows (digest
`sha256:9cec1688…`), one per `hw` lane, with `imm16` as field content (ADR-0014,
`EXP-0016`); `A64-P7-movz-lane` is 20 bytes over all four, and `N18c`/`N01d` pin
the pre-scaled literal and the absent `lsl #8` lane. `0.6.0` adds three shift
rows (digest `sha256:1151944e…`), one per keyword, with the amount as an `imm6`
operand in `0…63` (ADR-0015, `EXP-0017`); `A64-P8-shift-modifier` is 24 bytes
over all three, and `N03-imm6`/`N19`/`N01e` pin the range, the modifier carrier
and the absent extend family. `0.7.0` adds eight extend rows (digest
`sha256:1bb92035…`), one per `option` value, with the keyword fixing the source
width and the amount as an `imm3` operand over `0…4` minus `5…7` (ADR-0016,
`EXP-0018`); `A64-P9-extend-modifier` is 32 bytes over all eight, and
`N03-imm3`/`N16c`/`N02b`/`N01f` pin the field end, the excluded tail, the source
class and the absent `sub` node. `0.8.0` adds six `sub` rows (digest
`sha256:9f82b566…`) from the `op = 1` twin of the two `add` nodes, with the
mnemonic as the form family and register 31 reading `xzr` (ADR-0017, `EXP-0019`);
`A64-P10-sub-family` is 24 bytes over six forms, and `N01g`/`N01h`/`N18d` pin the
absent `subs`, the absent `w` form and the literal that only fits the other `sh`
half. `0.9.0` adds twelve `adds`/`subs` rows (digest `sha256:99728cd9…`) from the
four `S = 1` nodes, one bit over the `add`/`sub` shapes, with the flag-setting
mnemonic as the form family (ADR-0018, `EXP-0020`); `A64-P11-adds-subs-family` is
48 bytes over twelve forms, and `N01i`/`N01j`/`N18e` pin the absent `cmp` alias,
the absent `w` form and the literal that only fits the other `sh` half. `0.10.0`
adds twenty-four `w` rows (digest `sha256:e958d69b…`), the same six shapes on the
eight `sf = 0` nodes with every register slot `aarch64.gpr32`/`w32` and the
32-bit `imm6` tail excluded (ADR-0019, `EXP-0021`); `A64-P12-w-rows` is 96 bytes
over twenty-four forms, and `N01k`/`N02c`/`N16d`/`N18f` pin the version boundary,
the `x64` operand, `imm6 = 32` and the same literal. `0.11.0` adds twenty-four
extended `sub`/`adds`/`subs` rows (digest `sha256:c5a9aec9…`), the eight
`option` rows repeated on the three `op = 1`/`S = 1` extended nodes, with the
keyword still fixing `src2`'s width and `imm3` still excluded over `5…7`
(ADR-0020, `EXP-0022`); `A64-P13-ext-family` is 108 bytes over twenty-seven
instructions, and `N01l`/`N02d`/`N16e` pin the absent 32-bit extended node, the
wrong `src2` class and `imm3 = 5`. `0.12.0` adds forty `cmp`/`cmn` alias rows
(digest `sha256:8a428926…`), each the `subs`/`adds` base row with `Rd` pinned to
31 and the `dest` slot removed, with the MRS alias node used only as the pairing
check because it carries no `encoding` (ADR-0021, `EXP-0023`);
`A64-P14-cmp-cmn-family` is 188 bytes over forty-seven instructions, and
`N02e`/`N01i`/`N01m` pin the extra `dest` operand and the two version boundaries.
`0.13.0` adds the three store `imm9` rows (digest `sha256:d3876dd3…`), the load
rows' layouts with `opc = 00` and `Rt` as `src`, so the kind stays the `form_id`
and `disp` keeps its signed-byte range (ADR-0022, `EXP-0024`);
`A64-P15-store-imm9-addressing` is 32 bytes over five forms, and `N03` ×2 plus
`N01n` pin the two range ends and the `0.12.0` boundary. `0.14.0` adds the
literal load (digest `sha256:a90ceac1…`), `LDR_64_loadlit` with `opc = 01` and
`dest`/`target` as its only slots: `imm19` is field content in 4-byte units, so a
byte displacement is a `pcrel_begin` + `scale(2)` fixup (ADR-0023, `EXP-0025`);
`A64-P16-loadlit` is 24 bytes over one form, `N04d` rejects `imm19 = 262144`,
`N20` rejects a 2-byte symbol offset as `E-RANGE-003`, and `N01o` is the `0.13.0`
boundary. `0.15.0` adds the sixteen register-offset rows (digest
`sha256:422ebb83…`), `option` and `S` pinned per row and `Rm` as an `index` slot
whose width follows `option`, so the scale is never an operand (ADR-0024,
`EXP-0026`); `A64-P17-regoff` is 80 bytes over the sixteen rows plus four
register-31 rows, `N01p` is the `0.14.0` boundary, `N01q` rejects a `-lsl1` row,
`N02f` rejects a `w32` index on a `-lsl0` row, and `N19b` rejects `lsl #3` as a
modifier. `0.16.0` adds the sixteen 32-bit register-offset rows (digest
`sha256:1e83c6ca…`), the same eight pairs at `size = 10` with `option` intact,
`S = 1` as `#2` and only `Rt` changed to `w32` (ADR-0025, `EXP-0027`);
`A64-P18-w32regoff` is 80 bytes over the sixteen rows plus the four register-31
rows, `N01r` is the `0.15.0` boundary, `N01s` rejects a `-lsl3` row, `N02g`
rejects a `w32` index on `-lsl0`, `N02h` rejects an `x64` destination, and
`N19c` rejects `lsl #2` as a modifier. `0.17.0` adds the eight 64-bit
`movk`/`movn` rows (digest `sha256:de2c53e1…`), the four `hw` lanes on each of
`MOVK_64_movewide`/`MOVN_64_movewide` with `opc` fixed by the node and `imm16`
stored raw (ADR-0026, `EXP-0028`); `A64-P19-movwide` is 48 bytes over the eight
rows plus four boundary rows, `N01t` rejects a `-lsl8` lane, `N01u` is the
`0.16.0` boundary, `N01v` rejects a `w32` lane, `N01w` rejects the `mov` alias,
`N02i` rejects a `w32` destination, and `N03-movk-imm16`/`N18g` reject the field
end and a pre-scaled literal.
A64-P5/P6 use `llvm-mc` →
`ld.lld` → `llvm-objcopy`
because `llvm-mc` leaves AArch64 branch and `adrp` fields as relocations; A64-P3,
A64-P4, A64-P7, A64-P8, A64-P9, A64-P10, A64-P11, A64-P12, A64-P13, A64-P14,
A64-P15, A64-P16, A64-P17, A64-P18 and A64-P19
need no
linker
because their
operands are immediates or local labels in one section and `llvm-mc` resolves
them, emitting no relocations.
The generator now gates each form on a `since` version, so an older document
cannot lose a form and a newer one cannot gain one by accident. The fixture gate
scans every `fixtures/<isa>/<kind>/` directory, so a new table's vectors are gated
the moment they land.

The RV64 slice adds two documents. `definitions/rv64/0.1.0.json` holds seven
base-`I` forms (`add`, `addi`, `beq`, `jal`, `auipc`, `ld`, `sd`; digest
`sha256:6afb2bf4…`); `definitions/rv64/0.2.0.json` adds `riscv:c.addi/rd-imm6`
and declares `["rv64i","rv64c"]` (eight forms; digest `sha256:8329a38f…`). Both
carry the BSD-3-Clause-Clear notice. ADR-0007 fixes the source as the UDB
resolved spec (`sha256:be184986…`); `EXP-0009` measures eight instruction nodes
and reproduces fourteen `llvm-mc` byte strings from their `location` fields;
`EXP-0010` generates both documents from the same eight nodes, asserts full-bit
coverage, selects the `RV64` encoding block of `ld`/`sd` so the `RV32` Zilsd
`not:` list cannot leak, turns each `not:` into the slot's `excluded` list
(ADR-0009), and re-encodes sixteen probe vectors from the tables it built.
`tools/check_rv64_source.py` gates the drop, the SPDX headers and
`definitions/rv64/NOTICE`.

The nine positive fixtures exercise `add`, both `addi` endpoints, the B-type
scatter forward and backward, the J-type scatter forward and backward, the
`auipc` field, `ld`/`sd` at both signed imm12 endpoints, and `c.addi` (four
immediates, with the 4-byte `addi` on the same immediate beside it), plus the
`pcrel_hi`/`pcrel_lo12` pair. The twelve negatives pin `E-FORM-001` (including
`N01c`, the same form named against `0.1.0`), `E-OPERAND-001`, `E-RANGE-001`,
`E-RANGE-002`, `E-RANGE-004` (`N16a`/`N16b`, the excluded zeroes),
`E-FIXUP-009`/`E-FIXUP-007` (`N17a`/`N17b`/`N17c`, the pair half),
`E-TARGET-001` (`N06`, a plan that declares `rv64i` against a table that also
declares `rv64c`), and (read time) `E-OPERAND-003`. `RV-P8-pcrel-pair` is the first pair fixture whose oracle is the
object file's relocation records rather than linked bytes: one `auipc`, one `addi`
and one `sd`, all `emit_relocation`, so one `hi` and two `lo` members produce
three records, and the bytes are three templates with zero immediates while
`llvm-readobj -r` supplies the records (`HI20`, `LO12_I`, `LO12_S`). Its companion
`RV-P8-pcrel-pair-resolved` is the arithmetic gate: `auipc` at 4, symbol at
0x1000, both fixups `resolve_in_place`, and the linked words `0x00001517` /
`0xFFC50513` equal `(0x1000 - 4 + 0x800) >> 12 = 1` and
`(0x1000 - 4) & 0xFFF = 0xFFC`; `lo12_i` would write 0x000, `pcrel_begin` on the
low half 0xFF8, and dropping `+0x800` 0, so the fixture separates the decision
from its neighbours. See ADR-0010.

The materializer is deliberately not a bridge to LLVM: it reads only the plan
and the pinned definition, writes bytes and RELA-shaped records, and has no
fallback when a form, field or symbol is missing.

Phase 2 output: `EXP-0002` (OD-01, OD-03), `EXP-0003` (the alias pairs behind
OD-11/ADR-0004), the `pcrel_end` fix in `03_fixup_model.md` §4, the observed
relocation semantics in §6.1, ADR-0004 (OD-10, OD-11), the rewritten
`02_encoding_choices.md` with per-row carriers, the counterexample/retirement
sections in `04_errors.md`, and the OD-02/OD-04/OD-09 freeze: two fixup modes
with one effect each, a structured `form_id` with loud failure, and the exact
integer/address model in `01_contract.md` §3.1. The schema lost
`reject_if_unresolved`, `overwrite_bytes` and the one-value `bit_order` enum, and
`E-FIXUP-004` is retired.

`EXP-0002`'s plan-size numbers were measured with the then-required empty
`encoding_choices` list. ADR-0004 removes that field, so absolute sizes drop by
about 22 B per instruction; the A-vs-B comparison is unaffected in direction.

Phase 1 output to read first: `docs/fmp-v0/90_boundary_audit.md` (findings
F-01…F-15, gate answers in §4) and `docs/fmp-v0/91_reuse_matrix.md`.
Raw experiment records: `research/evidence/experiments/EXP-0001-*.md`,
`research/evidence/experiments/EXP-0002/README.md`.

## Known environment facts (verified 2026-11-03)

| Item | Value |
|---|---|
| Host | Windows, `C:\Users\hanni\Projects\MonAsm` |
| Git remote | `git@github.com:Mr-enthalpy/MonAsm.git` (SSH, authenticated) |
| Zig | 0.17.0 at `C:\Users\hanni\Tools\zig` |
| LLVM | 23.1.2 at `C:\Users\hanni\Tools\llvm` (`llvm-mc` verified on x86-64, AArch64, RV64) |
| GNU binutils | not installed (llvm-objdump/llvm-readobj cover v0 needs) |
| Rust | 1.96.0 (`stable-x86_64-pc-windows-msvc`) |
| Visual Studio | 2022 present |
| Python | 3.8 |
| WSL | executable present, no distribution installed |

## Immutable source text

`docs/fmp-v0/00_directive.md` is a verbatim copy of the research directive. It is
never edited. Integrity checksum (SHA-256) is recorded in
`research/evidence/source_index.md`.
