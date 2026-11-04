# EXP-0031 — x86-64 prefix bytes and the 8-bit register sets

- Date: 2026-11-05
- Question: what does `0x66` change, how does a `0x40`–`0x4f` prefix change the
  meaning of `ModRM` register numbers 4–7, and which combinations does the
  assembler refuse?
- Toolchain: `llvm-mc`/`llvm-objcopy`/`llvm-objdump` 23.1.2
- Definition source: none. The field layout is the one `EXP-0004` and `EXP-0030`
  already measured; no ISA manual text was re-read for this slice.
- Fixture oracle: `EXP-0005` (regenerated with `P5.asm` added)

## 1. The shape

The prefix byte precedes the opcode, and `ModRM` keeps the same three fields it
has without a prefix:

| Bits | Meaning |
|---|---|
| 7–6 | `mod` |
| 5–3 | `reg` |
| 2–0 | `r/m` |

Both `0x66` and `0x40`–`0x4f` are one byte, and neither is addressable as an
operand: they are byte 0 of the form. What changes is the meaning of the fields
that follow, which is why the same `ModRM` byte appears in rows with different
register widths.

The names "operand-size prefix" and "REX prefix" are conventional labels; the
evidence for the behaviour below is the measured byte strings, not the label.
`0x40` is the prefix with no extension bits set, which is the one this slice
uses, because every register number is inside the three-bit field.

## 2. The fields, measured

One instruction per run at offset 0, `llvm-mc -show-encoding`:

| Source | Encoding | Reading |
|---|---|---|
| `movw %bx, %ax` | `66 89 d8` | `0x66`, then `89 /r`: `reg = 011`, `r/m = 000` |
| `movw %si, %di` | `66 89 f7` | `reg = 110`, `r/m = 111` |
| `movw %dx, %cx` | `66 89 d1` | `reg = 010`, `r/m = 001` |
| `movw %ax, %ax` | `66 89 c0` | `reg = r/m = 000` |
| `movb %ah, %ch` | `88 e5` | no prefix; `reg = 100`, `r/m = 101` |
| `movb %ch, %ah` | `88 ec` | `reg = 101`, `r/m = 100` |
| `movb %ah, %ah` | `88 e4` | `reg = r/m = 100` |
| `movb %al, %cl` | `88 c1` | `reg = 000`, `r/m = 001` |
| `movb %spl, %bpl` | `40 88 e5` | `0x40`, then `89`-family `88 /r` with the same `e5` |
| `movl %eax, %eax` | `89 c0` | the 32-bit reading of the same `ModRM` |
| `movq %rax, %rax` | `48 89 c0` | the 64-bit reading |
| `movw %ax, %ax` | `66 89 c0` | the 16-bit reading |

`-disassemble` over the whole 3-bit domain, both directions of the 16-bit pair:

| Bytes | Decodes as | Bytes | Decodes as |
|---|---|---|---|
| `66 89 c0` | `movw %ax, %ax` | `66 8b c0` | `movw %ax, %ax` |
| `66 89 c8` | `movw %cx, %ax` | `66 8b c8` | `movw %ax, %cx` |
| `66 89 d0` | `movw %dx, %ax` | `66 8b d0` | `movw %ax, %dx` |
| `66 89 d8` | `movw %bx, %ax` | `66 8b d8` | `movw %ax, %bx` |
| `66 89 e0` | `movw %sp, %ax` | `66 8b e0` | `movw %ax, %sp` |
| `66 89 e8` | `movw %bp, %ax` | `66 8b e8` | `movw %ax, %bp` |
| `66 89 f0` | `movw %si, %ax` | `66 8b f0` | `movw %ax, %si` |
| `66 89 f8` | `movw %di, %ax` | `66 8b f8` | `movw %ax, %di` |

`%sp` is encodable at 16 bits in a register-direct `ModRM`: `mod = 11` selects
the register form, so the SIB byte `ADR-0028` measured for `%rsp` as a base does
not apply here. That is why the 16-bit rows have no `excluded` list.

The 8-bit pair, over numbers 4–7 on both `ModRM` fields:

| Bytes | Decodes as | Bytes | Decodes as |
|---|---|---|---|
| `88 e0` | `movb %ah, %al` | `40 88 e0` | `movb %spl, %al` |
| `88 e1` | `movb %ah, %cl` | `40 88 e1` | `movb %spl, %cl` |
| `88 e2` | `movb %ah, %dl` | `40 88 e2` | `movb %spl, %dl` |
| `88 e3` | `movb %ah, %bl` | `40 88 e3` | `movb %spl, %bl` |
| `88 e4` | `movb %ah, %ah` | `40 88 e4` | `movb %spl, %spl` |
| `88 e5` | `movb %ah, %ch` | `40 88 e5` | `movb %spl, %bpl` |
| `88 e6` | `movb %ah, %dh` | `40 88 e6` | `movb %spl, %sil` |
| `88 e7` | `movb %ah, %bh` | `40 88 e7` | `movb %spl, %dil` |
| `88 c4` | `movb %al, %ah` | `40 88 c4` | `movb %al, %spl` |
| `88 c5` | `movb %al, %ch` | `40 88 c5` | `movb %al, %bpl` |
| `88 c6` | `movb %al, %dh` | `40 88 c6` | `movb %al, %sil` |
| `88 c7` | `movb %al, %bh` | `40 88 c7` | `movb %al, %dil` |

Four readings from the table:

