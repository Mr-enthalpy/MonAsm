# EXP-0100 -- the Level 1 envelope is the same plan, split into sections

- Date: 2026-11-08
- Question: can `artifact: sections` describe the Level 0 image as sections and
  a declared symbol table without a second encoder, and does a virtual `.bss`
  section stay out of the file bytes?
- Toolchain: `llvm-mc` 23.1.2, `llvm-objcopy`, `llvm-readobj`, `llvm-objdump`
- Definition: `monasm.isa.x86/0.2.0` (the table `X86-P6` already names)
- Source: `research/evidence/experiments/EXP-0100/level1-sections.asm`
- Fixture: `fixtures/x86_64/positive/X86-P71-level-one-sections.*`
- Decision: `ADR-0096`

## 1. Input and Level 0 bytes

`level1-sections.asm` is the `X86-P6` body plus a `.bss` section:

```asm
    .text
    movq 16(%rip), %rax
    movq L1(%rip), %rcx
    .space 2
    movq %rdx, L1(%rip)
    .space 9
L1:
    .byte 0xaa, 0xbb, 0xcc, 0xdd
    movq ext(%rip), %rbx
    .section .bss
S2:
    .zero 8
```

`input_sha256 = f2d6f9a264047df36ef843d205794de2c5ff5eec1c8377706e85303c2a70c2ad`.

```text
llvm-mc -triple=x86_64 -filetype=obj level1-sections.asm -o out.o
llvm-objcopy -O binary --only-section=.text out.o out.bin
```

`out.bin` is 43 bytes with
`output_sha256 = 1e70735cff06ee7a57c34709753ea715ac9098f5c4d8bcb650804eb8c04709bf`,
the same hash as `X86-P6`. The `.bss` section is `SHT_NOBITS`, so it adds no byte
to `out.bin`; `llvm-objcopy --only-section=.text` would otherwise fail on a
section with no file payload.

## 2. Sections and symbols

`llvm-readobj --sections out.o` reports:

| Section | Type | Size |
|---|---|---|
| `.text` | `SHT_PROGBITS` | 43 |
| `.bss` | `SHT_NOBITS` | 8 |

`llvm-readobj --symbols out.o` reports:

| Name | Binding | Section | Value |
|---|---|---|---|
| `L1` | local | `.text` | `0x20` |
| `S2` | local | `.bss` | `0x0` |
| `ext` | global | undefined | `0x0` |

The plan declares those three symbols and sets
`symbol_order = ["ext", "S2", "S1"]`, where `S1` is the plan id for `L1`. That
order is not `symbol_id` order (`S1`, `S2`, `ext`), so `X86-P71` pins the
declared order rather than a sort.

`llvm-readobj --relocations out.o` reports one record:

```text
0x27 R_X86_64_PC32 ext 0xFFFFFFFFFFFFFFFC
```

That is the `pcrel_end` fixup on `movq ext(%rip), %rbx`, carried unchanged in
the Level 1 `fixups[]` array.

## 3. What this establishes

- The Level 1 section split is a projection of the plan's `sections[]` in
  `section_order`; the `.text` bytes are exactly the Level 0 image, so no second
  encoder exists to disagree.
- A non-image-backed section is representable with its virtual size and no
  bytes (`"bytes_hex": ""`), which is why the envelope lists it instead of
  dropping it.
- The declared symbol table is the plan's `symbols[]` in the plan's order; no
  symbol is synthesized, so the RV64 `pcrel_lo12` local-label case remains a
  later writer task.
