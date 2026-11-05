# EXP-0045 -- VEX.256 memory rows at `L = 1`

- Date: 2026-11-05
- Question: which bytes do the VEX.256 memory shapes use, is the displacement
  compressed, and do the two base windows and the four-bit vector slot carry
  over from the VEX.128 rows unchanged?
- Toolchain: `llvm-mc`/`llvm-objcopy` 23.1.2
- Definition: `definitions/x86_64/0.16.0.json`
  (`sha256:64ea1acf467afb2f858a5cb2967839445a5ffecac164a5f1b61931cb8fb3b99e`)
- Fixture oracle: `fixtures/x86_64/positive/X86-P20-vex-ymm-memory.oracle.json`
- Source: `research/evidence/experiments/EXP-0045/P20.asm`
- Decision: `ADR-0043`

## 1. The measurement

`llvm-mc -triple=x86_64 -show-encoding` on 2026-11-05. No directive is needed:
the `ymm` operand selects VEX.256, because `zmm` does not exist in VEX and
`xmm` selects the 128-bit row.

| Source | Bytes | Length |
|---|---|---|
| `vmovaps (%rax), %ymm0` | `c5 fc 28 00` | 4 |
| `vmovaps %ymm0, (%rax)` | `c5 fc 29 00` | 4 |
| `vmovaps 32(%rax), %ymm0` | `c5 fc 28 40 20` | 5 |
| `vmovaps %ymm0, -32(%rax)` | `c5 fc 29 40 e0` | 5 |
| `vmovaps 127(%rax), %ymm0` | `c5 fc 28 40 7f` | 5 |
| `vmovaps -128(%rax), %ymm0` | `c5 fc 28 40 80` | 5 |
| `vmovaps 128(%rax), %ymm0` | `c5 fc 28 80 80 00 00 00` | 8 |
| `vmovaps %ymm0, -129(%rax)` | `c5 fc 29 80 7f ff ff ff` | 8 |
| `vmovaps (%rax), %ymm8` | `c5 7c 28 00` | 4 |
| `vmovaps %ymm8, (%rax)` | `c5 7c 29 00` | 4 |
| `vmovaps (%r8), %ymm0` | `c4 c1 7c 28 00` | 5 |
| `vmovaps %ymm0, (%r8)` | `c4 c1 7c 29 00` | 5 |
| `vmovaps 32(%r8), %ymm0` | `c4 c1 7c 28 40 20` | 6 |
| `vmovaps %ymm0, -32(%r8)` | `c4 c1 7c 29 40 e0` | 6 |
| `vmovaps 127(%r8), %ymm0` | `c4 c1 7c 28 40 7f` | 6 |
| `vmovaps -128(%r8), %ymm0` | `c4 c1 7c 28 40 80` | 6 |
| `vmovaps 128(%r8), %ymm0` | `c4 c1 7c 28 80 80 00 00 00` | 9 |
| `vmovaps %ymm0, -129(%r8)` | `c4 c1 7c 29 80 7f ff ff ff` | 9 |
| `vmovaps (%r8), %ymm8` | `c4 41 7c 28 00` | 5 |
| `vmovaps %ymm8, (%r8)` | `c4 41 7c 29 00` | 5 |
| `vmovaps 32(%r8), %ymm8` | `c4 41 7c 28 40 20` | 6 |
| `vmovaps %ymm8, -32(%r8)` | `c4 41 7c 29 40 e0` | 6 |
| `vmovaps %ymm8, 128(%r8)` | `c4 41 7c 29 80 80 00 00 00` | 9 |
| `vmovaps 128(%r8), %ymm8` | `c4 41 7c 28 80 80 00 00 00` | 9 |

`llvm-mc -disassemble` on `probes.txt` returns each source line unchanged,
including `(%rax), %ymm8` and `(%r8), %ymm8`, so the bytes are not a different
width or a different base. The twin of every 128-bit VEX memory row is the same
byte string with `P1` changed from `f8`/`78` to `fc`/`7c`.

## 2. VEX has no compressed displacement

The `disp8` byte is the plain signed offset, unlike EVEX `disp8*N`:

| Source | Byte | `llvm-mc -disassemble` |
|---|---|---|
| `vmovaps 32(%rax), %ymm0` | `20` | `32(%rax)` |
| `vmovaps 127(%rax), %ymm0` | `7f` | `127(%rax)` |
| `vmovaps -128(%rax), %ymm0` | `80` | `-128(%rax)` |
| `vmovaps 128(%rax), %ymm0` | `80 00 00 00` | `128(%rax)` |

