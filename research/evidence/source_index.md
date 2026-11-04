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
| Arm MRS 2026-06 OPENSOURCE A-profile FAT (**pinned**) | Arm download; archive `AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz`, local drop `research/external/arm-mrs/` | archive `sha256:fe458c52…`; `Instructions.json` `a1ad2c65…`; `Features.json` `63325900…`; release `2026-06_rel`, build 818, schema 2.9.5 | 2026-06 | **BSD-3-Clause**: `_meta.license.info` = "licensed under the BSD 3-clause license"; `docs/notice.html` = three conditions + disclaimer | 2026-11-04 | Source of `definitions/aarch64/`; notice ships beside the table | read; hashes match XirAsm's manifest exactly; gate is `python tools/check_mrs.py` (`EXP-0007`, ADR-0006) |
| Arm MRS 2026-06 A-profile FAT (**rejected**) | same release, different packaging, `AARCHMRS_A_profile_FAT-2026-06` | `Features.json` only, `1590274` B, `sha256:6d5c19e7…` | 2026-06 | **Arm proprietary notice**: no reproduction without prior written permission; use/distribution bound to the recipient's Arm agreement | 2026-11-04 | Licence evidence for `OD-07` | **not usable**: fails the hash and licence gate (`EXP-0006`, ADR-0006) |
| Arm A64 ISA, `ADD (immediate)` and `B.cond` (**revision-pinned, citation-only**) | Arm `DDI0602` instruction pages, read at the public mirror `https://www.scs.stanford.edu/~zyedidia/arm64/add_addsub_imm.html` and `.../b_cond.html` | revision `2026-03_rel` (2026-03-26) in both page footers; no local file, not hashed | 2026-03 | **© Arm Limited, "Non-Confidential"**: facts and references only, no passage reproduced into `docs/` | 2026-11-04 | The normative statements behind `A64-P2`'s `-lsl12` half (`<imm>` is 0–4095 in `imm12`, `sh` selects `LSL #0`/`LSL #12`, ADR-0011) and behind `A64-P4` (`<cond>` is one of sixteen standard conditions encoded in the 4-bit `cond`, `<label>` is a ±1 MB PC-relative offset encoded as `imm19` × 4, ADR-0012) | read; `EXP-0013` §1 and `EXP-0014` §1 restate the statements each page gives (`EV-27`) |
| RISC-V UDB resolved spec (**pinned**) | `resolved_spec` export of https://github.com/riscv/riscv-unified-db, local drop `research/external/rv64-udb/` | archive `sha256:be184986…` (`2694443` B); 8 nodes hashed in `EXP-0009` §4; upstream repo commit **`cadd46e22487a2002cead3883b34e72766103cdf`** (2026-10-31), agreed by `EV-24` and **not asserted by the archive**, whose `.stamp` is still empty | no revision embedded | **BSD-3-Clause-Clear**, per-file SPDX header; text `sha256:e3f4d72a…` (1,700 B, UDB `LICENSE-BSD-3-Clause-Clear.txt`) | 2026-11-04 | Source of `definitions/rv64/0.1.0.json` (seven base-`I` forms) and `0.2.0.json` (the same seven plus `riscv:c.addi/rd-imm6`); notice ships beside the tables | read; the generator's 16 probe vectors match `llvm-mc` and nine positive / eleven negative fixtures gate the generated tables; gates are `python tools/check_rv64_source.py` and `python tools/check_definition.py` (`EXP-0009`, `EXP-0010`, `EXP-0012`, `EXP-0011`, ADR-0007, ADR-0009). `EV-24` binds the nodes to the commit by source-map geometry |
| RISC-V ELF psABI (**pinned**) | https://github.com/riscv-non-isa/riscv-elf-psabi-doc | tag `v2.0-rc0` = `04c0eb8a1a83edc81b20f1fd919e773960354b3e`, which is also tagged `draft-20261008-04c0eb8a…`; 2026-10-08; `riscv-elf.adoc` `sha256:3d65a2ce…` (115,951 B) | adoc sources, no release number | **CC-BY-4.0**: `LICENSE` `sha256:1a7ddeb1…` (19,046 B); attribution required | 2026-11-04 | Normative `R_RISCV_PCREL_HI20` / `_LO12_I` / `_LO12_S` pairing (ADR-0010) | read `riscv-elf.adoc` §"PC-Relative Symbol Addresses" (`:1570-1605`), relocation rows `:1184`/`:1186`, linker note `:2495-2509`; clone at `research/external/architecture-knowledge/riscv-elf-psabi-doc`, not redistributed (`EV-22`) |
| Arm AAELF64, via `abi-aa` (**pinned, unread**) | https://github.com/ARM-software/abi-aa | `a1b53459479e88f3492ca9b11a161313764ab138` (`git describe` → `2026Q3`), 2026-11-02; `aaelf64/aaelf64.rst` `sha256:f2342b4b…` (156,341 B) | 2026Q3 | **CC-BY-SA-4.0**: `aaelf64/LICENSE` `sha256:4d066ca5…` (1,334 B); cite it, do not paste its passages | 2026-11-04 | Candidate source for AArch64 relocation semantics (`A64-P2` `-lsl12`, `A64-P3`/`P7`/`P8`) | **cloned, body not read**; licence read from `LICENSE.md` and `aaelf64/LICENSE` (`EV-25`) |
| ELF x86-64 psABI | https://gitlab.com/x86-psABIs/x86-64-ABI | `e1ce098331da5dbd66e1ffc74162380bcc213236`, 2025-03-12 | — | **CC-BY-4.0**, declared inside the document at `abi.tex:31-32`; the tree carries **no** `LICENSE` file | 2026-11-04 | Candidate source for x86 ModRM/SIB and relocation rules (`X86-P4`/`P6`) | **cloned, body not read**; `object-files.tex` `sha256:6d28e669…` (32,309 B), `low-level-sys-info.tex` `sha256:a9a6bddf…` (107,786 B) |
| Intel SDM, combined Vol 1 + 2A-2D + 3A-3D + 4 (**pinned, citation-only**) | local drop `C:\Users\hanni\Downloads\325462-093-sdm-vol-1-2abcd-3abcd-4.pdf`, from Intel's developer manual page | order number `253665-093US`, September 2026; `sha256:a4a62e6a…` (26,664,929 B; 5,364 pages) | revision 093 | **no licence granted**: p.2 allows "publish an unmodified copy" and 0BSD for sample code, and states "No rights are granted to create modifications or derivatives of this document" | 2026-11-04 | Reference for x86 encoding *rules* (Vol 2 ModRM/SIB, opcode maps) | **pinned by hash; front matter read (pp.2-3), body not read** (`EV-23`). Not redistributed and not reproduced: we use facts and section references, never copied text |
| RISC-V ISA manual | https://github.com/riscv/riscv-isa-manual | `418bdc4990ae2d60a86f1e11e8d7795aa279da61`, 2026-11-02 | — | **CC-BY-4.0** (`src/license.adoc`, which also fixes the citation format) | 2026-11-04 | Optional normative cross-check for HINT semantics behind `c.addi`'s `excluded 0` (`EC-19`, `OD-14`) | **cloned, body not read**; chapters live in `src/unpriv/` and `src/priv/`, not `src/*.adoc` |
| intelxed/xed | https://github.com/intelxed/xed | `0bcb6237345c5066726dcc08b3d87928df3b5b26`, 2026-08-24 | — | **Apache-2.0**: `LICENSE` `sha256:6f3ca222…` (10,205 B) | 2026-11-04 | Permissive x86 opcode-table cross-check, the role riscv-opcodes plays for RV64 | **cloned, not read**; opcode data under `datafiles/` |
| riscv-opcodes (**cross-check**) | https://github.com/riscv/riscv-opcodes | `f24ac23ec9fa947011781a09cd6fd25a7c36dc45`, 2026-10-14 | `main` | BSD-3-Clause (`LICENSE` `sha256:ea19b748…`) | 2026-11-04 | Upstream cross-check for RV64 fixed bits, register ranges, and the `EC-19`/`EC-20` claims | read; **not a source of the table**: it gives field ranges but no B/J/RVC value-bit scatter (`EXP-0009` §7) |
| LLVM | https://github.com/llvm/llvm-project | `llvmorg-23.1.2` | 23.1.2 | Apache-2.0 WITH LLVM-exception | 2026-11-03 | Oracle, encoding knowledge | installed (`C:\Users\hanni\Tools\llvm`) |
| GNU binutils | — | not installed | — | GPL | — | Secondary oracle | deferred (LLVM tools cover v0) |

