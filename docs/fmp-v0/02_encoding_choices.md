# Encoding Decisions and Their Carriers

Status: **draft** (registry rows are frozen individually). This is the operational
form of INV-02, under ADR-0004.

## The rule

Given a frozen plan and a pinned definition, exactly one byte sequence may result.
A byte-affecting decision is legal only if it is carried by an explicit plan field.
The carriers are a closed set:

| Carrier | How the plan expresses it |
|---|---|
| `form variant` | the `<variant>` component of `form_id`, e.g. `rm64-imm8` vs `rm64-imm32` |
| `encoding family` | the `<encoding_family>` component of `form_id`, e.g. `legacy` / `vex` / `evex` |
| `operand type` | an operand's `kind` / `target_type`, e.g. `wreg` vs `xreg`, `imm8` vs `imm32` |
| `operand modifier` | an entry in `operands[].modifiers`, e.g. `lock`, `addr_size`, `aq` |
| `fixup field` | a required field of the fixup record, e.g. `pc_reference_rule` |
| `target identity` | a field of `target_identity`, e.g. `execution_mode`, `enabled_extensions` |
| `none` | the variation is unsupported; the definition pins one output and a plan cannot ask for the other |

If no carrier is named, the decision is missing and the definition MUST NOT supply
a default. ADR-0004 removed `encoding_choices` as a carrier: a plan states a
machine form, not a form plus a modifier list that restates it.

Two failure modes to avoid:

- **Under-frozen:** the materializer still has to choose. Detected by asking "could
  two honest implementers of this definition emit different bytes for this plan?"
- **Over-frozen:** the plan carries bit patterns and the definition becomes
  decorative. Detected by asking "would this plan still be valid after a
  legitimate definition bug-fix that does not change observable semantics?"

## Test used to classify a decision

For each candidate:

1. Name the two or more legal outputs and their observable difference.
2. Ask whether the difference is *implied by naming the form* (same `form_id` ⇒
   same bytes). If yes, the carrier is `form variant` or `encoding family`, and
   the two outputs need different `form_id`s.
3. Ask whether the difference is *implied by a typed operand* (e.g. a width-typed
   value or register class). If yes, the carrier is `operand type` or
   `operand modifier`.
4. Ask whether the difference is a range legality issue rather than a choice. If
   yes, it is `E-RANGE-*`, not a carrier.
5. Ask whether the difference belongs to layout or to a fixup field. If yes, it is
   a `fill` fragment or a required fixup field.
6. Otherwise the difference is **not expressible in v0**: the carrier is `none`,
   the definition must pin one output, and the other must be unreachable.

A decision that reaches step 6 is not silently dropped. It is recorded here with
`none` and a negative test proving the unsupported variation cannot be requested.

## Registry

`frozen` means the counterexample is written and the carrier is decided. `draft`
means the carrier is plausible but no observed counterexample exists yet; it must
not be moved to `frozen` on the strength of an argument alone.

