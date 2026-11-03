# ADR-0004: `form_id` carries every encoding decision; no plan-level choice list

- Status: accepted
- Date: 2026-11-04
- Settles: OD-11 (and unblocks OD-04, OD-10)
- Supersedes: none
- Superseded by: none
- Narrows: `00_directive.md` §4.3/§4.5 candidate model (the directive is immutable;
  this ADR records which of its candidate carriers v0 keeps)

## Context

`01_contract.md` §7 makes `encoding_choices` a required field and states that
"empty when a choice exists means the encoder picks silently". `INV-02` is
written as a choice-set exactness check over that field, and three error codes
(`E-CHOICE-001/002/003`), negative test `N01`, and the whole of
`02_encoding_choices.md`'s validation section depend on it.

`02_encoding_choices.md` assigns every `EC-*` row an **Owner**: the mechanism
that makes the decision explicit. Reading the registry as written:

| Owner in the registry | Rows |
|---|---|
| `form_id` variant / encoding family | EC-01, EC-02, EC-03, EC-04, EC-05, EC-07, EC-09, EC-12, EC-13, EC-14, EC-15, EC-16, EC-17, EC-18, EC-19, EC-21, EC-23, EC-25 |
| operand `target_type` / `modifiers` | EC-06, EC-08, EC-10, EC-11, EC-20, EC-24, EC-26 |
| fixup field (`pc_reference_rule`) | EC-22 |

Under that assignment **no `EC-*` selection would ever appear in a v0 plan**.
The field would always be `[]`, the required-choice-set comparison would always
compare two empty sets, and `N01`/`E-CHOICE-001` would be unreachable. A
required field whose only legal value is `[]` is decorative; that is the
over-freezing failure the same document warns about, one level up.

The document's own classification test (step 5: "otherwise it is an explicit
choice and gets an `EC-*` ID") therefore contradicts its own registry: under its
test, the rows above would not receive `EC-*` IDs at all, because their
difference is implied by `form_id` or by a typed operand.

The registry is still valuable. What is wrong is calling the `EC-*` ID a plan
value. It is a handle for a decision *site*, whose carrier is one of the plan's
existing frozen fields.

Measured on the x86 slice (llvm-mc 23.1.2, 2026-11-04; full run and commands in
`research/evidence/experiments/EXP-0003/`, summarised in
`02_encoding_choices.md` under "Evidence"):

- `mov rax, rbx` has two legal 3-byte encodings, `48 89 d8` (`89 /r`) and
  `48 8b c3` (`8B /r`). Both disassemble to `movq %rbx, %rax`. No operand or
  modifier distinguishes them; only the named opcode form does.
- `add rax, 1` is `48 83 c0 01` (4 B) or `48 81 c0 01 00 00 00` (7 B).
- `add rax, 300` is `48 05 2c 01 00 00` (6 B) or `48 81 c0 2c 01 00 00` (7 B).
- `mov eax, ebx` is `89 d8` (2 B) or `40 89 d8` (3 B, redundant `REX` prefix,
  still decodes as `movl %ebx, %eax`).

Each pair is described by **different rows of the ISA opcode table**, or by a
definition rule that forbids the redundant byte. None is a residual choice left
after naming the machine form.

`00_directive.md` §4.3 requires `form_id` to name "a definite machine encoding
form, not merely a vague mnemonic". §4.5 asks, for each byte-affecting decision,
whether it belongs in `form_id`, in an operand type, in an explicit encoding
choice, in layout/fixup, or in the definition's deterministic algorithm — and
that is a question about *where the decision is carried*, not a mandate that all
five carriers exist.

## Decision

1. **`form_id` is the only carrier of encoding-form identity.** It names the
   machine form directly, including the operand signature and the opcode family
   when the mnemonic alone is ambiguous.
2. **`encoding_choices` is removed from the plan and from the schema** in
   `fmp/0.1`. A plan cannot state an encoding decision twice, and cannot state
   one the definition does not name.
3. **An `EC-*` ID is a documentation handle, not a plan value.** Each registry
   row MUST name its carrier, drawn from a closed set: `form variant`, `encoding
   family`, `operand type`, `operand modifier`, `fixup field`, `target identity`,
   or `none` (the variation is unsupported; a plan that implies it is rejected).
4. **Definition forms are total and keyed.** `(form_id, operand signature,
   target_identity)` resolves to exactly one byte template by lookup. No default,
   wildcard, "closest match", or variant inferred from operand values.
