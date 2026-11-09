# ADR-0103: `fmp-def/0.2` states a per-form extension requirement

- Status: accepted
- Date: 2026-11-08
- Settles: `X86-P74` (the first `fmp-def/0.2` table: 513 forms with
  `requires_extensions`, and the positive/negative vectors that exercise it)
- Supersedes: none
- Superseded by: none
- Revises: `01_contract.md` §2/§4/§13 (the subset rule and the step-6 gate);
  `02_encoding_choices.md` EC-09 (the extension carrier is per form under
  `0.2`); `07_definition_format.md` §2/§3/§8.1/§9 (the format, the field and the
  load checks); `04_errors.md` §2.3/§2.4 (`E-TARGET-003` leaves the unreachable
  list, 37 → 38); `05_open_decisions.md` OD-05; the x86 table of
  `06_validation_matrix.md`; adds `definitions/x86_64/0.68.0.json`, `EXP-0104`
  and the `X86-P74`/`N06b`/`N06c` fixtures

## Context

Every shipped table declares one `enabled_extensions` set for the whole
document, and a plan must repeat it exactly (`E-TARGET-001`). That models "this
table is for a machine with these extensions" but not "this row needs that
extension": `0.5.0` lists `avx`, `avx512f` and `avx512vl` because one EVEX row
needs them, so a plan for a plain AVX machine has to claim AVX-512 to name any
row at all, and `E-TARGET-003` has no trigger (`04_errors.md` §2.3).

The failure the missing field allows is concrete: a plan declares
`enabled_extensions: ["avx"]` and names a `zmm` EVEX row. Under a pure subset
rule that plan's set is a subset of the table's set, so step 2 passes, the row
is found, the operands are legal and the materializer emits `62 …`. On a
machine without AVX-512 the first instruction raises `#UD`; the materializer
has accepted a plan the target cannot execute. The plan said which extensions
it may use; the table never said which ones the row uses.

`EXP-0104` measures the width split behind the x86 requirements with
`llvm-mc`/`llvm-objcopy` 23.1.2 on 2026-11-08:

| Source | Bytes | Family | Width field |
|---|---|---|---|
| `vmovaps %xmm1, %xmm0` | `c5 f8 28 c1` | VEX | `L = 0` (128-bit) |
| `vmovaps %ymm1, %ymm0` | `c5 fc 28 c1` | VEX | `L = 1` (256-bit) |
| `vmovaps %zmm1, %zmm0` | `62 f1 7c 48 28 c1` | EVEX | `L'L = 10` (512-bit) |

`llvm-mc -disassemble` reads the byte strings the assembler will not select:
`62 f1 7c 08 28 c1` is `%xmm1, %xmm0` (`L'L = 00`), `62 f1 7c 28 28 c1` is
`%ymm1, %ymm0` (`L'L = 01`) and `62 f1 7c 48 28 c1` is `%zmm1, %zmm0`
(`L'L = 10`). The width, not the mnemonic, decides which EVEX feature the row
uses: `L'L = 00/01` is AVX-512VL and `L'L = 10` is AVX-512F.

`mattr.txt` records the limit of the local oracle: `vmovaps` still assembles
with `-mattr=-avx`, `-mattr=-avx512f`, `-mattr=-avx512vl` and all three
switched off (rc 0 in every case), so `llvm-mc` 23.1.2 has no per-mnemonic
extension gate to use as a second source. The step from those width bits to the
extension names is therefore `inference` from the documented ISA, and the
table below is labelled accordingly.

## Decision

1. **Two definition formats, one new required field.** `fmp-def/0.1` is
   unchanged. `fmp-def/0.2` requires `requires_extensions` on **every** form;
   `[]` is the baseline, not an omission. The field stays out of the plan and
   out of `fmp/0.1`: the requirement belongs to the encoding, and a plan field
   would let the plan weaken its own gate.