| ID | ISA | Legal outputs | Observable difference | Carrier | Counterexample if the carrier is removed | Status |
|---|---|---|---|---|---|---|
| EC-01 | x86-64 | `add r/m64, imm` as sign-extended imm8 (`83 /0 ib`) vs imm32 (`81 /0 id`) | 4 vs 7 bytes with `REX.W` | `form variant` (`rm64-imm8` / `rm64-imm32`) | `add rax, 1` is legal both ways (`48 83 c0 01`, `48 81 c0 01 00 00 00`); an encoder that picks by value violates INV-02 and shifts every later offset. | frozen |
| EC-02 | x86-64 | Memory displacement as disp8 (mod=01) vs disp32 (mod=10) | 1 vs 4 displacement bytes | `form variant` (`mem-disp8` / `mem-disp32`) | `mov rax, [rbp-8]` → `48 8b 45 f8` (disp8); `[rbp-200]` → disp32. Not exercised by the v0 slice, which has no memory operand. | frozen |
| EC-03 | x86-64 | Relative branch rel8 (`EB`) vs rel32 (`E9`) | 2 vs 5 bytes | `form variant` (`rel8` / `rel32`) | llvm-mc 23.1.2: `jmp .+0x81` → `eb 7f` (2 B) but `jmp .+0x82` → `e9 7d 00 00 00` (5 B). One byte of target distance changes the instruction length; that is relaxation, not encoding (INV-04). | frozen |
| EC-04 | x86-64 | Accumulator form (`05 id`, `B8+rd`) vs ModRM form (`81 /0 id`, `C7 /0 id`) | Different opcode byte; the accumulator form is one byte shorter because it has no ModRM | `form variant` (`rax-imm32` / `rm64-imm32`) | `add rax, 300` → `48 05 2c 01 00 00` (6 B) or `48 81 c0 2c 01 00 00` (7 B); `mov eax, 300` → `b8 2c 01 00 00` (5 B) or `c7 c0 2c 01 00 00` (6 B). Both tools pick the accumulator and neither exposes the other. | frozen |
| EC-05 | x86-64 | `moffs` absolute form (`A0-A3`) vs ModRM with disp32 | Different length and prefix behavior | `form variant` (`moffs` / `mem-abs32`) | `mov al, [0x1234]` has two legal encodings with different sizes. | draft |
| EC-06 | x86-64 | REX presence and W/R/X/B bits; high-byte registers (`AH`) are illegal with any REX | Legality and one prefix byte | `operand type` (register class → REX bits) + definition rule | A plan naming `AH` with a 64-bit operand cannot be encoded; the encoder must reject, not silently switch registers. | frozen |
| EC-07 | x86-64 | Operand-size prefix `0x66` vs a distinct 16/32/64-bit form | One prefix byte, different semantics | `form variant` (`r16-*`) | `add ax, bx` requires `66`; omitting it changes the operand width. | frozen |
| EC-08 | x86-64 | Address-size prefix `0x67` in 64-bit mode | One prefix byte and truncation semantics | `operand modifier` (`addr_size`) | 32-bit addressing in 64-bit mode truncates the effective address. | draft |
| EC-09 | x86-64 | Legacy SSE vs VEX vs EVEX for the same operation | Prefix family, 2–4 bytes, register reach | `encoding family` (`legacy` / `vex` / `evex`) | `vaddps xmm0,xmm1,xmm2` fits 2-byte VEX but is also expressible in EVEX. | draft (deferred, `X86-P9`) |
| EC-10 | x86-64 | `LOCK` / `REP` / segment prefix presence | One or more prefix bytes | `operand modifier` (`lock` / `rep` / `segment`) | `lock add [rax], ebx` vs plain `add` differ only by `F0`, with different semantics. | draft |
| EC-11 | AArch64 | 32-bit (`w`) vs 64-bit (`x`) variant | Different `sf` bit, different semantics | `operand type` (`wreg` / `xreg`) | `add w0,w1,w2` vs `add x0,x1,x2` differ in one bit and in overflow behavior. | frozen |
| EC-12 | AArch64 | `add/sub` immediate: imm12 vs imm12 shifted by 12 | Different `sh` bit and range | `form variant` (`imm12` / `imm12-scaled`) | `add x0,x1,#1` and `add x0,x1,#1,lsl #12` are both legal spellings of different values. | frozen |
| EC-13 | AArch64 | Shifted-register vs extended-register form | Different `shift`/`option` fields | `form variant` (`shifted-reg` / `extended-reg`) | `add x0,x1,x2,lsl #3` vs `add x0,x1,w2,uxtw #3` share a mnemonic but not an encoding. | frozen |
| EC-14 | AArch64 | Load/store addressing: unsigned-offset vs pre-index vs post-index vs unscaled vs register-offset | Different addressing bits (bit 24, bits 11–10) and writeback semantics | `form variant` (`unsigned-offset` / `pre-index` / `post-index` / `unscaled` / `register-offset`) | llvm-mc 23.1.2: `ldr x0,[x1,#16]` is `0xf9400820` (`imm12 = 2`, unsigned-offset) while `ldur x0,[x1,#16]` is `0xf8410020` (`imm9 = 16`, unscaled). Worse, `ldr x0,[x1,#1]` emits `0xf8401020`, which `llvm-objdump` reads back as `ldur`: the mnemonic does not name the form, so the assembler silently switches instruction on the offset's value (INV-02). | frozen |
| EC-15 | AArch64 | Literal load vs `adrp` + `lo12` sequence | Instruction count (INV-03 boundary) | `form variant` (one instruction vs two planned instructions) | A "load from label" request is a plan decision: one literal load or two instructions. | frozen |
| EC-16 | AArch64 | `mov` alias family: `movz` / `movn` / `orr` immediate / register | Different opcodes | `form variant` (`movz` / `movn` / `orr-imm` / `reg`) | `mov x0,#1` can be `movz` or `orr`; both are legitimate and differ in bytes. | draft |
| EC-17 | AArch64 | `adr` (±1 MB) vs `adrp` (page) for a symbol address | Different instruction and fixup kind | `form variant` + `fixup field` (`kind`) | Choosing `adrp` when the target is in range changes both bytes and relocation semantics. | frozen |
| EC-18 | AArch64 | `b.cond` vs `cbz/cbnz` vs `tbz/tbnz` for a conditional transfer | Different forms and operand sets | `form variant` | A planner that says only "branch if zero" has not chosen a form. The `b.cond` half now ships as `aarch64:b.cond/imm19`; `cbz`/`tbnz` are absent, so naming one is `E-FORM-001`. | draft |
| EC-19 | RV64 | Compressed (`c.*`, 2 bytes) vs standard (4 bytes) | 2 vs 4 bytes | `form variant` (the `c.` mnemonic is a different form; `riscv:c.addi/rd-imm6` in `0.2.0`) | With `-mattr=+c`, `addi a0, a0, 1` assembles to `05 05`; the same immediate with `a1` stays `13 85 15 00`, and `c.addi a0, 1` is `05 05` only because it was named. An encoder that picks by register/operand shape violates INV-02. | frozen |
| EC-20 | RV64 | Compressed register class `x8–x15` (3-bit field) vs full 5-bit register | Legality | `operand type` + definition rule | `c.lw a6, 0(a0)` is rejected ("register must be a GPR from x8 to x15"); `c.lw a2, 0(a0)` is `10 41`. `c.addi a6, 5` is legal (`15 08`): its `xd` is a 5-bit field, so the rule is per form, not per mnemonic prefix. | frozen |
| EC-21 | RV64 | Absolute vs PC-relative symbol materialization: `lui`+`addi` vs `auipc`+`addi` | Instruction pair and relocation kind | `form variant` + `fixup field` (`kind`) | Choosing PC-relative changes both instructions and the fixup pair. | frozen |
| EC-22 | RV64 | B-type/J-type immediate scatter is fixed by form, but the PC base is not | Fixup value | `fixup field` (`pc_reference_rule`) | Same form, different `P`, different bytes: a contract bug. | frozen |
| EC-23 | RV64 | `jal` vs `jalr` for a call; `c.j` vs `jal` for a jump | Different instruction, range, link behavior | `form variant` | A "call" that becomes `jalr` needs a base register the plan never provided. | draft |
| EC-24 | RV64 | `fence` `fm`/`pred`/`succ` field values | Bits 31–28, 27–24, 23–20 | `operand type` (`fence_mask`) | `fence rw,rw` vs `fence iorw,iorw` differ in fields, not in mnemonic. | draft |
| EC-25 | RV64 | CSR operation immediate (`csrrwi`) vs register (`csrrw`) | Different funct3 | `form variant` | `csrrwi` cannot carry a register operand; a generic "CSR op" leaves the choice open. | draft |
| EC-26 | RV64 | Atomic `aq`/`rl` bits | Bits 26–25 | `operand modifier` (`aq` / `rl`) | `amoadd.w` vs `amoadd.w.aqrl` differ in ordering semantics and bytes. | draft |
| EC-27 | x86-64 | `89 /r` (`MOV r/m64, r64`) vs `8B /r` (`MOV r64, r/m64`) | Different opcode bytes, same length, same semantics | `form variant` (`rm-r64` / `r64-rm`) | `mov rax, rbx` is both `48 89 d8` and `48 8b c3`; both disassemble to `movq %rbx, %rax` and both are 3 bytes. `expected_size` cannot detect a wrong choice, and no operand distinguishes them; only `expected_digest` can (OD-01). | frozen |
| EC-28 | x86-64 | Minimal prefix set vs a redundant prefix (`89 d8` vs `40 89 d8`; likewise a redundant `66`, segment or `REX` prefix) | One byte per redundant prefix, identical semantics | `none` — definition rule: emit the minimal prefix set | `40 89 d8` decodes as `movl %ebx, %eax`, exactly like `89 d8`. Two honest implementers could differ by one byte with no observable semantic difference, so the definition must pin minimality and no plan field may request the redundant byte. | frozen |
| EC-29 | AArch64 | `b.cond` condition: sixteen values in the 4-bit `cond` field | Bits 0–3; no length, opcode or relocation change | `operand type` (`aarch64.cond` / `cond4`) | `b.eq .+4` is `0x54000020` and `b.ne .+4` is `0x54000021`: one nibble apart, both 4 bytes, so a wrong condition is a valid word that branches on the wrong flags. Masking `cond = 16` to four bits yields `0x0`, which is `eq` (`ADR-0012`, `EXP-0014`). | frozen |
| EC-30 | AArch64 | `MOVZ` lane: `hw` selects which 16-bit lane of the 64-bit destination the `imm16` content lands in | Bits 22–21; the value the instruction builds is `imm16 << 16·hw` | `form variant` (`-lsl0` … `-lsl48`) | `llvm-mc` 23.1.2: `movz x0, #0x1234` is `0xd2824680` and `movz x0, #0x1234, lsl #16` is `0xd2a24680`. Both put the same `imm16 = 0x1234` at bits 20–5 and differ only in bits 22–21, so neither the operand value nor `expected_size` can tell them apart; two honest implementers of one `movz` row would emit different words (`ADR-0014`, `EXP-0016`). | frozen |
| EC-31 | AArch64 | Shift on a register operand: `lsl` / `lsr` / `asr` with an amount `0…63` (`shift` at 23–22, `imm6` at 15–10) | Bits 23–22 and 15–10; the operand value is combined with a shifted register | `form variant` for the keyword (`-imm6-lsl` … `-imm6-asr`), `operand type` for the amount (`aarch64.imm` / `imm6`) | `llvm-mc` 23.1.2: `add x0, x1, x2, lsl #3` is `0x8b020c20` and `add x0, x1, x2, lsr #7` is `0x8b421c20`; every register field is identical, and a plan that stated only the registers could not distinguish the two words. The amount is a second reading of the same instruction: `lsl #0` and `lsl #63` differ only in `imm6`. The keyword has no numeric spelling (`ror` is rejected, `shift = 11` is unallocated), and a `modifiers` entry cannot carry it — the `-lsl0` row with `{"name": "lsl", "value": 3}` is `E-OPERAND-003` (`N19`), because the materializer would otherwise emit the unshifted word and report success (`ADR-0015`, `EXP-0017`). | frozen |

