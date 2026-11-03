# EXP-0001 — XirAsm encoder boundary probes

- Date: 2026-11-03
- Subject: XirAsm `0.3.5`, revision `3ee8a439f5ba`
- Toolchain: Zig `0.17.0`, LLVM `23.1.2`
- Basis: **experiment** (commands and raw output below)
- Purpose: settle gate G1 with observed behaviour, not with source reading alone

This record backs the findings in `docs/fmp-v0/90_boundary_audit.md`. Every
number quoted there must appear here or in the source citations there.

## 0. Build

```text
cd research/external/XirAsm
zig build -Doptimize=ReleaseSafe      # exit 0
zig-out/bin/xirasm.exe                3,227,136 bytes
zig-out/bin/xirasm.pdb                6,758,400 bytes
```

The build produced no diagnostics on stdout/stderr; `build.log` contains only
`exit=0`. The extracted snapshot has no `.git` directory (it came from the
`codeload` tarball), so the revision is the one pinned in
`research/evidence/source_index.md`, not a local `HEAD`.

Note: `zig build` also emitted a default step set that included the repository's
own checkers, so the binary is the same one the project tests against.

## 1. How the probes were run

Sources are flat-binary inputs of the form `origin(0)` plus `x86.use64()`, or
`riscv.use64();`, assembled with:

```text
xirasm <src>.xir -o <out>.bin --no-progress
```

Bytes are printed as lowercase hex, in file order. Oracle comparison used:

```text
llvm-mc -triple=x86_64 -x86-asm-syntax=intel -show-encoding
llvm-mc -triple=aarch64 -show-encoding
llvm-mc -triple=riscv64 -mattr=+c -show-encoding
```

The probe scripts live in `research/external/xirasm-probe/` (disposable zone, not
committed). They only wrap the above; no transformation of the output.

## 2. x86-64: branch form selection (EC-03, N04)

| Source | Bytes | Length | LLVM oracle |
|---|---|---|---|
| `jmp 0x10` | `eb 0e` | 2 | n/a (LLVM rejects numeric branch targets) |
| `jmp short 0x10` | `eb 0e` | 2 | n/a |
| `jmp near 0x10` | `e9 0b 00 00 00` | 5 | n/a |
| `jne 0x10` | `75 0e` | 2 | n/a |
| `jne short 0x10` | `75 0e` | 2 | n/a |
| `jne near 0x10` | `0f 85 0a 00 00 00` | 6 | n/a |

**Observation.** The unqualified mnemonic produces the rel8 form. The source did
not ask for rel8; the encoder selected it. `jmp` and `jne` behave the same way.

### 2.1 Upward promotion

| Source | Bytes | Length | Arithmetic check |
|---|---|---|---|
| `jmp 0x1000` | `e9 fb 0f 00 00` | 5 | `0x1000 - 5 = 0xFFB` ✓ |
| `jmp 0x100000` | `e9 fb ff 0f 00` | 5 | `0x100000 - 5 = 0xFFFFB` ✓ |

**Observation.** When rel8 does not fit, the same unqualified mnemonic silently
becomes rel32. Encoding size therefore depends on the target value: the same
`form` is not even stable across one plan.

### 2.2 Numeric `short` targets: base and truncation

| Source | Bytes | What it should be |
|---|---|---|
| `jmp short 0x7f` | `eb 7d` | `0x7f - 2 = 125` ✓ |
| `jmp short 0x81` | `eb 7f` | `0x81 - 2 = 127` ✓ |
| `jmp short 0x82` | `eb 80` | 128 is out of range; **wrapped to −128** |
| `nop` + `jmp short 0x82` | `90 eb 80` | next IP is 3, so `0x82 - 3 = 127` → `eb 7f` |
| `nop` + `jmp short 0x81` | `90 eb 7f` | next IP is 3, so `0x81 - 3 = 126` → `eb 7e` |
| `nop` + `jmp short 0x1000` | `90 eb fe` | `0x1000 - 3 = 4093` → out of range, must reject |
| `origin(0x3005)` + `jmp short 0x3010` | `eb 0e` | next IP is `0x3007`, so displacement is `9` → `eb 09` |

