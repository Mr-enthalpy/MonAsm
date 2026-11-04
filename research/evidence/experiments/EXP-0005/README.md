# EXP-0005 — x86-64 positive fixtures, measured with LLVM

- Date: 2026-11-04 (extended 2026-11-05 with `X86-P6`)
- Subject: `fixtures/x86_64/positive/` — the six bytes-emitting vectors
- Toolchain: LLVM 23.1.2 (`llvm-mc`, `llvm-objcopy`, `llvm-readobj`), Python 3.8
- Basis: **experiment** for every byte below
- Reproduce: `python fixture_oracle.py` (rewrites), or
  `python fixture_oracle.py --check` (verifies without rewriting)

## 1. Why this is not a self-check

The fixture gate compares two independently produced byte strings:

1. the materializer's output, from the plan and the definition table;
2. `*.expected.bin`, produced by `llvm-mc` from the `.asm` input in this
   directory, extracted with `llvm-objcopy --only-section=.text`.

`fixture_oracle.py` records the tool version, the exact command, the SHA-256 of
the input and of the output, and the expected relocation count. A passing
`cargo test -p fmp-cli --test fixtures` therefore means the plan, the table and
LLVM agree, not that a function agrees with itself.

## 2. Measured

| Fixture | Plan | Oracle bytes | Size | Oracle |
|---|---|---|---|---|
| `X86-P1-mov-r64-both-directions` | `mov %rbx,%rax` then the `8B /r` move | `4889d8 488bc3` | 6 | `manual+disassembly` |
| `X86-P2-add-imm8-and-imm32` | `addq $1,%rax`; `addq $300,%rbx` | `4883c001 4881c32c010000` | 11 | `llvm-mc` |
| `X86-P3-two-legal-encodings` | `addq $300,%rax`; `addq $300,%rbx` | `48052c010000 4881c32c010000` | 13 | `llvm-mc` |
| `X86-P7-short-and-near-branch` | `jmp .+0x81`; `jmp .+0x82` | `eb7f e97d000000` | 7 | `llvm-mc` |
| `X86-P6-rip-relative` | `movq 16(%rip),%rax`; local load/store against `L1` at `0x20`; `movq ext(%rip),%rbx` | `488b0510000000 488b0d12000000` + 2×`00` + `48891509000000` + 9×`00` + `aabbccdd 488b1d00000000` | 43 | `llvm-mc` + `llvm-readobj` |
| `X86-P8-local-and-external-branch` | `jmp L1` (resolved); `jmp ext` (recorded) | `e9cb000000` + 200×`00` + `4889d8 4883c001 e900000000` | 217 | `llvm-mc` + `llvm-readobj` |

`EXP-0004` decoded every row of the definition table, including the forms LLVM
will not assemble from a mnemonic. This experiment adds the end-to-end plan
path: the plan names a form, the table places the fields, and the bytes match.

## 3. Cases LLVM cannot emit from assembly text

Three bytes in the table are not produced by `llvm-mc` from a mnemonic. They are
**decode-verified**, not assembled, and the oracle record says so:

- `X86-P1`'s second instruction (`REX.W 8B /r`). Assembling `movq %rbx, %rax`
  always yields `48 89 d8`; `48 8b c3` is verified by disassembly
  (`llvm-mc -disassemble` prints `movq %rbx, %rax`). The fixture still needs the
  `8B` direction because `X86-P1`/`X86-P3` require both directions as distinct
  forms, and a plan must be able to name the one it wants.
- `X86-P3`'s second instruction (`REX.W 81 /0 id`) is measured on `%rbx`.
  `llvm-mc` always picks the accumulator form `48 05 2c 01 00 00` when the
  destination is `%rax`, so the `81 /0` row with `%rax` is decode-verified in
  `EXP-0004`. The fixture pairs `05 id` on `%rax` with `81 /0 id` on `%rbx`,
  which keeps every byte measured while still showing the two forms are
  different plans with identical semantics.

## 4. Branch notes

- `llvm-mc` shortens a same-section branch when `rel8` fits: `jmp L1` becomes
  `eb`. A `rel32` resolve case therefore needs a target more than 127 bytes
  away. `X86-P8` places `L1` after a 200-byte `.space`, giving
  `jmp L1` → `e9 cb 00 00 00`. Our plan states `x86:jmp/rel32/legacy`
  explicitly; the fixture never relies on LLVM's choice.
- `llvm-mc` promotes `jmp .+0x82` to `e9 7d 00 00 00` because `+0x82` does not
  fit `rel8`. `X86-P7` pairs `.+0x81` (`eb 7f`) with `.+0x82` (`e9 7d …`) to
  show both forms as separate plans, not a promotion rule.
- `X86-P8`'s external branch assembles to `e9 00 00 00 00` plus
  `R_X86_64_PLT32 ext 0xFFFFFFFFFFFFFFFC` at offset `0xD5`
  (`llvm-readobj --relocations`). The plan's `emit_relocation` zeroes the
  descriptor bits and emits one record; `records = 1` in the oracle record is
  the measured count. Our `pcrel_end` with `addend = 0` is the same value as
  ELF's `S + A - P` with `A = -4` (`03_fixup_model.md` §6.1).

## 5. Files

| File | Meaning |
|---|---|
| `P1.asm` … `P8.asm` | The assembled source, one per fixture |
| `fixture_oracle.py` | Regenerates `*.expected.bin` and `*.oracle.json`; `--check` verifies |
| `../fixtures/x86_64/positive/*.fmp.json` | The plans |
| `../fixtures/x86_64/positive/*.expected.bin` | Oracle bytes |
| `../fixtures/x86_64/positive/*.oracle.json` | Tool version, command, hashes, record count |