1. **The prefix changes the register set, not the field.** `88 e5` and
   `40 88 e5` have the same opcode and the same `ModRM`; the first is
   `ah, ch`, the second `spl, bpl`.
2. **`0x40 88 c1` is the same instruction as `88 c1`.** `llvm-mc -disassemble`
   prints `movb %al, %cl` for both. A prefix with no extension bits is legal
   but redundant (`EC-28`), which is why the REX row excludes `0–3`: otherwise
   one register pair would have two legal rows.
3. **Order matters.** `66 48 89 c0` decodes as `movq %rax, %rax`, and
   `48 66 89 c0` decodes as `movw %ax, %ax`. The prefix closest to the opcode
   decides the width, so a form that owns `0x66` carries it in the template
   rather than letting an operand or a later stage add it.
4. **The assembler refuses mixed sets.** `movb %ah, %spl`, `movb %spl, %ah`
   and `movb %ah, %r8b` all report
   `can't encode 'ah' in an instruction requiring EVEX/REX2/REX prefix`, and
   `movw %ax, %eax` reports `invalid operand for instruction`.

## 3. The vector

Input `P5.asm` (LF, trailing newline; 100 bytes,
`sha256:2025c68efd6397b6ff70dfb3795d052c88b37cf8cdce22b42ffa926a67faf151`):

```text
movw %bx, %ax
movw %si, %di
movb %ah, %ch
movb %ch, %ah
movb %al, %cl
movb %spl, %bpl
movb %ah, %ah
```

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | `66 89 d8` | 16-bit store-direction `mov`: `r/m = %ax`, `reg = %bx` |
| 3 | `66 89 f7` | `r/m = %di`, `reg = %si` |
| 6 | `88 e5` | high bytes: `r/m = %ch`, `reg = %ah` |
| 8 | `88 ec` | the same two numbers swapped: `r/m = %ah`, `reg = %ch` |
| 10 | `88 c1` | low bytes without a prefix: `r/m = %cl`, `reg = %al` |
| 12 | `40 88 e5` | the same `e5` with `0x40`: `r/m = %bpl`, `reg = %spl` |
| 15 | `88 e4` | number 4 on both sides is `%ah`, not `%spl` |

The appended `66 8b c3` is the load direction at 16 bits: `reg = %ax`,
`r/m = %bx`, decoding as `movw %bx, %ax`. `llvm-mc` always emits `89 /r` for
`movw %bx, %ax`, so this half is derived from the opcode pair already measured
at 64 bits (`X86-P1`) and verified by `llvm-mc -disassemble`; the oracle record
says `manual+disassembly` and carries that line.

Output: 20 bytes,
`sha256:e38f01697dade526a61fae6932b4cde283c32bce12ede7d63c096a2c98615cac`,
`bytes_hex` `6689d86689f788e588ec88c14088e588e4668bc3`.

No relocations: every operand is a register, so the record has `records = 0`.

## 4. What this fixes, and what it does not

Fixes:

- `0x66` as template byte 0 of the 16-bit rows, with `x86.gpr16` the only
  operand kind they accept;
- `x86.gpr8h` as the high-byte set (numbers 4–7 = `ah`/`ch`/`dh`/`bh`) and
  `x86.gpr8` as the low-byte set, split into a REX-less row (0–3) and a REX row
  (4–7);
- the load-time rule that a `gpr8h` slot cannot sit in a REX template and a
  REX-less `gpr8` slot must exclude 4–7 (`E-DEF-001`);
- the negative evidence: the 16-bit row against `0.3.0` is `E-FORM-001`
  (`N01z`), a `gpr8h` operand on the REX row is `E-OPERAND-001` on both `kind`
  and `target_type` (`N02k`), and number 4 in the REX-less row is
  `E-RANGE-004` (`N16g`).

Does not fix:

- **the `8A` direction at 8 bits.** Only `88` is measured here; `X86-P1` covers
  the direction pair at 64 bits.
- **memory operands at 16 or 8 bits.** `mod = 00`/`01`/`10` with a base brings
  back the SIB byte and the `spl`–`dil` base registers.
- **`r8`–`r15` byte registers.** They need extension bits on the `0x40` prefix,
  so `EC-06`/`EC-08` govern them.
- **the `0x67` address-size prefix.** `EC-08` is still outside the surface.
- **a redundant-prefix rule as a form.** `EC-28` records the behaviour, but this
  slice makes the two encodings of `al, cl` illegal by exclusion rather than by
  offering both.

## 5. Result

The rows ship in `definitions/x86_64/0.4.0.json`, which repeats the seventeen
`0.3.0` forms and adds five:

```text
definition  definitions/x86_64/0.4.0.json
namespace   monasm.isa.x86
version     0.4.0
forms       22
digest      sha256:ee2141cbb17f338c5b4a9de0302076bb2416838c09f7c44e2ca097cb142a2682
```

`07_definition_format.md` §8 records the digest; `EXP-0005` §2 records the
regenerated fixture.

Our materializer emits the 20 bytes above and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `X86-P5-prefixes` | seven assembled instructions plus the decode-verified `66 8b c3` | 20 bytes, `sha256:e38f0169…`, no record |
| `N01z-absent-16bit-form` | the `rm16` row against `0.3.0` | `E-FORM-001` |
| `N02k-high-byte-operand-on-rex-form` | `x86.gpr8h`/`rm8h` on the REX row | `E-OPERAND-001` on `kind` and `target_type` |
| `N16g-low-byte-number-four-without-rex` | `reg = 4` in the REX-less low-byte row | `E-RANGE-004` |