Two separate defects are visible:

1. **No range check on the numeric path.** `jmp short 0x82` and
   `jmp short 0x1000` are truncated to 8 bits instead of being rejected.
2. **The displacement base ignores the instruction's offset.** With
   `origin(0x3005)` the encoder behaves as if the branch sat at offset 0 and used
   `0x3002` as the next IP. Every measured case is consistent with
   `disp = target - (origin + instruction_size)`, independent of preceding bytes.

The mechanism is an inference: the frontend resolves a numeric target to a
concrete displacement before layout, so no `Fixup` is created and the range check
in the fixup materializer never runs (see §2.3).

### 2.3 Label targets: base and rejection are correct

| Source | Bytes | Note |
|---|---|---|
| `jmp short tgt` / `tgt: nop` | `eb 00 90` | displacement 0 ✓ |
| `nop` / `jmp short lbl` / `lbl: nop` | `90 eb 00 90` | base follows real layout ✓ |
| `jmp short far_lbl` + 200 `nop` + `far_lbl: ret` | **rejected** | `error: PC-relative fixup target 'far_lbl' (0xca) does not fit the signed 8-bit displacement` |

**Observation.** The label path is correct: the base is the real next IP and an
out-of-range displacement is a hard error. Only the numeric path is broken. This
matters because it shows the library already knows how to reject; the numeric
path bypasses that knowledge.

## 3. x86-64: immediate and displacement form selection (EC-01, EC-02, EC-04)

| Source | XirAsm bytes | `llvm-mc` bytes | Match |
|---|---|---|---|
| `add rax, 1` | `48 83 c0 01` (imm8) | `48 83 c0 01` | yes |
| `add rax, 300` | `48 05 2c 01 00 00` | `48 05 2c 01 00 00` | yes |
| `add rax, 0x10000` | `48 05 00 00 01 00` | — | accumulator form |
| `mov rax, rbx` | `48 89 d8` | `48 89 d8` | yes |
| `mov rax, [rbp-8]` | `48 8b 45 f8` (disp8) | `48 8b 45 f8` | yes |
| `mov rax, [rbp-200]` | `48 8b 85 38 ff ff ff` (disp32) | — | disp32 |

**Observation.** Both encoders make identical choices, and both are legal. That
is exactly the problem the FMP solves: `add rax, 300` has at least two legal
encodings (`05 id` accumulator and `81 /0 id` ModRM), both tools pick the
accumulator form, and neither offers an operand-level way to request the other.
`EC-01`, `EC-02` and `EC-04` now have observed counterexamples rather than
hypothetical ones.

There is no text qualifier for these choices: the x86 operand parser recognises
`short`, `near`, `far` and `strict` only, and only for branch operands
(`api.zig:759-767`). Immediates and displacements have no equivalent.

## 4. RV64: forms, ranges, and the absence of auto-compression (EC-19, EC-20)

Prelude `riscv.use64();`.

| Source | XirAsm bytes | `llvm-mc -mattr=+c` bytes | Match |
|---|---|---|---|
| `addi a0, a1, 5` | `13 85 55 00` | `13 85 55 00` | yes |
| `addi a0, a1, 2047` | `13 85 f5 7f` | `13 85 f5 7f` | yes |
| `addi a0, a1, 2048` | **rejected** | — | correct |
| `addi a0, a1, -2048` | `13 85 05 80` | `13 85 05 80` | yes |
| `addi a0, a1, -2049` | **rejected** | — | correct |
| `addi a0, a0, 1` | `13 05 15 00` (4 bytes) | — | **no compression** |
| `nop` + `addi a0, a0, 1` | `13 00 00 00` + `13 05 15 00` | — | `nop` is 4 bytes |
| `c.addi a4, 5` | `15 07` | `15 07` | yes |
| `c.addi a6, 5` | **rejected** | — | x16 outside `x8..x15` |
| `c.addi a0, 0` | `01 05` | — | `c.nop` hint, architecturally legal |
| `beq a0, a1, 0x100` | `63 00 b5 10` | `63 00 b5 10` | yes |
| `beq a0, a1, 0x1008` | **rejected** | — | outside ±4 KiB |
| `jal ra, 0x100` | `ef 00 00 10` | `ef 00 00 10` (`jal 256`) | yes |
| `c.j 0x100` | `01 a2` | — | yes |
| `c.j 0x800` | **rejected** | — | outside ±2 KiB |

