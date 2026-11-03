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
| Zig | **not installed** |
| LLVM / clang / llvm-mc | **not installed** |
| GNU binutils | **not installed** |
| WSL | executable present, **no distribution installed** |
| Network | GitHub SSH authenticated; HTTPS reachable with occasional TLS retries |

## Pinned sources

| Source | URL | Revision | Version | License | Retrieved | Use | Status |
|---|---|---|---|---|---|---|---|
| XirAsm | https://github.com/xir-kuku/XirAsm | `3ee8a439f5ba` (`main`) | repo `0.3.5` | Apache-2.0 | 2026-11-03 | Boundary audit, knowledge, test ideas | read-only, not built |
| XirAsm-lib | same repo, `deps/xirasm-lib` | `3ee8a439f5ba` | `0.1.5` | Apache-2.0 | 2026-11-03 | Encoder audit; Zig `0.17.0` minimum | not built |
| LLVM | https://github.com/llvm/llvm-project | TBD | TBD | Apache-2.0 WITH LLVM-exception | — | Oracle, encoding knowledge | **pending gate G0** |
| GNU binutils | — | TBD | TBD | GPL | — | Secondary oracle | pending |

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
| EV-04 | Does XirAsm build with the available toolchain? | — | Zig 0.17 missing | **not run** |

## Known gaps

- LLVM is not installed, so no oracle bytes exist yet and gate G0 is blocked.
- XirAsm has not been built or executed; all behavior claims are source reading.
- No AArch64 encoding source has been selected yet (OD-07).
- Cross-host determinism (EXP-R3) is untested and must stay marked `unverified`.