## v0 surface (OD-10)

v0 ships only the forms its slices use. The definition table is the feature
surface: a variant that is absent cannot be selected, repaired or approximated,
and naming it is `E-FORM-001`. There is no feature flag and no partially
implemented form.

The x86-64 slice is seven forms covering four frozen `EC` rows:

| `form_id` | Bytes | Operand signature | Covers |
|---|---|---|---|
| `x86:mov/rm-r64/legacy` | `REX.W 89 /r` | dest `rm64`, src `r64` | EC-27 |
| `x86:mov/r64-rm/legacy` | `REX.W 8B /r` | dest `r64`, src `rm64` | EC-27 |
| `x86:add/rm64-imm8/legacy` | `REX.W 83 /0 ib` | dest `rm64`, imm `imm8` | EC-01 |
| `x86:add/rm64-imm32/legacy` | `REX.W 81 /0 id` | dest `rm64`, imm `imm32` | EC-01, EC-04 |
| `x86:add/rax-imm32/legacy` | `REX.W 05 id` | imm `imm32`, register fixed to `rax` | EC-04 |
| `x86:jmp/rel8/legacy` | `EB cb` | `rel8` target | EC-03 |
| `x86:jmp/rel32/legacy` | `E9 cd` | `rel32` target | EC-03 |

