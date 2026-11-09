# ADR-0124: the gates run in CI, and the oracle runs without a shell

- Status: accepted
- Date: 2026-11-10
- Settles: which checks are hosted as a gate, and how `rerun.py` executes a
  recorded command
- Supersedes: none
- Superseded by: none
- Revises: the `rerun.py` sections of `tools/oracle/README.md`; adds
  `.github/workflows/gates.yml`; adds the CI row to `06_validation_matrix.md`
  §3 (`AC-*`)

## Context

Two gate holes were left after M6 closed.

1. **The hosted CI ran the tests and nothing else.** `.github/workflows/determinism.yml`
   runs `cargo test --workspace` on three hosts, which covers `EXP-R1`–`EXP-R6`.
   It does not run `tools/check_ids.py` or `tools/check_definition.py`, does not
   check formatting, and does not run the oracle. Every one of those was a local
   habit, so a change could land with a duplicated `N*` ID, a definition whose
   reading-aid table drifted from its JSON, or a fixture whose recorded oracle
   bytes no longer reproduce — and the badge stayed green.
2. **The oracle harness executed a string from a data file through a shell.**
   `run_record` built `executable` by splicing the input basename into the
   `command` field of a `*.oracle.json` and called `subprocess.run(..., shell=True)`.
   The record is repository data that anyone can edit in a pull request, and
   `shell=True` gives it the full command language: `&&` chains beyond the
   intended stage, redirection, variable expansion, and any program on `PATH`.
   It also made the harness's behaviour depend on a shell's quoting rules rather
   than on argv, which is exactly the class of hidden input `INV-05` is about.
   The `&&` splitting the records already use was being interpreted by the
   shell, not by the harness, so the harness could not say which stage failed.

The rerun harness is also the only check that compares our bytes with an
independent authority on every push, which is what `AGENTS.md` hard rule 5
("two independent sources per positive vector") means in practice.

## Decision

1. **`.github/workflows/gates.yml` hosts the contract gates.** Three jobs, all on
   `ubuntu-24.04`:
   - `documents`: `python tools/check_ids.py`, `python tools/check_definition.py`,
     and `git diff --check <base> HEAD` on a full checkout, where the base is the
     event's pull-request merge base, else `github.event.before`, else `HEAD^`;
   - `workspace`: `rustup toolchain install 1.96.0 --profile minimal` plus
     `rustup component add rustfmt`, then `cargo +1.96.0 fmt --all -- --check`
     and `cargo +1.96.0 test --workspace` in `prototype/`;
   - `oracle`: install the `LLVM-23.1.2-Linux-X64.tar.zst` release asset, check
     its SHA-256 against the release attestation, verify `llvm-mc --version`
     reports `23.1.2`, then
     `python tools/oracle/rerun.py --allow-skip-reason manual-derivation`.