PDF reading harness: `research/external/pdfpeek.py` (pypdf 5.9.0) prints document
metadata, a bounded page range, or the lines matching a term. It exists so the
5,364-page SDM never enters a context window. pypdf is a research-only
convenience: no gate imports it, and the Python gates stay stdlib-only.

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
| EV-09 | Does RV64 auto-compress in XirAsm? | `addi a0,a0,1`, `nop` | No: 4 bytes each; `c.*` only when written. This is XirAsm's behaviour; `llvm-mc` with `-mattr=+c` does compress `addi a0,a0,1` (`EXP-0012` §2.2) | observed (experiment) |
| EV-10 | Does RV64 reject out-of-range values? | `addi ...,2048`, `beq ...,0x1008`, `c.j 0x800` | Yes, all rejected | observed (experiment) |
| EV-11 | Is AArch64 reachable without the macro include? | `--isa aarch64` + `add x0,x1,x2` | No: "instruction text emission is not supported for this target ISA" | observed (experiment) |
| EV-12 | Do duplicate RISC-V specs create ambiguity? | parse all 1,700 specs | No: 1,363 distinct names at xlen 64, zero duplicates per xlen | observed (experiment) |
| EV-13 | Where does AArch64 encoding knowledge originate? | `include/arm/a64/generated/latest/NOTICE`, `manifest.json` | Arm Architecture Machine Readable Specification 2026-06; 4,350 instructions, 292 aliases | observed (source) |
| EV-14 | What licence does the upstream MRS package declare? | read `_meta.license` and `docs/notice.html` in both measured archives | Two answers, because there are two packagings: the OPENSOURCE archive declares BSD-3-Clause (per-file and in the notice); the other `AARCHMRS_A_profile_FAT-2026-06` archive forbids reproduction without prior written permission | observed (source, `EXP-0006`, `EXP-0007`) |
| EV-15 | Do XirAsm's manifest hashes identify a public MRS drop? | hash both archives' files; compare with `source_lock.files` | Yes for the OPENSOURCE packaging — `a1ad2c65…` and `63325900…` match byte for byte. No for the other packaging (`6d5c19e7…`) nor for 2026-09 (`d4bc3952…`) | observed (experiment, `EXP-0007`) |
| EV-16 | Does the release block distinguish the two packagings? | compare `_meta.version` of both archives | No: both declare `vFATAp1-A`/818/`2026-06_rel`/2.9.5. A pin that names only the release accepts the non-redistributable archive | observed (experiment, `EXP-0007` §3) |
| EV-17 | Does riscv-opcodes state the B/J/RVC immediate scatter? | read `arg_lut.csv`, `extensions/rv_i`, `extensions/rv_c` at `f24ac23e…` | No: it gives ranges (`bimm12hi 31..25`, `bimm12lo 11..7`, `jimm20 31..12`) and field names, but never which value bits go where | observed (source, `EXP-0009` §7) |
| EV-18 | Does the UDB resolved spec state field positions and scaling? | read `inst/I/{beq,jal,auipc,add,addi,ld,sd}.yaml`, `inst/C/c.addi.yaml` | Yes: `location` is a value-order bit-group list (e.g. `beq`: `"31|7|30-25|11-8"`), with `left_shift`, `sign_extend`, `not`; 14 vectors encoded from it match `llvm-mc` byte for byte | observed (experiment, `EXP-0009` §4–§6) |
| EV-19 | Does a table derived from `location` reproduce `llvm-mc` through the materializer? | build `definitions/rv64/0.1.0.json` and `0.2.0.json` from eight nodes, then `cargo test --workspace` | Yes: seven positive fixtures match `llvm-mc 23.1.2` bytes and eight negatives produce exactly the registered diagnostics; the generator refuses a form whose bits are not covered once | observed (experiment, `EXP-0010`) |
| EV-20 | Is a memory operand one field or several? | `llvm-mc -show-encoding` for x86 `movq` disp8/disp32/`[rbp]`, AArch64 `ldr x0,[x1,#16]`, RV64 `ld`/`sd` ±2047; read the `RV64` block of `inst/I/{ld,sd}.yaml` | Several: RV64 spans `xs1`/`imm`/`xd`; x86 changes form with the value (`48 8b 41 08` vs `48 8b 81 00 10 00 00`, `[rbp]` → `48 8b 45 00`); AArch64's `imm12` is scaled (`#16` → `2`) | observed (experiment, `EXP-0011`) |
| EV-21 | Does an in-range zero in `c.addi` still encode the operation the plan names? | `llvm-mc -triple=riscv64 -mattr=+c` on `c.addi a0, 0`, `c.addi x0, 1`, `c.addi x0, 0`; decode with `llvm-objdump` | No: `01 05` is `c.addi a0, 0x0` (a HINT), `05 00` is `c.nop 0x1`, `01 00` is `nop`. Both zeroes are inside the declared ranges, so the rejection needs a slot-level rule; the `x8..x15` class belongs to `c.lw`, not `c.addi` (`c.addi a6, 5` → `15 08` is accepted) | observed (experiment, `EXP-0012` §2) |
| EV-22 | Does the psABI state the HI20/LO12 pairing normatively, or only by example? | read `riscv-elf.adoc` at `v2.0-rc0` | Normatively: `PCREL_HI20` is "High 20 bits of 32-bit PC-relative reference"; `PCREL_LO12_I`/`_S` are "Low 12 bits … `%pcrel_lo(address of %pcrel_hi)`, the addend must be 0" (`:1184`, `:1186`); the low half's symbol is a label at the `auipc`, one `hi` may serve several `lo`s, and they need not be adjacent (`:1574-1605`) | observed (source) |
| EV-23 | What does the Intel SDM permit, and what does that change about how we use it? | read p.2 "Notices & Disclaimers" and p.3 of `325462-093` | The only grants are "publish an unmodified copy" and 0BSD for code marked as sample; the page also disclaims rights to "create modifications or derivatives". Encoding facts are not the licensed subject matter, so we read the manual for facts and section numbers and never reproduce its text | observed (source) |
| EV-24 | Does the revision-less UDB archive agree with an upstream commit? | `python tools/udb_binding.py` compares each node's `SOURCE MAP` `key -> file:line:column` against the repo tree at `cadd46e2` | All 231 recorded positions land: 199 direct (key token on the recorded line) and 32 indexed (a list element's index resolves to its parent key). Zero unexplained. No drift, but the archive still does not name a commit, so this is agreement, not provenance | observed (experiment) |
| EV-25 | What licence do the AArch64 ABI documents carry? | read `abi-aa/LICENSE.md`, `abi-aa/aaelf64/LICENSE`, and the AAELF64 directory listing | CC-BY-SA-4.0 plus a patent grant, **per directory**: `LICENSE.md` says each ABI document "ha[s its] own license file included in the directory", and the legacy folder is Arm-proprietary. We restate facts and cite the section; passages are not pasted into `docs/` | observed (source) |
| EV-26 | Does an assembler pick the AArch64 `add`-immediate form from the literal's value? | `llvm-mc` on `#0xfff`, `#0x1000`, `#0x1ffc`, `#0x1001`, `#0xfff000`, `#0x1000000` and the explicit `lsl #12` spellings; `llvm-objdump` on the words | Yes: `#0x1000` becomes `sh = 1, imm12 = 1` while `#0xfff` stays `sh = 0`. With explicit `lsl #12` the operand is field content in `[0, 4095]`; `0x1ffc`, `0x1001` and `0x1000000` are rejected rather than rounded. The representable set is `[0,4095] ∪ {k<<12}`. A materializer must not imitate the silent choice (`INV-02`) | observed (experiment, `EXP-0013` §2) |
| EV-27 | Is the `B.cond` condition a separate instruction per condition, and what does the assembler accept for the label? | Arm A64 ISA `B.cond` page at `2026-03_rel`; `llvm-mc` on all sixteen `b.<cond> .+4` spellings and on the boundary offsets `+1048572`, `+1048576`, `-1048576`, `-1048580`, `-4`, `0` | The page defines one instruction whose 4-bit `cond` takes sixteen encoded values (including `AL` = 1110 and `NV` = 1111) and whose `imm19` is the label offset divided by 4; all sixteen assemble, differing only in bits 0–3 (`b.al` → `0x5400002e`), and the reachable byte range is `-1048576 … +1048572` because `+1048576` is out of `imm19`. So the condition is an operand, not a form variant (`EC-29`, ADR-0012) | observed (source + experiment, `EXP-0014` §1–§3) |