The variant names the operand signature as the ISA opcode table spells it, which
is what makes the two `mov` forms and the two `add` immediate forms distinct
without an extra choice field. A plan that names `x86:mov/r64-r64` or
`x86:add/rm64-imm` is rejected: those ids are not in the v0 definition.

The AArch64 slice is eighteen forms across six documents, covering nine frozen
`EC` rows:

| `form_id` | Encoding | Operand signature | Table | Covers |
|---|---|---|---|---|
| `aarch64:add/x64-x64-x64-lsl0` | `ADD (shifted register)`, `sf=1`, `shift=LSL`, `imm6=0` | dest `x64`, src `x64`, src2 `x64` | all | EC-11, EC-13 |
| `aarch64:add/x64-imm12-lsl0` | `ADD (immediate)`, `sf=1`, `sh=0` | dest `x64`, src `x64`, imm `imm12` | all | EC-11, EC-12 (`sh=0` half) |
| `aarch64:add/x64-imm12-lsl12` | `ADD (immediate)`, `sf=1`, `sh=1` | dest `x64`, src `x64`, imm `imm12` (field content) | `0.2.0`+ | EC-11, EC-12 (`sh=1` half) |
| `aarch64:bl/imm26` | `BL imm26` | `imm26` target | all | A64-P5 |
| `aarch64:adrp/x64-imm21` | `ADRP immlo:immhi` | dest `x64`, `imm21` target | all | EC-15, EC-17 |
| `aarch64:b.cond/imm19` | `B.cond`, `o0=0` | cond `cond4`, `imm19` target | `0.3.0`+ | EC-29, A64-P4 |
| `aarch64:ldr/x64-base-imm12` | `LDR (immediate)`, `size=11`, bit 24 = 1 | dest `x64`, base `x64`, disp `imm12` (8-byte units) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:ldr/x64-base-imm9-pre` | `LDR (immediate)`, bits 11–10 = `11` | dest `x64`, base `x64`, disp `imm9` (signed bytes) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:ldr/x64-base-imm9-post` | `LDR (immediate)`, bits 11–10 = `01` | dest `x64`, base `x64`, disp `imm9` (signed bytes) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:ldur/x64-base-imm9` | `LDUR`, bits 11–10 = `00` | dest `x64`, base `x64`, disp `imm9` (signed bytes) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:str/x64-base-imm12` | `STR (immediate)`, `size=11`, bit 24 = 1 | src `x64`, base `x64`, disp `imm12` (8-byte units) | `0.4.0`+ | EC-14, A64-P3 |
| `aarch64:movz/x64-imm16-lsl0` | `MOVZ`, `sf=1`, `opc=10`, `hw=00` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:movz/x64-imm16-lsl16` | `MOVZ`, `hw=01` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:movz/x64-imm16-lsl32` | `MOVZ`, `hw=10` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:movz/x64-imm16-lsl48` | `MOVZ`, `hw=11` | dest `x64`, imm `imm16` (field content) | `0.5.0`+ | EC-30, A64-P7 |
| `aarch64:add/x64-x64-x64-imm6-lsl` | `ADD (shifted register)`, `sf=1`, `shift=LSL` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` (amount) | `0.6.0`+ | EC-31, A64-P8 |
| `aarch64:add/x64-x64-x64-imm6-lsr` | `ADD (shifted register)`, `shift=LSR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` (amount) | `0.6.0`+ | EC-31, A64-P8 |
| `aarch64:add/x64-x64-x64-imm6-asr` | `ADD (shifted register)`, `shift=ASR` | dest `x64`, src `x64`, src2 `x64`, imm `imm6` (amount) | `0.6.0`+ | EC-31, A64-P8 |

