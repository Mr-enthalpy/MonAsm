# ADR-0010: A PC-relative RV64 pair carries its own reference point

- Status: accepted
- Date: 2026-11-04
- Settles: `OD-15` (how a `hi`/`lo` pair expresses RISC-V's "the low half names the high half")
- Supersedes: none
- Superseded by: none

## Context

`03_fixup_model.md` has carried a `pair_group`/`pair_role` relation since OD-02,
and N12 pins the rejection of a broken group. AArch64's `adrp` + `add :lo12:`
fits it, because its low half is an *absolute* low 12 bits: `P` plays no part, so
`lo12_i` reads `S + A` and the rule is `none` (`A64-P6`).

RISC-V is not that shape. The psABI (pinned at tag `v2.0-rc0`, `EV-22`;
`riscv-elf.adoc:1578-1605`, `:1184`, `:1186`) states four things `fmp/0.1` cannot
express:

1. `R_RISCV_PCREL_LO12_I`/`_S` are resolved against the **`hi` field's address**,
   not against their own. The relocation's symbol is "a label pointing to an
   instruction in the same section with a high-part relocation entry that points
   to the target symbol", and the value is `symbol_address - hi20_reloc_offset`.
2. Their value is "the same as the paired high-part relocation", i.e. the low 12
   bits of `S + A - P_hi`.
3. "The addend must be 0" on both low-part relocations.
4. The pair is 1:N — one `hi` serves "one or more I-Type instructions … or S-Type
   instructions" — and the members are "not necessarily sequential or in pairs".

Rule 1 is the load-bearing one. `pcrel_begin` computes `P` as *the fixup's own
site*, so a `lo` member that names it measures from the `addi` instead of the
`auipc`. With `auipc` at 0 and `addi` at 4 referencing a symbol at 0, the `hi`
computes `0 - 0` and the `lo` computes `0 - 4`: the two halves disagree by the
distance between them, and the materialized address is off by exactly that.

The same argument rules out reusing `lo12_i`. It computes `(S + A) & 0xFFF`,
which equals the correct value only when `P_hi` happens to be page-aligned. With
`auipc` at `0x1004` and a symbol at `0x2000`, the pair needs `0x2000 - 0x1004`
`= 0xFFC` low bits while `lo12_i` yields `0x000` — a silent page-off error
whenever the `auipc` is not the first instruction in its page.

## Decision

1. **A new `pc_reference_rule`, `pcrel_hi`.** `P` is the address of the paired
   `hi` member's site. It is only legal on a fixup with `pair_role: lo`, and the
   `hi` member MUST be in the same section, because the source says the label
   points at an instruction in the same section. A `lo` without a resolvable `hi`
   is `E-FIXUP-007`.
2. **A new `value_transform`, `pcrel_lo12`.** `v = (S + A - P_hi) & 0xFFF`, a
   mask, never range-checked — the same class as `lo12_i`, applied to the
   displaced value instead of the absolute one.
3. **`lo12_s` stays undefined and stays `E-VERSION-001`.** The `_i`/`_s` suffix
   names the *instruction form*, which `form_id` already carries, so a second
   transform would be a second carrier for one fact (`OD-11`, ADR-0004). An S-type
   low half is `pcrel_lo12` with an S-type `field_descriptor`; the scatter is the
   descriptor's job, exactly as it is for `sd` without a pair (`RV-P3`).
4. **A `pcrel_lo12` fixup MUST carry `addend: 0`.** The `hi` already carried the
   addend into the shared displacement, and the `lo` value is derived from it, so
   a `lo` addend would be added twice. A non-zero one is `E-FIXUP-009`, never
   folded in silently.
5. **A group is exactly one `hi` and at least one `lo`**, all naming the same
   logical target, and a `pcrel_hi` member must sit in its `hi`'s section.
   `E-FIXUP-007` keeps the code; the cardinality it enforces changes from 1:1 to
   1:N, which is what the source states. Keeping 1:1 would force a plan with one
   `auipc` feeding a load and a store to re-emit the `auipc`, which changes the
   bytes to satisfy a check.
6. **The rounding belongs to `pcrel_hi20` and is applied once.** The psABI
   computes `HI20 = (symbol_address - hi20_reloc_offset + 0x800) >> 12`, so the
   `+0x800` is part of the transform. `addend` is therefore the unrounded addend;
   a plan that pre-rounds would have `0x800` added twice, which is why the
   transform, not the plan, owns it. `01_contract.md` §3.2's 33-bit
   counterexample assumes exactly this split and stands unchanged.
7. **`target` stays the logical symbol on both members.** The ELF spelling — the
   low record's symbol field naming the `hi` site — is a serialization detail that
   §6.1 and `01_contract.md` §11 already assign to Level 1. The group is coherent
   through `pair_group`, and every member's `target` names the same symbol, so
   §7's "same logical target" rule and §6.1's "names the `auipc`, not the target"
   describe two levels rather than contradicting each other; §7 gains one sentence
   saying so.

## Consequences

- `RV-P8`'s pair half unblocks with two positive fixtures and two negatives:
  `RV-P8-pcrel-pair` (one `auipc`, one `addi` and one `sd`, all
  `emit_relocation`: one `hi` and two `lo` members, three records) and
  `RV-P8-pcrel-pair-resolved` (one `auipc` at 4, one `addi` at 8, a symbol at
  0x1000, both `resolve_in_place`), then `N17a` (a `lo` with `addend: 4` →
  `E-FIXUP-009`), `N17b` (`pcrel_hi` on a fixup with no `pair_role` →
  `E-FIXUP-007`) and `N17c` (a `lo` in a different section from its `hi` →
  `E-FIXUP-007`). The `sd` member is also the measurement for Decision 3:
  `llvm-mc` emits `R_RISCV_PCREL_LO12_S` for the same `pcrel_lo12` value with an
  S-type descriptor, so no second transform is needed.
- `E-FIXUP-007` changes meaning for every ISA: the "exactly two members" check
  becomes "one `hi`, at least one `lo`". `N12a` still passes — it rejects a group
  with two `hi` members — because that failure is independent of the count.
- AArch64 is unaffected: `adrp`+`:lo12:` keeps `none` + `lo12_i`, and its `lo`
  may now legally be joined by a second `lo` without a format change.
- `fmp/0.1` gains two enum values and one error code, and keeps one record shape.
  Nothing changes for a plan that names neither.
- The resolved half is now measured, not assumed:
  `RV-P8-pcrel-pair-resolved` links to `0x00001517` / `0xFFC50513`, which equals
  `(0x1000 - 4 + 0x800) >> 12 = 1` and `(0x1000 - 4) & 0xFFF = 0xFFC`. The three
  near-miss rules each produce a different word (`lo12_i` → 0x000,
  `pcrel_begin` on the `lo` → 0xFF8, dropping `+0x800` → 0), so the fixture
  distinguishes the decision instead of merely agreeing with it. The 1:N half is
  still only proven at the record level (`llvm-readobj -r`), because
  `emit_relocation` zeroes the fields by contract.

## Alternatives considered

- **Reuse `pcrel_begin` and store the `hi` offset in the `lo`'s target.** Rejected:
  it makes `target` mean two different things, and §7's "same logical target"
  would have to be dropped, which is the property that keeps a group coherent.
- **Add a `lo12_s` transform.** Rejected in Decision 3.
- **Carry the addend on the `hi` only, and let the `lo` inherit it.** Rejected: the
  pair already shares `S + A`; a second place to put an addend is a second writer
  for the same value (`OD-02`), and the source forbids a non-zero `lo` addend
  outright.
- **Keep 1:1 and require one `auipc` per reference.** Rejected: it makes the plan
  express the linker's job (deduplicating `auipc`) instead of the machine facts,
  and it changes bytes to satisfy a validator.
- **Model the pair as one fixup covering both instructions.** Rejected: the two
  sites are not contiguous in general (the psABI explicitly allows other
  instructions between them), and `field_descriptor` is relative to one site.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The low half's reference point is the `hi` field's address | `riscv-elf.adoc:1578-1605`, read at `v2.0-rc0`; `EXP-0002` §6.2 observed the same shape in an object file | high |
| Low-part addend must be 0 | `riscv-elf.adoc:1184`/`:1186`, read | high |
| One `hi` may serve several `lo`s, non-adjacent | `riscv-elf.adoc:1580-1605`, read | high |
| The pair is in one section | `riscv-elf.adoc:1584-1590`, read; `N17c` rejects a cross-section `lo` | high |
| `lo12_i` differs from `pcrel_lo12` unless `P_hi` is page-aligned | arithmetic on the two definitions, and `RV-P8-pcrel-pair-resolved` measures it: `lo12_i` would write 0x000 where the linked word holds 0xFFC | high |
| `+0x800` belongs to the `hi` computation | `riscv-elf.adoc:1600`, read; `RV-P8-pcrel-pair-resolved` drops it to 0 and the linked word is 1 | high |

## Review triggers

- A `lo` member ever needs its own addend. That contradicts the source and would be
  a new decision, not a wider field.
- A pair whose `hi` is in a different section from its `lo`. The source excludes it;
  admitting it needs a section-relative address model that v0 does not have.
- A target whose `hi` and `lo` must round independently (a non-frozen rounding
  rule). `pcrel_hi20` owns rounding today; a second owner would need this ADR
  superseded.
- Level 1 landing. It must synthesize the local label for the `lo` record, and this
  ADR says the record itself does not store it.
