# M6 Plan — Coverage Round 2

- Status: accepted (`ADR-0112`)
- Date: 2026-11-09
- Baseline: Phase 6 closed (`ADR-0111`): 759 forms, 121 positive and 586
  negative plans, `fmp/0.1` frozen
- Scope: seven slices plus a closure ADR; one ADR per slice; no contract change

## 1. Why this round

M5 added seven vertical slices, but the integer surface is still a set of
strips rather than families. The gaps are not open format questions: each is
the same form/operand split the existing rows already use, and each is already
absent from the pinned tables, so a plan that names it is `E-FORM-001` today.

| Missing surface | Evidence |
|---|---|
| x86 `add`/`sub` exist only at 64 bits; no `and`/`or`/`xor`/`cmp` at any width | `definitions/x86_64/0.74.0.json` family scan: `add` 3, `sub` 6, no other ALU mnemonic |
| no x86 `mov` immediate row; `movl $ext, %eax` is a recorded gap | `ADR-0093` review triggers; `0.74.0` has no `mov` row with an immediate slot |
| `sub` has no memory direction; `2B /r` and the `29 /r` memory shapes are deferred | `ADR-0110` decision 4 and review triggers |
| RV64 has only `ld`/`sd`; no other load/store width | `definitions/rv64/0.5.0.json`: 15 forms |
| AArch64 has no `adr`, `mul` or `csel` | `definitions/aarch64/0.18.0.json` family scan |

M6 closes these gaps under the M5 rules: one ADR per family, a measured
positive vector, an independent oracle, and an `E-FORM-001` fixture for the
sibling the slice leaves out.

## 2. Scope

| # | ADR | Slice | Definition | New rows | Vector |
|---|---|---|---|---|---|
| `S1` | `ADR-0113` | x86 ALU register/register at three widths | `x86/0.75.0` | 16 | `X86-P81` |
| `S2` | `ADR-0114` | x86 ALU immediate at three widths | `x86/0.76.0` | 36 | `X86-P82` |
| `S3` | `ADR-0115` | x86 `mov` immediate at 16/32/64 | `x86/0.77.0` | 6 | `X86-P83` |
| `S4` | `ADR-0116` | x86 `sub` memory directions | `x86/0.78.0` | 12 | `X86-P84` |
| `S5` | `ADR-0117` | RV64 load/store widths | `rv64/0.6.0` | 9 | `RV-P12` |
| `S6` | `ADR-0118` | AArch64 `adr` | `aarch64/0.19.0` | 1 | `A64-P23` |
| `S7` | `ADR-0119` | AArch64 `mul` and `csel` | `aarch64/0.20.0` | 4 | `A64-P24` |
| — | `ADR-0120` | Closure and metrics | — | — | — |

The round adds 84 forms: x86 564 → 634, AArch64 180 → 185, RV64 15 → 24, for
843 in total. Positive vectors grow 121 → 128; each slice adds at least three
negatives and the closure ADR records the exact corpus.

The standing non-goals stay closed: `moffs`, APX `d5`, EVEX masking and
broadcast, AArch64 `EC-16` (the `mov` alias) and `EC-18` (`cbz`/`tbz`),
RV64 `c.j`/`c.jalr`, and FP/SIMD beyond SSE. Level 2 containers stay out of
`fmp/0.1`.

The round also defers, and each slice names it in its review triggers:

- the high register windows (`%r8`-`%r15`) and SIB/index and zero-displacement
  memory shapes;
- the 8-bit ALU and `mov` immediate windows (the three byte-register sets);
- `movabs` (`REX.W B8+rd io`, a 64-bit immediate), `adc`/`sbb`, `test`,
  `neg`/`not`, and the memory forms of the new ALU mnemonics;
- RV64 `fence`, `ecall`/`ebreak`, atomics and the compressed family;
- AArch64 `tbz`/`tbnz`, `madd`/`msub` with a non-zero `Ra`, and
  `cset`/`cinc`.