The `-lsl0`/`-lsl12` suffix is part of the id because the MRS node leaves
`shift`, `imm6` and `sh` variable; the table pins them and the name says so
(`07_definition_format.md` §8.2). Both halves of `EC-12` are therefore carried
by a form variant, not by a value-dependent bit. `-lsl12` is in `0.2.0` and later
only, so naming it against `0.1.0` is `E-FORM-001` (`N01`). The
`-lsl0` … `-lsl48` suffix on the four `movz` rows is the same device for the
2-bit `hw` lane selector, and `-imm6-lsl` … `-imm6-asr` is the same device again
for the 2-bit `shift` selector, with the amount as the last operand.

`b.cond` is the opposite case and shows where the line is: the condition is a
4-bit *operand* (`EC-29`), so one row covers all sixteen conditions, while the
`b.cond`-vs-`cbz`-vs-`tbz` choice of instruction is a form variant (`EC-18`).

`movz` is the third shape, between those two. The lane is an *encoding* field
(`hw` at bits 22–21), not a condition and not a choice of instruction, and the
assembly language gives it four spellings (`lsl #0/#16/#32/#48`) but no operand:
`llvm-mc` rejects `lsl #8` and rejects a pre-scaled literal such as `#0x10000`
(`EXP-0016` §2). So `0.5.0` carries one row per lane, `imm16` stays field content
in `0…65535`, and the `mov` alias — which *does* pick the lane from the literal's
value — stays out as `EC-16` (`EC-30`, ADR-0014).

