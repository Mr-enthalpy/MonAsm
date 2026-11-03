# Open Decisions

Status: **draft**. Each entry states the question, the candidate answers, the
evidence that would settle it, and the acceptance criterion it blocks. Nothing
here is decided until it says `accepted`.

| ID | Question | Options | Evidence needed | Blocks | Status |
|---|---|---|---|---|---|
| OD-01 | Does the plan carry expected bytes? | A: form + operands + choices only; B: plus optional expected bytes/hash; C: full byte template + explicit patch fields | One vertical slice per ISA built under A and B; measure plan size, verifiability, and whether B catches real definition drift | AC-04, AC-07 | open |
| OD-02 | When is a fixup applied vs. recorded? | Resolve in place when the target is local; always emit a record for unresolved; always emit for cross-section | The three AC-05 cases plus one external-symbol case; measure whether "record" loses information | AC-05 | open |
| OD-03 | Which output level does v0 ship? | Level 0 only; Level 0 + Level 1; Level 2 | Whether any AC-05 case is inexpressible without symbol/relocation table structure | AC-03 | open (ADR-0003 provisional: Level 0/1) |
| OD-04 | How is `form_id` made stable? | Namespace + mnemonic + variant + encoding family; definition-assigned opaque id + digest; match/mask pattern from the definition | Two definition revisions with a renamed form; confirm the id survives or fails loudly | AC-08, Q2 | open |
| OD-05 | How are unknown fields and extensions handled? | Reject all; allow `x_*` namespaced fields; version-gated extension objects | A plan written by a newer planner read by an older materializer | AC-10, Q10 | open |
| OD-06 | What does the definition digest cover, and how are upgrades handled? | Hash the generated tables; hash the normalized rule source; hash both; hash plus explicit compatibility classes | A one-byte rule change (immediate range) and a comment-only change; confirm the first breaks and the second does not | N10, EXP-R5 | open |
| OD-07 | Where does AArch64 encoding knowledge come from? | Re-derive from the ISA manual; extract from XirAsm's generated meta-DSL; extract from LLVM TableGen; combination | A slice with `add`/`b.cond`/`adrp` producing oracle-matching bytes from own tables | AC-03, AC-05 | open — Route C assumed |
| OD-08 | What is the canonical wire form? | Canonical JSON; deterministic binary encoding; both (JSON as source, binary as transport) | Plan size and round-trip determinism for the three slices | AC-07 | open |
| OD-09 | What integer/address model does the plan use? | i64 everywhere with explicit width checks; per-field typed integers; arbitrary precision | A negative offset, a `u64` address, and a 33-bit intermediate in `hi20` computation | AC-02 | open |
| OD-10 | What is v0's minimal supported feature surface? | Only the EC entries required by the three slices; all EC entries with a proof; defer x86 VEX/EVEX and RISC-V atomics | Slice construction; each deferred feature needs a rejection test | AC-09, AC-10 | open |

## Decision procedure

1. Build the smallest experiment that distinguishes the options.
2. Record the measurement in `research/evidence/experiments/`.
3. Accept with an ADR if the decision changes an architecture boundary; otherwise
   mark the row `accepted` here with a one-line rationale.
4. Superseding an accepted row requires a new ADR reference in the same row.