**Observation.** The RISC-V path is genuinely strict: out-of-range immediates,
out-of-range branch displacements and compressed-register violations are all
rejected. It also never compresses automatically: `addi a0, a0, 1` stays 4 bytes
even though `c.addi` would fit, and `nop` expands to the 4-byte `addi x0,x0,0`
rather than `c.nop`. `EC-19` and `EC-20` are confirmed from the other direction:
the library's *correct* restraint is the behaviour our contract must mandate.

**Caveat.** These rejections reach the user as one message,
`error: unsupported RISC-V instruction form`. The library returns distinct errors
(`ImmediateOutOfRange`, `RegisterOutOfRange`, `OperandCountMismatch`, …), but
`mapX86EncodeError` and its RISC-V counterpart collapse them
(`src/frontend/backend_adapter.zig:573-587`). The library's error set is usable;
the frontend's is not.

## 5. AArch64: no encoder without the macro library (F-06, OD-07)

| Test | Result |
|---|---|
| `--isa aarch64` with `add x0, x1, x2`, no import | `error: instruction text emission is not supported for this target ISA` |
| Same with `import("arm/a64-macros.inc");` | 4 bytes |
| `tests/isa/arm/label_case.asm` | 48 bytes |

`label_case.asm` output, split into instructions, with the `llvm-mc` result:

| Instruction | XirAsm | `llvm-mc -triple=aarch64` | Match |
|---|---|---|---|
| `adrp x11, MyTable` | `0b 00 00 90` | `0b 00 00 90` (`adrp x11, #0`) | yes |
| `add x11, x11, :lo12:MyTable` | `6b 21 00 91` | `6b 21 00 91` (`add x11, x11, #8`) | yes |
| `ldr x12, [x11, :lo12:MyTable]` | `6c 05 40 f9` | `6c 05 40 f9` (`ldr x12, [x11, #8]`) | yes |
| `mov x13, #1` | `2d 00 80 d2` | `2d 00 80 d2` (`movz x13, #1`) | yes |
| `ret` | `c0 03 5f d6` | `c0 03 5f d6` | yes |

**Observation.** AArch64 encoding is correct and it is entirely macro-driven.
Without the include there is no AArch64 encoder at all, which is the strongest
possible confirmation of F-01: the library has no AArch64 backend, and the
frontend reaches AArch64 only through an interpreted include tree.

Note the `mov x13, #1` row: the source says `mov`, the bytes are `movz`. The
expansion happens in the macro layer before any encoder runs. That is `EC-16`
(`mov` alias family) observed in the wild, and it is `INV-01`/`INV-03` material:
the alias choice is made for the user.

## 6. What this record does and does not prove

Proven by experiment:

- unqualified x86 branches are auto-shortened and auto-promoted (§2, §2.1);
- numeric `short` branches are truncated without a range check and use a base
  that ignores the instruction offset (§2.2);
- label branches are range-checked correctly (§2.3);
- x86 immediate and displacement form selection is implicit and matches LLVM
  (§3);
- RV64 rejects out-of-range values and never compresses automatically (§4);
- AArch64 requires the macro include and is absent otherwise (§5).

Not proven here:

- the *mechanism* by which numeric branch targets escape the fixup path — the
  explanation in §2.2 is an inference from behaviour plus
  `src/frontend/backend_adapter.zig:266-287`, not a traced call path;
- anything about RISC-V pairs (`auipc` + `lo12`) — not exercised;
- anything about LLVM internals — LLVM was used only as an oracle.
