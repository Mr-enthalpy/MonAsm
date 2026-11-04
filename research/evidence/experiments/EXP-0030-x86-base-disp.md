# EXP-0030 — x86-64 base+displacement addressing and the `%rsp` SIB byte

- Date: 2026-11-05
- Question: which ModRM bits carry a base+displacement reference, how wide are
  the two displacement fields, what changes when the base is `%rsp`, and what
  does the assembler choose at the boundaries?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: none. The field layout is read off the measured bytes and
  the ModRM rule already recorded in `ADR-0008`/`ADR-0027`; the rule itself is
  from the ISA manual and was not re-read for this slice.
- Fixture oracle: `EXP-0005` (regenerated with `P4.asm` added)

## 1. The shape

After `REX.W` and the opcode, `ModRM` is the third byte. For
`movq 8(%rbp), %rax` the measured ModRM is `0x4d`:

| Bits | Value | Meaning |
|---|---|---|
| 7–6 | `01` | `mod = 01` — one displacement byte |
| 5–3 | `000` | `reg = 000` — the destination (or the source for opcode `89`) |
| 2–0 | `101` | `r/m = 101` — the base (`%rbp`) |

`mod = 10` is the same with four displacement bytes. `mod = 00` with
`r/m = 101` is RIP (`ADR-0027`), and `r/m = 100` is followed by a SIB byte in
every mod. The instruction is therefore 4 bytes with `disp8` and 7 with
`disp32` when the base is in `r/m`, and 5/8 when `%rsp` adds the SIB byte.

## 2. The fields, measured

One instruction per run at offset 0, `llvm-mc -show-encoding`:

| Source | Encoding | Reading |
|---|---|---|
| `movq 0(%rbp), %rax` | `48 8b 45 00` | `mod = 01`, `r/m = 101`, `disp8 = 0` |
| `movq 8(%rbp), %rcx` | `48 8b 4d 08` | `reg = 001`, `disp8 = 8` |
| `movq -1(%rax), %rdx` | `48 8b 50 ff` | `r/m = 000`, `disp8 = -1` |
| `movq -128(%rbp), %rax` | `48 8b 45 80` | bottom of `disp8` |
| `movq 127(%rbp), %rax` | `48 8b 45 7f` | top of `disp8` |
| `movq 128(%rbp), %rax` | `48 8b 85 80 00 00 00` | `mod = 10`, `disp32 = 128` |
| `movq -129(%rbp), %rax` | `48 8b 85 7f ff ff ff` | `mod = 10`, `disp32 = -129` |
| `movq 4096(%rbp), %rbx` | `48 8b 9d 00 10 00 00` | `reg = 011`, `disp32` |
| `movq 8(%rsp), %rsi` | `48 8b 74 24 08` | `r/m = 100`, SIB `24`, `disp8 = 8` |
| `movq 128(%rsp), %rdi` | `48 8b bc 24 80 00 00 00` | SIB, `disp32 = 128` |
| `movq 4096(%rsp), %rdi` | `48 8b bc 24 00 10 00 00` | SIB, `disp32 = 4096` |
| `movq 8(%rax), %rax` | `48 8b 40 08` | `mod = 01`, no SIB |
| `movq (%rax), %rax` | `48 8b 00` | `mod = 00`, no displacement |
| `movq %rax, 16(%rbp)` | `48 89 45 10` | store direction, opcode `89` |
| `movq %rdx, 4096(%rsp)` | `48 89 94 24 00 10 00 00` | store, SIB, `disp32` |
| `movq %rax, 128(%rsp)` | `48 89 84 24 80 00 00 00` | store, SIB, `disp32` |

The SIB byte `24` decodes as `scale = 00`, `index = 100` (no index) and
`base = 100` (`%rsp`). The same register number `4` is legal as a base in both
shapes; only the ModRM `r/m` and the extra byte differ.

The assembler's boundary behaviour is the assembler's, not the plan's: it picks
`mod = 01` for `-128…127` and `mod = 10` outside that, and it picks `mod = 00`
for a zero displacement on every base except `%rbp`. A plan names the form, so
the materializer never makes that choice; `disp32 = 8` stays `mod = 10`
(`ADR-0028` decision 5).

## 3. The vector

Input `P4.asm` (LF, trailing newline; 195 bytes,
`sha256:ab92314b65aefa5293a215e1a03fb76f426c7e6f396ccb125dac6976dc0c0ebb`):

