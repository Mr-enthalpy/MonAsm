# EXP-0011 — a memory operand is several fields, and x86 chooses its form from a value

- Date: 2026-11-04
- Subject: how a memory operand must be represented in a plan (`OD-13`), and the
  three measurements ADR-0008 rests on
- Basis: **experiment** for every byte string, hash and field decode
- Reproduce: the commands in §1, then `cargo test --workspace`
- Depends on: `EXP-0009`, ADR-0007; feeds ADR-0008, `RV-P3`, `N15`

## 1. Why this experiment exists

Four coverage rows (`X86-P4`/`P5`/`P6`, `A64-P3`) and one RV64 row (`RV-P3`) were
blocked by one unasked question: what is a memory operand *in the plan*? The
contract sketched per-ISA `mem` kinds in §8 and simultaneously restricted §8.1 to
four payload shapes, none of them a memory operand. Any table slice would have
had to answer the question by accident.

The candidate answers were:

- **A** — one composite payload per ISA (`{"mem": {base, index, scale, disp}}`);
- **B** — one operand per encoded field (`base`, `disp`, `index`, `scale`), with
  the addressing form carried by the `form_id`;
- **C** — one `form_id` per mnemonic, with the addressing form chosen from the
  operand values.

B and C emit the same bytes for most inputs; they differ in *where the decision
lives*, which is what `INV-02` and ADR-0004 make load-bearing. So the experiment
does not ask "does it work" but "does the encoding form change while the operand
list stays the same". If it does, C is not available.

All measurements used LLVM 23.1.2 at `C:\Users\hanni\Tools\llvm\bin`:

```powershell
llvm-mc -triple=<triple> -filetype=obj input.s -o out.o
llvm-objcopy -O binary --only-section=.text out.o out.bin
llvm-mc -triple=<triple> -show-encoding input.s
```

Each input file is written with `\n` line endings and one trailing newline; the
SHA-256 of the input and of the extracted `.text` are recorded so a re-run is
comparable.

## 2. RV64: the source states three separate fields

Read from the pinned UDB resolved spec (`ADR-0007`), `RV64` blocks only:

| Node | Size | SHA-256 | `encoding.RV64` variables |
|---|---|---|---|
| `inst/I/ld.yaml` | 27033 B | `a2afcd44fd54f5de7a9a9226f66f273b92c4e868a3519782a06c0f0fe3cc4c35` | `imm` `31-20`, `sign_extend: true`; `xs1` `19-15`; `xd` `11-7` |
| `inst/I/sd.yaml` | 26947 B | `f0b69996f811f7ae206f9219cf6057318eb908d6f04af70e83e403606c71390e` | `imm` `"31-25|11-7"`, `sign_extend: true`; `xs2` `24-20`; `xs1` `19-15` |

Two facts follow, and neither is a matter of taste:

1. The address is **two fields with different ranges and different owners**: a
   base register is 5 bits, the displacement is 12 bits, and a fixup that covers
   the displacement does not cover the base. A single `{base, disp}` operand
   would have to answer "which field does this fixup cover" twice.
2. `sd`'s displacement is **not contiguous** (`[31:25]` and `[11:7]`), while
   `ld`'s is. A composite payload would need per-form knowledge of that split,
   which the slots already carry.

The `RV32` blocks in the same nodes carry a `not:` list on `xd`/`xs2` (the Zilsd
even-register pairing). Those blocks are not this table's source; the generator
selects the `RV64` block by header (`EXP-0010` §3.1).

`definedBy` is an `anyOf` over (`xlen: 64`, `I`) and (`xlen: 32`, `Zilsd`), so the
RV64 form is admitted by the first branch and `enabled_extensions: ["rv64i"]`
covers it.

## 3. RV64: the oracle bytes, and the plan decomposition

Input lines (one per instruction):

```text
ld a0, 8(a1)
sd a2, 8(a1)
ld a0, -2048(a1)
sd a2, 2047(a1)
```

`llvm-mc -triple=riscv64 -filetype=obj` → `.text` is 16 B:
`03 b5 85 00 23 b4 c5 00 03 b5 05 80 a3 bf c5 7e`.