2. **`enabled_extensions` becomes an upper bound under `0.2`.** The table's set
   is what the table can encode; the plan's set MUST be a subset
   (`E-TARGET-001`). Under `0.1` the comparison stays exact equality, so every
   existing fixture and `N06` keep their meaning.
3. **The per-form gate is `E-TARGET-003` at step 6.** After the form is found,
   the first name in the row's `requires_extensions` that the plan lacks is
   reported with `extension`, `form_id` and path `/instructions/N/form_id`, and
   the instruction's operand checks are skipped (`continue`), so one
   instruction yields one diagnostic. It is a static check, not a load-time
   check: it needs a named form, and it leaves the table loadable
   (`01_contract.md` §13).
4. **The loader rejects an unusable requirement.** A `0.2` form whose
   requirement names an extension the table does not declare, or whose list is
   empty-named, repeated or unsorted, is `E-DEF-001`. A form that requires what
   the table cannot encode could never be named by a matching plan, so the dead
   requirement would silently disable the gate. A `0.1` form that carries the
   field is also `E-DEF-001`: the object is closed, so an older loader cannot
   read a newer table and ignore the rule.
5. **`0.68.0` is the first `0.2` table.** It repeats the 513 forms of `0.67.0`
   with the same ids, templates and slots, so the bytes are unchanged, and adds
   one requirement per form:

   | Rows | Count | `requires_extensions` |
   |---|---|---|
   | `/legacy` | 388 | `[]` |
   | `/vex` | 38 | `["avx"]` |
   | `/evex` with a `zmm` slot | 29 | `["avx","avx512f"]` |
   | `/evex` with only `xmm`/`ymm` slots | 58 | `["avx","avx512f","avx512vl"]` |

   125 rows are gated, and every gated row is a `vmovaps` row. The digest is
   `sha256:4c9ff304b305ceb831fd99e22bf0a7c422cce4104d08de604a6509f58e1501d2`.
   The `0.2` set is listed in sorted order so the reported missing name is
   determined by the set, never by the JSON spelling.
6. **No materializer or plan change.** `fmp-model` gains the field and the
   format enum, `fmp-validate` gains the subset branch and the gate,
   `tools/check_definition.py` checks both formats, and the plan object remains
   the closed `fmp/0.1` object. Byte emission is untouched: `0.68.0` re-renders
   every form block, so its textual diff against `0.67.0` is large, but no
   template changed.

## Consequences

- `X86-P74-per-form-requirements` is `X86-P20`'s 24 VEX.256 instructions
  re-pinned to `0.68.0` with `enabled_extensions: ["avx"]`: a legal subset, and
  every named row requires only `avx`. The bytes are the same 144, and the
  oracle record shares `X86-P20`'s `input_sha256`
  (`5d120f3f2ebbc8ef580abababd46700002ece01365dcbaefa8cac969bd2e7eec`) and
  `output_sha256`
  (`a42f3ec7d528bcd4ba1f5ac80d20cb876f673a452ee4f7de318592862b708fe6`), because
  the independent measurement is the same `EXP-0045/P20.asm` run. `rerun.py`
  re-derives both records from that one input.
- `N06b-per-form-extension-not-enabled` declares `[]` and names a VEX row:
  step 2 passes (empty is a subset) and step 6 reports `E-TARGET-003` with
  `extension = avx`.
- `N06c-extension-not-declared-by-definition` declares `["sse4.2"]` and names a
  legacy row: step 2 reports `E-TARGET-001` with `found = sse4.2`, and the
  form's empty requirement adds nothing.
- `04_errors.md` §2.4 moves from 37 to 38 fixture-covered codes of 43 active;
  `E-TARGET-003` leaves §2.3, and `E-LAYOUT-005` and `E-INTERNAL-001` remain.
- `X86-P74` extends form coverage: `check_definition.py` requires every form of
  the newest table per ISA to be named by a positive fixture, and `0.68.0`
  inherits `0.67.0`'s full coverage because the form set is unchanged.
