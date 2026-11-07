# EXP-0103 -- the x86 direct `call rel32` row

- Date: 2026-11-08
- Question: how is a direct call encoded at the 64-bit operand size, how does
  a local label resolve, and what does the deliberately absent indirect
  family look like?
- Toolchain: `llvm-mc`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition: `definitions/x86_64/0.67.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P73-call-rel32.oracle.json`
- Sources: `research/evidence/experiments/EXP-0103/probe.asm`,
  `research/evidence/experiments/EXP-0103/indirect.asm`
- Decision: `ADR-0102`

## 1. The measurement

`llvm-mc -show-encoding` and the object bytes agree on all four instructions;
`measure.py` asserts the 19-byte `.text`, writes `bytes.txt`,
`show-encoding.txt` and `relocations.txt`, and fails unless the object carries
exactly one `R_X86_64_PLT32 ext -4` record.

| Source | Bytes | Length | Shape |
|---|---|---|---|
| `call L1` | `e8 05 00 00 00` | 5 | local symbol, `pcrel_end` |
| `call ext` | `e8 00 00 00 00` | 5 | external symbol, one relocation |
| `addq $1, %rax` | `48 83 c0 01` | 4 | the `0.1.0` row that hosts `L1` |
| `call .+130` | `e8 7d 00 00 00` | 5 | literal field value `125` |

`L1` is at offset 10 and the call ends at offset 5, so the first field is
`10 − 5 = 5`. `pcrel_begin` would have written `10`, and the measured `05`
rules it out. `llvm-mc` prints the second instruction as
`callq ext # fixup A - offset: 1, value: ext, kind: reloc_branch_4byte_pcrel`,
which is the same fixup kind it uses for `jmp rel32`.

`call .+130` is the literal-displacement path: llvm-mc measures `130` from
the start of the instruction, so the field is `130 − 5 = 125 = 0x7d`. The
expression is llvm-mc syntax; the plan carries the field value, not the
expression.

The relocation record is the same class as `jmp ext` in `X86-P8`:

```text
Relocations [
  Section (3) .rela.text {
    0x6 R_X86_64_PLT32 ext 0xFFFFFFFFFFFFFFFC
  }
]
```

The `-4` addend and `pcrel_end` with addend 0 describe the same arithmetic:
the linker writes `ext − P` with `P` four bytes before the fixup site, which
is the end of the instruction when the field starts one byte into it.

## 2. The indirect family is a different encoding

`indirect.asm` measures the shapes this slice does not take:

| Source | Bytes | Length |
|---|---|---|
| `callq *%rax` | `ff d0` | 2 |
| `callq *(%rax)` | `ff 10` | 2 |
| `callq *8(%rax)` | `ff 50 08` | 3 |

The first is `FF /2` with `mod = 11`; the second is `FF /2` with `mod = 00`
and `r/m = 000`; the third adds a `disp8`. None of them has an `E8` byte.
The indirect call is therefore not a longer direct call: it is a separate
form family with a `ModRM` byte and a register-or-memory operand, and it stays
absent until it gets its own operand geometry and fixture.

## 3. The fixture

`X86-P73-call-rel32` is the four-instruction, 19-byte vector above.
`expected.bin` comes from `llvm-mc` + `llvm-objcopy`, never from the
materializer; the oracle's `input_sha256` is
`a282dfc425ca43038f9aa4a43b822ec4a32f290f1e77a576c3f2658498d2a90c`
(`probe.asm`) and its `output_sha256` is
`0f9014099643ce792b93e64482d630ddee32310657e46211a1ab6aa9276521fb`
(the 19-byte `.text`).

`0.67.0` has 513 forms and the canonical digest
`sha256:367d76ebf89ee9c1cf51f561b4798eeb0a2000ae3688ee9a52a4c4a9eaea5c9e`.

## 4. Negative coverage

| Case | Plan | Error |
|---|---|---|
| `N01el` | names `x86:call/rm64/legacy`, which no version has | `E-FORM-001` |
| `N01em` | names `call/rel32` against `0.66.0` | `E-FORM-001` |
| `N02cu` | passes `x86.gpr64`/`r64` as the target | `E-OPERAND-001` twice (`kind`, `target_type`) |
| `N02cv` | omits the target operand | `E-OPERAND-002` |
| `N04g` | target value `2147483648` | `E-RANGE-002` (`max 2147483647`) |

`N04g` is the field-width boundary: the value fits an unsigned 32-bit field
but not the signed displacement the row encodes, and the answer is a
rejection, not a wrap.

## 5. What the slice defers

- The indirect `FF /2` call, with its `ModRM` and register-or-memory operand.
- The `66`/`67` prefixed calls and the 16/32-bit operand sizes.
- A non-symbol relocation target in the displacement.
- `lcall`, `syscall` and the other instructions that reuse `E8`.
