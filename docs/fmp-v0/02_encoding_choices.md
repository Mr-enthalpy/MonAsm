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
| EC-14 | AArch64 | Load/store addressing: unsigned-offset vs pre-index vs post-index vs register-offset | Different addressing bits and writeback semantics | `form variant` (`unsigned-offset` / `pre-index` / `post-index` / `register-offset`) | `ldr x0,[x1,#8]` vs `ldr x0,[x1],#8` differ in writeback; an encoder must not pick one. | frozen |
| EC-15 | AArch64 | Literal load vs `adrp` + `lo12` sequence | Instruction count (INV-03 boundary) | `form variant` (one instruction vs two planned instructions) | A "load from label" request is a plan decision: one literal load or two instructions. | frozen |
| EC-16 | AArch64 | `mov` alias family: `movz` / `movn` / `orr` immediate / register | Different opcodes | `form variant` (`movz` / `movn` / `orr-imm` / `reg`) | `mov x0,#1` can be `movz` or `orr`; both are legitimate and differ in bytes. | draft |
| EC-17 | AArch64 | `adr` (±1 MB) vs `adrp` (page) for a symbol address | Different instruction and fixup kind | `form variant` + `fixup field` (`kind`) | Choosing `adrp` when the target is in range changes both bytes and relocation semantics. | frozen |
| EC-18 | AArch64 | `b.cond` vs `cbz/cbnz` vs `tbz/tbnz` for a conditional transfer | Different forms and operand sets | `form variant` | A planner that says only "branch if zero" has not chosen a form. | draft |
| EC-19 | RV64 | Compressed (`c.*`, 2 bytes) vs standard (4 bytes) | 2 vs 4 bytes | `form variant` (the `c.` mnemonic is a different form) | `c.addi` and `addi` are distinct forms; an encoder that compresses `addi` violates INV-02. | frozen |
| EC-20 | RV64 | Compressed register class `x8–x15` (3-bit field) vs full 5-bit register | Legality | `operand type` + definition rule | `c.addi x16, 1` is not encodable; the encoder must reject, not widen. | frozen |
| EC-21 | RV64 | Absolute vs PC-relative symbol materialization: `lui`+`addi` vs `auipc`+`addi` | Instruction pair and relocation kind | `form variant` + `fixup field` (`kind`) | Choosing PC-relative changes both instructions and the fixup pair. | frozen |
| EC-22 | RV64 | B-type/J-type immediate scatter is fixed by form, but the PC base is not | Fixup value | `fixup field` (`pc_reference_rule`) | Same form, different `P`, different bytes: a contract bug. | frozen |
| EC-23 | RV64 | `jal` vs `jalr` for a call; `c.j` vs `jal` for a jump | Different instruction, range, link behavior | `form variant` | A "call" that becomes `jalr` needs a base register the plan never provided. | draft |
| EC-24 | RV64 | `fence` `fm`/`pred`/`succ` field values | Bits 31–28, 27–24, 23–20 | `operand type` (`fence_mask`) | `fence rw,rw` vs `fence iorw,iorw` differ in fields, not in mnemonic. | draft |
| EC-25 | RV64 | CSR operation immediate (`csrrwi`) vs register (`csrrw`) | Different funct3 | `form variant` | `csrrwi` cannot carry a register operand; a generic "CSR op" leaves the choice open. | draft |
| EC-26 | RV64 | Atomic `aq`/`rl` bits | Bits 26–25 | `operand modifier` (`aq` / `rl`) | `amoadd.w` vs `amoadd.w.aqrl` differ in ordering semantics and bytes. | draft |
| EC-27 | x86-64 | `89 /r` (`MOV r/m64, r64`) vs `8B /r` (`MOV r64, r/m64`) | Different opcode bytes, same length, same semantics | `form variant` (`rm-r64` / `r64-rm`) | `mov rax, rbx` is both `48 89 d8` and `48 8b c3`; both disassemble to `movq %rbx, %rax` and both are 3 bytes. `expected_size` cannot detect a wrong choice, and no operand distinguishes them; only `expected_digest` can (OD-01). | frozen |
| EC-28 | x86-64 | Minimal prefix set vs a redundant prefix (`89 d8` vs `40 89 d8`; likewise a redundant `66`, segment or `REX` prefix) | One byte per redundant prefix, identical semantics | `none` — definition rule: emit the minimal prefix set | `40 89 d8` decodes as `movl %ebx, %eax`, exactly like `89 d8`. Two honest implementers could differ by one byte with no observable semantic difference, so the definition must pin minimality and no plan field may request the redundant byte. | frozen |

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

`EC-05`, `EC-09` and `EC-10` are out of v0. `X86-P9` (explicit encoding family)
stays deferred, so `vex`/`evex` never appear in a v0 `form_id`. The RV64 and
AArch64 slices are not yet chosen; their rows stay `draft` where marked.

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
- `EC-19` — F-11: `addi a0, a0, 1` stays 4 bytes; `c.addi a4, 5` is 2 bytes only
  when written explicitly.
- `EC-20` — F-10: `c.addi a6, 5` rejected; the `x8..x15` range is enforced at
  `encode.zig:1109-1112`.

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
  be frozen. None of them is required by the x86 slice.
- AArch64 rows depend on the knowledge source question (OD-07), which is still
  blocked on a licence review.