The shift on a register operand is the fourth shape and the one a plan would most
naturally try to carry as a modifier. It is two decisions in one spelling:
`add x0, x1, x2, lsl #3` names a *kind* (`lsl`/`lsr`/`asr`, three keywords and no
numeric spelling — `ror` is rejected and `shift = 11` is unallocated) and an
*amount* (`imm6`, `0…63`). `0.6.0` carries the kind as the form
(`-imm6-lsl` … `-imm6-asr`) and the amount as an `imm6` operand, because a
`modifiers` entry is a guard that never writes a bit: the `-lsl0` row with
`{"name": "lsl", "value": 3}` is `E-OPERAND-003` (`N19`), and silently accepting it
would emit the unshifted word and report success (`EC-31`, ADR-0015). The extend
family (`add x0, x1, w2, uxtw #3` → `0x8b224c20`) is a different node with a
narrower source operand, so it has no row (`E-FORM-001`, `N01e`).

The five load/store rows carry `EC-14` and are the AArch64 half of `ADR-0008`:
the address is `base` + `disp`, never one memory payload, and the addressing
kind is the `form_id`. `disp` is field content, so the unit belongs to the row:
the two unsigned-offset rows count 8-byte units (`#16` is `disp = 2`) and the
three `imm9` rows count signed bytes (`-256 … 255`), with `align_bits = 0` on
both because the slot holds the field, not the byte offset (`ADR-0013`). The
register-offset kind (`aarch64:ldr/x64-base-regoff`), the literal load and the
store's `imm9` kinds are absent, so naming any of them is `E-FORM-001`.

`EC-05`, `EC-09` and `EC-10` are out of v0. `X86-P9` (explicit encoding family)
stays deferred, so `vex`/`evex` never appear in a v0 `form_id`.

The RV64 slice is eight forms across two documents, generated from the pinned UDB
nodes (ADR-0007, ADR-0009). Seven base-`I` forms are in `0.1.0`; `c.addi` joins
them in `0.2.0`, because it needs `rv64c` and the document's extension set is part
of its identity:

| `form_id` | Encoding | Operand signature | Table | Covers |
|---|---|---|---|---|
| `riscv:add/rd-rs1-rs2` | `ADD` R-type, `funct7=0`, `funct3=0` | dest `xreg`, src `xreg`, src2 `xreg` | `0.1.0` | `RV-P1` |
| `riscv:addi/rd-rs1-imm12` | `ADDI`, `funct3=0` | dest `xreg`, src `xreg`, imm `imm12` | `0.1.0` | `RV-P2` |
| `riscv:beq/rs1-rs2-imm12` | `BEQ` B-type, `funct3=0` | src `xreg`, src2 `xreg`, `imm12` target | `0.1.0` | `RV-P4`, `EC-22` |
| `riscv:jal/rd-imm20` | `JAL` J-type | dest `xreg`, `imm20` target | `0.1.0` | `RV-P5`, `EC-22` |
| `riscv:auipc/rd-imm20` | `AUIPC` U-type | dest `xreg`, `imm20` target | `0.1.0` | `RV-P8` (field half), `EC-21` (instruction half) |
| `riscv:ld/rd-base-imm12` | `LOAD` I-type, `funct3=011` | dest `xreg`, base `xreg`, disp `imm12` | `0.1.0` | `RV-P3` |
| `riscv:sd/rs-base-imm12` | `STORE` S-type, `funct3=011` | src `xreg`, base `xreg`, disp `imm12` | `0.1.0` | `RV-P3` |
| `riscv:c.addi/rd-imm6` | `C.ADDI` CI-format, 16-bit | dest `xreg` (`excl 0`), imm `imm6` (`excl 0`) | `0.2.0` | `RV-P7`, `EC-19`, `OD-14` |

The two memory forms decompose the address into `base` + `disp` rather than one
payload operand, and the addressing form is the `form_id` (ADR-0008, `OD-13`).
That is the same carrier `EC-02` names for x86's disp8/disp32 split, and it is
what keeps an encoder from choosing `mod` from the displacement's value.

`EC-19` is carried by `riscv:c.addi/rd-imm6`: `0.2.0` names the compressed form,
`0.1.0` does not, and a plan that asks for it against `0.1.0` is `E-FORM-001`
(`N01c`). Its `not: 0` is the `excluded` field of ADR-0009/`OD-14`; naming either
zero is `E-RANGE-004` (`N16a`, `N16b`), never a silent `c.nop`/HINT.

