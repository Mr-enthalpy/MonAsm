# Encoder Boundary Audit — Phase 1

Status: **complete for gate G1** (2026-11-03). Behavioural claims in this document
are marked `experiment` and reproduce from
`research/evidence/experiments/EXP-0001-xirasm-boundary-probes.md`. Claims that
rest on reading code alone are marked `source`. Claims we could not settle are
marked `unverified` and are listed in §8.

This document answers one question: **where is the smallest boundary at which
XirAsm stops being a policy layer and starts being an encoder, and what crosses
that boundary in each direction?** It does not re-open the assembler survey
(`AGENTS.md`, "Never do").

## 1. Subject

| Field | Value |
|---|---|
| Repository | `https://github.com/xir-kuku/XirAsm` |
| Revision | `3ee8a439f5ba` (`main`, retrieved 2026-11-03 via `codeload` tarball) |
| Product version | `0.3.5` (`xirasm --version`) |
| Library | `deps/xirasm-lib`, `VERSION` = `0.1.5` |
| Library Zig requirement | `minimum_zig_version = "0.17.0"` |
| License | Apache-2.0 (repository); generated A64 includes carry an Arm notice plus MPL-2.0, see F-13 |
| Build | `zig build -Doptimize=ReleaseSafe`, exit 0, `zig-out/bin/xirasm.exe` 3,227,136 bytes |
| Oracle | LLVM 23.1.2 |

## 2. Method

1. Read the library's public surface and follow each call path from the frontend.
2. Build the pinned revision and drive it with single-purpose sources.
3. Compare every byte against `llvm-mc`.
4. Where source reading and observed behaviour disagreed, the observation wins
   and the discrepancy is recorded.

No claim below is based on a function name. The three names most likely to
mislead — `encode()`, `materializeFixup()`, `encodeRaw()` — each have a finding
that says what they actually do.

## 3. Findings

### F-01 — The library has no AArch64 backend at all

- Evidence `source`: `deps/xirasm-lib/src/xirasm_backend.zig:3-5` exports exactly
  `x86`, `riscv`, `spirv`. The `src/` directory contains exactly
  `x86_encoder/`, `riscv_encoder/`, `spirv_encoder/`.
- `aarch64` and `arm64` appear **zero** times in library `.zig` sources.
- Caution for future readers: `a64` is *not* a counterexample. All 21 matches are
  x86 address-size prefixes (`p_a64`, `match.p_a64`) and the Itanium flag
  `if_ia64`. Searching for `a64` and concluding "AArch64 is supported" is exactly
  the naming-based inference `AGENTS.md` rule 4 forbids.
- Evidence `experiment`: `--isa aarch64` with `add x0, x1, x2` and no import
  fails with `error: instruction text emission is not supported for this target
  ISA`. There is no AArch64 encoder path in the assembler core.
- Confidence: **high**.

### F-02 — The library excludes the entire FMP surface

- Evidence `source`: `deps/xirasm-lib/README.md:12-19` lists as out of scope:
  assembler symbol tables and labels, pseudo directives and frontend source
  control, runtime page allocation, C ABI runners, Meta VM behaviour, and
  object/linker ownership.
- Interpretation: layout, symbols, fixups and object formats are frontend
  responsibilities. Any "reuse the library" route still builds the whole FMP
  layer ourselves.
- Confidence: **high**.

### F-03 — x86 form selection happens inside `findMatch`, and it is policy

- Evidence `source`: `deps/xirasm-lib/src/x86_encoder/match.zig:287-331`.
  `findMatch` clears any caller-supplied choice (`instruction.itemp = null`,
  `itempindex = -1`) and then scans the instruction's template bucket, keeping the
  best-ranked match.
- `match.zig:311-320` breaks out early on an exact match, and
  `match.zig:339-349` (`preferSameRankMatch`) implements a hand-written
  tie-break: when two templates match equally, prefer the exact 64-bit O64 row
  over a byte-size alias. The comment at `match.zig:343-345` states the reason —
  "source-chain data has OPT byte-size aliases for reg64,rm8 forms and later
  exact o64 rows… the exact W row must win, while unrelated OPT rows such as
  RDPID reg64 keep their shorter first-match encoding."
- Interpretation: the library contains curated policy over equally legal
  encodings. It is *good* policy — it is still policy, and it is invisible to the
  caller.