| Input SHA-256 | Output SHA-256 | Size |
|---|---|---|
| `676c0707ab4f83f6e1024abf2f2219d68787ad511e7383ea38f0de75adfffa47` | `eb1ed98b0adaee914df5c429223ea91434f049dd4255ef7f22f2f54f4203efb4` | 16 B |

Decoding the four words against §2 (little-endian words):

| Word | Instruction | Fields |
|---|---|---|
| `0x0085b503` | `ld a0, 8(a1)` | `xd=10`, `xs1=11`, `imm=8` |
| `0x00c5b423` | `sd a2, 8(a1)` | `xs2=12`, `xs1=11`, `imm=8` (`[11:7]=8`, `[31:25]=0`) |
| `0x8005b503` | `ld a0, -2048(a1)` | `imm=-2048` (`0x800`, sign-extended) |
| `0x7ec5bfa3` | `sd a2, 2047(a1)` | `imm=2047` (`[11:7]=0x1f`, `[31:25]=0x3f`) |

The plan for the same four instructions is in
`fixtures/rv64/positive/RV-P3-ld-sd-base-offset.fmp.json`: each instruction has
three operands — `dest`/`src`, `base`, `disp` — with payloads `{reg}`,
`{reg}`, `{value}`. No operand carries both a register and a displacement, and
no fixup is present (`records: 0`); the displacement is a plain field value
because RV64 does not scale the load/store immediate.

The rejected alternative is pinned from the other side:
`fixtures/rv64/negative/N15-composite-memory-payload.fmp.json` supplies
`{"mem": {"base": 11, "disp": 8}}` for the base operand and is rejected at
**read** time with `E-OPERAND-003` at `/instructions/0/operands/1/payload`. That
is why the fixture harness gained a `phase` key (`fixtures/README.md`): there is
no definition lookup when the plan itself is not `fmp/0.1`.

## 4. x86: the encoding form changes, and the operand list does not

Input lines (AT&T syntax; the Intel spelling `mov rax, [rcx+8]` is rejected by
`llvm-mc` with *"unknown use of instruction mnemonic without a size suffix"*, so
the size suffix is not optional here):

```text
movq 8(%rcx), %rax
movq 4096(%rcx), %rax
movq (%rbp), %rax
```

| Line | Bytes | Size | Input SHA-256 | Output SHA-256 |
|---|---|---|---|---|
| `movq 8(%rcx), %rax` | `48 8b 41 08` | 4 B | `7ca86e2681cfc6d7e5023ebbeb5e0df0f4e84ce67c1365472af9bc6ae8a803c4` | `810de49edf5c9302862254e9dbda0161e90553d6d5961711804267e08e4d67cf` |
| `movq 4096(%rcx), %rax` | `48 8b 81 00 10 00 00` | 7 B | `a44c53d48e718faa66655888882be4e4dac2bede6dea3f61bf138bf803a799d8` | `7b5584e59d9170f955bc65786915bcad1acb5c5a2b2f9dad7e92a74888413908` |
| `movq (%rbp), %rax` | `48 8b 45 00` | 4 B | `200faae82550cd3e513f8a5ccc9c7d25e3d5a026b849df8cd506546ab3254b0d` | `c792e8865d251e18260dc1f367556149e46e45e8a66c7a31715084cc5878e672` |

Three separate facts:

1. **The displacement's value selects the encoding form.** `8` fits a signed
   8-bit displacement → `ModRM.mod = 01` with a `disp8`; `4096` does not →
   `mod = 10` with a `disp32`. Same mnemonic, same operand list, 3 bytes
   different, and the only difference is the value. An encoder that picks mod
   from the value has made an encoding-form decision (`INV-02`) that no plan
   field records.
2. **A base register can force a wider form for the same reason.** `(%rbp)` has
   no displacement at all, yet the encoding is `mod = 01` with a zero `disp8`:
   `mod = 00` with `r/m = 101` means RIP-relative, so a base of `rbp` cannot use
   the compact no-displacement form. The rule itself comes from the ISA manual
   and was **not** re-read for this experiment (`inference` from the bytes plus
   the ModRM encoding rule); the bytes are observed.
