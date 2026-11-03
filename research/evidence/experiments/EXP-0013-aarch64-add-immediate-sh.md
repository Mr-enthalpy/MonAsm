# EXP-0013 — AArch64 `add` immediate: `sh`, the field, and the scaled literal

- Date: 2026-11-04
- Question: how does `fmp/0.1` express `add Xd, Xn, #imm, lsl #12` without a
  slot-level transform, and what does the oracle do when the plan does not name
  the form?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj`/`ld.lld`
  23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`)
- Semantics source: Arm A64 ISA, `ADD (immediate)`, revision `2026-03_rel`
  (2026-03-26), read at the public mirror
  `https://www.scs.stanford.edu/~zyedidia/arm64/add_addsub_imm.html`; the
  canonical copy is Arm's `DDI0602` page on `developer.arm.com`. Facts are
  restated; the page's text is not copied into this repository.

## 1. What the architecture states

The page gives the 32-bit field map `sh` at bit 22 and `imm12` at bits 10–21,
and three statements that matter here:

- the assembler symbol `<imm>` is "an unsigned immediate, in the range 0 to
  4095, encoded in the `imm12` field";
- the optional shift is encoded in `sh`: `0` is `LSL #0`, `1` is `LSL #12`;
- the decode is `imm = if sh == '0' then Zeros{12}::imm12 else imm12::Zeros{12}`.

So the architectural operand is a 12-bit field plus a one-bit shift. `sh = 1`
does not widen the field; it moves the field's twelve bits up by twelve.

The MRS node `ADD_64_addsub_imm` states the same layout and nothing about
meaning: `sh` is `x` at `22+1`, `imm12` is twelve `x` at `10+12`, and the
package omits descriptive content (`research/external/arm-mrs/README.md`).
`EXP-0008` generation already pins `sh = 0` for the `-lsl0` row.

## 2. What `llvm-mc` does with the plain literal

One instruction per object, `llvm-mc -triple=aarch64 -filetype=obj`, bytes read
back with `llvm-objcopy -O binary --only-section=.text`:

| Source line | Result | Word |
|---|---|---|
| `add x0, x1, #0xfff` | accepted, `sh = 0`, `imm12 = 0xfff` | `0x913ffc20` |
| `add x0, x1, #0x800` | accepted, `sh = 0`, `imm12 = 0x800` | `0x91200020` |
| `add x0, x1, #0x1000` | accepted, `sh = 1`, `imm12 = 0x1` | `0x91400420` |
| `add x0, x1, #0x1ffc` | **rejected** | — |
| `add x0, x1, #0x1001` | **rejected** | — |
| `add x0, x1, #0xfff000` | accepted, `sh = 1`, `imm12 = 0xfff` | `0x917ffc20` |
| `add x0, x1, #0x1000000` | **rejected** | — |
| `add x0, x1, #0xfff, lsl #12` | accepted, same word as `#0xfff000` | `0x917ffc20` |
| `add x0, x1, #0xfff000, lsl #12` | **rejected** | — |
| `add x0, x1, #0x1000, lsl #12` | **rejected** | — |

Two observations, both needed by the decision:

1. The representable literals are exactly `[0, 4095]` and
   `{k << 12 | 1 <= k <= 4095}`. `0x1ffc` and `0x1001` are in neither set and
   are rejected rather than rounded.
2. With a plain literal, the assembler **chooses `sh` from the value**:
   `#0x1000` becomes `sh = 1`, while `#0xfff` stays `sh = 0`. With an explicit
   `lsl #12`, the operand is field content again and must be in `[0, 4095]`.

Observation 2 is the boundary this project cannot cross: an encoder that turns
`0x1000` into a different form has selected an encoding form from an operand
value (`INV-02`). `llvm-mc` is allowed to; a materializer executing a frozen
plan is not.

## 3. The vector

Input, one line each (LF, trailing newline, two leading spaces kept; 116 bytes,
`sha256:d2a5b611988ac5abf0d379aa3ae78a5218a75f0509c053e3bdf8f7a7ae210485`):

```text
  add x0, x1, #0x1, lsl #12
  add x0, x1, #0x123, lsl #12
  add x2, x3, #0xfff, lsl #12
  add x0, x1, #0x0, lsl #12
```

Command: `llvm-mc -triple=aarch64 -filetype=obj A64-P2-add-imm12-lsl12.s -o out.o`
then `llvm-objcopy -O binary --only-section=.text out.o out.bin`.

