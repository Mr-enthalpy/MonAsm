# EXP-0025 — AArch64 literal load: `imm19`, no base register

- Date: 2026-11-04
- Question: what bits name `LDR (literal)`, how is its displacement referenced
  and scaled, which node variants exist, and does a store literal exist?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: none read for this slice. The bytes, the field range and the
  scaling come from the MRS node and the assembler. Whether register 31 is `sp`
  or `xzr` is not tested here, because it changes no bit.

## 1. The node

`LDR_64_loadlit` is the one load in the `0.1.0`…`0.14.0` table with no `Rn`.
`start+width` counts from bit 0 of the 32-bit word:

### `LDR_64_loadlit` → `aarch64:ldr/x64-imm19`

| Field | start+width | Value | Our use |
|---|---|---|---|
| `opc` | 30+2 | `01` | fixed — `LDR Xt` |
| — | 28+2 | `01` | fixed |
| — | 27+1 | `1` | fixed |
| `VR` | 26+1 | `0` | fixed (no SIMD/FP) |
| — | 25+1 | `0` | fixed |
| — | 24+1 | `0` | fixed |
| `imm19` | 5+19 | `xxxxxxxxxxxxxxxxxxx` | slot `target`, signed field content |
| `Rt` | 0+5 | `xxxxx` | slot `dest` |
| `Rn` | — | absent | no `base` slot exists |

The fixed bits are `0x58000000`. Unlike the offset rows of `EXP-0015` and
`EXP-0024`, bits 11–10 and bit 21 are not fields here: there is no addressing
kind to choose, because the address is the PC and the displacement is the only
variable part besides the destination. The node's operand list is empty, so the
`Rt`/`imm19` pairing is asserted by the generator, not by an MRS operand.

**The absence scan.** Every node name containing `loadlit` in the drop is
returned by the same walk:

```text
LDRSW_64_loadlit  LDR_32_loadlit  LDR_64_loadlit  LDR_D_loadlit
LDR_Q_loadlit  LDR_S_loadlit  PRFM_P_loadlit   (+ a non-instruction `loadlit` container)
```

There is no `STR_*_loadlit`, and a direct lookup of `STR_64_loadlit` returns
zero nodes. Four of the seven loads differ by `opc` under the same name: `01` is
`LDR Xt`, `00` is `LDR Wt`, `10` is `LDRSW Xt` and `11` is `PRFM`; `VR = 1` is
the `S`/`D`/`Q` family. `opc` therefore selects the destination class and the
operation, which is a `form_id` decision (`INV-02`), not an operand value.

## 2. The field, measured

One instruction per run at offset 0, `llvm-mc -triple=aarch64 -filetype=obj`,
then `llvm-objcopy -O binary --only-section=.text`:

| Source | Word | `imm19` | Reading |
|---|---|---|---|
| `ldr x0, #0` | `0x58000000` | 0 | loads from the instruction's own address |
| `ldr x0, #4` | `0x58000020` | 1 | the field counts 4-byte units |
| `ldr x0, #-4` | `0x58ffffe0` | −1 | two's complement in the field |
| `ldr x0, #1048572` | `0x587fffe0` | 262143 | top of the positive range |
| `ldr x0, #-1048576` | `0x58800000` | −262144 | bottom of the range |
| `ldr x0, #1048576` | — | — | **rejected** |
| `ldr x0, #-1048580` | — | — | **rejected** |
| `ldr x0, #2` | — | — | **rejected** |
| `ldr x0, #-2` | — | — | **rejected** |
| `ldr x0, #6` | — | — | **rejected** |

Every rejection reads `expected label or encodable integer pc offset`: the
assembler does not separate "outside 19 bits" from "not a multiple of 4". `#12`
at offset 4 is `0x58000060` (`imm19 = 3`), so the field value is not the byte
displacement but the displacement divided by four, stated at the site.

**The reference is the instruction address, not the end.** A `ldr x0` with its
label 20 bytes ahead assembles to `0x580000a0`, i.e. `imm19 = 5`, not 6. That is
`pcrel_begin`, the same reference the `b`/`bl`/`b.cond` rows use, and it is why
the byte range is `−1048576 … +1048572`: the upward end is 262143 words, one
word short of a round MiB.

**The other `opc` values are different rows.** At offset 0:

| Source | Word | What `opc` selects |
|---|---|---|
| `ldr w0, #4` | `0x18000020` | `LDR Wt` — 32-bit destination |
| `ldrsw x0, #4` | `0x98000020` | `LDRSW Xt` — sign-extending load |
| `ldr q0, #4` | `0x9c000020` | `VR = 1`, SIMD/FP |
| `prfm pldl1keep, #8` | `0xd8000040` | `PRFM` — prefetch, no destination register |

