# Encoding Choices

Status: **draft**. This is the operational form of INV-02.

## The rule

Given a frozen plan and a pinned definition, exactly one byte sequence may result.
A decision belongs in the plan only when two conditions hold:

1. Several outputs are legal for the same `form_id + operands + target`.
2. The outputs are observably different (different bytes, different size, or
   different fixup behavior).

If the value is uniquely determined by the frozen input and the versioned rules,
the encoder computes it. If it is not, the plan must say it explicitly.

Two failure modes to avoid:

- **Under-frozen:** the encoder still has to choose. Detected by asking "could
  two honest implementers of this definition emit different bytes for this
  plan?"
- **Over-frozen:** the plan carries raw bit patterns and the definition becomes
  decorative. Detected by asking "would this plan still be valid after a
  legitimate definition bug-fix that does not change observable semantics?"

## Test used to classify a choice

For each candidate:

1. Name the two or more legal outputs and their observable difference.
2. Ask whether the difference is *implied* by `form_id` (same form ⇒ same bytes).
3. Ask whether the difference is *implied* by an operand (e.g. a width-typed
   operand).
4. Ask whether the difference is a range legality issue rather than a choice.
5. Otherwise it is an explicit choice and gets an `EC-*` ID.

## Registry

| ID | ISA | Choice | Observable difference | Owner | Counterexample if unfrozen | Status |
|---|---|---|---|---|---|---|
| EC-01 | x86-64 | `add r/m64, imm` as sign-extended imm8 (`83 /0 ib`) vs imm32 (`81 /0 id`) | 4 vs 7 bytes | `form_id` variant (`r64-imm8` / `r64-imm32`) | `add rax, 1` is legal both ways; an encoder that "picks short" violates INV-02 and shifts every later offset. | frozen |
| EC-02 | x86-64 | Memory displacement as disp8 (mod=01) vs disp32 (mod=10) | 1 vs 4 displacement bytes | `form_id` variant (`mem-disp8` / `mem-disp32`) | `mov rax, [rbp-8]` fits disp8; forcing disp32 is legal but 3 bytes longer. | frozen |
| EC-03 | x86-64 | Relative branch rel8 (`EB`/`70+cc`) vs rel32 (`E9`/`0F 80+cc`) | 2 vs 5/6 bytes, different range | `form_id` variant (`rel8` / `rel32`) | Both are legal for a near target; choosing by distance is relaxation (INV-04). | frozen |
| EC-04 | x86-64 | Accumulator short form vs ModRM immediate form | Different opcode bytes, same length | `form_id` variant | `mov eax, imm32` (`B8+rd`) vs `mov r/m32, imm32` (`C7 /0`) both exist. | draft |
| EC-05 | x86-64 | `moffs` absolute form (`A0-A3`) vs ModRM with disp32 | Different length and prefix behavior | `form_id` variant | `mov al, [0x1234]` has two legal encodings with different sizes. | draft |
| EC-06 | x86-64 | REX presence and W/R/X/B bits; high-byte registers (`AH`) are illegal with any REX | Legality and one prefix byte | `operand.target_type` + definition rule | A plan naming `AH` with a 64-bit operand cannot be encoded; the encoder must not silently switch registers. | frozen |
| EC-07 | x86-64 | Operand-size prefix `0x66` vs distinct 32/64-bit form for 16-bit operations | One prefix byte, different semantics | `form_id` | `add ax, bx` requires `66`; omitting it changes the operand width. | frozen |
| EC-08 | x86-64 | Address-size prefix `0x67` in 64-bit mode | One prefix byte and truncation semantics | `operand.modifiers` (`addr_size`) | 32-bit addressing in 64-bit mode truncates the effective address. | draft |
| EC-09 | x86-64 | Legacy SSE vs VEX vs EVEX for the same operation | Prefix family, 2–4 bytes, register reach | `form_id` encoding family | `vaddps xmm0,xmm1,xmm2` fits 2-byte VEX but is also expressible in EVEX. | draft |
| EC-10 | x86-64 | `LOCK` / `REP` / segment prefix presence | One or more prefix bytes | `operand.modifiers` / `form_id` | `lock add [rax], ebx` vs plain `add` differ only by `F0`, with different semantics. | draft |
| EC-11 | AArch64 | 32-bit (`w`) vs 64-bit (`x`) variant | Different `sf` bit, different semantics | `operand.target_type` (`wreg` / `xreg`) | `add w0,w1,w2` vs `add x0,x1,x2` differ in one bit and in overflow behavior. | frozen |
| EC-12 | AArch64 | `add/sub` immediate: imm12 vs imm12 shifted by 12 | Different `sh` bit and range | `form_id` variant (`imm12` / `imm12-scaled`) | `add x0,x1,#1` and `add x0,x1,#1,lsl #12` are both legal spellings of different values. | frozen |
| EC-13 | AArch64 | Shifted-register vs extended-register form | Different `shift`/`option` fields | `form_id` variant | `add x0,x1,x2,lsl #3` vs `add x0,x1,w2,uxtw #3` share a mnemonic but not an encoding. | frozen |
| EC-14 | AArch64 | Load/store addressing: unsigned-offset vs pre-index vs post-index vs register-offset | Different addressing bits and writeback semantics | `form_id` variant | `ldr x0,[x1,#8]` vs `ldr x0,[x1],#8` differ in writeback; an encoder must not pick one. | frozen |
| EC-15 | AArch64 | Literal load vs `adrp` + `lo12` sequence | Instruction count (INV-03 boundary) | `form_id` + layout | A "load from label" request is a plan decision: one literal load or two instructions. | frozen |
| EC-16 | AArch64 | `mov` alias family: `movz` / `movn` / `orr` immediate / register | Different opcodes | `form_id` | `mov x0,#1` can be `movz` or `orr`; both are legitimate and differ in bytes. | draft |
| EC-17 | AArch64 | `adr` (±1 MB) vs `adrp` (page) for a symbol address | Different instruction and fixup kind | `form_id` + fixup kind | Choosing `adrp` when the target is in range changes both bytes and relocation semantics. | frozen |
| EC-18 | AArch64 | `b.cond` vs `cbz/cbnz` vs `tbz/tbnz` for a conditional transfer | Different forms and operand sets | `form_id` | A planner that says only "branch if zero" has not chosen a form. | draft |
| EC-19 | RV64 | Compressed (`c.*`, 2 bytes) vs standard (4 bytes) | 2 vs 4 bytes | `form_id` (explicit `c.` mnemonic) | `c.addi` and `addi` are distinct forms; an encoder that compresses `addi` violates INV-02. | frozen |
| EC-20 | RV64 | Compressed register class `x8–x15` (3-bit field) vs full 5-bit register | Legality | `operand.target_type` + definition rule | `c.addi x16, 1` is not encodable; the encoder must reject, not widen. | frozen |
| EC-21 | RV64 | Absolute vs PC-relative symbol materialization: `lui`+`addi` vs `auipc`+`addi` | Instruction pair and relocation kind | `form_id` + fixup pair | Choosing PC-relative changes both instructions and the fixup pair. | frozen |
| EC-22 | RV64 | B-type/J-type immediate scatter is fixed by form, but the PC base is not | Fixup value | `pc_reference_rule` (see 03) | Same form, different `P`, different bytes: a contract bug. | frozen |
| EC-23 | RV64 | `jal` vs `jalr` for a call; `c.j` vs `jal` for a jump | Different instruction, range, link behavior | `form_id` | A "call" that becomes `jalr` needs a base register the plan never provided. | draft |
| EC-24 | RV64 | `fence` `fm`/`pred`/`succ` field values | Bits 31–28, 27–24, 23–20 | `operand.target_type` (`fence_mask`) | `fence rw,rw` vs `fence iorw,iorw` differ in fields, not in mnemonic. | draft |
| EC-25 | RV64 | CSR operation immediate (`csrrwi`) vs register (`csrrw`) | Different funct3 | `form_id` | `csrrwi` cannot carry a register operand; a generic "CSR op" leaves the choice open. | draft |
| EC-26 | RV64 | Atomic `aq`/`rl` bits | Bits 26–25 | `operand.modifiers` | `amoadd.w` vs `amoadd.w.aqrl` differ in ordering semantics and bytes. | draft |

`frozen` means the counterexample is written and the owner is decided. `draft`
means the owner is plausible but not yet proven against a real vector.

## Not choices

These are computed by the definition and MUST NOT be stored as choices:

- opcode bits, funct fields, and ModRM/RM field placement implied by the form;
- REX.W for a 64-bit x86 form;
- register number encoding from an operand's `target_type`;
- immediate bit placement implied by the form (including B-type/J-type scatter);
- byte order, which comes from `target_identity.byte_order`;
- alignment, which is a `fill` fragment, not an instruction property.

If a proposed plan field merely restates one of these, it is over-freezing: it
duplicates rule knowledge into the plan and will drift.

## Validation obligation

For each instruction, the materializer MUST compute the *required choice set*
from the resolved form and operand types, then compare it with the plan's
`encoding_choices`:

- missing entry → `E-CHOICE-001` (N01);
- unexpected entry → `E-CHOICE-002`;
- duplicate entry → `E-CHOICE-002`;
- value outside the form's allowed set → `E-CHOICE-003`.

The comparison MUST be a set comparison over the definition's declared
requirements, never a "best available" match.

## Open work

Which of EC-01…EC-26 must be in v0 is decided in `05_open_decisions.md`
(OD-01, OD-04) once the three slices are selected.
