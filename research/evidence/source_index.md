# Source Evidence Index

Every technical claim in the contract set must trace to a pinned source and, when
behavior is claimed, to a reproducible experiment.

## Environment snapshot

Verified 2026-11-03 on the development host:

| Item | Value |
|---|---|
| Host OS | Windows (win32) |
| Repository | `C:\Users\hanni\Projects\MonAsm` |
| Remote | `git@github.com:Mr-enthalpy/MonAsm.git` (SSH) |
| Rust | 1.96.0, `stable-x86_64-pc-windows-msvc` |
| Installed Rust targets | `x86_64-pc-windows-msvc`, `x86_64-unknown-linux-gnu` |
| Visual Studio | 2022 |
| Python | 3.8 |
| Node.js | present |
| Zig | **0.17.0** (`C:\Users\hanni\Tools\zig\zig.exe`) |
| LLVM / clang / llvm-mc | **23.1.2** (`C:\Users\hanni\Tools\llvm\bin`) |
| GNU binutils | not installed (LLVM tools cover v0 needs) |
| WSL | executable present, **no distribution installed** |
| Network | GitHub SSH authenticated; HTTPS reachable with occasional TLS retries |

## Pinned sources

| Source | URL | Revision | Version | License | Retrieved | Use | Status |
|---|---|---|---|---|---|---|---|
| XirAsm | https://github.com/xir-kuku/XirAsm | `3ee8a439f5ba` (`main`) | repo `0.3.5` | Apache-2.0 | 2026-11-03 | Boundary audit, knowledge, oracle cross-check | **built and executed** 2026-11-03; snapshot in gitignored `research/external/XirAsm` |
| XirAsm-lib | same repo, `deps/xirasm-lib` | `3ee8a439f5ba` | `0.1.5` | Apache-2.0 | 2026-11-03 | Encoder audit; Zig `0.17.0` minimum | audited, not adopted (see `docs/fmp-v0/91_reuse_matrix.md`) |
| Arm MRS 2026-06 A-profile FAT | Arm download (account-gated); local drop `research/external/arm-mrs/` | `2026-06_rel`, build 818, schema 2.9.5 (declared in `_meta.version`) | 2026-06 | **Arm proprietary notice**: no reproduction without prior written permission; use/distribution bound to the recipient's Arm agreement | 2026-11-04 | Licence evidence for `OD-07` | read; **not redistributable as shipped**; `Instructions.json` not obtained (`EXP-0006`) |
| LLVM | https://github.com/llvm/llvm-project | `llvmorg-23.1.2` | 23.1.2 | Apache-2.0 WITH LLVM-exception | 2026-11-03 | Oracle, encoding knowledge | installed (`C:\Users\hanni\Tools\llvm`) |
| GNU binutils | — | not installed | — | GPL | — | Secondary oracle | deferred (LLVM tools cover v0) |

## Installed toolchain (gate G0)

Installed at user scope because this shell has no administrator rights. The
entries below are on the **user** `PATH`, so every new shell and every future
project inherits them without elevation.

| Tool | Version | Path | Verification |
|---|---|---|---|
| Zig | 0.17.0 | `C:\Users\hanni\Tools\zig\zig.exe` | `zig version` → `0.17.0` |
| LLVM | 23.1.2 | `C:\Users\hanni\Tools\llvm\bin\llvm-mc.exe` | `llvm-mc --version` → `LLVM version 23.1.2` |

Provenance:

```text
zig archive:  https://ziglang.org/download/0.17.0/zig-x86_64-windows-0.17.0.zip
              size 100268137
              sha256 b5663f69581dcf391293fbf16c06cb80d81d806545ce618b4d0bab7f0eb8c428 (verified)

llvm archive: https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.2/
              clang+llvm-23.1.2-x86_64-pc-windows-msvc.tar.zst
              size 276469918
              sha256 ceaee048142fece144752c6f6431cb0905a7a6160f78ab8cf5cf0b6216f99418 (recorded)
```

