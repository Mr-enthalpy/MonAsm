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

### State (2026-11-10, llvm-mc 23.1.2)

`122/128 re-derived, 6 skipped, 0 failed`:

- 79 x86-64 records reproduce byte-identically, including the `ld.lld` one,
  `X86-P74` (which shares its input with `X86-P20`), the `X86-P75`-`X86-P80`
  widening vectors and the M6 vectors `X86-P81`-`X86-P84`.
- 26 AArch64 records reproduce: every `A64-P1`–`A64-P24` input resolves.
- 17 RV64 records reproduce: every `RV-P1`–`RV-P12` input resolves.
- 6 x86-64 records are `manual-derivation`: `X86-P1`, `X86-P4`, `X86-P5`,
  `X86-P9`, `X86-P10` and `X86-P83`. The expected bytes include an encoding
  `llvm-mc` will not select from a mnemonic (documented per record).

The 29 records that were `input-not-stored` on 2026-11-08 are resolved:

- Twenty inputs now hash to the value the record already carried, so nothing
  was re-pinned. Twelve are copied verbatim from fenced source listings in
  their experiment documents (`A64-P10`–`A64-P13`, `A64-P15`–`A64-P17`,
  `A64-P19`, `A64-P2-add-imm12-lsl12`, `A64-P3`, `A64-P4`, `RV-P3`); the other
  eight (`RV-P1`, `RV-P2`, `RV-P4`, `RV-P5`, `RV-P7`, `RV-P8-auipc-imm20`,
  `RV-P8-pcrel-pair`, `RV-P8-pcrel-pair-resolved`) were rebuilt from the
  recorded spellings and came out byte-identical.
- Nine AArch64 inputs (`A64-P1`, `A64-P2-add-imm12`, `A64-P5`, `A64-P6`,
  `A64-P7`, `A64-P8`, `A64-P9`, `A64-P14`, `A64-P18`) were rebuilt from the
  spellings in the experiment tables and the `*.oracle.json` notes, kept under
  `research/evidence/experiments/EXP-XXXX/`, and `input_sha256` was re-pinned to
  the rebuilt bytes. The original whitespace was not recorded, so those files
  cannot be byte-identical to what was hashed.
- In every case the recorded command reproduces the committed `expected.bin`,
  `output_sha256` and `size`; a rebuilt input therefore cannot be told apart by
  the bytes it produces. `A64-P14` and `A64-P18` are smaller than the byte
  counts their notes previously stated; the notes now record the rebuilt size
  and the recovery. The six `manual-derivation` records are the only reason
  `--strict` still exits 1.

A corrupted `expected.bin` fails the run (byte offset is printed) and exits `1`;
this was checked by flipping one byte of `X86-P6` and restoring it.
