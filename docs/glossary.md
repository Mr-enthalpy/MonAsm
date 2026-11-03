# Glossary

Terms used across the contract set. Keep definitions here once; other documents
link to them instead of redefining.

| Term | Definition |
|---|---|
| **Machine fact** | A property of the output that is decided, not derived: which instruction form, which encoding family, which byte count, which fixup kind. |
| **Policy** | Any rule that picks among several legal outputs. Policy belongs upstream, never in the materializer. |
| **Frozen Machine Plan (FMP)** | A serialized set of machine facts, bound to a target identity and a definition identity, sufficient to emit bytes without further choice. |
| **Planner** | The upstream component that selects instructions, legalizes operands, chooses encoding forms, lays out sections, and plans fixups. Out of scope for this repository. |
| **Materializer** | The component that validates an FMP and executes it deterministically. In scope. |
| **Definition (target definition)** | A versioned, digestible rule set describing legal forms, operand constraints, field placement, and fixup semantics for one ISA variant. |
| **Definition identity** | Namespace + version + digest that pins exactly one definition instance. |
| **`form_id`** | A stable, definition-bound identifier of one machine encoding form, not a mnemonic and not a library-internal opcode number. |
| **Encoding choice** | A decision that changes emitted bytes but is not derivable from `form_id + operands + target`; catalogued as `EC-*`. |
| **Fragment** | A contiguous byte range within a section with a declared kind and size. |
| **Fixup** | A planned patch at a known site with a declared kind, target reference, addend, and range constraint. |
| **Relaxation** | Replacing an encoding with a different-size encoding (e.g. `jmp rel8` → `rel32`). Forbidden in the materializer (INV-04). |
| **Resolution mode** | What the plan requires at fixup time: resolve in place, emit a relocation record, or reject. |
| **Canonical form** | The unique serialization of an FMP: sorted keys, no insignificant whitespace, integers only, LF, UTF-8. |
| **Fingerprint** | SHA-256 over the canonical plan plus domain separation plus definition digest. |
| **Oracle** | An independent authority used to check our bytes (llvm-mc, binutils, manual derivation). Never the same code path as the thing under test. |
| **Level 0 / 1 / 2** | Bytes + fixup records / laid-out sections + symbols + relocations / complete object files. |
| **Route A / B / C** | XirAsm-lib-centered / LLVM MC-centered / self-owned kernel (see ADR-0001 and directive §13). |
| **Disposable zone** | `tools/oracle/`, `research/external/`: deletable without breaking the product build. |
| **`TBD`** | Not yet supported by evidence. Never treat as frozen. |
| **`inference`** | A conclusion from reading code, not yet confirmed by execution. |
| **`unverified`** | A claim we cannot support yet in this environment. |