5. **`INV-02` is restated** as a property of the definition plus exact plan
   checks: no byte-affecting decision is left to the materializer; every decision
   is carried by an explicit plan field or eliminated by a definition rule; a
   plan naming a form the definition does not contain is `E-FORM-001`, never
   repaired.

Supporting rule for `form_id` shape, so that identity does not depend on how many
alternatives a future definition happens to list:

- For `isa_family: x86` the third component is **required**: `legacy` means the
  one-byte-map family (no VEX/EVEX). A variant that is ambiguous within a family
  gets a distinct `<variant>`, not a fourth component.
- For `isa_family: aarch64` and `riscv` the third component is **absent** in v0;
  their variant names are already exhaustive (a compressed RISC-V instruction is
  a different mnemonic `c.addi`, not a family).

## Consequences

- **The definition table becomes the v0 feature surface** (OD-10). An
  unsupported variant does not exist, so its absence is `E-FORM-001` rather than
  a feature flag or a runtime rejection path. One mechanism, one error.
- **`INV-02`'s test changes shape, and gets stronger.** It is no longer a runtime
  set comparison that a planner can satisfy by writing a list; it is (a) an exact
  lookup test on the plan side, and (b) a structural property of the definition
  (one template per key, enforced by the table's type). No code path can select,
  because there is nothing to select between.
- **`N01` is redefined** from "a required encoding choice is absent" to "a plan
  names a form that leaves a byte-affecting decision open". The directive's N01
  intent is preserved; the carrier moved.
- **`E-CHOICE-001/002/003` are retired, never repurposed.** Their load is carried
  by `E-FORM-001` (missing/under-specified form) and `E-OPERAND-001/002`
  (signature mismatch).
- **OD-04 becomes load-bearing and is narrowed.** `form_id` must survive a
  definition revision unchanged or fail loudly with `E-FORM-001`; it need not
  survive a rename silently. Since plans are always interpreted against the
  pinned definition (version + digest), a rename is a visible break, not a byte
  change.
- **OD-01's variant B gets a second, independent justification.** `mov r64,r64`
  has two legal encodings of identical length and identical semantics
  (`48 89 d8` / `48 8b c3`). `expected_size` cannot tell them apart and neither
  can any operand field; only the per-instruction digest can.
- Plan size drops by the always-empty list (about 22 B per instruction in the
  EXP-0002 canonical-JSON measurement: `"encoding_choices":[]` plus its comma).
  The A-vs-B comparison in `EXP-0002` is unaffected in direction, since both
  variants lose the same field.

## Alternatives considered

- **B: coarse `form_id` + explicit `encoding_choices` enums.** Rejected. It
  duplicates the form table as an allowed-value set, creates two selectors that
  must agree for every instruction, and contradicts directive §4.3's "definite
  machine form, not a vague mnemonic". Its only claimed benefit — stability when
  a variant is added — is already provided by pinning
  `definition_identity.version + digest`: a plan is never reinterpreted across
  definitions.
- **Keep the field required but always empty.** Rejected as decorative: it
  restates "the definition has no defaults" without testing anything, and it
  invites a later implementer to populate it, reintroducing a second selector.
- **C: byte template + patch fields.** Rejected earlier in OD-01/`EXP-0002`.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `89 /r` and `8B /r` are both legal, same length, same semantics | `llvm-mc -disassemble` round trip, 2026-11-04 | high |
| `83` (imm8) vs `81` (imm32) differ in size | `llvm-mc -show-encoding`, F-07 | high |
| `05 id` (accumulator) is one byte shorter than `81 /0 id` | `llvm-mc` bytes; 6 vs 7 with `REX.W` | high |
| `40 89 d8` decodes as `movl %ebx, %eax` | `llvm-mc -disassemble` | high |
| No `EC-*` row leaves a residual plan-level choice once a carrier is named | classification of the registry by the document's own test | high |
| `encoding_choices` would always be empty in v0 | derived from the Owner column | high |
| Removing the field does not weaken `INV-02` | argument above; to be tested in Phase 3/4 | medium until `N01` and the per-EC negatives exist |

## Review triggers

Revisit if a slice produces a byte-affecting decision that is genuinely not
expressible as `form_id` + typed operand + fixup field + target identity — that
is, a case where two honest implementers of the *same* `form_id` and the same
operands must disagree. If such a case appears, it is evidence for reinstating a
plan-level choice object, and it needs a new ADR that marks this one
`superseded`.