`EC-21` is now carried on its PC-relative side. The `auipc` form fixes the
instruction, `pcrel_hi20`/`pcrel_lo12` carry the transform, ADR-0010 pins the
psABI relation as `pc_reference_rule: pcrel_hi` plus a 1:N `pair_group`, and two
fixtures claim it — `RV-P8-pcrel-pair` on the record side and
`RV-P8-pcrel-pair-resolved` against a linked binary. What EC-21 still does not
decide is the *absolute* alternative `lui`+`addi`: no v0 form carries `lui`, so
the choice is embodied by which form the plan names and cannot yet be measured
against both sides. `EC-20` stays without a carrier because v0 has no 3-bit
compressed register field (`c.lw`-style CL/CS forms are not in either table); its
example is `c.lw`.

## Evidence

### Phase 1 (2026-11-03)

`docs/fmp-v0/90_boundary_audit.md` supplies observed counterexamples. "Observed"
means a built assembler produced both variants or refused to, and llvm-mc 23.1.2
agreed where it could express the case.

- `EC-01` — F-07: `add rax, 1` → `48 83 c0 01` in both XirAsm and llvm-mc; there
  is no way to request the `81 /0 id` form.
- `EC-02` — F-07: `mov rax, [rbp-8]` → `48 8b 45 f8` (disp8); `[rbp-200]` →
  disp32. Chosen implicitly in both tools.
- `EC-03` — F-04, F-06: XirAsm `jmp 0x10` → `eb 0e`, `jmp 0x1000` →
  `e9 fb 0f 00 00`. The same mnemonic changes size with the target value.
- `EC-04` — F-07: `add rax, 300` → `48 05 2c 01 00 00` (accumulator) in both
  tools; `81 /0 id` is equally legal and unreachable.
- `EC-16` — EXP-0001 §5: AArch64 `mov x13, #1` assembled to `movz` bytes
  (`2d 00 80 d2`) inside the macro layer.
- `EC-19` — F-11, `EXP-0012` §2: `addi a0, a0, 1` stays 4 bytes without `+c`; with
  `-mattr=+c` llvm-mc assembles the same line to `05 05`, and `c.addi a4, 5` is
  2 bytes only when written explicitly. The plan-side `form_id` is the carrier.
- `EC-20` — F-10, `EXP-0012` §2: `c.lw a6, 0(a0)` is rejected; `c.lw a2, 0(a0)`
  is `10 41`. The earlier example (`c.addi a6, 5`) was wrong: measured, `c.addi`
  accepts it as `15 08`, because its `xd` is a 5-bit field. The `x8..x15` rule is
  per form, not per `c.` prefix.

### Measured 2026-11-04 (llvm-mc 23.1.2)

Full run, method and caveats: `research/evidence/experiments/EXP-0003/`. Rerun
with `python exp0003.py`; the README table is regenerated by `--emit`.

Commands: `llvm-mc -triple=x86_64 -x86-asm-syntax=intel -show-encoding` for
assembly, `-disassemble` with a byte list for decoding, `-filetype=obj` plus
`llvm-objdump -d` for branch layout.

| Observation | Result |
|---|---|
| `mov rax, rbx` | `48 89 d8` |
| `mov eax, ebx` | `89 d8` |
| `48 8b c3` disassembles | `movq %rbx, %rax` |
| `48 89 d8` disassembles | `movq %rbx, %rax` |
| `0x40 0x89 0xd8` disassembles | `movl %ebx, %eax` |
| `add rax, 1` | `48 83 c0 01` |
| `add rax, 300` | `48 05 2c 01 00 00` |
| `48 81 c0 2c 01 00 00` disassembles | `addq $300, %rax` |
| `mov eax, 300` | `b8 2c 01 00 00` |
| `c7 c0 2c 01 00 00` disassembles | `movl $300, %eax` |
| `jmp .+0x81` | `eb 7f` (2 B) |
| `jmp .+0x82` | `e9 7d 00 00 00` (5 B) |
| `jmp .+0x1000` | `e9 fb 0f 00 00` |

Two oracle cautions found while collecting these:

- llvm-mc does not use a bare integer branch operand as an absolute target:
  `jmp 0x12`, `jmp 0x7f`, `jmp 0x80`, `jmp 0x1000` and `jmp 5` all emit
  `e9 00 00 00 00` under `-filetype=obj`. Only a label or a `.+N` expression
  reaches the encoder.
- `llvm-mc -disassemble` prints the branch *displacement*, not the resolved
  target (`eb 0e` prints as `jmp 14`). Branch target arithmetic therefore cannot
  be validated with the disassembler; the fixture must compare bytes and compute
  the target from the plan.

## Not choices

