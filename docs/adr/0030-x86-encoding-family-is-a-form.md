# ADR-0030: The x86 encoding family is a form fact

- Status: accepted
- Date: 2026-11-05
- Settles: `X86-P9` (SSE vs VEX vs EVEX for one operation)
- Supersedes: none
- Superseded by: none

## Context

`X86-P9` asks which of the three x86 encoding families a plan selects. `EC-09`
was `draft` and carried the choice as an "encoding family" field, which `OD-11`
had already removed: a byte-affecting choice is a `form_id`, never a second
selector. The question left is whether one operation really has three encodings
at the same operand shape.

`llvm-mc` 23.1.2 measures the following on 2026-11-05. The first, second and
fourth rows come from `-show-encoding`; the EVEX.128 row (third) from
`-disassemble`:

| Source | Bytes | Family |
|---|---|---|
| `movaps %xmm1, %xmm0` | `0f 28 c1` | legacy SSE, no prefix |
| `vmovaps %xmm3, %xmm2` | `c5 f8 28 d3` | two-byte VEX |
| `vmovaps %xmm5, %xmm4` (bytes `62 f1 7c 08 28 e5`) | `62 f1 7c 08 28 e5` | EVEX.128 |
| `vmovaps %zmm1, %zmm0` | `62 f1 7c 48 28 c1` | EVEX.512 |

Four facts decide the shape list:

1. **The operation and the operands are the same; the bytes are not.** All
   three `xmm` rows name `movaps`/`vmovaps` with one destination and one source
   in `xmm0`–`xmm7`. Only the prefix family and, because the prefix length
   changes, the position of `ModRM` differ. A mnemonic plus operands therefore
   does not determine the bytes.
2. **VEX and EVEX are both legal at the same width.** `llvm-mc -disassemble`
   prints `vmovaps %xmm1, %xmm0` for both `c5 f8 28 c1` and
   `62 f1 7c 08 28 c1`. `llvm-mc` always emits the VEX form from the mnemonic,
   but the EVEX form exists (`EVEX.128` is enabled by AVX-512VL and needs no
   mask). A single `vmovaps/xmm-xmm` row would leave the family to the
   implementer, which is exactly the value-driven choice `INV-02` forbids.
3. **The prefix length moves every field.** `ModRM` is byte 2 in the legacy
   row, byte 3 in the VEX row and byte 5 in the EVEX row, so the same
   destination register lands at bit 19, 27 or 43. The family cannot be a byte
   appended at the end; it is the front of the template.
4. **The family fixes bits that are not operands.** Two-byte VEX `C5 F8` is
   `R̄ = 1`, `vvvv = 1111`, `L = 0`, `pp = 00`. EVEX `62 F1 7C 08` is
   `R̄ = X̄ = B̄ = R̄' = 1`, `W = 0`, `vvvv = 1111`, `V' = 1`, `L'L = 00`,
   `aaa = 000`. All of these are reserved or extension bits for a register-only
   form with no mask; they are template, not operands. The same bits are why
   these rows stop at `xmm0`–`xmm7`: `xmm8`–`xmm15` need `R`/`B` set, which
   would make the prefix different per operand.

`llvm-mc` confirms the width split: `62 f1 7c 28 28 c1` (where `L'L = 01`)
decodes as `vmovaps %ymm1, %ymm0`, and `62 f1 7c 48 28 c1` as
`vmovaps %zmm1, %zmm0`. Only `L'L = 00` is the 128-bit row this slice ships.

## Decision

1. **`X86-P9` ships as three rows in `definitions/x86_64/0.5.0.json`:**
   - `x86:movaps/xmm-xmm/legacy` (`0F 28 /r`, 3 bytes)
   - `x86:vmovaps/xmm-xmm/vex` (`C5 F8 28 /r`, 4 bytes)
   - `x86:vmovaps/xmm-xmm/evex` (`62 F1 7C 08 28 /r`, 6 bytes)
2. **The family is the `form_id` component.** `01_contract.md` §7 already
   requires `<encoding_family>` for x86 and allows `legacy`/`vex`/`evex`; this
   ADR is the first slice to use the last two. No operand, modifier or extra
   field states the family.
3. **The prefix is template, and the `ModRM` placement follows it.** The
   destination is `ModRM.reg` at `[19,3]`, `[27,3]` or `[43,3]`; the source is
   `ModRM.rm` at `[16,3]`, `[24,3]` or `[40,3]`. The bits the family fixes are
   template constants, so no slot writes them.
4. **`x86.xmm` is one kind for all three rows.** The register set does not
   change with the family, so the kind cannot be used to infer it. Likewise the
   rows cannot be reached through each other's signatures: all three have the
   same operand types and differ only in `form_id`.
5. **Extension registers stay out.** The fixed `R`/`B`/`R'` bits give the rows
   `xmm0`–`xmm7`; `xmm8`–`xmm15` need an extension bit and are rejected
   `E-OPERAND-004` (`N14b`), exactly as `r8`–`r15` are on the `gpr64` rows
   (`EC-06`).
6. **The table declares its extensions, and the plan must match.** EVEX.128
   needs AVX-512VL, so `0.5.0` declares
   `enabled_extensions: ["avx", "avx512f", "avx512vl"]` and a plan naming the
   table must declare the same sorted set (`E-TARGET-001`, `N06`). There is
   still one set per table and no per-form requirement, so `E-TARGET-003`
   remains unreachable (`04_errors.md` §2.3).
