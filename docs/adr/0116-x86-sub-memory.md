# ADR-0116: `sub` memory directions at 64/32/16 bits

- Status: accepted
- Date: 2026-11-10
- Settles: `X86-P84` (the twelve `sub` memory rows and their byte vector)
- Supersedes: none
- Superseded by: none
- Revises: `EC-42` of `02_encoding_choices.md` (widened from the
  register/register pair to include the memory direction), the reading-aid
  table and `0.78.0` paragraph of `07_definition_format.md` §8.1, the x86 table
  of `06_validation_matrix.md`, and the `S4` row of `10_m6_plan.md` (marked
  landed); adds `definitions/x86_64/0.78.0.json`, `EXP-0115` and the
  `X86-P84`/`N01fb`/`N01fc`/`N03zz` fixtures

## Context

`0.77.0` has the `sub` register/register rows (`29 /r` at three widths) and the
immediate rows, but no `sub` row with a memory operand. Plan `X86-P84` names
the store direction (`29 /r`) and the load direction (`2B /r`) at 64, 32 and
16 bits, each with `base + disp8` and `base + disp32`.

The two directions are different opcode bytes for the same operands:

| Direction | Opcode | Register | Memory |
|---|---|---|---|
| store (`%rcx` into `8(%rax)`) | `29` | `ModRM.reg` | `ModRM.r/m` |
| load (`8(%rax)` into `%rcx`) | `2B` | `ModRM.reg` | `ModRM.r/m` |

`EXP-0115` measures `subq %rcx, 8(%rax)` as `48 29 48 08` and
`subq 8(%rax), %rcx` as `48 2b 48 08`: one opcode byte apart, the same
`ModRM` bytes. A plan that states only "subtract `%rcx` and `8(%rax)`" has not
chosen the byte.

`EC-42` already states the direction rule for the register/register pair, where
the `2B` spelling is absent (`N01ej`). The memory slice does not change that
decision, it names the memory rows for both opcodes, so the split is visible in
the table rather than implied.

## Decision

1. **Twelve new rows.** `0.78.0` appends `29 /r` and `2B /r` at 64, 32 and
   16 bits, each with `base + disp8` and `base + disp32`:
   - `sub/base-disp8-r64`, `sub/base-disp32-r64`, `sub/r64-base-disp8`,
     `sub/r64-base-disp32`;
   - the same four at `r32`;
   - the same four at `r16`.
2. **The register role follows the existing memory rows.** A memory
   destination keeps the `base` role and the register is `src`
   (`x86:mov/base-disp8-r64`); a memory source is `src` and the register is
   `dest` (`x86:mov/r64-base-disp8`). The form id spells the direction, so the
   row is chosen, never inferred from operand order.
3. **`EC-42` is revised, not duplicated.** The row already names the
   `opcode`/`opcode+1` pair; the slice adds the memory instance and the measured
   bytes, so the count stays 42. No new `EC` row.
4. **The base stays a 64-bit register at every width** (`x86.gpr64`/`rm64`),
   matching the `mov` memory rows: in 64-bit mode the address register is
   64-bit while only the data width changes.
5. **The field layout is the measured template with the fields zeroed.** The
   register is `[2,1]` (`REX.R`) + `[19,3]` at 64 bits, `[11,3]` at 32 bits and
   `[19,3]` at 16 bits. The base is `[0,1]` (`REX.B`) + `[16,3]` at 64 bits,
   `[8,3]` at 32 bits and `[16,3]` at 16 bits; the displacement follows the
   base at `[24,8]`/`[24,32]` (64 and 16 bits) and `[16,8]`/`[16,32]` (32 bits).
6. **The three shapes outside the vector are measured, not inferred.** `%rsp`
   as the base needs `SIB` (`48 29 4c 24 08`); `%r8` as the base sets `REX.B`
   (`49 29 48 08`), which the 64-bit rows already carry, so those bases are
   reachable but not exercised here; a zero displacement needs `mod = 00`
   (`48 29 08`), a different template of a different length. `%rsp`/`%r12` are
   `excluded` on every row; the zero-displacement shape stays out.
