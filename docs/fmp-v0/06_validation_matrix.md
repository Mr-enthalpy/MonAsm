# Validation Matrix

Status: **draft**. Fixtures and results are filled in Phases 3–4. This file is
the canonical registry for `N*`, `EXP-R*`, and `AC-*`.

## 1. Negative tests (`N*`)

Every negative test must produce a registry code, not a generic failure. Fixture
naming: `fixtures/<isa>/negative/N0X-<slug>.fmp.json`.

| ID | Input condition | Expected | Code | ISAs | Fixture | Status |
|---|---|---|---|---|---|---|
| N01 | A required encoding choice is absent | Reject | E-CHOICE-001 | x86, aarch64, rv64 | TBD | planned |
| N02 | Operand register class does not match the form | Reject | E-OPERAND-001 | x86, aarch64, rv64 | TBD | planned |
| N03 | Immediate exceeds the field's range | Reject | E-RANGE-001 | x86, aarch64, rv64 | TBD | planned |
| N04 | Branch displacement exceeds the form's range | Reject, never expand | E-RANGE-002 / E-FIXUP-003 | x86, aarch64, rv64 | TBD | planned |
| N05 | `expected_size` disagrees with the encoded length | Reject | E-SIZE-001 / E-LAYOUT-003 | x86, aarch64, rv64 | TBD | planned |
| N06 | Form requires a disabled target extension | Reject | E-TARGET-003 | rv64 (C), x86 (AVX), aarch64 (optional feature) | TBD | planned |
| N07 | Fixup kind is incompatible with the field | Reject | E-FIXUP-001 | x86, aarch64, rv64 | TBD | planned |
| N08 | Reference to a symbol that does not exist | Reject per resolution mode | E-SYMBOL-001 / E-FIXUP-002 | x86, aarch64, rv64 | TBD | planned |
| N09 | Two layout fragments overlap | Reject | E-LAYOUT-001 | all (layout is ISA-independent) | TBD | planned |
| N10 | Definition digest does not match | Reject | E-DEF-001 | all | TBD | planned |
| N11 | Plan implies implicit alignment or padding | Reject | E-LAYOUT-002 / E-LAYOUT-005 | all | TBD | planned |
| N12 | Associated relocation pair is incomplete or inconsistent | Reject | E-FIXUP-007 | aarch64 (`adrp`+`lo12`), rv64 (`auipc`+`lo12`) | TBD | planned |
| N13 | `expected_digest` is present and the emitted bytes hash to a different value | Reject, never re-encode to match | E-BYTE-001 | x86, aarch64, rv64 | TBD | planned |

N13's counterexample is `EXP-0002` W2: a same-length encoder defect turns
`48 89 d8` (`mov rax, rbx`) into `49 89 d8` (`mov r8, rbx`), both 3 bytes and
both legal. `expected_size` cannot see it; only the digest can. The test must
also confirm the materializer does **not** attempt a repair (W4: a plan whose
immediate is edited must be rejected, not re-encoded around).

Applicability notes: N12 is not applicable to x86-64 in v0 because the selected
x86 slice uses a single-site `rel32`; if an x86 pair case is added, the row must
be revisited.

### Phase 1 evidence for N03 and N04

The audit produced both the positive restraint and the negative counterexample
from a built reference implementation (`90_boundary_audit.md` F-06, F-10, F-11;
raw commands in `research/evidence/experiments/EXP-0001-xirasm-boundary-probes.md`):

| Behaviour | Reference implementation | What our materializer must do instead |
|---|---|---|
| RISC-V immediate out of field range | rejects (`addi a0,a1,2048`) | same: `E-RANGE-001` |
| RISC-V branch out of range | rejects (`beq ...,0x1008`, `c.j 0x800`) | same: `E-RANGE-002` |
| x86 label branch out of `rel8` | rejects (`does not fit the signed 8-bit displacement`) | same: `E-FIXUP-003` |
| x86 numeric `short` branch out of `rel8` | emits `eb 80` for target `0x82` — **silently truncated** | reject: `E-RANGE-002`. This is the concrete failure N04 exists to prevent. |
| x86 unqualified branch | auto-shortens to `rel8`, promotes to `rel32` when far | never shorten, never promote: `INV-02`, `INV-04` |

## 2. Determinism experiments (`EXP-R*`)

| ID | Experiment | Method | Observable | Status |
|---|---|---|---|---|
| EXP-R1 | Repeated execution | Materialize the same plan 100 times in one process; compare bytes, fixup records, fingerprints | Byte equality | planned |
| EXP-R2 | Cross-process | Run the CLI in N independent processes; compare hashes of artifacts | Hash equality | planned |
| EXP-R3 | Different host environment | Run on a second OS/compiler/host where available; otherwise mark unverified | Hash equality or explicit `unverified` | planned |
| EXP-R4 | Serialization replay | Serialize → parse → materialize; compare with direct materialization | Byte equality | planned |
| EXP-R5 | Definition perturbation | Swap the definition for a modified one; expect E-DEF-001, not silent bytes | Error identity | planned |
| EXP-R6 | Negative determinism | Repeat an invalid plan; compare error identity (code+path+detail keys), ignoring `message` | Identity equality | planned |

