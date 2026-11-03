# ADR-0008: A memory operand is field-level operands, not a payload shape

- Status: accepted
- Date: 2026-11-04
- Settles: `OD-13` (how a memory operand is represented in a plan)
- Supersedes: none
- Superseded by: none

## Context

Four coverage rows — `X86-P4`/`P5`/`P6`, `A64-P3` and `RV-P3` — were all blocked
by the same sentence in `01_contract.md` §8.1: `fmp/0.1` fixes four payload
shapes (`{reg}`, `{value}`, `{symbol_id}`, `{}`), and a payload that is none of
them is `E-OPERAND-003`. §8 meanwhile sketched the *intended* kinds for a later
slice — `x86.mem`, `aarch64.mem.*`, `riscv.mem.base-offset` — and labelled the
table `draft`. The rows could not be planned until the representation was
chosen, and choosing it inside a form definition would have made the operand,
not the `form_id`, carry an encoding decision (`OD-11`).

Three measurements decide the question. Each was taken with `llvm-mc 23.1.2`
on 2026-11-04 and is recorded in `EXP-0011`.

1. **A memory operand spans fields with different ranges and different owners.**
   `ld a0, 8(a1)` (`03 b5 85 00`) is a 5-bit `xs1`, a 12-bit sign-extended
   `imm`, and a 5-bit `xd`. `sd a2, 2047(a1)` (`a3 bf c5 7e`) has the same `xs1`
   base plus a 5-bit `xs2` data register and an `imm` that is scattered over
   `[31:25]` and `[11:7]`.
   A single operand holding `{base, disp}` would need two ranges, two bit
   positions, and two answers to "which field does a fixup cover".
2. **The address computation has no encoding form to choose in RV64, but x86
   does.** `movq 8(%rcx), %rax` is `48 8b 41 08` (ModRM mod=01, disp8), while
   `movq 4096(%rcx), %rax` is `48 8b 81 00 10 00 00` (mod=10, disp32): the same
   mnemonic and the same operand list produce a 4-byte and a 7-byte encoding,
   and only the displacement's *value* distinguishes them. `movq (%rbp), %rax`
   is `48 8b 45 00`, not a 3-byte mod=00 form, because mod=00 with
   `r/m = 101` means RIP-relative; the base register's value forces a disp8.
3. **AArch64's offset slot is already the field, not the byte displacement.**
   `ldr x0, [x1, #16]` is `20 08 40 f9`: `imm12 = 2`, because the field is
   scaled by the access size. §8.3 already says the slot holds field content,
   so a `{base, disp}` payload would have to say whether `disp` is bytes or the
   field value — a second decision in the same field.