These are computed by the definition and MUST NOT be stored or requested:

- opcode bits, funct fields, and ModRM/RM field placement implied by the form;
- `REX.W` for a 64-bit x86 form;
- register number encoding from an operand's `target_type`;
- immediate bit placement implied by the form (including B-type/J-type scatter);
- the value of a fixup-covered field, which that fixup writes alone (OD-02);
- byte order, which comes from `target_identity.byte_order`;
- alignment and padding, which are `fill` fragments, not instruction properties.

If a proposed field merely restates one of these, it is over-freezing: it
duplicates rule knowledge into the plan and will drift.

## Validation obligation

The materializer performs exact checks; none of them compares a "choice set".

Plan side, in contract §13 order:

1. `form_id` resolves to exactly one definition row (`E-FORM-001`). No default,
   no variant inferred from operand values, no appending of a width suffix.
2. Operand signature matches the form's declared signature: count, role sequence,
   `kind`, `target_type` (`E-OPERAND-001`/`002`/`003`).
3. Operand values fit the form's declared ranges (`E-RANGE-001`/`002`/`003`).
4. Encoded length equals `expected_size` (`E-SIZE-001`).
5. If present, the hash of the emitted bytes equals `expected_digest`
   (`E-BYTE-001`).
6. Fixup fields are all present; nothing is defaulted. Each fixup has exactly one
   writer and one effect: `resolve_in_place` writes, `emit_relocation` zeroes
   and records (`E-FIXUP-*`, OD-02).

Definition side:

- The form table is keyed by `(form_id, operand signature, target_identity)` and
  maps to exactly one byte template. Ambiguity is unrepresentable, so there is no
  runtime branch that could choose.
- A wildcard or fallback row that can match more than one form is a definition
  defect (`E-DEF-001` at load time), not a plan error.

Test obligation per `EC` row:

- carrier is `none`: a test must show the variation cannot be requested — the
  plan cannot produce those bytes, and if a plan claims them via
  `expected_digest` the result is `E-BYTE-001`.
- carrier is a plan field: a test must show that removing or falsifying the
  carrier is rejected, not repaired.
- carrier is `form variant`: the negative test is `N01` (a coarse or absent form
  is `E-FORM-001`).

## Open work

The v0 `EC` set is decided (OD-10). What remains is per-row evidence:

- `EC-05`, `EC-08`, `EC-09`, `EC-10`, `EC-16`, `EC-18`, `EC-23`, `EC-24`,
  `EC-25`, `EC-26` are `draft` and need an observed counterexample before they can
  be frozen. None of them is required by the x86 slice. `EC-08`, `EC-10` and
  `EC-26` name `operand modifier` as the carrier for `addr_size`, `lock`/`rep` and
  `aq`/`rl`; ADR-0015 shows that in v0 a modifier is a guard that never writes a
  bit, so each of those rows still needs a decision about which of the two
  readings it is.
- The AArch64 rows now have a table (ADR-0005, ADR-0006, ADR-0011, ADR-0012):
  EC-11, EC-13, EC-15 and EC-17 are exercised by `definitions/aarch64/0.1.0.json`;
  EC-12 in both halves, `sh=0` in `0.1.0` and `sh=1` in `0.2.0`; EC-29 in `0.3.0`,
  which carries the condition as an operand rather than as sixteen forms; EC-14 in
  `0.4.0`, one row per addressing kind; EC-30 in `0.5.0`, one row per `movz` lane;
  EC-31 in `0.6.0`, one row per shift keyword with the amount as an `imm6`
  operand.
  EC-16 (the `mov` alias family) and EC-18 stay `draft` and are not in the v0
  surface: EC-30 decides the lane *inside* `movz` and does not decide which
  lowering a `mov` request becomes. EC-13's shifted-register half is carried by
  `0.1.0` and `0.6.0`; its extended-register half has no row yet, and neither has
  `sub`, the `w` rows or the load/store kinds listed above.
- The RV64 source is settled (ADR-0007: the UDB resolved spec, pinned by archive
  hash in `EXP-0009`), and both documents are generated: `definitions/rv64/0.1.0.json`
  and `0.2.0.json` (ADR-0009). `RV-P7` (`c.addi`) needed a format decision before
  it could land: the source forbids `imm = 0` and `xd = 0`, and `fmp-def/0.1`
  cannot express `not: 0` (§4 of `07_definition_format.md`); ADR-0009 added the
  closed `excluded` list instead of widening the schema.
