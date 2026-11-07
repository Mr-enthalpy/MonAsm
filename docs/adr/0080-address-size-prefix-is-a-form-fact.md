# ADR-0080: the address-size prefix `0x67` is a form fact

- Status: accepted
- Date: 2026-11-07
- Settles: `X86-P57` (the `0x67` prefix on the `REX`-less 32-bit indexed `mov`
  rows, both directions at both displacement widths)
- Supersedes: none
- Superseded by: none
- Revises: `EC-08` (draft → frozen; the carrier is `form variant`, not an
  operand modifier), `EC-02` (the displacement axis gains the `0x67` rows at
  `[32,8]`/`[32,32]`), `EC-37` (the `SIB` slot is a 32-bit address register on
  these rows) and `EC-38` (the `0x67` row is a no-`REX` window whose base reach
  stays `0`–`7`)

## Context

`ADR-0029` settled that the operand-size prefix `0x66` is a form fact: the prefix
changes the meaning of the same `ModRM` field, so the row and the template carry
it, not an operand modifier. `EC-08` has been `draft` since the contract was
written, and it tentatively proposed `operand modifier` (`addr_size`) as the
carrier. `X86-P57` is the first measured slice that needs the answer.

`EXP-0082` measures the `0x67` prefix on the four `REX`-less 32-bit indexed
`mov` rows and four facts come out:

1. **`0x67` is one byte in front of the opcode.** `movl 8(%eax,%ecx,1), %eax`
   is `67 8b 44 08 08`: byte 0 is `67`, byte 1 is the opcode, byte 2 is
   `ModRM`, byte 3 is `SIB` and byte 4 is `disp8`. The four rows are five bytes
   at `disp8` and eight at `disp32`.
2. **The base and index name 32-bit registers.** `movl 8(%eax,%ecx,1), %eax` is
   the same `SIB = 08` as the 64-bit row `8b 44 08 08` (`EC-37`), but the
   operand names are `%eax`/`%ecx`, not `%rax`/`%rcx`. The register in
   `ModRM.reg` stays a 32-bit value operand (`%eax`), so only the address
   registers shrink.
3. **`%esp` is still not an index, and `%ebp` still is.** `llvm-mc` rejects
   `8(%eax,%esp,1)` (`invalid base+index expression`); `8(%eax,%ebp,1)` is
   `67 8b 44 28 08` (`SIB.index = 101`). `%esp` is a legal base
   (`67 8b 44 0c 08`, `SIB.base = 100`).
4. **`0x67` precedes `REX`.** `movl 8(%r8d,%r9d,1), %r8d` is
   `67 47 8b 44 08 08`, so a future `REX` window on an `addr32` row puts the
   address-size byte first and the `REX` byte second. Those rows are deferred.

## Decision

1. **`EC-08` is frozen with `form variant` as the carrier.** `0x67` is template
   byte 0 of the row, exactly as `0x66` is in `ADR-0029`. No plan operand or
   modifier requests it, and no code path picks it from an operand kind.
2. **`0.53.0` appends four rows: two directions × two displacement widths.**
   Each row is the `REX`-less 32-bit indexed shape with `0x67` in front.

   | Direction | Displacement | `form_id` | Template | Length |
   |---|---|---|---|---|
   | load | `disp8` | `x86:mov/r32-addr32-base-index-disp8/legacy` | `67 8b 44 00 00` | 5 |
   | store | `disp8` | `x86:mov/addr32-base-index-disp8-r32/legacy` | `67 89 44 00 00` | 5 |
   | load | `disp32` | `x86:mov/r32-addr32-base-index-disp32/legacy` | `67 8b 84 00 00 00 00 00` | 8 |
   | store | `disp32` | `x86:mov/addr32-base-index-disp32-r32/legacy` | `67 89 84 00 00 00 00 00` | 8 |

3. **The address registers are `x86.gpr32` slots.** The base is
   `x86.gpr32`/`rm32` at `[24,3]` and the index is
   `x86.gpr32`/`sib_index32` at `[27,3]`, with the index excluding `4` (the
   "no index" encoding, `EC-37`). The `rm32` and `sib_index32` target types are
   new; each target type keeps its one-kind invariant (`rm64`/`sib_index` stay
   `x86.gpr64`). The value operand is unchanged: `x86.gpr32`/`r32` at
   `[19,3]`.