7. **`EC-09` is frozen** with `form variant` as the carrier; `EXP-0032` records
   the measurement.
8. **Only `0F 28` at `xmm` width.** The `0F 29` store direction, memory
   operands, masking (`aaa`), `ymm`/`zmm`, the three-byte `C4` VEX form, the
   `0x66`-prefixed `movapd` and the `movdqa` family stay out. Each is a
   different form family or needs a field this slice does not model.

## Consequences

- `X86-P9` moves from deferred to passing with a 13-byte fixture:
  `movaps %xmm1,%xmm0` + `vmovaps %xmm3,%xmm2` assembled by `llvm-mc`, plus the
  decode-verified `62 f1 7c 08 28 e5` (`vmovaps %xmm5,%xmm4`).
- `N01aa` names `x86:vmovaps/xmm-xmm` with no family (`E-FORM-001`, no
  default); `N01ab` names the VEX row against `0.4.0` (`E-FORM-001`, the
  version boundary); `N02l` puts `x86.zmm` on the `xmm` row
  (`E-OPERAND-001` on `kind` and `target_type`, so the width cannot silently
  select another family); `N06` omits the extensions (`E-TARGET-001`);
  `N14b` names `xmm8` (`E-OPERAND-004`).
- The table grows from 22 to 25 rows, so `07_definition_format.md` §8.1 and
  the digest move with it. `0.5.0` is the first x86 table with a non-empty
  `enabled_extensions`, so every plan that names it must carry the same list.
- `OD-10`'s VEX/EVEX deferral is lifted by this slice; `EC-05`, `EC-10` and
  RISC-V atomics stay out.
- Cost: three rows for one operation direction. A future slice that adds the
  store direction or `ymm`/`zmm` doubles or triples the family list; keeping
  one row with a family operand would put the family in the plan as a value,
  which is what `OD-11` removed.

## Alternatives considered

- **One `vmovaps/xmm-xmm` row with an `encoding_family` operand or modifier.**
  Rejected: `OD-11` chose `form_id` as the only carrier and removed
  `encoding_choices`; a family field is the same second selector under a new
  name, and `04_errors.md` already rejects an unpermitted modifier with
  `E-OPERAND-003`.
- **One row and let the encoder pick VEX unless the operand needs EVEX.**
  Rejected: at `xmm` width neither encoding needs EVEX, so the choice would be
  an implementation preference, and two honest implementers would emit
  different bytes (`INV-02`).
- **Ship only the EVEX.512 (`zmm`) row to avoid a decode-verified vector.**
  Rejected: the slice's question is the family at one operand shape. At 512
  bits the width already implies EVEX, so the family would look inferable from
  the operand, which is the false conclusion this ADR exists to prevent.
- **Encode the family as a leading template fragment chosen by the plan.**
  Rejected: a plan field that selects a fragment is a selector again; the form
  table is the only place the decision may live.
- **Declare no extensions and treat AVX-512 as an environment fact.**
  Rejected: `01_contract.md` §2 says `enabled_extensions` determines which
  forms are legal, and `INV-05` forbids a hidden host dependency. The plan and
  the definition must name the same target.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `movaps %xmm1,%xmm0` is `0f 28 c1`; `vmovaps %xmm3,%xmm2` is `c5 f8 28 d3` | `llvm-mc -show-encoding`, `EXP-0032` §2 | high |
| `62 f1 7c 08 28 e5` decodes as `vmovaps %xmm5,%xmm4` | `llvm-mc -disassemble`, `EXP-0032` §2 | high |
| `62 f1 7c 28 28 c1` is `ymm`, `62 f1 7c 48 28 c1` is `zmm` | `llvm-mc -disassemble`, `EXP-0032` §2 | high |
| The EVEX.128 form is legal without a mask | `llvm-mc -disassemble` accepts `aaa = 000` and prints the instruction; `EXP-0032` §2 | high |
| `llvm-mc` selects VEX, never EVEX, for `vmovaps %xmm, %xmm` | `-show-encoding` on the mnemonic; `EXP-0032` §2 | high |
| `xmm8`–`xmm15` change the REX/VEX/EVEX extension bits | `movaps %xmm8,%xmm9` is `45 0f 28 c8`; `62 71 7c 08 28 c1` decodes as `vmovaps %xmm1,%xmm8`; `EXP-0032` §2 | high |

## Review triggers

- `ymm`/`zmm` rows are attempted: `L'L` becomes part of the form, and a
  `zmm` row needs `R'`/`V'` for registers 16–31, which is a slot-kind decision.
- A memory operand is added: `EVEX` also changes displacement compression
  (`disp8*N`), so the `disp` field is not the same on the two sides of the
  family.
- Masking is added: `aaa` becomes a `x86.k` operand, and `{z}` needs a second
  form, not a modifier.
- The three-byte `C4` VEX form is added: it carries `X`/`B` and a different
  `mmmmm`, so the `vex` suffix alone would no longer pin the template.
- A per-form extension requirement is added: `E-TARGET-003` becomes reachable
  and `N06` must be split into the two codes.
