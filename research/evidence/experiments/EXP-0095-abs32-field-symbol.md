# EXP-0095 -- a symbol in an absolute 32-bit content field (`R_X86_64_32S`)

- Date: 2026-11-08
- Question: when a symbol names an absolute 32-bit content field, what do the
  bytes, the relocation and the resolved value look like, and does the field's
  kind (`disp32` vs `imm32`) change any of it?
- Toolchain: `llvm-mc`/`llvm-readobj`/`llvm-objcopy` 23.1.2, `ld.lld` 23.1.2,
  `llvm-nm`/`llvm-objdump` 23.1.2
- Definition: `definitions/x86_64/0.65.0.json`
- Fixture oracle: `fixtures/x86_64/positive/X86-P70-abs32-symbol.oracle.json`
  and `X86-P70-abs32-symbol-resolved.oracle.json`
- Source: `research/evidence/experiments/EXP-0095/`
- Decision: `ADR-0093`

## 1. The measurement

`probe.asm` names one external symbol `ext` in nine absolute 32-bit fields:
eight 32-bit displacements (four value widths, both directions, the extended
prefixes, the high-byte row and one EVEX row) and one 32-bit immediate.

| Source | Bytes | Length | Field | Record offset |
|---|---|---|---|---|
| `movl ext, %eax` | `8b 04 25 00 00 00 00` | 7 | `[24,32]` | `0x3` |
| `movl %eax, ext` | `89 04 25 00 00 00 00` | 7 | `[24,32]` | `0xA` |
| `movl ext, %r8d` | `44 8b 04 25 00 00 00 00` | 8 | `[32,32]` | `0x12` |
| `movq ext, %rax` | `48 8b 04 25 00 00 00 00` | 8 | `[32,32]` | `0x1A` |
| `movw %r9w, ext` | `66 44 89 0c 25 00 00 00 00` | 9 | `[40,32]` | `0x23` |
| `movb %ah, ext` | `88 24 25 00 00 00 00` | 7 | `[24,32]` | `0x2A` |
| `movb ext, %al` | `8a 04 25 00 00 00 00` | 7 | `[24,32]` | `0x31` |
| `vmovaps ext, %zmm1` | `62 f1 7c 48 28 0c 25 00 00 00 00` | 11 | `[56,32]` | `0x3C` |
| `addq $ext, %rax` | `48 81 c0 00 00 00 00` | 7 | `[24,32]` | `0x43` |

Every field is zero in the object bytes, and `llvm-mc -disassemble` reads all
nine as `0` (`probes-disassembled.txt`):

```
    movl    0, %eax
    movl    %eax, 0
    movl    0, %r8d
    movq    0, %rax
    movw    %r9w, 0
    movb    %ah, 0
    movb    0, %al
    vmovaps    0, %zmm1
    addq    $0, %rax
```

`llvm-readobj --relocations` reports nine `R_X86_64_32S ext 0x0` records and
nothing else (`relocations.txt`):

```
    0x3 R_X86_64_32S ext 0x0
    0xA R_X86_64_32S ext 0x0
    0x12 R_X86_64_32S ext 0x0
    0x1A R_X86_64_32S ext 0x0
    0x23 R_X86_64_32S ext 0x0
    0x2A R_X86_64_32S ext 0x0
    0x31 R_X86_64_32S ext 0x0
    0x3C R_X86_64_32S ext 0x0
    0x43 R_X86_64_32S ext 0x0
```

Two facts follow. The record offset is the field's first byte in all nine
cases, so the record is field-shaped, and the field is zero, so the reference
travels in the record and not in the bytes. The field's kind is irrelevant:
`disp32` at four template lengths and `imm32` produce the same record class.