4. **The geometry is the `0.51.0` geometry.** `ModRM` is byte 2 (the `0x67`
   byte replaces the `REX` byte), so the register is `[19,3]`, `SIB` is byte 3
   (base `[24,3]`, index `[27,3]`, scale `[30,2]`) and the displacement is
   `[32,8]` or `[32,32]`. Only the slot kinds change.
5. **A value past the 3-bit field is rejected.** Register, base and index are
   three-bit slots, so `8`–`15` is `E-OPERAND-004`; the extended `addr32` rows
   are a future form, not an operand value. Nothing truncates.
6. **No schema, loader or materializer change.** `target_type` is a free string
   matched between plan and definition, and the existing `E-OPERAND-004`
   field-width check already covers the 3-bit slots.

## Consequences

- `0.53.0` is a 417-form document that byte-reproduces every `0.52.0` row. Its
  digest is recorded in `07_definition_format.md` §8 and in the fixture oracle.
- The positive fixture `X86-P57-gpr32-mov-index-addr32-window` has ten
  instructions and 56 bytes: the four rows plus six corners (`%esp` as a base,
  `%ebp` as a base, `%edi`/`%esi` at x4, the x8 scale, a negative displacement
  and `%edx`/`%ebx` at x2). Its `expected.bin` comes from `llvm-mc` +
  `llvm-objcopy`, never from the materializer.
- Negatives pin the version boundary in both directions, a missing index, the
  scale field's end, the index's `4` exclusion and the 3-bit field end on the
  base and index.
- `EC-08` becomes a frozen row and counts toward `G2`; no `EC` row is added or
  renumbered.

## Alternatives rejected

- **Carry `addr_size` as an operand modifier.** Rejected for the reason
  `ADR-0029` rejected `0x66` as a modifier: the prefix changes the meaning of
  the base/index fields, so two plans with the same register names would encode
  different instructions. `04_errors.md` also rejects an unused modifier with
  `E-OPERAND-003`, and no operand owns the byte.
- **One row that accepts both `%eax` and `%rax` bases and inserts `0x67` when
  it sees a 32-bit kind.** Rejected: the length and the row would be chosen from
  an operand value (`INV-02`, `INV-04`), and `movl 8(%rax,%rcx,1), %eax` is a
  different instruction (`8b 44 08 08`, four bytes).
- **Keep the register as `x86.gpr64` and let the prefix truncate it.**
  Rejected: the operand is a 32-bit address register; naming `%rax` and
  truncating to `%eax` is a silent repair (`INV-07`).
- **Add the `0x67`+`REX` windows now.** `67 47 8b 44 08 08` and
  `67 44 8b 44 08 08` are different forms with a second prefix byte; each needs
  its own row, and mixing them into this slice would double the table.
- **Add `%r8d`–`%r15d` address registers now.** The 3-bit base/index fields
  would need a `REX.B`/`REX.X` placement and an `0x67` byte before the `REX`
  byte; that is the deferred `addr32` `REX` split.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `67 8b 44 08 08` is the `addr32` load at five bytes | `llvm-mc -show-encoding`, `EXP-0082` §1 | high |
| `0x67` is byte 0, opcode byte 1, `ModRM` byte 2, `SIB` byte 3, `disp8` byte 4 | `llvm-mc -show-encoding`, `EXP-0082` §2 | high |
| `%esp` is rejected as an index; `%ebp` is legal | `llvm-mc`, `EXP-0082` §3 | high |
| `0x67` precedes `REX` (`67 47 8b 44 08 08`) | `llvm-mc -show-encoding`, `EXP-0082` §3 | high |
| the `disp32` rows are eight bytes with `disp32` at `[32,32]` | `llvm-mc -show-encoding`, `EXP-0082` §1 | high |
| the ten byte strings decode back to the same registers | `llvm-mc -disassemble`, `EXP-0082` §1 | high |

## Review triggers

- An `addr32` row with a `REX` byte is attempted (`67` then `REX`).
- A `%r8d`–`%r15d` base or index is requested.
- A symbol or relocation in an `addr32` displacement is requested.
- The no-base indexed shape or the `moffs` form is attempted with `0x67`.
- An EVEX or VEX row is proposed with an address-size prefix.
