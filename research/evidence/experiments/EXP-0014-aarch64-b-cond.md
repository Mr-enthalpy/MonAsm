# EXP-0014 — AArch64 `B.cond`: the condition field and the ±1 MB displacement

- Date: 2026-11-04
- Question: which bits of `B.cond` are variable, are all sixteen conditions
  encodable, and what exactly does the assembler accept for the label offset?
- Toolchain: `llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj` 23.1.2
- Definition source: Arm MRS 2026-06_rel, `Instructions.json`
  (`sha256:a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe`),
  node `B_only_condbranch`
- Semantics source: Arm A64 ISA, `B.cond`, revision `2026-03_rel` (2026-03-26),
  read at the public mirror
  `https://www.scs.stanford.edu/~zyedidia/arm64/b_cond.html`; the canonical copy is
  Arm's `DDI0602` page on `developer.arm.com`. Facts are restated; the page's text
  is not copied into this repository.

## 1. What the sources state

The MRS node gives six encoding fields:

| Field | start+width | MRS value |
|---|---|---|
| `op0` | 29+3 | `'010'` |
| — | 26+3 | `'101'` |
| — | 24+2 | `'00'` |
| `imm19` | 5+19 | `xxxxxxxxxxxxxxxxxxx` |
| `o0` | 4+1 | `'0'` |
| `cond` | 0+4 | `xxxx` |

Two variable fields, four fixed ones; the template is therefore `00000054` with
`cond` in the low nibble and `imm19` starting at bit 5.

The ISA page states three things:

- `<cond>` is one of the standard conditions, "encoded in the standard way", and
  it lists all sixteen — `EQ` through `LE`, then `AL` (1110) and `NV` (1111);
- `<label>` is the program label to branch to, with an offset from the
  instruction's address in the range ±1 MB, encoded as `imm19` times 4;
- decode is `offset = SignExtend(imm19::'00')` and the branch is taken when
  `ConditionHolds(condition)`.

So the *field* is a 4-bit condition; the sixteen names are values of that field,
not sixteen instructions. The page also states that the instruction is a hint
("this is not a subroutine call or return") for branch-type prediction, which
does not affect the bytes.

## 2. The sixteen conditions, measured

One instruction per run, `b.<cond> .+4`, assembled with
`llvm-mc -triple=aarch64 -filetype=obj` and read back with `llvm-objcopy -O
binary --only-section=.text`:

| `<cond>` | value | word | bytes |
|---|---|---|---|
| `eq` | 0x0 | `0x54000020` | `20 00 00 54` |
| `ne` | 0x1 | `0x54000021` | `21 00 00 54` |
| `cs` | 0x2 | `0x54000022` | `22 00 00 54` |
| `cc` | 0x3 | `0x54000023` | `23 00 00 54` |
| `mi` | 0x4 | `0x54000024` | `24 00 00 54` |
| `pl` | 0x5 | `0x54000025` | `25 00 00 54` |
| `vs` | 0x6 | `0x54000026` | `26 00 00 54` |
| `vc` | 0x7 | `0x54000027` | `27 00 00 54` |
| `hi` | 0x8 | `0x54000028` | `28 00 00 54` |
| `ls` | 0x9 | `0x54000029` | `29 00 00 54` |
| `ge` | 0xa | `0x5400002a` | `2a 00 00 54` |
| `lt` | 0xb | `0x5400002b` | `2b 00 00 54` |
| `gt` | 0xc | `0x5400002c` | `2c 00 00 54` |
| `le` | 0xd | `0x5400002d` | `2d 00 00 54` |
| `al` | 0xe | `0x5400002e` | `2e 00 00 54` |
| `nv` | 0xf | `0x5400002f` | `2f 00 00 54` |

All sixteen assemble. The words differ **only** in bits 0–3, which is the
measured form of "the condition is a field, not a shape": there is no second
opcode, no length change, no relocation. `b.al` and `b.nv` are accepted and encode
`0x5400002e` / `0x5400002f`; the assembler does not fold them into the 26-bit
unconditional `b`.

## 3. The vector

Input (LF, trailing newline, two leading spaces; 33 bytes,
`sha256:ea259809351277bcd6914f1c5a6bedea6f2f37405bcb98ef553c0fbc7147ec2b`):

```text
a:
  b.eq c
c:
  b.ne a
  b.gt a
```

`llvm-mc -triple=aarch64 -filetype=obj bcond.s -o bcond.o` emits **no
relocations** (`llvm-readobj -r` prints an empty list), because all three targets
are local labels in the same section; the object's `.text` is 12 bytes.

| Offset | Bytes | Word | `llvm-objdump` |
|---|---|---|---|
| 0 | `20 00 00 54` | `0x54000020` | `b.eq 0x4 <c>` |
| 4 | `e1 ff ff 54` | `0x54ffffe1` | `b.ne 0x0 <a>` |
| 8 | `cc ff ff 54` | `0x54ffffcc` | `b.gt 0x0 <a>` |

Output: 12 bytes,
`sha256:67853f38e2b3913bd42e25250f714278aff11d845370c5bae27d542763edfdfa`.