- Decisive detail: because `findMatch` resets `itemp`, a caller **cannot** pin a
  template by pre-setting it, and `size.insnSize` (`size.zig:129-138`) calls
  `findMatch` again on every size query. The public x86 surface
  (`api.zig` `pub fn` list) is `encodeBuiltinUnits`,
  `encodeBuiltinUnitsWithResolver`, `materializeOutput`, `materializeFixup` —
  there is no form-level entry point.
- Confidence: **high**.

### F-04 — x86 branch relaxation is controllable, but only by lying about state

- Evidence `source`: `api.zig:759-767` — `automaticBranchRelaxationCandidate`
  returns false when the operand carries `near|short|far|strict`. So the *text*
  qualifiers do force a form.
- `api.zig:328-335` — the relaxation hint is applied only when
  `branch_relaxation_hint == .near` **and** `branch_relaxation_current_known` is
  non-null and false. `api.zig:75-79` shows `branch_relaxation_hint` defaults to
  `null` and `current_known` defaults to `null`.
- Interpretation: to force the near form for a target whose value you already
  know, you must also declare that you do not know it. The API has no
  "this target is known; still use the near form" state.
- Evidence `experiment`: the default path auto-shortens. `jmp 0x10` → `eb 0e`;
  `jmp 0x1000` → `e9 fb 0f 00 00`. The same mnemonic produces different sizes
  depending on the value.
- Confidence: **high**.

### F-05 — The frontend re-encodes branches to force `.near`, then rewrites the fixup from the size

- Evidence `source`: `src/frontend/backend_adapter.zig:258-281`. First pass runs
  with the default context. If any fixup was produced *and* the mnemonic is a
  branch, the whole instruction is re-encoded with
  `withBranchRelaxationHint(.near)` and `withBranchRelaxationCurrentKnown(&false)`.
- `backend_adapter.zig:287` then calls `applyX86BranchFallbackFixup`, which
  rewrites a fixup record's `kind`, `offset` and `width_bits` **based on the
  encoded size** (2 bytes → `pc_relative`, offset 1, width 8; 5 bytes →
  `pc_relative`, offset 1, width 32).
- Interpretation: the fixup's meaning is retrofitted from the encoding the
  encoder happened to choose. If `INV-02` existed as a test in this codebase, this
  function would fail it. It is also the clearest single piece of evidence that
  form selection and fixup semantics cannot be separated after the fact — the FMP
  must carry both, decided upstream.
- Confidence: **high** (source read; the two-pass behaviour is also consistent
  with every experiment in §F-06).

### F-06 — Numeric `short` branches bypass the range check and use a wrong base

- Evidence `experiment` (full table in EXP-0001 §2.2):

| Source | Bytes | Correct answer |
|---|---|---|
| `jmp short 0x82` | `eb 80` | out of range; must reject |
| `nop` + `jmp short 0x82` | `90 eb 80` | `eb 7f` |
| `origin(0x3005)` + `jmp short 0x3010` | `eb 0e` | `eb 09` |

- Two defects: no 8-bit range check on the numeric path, and a displacement base
  of `origin + instruction_size` that ignores the instruction's real offset.
- Contrast `experiment`: the label path is correct in both respects —
  `nop + jmp short lbl + lbl: nop` → `90 eb 00 90`, and an out-of-range label is
  rejected with `error: PC-relative fixup target 'far_lbl' (0xca) does not fit
  the signed 8-bit displacement`.
- Interpretation `inference`: a numeric target is folded into a concrete
  displacement before layout, so no `Fixup` is created and the range check in the
  fixup materializer never runs.
- Confidence: **high** for the behaviour, **medium** for the mechanism.

### F-07 — x86 immediate and displacement width are chosen implicitly, and LLVM agrees

- Evidence `experiment` (EXP-0001 §3): `add rax, 1` → `48 83 c0 01` (imm8);
  `add rax, 300` → `48 05 2c 01 00 00` (accumulator `05 id`, *not* `81 /0 id`);
  `mov rax, [rbp-8]` → `48 8b 45 f8` (disp8); `mov rax, [rbp-200]` → disp32.
  `llvm-mc` emits identical bytes for the first, second and fourth.
- There is no operand-level way to request the other form: the x86 operand parser
  recognises only `short`, `near`, `far`, `strict`, and only for branches
  (`api.zig:759-767`).