## 3. Slice detail

### S1 — x86 ALU register/register (`ADR-0113`, `0.75.0`, `X86-P81`)

16 rows, one low-register window, the `r/m`-destination direction:

- `add`/`sub` at 32 and 16 bits (4 rows), completing the 64-bit rows that
  already exist;
- `and`/`or`/`xor`/`cmp` at 64, 32 and 16 bits (12 rows).

`EC-42` is revised in place: the whole `opcode`/`opcode+1` pair
(`01`/`03`, `09`/`0B`, `21`/`23`, `29`/`2B`, `31`/`33`, `39`/`3B`) has the
same direction choice, and the register-destination sibling of every pair
stays absent. No new `EC` row is needed.

The slice leaves out `adc`/`sbb`, the 8-bit widths, the high register window
and memory shapes. Negatives: `adc` (`E-FORM-001`), the previous-version
boundary, register `8` past the three-bit field (`E-OPERAND-004`) and a missing
source (`E-OPERAND-002`).

### S2 — x86 ALU immediate (`ADR-0114`, `0.76.0`, `X86-P82`)

36 rows:

- `add`/`sub` at 32 bits (`imm8`, `imm32`) and 16 bits (`imm8`, `imm16`),
  8 rows;
- `and`/`or`/`xor`/`cmp` at 64, 32 and 16 bits, `imm8` plus `imm32`/`imm16`,
  24 rows;
- the `%rax` short form of the four new mnemonics at 64 bits (`25`, `0D`,
  `35`, `3D`), 4 rows.

`EC-04` already carries `imm8` vs `imm32`; the 16-bit `iw` width is the
existing operand-size prefix (`EC-07`). If the `%rax` short form is not already
a named decision, the slice adds one `EC` row before the rows land.

The `test`/`neg`/`not` group, the 8-bit width, the 32/16-bit `%rax` short
forms and the memory forms stay out. Negatives: `test` (`E-FORM-001`), the
signed-8 end, the `imm16` end and the version boundary.

### S3 — x86 `mov` immediate (`ADR-0115`, `0.77.0`, `X86-P83`)

6 rows:

- `B8+rd` at 16/32/64 (`66 B8+rw iw`, `B8+rd id`, `REX.W B8+rd id`);
- `C7 /0` at 16/32/64 (`66 C7 /0 iw`, `C7 /0 id`, `REX.W C7 /0 id`).

Both shapes encode `mov r64, imm32`, so the choice is byte-affecting: the
slice adds one `EC` row and the plan names the row, never a flag.

`movabs` (`REX.W B8+rd io`), the 8-bit `B0`/`C6` windows and the high register
windows stay out. Negatives: `movabs` (`E-FORM-001`), the signed-32 end and the
version boundary.

### S4 — x86 `sub` memory directions (`ADR-0116`, `0.78.0`, `X86-P84`)

12 rows: `29 /r` (store direction) and `2B /r` (load direction) at 64, 32 and
16 bits, each with `base + disp8` and `base + disp32`, low base window.

`EC-42` is revised again to state the memory direction: `29` keeps the
destination in `ModRM.r/m`, `2B` in `ModRM.reg`. The register/register `2B`
spelling stays absent (`N01ej`).

`%rsp`/`%r12` need a SIB base, the zero-displacement shape needs `mod = 00`, and
the high base window needs `REX.B`; all three stay out. Negatives: an absent
indexed sibling (`E-FORM-001`), the signed-8 end and the version boundary.

### S5 — RV64 load/store widths (`ADR-0117`, `0.6.0`, `RV-P12`)

9 rows: `lb`, `lh`, `lw`, `lbu`, `lhu`, `lwu`, `sb`, `sh`, `sw`. Each is one
form: `rs1` base, `rd` or `rs2` value, `imm12` field content. `ld`/`sd` are
unchanged.