EXP-R3 must not be claimed unless actually executed. "Not tested on a second
host" is the honest result.

## 3. Acceptance criteria (`AC-*`)

| ID | Requirement | Evidence form | Status |
|---|---|---|---|
| AC-01 | Contract complete enough to guide implementation | `01_contract.md` with no `TBD` on fields used by the three slices | in progress |
| AC-02 | Key fields justified | Each frozen field cites a counterexample or source evidence | in progress |
| AC-03 | Three-ISA vertical slices | One closed loop per ISA: plan → validate → encode → fixup → oracle compare | planned |
| AC-04 | Encoding ambiguity proven absent | x86 `imm8`/`imm32` and `rel8`/`rel32`; RV64 `c.*` vs standard, both explicit | planned |
| AC-05 | Fixups validated | x86 `rel32`; AArch64 `adrp`+`:lo12:`; RV64 `auipc`+`lo12` or B-type scatter | planned |
| AC-06 | Strict rejection | All applicable N01–N12 with recorded codes | planned |
| AC-07 | Deterministic replay | EXP-R1, EXP-R2, EXP-R4, EXP-R5 | planned |
| AC-08 | Reuse boundary backed by source evidence | `90_boundary_audit.md` with revision, file, symbol, line range | **done** for XirAsm; LLVM internals deferred (see audit §8) |
| AC-09 | Unresolved problems stated | `05_open_decisions.md` with blocking impact, no "later" hand-waving | in progress |
| AC-10 | Executable next step | Final report §H: modules, order, gates, blockers | planned |

## 4. Positive vectors

Each vector needs **two independent sources**: our materializer, and an oracle
(`llvm-mc` bytes, binutils, or a manual derivation recorded in
`research/evidence/experiments/`). The oracle's exact version must be recorded.

### x86-64 (directive §6.1)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| X86-P1 | Register-to-register transfer | `mov r64, r64` (`REX.W 89 /r`) | llvm-mc | planned |
| X86-P2 | Arithmetic with immediate | `add r64, imm32` and `add r64, imm8` as separate forms | llvm-mc | planned |
| X86-P3 | Same operation, different legal encodings | `add rax, 1` in `imm8` form; `mov eax, imm32` vs `C7 /0` | llvm-mc | planned |
| X86-P4 | Displacement width | `mov rax, [rbp-8]` (disp8) vs (disp32) | llvm-mc | planned |
| X86-P5 | Prefix rules | 16-bit operand with `0x66`; REX + high-byte rejection | llvm-mc | planned |
| X86-P6 | RIP-relative reference | `mov rax, [rip+disp32]` with a fixup | llvm-mc + readelf | planned |
| X86-P7 | Short vs near branch | `jmp rel8` and `jmp rel32` as explicit plans | llvm-mc | planned |
| X86-P8 | External call fixup | `call rel32` to an undefined symbol, record emitted | llvm-mc + readelf | planned |
| X86-P9 | Explicit encoding family | SSE vs VEX vs EVEX for one operation | llvm-mc | deferred (OD-10) |

### AArch64 (directive §6.2)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| A64-P1 | Register arithmetic | `add x0, x1, x2` (`shifted-register`) | llvm-mc | planned |
| A64-P2 | Immediate arithmetic | `add x0, x1, #imm12` and scaled variant | llvm-mc | planned |
| A64-P3 | Load/store addressing | unsigned-offset vs pre/post-index as distinct forms | llvm-mc | planned |
| A64-P4 | Conditional branch | `b.eq` imm19 | llvm-mc | planned |
| A64-P5 | Unconditional branch/call | `bl` imm26 | llvm-mc | planned |
| A64-P6 | PC-relative pair | `adrp` + `add #:lo12:` with `pair_group` | llvm-mc + readelf | planned |
| A64-P7 | Scattered/scaled field | ins/del of a scaled immediate, or `movz` shift | llvm-mc | planned |
| A64-P8 | Target-specific modifier | shift/extend modifier on a register operand | llvm-mc | planned |

### RV64 (directive §6.3)

| ID | Requirement | Candidate form | Oracle | Status |
|---|---|---|---|---|
| RV-P1 | Standard integer arithmetic | `add` (R-type) | llvm-mc | planned |
| RV-P2 | I-type immediate | `addi` imm12 | llvm-mc | planned |
| RV-P3 | Load/store | `ld`/`sd` base+offset | llvm-mc | planned |
| RV-P4 | Conditional branch | `beq` B-type scatter | llvm-mc | planned |
| RV-P5 | Control transfer | `jal` J-type scatter | llvm-mc | planned |
| RV-P6 | Scattered fields | B-type and J-type bit placement verified byte-for-byte | llvm-mc | planned |
| RV-P7 | Compressed vs standard | `c.addi` (2 bytes) vs `addi` (4 bytes), never chosen by the encoder | llvm-mc | planned |
| RV-P8 | Associated reference | `auipc`+`addi` pair with `hi20`/`lo12` | llvm-mc + readelf | planned |

## 5. Gate G3

G3 passes when each ISA has at least three positive vectors with matching oracle
bytes and two negative vectors with registry codes, all reproducible from a clean
checkout with the recorded toolchain versions.