- The EVEX per-width requirements are decided here but not yet exercised by a
  positive vector; a plan that names an EVEX row with only `["avx"]` is
  `E-TARGET-003` even though no fixture pins that exact pair today.

## Alternatives rejected

- **An `extension_model` object (`min_extensions`, `implies`, …).** Rejected:
  it is a second vocabulary for one fact. A list per form is the smallest
  statement that answers "may this machine run this row?".
- **Filter the table per plan at load (`eligible_forms`).** Rejected: a filtered
  table makes form lookup depend on the plan, so the same `form_id` would be
  present or absent by environment rather than by `definition_identity`
  (`INV-05`), and `E-FORM-001` would hide a target mismatch (`INV-07`).
- **Make `requires_extensions` optional so `0.1` tables carry over.** Rejected:
  an omitted annotation silently disables the gate, which is exactly the
  failure this ADR fixes. The version bump makes the field mandatory.
- **Put the requirement in the plan.** Rejected: the plan would state what its
  own instructions need, so a plan could understate the requirement and pass.
  The encoding's requirement is not the caller's decision (`INV-01`).
- **Keep equality and add a second, independent `required_extensions` list.**
  Rejected: two sets would have to agree, and the rule for disagreement would
  be another implicit decision.
- **Give EVEX rows only `avx512f` and let a plan omit `avx`.** Rejected: every
  AVX-512 row is also a VEX-era extended encoding, and the table's own set
  already names `avx` first. A plan on an AVX-512 machine can declare all
  three; a plan that declares only `avx512f` would name a legacy row and miss
  nothing visible today, but the ordered list keeps the dependency explicit.
- **Use `-mattr` as the gating oracle.** Not an alternative, a measurement
  result: `llvm-mc` 23.1.2 does not gate x86 mnemonics on `-mattr`
  (`EXP-0104` `mattr.txt`), so the mapping is inference, not measured
  rejection.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| VEX.128 is `L = 0` and VEX.256 is `L = 1` | object bytes and `-show-encoding`, `EXP-0104` §1 | high |
| EVEX.128/256/512 are `L'L = 00/01/10` | `llvm-mc -disassemble`, `EXP-0104` §1; `EXP-0032` §2 | high |
| `llvm-mc` 23.1.2 does not gate `vmovaps` on `-mattr` | four rc-0 runs, `EXP-0104` `mattr.txt` | high |
| VEX rows need `avx`; EVEX `zmm` rows need `avx512f`; EVEX `xmm`/`ymm` rows need `avx512vl` | width bits above plus documented ISA dependencies; not measured as a rejection | inference |
| `0.67.0` has no per-form requirement | `definitions/x86_64/0.67.0.json`, key scan | high |
| `0.68.0` repeats the 513 forms and adds 125 gated rows | `generate_0680.py` assertion plus digest, `check_definition.py` | high |
| `N06b` is `E-TARGET-003` on `avx` | fixture gate and CLI run, `EXP-0104` §4 | high |
| `N06c` is `E-TARGET-001` with `found = sse4.2` | fixture gate and CLI run, `EXP-0104` §4 | high |
| `X86-P74` is 144 bytes identical to `X86-P20` | object bytes, `EXP-0045/P20.asm` and `EXP-0104` `fixture_p74.py` | high |

## Review triggers

- A table gains a form that needs an extension not already in the table's own
  set; the loader rejects it, so the table's set must be widened first and that
  is a new ADR.
- A positive fixture is proposed for an EVEX row; it must declare the exact
  width requirement, and the `0.1` equality fixtures must stay untouched.
- A definition format `0.3` is proposed; `0.2` is the format the loader reads
  and any new rule is a new document format, not a silent field.
- Another ISA gains an optional extension whose rows differ by encoding (for
  example RV64 `C` or an AArch64 feature); the same per-form field applies, but
  the extension names and the table's set need their own evidence.