2. **A version mismatch is a failure, not a skip, and the install is exact.**
   The records pin `llvm-mc 23.1.2`; if the runner installs another minor, every
   record would become a `toolchain-version` skip and the gate would pass while
   checking nothing. The first hosted run showed why a channel install cannot
   satisfy this: `apt.llvm.org`'s `llvm-toolchain-noble-23` served `23.1.6`
   (`42677800026`). The job therefore downloads
   `LLVM-23.1.2-Linux-X64.tar.zst` from the `llvmorg-23.1.2` release, checks
   SHA-256 `6382de1c…b52534` (the digest the release's attestation names),
   extracts it, and greps the version first.
3. **`rerun.py` runs argv, never a shell.** A record's `command` is split on
   `&&` into stages, each stage is parsed with `shlex.split`, and every stage
   runs through `subprocess.run(argv, shell=False)`. The first failing stage is
   the one reported.
4. **The executable is an allowlist entry.** A stage's `argv[0]` basename must be
   one of `llvm-mc`, `llvm-objcopy`, `llvm-readobj`, `ld.lld`; anything else is a
   `command-shape` failure with reason `executable-not-allowed`. A record cannot
   ask the harness to run a program that is not one of the four oracles.
5. **A record written for a shell is refused, not reinterpreted.** A stage token
   containing `;`, `|`, `&`, `<`, `>`, `$` or a backtick is a `command-shape`
   failure. Running such a token as a literal argument would change the record's
   meaning silently (`INV-07`); the record must be rewritten as plain argv.
6. **Skips must be named.** `--allow-skip-reason REASON` keeps a skip a skip;
   any skip whose reason was not named is counted as a failure and exits 1.
   `--strict` still fails on *every* skip, including allowed ones. The
   `manual-derivation` reason is the only one the corpus needs, and CI passes
   exactly that.
7. **`check_mrs.py` and `check_rv64_source.py` stay local.** Both verify a
   *local* upstream drop under `research/external/`, which is gitignored, so a
   hosted runner has nothing to verify. Their subject is "the pinned source this
   definition was derived from", and that question only arises while a definition
   is being authored. What protects the shipped tables in CI is
   `check_definition.py` plus the `cargo test` fixture gate, both of which read
   the committed `definitions/` bytes.
8. **The whitespace gate diffs the range the event names.** The first hosted run
   failed with `fatal: ambiguous argument 'HEAD^'` because `actions/checkout` is
   shallow by default, so the comparison had no base. The `documents` job checks
   out `fetch-depth: 0` and resolves the base in this order: the pull request's
   merge base, `github.event.before`, `HEAD^`. A root commit has no earlier
   revision, so the step compares `HEAD` with itself and reports an empty range
   rather than failing on a missing object.

## Consequences

- A pull request that duplicates an ID, drifts a definition table, breaks
  formatting, or changes a byte the oracle disagrees with now fails a hosted
  check instead of a reviewer's memory.
- A malicious or careless `*.oracle.json` cannot run arbitrary commands, and a
  record that only worked under a shell fails loudly with `command-shape`
  instead of running with different arguments.
- `rerun.py` now reports a real stage failure (`command-failed`) with the failing
  stage's first stderr line; the previous shell run collapsed all stages into one
  exit code.
- The oracle job depends on a network download of a 1.2 GB LLVM 23.1.2 release
  asset on the runner, and on roughly 12 GB of temporary disk while it is
  decompressed (the archive's members total 11.55 GiB). That install is the one
  step this repository cannot verify offline; the workflow makes it loud (digest
  mismatch, download failure or version mismatch fails the job) rather than
  optional.
- The `workspace` job installs `rustfmt` explicitly. A `--profile minimal`
  toolchain has no `cargo-fmt`, which is how the first hosted run failed before
  it compiled anything.
- Local runs must pass `--allow-skip-reason manual-derivation` to exit 0 on the
  current corpus. That is deliberate: the six hand-derived records are the only
  reason the gate is not fully reproducible, and they are now visible in the
  invocation instead of in a default.

## Alternatives rejected

- **Use `--strict` in CI and backfill the six `manual-derivation` records.**
  Rejected: those six expected images contain an encoding `llvm-mc` will not
  select from the mnemonic (for example the `X86-P1` manual form). Writing
  assembler spellings that produce them would replace the record's meaning with
  a different derivation; the correct treatment is an explicit, named skip.
- **Keep `shell=True` and sanitise the record text.** Rejected: sanitising a
  shell string is a parser problem with no end, and it still leaves the harness
  depending on the local shell's quoting. `shlex` plus `shell=False` is the same
  records with no shell in the loop.
- **Allow any executable and check only the arguments.** Rejected: the
  allowlist is four names; the argument surface of a foreign program is unknown
  and unnecessary.
- **Run `check_mrs.py`/`check_rv64_source.py` in CI against a checked-in drop.**
  Rejected: the drops are third-party archives with licence terms that keep them
  out of the repository (`ADR-0006`, `ADR-0007`); committing them to satisfy CI
  would change the licence posture of the repository.
- **Add the gates to `determinism.yml`.** Rejected: that workflow's job is the
  cross-host determinism observation (`EXP-R3`); mixing a network-dependent
  oracle into it would make a determinism failure and an oracle failure
  indistinguishable.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `rerun.py` called `subprocess.run(..., shell=True)` with a command read from `*.oracle.json` | `47a383b` `tools/oracle/rerun.py` `run_record` | high |
| The corpus has 128 records, 127 distinct `command` strings (two records share one) and 6 `manual+disassembly` records | scan over `fixtures/*/positive/*.oracle.json` | high |
| The changed harness reproduces `122/128 re-derived, 6 skipped, 0 failed` with `--allow-skip-reason manual-derivation` | `python tools/oracle/rerun.py --allow-skip-reason manual-derivation` on this tree, exit 0 | high |
| Without the flag the same run exits 1 with six `skip-not-allowed` failures | the same command without the flag | high |
| A bare executable name containing a dot (`ld.lld`) is not found by `CreateProcess` under `shell=False`; the harness resolves every stage with `shutil.which` first | the first version of the change failed with `[WinError 2]` for the six `ld.lld` records until `argv[0]` was replaced with the resolved path; `llvm-mc` (no dot) was unaffected | high |
| A stage naming `rm` is refused with `executable-not-allowed`, and a stage containing `;` or `>` with `command-shape` | in-process calls to `parse_command` with hand-written records | high |
| The first hosted `gates` run (`42677800026`) failed three steps: `Formatting` (`'cargo-fmt' is not installed for the toolchain '1.96.0'`), `Whitespace and line endings` (`fatal: ambiguous argument 'HEAD^'`), and `Pin the toolchain the records name` (`Ubuntu LLVM version 23.1.6`) | `gh run view 42677800026 --log-failed` | high |
| `apt.llvm.org`'s noble `llvm-toolchain-noble-23` channel installs the newest 23.x, which was `23.1.6`, not the pinned `23.1.2` | the same log: the `llvm-mc --version` output printed by the failing step | high |
| The `llvmorg-23.1.2` release publishes `LLVM-23.1.2-Linux-X64.tar.zst`, and its attestation asset `LLVM-23.1.2-Linux-X64.tar.zst.jsonl` names SHA-256 `6382de1c1a210ce5a5cc49d18bc8444d137742e7cbf9b19f4ae602bb1ab52534` for it | `gh release download llvmorg-23.1.2 -p LLVM-23.1.2-Linux-X64.tar.zst.jsonl`, then the decoded DSSE payload's `subject[1].digest.sha256`; the Sigstore signature itself was not verified here, but the downloaded asset hashes to the same digest (`Get-FileHash -Algorithm SHA256`) | high |
| That asset contains `bin/llvm-mc`, `bin/llvm-objcopy`, `bin/llvm-readobj`, `bin/lld` and the symlink `bin/ld.lld`, and has no shared `libLLVM.so` because the tools are statically linked | the archive listing of the downloaded asset: 11,465 members; `bin/llvm-mc` 57,767,024 B, `bin/llvm-objcopy` 9,288,624 B, `bin/llvm-readobj` 13,106,960 B, `bin/lld` 213,649,712 B, `bin/ld.lld` size 0; only `lib/libLLVM*.a` exists | high |
| The asset is a zstd frame with a 1 GiB window, so a default `zstd -d` refuses it ("Frame requires too much memory for decoding") and the install passes `--long=31` | `zstandard.get_frame_parameters(...).window_size == 1073741824` on this asset; the first decode attempt without a raised window limit failed with that message | high |

## Review triggers

- The `oracle` job's digest check fails: the release asset was replaced or
  removed, and the install recipe (or the pinned version) needs re-deciding.
  This trigger replaced the "first run fails" one after `42677800026` showed
  that the `apt.llvm.org` channel cannot hold a point release.
- A seventh `manual-derivation` record is added, or one of the six is resolved;
  the CI invocation's `--allow-skip-reason` list is part of the gate and changes
  with it.
- A new oracle tool is needed (for example `llvm-objdump`); it must be added to
  `ALLOWED_EXECUTABLES` in the same change that records it.
- A check becomes cheap enough to run on every push that is not in `gates.yml`
  today; adding a job is a change to this decision, not a workflow-only edit.
