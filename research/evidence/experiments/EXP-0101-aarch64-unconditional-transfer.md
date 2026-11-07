# EXP-0101 -- AArch64 unconditional transfers: the field, the register forms, and the link bit

- Date: 2026-11-08
- Question: what do `b`, `br`, `blr` and `ret` encode, what does the `b`/`bl`
  split change, and which register values does the assembler accept?
- Toolchain: `llvm-mc`/`llvm-readobj`/`llvm-objcopy` 23.1.2
- Definition: `definitions/aarch64/0.18.0.json` (the `0.17.0` table plus
  `aarch64:b/imm26`, `br/rn`, `blr/rn` and `ret/rn`)
- Fixture oracle: `fixtures/aarch64/positive/A64-P21-b-imm26.oracle.json`,
  `A64-P21-b-local-symbol.oracle.json` and `A64-P22-register-branch.oracle.json`
- Source: `research/evidence/experiments/EXP-0101/`
- Decision: `ADR-0100`

## 1. `b`: the field is `imm26`

`field.asm` is three `b` instructions with fixed byte displacements:

| Source | Bytes | Word | Field |
|---|---|---|---|
| `b #0` | `00 00 00 14` | `0x14000000` | 0 |
| `b #4` | `01 00 00 14` | `0x14000001` | 1 |
| `b #-4` | `ff ff ff 17` | `0x17ffffff` | -1 |

`imm26` sits at 0-25, bits 29-30 are `00`, bits 26-28 are `101` and bit 31 is
0 for `b` (it is 1 for `bl`); the Arm MRS `B` node fixes that shape. llvm-mc's
`#n` is a *byte* displacement, so the plan's field values 0, 1 and -1 are
spelled `#0`, `#4` and `#-4` in the source. No relocations: the values are
literals.

The measured ends are `b #33554428` = `0x147fffff` (`imm26 = 33554431`) and
`b #-33554432` = `0x17800000` (`imm26 = -33554432`). `b #33554432` is outside
the field, and llvm-mc 23.1.2 does not reject it: it wraps to `0x14800000`
(`imm26 = 0`). v0 is stricter — the operand slot is the 26-bit field, and
`N04e` states `33554432` to get `E-RANGE-002` instead of a silently displaced
branch (`INV-07`).

## 2. `br` / `blr` / `ret`: one shape, two varying fields

`indirect.asm` is six instructions:

| Source | Bytes | Word | `op` (21-22) | `Rn` (5-9) |
|---|---|---|---|---|
| `br x1` | `20 00 1f d6` | `0xd61f0020` | `00` | 1 |
| `br x0` | `00 00 1f d6` | `0xd61f0000` | `00` | 0 |
| `blr x2` | `40 00 3f d6` | `0xd63f0040` | `01` | 2 |
| `ret x30` | `c0 03 5f d6` | `0xd65f03c0` | `10` | 30 |
| `ret x0` | `00 00 5f d6` | `0xd65f0000` | `10` | 0 |
| `ret x19` | `60 02 5f d6` | `0xd65f0260` | `10` | 19 |

All six share `op0 = 110` at 29-31, `101` at 26-28, bit 25 = 1, `Z = 0` at 24,
bit 23 = 0, `op2 = 11111` at 16-20, `0000` at 12-15, `A = 0`/`M = 0` at 10-11
and `Rm = 00000` at 0-4. Only `op` and `Rn` move, so one slot at `[5,5]` plus a
fixed template per row expresses the family. There are no relocations: every
operand is a register.

The register class is `Xn`. Measured acceptance and rejection under
llvm-mc 23.1.2:

| Source | Result |
|---|---|
| `br xzr` | `e0 03 1f d6` (`0xd61f03e0`), accepted, `Rn = 31` |
| `ret xzr` | `e0 03 5f d6` (`0xd65f03e0`), accepted, `Rn = 31` |
| `br x31` | prints `br xzr`, `0xd61f03e0` |
| `ret` | `c0 03 5f d6`, i.e. `ret x30` |
| `ret w0` | rejected: `invalid operand for instruction` |
| `blr sp` | rejected: `invalid operand for instruction` |

So the five-bit field encodes all 32 values, 31 included; the slot needs no
`excluded` list. The `sp` reading is not available because the node's operand is
`Xn` (where 31 means `xzr`), and a `w32` operand is a different register class.

## 3. `b` against local labels

`local.asm` puts `back` at 0, `here` at 4 and `ahead` at 8, with one `b` at
each site:

```text
.text
back:
  b ahead
here:
  b here
ahead:
  b back
```

The bytes are `02 00 00 14 00 00 00 14 fe ff ff 17`, i.e. `0x14000002`,
`0x14000000` and `0x17fffffe`. The byte displacements are +8, 0 and -8, and the
field values are `2`, `0` and `-2`, which is `(S + A - P) >> 2` with `P` the
instruction's own address. llvm-mc resolves both labels, so `llvm-readobj -r`
is empty and no linker is involved.

A source-level trap: two labels with no instruction between them both bind to
the *next* instruction's address, so a source that intends an intermediate
offset has to keep an instruction between the labels.

## 4. The link bit and the two relocations

`extern.asm` is `b ext` followed by `bl ext`. The object bytes are
`00 00 00 14 00 00 00 94` (both fields zero) and `llvm-readobj
--relocations` reports:

```text
0x0 R_AARCH64_JUMP26  ext 0x0
0x4 R_AARCH64_CALL26  ext 0x0
```

The two words differ only in bit 31, and the two relocation kinds differ. That
is the counterexample for `EC-41`: the choice is observable to the consumer of
the artifact, so the link bit belongs to the form, not to the fixup and not to a
modifier. `N19d` states `{ "name": "link", "value": true }` on the `b` target
and gets `E-OPERAND-003` at the modifiers array.

## 5. The assembler's bare `ret`

`default.asm` is a single `ret`. It assembles to `c0 03 5f d6` (`0xd65f03c0`),
the same word as `ret x30`. That default is a hidden input: a plan that names
`aarch64:ret` would be asking the materializer to supply `x30`. v0 has no such
form, so `N01y` is `E-FORM-001`, and `aarch64:ret/rn` requires the register
(`A64-P22` names `30`, `0` and `19`).

## 6. Scope of the measurement

- The conditional siblings `cbz`/`cbnz`/`tbz`/`tbnz` are not measured here and
  do not ship; `EC-18` owns that decision and `N01x` keeps the absence loud.
- Authenticated branches (`braa`/`blraa`) and the `sp` register class are out
  of scope; the first is a different MRS node, the second has no operand kind.
- The measurement says nothing about `b`'s run-time semantics. The definition
  states the field layout, not what the instruction does; the format has no
  defaults and no optional bytes (`07_definition_format.md` §5).

## Reproduce

```text
python research/evidence/experiments/EXP-0101/measure.py
```

The script assembles the five inputs, asserts the five byte strings and the two
relocation names, and writes `bytes.txt`, `relocations.txt` and
`show-encoding.txt`.