```text
    movq 0(%rbp), %rax
    movq 8(%rbp), %rcx
    movq -1(%rax), %rdx
    movq 4096(%rbp), %rbx
    movq 8(%rsp), %rsi
    movq 4096(%rsp), %rdi
    movq %rax, 16(%rbp)
    movq %rdx, 4096(%rsp)
```

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | `48 8b 45 00` | `%rbp` at displacement 0: `mod = 01`, not RIP |
| 4 | `48 8b 4d 08` | `disp8 = 8`, destination `%rcx` |
| 8 | `48 8b 50 ff` | `disp8 = -1` |
| 12 | `48 8b 9d 00 10 00 00` | `disp32 = 4096`, destination `%rbx` |
| 19 | `48 8b 74 24 08` | `%rsp`, SIB `24`, `disp8 = 8` |
| 24 | `48 8b bc 24 00 10 00 00` | `%rsp`, SIB, `disp32 = 4096` |
| 32 | `48 89 45 10` | store to `%rbp+16` |
| 36 | `48 89 94 24 00 10 00 00` | store to `%rsp+4096` |
| 44 | `48 8b 85 08 00 00 00` | `mod = 10` with a displacement that fits `disp8` |

The last instruction is not produced by assembling text: `llvm-mc` always picks
`mod = 01` for `8(%rbp)`. Its bytes are derived from the ModRM rule and verified
by `llvm-mc -disassemble`, which prints `movq 8(%rbp), %rax`; the oracle record
says `manual+disassembly` and carries that line.

Output: 51 bytes,
`sha256:fc9a38e6d91ec566efda0379f209b896f94fbab9205efe005f70938afbc35ea3`,
`bytes_hex`
`488b4500488b4d08488b50ff488b9d00100000488b742408488bbc2400100000488945104889942400100000488b8508000000`.

No relocations: every displacement is a literal, so the record has
`records = 0`.

## 4. What this fixes, and what it does not

Fixes:

- the ModRM `mod`/`r/m`/`reg` placement for the two widths;
- the `%rsp` SIB byte, `24`, with the base repeated in the SIB field;
- the signed domains: `disp8` is `-128…127`, `disp32` is
  `-2147483648…2147483647`;
- the negative evidence: the same ids against `0.2.0` are `E-FORM-001`
  (`N01y`), `disp8 = 128` is `E-RANGE-001` on the `disp8` row
  (`N03-disp8-out-of-range`), and `%rsp` in a non-SIB row is `E-RANGE-004`
  (`N16f`).

Does not fix:

- **index and scale (`[base + index*scale + disp]`).** SIB with a non-empty
  index is a different shape for every index/scale pair.
- **`mod = 00` with a base.** `movq (%rax), %rax` is `48 8b 00`, a different row
  with no displacement at all.
- **`%r12` and `r8`–`r15`.** They need `REX.B`/`REX.X`, and the base slot is
  three bits.
- **the `0x67` address-size prefix and `moffs`.** `EC-08` and `EC-05` are still
  outside the surface.
- **symbolic displacements on a base row.** They would need a decision about the
  reference base and addend; `pcrel_end` describes RIP-relative and branch
  sites, not `[rbp+8]`.
- **16-bit (`0x66`) and 8-bit widths (`X86-P5`).**

## 5. Result

The rows ship in `definitions/x86_64/0.3.0.json`, which repeats the nine
`0.2.0` forms and adds eight:

```text
definition  definitions/x86_64/0.3.0.json
namespace   monasm.isa.x86
version     0.3.0
forms       17
digest      sha256:02500bf74d5c3db7816a30aca6c9c4d8fc7c5097306bc742f51284636c487c10
```

`07_definition_format.md` §8 records the digest; `EXP-0005` §2 records the
regenerated fixture.

Our materializer emits the 51 bytes above and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `X86-P4-base-disp` | eight assembled instructions plus the small-value `disp32` | 51 bytes, `sha256:fc9a38e6…`, no record |
| `N01y-absent-basedisp-form` | the `disp8` row against `0.2.0` | `E-FORM-001` |
| `N03-disp8-out-of-range` | `disp8 = 128` | `E-RANGE-001` |
| `N16f-rsp-on-non-sib-form` | `%rsp` as a `base` operand | `E-RANGE-004` |