Three things are pinned by one vector:

- `b.eq c` at 0 to 4 is `+4`, so `imm19 = 1` (`1 << 5 = 0x20`);
- `b.ne a` at 4 to 0 is `−4`, so `imm19 = −1`, which is `0x7ffff` in 19 bits
  (`0x7ffff << 5 = 0xffffe0`, plus `cond = 1` → `0xffffe1`);
- `b.gt a` at 8 to 0 is `−8`, so `imm19 = −2` (`0x7fffe << 5 = 0xffffc0`, plus
  `cond = 0xc` → `0xffffcc`).

The three conditions (`0x0`, `0x1`, `0xc`) and the three displacements
(`+1`, `−1`, `−2` in field units) are all different, so a defect in either field
moves bytes the others do not.

Boundary runs, same single-instruction method:

| Source | Result |
|---|---|
| `b.eq .+0` | accepted, `0x54000000` (`00 00 00 54`) |
| `b.eq .+4` | accepted, `0x54000020` (`20 00 00 54`) |
| `b.eq .+1048572` | accepted, `0x547fffe0` (`e0 ff 7f 54`) — `imm19 = 0x3ffff` |
| `b.eq .+1048576` | **rejected** |
| `b.eq .-1048576` | accepted, `0x54800000` (`00 00 80 54`) — `imm19 = −0x40000` |
| `b.eq .-1048580` | **rejected** |

The reachable set is therefore `−1048576 … +1048572`, not "±1 MB": the page's
±1 MB is the label range before the ×4 encoding, and the low end is the one that
uses the full magnitude. A plan states the displacement in bytes and the fixup
scales it (`transform_shift: 2`), so the range check is on the scaled value with
`signed: true, bits: 19, align_bits: 2`.

## 4. The two fields are independent

`b.eq .+4` is `20 00 00 54` and `b.ne .+4` is `21 00 00 54`: one nibble apart.
`b.eq .-4` is `e0 ff ff 54` and `b.eq .+4` is `20 00 00 54`: bits 5–23 apart, low
nibble identical. Neither spelling changes the instruction's length, so a plan
that names the wrong condition produces a valid 4-byte word that branches on the
wrong flags — a silent wrong program, which is why the condition has to be a plan
field and not a table default.

## 5. What this fixes, and what it does not

Fixes:

- the form's template: `00000054`, with `cond` at `[0,4]` and `imm19` at `[5,19]`,
  both derived from the MRS node by the generator;
- the operand rule: the condition is `aarch64.cond`/`cond4` field content in
  `0..15`, and the target is `aarch64.rel`/`imm19` field content, with the byte
  displacement expressed as a `pcrel_begin` + `scale` fixup;
- the negative evidence: `cond = 16` is `E-RANGE-001` (masking it produces `eq`),
  and a displacement of `262144` field units is `E-RANGE-002`.

Does not fix:

- `cbz`/`cbnz`/`tbz`/`tbnz`. They are the other half of `EC-18`, with different
  opcodes and operand sets (a register plus `imm19`/`imm14`), so they need their
  own nodes and rows.
- The condition's *meaning*. `ConditionHolds` reads the flags; a plan cannot state
  flags, and the materializer does not interpret them. `NV` is encodable here
  exactly as the architecture defines it, and the table does not add a rule about
  which condition a program should test.

## 6. Result

The row shipped in a new document rather than in `0.2.0`, so a plan built against
an older table keeps its exact bytes and cannot silently acquire a new form:

```text
definition  definitions/aarch64/0.3.0.json
namespace   monasm.isa.aarch64
version     0.3.0
forms       6
digest      sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb
```

The five `0.2.0` rows are repeated verbatim, so the only change is the added
`aarch64:b.cond/imm19`; the generator asserts the frozen `0.1.0` and `0.2.0`
digests, which is what shows the earlier rows did not move (`EXP-0008` §6).

Our materializer reproduces the vector byte-for-byte — 12 bytes,
`20000054e1ffff54ccffff54`, no fixup records, because all three displacements are
resolved in place — and rejects the two negatives with the registered diagnostic
sets:

| Fixture | Input | Diagnostic |
|---|---|---|
| `A64-P4-b-cond` | three `b.cond` rows, conditions 0/1/12, displacements +4/−4/−8 | 12 bytes, `sha256:67853f38…` |
| `N03-cond-out-of-range` | `cond = 16` | `E-RANGE-001` at `/instructions/0/operands/0/payload/value`, `min 0`, `max 15` |
| `N04c-bcond-imm19-out-of-range` | `imm19 = 262144` | `E-RANGE-002` at `/instructions/0/operands/1/payload/value`, `min −262144`, `max 262143` |

Two facts make this slice different from the `add` rows before it. The oracle
needed no linker: `llvm-mc` resolved the three local labels itself and
`llvm-readobj -r` printed an empty relocation list, so the compared bytes are the
assembler's own rather than a linker's output. And the condition is *plan data*,
not a table row: `{"value": 1}` means `ne` because the field is `cond`, which is
why `cond = 16` has to be a range error rather than a masked nibble.
