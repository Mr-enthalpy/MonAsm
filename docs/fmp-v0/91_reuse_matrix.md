# Reuse Matrix — Phase 1

Status: **complete for Phase 1**. Classifies every XirAsm component we examined,
per the directive's four classes (`00_directive.md` §2.1). Every row cites the
finding in `90_boundary_audit.md` that justifies it.

The question is not "is this code good" — it is good code. The question is
"can the FMP retain the decision authority if we link this".

## Classes

| Class | Meaning |
|---|---|
| **A** | Directly reusable. No implicit decision enters the materializer. |
| **B** | Reusable behind a thin adapter; the adapter supplies every decision. |
| **C** | Needs local modification or splitting to satisfy the determinism contract. |
| **D** | Not reusable. The policy coupling cannot be isolated. |

## Matrix

| Component | Path | Class | Evidence | Reason |
|---|---|---|---|---|
| x86 full encode pipeline | `x86_encoder/api.zig:258-367` (`encodeBuiltinUnitsWithResolver`) | **D** | F-03, F-04, F-05, F-07 | Selects the template, selects the branch form, re-encodes to `.near` on the second pass, and rewrites the fixup from the encoded size. Four independent decisions, none addressable. |
| x86 template matcher | `x86_encoder/match.zig:287-349` | **D** as code, **A** as knowledge | F-03 | `findMatch` resets any caller-supplied choice and applies curated tie-breaks. The generated bucket data is useful for *understanding* which forms exist. |
| x86 size calculator | `x86_encoder/size.zig:129-151` | **D** as code, **C** as knowledge | F-03, F-04 | Requires `ins.itemp`, which only `findMatch` sets; length depends on prefix and relaxation state. The bytecode-length idea is worth keeping, the implementation is not separable. |
| x86 fixup model | `x86_encoder/encode.zig:127-140`, `api.zig:1550-1583` | **D** | F-05, F-06 | `Fixup` is `{kind: absolute\|relative\|segment, size, toffset, relbase}` — contiguous bytes only. No field descriptor, no `pc_reference_rule`, no value transform, no range constraint, no resolution mode, no pair. `materializeFixup` does range-check `relative` (`api.zig:1565-1573`), but F-06 shows numeric branches never reach it. |
| x86 error taxonomy | `x86_encoder/api.zig:178-204` | **A** as reference | F-14 | A good list of distinct failure reasons (`AmbiguousMemorySize`, `CmpR64ImmediateOutOfRange`, `HighRegisterNotAllowed`, `ImpossibleAddressSize`, …). Use it to cross-check our `E-*` registry; never link it. |
| RV64 instruction table | `riscv_encoder/generated_core.zig` (1,700 specs at `:10277`) | **B** | F-08, F-09, F-10 | Plain data: `name`, `match`, `mask`, `format`, `semantic`, `bit_width`, `min_xlen`, `max_xlen`, `fields[{name, lsb, width}]`. Perfectly usable as the *input* to our own generator. Its `semantic` tag and `match/mask` must not become durable ids. |
| RV64 `encodeRaw` | `riscv_encoder/api.zig:28` → `encode.zig:137-144` | **B** | F-08 | Genuinely form-addressable: takes a pinned `*InstructionSpec`, checks operand count, packs fields, and `packField` rejects over-wide values (`encode.zig:1250-1254`). Weakness: the spec identity is an index or `match/mask`, not a versioned id. |
| RV64 `encode` (semantic) | `riscv_encoder/api.zig:24` → `encode.zig:146+` | **D** | F-08 | Resolves operands through a semantic switch (`rd`, `rs1`, `rd_n0`, `c_rs1_p_offset`, …) and field-name aliases (`encode.zig:968`, `1285`). That is instruction-shape knowledge applied at encode time — `INV-01` territory. |
| RV64 text frontend | `riscv_encoder/source.zig`, `src/frontend/backend_adapter.zig:398-440` | **D** | F-08, F-15 | Parses assembly text; our plan has no text. |
| AArch64 include tree | `include/arm/a64/**`, 40.88 MB | **D** as runtime, **A** as knowledge | F-12, F-13 | A Meta-language program with `for`/`while`/string parsing. Executing it violates `INV-06`; depending on it violates `INV-05`. |
| Arm MRS provenance | `include/arm/a64/generated/latest/NOTICE`, `manifest.json` | **A** as knowledge | F-13 | Points at the authoritative source (Arm Architecture MRS, 2026-06) with node counts and upstream hashes. We should generate from the MRS directly. |
| Frontend Meta VM / macros | `src/frontend/meta_*.zig`, `macro.zig` | **D** | F-12, F-15 | An interpreter inside the assembler. Wholesale violation of `INV-06`. |
| ISA test corpus | `tests/isa/**` | **D as fixtures** | F-15 | The `.asm` files are Meta source with `for` loops and macros, produced by the system under audit. Useful as a *list of cases to cover*, useless as an oracle or as fixtures. |
| SPIR-V encoder | `spirv_encoder/` | **not evaluated** | — | Out of scope for FMP v0. |

## What the classes mean for the route decision

- **x86: nothing is A or B.** Every path that produces bytes also selects the
  form. Route A would require a fork, not an adapter. ADR-0001's rejection of
  Route A stands, now with behavioural evidence rather than a file listing.
- **RV64: B is real but narrow.** `encodeRaw` plus the public spec table is the
  only place in the library where a caller can say "this form, these fields".
  It is a viable *oracle cross-check* for our own RV64 tables in Phase 3 — not a
  runtime dependency, because the spec identity is not version-stable.
- **AArch64: knowledge only.** The MRS pointer in F-13 is the useful output of
  this audit; the 40.9 MB Meta tree is not.

## Reuse decision

No component is adopted into the product path. The matrix is used for three
purposes:

1. **Knowledge**: RV64 spec tables and the Arm MRS pointer feed our own
   generator in Phase 3 (`OD-07`).
2. **Oracle**: the built `xirasm.exe` can be run out-of-process on hand-written
   sources to cross-check a byte, always alongside `llvm-mc` and never as the
   only source (rule 5).
3. **Test design**: the error taxonomy and the `tests/isa/**` case list tell us
   which failures to write negative tests for.

This is consistent with ADR-0001: XirAsm stays outside the product boundary, in
`research/external/` and `tools/oracle/`, both deletable.