Extraction notes: `bsdtar` refused the zstd frame ("requires too much memory for
decoding"), so the archive was expanded with 7-Zip 24.09, which supports zstd.
The `winget` route was abandoned: `winget install zig.zig` produced no output and
timed out after 15 minutes, consistent with an elevation prompt in a
non-interactive shell.

Oracle smoke test (all three ISAs, 2026-11-03):

```text
mov rax, rbx   -> 48 89 d8        (x86-64, intel syntax, -show-encoding)
add x0, x1, x2 -> 20 00 02 8b     (aarch64)
addi a0, a1, 5 -> 13 85 55 00     (riscv64)
```

x86-64 requires `-x86-asm-syntax=intel` for Intel operand order; AT&T is the
default. Every oracle invocation must record this flag.

Verified in a freshly created process environment (`-UseNewEnvironment`), not just
in the installing shell: `llvm-mc --version` and `zig version` both resolve
through the user `PATH`. `llvm-mc` reports registered targets including
`aarch64`, `riscv64`, and `x86-64`.

XirAsm snapshots, if any, live in `research/external/` which is gitignored.
Reproducibility comes from the revision above, not from the snapshot.

## Directive integrity

`docs/fmp-v0/00_directive.md` is the immutable research directive. It is copied
verbatim and never edited. Any mismatch below is a defect.

```text
directive_sha256: 1fe928cae8e2191165559f4fcc053d8efaa270dac7fa5b54221635eb973cc173
```

Verified by `python tools/check_ids.py`.

## Evidence record format

```text
repository:   <url>
revision:     <sha or version>
file_path:    <path within repository>
symbol:       <function, type, or section>
line_range:   <start-end>
observed:     <what the code or experiment shows>
interpretation:<what we conclude>
confidence:   high | medium | low
basis:        source | experiment | documentation | inference | unverified
experiment:   <command or fixture, if any>
```

## Experiments

| ID | Question | Command | Result | Status |
|---|---|---|---|---|
| EV-01 | Does the library expose an AArch64 encoder? | repository tree listing | No `aarch64_encoder`; `xirasm_backend.zig:3-5` exports x86, riscv, spirv; zero `aarch64`/`arm64` references in library sources | observed (source) |
| EV-02 | Is the RISC-V API form-addressable? | read `riscv_encoder/api.zig` | Partly: `encodeRaw(request, spec)` accepts a pinned spec and `tables.instructions` is public, but spec identity is an index or `match/mask` | observed (source) |
| EV-03 | Can x86 relaxation be pinned? | read `x86_encoder/api.zig` + probes | Hint exists but only applies when the caller declares the target unknown; default auto-shortens (`jmp 0x10` → `eb 0e`) | observed (source + experiment) |
| EV-04 | Does XirAsm build with the available toolchain? | `zig build -Doptimize=ReleaseSafe` | Yes, exit 0; `xirasm.exe` 3,227,136 bytes | observed (experiment) |
| EV-05 | Can `llvm-mc` emit bytes for all three ISAs? | `llvm-mc -triple=... -show-encoding` | Yes; outputs recorded above | observed (experiment) |
| EV-06 | Does x86 auto-shorten branches? | `jmp 0x10`, `jmp 0x1000` | `eb 0e` then `e9 fb 0f 00 00`; the same mnemonic changes size with the target | observed (experiment) |
| EV-07 | Does an explicit `short` branch range-check? | `jmp short 0x82`, `jmp short 0x1000` | No: `eb 80` and `eb fe` — silently truncated | observed (experiment) |
| EV-08 | Does a label branch range-check? | `jmp short far_lbl` + 200 nops | Yes: rejected, "does not fit the signed 8-bit displacement" | observed (experiment) |
| EV-09 | Does RV64 auto-compress? | `addi a0,a0,1`, `nop` | No: 4 bytes each; `c.*` only when written | observed (experiment) |
| EV-10 | Does RV64 reject out-of-range values? | `addi ...,2048`, `beq ...,0x1008`, `c.j 0x800` | Yes, all rejected | observed (experiment) |
| EV-11 | Is AArch64 reachable without the macro include? | `--isa aarch64` + `add x0,x1,x2` | No: "instruction text emission is not supported for this target ISA" | observed (experiment) |
| EV-12 | Do duplicate RISC-V specs create ambiguity? | parse all 1,700 specs | No: 1,363 distinct names at xlen 64, zero duplicates per xlen | observed (experiment) |
| EV-13 | Where does AArch64 encoding knowledge originate? | `include/arm/a64/generated/latest/NOTICE`, `manifest.json` | Arm Architecture Machine Readable Specification 2026-06; 4,350 instructions, 292 aliases | observed (source) |
| EV-14 | What licence does the upstream MRS package declare? | read `Features.json` `_meta.license` and `docs/notice.html` | Proprietary notice: no reproduction without prior written permission; distribution bound to the recipient's Arm agreement. The BSD-3 text XirAsm reproduces is not in the upstream package | observed (source, `EXP-0006`) |
| EV-15 | Do XirAsm's manifest hashes identify the public MRS files? | hash the 2026-06 and 2026-09 `Features.json`; compare with `source_lock.files` | No: 2026-06 is `6d5c19e7…`, 2026-09 is `d4bc3952…`, manifest says `63325900…`; canonicalisation does not close the gap | observed (experiment, `EXP-0006`) |

Full commands and byte-level output: `experiments/EXP-0001-xirasm-boundary-probes.md`.
Findings and interpretations: `docs/fmp-v0/90_boundary_audit.md`.

## Known gaps

- LLVM was verified as an oracle only; no LLVM source has been read, so the
  `MCAssembler` vs `MCCodeEmitter` relaxation boundary stays `unverified`.
- The AArch64 licence question changed shape: the 2026-06 FAT package's own
  notice forbids reproduction without prior written permission and binds
  use/distribution to the recipient's Arm agreement. The BSD-3 text XirAsm
  reproduces was not found upstream, and its manifest file hashes do not match
  the public files (`EXP-0006`). The `Instructions.json` package was not
  downloaded, so its terms stay `unverified`. `ADR-0005` must be superseded
  before any AArch64 table is generated from MRS data.
- RISC-V relocation pairs (`auipc` + `lo12`) were not exercised; `AC-05` needs
  them in Phase 3.
- Cross-host determinism (EXP-R3) is untested and must stay marked `unverified`.
- The LLVM archive hash is recorded from the download, not cross-checked against
  an upstream digest (the `.jsonl` asset downloaded empty and the API request was
  rate-limited). Re-check when convenient.