`32` is content `32`, not content `1` times a unit. There is no `disp8x32` slot
on these rows and no `EC-39` fact: the four `disp8` rows use the same
`{ "signed": true, "bits": 8, "align_bits": 0 }` carrier as the `0.3.0` GPR
rows (`EC-02`, `EC-35`).

## 3. The two base windows are the VEX.128 windows

The two-byte prefix has no `B̄`. The base is the three low `ModRM.rm` bits, so
`%r8` is not encodable in that row; the three-byte prefix adds `B̄` at bit 13
inverted and moves `ModRM` one byte later. The exclusions are unchanged from
`0.11.0`/`0.12.0`:

| Window | `disp` rows | no-displacement rows |
|---|---|---|
| two-byte `C5 FC` | `%rsp` (`4`) | `%rsp`/`%rbp` (`4, 5`) |
| three-byte `C4 C1 7C` | `r8`–`r15` minus `%r12` (`0…7, 12`) | `r8`–`r15` minus `%r12`/`%r13` (`12, 13`) |

`vmovaps 32(%r8), %ymm0` is `c4 c1 7c 28 40 20`: `B̄` is `0` and the low three
bits of `r8` are `0`. The same instruction with `%rax` is `c5 fc 28 40 20`
(four bytes fewer because the prefix is two bytes and there is no `B̄`).

## 4. The vector slot is still four bits

`R̄` at bit 15 inverted plus `ModRM.reg` reaches `ymm0`–`ymm15` in both windows.
`vmovaps (%rax), %ymm8` is `c5 7c 28 00` (`R̄` flips, `P1` becomes `7c`), and
`vmovaps (%r8), %ymm8` is `c4 41 7c 28 00` (`B̄` and `R̄` both carry in byte 1).
`ymm16` needs a fifth bit and is rejected; the row never truncates it.

## 5. The definition rows

`0.16.0` appends the twelve rows enumerated in `ADR-0043`, in the same order as
the VEX.128 block: `disp8` load, `disp32` load, `disp8` store, `disp32` store,
no-displacement load, no-displacement store, then the same six with the
three-byte base-extended prefix. The vector slot is `x86.ymm`/`ymm` at
`[15,1]` inverted + `[27,3]` (low base) or `[15,1]` inverted + `[35,3]` (high
base); the base is `[24,3]` or `[13,1]` inverted + `[32,3]`; the displacement
is `[32,8]`/`[32,32]` or `[40,8]`/`[40,32]`. There is no new `EC` row.

## 6. The fixture

`X86-P20-vex-ymm-memory` is twenty-four instructions and 144 bytes, one for
every row and every window: the four `disp8` ends at each base window, the
`disp32` promotions at `128`/`-129`, `ymm8` with a low base, and base `r8`
with `ymm8` so both extension bits carry. `expected.bin` comes from `llvm-mc` +
`llvm-objcopy`, never from our materializer; the oracle's `input_sha256` is
`P20.asm` (`5d120f3f…`) and its `output_sha256` is the 144-byte `.text`
(`a42f3ec7…`).

## 7. Negative coverage

The new rows are pinned by six negative fixtures:

- `N01am` names `x86:vmovaps/ymm-base-ext-disp8/vex` against `0.15.0`:
  `E-FORM-001`, the version boundary for the three-byte window. `N01al`
  remains the same boundary for the two-byte
  `x86:vmovaps/ymm-base-disp8/vex`.
- `N02q` passes a `zmm` operand to `x86:vmovaps/ymm-base-disp8/vex`:
  `E-OPERAND-001` on `kind` and `target_type`, because width is part of the
  kind.
- `N14s` passes `ymm16` to a four-bit VEX memory slot: `E-OPERAND-004`.
- `N16r` uses `%rbp` on `x86:vmovaps/ymm-base/vex`: `E-RANGE-004`, because
  `mod=00` spends `r/m=101` on the RIP-relative escape.
- `N16s` uses `%r12` on `x86:vmovaps/ymm-base-ext-disp8/vex`: `E-RANGE-004`,
  because its low three bits are the SIB-forcing `%rsp` value.
- `N03f` passes content `128` to `x86:vmovaps/ymm-base-disp8/vex`:
  `E-RANGE-001`, one past the signed byte. VEX cannot promote to a compressed
  unit; the plan must name the `disp32` row.
