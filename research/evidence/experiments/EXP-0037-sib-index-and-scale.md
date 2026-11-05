# EXP-0037 — x86-64 `base + index*scale + disp`, and the `REX.X` bit

- Date: 2026-11-05
- Question: how do an index register and a scale reach a `SIB` byte, which bit
  extends the index, and what happens to an index field of `100`?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.8.0.json`
  (`sha256:e55f694ae29e90854c8352aba60202cbd060d6333aff2a69b2e54978910155f5`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P12-base-index-scale.oracle.json`
- Source: `research/evidence/experiments/EXP-0037/P12.asm`
- Decision: `ADR-0035`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05:

| Source | Bytes | `REX` | `ModRM` | `SIB` |
|---|---|---|---|---|
| `movq 8(%rax,%rcx,1), %rdx` | `48 8b 54 08 08` | `0100 1000` `W=1` | `01 010 100` | `00 001 000` |
| `movq 8(%rax,%rcx,2), %rdx` | `48 8b 54 48 08` | `W=1` | `01 010 100` | `01 001 000` |
| `movq 8(%rax,%rcx,4), %rdx` | `48 8b 54 88 08` | `W=1` | `01 010 100` | `10 001 000` |
| `movq 8(%rax,%rcx,8), %rdx` | `48 8b 54 c8 08` | `W=1` | `01 010 100` | `11 001 000` |
| `movq 8(%r8,%r9,2), %r10` | `4f 8b 54 48 08` | `W=1 R=1 X=1 B=1` | `01 010 100` | `01 001 000` |
| `movq 8(%rax,%r12,4), %rdx` | `4a 8b 54 a0 08` | `W=1 X=1` | `01 010 100` | `10 100 000` |
| `movq 8(%r12,%r13,8), %r15` | `4f 8b 7c ec 08` | `W=1 R=1 X=1 B=1` | `01 111 100` | `11 101 100` |
| `movq 8(%r13,%r12,8), %rdx` | `4b 8b 54 e5 08` | `W=1 X=1 B=1` | `01 010 100` | `11 100 101` |
| `movq 128(%r8,%r14,2), %r11` | `4f 8b 9c 70 80 00 00 00` | `W=1 R=1 X=1 B=1` | `10 011 100` | `01 110 000` |
| `movq %rdx, 8(%rax,%rcx,4)` | `48 89 54 88 08` | `W=1` | `01 010 100` | `10 001 000` |
| `movq %r15, 128(%r12,%r13,8)` | `4f 89 bc ec 80 00 00 00` | `W=1 R=1 X=1 B=1` | `10 111 100` | `11 101 100` |
| `movq 8(%rsp,%rcx,1), %rdx` | `48 8b 54 0c 08` | `W=1` | `01 010 100` | `00 001 100` |
| `movq 8(%rax,%rbp,1), %rdx` | `48 8b 54 28 08` | `W=1` | `01 010 100` | `00 101 000` |

`r/m = 100` is the whole of the shape: it announces the `SIB` byte, and the
byte is `scale` (bits 7–6), `index` (bits 5–3, extended by `REX.X`) and `base`
(bits 2–0, extended by `REX.B`). The register in `ModRM.reg` is the destination
or the source, as in every other `mov` row, and the displacement follows at
byte 4 (`mod = 01`) or bytes 4–7 (`mod = 10`).

## 2. The scale is field content

The same `ModRM` byte (`54`) with the same base and index produces four `SIB`
top bytes (`08`, `48`, `88`, `c8`). Nothing else in the instruction changes, so
the scale is a two-bit field, not a form and not a fourth row per multiplier:
`00` is ×1, `01` is ×2, `10` is ×4 and `11` is ×8. The multiplier the
programmer writes (`1`, `2`, `4`, `8`) is the derived value `1 << content`.

The plan therefore carries the content. Carrying the multiplier would make the
materializer compute `1 << value` before writing the field — arithmetic that
changes encoded bits, which is an implicit encoding step (`INV-02`) — and it
could not express ×16 at all, because a two-bit field has no fourth multiplier.
`N03c` passes `8`, the multiplier of the last column, and gets `E-RANGE-001`
with `min = 0`, `max = 3`, `target_type = scale2`.

## 3. `SIB.index = 100` means "no index"

Two measurements decide the index's domain:

- `llvm-mc` rejects `movq 8(%rax,%rsp,1), %rdx` with `invalid base+index
  expression`, so `%rsp` is not an index register at all.
- `48 8b 54 20 08` — the bytes an encoder would produce for that source by
  copying `4` into the index field with `REX.X = 0` — decodes as
  `movq 8(%rax,%riz), %rdx`. The index disappears and the instruction silently
  means `[rax + 8]`.

`%r12` is the opposite case: its low three bits are also `100`, but with
`REX.X = 1` the field is `%r12` (`4a 8b 54 a0 08`). So the exclusion is exactly
`4`, and `4b 8b 54 e5 08` (`index = 100`, `REX.X = 1`, `base = 101`,
`REX.B = 1`) is `movq 8(%r13,%r12,8), %rdx`. The base has no exclusion at all:
`r/m = 100` already announced the `SIB` byte, so a `SIB` base of `100` is
`%rsp`/`%r12`, not "no base".

## 4. The oracle

`P12.asm` is thirteen `mov` mnemonics with no hand-assembled bytes. `.text` is
71 bytes and the plan emits no record. Output SHA-256
`6a9da912ac091b0d6966eb550782cdad456f933603bcc5dc43153919a9a00d87`.

Every displacement in the source fits the width of the form the plan names
(`8` for `disp8`, `128` for `disp32`), so `llvm-mc`'s own choice of `mod`
coincides with the named form; no promotion is being relied on.

## 5. The rejections

`N16i` names `0.8.0`'s `x86:mov/r64-base-index-disp8/legacy` with
`index.reg = 4`, the "no index" encoding. The value fits the 4-bit field, so the
plan is rejected by the exclusion before any byte is written:

```text
E-RANGE-004  /instructions/0/operands/2/payload/reg
             target_type=sib_index value=4 excluded=[4]
```

`N03c` is the scale end: `payload.value = 8` on `scale2` is `E-RANGE-001`
(`min = 0`, `max = 3`), not a truncation to `0` (×1) and not a third bit that
would land in the displacement byte.

`N01ad` names the same form against `0.7.0`, where the row does not exist:
`E-FORM-001`. This is the version boundary, not a silent fallback to the
base+disp rows.

## 6. What this does not claim

- `mod = 00` (a `SIB` row with no displacement) is not a v0 row. `r13` as a base
  under `mod = 00` is the `r/m = 101` RIP-relative collision, and a `SIB` base of
  `101` under `mod = 00` means "no base" with a `disp32`; both are unmeasured
  here.
- A base-only `SIB` row (`index = 4` as a legal value) is not a v0 form: the
  `SIB` byte exists for the index, and `index = 4` is the encoding of "none".
- The 8-bit and 16-bit rows, the SSE/VEX/EVEX memory operands and the `0x67`
  address-size prefix are unchanged and untested here.
- No measurement was made on a second host or toolchain; this record is one
  `llvm-mc` 23.1.2 run on one Windows host.