- Interpretation: two independent, correct assemblers both pick the same form and
  both refuse to let the user pick the other. This is the load-bearing
  counterexample for `EC-01`, `EC-02` and `EC-04`.
- Confidence: **high**.

### F-08 — RISC-V is mnemonic-driven, but `encodeRaw` does accept a pinned spec

- Evidence `source`: `riscv_encoder/tables.zig:11-18` linear-scans
  `generated_core.instructions` and returns the **first** spec whose name matches
  and whose `min_xlen <= xlen <= max_xlen`.
- `riscv_encoder/api.zig:16-28` exposes `instructionByMnemonic`,
  `instructionByMnemonicAnyXLen`, `encode` (semantic) and `encodeRaw`.
- `encodeRaw` takes `spec: *const types.InstructionSpec`, and
  `tables.instructions` is public (`tables.zig:5`), with all `InstructionSpec`
  fields public (`types.zig`). So a caller **can** pin a form: scan the table for
  the desired `match`/`mask`/`format`, then call `encodeRaw`.
- This is the one genuine form-addressable entry point found in the library.
  Its weakness is identity: the natural keys are an array index or `match/mask`,
  neither of which is a stable contract across definition versions (Q2, `OD-04`).
- Confidence: **high**.

### F-09 — Duplicate-spec ambiguity does not exist at a fixed xlen

This was a hypothesis; the experiment refutes it. Recorded because refuted
hypotheses are also findings.

- Evidence `experiment`: parsed all 1,700 `InstructionSpec` entries from
  `generated_core.zig:10277`. At `xlen=64`, 1,363 specs are valid and they have
  1,363 **distinct** names. At `xlen=32`: 1,433 and 1,433. Zero names resolve to
  more than one spec at a given xlen.
- Four names appear twice overall — `ld`, `slli`, `srai`, `srli` — each split
  across the RV32/RV64 ranges. `slli`/`srai`/`srli` even share `match` and `mask`
  (`0x00001013` etc.); the difference is field width, `shamtw` (lsb 20, width 5)
  vs `shamtd` (lsb 20, width 6). The xlen gate is what disambiguates them,
  correctly.
- Interpretation: the first-match scan is deterministic and unambiguous. The
  problem is not ambiguity; it is that the *selector* is a mnemonic string, so
  form identity is still implicit (`INV-01`).
- Confidence: **high**.

### F-10 — RISC-V range and register checks are genuinely strict

- Evidence `experiment` (EXP-0001 §4): `addi ...,2048` and `addi ...,-2049`
  rejected; `beq ...,0x1008` rejected; `c.j 0x800` rejected; `c.addi a6,5`
  (x16) rejected.
- Evidence `source`: `encode.zig:1250-1254` (`packField`) rejects values wider
  than the field; `encode.zig:1256-1274` provides `unsignedRange`,
  `wrapSigned`, `wrapAlignedSigned` (range plus alignment);
  `encode.zig:1109-1112` (`compressedRegValue`) restricts compressed registers to
  `x8..x15`.
- Interpretation: this is the behaviour `INV-07` demands. It also shows the
  library knew how to reject in 2026 — the x86 numeric-branch truncation (F-06)
  is a gap, not an architectural limit.
- Confidence: **high**.

### F-11 — RISC-V never compresses automatically

- Evidence `experiment`: `addi a0, a0, 1` → `13 05 15 00` (4 bytes, though
  `c.addi` fits); `nop` → `13 00 00 00` (4 bytes, not `c.nop`); `c.addi a4, 5`
  → `15 07` only when written explicitly.
- Interpretation: `EC-19` is satisfied by the reference implementation from the
  other direction — a correct assembler must *not* compress. Our materializer
  must reproduce this restraint, and `N04` must ensure we reject rather than
  shorten.
- Confidence: **high**.

### F-12 — AArch64 is a 40.9 MB Meta-language program, not a component

- Evidence `source`: `include/arm/a64.inc` is 301 bytes of eight `import(...)`
  lines. The real content is `include/arm/a64/**`, **40.88 MB**, including
  `generated/latest/source-bodies.inc` (6,964,127 B),
  `source-dispatch.inc` (5,653,452 B), `manifest.json` (1,898,361 B),
  `legacy.inc` (1,405,736 B), `entry.inc` (1,325,943 B).