| Offset | Bytes | Word | `llvm-objdump` |
|---|---|---|---|
| 0 | `20 04 40 91` | `0x91400420` | `add x0, x1, #0x1, lsl #12 // =0x1000` |
| 4 | `20 8c 44 91` | `0x91448c20` | `add x0, x1, #0x123, lsl #12 // =0x123000` |
| 8 | `62 fc 7f 91` | `0x917ffc62` | `add x2, x3, #0xfff, lsl #12 // =0xfff000` |
| 12 | `20 00 40 91` | `0x91400020` | `add x0, x1, #0x0, lsl #12 // =0x0` |

Output: 16 bytes,
`sha256:f5c58e6e124afdded3271dce68c3f2282ea8f6521889f08b5ad390f76fb6d0b7`.

The last line is the one that settles the shape: `#0x0, lsl #12` encodes
`sh = 1`, because the *form* was named, not inferred from the value. The same
numeric value without the shift would be `0x91000020` (`sh = 0`).

## 4. What this fixes, and what it does not

Fixes:

- the new form's template: the `-lsl0` word with bit 22 set
  (`0x91000000` → `0x91400000`), `imm12` still at `[10,12]`;
- the operand rule: `{ "value": n }` is field content in `[0, 4095]`, and the
  scaled literal `n << 12` is a property of the form, exactly as `bl`'s `imm26`
  is a count of instructions rather than bytes (`07_definition_format.md` §8.3);
- the rejection evidence: `N18a` states `0x1000` on the `-lsl0` form and must
  get `E-RANGE-001`, not a silent form switch (what `llvm-mc` does);
  `N18b` states `0x123000` on the `-lsl12` form and must be rejected the same
  way, because it is not field content.

Does not fix:

- the *address* meaning of a scaled low half, though its record path is now
  measured (§5): the low half fills the same 12-bit field, and the instruction's
  `sh = 1` then adds that field at bit 12, so the pair is not `S + A`. `A64-P2`
  does not need a `:lo12:` in the scaled form, and none exists.
- the `sub` immediate form. It has the same `sh` field and the same decision,
  so it needs no separate experiment; it needs its own `form_id` when a slice
  asks for it.

## 5. The scaled low half at the record and link level

Question: a future plan might put a `:lo12:` in the `-lsl12` form. What does the
toolchain do? Two inputs, the same symbol `ext = 0x123450`, linked with
`ld.lld --image-base=0 -Ttext=0 --defsym=ext=0x123450`:

| Input (after `adrp x0, ext`) | `llvm-readobj -r` | Linked word at +4 |
|---|---|---|
| `add x0, x0, #:lo12:ext` | `ADR_PREL_PG_HI21` at `0x0`, `ADD_ABS_LO12_NC` at `0x4` | `91114000` (`add x0, x0, #0x450`) |
| `add x0, x0, #:lo12:ext, lsl #12` | the same two kinds at the same sites | `91514000` (`add x0, x0, #0x450, lsl #12`) |

- The modifier needs the `#` when a shift follows: `:lo12:ext, lsl #12` is
  rejected ("invalid operand"), `#:lo12:ext, lsl #12` is accepted. That is an
  assembler spelling rule, not an architecture rule.
- The relocation kind does not change and the linker writes the same field value
  `0x450`; the instruction then shifts it, so the addend is `0x450000`.
  `0x123000 + 0x450000 = 0x573000`, which is **not** `0x123450`. A scaled low
  half is therefore not a drop-in replacement for the `adrp` + `:lo12:` address
  sequence; a slice that wants one must say what the addend means.

Commands and hashes (LF, two leading spaces per line, trailing newline):

```text
link.s  (2 lines, 49 B,  sha256:8e0b467418b8ab3b016b78d82624945a155ade4c976d250c2b2d5cebce207cb8)
link0.s (2 lines, 40 B,  sha256:70578608bfcdbab9d916ecbb9c65de79892d577ae2fe35a7bfa589e2410a964a)
link.o  sha256:af3263c5f26ccc8d699c2a4ef5c1481d14f395e88d9a72a0c147f1332d9e8bb2
link0.o sha256:c4b6fb3e7636aab994bdc111ac9b3a3ffef959e0e009563e997dab3a75d3d263
link.bin  (8 B) sha256:e8420689de9b0ee507fdede2bc032d39b2dbba40ebe686de5cc845723c80205f
link0.bin (8 B) sha256:7a125cff28e065a73d472d6f8fe70a52bfbe9f9c591b3801e24bf910b3d08c3d
```

`llvm-mc` 23.1.2, `ld.lld` and `llvm-readobj` all from the same 23.1.2 install.