7. **`0.78.0` is additive and immutable.** It repeats the 620 `0.77.0` forms
   byte-for-byte, and the generator asserts the reproduction before it writes
   the new version. The digest is
   `sha256:30cb9f13047ff742d8f53a20f93218a601302bd52814ad26364347cb85576a21`.

## Consequences

- `X86-P84-sub-mem` is the 62-byte vector of twelve instructions: the two
  directions at three widths and two displacement sizes. The register is
  `%rcx`/`%ecx`/`%cx` or `%rdx`/`%edx`/`%dx`; the base is `%rax` for the
  `disp8` rows and `%rbx` for the `disp32` rows. The input hash is
  `021f2357172bb9ca3c338d326444dce9feef322281995f8787866110b5cf0000` and the
  output hash is
  `c5835c0f6f00d2f84ad8c201c215bf108abb53011f1e4e173f289a7253a03c10`.
- Every instruction is selectable from a mnemonic, so the oracle is `assembler`
  and `tools/oracle/rerun.py` re-derives the whole image (no
  `manual+disassembly` skip).
- `N01fb` (absent indexed sibling) and `N01fc` (a `0.78.0` row against
  `0.77.0`) are `E-FORM-001`; `N03zz` (`disp8 = 128`) is `E-RANGE-001`.
- The x86 table grows to 632 forms. The corpus grows to 125 positives and 601
  negatives, and every form in `0.78.0` is named by a positive fixture
  (`check_definition.py`).
- `0.77.0` remains readable and unchanged, so a plan pinned to it cannot name
  the new rows and keeps its old byte behaviour.

## Alternatives rejected

- **One row with a direction selector.** Rejected: the opcode byte is template
  content, and a selector is an implicit encoding-form choice (`INV-02`).
- **Only the store direction (`29 /r`).** Rejected: `2B /r` is a legal encoding
  of the same operation, and leaving it out makes `EC-42` one-sided in the
  memory case.
- **Add the register/register `2B` spelling here.** Rejected: it is a separate
  row and a separate decision; `N01ej` records its absence, and this slice is
  the memory geometry.
- **Add `%rsp`/`%r12` by folding `SIB` into the template.** Rejected: `SIB` is
  a variable byte with its own operand, and `%rsp`/`%r12` already have
  dedicated `rsp-*`/`r12-*` rows in the `mov` family. They are a separate
  slice.
- **Add the zero-displacement shape (`mod = 00`).** Rejected: it is a distinct
  template of a different length, and `%rbp`/`%r13` need `disp8 = 0` there.
- **Add the high base window (`%r8`-`%r15`) as new rows.** Rejected: at 64 bits
  `REX.B` shares the `REX.W` byte, so the existing rows already reach those
  bases; a value in `excluded` for 32/16 bits can only widen if a `REX` byte is
  added, which changes the length.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `0.77.0` has no `sub` row with a memory operand | form-id scan of `definitions/x86_64/0.77.0.json` | high |
| The twelve instructions are 62 bytes | `llvm-mc` object bytes, `EXP-0115` `measure.py` | high |
| `29` and `2B` differ only in the opcode byte | `llvm-mc -disassemble`, `EXP-0115` `direction.txt` | high |
| `%rsp`/`%r12` need `SIB`, `%r8` needs `REX.B`, zero displacement needs `mod = 00` | `llvm-mc -show-encoding`, `EXP-0115` `direction.txt` | high |
| `N01fb`/`N01fc` are `E-FORM-001`, `N03zz` `E-RANGE-001` | fixture gate, `EXP-0115` | high |
| `0.78.0` repeats `0.77.0` unchanged | generator assertion and digest | high |

## Review triggers

- The register/register `2B` spelling is proposed; it needs its own rows and
  ends the `N01ej` absence.
- `%rsp`/`%r12` as bases are proposed; they need the `SIB` geometry.
- The zero-displacement shape is proposed; it is a different `mod` and length,
  and `%rbp`/`%r13` need `disp8 = 0` to express it.
- Indexed addressing (`base + index * scale + disp`) is proposed; `SIB` adds an
  index and scale slot and its own exclusions.
- The 8-bit width or the immediate direction of `sub` memory is proposed; each
  is a different opcode or a different immediate slot.