**There is no store literal.** `str x0, #4` and `str x0, lit` both fail with
`invalid operand for instruction`. The store side of the literal kind is not a
row this table is postponing; it does not exist in the ISA surface the drop and
the assembler agree on.

## 3. The vector

Input (LF, trailing newline; 104 bytes,
`sha256:4826ea6ba480496ca463852643e33a63f1df26565114de561451f62d88f45fe8`):

```text
.L1:
  ldr x0, .L2
  ldr x1, #-4
.L2:
  ldr x2, #1048572
  ldr x3, #-1048576
  ldr x4, .L1
  ldr x5, #4
```

`.L1` is offset 0 and `.L2` is offset 8, so the two symbol targets are the two
instruction addresses the plan's symbols name. `llvm-readobj -r` prints an empty
relocation list: `llvm-mc` resolves local labels itself, and no linker is
involved.

| Offset | Bytes | Word | `llvm-objdump` | Plan `imm19` |
|---|---|---|---|---|
| 0 | `40 00 00 58` | `0x58000040` | `ldr x0, 0x8` | `2` (fixup to `.L2`) |
| 4 | `e1 ff ff 58` | `0x58ffffe1` | `ldr x1, 0x0` | `-1` |
| 8 | `e2 ff 7f 58` | `0x587fffe2` | `ldr x2, 0x100004` | `262143` |
| 12 | `03 00 80 58` | `0x58800003` | `ldr x3, 0xfffffffffff0000c` | `-262144` |
| 16 | `84 ff ff 58` | `0x58ffff84` | `ldr x4, 0x0` | `-4` (fixup to `.L1`) |
| 20 | `25 00 00 58` | `0x58000025` | `ldr x5, 0x18` | `1` |

Output: 24 bytes,
`sha256:a9b2f62fe38b21cdabce3a7ba3136ba240fda4dd80f25e9b1f628d556324ae37`,
`bytes_hex` `40000058e1ffff58e2ff7f580300805884ffff5825000058`.

The vector pins each decision independently:

- the symbol path at a forward (`2`) and a backward (`-4`) target, through two
  different sites, so an end-versus-begin reference slips in either direction;
- plain field content at `-1` and `1`, which no other row in the vector produces;
- both ends of the signed 19-bit field (`262143`, `-262144`);
- `Rt` in the low five bits at six distinct registers, so a placement slip is
  visible in every word.

## 4. What this fixes, and what it does not

Fixes:

- the template `0x58000000` and the two slot placements, derived from the MRS
  fields by the generator;
- the statement that `imm19` is signed field content in 4-byte units and that the
  byte displacement is the fixup's `scale(2)`, not a slot transform;
- the reference rule: `pcrel_begin`, measured with a label 20 bytes ahead;
- the operand list: `dest`, `target`, no `base`;
- the negative evidence: `0.13.0` has no such row (`E-FORM-001`), a field value
  of 262144 is `E-RANGE-002`, and a fixup displacement of 2 bytes is
  `E-RANGE-003`.

Does not fix:

- **register offset** (`Rm`/`option`/`S`, bit 21 = 1): a second register, a shift
  kind and the `S` bit, still absent (`E-FORM-001`, `N01b`).
- **the `w`, `LDRSW`, `PRFM` and SIMD/FP literal loads**: `opc` and the
  destination class change, so each is its own row.
- **a store literal**: no node and no accepted spelling.
- **data in a code section**: the vector's labels are instruction addresses, so
  no output fragment beyond `instruction` is exercised; a plan whose literal
  names data bytes in `.text` is an output-contract question, not a row.

## 5. Result

The row ships in `definitions/aarch64/0.14.0.json`, which repeats the 135
`0.13.0` forms and adds one:

```text
definition  definitions/aarch64/0.14.0.json
namespace   monasm.isa.aarch64
version     0.14.0
forms       136
digest      sha256:a90ceac19824fbb00731e040346daa191973652e58522fab72336e24f769a5ba
```

`EXP-0008` §6 is the authoritative copy of the digest.

Our materializer emits the 24 bytes above, with two `pcrel_begin` + `scale(2)`
fixup records resolved in place, and rejects:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P16-loadlit` | six instructions, one form | 24 bytes, `sha256:a9b2f62f…` |
| `N01o-absent-loadlit-form` | `ldr/x64-imm19` against `0.13.0` | `E-FORM-001` |
| `N04d-loadlit-imm19-out-of-range` | `imm19 = 262144` | `E-RANGE-002`, `min -262144`, `max 262143` |
| `N20-loadlit-fixup-misaligned` | symbol at offset 2, displacement 2 bytes | `E-RANGE-003`, `required_align 2`, `value 2` |

The alignment split is our own: the assembler reports `#2` and `#1048576` with
one message, and `OD-09` puts alignment on the pre-transform value and range on
the post-transform value, so the two failures stay two diagnostics (`ADR-0023`
decision 6).