- These are executable Meta functions, not tables. `include/arm/a64/scalar.inc`
  contains `fn a64_modifier_prefix(text: string) -> u64` with `for` loops,
  `starts_with`, `lower`, `trim` and `assert`. Operand text is parsed by string
  manipulation at assembly time.
- Evidence `experiment`: without the import, AArch64 fails outright (F-01).
  With it, all five bytes groups in `label_case.asm` match `llvm-mc` exactly.
- Interpretation: AArch64 could be *reused as an oracle* by shelling out, but it
  cannot be linked into a materializer that must satisfy `INV-06` (no
  metaprogramming) and `INV-05` (no hidden state). The value is the *knowledge*,
  and F-13 says where that knowledge comes from.
- Confidence: **high**.

### F-13 — The AArch64 knowledge source is Arm's Machine Readable Specification

- Evidence `source`: `include/arm/a64/generated/latest/NOTICE` states the
  inventory and encoding mappings use the **Arm Architecture Machine Readable
  Specification, 2026-06**, and reproduces Arm's three-clause BSD notice
  ("Copyright 2010-2026 Arm Limited or its affiliates").
  `manifest.json` records `"generator": "tools/a64/2026-10-10/generate.py"` and
  node counts: 4,350 `Instruction`, 292 `InstructionAlias`, 778 `InstructionGroup`;
  it also pins upstream file hashes (e.g. `Features.json` sha256
  `633259000ffd3da32900bd0c0c1beae4a9eea7095c278f74d62a00c846b41187`).
  The directory also ships `MPL-2.0.txt`.
- Interpretation: this settles `OD-07`'s knowledge-source question in principle.
  The authoritative, machine-readable source exists and is permissively licensed
  under an Arm notice; XirAsm already demonstrates a generator pipeline over it.
  Route C should generate its own tables from the MRS rather than inherit the
  Meta layer. The licensing question (which parts are Arm-licensed, which MPL-2.0)
  needs a deliberate answer before any file is copied.
- Confidence: **high** for provenance, **unverified** for licence obligations.

### F-14 — The frontend's error model is lossy; the library's is not

- Evidence `source`: `src/frontend/backend_adapter.zig:573-587` maps most
  `x86.EncodeError` values to `error.UnsupportedX86Instruction` via
  `else => ...`; `mapX86MaterializeError` at `:589-599` collapses six distinct
  materialization failures into `BackendOutputMaterializationFailed`; and
  `mapRiscvSourceError` at `:601-606` is
  `error.OutOfMemory => ..., else => error.UnsupportedRiscvInstruction` — every
  non-OOM RISC-V failure becomes one message.
- Evidence `experiment`: four distinct RISC-V failures
  (immediate out of range, branch out of range, compressed-register violation,
  out-of-range `c.j`) all surface as `error: unsupported RISC-V instruction form`.
- Interpretation: `E-*` codes cannot be recovered from the frontend, but the
  library's own error set distinguishes the cases. If error identity were ever
  needed from this system, it would have to come from the library, not the CLI.
- Confidence: **high**.

### F-15 — The source language is itself a program with loops and macros

- Evidence `source`: `tests/isa/x86/branch_boundary_matrix.asm` uses
  `for i in range(0, 127) { nop }`; `tests/isa/arm/label_case.asm` uses
  `import("arm/a64-macros.inc")`, `dq(...)` data directives and `:lo12:`
  modifiers.
- Interpretation: the `.asm` test corpus cannot be used as a neutral oracle or a
  fixture source. It is Meta source executed by the frontend, so a byte produced
  from it depends on interpreter semantics, not just on the instruction.
- Confidence: **high**.
- Consequence for us: fixtures must hold *frozen FMP plans*, never XirAsm source.

## 4. Gate G1

The gate asked three questions. Answers:

| Question | Answer | Basis |
|---|---|---|
| Can x86 branch relaxation be disabled? | **No, not cleanly.** Forms can be forced with the `short`/`near` text qualifiers for known targets, and with a hint for unknown targets — but the hint only takes effect when the caller declares the target unknown (`api.zig:328-331`), and the default is to let the encoder choose. There is no way to pin the template index (`findMatch` resets it). | F-03, F-04, F-05 |
| Is the RISC-V API form-addressable? | **Partly.** `encodeRaw(request, spec)` accepts a pinned `*const InstructionSpec`, and the spec table is public. Identity is the gap: index or `match/mask` is not version-stable. | F-08, F-09 |
| Is there an AArch64 library entry point? | **No.** Zero `aarch64`/`arm64` references; AArch64 exists only as a 40.9 MB interpreted Meta program driven by `include/arm/a64/**`. | F-01, F-12 |