3. **The length is not a property of the mnemonic.** A `form_id` per mnemonic
   would have to encode three different instruction lengths under one name, so
   either `expected_size` becomes a hint (which `04_errors.md` `E-SIZE-001`
   forbids) or the form must be split.

This is the measurement that rules out candidate C. It also explains why
`X86-P4` and `X86-P6` are now stated as a precondition rather than a payload
question: the slice must enumerate one `form_id` per ModRM mod / SIB shape,
measured, before a fixture can exist.

## 5. AArch64: the immediate field is already scaled

```text
ldr x0, [x1, #16]
```

`llvm-mc -triple=aarch64` → `20 08 40 f9`, 4 B; input SHA-256
`50af4f8df3c7c2da1edfa7df7ad75baae1bce600c428e52b8e67bed9aaa2ec86`, output
SHA-256 `f6dfccf5a4ba3e268542933e80a75cf13ae691395f51deb1240d9f4a863aa9c3`.

Bits `[21:10]` decode to `imm12 = 2`, not `16`: the field is scaled by the access
size (8 bytes for a 64-bit `ldr`). That is consistent with
`07_definition_format.md` §8.3 — the slot holds **field content**, not the
source-level offset — but it means a composite `{base, disp}` payload would need
a second answer inside the same field: bytes or field value. Splitting the
operand removes the ambiguity; the AArch64 slice still has to decide *which* of
the two a plan states, and that belongs with the form, not with the payload
shape.

`A64-P3` is not admitted here. Its four addressing kinds (unsigned-offset,
pre/post-index, register-offset, literal) are four `form_id` variants, and each
needs its own measured bytes before it lands.

## 6. What this settles, and what it does not

Settled (`ADR-0008`, `OD-13`):

- A memory operand is one operand per encoded field. `fmp/0.1` keeps its four
  payload shapes; a composite object is `E-OPERAND-003`, now exercised by `N15`.
- The addressing form is a `form_id` variant, because the encoding form is a
  function of operand values on x86 (§4) and because pre/post-index and
  scaled/unscaled immediates are different instructions on AArch64.
- `RV-P3` lands as `riscv:ld/rd-base-imm12` and `riscv:sd/rs-base-imm12`, three
  operands each, with `disp` as the byte displacement (§3).
- `RV-P3`'s bytes are pinned by the fixture and by this record; the generator
  re-encodes the same four vectors from the table it builds (`EXP-0010` §4).

Not settled, and explicitly left open:

- **Which x86 variants v0 needs.** At minimum `mod=00/01/10` and "with/without
  SIB", plus the RIP-relative form; the set is not enumerated or measured yet.
  `X86-P4`/`P6` stay deferred.
- **AArch64's byte-vs-field-value question for `disp`** and its four addressing
  variants. `A64-P3` stays deferred.
- **The ModRM rule in §4.2.** The bytes are observed; the manual text behind the
  `mod=00`/`r/m=101` rule was not re-read, so the *reason* is recorded as
  `inference`, not as a cited source.
- **A memory operand that is genuinely one field.** None was found in these
  three ISAs for this slice. If one appears (a compressed load's `uimm` still
  carries a destination, so it is not one), the rule is "one value, one slot",
  not "memory operands are always decomposed".

## 7. Reproduction

```powershell
$env:PYTHONIOENCODING="utf-8"
# §3 vectors
llvm-mc -triple=riscv64 -filetype=obj rv64.s -o rv64.o
llvm-objcopy -O binary --only-section=.text rv64.o rv64.bin
# §4 vectors
llvm-mc -triple=x86_64 -filetype=obj x86.s -o x86.o
llvm-objcopy -O binary --only-section=.text x86.o x86.bin
# §5 vector
llvm-mc -triple=aarch64 -filetype=obj a64.s -o a64.o
llvm-objcopy -O binary --only-section=.text a64.o a64.bin
# the table and the fixtures
python research\evidence\experiments\EXP-0010\generate_rv64.py
cd prototype; cargo test --workspace
```

The fixture gate is the independent check: `RV-P3-ld-sd-base-offset` compares
the materializer's bytes with `expected.bin`, which was copied from the oracle's
`.text` and is pinned by `oracle.json`'s `output_sha256`.
