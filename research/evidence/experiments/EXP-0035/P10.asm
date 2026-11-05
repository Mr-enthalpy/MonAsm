# X86-P10 — `EXP-0035`. Assemble with:
#   llvm-mc -triple=x86_64 -filetype=obj P10.asm -o P10.o
#   llvm-objcopy -O binary --only-section=.text P10.o P10.bin
#
# The two `8B` register-direct rows are hand-derived from the form's placements
# (`ADR-0033`) and emitted as bytes rather than mnemonics, because `llvm-mc`
# always selects the `89` direction for a register-to-register move (`EC-27`).
# `llvm-mc -disassemble` confirms both decodings:
#   4c 8b e0 -> movq %rax, %r12
#   4d 8b f5 -> movq %r13, %r14
	movq	%r8, %r9
	movq	%r15, %rax
	.byte	0x4c, 0x8b, 0xe0
	.byte	0x4d, 0x8b, 0xf5
	movq	%r15, %r8
	addq	$1, %r8
	addq	$0x7fffffff, %r15
	movq	L1(%rip), %r10
	movq	%r11, L1(%rip)
L1:
	.byte	0xaa, 0xbb, 0xcc, 0xdd
