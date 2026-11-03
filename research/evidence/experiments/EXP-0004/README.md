# EXP-0004 — the x86-64 v0 definition table, verified by an independent decoder

- Date: 2026-11-04
- Subject: `definitions/x86_64/0.1.0.json` and `OD-06`'s two digest cases
- Toolchain: LLVM 23.1.2 (`llvm-mc -disassemble`), Python 3.8
- Basis: **experiment** for every byte and every digest below
- Reproduce: `python exp0004.py` in this directory

## 1. Why this is not a self-check

The table under test says where each operand's bits go. If the same code that
writes the bytes also decides what the bytes mean, a wrong table passes happily.
So the check uses two implementations that cannot share a bug:

1. `exp0004.py` implements `07_definition_format.md` §4.1 independently of the
   Rust materializer: it reads the table, applies the placement rule, and emits
   bytes.
2. `llvm-mc -disassemble` reads those bytes back and prints the operands.

The expected text comes from the case's **inputs**, never from the encoder. A
decoder disagreement is a table defect, not a formatting detail.

Coverage: every `form_id` in the table, and every value the field can hold where
that is affordable — all 64 register pairs for the two `mov` forms, all eight
destination registers for the `add` immediate forms, and the four extremes of
each immediate and displacement range.

## 2. Measured

<!-- forms-table:start -->
| `form_id` | cases | pass | sample plan | sample bytes | decodes as |
|---|---|---|---|---|---|
| `x86:mov/rm-r64/legacy` | 64 | 64 | `[0, 0]` | `4889c0` | `movq %rax, %rax` |
| `x86:mov/r64-rm/legacy` | 64 | 64 | `[0, 0]` | `488bc0` | `movq %rax, %rax` |
| `x86:add/rm64-imm8/legacy` | 40 | 40 | `[0, -128]` | `4883c080` | `addq $-128, %rax` |
| `x86:add/rm64-imm32/legacy` | 40 | 40 | `[0, -2147483648]` | `4881c000000080` | `addq $-2147483648, %rax` |
| `x86:add/rax-imm32/legacy` | 5 | 5 | `[-2147483648]` | `480500000080` | `addq $-2147483648, %rax` |
| `x86:jmp/rel8/legacy` | 5 | 5 | `[-128]` | `eb80` | `jmp -128` |
| `x86:jmp/rel32/legacy` | 5 | 5 | `[-2147483648]` | `e900000080` | `jmp -2147483648` |
<!-- forms-table:end -->

Two rows deserve a note, because `llvm-mc` will not emit them from assembly text:

- `x86:mov/r64-rm/legacy` (`REX.W 8B /r`): assembling `mov rax, rbx` produces
  `48 89 d8`, the `89` form. The `8B` row is reached only by decoding
  (`EXP-0003` measured `48 8b c3` → `movq %rbx, %rax`). It is in the table
  because `X86-P1`/`X86-P3` require both directions as distinct forms
  (`EC-27`), and a plan that wants `8B` must be able to say so.
- `x86:add/rm64-imm32/legacy` (`REX.W 81 /0 id`): assembling `add rax, 300`
  produces `48 05 2c 01 00 00`, the accumulator form (`EC-04`). `81 /0` has no
  mnemonic spelling in `llvm-mc`; it is reachable by decoding, which is what
  this experiment does for all 40 of its cases.

## 3. The register-number bound

The table's `ModRM` register fields are 3 bits wide and the `REX` byte is fixed
at `0x48`, so`r8`–`r15` are not encodable in v0. That is a bound, not a detail:
truncating `r9` (9 = `0b1001`) to 3 bits yields `0b001`, and the measured bytes
`48 89 c8` decode as `movq %rcx, %rax`. A plan that names `mov rax, r9` is
therefore rejected `E-OPERAND-004` rather than emitted as a move of a different
register. `movq %rcx, %rax` above is the decoded form of exactly that byte
string, so the counterexample is measured, not argued.

## 4. The digest, both ways (`OD-06`)

`OD-06` asks for one measurement: a one-byte rule change must break the digest,
a comment-only change must not. The definition is data-only JSON and its digest
is taken over the canonical form (`07_definition_format.md` §6), so:

<!-- digest-table:start -->
| Input | sha256 |
|---|---|
| definition as stored | `c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad` |
| same document, keys in reverse order | `c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad` |
| one rule changed (`imm8` range, 8 -> 9 bits) | `505a42c6b28f2a95610755dac2bae6c10d549d29be5fee4953c88b9596a58ba6` |

verdict: formatting-preserving change keeps the digest: **True**; one-bit rule change breaks it: **True**.
<!-- digest-table:end -->

Consequences:

- A rule change — here one bit of an immediate range — moves the digest, so an
  old plan reading a new definition stops at `E-DEF-001`.
- Re-serialising the document with the keys in a different order leaves the
  digest identical, because canonicalization happens before hashing. The same
  holds for indentation, key order, and line endings.
- A comment cannot exist in a JSON document, and would not survive
  canonicalization if it could. The second half of the `OD-06` test is
  unrepresentable rather than silently ignored.

Limit: this measures the Python canonicalizer. The Rust materializer must
produce the same bytes; that cross-check belongs to the code, not to this
record, and is stated as `unverified` until it exists.

## 5. Reproduce

```text
python research/evidence/experiments/EXP-0004/exp0004.py
python research/evidence/experiments/EXP-0004/exp0004.py --emit   # rewrite §2 and §4
python tools/check_definition.py                                  # table vs doc §8
```

`FMP_LLVM_BIN` overrides the LLVM directory. `--emit` rewrites the two marked
tables in this file from an actual run, so the numbers in §2 and §4 are never
transcribed by hand.