G1 is **passed**: all three answers rest on source citations plus reproducible
experiments, and each is recorded with the command that produced it.

## 5. Consequences for the contract

| Finding | Contract consequence |
|---|---|
| F-03, F-05, F-07 | `EC-01`, `EC-02`, `EC-03`, `EC-04` are now evidenced rather than hypothetical. `EC-04` was `draft`; the accumulator-vs-ModRM counterexample is observed in two independent tools, so it can be frozen. |
| F-06 | Supplies the counterexample for `E-RANGE-002` / `N04`: a materializer that truncates an out-of-range `rel8` is exactly what `INV-07` forbids. |
| F-05 | Justifies keeping `fixup` fields explicit in the plan: form, size and fixup kind must be frozen together, never derived from each other. |
| F-10, F-11 | `EC-19`, `EC-20`, `N03`, `N04` describe behaviour a correct encoder already has; they are regression guards, not novel requirements. |
| F-12, F-13 | `OD-07` can be answered with Arm MRS as the knowledge source; the decision still needs a licence review. |
| F-14 | Our `E-*` registry must be richer than "assembler failed"; the library proves the distinctions exist. |
| F-15 | Fixtures are FMP plans, never XirAsm sources (`fixtures/README.md` already says this; now it has a reason). |
| F-03, F-08 | The reuse matrix classifies x86 as **D** and RISC-V as **B/C**; see `91_reuse_matrix.md`. |

## 6. What we would have to reimplement

Not a cost estimate, only a list of what the audit proved we cannot inherit
unchanged:

1. x86 template selection over equally legal encodings (F-03) — replaced by
   `form_id` lookup.
2. x86 branch form choice and the two-pass re-encode (F-04, F-05) — replaced by an
   explicit `EC-03` value.
3. x86 numeric-branch range checking (F-06) — replaced by `E-RANGE-002`.
4. The x86 `mov`/`add` accumulator and imm8 aliasing (F-07) — replaced by
   `form_id` variants.
5. RISC-V mnemonic resolution (F-08, F-09) — replaced by `form_id` lookup against
   our own table, with the same specs possible as a starting point.
6. AArch64 entirely (F-12) — new tables generated from the MRS (F-13).

## 7. Reproducing this audit

```bash
# pinned snapshot
curl -L -o xirasm.tar.gz https://codeload.github.com/xir-kuku/XirAsm/tar.gz/3ee8a439f5ba
tar -xzf xirasm.tar.gz -C research/external

# build
cd research/external/XirAsm
zig build -Doptimize=ReleaseSafe

# probes
cd ../xirasm-probe
./probe.ps1  -Cases 'a::jmp 0x10','b::jmp short 0x82'
./probe2.ps1 -Isa rv64 -Cases 'c::addi a0, a1, 2048'

# oracle
llvm-mc -triple=x86_64 -x86-asm-syntax=intel -show-encoding
```

Each probe writes `*.xir`, `*.bin` and `*.log`. The two scripts are scratch tools
under a gitignored directory; the recorded numbers in EXP-0001 are the durable
artefact.

## 8. Unverified

| Claim | Why it stays unverified |
|---|---|
| The numeric-branch defect's mechanism (displacement folded before layout) | Inferred from behaviour plus `backend_adapter.zig:266-287`; the actual fold site was not traced. |
| Whether `encodeRaw` can express every RV64 form we need | Only `addi`, compressed forms, `beq`, `jal` and `c.j` were exercised. |
| AArch64 licence obligations | The NOTICE and MPL-2.0 file were read; which files fall under which licence was not. |
| LLVM internals (relaxation in `MCAssembler` vs `MCCodeEmitter`) | LLVM was used only as an oracle; no LLVM source was read in Phase 1. |
| XirAsm behaviour on RISC-V relocation pairs (`auipc`+`lo12`) | Not exercised. Phase 3 needs it for `AC-05`. |
