# Oracle tools

Temporary. **Disposable zone** (ADR-0001): deleting this directory must not
break the product build.

## Purpose

Wrap independent authorities used to check our bytes:

- `llvm-mc` — primary oracle for x86-64, AArch64, RV64 encoding.
- `llvm-objdump` / `readelf` — relocation record checks.
- GNU `as` / `objdump` — secondary opinion when the first two agree and we want
  a third.

## Rules

- Oracles produce `*.expected.bin` and `*.oracle.json`; the materializer never
  produces expected data.
- Every record pins the exact version and command line.
- Nothing in `prototype/` may reference this directory.
- Scratch output goes to `out/` or `tmp/`, both gitignored.

## State

LLVM 23.1.2 is installed at `C:\Users\hanni\Tools\llvm\bin` and on the user
`PATH` (gate G0 passed). Wrappers are added per fixture in Phase 3.

Canonical invocation for the oracle records:

```bash
# x86-64: Intel operand order is explicit
llvm-mc -triple=x86_64 -x86-asm-syntax=intel -show-encoding

# AArch64
llvm-mc -triple=aarch64 -show-encoding

# RV64
llvm-mc -triple=riscv64 -show-encoding
```

## Rerun harness (`rerun.py`)

`python tools/oracle/rerun.py` re-derives the bytes for every positive fixture
whose assembler input is still in the tree, and reports the ones that are not.

**Input resolution is by content, not by name.** The harness hashes every
`*.s`/`*.asm` under `research/evidence/experiments/` and matches the
`input_sha256` in each `*.oracle.json`. A hash match proves the bytes are the
ones the record was made from; a name match proves nothing. When several files
share a hash (identical copies) the lexicographically first relative path wins,
so the run is deterministic (`INV-05`).

For a resolved record the harness copies the input into a temporary directory
under the basename the recorded command names, runs that command verbatim, and
compares the produced image with `*.expected.bin`, `output_sha256` and `size`.
The `records` field (relocation count) is not re-checked; the byte image and the
lookup hash are.

| Status | Meaning |
|---|---|
| `PASS` | Resolved input, command succeeded, bytes and hashes agree |
| `SKIP` | The record cannot be reproduced on this host; a reason is printed |
| `FAIL` | A resolved record produced different bytes, or its command failed |

Skip reasons are stable prefixes: `manual-derivation` (the expected bytes are
not the assembler output), `input-not-stored` (no file in the evidence tree
hashes to `input_sha256`), `toolchain-version` (installed `llvm-mc` differs from
the pinned `version`), `tool-missing` (e.g. `ld.lld` absent).

Exit codes: `0` when every resolved record passes, `1` on any `FAIL`, `2` when
`llvm-mc`/`llvm-objcopy` is unavailable or a record cannot be parsed. `--strict`
turns a `SKIP` into a failure; that is the gate to use once the missing inputs
are backfilled. The summary always prints `<pass>/<total> re-derived,
<skip> skipped`, so a partial run is never reported as a clean corpus.

### State (2026-11-08, llvm-mc 23.1.2)

`80/114 re-derived, 34 skipped, 0 failed`:

- 70 x86-64 records reproduce byte-identically, including the `ld.lld` one and
  `X86-P74`, which shares its input with `X86-P20`.
- 6 RV64 records reproduce: the committed `jal`, `pcrel_hi`/`pcrel_lo12`, `lui`
  and `jalr` inputs. 9 RV64 records are `input-not-stored`.
- 4 AArch64 records reproduce: the committed `A64-P21` (two inputs) and
  `A64-P22` inputs; the other 20 are `input-not-stored`.
- 5 x86-64 records are `manual-derivation`: the expected bytes include an
  encoding `llvm-mc` will not select from a mnemonic (documented per record).

The 29 `input-not-stored` records are exactly the 20 AArch64 and 9 RV64 records
whose inputs were never committed; the recorded `input_sha256` matches no file
in the evidence tree, so the harness refuses to treat them as verified.

A corrupted `expected.bin` fails the run (byte offset is printed) and exits `1`;
this was checked by flipping one byte of `X86-P6` and restoring it.