Full commands and byte-level output: `experiments/EXP-0001-xirasm-boundary-probes.md`.
Findings and interpretations: `docs/fmp-v0/90_boundary_audit.md`.

## Known gaps

- LLVM was verified as an oracle only; no LLVM source has been read, so the
  `MCAssembler` vs `MCCodeEmitter` relaxation boundary stays `unverified`.
- The AArch64 licence question has two answers, one per packaging. The pinned
  archive (`AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz`, `fe458c52…`) is
  BSD-3-Clause and matches XirAsm's manifest hashes; the other 2026-06 FAT
  package forbids reproduction without Arm's prior written permission
  (`EXP-0006`, `EXP-0007`). Only the pinned archive may feed
  `definitions/aarch64/`, and ADR-0006 makes the archive hash, both file hashes
  and the licence string the gate. Unverified: the `schema/` tree hash XirAsm
  records, and whether an embedded (non-JSON) table satisfies notice condition 2.
- RISC-V relocation pairs (`auipc` + `lo12`) are not yet exercised end to end, but
  the *source* gap is closed: the psABI is pinned (`v2.0-rc0`, `04c0eb8a…`) and
  states the HI20 value, the "the low half names the address of the `%pcrel_hi`"
  rule, the zero-addend rule, and that one `hi` may serve several `lo`s (`EV-22`).
  What `RV-P8` still needs is a format decision (ADR-0010) and a fixture, not
  more evidence.