`fence`, `ecall`/`ebreak`, atomics and the compressed load/store family stay
out. Negatives: `fence` (`E-FORM-001`), the `imm12` end and the version
boundary.

### S6 — AArch64 `adr` (`ADR-0118`, `0.19.0`, `A64-P23`)

1 row: `aarch64:adr/x64-imm21`. The immediate is split between `immlo`
(bits 30–29) and `immhi` (bits 23–5), and `P` is the instruction address, which
is the existing `pcrel_begin` rule — no new fixup rule is needed. The slice
adds one `EC` row for `adr` vs `adrp`: byte offset (±1 MiB) vs page.

`tbz`/`tbnz` (`EC-18`) and the `mov` alias (`EC-16`) stay closed. Negatives:
`adrp` named as `adr` (`E-FORM-001`), the `imm21` end and the version boundary.

### S7 — AArch64 `mul` and `csel` (`ADR-0119`, `0.20.0`, `A64-P24`)

4 rows:

- `mul` at 32 and 64 bits: the `MADD` alias with `Ra = 31`, so the plan names
  three operands and the alias node supplies the fixed field (the `cmp`/`cmn`
  precedent, `ADR-0021`);
- `csel` at 32 and 64 bits, with the condition as the existing
  `aarch64.cond`/`cond4` operand.

The slice adds one `EC` row for the `mul` alias. `madd`/`msub` with a non-zero
`Ra`, `cset`/`cinc` and `tbz`/`tbnz` stay out. Negatives: `madd` named as
`mul` (`E-FORM-001`), `cond = 16` (`E-OPERAND-004`) and the version boundary.

## 4. Definition and fixture plan

- Every slice is additive: the generator repeats the previous version
  byte-for-byte before appending, and the previous version stays frozen.
- Every new form is named by the slice's positive vector; `check_definition.py`
  enforces form coverage.
- Every vector has an `llvm-mc` 23.1.2 oracle (or a recorded manual derivation)
  and a second source: the materializer's output is compared against the
  oracle bytes, never against itself.
- Each slice adds at least one `E-FORM-001` fixture for its deliberately absent
  sibling, plus the operand/range negatives named above.
- `research/evidence/experiments/EXP-0112` onward holds the probes; the
  generators and measurement scripts stay with the evidence, not in the
  product crates.

## 5. Gates

Every slice keeps the existing gates green:

- `python tools/check_ids.py`;
- `python tools/check_definition.py` (definition changes);
- `python tools/check_rv64_source.py`;
- `cargo test --workspace`, `cargo fmt --all -- --check` from `prototype/`;
- `python tools/oracle/rerun.py` and `git diff --check`;
- CI on Ubuntu, macOS and Windows for the closure commit.

The closure ADR records the final form, fixture, `EC` and rerun numbers and
updates `STATUS.md`, `08_final_recommendation.md` §H and the per-slice docs.

## 6. Risks and responses

| Risk | Response |
|---|---|
| A new row copies an opcode from a sibling without measuring it | One `llvm-mc` probe per mnemonic/width pair; the ADR cites the measured bytes |
| `mov` immediate and the ALU immediate slice disagree on `imm16` vs `imm32` | The 16-bit rows use `iw`; the slice ADR states it and the oracle proves it |
| `sub` memory introduces SIB by accident | Base window excludes `%rsp`/`%r12`; no SIB row exists, so naming one is `E-FORM-001` |
| AArch64 `adr` split field is described as a single window | The field descriptor has two pieces; the descriptor width sum is checked |
| `mul` grows a fourth operand | The alias shape is the three-operand one; a fourth operand is `E-OPERAND-002` |
| The round reopens a closed non-goal | `EC-16`/`EC-18` and the other standing non-goals stay closed; a proposal reopens the scope ADR |

## 7. Order

`S1` → `S2` → `S3` → `S4` → `S5` → `S6` → `S7` → closure. The x86 ALU slices
come first because they share the direction and immediate rules; the RV64 and
AArch64 slices are independent and can move without changing the contract.