The failure this ADR prevents is not a wrong byte in one fixture. It is an
encoder that reads `disp` and picks mod=01 when it fits in 8 bits, or reads the
base register and inserts a SIB byte — that is `INV-02` ("no implicit
encoding-form selection") with the operand list unchanged, so no plan could
record which choice was made and no digest could pin it.

## Decision

1. **v0 has no memory payload shape.** A memory operand is decomposed into one
   operand per encoded field, using the roles `01_contract.md` §8 already
   defines: `base` for the address register, `disp` for the offset, and `index`
   /`scale` where an ISA has them. `fmp/0.1` keeps its four shapes, and a
   composite object such as `{"mem": {...}}` is `E-OPERAND-003` — now pinned by
   a fixture (`N15`) instead of being an unexercised branch.
2. **The addressing form is a `form_id` variant, never a value-driven choice.**
   Two instructions that differ in ModRM mod, in SIB presence, in pre/post-index,
   or in scaled/unscaled immediate need two `form_id`s. A `form_id` that leaves
   the choice open is not a v0 form.
3. **The slot holds field content (`§8.3`).** RV64 `ld`/`sd` do not scale, so
   `disp` is the byte displacement. AArch64's unsigned-offset `imm12` is scaled
   by the access size, so a plan states the field value or a fixup supplies it;
   which of the two is decided with the AArch64 form, not here. RV64's
   `auipc`-based pair keeps `transform_shift` in the fixup, as `ADR-0007` §4
   requires.
4. **RV64 `ld`/`sd` are the first slice.** The forms are
   `riscv:ld/rd-base-imm12` (`dest`/`base`/`disp`) and
   `riscv:sd/rs-base-imm12` (`src`/`base`/`disp`), generated from
   `inst/I/{ld,sd}.yaml` in the pinned UDB drop. The store's data operand is
   `src`; `src2` is reserved for a form with two source registers, and there is
   no second source here.
5. **x86 and AArch64 memory rows stay out until their variants are named.**
   `X86-P4`–`P6` need at least a mod=00/01/10 split and a SIB split, each with
   its own oracle bytes; `A64-P3` needs its four addressing kinds as four
   variants. Neither is a payload question any more, and neither is admitted by
   this ADR.
6. **§8's draft kinds are marked as not-v0.** The table is replaced by the
   per-ISA carrier column, so a later reader does not mistake a sketch for a
   promise.

## Consequences

- `RV-P3` unblocks with no contract change: the roles and the slot model
  already exist, and the only new artifacts are two generated forms, one
  positive fixture with four instructions, and one negative fixture.
- `E-OPERAND-003` stops being an unexercised rejection path. `N15` shows that a
  plan which tries to hand the materializer a base and an offset in one operand
  is rejected rather than partially read.
- The x86 slice gains a *precondition*, not a shortcut: before `X86-P4`, the
  `form_id` set must be enumerated from the ModRM/SIB shapes with measured
  bytes, because the encoder may not choose mod. That is a larger slice than it
  looked, and it is now honest about it.
- A future ISA with a memory operand that is genuinely one field (a compressed
  load's `uimm` in `c.lwsp` is not one — it also carries the destination) still
  follows this rule: if a field group is one value, it is one slot.
- Cost: a plan is more verbose for a memory instruction (three operands instead
  of one). That is the price of `INV-02`, and the plan already writes one
  operand per encoded field for every other instruction.

## Alternatives considered

- **A universal `Memory(base, index, scale, disp)` payload.** Rejected: one
  operand would own several fields with different ranges and different fixup
  eligibility, and §8.1's rule "a `{symbol_id}` payload requires a fixup that
  covers *the slot's* bits" would become ambiguous. It also invites the encoder
  to compose the fields, which is exactly the value-driven choice this ADR
  forbids.
- **A per-ISA compact payload (`riscv.mem.base-offset`).** Rejected for v0: for
  RV64 it saves one operand and buys an operand that cannot say which half a
  fixup covers. The `auipc`+`lo12` pair (`RV-P8`) is the case that needs exactly
  that distinction.
- **One `form_id` per mnemonic, with mod chosen from the displacement.** Rejected
  by the measured `48 8b 41 08` / `48 8b 81 00 10 00 00` pair: the encoding form
  is a function of the operand value, so two plans with the same `form_id` and
  different values would encode through different rules.
- **Admit `ld`/`sd` under the draft `riscv.mem.base-offset` kind and widen
  §8.1.** Rejected as the larger change with no extra guarantee: it changes the
  plan schema, the payload validator, the digest-covered document shape and
  every future memory form, in exchange for one fewer operand per instruction.
- **Read the offset as bytes and scale it in the definition.** Rejected: a
  definition slot has no transform (`§8.3`), and adding one would let a slot
  rescale values silently — the failure mode `A64-P2`'s `-lsl12` half is already
  waiting on.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `ld`/`sd` RV64 field positions and signedness | `inst/I/{ld,sd}.yaml` `encoding` blocks, read; `EXP-0011` §2 | high |
| `ld`/`sd` bytes for the fixture | `llvm-mc 23.1.2`, `EXP-0011` §3 | high |
| x86 memory length depends on the displacement value | `llvm-mc 23.1.2`, `EXP-0011` §4 | high |
| `[rbp]` needs a disp8 because mod=00/rm=101 is RIP-relative | `llvm-mc 23.1.2` bytes plus the ModRM rule; the rule itself is from the ISA manual, not re-read here | medium |
| AArch64 `ldr` imm12 is scaled by the access size | `llvm-mc 23.1.2`: `#16` encodes `imm12 = 2` | high |
| A composite payload is rejected with `E-OPERAND-003` | fixture `rv64/negative/N15-composite-memory-payload` | high |
| Which x86 form variants v0 needs | not enumerated yet; `X86-P4` and `X86-P6` remain planned | **unverified** |

## Review triggers

- `X86-P4`/`P5`/`P6` or `A64-P3` is attempted: the variant list must be
  enumerated and measured before any form lands.
- A plan needs an addressing mode whose fields are not separable (for example a
  base+index that the ISA encodes as one field).
- A future definition format adds slot-level transforms; this ADR's §3 would
  then need re-reading, because `disp` and field content would no longer be the
  same statement.