One printer divergence is recorded rather than smoothed over. `llvm-mc
-show-encoding` prints the `add` line as `48 83 c0 A` with an `FK_Data_1`
fixup (`show-encoding.txt`), but the object file contains the seven-byte
`48 81 c0 00 00 00 00` with a four-byte `R_X86_64_32S`
(`probe-bytes.txt`, `relocations.txt`). The object bytes are what the fixture
asserts; the printer's view is kept for reference only.

## 2. `resolve_in_place` measured with `ld.lld`

`resolved.asm` names a defined local symbol `L1` and binds `.text` at
`0x1000`; `L1` is at offset 30, so `S = 0x101e`. Linking with
`ld.lld -m elf_x86_64 --image-base=0 -Ttext 0x1000` and copying `.text`
gives (`resolved-bytes.txt`):

| Source | Bytes | Length | Value |
|---|---|---|---|
| `movq L1, %rax` | `48 8b 04 25 1e 10 00 00` | 8 | `0x101e` |
| `movl L1+4, %eax` | `8b 04 25 22 10 00 00` | 7 | `0x1022` |
| `movl %ecx, L1` | `89 0c 25 1e 10 00 00` | 7 | `0x101e` |
| `movw %dx, L1+2` | `66 89 14 25 20 10 00 00` | 8 | `0x1020` |
| `movb L1, %al` | `8a 04 25 1e 10 00 00` | 7 | `0x101e` |

The same object before linking carries five `R_X86_64_32S .text` records with
addends `0x1E`, `0x22`, `0x1E`, `0x20` and `0x1E`
(`resolved-relocations.txt`), which is `S + A` with `S` replaced by the
symbol's offset. `llvm-nm` on the linked image reports
`000000000000101e t L1` (`resolved-symbols.txt`), and `llvm-objdump -d`
disassembles the five fields as `0x101e`, `0x1022`, `0x101e`, `0x1020` and
`0x101e` (`resolved-disassembled.txt`):

```
0000000000001000 <.text>:
    1000:          movq    0x101e, %rax
    1008:          movl    0x1022, %eax
    100f:          movl    %ecx, 0x101e
    1016:          movw    %dx, 0x1020

000000000000101e <L1>:
    101e:          movb    0x101e, %al
```

The two non-zero addends are 4 and 2, so the resolved bytes separate the
addend from the base address instead of letting one stand for both.

## 3. Neighbours and rejected spellings

`adjacent.asm` keeps the same symbol but changes the reference class; none of
these is this slice (`adjacent-relocations.txt`):

| Source | Bytes | Length | Record | Addend |
|---|---|---|---|---|
| `movl ext, %eax` | `8b 04 25 00 00 00 00` | 7 | `R_X86_64_32S` | `0x0` |
| `movl ext(%rip), %eax` | `8b 05 00 00 00 00` | 6 | `R_X86_64_PC32` | `-4` |
| `movabs ext, %rax` | `48 a1 00 00 00 00 00 00 00 00` | 10 | `R_X86_64_64` | `0x0` |
| `movl $ext, %eax` | `b8 00 00 00 00` | 5 | `R_X86_64_32` | `0x0` |
| `addq $ext, %rax` | `48 81 c0 00 00 00 00` | 7 | `R_X86_64_32S` | `0x0` |

The RIP-relative row measures from the end of the instruction (`P - 4`), the
`moffs` row carries an eight-byte offset, and `movl $ext, %eax` is the
unsigned 32-bit absolute class in an immediate field that `0.65.0` has no row
for. So the class is a fact of the row's field and reference rule, not of the
symbol's value.

Three width spellings are rejected (`rejected.asm`, `rejected.txt`):
`movl ext, %ax`, `movq ext, %eax` and `movw ext, %r9d` each produce `invalid
operand for instruction`. A plan names the width in `form_id`, so the same
three pairs are `E-OPERAND-001` before any byte is produced.

## Reproduce

```
python research/evidence/experiments/EXP-0095/measure.py
```

The script re-assembles all five sources, re-links `resolved.asm`, re-reads
the relocations and symbols, and asserts every byte string above.
