# EXP-0003 — x86-64 alias pairs and branch length

- Date: 2026-11-04
- Tool: LLVM 23.1.2 (`llvm-mc`, `llvm-objdump`)
- Script: `exp0003.py`
- Feeds: OD-11 / ADR-0004 (`EC-27`, `EC-28`), `EC-01`, `EC-03`, `EC-04`
- Supersedes: none

## Question

For each alias pair in the v0 x86 slice, is the difference a residual choice
left to the encoder, or a distinct row of the ISA opcode table? A residual
choice would defeat ADR-0004; a distinct row makes `form_id` the carrier.

Secondary question, for Phase 3: what does llvm-mc actually do with a numeric
branch target, so it is used as an oracle only where it is one?

## Method

1. Assemble each snippet with `llvm-mc -triple=x86_64 -x86-asm-syntax=intel
   -show-encoding`. This reports the encoding only when the whole instruction is
   resolved; branch targets leave a fixup and are handled in step 2.
2. Assemble the branch snippets with `-filetype=obj`, then read the bytes with
   `llvm-objdump -d`. This runs LLVM's assembler and layout path, which is the
   path that decides branch lengths.
3. Decode the alternative byte strings with `llvm-mc -triple=x86_64
   -disassemble`. This is the independent direction: it shows that the bytes the
   assembler refuses to emit are still legal instructions.

No project code is involved in any step, so the materializer is not validating
itself.

## Measured

<!-- measured-table:start -->
| Direction | Input | Bytes | Decodes as |
|---|---|---|---|
| assemble | `mov rax, rbx` | `48 89 d8` | |
| assemble | `mov eax, ebx` | `89 d8` | |
| assemble | `add rax, 1` | `48 83 c0 01` | |
| assemble | `add rax, 300` | `48 05 2c 01 00 00` | |
| assemble | `mov eax, 300` | `b8 2c 01 00 00` | |
| assemble | `jmp .+0x81` | `eb 7f` | |
| assemble | `jmp .+0x82` | `e9 7d 00 00 00` | |
| assemble | `jmp .+0x1000` | `e9 fb 0f 00 00` | |
| assemble | `jmp 0x12` | `e9 00 00 00 00` | |
| assemble | `jmp 0x7f` | `e9 00 00 00 00` | |
| assemble | `jmp 0x80` | `e9 00 00 00 00` | |
| assemble | `jmp 0x1000` | `e9 00 00 00 00` | |
| assemble | `jmp 5` | `e9 00 00 00 00` | |
| disassemble | `48 89 d8` | | `movq %rbx, %rax` |
| disassemble | `48 8b c3` | | `movq %rbx, %rax` |
| disassemble | `40 89 d8` | | `movl %ebx, %eax` |
| disassemble | `89 d8` | | `movl %ebx, %eax` |
| disassemble | `48 81 c0 2c 01 00 00` | | `addq $300, %rax # imm = 0x12C` |
| disassemble | `c7 c0 2c 01 00 00` | | `movl $300, %eax # imm = 0x12C` |
| disassemble | `eb 0e` | | `jmp 14` |
| disassemble | `e9 fb 0f 00 00` | | `jmp 4091` |
<!-- measured-table:end -->

## Readings

1. **`mov rax, rbx` has two legal 3-byte encodings.** `48 89 d8` (`89 /r`,
   `MOV r/m64, r64`) and `48 8b c3` (`8B /r`, `MOV r64, r/m64`) both decode to
   `movq %rbx, %rax`. llvm-mc emits only the first and exposes no selector for
   the second. This is `EC-27`: the two are distinct opcode-table rows, so
   `form_id` carries the difference, and `expected_size` cannot detect a wrong
   choice because both are 3 bytes.
2. **A redundant `REX` prefix is legal.** `40 89 d8` decodes to
   `movl %ebx, %eax`, exactly like `89 d8`, but is one byte longer. This is
   `EC-28`: the variation is not a plan decision, it is a definition rule (emit
   the minimal prefix set). No plan field may request the redundant byte.
3. **The accumulator form is shorter, not the same length.**
   `48 81 c0 2c 01 00 00` (`81 /0 id`) decodes to `addq $300, %rax` and
   `c7 c0 2c 01 00 00` (`C7 /0 id`) decodes to `movl $300, %eax`. Both are legal
   and neither tool emits them, because both tools prefer the accumulator form
   (`48 05 …`, `b8 …`), which has no ModRM byte. The earlier registry text said
   "same length"; that was wrong and is corrected in `02_encoding_choices.md`.
4. **Branch length depends on target distance.** `jmp .+0x81` is `eb 7f` (2 B);
   `jmp .+0x82` is `e9 7d 00 00 00` (5 B). One byte of distance changes the
   instruction by three. This is `EC-03`, and it is why a branch form cannot be
   inferred from the target value (INV-04).
5. **A bare numeric branch target does not reach the encoder.** `jmp 0x12`,
   `jmp 0x7f`, `jmp 0x80`, `jmp 0x1000` and `jmp 5` all emit
   `e9 00 00 00 00` under `-filetype=obj`. `inference`: this is a front-end
   expression path, not an encoder property; the operand is not resolved to an
   absolute address in the section. Whatever the mechanism, the consequence is
   concrete: llvm-mc cannot be used as an oracle for a numeric branch target.
   XirAsm's silent truncation (F-06, `jmp short 0x82` → `eb 80`) lives on the
   numeric path, so the two tools are not comparable there — the comparison must
   use labels or `.+N`.
6. **The disassembler prints the displacement, not the target.** `eb 0e` prints
   as `jmp 14` and `e9 fb 0f 00 00` as `jmp 4091` (0xFFB). Branch target
   arithmetic must be computed from the plan and compared as bytes; reading the
   target off the disassembler would silently accept an off-by-`size` error.

## What this proves and what it does not

Proves:

- every alternative byte string in the table is a legal instruction, decoded by
  an independent tool;
- llvm-mc's assembler makes each form choice internally and offers no operand to
  override it;
- branch length in llvm-mc is a function of target distance.

Does not prove:

- which encoding our materializer must emit. That is the plan's `form_id` plus
  the definition (ADR-0004), checked against two sources per vector.
- that llvm-mc's choices are stable across versions. The version is pinned, and
  every fixture records it.

## Reproduce

```bash
python exp0003.py          # print the table
python exp0003.py --emit   # rewrite the measured table above
```

`FMP_LLVM_BIN` overrides the default LLVM directory. The script needs Python 3.8
or newer and does not import project code.