- The UDB resolved-spec archive records no revision of its own: `.stamp` is empty
  and `$source` names only a CI workspace. `EV-24` narrows this without closing
  it: all 231 recorded source-map positions land on the upstream tree at commit
  `cadd46e2` (2026-10-31), 199 directly and 32 through their parent key. The pin
  is therefore "archive hash plus this agreement check", which rules out drift on
  the eight nodes but does not prove the archive was generated from that commit.
  The check is `python tools/udb_binding.py`; it is not a gate because it needs
  both disposable drops.
- The x86 slice has no pinned *encoder* source in use: the SDM is pinned and its
  facts may be used, but its text is not reproduced, and `xed` (Apache-2.0) is
  cloned and unread. Either can supply `X86-P4`/`P6`; neither has been read yet.
  The x86-64 psABI is CC-BY-4.0 but declares that inside `abi.tex` rather than in
  a `LICENSE` file, so a licence gate must read the document, not the file list.
- AAELF64 is cloned but unread. Its CC-BY-SA-4.0 terms attach to the document's
  text, so state the facts in our own words and cite the section; do not paste
  passages into `docs/`.
- `c.addi` is admitted through a slot-level `excluded` list (ADR-0009, `OD-14`):
  the two zeroes are in range and are rejected only because the form excludes
  them (`EXP-0012`). The same construct's 16-value Zilsd list is read from the
  `RV32` block of `ld.yaml` but is not exercised end to end, because v0 is RV64.
- Cross-host determinism (EXP-R3) is untested and must stay marked `unverified`.
- The LLVM archive hash is recorded from the download, not cross-checked against
  an upstream digest (the `.jsonl` asset downloaded empty and the API request was
  rate-limited). Re-check when convenient.
