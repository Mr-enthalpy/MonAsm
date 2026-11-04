# ADR-0028: Base+displacement is four form shapes, and `%rsp` is one of them

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P4` (displacement width) and the SIB-byte question it carries
- Supersedes: none
- Superseded by: none

## Context

`X86-P4` asks for one displacement-width pair: `mov rax, [rbp-8]` (disp8) versus
the same reference with a disp32. `ADR-0008` settled that the addressing shape
is a `form_id` variant and that the displacement is field content, and
`ADR-0027` took the one shape that has no base register. This ADR enumerates the
base+displacement shapes that remain, and the `%rsp` case they expose.

`llvm-mc 23.1.2` measures the following on 2026-11-05 (`-show-encoding`):

| Source | Bytes | Reading |
|---|---|---|
| `movq 0(%rbp), %rax` | `48 8b 45 00` | `mod = 01`, `r/m = 101`, `disp8 = 0` — **not** RIP |
| `movq 8(%rbp), %rcx` | `48 8b 4d 08` | `reg = 001`, `r/m = 101`, `disp8 = 8` |
| `movq -1(%rax), %rdx` | `48 8b 50 ff` | `r/m = 000`, `disp8 = -1` |
| `movq -128(%rbp), %rax` | `48 8b 45 80` | bottom of `disp8` |
| `movq 127(%rbp), %rax` | `48 8b 45 7f` | top of `disp8` |
| `movq 128(%rbp), %rax` | `48 8b 85 80 00 00 00` | `mod = 10`, `disp32 = 128` |
| `movq -129(%rbp), %rax` | `48 8b 85 7f ff ff ff` | `mod = 10`, `disp32 = -129` |
| `movq 4096(%rbp), %rbx` | `48 8b 9d 00 10 00 00` | `mod = 10`, `reg = 011` |
| `movq 8(%rsp), %rsi` | `48 8b 74 24 08` | `r/m = 100` plus a SIB byte `24` |
| `movq 128(%rsp), %rdi` | `48 8b bc 24 80 00 00 00` | SIB plus `disp32` |
| `movq 4096(%rsp), %rdi` | `48 8b bc 24 00 10 00 00` | SIB plus `disp32` |
| `movq 8(%rax), %rax` | `48 8b 40 08` | `mod = 01`, no SIB |
| `movq (%rax), %rax` | `48 8b 00` | `mod = 00`, no displacement — a different shape |
| `movq %rax, 16(%rbp)` | `48 89 45 10` | store direction, opcode `89` |
| `movq %rdx, 4096(%rsp)` | `48 89 94 24 00 10 00 00` | store, SIB, `disp32` |
| `movq %rax, 128(%rsp)` | `48 89 84 24 80 00 00 00` | store, SIB, `disp32` |

Two facts decide the shape list:

1. **`mod` is a width selector, not a function of the base.** `%rbp` at
   displacement zero takes `mod = 01` and a zero `disp8`; `mod = 00` with
   `r/m = 101` would be RIP (`ADR-0027`). `%rax` at zero takes `mod = 00` and no
   displacement at all. A single base+displacement row would have to choose
   `mod` from the displacement value — the value-driven form selection `INV-02`
   forbids — and could not express `[rbp]` at all without falling into RIP.
2. **`%rsp` adds a byte that no operand names.** With `r/m = 100`, `mod = 00`
   and `mod = 01`/`10` are followed by a SIB byte; the measured `24` is
   `scale = 00`, `index = 100` (none) and `base = 100` (`%rsp`). If the same row
   accepted `%rsp` and inserted the SIB byte when it saw register 4, the
   instruction length would depend on an operand value, and a fixup or a later
   fragment offset would move with it (`INV-04`). That is the slice's second
   decision, and it is a form decision, not an encoder convenience.

`%r12` would also need a SIB byte, but it needs `REX.B` as well and is outside
the three-bit register field the table declares, so it stays out with `r8`–`r15`.

## Decision

1. **`X86-P4` ships as eight rows in `definitions/x86_64/0.3.0.json`:** load and
   store × `disp8`/`disp32` × base-in-`r/m`/`%rsp`-fixed.
   - `x86:mov/r64-base-disp8/legacy`, `x86:mov/r64-base-disp32/legacy`
   - `x86:mov/base-disp8-r64/legacy`, `x86:mov/base-disp32-r64/legacy`
   - `x86:mov/r64-rsp-disp8/legacy`, `x86:mov/r64-rsp-disp32/legacy`
   - `x86:mov/rsp-disp8-r64/legacy`, `x86:mov/rsp-disp32-r64/legacy`

   The store names put the memory side first, like `x86:mov/riprel32-r64`
   (`ADR-0027`); the operand list still starts with `src`, as `aarch64:str/…`
   does. The opcode direction remains the form (`EC-27`).
2. **`mod` and the SIB byte are template.** The base rows fix `mod = 01` or
   `mod = 10`; the `%rsp` rows fix `r/m = 100`, `SIB = 24` and the base `100` in
   both places. The plan cannot request a different ModRM or SIB shape through
   any row.
3. **The base is an operand in the general rows and the form in the `%rsp`
   rows.** The general rows carry `base` at `[16,3]` with `target_type: rm64`.
   The `%rsp` rows have no `base` operand: the form name states the base, the
   same way `x86:add/rax-imm32/legacy` states `%rax` (`EC-04`).
4. **`%rsp` is excluded from the general rows.** The base slot's `excluded` list
   is `[4]`, and a plan that names `%rsp` there is `E-RANGE-004`, not a SIB byte
   inserted at emission time. The value fits the three-bit field; it is rejected
   because the shape is wrong, which is exactly the `E-RANGE-004` case
   (`ADR-0009`, `OD-14`).
5. **The displacement is a `disp` operand and the form owns its width.** The
   slot is `kind: x86.imm`, `target_type: disp8` or `disp32`, signed, and field
   content. `disp8 = 128` is `E-RANGE-001` on the `disp8` row; it is never
   re-formed as `disp32`. `disp32 = 8` is legal on the `disp32` row and keeps
   `mod = 10`, even though `disp8` would be shorter — the plan names the
   encoding, and the fixture pins that (`X86-P4-base-disp`, last instruction,
   derived from the ModRM rule and decode-verified).
6. **Only the 64-bit `REX.W` moves, only `mov`, only a base with a
   displacement.** The `mod = 00` no-displacement shape (`48 8b 00`), index and
   scale, `r8`–`r15`, the address-size prefix `0x67`, `0x66` and the 8-bit high
   registers remain absent. Each is a different form family (`EC-05`, `EC-06`,
   `EC-07`, `EC-08`) and needs its own slice.
7. **No fixup is added to these rows.** The displacement is a literal in this
   slice; a symbolic displacement would need its own decision about the
   reference base and the addend, and `pcrel_end` does not describe `[rbp+8]`.

## Consequences

- `X86-P4` moves from deferred to passing with a 51-byte fixture covering:
  `%rbp` at displacement 0, a positive and a negative `disp8`, a `disp32`
  beyond the `disp8` range, a `disp8` and a `disp32` through the `%rsp` SIB
  shape, both store directions, and a small value held in `disp32`.
- `EC-02`'s carrier is now exercised in both halves; `EC-35` records the SIB
  decision.
- The definition table grows from 9 to 17 rows, so `07_definition_format.md`
  §8.1 and the digest move with it.
- `N01y` is the `0.2.0` version boundary, `N03-disp8-out-of-range` pins the
  field end, and `N16f` pins the `%rsp` exclusion.
- Cost: four shapes times two directions, all mechanically derivable from the
  two ModRM measurements above. Index/scale, `mod = 00` and the extension
  registers still need their own ADRs.

## Alternatives considered

- **One row per displacement width with a free base.** Rejected: `%rsp` would
  then change the instruction length from an operand value, and `INV-04` says
  layout is not chosen at emission time.
- **Model the SIB byte as an operand or a modifier (`sib: true`).** Rejected: the
  plan would restate a computed encoding fact (`02_encoding_choices.md`, "Not
  choices"), and a plan could ask for a SIB byte on `%rax` or omit it on `%rsp`,
  producing a wrong instruction with no error.
- **Keep `%rsp` out of the slice entirely.** Rejected: the directive's `X86-P4`
  is about displacement width, and `%rsp` is the one base where the measured
  bytes show that the width decision is not the only byte decision. Leaving it
  out would make the table look complete while a legal `[rsp+8]` had no form.
- **Let `%rsp` reuse the general row with `excluded` reversed.** Rejected: there
  would then be two rows for the same base, and the plan's choice between them
  would be a second selector for one encoding.
- **Use `mod = 00` for `[rbp]`.** Rejected: that is the RIP shape (`ADR-0027`),
  and `llvm-mc` itself emits `45 00`, not `05`.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The sixteen byte strings in Context | `llvm-mc 23.1.2`, `EXP-0030` §2 | high |
| `disp8` is signed 8-bit and `disp32` signed 32-bit | the two endpoint pairs `80`/`7f` and `80 00 00 00`/`7f ff ff ff`; the assembler switches at 128/−129 (`EXP-0030` §2) | high |
| `%rsp` forces a SIB byte whose base is also `100` | `48 8b 74 24 08` and `48 8b bc 24 …` (`EXP-0030` §2) | high |
| `mod = 00` with `r/m = 101` is RIP, not `%rbp` | `ADR-0027`; `0(%rbp)` measures `45 00` | high |
| `disp32` with a small value keeps `mod = 10` | manual ModRM derivation plus `llvm-mc -disassemble` on `48 8b 85 08 00 00 00`, recorded in `EXP-0005` | high |
| The general rows' base field is three bits | the `ModRM` layout already used by `0.1.0`; `N14` pins the failure above 7 | high (consequence of the field width) |

## Review triggers

- Index/scale or `mod = 00` is attempted: the SIB matrix must be enumerated for
  every base and index combination, and this ADR's `%rsp` row must not be
  widened to carry an index.
- A symbolic displacement on a base row is requested: first decide its
  reference base and addend, because `pcrel_end` describes RIP-relative and
  branch sites only.
- The table gains `REX.B`/`REX.X` slots for `r8`–`r15`: `%r12` then joins the
  SIB family, and `%r13` joins the `disp8 = 0` case.
