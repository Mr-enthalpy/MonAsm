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
| XirAsm | https://github.com/xir-kuku/XirAsm | `3ee8a439f5ba` (`main`) | repo `0.3.5` | Apache-2.0 | 2026-11-03 | Boundary audit, knowledge, test ideas | read-only, not built |
| XirAsm-lib | same repo, `deps/xirasm-lib` | `3ee8a439f5ba` | `0.1.5` | Apache-2.0 | 2026-11-03 | Encoder audit; Zig `0.17.0` minimum | not built |
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
| EV-01 | Does the library expose an AArch64 encoder? | repository tree listing | No `aarch64_encoder`; `xirasm_backend.zig:3-5` exports x86, riscv, spirv | observed (source) |
| EV-02 | Is the RISC-V API form-addressable? | read `riscv_encoder/api.zig` | No: mnemonic + operands, internal table lookup | observed (source) |
| EV-03 | Can x86 relaxation be pinned? | read `x86_encoder/api.zig` | There is a hint field; default `null` leaves the decision inside | inference; needs experiment |
| EV-04 | Does XirAsm build with the available toolchain? | — | Zig 0.17.0 now installed; build not yet attempted | **pending** |
| EV-05 | Can `llvm-mc` emit bytes for all three ISAs? | `llvm-mc -triple=... -show-encoding` | Yes; outputs recorded above | observed (experiment) |

## Known gaps

- XirAsm has not been built or executed yet; all behavior claims are source
  reading.
- No AArch64 encoding source has been selected yet (OD-07).
- Cross-host determinism (EXP-R3) is untested and must stay marked `unverified`.
- LLVM was verified as an oracle only; no LLVM code has been read in depth yet.
- The LLVM archive hash is recorded from the download, not cross-checked against
  an upstream digest (the `.jsonl` asset downloaded empty and the API request was
  rate-limited). Re-check when convenient.
